"""数据测试：学科「不开设年级」声明（签署测试卡 TC-1，2026-10-08）。

锁定三件事（裁定 D-4③：地理 grade9 属年级配置错位，不是内容缺口）：
1. 真实库下 geography 无 pending（grade9 由 SUBJECT_GRADES_NOT_OFFERED
   声明为不开设，依据 docs/research/k12/geography.md 与 hainan.md）；
2. fail-closed：数据侧一旦出现 geography_grade9 文件（tmp_path 副本注入
   验证，不触碰真实 data/），validate 必须报错；
3. 其他学科语义一字不变：math 7-9 缺位仍报错；biology 档内缺 9 仍 pending。

测试文件名含 grade_not_offered，供 `pytest -k grade_not_offered` 选中。
"""
import glob
import importlib.util
import json
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]


def _load_vk():
    """按文件路径加载 tools/validate_knowledge.py（不依赖包导入路径）。"""
    spec = importlib.util.spec_from_file_location(
        "validate_knowledge_tc1", str(_ROOT / "tools" / "validate_knowledge.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_declaration_freezes_geography_nine_only():
    vk = _load_vk()
    assert vk.SUBJECT_GRADES_NOT_OFFERED == {"geography": (9,)}


def test_real_bank_geography_no_pending_and_no_grade9_files():
    vk = _load_vk()
    grade_paths = vk._discover_subjects(
        vk.KNOWLEDGE_DIR, vk.SUBJECT_KNOWLEDGE_RE
    )["geography"]
    errors: list[str] = []
    pending = vk._validate_subject_grades("geography", grade_paths, errors)
    assert errors == []
    assert pending == [], f"geography 不应再有 pending 缺档: {pending}"
    for directory in (vk.KNOWLEDGE_DIR, vk.ITEMS_DIR, vk.MC_DIR, vk.ARCH_DIR):
        hits = glob.glob(os.path.join(directory, "geography_grade9*.json"))
        assert hits == [], f"真实库不得存在 geography_grade9 文件: {hits}"


def test_injected_geography_grade9_fails_closed(tmp_path, monkeypatch, capsys):
    vk = _load_vk()
    kdir = tmp_path / "knowledge"
    kdir.mkdir()
    for name in ("items", "misconceptions", "archetypes"):
        (tmp_path / name).mkdir()
    for g in (7, 8, 10, 11, 12):
        (kdir / f"geography_grade{g}.json").write_text(
            json.dumps({"knowledge_points": []}), encoding="utf-8"
        )
    (kdir / "geography_grade9.json").write_text(
        json.dumps({"knowledge_points": []}), encoding="utf-8"
    )
    monkeypatch.setattr(vk, "KNOWLEDGE_DIR", str(kdir))
    monkeypatch.setattr(vk, "ITEMS_DIR", str(tmp_path / "items"))
    monkeypatch.setattr(vk, "MC_DIR", str(tmp_path / "misconceptions"))
    monkeypatch.setattr(vk, "ARCH_DIR", str(tmp_path / "archetypes"))
    monkeypatch.setattr(sys, "argv", ["validate_knowledge.py"])
    rc = vk.main()
    out = capsys.readouterr().out
    assert rc == 1
    assert "grade 9 declared not offered" in out


def test_math_core_missing_still_error():
    vk = _load_vk()
    errors: list[str] = []
    pending = vk._validate_subject_grades(
        "math", [(7, "math_grade7.json")], errors
    )
    assert any("missing core knowledge file: math_grade8.json" in e for e in errors)
    assert any("missing core knowledge file: math_grade9.json" in e for e in errors)
    assert pending == [1, 2, 3, 4, 5, 6, 10, 11, 12]


def test_other_subject_band_gap_still_pending():
    """biology grade9 不在不开设声明里：档内缺 9 仍按 pending 语义。"""
    vk = _load_vk()
    errors: list[str] = []
    pending = vk._validate_subject_grades(
        "biology", [(7, "biology_grade7.json"), (8, "biology_grade8.json")], errors
    )
    assert errors == []
    assert pending == [9, 10, 11, 12]
