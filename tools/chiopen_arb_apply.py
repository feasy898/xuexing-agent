"""chiopen 仲裁 acceptable 类落库（TC-8 收尾第二步）。

读取 chiopen 仲裁队列中 judge_verdict=acceptable 的行：
- 把盲解写法补进题目 acceptable_variants（去重，标答保留）；
- 回填 verification [原单代理签名, 盲解方签名]（answers_agree=true）；
- 行置 resolved。KNOWN_ISSUE_COUNT 由调用方另行同步（--sync-known）。
"""
import argparse
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from xuexing.itembank_v2 import validate_bank_v2  # noqa: E402

KNOWN_FILE = os.path.join(ROOT, "tests", "data", "test_itembank_v2_data.py")


def main() -> int:
    ap = argparse.ArgumentParser(description="chiopen 仲裁 acceptable 落库")
    ap.add_argument("--queue", required=True)
    ap.add_argument("--subject", required=True)
    ap.add_argument("--grade", required=True, type=int)
    ap.add_argument("--blind-agent", required=True, help="该批盲解方签名（与回填 agents[1] 一致）")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--sync-known-issue-count", action="store_true")
    ap.add_argument("--data-dir", default=os.path.join(ROOT, "data"))
    args = ap.parse_args()

    queue = json.load(open(args.queue, encoding="utf-8"))
    acceptable = [r for r in queue["queue"]
                  if r.get("judge_verdict") == "acceptable" and r.get("status") == "resolved"]
    if not acceptable:
        print("NOTHING-TO-APPLY（无 acceptable 行）")
        return 0

    path = os.path.join(args.data_dir, "items", f"{args.subject}_grade{args.grade}_items.json")
    data = json.load(open(path, encoding="utf-8"))
    by_id = {it["id"]: it for it in data["items"]}

    applied = 0
    for row in acceptable:
        it = by_id.get(row["id"])
        if it is None:
            continue
        ans = (row.get("solver_answer") or "").strip()
        if not ans:
            continue
        variants = it.setdefault("acceptable_variants", [])
        if ans not in variants:
            variants.append(ans)
        it["verification"] = {"agents": [it["verification"]["agents"][0], args.blind_agent],
                              "answers_agree": True}
        applied += 1

    if args.apply and applied:
        errs = [e for e in validate_bank_v2(data["items"]) if "verification" in e]
        if errs:
            raise SystemExit(f"回填后 v2 校验 verification 类错误: {errs[:5]}")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"APPLIED {applied} 题（变体补录 + 第二代理回填）-> {path}")

    if args.sync_known_issue_count and applied:
        single_total = 0
        items_dir = os.path.join(args.data_dir, "items")
        for name in sorted(os.listdir(items_dir)):
            if not name.endswith("_items.json"):
                continue
            with open(os.path.join(items_dir, name), encoding="utf-8") as f:
                single_total += sum(
                    1 for it in json.load(f)["items"]
                    if len((it.get("verification") or {}).get("agents", [])) == 1)
        with open(KNOWN_FILE, encoding="utf-8") as f:
            text = f.read()
        new_text, n = re.subn(r"^KNOWN_ISSUE_COUNT = \d+",
                              f"KNOWN_ISSUE_COUNT = {single_total}",
                              text, count=1, flags=re.M)
        if n != 1:
            raise SystemExit("KNOWN_ISSUE_COUNT 定位失败")
        with open(KNOWN_FILE, "w", encoding="utf-8") as f:
            f.write(new_text)
        print(f"KNOWN_ISSUE_COUNT -> {single_total}")
    print("CHIOPEN-ARB-APPLY-OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
