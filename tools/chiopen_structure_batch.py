"""语文开放答案题结构化批处理（签署测试卡 TC-8 数据侧工具）。

对语文无选项开放题分两阶段处理（两模型族）：
- 结构化（family A）：为 fill/dictation 等生成 acceptable_variants（只允许
  与标答同义/同实的写法：异体字、通假、近义表达、全半角/标点差异），或为
  改错/连线类生成 scoring_points [{point, score>0}]；作文类（essay/
  applied-writing）的 rubric+calibration 属重流程，不在本工具（后续批）。
- 盲答（family B）：另一模型族只看题面作答；
- 比对（确定性代码）：盲答（归一化）命中标答或任一 variant → agree，
  回填 verification [原签名, 盲解签名]；未命中 → chiopen 仲裁队列
  （status open），不回填。结构化字段对 agree/open 一并写入（其有效性
  独立于裁决），并逐题留痕 struct ledger。

纪律：不改 form 原值；不删题；不改写答案本身；key 只从环境变量读
（LLM_API_KEY/LLM_BASE_URL=结构化族，BLIND_LLM_API_KEY/BLIND_LLM_BASE_URL=
盲答族）；配额熔断复用 blind_solve_items。
"""
import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

from blind_solve_items import _chat, _check_endpoint, extract_answer  # noqa: E402

STRUCTURE_RULES = {
    "fill": "生成 acceptable_variants：除标准答案外，学生可接受的其他等价写法。只允许：异体字/通假字、同义等价表达、可互换的语序、全半角与标点差异。禁止编造新的事实或含义。标准答案本身必须也在数组里。",
    "dictation": "生成 acceptable_variants：默写题的可接受写法差异（如「唯」/「惟」类异体互通——仅当各版本教材皆可）。禁止放宽到错误默写。标准答案必须也在数组里。",
    "transcription": "生成 acceptable_variants：与标准答案等价的转写差异。标准答案必须也在数组里。",
    "correction": "生成 scoring_points：改错题的采分点（找出错误、正确改法），格式 [{\"point\": 描述, \"score\": 分值}]，每个 score>0。",
    "translation": "生成 acceptable_variants：与标准答案等价的翻译写法（可容忍的同义替换）。标准答案必须也在数组里。",
    "connection": "生成 scoring_points：连线/匹配题的采分点（每组正确配对一个采分点），格式 [{\"point\": 描述, \"score\": 分值}]。",
}
VARIANT_FORMS = ("fill", "dictation", "transcription", "translation")


def normalize(text):
    t = str(text or "").strip().lower()
    t = re.sub(r"[\s，。；：、！？“”‘’（）《》〈〉—\-·.,;:!?'\"()\[\]{}<>]", "", t)
    table = str.maketrans(
        "０１２３４５６７８９ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ",
        "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")
    return t.translate(table)


def parse_json_block(text):
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def structure_item(base_url, key, model, item):
    form = item.get("form")
    rule = STRUCTURE_RULES.get(form)
    if not rule:
        return None, None
    want_variants = form in VARIANT_FORMS
    prompt = (
        f"题目（{form}）：{item['stem'].strip()}\n"
        f"标准答案：{item['answer']}\n"
        f"任务：{rule}\n"
        "只输出一个 JSON 对象（不要多余文字）："
        + ('{"acceptable_variants": ["...", "..."]}' if want_variants
           else '{"scoring_points": [{"point": "...", "score": 1}]}')
    )
    st = parse_json_block(_chat(base_url, key, model, [
        {"role": "system", "content": "你是语文教研结构化代理。只输出 JSON。"},
        {"role": "user", "content": prompt},
    ]))
    if not isinstance(st, dict):
        return None, None
    if want_variants:
        v = st.get("acceptable_variants")
        if isinstance(v, list) and v and all(isinstance(x, str) and x.strip() for x in v) \
                and normalize(item["answer"]) in {normalize(x) for x in v}:
            return list(dict.fromkeys(v)), None
        return None, None
    p = st.get("scoring_points")
    if isinstance(p, list) and p and all(
            isinstance(x, dict) and str(x.get("point", "")).strip()
            and isinstance(x.get("score"), (int, float)) and x["score"] > 0 for x in p):
        return None, [{"point": str(x["point"]), "score": x["score"]} for x in p]
    return None, None


def blind_answer(base_url, key, model, item):
    return extract_answer(_chat(base_url, key, model, [
        {"role": "system", "content": "你是独立作答代理。只依据题面作答，最终答案放最后一行 ANSWER: 之后，简洁作答。"},
        {"role": "user", "content": item["stem"].strip() + "\n最后一行必须是：ANSWER: <最终答案>"},
    ]))


def main() -> int:
    ap = argparse.ArgumentParser(description="语文开放题结构化批（两模型族+代码比对）")
    ap.add_argument("--grade", required=True, type=int)
    ap.add_argument("--forms", required=True, help="逗号分隔，如 fill,dictation")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--structure-model", required=True)
    ap.add_argument("--structure-agent", required=True)
    ap.add_argument("--blind-model", required=True)
    ap.add_argument("--blind-agent", required=True)
    ap.add_argument("--batch", required=True)
    ap.add_argument("--date", required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--data-dir", default=os.path.join(ROOT, "data"))
    ap.add_argument("--allow-network", action="store_true")
    args = ap.parse_args()
    if not args.allow_network:
        raise SystemExit("拒绝运行：须显式 --allow-network")
    key_a = os.environ.get("LLM_API_KEY") or ""
    base_a = os.environ.get("LLM_BASE_URL") or ""
    key_b = os.environ.get("BLIND_LLM_API_KEY") or key_a
    base_b = os.environ.get("BLIND_LLM_BASE_URL") or base_a
    if not key_a or not base_a:
        raise SystemExit("拒绝运行：环境未注入 LLM_API_KEY / LLM_BASE_URL")
    _check_endpoint(base_a)
    _check_endpoint(base_b)

    path = os.path.join(args.data_dir, "items", f"chinese_grade{args.grade}_items.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    forms = {x.strip() for x in args.forms.split(",") if x.strip()}
    scope = [
        it for it in data["items"]
        if not it.get("options")
        and it.get("form") in forms
        and len((it.get("verification") or {}).get("agents", [])) == 1
    ]
    if args.limit:
        scope = scope[: args.limit]
    if not scope:
        print("NOTHING-TO-DO（范围无单代理开放题）")
        return 0
    print(f"CHIOPEN {len(scope)} items grade={args.grade} forms={sorted(forms)}")

    by_id = {it["id"]: it for it in data["items"]}
    struct_ledger = []
    agree_rows, open_rows = [], []
    struct_ok = struct_fail = 0
    for it in scope:
        variants, points = structure_item(base_a, key_a, args.structure_model, it)
        ans = blind_answer(base_b, key_b, args.blind_model, it)
        if variants is None and points is None:
            struct_fail += 1
            open_rows.append({"id": it["id"], "form": it.get("form"),
                              "bank_answer": it["answer"], "solver_answer": ans,
                              "status": "open", "reason": "structure_invalid"})
            print(f"  {it['id']} STRUCT-FAIL")
            continue
        struct_ok += 1
        struct_ledger.append({"id": it["id"], "structure_agent": args.structure_agent,
                              "structure_model": args.structure_model,
                              "acceptable_variants": variants, "scoring_points": points})
        cand = [it["answer"]] + (variants or [])
        hit = ans is not None and normalize(ans) in {normalize(c) for c in cand}
        if not hit and points:
            joined = "；".join(x["point"] for x in points)
            hit = ans is not None and normalize(ans) in normalize(joined)
        row = {"id": it["id"], "form": it.get("form"),
               "bank_answer": it["answer"], "solver_answer": ans,
               "verdict": "agree" if hit else "disagree"}
        (agree_rows if hit else open_rows).append(
            row if hit else dict(row, status="open"))
        print(f"  {it['id']} {row['verdict']}")

    if args.apply:
        for rec in struct_ledger:
            target = by_id[rec["id"]]
            if rec["acceptable_variants"]:
                target["acceptable_variants"] = rec["acceptable_variants"]
            elif rec["scoring_points"]:
                target["scoring_points"] = rec["scoring_points"]
        for row in agree_rows:
            target = by_id[row["id"]]
            target["verification"] = {
                "agents": [target["verification"]["agents"][0], args.blind_agent],
                "answers_agree": True,
            }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"APPLIED 结构化 {len(struct_ledger)} 题 + 第二代理回填 {len(agree_rows)} 题 -> {path}")

    struct_path = os.path.join(args.data_dir, "verification", f"chiopen_struct_{args.batch}.json")
    with open(struct_path, "w", encoding="utf-8") as f:
        json.dump({"batch": args.batch, "date": args.date, "records": struct_ledger},
                  f, ensure_ascii=False, indent=2)
        f.write("\n")
    manifest = {
        "batch": args.batch, "date": args.date,
        "scope": {"grade": args.grade, "forms": sorted(forms), "limit": args.limit},
        "structure_agent": args.structure_agent, "structure_model": args.structure_model,
        "blind_agent": args.blind_agent, "blind_model": args.blind_model,
        "method": "keypoint-judge",
        "counts": {"agree": len(agree_rows), "disagree": len(open_rows),
                   "structure_ok": struct_ok, "structure_fail": struct_fail},
        "applied": bool(args.apply),
    }
    mpath = os.path.join(args.data_dir, "verification", f"verify_manifest_chiopen_{args.batch}.json")
    with open(mpath, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"STRUCT_LEDGER {struct_path}")
    print(f"MANIFEST {mpath}")
    if open_rows:
        qpath = os.path.join(args.data_dir, "verification", f"arbitration_queue_chiopen_{args.batch}.json")
        with open(qpath, "w", encoding="utf-8") as f:
            json.dump({"batch": args.batch, "queue": open_rows}, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"QUEUE {qpath} ({len(open_rows)} open，未回填)")
    print(f"AGREE {len(agree_rows)} OPEN {len(open_rows)} STRUCT_OK {struct_ok} STRUCT_FAIL {struct_fail}")
    print("CHIOPEN-BATCH-OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
