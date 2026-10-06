"""exam_report —— 个人作答报告页渲染（家长/学生可读的自包含 HTML）。

消费 xuexing.exam_loop 已算好的报告数据（逐题对错 + 知识点掌握 + 薄弱点 +
下一步建议），只做「数据 -> HTML」一件事：内联 CSS、无 JS、无外链，单文件即读。
与 xuexing.paper_render 的分工：paper_render 渲染**学生卷**（红线：绝不携带
answer/solution），本模块渲染**提交后的报告**（红线解除：正确答案与解析正是
报告要展示的内容）——两者红线相反，故分属两模块，绝不互相调用。

诊断与规划口径一律来自既有内核（diagnosis.diagnose / aggregate_to_clusters、
route.build_plan、recommend.recommend_for_profile），本模块不重算掌握度、不排序
薄弱点：它拿到什么就渲染什么。纯函数（无 IO、无随机、无时钟）。
"""
from __future__ import annotations

import html

__all__ = ["ReportRenderError", "render_report_html"]


class ReportRenderError(ValueError):
    """报告数据形态非法（fail-closed：不渲染半截报告）。"""


_CSS = """  * { box-sizing: border-box; }
  body {
    max-width: 900px; margin: 0 auto; padding: 18px 20px 40px;
    font-family: "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif;
    font-size: 15px; line-height: 1.7; color: #1c1c1c; background: #f7f8fa;
  }
  .report-head {
    background: #fff; border: 1px solid #dfe3e8; border-radius: 6px;
    padding: 16px 20px; margin-bottom: 16px;
  }
  .report-title { font-size: 20px; font-weight: 700; margin: 0 0 8px; }
  .report-meta { font-size: 13px; color: #555; }
  .report-meta span { margin: 0 10px 0 0; }
  .score-big { font-size: 30px; font-weight: 700; }
  .score-big .full { font-size: 15px; font-weight: 400; color: #666; }
  .card {
    background: #fff; border: 1px solid #dfe3e8; border-radius: 6px;
    padding: 14px 20px; margin-bottom: 16px;
  }
  .card h2 {
    font-size: 16px; margin: 0 0 10px; padding-bottom: 6px;
    border-bottom: 1px solid #eceff3;
  }
  table { width: 100%; border-collapse: collapse; font-size: 14px; }
  th, td { text-align: left; padding: 6px 8px; border-bottom: 1px solid #eef1f4;
           vertical-align: top; }
  th { color: #666; font-weight: 600; white-space: nowrap; }
  td.num { text-align: right; white-space: nowrap; }
  .verdict { font-weight: 700; white-space: nowrap; }
  .verdict.ok { color: #1a7f37; }
  .verdict.bad { color: #b42318; }
  .verdict.pending { color: #8a6d1f; }
  .stem { white-space: pre-wrap; }
  .answer-box {
    background: #f4f6f8; border-left: 3px solid #c3ccdb;
    padding: 4px 8px; margin: 4px 0; white-space: pre-wrap;
  }
  .kp-tag {
    display: inline-block; background: #eef3fb; color: #2f5d9e;
    border-radius: 3px; padding: 0 6px; margin: 2px 4px 2px 0;
    font-size: 12px;
  }
  .bar { background: #eceff3; border-radius: 3px; height: 8px; width: 90px;
         display: inline-block; vertical-align: middle; }
  .bar > i { display: block; height: 8px; border-radius: 3px; background: #4a86c8; }
  .bar.low > i { background: #d9822b; }
  .empty { color: #777; font-size: 14px; }
  .next { margin: 0; padding-left: 20px; }
  .next li { margin-bottom: 8px; }
  .why { color: #555; font-size: 13px; }
"""


def _esc(value) -> str:
    """动态文本 -> 转义后的 HTML 片段。非 str 先按 str() 收编再转义。"""
    return html.escape(value if isinstance(value, str) else str(value), quote=True)


def _pct(x) -> str:
    try:
        return f"{float(x) * 100:.0f}%"
    except (TypeError, ValueError):
        return "—"


def _bar(ratio, low: bool) -> str:
    width = max(0.0, min(1.0, float(ratio))) * 100.0
    return (f'<span class="bar{" low" if low else ""}">'
            f'<i style="width: {width:.0f}%"></i></span> {ratio * 100:.0f}%')


def _validate(report: dict) -> dict:
    if not isinstance(report, dict):
        raise ReportRenderError(f"report must be a dict, got {report!r}")
    for key in ("learner_id", "spec_id", "title"):
        if not isinstance(report.get(key), str) or not report[key]:
            raise ReportRenderError(f"report.{key} must be a non-blank str, got {report.get(key)!r}")
    for key in ("items", "kp_rows", "weak", "next_steps", "clusters"):
        if not isinstance(report.get(key), list):
            raise ReportRenderError(f"report.{key} must be a list, got {report.get(key)!r}")
    if not isinstance(report.get("score"), (int, float)) or isinstance(report.get("score"), bool):
        raise ReportRenderError(f"report.score must be a number, got {report.get('score')!r}")
    if not isinstance(report.get("total_points"), (int, float)) or isinstance(report.get("total_points"), bool):
        raise ReportRenderError(f"report.total_points must be a number, got {report.get('total_points')!r}")
    return report


def _render_items(report: dict) -> str:
    """逐题对错表：题号/分值/我的作答/正确答案/判定/涉及知识点。"""
    if not report["items"]:
        return '<p class="empty">本卷没有题目记录。</p>'
    rows = [
        "<table><tr><th>题号</th><th>分值</th><th>题目</th><th>我的作答</th>"
        "<th>正确答案</th><th>判定</th></tr>",
    ]
    for it in report["items"]:
        if it.get("correct") is True:
            verdict = '<span class="verdict ok">✓ 正确</span>'
        elif it.get("correct") is False:
            verdict = '<span class="verdict bad">✗ 错误</span>'
        else:
            # 主观题：本闭环不自动判分（不假装能判），如实标「待批改」而非
            # 计入对/错——凭字符串相等判解答题会造出假的错。
            verdict = '<span class="verdict pending">待批改</span>'
        given = it.get("learner_answer") or ""
        given_html = (f'<div class="answer-box">{_esc(given)}</div>' if given.strip()
                      else '<span class="empty">（未作答）</span>')
        right = it.get("expected") or ""
        right_html = f'<div class="answer-box">{_esc(right)}</div>' if right else '<span class="empty">—</span>'
        kp_tags = "".join(f'<span class="kp-tag">{_esc(name)}</span>'
                          for name in (it.get("kp_names") or []))
        rows.append(
            f'<tr><td class="num">{it.get("question_no")}</td>'
            f'<td class="num">{it.get("points")}</td>'
            f'<td><div class="stem">{_esc(it.get("stem", ""))}</div>{kp_tags}</td>'
            f'<td>{given_html}</td><td>{right_html}</td><td>{verdict}</td></tr>')
    rows.append("</table>")
    return "".join(rows)


def _render_kp_rows(report: dict) -> str:
    """本次涉及的知识点掌握度（只列 evidence>0 的，即本次真正测到的）。"""
    rows_in = [r for r in report["kp_rows"] if r.get("evidence")]
    if not rows_in:
        return '<p class="empty">本次作答没有落到任何图内知识点。</p>'
    out = [
        "<table><tr><th>知识点</th><th>所属板块</th><th>掌握度</th>"
        "<th>本次作答</th><th>累计证据</th></tr>",
    ]
    for r in sorted(rows_in, key=lambda x: (x.get("mastery", 0.0), x.get("kp_id", ""))):
        m = float(r.get("mastery", 0.0))
        out.append(
            f'<tr><td>{_esc(r.get("name") or r.get("kp_id"))}</td>'
            f'<td>{_esc(r.get("cluster") or "—")}</td>'
            f'<td>{_bar(m, low=m < 0.65)}</td>'
            f'<td class="num">{r.get("hit", 0)}/{r.get("tried", 0)}</td>'
            f'<td class="num">{r.get("evidence", 0)}</td></tr>')
    out.append("</table>")
    return "".join(out)


def _render_clusters(report: dict) -> str:
    clusters = [c for c in report["clusters"] if isinstance(c, dict)]
    if not clusters:
        return ""
    out = ["<p>" + "".join(
        f'<span class="kp-tag">{_esc(c.get("cluster"))} {_pct(c.get("mastery"))}</span>'
        for c in clusters) + "</p>"]
    return "".join(out)


def _render_weak(report: dict) -> str:
    weak = report["weak"]
    if not weak:
        return '<p class="empty">本次没有明显薄弱的知识点，保持住 👍</p>'
    out = ["<table><tr><th>知识点</th><th>板块</th><th>掌握度</th><th>薄弱原因</th></tr>"]
    for r in weak:
        out.append(
            f'<tr><td>{_esc(r.get("name") or r.get("kp_id"))}</td>'
            f'<td>{_esc(r.get("cluster") or "—")}</td>'
            f'<td>{_bar(float(r.get("mastery", 0.0)), low=True)}</td>'
            f'<td class="why">{_esc(r.get("why") or "掌握度低于目标线")}</td></tr>')
    out.append("</table>")
    return "".join(out)


def _render_next(report: dict) -> str:
    steps = report["next_steps"]
    if not steps:
        return '<p class="empty">当前没有需要优先补的知识点，先把本次错题弄懂即可。</p>'
    items = []
    for i, s in enumerate(steps, 1):
        rec = s.get("item_ids") or []
        rec_html = ("　练习题：" + "、".join(_esc(x) for x in rec[:5])) if rec else ""
        items.append(
            f'<li><b>{i}. {_esc(s.get("name") or s.get("kp_id"))}</b>'
            f'（掌握度 {_pct(s.get("mastery"))} → 目标 {_pct(s.get("target_mastery"))}）'
            f'<div class="why">建议策略：{_esc(s.get("strategy_name") or s.get("strategy_id") or "")}'
            f'{rec_html}</div></li>')
    return f'<ol class="next">{"".join(items)}</ol>'


def render_report_html(report: dict) -> str:
    """报告数据 dict -> 自包含 HTML 文档（UTF-8，无 JS/外链）。"""
    _validate(report)
    score = report["score"]
    total = report["total_points"]
    n_correct = sum(1 for it in report["items"] if it.get("correct") is True)
    n_wrong = sum(1 for it in report["items"] if it.get("correct") is False)
    n_pending = sum(1 for it in report["items"] if it.get("correct") is None)
    rate = (score / total) if total else 0.0
    pending = report.get("pending_points") or 0
    # 得分构成说明：主观题（解答题/实验题等）不在自动判分口径内，其分值既不计入
    # 得分也不算扣分——如实标出，否则「34 / 100」会被读成「扣了 66 分」。
    score_note = ("主观题的分值未计入得分，也未扣分" if pending else "全卷均为客观题")
    return "".join([
        "<!DOCTYPE html>\n",
        '<html lang="zh-CN">\n<head>\n<meta charset="utf-8">\n',
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n',
        f"<title>{_esc(report['title'])} · 作答报告</title>\n",
        f"<style>\n{_CSS}</style>\n</head>\n<body>\n",
        # 卷头：考生/卷型/得分
        '<div class="report-head">\n',
        f'  <h1 class="report-title">{_esc(report["title"])} · 作答报告</h1>\n',
        f'  <div class="report-meta">'
        f'<span>考生 <b>{_esc(report["learner_id"])}</b></span>'
        f'<span>卷型 {_esc(report["spec_id"])}</span>'
        f'<span>客观题答对 {n_correct}/{n_correct + n_wrong} 题</span>'
        f'<span>得分率 {_pct(rate)}</span></div>\n',
        f'  <div class="score-big">{score:g}<span class="full"> / {total:g} 分</span></div>\n',
        f'  <p class="why">本次共 {n_pending} 道主观题待人工批改，涉及 {pending:g} 分'
        f'（{score_note}）。</p>\n',
        "</div>\n",
        '<div class="card"><h2>一、逐题对错</h2>\n', _render_items(report), "\n</div>\n",
        '<div class="card"><h2>二、知识点掌握更新</h2>\n', _render_kp_rows(report), "\n",
        "  <p class=\"why\">板块总览：</p>\n", _render_clusters(report), "\n</div>\n",
        '<div class="card"><h2>三、薄弱知识点</h2>\n', _render_weak(report), "\n</div>\n",
        '<div class="card"><h2>四、下一步学习建议</h2>\n', _render_next(report), "\n</div>\n",
        '<div class="card"><p class="why">说明：掌握度由本仓诊断内核（知识点贝叶斯'
        '更新 + 先序一致性平滑）依据本次作答计算，薄弱点与学习顺序由学习路线内核'
        '按「影响×缺口」排序生成；同一份结论也可由 /learners/{id}/profile 与 '
        '/learners/{id}/plan 复核。</p></div>\n',
        "</body>\n</html>\n",
    ])
