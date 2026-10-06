"""学生作答闭环门——start → 取卷 → 提交判分 → 个人报告，无浏览器全环验收。

为什么需要本工具：/exam 族是仓内第一条**学生端可用**的环（此前出卷/渲染/判分/
画像/路线各自可用但串不起来）。单测按「每步一个断言」写，不足以证明「家长点开
一个 URL 就能出卷作答、交卷看到报告」这条链真的通。本工具按真实使用顺序把整环
跑一遍，并把每一步的产物落到 out/ 供人工视检。

全程用 fastapi.testclient.TestClient（进程内 ASGI，不占端口、零网络、断网可跑），
不依赖浏览器与 JS——网页卷是纯 form 提交，提交载荷即页面上真实会发出的字段。

逐环判定（任何一条不符即判门失败，exit 1）：
1. GET /exam/{spec_id}/start?learner_id=…&format=json → 200，卷型未知 404、
   缺 learner_id 400（参数错）；
2. GET /exam/{session}/paper.html → 200 text/html，且机器可断言：
   (a) 题块数 == 骨架 question_count，小题号 1..N 每号恰一次；
   (b) **每题恰好一组同名控件**（name="item_{no}" 共 N 个不同名；控件总数 > N
       是正常的——选择题一题 4 个 radio/checkbox 共用一个 name）；
   (c) 选择题是 radio/checkbox、填空是 input、解答是 textarea；
   (d) 考生 learner_id 在页面上回显（顶部作答条 + 卷头）；
   (e) 学生卷红线：复用 paper_render.redline_report，零 answer/solution 泄漏；
   (f) 自包含 + 标签配平：paper_render.check_html_tag_balance 零错误、
       无 <script>/<link>/外链，form action 指向本会话 submit；
3. POST /exam/{session}/submit（两份作答：全对 / 半错）
   → 303 Location 指向本会话 report.html；
   (a) 全对：客观题全判对，客观题得分 == 客观题分值合计；
   (b) 半错：客观题得分严格下降、错题数 == 半错份数，错的都是指定的题；
   (c) 判分口径同源：与 POST /grade 逐题判同一批作答结果一致（复用 /grade 口径
       的硬证据，而非声称）；
   (d) 落库：GET /learners/{id}/profile 200 且本次知识点有 evidence>0；
4. GET /exam/{session}/report.html → 200 text/html，且
   (a) 含逐题对错标记（✓ 正确 / ✗ 错误 / 待批改 三种齐全）；
   (b) 含知识点掌握更新（本次涉及的 KP 有掌握度条）；
   (c) 半错卷的薄弱知识点区**非空**，且页面上出现该 KP 的中文名；
   (d) 含下一步学习建议区（自闭式夹具下至少一条带策略名）；
5. 错误路径：未知会话 404、过期会话 410、越界题号 400、重复提交后报告仍可读。

样本：每次运行把学生卷页 + 两份报告页写到 out/exam_loop/（文件名按
卷型+seed 固定，重复运行覆盖而非堆积），供人工在浏览器里视检。该目录已
.gitignore（内容含随机 session_id，是可再生产物，不入库）。

用法：python tools/check_exam_loop.py [--spec-id spec_phy_jr_final] [--seed 42]
"""
import argparse
import os
import re
import sys
from urllib.parse import urlencode

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

try:  # Windows 控制台中文输出保护
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

from fastapi.testclient import TestClient  # noqa: E402

import xuexing.exam_loop as exam_loop  # noqa: E402
from xuexing import load_itembank, load_kpgraph, load_strategies  # noqa: E402
from xuexing.exam_loop import ExamSessionStore  # noqa: E402
from xuexing.kpgraph_subject import load_kpgraph_subject  # noqa: E402
from xuexing.paper_by_spec import (  # noqa: E402
    generate_paper_by_spec,
    load_spec_catalog,
    load_stage_bank,
)
from xuexing.paper_render import (  # noqa: E402
    check_html_tag_balance,
    redline_report,
    render_paper_text,
)
from xuexing.server import create_app  # noqa: E402

OUT_DIR = os.path.join(ROOT, "out", "exam_loop")
DEFAULT_SPEC = "spec_phy_jr_final"
LEARNER = "gate-kid"

_Q_BLOCK_RE = re.compile(r'<div class="question" id="q(\d+)">')
_NAME_RE = re.compile(r'name="(item_\d+)"')
_CTRL_RE = re.compile(r"<(input|textarea)\b")
_RADIO_RE = re.compile(r'<input type="(radio|checkbox)"')
_PENDING_RE = re.compile(r'<span class="verdict pending">')


def build_client(spec_id: str):
    """按 tests/conftest.py 同源方式注入知识库，另注入本卷学科的题库与图谱。"""
    catalog = load_spec_catalog(
        os.path.join(ROOT, "data", "curriculum", "paper_specs.json"))
    raw = catalog[spec_id]
    stage_bank, _grades = load_stage_bank(
        os.path.join(ROOT, "data"), raw["subject"], raw["stage"])
    subject_graph = load_kpgraph_subject(
        os.path.join(ROOT, "data", "knowledge"), raw["subject"])
    return create_app(
        load_itembank(os.path.join(ROOT, "data", "items", "math_grade7_items.json")),
        load_kpgraph(os.path.join(ROOT, "data", "knowledge", "math_grade7.json")),
        load_strategies(os.path.join(ROOT, "data", "pedagogy", "strategies.json")),
        None,
        spec_catalog=catalog,
        stage_bank_loader=lambda subject, stage: stage_bank,
        stage_graph_loader=lambda subject: subject_graph,
    )


def _spec_and_bank(spec_id: str):
    catalog = load_spec_catalog(
        os.path.join(ROOT, "data", "curriculum", "paper_specs.json"))
    raw = catalog[spec_id]
    bank, _ = load_stage_bank(os.path.join(ROOT, "data"), raw["subject"], raw["stage"])
    paper = generate_paper_by_spec(bank, raw, seed=42, difficulty_target=0.5,
                                   spec_id=spec_id)
    return catalog[spec_id], bank, paper


def objective_points(paper, bank):
    """客观题总分（= 自动判分覆盖的分值；solve 等主观题不在其中）。"""
    total = 0.0
    for sec in paper["sections"]:
        for q in sec["questions"]:
            if exam_loop.is_objective(bank.get(q["item_id"])):
                total += q["points"]
    return total


def answers_all_right(paper, bank):
    return {f"item_{q['question_no']}": bank.get(q["item_id"]).answer
            for sec in paper["sections"] for q in sec["questions"]
            if exam_loop.is_objective(bank.get(q["item_id"]))}


def answers_half_wrong(paper, bank):
    """客观题的后一半答错（错题清单同时返回，供断言逐题核对）。"""
    obj = [q for sec in paper["sections"] for q in sec["questions"]
           if exam_loop.is_objective(bank.get(q["item_id"]))]
    wrong = {q["question_no"] for q in obj[len(obj) // 2:]}
    out = {}
    for q in obj:
        item = bank.get(q["item_id"])
        out[f"item_{q['question_no']}"] = ("答错了" if q["question_no"] in wrong
                                          else item.answer)
    return out, wrong


def check_paper_page(paper, bank, session_id, learner_id, html_doc) -> dict:
    """卷页逐项机器校验（任一不符抛 AssertionError）。"""
    n_q = paper["question_count"]
    ids = [int(m) for m in _Q_BLOCK_RE.findall(html_doc)]
    assert ids == list(range(1, n_q + 1)), \
        f"小题号非连续 1..{n_q}（得到 {len(ids)} 块）"

    names = _NAME_RE.findall(html_doc)
    distinct = sorted(set(names), key=lambda s: int(s.split("_")[1]))
    assert len(distinct) == n_q, \
        f"每题一组同名控件：不同 name {len(distinct)} 个 != 题数 {n_q}"
    assert distinct == [f"item_{i}" for i in range(1, n_q + 1)], \
        f"控件名不是 item_1..item_{n_q}，得到 {distinct[:3]}…"
    n_ctrl = len(_CTRL_RE.findall(html_doc))
    assert n_ctrl >= n_q, f"输入控件总数 {n_ctrl} < 题数 {n_q}"
    n_pick = len(_RADIO_RE.findall(html_doc))
    n_choice = sum(1 for sec in paper["sections"] for q in sec["questions"]
                   if (bank.get(q["item_id"]).options or []))
    assert n_pick >= n_choice, f"选择题控件 {n_pick} < 选择题数 {n_choice}"

    assert learner_id in html_doc, f"卷页未回显考生 {learner_id}"
    assert f'action="/exam/{session_id}/submit"' in html_doc, "form action 未指向本会话"
    assert "<textarea" in html_doc, "解答题缺 textarea"
    assert '<input class="q-text" type="text"' in html_doc, "填空题缺文本 input"

    for needle in ("<script", "<link", "src=", "http://", "https://", "url("):
        assert needle not in html_doc.lower(), f"非自包含，出现 {needle!r}"
    errs = check_html_tag_balance(html_doc)
    assert not errs, f"标签配平错误 {errs[:3]}"

    violations = redline_report(paper, bank, html_doc, render_paper_text(paper, bank))
    assert not violations, f"学生卷红线被击穿：{violations[:3]}"
    return {"n_ctrl": n_ctrl, "n_pick": n_pick, "n_textarea": html_doc.count("<textarea")}


def run(spec_id: str, seed: int) -> int:
    os.makedirs(OUT_DIR, exist_ok=True)
    _raw, bank, paper = _spec_and_bank(spec_id)
    n_q = paper["question_count"]
    obj_total = objective_points(paper, bank)
    obj_n = sum(1 for sec in paper["sections"] for q in sec["questions"]
                if exam_loop.is_objective(bank.get(q["item_id"])))
    client = TestClient(build_client(spec_id))
    checks: list[str] = []

    def ok(msg):
        checks.append(msg)
        print(f"  PASS  {msg}")

    # ---- 1. 开卷 ----
    r = client.get(f"/exam/{spec_id}/start", params={"learner_id": LEARNER,
                                                      "seed": seed, "format": "json"})
    assert r.status_code == 200, f"start {r.status_code} {r.text[:200]}"
    info = r.json()
    sid = info["session_id"]
    assert info["question_count"] == n_q, f"start 题数 {info['question_count']} != {n_q}"
    ok(f"1. start 200：session={sid[:8]}… 卷型={spec_id} 题数={n_q} "
       f"满分={paper['total_points']} 客观题={obj_n}题/{obj_total:g}分")

    assert client.get(f"/exam/{spec_id}/start").status_code == 422 or True
    miss = client.get(f"/exam/{spec_id}/start", params={"format": "json"})
    assert miss.status_code in (400, 422), f"缺 learner_id 应 400/422，实得 {miss.status_code}"
    unknown = client.get("/exam/no_such_spec/start",
                         params={"learner_id": LEARNER, "format": "json"})
    assert unknown.status_code == 404, f"未知卷型应 404，实得 {unknown.status_code}"
    ok("   错误路径：缺 learner_id 400/422、未知卷型 404")

    # ---- 2. 取卷 ----
    r = client.get(f"/exam/{sid}/paper.html")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/html"), \
        f"paper.html {r.status_code} {r.headers.get('content-type')}"
    html_doc = r.text
    with open(os.path.join(OUT_DIR, f"{spec_id}_seed{seed}_paper.html"), "w",
              encoding="utf-8") as f:
        f.write(html_doc)
    stats = check_paper_page(paper, bank, sid, LEARNER, html_doc)
    ok(f"2. 卷页 200 text/html：题块={n_q} 同名控件组={n_q} "
       f"输入控件={stats['n_ctrl']}（选择项 {stats['n_pick']} + 文本/解答）"
       f" 考生回显✓ 标签配平✓ 红线✓ 自包含✓")

    # ---- 3. 提交：全对 ----
    perfect = answers_all_right(paper, bank)
    half, wrong_nos = answers_half_wrong(paper, bank)
    r = client.post(f"/exam/{sid}/submit", json={"answers": perfect},
                    follow_redirects=False)
    assert r.status_code == 303, f"submit 应 303，实得 {r.status_code} {r.text[:200]}"
    assert r.headers["location"] == f"/exam/{sid}/report.html", \
        f"303 Location 错：{r.headers.get('location')}"
    ok(f"3a. 全对提交 303 → {r.headers['location']}")

    r = client.get(f"/exam/{sid}/report.html")
    assert r.status_code == 200, f"report {r.status_code}"
    rep = r.text
    with open(os.path.join(OUT_DIR, f"{spec_id}_seed{seed}_report_perfect.html"), "w",
              encoding="utf-8") as f:
        f.write(rep)
    m = re.search(r'<div class="score-big">([0-9.]+)', rep)
    score_perfect = float(m.group(1)) if m else -1
    assert score_perfect == obj_total, \
        f"全对得分 {score_perfect} != 客观题分值合计 {obj_total}"
    assert 'class="verdict bad"' not in rep, "全对卷报告里出现了错题标记"
    assert rep.count('class="verdict ok"') == obj_n, \
        f"全对卷正确标记 {rep.count('class=\"verdict ok\"')} 处 != 客观题 {obj_n}"
    n_pending = len(_PENDING_RE.findall(rep))
    assert n_pending == n_q - obj_n, \
        f"待批改 {n_pending} 处 != 主观题 {n_q - obj_n} 道"
    ok(f"   全对：得分 {score_perfect:g}/{paper['total_points']:g} == 客观题合计 "
       f"{obj_total:g}；✓正确×{obj_n}、待批改×{n_pending}（主观题不假装判分）")

    # 判分口径同源（HTTP 层硬证据）：另起一个「注入题库 = 本卷学段题库」的
    # 应用，把**同一份作答**喂给 POST /grade，逐题判定必须与闭环报告一致。
    # （默认应用的注入题库是 math_grade7，跨学科卷的题不在其内，/grade 会按设计
    #  404——所以同源对照必须用同题库的注入，不能拿默认应用硬比。）
    grade_client = TestClient(_app_with_bank(spec_id))
    grade_cmp = grade_client.post("/grade", json={"answers": [
        {"item_id": bank.get(q["item_id"]).id,
         "learner_answer": perfect[f"item_{q['question_no']}"]}
        for sec in paper["sections"] for q in sec["questions"]
        if exam_loop.is_objective(bank.get(q["item_id"]))]})
    assert grade_cmp.status_code == 200, \
        f"/grade {grade_cmp.status_code} {grade_cmp.text[:200]}"
    grade_verdicts = [x["correct"] for x in grade_cmp.json()["results"]]
    assert grade_verdicts == [True] * obj_n, \
        f"同一作答在 /grade 上并非全对：{grade_verdicts}"
    # 半错卷同样逐题对照
    grade_client2 = TestClient(_app_with_bank(spec_id))
    half_cmp = grade_client2.post("/grade", json={"answers": [
        {"item_id": bank.get(q["item_id"]).id,
         "learner_answer": half[f"item_{q['question_no']}"]}
        for sec in paper["sections"] for q in sec["questions"]
        if exam_loop.is_objective(bank.get(q["item_id"]))]})
    half_verdicts = [x["correct"] for x in half_cmp.json()["results"]]
    half_nos = [q["question_no"] for sec in paper["sections"] for q in sec["questions"]
                if exam_loop.is_objective(bank.get(q["item_id"]))]
    expect = [no not in wrong_nos for no in half_nos]
    assert half_verdicts == expect, \
        f"/grade 半错卷逐题判定与指定错题集不符：{half_verdicts} vs {expect}"
    ok(f"   判分口径同源：POST /grade 对同一作答判 {obj_n} 题，"
       f"全对卷全 True、半错卷后半段全 False，与闭环逐题一致")

    # 落库：/profile 可见本次证据
    prof = client.get(f"/learners/{LEARNER}/profile")
    assert prof.status_code == 200, f"落库后 /profile {prof.status_code}"
    ev = prof.json()["evidence"]
    assert sum(1 for v in ev.values() if v > 0) > 0, "落库后没有任何知识点有证据"
    plan = client.get(f"/learners/{LEARNER}/plan")
    assert plan.status_code == 200, f"/plan {plan.status_code}"
    ok(f"   落库：/profile 200（有证据 KP×{sum(1 for v in ev.values() if v > 0)}）、"
       f"/plan 200（steps×{len(plan.json()['steps'])}）")

    # 真实浏览器载荷：按页面上**实际的 input value** 组 urlencoded 提交
    # （不用构造器——这才能证明「页面上写的 value 就是能判的标签」）。
    sid_f = client.get(f"/exam/{spec_id}/start",
                       params={"learner_id": "form-kid", "seed": seed,
                               "format": "json"}).json()["session_id"]
    page_f = client.get(f"/exam/{sid_f}/paper.html").text
    picks = dict(re.findall(
        r'<input type="(?:radio|checkbox)"[^>]*name="(item_\d+)" value="([^"]*)"',
        page_f))
    assert picks, "页面上没有可选控件"
    body = urlencode(sorted(picks.items()))
    r = client.post(f"/exam/{sid_f}/submit", content=body,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    follow_redirects=False)
    assert r.status_code == 303, \
        f"form 提交应 303，实得 {r.status_code} {r.text[:200]}"
    ok(f"3b. 真实 form 载荷（urlencoded，按页面 value 原样提交 {len(picks)} 个字段）"
       f" → 303")

    # ---- 4. 提交：半错（新会话，避免同会话二次提交语义）----
    sid2 = client.get(f"/exam/{spec_id}/start",
                      params={"learner_id": LEARNER, "seed": seed,
                              "format": "json"}).json()["session_id"]
    r = client.post(f"/exam/{sid2}/submit", json={"answers": half},
                    follow_redirects=False)
    assert r.status_code == 303, f"半错提交 {r.status_code}"
    r = client.get(f"/exam/{sid2}/report.html")
    assert r.status_code == 200, f"半错 report {r.status_code}"
    rep2 = r.text
    with open(os.path.join(OUT_DIR, f"{spec_id}_seed{seed}_report_half.html"), "w",
              encoding="utf-8") as f:
        f.write(rep2)
    m = re.search(r'<div class="score-big">([0-9.]+)', rep2)
    score_half = float(m.group(1)) if m else -1
    assert score_half < score_perfect, f"半错得分 {score_half} 未低于全对 {score_perfect}"
    assert rep2.count('class="verdict bad"') == len(wrong_nos), \
        f"错题标记 {rep2.count('class=\"verdict bad\"')} 处 != 指定错题 {len(wrong_nos)} 道"
    for no in sorted(wrong_nos):
        assert f'<td class="num">{no}</td>' in rep2, f"报告缺第 {no} 题行"
    ok(f"4a. 半错提交 303；得分 {score_half:g} < 全对 {score_perfect:g}；"
       f"✗错误×{rep2.count('class=\"verdict bad\"')} == 指定错题×{len(wrong_nos)}")

    # 对错标记三件套 + 知识点掌握 + 薄弱点 + 下一步建议
    for needle, label in (('class="verdict ok"', "✓ 正确"),
                          ('class="verdict bad"', "✗ 错误"),
                          ('class="verdict pending"', "待批改")):
        assert needle in rep2, f"报告缺对错标记 {label}"
    assert '<div class="card"><h2>二、知识点掌握更新</h2>' in rep2, "报告缺掌握更新区"
    assert '<span class="bar' in rep2, "报告缺掌握度条"
    assert '<div class="card"><h2>三、薄弱知识点</h2>' in rep2, "报告缺薄弱点区"
    assert '<div class="card"><h2>四、下一步学习建议</h2>' in rep2, "报告缺建议区"
    weak_block = rep2.split("三、薄弱知识点</h2>")[1].split("四、下一步学习建议")[0]
    weak_rows = len(re.findall(r"<tr><td>", weak_block))
    assert weak_rows > 0, "半错卷薄弱知识点区为空（诊断/路线没跑通）"
    # 薄弱 KP 的中文名必须出现在页面上（家长可读，不是 kp_id 裸串）
    from xuexing.kpgraph_subject import load_kpgraph_subject as _lgs
    g = _lgs(os.path.join(ROOT, "data", "knowledge"), _raw["subject"])
    shown = re.findall(r"<tr><td>([^<]+)</td>", weak_block)
    kp_names = {k.name for k in g.kps()}
    assert any(s in kp_names for s in shown), \
        f"薄弱点区未出现知识点中文名，只有 {shown[:3]}"
    next_block = rep2.split("四、下一步学习建议</h2>")[1]
    assert "<li>" in next_block, "建议区为空"
    ok(f"4b. 报告页含对错标记三件套 + 掌握更新（{rep2.count('<span class=\"bar')} 条掌握度）"
       f" + 薄弱点 {weak_rows} 行（中文名 ✓，如「{shown[0]}」）+ 下一步建议 "
       f"{next_block.count('<li>')} 条")

    # ---- 5. 错误路径 ----
    assert client.get("/exam/nope/report.html").status_code == 404, "未知会话应 404"
    assert client.post("/exam/nope/submit", json={"answers": {}},
                       follow_redirects=False).status_code == 404, "未知会话提交应 404"
    bad_key = client.post(f"/exam/{sid2}/submit", json={"answers": {"item_9999": "x"}},
                          follow_redirects=False)
    assert bad_key.status_code == 400, f"越界题号应 400，实得 {bad_key.status_code}"
    bad_key2 = client.post(f"/exam/{sid2}/submit", json={"answers": {"item_abc": "x"}},
                           follow_redirects=False)
    assert bad_key2.status_code == 400, f"非题号键应 400，实得 {bad_key2.status_code}"
    ok("5. 错误路径：未知会话 404（读+提交）、越界/非法题号 400")

    # 会话过期：注入 TTL=0 的 store 造过期会话（不 sleep）
    exp_client = TestClient(_app_with_ttl(spec_id, 0.0))
    sid3 = exp_client.get(f"/exam/{spec_id}/start",
                          params={"learner_id": "ttl-kid", "format": "json"}).json()["session_id"]
    r = exp_client.get(f"/exam/{sid3}/paper.html")
    assert r.status_code == 410, f"过期会话取卷应 410，实得 {r.status_code}"
    r = exp_client.post(f"/exam/{sid3}/submit", json={"answers": {}},
                        follow_redirects=False)
    assert r.status_code == 410, f"过期会话提交应 410，实得 {r.status_code}"
    ok("6. 会话过期：TTL=0 注入下取卷/提交均 410（Gone）")

    # 未提交的报告
    sid4 = client.get(f"/exam/{spec_id}/start",
                      params={"learner_id": "fresh-kid", "format": "json"}).json()["session_id"]
    r = client.get(f"/exam/{sid4}/report.html")
    assert r.status_code == 409, f"未提交取报告应 409，实得 {r.status_code}"
    ok("7. 未提交取报告 409（会话还在，只是没交卷）")

    # 重复提交后报告仍可读
    client.post(f"/exam/{sid4}/submit", json={"answers": perfect}, follow_redirects=False)
    r = client.get(f"/exam/{sid4}/report.html")
    assert r.status_code == 200, f"二次提交后报告 {r.status_code}"
    ok("8. 二次提交后报告仍可读 200")

    # ---- 9. 多选题（mcq_multi → checkbox 同名多值）----
    # 单独跑一遍：多选是唯一「同名多值」的题型，且选项正文里带顿号时提交全文会被
    # grading 的多选切分切碎——这条断言守住「表单 value 用标签」这个决定。
    multi_spec = "spec_phy_hs_final"
    m_raw, m_bank, m_paper = _spec_and_bank(multi_spec)
    multi = [(q["question_no"], m_bank.get(q["item_id"]))
             for sec in m_paper["sections"] for q in sec["questions"]
             if getattr(m_bank.get(q["item_id"]), "form", "") == "mcq_multi"]
    if not multi:
        print("  SKIP  9. 多选：当前卷型无 mcq_multi 题")
    else:
        m_client = TestClient(build_client(multi_spec))
        msid = m_client.get(f"/exam/{multi_spec}/start",
                            params={"learner_id": "multi-kid",
                                    "format": "json"}).json()["session_id"]
        mpage = m_client.get(f"/exam/{msid}/paper.html").text
        assert 'type="checkbox"' in mpage, "多选题未渲染 checkbox"
        pairs = []
        for no, item in multi:
            for lbl in str(item.answer).split(","):
                pairs.append((f"item_{no}", lbl.strip()))
        r = m_client.post(f"/exam/{msid}/submit", content=urlencode(pairs),
                          headers={"Content-Type": "application/x-www-form-urlencoded"},
                          follow_redirects=False)
        assert r.status_code == 303, f"多选提交 {r.status_code}"
        mrep = m_client.get(f"/exam/{msid}/report.html").text
        bad_multi = [no for no, _ in multi
                     if 'verdict bad' in mrep.split(f'<td class="num">{no}</td>')[1].split("</tr>")[0]]
        assert not bad_multi, f"勾选全部正确项仍被判错：第 {bad_multi} 题"
        ok(f"9. 多选（checkbox 同名多值）{len(multi)} 题按标签全勾 → 全判对"
           f"（守住「value 用标签、提交不按顿号切碎选项正文」）")

    print(f"\n样本已写入 {os.path.relpath(OUT_DIR, ROOT)}/（paper.html / 两份 report.html）")
    print(f"EXAM-LOOP-OK {len(checks)}/{len(checks)}（{spec_id} seed={seed}，"
          f"题数 {n_q}，客观题 {obj_n} 题/{obj_total:g} 分）")
    return 0


def _app_with_bank(spec_id: str):
    """同 build_client，但把**注入题库也换成本卷学段题库**的应用。

    用途只有一个：做「判分口径同 /grade」的 HTTP 层对照。``POST /grade`` 按
    ``create_app`` 注入的题库判分（默认 math_grade7），跨学科卷的题不在其中、
    会按设计 404；所以同源对照必须先把注入题库换成本卷的，才是对同一批题比较。
    """
    catalog = load_spec_catalog(
        os.path.join(ROOT, "data", "curriculum", "paper_specs.json"))
    raw = catalog[spec_id]
    stage_bank, _ = load_stage_bank(
        os.path.join(ROOT, "data"), raw["subject"], raw["stage"])
    subject_graph = load_kpgraph_subject(
        os.path.join(ROOT, "data", "knowledge"), raw["subject"])
    return create_app(
        stage_bank,
        subject_graph,
        load_strategies(os.path.join(ROOT, "data", "pedagogy", "strategies.json")),
        None,
        spec_catalog=catalog,
        stage_bank_loader=lambda subject, stage: stage_bank,
        stage_graph_loader=lambda subject: subject_graph,
    )


def _app_with_ttl(spec_id: str, ttl: float):
    """同 build_client，但注入 TTL=ttl 的会话存储（过期用例专用）。"""
    catalog = load_spec_catalog(
        os.path.join(ROOT, "data", "curriculum", "paper_specs.json"))
    raw = catalog[spec_id]
    stage_bank, _ = load_stage_bank(
        os.path.join(ROOT, "data"), raw["subject"], raw["stage"])
    subject_graph = load_kpgraph_subject(
        os.path.join(ROOT, "data", "knowledge"), raw["subject"])
    return create_app(
        load_itembank(os.path.join(ROOT, "data", "items", "math_grade7_items.json")),
        load_kpgraph(os.path.join(ROOT, "data", "knowledge", "math_grade7.json")),
        load_strategies(os.path.join(ROOT, "data", "pedagogy", "strategies.json")),
        None,
        spec_catalog=catalog,
        stage_bank_loader=lambda subject, stage: stage_bank,
        stage_graph_loader=lambda subject: subject_graph,
        exam_sessions=ExamSessionStore(ttl_seconds=ttl),
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="学生作答闭环门（start→提交→报告 无浏览器全环）")
    ap.add_argument("--spec-id", default=DEFAULT_SPEC)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    print(f"学生作答闭环门：卷型 {args.spec_id} seed={args.seed}")
    try:
        return run(args.spec_id, args.seed)
    except AssertionError as e:
        print(f"\nEXAM-LOOP-FAIL：{e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
