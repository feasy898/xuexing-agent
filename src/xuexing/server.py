"""确定性 REST API：出卷 / 提交作答 / 查画像 / 查计划 / 复习打卡，以及新模块
API（/trace /blueprint /grade /recommend /itembank/v2/validate
/coverage/standard /papers/by-spec）与机构多租户（X-Org-Id 头 + /orgs）；
成品卷渲染（GET /papers/by-spec/{spec_id}/render.html|render.txt）与知识地图
可视化（GET /learners/{id}/knowledge-map.html，自包含 HTML）。

薄胶水层：所有逻辑都在内核模块里，这里只做 HTTP 编解码与会话存储。
领域校验失败（内核 ValueError 族）映射 400，资源不存在映射 404，
请求体形态违规由 pydantic 映射 422；端点不实现任何领域算法。

机构多租户（specs/drafts/multitenant.spec.md §3.6-3.7）：全部有状态端点接受
可选请求头 X-Org-Id（缺省/空串/空白归并 DEFAULT_ORG_ID，见
xuexing.multitenant.resolve_org）；store 与 attempt 计数按 (org, learner)
分域——同一 learner_id 在不同机构下完全隔离；不带该头的请求行为与单租户
时代逐字节一致。无状态端点忽略该头。GET /orgs 只读枚举机构命名空间。

导入约定：绝对导入（from xuexing.xxx import ...）——与重生成注入装载约定一致
（见 specs/drafts/server.spec.md §2），本文件可被
run_contract.py --impl-dir <dir> --modules server 装载。
"""
import os
from datetime import date
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel

from xuexing.agent_shell import MockLLM, attribute_error
from xuexing.blueprint import build_blueprint
from xuexing.diagnosis import aggregate_to_clusters, diagnose
from xuexing.grading import grade_to_response
from xuexing.itembank import ItemBank
from xuexing.itembank_v2 import source_counts, validate_bank_v2, verification_stats
from xuexing.kpgraph import KPGraph, KPGraphError
from xuexing.kpgraph_subject import discover_subjects, load_kpgraph_subject
from xuexing.kmap import build_overview_kmap, build_subject_kmap, render_kmap_html
from xuexing.kt import KTEvent, trace, to_profile
from xuexing.multitenant import AttemptCounter, OrgStore, resolve_org
from xuexing.paper import generate_paper, select_next_item
from xuexing.paper_by_spec import (
    DEFAULT_CURRICULUM_DIR,
    generate_paper_by_spec,
    load_spec_catalog,
    load_stage_bank,
)
from xuexing.paper_render import render_paper_html, render_paper_text
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
    kmap_knowledge_dir: str | None = None,
) -> FastAPI:
    """spec_catalog：卷型库 {spec_id: 卷型 dict}（缺省装 data/curriculum/
    paper_specs.json）；stage_bank_loader：callable(subject, stage) -> ItemBank，
    卷型学段题库注入点（缺省按 data/items 文件装载并进程内缓存）。测试注入
    自闭式夹具用，与 bank/graph/strategies 同一套路。kmap_knowledge_dir：
    知识地图的学科图谱目录（缺省 data/knowledge，按 <subject>_grade<N>.json
    学科级装载 load_kpgraph_subject，进程内缓存）。"""
    app = FastAPI(title="xuexing-agent")
    store = OrgStore()
    misconceptions = misconceptions or []
    attempt_counts = AttemptCounter()
    if spec_catalog is None:
        spec_catalog = load_spec_catalog(
            os.path.join(DEFAULT_CURRICULUM_DIR, "curriculum", "paper_specs.json")
        )
    if stage_bank_loader is None:
        from functools import lru_cache

        @lru_cache(maxsize=None)
        def stage_bank_loader(subject: str, stage: str):  # noqa: F811
            return load_stage_bank(DEFAULT_CURRICULUM_DIR, subject, stage)[0]

    from functools import lru_cache as _lru_cache

    kmap_dir = kmap_knowledge_dir or os.path.join(DEFAULT_CURRICULUM_DIR, "knowledge")

    @_lru_cache(maxsize=None)
    def kmap_subject_graph(subject: str) -> KPGraph:
        """知识地图的学科图谱（进程内缓存；未知学科抛 KPGraphError → 404）。"""
        return load_kpgraph_subject(kmap_dir, subject)

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

    # ---- 知识地图可视化（owner："根据错误就可以绘制知识地图" 的"绘制"字面交付）。
    # 与成品卷渲染同一取舍：交付物是给人看的文档，浏览器直接打开 URL 即得
    # text/html；自包含（内联 CSS/SVG，零外部库/JS）。数据全部来自诊断内核
    # 真实产出：逐 KP mastery/置信度（与 /profile 同一 Profile）、学习路线
    # （与 /plan 同一 build_plan 同一入参）、学科图谱（load_kpgraph_subject）。
    # 画像没有的知识点一律"画像外"灰显，绝不编造；空学习者/无数据学科渲染
    # 诚实空态页。subject 缺省 → 跨学科总览（逐学科汇总）。----

    @app.get("/learners/{learner_id}/knowledge-map.html")
    def knowledge_map_html(learner_id: str, subject: str = "",
                           x_org_id: str | None = Header(default=None, alias="X-Org-Id")):
        org = resolve_org(x_org_id)
        entry = store.get(org, learner_id)
        if not entry or "profile" not in entry:
            raise HTTPException(404, "learner not found")
        profile = entry["profile"]
        if subject:
            try:
                subject_graph = kmap_subject_graph(subject)
            except KPGraphError as e:  # 未知学科（目录下无该学科年级文件）
                raise HTTPException(404, str(e))
            data = build_subject_kmap(profile, subject_graph, strategies,
                                      bank, date.today(), subject=subject)
        else:
            data = build_overview_kmap(profile, discover_subjects(kmap_dir),
                                       kmap_subject_graph)
        return HTMLResponse(render_kmap_html(data))

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
