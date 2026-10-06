"""听力音频生成器——eng_jr 6+1 道 listening 题 -> stepaudio-2.5-tts mp3。

为什么需要本工具：英语初中卷型（spec_eng_jr_final 听力大题 30 分）的听力题
此前只有题面文字，「听力」无音频可听。本工具把初中英语题库里全部
form=listening 的题（6 道 english_gap_llm_011..016 + 1 道 eng_en_jr_0194）
用仓内既有 TTS 内核合成 mp3，落到 data/audio/{item_id}.mp3，并把 sha256
清单写入 data/audio/manifest.json。

复用既有内核，不造平行实现：
- TTS 客户端：``mm_client.MMClient.tts``——step_plan 端点白名单
  （https://api.stepfun.com/step_plan/v1/audio/speech）、模型
  ``stepaudio-2.5-tts``、音色 ``linjiajiejie``、mp3；key 只从环境变量读
  （``XX_LLM_API_KEY`` / ``STEPFUN_API_KEY``，见 mm_client.KEY_ENV_VARS），
  **只进内存、绝不落盘**（本脚本不打印、不缓存、不写 key）；
- 朗读文本：题面里的「听力材料」原文（见 listening_material_text），不新增
  教学内容——唯一的例外是 eng_en_jr_0194（题面只有作答指令、无材料原文），
  音频文稿按该题自己的标答关键词（Sports Day / next Friday / school
  playground / relay race / first prize）编写，manifest 里 text_source
  如实标注 "authored"（其余 6 道 = "stem"）。

可复跑（sha256 清单）：默认模式下逐题对照 manifest 的 sha256——文件在且
哈希一致 → 跳过（0 次 TTS 调用）；缺失/不一致 → 恰好一次 tts 调用后原子
重写。``--force`` 全部重合成；``--check`` 只校验清单与文件（零出网），
供验收门/CI 使用。正常全量生成 = 7 次调用（预算 ≤10）。

用法：
  eval "$(agent-tools/llm-env stepfun)"   # key 走 env，不落盘
  python tools/gen_listening_audio.py               # 生成缺失/不一致的
  python tools/gen_listening_audio.py --force       # 全部重合成（7 次调用）
  python tools/gen_listening_audio.py --check       # 零出网校验清单
"""
import argparse
import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

try:  # Windows 控制台中文输出保护
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

from xuexing.mm_client import (  # noqa: E402
    ENDPOINTS,
    MODEL_TTS,
    TTS_VOICE,
    MMClient,
    HttpTransport,
)
from xuexing.paper_by_spec import load_stage_bank  # noqa: E402

DATA_DIR = os.path.join(ROOT, "data")
AUDIO_DIR = os.path.join(DATA_DIR, "audio")
MANIFEST_PATH = os.path.join(AUDIO_DIR, "manifest.json")

# 音频文件名（=题库 item.audio 字段值）字符白名单，与 paper_render._audio_html
# 的渲染白名单一致——生成器不产出渲染层会拒绝的文件名。
_NAME_CHARS = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")

# eng_en_jr_0194：题面只有作答指令（假设听一段学校运动会广播），无材料原文。
# 音频文稿按该题标答的 5 个关键词（活动/时间/地点/项目/结果）编写——不引入
# 标答之外的事实，manifest 如实标注 text_source="authored"。
AUTHORED_TEXTS = {
    "eng_en_jr_0194.mp3": (
        "Attention, everyone! Here is some news about our School Sports Day. "
        "It will be held next Friday on the school playground. "
        "The relay race will start at nine in the morning, "
        "and our class won first prize last year. "
        "Please come and cheer for your classmates!"
    ),
}


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def listening_material_text(stem: str) -> str:
    """题面 -> 朗读文本（确定性纯函数）。

    规则：取最后一个「听力材料」标记行**之后**的内容（标题行如「图书馆借书」
    不是材料）；在题块标记处截断（Questions: / 请根据… / 行首「数字.」的印刷
    题——印刷题学生看得见，音频只播材料，与真实听力考试一致）；逐行去掉行首
    「M:」/「W:」说话人标记（那是卷面记号，不是要说的话）。en_en_jr_0194 这类
    无材料题面走 AUTHORED_TEXTS 覆盖（调用方保证）。
    """
    lines = stem.splitlines()
    start = 0
    for i, line in enumerate(lines):
        if "听力材料" in line:
            start = i + 1
    end = len(lines)
    for i in range(start, len(lines)):
        s = lines[i].strip()
        if s == "Questions:" or s.startswith("请根据") or _is_question_line(s):
            end = i
            break
    body = []
    for line in lines[start:end]:
        s = line.strip()
        if s[:3] in ("M: ", "W: "):
            s = s[3:].strip()
        if s:
            body.append(s)
    return "\n".join(body).strip()


def _is_question_line(s: str) -> bool:
    """印刷题行：行首 1..2 位数字 + 「.」+ 空格（如 "1. What day ..."）。"""
    head, sep, _rest = s.partition(".")
    return sep == "." and head.isdigit() and head and s[len(head):][:2] in (". ", ".\t")


def discover_listening_items():
    """初中英语题库里的全部 listening 题（id 升序）-> [(item, 文件名)]。

    fail-closed：一题都没有 / 文件名不满足渲染白名单 → 直接报错退出，不生成
    半套资产。预期恰为 6+1=7 道（6 道 english_gap_llm_011..016 + 1 道
    eng_en_jr_0194），数量变化时如实报出，不静默吞。
    """
    bank, _grades = load_stage_bank(DATA_DIR, "english", "junior")
    rows = []
    for item in bank.items():
        if getattr(item, "form", "") != "listening":
            continue
        fname = f"{item.id}.mp3"
        if not fname or not set(fname) <= _NAME_CHARS:
            raise SystemExit(f"FAIL: unsafe audio file name for {item.id}: {fname!r}")
        rows.append((item, fname))
    if not rows:
        raise SystemExit("FAIL: no form=listening items in english junior bank")
    return sorted(rows, key=lambda row: row[0].id)


def _mp3_ok(audio: bytes) -> str:
    """TTS 返回字节的最小验收：非空 + mp3 头（ID3 标签或 0xFF 帧同步）。"""
    if not isinstance(audio, bytes) or len(audio) < 200:
        raise SystemExit(f"FAIL: tts returned implausible bytes: {len(audio) if audio else 0}B")
    if not (audio[:3] == b"ID3" or (audio[0] == 0xFF and (audio[1] & 0xE0) == 0xE0)):
        raise SystemExit("FAIL: tts returned bytes without an mp3 header")
    return sha256_hex(audio)


def load_manifest() -> dict:
    if not os.path.exists(MANIFEST_PATH):
        return {"model": MODEL_TTS, "voice": TTS_VOICE,
                "endpoint": ENDPOINTS["tts"], "files": {}}
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        return json.load(f)


def run(force: bool, check_only: bool) -> int:
    rows = discover_listening_items()
    manifest = load_manifest()
    files: dict = manifest.setdefault("files", {})

    if check_only:
        missing = []
        for _item, fname in rows:
            path = os.path.join(AUDIO_DIR, fname)
            entry = files.get(fname)
            if entry is None or not os.path.exists(path):
                missing.append(f"{fname}: 清单或文件缺失")
            elif sha256_hex(open(path, "rb").read()) != entry.get("sha256"):
                missing.append(f"{fname}: sha256 与清单不符")
        if missing:
            print("AUDIO-CHECK-FAIL")
            for m in missing:
                print(f"  {m}")
            return 1
        print(f"AUDIO-CHECK-OK（{len(rows)}/{len(rows)} 个 mp3 与清单 sha256 一致）")
        return 0

    todo = []
    for item, fname in rows:
        path = os.path.join(AUDIO_DIR, fname)
        want = files.get(fname, {}).get("sha256")
        if not force and want and os.path.exists(path) \
                and sha256_hex(open(path, "rb").read()) == want:
            print(f"  SKIP  {fname}（sha256 与清单一致，不重复调用 TTS）")
            continue
        todo.append((item, fname, path))
    if not todo:
        print(f"LISTENING-AUDIO-OK：{len(rows)} 题全部与清单一致，本次 TTS 调用 0 次"
              f"（可复跑：无 key 也能过）")
        return 0

    # 只有真要合成才需要 key/MMClient——复跑零调用时不读 env、不建客户端。
    key_env = [v for v in ("XX_LLM_API_KEY", "STEPFUN_API_KEY")
               if os.environ.get(v, "").strip()]
    if not key_env:
        print("FAIL: api key not set: none of XX_LLM_API_KEY, STEPFUN_API_KEY is available")
        return 2
    client = MMClient(transport=HttpTransport())  # key 构造期从 env 解析，只进内存
    os.makedirs(AUDIO_DIR, exist_ok=True)

    calls = 0
    for item, fname, path in todo:
        text = AUTHORED_TEXTS.get(fname) or listening_material_text(item.stem)
        if not text:
            raise SystemExit(f"FAIL: empty audio text for {item.id}")
        audio = client.tts(text)  # 既有内核：step_plan/v1/audio/speech，mp3
        calls += 1
        digest = _mp3_ok(audio)
        tmp = path + ".tmp"
        with open(tmp, "wb") as f:  # 原子写：半截 mp3 不进 data/audio
            f.write(audio)
        os.replace(tmp, path)
        files[fname] = {
            "item_id": item.id,
            "bytes": len(audio),
            "sha256": digest,
            "text": text,
            "text_sha256": sha256_hex(text.encode("utf-8")),
            "text_source": "authored" if fname in AUTHORED_TEXTS else "stem",
        }
        print(f"  TTS   {fname}  {len(audio)}B  sha256={digest[:12]}… "
              f"(text_source={files[fname]['text_source']})")

    manifest["model"] = MODEL_TTS
    manifest["voice"] = TTS_VOICE
    manifest["endpoint"] = ENDPOINTS["tts"]
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    print(f"LISTENING-AUDIO-OK：{len(rows)} 题，本次 TTS 调用 {calls} 次"
          f"（预算 ≤10）；清单 -> {os.path.relpath(MANIFEST_PATH, ROOT)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="eng_jr 听力题 TTS 音频生成（可复跑，sha256 清单）")
    ap.add_argument("--force", action="store_true", help="忽略清单全部重合成（7 次调用）")
    ap.add_argument("--check", action="store_true", help="零出网：只校验 mp3 与清单 sha256")
    args = ap.parse_args()
    return run(force=args.force, check_only=args.check)


if __name__ == "__main__":
    sys.exit(main())
