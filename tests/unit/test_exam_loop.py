"""单元测试：学生作答闭环（xuexing.exam + /exam/* 三端点 + 作答页渲染）。

自闭式夹具（不依赖 data/）钉住行为契约：
- 开卷 GET /exam/{spec_id}/start：200 text/html、learner 回显、会话号进 form
  action、题块与骨架一致、**作答字段组数 == 题数**（每题恰一组控件；单选/多选
  一组内每选项一个 radio/checkbox，填空一个 text input，解答一个 textarea）；
- 判分：客观题走 grading.grade_to_response（与 POST /grade 逐条同口径），
  solve 等主观题不自动判分、不进得分、不进画像，报告里标「待批改」；
- 提交 POST /exam/{session}/submit：原生 form 与 JSON 两条入口同结果、303 +
  Location 指向报告页；落库走与 /responses 同一个 OrgStore entry，因此
  GET /profile 与 /plan 立即可见；
- 报告 GET /exam/{session}/report.html：逐题对错标记、正确答案/解析只对错题
  展开、知识点掌握更新（本次前 → 后）、薄弱点与下一步学习建议（route 步骤）、
  自包含（无 script/外链）、标签配平；
- 错误契约：未知会话 404、未知卷型 404、空 learner_id 400、越界
  difficulty_target 400、越界题号/非法字段名/JSON 形态 400、重复交卷 409、
  未交卷取报告 409、会话过期 410（ExamStore(ttl=0) 注入）；
- 作答页红线：标答/解析的绝密串绝不进页面（复用 redline_report 同一实现）。
真实数据用例只做廉价不变式：真实初中物理卷跑完整环。
"""
import re

import pytest
from fastapi.testclient import TestClient

from xuexing.exam import (
    AUTO_ITEM_TYPES,
    ExamError,
    ExamStore,
    build_report,
    grade_submission,
    render_report_html,
)
from xuexing.itembank import ItemBank
from xuexing.kpgraph import KPGraph
from xuexing.paper_by_spec import generate_paper_by_spec
from xuexing.paper_render import (
    check_html_tag_balance,
    redline_report,
    render_exam_sheet_html,
    render_paper_text,
)
from xuexing.pedagogy import StrategyLibrary
from xuexing.server import create_app
from xuexing.types import Item, KnowledgePoint, Strategy

_SECRET = "【绝密】exam-73512"

MINI_SPEC = {
    "id": "spec_exam_demo",
    "subject": "physics",
    "stage": "junior",
    "usage": "final_exam",
    "duration_min": 60,
    "total_points": 11,
    "sections": [
        {"title": "一、选择题", "form": "choice", "count": 2, "points_each": 2},
        {"title": "二、填空题", "form": "fill", "count": 1, "points_each": 3},
        {"title": "三、解答题", "form": "solve", "count": 1, "points_each": 4},
    ],
}


def mini_bank(secret=False) -> ItemBank:
    """2 单选 + 1 填空 + 1 解答；secret=True 时标答/解析带绝密串（红线用）。"""
    b = ItemBank()
    ans = _SECRET if secret else "B"
    for i, d in (("c1", 0.2), ("c2", 0.5)):
        b.add(Item(id=i, item_type="choice", stem=f"选择-{i}-（　　）", answer=ans,
                   kps=["kp_lens"], difficulty=d, solution="因为所以",
                   options=["A. 甲", "B. 乙"], form="mcq_single"))
    b.add(Item(id="f1", item_type="fill", stem="填空-速度是 ____", answer=ans,
               kps=["kp_speed"], difficulty=0.4, solution="", form="填空"))
    b.add(Item(id="j1", item_type="solve", stem="解答-求合力", answer=ans,
               kps=["kp_force"], difficulty=0.6, solution="因为所以", form="简答"))
    return b


def mini_graph() -> KPGraph:
    g = KPGraph()
    for kp_id, name, prereq in (("kp_lens", "凸透镜成像", None),
                                ("kp_speed", "速度计算", None),
                                ("kp_force", "力的合成", "kp_speed")):
        g.add_kp(KnowledgePoint(id=kp_id, name=name, subject="physics", grade=8,
                                cluster="力学" if kp_id != "kp_lens" else "光学",
                                prereqs=[prereq] if prereq else []))
        if prereq:
            g.add_edge(prereq, kp_id)
    return g


def mini_strategies() -> StrategyLibrary:
    lib = StrategyLibrary()
    for i, (sid, mastery_lt, name) in enumerate((
            ("st_basic", 0.4, "基础夯实"), ("st_boost", 1.01, "专项突破"))):
        lib.add(Strategy(id=sid, name=name, description=name, priority=10 - i,
                         evidence=f"{name}的教学证据", mastery_lt=mastery_lt))
    return lib


@pytest.fixture
def exam_client():
    """每个用例一个干净 app（会话/画像都是进程内状态，测试间必须隔离）。"""
    app = create_app(mini_bank(), mini_graph(), mini_strategies(), [],
                     spec_catalog={MINI_SPEC["id"]: MINI_SPEC},
                     stage_bank_loader=lambda subject, stage: mini_bank(),
                     subject_graph_loader=lambda subject: mini_graph())
    return TestClient(app)


@pytest.fixture
def paper():
    return generate_paper_by_spec(mini_bank(), MINI_SPEC, seed=42,
                                  spec_id=MINI_SPEC["id"])


def _session(client, learner="stu-1", **params):
    r = client.get(f"/exam/{MINI_SPEC['id']}/start",
                   params={"learner_id": learner, "seed": 42, **params})
    assert r.status_code == 200, r.text[:200]
    m = re.search(r'action="/exam/([0-9a-f]+)/submit"', r.text)
    assert m, "作答页缺少 form action"
    return m.group(1), r.text


# ---------- 开卷 ----------

def test_start_returns_answerable_sheet(exam_client, paper):
    sess, sheet = _session(exam_client, learner="stu-sheet")
    assert sheet.startswith("<!DOCTYPE html>")
    assert "stu-sheet" in sheet and sess in sheet      # learner 与会话号回显
    assert 'action="/exam/%s/submit"' % sess in sheet  # 表单指向提交端点
    assert 'method="post"' in sheet
    # 题块与骨架一致
    nos = [int(m) for m in re.findall(r'<div class="question" id="q(\d+)">', sheet)]
    assert nos == list(range(1, paper["question_count"] + 1)) == [1, 2, 3, 4]
    # 每题恰好一组可提交控件：4 题 -> 4 个不同 name
    fields = re.findall(r'<(?:input|textarea)\b[^>]*\bname="item_(\d+)"', sheet)
    assert set(fields) == {"1", "2", "3", "4"}
    # 控件形态：选择 2 radio/选项、填空 text、解答 textarea
    assert sheet.count('type="radio" name="item_1"') == 2
    assert sheet.count('type="radio" name="item_2"') == 2
    assert '<input type="text" name="item_3"' in sheet
    assert '<textarea name="item_4"' in sheet
    assert check_html_tag_balance(sheet) == []


def test_start_sheet_has_no_answer_material(paper):
    """红线：标答/解析的绝密串绝不进作答页（redline_report 同一实现）。"""
    bank = mini_bank(secret=True)
    paper_s = generate_paper_by_spec(bank, MINI_SPEC, seed=42,
                                     spec_id=MINI_SPEC["id"])
    sheet = render_exam_sheet_html(paper_s, bank, "sess01", "stu-x")
    assert _SECRET not in sheet
    assert not redline_report(paper_s, bank, sheet,
                              render_paper_text(paper_s, bank)), "作答页红线违规"
    for needle in ("<script", "<link", "src=", "http://", "https://"):
        assert needle not in sheet.lower(), needle


def test_start_unknown_spec_404(exam_client):
    assert exam_client.get("/exam/nope/start", params={"learner_id": "x"}).status_code == 404


def test_start_blank_learner_400(exam_client):
    r = exam_client.get(f"/exam/{MINI_SPEC['id']}/start", params={"learner_id": "  "})
    assert r.status_code == 400


def test_start_difficulty_out_of_range_400(exam_client):
    r = exam_client.get(f"/exam/{MINI_SPEC['id']}/start",
                        params={"learner_id": "x", "difficulty_target": 2.0})
    assert r.status_code == 400


def test_start_missing_learner_422(exam_client):
    assert exam_client.get(f"/exam/{MINI_SPEC['id']}/start").status_code == 422


def test_start_each_call_new_session(exam_client):
    a, _ = _session(exam_client, learner="stu-a")
    b, _ = _session(exam_client, learner="stu-b")
    assert a != b


# ---------- 判分内核 ----------

def test_grade_submission_matches_grade_endpoint(paper):
    """客观题判定与 POST /grade 同一函数：同卷同答案 -> 逐条同 correct。"""
    from xuexing.grading import grade_to_response

    bank = mini_bank()
    answers = {1: "B", 2: "A", 3: "错值", 4: "随便写"}
    graded = grade_submission(paper, bank, answers)
    by_no = {rec["question_no"]: rec for rec in graded["items"]}
    for no in (1, 2, 3):
        item = bank.get(paper["sections"][0 if no < 3 else 1]
                        ["questions"][0 if no < 3 else 0]["item_id"])
        assert by_no[no]["correct"] is grade_to_response(item, answers[no]).correct
    # 主观题：待批改、不计分、不产出 Response
    assert by_no[4]["verdict"] == "pending" and by_no[4]["correct"] is None
    assert [r.item_id for r in graded["responses"]] == ["c1", "c2", "f1"]
    assert graded["auto_points"] == 7.0            # 2+2+3
    assert graded["auto_count"] == 3 and graded["auto_correct"] == 1
    assert graded["pending_count"] == 1 and graded["pending_points"] == 4.0
    assert graded["earned"] == 2.0                 # 只有第 1 题对


def test_grade_submission_rejects_bad_answer_type(paper):
    with pytest.raises(ExamError):
        grade_submission(paper, mini_bank(), {1: 5})


def test_grade_submission_blank_is_wrong(paper):
    """未作答/空白 -> 判错（grading 的未作答短路），不 400 不崩溃。"""
    graded = grade_submission(paper, mini_bank(), {})
    assert graded["earned"] == 0.0
    assert all(rec["verdict"] == "wrong"
               for rec in graded["items"] if rec["verdict"] != "pending")


# ---------- 提交 → 报告 ----------

def test_submit_all_correct_lands_profile(exam_client):
    sess, _ = _session(exam_client, learner="stu-perfect")
    form = {"item_1": "B", "item_2": "B", "item_3": "9", "item_4": "解：略"}
    r = exam_client.post(f"/exam/{sess}/submit", data=form, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == f"/exam/{sess}/report.html"
    # 落库：与 /responses 同一 store -> /profile、/plan 立即可见
    prof = exam_client.get("/learners/stu-perfect/profile").json()
    assert prof["evidence"]["kp_lens"] == 2 and prof["evidence"]["kp_speed"] == 1
    assert prof["mastery"]["kp_lens"] > 0.5
    plan = exam_client.get("/learners/stu-perfect/plan")
    assert plan.status_code == 200 and plan.json()["learner_id"] == "stu-perfect"


def test_submit_json_matches_form(exam_client):
    sess_a, _ = _session(exam_client, learner="stu-form")
    sess_b, _ = _session(exam_client, learner="stu-json")
    answers = {"1": "B", "2": "A", "3": "9"}
    form = {f"item_{k}": v for k, v in answers.items()}
    assert exam_client.post(f"/exam/{sess_a}/submit", data=form,
                            follow_redirects=False).status_code == 303
    assert exam_client.post(f"/exam/{sess_b}/submit", json={"answers": answers},
                            follow_redirects=False).status_code == 303
    a = exam_client.get(f"/exam/{sess_a}/report.html").text
    b = exam_client.get(f"/exam/{sess_b}/report.html").text
    # 两份报告除会话号/learner 外同分（学科相同 -> 画像逐字段相同）
    assert "得分 <b>2</b> / 7 分" in a and "得分 <b>2</b> / 7 分" in b
    assert "stu-form" in a and "stu-json" in b


def test_report_page_content(exam_client):
    sess, _ = _session(exam_client, learner="stu-report")
    form = {"item_1": "B", "item_2": "A", "item_3": "9", "item_4": "解：略"}
    exam_client.post(f"/exam/{sess}/submit", data=form, follow_redirects=False)
    page = exam_client.get(f"/exam/{sess}/report.html").text
    assert page.startswith("<!DOCTYPE html>") and check_html_tag_balance(page) == []
    assert "stu-report" in page and MINI_SPEC["id"] in page
    # 逐题对错标记 + 错题展开正确答案/解析
    assert "✓ 正确" in page and "✗ 错误" in page
    assert "正确答案：B" in page and "解析：因为所以" in page
    # 主观题待批改说明 + 原样作答回显
    assert "待教师批改" in page and "解：略" in page
    # 知识点掌握更新（含本次前 → 后）与知识地图
    assert "知识点掌握更新" in page and "凸透镜成像" in page
    assert "知识地图" in page and "光学" in page
    # 薄弱点与下一步学习建议（答错 -> kp_lens 掌握度下压 -> 进弱集）
    assert "薄弱点与下一步学习建议" in page
    assert "专项突破" in page or "基础夯实" in page
    # 自包含
    for needle in ("<script", "<link", "src=", "http://", "https://"):
        assert needle not in page.lower(), needle


def test_report_escapes_html_in_answers(exam_client):
    """学生作答里的标记必须按字面转义，绝不产生可执行标记。"""
    sess, _ = _session(exam_client, learner="stu-xss")
    exam_client.post(f"/exam/{sess}/submit",
                     data={"item_1": "B", "item_3": "<script>alert(1)</script>"},
                     follow_redirects=False)
    page = exam_client.get(f"/exam/{sess}/report.html").text
    assert "<script>alert(1)</script>" not in page
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page


def test_report_before_submit_409(exam_client):
    sess, _ = _session(exam_client, learner="stu-pending")
    assert exam_client.get(f"/exam/{sess}/report.html").status_code == 409


def test_submit_twice_409(exam_client):
    sess, _ = _session(exam_client, learner="stu-twice")
    assert exam_client.post(f"/exam/{sess}/submit", data={},
                            follow_redirects=False).status_code == 303
    assert exam_client.post(f"/exam/{sess}/submit", data={},
                            follow_redirects=False).status_code == 409


def test_submit_unknown_session_404(exam_client):
    assert exam_client.post("/exam/" + "0" * 16 + "/submit", data={},
                            follow_redirects=False).status_code == 404
    assert exam_client.get("/exam/" + "0" * 16 + "/report.html").status_code == 404


def test_submit_bad_answers_400(exam_client):
    sess, _ = _session(exam_client, learner="stu-bad")
    # 越界题号 / 非法字段名 / JSON 缺 answers / JSON 非法体
    assert exam_client.post(f"/exam/{sess}/submit", data={"item_99": "x"},
                            follow_redirects=False).status_code == 400
    assert exam_client.post(f"/exam/{sess}/submit", data={"learner_id": "x"},
                            follow_redirects=False).status_code == 400
    assert exam_client.post(f"/exam/{sess}/submit", json={"nope": 1},
                            follow_redirects=False).status_code == 400
    bad = exam_client.post(f"/exam/{sess}/submit",
                           content="{not json", headers={"content-type": "application/json"},
                           follow_redirects=False)
    assert bad.status_code == 400
    # 前四次都是 400 -> 会话仍是 started，可用
    assert exam_client.post(f"/exam/{sess}/submit", data={},
                            follow_redirects=False).status_code == 303


def test_expired_session_410():
    app = create_app(mini_bank(), mini_graph(), mini_strategies(), [],
                     spec_catalog={MINI_SPEC["id"]: MINI_SPEC},
                     stage_bank_loader=lambda s, st: mini_bank(),
                     subject_graph_loader=lambda s: mini_graph(),
                     exam_store=ExamStore(ttl=0))
    c = TestClient(app)
    sess, _ = _session(c, learner="stu-expired")
    assert c.post(f"/exam/{sess}/submit", data={}, follow_redirects=False).status_code == 410
    assert c.get(f"/exam/{sess}/report.html").status_code == 410


def test_session_org_scopes_landing():
    """开卷带 X-Org-Id -> 画像落该机构域；default 域看不到（/responses 同契约）。"""
    app = create_app(mini_bank(), mini_graph(), mini_strategies(), [],
                     spec_catalog={MINI_SPEC["id"]: MINI_SPEC},
                     stage_bank_loader=lambda s, st: mini_bank(),
                     subject_graph_loader=lambda s: mini_graph())
    c = TestClient(app)
    r = c.get(f"/exam/{MINI_SPEC['id']}/start",
              params={"learner_id": "stu-mt", "seed": 42},
              headers={"X-Org-Id": "org-a"})
    sess = re.search(r'action="/exam/([0-9a-f]+)/submit"', r.text).group(1)
    # 提交不带机构头（原生 form 的真实情形）也写回开卷时的机构
    assert c.post(f"/exam/{sess}/submit", data={"item_1": "B"},
                  follow_redirects=False).status_code == 303
    assert c.get("/learners/stu-mt/profile",
                 headers={"X-Org-Id": "org-a"}).status_code == 200
    assert c.get("/learners/stu-mt/profile").status_code == 404
    assert "org-a" in {o["org_id"] for o in c.get("/orgs").json()["orgs"]}


# ---------- 纯函数层 ----------

def test_build_report_returns_profile_twice_safe(paper):
    """build_report 是纯函数：同输入同输出；第二次给新画像 -> 报告的「本次前」变了。"""
    bank, graph = mini_bank(), mini_graph()
    graded = grade_submission(paper, bank, {1: "B", 2: "A"})
    session = {"session_id": "s1", "learner_id": "stu-p", "org_id": "default",
               "spec_id": MINI_SPEC["id"], "seed": 42, "paper": paper}
    r1, prof1 = build_report(session, graded, None, bank, graph, mini_strategies(),
                             None, today=__import__("datetime").date(2026, 1, 1),
                             now_iso="2026-01-01T00:00:00Z")
    r2, prof2 = build_report(session, graded, None, bank, graph, mini_strategies(),
                             None, today=__import__("datetime").date(2026, 1, 1),
                             now_iso="2026-01-01T00:00:00Z")
    assert r1 == r2 and prof1 is not None and prof1 == prof2
    assert r1["updates"] and all(u["prev"] is None for u in r1["updates"])
    r3, prof3 = build_report(session, graded, prof1, bank, graph, mini_strategies(),
                             None, today=__import__("datetime").date(2026, 1, 1))
    assert all(u["prev"] == prof1.mastery[u["kp_id"]] for u in r3["updates"])
    assert prof3 is not None and prof3.mastery == prof1.mastery  # 证据不叠加的语义另由 diagnose 负责


def test_build_report_no_objective_items_keeps_profile():
    """全主观题作答 -> 不产生新画像（返回 None），报告如实说明（无画像可画）。"""
    bank, graph = mini_bank(), mini_graph()
    solve_only = dict(MINI_SPEC, id="spec_exam_solve_only", total_points=4,
                      sections=[{"title": "三、解答题", "form": "solve",
                                 "count": 1, "points_each": 4}])
    p = generate_paper_by_spec(bank, solve_only, seed=42, spec_id=solve_only["id"])
    graded = grade_submission(p, bank, {1: "解：略"})
    assert graded["responses"] == [] and graded["auto_count"] == 0
    session = {"session_id": "s2", "learner_id": "stu-q", "org_id": "default",
               "spec_id": solve_only["id"], "seed": 42, "paper": p}
    report, new_profile = build_report(session, graded, None, bank, graph,
                                       mini_strategies())
    assert new_profile is None and report["profile_present"] is False
    assert report["updates"] == [] and report["plan"] is None
    assert "待教师批改" in render_report_html(report)


def test_exam_store_expires_and_replaces():
    store = ExamStore(ttl=10)
    session = {"session_id": "a" * 16, "org_id": "default", "created_at": 100.0}
    store.open("default", session)
    got, expired = store.state_of("a" * 16, 105.0)
    assert got is session and expired is False
    got, expired = store.state_of("a" * 16, 111.0)
    assert got is session and expired is True
    assert store.state_of("b" * 16, 105.0) == (None, False)
    # 机构归并：同 session_id 在两个机构各自成域
    store.open("org-b", dict(session, org_id="org-b"))
    assert store.ids("org-b") == ["a" * 16] and store.ids() == ["a" * 16]
    # 非法 TTL / 容量 fail-closed
    with pytest.raises(ExamError):
        ExamStore(ttl=-1)
    with pytest.raises(ExamError):
        ExamStore(max_sessions=0)


def test_exam_store_evicts_oldest():
    store = ExamStore(ttl=100, max_sessions=2)
    for i, ts in enumerate((1.0, 2.0, 3.0)):
        store.open("default", {"session_id": f"{i}" * 16, "org_id": "default",
                               "created_at": ts})
    assert store.ids() == ["1" * 16, "2" * 16]


# ---------- 真实数据环（廉价不变式） ----------

def test_real_paper_full_loop():
    """真实初中物理卷跑完整环：开卷 -> 交卷 -> 报告 -> 画像。"""
    import os

    from xuexing import load_strategies
    from xuexing.kpgraph_subject import load_kpgraph_subject
    from xuexing.paper_by_spec import load_spec_catalog, load_stage_bank

    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    catalog = load_spec_catalog(
        os.path.join(root, "data", "curriculum", "paper_specs.json"))
    raw = catalog["spec_phy_jr_final"]
    bank = load_stage_bank(os.path.join(root, "data"), "physics", "junior")[0]
    graph = load_kpgraph_subject(os.path.join(root, "data", "knowledge"), "physics")
    app = create_app(bank, graph, load_strategies(
        os.path.join(root, "data", "pedagogy", "strategies.json")), [],
        spec_catalog=catalog, stage_bank_loader=lambda s, st: bank,
        subject_graph_loader=lambda s: graph)
    c = TestClient(app)
    r = c.get("/exam/spec_phy_jr_final/start", params={"learner_id": "stu-real",
                                                       "seed": 42})
    assert r.status_code == 200
    paper = generate_paper_by_spec(bank, raw, seed=42, spec_id="spec_phy_jr_final")
    fields = re.findall(r'<(?:input|textarea)\b[^>]*\bname="item_(\d+)"', r.text)
    assert set(fields) == {str(q["question_no"])
                           for s in paper["sections"] for q in s["questions"]}
    sess = re.search(r'action="/exam/([0-9a-f]+)/submit"', r.text).group(1)
    form = {f"item_{q['question_no']}": bank.get(q["item_id"]).answer
            for s in paper["sections"] for q in s["questions"]}
    assert c.post(f"/exam/{sess}/submit", data=form,
                  follow_redirects=False).status_code == 303
    page = c.get(f"/exam/{sess}/report.html").text
    assert check_html_tag_balance(page) == []
    prof = c.get("/learners/stu-real/profile").json()
    n_auto = sum(1 for s in paper["sections"] for q in s["questions"]
                 if bank.get(q["item_id"]).item_type in AUTO_ITEM_TYPES)
    assert sum(prof["evidence"].values()) == n_auto
