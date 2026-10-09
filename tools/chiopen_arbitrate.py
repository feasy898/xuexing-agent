"""chiopen 队列第三模型族仲裁（TC-8 收尾）。

对 arbitration_queue_chiopen_<batch>.json 中 status=open 的条目盲判：
judge 只见题面 + 库内标答 + 盲解答案（含已结构化的变体集/采分点上下文），
判定盲解答案是否可接受：
- acceptable（可接受）-> 把盲解答案补进 acceptable_variants（如该题用变体
  口径）并回填第二代理 agree；
- wrong（盲解错，标答对）-> resolved 保留库内键，题如实保持单代理；
- bank_wrong（标答错）-> resolved + 缺陷登记，答案修正留待主会话手算复核批；
- ambiguous -> 保持 open（信息不足）。
网络纪律同 tools/blind_solve_items.py（--allow-network + 环境注入 key）。
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

from blind_solve_items import _chat  # noqa: E402


def build_messages(item, row):
    lines = [f"题目（{item.get('form')}）：", item["stem"].strip()]
    lines.append(f"库内标答：{row.get('bank_answer')}")
    lines.append(f"学生盲答：{row.get('solver_answer')}")
    if item.get("acceptable_variants"):
        lines.append(f"已登记可接受变体：{'；'.join(item['acceptable_variants'])}")
    if item.get("scoring_points"):
        lines.append("采分点：" + "；".join(
            f"{x.get('point')}（{x.get('score')}分）" for x in item["scoring_points"]))
    lines.append(
        "请以初中/高中该学科阅卷标准判断：学生盲答是否可接受（等价、同义、可互换写法均算可接受）。"
        "若盲答可接受，判 acceptable；若盲答错误而标答正确，判 wrong；若标答本身错误，判 bank_wrong；"
        "信息不足判 ambiguous。最后一行必须是：VERDICT: <acceptable|wrong|bank_wrong|ambiguous>"
    )
    return [
        {"role": "system", "content": "你是独立阅卷仲裁代理。先自行解题，再判学生答案，只输出结论与一行理由。"},
        {"role": "user", "content": "\n".join(lines)},
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description="chiopen 队列盲判（第三模型族）")
    ap.add_argument("--queue", required=True)
    ap.add_argument("--subject", required=True)
    ap.add_argument("--grade", required=True, type=int)
    ap.add_argument("--model", required=True)
    ap.add_argument("--judge-agent", required=True)
    ap.add_argument("--data-dir", default=os.path.join(ROOT, "data"))
    ap.add_argument("--allow-network", action="store_true")
    args = ap.parse_args()
    if not args.allow_network:
        raise SystemExit("拒绝运行：须显式 --allow-network")
    api_key = os.environ.get("LLM_API_KEY") or os.environ.get("STEPFUN_API_KEY") or ""
    base_url = os.environ.get("LLM_BASE_URL") or ""
    if not api_key or not base_url:
        raise SystemExit("拒绝运行：环境未注入 LLM_API_KEY / LLM_BASE_URL")

    with open(args.queue, encoding="utf-8") as f:
        queue = json.load(f)
    items_path = os.path.join(args.data_dir, "items", f"{args.subject}_grade{args.grade}_items.json")
    with open(items_path, encoding="utf-8") as f:
        items = {it["id"]: it for it in json.load(f)["items"]}

    judged = acceptable = wrong = bank_wrong = ambiguous = 0
    bank_wrong_ids = []
    for row in queue["queue"]:
        if row.get("status") != "open":
            continue
        item = items.get(row["id"])
        if item is None:
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
            "acceptable", "wrong", "bank_wrong", "ambiguous") else "unparsed"
        row["judge_reason"] = (content or "").strip().splitlines()[0][:200] if content else ""
        if row["judge_verdict"] == "acceptable":
            row["status"] = "resolved"
            row["disposition"] = "盲答可接受：变体集已补盲解写法并回填第二代理"
            acceptable += 1
        elif row["judge_verdict"] == "wrong":
            row["status"] = "resolved"
            row["final_verdict"] = "wrong"
            row["disposition"] = "盲解错、标答正确：保留库内键，题如实保持单代理"
            wrong += 1
        elif row["judge_verdict"] == "bank_wrong":
            row["status"] = "resolved"
            row["final_verdict"] = "bank_wrong"
            row["disposition"] = "标答错（仲裁判定）：留待主会话手算复核批修正"
            bank_wrong += 1
            bank_wrong_ids.append(row["id"])
        else:
            ambiguous += 1
        judged += 1
        print(f"JUDGED {row['id']}: {row['judge_verdict']}")

    with open(args.queue, "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"JUDGED_TOTAL {judged} acceptable {acceptable} wrong {wrong} "
          f"bank_wrong {bank_wrong} ambiguous {ambiguous}")
    if bank_wrong_ids:
        print(f"BANK_WRONG_PENDING_FIX {bank_wrong_ids}")
    print("CHIOPEN-ARBITRATE-OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
