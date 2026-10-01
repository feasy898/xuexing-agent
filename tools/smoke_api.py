"""API 冒烟与起服工具（TASK.md 阶段 P：P-1 起服冒烟 / P-2 runbook 配套）。

为什么需要本工具：src/xuexing/server.py 的 create_app(bank, graph, strategies,
misconceptions=None) 要求注入知识库（题库/图谱/策略/误解库），没有无参工厂——
直接 `uvicorn xuexing.server:create_app --factory` 会报
`create_app() missing 3 required positional arguments`。本工具承担注入：
装载路径与 tests/conftest.py 完全同源（grade7 真实子库）。

用法：
  python tools/smoke_api.py
      离线冒烟（默认）：进程内 TestClient 走通全部端点族，零网络、断网可跑。
      退出码 0=全部通过；1=有失败（明细打印到 stdout）。

  python tools/smoke_api.py --serve [--host 127.0.0.1] [--port 8000]
      注入知识库后真实起服（uvicorn），供 curl 冒烟 / 联调；Ctrl+C 停止。

语义断言钉住 grade7 子库的既有题目（m7_010 标答 "2"、m7_013 标答 "-6"、
误解 mc_sign_neg 签名含 "5"）；这些题目在未来批次的注入中被重划时，需同步本工具。
"""
import argparse
import json
import os
import sys
import warnings

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


# ---------- 离线冒烟检查（断言口径取自 tests/contract 与 tests/integration） ----------

def run_smoke() -> int:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # 压掉 fastapi.testclient 的 httpx 弃用告警
        from fastapi.testclient import TestClient

    bank_raw = _load_json(BANK_PATH)["items"]
    kps_raw = _load_json(GRAPH_PATH)["knowledge_points"]
    topics = _load_json(CURRICULUM_PATH)
    app = load_app()
    client = TestClient(app)

    checks = []

    def check(name):
        def deco(fn):
            checks.append((name, fn))
            return fn
        return deco

    @check("POST /papers/diagnostic 出卷（item_ids 与蓝图等长）")
    def _(c):
        r = c.post("/papers/diagnostic",
                   json={"blueprint": {"kp_rational_add": 2, "kp_eq_solve": 1}, "seed": 42})
        assert r.status_code == 200, r.text
        paper = r.json()
        assert len(paper["item_ids"]) == 3, paper
        assert {"paper_id", "title", "blueprint", "item_ids"} <= set(paper), paper.keys()

    @check("POST /trace 学习轨迹 → 存画像（profile_saved=True，3 快照）")
    def _(c):
        r = c.post("/trace", json={
            "learner_id": "smoke-1",
            "events": [{"item_id": "m7_010", "correct": True, "day": 0.0},
                       {"item_id": "m7_011", "correct": False, "day": 3.0},
                       {"item_id": "m7_013", "correct": True, "day": 10.0}]})
        assert r.status_code == 200, r.text
        out = r.json()
        assert out["profile_saved"] is True and out["learner_id"] == "smoke-1", out
        assert len(out["snapshots"]) == 3, out

    @check("GET /learners/smoke-1/profile 画像五字段")
    def _(c):
        r = c.get("/learners/smoke-1/profile")
        assert r.status_code == 200, r.text
        assert {"learner_id", "mastery", "evidence", "updated_at", "confidence"} <= set(r.json())

    @check("GET /learners/smoke-1/plan 路线（steps 非空、含 reviews）")
    def _(c):
        r = c.get("/learners/smoke-1/plan")
        assert r.status_code == 200, r.text
        plan = r.json()
        assert plan["learner_id"] == "smoke-1" and len(plan["steps"]) > 0, plan["learner_id"]
        assert isinstance(plan["reviews"], list)

    @check("GET /learners/smoke-1/next_item 自适应选题（item_id 非空）")
    def _(c):
        r = c.get("/learners/smoke-1/next_item")
        assert r.status_code == 200, r.text
        assert isinstance(r.json().get("item_id"), str), r.json()

    @check("POST /learners/smoke-1/reviews 复习打卡（rating 9 → 400）")
    def _(c):
        r = c.post("/learners/smoke-1/reviews", json={"rating": 2})
        assert r.status_code == 200, r.text
        assert {"kp_id", "due", "interval_days", "ease"} <= set(r.json()), r.json().keys()
        assert c.post("/learners/smoke-1/reviews", json={"rating": 9}).status_code == 400

    @check("POST /grade 判分（原子 + 批量 n=3）")
    def _(c):
        r = c.post("/grade", json={"item_id": "m7_010", "learner_answer": "2"})
        assert r.status_code == 200 and r.json()["correct"] is True, r.text
        assert set(r.json()) == {"item_id", "correct", "learner_answer", "response_ms"}
        r = c.post("/grade", json={"answers": [
            {"item_id": "m7_010", "learner_answer": "2"},
            {"item_id": "m7_011", "learner_answer": "-5"},
            {"item_id": "m7_013", "learner_answer": "6"}]})
        assert r.status_code == 200, r.text
        out = r.json()
        assert out["mode"] == "batch" and out["n"] == 3, out
        assert [x["correct"] for x in out["results"]] == [True, True, False], out

    @check("POST /blueprint 蓝图（budget=3 → counts 合计 3）")
    def _(c):
        r = c.post("/blueprint", json={
            "targets": ["kp_rational_add", "kp_eq_solve"], "budget": 3})
        assert r.status_code == 200, r.text
        out = r.json()
        assert sum(out["counts"].values()) == out["budget"] == 3, out
        assert set(out["dimension_totals"]) == {"记忆", "理解", "应用"}, out

    @check("POST /recommend 推荐（kp 模式 + 画像模式）")
    def _(c):
        r = c.post("/recommend", json={"kp_id": "kp_rational_add"})
        assert r.status_code == 200, r.text
        out = r.json()
        assert out["mode"] == "kp" and out["item_ids"], out
        r = c.post("/recommend", json={"learner_id": "smoke-1"})
        assert r.status_code == 200, r.text
        out = r.json()
        assert out["mode"] == "profile" and out["recommendations"][0]["kp_id"] == "kp_rational_add", out

    @check("POST /attribute 错因归因（签名命中 mc_sign_neg，零 LLM）")
    def _(c):
        r = c.post("/attribute", params={"item_id": "m7_010", "learner_answer": "5"})
        assert r.status_code == 200, r.text
        assert r.json() == {"misconception_id": "mc_sign_neg"}, r.json()

    @check("POST /itembank/v2/validate 全库 schema v2（valid=True，total=题数）")
    def _(c):
        r = c.post("/itembank/v2/validate", json={"items": bank_raw})
        assert r.status_code == 200, r.text
        out = r.json()
        assert out["valid"] is True and out["errors"] == [], out["errors"][:5]
        assert out["total"] == len(bank_raw), out

    @check("POST /coverage/standard 课标覆盖（grade7 kps × 课标清单）")
    def _(c):
        r = c.post("/coverage/standard", json={"kp_dicts": kps_raw, "topics": topics})
        assert r.status_code == 200, r.text
        out = r.json()
        assert out["unmatched_kp_ids"] == [], out["unmatched_kp_ids"]
        assert out["coverage_rate"] > 0 and out["is_complete"] is False, out

    @check("多租户 X-Org-Id（org-a 隔离；缺省归并 default；/orgs 可见）")
    def _(c):
        r = c.post("/trace", json={
            "learner_id": "smoke-mt",
            "events": [{"item_id": "m7_010", "correct": True, "day": 0.0}]},
            headers={"X-Org-Id": "org-a"})
        assert r.status_code == 200 and r.json()["profile_saved"] is True, r.text
        assert c.get("/learners/smoke-mt/profile").status_code == 404  # 缺省域看不到
        assert c.get("/learners/smoke-mt/profile",
                     headers={"X-Org-Id": "org-a"}).status_code == 200
        orgs = c.get("/orgs").json()["orgs"]
        assert any(o["org_id"] == "org-a" and "smoke-mt" in o["learner_ids"] for o in orgs), orgs

    print(f"离线冒烟（进程内 TestClient，零网络）：{len(checks)} 项检查")
    failures = []
    for i, (name, fn) in enumerate(checks, 1):
        try:
            fn(client)
            print(f"  [{i}/{len(checks)}] {name} ...... PASS")
        except AssertionError as e:
            failures.append((name, e))
            print(f"  [{i}/{len(checks)}] {name} ...... FAIL: {e}")
        except Exception as e:  # noqa: BLE001
            failures.append((name, e))
            print(f"  [{i}/{len(checks)}] {name} ...... ERROR: {type(e).__name__}: {e}")

    n_kps = len({kp["id"] for kp in kps_raw})
    if failures:
        print(f"SMOKE FAILED: {len(failures)}/{len(checks)} checks failed "
              f"(bank={os.path.basename(BANK_PATH)} items={len(bank_raw)}, kps={n_kps})")
        return 1
    print(f"SMOKE OK: {len(checks)}/{len(checks)} checks passed "
          f"(bank={os.path.basename(BANK_PATH)} items={len(bank_raw)}, kps={n_kps})")
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
