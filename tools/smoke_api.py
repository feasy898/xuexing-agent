"""API 冒烟与起服工具（TASK.md 阶段 P：P-1 起服冒烟 / P-2 runbook 配套）。

为什么需要本工具：src/xuexing/server.py 的 create_app(bank, graph, strategies,
misconceptions=None) 要求注入知识库（题库/图谱/策略/误解库），没有无参工厂——
直接 `uvicorn xuexing.server:create_app --factory` 会报
`create_app() missing 3 required positional arguments`。本工具承担注入：
装载路径与 tests/conftest.py 完全同源（grade7 真实子库）。

用法：
  python tools/smoke_api.py
      离线冒烟（默认）：进程内 httpx ASGITransport 经 AsyncClient 直连
      create_app() 应用（本机 httpx 0.28 的 ASGITransport 仅 async；不占端口、
      零网络、断网可跑），按 docs/runbook.md §4 逐个调用全部 14 个端点 +
      1 项多租户 X-Org-Id 专项，收集状态码与关键响应字段。结尾打印
      SMOKE_OK <n>/<total>（全过，exit 0）或列出失败端点（exit 1）。
      本工具自身不设 XX_MM_SMOKE、不发任何网络请求：/attribute 的 LLM 兜底
      走 MockLLM（server.py:224），多模态模块根本不进 import 图。

  python tools/smoke_api.py --serve [--host 127.0.0.1] [--port 8000]
      注入知识库后真实起服（uvicorn），供 curl 冒烟 / 联调；Ctrl+C 停止。

语义断言钉住 grade7 子库的既有题目（m7_010 标答 "2"、m7_011 标答 "-5"、
m7_013 标答 "-6"，误解 mc_sign_neg 签名含 "5"）；这些题目在未来批次的
注入中被重划时，需同步本工具。
"""
import argparse
import asyncio
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

try:  # Windows 控制台中文输出保护
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

GRAPH_PATH = os.path.join(ROOT, "data", "knowledge", "math_grade7.json")
BANK_PATH = os.path.join(ROOT, "data", "items", "math_grade7_items.json")
STRATEGIES_PATH = os.path.join(ROOT, "data", "pedagogy", "strategies.json")
MISCONCEPTIONS_PATH = os.path.join(ROOT, "data", "misconceptions", "math_misconceptions.json")
CURRICULUM_PATH = os.path.join(ROOT, "data", "curriculum", "math_standard_2022_topics.json")


def load_app():
    """按 tests/conftest.py 同源方式注入知识库并构建 FastAPI 应用。"""
    from xuexing import load_itembank, load_kpgraph, load_strategies
    from xuexing.server import create_app
    from xuexing.types import Misconception

    with open(MISCONCEPTIONS_PATH, encoding="utf-8") as f:
        misconceptions = [Misconception(**mc) for mc in json.load(f)["misconceptions"]]
    return create_app(
        load_itembank(BANK_PATH),
        load_kpgraph(GRAPH_PATH),
        load_strategies(STRATEGIES_PATH),
        misconceptions,
    )


def _load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ---------- 离线冒烟：逐端点检查（顺序 = docs/runbook.md §4 速查表） ----------
# 每项 = 一个端点：断言期望状态码 + 关键响应字段，返回一行「采集到的字段」明细。

def run_smoke() -> int:
    import httpx

    bank_raw = _load_json(BANK_PATH)["items"]
    kps_raw = _load_json(GRAPH_PATH)["knowledge_points"]
    topics = _load_json(CURRICULUM_PATH)
    app = load_app()
    n_kps = len({kp["id"] for kp in kps_raw})

    checks: list[tuple[str, object]] = []

    def check(label):
        def deco(fn):
            checks.append((label, fn))
            return fn
        return deco

    # 1
    @check("POST /papers/diagnostic")
    async def _(c):
        r = await c.post("/papers/diagnostic",
                         json={"blueprint": {"kp_rational_add": 2, "kp_eq_solve": 1},
                               "seed": 42})
        assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"
        paper = r.json()
        assert {"paper_id", "title", "blueprint", "item_ids"} <= set(paper), paper.keys()
        assert len(paper["item_ids"]) == 3, paper["item_ids"]
        return f"200 | item_ids×{len(paper['item_ids'])} title={paper['title']!r}"

    # 2
    @check("POST /learners/smoke-1/responses")
    async def _(c):
        r = await c.post("/learners/smoke-1/responses", json={"responses": [
            {"item_id": "m7_010", "correct": True, "learner_answer": "2"},
            {"item_id": "m7_011", "correct": False, "learner_answer": "3"}]})
        assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"
        out = r.json()
        assert set(out) == {"learner_id", "mastery", "clusters"}, out.keys()
        assert out["learner_id"] == "smoke-1" and "kp_rational_add" in out["mastery"], out
        return f"200 | mastery×{len(out['mastery'])} clusters×{len(out['clusters'])}"

    # 3
    @check("GET /learners/smoke-1/profile")
    async def _(c):
        r = await c.get("/learners/smoke-1/profile")
        assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"
        out = r.json()
        assert {"learner_id", "mastery", "evidence", "updated_at", "confidence"} <= set(out)
        return f"200 | mastery×{len(out['mastery'])} confidence×{len(out['confidence'])}"

    # 4
    @check("GET /learners/smoke-1/plan")
    async def _(c):
        r = await c.get("/learners/smoke-1/plan")
        assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"
        plan = r.json()
        assert plan["learner_id"] == "smoke-1" and len(plan["steps"]) > 0, plan.keys()
        assert isinstance(plan["reviews"], list)
        step = plan["steps"][0]
        assert {"kp_id", "strategy_id", "recommended_item_ids"} <= set(step), step.keys()
        return f"200 | steps×{len(plan['steps'])} reviews×{len(plan['reviews'])} " \
               f"首个策略={plan['steps'][0]['strategy_id']}"

    # 5
    @check("GET /learners/smoke-1/next_item")
    async def _(c):
        r = await c.get("/learners/smoke-1/next_item")
        assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"
        item_id = r.json().get("item_id")
        assert isinstance(item_id, str), r.json()
        return f"200 | item_id={item_id}"

    # 6
    @check("POST /learners/smoke-1/reviews")
    async def _(c):
        r = await c.post("/learners/smoke-1/reviews", json={"rating": 2})
        assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"
        out = r.json()
        assert {"kp_id", "due", "interval_days", "ease"} <= set(out), out.keys()
        bad = await c.post("/learners/smoke-1/reviews", json={"rating": 9})
        assert bad.status_code == 400  # rating 越界按设计 400
        return f"200 | kp_id={out['kp_id']} due={out['due']} interval={out['interval_days']} " \
               f"(rating 9 → 400 按设计；kp_id 即 learner_id，server.py:208)"

    # 7
    @check("GET /orgs")
    async def _(c):
        r = await c.get("/orgs")
        assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"
        orgs = r.json()["orgs"]
        ids = [o["org_id"] for o in orgs]
        assert "default" in ids, ids  # 前面无头请求已建 default 域
        return f"200 | orgs={ids}"

    # 8
    @check("POST /attribute")
    async def _(c):
        r = await c.post("/attribute", params={"item_id": "m7_010", "learner_answer": "5"})
        assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"
        assert r.json() == {"misconception_id": "mc_sign_neg"}, r.json()  # 签名命中，零 LLM
        return "200 | misconception_id=mc_sign_neg（签名命中，MockLLM 路径）"

    # 9
    @check("POST /trace")
    async def _(c):
        r = await c.post("/trace", json={
            "learner_id": "smoke-kt",
            "events": [{"item_id": "m7_010", "correct": True, "day": 0.0},
                       {"item_id": "m7_011", "correct": False, "day": 3.0}]})
        assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"
        out = r.json()
        assert out["profile_saved"] is True and out["learner_id"] == "smoke-kt", out.keys()
        assert len(out["snapshots"]) == 2, out
        snap = out["snapshots"][-1]
        assert {"day", "item_id", "correct", "mastery", "evidence"} <= set(snap)
        return f"200 | profile_saved={out['profile_saved']} snapshots×{len(out['snapshots'])}"

    # 10
    @check("POST /blueprint")
    async def _(c):
        r = await c.post("/blueprint", json={
            "targets": ["kp_rational_add", "kp_eq_solve"], "budget": 3})
        assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"
        out = r.json()
        assert sum(out["counts"].values()) == out["budget"] == 3, out
        assert set(out["dimension_totals"]) == {"记忆", "理解", "应用"}, out
        return f"200 | counts={out['counts']} dimensions={sorted(out['dimension_totals'])}"

    # 11
    @check("POST /grade")
    async def _(c):
        r = await c.post("/grade", json={"item_id": "m7_010", "learner_answer": "2"})
        assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"
        one = r.json()
        assert set(one) == {"item_id", "correct", "learner_answer", "response_ms"}, one.keys()
        assert one["correct"] is True
        r = await c.post("/grade", json={"answers": [
            {"item_id": "m7_010", "learner_answer": "2"},
            {"item_id": "m7_011", "learner_answer": "-5"},
            {"item_id": "m7_013", "learner_answer": "6"}]})
        assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"
        batch = r.json()
        assert batch["mode"] == "batch" and batch["n"] == 3, batch
        assert [x["correct"] for x in batch["results"]] == [True, True, False], batch
        ghost = await c.post("/grade", json={"item_id": "ghost", "learner_answer": "x"})
        assert ghost.status_code == 404  # 未知题按设计 404
        return f"200 | 原子 correct=True；批量 n=3 判定=[True,True,False]（ghost → 404 按设计）"

    # 12
    @check("POST /recommend")
    async def _(c):
        r = await c.post("/recommend", json={"kp_id": "kp_rational_add"})
        assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"
        kp_mode = r.json()
        assert kp_mode["mode"] == "kp" and kp_mode["item_ids"], kp_mode.keys()
        r = await c.post("/recommend", json={"learner_id": "smoke-1"})
        assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"
        prof = r.json()
        assert prof["mode"] == "profile", prof.keys()
        assert prof["recommendations"][0]["kp_id"] == "kp_rational_add", prof
        return f"200 | kp 模式 item_ids×{len(kp_mode['item_ids'])}；画像最弱 kp=" \
               f"{prof['recommendations'][0]['kp_id']}"

    # 13
    @check("POST /itembank/v2/validate")
    async def _(c):
        r = await c.post("/itembank/v2/validate", json={"items": bank_raw})
        assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"
        out = r.json()
        assert out["valid"] is True and out["errors"] == [], out["errors"][:5]
        assert out["total"] == len(bank_raw), out
        return f"200 | valid=True total={out['total']} counts={out['counts']}"

    # 14
    @check("POST /coverage/standard")
    async def _(c):
        r = await c.post("/coverage/standard", json={"kp_dicts": kps_raw, "topics": topics})
        assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"
        out = r.json()
        assert out["unmatched_kp_ids"] == [], out["unmatched_kp_ids"]
        assert out["coverage_rate"] > 0 and out["is_complete"] is False, out
        return f"200 | coverage_rate={out['coverage_rate']:.3f} " \
               f"未覆盖条目×{len(out['uncovered_topic_ids'])}"

    # 15 —— 多租户专项（runbook §3.4：X-Org-Id 分域隔离 + /orgs 可见）
    @check("X-Org-Id 多租户隔离（trace/orgs × org-a）")
    async def _(c):
        r = await c.post("/trace", json={
            "learner_id": "smoke-mt",
            "events": [{"item_id": "m7_010", "correct": True, "day": 0.0}]},
            headers={"X-Org-Id": "org-a"})
        assert r.status_code == 200 and r.json()["profile_saved"] is True, r.text[:200]
        assert (await c.get("/learners/smoke-mt/profile")).status_code == 404  # 缺省域看不到
        ok = await c.get("/learners/smoke-mt/profile", headers={"X-Org-Id": "org-a"})
        assert ok.status_code == 200
        orgs = (await c.get("/orgs")).json()["orgs"]
        hit = [o for o in orgs if o["org_id"] == "org-a"]
        assert hit and "smoke-mt" in hit[0]["learner_ids"], orgs
        return "200/404 | org-a 与 default 隔离；/orgs 可见 org-a"

    async def _drive():
        transport = httpx.ASGITransport(app=app)  # 进程内直连 ASGI，不占端口
        async with httpx.AsyncClient(transport=transport, base_url="http://smoke") as client:
            passed, failures = 0, []
            for i, (label, fn) in enumerate(checks, 1):
                try:
                    detail = await fn(client)
                    passed += 1
                    print(f"  [{i:02d}/{len(checks)}] {label.ljust(36, ' ')} PASS  {detail}")
                except AssertionError as e:
                    failures.append(label)
                    print(f"  [{i:02d}/{len(checks)}] {label.ljust(36, ' ')} FAIL  {e}")
                except Exception as e:  # noqa: BLE001
                    failures.append(label)
                    print(f"  [{i:02d}/{len(checks)}] {label.ljust(36, ' ')} FAIL  "
                          f"{type(e).__name__}: {e}")
            return passed, failures

    print(f"离线冒烟（httpx ASGITransport 进程内直连，零网络不占端口）：{len(checks)} 项"
          f"（14 端点 + 1 多租户专项；bank={os.path.basename(BANK_PATH)} "
          f"items={len(bank_raw)} kps={n_kps}）")
    passed, failures = asyncio.run(_drive())
    if failures:
        print(f"SMOKE_FAIL {passed}/{len(checks)}，失败端点：")
        for label in failures:
            print(f"  - {label}")
        return 1
    print(f"SMOKE_OK {passed}/{len(checks)}")
    return 0


# ---------- 真实起服（P-1：注入知识库 → uvicorn → curl → 停止） ----------

def serve(host: str, port: int) -> int:
    import uvicorn

    bank_raw = _load_json(BANK_PATH)["items"]
    kps_raw = _load_json(GRAPH_PATH)["knowledge_points"]
    app = load_app()
    print(f"知识库注入完成：items={len(bank_raw)} kps={len({kp['id'] for kp in kps_raw})} "
          f"bank={os.path.relpath(BANK_PATH, ROOT)}")
    print(f"起服：http://{host}:{port}  （Ctrl+C 停止；只读冒烟见 docs/runbook.md §6）")
    uvicorn.run(app, host=host, port=port, log_level="info")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="xuexing-agent API 冒烟与起服")
    ap.add_argument("--serve", action="store_true", help="注入知识库并真实起服（uvicorn）")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args()
    if args.serve:
        return serve(args.host, args.port)
    return run_smoke()


if __name__ == "__main__":
    sys.exit(main())
