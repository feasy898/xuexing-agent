"""exam —— 学生作答闭环（开卷 → 作答 → 判分 → 画像 → 报告）的会话与报告内核。

为什么需要本模块：出卷（paper_by_spec/paper_spec）、成品卷渲染（paper_render）、
判分（grading）、诊断（diagnosis）、路线（route）、母题推荐（recommend）都已
就位，但缺一个把它们串成「学生真的能做一次题」的最薄一层——本模块就是这层：
一次开卷的**会话**（内存态）、一次提交的**判分与画像落地**、一页给家长/学生看的
**报告**。本模块不实现任何领域算法：判分调 grading.grade_to_response（与
``POST /grade`` 逐条同口径）、画像调 diagnosis.diagnose / aggregate_to_clusters
（与 ``POST /learners/{id}/responses`` 同口径）、学习计划调 route.build_plan +
recommend.attach_recommendations（与 ``GET /learners/{id}/plan``、``POST
/recommend?attach=true`` 同内核），卷面与作答页走 paper_render 的同一校验与取题
函数。

三处口径上的显式决策（都写在这里，避免后来者误读）：

1. **客观题/主观题分治**：``Item.item_type`` 属 ``choice``/``fill`` 的题走
   ``grading.grade_to_response`` 即时判分（与 /grade 完全同一函数，含 mcq_multi
   的 form 语义）；``solve``（解答/论述/材料分析）**不自动判分**——本仓唯一可用的
   主观测分手段是 grading.grade_fill 的字面等值，对解答题是伪判定。这与
   ``xuexing.types.Response`` 的注释一致：「客观题由系统判，主观题由教师/批改端
   给」。故：solve 题不进得分、不进画像作答序列，报告里标「待批改」并原样回显学生
   作答。其余 item_type（若题库出现）同样按待批改处理并在报告注明——不猜、不降级。

2. **学科级 bank/graph**：一次会话自带 (bank, graph)——bank 是该卷型学段的题库
   （server 的 stage_bank_loader 注入点），graph 是该学科全年级合并图
   （kpgraph_subject.load_kpgraph_subject）。诊断与画像必须用**本题所属学科**的
   bank/graph，否则 ``diagnose`` 的 B1（题库无此题即跳过）会把跨学科卷的作答证据
   全部丢掉，报告只剩先验。落进 store 的 profile 因此与 ``POST
   /learners/{id}/responses`` 语义同构、只是数据源学科不同。

3. **会话即能力（capability）**：session_id 是随机不透明串，作答页/提交/报告三处
   都不按 X-Org-Id 头二次鉴权（原生 <form> 也发不了自定义头）；机构归属在**开卷
   时**记入会话，后续落地一律写回该机构域，跨机构隔离由 org 归属保证而非按头过滤。
   这与仓内「/responses 等有状态端点按 (org, learner) 分域」一致。

会话状态机：``open`` → ``started`` →（``submit``）→ ``submitted``。
``ttl`` 到期（默认 2 小时，由 create_app 的 exam_store 注入点构造）后任何端点对
该会话一律 410 Gone；未知会话 404；已提交再提交 409；未提交就取报告 409。

纯度：渲染与判分/组数据是纯函数（无 IO、无随机、无时钟，唯一的时间来源是会话
记录的 created_at，由调用方注入）；只有 ExamStore 持有进程内可变状态，且不导出到
会话之外。
"""
from __future__ import annotations

import html
from datetime import datetime, timezone

from xuexing.diagnosis import aggregate_to_clusters, diagnose
from xuexing.grading import grade_to_response
from xuexing.paper_render import format_points, human_paper_title
from xuexing.recommend import attach_recommendations
from xuexing.route import build_plan
from xuexing.types import Response, to_dict

__all__ = [
    "AUTO_ITEM_TYPES",
    "DEFAULT_MAX_SESSIONS",
    "DEFAULT_SESSION_TTL",
    "ExamError",
    "ExamStore",
    "VERDICT_CORRECT",
    "VERDICT_PENDING",
    "VERDICT_WRONG",
    "build_report",
    "grade_submission",
    "render_report_html",
]

# 客观题题类：与 grading.grade 的分派一致（choice 覆盖 mcq_single/mcq_multi/
# 判断/单选等价类；fill 覆盖填空/默写类）。其余题类一律走「待批改」旁路。
AUTO_ITEM_TYPES = frozenset({"choice", "fill"})

VERDICT_CORRECT = "correct"
VERDICT_WRONG = "wrong"
VERDICT_PENDING = "pending"

DEFAULT_SESSION_TTL = 7200.0      # 秒；create_app(exam_session_ttl=…) 可调
DEFAULT_MAX_SESSIONS = 512        # 超量按 created_at 升序淘汰最旧会话（见 ExamStore）

_REPORT_RECS_PER_STEP = 3          # 报告里每个学习步骤挂的练习题数上限
_ISO = "%Y-%m-%d %H:%M:%SZ"


class ExamError(ValueError):
    """exam 模块的领域错误（ValueError 子类）——server 映射为 400。"""


# ---------------- 会话存储（进程内，按机构分域，与 OrgStore 同一分域口径） ----------------

class ExamStore:
    """开卷会话登记处：{org: {session_id: session}}。

    会话体是纯数据 dict（创建后只读——submit 把结果写进**新**的副本并整体换回，
    避免 report 渲染读到半写状态）。org 位用 multitenant.resolve_org 归并，与
    OrgStore/AttemptCounter 同款机构门。
    """

    def __init__(self, ttl: float = DEFAULT_SESSION_TTL,
                 max_sessions: int = DEFAULT_MAX_SESSIONS) -> None:
        if not isinstance(ttl, (int, float)) or isinstance(ttl, bool) or ttl < 0:
            raise ExamError(f"ttl must be a non-negative number, got {ttl!r}")
        if isinstance(max_sessions, bool) or not isinstance(max_sessions, int) or max_sessions < 1:
            raise ExamError(f"max_sessions must be an int >= 1, got {max_sessions!r}")
        self._ttl = float(ttl)
        self._max_sessions = max_sessions
        self._domains: dict[str, dict[str, dict]] = {}

    def open(self, org_id: str, session: dict) -> dict:
        """登记新会话（同 session_id 覆盖为最后一次开卷）。超量先淘汰最旧的。"""
        from xuexing.multitenant import resolve_org

        org = resolve_org(org_id)
        domain = self._domains.setdefault(org, {})
        while len(domain) >= self._max_sessions:
            oldest = min(domain.values(), key=lambda s: (s["created_at"], s["session_id"]))
            domain.pop(oldest["session_id"], None)
        domain[session["session_id"]] = session
        return session

    def get(self, session_id: str) -> dict | None:
        """按 session_id 跨机构取会话（会话即能力，见模块 docstring 第 3 条）。

        找不到或已过期一律返回 None——调用方据此区分需要的信息：过期会话另带
        ``expired`` 标记（用 :meth:`state_of`）。
        """
        for domain in self._domains.values():
            if session_id in domain:
                return domain[session_id]
        return None

    def state_of(self, session_id: str, now: float) -> tuple[str | None, bool]:
        """(会话 or None, 是否已过期)。过期判定 = now - created_at > ttl（严格大于，
        ttl=0 时任何已过创建瞬间的会话都算过期——供测试构造过期会话）。"""
        session = self.get(session_id)
        if session is None:
            return None, False
        expired = (now - session["created_at"]) > self._ttl
        return session, expired

    def replace(self, session: dict) -> None:
        """整体换回一份新会话副本（同 session_id、同 org）。"""
        for org, domain in self._domains.items():
            if session["session_id"] in domain:
                domain[session["session_id"]] = session
                return
        raise ExamError(f"session not registered: {session['session_id']!r}")

    def ids(self, org_id: str | None = None) -> list:
        """某机构（缺省=全部机构）的 session_id 列表，升序去重。只读。"""
        from xuexing.multitenant import resolve_org

        if org_id is None:
            out: set = set()
            for domain in self._domains.values():
                out.update(domain)
            return sorted(out)
        return sorted(self._domains.get(resolve_org(org_id), {}))


# ---------------- 判分（grading 内核；主观题走待批改旁路） ----------------

def _answer_text(raw) -> str:
    """表单/JSON 的原始作答值 -> 判分用文本。None/非 str/纯空白 -> None（未作答，
    grading 的未作答短路吃 None；空白串由 normalize_answer 后短路）。"""
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise ExamError(f"answer must be a str or null, got {type(raw).__name__}")
    return raw


def grade_submission(paper: dict, bank, answers: dict) -> dict:
    """一次提交 -> 逐题判定 + 客观题得分 + 供画像使用的作答序列（纯函数）。

    answers 形如 {question_no(int): str | None}。多选题的多个表单值由调用方先
    归并成一个串（分隔符 "、" 与 grading._split_multi 一致）。

    返回 ``{"items": [...], "earned": float, "auto_points": float,
    "auto_count": int, "auto_correct": int, "pending_count": int,
    "pending_points": float, "responses": [Response, ...]}``。
    """
    if not isinstance(answers, dict):
        raise ExamError(f"answers must be a dict, got {type(answers).__name__}")
    items: list[dict] = []
    responses: list[Response] = []
    earned = auto_points = pending_points = 0.0
    auto_count = auto_correct = pending_count = 0
    for sec in paper["sections"]:
        for q in sec["questions"]:
            no = q["question_no"]
            item = bank.get(q["item_id"])
            if item is None:
                raise ExamError(f"question {no}: item not in bank: {q['item_id']}")
            raw = answers.get(no)
            text = _answer_text(raw)
            points = q["points"]
            record = {
                "question_no": no,
                "item_id": item.id,
                "item_type": item.item_type,
                "form": getattr(item, "form", ""),
                "points": points,
                "section_title": sec["title"],
                "stem": item.stem.strip(),
                "options": [str(o) for o in (getattr(item, "options", None) or [])],
                "kps": list(item.kps),
                "learner_answer": text,
            }
            if getattr(item, "item_type", "") in AUTO_ITEM_TYPES:
                resp = grade_to_response(item, text)  # 与 POST /grade 同一函数
                record["correct"] = resp.correct
                record["verdict"] = VERDICT_CORRECT if resp.correct else VERDICT_WRONG
                # 报告是家长/学生端的事后页：此处才允许读 answer/solution
                record["answer"] = item.answer
                record["solution"] = getattr(item, "solution", "") or ""
                responses.append(resp)
                auto_count += 1
                auto_points += points
                if resp.correct:
                    auto_correct += 1
                    earned += points
            else:
                record["correct"] = None
                record["verdict"] = VERDICT_PENDING
                record["answer"] = None
                record["solution"] = None
                pending_count += 1
                pending_points += points
            items.append(record)
    return {
        "items": items,
        "earned": earned,
        "auto_points": auto_points,
        "auto_count": auto_count,
        "auto_correct": auto_correct,
        "pending_count": pending_count,
        "pending_points": pending_points,
        "responses": responses,
    }


# ---------------- 报告数据组装（diagnosis + route + recommend 内核） ----------------

def build_report(session: dict, graded: dict, prev_profile, bank, graph, strategies,
                 misconceptions=None, today=None, now_iso: str = "") -> tuple:
    """提交结果 + 该学科 bank/graph -> (报告数据 dict, 本次画像或 None)（纯函数，不落库）。

    画像：仅客观题作答进 ``diagnosis.diagnose``（主观题待批改，无对错证据不入图）；
    客观题为 0 题时不动画像，只回显既有画像（无则 None），第二返回值亦为 None
    ——调用方据此**不覆盖** store 里已有的画像。学习计划：``route.build_plan`` +
    ``recommend.attach_recommendations``（同 ``/plan`` 与 ``/recommend?attach=true``
    内核）。计划失败（route 的先序死锁等 ValueError）不影响画像产出，如实记进
    ``plan_error`` 由报告页显示。
    """
    if today is None:
        today = datetime.now(timezone.utc).date()
    responses: list[Response] = list(graded["responses"])
    profile = prev_profile
    new_profile = None
    clusters: dict = {}
    if responses:
        profile = diagnose(responses, bank, graph, learner_id=session["learner_id"])
        new_profile = profile
        clusters = aggregate_to_clusters(profile, graph)
    elif prev_profile is not None:
        clusters = aggregate_to_clusters(prev_profile, graph)

    plan_dict = None
    plan_error = None
    if profile is not None:
        try:
            plan = build_plan(profile, bank, graph, strategies, today)
            plan = attach_recommendations(plan, bank, misconceptions, _REPORT_RECS_PER_STEP)
            plan_dict = to_dict(plan)
        except ValueError as e:
            plan_error = f"{type(e).__name__}: {e}"

    kp_name = {}
    for kp in graph.kps():
        kp_name[kp.id] = kp.name

    mastery = dict(profile.mastery) if profile is not None else {}
    evidence = dict(profile.evidence) if profile is not None else {}
    touched = sorted({k for rec in graded["items"] for k in rec["kps"] if k in evidence})
    updates = [
        {
            "kp_id": kp,
            "kp_name": kp_name.get(kp, kp),
            "mastery": mastery.get(kp, 0.0),
            "prev": (prev_profile.mastery.get(kp) if prev_profile is not None else None),
            "evidence": evidence.get(kp, 0),
        }
        for kp in touched
    ]

    steps = []
    for step in (plan_dict or {}).get("steps", []):
        steps.append({
            "kp_id": step["kp_id"],
            "kp_name": kp_name.get(step["kp_id"], step["kp_id"]),
            "strategy_id": step["strategy_id"],
            "rationale": step["rationale"],
            "target_mastery": step["target_mastery"],
            "recommended_item_ids": step.get("recommended_item_ids", []),
        })

    report = {
        "session_id": session["session_id"],
        "learner_id": session["learner_id"],
        "org_id": session["org_id"],
        "spec_id": session["spec_id"],
        "seed": session["seed"],
        "title": human_paper_title(session["paper"]),
        "total_points": session["paper"]["total_points"],
        "question_count": session["paper"]["question_count"],
        "duration_min": session["paper"]["duration_min"],
        "submitted_at": now_iso,
        "items": graded["items"],
        "earned": graded["earned"],
        "auto_points": graded["auto_points"],
        "auto_count": graded["auto_count"],
        "auto_correct": graded["auto_correct"],
        "pending_count": graded["pending_count"],
        "pending_points": graded["pending_points"],
        "profile_present": profile is not None,
        "profile_updated_at": (profile.updated_at if profile is not None else ""),
        "mastery": mastery,
        "updates": updates,
        "clusters": clusters,
        "plan": plan_dict,
        "plan_error": plan_error,
        "steps": steps,
        "reviews": (plan_dict or {}).get("reviews", []),
    }
    return report, new_profile


# ---------------- 报告页渲染（自包含 HTML，内联 CSS，无 JS/外链） ----------------

def _esc(text) -> str:
    return html.escape(text if isinstance(text, str) else str(text), quote=True)


def _pct(x) -> str:
    return f"{max(0.0, min(1.0, float(x))) * 100:.1f}%"


_REPORT_CSS = """  * { box-sizing: border-box; }
  body {
    max-width: 900px; margin: 0 auto; padding: 24px 20px 60px;
    font-family: "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif;
    font-size: 14px; line-height: 1.75; color: #1c1c1c; background: #fafafa;
  }
  h1 { font-size: 20px; margin: 0 0 4px; }
  h2 { font-size: 16px; margin: 28px 0 10px; padding-bottom: 6px;
       border-bottom: 2px solid #e0e0e0; }
  .meta { color: #555; font-size: 13px; margin-bottom: 16px; }
  .meta span { margin-right: 14px; }
  .score { background: #fff; border: 1px solid #e0e0e0; border-radius: 6px;
           padding: 14px 18px; margin-bottom: 8px; }
  .score b { font-size: 22px; }
  table { width: 100%; border-collapse: collapse; background: #fff; }
  th, td { border: 1px solid #e6e6e6; padding: 6px 8px; text-align: left;
           vertical-align: top; font-size: 13px; }
  th { background: #f2f4f7; }
  .v-correct { color: #157f3d; font-weight: 600; }
  .v-wrong { color: #b3261e; font-weight: 600; }
  .v-pending { color: #8a6d1f; font-weight: 600; }
  .bar { background: #eceff3; border-radius: 3px; height: 10px; width: 160px;
         display: inline-block; vertical-align: middle; }
  .bar > i { display: block; height: 10px; border-radius: 3px; background: #4a7ebb; }
  .note { background: #fff8e6; border: 1px solid #f0dfae; border-radius: 6px;
          padding: 8px 12px; font-size: 13px; color: #6b551a; }
  .kp-row td { padding: 4px 8px; }
"""


def render_report_html(report: dict) -> str:
    """报告数据 -> 自包含 HTML（家长/学生可读；无 JS、无外链、无表单）。"""
    total = report["total_points"]
    parts = [
        "<!DOCTYPE html>\n", '<html lang="zh-CN">\n<head>\n<meta charset="utf-8">\n',
        f"<title>作答报告 · {_esc(report['title'])}</title>\n",
        f"<!-- 学生作答报告：会话 {report['session_id']}，由 xuexing.exam 渲染"
        f"（判分 grading / 画像 diagnosis / 计划 route+recommend 内核）。 -->\n",
        f"<style>\n{_REPORT_CSS}</style>\n</head>\n<body>\n",
        f"<h1>{_esc(report['title'])} · 作答报告</h1>\n",
        '<div class="meta">'
        f'<span>学生 {_esc(report["learner_id"])}</span>'
        f'<span>卷型 {_esc(report["spec_id"])}</span>'
        f'<span>seed {report["seed"]}</span>'
        f'<span>共 {report["question_count"]} 题</span>'
        f'<span>提交于 {_esc(report["submitted_at"])}</span></div>\n',
        # ---- 成绩 ----
        '<div class="score">客观题得分 <b>'
        f'{format_points(report["earned"])}</b> / {format_points(report["auto_points"])} 分'
        f'（客观题 {report["auto_count"]} 道，答对 {report["auto_correct"]} 道）'
        f'<br>全卷满分 {format_points(total)} 分'
        + (f'；另有 {report["pending_count"]} 道解答题（{format_points(report["pending_points"])} 分）'
           f'待教师批改，本次不计入得分与知识地图。'
           if report["pending_count"] else "。")
        + "</div>\n",
    ]
    if report["pending_count"]:
        parts.append(
            '<div class="note">解答题需人工批改：本次只对客观题（选择题/填空题）做了'
            '系统判分与画像更新，解答题的原样作答已在下表回显，请交由教师批改。</div>\n')

    # ---- 逐题对错 ----
    parts.append("<h2>逐题对错</h2>\n<table>\n"
                 "<tr><th>题号</th><th>题型</th><th>判定</th><th>我的作答</th>"
                 "<th>正确答案 / 解析</th></tr>\n")
    for rec in report["items"]:
        verdict = rec["verdict"]
        vcls = {VERDICT_CORRECT: "v-correct", VERDICT_WRONG: "v-wrong"}.get(verdict, "v-pending")
        vtext = {VERDICT_CORRECT: "✓ 正确", VERDICT_WRONG: "✗ 错误"}.get(verdict, "待批改")
        mine = rec["learner_answer"]
        mine_text = "（未作答）" if not mine else _esc(mine)
        if verdict == VERDICT_WRONG:
            right = f"正确答案：{_esc(rec['answer'])}"
            if rec["solution"]:
                right += f"<br>解析：{_esc(rec['solution'])}"
        elif verdict == VERDICT_CORRECT:
            right = "—"
        else:
            right = "—（待教师批改）"
        parts.append(
            f"<tr><td>{rec['question_no']}</td>"
            f"<td>{_esc(rec['item_type'])}</td>"
            f'<td class="{vcls}">{vtext}</td>'
            f"<td>{mine_text}</td><td>{right}</td></tr>\n")
    parts.append("</table>\n")

    # ---- 知识点掌握更新 ----
    parts.append("<h2>知识点掌握更新</h2>\n")
    if not report["updates"]:
        parts.append('<div class="note">本次没有客观题作答证据，知识点掌握度未更新'
                     "（解答题批改后可重新诊断）。</div>\n")
    else:
        parts.append('<div class="meta" style="margin-bottom:6px">'
                     f"画像更新于 {_esc(report['profile_updated_at'])}；掌握度为 [0,1]，"
                     "条形越满越掌握。</div>\n")
        parts.append("<table>\n<tr><th>知识点</th><th>掌握度</th><th>本次前 → 后</th>"
                     "<th>作答次数</th></tr>\n")
        for u in report["updates"]:
            prev = "—" if u["prev"] is None else _pct(u["prev"])
            parts.append(
                f'<tr class="kp-row"><td>{_esc(u["kp_name"])}<br>'
                f'<span style="color:#888;font-size:11px">{_esc(u["kp_id"])}</span></td>'
                f'<td><span class="bar"><i style="width:{_pct(u["mastery"])}"></i></span> '
                f'{_pct(u["mastery"])}</td>'
                f"<td>{prev} → {_pct(u['mastery'])}</td><td>{u['evidence']}</td></tr>\n")
        parts.append("</table>\n")

    # ---- 知识地图（cluster 概览，diagnosis.aggregate_to_clusters 口径） ----
    if report["clusters"]:
        parts.append("<h2>知识地图（学段/主题平均掌握度）</h2>\n<table>\n"
                     "<tr><th>主题</th><th>平均掌握度</th></tr>\n")
        for label in sorted(report["clusters"]):
            m = report["clusters"][label]
            parts.append(
                f'<tr class="kp-row"><td>{_esc(label)}</td>'
                f'<td><span class="bar"><i style="width:{_pct(m)}"></i></span> {_pct(m)}</td>'
                "</tr>\n")
        parts.append("</table>\n")

    # ---- 薄弱点与下一步学习建议 ----
    parts.append("<h2>薄弱点与下一步学习建议</h2>\n")
    if report["plan_error"]:
        parts.append(f'<div class="note">本次未能生成学习计划（{_esc(report["plan_error"])}）；'
                     "作答与画像已正常记录。</div>\n")
    elif not report["steps"]:
        parts.append('<div class="note">本次没有低于掌握阈值的知识点——按现有证据无需补课，'
                     "继续做新题巩固即可。</div>\n")
    else:
        parts.append("<table>\n<tr><th>顺序</th><th>薄弱知识点</th><th>当前掌握度</th>"
                     "<th>学习策略</th><th>建议练习</th></tr>\n")
        for i, step in enumerate(report["steps"], 1):
            recs = "、".join(step["recommended_item_ids"]) or "—"
            parts.append(
                f"<tr><td>{i}</td><td>{_esc(step['kp_name'])}<br>"
                f'<span style="color:#888;font-size:11px">{_esc(step["kp_id"])}</span></td>'
                f"<td>{_pct(report['mastery'].get(step['kp_id'], 0.0))}</td>"
                f"<td>{_esc(step['strategy_id'])}<br>"
                f'<span style="color:#666;font-size:12px">{_esc(step["rationale"])}</span></td>'
                f"<td>{_esc(recs)}</td></tr>\n")
        parts.append("</table>\n")
    if report["reviews"]:
        due = report["reviews"][0]["due"]
        parts.append(f'<div class="meta">已达标知识点的复习日程：共 '
                     f'{len(report["reviews"])} 项，最近到期 {due}。</div>\n')

    parts.append('</body>\n</html>\n')
    return "".join(parts)
