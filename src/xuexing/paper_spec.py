"""paper_spec —— 卷型定义与校验（冻结契约：specs/frozen/paper_spec.spec.md）。

卷型（PaperSpec）是组卷蓝图的**声明式规格**：一份 dict 描述科目/学段/用途/时长/
总分与若干大题（section：标题、题型形态、题数、每题分值，可选难度带与知识点范围）。
本模块提供两个纯函数：

- ``load_spec(data)``：dict -> PaperSpec，逐字段严格校验（sections 非空、form
  非空、count >= 1、points_each > 0、Σ count×points_each == total_points、
  duration_min > 0），任一条失败抛 ``PaperSpecError``；
- ``score_blueprint(spec, paper_item_ids)``：把题 id 序列按 section 顺序装订成
  带小题号/分值/大题结构的卷面骨架 dict（题数不足或超出抛 PaperSpecError）。

与冻结模块 paper_layout 的分工（冻结）：paper_layout 消费 paper.generate_paper 的
Paper 对象做打印排版；本模块面向**规格声明与装订骨架**，不渲染、不组卷、不判分。

模块纯度：无 IO、无随机、无时钟、不读环境、无全局可变状态；不改任何入参
（输出全量新构造，回显的可选字段为拷贝、不与 spec 别名）；同输入同输出。

装载约束（与仓库其他冻结模块一致）：本文件可被 spec_from_file_location 以顶层
模块名 ``_regen_paper_spec`` 装载并顶替 sys.modules["xuexing.paper_spec"]，因此
不使用 ``from __future__ import annotations``、不使用相对导入，注解直接写真实
对象；零 xuexing 依赖（不 import 任何同包模块，也不需要 xuexing.types）。
"""

import math
from dataclasses import dataclass

__all__ = [
    "PaperSpecError",
    "SectionSpec",
    "PaperSpec",
    "load_spec",
    "score_blueprint",
]


class PaperSpecError(ValueError):
    """paper_spec 模块所有校验失败的异常类型（ValueError 直接子类）。"""


@dataclass(frozen=True)
class SectionSpec:
    """大题规格。可选字段缺失时为 None；difficulty_band 存 (lo, hi) 二元 tuple，
    kp_scope 存 str tuple（不可变快照，防调用方事后改动泄漏进卷型）。"""

    title: str
    form: str
    count: int
    points_each: float  # 实际接受 int|float（bool 一律拒绝）
    difficulty_band: tuple | None = None
    kp_scope: tuple | None = None


@dataclass(frozen=True)
class PaperSpec:
    """卷型。sections 为 SectionSpec tuple（不可变，保序）。"""

    subject: str
    stage: str
    usage: str
    duration_min: int
    total_points: float  # 实际接受 int|float
    sections: tuple


def _is_number(value):
    # bool 是 int 子类，一律按非数字拒绝；NaN/inf 同样拒绝（math.isfinite）。
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _is_nonblank_str(value):
    return isinstance(value, str) and value.strip() != ""


def _is_int(value):
    # bool 是 int 子类，规格一律按非 int 拒绝
    return isinstance(value, int) and not isinstance(value, bool)


def _check_difficulty_band(value, where, errors):
    """难度带：list/tuple、恰 2 个有限实数元素、0 <= lo <= hi <= 1。"""
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        errors.append(f"{where}.difficulty_band must be a pair of numbers with "
                      f"0 <= lo <= hi <= 1, got {value!r}")
        return
    lo, hi = value
    if not (_is_number(lo) and _is_number(hi) and 0 <= lo <= hi <= 1):
        errors.append(f"{where}.difficulty_band must be a pair of numbers with "
                      f"0 <= lo <= hi <= 1, got {value!r}")


def _check_kp_scope(value, where, errors):
    """知识点范围：非空 list、元素全为 strip 后非空的 str。"""
    if not isinstance(value, list) or not value:
        errors.append(f"{where}.kp_scope must be a non-empty list of non-blank str, got {value!r}")
        return
    for el in value:
        if not _is_nonblank_str(el):
            errors.append(
                f"{where}.kp_scope must be a non-empty list of non-blank str, got {value!r}"
            )
            return


def _check_section(raw, index, errors):
    """单节校验（累积该节全部消息；节级消息按 title→form→count→points_each→
    difficulty_band→kp_scope 固定序）。多出键一律忽略（前向兼容，与 paper_layout
    冻结规格的节 dict 语义一致）。"""
    where = f"spec.sections[{index}]"
    if not isinstance(raw, dict):
        errors.append(f"{where} must be a dict, got {raw!r}")
        return
    title = raw.get("title")
    if not _is_nonblank_str(title):
        errors.append(f"{where}.title must be a non-blank str, got {title!r}")
    form = raw.get("form")
    if not _is_nonblank_str(form):
        errors.append(f"{where}.form must be a non-blank str, got {form!r}")
    count = raw.get("count")
    if not (_is_int(count) and count >= 1):
        errors.append(f"{where}.count must be an int >= 1, got {count!r}")
    points_each = raw.get("points_each")
    if not (_is_number(points_each) and points_each > 0):
        errors.append(f"{where}.points_each must be a number > 0, got {points_each!r}")
    if "difficulty_band" in raw:
        _check_difficulty_band(raw["difficulty_band"], where, errors)
    if "kp_scope" in raw:
        _check_kp_scope(raw["kp_scope"], where, errors)


def load_spec(data) -> PaperSpec:
    """dict -> PaperSpec。校验顺序 V1→V8 冻结，**先累积全部消息再抛**（一次看全），
    全部通过才构造并返回 PaperSpec。任一失败抛 PaperSpecError（消息含全部违规）。"""
    errors = []
    if not isinstance(data, dict):
        raise PaperSpecError(f"spec must be a dict, got {data!r}")
    subject = data.get("subject")
    if not _is_nonblank_str(subject):
        errors.append(f"spec.subject must be a non-blank str, got {subject!r}")
    stage = data.get("stage")
    if not _is_nonblank_str(stage):
        errors.append(f"spec.stage must be a non-blank str, got {stage!r}")
    usage = data.get("usage")
    if not _is_nonblank_str(usage):
        errors.append(f"spec.usage must be a non-blank str, got {usage!r}")
    duration_min = data.get("duration_min")
    if not (_is_int(duration_min) and duration_min > 0):
        errors.append(f"spec.duration_min must be an int > 0, got {duration_min!r}")
    total_points = data.get("total_points")
    if not (_is_number(total_points) and total_points > 0):
        errors.append(f"spec.total_points must be a number > 0, got {total_points!r}")
    sections = data.get("sections")
    if not isinstance(sections, list) or not sections:
        errors.append(f"spec.sections must be a non-empty list, got {sections!r}")
        sections = []
    for index, raw in enumerate(sections, start=1):
        _check_section(raw, index, errors)
    # V8 总分一致性：Σ count×points_each 与 total_points 精确相等。仅当 sections
    # 为非空 list 且节级字段全部合法（每节 count 为 int>=1 且 points_each 为
    # number>0）时才评估——有非法分量或 sections 本身非法则跳过（消息已由节级
    # 校验报出，不重复报和）。
    if (
        _is_number(total_points)
        and total_points > 0
        and sections
        and all(
            isinstance(raw, dict)
            and _is_int(raw.get("count"))
            and raw["count"] >= 1
            and _is_number(raw.get("points_each"))
            and raw["points_each"] > 0
            for raw in sections
        )
    ):
        points_sum = sum(raw["count"] * raw["points_each"] for raw in sections)
        if points_sum != total_points:
            errors.append(
                f"spec sections points sum {points_sum!r} != total_points {total_points!r}"
            )
    if errors:
        raise PaperSpecError("; ".join(errors))
    return PaperSpec(
        subject=subject,
        stage=stage,
        usage=usage,
        duration_min=duration_min,
        total_points=total_points,
        sections=tuple(
            SectionSpec(
                title=raw["title"],
                form=raw["form"],
                count=raw["count"],
                points_each=raw["points_each"],
                difficulty_band=(
                    tuple(raw["difficulty_band"]) if "difficulty_band" in raw else None
                ),
                kp_scope=tuple(raw["kp_scope"]) if "kp_scope" in raw else None,
            )
            for raw in sections
        ),
    )


def score_blueprint(spec, paper_item_ids) -> dict:
    """PaperSpec + 题 id 序列 -> 卷面骨架 dict（装订，不判分不渲染）。

    装订闭式：大题按 sections 顺序编号（section_no 从 1 起）；第 i 大题依次消费
    其 count 个题 id；小题号（question_no）**全卷连续**从 1 起；每题分值恒为该
    大题 points_each；大题分值 section_points = count × points_each。spec 中该节
    设置了可选字段时，骨架中以拷贝回显 difficulty_band（list）/ kp_scope（list）。

    错误时机（均抛 PaperSpecError）：spec 非 PaperSpec 实例；paper_item_ids 非
    list/tuple；元素非 strip 后非空的 str（首个坏元素即抛）；题数与 Σ count 不相等
    （不足/超出分别报）。
    """
    if not isinstance(spec, PaperSpec):
        raise PaperSpecError(f"score_blueprint: spec must be a PaperSpec, got {spec!r}")
    if not isinstance(paper_item_ids, (list, tuple)):
        raise PaperSpecError(f"paper_item_ids must be a list or tuple, got {paper_item_ids!r}")
    for iid in paper_item_ids:
        if not _is_nonblank_str(iid):
            raise PaperSpecError(f"paper_item_ids elements must be non-blank str, got {iid!r}")
    needed = sum(section.count for section in spec.sections)
    if len(paper_item_ids) < needed:
        raise PaperSpecError(f"paper_item_ids too few: need {needed}, got {len(paper_item_ids)}")
    if len(paper_item_ids) > needed:
        raise PaperSpecError(f"paper_item_ids too many: need {needed}, got {len(paper_item_ids)}")

    out_sections = []
    question_no = 0
    cursor = 0
    for section_no, section in enumerate(spec.sections, start=1):
        questions = []
        for _ in range(section.count):
            question_no += 1
            questions.append({
                "question_no": question_no,
                "item_id": paper_item_ids[cursor],
                "points": section.points_each,
            })
            cursor += 1
        block = {
            "section_no": section_no,
            "title": section.title,
            "form": section.form,
            "count": section.count,
            "points_each": section.points_each,
            "section_points": section.count * section.points_each,
            "questions": questions,
        }
        if section.difficulty_band is not None:
            block["difficulty_band"] = list(section.difficulty_band)
        if section.kp_scope is not None:
            block["kp_scope"] = list(section.kp_scope)
        out_sections.append(block)

    return {
        "subject": spec.subject,
        "stage": spec.stage,
        "usage": spec.usage,
        "duration_min": spec.duration_min,
        "total_points": spec.total_points,
        "question_count": needed,
        "sections": out_sections,
    }
