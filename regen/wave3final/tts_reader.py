"""tts_reader —— 语音读题的确定性内核（第三波契约 specs/frozen/tts_reader.spec.md）。

实现约束（与规格 §2 一致）：
- 依赖面仅标准库 ``hashlib`` / ``re`` / ``collections.abc.MutableMapping`` /
  ``dataclasses.dataclass``；**不 import 任何 xuexing 模块**（item / paper / bank / tts
  一律按成员访问的鸭子对象注入）。
- 禁止相对导入；禁止 ``from __future__ import annotations``——后者会把 dataclass 字段
  注解字符串化，重生成注入装载（顶层模块名注册）时 ``dataclasses`` 的 KW_ONLY 探测按
  ``sys.modules.get(cls.__module__)`` 取模块 dict 会崩溃；因此注解直接写真实对象。
- 零 IO / 零网络 / 零随机 / 零时钟 / 零环境读取 / 无全局可变状态：音频字节的唯一来源是
  注入 tts 的返回值，模块不做任何字节变换。
"""

import hashlib
import re
from collections.abc import MutableMapping
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# §3.1 冻结常量与异常
# ---------------------------------------------------------------------------

#: 模块版本（冻结常量）。
READER_VERSION = "1"

#: 默认音色，与 ``mm_client.TTS_VOICE`` 相等；**原样使用，不 strip**。
DEFAULT_VOICE = "linjiajiejie"

#: 合成请求的 ``response_format``，与 ``mm_client.TTS_FORMAT`` 相等。
AUDIO_FORMAT = "mp3"

#: 合法题型（与 ``types.Item.item_type`` 值域一致）。
ITEM_TYPES = ("choice", "fill", "solve")

#: 句末标点集：字符集合语义的后缀判断（``str.endswith`` 接受元组）。
#: ``：``/``,``/``…`` 等一律视为非句末。
_SENTENCE_ENDINGS = ("。", "！", "？", ".", "!", "?")

#: 无显式标签时按位回退的标签表（选项上界 26 与此长度一致）。
_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

#: 选项数量闭式区间。
_MIN_OPTIONS = 2
_MAX_OPTIONS = 26

#: 选项显式标签闭式：单 ASCII 字母 + 分隔符（``.`` ``．`` ``、`` ``)`` ``）``）+
#: 可选空格/制表符 + 其余正文（贪婪到行尾，re.S 允许换行）。
_OPTION_LABEL_RE = re.compile(r"([A-Za-z])[.．、)）][ \t]*(.*)\Z", re.S)


class TTSError(ValueError):
    """本模块唯一异常类型（``ValueError`` 直接子类）。

    唯一例外：choice 题 ``options`` 属性整体缺失时按规格 §7.1 走
    ``getattr(item, "options", None)`` 安全访问，统一抛 ``TTSError``（与
    ``option_labels`` 同一入口对齐），不泄漏 ``AttributeError``。
    """


# ---------------------------------------------------------------------------
# 内部守卫与表面工具（复用，保证两个入口的守卫判定完全一致）
# ---------------------------------------------------------------------------


def _require_text(value, name: str) -> str:
    """要求 ``value`` 为非空白 ``str``，否则 TTSError。"""
    if not isinstance(value, str) or not value.strip():
        raise TTSError(f"{name} 必须为非空白 str")
    return value


def _require_voice(voice) -> str:
    """V1：voice 必须为非空白 str；判定用 ``.strip()``，**使用原样**。"""
    if not isinstance(voice, str) or not voice.strip():
        raise TTSError("voice 必须为非空白 str")
    return voice


def _require_tts(tts):
    """V2：tts 必须提供可调用的 ``tts`` 成员（鸭子表面）。"""
    member = getattr(tts, "tts", None)
    if not callable(member):
        raise TTSError("tts 必须提供可调用的 tts 成员")
    return member


def _require_cache(cache):
    """V3：cache 必须为 None 或 ``MutableMapping``；None 时内部新建空 dict。"""
    if cache is None:
        return {}
    if not isinstance(cache, MutableMapping):
        raise TTSError("cache 必须为 None 或 MutableMapping")
    return cache


def _require_audio(audio) -> bytes:
    """音频判据：``isinstance(audio, bytes) and len(audio) > 0``。"""
    if not isinstance(audio, bytes) or not audio:
        raise TTSError("音频必须为非空 bytes")
    return audio


def _option_pairs(raw_options) -> list:
    """校验选项表面并切分为 ``(label, body)`` 列表。

    绑定条款（规格 §3.2 顺序）：list/tuple → 2..26 项 → 逐项非空白 str →
    显式标签（``raw.strip()`` 上匹配，小写归一大写）/按位回退 → 标签不重复。
    """
    if not isinstance(raw_options, (list, tuple)):
        raise TTSError(f"item.options 必须是 list/tuple（实为 {type(raw_options).__name__}）")
    count = len(raw_options)
    if not _MIN_OPTIONS <= count <= _MAX_OPTIONS:
        raise TTSError(f"item.options 项数须在 {_MIN_OPTIONS}..{_MAX_OPTIONS}，实为 {count}")
    pairs = []
    for pos, raw in enumerate(raw_options):
        if not isinstance(raw, str) or not raw.strip():
            raise TTSError(f"item.options[{pos}] 必须为非空白 str")
        text = raw.strip()
        matched = _OPTION_LABEL_RE.match(text)
        if matched is None:
            pairs.append((_ALPHABET[pos], text))
        else:
            pairs.append((matched.group(1).upper(), matched.group(2).strip()))
    labels = [label for label, _ in pairs]
    if len(set(labels)) != len(labels):
        raise TTSError(f"选项标签重复：{labels}")
    return pairs


def _require_paper_surface(paper) -> None:
    """V4：``paper.paper_id`` / ``paper.title`` 必须为 str（空串合法，仅 isinstance 单判）。"""
    for name in ("paper_id", "title"):
        if not isinstance(getattr(paper, name, None), str):
            raise TTSError(f"paper.{name} 必须为 str")


def _bank_index(bank) -> dict:
    """V5：bank 表面 + 全量 id 校验（重复检测对未被卷面引用的题同样生效）。"""
    items_attr = getattr(bank, "items", None)
    if not callable(items_attr):
        raise TTSError("bank.items 必须可调用")
    try:
        catalogue = list(items_attr())
    except TypeError as exc:  # 返回 42 等不可迭代对象
        raise TTSError("bank.items() 必须返回可迭代对象") from exc
    index = {}
    for pos, item in enumerate(catalogue):
        item_id = _require_text(getattr(item, "id", None), f"bank.items()[{pos}].id")
        if item_id in index:
            raise TTSError(f"bank 内 id 重复：{item_id}")
        index[item_id] = item
    return index


def _volume_order(paper, index: dict) -> list:
    """V6：sections 规整化 + 卷面题序展开 + 逐题 item_type + 空卷门。

    卷面题序 = 节序 × 节内 ``item_ids`` 序；``sections`` 长度为 0 时回退
    ``paper.item_ids`` 作为单一隐式节。
    """
    sections = getattr(paper, "sections", None)
    if not isinstance(sections, (list, tuple)):
        raise TTSError(f"paper.sections 必须是 list/tuple（实为 {type(sections).__name__}）")
    if len(sections) == 0:
        fallback = getattr(paper, "item_ids", None)
        if not isinstance(fallback, (list, tuple)):
            raise TTSError("paper.sections 为空时 paper.item_ids 必须是 list/tuple")
        groups = [fallback]
    else:
        groups = []
        for pos, section in enumerate(sections):
            if not isinstance(section, dict):
                raise TTSError(f"paper.sections[{pos}] 必须是 dict")
            ids = section.get("item_ids")
            if not isinstance(ids, (list, tuple)):
                raise TTSError(f"paper.sections[{pos}].item_ids 必须是 list/tuple")
            groups.append(ids)
    ordered = []
    for ids in groups:
        for pos, item_id in enumerate(ids):
            _require_text(item_id, f"paper 卷面 id[{pos}]")
            if item_id not in index:
                raise TTSError(f"卷面引用的 id 不在 bank 中：{item_id}")
            item = index[item_id]
            item_type = getattr(item, "item_type", None)
            if not isinstance(item_type, str) or item_type not in ITEM_TYPES:
                raise TTSError(f"item[{item_id}].item_type 非法：{item_type!r}")
            ordered.append((item_id, item))
    if not ordered:
        raise TTSError("空卷门：展开后题目数为 0")
    return ordered


# ---------------------------------------------------------------------------
# §3.2 / §3.3 朗读文本闭式
# ---------------------------------------------------------------------------


def option_labels(item) -> list:
    """choice 题选项标签列（鸭子 item 只用 ``item.options``）。"""
    return [label for label, _ in _option_pairs(getattr(item, "options", None))]


def build_reading_text(item) -> str:
    """一道题 → 确定性朗读文本。

    只由题干与选项正文构造：绝不含 ``item.solution`` / ``item.answer``，无题号、
    无作答提示语。
    """
    _require_text(getattr(item, "id", None), "item.id")
    stem = _require_text(getattr(item, "stem", None), "item.stem")
    item_type = getattr(item, "item_type", None)
    if not isinstance(item_type, str) or item_type not in ITEM_TYPES:
        raise TTSError(f"item.item_type 非法：{item_type!r}")

    segments = [stem.strip()]
    if item_type == "choice":
        for pos, (label, body) in enumerate(_option_pairs(getattr(item, "options", None))):
            if not body:
                raise TTSError(f"item.options[{pos}] 正文（标签之后）为空")
            segments.append(f"选项{label}：{body}")

    text = ""
    for segment in segments:
        if text and not text.endswith(_SENTENCE_ENDINGS):
            text += "。"
        text += segment
    if not text.endswith(_SENTENCE_ENDINGS):
        text += "。"
    return text


# ---------------------------------------------------------------------------
# §3.4 ItemAudio
# ---------------------------------------------------------------------------


@dataclass
class ItemAudio:
    """一道题的合成产物（按位置可构造，逐字段相等）。"""

    item_id: str
    voice: str
    text: str
    audio: bytes
    from_cache: bool

    def to_dict(self) -> dict:
        """七键固定键序；``format`` 恒为 ``AUDIO_FORMAT``；**音频字节不序列化**。"""
        return {
            "item_id": self.item_id,
            "voice": self.voice,
            "format": AUDIO_FORMAT,
            "text": self.text,
            "audio_size": len(self.audio),
            "audio_sha256": hashlib.sha256(self.audio).hexdigest(),
            "from_cache": self.from_cache,
        }


# ---------------------------------------------------------------------------
# §3.5 / §3.6 合成与整卷读题
# ---------------------------------------------------------------------------


def synthesize_item(item, tts, *, voice=DEFAULT_VOICE, cache=None) -> ItemAudio:
    """单题合成。守卫次序 V1→V2→V3→V4，任一失败即抛 TTSError、cache 不被触碰。"""
    voice = _require_voice(voice)
    tts_call = _require_tts(tts)
    store = _require_cache(cache)
    # V4：build_reading_text 照常执行——缓存命中也恒重建 text。
    text = build_reading_text(item)

    item_id = getattr(item, "id", None)
    key = (item_id, voice)
    if key in store:
        audio = _require_audio(store[key])
        return ItemAudio(item_id, voice, text, audio, True)

    # 客户端自身异常原样传播（不包装、不重试）。
    audio = _require_audio(tts_call(text, voice=voice, response_format=AUDIO_FORMAT))
    store[key] = audio
    return ItemAudio(item_id, voice, text, audio, False)


def read_paper(paper, bank, tts, *, voice=DEFAULT_VOICE, cache=None) -> list:
    """整卷读题：按卷面题序逐题合成（共享同一 cache），返回按卷面题序的 ItemAudio 列表。

    守卫次序 V1→V2→V3→V4→V5→V6→V7，任一失败**零 tts 调用**、cache 不被污染。
    """
    _require_voice(voice)
    _require_tts(tts)
    store = _require_cache(cache)
    _require_paper_surface(paper)
    index = _bank_index(bank)
    ordered = _volume_order(paper, index)

    # V7：全量朗读文本预校验——先校验全卷再合成，首题失败前零出网。
    for _, item in ordered:
        build_reading_text(item)

    return [
        synthesize_item(item, tts, voice=voice, cache=store) for _, item in ordered
    ]
