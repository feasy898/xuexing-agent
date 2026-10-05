"""mm_ingest — 拍照录入管线确定性内核（重生成实例，冻结契约 v1，第三波）。

唯一权威契约：specs/frozen/mm_ingest.spec.md（冻结 v1）。管线：一张学生作答
照片 → 注入 client 的 VLM 结构化转写（题号→学生答案 JSON，schema 冻结）→
确定性校验（题号∈卷面、答案形态、置信度门）→ 注入 grader 产出 Response；
不可信条目（未知题号/重复题号/低置信/形态不符/卷面缺号）不猜测、不静默判分，
进人机协同复核队列。

装载约束（契约 §2 探针 LP1–LP3）：禁止相对导入；禁止 from __future__ import
annotations（dataclass 注解必须写真实对象）；绝对导入 xuexing.types 的
Response 与 to_dict，且只允许使用这两个名字。

模块间零 import：client 与 grader 都是注入的鸭子类型参数。全模块纯函数：
无 IO、无随机、无时钟、不读环境、无全局可变状态，同输入同输出。
"""

import json
import math
import re
from dataclasses import dataclass
from typing import Optional

from xuexing.types import Response, to_dict  # noqa: F401  契约 §2 要求导入

__all__ = [
    "IMAGE_FORMATS",
    "INGEST_VERSION",
    "MIN_CONFIDENCE",
    "REASON_ANSWER_FORM",
    "REASON_DUPLICATE_NUMBER",
    "REASON_LOW_CONFIDENCE",
    "REASON_MISSING_NUMBER",
    "REASON_UNKNOWN_NUMBER",
    "REVIEW_REASONS",
    "IngestError",
    "IngestResult",
    "ReviewItem",
    "build_transcribe_prompt",
    "ingest_photo",
    "option_labels",
    "parse_transcript",
]

# ---------- 冻结常量（契约 §3.1） ----------

INGEST_VERSION = "1"

#: ingest_photo 的缺省置信度门；confidence < 门限 进复核。
MIN_CONFIDENCE = 0.9

#: 合法图片格式元组（确切顺序冻结；大小写敏感）。
IMAGE_FORMATS = ("png", "jpg", "jpeg", "webp", "gif")

REASON_UNKNOWN_NUMBER = "unknown_number"
REASON_DUPLICATE_NUMBER = "duplicate_number"
REASON_MISSING_NUMBER = "missing_number"
REASON_LOW_CONFIDENCE = "low_confidence"
REASON_ANSWER_FORM = "answer_form"

#: 五个 REASON_* 常量的值按此顺序组成的元组。
REVIEW_REASONS = (
    REASON_UNKNOWN_NUMBER,
    REASON_DUPLICATE_NUMBER,
    REASON_MISSING_NUMBER,
    REASON_LOW_CONFIDENCE,
    REASON_ANSWER_FORM,
)

# ---------- 内部常量 ----------

_ITEM_TYPES = ("choice", "fill", "solve")
_MAX_BUBBLES = 26
_FALLBACK_LABELS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
#: 选项标签闭式（与 omr_sheet.parse_option 同闭式，跨模块锁定）。
_OPT_RE = re.compile(r"([A-Za-z])[.．、)）][ \t]*(.*)\Z", re.S)
_MISSING = object()

# VLM 转写提示词冻结文本（契约 §3.5；n 与 choice 标签行是仅有变量位）。
_PROMPT_HEADER = (
    "你是阅卷录入助手。下面是一张学生作答照片对应的卷面题目清单，请逐题转写学生答案。",
    "只输出一个 JSON 对象，不要输出任何其他文字。",
    "输出 JSON schema（冻结）：{\"answers\": [{\"number\": 题号整数, \"answer\": "
    "学生答案字符串或 null, \"confidence\": 0 到 1 的数字}]}",
    "规则：",
    "2. choice 题：answer 只输出被选选项的标签字母（A-Z 之一）；未作答输出 null。",
    "3. fill/solve 题：answer 按照片原样转写学生书写内容；未作答输出 null。",
    "4. confidence 是你对该条转写的置信度，取 0 到 1。",
    "卷面题目清单：",
)


class IngestError(ValueError):
    """本模块唯一异常类型（ValueError 直接子类），覆盖本模块一切校验失败。

    唯一例外：client/grader 自身抛出的异常按原类型传播，不包装、不吞掉。
    """


# ---------- 数据形状（契约 §3.2 / §3.3） ----------


@dataclass
class ReviewItem:
    """一条人机协同复核条目。reason 恰一个，词表见 REVIEW_REASONS。"""

    number: int  # 转写题号；missing_number 时为卷面缺号
    item_id: Optional[str]  # 卷内号给 item_id；unknown_number 恒 None
    answer: Optional[str]  # 转写原文；missing_number 恒 None
    confidence: Optional[float]  # 转写置信度；missing_number 恒 None
    reason: str
    detail: str

    def to_dict(self) -> dict:
        return {
            "number": self.number,
            "item_id": self.item_id,
            "answer": self.answer,
            "confidence": self.confidence,
            "reason": self.reason,
            "detail": self.detail,
        }


@dataclass
class IngestResult:
    """拍照录入产出：responses 按卷面题号升序；review = 条目级（转写序）+ 缺号（升序）。"""

    responses: list  # list[Response]，按卷面题号升序
    review: list  # list[ReviewItem]

    def to_dict(self) -> dict:
        return {
            "responses": [to_dict(r) for r in self.responses],
            "review": [item.to_dict() for item in self.review],
        }


# ---------- 内部 helpers ----------


def _is_int(value) -> bool:
    """int 且非 bool（bool 是 int 子类，必须显式排除）。"""
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value) -> bool:
    """int/float 且非 bool。"""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_unit_interval(value) -> bool:
    """有限数字且落在 [0.0, 1.0]；先做值域比较（大整数比较不溢出），再判有限性。"""
    if not _is_number(value):
        return False
    if not (0.0 <= value <= 1.0):
        return False
    return math.isfinite(value)


def _option_norm_texts(item) -> list:
    """choice 选项原文的去空白大写形态（标答=选项全文时的比对列）。"""
    return [opt.strip().upper() for opt in item.options]


def option_labels(item) -> list:
    """choice 题的选项标签列（与 omr_sheet.parse_option 同闭式，跨模块锁定）。

    逐选项 strip() 后匹配 _OPT_RE：命中 → 捕获字母归一大写；未命中 → 按位回退
    A..Z。守卫（任一违反 → IngestError）：options 非 list/tuple、属性缺失、
    长度 <2 或 >26、含非 str 或空白串、解析出的标签有重复。
    """
    options = getattr(item, "options", _MISSING)
    if options is _MISSING or not isinstance(options, (list, tuple)):
        raise IngestError("choice item must expose options as a list or tuple")
    if len(options) < 2:
        raise IngestError("choice item must have at least 2 options")
    if len(options) > _MAX_BUBBLES:
        raise IngestError(f"choice item must have at most {_MAX_BUBBLES} options")
    labels = []
    for index, opt in enumerate(options):
        if not isinstance(opt, str) or not opt.strip():
            raise IngestError("every option must be a non-blank string")
        stripped = opt.strip()
        match = _OPT_RE.match(stripped)
        if match is not None:
            label = match.group(1).upper()
        else:
            label = _FALLBACK_LABELS[index]
        labels.append(label)
    if len(set(labels)) != len(labels):
        raise IngestError("option labels must be unique")
    return labels


def _bank_index(bank) -> dict:
    """bank.items() → {item.id: item}（拷贝，不修改入参）。

    守卫：bank 无可调用 items()、items() 调用或迭代抛 TypeError、item id 非非
    空白 str、bank 内 id 重复 → IngestError。
    """
    items_attr = getattr(bank, "items", _MISSING)
    if items_attr is _MISSING or not callable(items_attr):
        raise IngestError("bank must expose a callable items()")
    try:
        raw = items_attr()
    except TypeError as exc:
        raise IngestError(f"bank.items() raised TypeError: {exc}") from exc
    try:
        collected = list(raw)
    except TypeError as exc:
        raise IngestError(f"bank.items() result is not iterable: {exc}") from exc
    index = {}
    for item in collected:
        item_id = getattr(item, "id", None)
        if not isinstance(item_id, str) or not item_id.strip():
            raise IngestError("every bank item must have a non-blank string id")
        if item_id in index:
            raise IngestError(f"duplicate bank item id: {item_id!r}")
        index[item_id] = item
    return index


def _section_lists(paper) -> list:
    """paper.sections 顺序展开为逐节的题 id 列表（拷贝，不修改入参）。

    空 sections → 回退单一隐式节 [{"item_ids": paper.item_ids}]（此时
    paper.item_ids 必须为 list/tuple）。守卫：sections 非 list/tuple、节非
    dict、节内 item_ids 非 list/tuple → IngestError。
    """
    sections = getattr(paper, "sections", _MISSING)
    if sections is _MISSING or not isinstance(sections, (list, tuple)):
        raise IngestError("paper.sections must be a list or tuple")
    if len(sections) == 0:
        item_ids = getattr(paper, "item_ids", _MISSING)
        if item_ids is _MISSING or not isinstance(item_ids, (list, tuple)):
            raise IngestError("paper.item_ids must be a list or tuple when sections is empty")
        return [list(item_ids)]
    lists = []
    for section in sections:
        if not isinstance(section, dict):
            raise IngestError("every paper section must be a dict")
        item_ids = section.get("item_ids")
        if not isinstance(item_ids, (list, tuple)):
            raise IngestError("every paper section must carry item_ids as a list or tuple")
        lists.append(list(item_ids))
    return lists


def _paper_questions(paper, bank) -> list:
    """卷面表面校验（契约 §3.7 V6–V8，顺序为绑定条款）→ [(number, item, labels, item_type)]。

    题号 1..N 由 sections 顺序展开决定（空 sections 回退 paper.item_ids），
    与 omr_sheet/paper_layout 同一编号语义。空卷门：展开后零题 → IngestError。
    """
    paper_id = getattr(paper, "paper_id", _MISSING)
    if not isinstance(paper_id, str):
        raise IngestError("paper.paper_id must be a str")
    title = getattr(paper, "title", _MISSING)
    if not isinstance(title, str):
        raise IngestError("paper.title must be a str")
    bank_index = _bank_index(bank)
    section_lists = _section_lists(paper)
    questions = []
    number = 0
    for item_ids in section_lists:
        for question_id in item_ids:
            if not isinstance(question_id, str) or not question_id.strip():
                raise IngestError("every paper question id must be a non-blank string")
            if question_id not in bank_index:
                raise IngestError(f"paper question id not in bank: {question_id!r}")
            item = bank_index[question_id]
            item_type = getattr(item, "item_type", None)
            if item_type not in _ITEM_TYPES:
                raise IngestError(f"item_type must be one of {_ITEM_TYPES}, got {item_type!r}")
            labels = None
            if item_type == "choice":
                labels = option_labels(item)
                answer = getattr(item, "answer", _MISSING)
                if not isinstance(answer, str):
                    raise IngestError("choice item answer must be a str")
                normalized = answer.strip().upper()
                if normalized not in labels and normalized not in _option_norm_texts(item):
                    raise IngestError(
                        "choice item answer must be a bubble label or an option full text"
                    )
            number += 1
            questions.append((number, item, labels, item_type))
    if not questions:
        raise IngestError("paper must contain at least one question")
    return questions


# ---------- 公开 API（契约 §3） ----------


def build_transcribe_prompt(paper, bank) -> str:
    """卷面 → 确定性 VLM 转写提示词（只含题号/题型/choice 标签，学生面卫生）。

    内部先经卷面表面校验（同 ingest_photo 的 V6–V8 与空卷门，失败抛
    IngestError），再渲染冻结文本；随后每题一行，choice 题追加 " 选项 " +
    "/".join(labels)；各行以 "\n" 连接，无尾随换行。同输入逐字节相等。
    """
    questions = _paper_questions(paper, bank)
    n = len(questions)
    lines = [
        _PROMPT_HEADER[0],
        _PROMPT_HEADER[1],
        _PROMPT_HEADER[2],
        _PROMPT_HEADER[3],
        f"1. 卷面共 {n} 道题，题号 1..{n}，每个题号在 answers 中恰好出现一次。",
        _PROMPT_HEADER[4],
        _PROMPT_HEADER[5],
        _PROMPT_HEADER[6],
        _PROMPT_HEADER[7],
    ]
    for number, item, labels, item_type in questions:
        if item_type == "choice":
            lines.append(f"{number}. choice 选项 " + "/".join(labels))
        else:
            lines.append(f"{number}. {item_type}")
    return "\n".join(lines)


def parse_transcript(text) -> list:
    """VLM 回复文本 → [{"number": int, "answer": str|None, "confidence": float}…]。

    切片闭式：strip() 后首个 "{" 到最后一个 "}" 做 JSON 解析（前后闲话、
    ```json 围栏容忍）；schema 冻结：顶层 dict 且含 answers list，entry 为 dict
    且三键必填（未知键忽略），number 为 int≥1（拒 bool），answer 为 str|None，
    confidence 为 [0,1] 有限数字（拒 bool）并规整为 float。任一违反 →
    IngestError。
    """
    if not isinstance(text, str):
        raise IngestError("transcript must be a str")
    stripped = text.strip()
    if not stripped:
        raise IngestError("transcript must not be empty")
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start < 0 or end <= start:
        raise IngestError("transcript must contain a JSON object")
    try:
        data = json.loads(stripped[start : end + 1])
    except ValueError as exc:
        raise IngestError(f"transcript JSON parse failed: {exc}") from exc
    if not isinstance(data, dict):
        raise IngestError("transcript JSON must be an object")
    if "answers" not in data:
        raise IngestError("transcript JSON must carry an answers list")
    answers = data["answers"]
    if not isinstance(answers, list):
        raise IngestError("transcript answers must be a list")
    entries = []
    for entry in answers:
        if not isinstance(entry, dict):
            raise IngestError("every transcript entry must be an object")
        for key in ("number", "answer", "confidence"):
            if key not in entry:
                raise IngestError(f"transcript entry missing required key: {key}")
        number = entry["number"]
        if not _is_int(number) or number < 1:
            raise IngestError("transcript number must be an int >= 1 (bool rejected)")
        answer = entry["answer"]
        if answer is not None and not isinstance(answer, str):
            raise IngestError("transcript answer must be a str or null")
        confidence = entry["confidence"]
        if not _is_unit_interval(confidence):
            raise IngestError("transcript confidence must be a finite number in [0, 1]")
        entries.append(
            {"number": number, "answer": answer, "confidence": float(confidence)}
        )
    return entries


def ingest_photo(
    image,
    paper,
    bank,
    client,
    grader,
    *,
    image_format="png",
    min_confidence=MIN_CONFIDENCE,
) -> IngestResult:
    """拍照录入管线主入口（校验顺序 V1..V8 冻结，任一失败抛 IngestError 且零出网）。

    恰好一次出网：client.vision(prompt, [image], image_format=image_format)；
    转写非法在出网之后抛 IngestError。client/grader 抛出的异常原样传播。
    路由优先级冻结：unknown_number > duplicate_number > low_confidence >
    answer_form；空白作答交 grader(item, None) 不伪造；duplicate 每个副本各一条；
    缺号按卷面题号升序排在条目级复核之后；responses 按卷面题号升序。
    """
    # V1 client 表面
    vision = getattr(client, "vision", _MISSING)
    if vision is _MISSING or not callable(vision):
        raise IngestError("client must expose a callable vision(...)")
    # V2 grader 表面
    if not callable(grader):
        raise IngestError("grader must be callable")
    # V3 image：非空 bytes（bytearray 一并拒绝）
    if not isinstance(image, bytes) or not image:
        raise IngestError("image must be non-empty bytes")
    # V4 image_format：∈ IMAGE_FORMATS（大小写敏感）
    if image_format not in IMAGE_FORMATS:
        raise IngestError(f"image_format must be one of {IMAGE_FORMATS}")
    # V5 min_confidence：有限数字且落在 [0, 1]
    if not _is_unit_interval(min_confidence):
        raise IngestError("min_confidence must be a finite number in [0, 1]")
    # V6–V8 卷面表面 + 空卷门
    questions = _paper_questions(paper, bank)
    total = len(questions)
    by_number = {number: q for number, q in ((q[0], q) for q in questions)}

    # 恰好一次出网（唯一注入口）
    prompt = build_transcribe_prompt(paper, bank)
    raw = vision(prompt, [image], image_format=image_format)
    entries = parse_transcript(raw)

    counts = {}
    for entry in entries:
        number = entry["number"]
        counts[number] = counts.get(number, 0) + 1

    graded = []  # [(卷面题号, Response)]，判分调用按转写序发生
    review = []
    for entry in entries:
        number = entry["number"]
        answer = entry["answer"]
        confidence = entry["confidence"]
        question = by_number.get(number)
        if question is None:
            # 1. 题号不在卷面 1..N（item_id 恒 None，不再看其余条件）
            review.append(
                ReviewItem(
                    number=number,
                    item_id=None,
                    answer=answer,
                    confidence=confidence,
                    reason=REASON_UNKNOWN_NUMBER,
                    detail=f"number {number} is not on paper (1..{total})",
                )
            )
            continue
        _number, item, labels, item_type = question
        if counts[number] > 1:
            # 2. 该题号在转写中出现 >1 次（每个副本各产一条）
            review.append(
                ReviewItem(
                    number=number,
                    item_id=item.id,
                    answer=answer,
                    confidence=confidence,
                    reason=REASON_DUPLICATE_NUMBER,
                    detail=f"number {number} transcribed {counts[number]} times",
                )
            )
            continue
        if confidence < min_confidence:
            # 3. 置信度门（严格小于；等于门限通过）
            review.append(
                ReviewItem(
                    number=number,
                    item_id=item.id,
                    answer=answer,
                    confidence=confidence,
                    reason=REASON_LOW_CONFIDENCE,
                    detail=(
                        f"confidence {confidence} < min_confidence {min_confidence}"
                    ),
                )
            )
            continue
        if answer is None or not answer.strip():
            # 4. VLM 显式 null/空白串：无作答证据恒判错，交 grader(item, None)
            graded.append((number, grader(item, None)))
            continue
        if item_type == "choice":
            # 5. choice 形态门：单字符标签（strip+大写）命中标签列才判
            token = answer.strip().upper()
            if len(token) == 1 and token in labels:
                index = labels.index(token)
                graded.append((number, grader(item, item.options[index])))
            else:
                review.append(
                    ReviewItem(
                        number=number,
                        item_id=item.id,
                        answer=answer,
                        confidence=confidence,
                        reason=REASON_ANSWER_FORM,
                        detail=(
                            f"choice answer must be a single bubble label in "
                            f"{labels}, got {answer!r}"
                        ),
                    )
                )
            continue
        # 6. fill/solve：原文透传，不 strip
        graded.append((number, grader(item, answer)))

    # 缺号：按卷面题号升序排在全部条目级复核之后
    transcribed = {entry["number"] for entry in entries}
    for number in sorted(by_number):
        if number not in transcribed:
            _number, item, _labels, _item_type = by_number[number]
            review.append(
                ReviewItem(
                    number=number,
                    item_id=item.id,
                    answer=None,
                    confidence=None,
                    reason=REASON_MISSING_NUMBER,
                    detail=f"number {number} missing from transcript",
                )
            )

    graded.sort(key=lambda pair: pair[0])
    return IngestResult(
        responses=[response for _number, response in graded], review=review
    )
