"""xuexing.tts_reader —— 语音读题确定性内核（盲重写实例）。

权威契约：specs/frozen/tts_reader.spec.md（定稿 v1，第三波冻结轮）。

行为要点（详见契约）：
- 把题干与选项渲染成确定性朗读文本（choice 题追加「选项L：正文」段；
  无题号、无作答提示语，绝不含 answer/solution）。
- 交给注入的 TTS 客户端（鸭子表面 ``tts(text, voice=…, response_format=…)
  -> bytes``）合成，并以 ``(item.id, voice)`` 为键缓存音频字节。
- ``read_paper`` 按卷面题序整卷合成，共享同一缓存。

模块间零 import：item / paper / bank / tts 均为注入的鸭子对象；本模块不
import 任何 xuexing 模块（含 types / mm_client / omr_sheet），跨模块一致性
由契约测试在测试侧锁定。

装载约束（契约冻结）：禁止相对导入；禁止字符串化注解的 __future__ 导入
（dataclass 字段注解必须是真实对象）；禁止第三方库、文件/网络 IO、随机、
系统时钟、环境读取、全局可变状态。
"""

import hashlib
import re
from collections.abc import MutableMapping
from dataclasses import dataclass

__all__ = [
    "AUDIO_FORMAT",
    "DEFAULT_VOICE",
    "ITEM_TYPES",
    "READER_VERSION",
    "ItemAudio",
    "TTSError",
    "build_reading_text",
    "option_labels",
    "read_paper",
    "synthesize_item",
]

READER_VERSION = "1"
DEFAULT_VOICE = "linjiajiejie"
AUDIO_FORMAT = "mp3"
ITEM_TYPES = ("choice", "fill", "solve")

# 句末标点集（契约 §3.3 规则 3/4 闭式）：段间拼接与收尾共用的字符集合，
# 后缀判断按「末字符是否属于该集合」的集合语义，而非单一后缀匹配。
_SENTENCE_ENDS = ("。", "！", "？", ".", "!", "?")

# 选项显式标签闭式正则（契约 §3.2 规则 3，与 omr_sheet/mm_ingest 同款）：
# 单个 ASCII 字母 + 分隔符 `.．、)）`，右侧为选项正文。
_OPTION_LABEL_RE = re.compile(r"([A-Za-z])[.．、)）][ \t]*(.*)\Z", re.DOTALL)

# 无显式标签时按位回退的标签字母表（契约 §3.2 规则 3）。
_LABEL_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


class TTSError(ValueError):
    """tts_reader 模块唯一异常类型（ValueError 直接子类）。"""


# ---------------------------------------------------------------- 内部工具


def _require_non_blank_str(value: object, what: str) -> None:
    """守卫：value 必须为非空白 str，否则抛 TTSError。"""
    if not isinstance(value, str) or not value.strip():
        raise TTSError(f"{what} 必须为非空白 str，得到 {value!r}")


def _split_option(raw: str) -> "tuple[str | None, str]":
    """拆单个选项原文 → ``(显式标签大写或 None, 正文)``。

    对 ``raw.strip()`` 匹配闭式正则：命中返回 ``(group(1).upper(),
    group(2).strip())``；未命中返回 ``(None, raw.strip())``。
    """
    text = raw.strip()
    match = _OPTION_LABEL_RE.match(text)
    if match is None:
        return None, text
    return match.group(1).upper(), match.group(2).strip()


def _cache_surface_ok(cache: object) -> bool:
    """守卫判据：cache 必须为 None 或 MutableMapping。"""
    return cache is None or isinstance(cache, MutableMapping)


def _tts_surface(tts: object):
    """守卫判据（V2）：tts 必须提供可调用的 ``tts`` 成员，返回该成员。"""
    tts_fn = getattr(tts, "tts", None)
    if not callable(tts_fn):
        raise TTSError("tts 必须提供可调用的 tts 成员")
    return tts_fn


def _ensure_non_empty_bytes(audio: object, what: str) -> None:
    """守卫判据：音频必须为非空 bytes（``isinstance(audio, bytes) and
    len(audio) > 0``），否则 TTSError。bytearray 不视为 bytes。"""
    if not isinstance(audio, bytes) or len(audio) == 0:
        raise TTSError(f"{what}必须为非空 bytes，得到 {type(audio).__name__}")


# ---------------------------------------------------------------- 公开 API


def option_labels(item: object) -> list[str]:
    """choice 题选项标签列（契约 §3.2）。

    守卫次序为绑定条款：
    1. ``item.options`` 必须为 list/tuple 且 ``2 <= len <= 26``；
    2. 逐项必须为非空白 str；
    3. 对 ``raw.strip()`` 匹配显式标签闭式正则，命中取 group(1).upper()，
       未命中按位回退 ``"ABCDEFGHIJKLMNOPQRSTUVWXYZ"[pos]``；
    4. 归一后标签不得重复。

    只读 ``item.options``（``item.id`` 仅用于错误消息）。
    """
    options = getattr(item, "options", None)
    if not isinstance(options, (list, tuple)):
        raise TTSError(
            f"item.options 必须为 list/tuple，得到 {type(options).__name__}"
        )
    if not 2 <= len(options) <= 26:
        raise TTSError(f"item.options 长度必须在 2..26，得到 {len(options)}")
    labels: list[str] = []
    for pos, raw in enumerate(options):
        if not isinstance(raw, str) or not raw.strip():
            raise TTSError(f"选项第 {pos} 项必须为非空白 str，得到 {raw!r}")
        explicit_label, _body = _split_option(raw)
        if explicit_label is None:
            labels.append(_LABEL_ALPHABET[pos])
        else:
            labels.append(explicit_label)
    if len(set(labels)) != len(labels):
        raise TTSError(f"归一后选项标签重复：{labels}")
    return labels


def build_reading_text(item: object) -> str:
    """一道题 → 确定性朗读文本（契约 §3.3）。

    拼接规则（顺序为绑定条款）：segments 以 ``stem.strip()`` 起；choice 逐项
    追加 ``f"选项{label}：{body}"``（label 来自 option_labels，body 为显式
    标签匹配后的剩余文本 strip，无显式标签为原文 strip，正文空白即
    TTSError）；段间在累积输出未以句末标点集 ``。！？.!?`` 结尾时插「。」；
    收尾同理补「。」。

    注：choice 题 ``options`` 属性整体缺失时，本实现按契约 §7.1 的替代自由
    度经 ``getattr`` 安全访问统一抛 TTSError（参考实现则泄漏 AttributeError，
    两种均合格）。
    """
    _require_non_blank_str(getattr(item, "id", None), "item.id")
    stem = getattr(item, "stem", None)
    _require_non_blank_str(stem, "item.stem")
    item_type = getattr(item, "item_type", None)
    if item_type not in ITEM_TYPES:
        raise TTSError(f"item.item_type 必须属于 {ITEM_TYPES}，得到 {item_type!r}")
    segments: list[str] = [stem.strip()]
    if item_type == "choice":
        labels = option_labels(item)
        for label, raw in zip(labels, item.options):
            _label, body = _split_option(raw)
            if not body:
                raise TTSError(f"选项 {label} 正文为空白")
            segments.append(f"选项{label}：{body}")
    out = segments[0]
    for segment in segments[1:]:
        if out and out[-1] not in _SENTENCE_ENDS:
            out += "。"
        out += segment
    if not out or out[-1] not in _SENTENCE_ENDS:
        out += "。"
    return out


@dataclass
class ItemAudio:
    """单题音频记录（契约 §3.4）；五字段、逐字段相等、按位置可构造。"""

    item_id: str
    voice: str
    text: str
    audio: bytes
    from_cache: bool

    def to_dict(self) -> dict:
        """七键 dict，键序冻结；format 恒为 AUDIO_FORMAT；字节不序列化。"""
        return {
            "item_id": self.item_id,
            "voice": self.voice,
            "format": AUDIO_FORMAT,
            "text": self.text,
            "audio_size": len(self.audio),
            "audio_sha256": hashlib.sha256(self.audio).hexdigest(),
            "from_cache": self.from_cache,
        }


def synthesize_item(
    item: object,
    tts: object,
    *,
    voice: str = DEFAULT_VOICE,
    cache: "MutableMapping | None" = None,
) -> ItemAudio:
    """单题合成（契约 §3.5）。

    守卫次序 V1→V2→V3→V4 严格绑定，任一失败抛 TTSError 且 cache 不被触碰：
    V1 voice 非空白 str（原样使用，不 strip）；V2 tts 提供可调用 ``tts``
    成员；V3 cache 为 None 或 MutableMapping；V4 ``build_reading_text(item)``
    （缓存命中也照常执行，text 恒重建）。

    缓存键 ``(item.id, voice)``：命中零次合成（缓存值须为非空 bytes 否则
    TTSError）；未命中恰好一次 ``tts(text=text, voice=voice,
    response_format=AUDIO_FORMAT)``（全部关键字实参），返回非空 bytes 否则
    TTSError 且不回填；通过则回填后返回 ``from_cache=False``。tts 自身异常
    原样传播。``cache=None`` 时内部新建空 dict，无跨调用持久化。
    """
    _require_non_blank_str(voice, "voice")  # V1
    tts_fn = _tts_surface(tts)  # V2
    if not _cache_surface_ok(cache):  # V3
        raise TTSError("cache 必须为 None 或 MutableMapping")
    text = build_reading_text(item)  # V4（命中也照常执行）
    store: MutableMapping = {} if cache is None else cache
    key = (item.id, voice)
    if key in store:
        audio = store[key]
        _ensure_non_empty_bytes(audio, f"缓存命中值（键 {key!r}）")
        return ItemAudio(
            item_id=item.id, voice=voice, text=text, audio=audio, from_cache=True
        )
    audio = tts_fn(text=text, voice=voice, response_format=AUDIO_FORMAT)
    _ensure_non_empty_bytes(audio, "tts 返回值（不回填缓存）")
    store[key] = audio
    return ItemAudio(
        item_id=item.id, voice=voice, text=text, audio=audio, from_cache=False
    )


def _bank_index(bank: object) -> dict:
    """守卫 V5：bank.items 必须可调用且返回可迭代；逐题 id 非空白 str；
    bank 内 id 不得重复（对全部题目生效，含未被卷面引用者）。返回
    ``{id: item}`` 索引。"""
    items_getter = getattr(bank, "items", None)
    if not callable(items_getter):
        raise TTSError("bank 必须提供可调用的 items() 成员")
    try:
        iterable = iter(items_getter())
    except TypeError:
        raise TTSError("bank.items() 必须返回可迭代对象") from None
    index: dict = {}
    for it in iterable:
        iid = getattr(it, "id", None)
        _require_non_blank_str(iid, "bank 题目 id")
        if iid in index:
            raise TTSError(f"bank 内题目 id 重复：{iid!r}")
        index[iid] = it
    return index


def _paper_order(paper: object) -> list:
    """守卫 V6 前半：sections 规整化 + 卷面题序展开。

    sections 必须为 list/tuple；每元素必须为 dict 且其 ``item_ids`` 必须为
    list/tuple；每个 id 必须为非空白 str（额外键一律忽略）。sections 长度为
    0 时回退 ``paper.item_ids``（必须为 list/tuple）作为单一隐式节。
    """
    sections = getattr(paper, "sections", None)
    if not isinstance(sections, (list, tuple)):
        raise TTSError("paper.sections 必须为 list/tuple")
    ordered: list = []
    if len(sections) == 0:
        fallback = getattr(paper, "item_ids", None)
        if not isinstance(fallback, (list, tuple)):
            raise TTSError("sections 为空时 paper.item_ids 必须为 list/tuple")
        for iid in fallback:
            _require_non_blank_str(iid, "paper.item_ids 元素")
            ordered.append(iid)
        return ordered
    for position, section in enumerate(sections):
        if not isinstance(section, dict):
            raise TTSError(f"sections[{position}] 必须为 dict")
        item_ids = section.get("item_ids")
        if not isinstance(item_ids, (list, tuple)):
            raise TTSError(f"sections[{position}].item_ids 必须为 list/tuple")
        for iid in item_ids:
            _require_non_blank_str(iid, f"sections[{position}] 题目 id")
            ordered.append(iid)
    return ordered


def read_paper(
    paper: object,
    bank: object,
    tts: object,
    *,
    voice: str = DEFAULT_VOICE,
    cache: "MutableMapping | None" = None,
) -> "list[ItemAudio]":
    """整卷读题（契约 §3.6）：按卷面题序逐题合成，返回按卷面题序的
    ItemAudio 列表。

    守卫次序 V1→V7 严格绑定，任一失败零 tts 调用：V1 voice；V2 tts 表面；
    V3 cache 表面；V4 paper 表面（paper_id/title 为 str，空串合法）；
    V5 bank 表面（items 可调用、返回可迭代、id 非空白 str 且不重复）；
    V6 sections 规整化 + 逐题 item_type（只校验卷面引用到的题）+ 空卷门；
    V7 全量朗读文本预校验（先校验全卷再合成）。

    传入的 cache 在本次调用内共享；cache=None 时内部新建。卷内同一题出现
    多次时，第二次起命中共享缓存（零新增合成）。
    """
    _require_non_blank_str(voice, "voice")  # V1
    _tts_surface(tts)  # V2
    if not _cache_surface_ok(cache):  # V3
        raise TTSError("cache 必须为 None 或 MutableMapping")
    if not isinstance(getattr(paper, "paper_id", None), str) or not isinstance(
        getattr(paper, "title", None), str
    ):  # V4（空串合法，仅 isinstance 单判）
        raise TTSError("paper.paper_id 与 paper.title 必须为 str")
    index = _bank_index(bank)  # V5
    ordered_ids = _paper_order(paper)  # V6 前半
    items: list = []
    for iid in ordered_ids:  # V6 后半：引用存在性 + item_type（只查引用题）
        if iid not in index:
            raise TTSError(f"卷面引用的题目 id 不在 bank 中：{iid!r}")
        ref = index[iid]
        if getattr(ref, "item_type", None) not in ITEM_TYPES:
            raise TTSError(f"卷面题目 {iid!r} 的 item_type 必须属于 {ITEM_TYPES}")
        items.append(ref)
    if not items:  # 空卷门
        raise TTSError("空卷：卷面展开后题目数为 0")
    for ref in items:  # V7：先校验全卷，再合成（首题失败前零出网）
        build_reading_text(ref)
    store: MutableMapping = {} if cache is None else cache
    audios: list = []
    for ref in items:
        audios.append(synthesize_item(ref, tts, voice=voice, cache=store))
    return audios
