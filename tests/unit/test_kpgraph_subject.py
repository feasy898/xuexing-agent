"""学科级装载器（kpgraph_subject）单元测试。

覆盖：跨年级 prereq 合并解析、发现约定（与 validate_knowledge 同一正则）、
错误路径（未知学科/跨文件重复 id）、以及 data/knowledge 实库 10 学科全量
装载门（validate() 为空 + 拓扑可用 + math 合并结果与 math_all.json 先例一致）。
"""
import json
import os

import pytest

from xuexing import load_kpgraph_subject  # 包根导出，与 load_kpgraph 同层
from xuexing.kpgraph import KPGraphError, load_kpgraph
from xuexing.kpgraph_subject import discover_subject_files, discover_subjects

EXPECTED_SUBJECTS = [
    "biology", "chemistry", "chinese", "english", "geography",
    "history", "math", "physics", "politics", "science",
]


def _kp(kp_id, grade, prereqs=None):
    return {
        "id": kp_id, "name": kp_id, "subject": "demo", "grade": grade,
        "cluster": "c", "description": "d", "standard_ref": "s",
        "prereqs": prereqs or [],
    }


def _write(tmp_path, name, kps):
    (tmp_path / name).write_text(
        json.dumps({"knowledge_points": kps}, ensure_ascii=False),
        encoding="utf-8",
    )


# ---------- 发现约定 ----------

def test_discover_ignores_non_grade_files(tmp_path):
    _write(tmp_path, "demo_grade1.json", [_kp("a", 1)])
    _write(tmp_path, "demo_all.json", [])          # 合并先例文件不入年级口径
    _write(tmp_path, "demo_grade11b.json", [])     # 非 <subject>_grade<N>.json
    _write(tmp_path, "other_grade2.json", [])      # 其他学科
    (tmp_path / "readme.txt").write_text("x", encoding="utf-8")
    assert discover_subject_files(str(tmp_path), "demo") == [
        str(tmp_path / "demo_grade1.json")
    ]
    assert discover_subjects(str(tmp_path)) == ["demo", "other"]


def test_discover_empty_directory(tmp_path):
    assert discover_subjects(str(tmp_path)) == []
    assert discover_subject_files(str(tmp_path), "demo") == []


# ---------- 合并装载 ----------

def test_merge_resolves_cross_grade_prereqs(tmp_path):
    _write(tmp_path, "demo_grade1.json", [_kp("kp_a", 1)])
    _write(tmp_path, "demo_grade2.json", [_kp("kp_b", 2, prereqs=["kp_a"])])
    g = load_kpgraph_subject(str(tmp_path), "demo")
    assert [kp.id for kp in g.kps()] == ["kp_a", "kp_b"]
    assert g.validate() == []
    order = g.topological_order()
    assert order.index("kp_a") < order.index("kp_b")
    assert g.children("kp_a") == ["kp_b"]
    # 下游出卷/诊断依赖的闭包/前沿查询可用
    assert g.descendants("kp_a") == {"kp_b"}
    assert g.ancestors("kp_b") == {"kp_a"}
    assert g.frontier({}, 0.65) == ["kp_a"]


def test_single_grade_file_alone_still_fails(tmp_path):
    """对照：同一数据逐文件 load_kpgraph 报 unknown endpoint——本入口存在的理由。"""
    _write(tmp_path, "demo_grade1.json", [_kp("kp_a", 1)])
    _write(tmp_path, "demo_grade2.json", [_kp("kp_b", 2, prereqs=["kp_a"])])
    with pytest.raises(KPGraphError, match="unknown endpoint in edge kp_a -> kp_b"):
        load_kpgraph(str(tmp_path / "demo_grade2.json"))
    # 学科级入口装载同一数据则成功
    assert load_kpgraph_subject(str(tmp_path), "demo").validate() == []


def test_unknown_subject_raises(tmp_path):
    with pytest.raises(KPGraphError) as excinfo:
        load_kpgraph_subject(str(tmp_path), "demo")
    assert "demo" in str(excinfo.value)


def test_duplicate_id_across_files_raises(tmp_path):
    _write(tmp_path, "demo_grade1.json", [_kp("kp_a", 1)])
    _write(tmp_path, "demo_grade2.json", [_kp("kp_a", 2)])
    with pytest.raises(KPGraphError, match="duplicate kp id: kp_a"):
        load_kpgraph_subject(str(tmp_path), "demo")


def test_missing_knowledge_points_key_passthrough(tmp_path):
    (tmp_path / "demo_grade1.json").write_text("{}", encoding="utf-8")
    with pytest.raises(KeyError):
        load_kpgraph_subject(str(tmp_path), "demo")


# ---------- 实库门（data/knowledge 实际划分） ----------

def test_real_data_all_ten_subjects_load(root):
    knowledge_dir = os.path.join(root, "data", "knowledge")
    subjects = discover_subjects(knowledge_dir)
    assert subjects == EXPECTED_SUBJECTS  # 以 data/knowledge 实际划分为准
    for subject in subjects:
        g = load_kpgraph_subject(knowledge_dir, subject)
        kps = g.kps()
        assert kps, subject
        assert g.validate() == [], subject
        assert len(g.topological_order()) == len(kps), subject  # 无环


def test_real_data_math_merge_matches_math_all(root):
    """math_all.json 先例一致性：年级合并结果的 id/prereqs 与其完全一致。"""
    knowledge_dir = os.path.join(root, "data", "knowledge")
    merged = load_kpgraph_subject(knowledge_dir, "math")
    all_file = load_kpgraph(os.path.join(knowledge_dir, "math_all.json"))
    assert {kp.id for kp in merged.kps()} == {kp.id for kp in all_file.kps()}
    for kp in merged.kps():
        assert merged.prereqs(kp.id) == all_file.prereqs(kp.id)
