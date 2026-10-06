"""单元测试：paper_render —— 成品卷渲染（打印友好 HTML + 纯文本备用）。

自闭式夹具（不依赖 data/ 的用例）钉住行为契约：
- 渲染结构：题块数==骨架小题数、小题号全卷连续、大题标题带每题/共分值、
  卷头（标题/满分/时长/满分注意）、A4 打印分页 CSS、页脚页码 CSS；
- 转义：题面/选项含 <>&"' 时按字面转义呈现，绝无原生 <script> 等可执行标记；
- 红线（出卷侧）：answer/solution 字段值绝不进 HTML/文本；全卷无 answer/
  solution 词根（含 CSS 类名——作答框类名刻意用 reply-box）；泄漏扫描器本身
  有阴性对照（构造坏产物必须被 flags）；
- 端点：GET /papers/by-spec/{spec_id}/render.html 与 render.txt——200 与
  content-type、与 POST /papers/by-spec 同源同题序、未知卷型 404、卷型内部
  不一致 400、非法 query 422。
真实数据用例只做廉价不变式：真实物理初中卷渲染合法且标答/解析零出现。
"""
import os
import re

import pytest
from fastapi.testclient import TestClient

from xuexing.itembank import ItemBank
from xuexing.paper_by_spec import generate_paper_by_spec
from xuexing.paper_render import (
    FORBIDDEN_TOKENS,
    PaperRenderError,
    check_html_tag_balance,
    format_points,
    human_paper_title,
    redline_report,
    render_paper_html,
    render_paper_text,
)
from xuexing.server import create_app
from xuexing.types import Item

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# 绝密标记串：若出现在成品卷中即红线击穿（刻意不含 answer/solution ASCII 词根，
# 否则词根扫描会先于值扫描报警，测不到「值级泄漏」这一层）。
_SECRET_ANSWER = "【绝密】never-show-73512"
_SECRET_SOLUTION = "【绝密】hide-me-918273"

MINI_SPEC = {
    "id": "spec_render_demo",
    "subject": "physics",
    "stage": "junior",
    "usage": "final_exam",
    "duration_min": 80,
    "total_points": 10,
    "sections": [
        {"title": "一、选择题", "form": "choice", "count": 2, "points_each": 3},
        {"title": "二、解答题", "form": "solve", "count": 1, "points_each": 4},
    ],
}


def mini_bank(secret=False) -> ItemBank:
    """两道单选 + 一道解答。secret=True 时标答/解析带绝密标记串（红线用）。"""
    b = ItemBank()
    answer = _SECRET_ANSWER if secret else "B"
    solution = _SECRET_SOLUTION if secret else "因为所以"
    for i, d in (("c1", 0.2), ("c2", 0.5)):
        b.add(Item(id=i, item_type="choice", stem=f"选择-{i}-（　　）", answer=answer,
                   kps=["kp"], difficulty=d, solution=solution,
                   options=["A. 甲", "B. 乙"], form="mcq_single"))
    b.add(Item(id="j1", item_type="solve", stem="解答-计算题", answer=answer,
               kps=["kp"], difficulty=0.6, solution=solution, form="简答"))
    return b


@pytest.fixture(scope="module")
def paper():
    bank = mini_bank()
    return generate_paper_by_spec(bank, MINI_SPEC, seed=42, spec_id=MINI_SPEC["id"])


@pytest.fixture(scope="module")
def html_doc(paper):
    return render_paper_html(paper, mini_bank())


@pytest.fixture(scope="module")
def text_doc(paper):
    return render_paper_text(paper, mini_bank())


# ---------- 渲染结构 ----------

def test_html_structure_matches_skeleton(html_doc, paper):
    # 文档骨架与打印 CSS：DOCTYPE / charset / A4 分页 / 页脚页码
    assert html_doc.startswith("<!DOCTYPE html>")
    assert 'charset="utf-8"' in html_doc
    assert "@page" in html_doc and "size: A4" in html_doc
    assert "counter(page)" in html_doc
    # 题块数==骨架小题数，小题号全卷连续 1..N 且有序
    ids = [int(m) for m in
           __import__("re").findall(r'<div class="question" id="q(\d+)">', html_doc)]
    assert ids == list(range(1, paper["question_count"] + 1)) == [1, 2, 3]
    # 大题标题带每题/共分值；两道大题都在
    assert "一、选择题" in html_doc and "（每题 3 分，共 6 分）" in html_doc
    assert "二、解答题" in html_doc and "（每题 4 分，共 4 分）" in html_doc
    # 卷头：人话标题 / 满分 / 时长 / 题数 / 卷型 / 满分注意
    assert "<title>初中物理期末考试卷</title>" in html_doc
    assert "满分 10 分" in html_doc and "考试时长 80 分钟" in html_doc
    assert "共 3 题" in html_doc and "卷型 spec_render_demo" in html_doc
    assert "满分注意" in html_doc
    # 逐题分值标注恰出现一次，合计==卷型总分
    pts = [float(m) for m in
           __import__("re").findall(r'<span class="q-points">（([0-9.]+)分）</span>', html_doc)]
    assert pts == [3.0, 3.0, 4.0]
    assert sum(pts) == 10.0
    # 标签配平（内核自校验器）
    assert check_html_tag_balance(html_doc) == []


def test_html_choice_options_vertical(html_doc):
    # 选择题选项竖排：每项独立块级元素、保持题库顺序、转义后原样呈现
    assert html_doc.index('<div class="q-option">A. 甲</div>') < \
        html_doc.index('<div class="q-option">B. 乙</div>')
    assert html_doc.count('<div class="q-option">') == 4  # 2 题 × 2 选项


def test_reply_areas_by_item_type(html_doc, text_doc):
    # 解答题留答题框（reply-box 高框）；选择题有选项则不设作答区
    assert '<div class="reply-box" style="height: 48mm;"></div>' in html_doc
    block = html_doc[html_doc.index('id="q3"'):]
    assert "reply-box" in block[:400]
    choice_blocks = html_doc[html_doc.index('id="q1"'):html_doc.index('id="q3"')]
    assert "reply-box" not in choice_blocks and "blank-line" not in choice_blocks


def test_render_deterministic(paper):
    bank = mini_bank()
    assert render_paper_html(paper, bank) == render_paper_html(paper, bank)
    assert render_paper_text(paper, bank) == render_paper_text(paper, bank)


def test_format_points_and_title():
    # 分值格式化：整数去尾、小数保留；人话标题
    assert format_points(3) == "3" and format_points(3.0) == "3"
    assert format_points(7.5) == "7.5"
    assert human_paper_title(
        {"subject": "physics", "stage": "junior", "usage": "final_exam"}) == "初中物理期末考试卷"
    assert human_paper_title(
        {"subject": "math", "stage": "primary", "usage": "unit_test"}) == "小学数学单元测试卷"
    # 未收录的枚举值原样回显（不抛异常）
    assert human_paper_title(
        {"subject": "ocr", "stage": "junior", "usage": "quiz"}) == "初中ocrquiz卷"


# ---------- 转义 ----------

def test_html_escapes_hostile_stem_and_options():
    bank = ItemBank()
    bank.add(Item(id="x1", item_type="choice", form="mcq_single",
                  stem='<script>alert("x")</script> 已知 a<b & c>d，选（　　）',
                  answer="B", kps=["kp"], difficulty=0.5,
                  options=['<b>A. 选项&"引号"</b>', "B. 正常"], solution="x"))
    spec = {"id": "spec_escape", "subject": "demo", "stage": "junior",
            "usage": "final_exam", "duration_min": 10, "total_points": 5,
            "sections": [{"title": "一、选择<script>", "form": "choice",
                          "count": 1, "points_each": 5}]}
    paper = generate_paper_by_spec(bank, spec, seed=1, spec_id="spec_escape")
    doc = render_paper_html(paper, bank)
    # 全部动态文本按实体转义，绝无原生可执行标记
    assert "&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;" in doc
    assert "<script>" not in doc and "<b>" not in doc
    assert "a&lt;b &amp; c&gt;d" in doc
    assert '选项&amp;&quot;引号&quot;&lt;/b&gt;' in doc
    assert "<h2" in doc and "一、选择&lt;script&gt;" in doc  # 大题标题同样转义
    assert check_html_tag_balance(doc) == []  # 转义后配平不受敌意输入破坏


# ---------- 红线：答案/解析绝不渲染 ----------

def test_redline_no_answer_solution_leak():
    bank = mini_bank(secret=True)
    paper = generate_paper_by_spec(bank, MINI_SPEC, seed=42, spec_id=MINI_SPEC["id"])
    doc_html = render_paper_html(paper, bank)
    doc_text = render_paper_text(paper, bank)
    # 值级：绝密标记串（答案/解析）绝不进 HTML/文本
    for doc in (doc_html, doc_text):
        assert _SECRET_ANSWER not in doc
        assert _SECRET_SOLUTION not in doc
    # 词根级：全卷无 answer/solution 字样（含类名/注释——作答框类名刻意用 reply-box）
    for tok in FORBIDDEN_TOKENS:
        assert tok.lower() not in doc_html.lower(), tok
        assert tok.lower() not in doc_text.lower(), tok
    # 内核红线自检：干净产物零报告
    assert redline_report(paper, bank, doc_html, doc_text) == []


def test_redline_report_flags_planted_leak():
    """泄漏扫描器对照实验：渲染产物被手工植入答案值时必须被 flags（防扫描器
    恒真空转）；同时题干自带答案（剔除 stem 后）不误报。"""
    bank = mini_bank(secret=True)
    paper = generate_paper_by_spec(bank, MINI_SPEC, seed=42, spec_id=MINI_SPEC["id"])
    doc_html = render_paper_html(paper, bank)
    doc_text = render_paper_text(paper, bank)
    bad_html = doc_html.replace("</body>", _SECRET_ANSWER + "</body>")
    report = redline_report(paper, bank, bad_html, doc_text)
    assert report and _SECRET_ANSWER in report[0] and "html" in report[0]
    # 题干自带答案（che 类数据缺陷）：值只出现在 stem 内 → 剔除 stem 后不误报
    bank2 = ItemBank()
    bank2.add(Item(id="s1", item_type="fill", form="fill_blank",
                   stem="以______（填分子或离子）的形式", answer="分子或离子",
                   kps=["kp"], difficulty=0.5, solution=""))
    spec2 = {"id": "spec_stemleak", "subject": "demo", "stage": "junior",
             "usage": "final_exam", "duration_min": 10, "total_points": 5,
             "sections": [{"title": "一、填空", "form": "fill",
                           "count": 1, "points_each": 5}]}
    paper2 = generate_paper_by_spec(bank2, spec2, seed=1, spec_id="spec_stemleak")
    assert redline_report(paper2, bank2,
                          render_paper_html(paper2, bank2),
                          render_paper_text(paper2, bank2)) == []


# ---------- fail-closed 与标签配平自校验 ----------

def test_missing_item_or_blank_stem_fail_closed():
    bank = mini_bank()
    paper = generate_paper_by_spec(bank, MINI_SPEC, seed=42, spec_id=MINI_SPEC["id"])
    # 题在库中消失（ghost）：结构合法但取题失败 → fail-closed
    ghost = dict(paper, question_count=1, sections=[
        dict(paper["sections"][0], count=1, section_points=3,
             questions=[dict(paper["sections"][0]["questions"][0], item_id="ghost")])])
    with pytest.raises(PaperRenderError, match="ghost"):
        render_paper_html(ghost, bank)
    empty_stem_bank = ItemBank()
    empty_stem_bank.add(Item(id="e1", item_type="solve", stem="  ", answer="a",
                             kps=["kp"], difficulty=0.5, form="solve"))
    spec1 = {"id": "spec_one", "subject": "demo", "stage": "junior",
             "usage": "final_exam", "duration_min": 10, "total_points": 5,
             "sections": [{"title": "一、解答", "form": "solve",
                           "count": 1, "points_each": 5}]}
    p1 = generate_paper_by_spec(empty_stem_bank, spec1, seed=1, spec_id="spec_one")
    with pytest.raises(PaperRenderError, match="blank stem"):
        render_paper_html(p1, empty_stem_bank)


def test_check_html_tag_balance():
    # 配平器本身可用：交叉嵌套 / 未闭合 / 多余闭标签都要报；合法文档零报
    assert check_html_tag_balance("<html><body><p>x</p></body></html>") == []
    assert any("crosses" in e for e in check_html_tag_balance("<div><p>x</div>"))
    assert any("unclosed" in e for e in check_html_tag_balance("<div><p>x"))
    assert any("empty stack" in e for e in check_html_tag_balance("<div>x</div></b>"))
    assert any("stray" in e for e in
               check_html_tag_balance("<div><p>x</span></p></div>"))
    # 空元素免闭配
    assert check_html_tag_balance('<html><meta charset="utf-8"><br></html>') == []


# ---------- 纯文本简版 ----------

def test_text_version_simple(text_doc):
    assert "<div" not in text_doc and "<html" not in text_doc
    assert text_doc.startswith("初中物理期末考试卷")
    assert "满分 10 分" in text_doc and "共 3 题" in text_doc
    for no in (1, 2, 3):
        assert f"  {no}." in text_doc
    assert "一、选择题（每题 3 分，共 6 分）" in text_doc
    assert "A. 甲" in text_doc and "B. 乙" in text_doc
    assert "＿" in text_doc  # 解答题作答区占位


# ---------- 真实数据（廉价不变式） ----------

def test_render_real_spec_phy_jr_final():
    from xuexing.paper_by_spec import load_spec_catalog, load_stage_bank

    catalog = load_spec_catalog(os.path.join(ROOT, "data", "curriculum", "paper_specs.json"))
    bank, _ = load_stage_bank(os.path.join(ROOT, "data"), "physics", "junior")
    paper = generate_paper_by_spec(bank, catalog["spec_phy_jr_final"],
                                   seed=42, spec_id="spec_phy_jr_final")
    doc = render_paper_html(paper, bank)
    assert check_html_tag_balance(doc) == []
    assert doc.count('<div class="question"') == paper["question_count"] == 31
    assert "满分 100 分" in doc and "共 31 题" in doc
    # 红线：真实库全量扫描——词根零出现；长标答/解析值（len>=10，避免短语
    # 与他题题干的合法词汇碰撞）零出现
    low = doc.lower()
    for tok in FORBIDDEN_TOKENS:
        assert tok.lower() not in low, tok
    sel = {q["item_id"] for s in paper["sections"] for q in s["questions"]}
    for item in bank.items():
        if item.id not in sel:
            continue
        for val in (item.answer.strip(), item.solution.strip()):
            if len(val) >= 10:
                assert val not in doc, f"{item.id} 作答依据泄漏"
    assert redline_report(paper, bank, doc, render_paper_text(paper, bank)) == []


# ---------- 端点：GET /papers/by-spec/{spec_id}/render.html 与 render.txt ----------

@pytest.fixture(scope="module")
def render_client(bank, graph, strategies):
    app = create_app(bank, graph, strategies, [],
                     spec_catalog={MINI_SPEC["id"]: MINI_SPEC},
                     stage_bank_loader=lambda subject, stage: mini_bank())
    return TestClient(app)


def test_endpoint_render_html_matches_post_structure(render_client):
    # 同 (spec_id, seed) 下，GET 渲染卷与 POST 结构卷同源同题序
    post = render_client.post("/papers/by-spec", json={"spec_id": MINI_SPEC["id"], "seed": 42})
    assert post.status_code == 200
    posted = post.json()
    flat = [q["item_id"] for s in posted["sections"] for q in s["questions"]]
    r = render_client.get(f"/papers/by-spec/{MINI_SPEC['id']}/render.html",
                          params={"seed": 42})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    doc = r.text
    bank = mini_bank()
    for i, item_id in enumerate(flat, start=1):
        assert f'id="q{i}"' in doc
        stem = bank.get(item_id).stem
        assert stem in doc, f"第 {i} 题题面与 POST 结构不一致"
    assert "<title>初中物理期末考试卷</title>" in doc


def test_endpoint_render_text_ok(render_client):
    r = render_client.get(f"/papers/by-spec/{MINI_SPEC['id']}/render.txt")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/plain")
    assert "初中物理期末考试卷" in r.text


def test_endpoint_render_deterministic(render_client):
    url = f"/papers/by-spec/{MINI_SPEC['id']}/render.html"
    assert render_client.get(url, params={"seed": 42}).content == \
        render_client.get(url, params={"seed": 42}).content


def test_endpoint_render_unknown_spec_404(render_client):
    assert render_client.get("/papers/by-spec/no_such_spec/render.html").status_code == 404
    assert render_client.get("/papers/by-spec/no_such_spec/render.txt").status_code == 404


def test_endpoint_render_inconsistent_spec_400(bank, graph, strategies):
    bad = dict(MINI_SPEC, id="spec_render_badtotal", total_points=11)  # 节和 10 != 11
    app = create_app(bank, graph, strategies, [],
                     spec_catalog={"spec_render_badtotal": bad,
                                   MINI_SPEC["id"]: MINI_SPEC},
                     stage_bank_loader=lambda subject, stage: mini_bank())
    client = TestClient(app)
    r = client.get("/papers/by-spec/spec_render_badtotal/render.html")
    assert r.status_code == 400
    assert "points sum 10 != total_points 11" in r.json()["detail"]


def test_endpoint_render_bad_query_422(render_client):
    # seed 类型违规 → pydantic/FastAPI 422
    assert render_client.get(f"/papers/by-spec/{MINI_SPEC['id']}/render.html",
                             params={"seed": "abc"}).status_code == 422
    # difficulty_target 越界是合法 float → 领域校验 400（与 POST 出卷同语义）
    assert render_client.get(f"/papers/by-spec/{MINI_SPEC['id']}/render.html",
                             params={"difficulty_target": 7}).status_code == 400


# ---------------------------------------------------------------------------
# 红线语料适配（2026-10-06）——短数字巧合豁免与英语卷词根豁免的边界钉板
# ---------------------------------------------------------------------------

def test_short_numeric_exemption_boundary():
    """纯数字短值(≤4, 至多一个小数点)豁免；长数字串/含字母值不豁免。"""
    from xuexing.paper_render import _is_short_numeric
    assert _is_short_numeric("25") and _is_short_numeric("1.5") and _is_short_numeric("13")
    assert not _is_short_numeric("11010519491231002X")  # 身份证形态长值
    assert not _is_short_numeric("1.2.3") and not _is_short_numeric("abc") and not _is_short_numeric("")
    assert not _is_short_numeric("123456")  # 长数字串不豁免


def test_english_token_exempt_only_for_english_papers():
    """英语卷豁免 ASCII 词根；非英语卷出现 answer 词根仍判违规。"""
    from xuexing.paper_render import redline_report
    # 中文卷(html 含 'answer') 应违规
    paper = {"subject": "math", "total_points": 10, "duration_min": 40,
             "sections": []}
    v = redline_report(paper, {}, "see answer here", "")
    assert any("answer" in x for x in v)
    # 英语卷同内容不违规(ASCII 词根豁免), 但中文禁词照扫
    paper_en = {"subject": "english", "total_points": 10, "duration_min": 40,
                "sections": []}
    v2 = redline_report(paper_en, {}, "see answer here", "")
    assert not any("answer" in x for x in v2)
    v3 = redline_report(paper_en, {}, "参考答案", "")
    assert any("参考答案" in x for x in v3)
