"""冷启动平均画像 v0（签署测试卡 TC-3，2026-10-08；裁定 D-5）。

静态分发没有学习者数据（owner 立项原话：静态卷「不清楚具体的学员消费
者，只能以平均画像去出」）。本模块用确定性规则构建「平均画像 v0」：

- 先验掌握度：纯规则赋值——本年级新学 KP 取 0.30，前序年级 KP 取 0.60
  （数值冻结于规格 specs/drafts/cold_start_profile.spec.md；学期参数 v0
  不区分：KP 无学期粒度标注）。
- 难度配比：默认 basic:medium:hard = 7:2:1，出处 docs/research/k12/
  hainan.md 中考节「基础:中等:较难≈7:2:1，难度系数 0.60–0.65」；卷型可
  覆盖（和仍须为 1）。
- 题目计量先验：difficulty_prior 取库内现有 difficulty（专家先验），
  calibration_source=expert_prior、calibrated=false——不伪造 IRT 参数，
  不宣称已校准。

红线：不使用任何真实学生数据；掌握度不由 LLM 产出（确定性规则输出）；
同一输入必须同一输出（逐字节可重建）。纯 stdlib，零网络。
"""
import json
import re

PROFILE_VERSION = "v0"
CALIBRATED = False
CALIBRATION_SOURCE = "expert_prior"

# 冻结数值（改值 = 改规格 + 留痕，见 specs/drafts/cold_start_profile.spec.md）
MASTERY_PRIOR_CURRENT_GRADE = 0.3
MASTERY_PRIOR_PREREQUISITE = 0.6
DEFAULT_DIFFICULTY_MIX = {"basic": 0.7, "medium": 0.2, "hard": 0.1}
DIFFICULTY_BANDS = {
    "basic": [0.75, 1.0],
    "medium": [0.4, 0.75],
    "hard": [0.0, 0.4],
}

PRIOR_RULE_NOTE = (
    "mastery_prior: current_grade=0.30, prerequisite_grade=0.60 "
    "(frozen v0; term not differentiated — KP has no term-level annotation)"
)
SOURCE_NOTE = (
    "cold-start average profile v0: deterministic rules only (Hainan "
    "7:2:1 difficulty mix, docs/research/k12/hainan.md); no learner data; "
    "not calibrated against real response data"
)

_ALLOWED_TERMS = (None, 1, 2)


class ColdStartProfileError(ValueError):
    """画像构建入参非法（年级不匹配 / 配比非法 / 学期未知）。"""


def to_canonical_json(obj) -> str:
    """规范 JSON 序列化：数据文件与重建结果逐字节一致的唯一口径。"""
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


_ENTRY_ID_RE = re.compile(r"^(?P<subject>[a-z]+)_grade(?P<grade>\d+)[a-z]*$")


def parse_entry_id(entry_id):
    """'math_grade7' / 'math_grade11b' -> ('math', 7/11)。

    年级数字后允许字母后缀（库内 math_grade11b/12b 为同年级补充 KP 文件，
    内部 KP grade 与数值年级一致）；其余格式抛 ColdStartProfileError。
    """
    m = _ENTRY_ID_RE.match(str(entry_id))
    if not m:
        raise ColdStartProfileError(f"bad entry id: {entry_id!r}")
    return m.group("subject"), int(m.group("grade"))


def build_entry(subject, grade, knowledge_points, term=None, difficulty_mix=None):
    """单学科×年级的画像条目（含学期可选参数，v0 不改变先验）。"""
    if term not in _ALLOWED_TERMS:
        raise ColdStartProfileError(f"term must be None|1|2, got {term!r}")
    mix = dict(DEFAULT_DIFFICULTY_MIX if difficulty_mix is None else difficulty_mix)
    if set(mix) != set(DEFAULT_DIFFICULTY_MIX):
        raise ColdStartProfileError(f"difficulty_mix keys must be basic/medium/hard, got {sorted(mix)}")
    if abs(sum(mix.values()) - 1.0) > 1e-9:
        raise ColdStartProfileError(f"difficulty_mix must sum to 1, got {mix}")
    kp_ids = []
    mastery_prior = {}
    for kp in knowledge_points:
        kp_id = kp["id"]
        if kp_id in mastery_prior:
            raise ColdStartProfileError(f"duplicate kp id: {kp_id}")
        kp_grade = int(kp.get("grade", grade))
        if kp_grade > int(grade):
            raise ColdStartProfileError(
                f"kp {kp_id} grade {kp_grade} ahead of entry grade {grade}"
            )
        prior = (
            MASTERY_PRIOR_CURRENT_GRADE
            if kp_grade == int(grade)
            else MASTERY_PRIOR_PREREQUISITE
        )
        kp_ids.append(kp_id)
        mastery_prior[kp_id] = prior
    return {
        "kp_ids": kp_ids,
        "mastery_prior": mastery_prior,
        "difficulty_mix": mix,
        "difficulty_bands": {k: list(v) for k, v in DIFFICULTY_BANDS.items()},
        "prior_rule": PRIOR_RULE_NOTE,
        "calibrated": CALIBRATED,
        "calibration_source": CALIBRATION_SOURCE,
    }


def build_profiles(knowledge_by_entry_id):
    """{entry_id: knowledge_points} -> 完整画像 dict（entries 键=文件 stem）。"""
    entries = {}
    for entry_id in sorted(knowledge_by_entry_id):
        subject, grade = parse_entry_id(entry_id)
        entries[entry_id] = build_entry(
            subject, grade, knowledge_by_entry_id[entry_id]
        )
    return {
        "profile_version": PROFILE_VERSION,
        "calibrated": CALIBRATED,
        "source_note": SOURCE_NOTE,
        "entries": entries,
    }


def build_item_priors(items):
    """题库 -> 题目计量先验 dict（difficulty_prior=库内 difficulty）。"""
    priors = {}
    for it in items:
        item_id = it["id"]
        if item_id in priors:
            raise ColdStartProfileError(f"duplicate item id: {item_id}")
        priors[item_id] = {
            "difficulty_prior": float(it["difficulty"]),
            "calibration_source": CALIBRATION_SOURCE,
            "calibrated": CALIBRATED,
        }
    return {
        "profile_version": PROFILE_VERSION,
        "calibrated": CALIBRATED,
        "source_note": SOURCE_NOTE,
        "items": priors,
    }
