"""单元测试：exam_loop / exam_report —— 学生作答闭环的真实实卷用例。

契约层（tests/contract/test_exam_loop_contract.py）用自闭式夹具钉死了行为；
本文件只做**真实数据**的廉价不变式，证明闭环在真实题库上确实跑得通、且不因
具体卷型的怪癖（选项里带顿号、题面带标记、学科图比单年级图大得多）崩掉：

- 跨学科实卷（初中物理期末卷）整环跑通：start → 卷页 → 提交 → 报告；
- 卷页红线（redline_report 零违规）在真实题面上成立；
- 「页面上的每个选项标签，按标答勾选后判分内核全判对」——守住渲染层与判分内核
  的标签口径一致（多选尤其：选项正文带「、」时提交全文会被切碎）；
- 报告的薄弱知识点用**中文名**呈现（家长可读），不是 kp_id 裸串；
- 主观题（实验/计算/解答）在真实卷里同样不自动判分、不进画像证据。
"""
import os
import re

import pytest
from fastapi.testclient import TestClient

from xuexing import load_itembank, load_kpgraph, load_strategies
from xuexing.exam_loop import ExamSessionStore, is_objective
from xuexing.kpgraph_subject import load_kpgraph_subject
from xuexing.paper_by_spec import (
    generate_paper_by_spec,
    load_spec_catalog,
    load_stage_bank,
)
from xuexing.paper_render import (
    check_html_tag_balance,
    redline_report,
    render_paper_text,
)
from xuexing.server import create_app

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA = os.path.join(ROOT, "data")

# 真实卷型：初中物理期末（10 单选 + 15 填空 + 6 实验/计算解答）。
# 这是 check_exam_loop.py 的同一套卷——验收门与单测打在同一份真实数据上。
REAL_SPEC = "spec_phy_jr_final"
REAL_SUBJECT = "physics"


def _catalog():
    return load_spec_catalog(os.path.join(DATA, "curriculum", "paper_specs.json"))


def _real_bank(spec_id=REAL_SPEC):
    raw = _catalog()[spec_id]
    bank, _grades = load_stage_bank(DATA, raw["subject"], raw["stage"])
    return raw, bank


def _real_paper(spec_id=REAL_SPEC, seed=42):
    raw, bank = _real_bank(spec_id)
    paper = generate_paper_by_spec(bank, raw, seed=seed, difficulty_target=0.5,
                                   spec_id=spec_id)
    return raw, bank, paper


@pytest.fixture(scope="module")
def real_client():
    raw, bank = _real_bank()
    graph = load_kpgraph_subject(os.path.join(DATA, "knowledge"), raw["subject"])
    app = create_app(
        load_itembank(os.path.join(DATA, "items", "math_grade7_items.json")),
        load_kpgraph(os.path.join(DATA, "knowledge", "math_grade7.json")),
        load_strategies(os.path.join(DATA, "pedagogy", "strategies.json")),
        None,
        spec_catalog=_catalog(),
        stage_bank_loader=lambda subject, stage: bank,
        stage_graph_loader=lambda subject: graph,
    )
    return TestClient(app)


def _start(client, learner, **params):
    params = {"learner_id": learner, "format": "json", **params}
    r = client.get(f"/exam/{REAL_SPEC}/start", params=params)
    assert r.status_code == 200, r.text
    return r.json()


def _items(paper, bank):
    return [(q["question_no"], bank.get(q["item_id"]))
            for sec in paper["sections"] for q in sec["questions"]]


def test_real_paper_loop_end_to_end(real_client):
    """真实初中物理卷整环：开卷 → 卷页 → 全对提交 → 报告。"""
    _raw, bank, paper = _real_paper()
    n_q = paper["question_count"]
    info = _start(real_client, "real-kid")
    assert info["question_count"] == n_q

    sid = info["session_id"]
    page = real_client.get(f"/exam/{sid}/paper.html")
    assert page.status_code == 200
    body = page.text
    assert body.count('<div class="question" id="q') == n_q
    assert sorted({int(m) for m in re.findall(r'name="item_(\d+)"', body)}) == \
        list(range(1, n_q + 1))
    assert "real-kid" in body
    assert not check_html_tag_balance(body)

    answers = {f"item_{no}": it.answer for no, it in _items(paper, bank)
               if is_objective(it)}
    r = real_client.post(f"/exam/{sid}/submit", json={"answers": answers},
                         follow_redirects=False)
    assert r.status_code == 303

    rep = real_client.get(f"/exam/{sid}/report.html")
    assert rep.status_code == 200
    text = rep.text
    obj_total = sum(q["points"] for sec in paper["sections"] for q in sec["questions"]
                    if is_objective(bank.get(q["item_id"])))
    score = float(re.search(r'<div class="score-big">([0-9.]+)', text).group(1))
    assert score == obj_total  # 客观题全对；主观题分值不预扣
    assert 'class="verdict bad"' not in text
    assert not check_html_tag_balance(text)


def test_real_paper_page_redline(real_client):
    """真实题面上学生卷红线成立（零 answer/solution 词根与值泄漏）。"""
    _raw, bank, paper = _real_paper()
    sid = _start(real_client, "redline-kid")["session_id"]
    body = real_client.get(f"/exam/{sid}/paper.html").text
    assert not redline_report(paper, bank, body, render_paper_text(paper, bank))


def test_real_page_option_labels_all_gradeable(real_client):
    """页面上出现的每个选项标签，按标答勾选后内核全判对。

    这是「渲染层 option_label 与 grading 标签派生同口径」的实卷证据。多选题的
    选项正文里带顿号（真实卷里就有「与 Q、U 无关」这类），提交全文会被
    grading._split_multi 切碎——所以表单 value 必须是标签。
    """
    _raw, bank, paper = _real_paper()
    sid = _start(real_client, "label-kid")["session_id"]
    body = real_client.get(f"/exam/{sid}/paper.html").text
    on_page: dict[str, set[str]] = {}
    for name, val in re.findall(
            r'<input type="(?:radio|checkbox)"[^>]*name="(item_\d+)" value="([^"]*)"',
            body):
        on_page.setdefault(name, set()).add(val)

    pairs = []
    for no, item in _items(paper, bank):
        if not item.options:
            continue
        field = f"item_{no}"
        assert field in on_page, f"第 {no} 题在页面上没有选项控件"
        for lbl in [x.strip() for x in str(item.answer).split(",")]:
            assert lbl in on_page[field], \
                f"第 {no} 题标答标签 {lbl!r} 不在页面 value {on_page[field]} 里"
            pairs.append((field, lbl))

    r = real_client.post(f"/exam/{sid}/submit",
                         content="&".join(f"{k}={v}" for k, v in pairs),
                         headers={"Content-Type": "application/x-www-form-urlencoded"},
                         follow_redirects=False)
    assert r.status_code == 303
    text = real_client.get(f"/exam/{sid}/report.html").text
    blocks = text.split("一、逐题对错</h2>")[1].split("二、知识点掌握更新")[0]
    wrong = [no for no, item in _items(paper, bank)
             if item.options and 'class="verdict bad"'
             in blocks.split(f'<tr><td class="num">{no}</td>')[1].split("</tr>")[0]]
    assert not wrong, f"按页面标签勾选标答仍被判错：第 {wrong} 题"


def test_real_report_shows_kp_names_not_ids(real_client):
    """薄弱点区呈现知识点中文名（家长可读），不是 kp_id 裸串。"""
    _raw, bank, paper = _real_paper()
    graph = load_kpgraph_subject(os.path.join(DATA, "knowledge"), REAL_SUBJECT)
    names = {kp.name for kp in graph.kps()}
    sid = _start(real_client, "names-kid")["session_id"]
    # 全错卷：每个知识点都掉掌握度，薄弱点区必然有内容
    answers = {f"item_{no}": "错答" for no, _it in _items(paper, bank)}
    real_client.post(f"/exam/{sid}/submit", json={"answers": answers},
                     follow_redirects=False)
    text = real_client.get(f"/exam/{sid}/report.html").text
    weak = text.split("三、薄弱知识点</h2>")[1].split("四、下一步学习建议")[0]
    rows = re.findall(r"<tr><td>([^<]+)</td>", weak)
    assert rows, "全错卷的薄弱点区不应为空"
    assert any(r in names for r in rows), f"薄弱点区没出现知识点中文名：{rows[:3]}"
    assert "kp_" not in weak, "薄弱点区泄漏了 kp_id 裸串"


def test_real_subjective_items_pending(real_client):
    """真实卷里的实验/计算题标「待批改」、不进画像证据。"""
    _raw, bank, paper = _real_paper()
    subj = [(no, it) for no, it in _items(paper, bank) if not is_objective(it)]
    assert subj, "真实卷里应含主观题（实验/计算）"
    sid = _start(real_client, "subj-kid")["session_id"]
    real_client.post(f"/exam/{sid}/submit", json={"answers": {}}, follow_redirects=False)
    text = real_client.get(f"/exam/{sid}/report.html").text
    blocks = text.split("一、逐题对错</h2>")[1].split("二、知识点掌握更新")[0]
    for no, _it in subj:
        row = blocks.split(f'<tr><td class="num">{no}</td>')[1].split("</tr>")[0]
        assert 'class="verdict pending"' in row, f"第 {no} 题（主观题）应待批改"
    # 交白卷：客观题全错，主观题不进证据 → 证据只可能来自客观题
    prof = real_client.get("/learners/subj-kid/profile").json()
    assert sum(prof["evidence"].values()) > 0  # 空白也判错，仍是有效证据


def test_real_report_plan_and_mastery_sections(real_client):
    """真实卷报告：掌握更新/薄弱点/建议三区都有内容。"""
    _raw, bank, paper = _real_paper()
    sid = _start(real_client, "plan-kid")["session_id"]
    obj = {f"item_{no}": it.answer for no, it in _items(paper, bank) if is_objective(it)}
    # 故意只对一半：让画像有高有低，薄弱点区才有东西可展示
    for k in list(obj)[::2]:
        obj[k] = "错答"
    real_client.post(f"/exam/{sid}/submit", json={"answers": obj},
                     follow_redirects=False)
    text = real_client.get(f"/exam/{sid}/report.html").text
    assert '<span class="bar' in text  # 掌握度条
    weak = text.split("三、薄弱知识点</h2>")[1].split("四、下一步学习建议")[0]
    assert "<tr><td>" in weak
    nxt = text.split("四、下一步学习建议</h2>")[1]
    assert "<li>" in nxt
    assert "策略" in nxt  # 建议带策略名


def test_real_session_expiry_410():
    """真实数据 + 注入 TTL=0：整环在过期边界上返回 410。"""
    raw, bank = _real_bank()
    graph = load_kpgraph_subject(os.path.join(DATA, "knowledge"), raw["subject"])
    app = create_app(
        load_itembank(os.path.join(DATA, "items", "math_grade7_items.json")),
        load_kpgraph(os.path.join(DATA, "knowledge", "math_grade7.json")),
        load_strategies(os.path.join(DATA, "pedagogy", "strategies.json")),
        None,
        spec_catalog=_catalog(),
        stage_bank_loader=lambda subject, stage: bank,
        stage_graph_loader=lambda subject: graph,
        exam_sessions=ExamSessionStore(ttl_seconds=0.0),
    )
    c = TestClient(app)
    sid = c.get(f"/exam/{REAL_SPEC}/start",
                params={"learner_id": "ttl-kid", "format": "json"}).json()["session_id"]
    assert c.get(f"/exam/{sid}/paper.html").status_code == 410
    assert c.post(f"/exam/{sid}/submit", json={"answers": {}},
                  follow_redirects=False).status_code == 410
    assert c.get(f"/exam/{sid}/report.html").status_code == 410


def test_real_specs_with_multiselect_render_checkboxes():
    """含多选题的真实卷型（高中物理/化学）渲染 checkbox 而非 radio。"""
    spec_id = "spec_phy_hs_final"
    raw, bank = _real_bank(spec_id)
    paper = generate_paper_by_spec(bank, raw, seed=42, difficulty_target=0.5,
                                   spec_id=spec_id)
    multi = [it for _no, it in _items(paper, bank)
             if getattr(it, "form", "") == "mcq_multi"]
    assert multi, f"{spec_id} 应含多选题"
    graph = load_kpgraph_subject(os.path.join(DATA, "knowledge"), raw["subject"])
    app = create_app(
        load_itembank(os.path.join(DATA, "items", "math_grade7_items.json")),
        load_kpgraph(os.path.join(DATA, "knowledge", "math_grade7.json")),
        load_strategies(os.path.join(DATA, "pedagogy", "strategies.json")),
        None,
        spec_catalog=_catalog(),
        stage_bank_loader=lambda subject, stage: bank,
        stage_graph_loader=lambda subject: graph,
    )
    c = TestClient(app)
    sid = c.get(f"/exam/{spec_id}/start",
                params={"learner_id": "multi-kid", "format": "json"}).json()["session_id"]
    body = c.get(f"/exam/{sid}/paper.html").text
    assert 'type="checkbox"' in body
    n_multi_opts = sum(len(it.options or []) for it in multi)
    assert body.count('type="checkbox"') == n_multi_opts
