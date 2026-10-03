"""知识库（数据）校验：图谱、题库、误解、母题四类资产的完整性。

知识库已从"七年级 4 章节簇"扩展为全学科（数学/英语/语文/物理/化学/生物/
历史/地理/政治/小学科学）× 小学（1-6 年级）+ 初中（7-9 年级）+ 高中
（10-12 年级）覆盖，本文件与 tools/validate_knowledge.py 同口径：图谱按
<subject>_grade<N>.json 全学科扫描后合并检查，题库 / 误解库 / 母题库分别
扫描 data/ 下对应目录的全部文件。验证器图谱口径为学科文件全量（缺某学科
某年级文件时记 pending 不报错）；本文件夹具按（年级, 学科, 文件）动态发现、
覆盖库内现存数据，另对 math_all 合并视图单独做 1-12 年级检查（随学段扩张
逐段长到 1-12）。
断言一律下限式（非空、集合归属、数量下限），不锁定具体规模数字——
扩库只增不减时测试应保持通过。
"""
import glob
import json
import os
import re

import pytest

from xuexing.itembank import itembank_from_dict
from xuexing.kpgraph import kpgraph_from_dict

# 项目根目录（与 conftest 的 ROOT 同口径），便于直接定位 data/ 下的非夹具资源
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 数学课标（2022 年版 + 高中 2017 年版 2020 修订）章节簇全集：按学段登记。
# 断言为"归属"而非"相等"——新增簇时在此登记即可，不锁簇数。
# 其余学科的章节簇体系各成一体（语文数百个簇），与 validate_knowledge.py
# 同口径只做"非空"校验，不在此登记。
CURRICULUM_CLUSTERS = {
    # 第一、二学段（1-4 年级）
    "数与运算", "数量关系", "图形与几何", "统计与概率", "综合与实践",
    # 七年级（第四学段）
    "有理数", "整式加减", "一元一次方程", "图形初步", "实数",
    "相交线与平行线", "平面直角坐标系", "二元一次方程组",
    "不等式与不等式组", "数据的收集与整理",
    # 八年级（第四学段）
    "三角形", "全等三角形", "轴对称", "整式乘法与因式分解", "分式",
    "勾股定理", "平行四边形", "一次函数", "二次根式", "数据的分析",
    # 九年级（第四学段）
    "一元二次方程", "二次函数", "旋转", "圆", "概率初步",
    "反比例函数", "相似", "锐角三角函数",
    # 高中（必修+选择性必修）
    "集合与常用逻辑用语", "函数的概念与性质", "函数", "三角函数",
    "指数函数与对数函数", "一元二次函数、方程和不等式",
    "平面向量及其应用", "复数", "立体几何初步", "空间向量与立体几何",
    "直线和圆的方程", "圆锥曲线的方程", "统计", "概率",
    "数列", "一元函数的导数及其应用", "数学建模与探究",
    "计数原理", "概率与统计（选修）", "空间解析几何初步",
    "导数及其应用（选修）",
    # 高中·选择性必修第三册（按章登记）
    "选择性必修第三册·第六章 计数原理",
    "选择性必修第三册·第七章 随机变量及其分布",
    "选择性必修第三册·第八章 成对数据的统计分析",
}

# 年级文件动态发现（<subject>_grade<N>.json，全学科）：随学段落库自然生长，
# 避免跨批次改元组。命名规范与 tools/validate_knowledge.py 的
# SUBJECT_KNOWLEDGE_RE 同口径；math_all.json（合并视图）与非规范命名的
# 补充批次（如 math_grade11b.json）不入图谱口径。
_SUBJECT_GRADE_RE = re.compile(r"^([a-z]+)_grade(\d+)\.json$")


def _discover_grade_files(root):
    """扫描全部学科的年级图谱文件 → sorted {grade: {subject: [path, ...]}}。

    每年级每学科的文件作为独立列表（同年级同学科未来出现多个文件时按文件名
    依次追加），数学/英语/语文/物理/化学/生物/历史/地理/政治/小学科学全部
    纳入 merged_graph 口径。
    """
    found = {}
    for path in sorted(glob.glob(f"{root}/data/knowledge/*_grade*.json")):
        m = _SUBJECT_GRADE_RE.match(os.path.basename(path))
        if not m:
            continue
        subject, grade = m.group(1), int(m.group(2))
        found.setdefault(grade, {}).setdefault(subject, []).append(path)
    return {
        grade: {subject: paths for subject, paths in sorted(subjects.items())}
        for grade, subjects in sorted(found.items())
    }


# 下限口径（现库远高于此；取值只防"文件被清空/大幅截断"）。
MIN_KPS_PER_GRADE = 20  # 数学初中及以上任一年级文件的知识点数下限
MIN_KPS_PER_GRADE_ELEMENTARY = 10  # 数学小学任一年级文件的知识点数下限
MIN_KPS_MERGED = 60  # 合并图谱知识点数下限
MIN_CLUSTERS_MERGED = 8  # 合并图谱章节簇数下限
MIN_PRIMARY_ITEMS_PER_KP = 3  # 覆盖率口径与验收门默认一致
MIN_ARCHETYPES_PER_FILE = 6  # 每个母题文件的条数下限（与验收门一致）
# 非数学学科每文件知识点数下限：按现库各学科最小文件留余量取值（防截断，
# 不锁规模）。现库最小：英语 grade2=12、语文 grade12=12、生物 grade9=5、
# 地理 grade12=11、政治 grade12=20、历史 grade12=32、化学 grade10=63、
# 物理 grade10=65、小学科学 grade2=48。
MIN_KPS_PER_FILE_BY_SUBJECT = {
    "biology": 4,
    "chemistry": 50,
    "chinese": 10,
    "english": 10,
    "geography": 10,
    "history": 25,
    "physics": 50,
    "politics": 15,
    "science": 40,
}


# ---------- 夹具：与验收门同口径的合并视图 ----------


@pytest.fixture(scope="session")
def grade_kps(root):
    """按（年级, 学科, 文件）读原始图谱数据；顺带校验 id 全库不重复。

    结构：{grade: {subject: [该年级该学科每个文件的 kps, ...]}}。
    数学沿用原防截断下限（小学 10 / 初中及以上 20），非数学学科用
    MIN_KPS_PER_FILE_BY_SUBJECT 的学科专属下限。
    """
    out = {}
    seen = {}
    grade_files = _discover_grade_files(root)
    assert "math" in grade_files.get(7, {}), "grade7 math knowledge file missing"
    for grade, subjects in grade_files.items():
        out[grade] = {}
        for subject, paths in subjects.items():
            kp_lists = []
            for path in paths:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                kps = data["knowledge_points"]
                if subject == "math":
                    floor = (
                        MIN_KPS_PER_GRADE_ELEMENTARY if grade <= 6 else MIN_KPS_PER_GRADE
                    )
                else:
                    floor = MIN_KPS_PER_FILE_BY_SUBJECT.get(subject, 0)
                assert len(kps) >= floor, (
                    f"{subject} grade{grade}: only {len(kps)} kps (< {floor})"
                )
                for kp in kps:
                    assert kp["id"] not in seen, (
                        f"duplicate kp id: {kp['id']} "
                        f"({seen.get(kp['id'])} & {os.path.basename(path)})"
                    )
                    seen[kp["id"]] = os.path.basename(path)
                kp_lists.append(kps)
            out[grade][subject] = kp_lists
    return out


def _iter_subject_kps(grade_kps, subject):
    """展平指定学科在 grade_kps 中的全部知识点（跨年级、跨文件）。"""
    return [
        kp
        for subjects in grade_kps.values()
        for kp_list in subjects.get(subject, [])
        for kp in kp_list
    ]


@pytest.fixture(scope="session")
def merged_graph(grade_kps):
    """合并全学科已落库各年级的知识点图谱。"""
    merged = [
        kp
        for grade in sorted(grade_kps)
        for subject in sorted(grade_kps[grade])
        for kp_list in grade_kps[grade][subject]
        for kp in kp_list
    ]
    assert len(merged) >= MIN_KPS_MERGED, f"merged graph only has {len(merged)} kps"
    return kpgraph_from_dict({"knowledge_points": merged})


@pytest.fixture(scope="session")
def merged_bank(root):
    """合并 data/items/*.json 的题库；先在原始 dict 层查重复 id / 重复整题
    （bank.add 按 id 覆盖，重复必须在入构前拦截）。

    重复判定 = 全题（题干+选项+答案+题型）逐项相同。只比对题干会误伤选择题
    里的通用题干（如「下列说法正确的是（　　）」）：2026-10-03 物理/化学/语文
    扩科批落库后实测 31 对同题干题目全部选项/答案各异，均为合法独立题；
    真重复（同 id 同内容，如 chi_hs_0198 曾同文件落两条）仍会被此处拦下。
    """
    paths = sorted(glob.glob(f"{root}/data/items/*.json"))
    assert paths, "no item files found under data/items/"
    seen_id, seen_question = {}, {}
    items = []
    for path in paths:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        for it in data["items"]:
            assert it["id"] not in seen_id, f"duplicate item id: {it['id']}"
            seen_id[it["id"]] = os.path.basename(path)
            question = (
                str(it.get("stem", "")).strip(),
                json.dumps(it.get("options"), ensure_ascii=False, sort_keys=True),
                str(it.get("answer", "")).strip(),
                str(it.get("item_type", "")).strip(),
            )
            assert question not in seen_question, (
                f"duplicate question: {it['id']} (first seen)"
            )
            seen_question[question] = it["id"]
            items.append(it)
    return itembank_from_dict({"items": items})


# ---------- 图谱 ----------


def test_kpgraph_is_valid_dag(merged_graph):
    assert merged_graph.validate() == []
    order = merged_graph.topological_order()
    assert sorted(order) == sorted(kp.id for kp in merged_graph.kps())


def test_kpgraph_metadata_and_clusters(merged_graph):
    kps = merged_graph.kps()
    assert len(kps) >= MIN_KPS_MERGED
    clusters = set()
    for kp in kps:
        assert kp.name and kp.cluster and kp.standard_ref, f"{kp.id} missing metadata"
        assert str(kp.description).strip(), f"{kp.id}: empty description"
        assert 1 <= kp.grade <= 12, f"{kp.id}: grade {kp.grade} out of 1-12"
        clusters.add(kp.cluster)
    assert len(clusters) >= MIN_CLUSTERS_MERGED


def test_grade_files_scope(grade_kps):
    """各（年级,学科）文件的知识点都归属本年级、章节簇非空；数学知识点另须
    归属数学课标簇集合（CURRICULUM_CLUSTERS 仅登记数学课标，其余学科与
    validate_knowledge.py 同口径只查非空）。"""
    for grade, subjects in grade_kps.items():
        for subject, kp_lists in subjects.items():
            clusters = set()
            for kps in kp_lists:
                for kp in kps:
                    assert int(kp["grade"]) == grade, f"{kp['id']}: grade {kp['grade']} in grade{grade} file"
                    assert str(kp.get("cluster", "")).strip(), f"{kp['id']}: empty cluster"
                    if subject == "math":
                        assert kp.get("cluster") in CURRICULUM_CLUSTERS, f"{kp['id']}: unknown cluster"
                    assert str(kp.get("standard_ref", "")).strip(), f"{kp['id']}: empty standard_ref"
                    assert str(kp.get("description", "")).strip(), f"{kp['id']}: empty description"
                    clusters.add(kp["cluster"])
            assert clusters, f"{subject} grade{grade}: no clusters"


# ---------- 合并视图 math_all.json ----------


def test_math_all_merged_view_within_1_12(root, grade_kps):
    """math_all 是数学年级文件的合并视图（仅数学口径，其他学科不经它合并）：
    年级全部落在 1-12（随学段扩张逐段长到 1-12），且不丢已落库数学年级
    文件中的任何知识点。"""
    with open(f"{root}/data/knowledge/math_all.json", encoding="utf-8") as f:
        data = json.load(f)
    kps = data["knowledge_points"]
    assert kps, "math_all.json has no knowledge points"
    bad = [
        (kp["id"], kp.get("grade"))
        for kp in kps
        if not 1 <= int(kp.get("grade", 0)) <= 12
    ]
    assert bad == [], f"math_all kps grade out of 1-12: {bad}"
    core_ids = {kp["id"] for kp in _iter_subject_kps(grade_kps, "math")}
    missing = sorted(core_ids - {kp["id"] for kp in kps})
    assert not missing, f"math_all lost grade kps: {missing}"


# ---------- 题库 ----------


def test_items_schema_and_kp_refs(merged_bank, merged_graph):
    errs = merged_bank.validate_all(valid_kp_ids={kp.id for kp in merged_graph.kps()})
    assert errs == [], errs


def test_every_kp_meets_primary_item_floor(merged_graph, merged_bank, grade_kps):
    # 覆盖率下限目前只对有题库建设的数学执行（与验收门口径一致：无题库学科
    # 不入该口径；英语题库 425 题尚未达到 3 题/KP 的主覆盖门，扩科见台账）。
    math_ids = {kp["id"] for kp in _iter_subject_kps(grade_kps, "math")}
    # 加载题数豁免集 = 误解库『无误解』豁免 ∪ 题库『题目采集中』豁免
    # （与 tools/validate_knowledge.py 同口径：豁免的 KP 同时豁免误解覆盖
    # 与主知识点题数检查）。
    item_exempt: set[str] = set()
    # 题库『题目采集中』豁免
    exempt_path = os.path.join(_ROOT, "data", "coverage_exemptions.json")
    if os.path.exists(exempt_path):
        with open(exempt_path, encoding="utf-8") as f:
            edata = json.load(f)
        for ex in edata.get("exemptions", []):
            kp_id = ex.get("kp_id")
            if isinstance(kp_id, str) and kp_id.strip():
                item_exempt.add(kp_id)
    # 误解库『无误解』豁免（同名 kp_id）
    mc_dir = os.path.join(_ROOT, "data", "misconceptions")
    if os.path.isdir(mc_dir):
        for fname in os.listdir(mc_dir):
            if not fname.endswith(".json"):
                continue
            try:
                with open(os.path.join(mc_dir, fname), encoding="utf-8") as f:
                    d = json.load(f)
                for ex in d.get("exemptions", []) or []:
                    kp_id = ex.get("kp_id")
                    if isinstance(kp_id, str) and kp_id.strip():
                        item_exempt.add(kp_id)
            except Exception:  # noqa: BLE001
                pass
    below = [
        (kp.id, len(merged_bank.by_kp(kp.id, primary_only=True)))
        for kp in merged_graph.kps()
        if kp.id in math_ids
        and kp.id not in item_exempt
        and len(merged_bank.by_kp(kp.id, primary_only=True)) < MIN_PRIMARY_ITEMS_PER_KP
    ]
    assert below == [], f"kps below {MIN_PRIMARY_ITEMS_PER_KP} primary items: {below}"


# ---------- 误解库（data/misconceptions/ 全量文件）----------


def test_misconception_refs_valid(root, merged_graph, merged_bank):
    kp_ids = {kp.id for kp in merged_graph.kps()}
    mc_ids = set()
    paths = sorted(glob.glob(f"{root}/data/misconceptions/*.json"))
    assert paths, "no misconception files found"
    for path in paths:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        for mc in data["misconceptions"]:
            assert mc["id"] not in mc_ids, f"duplicate misconception {mc['id']}"
            mc_ids.add(mc["id"])
            assert mc["kp_id"] in kp_ids, mc["id"]
            assert str(mc.get("hint", "")).strip(), f"{mc['id']} missing hint"
            assert str(mc.get("signature", "")).strip(), f"{mc['id']} missing signature"
    for it in merged_bank.items():
        for m in it.misconceptions:
            assert m in mc_ids, f"{it.id}: unknown misconception {m}"


# ---------- 母题库（data/archetypes/ 全量文件）----------


def test_archetypes_valid(root, merged_graph):
    kp_ids = {kp.id for kp in merged_graph.kps()}
    seen = set()
    paths = sorted(glob.glob(f"{root}/data/archetypes/*.json"))
    assert paths, "no archetype files found"
    for path in paths:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        arcs = data.get("archetypes", [])
        assert len(arcs) >= MIN_ARCHETYPES_PER_FILE, (
            f"{os.path.basename(path)}: only {len(arcs)} archetypes"
        )
        for a in arcs:
            assert a["id"] not in seen, f"duplicate archetype {a['id']}"
            seen.add(a["id"])
            for field in ("name", "pattern", "example"):
                assert str(a.get(field, "")).strip(), f"{a['id']}: empty {field}"
            assert a.get("kp_ids"), f"{a['id']}: no kp_ids"
            unknown = [k for k in a["kp_ids"] if k not in kp_ids]
            assert not unknown, f"{a['id']}: unknown kps {unknown}"
            assert a.get("variant_axes"), f"{a['id']}: no variant_axes"


# ---------- 教学策略库（conftest 注入的 strategies 夹具）----------


def test_strategies_have_evidence_and_fallback(strategies):
    all_s = strategies.strategies()
    assert len(all_s) >= 5
    for s in all_s:
        assert s.evidence, f"{s.id} missing evidence"
    # 兜底策略：任意 (mastery, grade) 都能选出策略
    for m in (0.05, 0.5, 0.95):
        for g in (3, 7, 9):
            strategies.select(m, g)
