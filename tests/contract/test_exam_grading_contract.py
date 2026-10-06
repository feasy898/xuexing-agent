"""契约：教师批改端 /exam/{session}/pending + /exam/{session}/grade-subjective。

钉住（自闭式夹具，不依赖 data/）：
- pending 清单：未提交 409；只列**待批改**题（客观题不在清单）；题面/学生作答/
  分值/参考答案/评分要点（题库 solution 字段，「评分要点字段若有」的落点）/
  知识点字段齐备；全批完 → 诚实空表；
- grade-subjective：入总分（报告页刷新即见）、入画像证据（/profile 的
  evidence/mastery 变化）、按达标线（MASTERY_TARGET=0.65 得分率）记对/错；
- 批改终审不静默覆盖：重复批改 409、批已自动判分的客观题 409；
- 参数门：题号不在本卷 400、给分越界（<0 / >points / 非有限数）400；
- 全环：start → submit → pending → grade → report/profile/plan 一条链上
  总分与画像的**变化量**断言（批改前 vs 批改后）；
- 内核面（exam_loop.apply_subjective_grade / pending_payload）：0.65 边界、
  未交卷拒批、评语类型守卫。

真实实卷用例与门在 tests/unit/test_exam_loop.py 与 tools/check_exam_loop.py
（§10）；本文件与其同一套自闭式夹具风格（spec 2 单选 3 分 + 1 填空 2 分 +
1 解答 5 分 = 15 分）。
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from xuexing.exam_loop import (
    ExamAlreadyGraded,
    ExamLoopError,
    MASTERY_TARGET,
    apply_subjective_grade,
    pending_payload,
)
from xuexing.itembank import ItemBank
from xuexing.kpgraph import KPGraph
from xuexing.pedagogy import StrategyLibrary
from xuexing.server import create_app
from xuexing.types import Item, KnowledgePoint, Strategy

_SECRET_SOLUTION = "【评分要点】step-1 列式 step-2 计算，绝密标记 47112"

# 与 test_exam_loop_contract 同构的卷型：客观题 2×3+2=8 分，主观题解答 1×5 分
# 合计 13 分（V8：Σcount×points_each == total_points，错了出不了卷）
_SPEC = {
    "id": "spec_grade_demo",
    "subject": "demo",
    "stage": "junior",
    "usage": "final_exam",
    "duration_min": 60,
    "total_points": 13,
    "sections": [
        {"title": "一、选择题", "form": "choice", "count": 2, "points_each": 3},
        {"title": "二、填空题", "form": "fill", "count": 1, "points_each": 2},
        {"title": "三、解答题", "form": "solve", "count": 1, "points_each": 5},
    ],
}


@pytest.fixture
def bank():
    b = ItemBank()
    b.add(Item(id="c1", item_type="choice", stem="单选一", answer="A", kps=["a"],
               difficulty=0.5, options=["A. x", "B. y"], form="mcq_single"))
    b.add(Item(id="c2", item_type="choice", stem="单选二", answer="B", kps=["b"],
               difficulty=0.5, options=["A. x", "B. y"], form="mcq_single"))
    b.add(Item(id="f1", item_type="fill", stem="填空", answer="50", kps=["b"],
               difficulty=0.5, form="fill_blank"))
    b.add(Item(id="s1", item_type="solve", stem="解答题面", answer="【标答】42",
               kps=["c"], difficulty=0.5, form="solve", solution=_SECRET_SOLUTION))
    b.add(Item(id="c3", item_type="choice", stem="备用单选", answer="A", kps=["c"],
               difficulty=0.5, options=["A. x", "B. y"], form="mcq_single"))
    return b


@pytest.fixture
def graph():
    g = KPGraph()
    g.add_kp(KnowledgePoint(id="a", name="甲", subject="demo", grade=8, cluster="c1"))
    g.add_kp(KnowledgePoint(id="b", name="乙", subject="demo", grade=8, cluster="c1",
                            prereqs=["a"]))
    g.add_kp(KnowledgePoint(id="c", name="丙", subject="demo", grade=8, cluster="c2",
                            prereqs=["b"]))
    for kp in g.kps():
        for p in kp.prereqs:
            g.add_edge(p, kp.id)
    return g


@pytest.fixture
def strategies():
    lib = StrategyLibrary()
    lib.add(Strategy(id="s_mid", name="中等策略", description="d",
                     priority=8, evidence="e", mastery_gte=0.4, mastery_lt=0.65))
    lib.add(Strategy(id="s_high", name="高掌握策略", description="d",
                     priority=6, evidence="e", mastery_gte=0.65))
    return lib


@pytest.fixture
def client(bank, graph, strategies):
    catalog = {_SPEC["id"]: _SPEC}
    return TestClient(create_app(
        bank, graph, strategies, None,
        spec_catalog=catalog,
        stage_bank_loader=lambda subject, stage: bank,
        stage_graph_loader=lambda subject: graph,
    ))


def _start(client, learner="kid-1"):
    r = client.get("/exam/spec_grade_demo/start",
                   params={"learner_id": learner, "format": "json"})
    assert r.status_code == 200, r.text
    return r.json()


def _submit_objective_all_right(client, sid):
    """客观题全对 + 解答题写一段作答（成为待批改题）。"""
    answers = {"item_1": "A", "item_2": "B", "item_3": "50", "item_4": "我的解答过程"}
    r = client.post(f"/exam/{sid}/submit", json={"answers": answers},
                    follow_redirects=False)
    assert r.status_code == 303, r.text
    return answers


_OBJ_TOTAL = 8.0   # 客观题合计（2×3 + 2）
_SOLVE_PTS = 5.0   # 解答题分值
_SOLVE_NO = 4      # 解答题的题号（装订后小题号连续，客观题在前）


def test_pending_before_submit_409(client):
    sid = _start(client)["session_id"]
    r = client.get(f"/exam/{sid}/pending")
    assert r.status_code == 409
    assert "not submitted" in r.json()["detail"]


def test_pending_lists_only_subjective_with_rubric(client):
    """清单只含待批改题；题面/作答/分值/参考答案/评分要点/知识点齐备。"""
    sid = _start(client)["session_id"]
    _submit_objective_all_right(client, sid)
    r = client.get(f"/exam/{sid}/pending")
    assert r.status_code == 200
    pend = r.json()
    assert pend["n_pending"] == 1 and len(pend["items"]) == 1
    assert pend["pending_points"] == _SOLVE_PTS
    row = pend["items"][0]
    assert row["question_no"] == _SOLVE_NO
    assert row["item_id"] == "s1" and row["item_type"] == "solve"
    assert row["stem"] == "解答题面"
    assert row["learner_answer"] == "我的解答过程"
    assert row["points"] == _SOLVE_PTS
    assert row["expected"] == "【标答】42"
    assert row["rubric"] == _SECRET_SOLUTION  # 评分要点 = 题库 solution 字段
    assert row["kps"] == ["c"]
    # 客观题不进清单（已自动判分）
    assert all(it["item_id"] != "c1" for it in pend["items"])


def test_pending_empty_after_all_graded(client):
    """全批完 → 诚实空表（n_pending=0、items=[]），不是报错也不是假待办。"""
    sid = _start(client)["session_id"]
    _submit_objective_all_right(client, sid)
    r = client.post(f"/exam/{sid}/grade-subjective",
                    json={"question_no": _SOLVE_NO, "score": _SOLVE_PTS,
                          "comment": "满分"})
    assert r.status_code == 200
    pend = client.get(f"/exam/{sid}/pending").json()
    assert pend["n_pending"] == 0 and pend["items"] == []
    assert pend["pending_points"] == 0


def test_grade_subjective_full_marks_and_report_refresh(client):
    """满分批改 → correct、总分=客观+教师分、报告页刷新可见教师批改。"""
    sid = _start(client)["session_id"]
    _submit_objective_all_right(client, sid)
    r = client.post(f"/exam/{sid}/grade-subjective",
                    json={"question_no": _SOLVE_NO, "score": _SOLVE_PTS,
                          "comment": "步骤完整，给满分。"})
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["correct"] is True
    assert out["score"] == _SOLVE_PTS and out["points"] == _SOLVE_PTS
    assert out["comment"] == "步骤完整，给满分。"
    assert out["total_score"] == _OBJ_TOTAL + _SOLVE_PTS
    assert out["n_pending"] == 0 and out["pending_points"] == 0
    assert out["report_url"] == f"/exam/{sid}/report.html"
    rep = client.get(f"/exam/{sid}/report.html").text
    assert f"{_OBJ_TOTAL + _SOLVE_PTS:g}" in rep           # 刷新后的总分上页
    assert "教师批改 5/5 分" in rep                        # 教师批改判定上页
    assert "评语：步骤完整，给满分。" in rep                # 评语上页
    assert "主观题已经教师批改 1 题" in rep                 # 得分构成说明
    assert "待批改" not in rep                              # 不再有「待批改」


def test_grade_partial_below_threshold_counts_wrong(client):
    """3/5=0.6 < 达标线 0.65 → 证据记错（不给对），但得分仍入总分。"""
    sid = _start(client)["session_id"]
    _submit_objective_all_right(client, sid)
    r = client.post(f"/exam/{sid}/grade-subjective",
                    json={"question_no": _SOLVE_NO, "score": 3})
    assert r.status_code == 200
    out = r.json()
    assert out["correct"] is False
    assert out["total_score"] == _OBJ_TOTAL + 3
    rep = client.get(f"/exam/{sid}/report.html").text
    assert "✗ 教师批改 3/5 分" in rep


def test_full_loop_profile_and_plan_change_after_grading(client):
    """全环：start → submit → pending → grade → 总分/画像/计划一条链的变化量。

    批改前：解答题不进画像（correct=None），KP 丙无证据、掌握度=先验；
    批改后（满分）：丙 evidence +1、mastery 上升、/plan 仍可算。
    """
    sid = _start(client, learner="loop-kid")["session_id"]
    _submit_objective_all_right(client, sid)
    prof_before = client.get("/learners/loop-kid/profile").json()
    assert prof_before["evidence"].get("c", 0) == 0  # 主观题没进画像

    r = client.post(f"/exam/{sid}/grade-subjective",
                    json={"question_no": _SOLVE_NO, "score": _SOLVE_PTS})
    assert r.status_code == 200
    prof_after = client.get("/learners/loop-kid/profile").json()
    assert prof_after["evidence"]["c"] == prof_before["evidence"].get("c", 0) + 1
    assert prof_after["mastery"]["c"] > prof_before["mastery"]["c"]
    # 闭环的另一半也活着：/plan 用更新后的画像还能出计划
    assert client.get("/learners/loop-kid/plan").status_code == 200
    # 批改过的会话报告可复核
    assert client.get(f"/exam/{sid}/report.html").status_code == 200


def test_regrade_rejected_409(client):
    sid = _start(client)["session_id"]
    _submit_objective_all_right(client, sid)
    first = client.post(f"/exam/{sid}/grade-subjective",
                        json={"question_no": _SOLVE_NO, "score": 4})
    assert first.status_code == 200
    again = client.post(f"/exam/{sid}/grade-subjective",
                        json={"question_no": _SOLVE_NO, "score": _SOLVE_PTS})
    assert again.status_code == 409
    assert "already graded by teacher" in again.json()["detail"]
    # 分数没被二次批改覆盖
    assert client.get(f"/exam/{sid}/report.html").text.count("教师批改 4/5 分") == 1


def test_grade_objective_question_409(client):
    sid = _start(client)["session_id"]
    _submit_objective_all_right(client, sid)
    r = client.post(f"/exam/{sid}/grade-subjective",
                    json={"question_no": 1, "score": 3})
    assert r.status_code == 409
    assert "auto-graded" in r.json()["detail"]


@pytest.mark.parametrize("payload", [
    {"question_no": 99, "score": 1},            # 题号不在本卷
    {"question_no": _SOLVE_NO, "score": -0.5},  # 负分
    {"question_no": _SOLVE_NO, "score": 5.5},   # 超过该题满分
])
def test_grade_bad_request_400(client, payload):
    sid = _start(client)["session_id"]
    _submit_objective_all_right(client, sid)
    r = client.post(f"/exam/{sid}/grade-subjective", json=payload)
    assert r.status_code == 400


def test_grade_non_finite_score_400(client):
    """1e999 是合法 JSON 数字但溢出成 inf——必须被内核拒成 400，不落账。"""
    sid = _start(client)["session_id"]
    _submit_objective_all_right(client, sid)
    r = client.post(f"/exam/{sid}/grade-subjective",
                    content='{"question_no": 4, "score": 1e999}',
                    headers={"Content-Type": "application/json"})
    assert r.status_code == 400
    # 账本没被 inf 污染：正常批改仍然 200，总分不含 inf
    r2 = client.post(f"/exam/{sid}/grade-subjective",
                     json={"question_no": _SOLVE_NO, "score": _SOLVE_PTS})
    assert r2.status_code == 200 and r2.json()["total_score"] == _OBJ_TOTAL + _SOLVE_PTS


def test_grade_before_submit_409(client):
    sid = _start(client)["session_id"]
    r = client.post(f"/exam/{sid}/grade-subjective",
                    json={"question_no": _SOLVE_NO, "score": 5})
    assert r.status_code == 409


def test_unknown_session_404(client):
    assert client.get("/exam/nope/pending").status_code == 404
    assert client.post("/exam/nope/grade-subjective",
                       json={"question_no": 1, "score": 1}).status_code == 404


# ---------------- 内核面（无 HTTP）：边界与守卫 ----------------

def _kernel_session() -> dict:
    """最小已交卷会话（1 道待批改解答题，5 分，KP c）。"""
    return {
        "session_id": "s-kernel", "learner_id": "k", "spec_id": "x",
        "title": "t", "submitted": True,
        "graded": {"score": 0.0, "responses": [], "items": [
            {"question_no": 1, "item_id": "s1", "points": 5.0, "item_type": "solve",
             "stem": "题", "expected": "答", "learner_answer": "作答",
             "correct": None, "graded": False, "kps": ["c"]},
        ]},
    }


def test_kernel_boundary_065_ratio():
    """得分率恰在达标线（0.65）→ 记对；差一点 → 记错。5 分题：3.25 对、3.2 错。"""
    resp = apply_subjective_grade(_kernel_session(), 1, 5.0 * MASTERY_TARGET)
    assert resp.correct is True
    resp2 = apply_subjective_grade(_kernel_session(), 1, 3.2)
    assert resp2.correct is False


def test_kernel_full_marks_appends_response_and_updates_ledger():
    session = _kernel_session()
    resp = apply_subjective_grade(session, 1, 5.0, comment="好")
    assert resp.correct is True and resp.item_id == "s1"
    assert session["graded"]["score"] == 5.0
    assert len(session["graded"]["responses"]) == 1
    row = session["graded"]["items"][0]
    assert row["graded"] is True and row["teacher_score"] == 5.0
    assert row["teacher_comment"] == "好"


def test_kernel_rejects_before_submit_and_bad_args():
    session = {"session_id": "s2", "learner_id": "k", "spec_id": "x",
               "title": "t", "submitted": False}
    with pytest.raises(ExamLoopError):
        pending_payload(session)
    with pytest.raises(ExamLoopError):
        apply_subjective_grade(session, 1, 1)
    session["submitted"] = True
    session["graded"] = _kernel_session()["graded"]
    with pytest.raises(ExamLoopError):
        apply_subjective_grade(session, 1, 1, comment=123)  # 评语非 str
    with pytest.raises(ExamLoopError):
        apply_subjective_grade(session, True, 1)            # 题号非 int（bool 拒）
    with pytest.raises(ExamLoopError):
        apply_subjective_grade(session, 2, 1)               # 题号不在本卷
    # 真正批入一次后，重复批改 → ExamAlreadyGraded（终审不覆盖）
    apply_subjective_grade(session, 1, 2.0)
    with pytest.raises(ExamAlreadyGraded):
        apply_subjective_grade(session, 1, 5.0)
