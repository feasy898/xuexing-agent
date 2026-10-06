"""学生作答闭环验收门（无浏览器全环，exit 0 = 门通过）。

为什么需要本工具：出卷（tools/check_paper_spec.py）、成品卷渲染
（tools/check_paper_render.py）都有离线门，但「学生真的能做一次题」这条链
（开卷 → 作答页 → 交卷判分 → 画像落地 → 报告页）此前没有任何机器门：出错
形态是「页面能开但交卷 500」「报告里没有薄弱点」这种只有人点开才发现的问题。
本工具用 fastapi.testclient.TestClient 走完整 HTTP 环（不占端口、不联网、
不需要浏览器），逐项断言：

  (1) 开卷 GET /exam/{spec_id}/start?learner_id=X&seed=.. → 200 text/html；
      会话号可从 form action 提取；**learner 回显**在页面上；题块数 ==
      question_count；**作答字段组数（name=item_{no} 去重）== 题数**（每题恰好
      一组可提交控件；单选/多选题一组里有多个 radio/checkbox，这是「选项」不是
      「题目」——同时断言控件总数 == Σ选项数 + 非选择题数，两头对齐）；
  (2) 作答页红线：复用 xuexing.paper_render.redline_report 的同一实现——页面上
      不得出现 answer/solution 词根，也不得出现任一题的 answer/solution 字段值；
      标签配平（check_html_tag_balance 零错误）、自包含（无 script/link/外链）；
  (3) 全对作答：按题库 answer 逐题填入（客观题全对）→ POST submit（原生
      form 编码，模拟浏览器点「交卷」）→ 303 + Location 指向 report.html；
      GET /profile 断言**已落库**（evidence 计数 == 客观题数）；
  (4) 半错作答：独立会话，同一份卷面（seed 相同 -> 题序相同）客观题答对一半、
      另一半填错 -> 得分 < 满分且 == 预期；报告页含对错标记（正确/错误两类都
      出现）、**薄弱知识点**（掌握度低于阈值的知识点及其 id）、下一步学习建议
      （route 产出的步骤）以及本次待批改的解答题说明；
  (5) 错误契约：未知会话 404、未知卷型 404、缺 learner_id 400、越界
      difficulty_target 400、越界题号 400、重复交卷 409、过期会话 410
      （用 ExamStore(ttl=0) 构造）。

门通过条件（exit 0）：上述各项全部通过，失败即打印并 exit 1。纯校验，不落盘。

用法：python tools/check_exam_loop.py [--spec-id spec_phy_jr_final] [--seed 42]
"""
import argparse
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

try:  # Windows 控制台中文输出保护
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

from fastapi.testclient import TestClient  # noqa: E402

from xuexing import load_strategies  # noqa: E402
from xuexing.exam import AUTO_ITEM_TYPES, ExamStore, grade_submission  # noqa: E402
from xuexing.kpgraph_subject import load_kpgraph_subject  # noqa: E402
from xuexing.paper_by_spec import (  # noqa: E402
    generate_paper_by_spec,
    load_spec_catalog,
    load_stage_bank,
)
from xuexing.paper_render import check_html_tag_balance, redline_report  # noqa: E402
from xuexing.server import create_app  # noqa: E402

STRATEGIES_PATH = os.path.join(ROOT, "data", "pedagogy", "strategies.json")
CURRICULUM = os.path.join(ROOT, "data")

_ACTION_RE = re.compile(r'action="/exam/([0-9a-f]+)/submit"')
_Q_BLOCK_RE = re.compile(r'<div class="question" id="q(\d+)">')
_FIELD_RE = re.compile(r'<(?:input|textarea)\b[^>]*\bname="item_(\d+)"')
_RADIO_RE = re.compile(r'<input type="(radio|checkbox)"[^>]*name="item_(\d+)"')
_TEXTIN_RE = re.compile(r'<input type="text" name="item_(\d+)"')
_TEXTAREA_RE = re.compile(r'<textarea name="item_(\d+)"')

# 卷型必须能出卷（题库同型题足）且含客观题（否则「判分」无从验起）
DEFAULT_SPEC = "spec_phy_jr_final"


def build(spec_id: str, seed: int, store=None):
    """按真实 data/ 装一个 app：卷型库 + 学段题库 + 学科图 + 策略库。"""
    catalog = load_spec_catalog(os.path.join(CURRICULUM, "curriculum", "paper_specs.json"))
    raw = catalog[spec_id]
    bank = load_stage_bank(CURRICULUM, raw["subject"], raw["stage"])[0]
    graph = load_kpgraph_subject(os.path.join(CURRICULUM, "knowledge"), raw["subject"])
    app = create_app(
        bank, graph, load_strategies(STRATEGIES_PATH), [],
        spec_catalog=catalog,
        stage_bank_loader=lambda subject, stage: bank,
        subject_graph_loader=lambda subject: graph,
        exam_store=store,
    )
    return app, catalog[spec_id], bank


def session_of(sheet_html: str) -> str:
    m = _ACTION_RE.search(sheet_html)
    assert m, "作答页没有 form action（无法定位会话号）"
    return m.group(1)


def paper_answers(paper, bank) -> dict:
    """卷面 -> {题号: 题库标准答案}（客观题即答即对；主观题字面答案）。"""
    return {q["question_no"]: bank.get(q["item_id"]).answer
            for sec in paper["sections"] for q in sec["questions"]}


def half_wrong_answers(paper, bank) -> dict:
    """客观题答对一半（按题号顺序交替），主观题照抄标准答案（不进得分）。"""
    out = {}
    auto_seen = 0
    for sec in paper["sections"]:
        for q in sec["questions"]:
            item = bank.get(q["item_id"])
            no = q["question_no"]
            if getattr(item, "item_type", "") in AUTO_ITEM_TYPES:
                auto_seen += 1
                if auto_seen % 2 == 1:
                    out[no] = item.answer
                    continue
                options = [str(o).strip() for o in (getattr(item, "options", None) or [])]
                wrong = "作答必错" if not options else _first_wrong_option(options, item)
                out[no] = wrong
            else:
                out[no] = item.answer
    return out


def _first_wrong_option(options, item) -> str:
    """选一个非正确项（按 grading 的标签口径比对；找不到就退回一个字面串）。"""
    labels = [o.split(".", 1)[0].strip() for o in options]
    correct = str(item.answer).strip()
    for opt, label in zip(options, labels):
        if label != correct and opt != correct:
            return opt
    return "作答必错"


def check_step_1_start(app, spec_id, seed, learner_id) -> str:
    """开卷 -> 会话 + 可作答卷 HTML（题数/控件数/learner 回显）。"""
    c = TestClient(app)
    r = c.get(f"/exam/{spec_id}/start", params={"learner_id": learner_id, "seed": seed})
    assert r.status_code == 200, f"start 状态码 {r.status_code}：{r.text[:200]}"
    assert r.headers["content-type"].startswith("text/html"), r.headers["content-type"]
    sheet = r.text
    assert sheet.startswith("<!DOCTYPE html>") and 'charset="utf-8"' in sheet
    assert learner_id in sheet, "作答页没有回显 learner_id"

    paper = _paper_for(app, spec_id, seed)
    n_q = paper["question_count"]
    nos = [int(m) for m in _Q_BLOCK_RE.findall(sheet)]
    assert nos == list(range(1, n_q + 1)), f"题块号非连续 1..{n_q}：{len(nos)} 块"

    fields = _FIELD_RE.findall(sheet)
    groups = {int(x) for x in fields}
    assert groups == set(range(1, n_q + 1)), \
        f"作答字段组数 {len(groups)} != 题数 {n_q}（缺 {sorted(set(range(1, n_q + 1)) - groups)[:5]}）"

    # 控件总数 = Σ选择题选项数 + 非选择题数（选择题一个控件/选项，其余一个控件/题）
    n_opts = sum(len([o for o in (getattr(bank_get(app, q["item_id"]), "options", None) or [])])
                 for sec in paper["sections"] for q in sec["questions"])
    n_other = sum(1 for sec in paper["sections"] for q in sec["questions"]
                  if not (getattr(bank_get(app, q["item_id"]), "options", None) or []))
    assert len(fields) == n_opts + n_other, \
        f"控件总数 {len(fields)} != 选项数 {n_opts} + 非选择题数 {n_other}"
    assert len(_TEXTAREA_RE.findall(sheet)) == sum(
        1 for sec in paper["sections"] for q in sec["questions"]
        if bank_get(app, q["item_id"]).item_type not in AUTO_ITEM_TYPES), "解答题未给 textarea"
    assert len(_TEXTIN_RE.findall(sheet)) == sum(
        1 for sec in paper["sections"] for q in sec["questions"]
        if bank_get(app, q["item_id"]).item_type == "fill"), "填空题未给 text input"
    radios = _RADIO_RE.findall(sheet)
    assert all(t in ("radio", "checkbox") for t, _ in radios), "选择题控件类型异常"
    sess = session_of(sheet)
    return f"200 | 题×{n_q} 字段组×{len(groups)} 控件×{len(fields)} " \
           f"(选项×{n_opts}+其他×{n_other}) 会话={sess} learner 回显✓"


def check_step_2_redline(app, spec_id, seed) -> str:
    """作答页红线：与成品卷同一 redline_report；标签配平 + 自包含。"""
    c = TestClient(app)
    sheet = c.get("/exam/%s/start" % spec_id,
                  params={"learner_id": "stu-redline", "seed": seed}).text
    paper = _paper_for(app, spec_id, seed)
    errs = check_html_tag_balance(sheet)
    assert not errs, f"作答页标签配平错误：{errs[:3]}"
    for needle in ("<script", "<link", "src=", "http://", "https://", "url("):
        assert needle not in sheet.lower(), f"作答页非自包含（{needle!r}）"
    # 纯文本替代品用同一份卷渲染（供 redline_report 双输入），与 check_paper_render 同源
    from xuexing.paper_render import render_paper_text
    text_doc = render_paper_text(paper, bank_of(app))
    violations = redline_report(paper, bank_of(app), sheet, text_doc)
    assert not violations, f"作答页红线违规：{violations[:3]}"
    return "红线✓ 配平✓ 自包含✓（复用 redline_report/check_html_tag_balance）"


def check_step_3_all_correct(app, spec_id, seed) -> str:
    """全对作答 -> 303 -> 报告 200 -> 画像落库。"""
    c = TestClient(app)
    learner = "stu-all-correct"
    sheet = c.get(f"/exam/{spec_id}/start",
                  params={"learner_id": learner, "seed": seed}).text
    sess = session_of(sheet)
    answers = paper_answers(_paper_for(app, spec_id, seed), bank_of(app))
    form = {f"item_{no}": v for no, v in answers.items()}

    r = c.post(f"/exam/{sess}/submit", data=form, follow_redirects=False)
    assert r.status_code == 303, f"submit 状态码 {r.status_code}：{r.text[:200]}"
    assert r.headers["location"] == f"/exam/{sess}/report.html", r.headers.get("location")

    rep = c.get(f"/exam/{sess}/report.html")
    assert rep.status_code == 200, f"report 状态码 {rep.status_code}"
    assert not check_html_tag_balance(rep.text), "报告页标签配平错误"

    # 落库：客观题全对 -> 得分 == 客观题满分；evidence 计数 == 客观题数
    paper = _paper_for(app, spec_id, seed)
    graded = grade_submission(paper, bank_of(app), answers)
    assert graded["earned"] == graded["auto_points"], \
        f"全对应满分：{graded['earned']} != {graded['auto_points']}"
    prof = c.get(f"/learners/{learner}/profile")
    assert prof.status_code == 200, f"画像未落库：{prof.status_code}"
    body = prof.json()
    assert sum(body["evidence"].values()) == graded["auto_count"], \
        f"证据数 {sum(body['evidence'].values())} != 客观题数 {graded['auto_count']}"
    plan = c.get(f"/learners/{learner}/plan")
    assert plan.status_code == 200, f"计划端点不可用：{plan.status_code}"
    return f"303 -> report 200 | 得分 {graded['earned']}/{graded['auto_points']} " \
           f"客观题×{graded['auto_count']} 待批改×{graded['pending_count']} " \
           f"evidence 合计={sum(body['evidence'].values())} /plan 200"


def check_step_4_half_wrong(app, spec_id, seed) -> str:
    """半错作答 -> 分数减半 -> 报告含对错标记 + 薄弱知识点 + 建议 + 待批改说明。"""
    c = TestClient(app)
    learner = "stu-half-wrong"
    sheet = c.get(f"/exam/{spec_id}/start",
                  params={"learner_id": learner, "seed": seed}).text
    sess = session_of(sheet)
    paper = _paper_for(app, spec_id, seed)
    answers = half_wrong_answers(paper, bank_of(app))
    form = {f"item_{no}": v for no, v in answers.items()}

    r = c.post(f"/exam/{sess}/submit", data=form, follow_redirects=False)
    assert r.status_code == 303, f"submit 状态码 {r.status_code}：{r.text[:200]}"
    rep = c.get(f"/exam/{sess}/report.html")
    assert rep.status_code == 200
    page = rep.text

    graded = grade_submission(paper, bank_of(app), answers)
    assert 0 < graded["earned"] < graded["auto_points"], \
        f"半错卷应部分得分：{graded['earned']}/{graded['auto_points']}"
    n_wrong = graded["auto_count"] - graded["auto_correct"]
    assert graded["auto_correct"] > 0 and n_wrong > 0, \
        f"半错卷两类判定都应出现：{graded['auto_correct']}/{graded['auto_count']}"
    # 判定的正确/错误必须与「我们故意填错的那一半」一一对应（防止填错手法失效）
    correct_answers = paper_answers(paper, bank_of(app))
    intended_wrong = {no for no, v in answers.items() if v != correct_answers[no]}
    actually_wrong = {rec["question_no"] for rec in graded["items"]
                      if rec["verdict"] == "wrong"}
    assert actually_wrong == intended_wrong, \
        f"故意填错与判错不一致：填错 {sorted(intended_wrong)[:5]} 判错 {sorted(actually_wrong)[:5]}"

    # 对错标记：两类都要出现在报告页（逐题表）
    assert "✓ 正确" in page and "✗ 错误" in page, "报告缺对错标记"
    assert f"{graded['auto_correct']} 道" in page, "报告未回显答对题数"
    # 薄弱知识点：报告的「知识点掌握更新」段落里必须有本卷题目命中的 kp（id 可见）
    prof = c.get(f"/learners/{learner}/profile").json()
    weak = [kp for kp, m in prof["mastery"].items()
            if m < 0.65 and prof["evidence"].get(kp, 0) > 0]
    assert weak, "半错卷理应产生低于阈值的知识点"
    assert "知识点掌握更新" in page, "报告缺知识点掌握更新段"
    assert any(kp in page for kp in weak), f"报告未出现薄弱知识点 id：{weak[:3]}"
    # 下一步学习建议：route 产出的步骤（薄弱 kp 出现在建议表里）
    assert "薄弱点与下一步学习建议" in page, "报告缺学习建议段"
    assert any(kp in page for kp in weak), "建议段未命中薄弱知识点"
    # 主观题待批改说明与原样作答回显
    if graded["pending_count"]:
        assert "待教师批改" in page, "报告缺待批改说明"
    # 报告页自包含
    for needle in ("<script", "<link", "src=", "http://", "https://"):
        assert needle not in page.lower(), f"报告页非自包含（{needle!r}）"
    return f"303 -> report 200 | 得分 {graded['earned']}/{graded['auto_points']} " \
           f"（对{graded['auto_correct']}/错{graded['auto_count'] - graded['auto_correct']}）" \
           f"薄弱知识点×{len(weak)} 建议段✓ 待批改×{graded['pending_count']}"


def check_step_5_errors(app, spec_id, seed) -> str:
    """错误契约：404 / 400 / 409 / 410。"""
    c = TestClient(app)
    detail = []
    # 未知会话 -> 404（submit 与 report 都是）
    r = c.post("/exam/deadbeefdeadbeef/submit", data={}, follow_redirects=False)
    assert r.status_code == 404, f"未知会话 submit 应 404，实得 {r.status_code}"
    r = c.get("/exam/deadbeefdeadbeef/report.html")
    assert r.status_code == 404, f"未知会话 report 应 404，实得 {r.status_code}"
    detail.append("未知会话 404/404")
    # 未知卷型 -> 404
    r = c.get("/exam/no-such-spec/start", params={"learner_id": "x"})
    assert r.status_code == 404, f"未知卷型应 404，实得 {r.status_code}"
    detail.append("未知卷型 404")
    # 缺 learner_id -> 400（FastAPI 必填 query 缺失为 422；空串才是 400）
    r = c.get(f"/exam/{spec_id}/start", params={"learner_id": ""})
    assert r.status_code == 400, f"空 learner_id 应 400，实得 {r.status_code}"
    detail.append("空 learner_id 400")
    # difficulty_target 越界 -> 400（复用出卷 fail-closed）
    r = c.get(f"/exam/{spec_id}/start",
              params={"learner_id": "x", "difficulty_target": 1.5})
    assert r.status_code == 400, f"越界 difficulty_target 应 400，实得 {r.status_code}"
    detail.append("越界 difficulty_target 400")
    # 越界题号 / 非法字段名 -> 400
    sess = session_of(c.get(f"/exam/{spec_id}/start",
                            params={"learner_id": "stu-bad", "seed": seed}).text)
    r = c.post(f"/exam/{sess}/submit", data={"item_9999": "x"}, follow_redirects=False)
    assert r.status_code == 400, f"越界题号应 400，实得 {r.status_code}"
    r = c.post(f"/exam/{sess}/submit", data={"hacker": "x"}, follow_redirects=False)
    assert r.status_code == 400, f"非法字段名应 400，实得 {r.status_code}"
    # JSON 体形态违规 -> 400（缺 answers）
    r = c.post(f"/exam/{sess}/submit", json={"nope": 1}, follow_redirects=False)
    assert r.status_code == 400, f"JSON 缺 answers 应 400，实得 {r.status_code}"
    detail.append("越界题号/非法字段/JSON 形态 400")
    # 重复交卷 -> 409
    c.post(f"/exam/{sess}/submit", data={}, follow_redirects=False)
    r = c.post(f"/exam/{sess}/submit", data={}, follow_redirects=False)
    assert r.status_code == 409, f"重复交卷应 409，实得 {r.status_code}"
    detail.append("重复交卷 409")
    # 未交卷取报告 -> 409
    sess2 = session_of(c.get(f"/exam/{spec_id}/start",
                             params={"learner_id": "stu-noreport", "seed": seed}).text)
    r = c.get(f"/exam/{sess2}/report.html")
    assert r.status_code == 409, f"未交卷报告应 409，实得 {r.status_code}"
    detail.append("未交卷报告 409")
    return "；".join(detail)


def check_step_6_expired(spec_id, seed) -> str:
    """过期会话：ExamStore(ttl=0) —— 任何时刻取用都判 410。"""
    app, _, _ = build(spec_id, seed, store=ExamStore(ttl=0))
    c = TestClient(app)
    learner = "stu-expired"
    sess = session_of(c.get(f"/exam/{spec_id}/start",
                            params={"learner_id": learner, "seed": seed}).text)
    r = c.post(f"/exam/{sess}/submit", data={}, follow_redirects=False)
    assert r.status_code == 410, f"过期会话 submit 应 410，实得 {r.status_code}"
    r = c.get(f"/exam/{sess}/report.html")
    assert r.status_code == 410, f"过期会话 report 应 410，实得 {r.status_code}"
    return f"ttl=0 会话 {sess}：submit 410 / report 410"


def check_step_7_json_and_org(spec_id, seed) -> str:
    """JSON 提交同口径 + 机构分域落库（X-Org-Id 隔离）。"""
    app, _, _ = build(spec_id, seed)
    c = TestClient(app)
    learner = "stu-json"
    sheet = c.get(f"/exam/{spec_id}/start",
                  params={"learner_id": learner, "seed": seed},
                  headers={"X-Org-Id": "org-x"}).text
    sess = session_of(sheet)
    paper = _paper_for(app, spec_id, seed)
    answers = paper_answers(paper, bank_of(app))
    r = c.post(f"/exam/{sess}/submit",
               json={"answers": {str(k): v for k, v in answers.items()}},
               follow_redirects=False)
    assert r.status_code == 303, f"JSON submit 应 303，实得 {r.status_code}：{r.text[:200]}"
    # 画像落在 org-x 域，default 域查不到（与 /responses 的多租户契约一致）
    ok = c.get(f"/learners/{learner}/profile", headers={"X-Org-Id": "org-x"})
    assert ok.status_code == 200, f"org-x 域画像应 200，实得 {ok.status_code}"
    miss = c.get(f"/learners/{learner}/profile")
    assert miss.status_code == 404, f"default 域应看不到，实得 {miss.status_code}"
    orgs = c.get("/orgs").json()["orgs"]
    assert any(o["org_id"] == "org-x" for o in orgs), f"/orgs 未见 org-x：{orgs}"
    return f"JSON submit 303 | org-x 画像 200 / default 404，/orgs 可见 org-x"


# ---- 便捷访问：从 app 反查卷面与题库（与开卷同一装订路径） ----

def _paper_for(app, spec_id, seed) -> dict:
    catalog = load_spec_catalog(os.path.join(CURRICULUM, "curriculum", "paper_specs.json"))
    raw = catalog[spec_id]
    bank = load_stage_bank(CURRICULUM, raw["subject"], raw["stage"])[0]
    return generate_paper_by_spec(bank, raw, seed=seed, spec_id=spec_id)


def bank_of(app):
    catalog = load_spec_catalog(os.path.join(CURRICULUM, "curriculum", "paper_specs.json"))
    raw = catalog[_CURRENT["spec_id"]]
    return load_stage_bank(CURRICULUM, raw["subject"], raw["stage"])[0]


def bank_get(app, item_id):
    return bank_of(app).get(item_id)


_CURRENT = {"spec_id": DEFAULT_SPEC}


def main() -> int:
    ap = argparse.ArgumentParser(description="学生作答闭环门（TestClient 无浏览器全环）")
    ap.add_argument("--spec-id", default=DEFAULT_SPEC)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    _CURRENT["spec_id"] = args.spec_id

    app, raw, bank = build(args.spec_id, args.seed)
    n_obj = sum(1 for item in bank.items() if getattr(item, "item_type", "") in AUTO_ITEM_TYPES)
    print(f"学生作答闭环门 {args.spec_id}（seed={args.seed}，学科 {raw['subject']}，"
          f"题库 {len(list(bank.items()))} 题，其中客观题 {n_obj} 题）：")

    steps = [
        ("(1) 开卷 + 作答页结构", lambda: check_step_1_start(app, args.spec_id, args.seed, "stu-s1")),
        ("(2) 作答页红线/配平/自包含", lambda: check_step_2_redline(app, args.spec_id, args.seed)),
        ("(3) 全对作答 → 303 → 报告 → 落库", lambda: check_step_3_all_correct(app, args.spec_id, args.seed)),
        ("(4) 半错作答 → 得分/对错标记/薄弱点/建议", lambda: check_step_4_half_wrong(app, args.spec_id, args.seed)),
        ("(5) 错误契约 404/400/409", lambda: check_step_5_errors(app, args.spec_id, args.seed)),
        ("(6) 会话过期 410", lambda: check_step_6_expired(args.spec_id, args.seed)),
        ("(7) JSON 提交 + 机构分域", lambda: check_step_7_json_and_org(args.spec_id, args.seed)),
    ]
    passed, failed = 0, []
    for i, (label, fn) in enumerate(steps, 1):
        try:
            detail = fn()
            passed += 1
            print(f"  [{i}/{len(steps)}] {label.ljust(34, ' ')} PASS  {detail}")
        except AssertionError as e:
            failed.append(label)
            print(f"  [{i}/{len(steps)}] {label.ljust(34, ' ')} FAIL  {e}")
        except Exception as e:  # noqa: BLE001
            failed.append(label)
            print(f"  [{i}/{len(steps)}] {label.ljust(34, ' ')} FAIL  {type(e).__name__}: {e}")

    if failed:
        print(f"EXAM-LOOP-FAIL {passed}/{len(steps)}，失败环节：")
        for label in failed:
            print(f"  - {label}")
        return 1
    print(f"EXAM-LOOP-OK {passed}/{len(steps)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
