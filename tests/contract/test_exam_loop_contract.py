"""契约：学生作答闭环 /exam（开卷 → 提交判分 → 个人报告）。

薄胶水层行为契约：三个端点只做 HTTP 编解码，判分/画像/路线一律等价于既有内核
（**I 内核等价**：同一份作答，端点判定 == 直接调 ``grading.grade_to_response``；
报告里的画像 == ``diagnosis.diagnose``；建议 == ``route.build_plan``）。

自闭式夹具（不依赖 data/）钉住：
- 端点契约：start 200/404/400、paper.html 200/404、submit 303+Location、
  report 200/404/409、过期 410；
- 卷页结构：题块数==题数、**每题恰好一组同名控件** name=item_{no}、选择题
  radio/多选 checkbox/填空 input/解答 textarea、考生回显、自包含、标签配平；
- 学生卷红线：复用 paper_render.redline_report，标答/解析值零泄漏（含 CSS 里
  的数字也不许撞答案值——这条是实测踩出来的：answer "50" 曾撞上 max-width:150mm）；
- 判分口径同源：端点判定 == grade_to_response；全对/半错两份作答的分数与错题集；
- 主观题不假装判：solve 题 correct=None、标「待批改」、不进画像证据、不预扣分；
- 报告四区齐备：对错标记三件套 / 掌握更新 / 薄弱点（中文名）/ 下一步建议；
- 落库：``/learners/{id}/profile`` 能看到本次证据（等价于 /responses 的数据）；
- 错误路径：越界题号 400、非题号键 400、缺 learner_id 400、未知卷型 404；
- 会话过期：注入 TTL=0/可控时钟的 ExamSessionStore，不 sleep 造过期。

真实数据用例（tests/unit/test_exam_loop.py）只做跨学科实卷的廉价不变式。
"""
from datetime import date
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient

from xuexing.diagnosis import diagnose
from xuexing.exam_loop import (
    ExamLoopError,
    ExamSessionExpired,
    ExamSessionNotFound,
    ExamSessionStore,
    collect_answers,
    grade_submission,
    is_objective,
)
from xuexing.grading import grade_to_response
from xuexing.itembank import ItemBank
from xuexing.kpgraph import KPGraph
from xuexing.paper_render import (
    check_html_tag_balance,
    option_label,
    redline_report,
    render_paper_text,
    reply_field_name,
)
from xuexing.pedagogy import StrategyLibrary
from xuexing.route import build_plan
from xuexing.server import create_app
from xuexing.types import Item, KnowledgePoint, Strategy

_SECRET_ANSWER = "【绝密】never-show-73512"
_SECRET_SOLUTION = "【绝密】hide-me-918273"

# 卷型：2 道单选（各 3 分）+ 1 道多选（2 分）+ 1 道填空（2 分）+ 1 道解答（5 分）
# = 15 分、5 道题。客观题合计 10 分（4 题），主观题 5 分——分数断言据此分账。
# 五个大题都在，因为 **multi_select 是独立题型等价类**（只收 mcq_multi），
# 单选大题永远选不到多选题——这正是「同型归并、不跨型兜底」的设计。
_EXAM_SPEC = {
    "id": "spec_exam_demo",
    "subject": "demo",
    "stage": "junior",
    "usage": "final_exam",
    "duration_min": 60,
    "total_points": 15,
    "sections": [
        {"title": "一、选择题", "form": "choice", "count": 2, "points_each": 3},
        {"title": "二、多选题", "form": "multi_select", "count": 1, "points_each": 2},
        {"title": "三、填空题", "form": "fill", "count": 1, "points_each": 2},
        {"title": "四、解答题", "form": "solve", "count": 1, "points_each": 5},
    ],
}
_EXAM_BAD_TOTAL = dict(_EXAM_SPEC, id="spec_exam_badtotal", total_points=11)


@pytest.fixture
def exam_graph():
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
def exam_bank():
    """自闭式题库：2 单选 + 1 多选 + 1 填空 + 1 解答。KP 全部落在 exam_graph 内。"""
    b = ItemBank()
    b.add(Item(id="c1", item_type="choice", stem="题面 <script>alert(1)</script> 甲",
               answer="B", kps=["a"], difficulty=0.5,
               options=["A. 甲 & 乙", "B. 丙 <D>"], form="mcq_single"))
    b.add(Item(id="c2", item_type="choice", stem="多选题面", answer="A,D", kps=["b"],
               difficulty=0.5, form="mcq_multi",
               options=["A. 甲", "B. 乙", "C. 丙", "D. 与 Q、U 无关"]))
    b.add(Item(id="f1", item_type="fill", stem="填空题面", answer="50", kps=["b"],
               difficulty=0.5, form="fill_blank"))
    b.add(Item(id="s1", item_type="solve", stem="解答题面", answer=_SECRET_ANSWER,
               kps=["c"], difficulty=0.5, form="solve", solution=_SECRET_SOLUTION))
    b.add(Item(id="c3", item_type="choice", stem="备用单选", answer="A", kps=["c"],
               difficulty=0.5, options=["A. 甲", "B. 乙"], form="mcq_single"))
    return b


@pytest.fixture
def exam_strategies():
    lib = StrategyLibrary()
    lib.add(Strategy(id="s_low", name="低掌握度策略", description="d",
                     priority=10, evidence="e", mastery_lt=0.4))
    lib.add(Strategy(id="s_mid", name="中等掌握度策略", description="d",
                     priority=8, evidence="e", mastery_gte=0.4, mastery_lt=0.65))
    lib.add(Strategy(id="s_high", name="高掌握度策略", description="d",
                     priority=6, evidence="e", mastery_gte=0.65))
    return lib


@pytest.fixture
def exam_catalog():
    return {s["id"]: s for s in (_EXAM_SPEC, _EXAM_BAD_TOTAL)}


@pytest.fixture
def exam_client(exam_bank, exam_graph, exam_strategies, exam_catalog):
    app = create_app(
        exam_bank, exam_graph, exam_strategies, None,
        spec_catalog=exam_catalog,
        stage_bank_loader=lambda subject, stage: exam_bank,
        stage_graph_loader=lambda subject: exam_graph,
    )
    return TestClient(app)


def _start(client, learner="kid-1", **params):
    params = {"learner_id": learner, "format": "json", **params}
    r = client.get("/exam/spec_exam_demo/start", params=params)
    assert r.status_code == 200, r.text
    return r.json()


def _paper_items(exam_bank):
    """本卷题序 [(question_no, item)]——由真实装订结果导出，测试不硬编码题序。"""
    from xuexing.paper_by_spec import generate_paper_by_spec
    paper = generate_paper_by_spec(
        exam_bank, _EXAM_SPEC, seed=42, difficulty_target=0.5, spec_id="spec_exam_demo")
    return [(q["question_no"], exam_bank.get(q["item_id"]))
            for sec in paper["sections"] for q in sec["questions"]]


def _objective_items(exam_bank):
    return [(no, it) for no, it in _paper_items(exam_bank) if is_objective(it)]


def _correct_answer(item):
    """标答 -> 作答载荷值。

    统一给 str（就是 ``item.answer`` 原样）：判分内核 ``grade_to_response`` 的
    签名是 ``learner_answer: str | None``，多选内部再按分隔符切——所以 str 与
    「表单同名多值」是等价的两种载荷，不必在测试里造 list 绕开内核签名。
    """
    return str(item.answer)


def _row(rep: str, question_no: int) -> str:
    """报告「一、逐题对错」表里第 no 行的 HTML。

    按 ``</tr>`` 切行、而不是按 ``<td class="num">N</td>`` 切——后者在「题号
    恰好等于该题分值」时会切出空片（本夹具第 5 题：题号 5、分值 5，两格文本
    相同）。只在这张表里找，避免撞上掌握度表同名的 num 列。
    """
    items_block = rep.split("一、逐题对错</h2>")[1].split("二、知识点掌握更新")[0]
    head, _, rest = items_block.partition("<tbody")  # 无 tbody 时 head 为空
    for chunk in (rest or items_block).split("</tr>"):
        row = chunk[chunk.rfind("<tr>"):]
        if row.startswith(f'<tr><td class="num">{question_no}</td>'):
            return row
    raise AssertionError(f"报告逐题表里没有第 {question_no} 行")


def _answers_all_right(exam_bank):
    """全对作答（字段名走 reply_field_name，与页面一致）。"""
    return {reply_field_name(no): _correct_answer(it)
            for no, it in _objective_items(exam_bank)}


def _answers_half_wrong(exam_bank):
    """半错：客观题的后一半答错，填空/单选对，解答随便写。"""
    obj = _objective_items(exam_bank)
    wrong = {no for no, _ in obj[len(obj) // 2:]}
    out = {reply_field_name(no): ("答错了" if no in wrong else _correct_answer(it))
           for no, it in obj}
    for no, it in _paper_items(exam_bank):
        if not is_objective(it):
            out[reply_field_name(no)] = "解答内容"
    return out


# ---------- 1. 开卷 ----------

def test_start_returns_answerable_paper_html(exam_client):
    r = exam_client.get("/exam/spec_exam_demo/start", params={"learner_id": "kid-1"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    body = r.text
    assert 'action="/exam/' in body and '/submit"' in body
    assert "kid-1" in body  # 考生回显
    assert body.count('<div class="question" id="q') == 5
    assert body.count("<textarea") == 1  # 解答题
    assert '<input class="q-text"' in body  # 填空题


def test_start_json_shape(exam_client):
    info = _start(exam_client)
    assert set(info) >= {"session_id", "spec_id", "learner_id", "question_count",
                         "total_points", "paper_url", "submit_url", "report_url",
                         "expires_in_seconds"}
    assert info["question_count"] == 5 and info["total_points"] == 15
    sid = info["session_id"]
    assert info["paper_url"] == f"/exam/{sid}/paper.html"
    assert info["report_url"] == f"/exam/{sid}/report.html"


def test_start_unknown_spec_404(exam_client):
    r = exam_client.get("/exam/no_such_spec/start", params={"learner_id": "k"})
    assert r.status_code == 404


def test_start_missing_learner_id_422(exam_client):
    # learner_id 是必填 query：缺参数由 pydantic 映射 422
    r = exam_client.get("/exam/spec_exam_demo/start")
    assert r.status_code == 422
    # 给了但空白 → 领域校验 400
    r = exam_client.get("/exam/spec_exam_demo/start", params={"learner_id": "  "})
    assert r.status_code == 400


def test_start_inconsistent_spec_400(exam_client):
    # 节和 2×3+1×2+1×5=13 != 11 → paper_spec V8 fail-closed（不降级凑题）
    r = exam_client.get("/exam/spec_exam_badtotal/start",
                        params={"learner_id": "k", "format": "json"})
    assert r.status_code == 400


def test_paper_page_controls_one_name_per_question(exam_client, exam_bank):
    """每题**恰好一组**同名控件：N 个不同 name=item_{no}（选择题多控件共用一名）。"""
    import re
    sid = _start(exam_client)["session_id"]
    body = exam_client.get(f"/exam/{sid}/paper.html").text
    names = re.findall(r'name="(item_\d+)"', body)
    assert sorted(set(names)) == [f"item_{i}" for i in range(1, 6)]
    # 控件总数 > 题数是正常的：选择题一题多个选项共用一个 name
    assert len(names) > 5
    n_opt = sum(len(it.options or []) for _no, it in _paper_items(exam_bank)
               if it.options)
    assert body.count('type="radio"') + body.count('type="checkbox"') == n_opt
    assert body.count('type="radio"') == 4      # 两道单选题 × 2 个选项
    assert body.count('type="checkbox"') == 4  # 多选题 × 4 个选项


def test_paper_page_option_values_are_labels(exam_client):
    """选项控件 value 是标签（多选要过顿号切分，全文会被切碎）。"""
    import re
    sid = _start(exam_client)["session_id"]
    body = exam_client.get(f"/exam/{sid}/paper.html").text
    vals = re.findall(r'<input type="(?:radio|checkbox)"[^>]*name="item_(\d+)" '
                      r'value="([^"]*)"', body)
    assert vals, "卷页没有选项控件"
    for _no, val in vals:
        assert val in {"A", "B", "C", "D"}, f"选项 value 不是标签：{val!r}"
    # label 文本仍是完整选项（学生看得到全文）
    assert "与 Q、U 无关" in body


def test_paper_page_escapes_and_balances(exam_client):
    import re
    sid = _start(exam_client)["session_id"]
    body = exam_client.get(f"/exam/{sid}/paper.html").text
    assert "<script>alert(1)</script>" not in body  # 题面里的标记被转义
    assert "&lt;script&gt;" in body
    assert not check_html_tag_balance(body)
    for needle in ("<script", "<link", "src=", "http://", "https://", "url("):
        assert needle not in body.lower()


def test_paper_page_redline_no_answer_leak(exam_client, exam_bank, exam_graph):
    """红线：标答/解析值零泄漏；含 CSS 数字（answer "50" 曾撞 max-width:150mm）。"""
    from xuexing.paper_by_spec import generate_paper_by_spec
    paper = generate_paper_by_spec(
        exam_bank, _EXAM_SPEC, seed=42, difficulty_target=0.5, spec_id="spec_exam_demo")
    sid = _start(exam_client)["session_id"]
    body = exam_client.get(f"/exam/{sid}/paper.html").text
    assert not redline_report(paper, exam_bank, body, render_paper_text(paper, exam_bank))


def test_paper_page_unknown_session_404(exam_client):
    assert exam_client.get("/exam/ghost/paper.html").status_code == 404


def test_paper_page_reopen_is_idempotent(exam_client):
    sid = _start(exam_client)["session_id"]
    a = exam_client.get(f"/exam/{sid}/paper.html").text
    b = exam_client.get(f"/exam/{sid}/paper.html").text
    assert a == b  # 会话冻结，重开是同一份卷


# ---------- 2. 提交判分 ----------

def test_submit_redirects_303_to_report(exam_client, exam_bank):
    sid = _start(exam_client)["session_id"]
    r = exam_client.post(f"/exam/{sid}/submit", json={"answers": _answers_all_right(exam_bank)},
                         follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == f"/exam/{sid}/report.html"


def test_submit_grading_matches_grade_kernel(exam_client, exam_bank):
    """I 内核等价：端点判定逐题 == grading.grade_to_response（= /grade 口径）。"""
    import re
    sid = _start(exam_client)["session_id"]
    exam_client.post(f"/exam/{sid}/submit", json={"answers": _answers_all_right(exam_bank)},
                     follow_redirects=False)
    rep = exam_client.get(f"/exam/{sid}/report.html").text
    checked = 0
    for no, item in _objective_items(exam_bank):
        # 用同一个冻结内核算期望值（多选按标签集合，与表单提交值同形）
        want = grade_to_response(item, _correct_answer(item)).correct
        seg = _row(rep, no)
        assert ('class="verdict ok"' in seg) is want, f"第 {no} 题判定与内核不符"
        checked += 1
    assert checked == 4  # 四道客观题都核对过


def test_submit_form_urlencoded_path(exam_client, exam_bank):
    """真实浏览器载荷：urlencoded；多选题的 checkbox 是同名多值。"""
    import re
    sid = _start(exam_client)["session_id"]
    # 按页面上真实的控件组装：radio 每题一个值、checkbox 同名多值。
    # 取值一律用**页面 value 本身**（不是我们另造的字符串）——这才证明
    # 「页面上写的 value 就是判分内核认的标签」。
    page = exam_client.get(f"/exam/{sid}/paper.html").text
    picks = re.findall(
        r'<input type="(?:radio|checkbox)"[^>]*name="(item_\d+)" value="([^"]*)"', page)
    assert picks, "卷页没有选项控件"
    on_page = {}
    for name, val in picks:
        on_page.setdefault(name, set()).add(val)
    pairs = []
    for no, item in _paper_items(exam_bank):
        if not item.options:
            continue
        if getattr(item, "form", "") == "mcq_multi":
            # 多选：勾上标答的每个标签（同名多值）
            for lbl in str(item.answer).split(","):
                lbl = lbl.strip()
                assert lbl in on_page[reply_field_name(no)], \
                    f"标答标签 {lbl} 不在页面控件 value 里：{on_page[reply_field_name(no)]}"
                pairs.append((reply_field_name(no), lbl))
        else:
            lbl = str(item.answer).strip()
            assert lbl in on_page[reply_field_name(no)], \
                f"标答标签 {lbl} 不在页面控件 value 里"
            pairs.append((reply_field_name(no), lbl))
    body = urlencode(pairs)
    r = exam_client.post(f"/exam/{sid}/submit", content=body,
                         headers={"Content-Type": "application/x-www-form-urlencoded"},
                         follow_redirects=False)
    assert r.status_code == 303
    rep = exam_client.get(f"/exam/{sid}/report.html").text
    # 页面每个选项都勾了 = 全选；单选/多选的正确答案都得判对
    for no, item in _objective_items(exam_bank):
        if item.options:
            seg = _row(rep, no)
            assert 'class="verdict ok"' in seg, f"第 {no} 题按页面选项提交却判错"


def test_submit_score_all_right_and_half_wrong(exam_client, exam_bank):
    """全对 = 客观题分值合计；半错 = 只保留前半段客观题的分。主观题不预扣。"""
    import re
    from xuexing.paper_by_spec import generate_paper_by_spec
    paper = generate_paper_by_spec(exam_bank, _EXAM_SPEC, seed=42,
                                   difficulty_target=0.5, spec_id="spec_exam_demo")
    points = {q["question_no"]: q["points"] for sec in paper["sections"]
              for q in sec["questions"]}
    obj = [no for no, it in _objective_items(exam_bank)]
    obj_total = sum(points[no] for no in obj)
    assert obj_total == 10.0  # 3+3+2+2
    assert paper["total_points"] == 15  # 另有解答题 5 分

    sid = _start(exam_client, learner="perfect")["session_id"]
    exam_client.post(f"/exam/{sid}/submit", json={"answers": _answers_all_right(exam_bank)},
                     follow_redirects=False)
    rep = exam_client.get(f"/exam/{sid}/report.html").text
    score = float(re.search(r'<div class="score-big">([0-9.]+)', rep).group(1))
    assert score == obj_total  # 主观题 5 分待批改、不预扣
    assert "主观题的分值未计入得分，也未扣分" in rep  # 报告如实说明未计入的分值

    sid2 = _start(exam_client, learner="half")["session_id"]
    exam_client.post(f"/exam/{sid2}/submit", json={"answers": _answers_half_wrong(exam_bank)},
                     follow_redirects=False)
    rep2 = exam_client.get(f"/exam/{sid2}/report.html").text
    score2 = float(re.search(r'<div class="score-big">([0-9.]+)', rep2).group(1))
    assert score2 < score
    assert score2 == sum(points[no] for no in obj[:len(obj) // 2])
    assert rep2.count('class="verdict bad"') == len(obj) - len(obj) // 2


def test_subjective_items_not_auto_graded(exam_client, exam_bank):
    """主观题：标「待批改」、不进画像证据、不预扣分。"""
    sid = _start(exam_client)["session_id"]
    exam_client.post(f"/exam/{sid}/submit", json={"answers": _answers_all_right(exam_bank)},
                     follow_redirects=False)
    rep = exam_client.get(f"/exam/{sid}/report.html").text
    subj = [(no, it) for no, it in _paper_items(exam_bank) if not is_objective(it)]
    assert subj, "夹具里没有主观题，用例失去意义"
    for no, _it in subj:
        seg = _row(rep, no)
        assert 'class="verdict pending"' in seg  # 待批改，不是「错」
    assert "待批改" in rep  # 头部也说明
    # 主观题的知识点不因它进画像（s1 的 kp 是 c；c 若也出现在客观题里则不适用）
    subj_kps = {k for _no, it in subj for k in it.kps}
    prof = exam_client.get("/learners/kid-1/profile").json()
    for kp in subj_kps:
        covered_by_objective = any(
            kp in (it.kps or []) for _no, it in _objective_items(exam_bank))
        if not covered_by_objective:
            assert prof["evidence"][kp] == 0, f"主观题知识点 {kp} 不该进画像证据"


def test_unknown_question_no_400(exam_client):
    """越界题号 → 400（不猜题号；否则学生能把答案写到不存在的题上）。"""
    sid = _start(exam_client)["session_id"]
    r = exam_client.post(f"/exam/{sid}/submit",
                         json={"answers": {"item_9999": "x"}}, follow_redirects=False)
    assert r.status_code == 400


def test_non_numeric_question_key_400(exam_client):
    sid = _start(exam_client)["session_id"]
    r = exam_client.post(f"/exam/{sid}/submit",
                         json={"answers": {"item_abc": "x"}}, follow_redirects=False)
    assert r.status_code == 400


def test_malformed_json_422(exam_client):
    sid = _start(exam_client)["session_id"]
    r = exam_client.post(f"/exam/{sid}/submit", content=b"{not json",
                         headers={"Content-Type": "application/json"},
                         follow_redirects=False)
    assert r.status_code == 422


def test_submit_unknown_session_404(exam_client):
    r = exam_client.post("/exam/ghost/submit", json={"answers": {}},
                         follow_redirects=False)
    assert r.status_code == 404


def test_report_before_submit_409(exam_client):
    sid = _start(exam_client)["session_id"]
    r = exam_client.get(f"/exam/{sid}/report.html")
    assert r.status_code == 409


# ---------- 3. 报告页 ----------

def test_report_has_four_sections_and_marks(exam_client, exam_bank):
    sid = _start(exam_client)["session_id"]
    exam_client.post(f"/exam/{sid}/submit", json={"answers": _answers_half_wrong(exam_bank)},
                     follow_redirects=False)
    r = exam_client.get(f"/exam/{sid}/report.html")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/html")
    rep = r.text
    for title in ("一、逐题对错", "二、知识点掌握更新", "三、薄弱知识点",
                  "四、下一步学习建议"):
        assert f"<h2>{title}</h2>" in rep
    for mark in ("正确", "错误", "待批改"):
        assert mark in rep
    assert not check_html_tag_balance(rep)
    for needle in ("<script", "<link", "src=", "http://", "https://"):
        assert needle not in rep.lower()  # 自包含


def test_report_shows_weak_kps_with_names(exam_client, exam_bank):
    """薄弱点区非空，且出现 KP 中文名（家长可读，不是 kp_id 裸串）。"""
    sid = _start(exam_client)["session_id"]
    exam_client.post(f"/exam/{sid}/submit", json={"answers": _answers_half_wrong(exam_bank)},
                     follow_redirects=False)
    rep = exam_client.get(f"/exam/{sid}/report.html").text
    weak = rep.split("三、薄弱知识点</h2>")[1].split("四、下一步学习建议")[0]
    assert "<tr><td>" in weak  # 非空
    assert "甲" in weak or "乙" in weak  # KP 中文名


def test_report_mastery_matches_diagnose_kernel(exam_client, exam_bank, exam_graph):
    """I 内核等价：报告里的掌握度 == diagnosis.diagnose 的输出。"""
    from xuexing.types import Response
    sid = _start(exam_client)["session_id"]
    exam_client.post(f"/exam/{sid}/submit", json={"answers": _answers_half_wrong(exam_bank)},
                     follow_redirects=False)
    # 复算：只取客观题（solve 不进证据），逐条用冻结内核判
    half = _answers_half_wrong(exam_bank)
    responses = [
        Response(it.id, grade_to_response(it, half[reply_field_name(no)]).correct,
                 half[reply_field_name(no)])
        for no, it in _objective_items(exam_bank)
    ]
    expect = diagnose(responses, exam_bank, exam_graph, learner_id="kid-1")
    prof = exam_client.get("/learners/kid-1/profile").json()
    assert prof["mastery"] == expect.mastery
    assert prof["evidence"] == expect.evidence


def test_report_next_steps_match_plan_kernel(exam_client, exam_bank, exam_graph,
                                             exam_strategies):
    """I 内核等价：建议步骤来自 route.build_plan（同一函数、同一排序）。"""
    from xuexing.exam_loop import _scoped_profile
    from xuexing.types import Response
    sid = _start(exam_client)["session_id"]
    exam_client.post(f"/exam/{sid}/submit", json={"answers": _answers_half_wrong(exam_bank)},
                     follow_redirects=False)
    rep = exam_client.get(f"/exam/{sid}/report.html").text
    half = _answers_half_wrong(exam_bank)
    responses = [
        Response(it.id, grade_to_response(it, half[reply_field_name(no)]).correct,
                 half[reply_field_name(no)])
        for no, it in _objective_items(exam_bank)
    ]
    profile = diagnose(responses, exam_bank, exam_graph, learner_id="kid-1")
    plan = build_plan(_scoped_profile(profile), exam_bank, exam_graph,
                      exam_strategies, date.today())
    for step in plan.steps:
        assert step.kp_id in rep or step.strategy_id in rep


def test_report_escapes_answer_only_after_submission(exam_client, exam_bank):
    """报告页**可以**展示正确答案（红线只管学生卷）。"""
    sid = _start(exam_client)["session_id"]
    exam_client.post(f"/exam/{sid}/submit", json={"answers": _answers_half_wrong(exam_bank)},
                     follow_redirects=False)
    rep = exam_client.get(f"/exam/{sid}/report.html").text
    # 题1 正确答案 B、题2 正确答案 A,D 出现在报告里
    assert "正确答案" in rep


def test_report_persists_after_resubmit(exam_client, exam_bank):
    sid = _start(exam_client)["session_id"]
    exam_client.post(f"/exam/{sid}/submit", json={"answers": _answers_all_right(exam_bank)},
                     follow_redirects=False)
    exam_client.post(f"/exam/{sid}/submit", json={"answers": _answers_half_wrong(exam_bank)},
                     follow_redirects=False)
    assert exam_client.get(f"/exam/{sid}/report.html").status_code == 200


# ---------- 4. 落库（等价 /responses） ----------

def test_submit_lands_in_learner_store(exam_client, exam_bank):
    """落库：/profile 能复核本次作答（与 /responses 同一 store 形状）。"""
    sid = _start(exam_client, learner="landed")["session_id"]
    exam_client.post(f"/exam/{sid}/submit", json={"answers": _answers_all_right(exam_bank)},
                     follow_redirects=False)
    prof = exam_client.get("/learners/landed/profile")
    assert prof.status_code == 200
    assert prof.json()["evidence"]["a"] > 0
    plan = exam_client.get("/learners/landed/plan")
    assert plan.status_code == 200  # 与 /responses 后一致：能出计划


# ---------- 5. 会话过期（注入时钟，不 sleep） ----------

def test_session_expired_410(exam_bank, exam_graph, exam_strategies, exam_catalog):
    """TTL=0：开卷即过期，取卷/提交/报告全 410。"""
    app = create_app(
        exam_bank, exam_graph, exam_strategies, None,
        spec_catalog=exam_catalog,
        stage_bank_loader=lambda s, st: exam_bank,
        stage_graph_loader=lambda s: exam_graph,
        exam_sessions=ExamSessionStore(ttl_seconds=0.0),
    )
    c = TestClient(app)
    sid = _start(c)["session_id"]
    assert c.get(f"/exam/{sid}/paper.html").status_code == 410
    assert c.post(f"/exam/{sid}/submit", json={"answers": {}},
                  follow_redirects=False).status_code == 410
    assert c.get(f"/exam/{sid}/report.html").status_code == 410


def test_session_store_expiry_uses_injected_clock():
    """过期判定是纯函数式的 now-created >= ttl：可控时钟直接推进，无 sleep。"""
    now = [1000.0]
    store = ExamSessionStore(ttl_seconds=60.0, clock=lambda: now[0])
    store.put("default", {"session_id": "s1", "created_at": store._clock()})
    assert store.get("default", "s1")["session_id"] == "s1"  # 未过期
    now[0] += 59.0
    assert store.get("default", "s1")["session_id"] == "s1"  # 仍未过期
    now[0] += 1.0
    with pytest.raises(ExamSessionExpired):
        store.get("default", "s1")


def test_session_store_not_found_and_org_isolation():
    store = ExamSessionStore()
    with pytest.raises(ExamSessionNotFound):
        store.get("default", "nope")
    store.put("org-a", {"session_id": "s1"})
    with pytest.raises(ExamSessionNotFound):
        store.get("org-b", "s1")  # org 分域隔离
    with pytest.raises(ExamSessionNotFound):
        store.get("default", "s1")


def test_exam_endpoints_org_isolated(exam_client):
    sid = _start(exam_client)["session_id"]
    assert exam_client.get(f"/exam/{sid}/paper.html",
                           headers={"X-Org-Id": "other"}).status_code == 404
    assert exam_client.get(f"/exam/{sid}/paper.html").status_code == 200


def test_exam_endpoints_ignore_learner_org_mismatch(exam_client, exam_bank):
    """会话绑定开卷时的 org；换 org 看不到（与 /learners 同构）。"""
    sid = _start(exam_client)["session_id"]
    r = exam_client.post(f"/exam/{sid}/submit", json={"answers": _answers_all_right(exam_bank)},
                         headers={"X-Org-Id": "other"}, follow_redirects=False)
    assert r.status_code == 404


# ---------- 6. 内核直测（不经 HTTP） ----------

def test_collect_answers_accepts_field_names_and_numbers(exam_bank):
    sess = {"paper": {"sections": [
        {"questions": [{"question_no": 1, "item_id": "c1", "points": 3},
                       {"question_no": 2, "item_id": "c2", "points": 3}]}]}}
    got = collect_answers(sess, {"item_1": "B", "2": ["A", "D"]})
    assert got == {1: "B", 2: "A、D"}


def test_collect_answers_blank_is_none(exam_bank):
    sess = {"paper": {"sections": [
        {"questions": [{"question_no": 1, "item_id": "c1", "points": 3}]}]}}
    assert collect_answers(sess, {"item_1": "   "}) == {1: None}
    assert collect_answers(sess, {}) == {}


def test_grade_submission_rejects_unknown_no(exam_bank):
    sess = {"paper": {"sections": [
        {"questions": [{"question_no": 1, "item_id": "c1", "points": 3}]}]},
        "bank": exam_bank}
    with pytest.raises(ExamLoopError):
        grade_submission(sess, {"item_7": "x"})


def test_is_objective_classification(exam_bank):
    assert is_objective(exam_bank.get("c1"))  # choice
    assert is_objective(exam_bank.get("f1"))  # fill
    assert not is_objective(exam_bank.get("s1"))  # solve 不自动判


def test_option_label_matches_grading_labels(exam_bank):
    """渲染层的 option_label 与 grading 的标签派生同口径。

    grading 那边是 ``normalize_answer(o).split(".",1)[0].strip()``——多一步归一化
    （全角折叠/小写化）。渲染层给的是**原样标签**，判分入口 grade_to_response 会先
    归一化学员作答，所以两边对同一选项得到同一个标签（大小写/全角差异被归一吃掉）。
    """
    from xuexing.grading import grade_choice, normalize_answer
    for item_id in ("c1", "c2"):
        item = exam_bank.get(item_id)
        for opt in item.options:
            kernel_label = normalize_answer(opt).split(".", 1)[0].strip()
            assert option_label(opt).strip().lower() == kernel_label
    # 端到端：按渲染层的标签作答，判分内核必须认（多选尤其——标签无顿号可被切碎）
    assert grade_choice(exam_bank.get("c2"), "A、D") is True
    assert grade_choice(exam_bank.get("c2"), "A,B") is False   # 少选一项即错
