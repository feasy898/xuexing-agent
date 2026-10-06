"""paper_by_spec —— 卷型库驱动的组卷（POST /papers/by-spec 的内核）。

消费 data/curriculum/paper_specs.json 卷型库（K12-4-w1，海南默认 profile）：
按卷型的学段（stage→年级文件范围）、题型（form→题库形态等价类）、分值
（count×points_each，且 V8 要求 Σ==total_points）约束，从既有题库选题并
装订成「大题-小题」层级卷面骨架。

复用冻结模块 xuexing.paper_spec：
- ``load_spec``：卷型 dict 的严格校验（任一违规——含 Σcount×points_each !=
  total_points——抛 PaperSpecError，**fail-closed**：不降级、不用别卷型凑）；
- ``score_blueprint``：把选出的题 id 序列装订成带小题号/分值/大题结构的骨架
  dict（全卷小题号连续、大题分值=Σ小题分值=total_points 由 V8 保证）。

题型等价类（FORM_ALIASES）：卷型 form 词表（choice/fill/solve/…）与题库
``Item.form`` 词表（mcq_single/单选/简答/…）不一致，此表声明「同一题型的
不同写法」。等价类以题面实况为准绳校准（如初中政治卷 form=comprehension
的题面即「结合材料，运用……」的材料分析题），**只做同型归并，不做跨型兜底**：
判断题不进选择题、默写不冒充填空、听力不足就报缺。凡卷型要求的题型在题库
中没有足够同型题，抛 PaperBySpecError 如实报缺。

form 缺失的题（Item.form 为 None/空白，如初中数学全库）按 item_type 粗类
（choice/fill/solve）回退；**有具体 form 的题一律不回退**——防止 form=判断
的题因 item_type=choice 而泄漏进选择题大题。

确定性：与 paper.generate_paper 同款规范性过程——单 random.Random(seed)、
候选按 (|难度-目标|, id) 排名、排名序前 2n 道进 shuffle、取前 n 道，同输入
同输出。

模块边界：选题与装订是纯函数（无 IO、无时钟、无全局状态）；题库文件与卷型
目录的装载是显式 IO 函数，供 server/tools 调用。
"""
from __future__ import annotations

import json
import os
import random

from xuexing.itembank import ItemBank, load_itembank
from xuexing.paper_spec import PaperSpec, PaperSpecError, load_spec, score_blueprint

__all__ = [
    "PaperBySpecError",
    "STAGE_GRADE_RANGE",
    "FORM_ALIASES",
    "FORM_TYPE_FALLBACK",
    "DEFAULT_CURRICULUM_DIR",
    "load_spec_catalog",
    "stage_item_paths",
    "load_stage_bank",
    "eligible_items",
    "select_items_for_spec",
    "generate_paper_by_spec",
]

DEFAULT_CURRICULUM_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
)


class PaperBySpecError(ValueError):
    """paper_by_spec 模块的组卷失败（题型无映射/同型题不足/学段无题库）。"""


# 卷型 stage -> 题库年级文件范围（含端点）。题库按 {subject}_grade{N}_items.json
# 组织，学段约束落地为「只装该年级区间内实际存在的文件」。
STAGE_GRADE_RANGE = {"primary": (1, 6), "junior": (7, 9), "high": (10, 12)}

# 题型等价类：卷型 form -> 题库 Item.form 的同型写法（精确匹配，strip 后比较）。
# 维护约定：新增等价类必须抽查题面实况确认同型（同型归并，不跨型兜底）。
FORM_ALIASES = {
    # 单选一族：mcq_single / choice / multiple_choice / 单选 均为四选一单选
    "choice": ("mcq_single", "choice", "multiple_choice", "单选"),
    "multi_select": ("mcq_multi",),
    "fill": ("fill", "fill_blank", "填空"),
    "truefalse": ("判断",),
    # 阅读理解/综合题一族：geography 的 comprehensive/map_reading 是读图综合，
    # politics 的 材料分析 同为材料作答
    "comprehension": ("comprehension", "reading", "comprehensive", "map_reading", "材料分析"),
    "cloze": ("cloze",),
    "essay": ("essay", "writing", "open_write", "narrative"),
    "writing": ("writing", "open_write", "essay", "continuation"),
    "listening": ("listening",),
    "reading": ("reading",),
    "match": ("matching", "connection"),
    "observe": ("observe", "observation", "观察"),
    "experiment": ("experiment",),
    "process_flow": ("process_flow",),
    "proof": ("proof",),
    "seven_to_five": ("seven_to_five_sequence",),
    "summary": ("summary", "概要写作"),
    # 解答/简答/论述/材料分析同为主观测答；politics 高考卷 form=comprehension
    # 的题面即「结合材料，运用……」材料分析（实况校准 2026-10-06）
    "solve": ("solve", "short_answer", "简答", "论述", "材料分析", "comprehension"),
    "computation": ("computation", "calculation"),
    "word_problem": ("word_problem",),
    "construction": ("construction", "drawing", "diagram"),
    "synthesis": ("synthesis",),
}

# form 缺失（None/空白）时的 item_type 粗类回退。**只对无 form 的题生效**：
# 有具体 form 的题必须命中 FORM_ALIASES，否则视为不同型（防判断题冒充选择题）。
# 压轴/应用/计算解答在卷面上都是解答题族；作文/判断/作图无粗类对应，不回退。
FORM_TYPE_FALLBACK = {
    "choice": ("choice",),
    "fill": ("fill",),
    "solve": ("solve",),
    "computation": ("solve",),
    "word_problem": ("solve",),
    "synthesis": ("solve",),
}


def load_spec_catalog(path: str) -> dict:
    """卷型库 JSON -> {spec_id: 原始卷型 dict}。重 id / id 非非空白 str 抛
    PaperBySpecError（fail-closed：宁可拒绝装载也不静默吞卷型）。"""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    specs = data.get("specs") if isinstance(data, dict) else None
    if not isinstance(specs, list) or not specs:
        raise PaperBySpecError(f"spec catalog must be a dict with non-empty 'specs' list, got {data!r}")
    catalog: dict = {}
    for raw in specs:
        if not isinstance(raw, dict):
            raise PaperBySpecError(f"spec catalog entries must be dicts, got {raw!r}")
        spec_id = raw.get("id")
        if not isinstance(spec_id, str) or not spec_id.strip():
            raise PaperBySpecError(f"spec id must be a non-blank str, got {spec_id!r}")
        if spec_id in catalog:
            raise PaperBySpecError(f"duplicate spec id in catalog: {spec_id}")
        catalog[spec_id] = raw
    return catalog


def stage_item_paths(data_dir: str, subject: str, stage: str) -> list:
    """学段约束的题库文件列表（data_dir/items/{subject}_grade{N}_items.json，
    N ∈ stage 年级区间且文件实际存在，按年级升序）。stage 未知抛 PaperBySpecError。"""
    if stage not in STAGE_GRADE_RANGE:
        raise PaperBySpecError(
            f"unknown stage {stage!r}: expected one of {sorted(STAGE_GRADE_RANGE)}"
        )
    lo, hi = STAGE_GRADE_RANGE[stage]
    paths = []
    for grade in range(lo, hi + 1):
        p = os.path.join(data_dir, "items", f"{subject}_grade{grade}_items.json")
        if os.path.exists(p):
            paths.append(p)
    return paths


def load_stage_bank(data_dir: str, subject: str, stage: str):
    """装载学段题库：合并年级区间内各文件 -> (ItemBank, 实际装载的年级 tuple)。
    区间内一个题库文件都没有 → PaperBySpecError（如实报缺，不拿别的学段凑）。"""
    paths = stage_item_paths(data_dir, subject, stage)
    if not paths:
        raise PaperBySpecError(
            f"no item files for subject={subject} stage={stage} "
            f"(grades {STAGE_GRADE_RANGE[stage][0]}-{STAGE_GRADE_RANGE[stage][1]}) in {data_dir}"
        )
    bank = ItemBank()
    for p in paths:
        for item in load_itembank(p).items():
            bank.add(item)  # 跨文件重 id 由 ItemBank.add 的查重兜住
    # 文件名形如 {subject}_grade{N}_items.json；按年级数字升序返回
    grades = tuple(
        int(os.path.basename(p).split("_grade")[1].split("_")[0]) for p in paths
    )
    return bank, grades


def _item_form(item) -> str:
    form = getattr(item, "form", None)
    return form.strip() if isinstance(form, str) else ""


def matches_form(item, form: str) -> bool:
    """单题与卷型 form 的同型判定：有具体 form 必须命中等价类；无 form 按
    item_type 粗类回退；等价类未收录的卷型 form 一律 False（调用方报缺）。"""
    aliases = FORM_ALIASES.get(form)
    if aliases is None:
        return False
    concrete = _item_form(item)
    if concrete:
        return concrete in aliases
    return getattr(item, "item_type", "") in FORM_TYPE_FALLBACK.get(form, ())


def eligible_items(bank, form: str) -> list:
    """题库中与卷型 form 同型的题（id 升序）。form 未收录等价类 → 空表
    （调用方以「无题型映射」报缺，不静默当 0 题处理）。"""
    if form not in FORM_ALIASES:
        return []
    return [item for item in bank.items() if matches_form(item, form)]


def select_items_for_spec(bank, spec: PaperSpec, seed: int = 42,
                          difficulty_target: float = 0.5) -> list:
    """按卷型逐大题选题：同型、未被他大题占用、难度最接近目标。
    规范性过程与 paper.generate_paper 一致（候选 (|难度-目标|, id) 排名，
    排名序前 2n 道进 shuffle，取前 n 道按 id 升序返回）；全卷共用一个
    random.Random(seed)，大题按 sections 顺序消费随机流——同输入同输出。
    任何大题同型题不足（含题型无映射）抛 PaperBySpecError，**fail-closed**：
    不返回部分结果，不用别的题型凑数。"""
    if not 0.0 <= difficulty_target <= 1.0:
        raise PaperBySpecError(f"difficulty_target out of range: {difficulty_target}")
    rng = random.Random(seed)
    used: set = set()
    picked: list = []
    for no, section in enumerate(spec.sections, start=1):
        if section.form not in FORM_ALIASES:
            raise PaperBySpecError(
                f"section {no} ({section.title!r}): form {section.form!r} has no bank form mapping"
            )
        candidates = [
            item for item in eligible_items(bank, section.form) if item.id not in used
        ]
        if len(candidates) < section.count:
            raise PaperBySpecError(
                f"section {no} ({section.title!r}, form={section.form}): not enough eligible items: "
                f"need {section.count}, have {len(candidates)}"
            )
        ranked = sorted(
            candidates, key=lambda it: (abs(it.difficulty - difficulty_target), it.id)
        )
        pool = ranked[: max(section.count * 2, section.count)]
        rng.shuffle(pool)
        chosen = sorted(pool[: section.count], key=lambda it: it.id)
        picked.extend(item.id for item in chosen)
        used.update(item.id for item in chosen)
    return picked


def generate_paper_by_spec(bank, spec_data: dict, seed: int = 42,
                           difficulty_target: float = 0.5,
                           spec_id: str = "") -> dict:
    """卷型 dict -> 完整卷面结构（组卷总入口）。

    流程：load_spec 严格校验（内部不一致如 Σ分值 != total_points 在此
    fail-closed）→ select_items_for_spec 逐大题同型选题 → score_blueprint
    装订「大题-小题」层级（小题号全卷连续、分值逐题落位）。返回骨架 dict
    追加 spec_id / seed / difficulty_target / item_ids（平铺题序，便于客户端
    取题面）。html/文本渲染不在本模块（后置）。
    """
    spec = load_spec(spec_data)  # PaperSpecError（ValueError 子类）直接上抛
    item_ids = select_items_for_spec(bank, spec, seed=seed,
                                     difficulty_target=difficulty_target)
    skeleton = score_blueprint(spec, item_ids)
    sid = spec_id or (spec_data.get("id") if isinstance(spec_data, dict) else "")
    out = {"spec_id": sid, "seed": seed, "difficulty_target": difficulty_target}
    out.update(skeleton)
    out["item_ids"] = list(item_ids)
    return out
