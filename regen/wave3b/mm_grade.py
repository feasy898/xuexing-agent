"""mm_grade —— 主观解答题（solve）手写作答照片的 VLM 辅助判分确定性内核。

契约来源：specs/frozen/mm_grade.spec.md（冻结 v1，第三波）。本文实现严格遵守该契约的
公开 API（第 3 节）、不变量（第 4 节）、确定性与随机性（第 5 节）与错误行为（第 6 节）。

判分诚实性三原则（见 spec §1 / §7）：

1. VLM prompt 只含题面（stem）与转写指令，**绝不含** answer / solution——防止 VLM 把参考
   答案抄进学生步骤；给分 100% 在本地按冻结规则计算。
2. 宁可交人，不猜：低置信步骤不计分只标记；步骤不齐记 ``partial_match``；缺最终答案记
   ``final_answer_missing``；步骤全对但答案判错记 ``contradiction``。
3. 闭环两路互斥：干净建议走 ``suggest_response``，需复核建议走 ``confirm_review``。

模块纯度（spec §2 / §5）：无 IO、无随机、无时钟、不读环境、无全局可变状态；唯一的外部
交互是注入的 ``client.vision`` 恰好一次调用。``client`` 与 ``answer_grader`` 均为注入的鸭子
参数，本模块绝不 import 它们的定义模块。

装载约束（spec §2）：本文件被 ``spec_from_file_location`` 以顶层模块名 ``_regen_mm_grade``
装载，因此**不使用** ``from __future__ import annotations``（字符串化注解曾崩 dataclasses
探测）、**不使用**相对导入（相对导入在顶层名装载时失败）；注解直接写真实对象。
"""

import json
import math
import re

from dataclasses import dataclass
from typing import Optional

from xuexing.types import Response

__all__ = [
    "GRADE_VERSION",
    "IMAGE_FORMATS",
    "MIN_CONFIDENCE",
    "REASON_CONTRADICTION",
    "REASON_FINAL_ANSWER_MISSING",
    "REASON_LOW_CONFIDENCE",
    "REASON_PARTIAL_MATCH",
    "REVIEW_REASONS",
    "GradeError",
    "GradeSuggestion",
    "Response",
    "StepScore",
    "build_grade_prompt",
    "confirm_review",
    "grade_solution",
    "match_key",
    "parse_transcription",
    "solution_steps",
    "steps_match",
    "suggest_response",
]


# ---------------------------------------------------------------------------
# §3.1 常量与异常（值一律冻结）
# ---------------------------------------------------------------------------


class GradeError(ValueError):
    """本模块唯一异常类型。

    唯一例外是注入的 ``client.vision`` 与 ``answer_grader`` 自身抛出的异常——按 spec
    §3.8 第 6 条原样传播（不包装、不吞）。
    """


#: 判分内核版本。prompt 文案与转写 schema 均由此版本承载；加字段 / 改文案 = 换契约。
GRADE_VERSION = "1"

#: 步骤级置信度门。边界为**含等于**：``confidence == min_confidence`` 参与匹配。
MIN_CONFIDENCE = 0.9

#: 允许的图片格式（顺序与大小写均冻结），与 ``mm_client.IMAGE_MIME`` 键集相等。
IMAGE_FORMATS = ("png", "jpg", "jpeg", "webp", "gif")

REASON_LOW_CONFIDENCE = "low_confidence"
REASON_FINAL_ANSWER_MISSING = "final_answer_missing"
REASON_PARTIAL_MATCH = "partial_match"
REASON_CONTRADICTION = "contradiction"

#: 复核原因词表：值与顺序冻结，``suggestion.reasons`` 严格按此顺序、无重复。
REVIEW_REASONS = (
    REASON_LOW_CONFIDENCE,
    REASON_FINAL_ANSWER_MISSING,
    REASON_PARTIAL_MATCH,
    REASON_CONTRADICTION,
)


# ---------------------------------------------------------------------------
# 内部冻结常量
# ---------------------------------------------------------------------------

#: 行首序号标记（spec §7：冻结，非智能纠错）。可选全/半角开括号 + 1..3 位 ASCII 数字
#: 或中文数字 + 恰一个分隔符 + 紧随空白。只剥**一个**。
_STEP_MARKER_RE = re.compile(r"^[（(]?[0-9一二三四五六七八九十]{1,3}[、.．:：)）]\s*")

#: 全部空白（``\s+`` 含 U+3000 等 Unicode 空白）。
_WHITESPACE_RE = re.compile(r"\s+")


class _FullwidthFold:
    """无状态的全角折叠映射（``str.translate`` 要求映射对象实现 ``__getitem__``）。

    码点 ∈ [0xFF01, 0xFF5E] → ``chr(cp - 0xFEE0)``；U+3000 → 半角空格；其余原样。
    刻意做成 ``__slots__`` 空状态的不可变对象而非模块级 dict 表，避开 §2 / §5 禁止的
    「全局可变状态」。
    """

    __slots__ = ()

    def __getitem__(self, codepoint):
        if 0xFF01 <= codepoint <= 0xFF5E:
            return chr(codepoint - 0xFEE0)
        if codepoint == 0x3000:
            return " "
        return chr(codepoint)


_FULLWIDTH_FOLD = _FullwidthFold()

#: §3.5 逐字节冻结的 prompt 前 8 行；第 9 行为 ``item.stem`` 原样。
_PROMPT_LINES = (
    "你是阅卷助手。下面是一道主观解答题的题面，请从学生手写作答照片中逐行转写学生的解答过程。",
    "只输出一个 JSON 对象，不要输出任何其他文字。",
    '输出 JSON schema（冻结）：{"steps": [{"text": 学生某一步书写内容的原样转写, '
    '"confidence": 0 到 1 的数字}], "final_answer": 学生最终答案字符串或 null}',
    "规则：",
    "1. 只转写学生实际书写的内容，按书写顺序逐行转写；不补全、不改写、不自己计算。",
    "2. text 是该步原样转写；confidence 是你对该步转写的置信度，取 0 到 1。",
    "3. 学生写了最终答案则原样转写为 final_answer；没有写输出 null。",
    "题面：",
)


# ---------------------------------------------------------------------------
# §3.7 数据形状
# ---------------------------------------------------------------------------


@dataclass
class StepScore:
    """一个参考步骤的给分结果。"""

    index: int                   # 参考步骤下标（0 起，参考解切分序）
    ref_text: str                # 参考步骤原文（切分后）
    student_text: Optional[str]  # 配对到的学生步骤原文；未配对 None
    awarded: int                 # 1=配对计 1 分；0=未配对不计分

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "ref_text": self.ref_text,
            "student_text": self.student_text,
            "awarded": self.awarded,
        }


@dataclass
class GradeSuggestion:
    """一次判分的完整建议：分步给分 + 复核原因。"""

    item_id: str
    steps: list                   # list[StepScore]，参考步骤序
    max_points: int               # 满分 = 参考步骤数
    suggested_points: int         # 建议得分（配对数）
    final_answer: Optional[str]   # 转写最终答案（空白已规整为 None）
    final_answer_correct: bool    # answer_grader(item, final_answer) 的判定
    flagged_steps: list           # list[str]：低于置信度门的学生步骤原文（转写序）
    reasons: list                 # list[str]：REVIEW_REASONS 词表序、无重复
    needs_review: bool            # == bool(reasons)

    def to_dict(self) -> dict:
        return {
            "item_id": self.item_id,
            "steps": [step.to_dict() for step in self.steps],
            "max_points": self.max_points,
            "suggested_points": self.suggested_points,
            "final_answer": self.final_answer,
            "final_answer_correct": self.final_answer_correct,
            "flagged_steps": list(self.flagged_steps),
            "reasons": list(self.reasons),
            "needs_review": self.needs_review,
        }


# ---------------------------------------------------------------------------
# 内部守卫与渲染
# ---------------------------------------------------------------------------


def _is_blank(value) -> bool:
    """非 str 或 strip 后为空。"""
    return not isinstance(value, str) or not value.strip()


def _validate_item_surface(item):
    """§3.8-V6 题目表面守卫，返回 ``(item_id, stem, ref_steps)``。

    顺序冻结：``id`` 非空 str → ``item_type == "solve"`` → ``stem`` 非空 str →
    ``answer`` 非空 str → ``solution`` 为 str 且切出 ≥ 1 步。任一失败抛 ``GradeError``。
    """
    item_id = getattr(item, "id", None)
    if _is_blank(item_id):
        raise GradeError("item.id must be a non-empty str")

    item_type = getattr(item, "item_type", None)
    if item_type != "solve":
        raise GradeError("item.item_type must be 'solve', got %r" % (item_type,))

    stem = getattr(item, "stem", None)
    if _is_blank(stem):
        raise GradeError("item.stem must be a non-empty str")

    answer = getattr(item, "answer", None)
    if _is_blank(answer):
        raise GradeError("item.answer must be a non-empty str")

    solution = getattr(item, "solution", None)
    if not isinstance(solution, str):
        raise GradeError("item.solution must be a str, got %r" % (type(solution).__name__,))

    ref_steps = solution_steps(solution)
    if not ref_steps:
        raise GradeError("item.solution yields no steps")

    return item_id, stem, ref_steps


def _render_grade_prompt(stem: str) -> str:
    """由题面确定性渲染 §3.5 的 9 行 prompt（末行为 stem 原样）。"""
    return "\n".join(_PROMPT_LINES + (stem,))


def _require_suggestion_surface(suggestion):
    """§3.9：``suggestion`` 必须暴露非空 str ``item_id`` 与 bool ``needs_review``。"""
    item_id = getattr(suggestion, "item_id", None)
    if _is_blank(item_id):
        raise GradeError("suggestion.item_id must be a non-empty str")

    needs_review = getattr(suggestion, "needs_review", None)
    if not isinstance(needs_review, bool):
        raise GradeError("suggestion.needs_review must be a bool")

    return item_id, needs_review


# ---------------------------------------------------------------------------
# §3.2 / §3.3 / §3.4 冻结的文本与匹配规则
# ---------------------------------------------------------------------------


def solution_steps(solution: str) -> list[str]:
    """参考解文本 → 步骤列表（判分侧唯一步骤来源）。

    冻结规则：按行切分（``splitlines``，容忍 ``\\r\\n``）→ 逐行去首尾空白 → 剥**一个**
    行首序号标记 → 再 strip → 丢空行。非 str → ``GradeError``；切不出步骤 → ``[]``
    （拒绝由调用方守卫负责）。
    """
    if not isinstance(solution, str):
        raise GradeError("solution_steps requires a str, got %r" % (type(solution).__name__,))

    steps = []
    for raw_line in solution.splitlines():
        line = raw_line.strip()
        line = _STEP_MARKER_RE.sub("", line, count=1).strip()
        if line:
            steps.append(line)
    return steps


def match_key(text: str) -> str:
    """匹配键：全角折叠 → 删除**全部**空白 → 小写化（不剥尾部标点）。"""
    if not isinstance(text, str):
        raise GradeError("match_key requires a str, got %r" % (type(text).__name__,))

    folded = text.translate(_FULLWIDTH_FOLD)
    return _WHITESPACE_RE.sub("", folded).lower()


def steps_match(ref_text: str, student_text: str) -> bool:
    """双向包含匹配（冻结）。任一侧键为空（空白 / 空串步骤）→ ``False``。"""
    if not isinstance(ref_text, str):
        raise GradeError("steps_match requires a str reference step, got %r"
                         % (type(ref_text).__name__,))
    if not isinstance(student_text, str):
        raise GradeError("steps_match requires a str student step, got %r"
                         % (type(student_text).__name__,))

    ref_key = match_key(ref_text)
    student_key = match_key(student_text)
    if not ref_key or not student_key:
        return False
    return student_key == ref_key or ref_key in student_key or student_key in ref_key


# ---------------------------------------------------------------------------
# §3.5 / §3.6 提示词与转写解析
# ---------------------------------------------------------------------------


def build_grade_prompt(item) -> str:
    """solve 题 → 确定性 VLM 转写提示词。**只含题面，绝不含 answer / solution**。"""
    _item_id, stem, _ref_steps = _validate_item_surface(item)
    return _render_grade_prompt(stem)


def parse_transcription(text: str) -> dict:
    """VLM 回复文本 → ``{"steps": [...], "final_answer": str | None}``（schema 冻结）。"""
    if not isinstance(text, str):
        raise GradeError("parse_transcription requires a str, got %r" % (type(text).__name__,))

    stripped = text.strip()
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start < 0 or end < 0 or end < start:
        raise GradeError("transcription text contains no json object")

    try:
        payload = json.loads(stripped[start:end + 1])
    except json.JSONDecodeError as exc:
        raise GradeError("transcription json slice is not valid json: %s" % (exc,)) from exc

    if not isinstance(payload, dict):
        raise GradeError("transcription json must be an object, got %r"
                         % (type(payload).__name__,))

    if "steps" not in payload:
        raise GradeError("transcription json is missing the 'steps' key")
    raw_steps = payload["steps"]
    if not isinstance(raw_steps, list):
        raise GradeError("transcription 'steps' must be a list, got %r"
                         % (type(raw_steps).__name__,))

    steps = []
    for position, raw_step in enumerate(raw_steps):
        if not isinstance(raw_step, dict):
            raise GradeError("transcription step %d must be an object, got %r"
                             % (position, type(raw_step).__name__,))
        if "text" not in raw_step:
            raise GradeError("transcription step %d is missing the 'text' key" % (position,))
        step_text = raw_step["text"]
        if not isinstance(step_text, str):
            raise GradeError("transcription step %d 'text' must be a str, got %r"
                             % (position, type(step_text).__name__,))
        if "confidence" not in raw_step:
            raise GradeError("transcription step %d is missing the 'confidence' key" % (position,))
        confidence = raw_step["confidence"]
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            raise GradeError("transcription step %d 'confidence' must be a number, got %r"
                             % (position, type(confidence).__name__,))
        confidence = float(confidence)
        if not math.isfinite(confidence) or confidence < 0.0 or confidence > 1.0:
            raise GradeError("transcription step %d 'confidence' must be finite in [0, 1], got %r"
                             % (position, raw_step["confidence"]))
        # 未知键忽略；输出步骤 dict 的键集恰为 {"text", "confidence"}。
        steps.append({"text": step_text, "confidence": confidence})

    if "final_answer" in payload:
        raw_final = payload["final_answer"]
        if raw_final is None:
            final_answer = None
        elif isinstance(raw_final, str):
            final_answer = raw_final.strip() or None
        else:
            raise GradeError("transcription 'final_answer' must be a str or null, got %r"
                             % (type(raw_final).__name__,))
    else:
        final_answer = None

    return {"steps": steps, "final_answer": final_answer}


# ---------------------------------------------------------------------------
# §3.8 判分管线
# ---------------------------------------------------------------------------


def grade_solution(
    item,
    image: bytes,
    client,
    answer_grader,
    *,
    image_format: str = "png",
    min_confidence: float = MIN_CONFIDENCE,
) -> GradeSuggestion:
    """VLM 辅助判分管线：守卫 → 恰好一次出网 → 解析 → 恰好一次答案判定 → 本地分步给分。

    守卫顺序冻结（V1..V6），任一失败抛 ``GradeError`` 且**零次** ``client.vision`` 调用。
    注入对象自身抛出的异常原样传播（不包装、不吞）。
    """
    # --- V1：client 有 callable vision -------------------------------------
    vision_fn = getattr(client, "vision", None)
    if not callable(vision_fn):
        raise GradeError("client must expose a callable vision(prompt, images, image_format=)")

    # --- V2：answer_grader callable ----------------------------------------
    if not callable(answer_grader):
        raise GradeError("answer_grader must be callable, got %r" % (type(answer_grader).__name__,))

    # --- V3：image 为非空 bytes --------------------------------------------
    if not isinstance(image, bytes) or len(image) == 0:
        raise GradeError("image must be non-empty bytes, got %r" % (type(image).__name__,))

    # --- V4：image_format in IMAGE_FORMATS（大小写敏感） ---------------------
    if image_format not in IMAGE_FORMATS:
        raise GradeError("image_format must be one of %r, got %r"
                         % (IMAGE_FORMATS, image_format))

    # --- V5：min_confidence 为 [0, 1] 的有限数字（拒 bool） ------------------
    if (isinstance(min_confidence, bool)
            or not isinstance(min_confidence, (int, float))
            or not math.isfinite(min_confidence)
            or min_confidence < 0.0
            or min_confidence > 1.0):
        raise GradeError("min_confidence must be a finite number in [0, 1], got %r"
                         % (min_confidence,))

    # --- V6：题目表面 -------------------------------------------------------
    item_id, stem, ref_steps = _validate_item_surface(item)

    # --- 1. 恰好一次出网（线上 prompt 逐字节等于 build_grade_prompt(item)） ---
    raw = vision_fn(_render_grade_prompt(stem), [image], image_format=image_format)

    # --- 2. 解析转写（失败则 answer_grader 不被调用） -----------------------
    transcription = parse_transcription(raw)
    transcribed_steps = transcription["steps"]
    final_answer = transcription["final_answer"]

    # --- 3. 恰好一次答案判定（final_answer 可为 None：无证据也诚实判定一次） -
    verdict = answer_grader(item, final_answer)
    if not isinstance(verdict, bool):
        raise GradeError("answer_grader must return a bool, got %r" % (type(verdict).__name__,))

    # --- 4. 分步给分（规则冻结） --------------------------------------------
    trusted = []
    flagged_steps = []
    for transcribed in transcribed_steps:
        if transcribed["confidence"] < min_confidence:
            flagged_steps.append(transcribed["text"])
        else:
            trusted.append(transcribed["text"])

    used = [False] * len(trusted)
    step_scores = []
    suggested_points = 0
    for index, ref_text in enumerate(ref_steps):
        paired_text = None
        for position, student_text in enumerate(trusted):
            if not used[position] and steps_match(ref_text, student_text):
                used[position] = True
                paired_text = student_text
                break
        awarded = 1 if paired_text is not None else 0
        suggested_points += awarded
        step_scores.append(
            StepScore(index=index, ref_text=ref_text, student_text=paired_text, awarded=awarded)
        )
    max_points = len(ref_steps)

    # --- 5. 复核路由（按 REVIEW_REASONS 词表序累积） ------------------------
    reasons = []
    if flagged_steps:
        reasons.append(REASON_LOW_CONFIDENCE)
    if final_answer is None:
        reasons.append(REASON_FINAL_ANSWER_MISSING)
    if suggested_points < max_points:
        reasons.append(REASON_PARTIAL_MATCH)
    if suggested_points == max_points and verdict is False:
        reasons.append(REASON_CONTRADICTION)

    return GradeSuggestion(
        item_id=item_id,
        steps=step_scores,
        max_points=max_points,
        suggested_points=suggested_points,
        final_answer=final_answer,
        final_answer_correct=verdict,
        flagged_steps=flagged_steps,
        reasons=reasons,
        needs_review=bool(reasons),
    )


# ---------------------------------------------------------------------------
# §3.9 人机协同闭环两路（互斥）
# ---------------------------------------------------------------------------


def suggest_response(suggestion, response_ms: Optional[int] = None) -> Response:
    """干净建议（``needs_review is False``）→ ``Response``（``correct`` 恒 ``True``）。"""
    item_id, needs_review = _require_suggestion_surface(suggestion)
    if needs_review:
        raise GradeError("suggestion needs review: use confirm_review instead")
    return Response(
        item_id=item_id,
        correct=True,
        learner_answer=getattr(suggestion, "final_answer", None),
        response_ms=response_ms,
    )


def confirm_review(
    suggestion,
    correct: bool,
    learner_answer: Optional[str] = None,
    response_ms: Optional[int] = None,
) -> Response:
    """需复核建议（``needs_review is True``）→ 人审终审 ``Response``。"""
    item_id, needs_review = _require_suggestion_surface(suggestion)
    if not needs_review:
        raise GradeError("suggestion is already clean: use suggest_response instead")
    if not isinstance(correct, bool):
        raise GradeError("correct must be a bool, got %r" % (type(correct).__name__,))
    # 缺省判定是 `is None`：传入 "" / 0 等「假值」仍按人审改写记录，不回落到转写答案。
    answer = learner_answer if learner_answer is not None else getattr(suggestion, "final_answer", None)
    return Response(
        item_id=item_id,
        correct=correct,
        learner_answer=answer,
        response_ms=response_ms,
    )
