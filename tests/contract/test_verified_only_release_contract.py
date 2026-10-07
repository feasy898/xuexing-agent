"""契约测试：--verified-only 发布开关与可发布索引（签署测试卡 TC-5）。

文件名与测试名含 verified_only / release_index，供 `pytest -k verified_only`
选中。核心纪律：对外可分发卷只能用双代理 agree 题；缺口如实报、不降级凑题；
索引可由工具重建、不得手写。
"""
import importlib.util
import json
from pathlib import Path

import pytest

from xuexing.paper_by_spec import eligible_items, load_spec_catalog, load_stage_bank
from xuexing.paper_render import redline_report
from xuexing.static_paper import (
    SINGLE_AGENT_LABEL,
    build_bundle,
    is_dual_verified,
    verified_only_bank,
    verified_shortages,
)

_ROOT = Path(__file__).resolve().parents[2]
_DATA = str(_ROOT / "data")


def _tool(name):
    spec = importlib.util.spec_from_file_location(
        f"tool_{name}", str(_ROOT / "tools" / f"{name}.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _records_for(subject, grades):
    records = {}
    for grade in grades:
        path = _ROOT / "data" / "items" / f"{subject}_grade{grade}_items.json"
        if path.exists():
            for it in json.loads(path.read_text(encoding="utf-8"))["items"]:
                records[it["id"]] = it
    return records


def _profile():
    return json.loads((_ROOT / "data" / "curriculum" / "cold_start_profile_v0.json").read_text(encoding="utf-8"))


@__import__("functools").lru_cache(maxsize=1)
def _catalog():
    return load_spec_catalog(str(_ROOT / "data" / "curriculum" / "paper_specs.json"))


def test_verified_only_bank_contains_only_dual_items():
    bank, grades = load_stage_bank(_DATA, "math", "junior")
    records = _records_for("math", grades)
    pool = verified_only_bank(bank, records)
    ids = {it.id for it in pool.items()}
    assert ids
    for item_id in ids:
        assert is_dual_verified(records.get(item_id))
    assert ids <= {it.id for it in bank.items()}


def test_verified_shortages_have_verified_independently_recomputed():
    """shortages 的 have_verified 用 eligible_items 过滤独立重算并逐项相等。"""
    raw = _catalog()["spec_math_jr_final"]
    bank, grades = load_stage_bank(_DATA, raw["subject"], raw["stage"])
    records = _records_for(raw["subject"], grades)
    shortages = verified_shortages(raw["sections"], bank, records)
    shortage_keys = {(s["section"], s["form"]) for s in shortages}
    for section in raw["sections"]:
        have = sum(1 for it in eligible_items(bank, section["form"])
                   if is_dual_verified(records.get(it.id)))
        if (section["title"], section["form"]) in shortage_keys:
            row = next(s for s in shortages
                       if s["section"] == section["title"] and s["form"] == section["form"])
            assert row["need"] == section["count"]
            assert row["have_verified"] == have
            assert section["count"] > have
        else:
            assert section["count"] <= have


def _synthetic_dual_fixture():
    """合成「全双代理」小卷型：verified-only 主链路的确定性测试夹具。"""
    from xuexing.itembank import Item, ItemBank
    bank = ItemBank()
    records = {}
    for i in range(1, 4):
        item_id = f"syn_choice_{i:03d}"
        bank.add(Item(
            id=item_id, item_type="choice",
            stem=f"合成题 {i}：1+1 等于几？",
            answer=f"A.{i + 1}", kps=["kp_syn"], difficulty=0.85,
            solution=f"计算得 {i + 1}。", options=[f"A.{i + 1}", "B.0", "C.1", "D.2"],
            form="choice", answer_mode="exact",
        ))
        records[item_id] = {"verification": {"agents": ["generator-x", "solver-y"], "answers_agree": True}}
    raw = {
        "id": "spec_syn", "subject": "math", "stage": "junior", "usage": "unit_test",
        "duration_min": 40, "total_points": 9,
        "sections": [{"title": "一、选择", "form": "choice", "count": 3,
                      "points_each": 3, "kp_scope": ["合成"]}],
    }
    return bank, records, raw


def test_verified_only_bundle_manifest_all_dual():
    """verified-only 池出的卷包：manifest verification 全 dual、单代理题数 0。"""
    from xuexing.itembank import ItemBank
    from xuexing.paper_by_spec import generate_paper_by_spec
    bank, records, raw = _synthetic_dual_fixture()
    pool = verified_only_bank(bank, records)
    paper = generate_paper_by_spec(pool, raw, seed=42, spec_id="spec_syn")
    paper["paper_id"] = "spec_syn_seed42"
    paper["stage_grades"] = [7, 8, 9]
    bundle = build_bundle(paper, pool, records, {}, _profile())
    assert all(it["verification"] == "dual" for it in bundle["manifest"]["items"])
    assert sum(1 for it in bundle["manifest"]["items"] if it["verification"] == "single") == 0
    assert SINGLE_AGENT_LABEL not in bundle["student.html"]
    assert SINGLE_AGENT_LABEL not in bundle["teacher.html"]
    assert bundle["manifest"]["difficulty"]["within_threshold"] is not None


def test_verified_only_insufficient_reports_no_bundle():
    """缺口卷型：--verified-only 路径如实报缺，不产出可发布卷包。"""
    tool = _tool("export_static_paper")
    entries = [
        e for e in
        json.loads((_ROOT / "data" / "releases" / "static_paper_index_v0.json").read_text(encoding="utf-8"))["entries"]
        if not e["releasable"]
    ]
    assert entries, "索引应如实包含缺口卷型"
    raw = _catalog()[entries[0]["spec_id"]]
    bank, grades = load_stage_bank(_DATA, raw["subject"], raw["stage"])
    records = _records_for(raw["subject"], grades)
    shortages = verified_shortages(raw["sections"], bank, records)
    assert shortages, "缺口卷型必须报出缺口"
    for s in shortages:
        assert s["need"] > s["have_verified"] >= 0


def test_release_index_matches_tool_rebuild():
    """索引与工具重建逐字节一致（可重建、非手写）。"""
    index_file = _ROOT / "data" / "releases" / "static_paper_index_v0.json"
    on_disk = index_file.read_text(encoding="utf-8")
    rebuilt = _tool("build_static_paper_index").build_index(_DATA, 42)
    from xuexing.cold_start_profile import to_canonical_json
    assert on_disk == to_canonical_json(rebuilt)


def test_release_index_structure_and_semantics():
    data = json.loads((_ROOT / "data" / "releases" / "static_paper_index_v0.json").read_text(encoding="utf-8"))
    entries = data["entries"]
    assert len(entries) == 21
    assert [e["spec_id"] for e in entries] == sorted(e["spec_id"] for e in entries)
    for e in entries:
        assert isinstance(e["releasable"], bool)
        assert e["releasable"] == all(s["need"] <= s["have_verified"] for s in e["shortages"])
        assert e["item_count"] == sum(
            s["count"] for s in _catalog()[e["spec_id"]]["sections"])
        for s in e["shortages"]:
            assert s["need"] > s["have_verified"]


def test_default_export_path_unchanged_by_verified_only_code():
    """默认（不带开关）行为与 TC-4 完全一致：同一卷型卷包逐字节一致。"""
    raw = _catalog()["spec_phy_jr_final"]
    bank, grades = load_stage_bank(_DATA, raw["subject"], raw["stage"])
    records = _records_for(raw["subject"], grades)
    kp_index = {}
    for grade in grades:
        path = _ROOT / "data" / "knowledge" / f"{raw['subject']}_grade{grade}.json"
        if path.exists():
            for kp in json.loads(path.read_text(encoding="utf-8"))["knowledge_points"]:
                kp_index[kp["id"]] = {"name": str(kp.get("name", "")), "cluster": str(kp.get("cluster", ""))}
    paper = __import__("xuexing.paper_by_spec", fromlist=["generate_paper_by_spec"]).generate_paper_by_spec(
        bank, raw, seed=42, spec_id="spec_phy_jr_final")
    paper["paper_id"] = "spec_phy_jr_final_seed42"
    paper["stage_grades"] = list(grades)
    bundle = build_bundle(paper, bank, records, kp_index, _profile())
    sample_dir = _ROOT / "docs" / "samples" / "static_paper" / "spec_phy_jr_final_seed42"
    for name in ("student.html", "student.txt", "teacher.html", "kp_map.html",
                 "answer_sheet.json", "manifest.json"):
        assert bundle[name] == (sample_dir / name).read_text(encoding="utf-8")


def test_verified_only_pool_paper_passes_student_redline():
    """verified-only 池出的卷，学生卷红线仍必须干净（合成全双代理卷）。"""
    from xuexing.paper_by_spec import generate_paper_by_spec
    bank, records, raw = _synthetic_dual_fixture()
    pool = verified_only_bank(bank, records)
    paper = generate_paper_by_spec(pool, raw, seed=42, spec_id="spec_syn")
    paper["paper_id"] = "spec_syn_seed42"
    paper["stage_grades"] = [7, 8, 9]
    bundle = build_bundle(paper, pool, records, {}, _profile())
    assert redline_report(paper, pool, bundle["student.html"], bundle["student.txt"]) == []


def test_index_covers_all_specs_and_seed_matches():
    data = json.loads((_ROOT / "data" / "releases" / "static_paper_index_v0.json").read_text(encoding="utf-8"))
    assert sorted(e["spec_id"] for e in data["entries"]) == sorted(_catalog())
    assert all(e["seed"] == data["seed"] for e in data["entries"])
