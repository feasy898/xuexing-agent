"""exam_loop —— 学生作答闭环内核（开卷 → 提交判分 → 个人报告）。

为什么单独成模块：server.py 是薄胶水层（只做 HTTP 编解码），而「会话 + 判分 +
报告装配」是一段有实质判定逻辑的业务流，不该塞进端点函数。三个端点（见
server.py）只做编解码，本模块承担全部判定。

**复用既有内核，绝不另造平行实现**（本模块的核心约束）：
- 出卷：``paper_by_spec.generate_paper_by_spec`` + ``paper_spec.load_spec``——
  与 ``POST /papers/by-spec`` / ``GET .../render.html`` 同一条装订路径；
- 渲染学生卷：``paper_render.render_exam_form_html``（与打印成品卷共用
  ``_validate_paper``/``_item_for``/``_esc``，红线同）；
- 判分：``grading.grade_to_response``——与 ``POST /grade`` **逐字同一个函数**，
  归一化/单位门/数值等值/choice 两趟解析全部来自冻结契约，本模块不写任何
  判分规则；
- 诊断：``diagnosis.diagnose`` + ``aggregate_to_clusters``——与
  ``POST /learners/{id}/responses`` 同一个入口；
- 路线：``route.build_plan``（薄弱点排序 = 「影响×缺口」拓扑序）+ ``recommend``
  家族的 ``attach_recommendations``（练习题挂载）——与
  ``GET /learners/{id}/plan`` / ``POST /recommend?attach`` 同一实现；
- 报告页：``exam_report.render_report_html``（纯渲染）。

**客观题即时判分、主观题不假装判**：``item_type`` 为 ``choice``/``fill`` 的题走
``grade_to_response`` 即时判分（客观题口径 = ``POST /grade`` 口径）；``solve``
（解答题）在本最小闭环里**不自动判分**——仓内没有主观题评分器，凭字符串相等判
解答题会造出假的「错」，故记为待批改（``correct=None``）、不进画像证据。这与
``types.Response`` 的注释「主观题由教师/批改端给」一致。

**画像范围（诚实声明）**：本模块诊断用的是**本场考试所属学科的 KP 图**
（``kpgraph_subject.load_kpgraph_subject`` 装载，见 server.py 注入点），不是
``create_app`` 注入的单年级图。原因：本卷题目来自该学科题库，其知识点在该学科
图内；若拿别的学科图诊断，``diagnosis`` 会按契约跳过图外知识点（B 分支），
画像将全空。跨学科考试后，``GET /learners/{id}/plan`` 仍按应用注入图计算（那是
既有端点的既有行为，本模块不改写），报告页的「下一步建议」用本卷学科图计算——
两者在单学科应用中等价。

会话存储：进程内 dict（``ExamSessionStore``），按 (org, session_id) 分域，与
multitenant 的 org 语义一致（X-Org-Id 缺省归并走 ``resolve_org``）。带 TTL 会话
过期（默认 2 小时，注入 ``monotonic`` 时钟，无真实 sleep 依赖）。**不落盘**：
最小闭环的定位是渠道无关的一次性考试会话；学习者画像与作答流水照旧落既有
OrgStore（``entry["responses"]`` / ``entry["profile"]``），所以 ``/profile``
仍能复核本次结果。
"""
from __future__ import annotations

import secrets
import time
from typing import Callable

from xuexing.diagnosis import aggregate_to_clusters, diagnose
from xuexing.grading import grade_to_response
from xuexing.multitenant import resolve_org
from xuexing.paper_render import REPLY_FIELD_PREFIX, render_exam_form_html
from xuexing.recommend import attach_recommendations
from xuexing.route import RouteError, build_plan
from xuexing.types import Profile, Response

__all__ = [
    "ExamLoopError",
    "ExamSessionNotFound",
    "ExamSessionExpired",
    "ExamSessionStore",
    "DEFAULT_SESSION_TTL_SECONDS",
    "MASTERY_TARGET",
    "is_objective",
    "collect_answers",
    "grade_submission",
    "build_report",
    "exam_html",
]

# 会话有效期（秒）。超时后 start 之外的读/写一律 410（见 ExamSessionExpired）。
DEFAULT_SESSION_TTL_SECONDS = 7200

# 「已达标」的掌握度线，与 route.build_plan 的 mastery_threshold 缺省值同源
# （同一次调用里显式传入，不依赖缺省，避免两处各写一个魔数）。
MASTERY_TARGET = 0.65

# 可即时判分的题型（= types.Item.item_type 的客观题型）；solve 走人工批改。
OBJECTIVE_TYPES = ("choice", "fill")

# 报告里「建议先练」的题目数上限（recommend 家族同一 limit 口径）。
RECOMMEND_LIMIT = 5


class ExamLoopError(ValueError):
    """作答闭环的领域校验失败（参数错 → 400）。"""


class ExamSessionNotFound(ExamLoopError):
    """会话不存在（含 org 不匹配）→ 404。"""


class ExamSessionExpired(ExamLoopError):
    """会话已过 TTL → 410（Gone：资源曾存在、现不可用）。"""


def _pct(x) -> str:
    return f"{float(x) * 100:.0f}%"


def is_objective(item) -> bool:
    """该题是否走即时判分（客观题）。solve/未知题型 → False（不假装能判）。"""
    return getattr(item, "item_type", "") in OBJECTIVE_TYPES


class ExamSessionStore:
    """进程内考试会话 {(org, session_id): session} + TTL 过期。

    时钟注入（``clock``，默认 ``time.monotonic``）：过期判定是纯函数式的
    「now - created >= ttl」，测试可注入可控时钟而不 sleep。
    会话上限 ``max_sessions``：超限时按 created_at 升序淘汰最旧者（防内存
    无界增长；淘汰后其报告页 410/404，如实告知）。
    """

    def __init__(self, ttl_seconds: float = DEFAULT_SESSION_TTL_SECONDS,
                 max_sessions: int = 512,
                 clock: Callable[[], float] = time.monotonic) -> None:
        if not isinstance(ttl_seconds, (int, float)) or isinstance(ttl_seconds, bool) or ttl_seconds < 0:
            raise ExamLoopError(f"ttl_seconds must be a number >= 0, got {ttl_seconds!r}")
        if not isinstance(max_sessions, int) or isinstance(max_sessions, bool) or max_sessions < 1:
            raise ExamLoopError(f"max_sessions must be an int >= 1, got {max_sessions!r}")
        if not callable(clock):
            raise ExamLoopError("clock must be callable")
        self.ttl_seconds = float(ttl_seconds)
        self.max_sessions = max_sessions
        self._clock = clock
        self._sessions: dict[tuple[str, str], dict] = {}

    def new_session_id(self) -> str:
        """新会话 id（URL 安全、不可枚举：32 字节 CSPRNG → 43 字符 base64url）。"""
        return secrets.token_urlsafe(32)

    def put(self, org_id: str | None, session: dict) -> str:
        """登记会话（get-or-create 语义由调用方保证唯一 id）-> 返回 session_id。
        超上限时淘汰 created_at 最旧的一条。"""
        org = resolve_org(org_id)
        sid = session["session_id"]
        session.setdefault("created_at", self._clock())
        self._sessions[(org, sid)] = session
        if len(self._sessions) > self.max_sessions:
            oldest = min(self._sessions.values(), key=lambda s: s["created_at"])
            self._sessions.pop((oldest["org_id"], oldest["session_id"]), None)
        return sid

    def get(self, org_id: str | None, session_id: str) -> dict:
        """取会话：不存在 → ExamSessionNotFound；已过期 → ExamSessionExpired。
        org 位先归并再查（缺省域看不到别的机构会话，与 /learners 隔离同构）。"""
        if not isinstance(session_id, str) or not session_id.strip():
            raise ExamLoopError(f"session_id must be a non-blank str, got {session_id!r}")
        org = resolve_org(org_id)
        session = self._sessions.get((org, session_id))
        if session is None:
            raise ExamSessionNotFound(f"exam session not found: {session_id}")
        if self._clock() - session["created_at"] >= self.ttl_seconds:
            raise ExamSessionExpired(f"exam session expired: {session_id}")
        return session

    def drop(self, org_id: str | None, session_id: str) -> None:
        """删除会话（幂等；不存在不抛）。"""
        self._sessions.pop((resolve_org(org_id), session_id), None)

    def count(self) -> int:
        """当前会话数（只读，测试与自检用）。"""
        return len(self._sessions)


def exam_html(session: dict) -> str:
    """会话 -> 可作答学生卷 HTML（委托 paper_render，本模块不产标记）。"""
    return render_exam_form_html(
        session["paper"], session["bank"],
        session_id=session["session_id"], learner_id=session["learner_id"])


def _question_index(session: dict) -> dict[int, dict]:
    """{question_no: {"question_no", "item_id", "points"}}，题号全卷唯一。"""
    index: dict[int, dict] = {}
    for sec in session["paper"]["sections"]:
        for q in sec["questions"]:
            index[q["question_no"]] = q
    return index


def collect_answers(session: dict, raw: dict) -> dict[int, str | None]:
    """提交载荷 -> {题号: 原始作答串}（未提交/空白 → None）。

    接受两种键：``"item_3"``（网页表单字段名，走 ``REPLY_FIELD_PREFIX`` 约定）
    与 ``3``/``"3"``（JSON 客户端直接给题号）。多选（同名多值）按顿号连接——
    ``grading._resolve_multi`` 的分隔符含「、」，与该口径一致。

    契约要点：**不猜题号**。出现本卷没有的题号 → ExamLoopError（400），否则
    学生可以把答案写到不存在的题上而无人察觉。合法题号的缺失项 → None（未作答），
    这不是错误：交白卷是合法行为（判分口径与 ``POST /grade`` 传 None 一致）。
    """
    if not isinstance(raw, dict):
        raise ExamLoopError(f"answers must be a dict, got {type(raw).__name__}")
    index = _question_index(session)
    out: dict[int, str | None] = {}
    for key, value in raw.items():
        if isinstance(key, str) and key.startswith(REPLY_FIELD_PREFIX):
            tail = key[len(REPLY_FIELD_PREFIX):]
        else:
            tail = key
        try:
            no = int(str(tail).strip())
        except (TypeError, ValueError):
            raise ExamLoopError(
                f"answer key must be a question number or {REPLY_FIELD_PREFIX}<no>, got {key!r}")
        if no not in index:
            raise ExamLoopError(
                f"question {no} is not in this exam (1..{max(index)})")
        if isinstance(value, (list, tuple)):  # checkbox 多选：同名多值
            parts = [str(v).strip() for v in value if str(v).strip()]
            out[no] = "、".join(parts) if parts else None
        elif value is None:
            out[no] = None
        elif isinstance(value, str):
            out[no] = value if value.strip() else None
        else:
            raise ExamLoopError(
                f"answer for question {no} must be str or list, got {type(value).__name__}")
    return out


def grade_submission(session: dict, raw: dict) -> dict:
    """提交载荷 -> 判分结果（逐题对错 + 得分 + 待入画像的 Response 列表）。

    判分一律委托 ``grading.grade_to_response``（= ``POST /grade`` 口径）。
    客观题（choice/fill）即时判分；solve 题记 ``correct=None``（待批改）且
    **不进画像**——凭字符串相等判解答题会造出假的错，比不判更坏。
    得分 = 客观题得分之和（待批改题不预扣分，报告里如实标注）。
    """
    bank = session["bank"]
    answers = collect_answers(session, raw)
    index = _question_index(session)

    items: list[dict] = []
    responses: list[Response] = []
    score = 0.0
    for no in sorted(index):
        q = index[no]
        item = bank.get(q["item_id"])
        if item is None:  # 会话装订时题必在库；这里仍 fail-closed，不静默跳题
            raise ExamLoopError(
                f"question {no}: item not in bank: {q['item_id']}")
        given = answers.get(no)
        objective = is_objective(item)
        if objective:
            try:
                resp = grade_to_response(item, given)
            except ValueError as e:  # GradingError（题目侧非法）→ 400
                raise ExamLoopError(f"question {no}: {e}")
            correct = bool(resp.correct)
            score += q["points"] if correct else 0
            responses.append(resp)
        else:
            correct = None
        items.append({
            "question_no": no,
            "item_id": item.id,
            "points": q["points"],
            "item_type": getattr(item, "item_type", ""),
            "stem": item.stem,
            "expected": getattr(item, "answer", ""),
            "learner_answer": given,
            "correct": correct,
            "graded": objective,
            "kps": list(getattr(item, "kps", []) or []),
        })
    return {"items": items, "score": score, "responses": responses}


def _kp_stats(items: list[dict], graph) -> tuple[dict, set]:
    """本次作答的知识点统计 -> ({kp_id: (hit, tried)}, 本次测到的图内 kp_id 集)。

    只统计**主知识点**（kps[0]）：与 diagnose 的 B3「按声明顺序、首个权重 1.0、
    其余 0.5」口径一致地取主知识点做「本次对错」呈现，不另立归属规则。图外
    知识点跳过（与 diagnose 跳过图外 KP 同理——它在那边不产生证据）。
    """
    hits: dict[str, int] = {}
    tried: dict[str, int] = {}
    for it in items:
        kps = it.get("kps") or []
        if not kps:
            continue
        kp = kps[0]
        if not graph.has(kp):
            continue
        tried[kp] = tried.get(kp, 0) + 1
        if it.get("correct"):
            hits[kp] = hits.get(kp, 0) + 1
    return ({kp: (hits.get(kp, 0), tried[kp]) for kp in tried}, set(tried))


def _scoped_profile(profile: Profile) -> Profile:
    """把画像收窄到**本次真正测到**的知识点（evidence > 0）。

    为什么：``diagnose`` 对图内每个 KP 都给先验 0.5，而 ``build_plan`` 的弱集是
    「mastery < 0.65 的图内 KP」——学科级图（数百 KP）下未测 KP 全都会被算成
    「薄弱」，报告的建议列表会被几百条噪声淹没。收窄只是**喂给既有内核的输入**，
    不改 build_plan 的任何排序/门控逻辑。
    """
    kps = {k for k, n in profile.evidence.items() if n > 0}
    return Profile(
        learner_id=profile.learner_id,
        mastery={k: profile.mastery[k] for k in kps if k in profile.mastery},
        evidence={k: profile.evidence[k] for k in kps},
        updated_at=profile.updated_at,
    )


def build_report(session: dict, graded: dict, graph, strategies, misconceptions=None,
                 bank=None, today=None) -> dict:
    """判分结果 + 内核 -> 报告数据 dict（``exam_report`` 渲染它）。

    流程（全部既有内核）：``diagnose`` 出画像 → ``aggregate_to_clusters`` 出板块
    总览 → 收窄画像 → ``build_plan`` 排薄弱点与学习顺序 → ``attach_recommendations``
    挂练习题。路线内核抛 ``RouteError``（先序死锁/策略选不出）时如实记 plan_error
    并降级为「暂无建议」，不让报告页 500。
    """
    import datetime  # 局部导入：模块顶层保持「无时钟」形象，只在取今天日期时用

    today = today if today is not None else datetime.date.today()
    bank = bank if bank is not None else session["bank"]
    profile = diagnose(graded["responses"], bank, graph, learner_id=session["learner_id"])
    clusters = aggregate_to_clusters(profile, graph)
    stats, touched = _kp_stats(graded["items"], graph)
    scoped = _scoped_profile(profile)

    plan_error = ""
    steps, reviews, recs = [], [], {}
    try:
        plan = build_plan(scoped, bank, graph, strategies, today,
                          mastery_threshold=MASTERY_TARGET)
        with_items = attach_recommendations(plan, bank, misconceptions,
                                            limit=RECOMMEND_LIMIT)
        steps = list(with_items.steps)
        reviews = list(with_items.reviews)
        recs = {s.kp_id: list(s.recommended_item_ids) for s in steps}
    except (RouteError, ValueError) as e:  # 路线/推荐内核的领域失败：降级不崩
        plan_error = str(e)

    step_by_kp = {s.kp_id: s for s in steps}
    weak_rows = []
    for kp_id, mastery in sorted(scoped.mastery.items(), key=lambda kv: (kv[1], kv[0])):
        if mastery >= MASTERY_TARGET:
            continue
        kp = graph.get(kp_id)
        hit, tried = stats.get(kp_id, (0, 0))
        step = step_by_kp.get(kp_id)
        weak_rows.append({
            "kp_id": kp_id,
            "name": getattr(kp, "name", "") or kp_id,
            "cluster": getattr(kp, "cluster", "") or "",
            "mastery": mastery,
            "evidence": profile.evidence.get(kp_id, 0),
            "hit": hit,
            "tried": tried,
            "why": (f"掌握度 {_pct(mastery)} 低于目标线 {_pct(MASTERY_TARGET)}"
                    f"（本次 {tried} 题对 {hit} 题）"),
            "strategy_id": getattr(step, "strategy_id", ""),
        })

    next_steps = []
    for step in steps[:8]:
        kp = graph.get(step.kp_id)
        strategy = strategies.get(step.strategy_id) if hasattr(strategies, "get") else None
        next_steps.append({
            "kp_id": step.kp_id,
            "name": getattr(kp, "name", "") or step.kp_id,
            "cluster": getattr(kp, "cluster", "") or "",
            "mastery": scoped.mastery.get(step.kp_id, 0.0),
            "target_mastery": step.target_mastery,
            "strategy_id": step.strategy_id,
            "strategy_name": getattr(strategy, "name", "") or step.strategy_id,
            "rationale": step.rationale,
            "item_ids": recs.get(step.kp_id, []),
        })

    kp_rows = []
    for kp_id in sorted(touched, key=lambda k: (scoped.mastery.get(k, 1.0), k)):
        kp = graph.get(kp_id)
        hit, tried = stats.get(kp_id, (0, 0))
        kp_rows.append({
            "kp_id": kp_id,
            "name": getattr(kp, "name", "") or kp_id,
            "cluster": getattr(kp, "cluster", "") or "",
            "mastery": profile.mastery.get(kp_id, 0.0),
            "evidence": profile.evidence.get(kp_id, 0),
            "hit": hit,
            "tried": tried,
        })

    name_by_id = {r["kp_id"]: r["name"] for r in kp_rows}
    for it in graded["items"]:
        it["kp_names"] = [name_by_id.get(k, k) for k in (it.get("kps") or [])]

    # 待批改分值：solve 等主观题不在本闭环的判分口径内（见模块 docstring），
    # 报告必须显式标出「未计入得分的分值」，否则家长会把 60/100 误读成扣了 40 分。
    pending_points = sum(it["points"] for it in graded["items"] if not it["graded"])

    return {
        "learner_id": session["learner_id"],
        "spec_id": session["spec_id"],
        "title": session["title"],
        "session_id": session["session_id"],
        "score": graded["score"],
        "pending_points": pending_points,
        "total_points": session["paper"]["total_points"],
        "n_objective": sum(1 for it in graded["items"] if it["graded"]),
        "items": graded["items"],
        "kp_rows": kp_rows,
        "clusters": [{"cluster": label, "mastery": value} for label, value in clusters.items()],
        "weak": weak_rows,
        "next_steps": next_steps,
        "reviews": [{"kp_id": r.kp_id, "due": r.due,
                     "interval_days": r.interval_days, "ease": r.ease}
                    for r in reviews],
        "plan_error": plan_error,
        "profile": profile,
    }
