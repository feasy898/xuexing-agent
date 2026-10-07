"""契约测试：cold_start_profile（冷启动平均画像 v0，签署测试卡 TC-3）。

规格：specs/drafts/cold_start_profile.spec.md（不变量 I1..I12 逐条锁定）。
文件名含 cold_start_profile，供 `pytest -k cold_start_profile` 选中。
"""
import glob
import importlib
import json
import os
import re
from pathlib import Path

import pytest

from xuexing import cold_start_profile as csp
from xuexing.cold_start_profile import ColdStartProfileError

_ROOT = Path(__file__).resolve().parents[2]
PROFILE_FILE = _ROOT / "data" / "curriculum" / "cold_start_profile_v0.json"
PRIORS_FILE = _ROOT / "data" / "curriculum" / "item_difficulty_prior_v0.json"


def _knowledge_files():
    """{文件 stem: knowledge_points}，覆盖 data/knowledge/*_grade*.json。"""
    out = {}
    for path in sorted(glob.glob(str(_ROOT / "data" / "knowledge" / "*_grade*.json"))):
        with open(path, encoding="utf-8") as f:
            out[Path(path).stem] = json.load(f)["knowledge_points"]
    return out


def _all_items():
    items = []
    for path in sorted(glob.glob(str(_ROOT / "data" / "items" / "*_items.json"))):
        with open(path, encoding="utf-8") as f:
            items.extend(json.load(f)["items"])
    return items


def _sample_kps():
    return [
        {"id": "p_g1", "grade": 1},
        {"id": "p_g2", "grade": 2},
        {"id": "p_g3", "grade": 3},
    ]


# ---------- I1 确定性 ----------

def test_i1_deterministic_same_input_same_bytes():
    a = csp.to_canonical_json(csp.build_entry("math", 3, _sample_kps()))
    b = csp.to_canonical_json(csp.build_entry("math", 3, _sample_kps()))
    assert a == b


# ---------- I2/I3 kp_ids 与先验赋值 ----------

def test_i2_i3_entry_structure_and_prior_rule():
    entry = csp.build_entry("math", 3, _sample_kps())
    assert entry["kp_ids"] == ["p_g1", "p_g2", "p_g3"]
    assert entry["mastery_prior"] == {
        "p_g1": csp.MASTERY_PRIOR_PREREQUISITE,
        "p_g2": csp.MASTERY_PRIOR_PREREQUISITE,
        "p_g3": csp.MASTERY_PRIOR_CURRENT_GRADE,
    }
    assert all(0.0 <= v <= 1.0 for v in entry["mastery_prior"].values())


# ---------- I4 默认难度配比 7:2:1 ----------

def test_i4_default_difficulty_mix_is_hainan_721():
    entry = csp.build_entry("math", 3, _sample_kps())
    assert entry["difficulty_mix"] == {"basic": 0.7, "medium": 0.2, "hard": 0.1}
    assert abs(sum(entry["difficulty_mix"].values()) - 1.0) < 1e-9


def test_i4_mix_override_keeps_sum_gate():
    overridden = csp.build_entry(
        "math", 3, _sample_kps(),
        difficulty_mix={"basic": 0.5, "medium": 0.3, "hard": 0.2},
    )
    assert abs(sum(overridden["difficulty_mix"].values()) - 1.0) < 1e-9
    with pytest.raises(ColdStartProfileError):
        csp.build_entry("math", 3, _sample_kps(),
                        difficulty_mix={"basic": 0.5, "medium": 0.5, "hard": 0.5})


# ---------- I5 难度带三档衔接 ----------

def test_i5_bands_three_tiers_within_unit_interval():
    bands = csp.build_entry("math", 3, _sample_kps())["difficulty_bands"]
    assert set(bands) == {"basic", "medium", "hard"}
    edges = sorted((v[0], v[1]) for v in bands.values())
    assert edges[0][0] == 0.0 and edges[-1][1] == 1.0
    for (lo_a, hi_a), (lo_b, _) in zip(edges, edges[1:]):
        assert abs(hi_a - lo_b) < 1e-9


# ---------- I6 纯净性 ----------

def test_i6_no_forbidden_imports_no_network_no_learner_fields():
    src = (_ROOT / "src" / "xuexing" / "cold_start_profile.py").read_text(encoding="utf-8")
    forbidden = re.findall(
        r"^\s*(?:import|from)\s+(?:urllib|http|socket|requests|random|datetime|"
        r"xuexing\.mm_|xuexing\.agent_shell)",
        src, re.M,
    )
    assert forbidden == []
    blob = csp.to_canonical_json(csp.build_profiles({"math_grade3": _sample_kps()}))
    # 不得出现学习者/学生数据「字段」（键名级检查；source_note 说明文字不算）
    assert not re.search(r'"[a-z_]*(?:learner|student)[a-z_]*"\s*:', blob)


# ---------- I7 覆盖全部知识文件 ----------

def test_i7_profile_covers_all_knowledge_files():
    profile = json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
    files = _knowledge_files()
    assert set(profile["entries"]) == set(files)
    assert len(files) == 82


# ---------- I8 题目先验覆盖与诚实标注 ----------

def test_i8_item_priors_match_bank():
    priors = json.loads(PRIORS_FILE.read_text(encoding="utf-8"))["items"]
    bank = {it["id"]: it for it in _all_items()}
    assert set(priors) == set(bank)
    for item_id, prior in priors.items():
        assert prior["calibrated"] is False
        assert prior["calibration_source"] == "expert_prior"
        assert abs(prior["difficulty_prior"] - float(bank[item_id]["difficulty"])) < 1e-9


# ---------- I9 数据文件逐字节可重建 ----------

def test_i9_profile_file_byte_identical_rebuild():
    profile = csp.build_profiles(
        {stem: kps for stem, kps in _knowledge_files().items()}
    )
    assert csp.to_canonical_json(profile) == PROFILE_FILE.read_text(encoding="utf-8")


def test_i9_priors_file_byte_identical_rebuild():
    priors = csp.build_item_priors(_all_items())
    assert csp.to_canonical_json(priors) == PRIORS_FILE.read_text(encoding="utf-8")


# ---------- I10 版本与诚实标注 ----------

def test_i10_version_and_uncalibrated_flags():
    profile = json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
    assert profile["profile_version"] == "v0"
    assert profile["calibrated"] is False
    for entry in profile["entries"].values():
        assert entry["calibrated"] is False
        assert entry["calibration_source"] == "expert_prior"


# ---------- I11 错误行为 fail-closed ----------

def test_i11_errors_on_bad_inputs():
    with pytest.raises(ColdStartProfileError):
        csp.build_entry("math", 2, [{"id": "ahead", "grade": 3}])
    with pytest.raises(ColdStartProfileError):
        csp.build_entry("math", 3, _sample_kps(), term=7)
    with pytest.raises(ColdStartProfileError):
        csp.build_entry("math", 3, _sample_kps(),
                        difficulty_mix={"basic": 0.9, "medium": 0.2, "hard": 0.1})
    with pytest.raises(ColdStartProfileError):
        csp.parse_entry_id("math_grade_seven")
    with pytest.raises(ColdStartProfileError):
        csp.build_item_priors([{"id": "x", "difficulty": 0.5},
                               {"id": "x", "difficulty": 0.6}])


# ---------- I12 附加式：零内核依赖 ----------

def test_i12_no_internal_kernel_imports():
    src = (_ROOT / "src" / "xuexing" / "cold_start_profile.py").read_text(encoding="utf-8")
    assert not re.findall(r"^\s*from\s+xuexing(\.[a-z_]+)?\s+import", src, re.M)
    frozen_dir = _ROOT / "specs" / "frozen"
    assert not list(frozen_dir.glob("cold_start_profile*")), (
        "cold_start_profile 尚为 draft，不得出现冻结契约"
    )


# ---------- 学期参数 v0 语义（规格 §4） ----------

def test_term_accepts_none_one_two_only():
    for term in (None, 1, 2):
        csp.build_entry("math", 3, _sample_kps(), term=term)


def test_parse_entry_id_accepts_letter_suffixed_stems():
    assert csp.parse_entry_id("math_grade7") == ("math", 7)
    assert csp.parse_entry_id("math_grade11b") == ("math", 11)
    with pytest.raises(ColdStartProfileError):
        csp.parse_entry_id("math_grade_seven")


def test_spec_draft_exists_and_declares_invariants():
    spec = (_ROOT / "specs" / "drafts" / "cold_start_profile.spec.md").read_text(encoding="utf-8")
    for i in range(1, 13):
        assert f"I{i}" in spec
