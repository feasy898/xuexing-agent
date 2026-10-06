"""exam —— 学生作答闭环内核（会话 / 提交判分 / 个人报告页渲染）。

这是 server.py 里 ``/exam/*`` 三个端点的实现层：起卷发卷（``GET
/exam/{spec_id}/start``）、提交判分（``POST /exam/{session_id}/submit``）、
报告页（``GET /exam/{session_id}/report.html``）。

**本模块不含任何平行实现**——四件事全部转调仓内既有内核：

============================  ==========================================
环的一步                        复用的既有内核
============================  ==========================================
起卷（选题装订）                ``paper_by_spec.generate_paper_by_spec``
卷页渲染（HTML 控件）            ``paper_render.render_exam_html``
逐题判分                        ``grading.grade_to_response``（= POST /grade 口径）
知识点掌握 / 聚类                ``diagnosis.diagnose`` / ``aggregate_to_clusters``
下一步学习路线                  ``route.build_plan`` + ``recommend.attach_recommendations``
会话归属                        ``multitenant.resolve_org``（X-Org-Id 分域）
============================  ==========================================

口径诚实性（与既有端点逐条对齐，不另立标准）：

- 判分走 ``grade_to_response``，与 ``POST /grade`` 完全同一函数；**解答题
  （item_type=solve）同样按该内核的 fill 字面/数值等值支判**——本环不含教师
  批改通道，报告页据此措辞，不谎称过程分。
- 落库走与 ``POST /learners/{learner_id}/responses`` 相同的序列：``entry
  ["responses"]`` 追加本次逐题作答、``entry["profile"]`` 由 **diagnose 本次
  作答序列** 覆盖。因此 ``GET /learners/{id}/profile`` 与 ``/plan`` 在交卷后
  立刻反映本卷（画像是"最近一次提交"的诊断，与既有端点同语义，不做跨次累积）。
- 报告里的"掌握更新"给出 before→after：before 取自 store 中被覆盖掉的旧画像
  （无旧画像则 null，页面显示"首次诊断"），after 是本次 diagnose 结果。

会话生命周期：进程内 ``ExamSessions``（无持久化——最小环，重启即失效，由
``/exam/{session}/report.html`` 的 404 如实暴露）。会话按 (X-Org-Id 归并后的
org, session_id) 归属，跨 org 取用一律 404（与多租户口径一致）。超过
``ttl_seconds`` 未提交即过期（同样 404），由 create_app 注入的时钟判定以便
测试确定性地构造过期态。
"""
from __future__ import annotations

import html
import json
import time
from dataclasses import dataclass
from datetime import date
from urllib.parse import parse_qsl

from xuexing.diagnosis import aggregate_to_clusters, diagnose
from xuexing.grading import grade_to_response
from xuexing.multitenant import resolve_org
from xuexing.paper_render import format_points, human_paper_title
from xuexing.recommend import attach_recommendations
from xuexing.route import build_plan
from xuexing.types import Response

__all__ = [
    "ExamError",
    "SessionNotFound",
    "ExamSession",
    "ExamSessions",
    "MASTERY_THRESHOLD",
    "parse_submission_body",
    "grade_submission",
    "build_report",
    "render_report_html",
]

# 薄弱判定阈值：与 route.build_plan / recommend 的默认 mastery_threshold 同值
# （0.65），此处只用于报告页的"薄弱点"展示，不改变任何内核行为。
MASTERY_THRESHOLD = 0.65

# 报告页逐题明细上限（页面可读性）：超出部分如实打印"另有 N 题"。
MAX_REPORT_ITEMS = 60
# 报告页学习建议展示上限：计划本身全量生成（build_plan 不截断），只截展示。
MAX_PLAN_STEPS = 8
# 知识点群展示上限（本卷未涉及的群按掌握度升序补位到此数为止）。
MAX_CLUSTER_SHOW = 6


class ExamError(ValueError):
    """作答环领域校验失败（题不在库/题目侧非法/参数错），映射 HTTP 400。"""


class SessionNotFound(ExamError):
    """会话不存在、已过期或不属于本 org——一律 404（不泄露存在性差异）。"""


@dataclass
class ExamSession:
    """一次开卷的会话快照。paper 是**已装订好**的卷面结构（起卷时冻结），提交
    判分与报告页都只读它——同一个 session 的卷与渲染永远同源，不会二次组卷。"""

    session_id: str
    org_id: str
    learner_id: str
    spec_id: str
    seed: int
    difficulty_target: float
    paper: dict
    status: str = "open"          # open -> submitted（重复提交 409）
    created_at: float = 0.0
    report: dict | None = None
    subject: str = ""
    stage: str = ""


class ExamSessions:
    """进程内会话表 {session_id: ExamSession}（无 IO、无持久化）。

    ``clock``/``ttl_seconds`` 均可注入：TTL 以 clock() 的单调秒计，过期判定
    ``now - created_at > ttl_seconds``（默认 2 小时）。过期与不存在同抛
    SessionNotFound——调用方一律 404，外部观察不到"曾经存在过"。
    """

    def __init__(self, ttl_seconds: float = 7200.0, clock=time.monotonic):
        self._sessions: dict[str, ExamSession] = {}
        self._ttl = float(ttl_seconds)
        self._clock = clock

    def create(self, org_id: str, session: ExamSession) -> ExamSession:
        session.created_at = self._clock()
        session.org_id = resolve_org(org_id)
        self._sessions[session.session_id] = session
        return session

    def get(self, session_id: str, org_id: str | None) -> ExamSession:
        org = resolve_org(org_id)
        session = self._sessions.get(session_id)
        if session is None or session.org_id != org:
            raise SessionNotFound(f"exam session not found: {session_id}")
        if self._clock() - session.created_at > self._ttl:
            # 过期即从表中摘除：后续再取仍是同一 404（不复活、不重放）
            self._sessions.pop(session_id, None)
            raise SessionNotFound(f"exam session expired: {session_id}")
        return session

    def mark_submitted(self, session: ExamSession, report: dict) -> None:
        session.status = "submitted"
        session.report = report

    def count(self) -> int:
        return len(self._sessions)


def _question_rows(paper: dict) -> list:
    """卷面结构 -> [(question_no, item_id, points)]（全卷题序，与渲染一致）。"""
    rows = []
    for sec in paper["sections"]:
        for q in sec["questions"]:
            rows.append((q["question_no"], q["item_id"], q["points"]))
    return rows


def parse_submission_body(body: bytes, content_type: str) -> tuple[dict, str]:
    """提交体 -> ({控件名: [值, ...]}, mode)，mode ∈ {"form", "json"}。

    两种形态都收：浏览器 ``<form>`` 发的 ``application/x-www-form-urlencoded``
    与机器客户端的 ``application/json``（``{"item_1": "A"}`` 或
    ``{"answers": {...}}``）。

    为什么自己解析 urlencoded 而不用 ``Request.form()``：starlette 的 form 解析
    依赖可选包 ``python-multipart``（即便纯 urlencoded 也先 assert 它在位），
    而本仓零新依赖是硬约束，故用标准库 ``parse_qsl``——多值同名键（多选
    checkbox）在返回的 dict 里天然聚成 list，与 checkbox 语义一一对应。
    形态不受支持（非空体却不是这两种）抛 ExamError -> 400。
    """
    ctype = (content_type or "").split(";", 1)[0].strip().lower()
    if not body:
        return {}, "form"  # 空提交 = 全卷未作答（交卷仍成立，逐题判错）
    if ctype == "application/json" or (not ctype and body[:1] in (b"{", b"[")):
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            raise ExamError(f"invalid JSON body: {e}")
        if not isinstance(payload, dict):
            raise ExamError("JSON body must be an object of item_no -> answer")
        answers = payload.get("answers", payload)
        if not isinstance(answers, dict):
            raise ExamError("JSON 'answers' must be an object of item_no -> answer")
        raw = {}
        for key, value in answers.items():
            name = str(key)
            if not name.startswith("item_"):
                name = f"item_{name.lstrip('#')}"
            if isinstance(value, (list, tuple)):
                raw[name] = list(value)
            elif value is None:
                raw[name] = []
            elif isinstance(value, (str, int, float)) and not isinstance(value, bool):
                raw[name] = [str(value)]  # 数字作答按其十进制字面判（grading 侧再归一）
            else:
                raise ExamError(
                    f"answer for {name} must be a string, number or list, "
                    f"got {type(value).__name__}")
        return raw, "json"
    if ctype in ("application/x-www-form-urlencoded", ""):
        raw: dict = {}
        for key, value in parse_qsl(body.decode("utf-8", "replace"),
                                    keep_blank_values=True):
            raw.setdefault(key, []).append(value)
        return raw, "form"
    raise ExamError(f"unsupported content type for submit: {ctype!r}")


def _raw_to_str(values) -> str | None:
    """控件原始值（str 或多值 list）-> 提交给判分内核的作答串。

    多选 checkbox 同名多值按 "," 连接（grading._MULTI_SEP_RE 的分隔符族含逗号，
    故与内核的多选拆分口径一致）；全空（未作答）-> None，由内核按"未作答"判错。
    """
    if values is None:
        return None
    if isinstance(values, str):
        parts = [values]
    elif isinstance(values, (list, tuple)):
        parts = [v for v in values if isinstance(v, str)]
    else:
        raise ExamError(f"answer value must be str or list of str, got {type(values).__name__}")
    parts = [p for p in parts if p.strip() != ""]
    return ",".join(parts) if parts else None


def grade_submission(session: ExamSession, paper: dict, bank,
                     raw_answers: dict) -> list[Response]:
    """提交原始作答 -> 逐题 Response 列表（判分全权交给 grading 内核）。

    题序 = 卷面结构序（与卷页控件一一对应）；题不在库按 ExamError 报 400
    （fail-closed：宁可不判，也不拿别的题顶替）。题号在 raw_answers 中缺失
    等价"未作答"，仍产生一条 Response（correct=False），保证报告逐题齐全。
    """
    responses = []
    for no, item_id, _points in _question_rows(paper):
        item = bank.get(item_id)
        if item is None:
            raise ExamError(f"question {no}: item not in bank: {item_id}")
        answer = _raw_to_str(raw_answers.get(f"item_{no}"))
        try:
            responses.append(grade_to_response(item, answer))
        except ValueError as e:  # GradingError：题目侧非法（答案匹配不到选项等）
            raise ExamError(f"question {no}: {e}")
    return responses


def _kp_name(graph, kp_id: str) -> str:
    kp = graph.get(kp_id)
    return kp.name if kp is not None else kp_id


def build_report(session: ExamSession, paper: dict, bank, graph, strategies,
                 misconceptions, responses: list[Response], raw_answers: dict,
                 prior_profile=None, today: date | None = None) -> dict:
    """判分结果 -> 报告页数据模型（纯 dict，渲染层只做展示）。

    画像 = ``diagnose(responses, bank, graph, learner_id)``（本卷作答序列），
    聚类 = ``aggregate_to_clusters``；学习路线 = ``build_plan`` +
    ``attach_recommendations``（与 GET /learners/{id}/plan、POST /recommend
    attach=True 同一对函数）。build_plan 抛错（先序死锁等）不吞：把错误如实
    记进 plan_error 由页面显示，交卷本身仍然成功。
    """
    today = today or date.today()
    rows = _question_rows(paper)
    items = []
    earned = 0.0
    correct_count = 0
    for (no, item_id, points), resp in zip(rows, responses):
        item = bank.get(item_id)
        if resp.correct:
            correct_count += 1
            earned += float(points)
        items.append({
            "no": no,
            "item_id": item_id,
            "item_type": getattr(item, "item_type", ""),
            "stem": getattr(item, "stem", "").strip(),
            "options": [str(o) for o in (getattr(item, "options", None) or [])],
            "learner_answer": resp.learner_answer,
            "answer": getattr(item, "answer", ""),
            "solution": str(getattr(item, "solution", "") or ""),
            "points": float(points),
            "earned": float(points) if resp.correct else 0.0,
            "correct": bool(resp.correct),
            "kp_ids": list(getattr(item, "kps", []) or []),
        })

    total = float(paper["total_points"])
    profile = diagnose(responses, bank, graph, learner_id=session.learner_id)
    all_clusters = aggregate_to_clusters(profile, graph)

    touched = sorted({kp for it in items for kp in it["kp_ids"]})
    updates = []
    for kp_id in touched:
        after = profile.mastery.get(kp_id)
        if after is None:
            continue  # 图外知识点：diagnose 已跳过，报告不虚构数值
        before = None
        if prior_profile is not None:
            before = prior_profile.mastery.get(kp_id)
        updates.append({
            "kp_id": kp_id,
            "kp_name": _kp_name(graph, kp_id),
            "before": before,
            "after": after,
            "delta": None if before is None else round(after - before, 6),
            "evidence": profile.evidence.get(kp_id, 0),
            "confidence": round(profile.confidence(kp_id), 4),
        })
    updates.sort(key=lambda u: (u["after"], u["kp_id"]))

    weak = [u for u in updates if u["after"] < MASTERY_THRESHOLD]

    # 知识点群平均：整卷子图谱的聚类全量给出（家长要看全景），但报告页只展示
    # 本卷真正涉及的群 + 最弱的若干群——学科级图谱动辄几十个群，全列是噪声。
    # 口径仍是 aggregate_to_clusters 的返回值，此处只做展示层的挑选与排序。
    touched_clusters = sorted({
        graph.get(u["kp_id"]).cluster for u in updates
        if graph.get(u["kp_id"]) is not None})
    rest = {k: v for k, v in all_clusters.items() if k not in set(touched_clusters)}
    clusters_shown = {k: all_clusters[k] for k in touched_clusters if k in all_clusters}
    for k, _ in sorted(rest.items(), key=lambda kv: (kv[1], kv[0]))[:MAX_CLUSTER_SHOW]:
        clusters_shown[k] = all_clusters[k]
    clusters = clusters_shown

    steps, plan_error, reviews = [], "", []
    try:
        plan = build_plan(profile, bank, graph, strategies, today)
        attached = attach_recommendations(plan, bank, misconceptions)
        steps = [{
            "kp_id": s.kp_id,
            "kp_name": _kp_name(graph, s.kp_id),
            "strategy_id": s.strategy_id,
            "rationale": s.rationale,
            "target_mastery": s.target_mastery,
            "recommended_item_ids": list(s.recommended_item_ids),
        } for s in attached.steps]
        reviews = [{"kp_id": r.kp_id, "due": r.due, "interval_days": r.interval_days,
                    "ease": r.ease} for r in attached.reviews]
    except ValueError as e:  # RouteError / RecommendError：如实记录，不伪造建议
        plan_error = f"{type(e).__name__}: {e}"

    shown_steps = [s for s in steps if s["kp_id"] in {u["kp_id"] for u in updates}]
    if not shown_steps:
        shown_steps = steps[:MAX_PLAN_STEPS]
    shown_steps = shown_steps[:MAX_PLAN_STEPS]

    return {
        "session_id": session.session_id,
        "learner_id": session.learner_id,
        "spec_id": paper.get("spec_id", session.spec_id),
        "title": human_paper_title(paper),
        "profile": profile,
        "total_points": total,
        "earned_points": earned,
        "score_rate": round(earned / total, 6) if total > 0 else 0.0,
        "question_count": paper["question_count"],
        "correct_count": correct_count,
        "wrong_count": paper["question_count"] - correct_count,
        "items": items,
        "shown_item_count": min(len(items), MAX_REPORT_ITEMS),
        "mastery_updates": updates,
        "weak_points": weak,
        "clusters": clusters,
        "cluster_total": len(all_clusters),
        "cluster_hidden": len(all_clusters) - len(clusters),
        "plan_steps": steps,
        "plan_shown": shown_steps,
        "plan_error": plan_error,
        "reviews": reviews,
        "updated_at": profile.updated_at,
    }


# ---------------------------------------------------------------- 报告页渲染

_REPORT_CSS = """  * { box-sizing: border-box; }
  body {
    max-width: 900px; margin: 0 auto; padding: 18px 16px 40px;
    font-family: "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif;
    font-size: 14px; line-height: 1.75; color: #1a1a1a; background: #fafafa;
  }
  h1 { font-size: 20px; margin: 0 0 4px; }
  h2 { font-size: 16px; margin: 22px 0 8px; padding-bottom: 4px;
       border-bottom: 2px solid #d8d8d8; }
  .meta { color: #555; font-size: 13px; }
  .score { margin: 12px 0; padding: 10px 14px; background: #fff;
           border: 1px solid #ddd; border-radius: 6px; font-size: 15px; }
  .score strong { font-size: 22px; }
  table { width: 100%; border-collapse: collapse; background: #fff; }
  th, td { border: 1px solid #ddd; padding: 6px 8px; text-align: left;
           vertical-align: top; font-size: 13px; }
  th { background: #f0f2f5; }
  .ok { color: #137333; font-weight: 700; }
  .bad { color: #b3261e; font-weight: 700; }
  .muted { color: #777; }
  .q-stem { white-space: pre-wrap; }
  .q-ans { white-space: pre-wrap; }
  ul { margin: 6px 0; padding-left: 20px; }
  .foot { margin-top: 24px; font-size: 12px; color: #777; }
"""


def _esc(value) -> str:
    return html.escape(value if isinstance(value, str) else str(value), quote=True)


def _mark(correct: bool) -> str:
    return ('<span class="ok">✔ 正确</span>' if correct
            else '<span class="bad">✘ 错误</span>')


def _pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def render_report_html(report: dict) -> str:
    """报告页数据模型 -> 自包含 HTML（内联 CSS、无 JavaScript、无外链）。

    四块内容按家长可读顺序排：本次成绩 → 逐题对错（含正确答案与解析，便于
    讲题）→ 知识点掌握更新与薄弱点 → 下一步学习建议（来自 build_plan 的步骤、
    策略依据与推荐练习题）。所有动态文本经 html.escape 转义。
    """
    total_s = format_points(report["total_points"])
    earned_s = format_points(report["earned_points"])
    parts = [
        "<!DOCTYPE html>\n",
        '<html lang="zh-CN">\n<head>\n<meta charset="utf-8">\n',
        f'<title>{_esc(report["title"])} · 作答报告</title>\n',
        f"<!-- 个人作答报告：会话 {_esc(report['session_id'])}，"
        f"卷型 {_esc(report['spec_id'])}。判分与画像口径同 POST /grade、"
        "POST /learners/{id}/responses。 -->\n",
        f"<style>\n{_REPORT_CSS}</style>\n</head>\n<body>\n",
        f'<h1>{_esc(report["title"])} · 作答报告</h1>\n',
        f'<div class="meta">考生 <strong>{_esc(report["learner_id"])}</strong>'
        f' · 卷型 {_esc(report["spec_id"])}'
        f' · 作答编号 {_esc(report["session_id"])}'
        f' · 诊断时间 {_esc(report["updated_at"])}</div>\n',
        '<div class="score">得分 <strong>'
        f'{_esc(earned_s)}</strong> / {_esc(total_s)} 分'
        f'（得分率 {_esc(_pct(report["score_rate"]))}）'
        f' · 共 {_esc(report["question_count"])} 题'
        f' · 答对 {_esc(report["correct_count"])} 题'
        f' · 答错 {_esc(report["wrong_count"])} 题</div>\n',
    ]

    # ---- 逐题对错 ----
    parts.append("<h2>一、逐题对错</h2>\n")
    parts.append('<table><tr><th>题号</th><th>题目</th><th>你的作答</th>'
                 "<th>正确答案</th><th>判定</th><th>得分</th></tr>\n")
    for it in report["items"][:MAX_REPORT_ITEMS]:
        given = it["learner_answer"] or "（未作答）"
        parts.append(
            f'<tr><td>{_esc(it["no"])}</td>'
            f'<td class="q-stem">{_esc(it["stem"])}</td>'
            f'<td class="q-ans">{_esc(given)}</td>'
            f'<td class="q-ans">{_esc(it["answer"] or "—")}</td>'
            f'<td>{_mark(it["correct"])}</td>'
            f'<td>{_esc(format_points(it["earned"]))} / {_esc(format_points(it["points"]))}</td></tr>\n')
    parts.append("</table>\n")
    hidden = report["question_count"] - report["shown_item_count"]
    if hidden > 0:
        parts.append(f'<p class="muted">另有 {hidden} 题未在页面逐题展开'
                     "（总题数与得分已按全卷统计）。</p>\n")
    solutions = [it for it in report["items"] if it["solution"]]
    if solutions:
        parts.append("<h3>解析（供讲题参考）</h3>\n<ul>\n")
        for it in solutions[:MAX_REPORT_ITEMS]:
            parts.append(f'<li>第 {_esc(it["no"])} 题：{_esc(it["solution"])}</li>\n')
        parts.append("</ul>\n")

    # ---- 知识点掌握更新 ----
    parts.append("<h2>二、知识点掌握更新</h2>\n")
    if not report["mastery_updates"]:
        parts.append('<p class="muted">本卷题目未落在知识点图谱内，暂无掌握度更新。</p>\n')
    else:
        parts.append('<table><tr><th>知识点</th><th>诊断前</th><th>诊断后</th>'
                     "<th>变化</th><th>本题证据</th><th>置信度</th></tr>\n")
        for u in report["mastery_updates"]:
            before = "首次诊断" if u["before"] is None else f'{u["before"]:.2f}'
            delta = "—" if u["delta"] is None else f'{u["delta"]:+.2f}'
            parts.append(
                f'<tr><td>{_esc(u["kp_name"])}（{_esc(u["kp_id"])}）</td>'
                f'<td>{_esc(before)}</td><td>{u["after"]:.2f}</td>'
                f'<td>{_esc(delta)}</td><td>{_esc(u["evidence"])}</td>'
                f'<td>{u["confidence"]:.2f}</td></tr>\n')
        parts.append("</table>\n")
    if report["clusters"]:
        parts.append("<p>知识点群平均掌握度：")
        parts.append("；".join(
            f'{_esc(k)} {v:.2f}' for k, v in report["clusters"].items()))
        parts.append("。")
        if report.get("cluster_hidden"):
            parts.append(f'（本卷未涉及的群按掌握度升序展示最弱 '
                         f'{MAX_CLUSTER_SHOW} 个，全图共 {report["cluster_total"]} 个群。）')
        parts.append("</p>\n")

    # ---- 薄弱点 ----
    parts.append("<h2>三、薄弱知识点</h2>\n")
    if not report["weak_points"]:
        parts.append(f'<p>本次作答涉及的知识点掌握度均不低于 '
                     f'{MASTERY_THRESHOLD:.2f}，暂无新增薄弱点。</p>\n')
    else:
        parts.append("<ul>\n")
        for u in report["weak_points"]:
            parts.append(
                f'<li><strong>{_esc(u["kp_name"])}</strong>（{_esc(u["kp_id"])}）'
                f'：掌握度 {u["after"]:.2f}，本题证据 {_esc(u["evidence"])} 次'
                f'，置信度 {u["confidence"]:.2f}</li>\n')
        parts.append("</ul>\n")

    # ---- 下一步学习建议 ----
    parts.append("<h2>四、下一步学习建议</h2>\n")
    if report["plan_error"]:
        parts.append(f'<p class="muted">学习建议生成失败（{_esc(report["plan_error"])}）；'
                     "本次成绩与知识点画像不受影响。</p>\n")
    elif not report["plan_shown"]:
        parts.append('<p>当前没有低于阈值、需要优先补强的知识点——建议转入复习巩固。</p>\n')
    else:
        parts.append("<ol>\n")
        for s in report["plan_shown"]:
            recs = "、".join(s["recommended_item_ids"][:5]) or "（题库暂无推荐题）"
            parts.append(
                f'<li><strong>{_esc(s["kp_name"])}</strong>（{_esc(s["kp_id"])}）'
                f'：策略 {_esc(s["strategy_id"])}，目标掌握度 '
                f'{s["target_mastery"]:.2f}<br>'
                f'<span class="muted">依据：{_esc(s["rationale"])}；'
                f'推荐练习题：{_esc(recs)}</span></li>\n')
        parts.append("</ol>\n")
        if len(report["plan_steps"]) > len(report["plan_shown"]):
            parts.append(f'<p class="muted">完整计划共 {len(report["plan_steps"])} 步，'
                         f'此处展示与本卷最相关的 {len(report["plan_shown"])} 步'
                         f'（完整计划见 GET /learners/{_esc(report["learner_id"])}/plan）。'
                         "</p>\n")
    if report["reviews"]:
        nxt = min(r["due"] for r in report["reviews"])
        parts.append(f'<p class="muted">已达标的知识点进入间隔复习，最近一次到期日 '
                     f'{_esc(nxt)}，共 {len(report["reviews"])} 项。</p>\n')

    parts.extend([
        '<p class="foot">本报告由 xuexing.exam 渲染：判分取自 xuexing.grading，'
        "知识点画像取自 xuexing.diagnosis，学习路线取自 xuexing.route；"
        "口径与 POST /grade、POST /learners/{id}/responses、"
        "GET /learners/{id}/plan 一致。</p>\n",
        "</body>\n</html>\n",
    ])
    return "".join(parts)


