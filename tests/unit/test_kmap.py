"""知识地图可视化（kmap + GET /learners/{id}/knowledge-map.html）单元测试。

覆盖：数据层聚合（画像全覆盖不重不漏）、薄弱 top10 与 /plan 同源一致性、
路线降级、自包含渲染（标签配平/无外部资源）、热力与置信度编码、空态、
跨学科总览、以及端点级行为（200/404、KP 数出现=profile 数、体积上限、
多租户隔离）。
"""
import re
from datetime import date

import pytest
from fastapi.testclient import TestClient

from xuexing import load_itembank, load_kpgraph, load_kpgraph_subject, load_strategies
from xuexing.kmap import (
    MASTERY_THRESHOLD,
    WEAK_TOP_N,
    build_overview_kmap,
    build_subject_kmap,
    render_kmap_html,
)
from xuexing.kpgraph import kpgraph_from_dict
from xuexing.paper_render import check_html_tag_balance
from xuexing.route import build_plan
from xuexing.server import create_app
from xuexing.types import Profile

TODAY = date(2026, 10, 6)

# 无外部资源引用：自包含红线（http(s) 外链 / script / link / src / css url()）
EXTERNAL_REF_RE = re.compile(
    r"https?://|<script|<link\b|\bsrc=|url\(", re.IGNORECASE)


def _kp(kp_id, name, grade, cluster, prereqs=None):
    return {
        "id": kp_id, "name": name, "subject": "demo", "grade": grade,
        "cluster": cluster, "description": "d", "standard_ref": "s",
        "prereqs": prereqs or [],
    }


def _mini_graph():
    return kpgraph_from_dict({"knowledge_points": [
        _kp("kp_a1", "甲", 1, "章一"),
        _kp("kp_a2", "乙", 1, "章一", prereqs=["kp_a1"]),
        _kp("kp_b1", "丙", 2, "章二"),
        _kp("kp_b2", "丁", 2, "章二", prereqs=["kp_b1"]),
    ]})


def _profile(mastery, evidence=None, learner_id="L"):
    return Profile(learner_id=learner_id, mastery=dict(mastery),
                   evidence=dict(evidence or {}),
                   updated_at="2026-10-06T00:00:00Z")


def _subject_data(profile, graph, strategies=None):
    return build_subject_kmap(profile, graph, strategies, bank=None,
                              today=TODAY, subject="demo")


def _chips(html_doc):
    """解析全部 KP 芯片：[(kp_id, data-m or None, data-c, data-ev)]。"""
    out = []
    for m in re.finditer(
            r'<li class="kp[^"]*" id="kp-([A-Za-z0-9_]+)" data-kp="\1"'
            r'(?: data-m="([0-9.]+)" data-c="([0-9.]+)" data-ev="(\d+)")?',
            html_doc):
        out.append((m.group(1), m.group(2), m.group(3), m.group(4)))
    return out


def _weak_rows(html_doc):
    return [(int(m.group(1)), m.group(2), m.group(3)) for m in re.finditer(
        r'<li class="weak-row" data-rank="(\d+)" data-kp="([A-Za-z0-9_]+)" '
        r'data-m="([0-9.]+)"', html_doc)]


# ---------- 数据层：KP 覆盖与数值保真 ----------

def test_subject_kmap_covers_every_profile_kp_exactly_once():
    graph = _mini_graph()
    # 画像覆盖 3/4 个知识点（kp_b2 画像外）；含零证据的平滑值点
    profile = _profile(
        {"kp_a1": 0.9, "kp_a2": 0.123456, "kp_b1": 0.5},
        {"kp_a1": 4, "kp_a2": 2, "kp_b1": 0},
        learner_id="cover")
    data = _subject_data(profile, graph)

    assert data["empty"] is None
    assert data["stats"]["total"] == 4
    assert data["stats"]["covered"] == 3
    assert data["stats"]["measured"] == 2
    flat = [v for g in data["grades"] for c in g["clusters"] for v in c["kps"]]
    assert len(flat) == 4
    assert len({v["kp_id"] for v in flat}) == 4  # 不重不漏
    by_id = {v["kp_id"]: v for v in flat}
    assert by_id["kp_a2"]["mastery"] == 0.123456      # 数值逐字保真
    assert by_id["kp_a2"]["confidence"] == round(2 / 5.0, 4)
    assert by_id["kp_b1"]["evidence"] == 0            # 零证据如实
    assert by_id["kp_b2"]["mastery"] is None          # 画像外不给假值
    # 年级升序、章名升序
    assert [g["grade"] for g in data["grades"]] == [1, 2]
    assert [c["cluster"] for c in data["grades"][0]["clusters"]] == ["章一"]


def test_weak_top10_matches_plan_steps_and_profile():
    graph = _mini_graph()
    profile = _profile(
        {"kp_a1": 0.1, "kp_a2": 0.2, "kp_b1": 0.3, "kp_b2": 0.4},
        {"kp_a1": 3, "kp_a2": 3, "kp_b1": 3, "kp_b2": 3})
    data = _subject_data(profile, graph, strategies=_strategies())

    plan = build_plan(profile, None, graph, _strategies(), TODAY,
                      mastery_threshold=MASTERY_THRESHOLD)
    expect = plan.steps[:WEAK_TOP_N]
    assert [w["kp_id"] for w in data["weak_top"]] == [s.kp_id for s in expect]
    assert data["plan_available"] is True
    for w in data["weak_top"]:
        assert w["mastery"] < MASTERY_THRESHOLD          # 与画像一致：全为薄弱
        assert w["mastery"] == profile.mastery[w["kp_id"]]
        assert w["strategy_name"] and w["rationale"]     # 建议动作非空


def _strategies():
    return load_strategies(_repo("data", "pedagogy", "strategies.json"))


def test_weak_top10_falls_back_honestly_on_route_deadlock():
    # 先序环：a<->b 互相声称先序，route.build_plan 判死锁
    cyclic = kpgraph_from_dict({"knowledge_points": [
        _kp("kp_x", "X", 1, "章", prereqs=["kp_y"]),
        _kp("kp_y", "Y", 1, "章", prereqs=["kp_x"]),
    ]})
    profile = _profile({"kp_x": 0.3, "kp_y": 0.55}, {"kp_x": 2, "kp_y": 1})
    data = _subject_data(profile, cyclic, strategies=_strategies())

    assert data["plan_available"] is False
    assert "死锁" in data["plan_note"] or "不可用" in data["plan_note"]
    assert [w["kp_id"] for w in data["weak_top"]] == ["kp_x", "kp_y"]  # 掌握度升序
    assert all(w["strategy_name"] for w in data["weak_top"])


# ---------- 渲染层：自包含 / 热力 / 配平 ----------

def _filled_profile():
    return _profile(
        {"kp_a1": 0.9, "kp_a2": 0.123456, "kp_b1": 0.5, "kp_b2": 0.3},
        {"kp_a1": 4, "kp_a2": 2, "kp_b1": 0, "kp_b2": 1})


def test_render_self_contained_and_balanced():
    data = _subject_data(_filled_profile(), _mini_graph(), strategies=_strategies())
    doc = render_kmap_html(data)

    assert doc.startswith("<!DOCTYPE html>")
    assert 'charset="utf-8"' in doc
    assert EXTERNAL_REF_RE.search(doc) is None, "自包含红线：不允许外部资源引用"
    assert check_html_tag_balance(doc) == []
    assert 'class="weak-row"' in doc and 'id="heat-strip"' in doc


def test_render_encodes_mastery_confidence_and_weak_order():
    data = _subject_data(_filled_profile(), _mini_graph(), strategies=_strategies())
    doc = render_kmap_html(data)

    chips = {kp: (m, c, ev) for kp, m, c, ev in _chips(doc) if m is not None}
    assert set(chips) == set(_filled_profile().mastery)  # 画像点全渲染
    m, c, ev = chips["kp_a2"]
    assert m == "0.123456"                # 与 profile 值逐字一致
    assert c == "0.4000" and ev == "2"
    assert "hsla(" in doc                 # 色相热力 + 透明度置信度在位
    # 薄弱行与数据层一致且有序
    rows = _weak_rows(doc)
    assert [kp for _r, kp, _m in rows] == [w["kp_id"] for w in data["weak_top"]]
    assert [int(r) for r, _kp, _m in rows] == list(range(1, len(rows) + 1))
    for _r, kp, mval in rows:
        assert mval == f"{_filled_profile().mastery[kp]:.6f}"
        assert f'<a href="#kp-{kp}">' in doc  # 锚点可跳转


def test_empty_states_no_overlap_and_no_evidence():
    graph = _mini_graph()
    # 画像与学科无交集
    other = _profile({"kp_zzz": 0.5}, {"kp_zzz": 1})
    d1 = _subject_data(other, graph)
    assert d1["empty"]["reason"] == "no_overlap"
    doc1 = render_kmap_html(d1)
    assert "暂无数据" in doc1 and "无交集" in doc1
    assert check_html_tag_balance(doc1) == []

    # 空学习者：画像全覆盖但零作答证据
    empty = _profile({kp.id: 0.5 for kp in graph.kps()})
    d2 = _subject_data(empty, graph)
    assert d2["empty"]["reason"] == "no_evidence"
    doc2 = render_kmap_html(d2)
    assert "空画像" in doc2 or "无作答证据" in doc2
    assert EXTERNAL_REF_RE.search(doc2) is None


def test_overview_aggregates_by_subject():
    math_g = _mini_graph()
    chi_g = kpgraph_from_dict({"knowledge_points": [_kp("kp_c1", "文", 1, "章")]})
    subjects = ["demo", "chi"]
    loader = {"demo": math_g, "chi": chi_g}.__getitem__
    profile = _profile(
        {"kp_a1": 0.9, "kp_a2": 0.2, "kp_c1": 0.5},
        {"kp_a1": 3, "kp_a2": 1})  # chi 覆盖但零证据
    data = build_overview_kmap(profile, subjects, loader)

    assert data["mode"] == "overview" and data["any_evidence"] is True
    rows = {r["subject"]: r for r in data["subjects"]}
    assert rows["demo"]["total"] == 4 and rows["demo"]["covered"] == 2
    assert rows["demo"]["measured"] == 2 and rows["demo"]["weak"] == 1
    assert rows["chi"]["covered"] == 1 and rows["chi"]["measured"] == 0
    assert rows["chi"]["avg"] == 0.5
    doc = render_kmap_html(data)
    assert check_html_tag_balance(doc) == []
    assert EXTERNAL_REF_RE.search(doc) is None
    assert 'href="knowledge-map.html?subject=demo"' in doc
    assert "暂无任何学科" not in doc  # 有证据学科在，不误报空学习者横幅

    # 全学科零证据 -> 空学习者横幅如实出现
    no_ev = build_overview_kmap(
        _profile({"kp_a1": 0.5}, {}), subjects, loader)
    assert no_ev["any_evidence"] is False
    assert "暂无任何学科" in render_kmap_html(no_ev)


def test_render_rejects_unknown_mode():
    with pytest.raises(ValueError):
        render_kmap_html({"mode": "???"})


# ---------- 端点级行为（真实 data/knowledge 学科级装载）----------

@pytest.fixture(scope="module")
def kmap_client(bank, graph, strategies):
    app = create_app(bank, graph, strategies)
    return TestClient(app)


def test_endpoint_subject_map_matches_profile(kmap_client):
    r = kmap_client.post("/learners/kmap-stu/responses", json={
        "responses": [
            {"item_id": "m7_010", "correct": False},
            {"item_id": "m7_011", "correct": False},
            {"item_id": "m7_013", "correct": True},
        ]})
    assert r.status_code == 200
    prof = kmap_client.get("/learners/kmap-stu/profile").json()

    resp = kmap_client.get("/learners/kmap-stu/knowledge-map.html",
                           params={"subject": "math"})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")
    doc = resp.text

    subject_graph = load_kpgraph_subject(_repo_knowledge_dir(), "math")
    # KP 数出现 = profile 数：画像在本学科的每个 KP 恰出现一次、值逐字一致
    in_subject = {k: f"{v:.6f}" for k, v in prof["mastery"].items()
                  if subject_graph.has(k)}
    chips = {kp: m for kp, m, _c, _ev in _chips(doc) if m is not None}
    assert len(chips) == len(in_subject) == len(prof["mastery"])
    assert chips == in_subject
    # 图谱全量 KP 都有芯片（含画像外）
    assert len(_chips(doc)) == len(subject_graph.kps())
    # 薄弱 top10 与 /plan 数据一致
    strats = load_strategies(_repo("data", "pedagogy", "strategies.json"))
    from xuexing.types import Profile as P
    p_obj = P(learner_id=prof["learner_id"], mastery=prof["mastery"],
              evidence=prof["evidence"], updated_at=prof["updated_at"])
    plan = build_plan(p_obj, None, subject_graph, strats, TODAY,
                      mastery_threshold=MASTERY_THRESHOLD)
    got = _weak_rows(doc)
    assert [kp for _r, kp, _m in got] == [s.kp_id for s in plan.steps[:WEAK_TOP_N]]
    for _r, kp, mval in got:
        assert mval == f"{prof['mastery'][kp]:.6f}"
        assert prof["mastery"][kp] < MASTERY_THRESHOLD
    # 页头与自包含
    assert "kmap-stu" in doc and prof["updated_at"] in doc
    assert EXTERNAL_REF_RE.search(doc) is None
    assert check_html_tag_balance(doc) == []
    assert len(doc.encode()) < 2 * 1024 * 1024


def test_endpoint_overview_and_404s(kmap_client):
    kmap_client.post("/learners/kmap-stu2/responses", json={
        "responses": [{"item_id": "m7_010", "correct": True}]})

    resp = kmap_client.get("/learners/kmap-stu2/knowledge-map.html")
    assert resp.status_code == 200
    doc = resp.text
    assert check_html_tag_balance(doc) == []
    assert EXTERNAL_REF_RE.search(doc) is None
    for subject in ("math", "chinese", "english"):
        assert f'subject={subject}' in doc
    assert "kmap-stu2" in doc

    # 无数据学科：math 学习者查语文 -> 诚实空态页（非编造地图）
    empty_doc = kmap_client.get(
        "/learners/kmap-stu2/knowledge-map.html",
        params={"subject": "chinese"}).text
    assert "暂无数据" in empty_doc
    assert check_html_tag_balance(empty_doc) == []

    assert kmap_client.get("/learners/nobody/knowledge-map.html").status_code == 404
    assert kmap_client.get(
        "/learners/kmap-stu2/knowledge-map.html",
        params={"subject": "no_such_subject"}).status_code == 404


def test_endpoint_respects_org_isolation(kmap_client):
    kmap_client.post("/learners/org-stu/responses", json={
        "responses": [{"item_id": "m7_010", "correct": True}]},
        headers={"X-Org-Id": "org-a"})
    assert kmap_client.get(
        "/learners/org-stu/knowledge-map.html",
        headers={"X-Org-Id": "org-b"}).status_code == 404
    assert kmap_client.get(
        "/learners/org-stu/knowledge-map.html",
        headers={"X-Org-Id": "org-a"}).status_code == 200


# ---------- 夹具辅助 ----------

def _repo(*parts):
    import os
    return os.path.abspath(os.path.join(
        os.path.dirname(__file__), "..", "..", *parts))


def _repo_knowledge_dir():
    return _repo("data", "knowledge")
