"""mm_ingest — 拍照录入管线（BACKLOG P3）的确定性内核。

按 `specs/frozen/mm_ingest.spec.md`（冻结 v1，第三波）实现：

    一张学生作答照片
      → VLM 结构化转写（题号 → 学生答案 JSON，schema 冻结）
      → 确定性校验（题号 ∈ 卷面 1..N / 答案形态 / 置信度门）
      → 注入的 grader 产出 Response
      → 不可信条目（未知题号/重复题号/低置信/形态不符/卷面缺号）进复核队列

不可信条目「不猜测、不静默判分」：它们只进 `IngestResult.review`，零次 grader 调用。

模块间零 import：client（表面同 `mm_client.MMClient`）、grader（表面同
`grading.grade_to_response`）、bank/paper/item 全是注入的鸭子类型，只按成员调用。
与 `omr_sheet.parse_option` / `grading.grade_to_response` 的一致性由契约测试在测试内
跨模块锁定，本模块不 import 它们的定义。

学生面卫生：VLM prompt 只含题号/题型/choice 标签，绝不含 stem/answer/solution/选项正文。

全模块纯函数：无文件/网络 IO、无随机、无系统时钟、不读环境、不留全局可变状态
（无时间戳字段，无豁免）；同输入同输出。
"""

import json
import math
import re
from dataclasses import dataclass
from typing import Optional

from xuexing.types import Response, to_dict

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

# ---------- 3.1 常量与异常（冻结） ----------

INGEST_VERSION = "1"
MIN_CONFIDENCE = 0.9
IMAGE_FORMATS = ("png", "jpg", "jpeg", "webp", "gif")

REASON_UNKNOWN_NUMBER = "unknown_number"
REASON_DUPLICATE_NUMBER = "duplicate_number"
REASON_MISSING_NUMBER = "missing_number"
REASON_LOW_CONFIDENCE = "low_confidence"
REASON_ANSWER_FORM = "answer_form"
REVIEW_REASONS = (
    REASON_UNKNOWN_NUMBER,
    REASON_DUPLICATE_NUMBER,
    REASON_MISSING_NUMBER,
    REASON_LOW_CONFIDENCE,
    REASON_ANSWER_FORM,
)


class IngestError(ValueError):
    """本模块唯一异常类型（ValueError 的**直接**子类），覆盖本模块一切校验失败。

    唯一例外：client/grader 自身抛出的异常按原类型原样传播，本模块不转换、不吞掉。
    """


# ---------- 内部常量 ----------

_MISSING = object()  # 属性缺失哨兵（缺属性一律 IngestError，不漏 AttributeError）
_MAX_BUBBLES = 26  # choice 题气泡上限（26 = 回退标签列 A..Z 的长度）
_FALLBACK_LABELS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"  # 无显式标签选项的按位回退
_ITEM_TYPES = ("choice", "fill", "solve")
# 选项标签闭式：单 ASCII 字母 + 分隔符 [.．、)）]，与 omr_sheet.parse_option 同闭式
_OPT_RE = re.compile(r"([A-Za-z])[.．、)）][ \t]*(.*)\Z", re.S)

# 冻结 prompt 模板（仅两处变量位：{n} 与逐题清单行；schema 行含字面花括号，故拼接）
_PROMPT_PREAMBLE = (
    "你是阅卷录入助手。下面是一张学生作答照片对应的卷面题目清单，请逐题转写学生答案。\n"
    "只输出一个 JSON 对象，不要输出任何其他文字。\n"
    '输出 JSON schema（冻结）：{"answers": [{"number": 题号整数, "answer": '
    '学生答案字符串或 null, "confidence": 0 到 1 的数字}]}\n'
)
_PROMPT_RULES = (
    "规则：\n"
    "1. 卷面共 {n} 道题，题号 1..{n}，每个题号在 answers 中恰好出现一次。\n"
    "2. choice 题：answer 只输出被选选项的标签字母（A-Z 之一）；未作答输出 null。\n"
    "3. fill/solve 题：answer 按照片原样转写学生书写内容；未作答输出 null。\n"
    "4. confidence 是你对该条转写的置信度，取 0 到 1。\n"
    "卷面题目清单：\n"
)


# ---------- 3.2 / 3.3 输出形状 ----------

@dataclass
class ReviewItem:
    """复核队列条目：每条转写至多一个 reason（五词表之一）。"""

    number: int  # 转写题号；missing_number 时为卷面缺号
    item_id: Optional[str]  # 卷内号给 item_id；unknown_number 恒 None
    answer: Optional[str]  # 转写原文；missing_number 恒 None
    confidence: Optional[float]  # 转写置信度；missing_number 恒 None
    reason: str  # 恰一个，词表见 REVIEW_REASONS
    detail: str

    def to_dict(self) -> dict:
        """六字段原样成 dict（I16）。"""
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
    """一次拍照录入的产出：判分结果 + 复核队列。"""

    responses: list[Response]  # 按卷面题号升序（注解写真实对象，见 §2 装载约束）
    review: list  # list[ReviewItem]，条目级（转写序）+ 缺号（题号升序）

    def to_dict(self) -> dict:
        """responses 经 xuexing.types.to_dict 递归序列化（I16）。"""
        return {
            "responses": [to_dict(r) for r in self.responses],
            "review": [item.to_dict() for item in self.review],
        }


@dataclass
class _Question:
    """卷面展开后的一题（sections 顺序展开 / 空 sections 回退 paper.item_ids）。"""

    number: int  # 卷面题号 1..N
    item_id: str  # 卷内题号
    item: object  # 注入的 item 鸭子类型（只读 id/item_type/options/answer）
    item_type: str  # "choice" | "fill" | "solve"
    labels: list  # choice 题的标签列；非 choice 题为空列
    options: list  # choice 题 options 的拷贝（不修改入参）


# ---------- 3.4 option_labels ----------

def option_labels(item) -> list:
    """choice 题的选项标签列（与 omr_sheet.parse_option 同闭式，I3）。

    逐选项 `strip()` 后按 `([A-Za-z])[.．、)）][ \\t]*(.*)\\Z` 匹配：命中取捕获字母
    归一大写；未命中按位回退 `_FALLBACK_LABELS[i]`。

    守卫（任一违反 → IngestError）：options 缺失 / 非 list·tuple / 长度 < 2 /
    长度 > 26 / 含非 str 或空白串 / 解析出的标签有重复。
    """
    options = getattr(item, "options", _MISSING)
    if options is _MISSING:
        raise IngestError("choice item requires an options attribute")
    if not isinstance(options, (list, tuple)):
        raise IngestError("choice item.options must be a list or tuple")
    if len(options) < 2:
        raise IngestError("choice item.options needs at least 2 options")
    if len(options) > _MAX_BUBBLES:
        raise IngestError(
            f"choice item.options exceeds {_MAX_BUBBLES} options"
        )
    labels = []
    for index, option in enumerate(options):
        if not isinstance(option, str):
            raise IngestError(f"choice option {index} is not a str")
        text = option.strip()
        if not text:
            raise IngestError(f"choice option {index} is blank")
        matched = _OPT_RE.match(text)
        if matched is not None:
            labels.append(matched.group(1).upper())
        else:
            labels.append(_FALLBACK_LABELS[index])
    if len(set(labels)) != len(labels):
        raise IngestError("choice option labels are duplicated")
    return labels


# ---------- 3.5 build_transcribe_prompt ----------

def build_transcribe_prompt(paper, bank) -> str:
    """卷面 → 确定性 VLM 转写提示词（只含题号/题型/choice 标签，I4）。

    内部先经卷面表面校验（V6–V8 + 空卷门，失败抛 IngestError），再渲染冻结文本：
    仅 `{n}`（题数）与逐题清单行两处变量位；文本恰以清单末行结束，无尾随换行。
    """
    return _render_prompt(_paper_questions(paper, bank))


def _render_prompt(questions: list) -> str:
    """渲染冻结 prompt 文本（ingest_photo 与 build_transcribe_prompt 共用）。"""
    lines = []
    for question in questions:
        line = f"{question.number}. {question.item_type}"
        if question.item_type == "choice":
            line += " 选项 " + "/".join(question.labels)
        lines.append(line)
    rules = _PROMPT_RULES.replace("{n}", str(len(questions)))
    return _PROMPT_PREAMBLE + rules + "\n".join(lines)


# ---------- 3.6 parse_transcript ----------

def parse_transcript(text) -> list:
    """VLM 回复文本 → `[{"number", "answer", "confidence"}, ...]`（schema 冻结，I8）。

    切片闭式：首个 "{" 到最后一个 "}"（容忍前后闲话与 ```json 围栏）；无 "{" 或
    "}" 不在起点之后 → IngestError；JSON 解析失败（含两个独立对象）→ IngestError。
    """
    if not isinstance(text, str):
        raise IngestError("transcript must be a str")
    stripped = text.strip()
    if not stripped:
        raise IngestError("transcript is empty")
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start < 0 or end <= start:
        raise IngestError("transcript carries no JSON object")
    try:
        payload = json.loads(stripped[start:end + 1])
    except (TypeError, ValueError):
        raise IngestError("transcript JSON is malformed") from None
    if not isinstance(payload, dict):
        raise IngestError("transcript top level must be a JSON object")
    if "answers" not in payload:
        raise IngestError('transcript needs an "answers" key')
    raw_answers = payload["answers"]
    if not isinstance(raw_answers, list):
        raise IngestError('transcript "answers" must be a list')
    entries = []
    for entry in raw_answers:
        if not isinstance(entry, dict):
            raise IngestError("answers entry must be a JSON object")
        for key in ("number", "answer", "confidence"):
            if key not in entry:
                raise IngestError(f'answers entry needs a "{key}" key')
        number = entry["number"]
        if not _is_int(number) or number < 1:
            raise IngestError("number must be an int >= 1")
        answer = entry["answer"]
        if answer is not None and not isinstance(answer, str):
            raise IngestError("answer must be a str or null")
        confidence = entry["confidence"]
        if not _is_number(confidence):
            raise IngestError("confidence must be a number")
        if not 0.0 <= confidence <= 1.0 or not math.isfinite(confidence):
            raise IngestError("confidence must be finite within [0.0, 1.0]")
        entries.append(
            {"number": number, "answer": answer, "confidence": float(confidence)}
        )
    return entries


# ---------- 3.7 ingest_photo ----------

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
    """拍照录入管线主入口：照片 → VLM 转写 → 确定性校验 → 注入 grader → 产出。

    校验顺序 V1..V8 冻结，任一失败抛 IngestError 且**零次** client 调用；通过后恰好
    一次出网 `client.vision(prompt, [image], image_format=image_format)`。

    路由优先级冻结：unknown_number > duplicate_number > low_confidence > answer_form；
    空白 / null 作答交 `grader(item, None)`（恒判错，不伪造、不进复核）；choice 题单字符
    标签命中则交该下标的**选项原文全串**，fill/solve 原文透传（不 strip）。
    """
    # V1 client 表面
    if not callable(getattr(client, "vision", None)):
        raise IngestError("client.vision must be callable")
    # V2 grader 表面
    if not callable(grader):
        raise IngestError("grader must be callable")
    # V3 image：非空 bytes（bytearray 等非 bytes 一律拒绝）
    if not isinstance(image, bytes) or not image:
        raise IngestError("image must be non-empty bytes")
    # V4 image_format：大小写敏感
    if image_format not in IMAGE_FORMATS:
        raise IngestError(f"image_format must be one of {IMAGE_FORMATS}")
    # V5 min_confidence：[0.0, 1.0] 的有限非 bool 数字
    if not _is_number(min_confidence):
        raise IngestError("min_confidence must be a number")
    if not 0.0 <= min_confidence <= 1.0 or not math.isfinite(min_confidence):
        raise IngestError("min_confidence must be finite within [0.0, 1.0]")
    # V6–V8 卷面表面 + 空卷门（绑定条款，任一失败均零出网）
    questions = _paper_questions(paper, bank)

    # 恰好一次出网（唯一注入口）
    prompt = _render_prompt(questions)
    raw = client.vision(prompt, [image], image_format=image_format)
    entries = parse_transcript(raw)  # 转写非法 → IngestError，但 client 已调恰好一次

    total = len(questions)
    counts = {}
    for entry in entries:
        counts[entry["number"]] = counts.get(entry["number"], 0) + 1

    responses = {}
    review = []
    for entry in entries:
        number = entry["number"]
        answer = entry["answer"]
        confidence = entry["confidence"]
        count = counts[number]
        if number < 1 or number > total:  # 题号不在卷面 1..N
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
        question = questions[number - 1]
        if count > 1:  # 重复题号：每个副本各产一条复核
            review.append(
                ReviewItem(
                    number=number,
                    item_id=question.item_id,
                    answer=answer,
                    confidence=confidence,
                    reason=REASON_DUPLICATE_NUMBER,
                    detail=f"number {number} transcribed {count} times",
                )
            )
            continue
        if confidence < min_confidence:  # 严格小于；等于门限通过
            review.append(
                ReviewItem(
                    number=number,
                    item_id=question.item_id,
                    answer=answer,
                    confidence=confidence,
                    reason=REASON_LOW_CONFIDENCE,
                    detail=f"confidence {confidence} < min_confidence {min_confidence}",
                )
            )
            continue
        if answer is None or not answer.strip():  # 无作答证据 → 恒判错，不伪造
            responses[number] = grader(question.item, None)
            continue
        if question.item_type == "choice":
            token = answer.strip().upper()
            if len(token) == 1 and token in question.labels:
                index = question.labels.index(token)
                responses[number] = grader(question.item, question.options[index])
            else:
                review.append(
                    ReviewItem(
                        number=number,
                        item_id=question.item_id,
                        answer=answer,
                        confidence=confidence,
                        reason=REASON_ANSWER_FORM,
                        detail=(
                            "choice answer must be a single bubble label in "
                            f"{question.labels}, got {answer!r}"
                        ),
                    )
                )
            continue
        responses[number] = grader(question.item, answer)  # 原文透传，不 strip

    # 缺号：转写里完全没出现的卷面题号，按题号升序排在全部条目级复核之后
    for question in questions:
        if question.number in counts:
            continue
        review.append(
            ReviewItem(
                number=question.number,
                item_id=question.item_id,
                answer=None,
                confidence=None,
                reason=REASON_MISSING_NUMBER,
                detail=f"number {question.number} missing from transcript",
            )
        )

    return IngestResult([responses[number] for number in sorted(responses)], review)


# ---------- 卷面 / 题库表面（V6–V8，绑定条款） ----------

def _paper_questions(paper, bank) -> list:
    """卷面表面校验 + 展开成题号 1..N 的 _Question 列（产出拷贝，不改入参）。"""
    # V6-1 paper_id / title 必须为 str
    for attr in ("paper_id", "title"):
        value = getattr(paper, attr, _MISSING)
        if not isinstance(value, str):
            raise IngestError(f"paper.{attr} must be a str")
    # V6-2 bank.items() 可调用、返回可迭代、item.id 非空白 str 且 bank 内不重复
    index = _bank_index(bank)
    # V6-3/V7-3 sections 形态；空 sections 回退单一隐式节 [{item_ids: paper.item_ids}]
    sections = _section_lists(paper)
    # V6-4/V7-4/V8-4 逐题：题号、bank 可查、题型闭式、choice 标签与标答门
    questions = []
    for section in sections:
        for item_id in section:
            questions.append(_make_question(len(questions) + 1, item_id, index))
    if not questions:  # 空卷门
        raise IngestError("paper expands to zero questions")
    return questions


def _bank_index(bank) -> dict:
    """bank → {item.id: item}（id 须非空白 str 且不重复；产出拷贝，不改入参）。"""
    items_attr = getattr(bank, "items", _MISSING)
    if not callable(items_attr):
        raise IngestError("bank.items must be callable")
    try:
        raw_items = items_attr()
        iterator = iter(raw_items)
    except TypeError:
        raise IngestError("bank.items() must return an iterable") from None
    index = {}
    while True:
        try:
            item = next(iterator)
        except StopIteration:
            break
        except TypeError:
            raise IngestError("bank.items() must return an iterable") from None
        item_id = getattr(item, "id", _MISSING)
        if not isinstance(item_id, str) or not item_id.strip():
            raise IngestError("bank item id must be a non-blank str")
        if item_id in index:
            raise IngestError(f"bank item id is duplicated: {item_id}")
        index[item_id] = item
    return index


def _section_lists(paper) -> list:
    """paper.sections → 各节的题号列（拷贝）；空 sections 回退 paper.item_ids。"""
    sections = getattr(paper, "sections", _MISSING)
    if not isinstance(sections, (list, tuple)):
        raise IngestError("paper.sections must be a list or tuple")
    if not len(sections):  # 空 sections → 单一隐式节
        item_ids = getattr(paper, "item_ids", _MISSING)
        if not isinstance(item_ids, (list, tuple)):
            raise IngestError("paper.item_ids must be a list or tuple")
        sections = [{"item_ids": item_ids}]
    out = []
    for section in sections:
        if not isinstance(section, dict):
            raise IngestError("each paper section must be a dict")
        item_ids = section.get("item_ids", _MISSING)
        if not isinstance(item_ids, (list, tuple)):
            raise IngestError("each paper section needs a list/tuple item_ids")
        out.append(list(item_ids))
    return out


def _make_question(number: int, item_id, index: dict) -> _Question:
    """单题表面校验：题号非空白 str、在 bank 内、题型闭式、choice 标签与标答门。"""
    if not isinstance(item_id, str) or not item_id.strip():
        raise IngestError("paper question id must be a non-blank str")
    item = index.get(item_id)
    if item is None:
        raise IngestError(f"paper question {item_id} is not in the bank")
    item_type = getattr(item, "item_type", None)
    if item_type not in _ITEM_TYPES:
        raise IngestError(f"unsupported item_type: {item_type!r}")
    if item_type != "choice":
        return _Question(
            number=number,
            item_id=item_id,
            item=item,
            item_type=item_type,
            labels=[],
            options=[],
        )
    labels = option_labels(item)  # choice 选项守卫（V8）
    _check_choice_answer(item, labels)
    return _Question(
        number=number,
        item_id=item_id,
        item=item,
        item_type=item_type,
        labels=labels,
        options=list(item.options),
    )


def _check_choice_answer(item, labels: list) -> None:
    """choice 标答门：str，且去空白大写后 ∈ 标签列或等于某选项原文（去空白大写）。"""
    answer = getattr(item, "answer", _MISSING)
    if not isinstance(answer, str):
        raise IngestError("choice item.answer must be a str")
    token = answer.strip().upper()
    if token in labels:
        return
    for option in item.options:
        if isinstance(option, str) and option.strip().upper() == token:
            return
    raise IngestError(
        f"choice item.answer is neither a label nor an option: {answer!r}"
    )


# ---------- 数值判定 helpers（bool 一律拒绝） ----------

def _is_int(value) -> bool:
    """int 且非 bool。"""
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value) -> bool:
    """int/float 且非 bool。"""
    return isinstance(value, (int, float)) and not isinstance(value, bool)
