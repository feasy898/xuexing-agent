"""dv2 仲裁队列第三模型族盲判（签署测试卡 TC-7 流程 (5)）。

对 arbitration_queue_dv2_<batch>.json 中 status=open 的条目，由与生成方、
盲解方都不同的第三模型族逐条盲判：只见题面 + 两份答案（盲解答案 A / 库内
标答 B），输出终判。沿用 30bdcf0 先例：终判 ∈ format_diff / wrong_solve /
wrong_key / ambiguous；判定标答错（wrong_key）的题在台账登记后由后续批
修正答案并重新盲验，本工具不直接改题库。

网络纪律与 tools/blind_solve_items.py 相同：--allow-network + 环境注入 key、
端点白名单、配额熔断（同套实现，见 blind_solve_items）。
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

from blind_solve_items import _chat, _check_endpoint, ALLOWED_HOST_SUFFIXES  # noqa: E402


def build_messages(item, row):
    lines = [f"题目（{item.get('form') or item.get('item_type','')}）：", item["stem"].strip()]
    options = item.get("options") or []
    if options:
        lines.append("选项：")
        lines.extend(str(o).strip() for o in options)
    lines.append(f"盲解代理的答案（A）：{row['solver_answer']}")
    lines.append(f"题库现有标答（B）：{row['bank_answer']}")
    lines.append(
        "请独立解题后判断：A、B 哪个是该题的正确答案？"
        "若两者等价只是书写差异，判 equivalent；若题面信息不足以判定，判 ambiguous；"
        "若 B 错 A 对，判 wrong_key；若 A 错 B 对，判 wrong_solve。"
        "最后一行必须是：VERDICT: <format_diff|wrong_key|wrong_solve|equivalent|ambiguous>"
    )
    return [
        {"role": "system", "content": "你是独立仲裁评判代理。先自行解题，再比较两份答案，只输出结论与一行理由。"},
        {"role": "user", "content": "\n".join(lines)},
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description="dv2 仲裁队列盲判（第三模型族）")
    ap.add_argument("--queue", required=True)
    ap.add_argument("--subject", required=True)
    ap.add_argument("--grade", required=True, type=int)
    ap.add_argument("--model", required=True)
    ap.add_argument("--judge-agent", required=True)
    ap.add_argument("--data-dir", default=os.path.join(ROOT, "data"))
    ap.add_argument("--allow-network", action="store_true")
    args = ap.parse_args()
    if not args.allow_network:
        raise SystemExit("拒绝运行：本工具会真实调用 LLM API，必须显式加 --allow-network")
    api_key = os.environ.get("LLM_API_KEY") or os.environ.get("STEPFUN_API_KEY") or ""
    base_url = os.environ.get("LLM_BASE_URL", "")
    if not api_key or not base_url:
        raise SystemExit("拒绝运行：环境未注入 LLM_API_KEY / LLM_BASE_URL")
    host = base_url.split("/")[2]
    if not any(host == s or host.endswith("." + s) for s in ALLOWED_HOST_SUFFIXES):
        raise SystemExit(f"端点 {host} 不在白名单")

    with open(args.queue, encoding="utf-8") as f:
        queue = json.load(f)
    items_path = os.path.join(args.data_dir, "items", f"{args.subject}_grade{args.grade}_items.json")
    with open(items_path, encoding="utf-8") as f:
        items = {it["id"]: it for it in json.load(f)["items"]}

    judged = kept = 0
    for row in queue["queue"]:
        if row.get("status") != "open":
            continue
        item = items.get(row["id"])
        if item is None:
            print(f"SKIP {row['id']}: 题库中找不到")
            continue
        content = _chat(base_url, api_key, args.model, build_messages(item, row))
        verdict = "unparsed"
        for line in reversed((content or "").splitlines()):
            if line.strip().upper().startswith("VERDICT:"):
                verdict = line.split(":", 1)[1].strip().strip("`")
                break
        row["judge_agent"] = args.judge_agent
        row["judge_model"] = args.model
        row["judge_verdict"] = verdict if verdict in (
            "format_diff", "wrong_key", "wrong_solve", "equivalent", "ambiguous") else "unparsed"
        row["judge_reason"] = (content or "").strip().splitlines()[0][:200] if content else ""
        if row["judge_verdict"] in ("format_diff", "wrong_solve", "equivalent"):
            row["status"] = "resolved"
            row["final_verdict"] = row["judge_verdict"]
            row["disposition"] = "保留库内标答" if row["judge_verdict"] != "equivalent" else "两答案等价，保留库内写法"
            kept += 1
        judged += 1
        print(f"JUDGED {row['id']}: {row['judge_verdict']}")

    with open(args.queue, "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"JUDGED_TOTAL {judged} RESOLVED_KEEP {kept}")
    wrong_key = [r["id"] for r in queue["queue"] if r.get("judge_verdict") == "wrong_key"]
    if wrong_key:
        print(f"WRONG_KEY_PENDING_FIX {wrong_key}（标答错：台账留痕，后续批修正答案后重新盲验）")
    print("ARBITRATION-OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
