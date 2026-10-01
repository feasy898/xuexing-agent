"""mm_grade — 主观解答题（solve）手写作答照片的 VLM 辅助判分确定性内核。

重生成实例（第三波，冻结契约：specs/frozen/mm_grade.spec.md 冻结 v1）。
装载约束：无 `from __future__ import annotations`、无相对导入，注解直接写真实对象。
依赖仅标准库（json / math / re / dataclasses.dataclass / typing.Optional）与
`xuexing.types.Response`（绝对导入，唯一允许使用的 xuexing 类型）。
VLM 客户端（`client.vision`）与答案判定器（`answer_grader`）均为注入的鸭子参数，
本模块自身不出网、不判答案等值；prompt 只含题面，绝不泄漏 answer/solution；
给分 100% 在本地按冻结的确定性规则计算。
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

GRADE_VERSION = "1"

MIN_CONFIDENCE = 0.9

IMAGE_FORMATS = ("png", "jpg", "jpeg", "webp", "gif")

REASON_LOW_CONFIDENCE = "low_confidence"
REASON_FINAL_ANSWER_MISSING = "final_answer_missing"
REASON_PARTIAL_MATCH = "partial_match"
REASON_CONTRADICTION = "contradiction"

REVIEW_REASONS = (
    REASON_LOW_CONFIDENCE,
    REASON_FINAL_ANSWER_MISSING,
    REASON_PARTIAL_MATCH,
    REASON_CONTRADICTION,
)


class GradeError(ValueError):
    """本模块唯一异常类型（ValueError 直接子类）。"""


# 行首序号标记：可选全/半角开括号 + 1..3 位 ASCII 数字或中文数字 + 恰一个分隔符 + 紧随空白。
_STEP_MARKER_RE = re.compile(r"^[（(]?[0-9一二三四五六七八九十]{1,3}[、.．:：)）]\s*")

# VLM 转写提示词正文（前 8 行逐字节冻结；第 9 行为 item.stem 原样）。
_PROMPT_LINES = (
    "你是阅卷助手。下面是一道主观解答题的题面，请从学生手写作答照片中逐行转写学生的解答过程。",
    "只输出一个 JSON 对象，不要输出任何其他文字。",
    '输出 JSON schema（冻结）：{"steps": [{"text": 学生某一步书写内容的原样转写, "confidence": 0 到 1 的数字}], "final_answer": 学生最终答案字符串或 null}',
    "规则：",
    "1. 只转写学生实际书写的内容，按书写顺序逐行转写；不补全、不改写、不自己计算。",
    "2. text 是该步原样转写；confidence 是你对该步转写的置信度，取 0 到 1。",
    "3. 学生写了最终答案则原样转写为 final_answer；没有写输出 null。",
    "题面：",
)


def solution_steps(solution):
    """参考解文本 → 步骤列表：splitlines → 逐行 strip → 剥一个行首序号标记 → 再 strip → 丢空行。"""
    if not isinstance(solution, str):
        raise GradeError("solution must be str")
    steps = []
    for line in solution.splitlines():
        line = line.strip()
        line = _STEP_MARKER_RE.sub("", line, count=1)
        line = line.strip()
        if line:
            steps.append(line)
    return steps


def match_key(text):
    """匹配键：全角折叠（FF01-FF5E / U+3000）→ 删除全部空白 → 小写。"""
    if not isinstance(text, str):
        raise GradeError("match text must be str")
    folded = "".join(
        chr(ord(ch) - 0xFEE0) if 0xFF01 <= ord(ch) <= 0xFF5E else (" " if ch == "\u3000" else ch)
        for ch in text
    )
    return re.sub(r"\s+", "", folded).lower()


def steps_match(ref_text, student_text):
    """双向包含匹配：键相等或互为子串；任一侧键为空 → False。"""
    if not isinstance(ref_text, str) or not isinstance(student_text, str):
        raise GradeError("steps_match requires str inputs")
    ref_key = match_key(ref_text)
    student_key = match_key(student_text)
    if not ref_key or not student_key:
        return False
    return ref_key == student_key or ref_key in student_key or student_key in ref_key


def _validate_item(item):
    """题目表面守卫（V6）：id → item_type == "solve" → stem → answer → solution（≥1 步）。"""
    item_id = getattr(item, "id", None)
    if not isinstance(item_id, str) or not item_id.strip():
        raise GradeError("item.id must be a non-empty str")
    if getattr(item, "item_type", None) != "solve":
        raise GradeError("item.item_type must be 'solve'")
    stem = getattr(item, "stem", None)
    if not isinstance(stem, str) or not stem.strip():
        raise GradeError("item.stem must be a non-empty str")
    answer = getattr(item, "answer", None)
    if not isinstance(answer, str) or not answer.strip():
        raise GradeError("item.answer must be a non-empty str")
    solution = getattr(item, "solution", None)
    if not isinstance(solution, str) or not solution_steps(solution):
        raise GradeError("item.solution must be a str with at least one step")


def build_grade_prompt(item):
    """solve 题 → 确定性 VLM 转写提示词（9 行，只含题面，绝不包含 answer/solution）。"""
    _validate_item(item)
    return "\n".join(_PROMPT_LINES) + "\n" + item.stem


def parse_transcription(text):
    """VLM 回复文本 → {"steps": [{"text": str, "confidence": float}, ...], "final_answer": str | None}。"""
    if not isinstance(text, str):
        raise GradeError("transcription must be str")
    stripped = text.strip()
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start < 0 or end < start:
        raise GradeError("transcription contains no json object")
    payload = stripped[start : end + 1]
    try:
        data = json.loads(payload)
    except ValueError:
        raise GradeError("transcription is not valid json") from None
    if not isinstance(data, dict):
        raise GradeError("transcription json must be an object")
    raw_steps = data.get("steps")
    if not isinstance(raw_steps, list):
        raise GradeError("transcription must carry a steps list")
    steps = []
    for raw_step in raw_steps:
        if not isinstance(raw_step, dict):
            raise GradeError("each transcription step must be an object")
        if "text" not in raw_step or "confidence" not in raw_step:
            raise GradeError("each transcription step needs text and confidence")
        step_text = raw_step["text"]
        if not isinstance(step_text, str):
            raise GradeError("step text must be str")
        confidence = raw_step["confidence"]
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            raise GradeError("step confidence must be a finite number in [0, 1]")
        if isinstance(confidence, float) and not math.isfinite(confidence):
            raise GradeError("step confidence must be a finite number in [0, 1]")
        if not (0 <= confidence <= 1):
            raise GradeError("step confidence must be a finite number in [0, 1]")
        steps.append({"text": step_text, "confidence": float(confidence)})
    final_answer = data.get("final_answer")
    if final_answer is not None:
        if not isinstance(final_answer, str):
            raise GradeError("final_answer must be str or null")
        if not final_answer.strip():
            final_answer = None
    return {"steps": steps, "final_answer": final_answer}


@dataclass
class StepScore:
    """单个参考步骤的给分明细。"""

    index: int
    ref_text: str
    student_text: Optional[str]
    awarded: int

    def to_dict(self):
        return {
            "index": self.index,
            "ref_text": self.ref_text,
            "student_text": self.student_text,
            "awarded": self.awarded,
        }


@dataclass
class GradeSuggestion:
    """判分建议（分步给分 + 复核原因）。"""

    item_id: str
    steps: list
    max_points: int
    suggested_points: int
    final_answer: Optional[str]
    final_answer_correct: bool
    flagged_steps: list
    reasons: list
    needs_review: bool

    def to_dict(self):
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


def grade_solution(item, image, client, answer_grader, *, image_format="png", min_confidence=MIN_CONFIDENCE):
    """VLM 辅助判分管线：守卫 V1-V6 → 恰好一次 vision → 解析 → 恰好一次判定 → 冻结规则给分。"""
    vision_fn = getattr(client, "vision", None)
    if not callable(vision_fn):
        raise GradeError("client must expose a callable vision")
    if not callable(answer_grader):
        raise GradeError("answer_grader must be callable")
    if not isinstance(image, bytes) or not image:
        raise GradeError("image must be non-empty bytes")
    if image_format not in IMAGE_FORMATS:
        raise GradeError("image_format must be one of {}".format(IMAGE_FORMATS))
    if (
        isinstance(min_confidence, bool)
        or not isinstance(min_confidence, (int, float))
        or not math.isfinite(min_confidence)
        or not (0 <= min_confidence <= 1)
    ):
        raise GradeError("min_confidence must be a finite number in [0, 1]")
    _validate_item(item)

    prompt = build_grade_prompt(item)
    raw = vision_fn(prompt, [image], image_format=image_format)
    transcription = parse_transcription(raw)
    transcribed_steps = transcription["steps"]
    final_answer = transcription["final_answer"]

    verdict = answer_grader(item, final_answer)
    if not isinstance(verdict, bool):
        raise GradeError("answer_grader must return a bool")

    ref_steps = solution_steps(item.solution)
    flagged_steps = []
    trusted_steps = []
    for step in transcribed_steps:
        if step["confidence"] < min_confidence:
            flagged_steps.append(step["text"])
        else:
            trusted_steps.append(step["text"])

    used = [False] * len(trusted_steps)
    step_scores = []
    for index, ref_text in enumerate(ref_steps):
        matched = None
        for position, student_text in enumerate(trusted_steps):
            if not used[position] and steps_match(ref_text, student_text):
                matched = position
                break
        if matched is None:
            step_scores.append(StepScore(index=index, ref_text=ref_text, student_text=None, awarded=0))
        else:
            used[matched] = True
            step_scores.append(
                StepScore(index=index, ref_text=ref_text, student_text=trusted_steps[matched], awarded=1)
            )

    suggested_points = sum(step.awarded for step in step_scores)
    triggered = set()
    if flagged_steps:
        triggered.add(REASON_LOW_CONFIDENCE)
    if final_answer is None:
        triggered.add(REASON_FINAL_ANSWER_MISSING)
    if suggested_points < len(ref_steps):
        triggered.add(REASON_PARTIAL_MATCH)
    if suggested_points == len(ref_steps) and verdict is False:
        triggered.add(REASON_CONTRADICTION)
    reasons = [reason for reason in REVIEW_REASONS if reason in triggered]

    return GradeSuggestion(
        item_id=item.id,
        steps=step_scores,
        max_points=len(ref_steps),
        suggested_points=suggested_points,
        final_answer=final_answer,
        final_answer_correct=verdict,
        flagged_steps=flagged_steps,
        reasons=reasons,
        needs_review=bool(reasons),
    )


def _validate_suggestion(suggestion):
    """闭环两路共用的建议形状守卫：非空 str item_id + bool needs_review。"""
    item_id = getattr(suggestion, "item_id", None)
    if not isinstance(item_id, str) or not item_id:
        raise GradeError("suggestion.item_id must be a non-empty str")
    if not isinstance(getattr(suggestion, "needs_review", None), bool):
        raise GradeError("suggestion.needs_review must be bool")


def suggest_response(suggestion, response_ms=None):
    """干净建议（needs_review 为 False）→ Response(correct=True)。"""
    _validate_suggestion(suggestion)
    if suggestion.needs_review:
        raise GradeError("suggestion needs review; route it through confirm_review instead")
    return Response(
        item_id=suggestion.item_id,
        correct=True,
        learner_answer=getattr(suggestion, "final_answer", None),
        response_ms=response_ms,
    )


def confirm_review(suggestion, correct, learner_answer=None, response_ms=None):
    """需复核建议（needs_review 为 True）→ Response(correct=人审终审)。"""
    _validate_suggestion(suggestion)
    if not suggestion.needs_review:
        raise GradeError("suggestion is clean; route it through suggest_response instead")
    if not isinstance(correct, bool):
        raise GradeError("correct must be bool")
    if learner_answer is None:
        learner_answer = getattr(suggestion, "final_answer", None)
    return Response(
        item_id=suggestion.item_id,
        correct=correct,
        learner_answer=learner_answer,
        response_ms=response_ms,
    )
