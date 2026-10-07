"""契约测试：static_paper（静态卷包，签署测试卡 TC-4）。

规格：specs/drafts/static_paper.spec.md。文件名含 static_paper，供
`pytest -k static_paper` 选中。21 套卷型参数化，逐套断言九点（a..i）：
a) 学生卷红线零违规；b) Σ题分==卷型总分；c) 题号五处一致；d) kp_map 逐题
KP 对应；e) 零外链/脚本/表单/iframe；f) 固定文案逐字在位且「真题」不出
文案外；g) 单代理标签与 releasable 联动；h) 同输入两次构建逐字节一致；
i) manifest.profile_version==画像版本。
"""
import glob
import json
import re
from functools import lru_cache
from pathlib import Path

import pytest

from xuexing.paper_by_spec import (
    generate_paper_by_spec,
    load_spec_catalog,
    load_stage_bank,
)
from xuexing.paper_render import human_paper_title, redline_report
from xuexing.static_paper import (
    AI_LABEL,
    MAX_BAND_DEVIATION,
    ORIGINAL_NOTICE,
    SINGLE_AGENT_LABEL,
    StaticPaperError,
    band_of,
    band_shares,
    build_bundle,
    is_dual_verified,
    target_mix_for_grades,
    verify_bundle,
)

_ROOT = Path(__file__).resolve().parents[2]
_DATA = str(_ROOT / "data")


@lru_cache(maxsize=1)
def _catalog():
    return load_spec_catalog(str(_ROOT / "data" / "curriculum" / "paper_specs.json"))


@lru_cache(maxsize=32)
def _context(subject, stage):
    bank, grades = load_stage_bank(_DATA, subject, stage)
    records = {}
    for grade in grades:
        path = _ROOT / "data" / "items" / f"{subject}_grade{grade}_items.json"
        if path.exists():
            for it in json.loads(path.read_text(encoding="utf-8"))["items"]:
                records[it["id"]] = it
    kp_index = {}
    for grade in grades:
        path = _ROOT / "data" / "knowledge" / f"{subject}_grade{grade}.json"
        if path.exists():
            for kp in json.loads(path.read_text(encoding="utf-8"))["knowledge_points"]:
                kp_index[kp["id"]] = {"name": str(kp.get("name", "")), "cluster": str(kp.get("cluster", ""))}
    return bank, tuple(grades), records, kp_index


@lru_cache(maxsize=1)
def _profile():
    return json.loads((_ROOT / "data" / "curriculum" / "cold_start_profile_v0.json").read_text(encoding="utf-8"))


def _build(spec_id, seed=42):
    raw = _catalog()[spec_id]
    bank, grades, records, kp_index = _context(raw["subject"], raw["stage"])
    paper = generate_paper_by_spec(bank, raw, seed=seed, spec_id=spec_id)
    paper["paper_id"] = f"{spec_id}_seed{seed}"
    paper["stage_grades"] = list(grades)
    bundle = build_bundle(paper, bank, records, kp_index, _profile())
    return paper, bank, bundle


def _spec_ids():
    return sorted(_catalog())


# ---------- 21 套卷型参数化：逐套断言九点 a..i ----------

@pytest.mark.parametrize("spec_id", _spec_ids())
def test_bundle_nine_points_a_to_i(spec_id):
    paper, bank, bundle = _build(spec_id)
    manifest = bundle["manifest"]
    flat = [q for sec in paper["sections"] for q in sec["questions"]]
    numbers = [q["question_no"] for q in flat]

    # a) 学生卷红线
    assert redline_report(paper, bank, bundle["student.html"], bundle["student.txt"]) == []
    # b) Σ题分 == 卷型总分
    assert sum(q["points"] for q in flat) == paper["total_points"]
    # c) 题号五处一致
    assert [it["no"] for it in manifest["items"]] == numbers == list(range(1, len(flat) + 1))
    sheet_numbers = [q["number"] for q in json.loads(bundle["answer_sheet.json"])["questions"]]
    assert sheet_numbers == numbers
    # d) kp_map 逐题 KP 对应（整表按行解析）
    rows = {int(m.group(1)): m.group(2) for m in re.finditer(
        r"<tr><td>(\d+)</td><td>[\d.]+</td><td>(.*?)</td></tr>", bundle["kp_map.html"], re.S)}
    for it in manifest["items"]:
        assert it["no"] in rows
        for kp_id in it["kps"]:
            assert kp_id in rows[it["no"]]
    # e) 零外链/脚本/表单/iframe
    for name in ("student.html", "teacher.html", "kp_map.html"):
        assert not re.search(r"https?://|<script[^>]*src=|<link[^>]*href=|<iframe|<form",
                             bundle[name], re.I), name
    # f) 固定文案逐字出现；「真题」只在固定文案里
    for name in ("student.html", "teacher.html"):
        assert AI_LABEL in bundle[name]
        assert ORIGINAL_NOTICE in bundle[name]
        assert bundle[name].count("真题") == bundle[name].count(ORIGINAL_NOTICE)
    # g) 单代理标签与 releasable 联动
    has_single = any(it["verification"] == "single" for it in manifest["items"])
    if has_single:
        assert SINGLE_AGENT_LABEL in bundle["student.html"]
        assert manifest["releasable"] is False
    else:
        assert SINGLE_AGENT_LABEL not in bundle["student.html"]
    # h) 同输入两次构建逐字节一致
    _, _, rebuild = _build(spec_id)
    for name in ("student.html", "student.txt", "teacher.html", "kp_map.html",
                 "answer_sheet.json", "manifest.json"):
        assert bundle[name] == rebuild[name], name
    # i) 画像版本
    assert manifest["profile_version"] == _profile()["profile_version"]
    # 总门：verify_bundle 零违规
    assert verify_bundle(bundle, paper, bank, _profile()) == []


# ---------- 冻结常量与单元行为 ----------

def test_labels_frozen_verbatim():
    assert AI_LABEL == "本卷题目由 AI 辅助生成并经校验"
    assert ORIGINAL_NOTICE == "题目为原创（含 AI 辅助生成并经校验），对齐课标与教材，非真题"
    assert SINGLE_AGENT_LABEL == "内部样卷·未完成双代理复验"
    assert MAX_BAND_DEVIATION == 0.15


def test_band_of_boundaries_and_error():
    assert band_of(1.0) == "basic" and band_of(0.75) == "basic"
    assert band_of(0.74) == "medium" and band_of(0.4) == "medium"
    assert band_of(0.39) == "hard" and band_of(0.0) == "hard"
    with pytest.raises(StaticPaperError):
        band_of(1.1)


def test_is_dual_verified_truth_table():
    assert is_dual_verified({"verification": {"agents": ["a", "b"], "answers_agree": True}})
    assert not is_dual_verified({"verification": {"agents": ["a"], "answers_agree": True}})
    assert not is_dual_verified({"verification": {"agents": ["a", "b"], "answers_agree": False}})
    assert not is_dual_verified({})
    assert not is_dual_verified(None)


def test_target_mix_is_stage_mean_and_fail_closed():
    profile = _profile()
    target = target_mix_for_grades(profile, "math", (7, 8, 9))
    assert abs(target["basic"] - 0.7) < 1e-9
    assert abs(sum(target.values()) - 1.0) < 1e-9
    with pytest.raises(StaticPaperError):
        target_mix_for_grades({"entries": {}}, "nosuch", (1, 2))


def test_band_shares_sum_to_one_and_empty_error():
    shares = band_shares({"basic": 7, "medium": 2, "hard": 1})
    assert abs(sum(shares.values()) - 1.0) < 1e-9
    with pytest.raises(StaticPaperError):
        band_shares({"basic": 0, "medium": 0, "hard": 0})


def test_missing_paper_id_fails_closed():
    raw = _catalog()["spec_phy_jr_final"]
    bank, grades, records, kp_index = _context(raw["subject"], raw["stage"])
    paper = generate_paper_by_spec(bank, raw, seed=42, spec_id="spec_phy_jr_final")
    paper["stage_grades"] = list(grades)
    with pytest.raises(StaticPaperError):
        build_bundle(paper, bank, records, kp_index, _profile())


def test_missing_stage_grades_fails_closed():
    raw = _catalog()["spec_phy_jr_final"]
    bank, grades, records, kp_index = _context(raw["subject"], raw["stage"])
    paper = generate_paper_by_spec(bank, raw, seed=42, spec_id="spec_phy_jr_final")
    paper["paper_id"] = "x"
    with pytest.raises(StaticPaperError):
        build_bundle(paper, bank, records, kp_index, _profile())


def test_missing_item_record_fails_closed():
    raw = _catalog()["spec_phy_jr_final"]
    bank, grades, records, kp_index = _context(raw["subject"], raw["stage"])
    paper = generate_paper_by_spec(bank, raw, seed=42, spec_id="spec_phy_jr_final")
    paper["paper_id"] = "x"
    paper["stage_grades"] = list(grades)
    with pytest.raises(StaticPaperError):
        build_bundle(paper, bank, {}, kp_index, _profile())


def test_missing_kp_index_renders_fallback_names():
    """kp_index 缺失不炸：kp_map 以 kp_id 兜底显示（名称缺失不算错误）。"""
    raw = _catalog()["spec_phy_jr_final"]
    bank, grades, records, kp_index = _context(raw["subject"], raw["stage"])
    paper = generate_paper_by_spec(bank, raw, seed=42, spec_id="spec_phy_jr_final")
    paper["paper_id"] = "x"
    paper["stage_grades"] = list(grades)
    bundle = build_bundle(paper, bank, records, {}, _profile())
    assert verify_bundle(bundle, paper, bank, _profile()) == []


# ---------- 样本卷（docs/samples，供 owner 视检）逐点复核 ----------

def test_committed_sample_bundle_matches_fresh_build():
    sample_dir = _ROOT / "docs" / "samples" / "static_paper" / "spec_phy_jr_final_seed42"
    assert sample_dir.is_dir()
    _, _, bundle = _build("spec_phy_jr_final", seed=42)
    for name in ("student.html", "student.txt", "teacher.html", "kp_map.html",
                 "answer_sheet.json", "manifest.json"):
        assert (sample_dir / name).read_text(encoding="utf-8") == bundle[name]


def test_sample_student_txt_head_carries_labels():
    text = (_ROOT / "docs" / "samples" / "static_paper" / "spec_phy_jr_final_seed42" / "student.txt").read_text(encoding="utf-8")
    assert text.startswith(AI_LABEL + "\n" + ORIGINAL_NOTICE + "\n" + SINGLE_AGENT_LABEL + "\n")


def test_sample_teacher_contains_answers_and_points():
    html = (_ROOT / "docs" / "samples" / "static_paper" / "spec_phy_jr_final_seed42" / "teacher.html").read_text(encoding="utf-8")
    assert "【答案】" in html
    assert "【解析】" in html
    title = re.search(r"<h1>(.*?) · 教师卷</h1>", html).group(1)
    assert "物理" in title


def test_sample_kp_map_has_self_check_template():
    html = (_ROOT / "docs" / "samples" / "static_paper" / "spec_phy_jr_final_seed42" / "kp_map.html").read_text(encoding="utf-8")
    assert "纸面自诊知识地图" in html
    assert "☐" in html
    assert "不联网、不回传" in html


def test_manifest_hash_and_releasable_fields():
    _, _, bundle = _build("spec_phy_jr_final")
    manifest = bundle["manifest"]
    import hashlib
    for name, sha in manifest["files"].items():
        assert hashlib.sha256(bundle[name].encode("utf-8")).hexdigest() == sha
    assert set(manifest["files"]) == {
        "student.html", "student.txt", "teacher.html", "kp_map.html", "answer_sheet.json"}
    assert manifest["releasable"] is False
    assert "单代理" in manifest["releasable_reason"]


def test_deviation_threshold_reflected_in_manifest():
    _, _, bundle = _build("spec_phy_jr_final")
    diff = bundle["manifest"]["difficulty"]
    assert diff["threshold"] == 0.15
    assert diff["within_threshold"] == (diff["max_deviation"] <= 0.15 + 1e-9)
    assert manifest_releasable_consistent(bundle["manifest"])


def manifest_releasable_consistent(manifest):
    has_single = any(it["verification"] == "single" for it in manifest["items"])
    return manifest["releasable"] == ((not has_single) and manifest["difficulty"]["within_threshold"])
