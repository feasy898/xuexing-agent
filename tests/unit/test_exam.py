"""单元测试：exam —— 学生作答闭环（起卷 / 提交判分 / 报告页 / 会话）。

自闭式夹具（不依赖 data/）：mini 卷型 + mini 题库 + mini 知识点图谱，钉住
契约行为：
- 起卷：200 text/html、会话头、题块号连续、**每题恰一组 name=item_{no} 的
  作答控件**（选择 radio、多选 checkbox、填空 input、解答 textarea）、
  learner 回显、form action 指向本会话、标签配平；
- 红线：学生卷绝不带 answer/solution（词根 + 值级，委托内核 redline_report）；
- 判分复用：逐题判定与 ``grading.grade_to_response`` 逐条一致（= /grade 口径）；
- 落库：交卷后 GET /profile、/plan 立即反映本卷（同一 store 序列）；
- 报告页：得分/逐题对错标记/掌握更新/薄弱点/下一步建议四节齐全；
- 会话：未知 404、过期 404、跨 org 404、重复提交 409、未提交看报告 409、
  缺 learner_id 400、非法 content-type 400；
- 体解析：form 多值同名键（多选）、JSON 两种形态、空提交。
真实数据用例只做廉价不变式（物理高中卷跑通全环）。
"""
import os
import re

import pytest
from fastapi.testclient import TestClient

from xuexing.exam import (
    ExamError,
    ExamSession,
    ExamSessions,
    SessionNotFound,
    parse_submission_body,
)
from xuexing.grading import grade_to_response
from xuexing.itembank import ItemBank
from xuexing.kpgraph import kpgraph_from_dict
from xuexing.paper_render import FORBIDDEN_TOKENS, check_html_tag_balance, redline_report
from xuexing.server import create_app
from xuexing.types import Item

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

_Q_BLOCK_RE = re.compile(r'<div class="question" id="q(\d+)">')
_CTRL_NAME_RE = re.compile(r'name="(item_\d+)"')

_SECRET = "【绝密】never-show-73512"

# 三段卷：2 道单选（1 正 1 错）+ 1 道多选 + 1 道填空 + 1 道解答 = 5 题 15 分
MINI_SPEC = {
    "id": "spec_exam_demo",
    "subject": "physics",
    "stage": "junior",
    "usage": "final_exam",
    "duration_min": 60,
    "total_points": 15,
    "sections": [
        {"title": "一、选择题", "form": "choice", "count": 2, "points_each": 3},
        {"title": "二、多选题", "form": "multi_select", "count": 1, "points_each": 3},
        {"title": "三、填空题", "form": "fill", "count": 1, "points_each": 3},
        {"title": "四、解答题", "form": "solve", "count": 1, "points_each": 3},
    ],
}

MINI_GRAPH = {
    "knowledge_points": [
        {"id": "kp_a", "name": "力与平衡", "subject": "physics", "grade": 8,
         "cluster": "力学", "prereqs": []},
        {"id": "kp_b", "name": "电路与电容", "subject": "physics", "grade": 8,
         "cluster": "电学", "prereqs": []},
        {"id": "kp_c", "name": "浮力计算", "subject": "physics", "grade": 8,
         "cluster": "力学", "prereqs": ["kp_a"]},
    ]
}


def mini_bank(secret=False) -> ItemBank:  # noqa: D401 — 夹具：5 道题的最小题库
    b = ItemBank()
    leak = _SECRET if secret else "因为所以"
    b.add(Item(id="c1", item_type="choice", form="mcq_single",
               stem="两个大小相等的力平衡时（　　）", answer="B", kps=["kp_a"],
               difficulty=0.3, options=["A. 合力一定为零", "B. 合力为零", "C. 合力最大"],
               solution=leak))
    b.add(Item(id="c2", item_type="choice", form="mcq_single",
               stem="下列关于压力的说法正确的是（　　）", answer="A", kps=["kp_a"],
               difficulty=0.5, options=["A. 压力等于重力", "B. 压力与重力无关", "C. 压力恒为零"],
               solution=leak))
    b.add(Item(id="m1", item_type="choice", form="mcq_multi",
               stem="关于电容（多选）（　　）", answer="A,C", kps=["kp_b"],
               difficulty=0.4, options=["A. C=Q/U", "B. 电容与电荷量成正比", "C. 由电容器本身决定"],
               solution=leak))
    b.add(Item(id="f1", item_type="fill", form="fill_blank",
               stem="物体受到的浮力等于______。", answer="排开液体受到的重力",
               kps=["kp_c"], difficulty=0.4, solution=leak))
    b.add(Item(id="j1", item_type="solve", form="solve",
               stem="简述浮力产生的原因。", answer="液体上下表面压强差",
               kps=["kp_c"], difficulty=0.6, solution=leak))
    return b


def _with_strategies():
    """把 create_app 的 strategies 换成真实策略库（build_plan 需要能选策略）。"""
    from xuexing import load_strategies

    return load_strategies(os.path.join(ROOT, "data", "pedagogy", "strategies.json"))


@pytest.fixture()
def client():
    graph = kpgraph_from_dict(MINI_GRAPH)
    bank = mini_bank()
    app = create_app(bank, graph, _with_strategies(), [],
                     spec_catalog={MINI_SPEC["id"]: MINI_SPEC},
                     stage_bank_loader=lambda subject, stage: bank,
                     subject_graph_loader=lambda subject: graph,
                     exam_sessions=ExamSessions())
    return TestClient(app, follow_redirects=False)


def _start(client, learner="stu-x", **params):
    r = client.get(f"/exam/{MINI_SPEC['id']}/start", params={"learner_id": learner, **params})
    assert r.status_code == 200, r.text[:200]
    return r.headers["X-Exam-Session"], r.text


ALL_CORRECT = {"item_1": "B", "item_2": "A", "item_3": ["A", "C"],
               "item_4": "排开液体受到的重力", "item_5": "液体上下表面压强差"}
# 第 2/3 题写错（3+3 分），其余正确 -> 得分 9/15
HALF_WRONG = {"item_1": "B", "item_2": "B", "item_3": ["A", "B"],
              "item_4": "排开液体受到的重力", "item_5": "液体上下表面压强差"}


# ---------- 起卷 ----------

def test_start_returns_answerable_paper(client):
    session, doc = _start(client)
    assert session.startswith("exam-")
    assert doc.startswith("<!DOCTYPE html>") and 'charset="utf-8"' in doc
    # 题块号 1..5 连续，与卷结构一致
    assert [int(m) for m in _Q_BLOCK_RE.findall(doc)] == [1, 2, 3, 4, 5]
    # 每题恰一组作答控件，控件名与题号一一对应
    names = _CTRL_NAME_RE.findall(doc)
    assert set(names) == {f"item_{i}" for i in range(1, 6)}
    # 控件类型：单选 radio、多选 checkbox、填空 input、解答 textarea
    assert doc.count('type="radio"') == 6      # 2 题 × 3 选项
    assert doc.count('type="checkbox"') == 3   # 多选 1 题 × 3 选项
    assert 'class="q-input" type="text" name="item_4"' in doc
    assert '<textarea class="q-input q-textarea" name="item_5"' in doc
    # learner 回显 + form action 指向本会话
    assert "考生 <strong class=\"learner\">stu-x</strong>" in doc
    assert f'action="/exam/{session}/submit"' in doc
    assert "共 5 题" in doc and "满分 15 分" in doc
    assert check_html_tag_balance(doc) == []


def test_start_learner_id_required_400(client):
    r = client.get(f"/exam/{MINI_SPEC['id']}/start", params={"learner_id": "   "})
    assert r.status_code == 400
    assert client.get(f"/exam/{MINI_SPEC['id']}/start").status_code == 400


def test_start_unknown_spec_404(client):
    assert client.get("/exam/nope/start", params={"learner_id": "a"}).status_code == 404


def test_start_bad_query_422(client):
    r = client.get(f"/exam/{MINI_SPEC['id']}/start",
                   params={"learner_id": "a", "seed": "abc"})
    assert r.status_code == 422


def test_exam_page_redline_no_answer_leak():
    """红线：学生卷页绝不带 answer/solution（词根 + 值级，同打印版）。"""
    graph = kpgraph_from_dict(MINI_GRAPH)
    bank = mini_bank(secret=True)
    app = create_app(bank, graph, _with_strategies(), [],
                     spec_catalog={MINI_SPEC["id"]: MINI_SPEC},
                     stage_bank_loader=lambda s, st: bank,
                     subject_graph_loader=lambda s: graph)
    doc = TestClient(app).get(f"/exam/{MINI_SPEC['id']}/start",
                              params={"learner_id": "a"}).text
    assert _SECRET not in doc
    for tok in FORBIDDEN_TOKENS:
        assert tok.lower() not in doc.lower(), tok
    # 内核红线自检：干净产物零报告（渲染层自带的扫描器，非本测试的断言拼凑）
    from xuexing.paper_by_spec import generate_paper_by_spec

    paper = generate_paper_by_spec(bank, MINI_SPEC, seed=42, spec_id=MINI_SPEC["id"])
    assert redline_report(paper, bank, doc, "") == []


# ---------- 提交判分 ----------

def test_submit_form_303_and_full_score(client):
    session, _ = _start(client, "stu-all")
    r = client.post(f"/exam/{session}/submit", data=ALL_CORRECT)
    assert r.status_code == 303
    assert r.headers["location"] == f"/exam/{session}/report.html"
    doc = client.get(f"/exam/{session}/report.html").text
    assert "答对 5 题" in doc and "答错 0 题" in doc
    assert doc.count("✔ 正确") == 5 and "✘ 错误" not in doc
    assert "<strong>15</strong> / 15 分" in doc


def test_submit_json_summary_and_scoring(client):
    session, _ = _start(client, "stu-half")
    r = client.post(f"/exam/{session}/submit", json=HALF_WRONG)
    assert r.status_code == 200
    out = r.json()
    assert out["mode"] == "json" and out["learner_id"] == "stu-half"
    assert out["correct_count"] == 3 and out["wrong_count"] == 2
    assert out["score"] == 9.0 and out["total_points"] == 15.0
    assert out["report_url"] == f"/exam/{session}/report.html"
    assert out["weak_points"], "半错卷应产出薄弱知识点"


def test_submit_grading_matches_grade_kernel(client):
    """判分口径 = /grade：逐题判定与 grading.grade_to_response 逐条一致。

    做法：同库同答案送 POST /grade（批量）与作答环提交，两边的 correct 序列
    必须逐位相同——这正是「不许另造平行判分实现」的可观察证据。
    """
    session, _ = _start(client, "stu-parity")
    out = client.post(f"/exam/{session}/submit", json=HALF_WRONG).json()
    bank = mini_bank()
    flat = ["c1", "c2", "m1", "f1", "j1"]
    answers = []
    for key, item_id in zip(sorted(HALF_WRONG), flat):
        given = HALF_WRONG[key]
        answers.append({"item_id": item_id,
                        "learner_answer": ",".join(given) if isinstance(given, list) else given})
    graded = client.post("/grade", json={"answers": answers}).json()["results"]
    expect = [g["correct"] for g in graded]
    assert out["correct_count"] == sum(expect), (out["correct_count"], expect)
    # 报告页逐题标记：页面上 ✔ 的个数 == /grade 判对的题数
    doc = client.get(f"/exam/{session}/report.html").text
    assert doc.count("✔ 正确") == sum(expect) == out["correct_count"]
    assert doc.count("✘ 错误") == len(expect) - sum(expect) == out["wrong_count"]


def test_submit_multi_select_checkbox_values_joined():
    """多选同名多值按 ',' 连接后送内核（与 _MULTI_SEP_RE 分隔符族一致）。"""
    bank = mini_bank()
    assert grade_to_response(bank.get("m1"), "A,C").correct is True
    assert grade_to_response(bank.get("m1"), "A,B").correct is False


def test_submit_persists_profile_and_plan(client):
    """交卷后 /profile 与 /plan 立即反映本卷（与 POST /responses 同一 store 序列）。"""
    session, _ = _start(client, "stu-store")
    client.post(f"/exam/{session}/submit", json=HALF_WRONG)
    prof = client.get("/learners/stu-store/profile")
    assert prof.status_code == 200
    body = prof.json()
    assert body["learner_id"] == "stu-store"
    # kp_c（填空+解答，两题都对）掌握度高于 kp_a（选择一错一对）
    assert body["mastery"]["kp_c"] > body["mastery"]["kp_a"], body["mastery"]
    assert body["evidence"]["kp_c"] == 2, body["evidence"]
    plan = client.get("/learners/stu-store/plan")
    assert plan.status_code == 200 and plan.json()["learner_id"] == "stu-store"


# ---------- 报告页 ----------

def test_report_sections_and_marks(client):
    session, _ = _start(client, "stu-rep")
    client.post(f"/exam/{session}/submit", json=HALF_WRONG)
    r = client.get(f"/exam/{session}/report.html")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    doc = r.text
    for section in ("一、逐题对错", "二、知识点掌握更新", "三、薄弱知识点", "四、下一步学习建议"):
        assert section in doc, section
    assert doc.count("✔ 正确") == 3 and doc.count("✘ 错误") == 2
    # 掌握更新表给出 before/after 与薄弱点；建议节给出策略与练习题
    assert "掌握度" in doc and "策略" in doc
    assert "kp_a" in doc and "力与平衡" in doc
    assert check_html_tag_balance(doc) == []


def test_report_weak_points_nonempty_after_wrong_answers(client):
    session, _ = _start(client, "stu-weak")
    out = client.post(f"/exam/{session}/submit", json=HALF_WRONG).json()
    doc = client.get(f"/exam/{session}/report.html").text
    assert out["weak_points"], "半错卷应产出薄弱知识点"
    for kp_id in out["weak_points"]:
        assert kp_id in doc, f"薄弱知识点 {kp_id} 不在报告页"


def test_report_before_after_mastery_on_second_submit(client):
    """第二次交卷：报告的「诊断前」取自被覆盖的旧画像（掌握更新而非孤立快照）。"""
    s1, _ = _start(client, "stu-two")
    client.post(f"/exam/{s1}/submit", json=HALF_WRONG)
    s2, _ = _start(client, "stu-two")
    client.post(f"/exam/{s2}/submit", json=HALF_WRONG)
    doc = client.get(f"/exam/{s2}/report.html").text
    assert "首次诊断" not in doc, "第二次交卷不应显示首次诊断"
    assert "诊断前" in doc and "诊断后" in doc


def test_report_escapes_hostile_answer(client):
    """敌意作答（HTML 片段）按字面转义，绝不产生可执行标记。"""
    session, _ = _start(client, "stu-xss")
    hostile = dict(ALL_CORRECT, item_4="<script>alert(1)</script>")
    client.post(f"/exam/{session}/submit", json=hostile)
    doc = client.get(f"/exam/{session}/report.html").text
    assert "<script>alert(1)</script>" not in doc
    assert "&lt;script&gt;" in doc
    assert check_html_tag_balance(doc) == []


# ---------- 会话边界 ----------

def test_unknown_session_404(client):
    assert client.get("/exam/exam-nope/report.html").status_code == 404
    assert client.post("/exam/exam-nope/submit", data={}).status_code == 404


def test_expired_session_404():
    """过期会话：report 与 submit 均 404（构造确定性过期态：TTL=0）。"""
    graph = kpgraph_from_dict(MINI_GRAPH)
    bank = mini_bank()
    app = create_app(bank, graph, _with_strategies(), [],
                     spec_catalog={MINI_SPEC["id"]: MINI_SPEC},
                     stage_bank_loader=lambda s, st: bank,
                     subject_graph_loader=lambda s: graph,
                     exam_sessions=ExamSessions(ttl_seconds=0.0))
    c = TestClient(app, follow_redirects=False)
    session = c.get(f"/exam/{MINI_SPEC['id']}/start",
                    params={"learner_id": "a"}).headers["X-Exam-Session"]
    assert c.get(f"/exam/{session}/report.html").status_code == 404
    assert c.post(f"/exam/{session}/submit", data=ALL_CORRECT).status_code == 404


def test_expired_session_dropped_from_table():
    """过期即从表中摘除：再取仍是同一 404（不复活、不重放）。"""
    now = [100.0]
    sessions = ExamSessions(ttl_seconds=10.0, clock=lambda: now[0])
    s = ExamSession(session_id="e1", org_id="default", learner_id="a", spec_id="sp",
                    seed=42, difficulty_target=0.5, paper={})
    sessions.create(None, s)
    assert sessions.get("e1", None) is s
    now[0] = 105.0                     # TTL 内
    assert sessions.get("e1", None) is s
    now[0] = 111.0                     # 超 TTL
    with pytest.raises(SessionNotFound):
        sessions.get("e1", None)
    assert sessions.count() == 0       # 过期即摘除，不留残骸


def test_cross_org_session_404(client):
    session = client.get(f"/exam/{MINI_SPEC['id']}/start",
                         params={"learner_id": "a"},
                         headers={"X-Org-Id": "org-a"}).headers["X-Exam-Session"]
    assert client.get(f"/exam/{session}/report.html",
                      headers={"X-Org-Id": "org-b"}).status_code == 404
    assert client.get(f"/exam/{session}/report.html",
                      headers={"X-Org-Id": "org-a"}).status_code == 409  # 未提交


def test_double_submit_409(client):
    session, _ = _start(client, "stu-dup")
    assert client.post(f"/exam/{session}/submit", data=ALL_CORRECT).status_code == 303
    assert client.post(f"/exam/{session}/submit", data=ALL_CORRECT).status_code == 409


def test_report_before_submit_409(client):
    session, _ = _start(client, "stu-early")
    assert client.get(f"/exam/{session}/report.html").status_code == 409


def test_bad_content_type_400(client):
    session, _ = _start(client, "stu-ct")
    r = client.post(f"/exam/{session}/submit", content=b"x",
                    headers={"content-type": "application/xml"})
    assert r.status_code == 400


def test_empty_submit_is_all_wrong(client):
    """空提交 = 全卷未作答：仍交卷成功，逐题判错、得分 0。"""
    session, _ = _start(client, "stu-blank")
    r = client.post(f"/exam/{session}/submit", data={})
    assert r.status_code == 303
    doc = client.get(f"/exam/{session}/report.html").text
    assert doc.count("✘ 错误") == 5 and "答对 0 题" in doc


def test_missing_item_in_bank_400(client):
    """题不在库 → 400（fail-closed），会话保持 open：修正后可重试交卷。"""
    app = client.app
    session = client.get(f"/exam/{MINI_SPEC['id']}/start",
                         params={"learner_id": "stu-ghost"}).headers["X-Exam-Session"]
    # 起卷后让第 1 题在题库中消失（模拟题库热更丢题）——判分必须 400，绝不降级
    live = app.state.exam_sessions._sessions[session]
    secs = live.paper["sections"]
    first = secs[0]["questions"][0]
    live.paper = dict(live.paper, sections=[
        dict(secs[0], questions=[dict(first, item_id="ghost")] + secs[0]["questions"][1:]),
    ] + secs[1:])
    r = client.post(f"/exam/{session}/submit", data=ALL_CORRECT)
    assert r.status_code == 400, r.status_code
    assert "not in bank" in r.json()["detail"], r.json()
    # 会话仍是 open：卷修好后同一会话可正常交卷
    assert live.status == "open"
    assert client.get(f"/exam/{session}/report.html").status_code == 409


# ---------- 内核层单测（不经 HTTP） ----------

def test_grade_submission_ghost_item_raises():
    from xuexing.exam import grade_submission

    paper = {"sections": [{"questions": [{"question_no": 1, "item_id": "ghost",
                                          "points": 3}]}]}
    sess = ExamSession(session_id="e", org_id="default", learner_id="a", spec_id="sp",
                       seed=1, difficulty_target=0.5, paper=paper)
    with pytest.raises(ExamError, match="not in bank"):
        grade_submission(sess, paper, mini_bank(), {})


def test_parse_submission_body_form_multi_value():
    raw, mode = parse_submission_body(
        b"item_1=A&item_3=A&item_3=C&item_4=x", "application/x-www-form-urlencoded")
    assert mode == "form"
    assert raw == {"item_1": ["A"], "item_3": ["A", "C"], "item_4": ["x"]}


def test_parse_submission_body_json_shapes():
    raw, mode = parse_submission_body(b'{"item_1": "A"}', "application/json")
    assert mode == "json" and raw == {"item_1": ["A"]}
    raw, mode = parse_submission_body(b'{"answers": {"3": ["A", "C"]}}', "application/json")
    assert mode == "json" and raw == {"item_3": ["A", "C"]}
    # 数字作答按十进制字面（JSON 数字不带引号也收）
    raw, _ = parse_submission_body(b'{"item_4": 12.5}', "application/json")
    assert raw == {"item_4": ["12.5"]}


def test_parse_submission_body_rejects_bad_shapes():
    with pytest.raises(ExamError):
        parse_submission_body(b"[1,2]", "application/json")   # 非对象
    with pytest.raises(ExamError):
        parse_submission_body(b'"hi"', "application/json")     # 非对象
    with pytest.raises(ExamError):
        parse_submission_body(b'{"answers": 5}', "application/json")  # answers 非对象
    with pytest.raises(ExamError):
        parse_submission_body(b"{bad", "application/json")    # 非法 JSON
    with pytest.raises(ExamError):
        parse_submission_body(b"x", "application/xml")        # 不支持的 content-type
    with pytest.raises(ExamError):
        parse_submission_body(b'{"item_1": {"a": 1}}', "application/json")  # 值非标量
    # 空体 = 未作答，不抛（与空 form 体同语义）
    assert parse_submission_body(b"", "") == ({}, "form")
    assert parse_submission_body(b"{}", "application/json") == ({}, "json")


# ---------- 真实数据廉价不变式 ----------

def test_exam_loop_real_spec_phy_hs_final():
    from xuexing.paper_by_spec import load_spec_catalog, load_stage_bank

    catalog = load_spec_catalog(os.path.join(ROOT, "data", "curriculum", "paper_specs.json"))
    data_dir = os.path.join(ROOT, "data")
    bank = load_stage_bank(data_dir, "physics", "high")[0]
    app = create_app(None, None, _with_strategies(), [],
                     spec_catalog=catalog,
                     stage_bank_loader=lambda s, st: load_stage_bank(data_dir, s, st)[0],
                     exam_sessions=ExamSessions())
    c = TestClient(app, follow_redirects=False)
    r = c.get("/exam/spec_phy_hs_final/start", params={"learner_id": "real-1", "seed": 42})
    assert r.status_code == 200, r.text[:200]
    session = r.headers["X-Exam-Session"]
    doc = r.text
    n_q = len(set(_CTRL_NAME_RE.findall(doc)))
    posted = c.post("/papers/by-spec", json={"spec_id": "spec_phy_hs_final",
                                             "seed": 42}).json()
    assert n_q == posted["question_count"] == 16
    assert check_html_tag_balance(doc) == []
    # 全对提交：得分满分、报告页逐题全对
    payload = {}
    for sec in posted["sections"]:
        for q in sec["questions"]:
            payload[f"item_{q['question_no']}"] = bank.get(q["item_id"]).answer
    sub = c.post(f"/exam/{session}/submit", json=payload)
    assert sub.status_code == 200, sub.text[:300]
    assert sub.json()["correct_count"] == 16, sub.json()
    rep = c.get(f"/exam/{session}/report.html").text
    assert "答对 16 题" in rep and "✘ 错误" not in rep
