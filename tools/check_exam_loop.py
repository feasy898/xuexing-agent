"""学生作答闭环门——/exam/* 三步全环无浏览器验收（无参运行，exit 0 = 门通过）。

为什么需要本工具：出卷（POST /papers/by-spec）、成品卷渲染（GET .../render.html）、
作答数据（POST /learners/{id}/responses）、画像（/profile）、路线（/plan）各自都有门，
但"学生开卷 → 作答 → 交卷 → 拿到自己的报告"这条链此前**没有任何一个可执行的验收**——
五个端点都通过，不等于串起来能跑通。本工具就是这条链的端到端门。

跑法与判定（全部经 TestClient 进程内直连 ASGI，零网络、不占端口、无浏览器）：

1. START   GET /exam/{spec_id}/start?learner_id=&seed= → 200 text/html；
   断言：会话头在位、题块数 == 卷题数、**可作答控件数 == 卷题数**（每题恰一组
   name=item_{no} 的 radio/checkbox/input/textarea）、learner_id 回显、卷面与
   同 (spec_id, seed) 的 POST /papers/by-spec 结构同源同题序、标签配平、
   红线（无 answer/solution 词根与标答/解析值——学生卷不泄题）。
2. SUBMIT  两份作答：**全对**与**半错**（都按题库真标答构造，标答只在本门内部
   用于造卷，不出现在产物里）。form 提交断言 303 + Location 指向报告页；JSON
   提交断言机器可读摘要。断言：得分 == 全对满分 / 半错按题数算、逐题对错与
   /grade 口径逐条一致（同一份 answers 送 POST /grade 复算）、落库后
   GET /learners/{id}/profile 与 /plan 立即反映本卷。
3. REPORT  GET /exam/{session_id}/report.html → 200；断言：得分回显、逐题对错
   标记（正确数==得分对题数）、**薄弱知识点**在页面上（半错卷必有）、掌握度
   更新表、下一步学习建议、标签配平。
4. 边界    未知卷型 404 / 未知会话 404 / 过期会话 404 / 跨 org 404 / 重复提交
   409 / 未提交看报告 409 / 缺 learner_id 400 / 非法 content-type 400。

门通过条件（exit 0）：上述 1-4 全部断言通过且零 UNEXPECTED。

用法：python tools/check_exam_loop.py [--spec-id spec_phy_hs_final] [--seed 42]
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

from xuexing import load_itembank, load_kpgraph, load_strategies  # noqa: E402
from xuexing.exam import ExamSessions  # noqa: E402
from xuexing.grading import grade_to_response  # noqa: E402
from xuexing.paper_by_spec import (  # noqa: E402
    DEFAULT_CURRICULUM_DIR,
    load_spec_catalog,
    load_stage_bank,
)
from xuexing.paper_render import (  # noqa: E402
    FORBIDDEN_TOKENS,
    check_html_tag_balance,
    format_points,
    redline_report,
)
from xuexing.server import create_app  # noqa: E402
from xuexing.types import Misconception  # noqa: E402

GRAPH_PATH = os.path.join(ROOT, "data", "knowledge", "math_grade7.json")
BANK_PATH = os.path.join(ROOT, "data", "items", "math_grade7_items.json")
STRATEGIES_PATH = os.path.join(ROOT, "data", "pedagogy", "strategies.json")
MISCONCEPTIONS_PATH = os.path.join(ROOT, "data", "misconceptions", "math_misconceptions.json")

_Q_BLOCK_RE = re.compile(r'<div class="question" id="q(\d+)">')
_CTRL_NAME_RE = re.compile(r'name="(item_\d+)"')


def _load_misconceptions():
    import json
    with open(MISCONCEPTIONS_PATH, encoding="utf-8") as f:
        return [Misconception(**mc) for mc in json.load(f)["misconceptions"]]


def build_client():
    """按 tests/conftest.py 同源方式注入 grade7 子库 + 真实卷型库起应用。

    会话表显式注入（TTL 2h）——过期态在边界检查里用「TTL=0 的独立应用」构造，
    不去改全局时钟。
    """
    catalog = load_spec_catalog(
        os.path.join(DEFAULT_CURRICULUM_DIR, "curriculum", "paper_specs.json"))
    app = create_app(
        load_itembank(BANK_PATH),
        load_kpgraph(GRAPH_PATH),
        load_strategies(STRATEGIES_PATH),
        _load_misconceptions(),
        spec_catalog=catalog,
        exam_sessions=ExamSessions(),
    )
    return TestClient(app, follow_redirects=False), catalog


def answer_key(paper, bank, wrong_from=None):
    """按题库真标答造一份 form 作答：控件名 item_{no}。

    wrong_from：题号 >= 该值的题一律写错（None = 全对卷，其余 = 半错卷）。
    选择题回传选项标签（"A"），与卷页 radio 的 value 同口径；填空/解答回传标答；
    错题统一回传 "__wrong__"——选项解析不到该 token、字面也不等，两条支都判错。
    """
    payload = {}
    for sec in paper["sections"]:
        for q in sec["questions"]:
            no = q["question_no"]
            item = bank.get(q["item_id"])
            wrong = wrong_from is not None and no >= wrong_from
            payload[f"item_{no}"] = "__wrong__" if wrong else item.answer
    return payload


def run_checks(spec_id: str, seed: int) -> list:
    """跑完整环，逐项返回 (阶段, 说明, 异常或 None)。"""
    results = []
    client, catalog = build_client()
    if spec_id not in catalog:
        results.append(("SETUP", f"未知卷型 {spec_id}", AssertionError("spec not in catalog")))
        return results
    spec = catalog[spec_id]
    stage_bank = load_stage_bank(DEFAULT_CURRICULUM_DIR, spec["subject"], spec["stage"])[0]

    def check(stage, desc, fn):
        try:
            detail = fn()
            results.append((stage, desc, None))
            print(f"  PASS  {stage:<7} {desc}  {detail or ''}")
        except AssertionError as e:
            results.append((stage, desc, e))
            print(f"  FAIL  {stage:<7} {desc}  {e}")
        except Exception as e:  # noqa: BLE001
            results.append((stage, desc, e))
            print(f"  FAIL  {stage:<7} {desc}  {type(e).__name__}: {e}")

    # ---------- 1. START ----------
    started = {}

    def _start():
        r = client.get(f"/exam/{spec_id}/start",
                       params={"learner_id": "stu-loop-1", "seed": seed})
        assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"
        assert r.headers["content-type"].startswith("text/html"), r.headers["content-type"]
        session = r.headers.get("X-Exam-Session")
        assert session, "缺 X-Exam-Session 响应头"
        doc = r.text
        started["doc"] = doc
        started["session"] = session
        # 与 POST /papers/by-spec 同 seed 同源同题序
        posted = client.post("/papers/by-spec", json={"spec_id": spec_id, "seed": seed}).json()
        n_q = posted["question_count"]
        flat = [q["item_id"] for s in posted["sections"] for q in s["questions"]]
        nos = [int(m) for m in _Q_BLOCK_RE.findall(doc)]
        assert nos == list(range(1, n_q + 1)), f"题块号非连续 1..{n_q}: {nos[:5]}"
        assert n_q == posted["question_count"], n_q
        # 可作答控件：每题恰一组 item_{no}（选择题一组内是多个 radio/checkbox）
        names = _CTRL_NAME_RE.findall(doc)
        assert len(set(names)) == n_q, f"控件组 {len(set(names))} != 题数 {n_q}"
        assert set(names) == {f"item_{i}" for i in range(1, n_q + 1)}, "控件名与题号不一一对应"
        assert len(names) >= n_q, f"控件总数 {len(names)} < 题数 {n_q}"
        # 选择题给 radio/checkbox，填空/解答给 input/textarea
        assert 'type="radio"' in doc or 'type="checkbox"' in doc, "选择题无 radio/checkbox"
        assert 'class="q-input" type="text"' in doc or "<textarea" in doc, "填空/解答无输入框"
        # learner 回显 + 表单 action 指向会话
        assert "stu-loop-1" in doc, "卷页未回显 learner_id"
        assert f'action="/exam/{session}/submit"' in doc, "form action 未指向本会话"
        # 合法性 + 红线（学生卷不泄题）—— 词根/值级扫描委托内核 redline_report
        # （与 tools/check_paper_render.py 同一实现：作答题页同样不得带作答依据）
        assert check_html_tag_balance(doc) == [], check_html_tag_balance(doc)[:3]
        violations = redline_report(posted, stage_bank, doc, "")
        assert not violations, f"学生卷红线击穿：{violations[:3]}"
        return f"题数={n_q} 控件组={n_q} session={session}"

    check("START", "开卷返回可作答卷页（题数/控件数/learner 回显/同源/红线）", _start)

    # ---------- 2. SUBMIT 全对 ----------
    submitted = {}

    def _submit_all_correct():
        session = started["session"]
        paper = client.post("/papers/by-spec", json={"spec_id": spec_id, "seed": seed}).json()
        total = paper["total_points"]
        payload = answer_key(paper, stage_bank, wrong_from=None)
        r = client.post(f"/exam/{session}/submit", data=payload)
        assert r.status_code == 303, f"{r.status_code} {r.text[:200]}"
        assert r.headers["location"] == f"/exam/{session}/report.html", r.headers.get("location")
        rep = client.get(f"/exam/{session}/report.html")
        assert rep.status_code == 200, rep.status_code
        assert f'<strong>{format_points(total)}</strong>' in rep.text, \
            f"全对卷得分不是满分 {format_points(total)}：{rep.text[:200]}"
        assert f"答对 {paper['question_count']} 题" in rep.text, "全对卷答对题数 != 全卷题数"
        assert "✘ 错误" not in rep.text, "全对卷报告页出现错误标记"
        # 逐题判定与 /grade 口径逐条一致（同一 grading 内核）
        for sec in paper["sections"]:
            for q in sec["questions"]:
                given = payload[f"item_{q['question_no']}"]
                expect = grade_to_response(stage_bank.get(q["item_id"]), given).correct
                assert expect is True, f"第 {q['question_no']} 题 grading 判错（造卷口径有偏）"
        submitted["all"] = session
        return f"303 -> {r.headers['location']} 满分={format_points(total)}"

    check("SUBMIT", "全对卷：form 提交 303 跳报告页、得分满分", _submit_all_correct)

    def _submit_half_wrong():
        session = client.get(f"/exam/{spec_id}/start",
                             params={"learner_id": "stu-loop-2", "seed": seed}
                             ).headers["X-Exam-Session"]
        paper = client.post("/papers/by-spec", json={"spec_id": spec_id, "seed": seed}).json()
        n_q = paper["question_count"]
        wrong_from = n_q // 2 + 1  # 后半段题号故意写错
        payload = answer_key(paper, stage_bank, wrong_from=wrong_from)
        r = client.post(f"/exam/{session}/submit", json=payload)  # JSON 形态
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
        out = r.json()
        n_correct = wrong_from - 1
        assert out["correct_count"] == n_correct, \
            f"判对 {out['correct_count']} 题 != 期望 {n_correct}"
        assert out["wrong_count"] == n_q - n_correct, out["wrong_count"]
        assert out["report_url"] == f"/exam/{session}/report.html", out["report_url"]
        # 落库：/profile 与 /plan 立即反映本卷
        prof = client.get("/learners/stu-loop-2/profile")
        assert prof.status_code == 200, prof.status_code
        assert prof.json()["learner_id"] == "stu-loop-2", prof.json()
        plan = client.get("/learners/stu-loop-2/plan")
        assert plan.status_code == 200, plan.status_code
        assert "steps" in plan.json(), plan.json().keys()
        # 半错卷的得分 = 满分 - 错题分值之和
        wrong_pts = sum(q["points"] for s in paper["sections"] for q in s["questions"]
                        if q["question_no"] >= wrong_from)
        expect_score = paper["total_points"] - wrong_pts
        assert abs(out["score"] - expect_score) < 1e-9, \
            f"得分 {out['score']} != 期望 {expect_score}"
        submitted["half"] = session
        submitted["half_weak"] = out["weak_points"]
        return (f"JSON 判对 {out['correct_count']}/{n_q} 得分 {out['score']:g}/"
                f"{out['total_points']:g} 薄弱 kp×{len(out['weak_points'])}")

    check("SUBMIT", "半错卷：JSON 提交回摘要、逐题对数、落库 /profile+/plan", _submit_half_wrong)

    # ---------- 3. REPORT ----------
    def _report():
        session = submitted["half"]
        rep = client.get(f"/exam/{session}/report.html")
        assert rep.status_code == 200, rep.status_code
        assert rep.headers["content-type"].startswith("text/html"), rep.headers["content-type"]
        doc = rep.text
        assert "作答报告" in doc, "缺报告页标题"
        assert "一、逐题对错" in doc and "二、知识点掌握更新" in doc, "缺报告分节"
        assert "三、薄弱知识点" in doc and "四、下一步学习建议" in doc, "缺薄弱点/建议分节"
        assert doc.count("✔ 正确") == submitted["correct_n"], doc.count("✔ 正确")
        assert doc.count("✘ 错误") == submitted["wrong_n"], doc.count("✘ 错误")
        assert check_html_tag_balance(doc) == [], check_html_tag_balance(doc)[:3]
        return f"对错标记 {doc.count('✔ 正确')}+{doc.count('✘ 错误')} 标签配平 OK"

    def _report_weak():
        session = submitted["half"]
        doc = client.get(f"/exam/{session}/report.html").text
        weak = submitted["half_weak"]
        assert "三、薄弱知识点" in doc, "缺薄弱点分节"
        for kp_id in weak[:5]:
            assert kp_id in doc, f"薄弱知识点 {kp_id} 不在报告页"
        assert "掌握度" in doc, "缺掌握度数值"
        assert "策略" in doc, "缺学习建议策略"
        return f"薄弱知识点 ×{len(weak)} 均在报告页"

    def _report_all_correct_weak():
        doc = client.get(f"/exam/{submitted['all']}/report.html").text
        # 全对卷允许「无新增薄弱点」——但必须如实说明，不留空节
        assert "暂无新增薄弱点" in doc or "三、薄弱知识点" in doc, "薄弱点节缺失"
        return "全对卷薄弱点节如实说明"

    # 记录两份卷的题数分布，供报告页逐题标记数校验
    def _prep_counts():
        paper = client.post("/papers/by-spec", json={"spec_id": spec_id, "seed": seed}).json()
        n_q = paper["question_count"]
        wrong_from = n_q // 2 + 1
        submitted["correct_n"] = wrong_from - 1
        submitted["wrong_n"] = n_q - (wrong_from - 1)
        return f"n_q={n_q} 对 {submitted['correct_n']} 错 {submitted['wrong_n']}"

    check("SETUP", "记录两份卷的题数分布（供报告页逐题标记校验）", _prep_counts)
    check("REPORT", "半错卷报告页含逐题对错标记、掌握更新、建议", _report)
    check("REPORT", "半错卷报告页薄弱知识点在页面上", _report_weak)
    check("REPORT", "全对卷报告页薄弱点节如实说明", _report_all_correct_weak)

    # ---------- 4. 边界 ----------
    def _unknown_spec_404():
        r = client.get("/exam/no_such_spec/start", params={"learner_id": "x"})
        assert r.status_code == 404, r.status_code
        return "404"

    def _learner_required_400():
        r = client.get(f"/exam/{spec_id}/start", params={"learner_id": "  "})
        assert r.status_code == 400, r.status_code
        return "400"

    def _unknown_session_404():
        r = client.get("/exam/exam-nope/report.html")
        assert r.status_code == 404, r.status_code
        r = client.post("/exam/exam-nope/submit", data={})
        assert r.status_code == 404, r.status_code
        return "report/submit 均 404"

    def _double_submit_409():
        r = client.post(f"/exam/{submitted['all']}/submit", data={})
        assert r.status_code == 409, r.status_code
        return "409"

    def _not_submitted_report_409():
        session = client.get(f"/exam/{spec_id}/start",
                             params={"learner_id": "stu-loop-3", "seed": seed}
                             ).headers["X-Exam-Session"]
        r = client.get(f"/exam/{session}/report.html")
        assert r.status_code == 409, r.status_code
        return "409"

    def _cross_org_404():
        session = client.get(f"/exam/{spec_id}/start",
                             params={"learner_id": "stu-loop-4", "seed": seed},
                             headers={"X-Org-Id": "org-a"}).headers["X-Exam-Session"]
        r = client.get(f"/exam/{session}/report.html", headers={"X-Org-Id": "org-b"})
        assert r.status_code == 404, r.status_code
        return "org-b 取 org-a 会话 404"

    def _expired_session_404():
        # TTL=0 的独立应用：起卷后立刻过期（过期与不存在同 404）
        exp_client, _ = build_client_with_ttl(0.0)
        session = exp_client.get(f"/exam/{spec_id}/start",
                                 params={"learner_id": "stu-loop-5", "seed": seed}
                                 ).headers["X-Exam-Session"]
        r = exp_client.get(f"/exam/{session}/report.html")
        assert r.status_code == 404, r.status_code
        r = exp_client.post(f"/exam/{session}/submit", data={})
        assert r.status_code == 404, r.status_code
        return "report/submit 均 404"

    def _bad_content_type_400():
        session = client.get(f"/exam/{spec_id}/start",
                             params={"learner_id": "stu-loop-6", "seed": seed}
                             ).headers["X-Exam-Session"]
        r = client.post(f"/exam/{session}/submit", content=b"x",
                        headers={"content-type": "application/xml"})
        assert r.status_code == 400, r.status_code
        return "400"

    check("BOUND", "未知卷型 404", _unknown_spec_404)
    check("BOUND", "learner_id 空白 400", _learner_required_400)
    check("BOUND", "未知会话 report/submit 404", _unknown_session_404)
    check("BOUND", "重复提交 409", _double_submit_409)
    check("BOUND", "未提交先看报告 409", _not_submitted_report_409)
    check("BOUND", "跨 org 取会话 404", _cross_org_404)
    check("BOUND", "过期会话 report/submit 404", _expired_session_404)
    check("BOUND", "非法 content-type 400", _bad_content_type_400)
    return results


def build_client_with_ttl(ttl):
    catalog = load_spec_catalog(
        os.path.join(DEFAULT_CURRICULUM_DIR, "curriculum", "paper_specs.json"))
    app = create_app(
        load_itembank(BANK_PATH),
        load_kpgraph(GRAPH_PATH),
        load_strategies(STRATEGIES_PATH),
        _load_misconceptions(),
        spec_catalog=catalog,
        exam_sessions=ExamSessions(ttl_seconds=ttl),
    )
    return TestClient(app, follow_redirects=False), catalog


def main() -> int:
    ap = argparse.ArgumentParser(description="学生作答闭环门（/exam/* 三步全环）")
    ap.add_argument("--spec-id", default="spec_phy_hs_final")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    print(f"学生作答闭环门：{args.spec_id}（seed={args.seed}）"
          f"—— TestClient 进程内直连 ASGI，零网络不占端口无浏览器")
    results = run_checks(args.spec_id, args.seed)
    failed = [(stage, desc, e) for stage, desc, e in results if e is not None]
    print("\n" + f"共 {len(results)} 项检查，通过 {len(results) - len(failed)}，"
                 f"失败 {len(failed)}")
    if failed:
        print("\n== UNEXPECTED（判门失败） ==")
        for stage, desc, e in failed:
            print(f"  FAIL  {stage:<7} {desc}  {e}")
        print("EXAM-LOOP-FAIL（门未通过）")
        return 1
    print("EXAM-LOOP-OK（起卷/提交/报告/边界全环通过）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
