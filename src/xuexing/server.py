"""确定性 REST API：出卷 / 提交作答 / 查画像 / 查计划 / 复习打卡，以及新模块
API（/trace /blueprint /grade /recommend/itembank/v2/validate
/coverage/standard /papers/by-spec）、学生作答闭环（/exam/*）与机构多租户
（X-Org-Id 头 + /orgs）。

薄胶水层：所有逻辑都在内核模块里，这里只做 HTTP 编解码与会话存储。
领域校验失败（内核 ValueError 族）映射 400，资源不存在映射 404，
请求体形态违规由 pydantic 映射 422；端点不实现任何领域算法。

机构多租户（specs/drafts/multitenant.spec.md §3.6-3.7）：全部有状态端点接受
可选请求头 X-Org-Id（缺省/空串/空白归并 DEFAULT_ORG_ID，见
xuexing.multitenant.resolve_org）；store 与 attempt 计数按 (org, learner)
分域——同一 learner_id 在不同机构下完全隔离；不带该头的请求行为与单租户
时代逐字节一致。无状态端点忽略该头。GET /orgs 只读枚举机构命名空间。

学生作答闭环（/exam/*，见 xuexing.exam 模块 docstring）：开卷 GET
/exam/{spec_id}/start?learner_id=X&seed=.. → 会话 + 可作答卷 HTML；提交 POST
/exam/{session_id}/submit（表单或 JSON）→ 判分（grading 内核）+ 画像
（diagnosis 内核）落进同一个 OrgStore（与 POST /learners/{id}/responses 同
落点）→ 303 跳报告页；报告 GET /exam/{session_id}/report.html（route+recommend
内核给学习建议）。表单解析走 urllib.parse（零新依赖，不装 python-multipart）。

导入约定：绝对导入（from xuexing.xxx import ...）——与重生成注入装载约定一致
（见 specs/drafts/server.spec.md §2），本文件可被
run_contract.py --impl-dir <dir> --modules server 装载。
"""
import json
import os
import re
import secrets
import time
from datetime import date, datetime, timezone
from typing import Any
from urllib.parse import parse_qsl

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from pydantic import BaseModel

from xuexing.agent_shell import MockLLM, attribute_error
from xuexing.blueprint import build_blueprint
from xuexing.diagnosis import aggregate_to_clusters, diagnose
from xuexing.exam import (
    ExamError,
    ExamStore,
    build_report,
    grade_submission,
    render_report_html,
)
from xuexing.grading import grade_to_response
from xuexing.itembank import ItemBank
from xuexing.itembank_v2 import source_counts, validate_bank_v2, verification_stats
from xuexing.kpgraph import KPGraph
from xuexing.kpgraph_subject import load_kpgraph_subject
from xuexing.kt import KTEvent, trace, to_profile
from xuexing.multitenant import AttemptCounter, OrgStore, resolve_org
from xuexing.paper import generate_paper, select_next_item
from xuexing.paper_by_spec import (
    DEFAULT_CURRICULUM_DIR,
    generate_paper_by_spec,
    load_spec_catalog,
    load_stage_bank,
)
from xuexing.paper_render import (
    render_exam_sheet_html,
    render_paper_html,
    render_paper_text,
)
from xuexing.pedagogy import StrategyLibrary
from xuexing.recommend import (
    attach_recommendations,
    recommend_for_kp,
    recommend_for_profile,
)
from xuexing.route import build_plan
from xuexing.scheduler import ReviewLog, schedule
from xuexing.standard_coverage import check_coverage_dicts
from xuexing.types import Misconception, Response, to_dict


class BlueprintIn(BaseModel):
    blueprint: dict[str, int]
    seed: int = 42
    title: str = "诊断卷"
    difficulty_target: float = 0.5


class ResponseIn(BaseModel):
    item_id: str
    correct: bool
    learner_answer: str | None = None


class SubmitIn(BaseModel):
    responses: list[ResponseIn]


class ReviewIn(BaseModel):
    rating: int
    days_since_last: int = 0


# ---- 新模块 API 请求体（specs/drafts/server.spec.md §3）----

class KTEventIn(BaseModel):
    item_id: str
    correct: bool
    day: float


class TraceIn(BaseModel):
    events: list[KTEventIn]
    learner_id: str = ""
    prior: float = 0.5
    half_life_days: float = 7.0


class BlueprintReq(BaseModel):
    targets: list[str]
    budget: int
    ratios: dict[str, float] | None = None


class PaperBySpecIn(BaseModel):
    spec_id: str
    seed: int = 42
    difficulty_target: float = 0.5
    # 个性化选题尚未启用：当前仅随卷面回显（家长端/学校端预留字段）
    learner_id: str | None = None


class GradeAnswerIn(BaseModel):
    item_id: str
    learner_answer: str | None = None


class GradeIn(BaseModel):
    item_id: str | None = None
    learner_answer: str | None = None
    answers: list[GradeAnswerIn] | None = None


class RecommendIn(BaseModel):
    learner_id: str = ""
    kp_id: str = ""
    mastery_threshold: float = 0.65
    limit: int | None = None
    attach: bool = False


class ItemsV2In(BaseModel):
    # 元素刻意为任意 JSON 值：itembank_v2 校验器是全函数，
    # "非 dict → item is not a dict" 的语义要能经 HTTP 观察。
    items: list[Any]


class CoverageIn(BaseModel):
    kp_dicts: list[dict]
    topics: dict


def create_app(
    bank: ItemBank,
    graph: KPGraph,
    strategies: StrategyLibrary,
    misconceptions: list[Misconception] | None = None,
    spec_catalog: dict[str, dict] | None = None,
    stage_bank_loader=None,
    subject_graph_loader=None,
    exam_store: ExamStore | None = None,
) -> FastAPI:
    """spec_catalog：卷型库 {spec_id: 卷型 dict}（缺省装 data/curriculum/
    paper_specs.json）；stage_bank_loader：callable(subject, stage) -> ItemBank，
    卷型学段题库注入点（缺省按 data/items 文件装载并进程内缓存）。测试注入
    自闭式夹具用，与 bank/graph/strategies 同一套路。

    subject_graph_loader：callable(subject) -> KPGraph，作答闭环的学科级知识图
    （缺省按 data/knowledge/{subject}_grade*.json 合并装载并进程内缓存，见
    xuexing.kpgraph_subject.load_kpgraph_subject）——一次作答会话的诊断/路线
    必须用它，否则跨年级/跨学科卷的知识点在应用级 graph 里查不到。

    exam_store：/exam/* 的开卷会话登记处（缺省 ExamStore()，TTL 2 小时）。
    注入点只为测试（构造 TTL=0 的过期会话）；生产路径用缺省。"""
    app = FastAPI(title="xuexing-agent")
    store = OrgStore()
    misconceptions = misconceptions or []
    attempt_counts = AttemptCounter()
    exams = exam_store if exam_store is not None else ExamStore()
    if spec_catalog is None:
        spec_catalog = load_spec_catalog(
            os.path.join(DEFAULT_CURRICULUM_DIR, "curriculum", "paper_specs.json")
        )
    if stage_bank_loader is None:
        from functools import lru_cache

        @lru_cache(maxsize=None)
        def stage_bank_loader(subject: str, stage: str):  # noqa: F811
            return load_stage_bank(DEFAULT_CURRICULUM_DIR, subject, stage)[0]
    if subject_graph_loader is None:
        from functools import lru_cache

        @lru_cache(maxsize=None)
        def subject_graph_loader(subject: str) -> KPGraph:  # noqa: F811
            return load_kpgraph_subject(
                os.path.join(DEFAULT_CURRICULUM_DIR, "knowledge"), subject)

    @app.post("/papers/diagnostic")
    def make_paper(body: BlueprintIn):
        try:
            paper = generate_paper(
                bank, graph, body.blueprint, body.seed, body.title, body.difficulty_target
            )
        except ValueError as e:
            raise HTTPException(400, str(e))
        return to_dict(paper)

    def _paper_by_spec_or_error(spec_id: str, seed: int,
                                difficulty_target: float) -> dict:
        """spec_id -> 卷面结构 dict。spec 不在卷型库 → 404；卷型内部不一致/
        同型题不足/学段无题库 → 400（fail-closed：不降级凑题）。POST 出卷与
        GET 渲染共用同一条装订路径，保证「结构卷」与「成品卷」永远同源。"""
        raw_spec = spec_catalog.get(spec_id)
        if raw_spec is None:
            raise HTTPException(404, f"paper spec not found: {spec_id}")
        try:
            stage_bank = stage_bank_loader(raw_spec["subject"], raw_spec["stage"])
            return generate_paper_by_spec(
                stage_bank, raw_spec, seed=seed,
                difficulty_target=difficulty_target, spec_id=spec_id,
            )
        except ValueError as e:  # PaperSpecError / PaperBySpecError 均为 ValueError 子类
            raise HTTPException(400, str(e))

    @app.post("/papers/by-spec")
    def paper_by_spec(body: PaperBySpecIn):
        """卷型库驱动的出卷：按卷型学段/题型/分值约束从对应学段题库选题，
        装订大题-小题层级（分值合计==卷型总分由 paper_spec V8 保证）。
        spec_id 不存在 → 404；卷型内部不一致/同型题不足/学段无题库 → 400
        （fail-closed：不降级凑题）。逻辑全在 xuexing.paper_by_spec。"""
        paper = _paper_by_spec_or_error(body.spec_id, body.seed, body.difficulty_target)
        return {"learner_id": body.learner_id, **paper}

    # ---- 成品卷渲染（家长/学校可打印）。走独立 GET 而非塞进 POST 响应：
    # 交付物是给人打印的文档，浏览器/学校系统直接打开 URL 即得 text/html，
    # 零客户端胶水；by-spec 出卷对 (spec_id, seed, difficulty_target) 确定性，
    # GET 幂等/可缓存语义诚实；机器客户端的结构 JSON 保持精瘦。纯文本备用走
    # 姊妹路径 render.txt（同一内核同一次装订，不产生第二条出卷路径）。 ----

    @app.get("/papers/by-spec/{spec_id}/render.html")
    def paper_by_spec_render_html(spec_id: str, seed: int = 42,
                                  difficulty_target: float = 0.5):
        """成品卷 HTML（自包含：内联 CSS、A4 打印分页、页脚页码）。与 POST
        /papers/by-spec 同 seed 同 difficulty_target 时装订出同一份卷。"""
        paper = _paper_by_spec_or_error(spec_id, seed, difficulty_target)
        stage_bank = stage_bank_loader(
            spec_catalog[spec_id]["subject"], spec_catalog[spec_id]["stage"])
        try:
            html_doc = render_paper_html(paper, stage_bank)
        except ValueError as e:  # PaperRenderError：结构/题库侧 fail-closed
            raise HTTPException(400, str(e))
        return HTMLResponse(html_doc)

    @app.get("/papers/by-spec/{spec_id}/render.txt")
    def paper_by_spec_render_text(spec_id: str, seed: int = 42,
                                  difficulty_target: float = 0.5):
        """成品卷纯文本简版（HTML 不可用时的备用，同一内核渲染）。"""
        paper = _paper_by_spec_or_error(spec_id, seed, difficulty_target)
        stage_bank = stage_bank_loader(
            spec_catalog[spec_id]["subject"], spec_catalog[spec_id]["stage"])
        try:
            text_doc = render_paper_text(paper, stage_bank)
        except ValueError as e:  # PaperRenderError：结构/题库侧 fail-closed
            raise HTTPException(400, str(e))
        return PlainTextResponse(text_doc)

    # ---- 学生作答闭环（/exam/*）。见 xuexing.exam 模块 docstring 的口径声明：
    # 本段只做 HTTP 编解码 + 会话存取，判分/诊断/计划/推荐全部委托既有内核。 ----

    _ITEM_FIELD_RE = re.compile(r"^item_(\d+)$")

    def _exam_session_or_error(session_id: str) -> dict:
        """会话 id -> 会话。未知 404、过期 410、已提交再提交 409（状态机见
        xuexing.exam.ExamStore）。"""
        session, expired = exams.state_of(session_id, time.time())
        if session is None:
            raise HTTPException(404, f"exam session not found: {session_id}")
        if expired:
            raise HTTPException(410, f"exam session expired: {session_id}")
        if session["state"] != "started":
            raise HTTPException(409, f"exam session already submitted: {session_id}")
        return session

    def _exam_material(session: dict):
        """会话 -> (题库, 学科图)。取的是**该卷型学科**的题库与知识图，与
        start 时刻装订的 paper 同源（卷面已保证题在库）。"""
        raw_spec = spec_catalog[session["spec_id"]]
        stage_bank = stage_bank_loader(raw_spec["subject"], raw_spec["stage"])
        try:
            subject_graph = subject_graph_loader(raw_spec["subject"])
        except ValueError as e:  # KPGraphError：无该学科知识点文件 → 如实报缺
            raise HTTPException(400, f"no knowledge graph for subject "
                                     f"{raw_spec['subject']!r}: {e}")
        return stage_bank, subject_graph

    def _answers_from_form(raw: str, paper: dict) -> dict:
        """application/x-www-form-urlencoded 正文 -> {question_no: 文本}。

        零新依赖：urllib.parse.parse_qsl 手工解析（不引 python-multipart）。
        复选（mcq_multi 同 name 多值）用「、」归并——与 grading._split_multi
        的分隔符一致。题号不在本卷 -> 400（形态违规，不静默丢弃）。
        """
        out: dict = {}
        for key, value in parse_qsl(raw, keep_blank_values=True):
            m = _ITEM_FIELD_RE.match(key)
            if m is None:
                raise HTTPException(400, f"unexpected form field: {key!r}")
            no = int(m.group(1))
            out[no] = f"{out[no]}、{value}" if no in out else value
        known = {q["question_no"] for s in paper["sections"] for q in s["questions"]}
        unknown = sorted(set(out) - known)
        if unknown:
            raise HTTPException(400, f"form field item numbers not in paper: {unknown}")
        return out

    def _answers_from_json(body: dict, paper: dict) -> dict:
        """JSON {answers: {...}} -> {question_no: 文本}。键接受 3 或 "3"；
        值接受 str 或 list[str]（多选归并，同表单）。缺 answers 键 -> 400。"""
        raw = body.get("answers")
        if not isinstance(raw, dict):
            raise HTTPException(400, "provide answers: {question_no: str}")
        out: dict = {}
        for key, value in raw.items():
            try:
                no = int(key)
            except (TypeError, ValueError):
                raise HTTPException(400, f"answer key must be a question number, got {key!r}")
            if isinstance(value, list):
                if not all(isinstance(v, str) for v in value):
                    raise HTTPException(400, f"answer for {no} must be str or list[str]")
                out[no] = "、".join(value)
            elif isinstance(value, str) or value is None:
                out[no] = value
            else:
                raise HTTPException(400, f"answer for {no} must be str, list[str] or null")
        known = {q["question_no"] for s in paper["sections"] for q in s["questions"]}
        unknown = sorted(set(out) - known)
        if unknown:
            raise HTTPException(400, f"answer question numbers not in paper: {unknown}")
        return out

    @app.get("/exam/{spec_id}/start")
    def exam_start(spec_id: str, learner_id: str, seed: int = 42,
                   difficulty_target: float = 0.5,
                   x_org_id: str | None = Header(default=None, alias="X-Org-Id")):
        """开卷：按卷型装订一份卷 -> 登记会话 -> 返回可作答卷 HTML（学生直接答题）。

        答案在 session_id 里（一次一卷，GET 幂等语义不成立——每次调用是一次新的
        开卷，与 /papers/by-spec 的确定性出卷不冲突：同 spec/seed 的**卷面**相同，
        但会话是新的）。learner_id 缺省 400（必填，无默认学号）。
        """
        org = resolve_org(x_org_id)
        if not isinstance(learner_id, str) or not learner_id.strip():
            raise HTTPException(400, "learner_id is required")
        paper = _paper_by_spec_or_error(spec_id, seed, difficulty_target)
        raw_spec = spec_catalog[spec_id]
        try:
            subject_graph = subject_graph_loader(raw_spec["subject"])
        except ValueError as e:  # KPGraphError：学科无知识点文件
            raise HTTPException(400, f"no knowledge graph for subject "
                                     f"{raw_spec['subject']!r}: {e}")
        session = {
            "session_id": secrets.token_hex(8),
            "org_id": org,
            "learner_id": learner_id.strip(),
            "spec_id": spec_id,
            "seed": seed,
            "difficulty_target": difficulty_target,
            "subject": raw_spec["subject"],
            "paper": paper,
            "state": "started",
            "created_at": time.time(),
            "graded": None,
            "report": None,
        }
        exams.open(org, session)
        try:
            sheet = render_exam_sheet_html(paper, _exam_material(session)[0],
                                          session["session_id"], learner_id.strip())
        except ValueError as e:  # PaperRenderError：结构/题库侧 fail-closed
            raise HTTPException(400, str(e))
        return HTMLResponse(sheet)

    @app.post("/exam/{session_id}/submit")
    async def exam_submit(session_id: str, request: Request):
        """交卷：表单（原生 <form>）或 JSON 均可 -> 判分 -> 画像落 store -> 303
        跳报告页（学生视角是浏览器跳转；机器客户端跟 303 拿 Location）。

        落点与 POST /learners/{id}/responses 同一个 OrgStore entry
        （responses 追加 + profile 覆盖），因此 GET /profile 与 /plan 对
        作答环产出的画像同样可见。**机构取自会话而非请求头**——原生 <form>
        发不了 X-Org-Id，机构在开卷时已记入会话（xuexing.exam docstring 第 3 条），
        故本端点不读该头。
        """
        session = _exam_session_or_error(session_id)
        org = session["org_id"]
        content_type = (request.headers.get("content-type") or "").split(";")[0].strip()
        raw = (await request.body()).decode("utf-8")
        if content_type == "application/json":
            try:
                body = json.loads(raw) if raw else {}
            except json.JSONDecodeError as e:
                raise HTTPException(400, f"invalid JSON body: {e}")
            if not isinstance(body, dict):
                raise HTTPException(400, "JSON body must be an object")
            answers = _answers_from_json(body, session["paper"])
        else:
            answers = _answers_from_form(raw, session["paper"])

        stage_bank, subject_graph = _exam_material(session)
        try:
            graded = grade_submission(session["paper"], stage_bank, answers)
        except ExamError as e:  # 作答值形态违规（含题库缺题）
            raise HTTPException(400, str(e))

        entry = store.entry(org, session["learner_id"])
        entry["responses"].extend(
            {"item_id": r.item_id, "correct": r.correct,
             "learner_answer": r.learner_answer} for r in graded["responses"])
        prev_profile = entry.get("profile")
        report, new_profile = build_report(
            session, graded, prev_profile, stage_bank, subject_graph, strategies,
            misconceptions, date.today(),
            datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
        if new_profile is not None:  # 无客观题证据 -> 既有画像原样保留，不覆盖
            entry["profile"] = new_profile
        submitted = dict(session)
        submitted["state"] = "submitted"
        submitted["graded"] = graded
        submitted["report"] = report
        exams.replace(submitted)
        return RedirectResponse(f"/exam/{session_id}/report.html", status_code=303)

    @app.get("/exam/{session_id}/report.html")
    def exam_report(session_id: str):
        """报告页：逐题对错 + 知识点掌握更新 + 知识地图 + 薄弱点与下一步建议
        （自包含 HTML，家长可读，无 JS/外链）。未交卷 409——先 POST submit。
        报告只读已提交的会话快照，不读 store、也不读机构头（会话即能力）。"""
        session, expired = exams.state_of(session_id, time.time())
        if session is None:
            raise HTTPException(404, f"exam session not found: {session_id}")
        if expired:
            raise HTTPException(410, f"exam session expired: {session_id}")
        if session["state"] != "submitted" or session.get("report") is None:
            raise HTTPException(409, f"exam session not submitted: {session_id}")
        return HTMLResponse(render_report_html(session["report"]))

    @app.post("/learners/{learner_id}/responses")
    def submit(learner_id: str, body: SubmitIn,
               x_org_id: str | None = Header(default=None, alias="X-Org-Id")):
        org = resolve_org(x_org_id)
        responses = [
            Response(item_id=r.item_id, correct=r.correct, learner_answer=r.learner_answer)
            for r in body.responses
        ]
        profile = diagnose(responses, bank, graph, learner_id=learner_id)
        entry = store.entry(org, learner_id)
        entry["responses"].extend(body.responses)
        entry["profile"] = profile
        clusters = aggregate_to_clusters(profile, graph)
        return {"learner_id": learner_id, "mastery": profile.mastery, "clusters": clusters}

    @app.get("/learners/{learner_id}/profile")
    def get_profile(learner_id: str,
                    x_org_id: str | None = Header(default=None, alias="X-Org-Id")):
        org = resolve_org(x_org_id)
        entry = store.get(org, learner_id)
        if not entry or "profile" not in entry:
            raise HTTPException(404, "learner not found")
        p = entry["profile"]
        return {
            "learner_id": learner_id,
            "mastery": p.mastery,
            "evidence": p.evidence,
            "updated_at": p.updated_at,
            "confidence": {k: round(p.confidence(k), 4) for k in p.mastery},
        }

    @app.get("/learners/{learner_id}/plan")
    def get_plan(learner_id: str,
                 x_org_id: str | None = Header(default=None, alias="X-Org-Id")):
        org = resolve_org(x_org_id)
        entry = store.get(org, learner_id)
        if not entry or "profile" not in entry:
            raise HTTPException(404, "learner not found")
        plan = build_plan(entry["profile"], bank, graph, strategies, date.today())
        return to_dict(plan)

    @app.get("/learners/{learner_id}/next_item")
    def next_item(learner_id: str, scope: str = "", per_kp_cap: int = 3,
                  x_org_id: str | None = Header(default=None, alias="X-Org-Id")):
        org = resolve_org(x_org_id)
        entry = store.get(org, learner_id)
        if not entry or "profile" not in entry:
            raise HTTPException(404, "learner not found")
        scope_set = set(scope.split(",")) if scope else {kp.id for kp in graph.kps()}
        counts = attempt_counts.counts(org, learner_id)
        administered = entry.setdefault("administered", [])
        item_id = select_next_item(bank, entry["profile"], administered, scope_set, counts, per_kp_cap)
        if item_id is None:
            return {"item_id": None, "reason": "exhausted"}
        entry["administered"].append(item_id)
        primary = bank.get(item_id).kps[0]
        attempt_counts.bump(org, learner_id, primary)
        return {"item_id": item_id}

    @app.post("/learners/{learner_id}/reviews")
    def review(learner_id: str, body: ReviewIn,
               x_org_id: str | None = Header(default=None, alias="X-Org-Id")):
        if body.rating not in (0, 1, 2, 3):
            raise HTTPException(400, "rating must be 0-3")
        org = resolve_org(x_org_id)
        entry = store.entry(org, learner_id)
        entry["history"].append(body.rating)
        e = schedule(learner_id, [ReviewLog(rating=body.rating, days_since_last=body.days_since_last)], date.today())
        return to_dict(e)

    @app.get("/orgs")
    def list_orgs():
        # 只读枚举（multitenant 规格 §3.7 / I9）：org 升序、learner 升序
        return {"orgs": [
            {"org_id": org, "learner_ids": store.learner_ids(org)}
            for org in store.org_ids()
        ]}

    @app.post("/attribute")
    def attribute(item_id: str, learner_answer: str):
        item = bank.get(item_id)
        if item is None:
            raise HTTPException(404, "item not found")
        mc = attribute_error(item, learner_answer, misconceptions, MockLLM())
        return {"misconception_id": mc}

    # ---- 新模块 API（specs/drafts/server.spec.md §3.1-§3.6）----

    @app.post("/trace")
    def kt_trace(body: TraceIn,
                 x_org_id: str | None = Header(default=None, alias="X-Org-Id")):
        events = [KTEvent(item_id=e.item_id, correct=e.correct, day=e.day)
                  for e in body.events]
        try:
            snapshots = trace(events, bank, graph,
                              prior=body.prior, half_life_days=body.half_life_days)
        except ValueError as e:
            raise HTTPException(400, str(e))
        saved = False
        if body.learner_id:
            if not snapshots:  # 无快照可存
                raise HTTPException(400, "cannot save profile: trace has no snapshots")
            store.set_profile(resolve_org(x_org_id), body.learner_id,
                              to_profile(snapshots[-1], body.learner_id))
            saved = True
        return {
            "learner_id": body.learner_id or None,
            "profile_saved": saved,
            "snapshots": [
                {"day": s.day, "item_id": s.item_id, "correct": s.correct,
                 "mastery": s.mastery, "evidence": s.evidence}
                for s in snapshots
            ],
        }

    @app.post("/blueprint")
    def make_blueprint(body: BlueprintReq):
        try:
            bp = build_blueprint(body.targets, body.budget, graph, body.ratios)
        except ValueError as e:
            raise HTTPException(400, str(e))
        return {
            "targets": bp.targets,
            "budget": bp.budget,
            "ratios": bp.ratios,
            "allocation": bp.allocation,
            "dimension_totals": bp.dimension_totals,
            "counts": bp.counts(),
            "per_dimension": [
                {"dimension": dim, "counts": sub, "difficulty_target": dt}
                for dim, sub, dt in bp.per_dimension()
            ],
        }

    @app.post("/grade")
    def grade_answers(body: GradeIn):
        if body.answers is not None:  # 批量优先（I5）；原子：先验存在性再判分（I4）
            items = []
            for a in body.answers:
                item = bank.get(a.item_id)
                if item is None:
                    raise HTTPException(404, f"item not found: {a.item_id}")
                items.append(item)
            results = []
            for item, a in zip(items, body.answers):
                try:
                    resp = grade_to_response(item, a.learner_answer)
                except ValueError as e:
                    raise HTTPException(400, str(e))
                results.append(to_dict(resp))
            return {"mode": "batch", "n": len(results), "results": results}
        if body.item_id is None:
            raise HTTPException(400, "provide item_id or answers")
        item = bank.get(body.item_id)
        if item is None:
            raise HTTPException(404, f"item not found: {body.item_id}")
        try:
            resp = grade_to_response(item, body.learner_answer)
        except ValueError as e:
            raise HTTPException(400, str(e))
        return to_dict(resp)

    @app.post("/recommend")
    def recommend(body: RecommendIn,
                  x_org_id: str | None = Header(default=None, alias="X-Org-Id")):
        try:
            if body.kp_id:  # kp 模式优先（I5）
                ids = recommend_for_kp(body.kp_id, bank, misconceptions, body.limit)
                return {"mode": "kp", "kp_id": body.kp_id, "item_ids": ids}
            if body.learner_id:
                entry = store.get(resolve_org(x_org_id), body.learner_id)
                if not entry or "profile" not in entry:
                    raise HTTPException(404, "learner not found")
                profile = entry["profile"]
                if body.attach:
                    plan = build_plan(profile, bank, graph, strategies, date.today())
                    attached = attach_recommendations(plan, bank, misconceptions, body.limit)
                    return {"mode": "plan", "plan": to_dict(attached)}
                recs = recommend_for_profile(profile, bank, misconceptions,
                                             mastery_threshold=body.mastery_threshold,
                                             limit=body.limit)
                return {"mode": "profile", "recommendations": to_dict(recs)}
        except ValueError as e:
            raise HTTPException(400, str(e))
        raise HTTPException(400, "provide kp_id or learner_id")

    @app.post("/itembank/v2/validate")
    def item_v2_validate(body: ItemsV2In):
        # 校验器是全函数：任意输入不抛异常，恒 200（I2/I7 只读）
        errors = validate_bank_v2(body.items)
        total, verified = verification_stats(body.items)
        return {
            "valid": not errors,
            "errors": errors,
            "counts": source_counts(body.items),
            "total": total,
            "verified": verified,
        }

    @app.post("/coverage/standard")
    def coverage_standard(body: CoverageIn):
        try:
            report = check_coverage_dicts(body.kp_dicts, body.topics)
        except ValueError as e:
            raise HTTPException(400, str(e))
        return {
            "coverage_rate": report.coverage_rate,
            "is_complete": report.is_complete(),
            "uncovered_topic_ids": list(report.uncovered_topic_ids),
            "unmatched_kp_ids": list(report.unmatched_kp_ids),
            "matched_kp_ids": list(report.matched_kp_ids),
            "covered_topic_ids": list(report.covered_topic_ids),
            "matches": [
                {"kp_id": m.kp_id, "topic_ids": list(m.topic_ids)}
                for m in report.matches
            ],
        }

    return app
