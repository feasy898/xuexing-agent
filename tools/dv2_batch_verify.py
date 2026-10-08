"""批次双代理复验（签署测试卡 TC-7/TC-8 数据侧裁决工具）。

对单个年级题库文件内的单代理题，用 dual_verify 内核裁决：
- 代理通道：generator=key（其独立解题产物即库内标答，历史通道语义）+
  solver=ledger:<盲解台账>（tools/blind_solve_items.py 产出）；
- agree -> 回填 verification {"agents": [generator, solver], "answers_agree":
  true}（backfill_item 原子替换，single_agent 标记与延期 note 随之消失）；
- disagree -> data/verification/arbitration_queue_dv2_<batch>.json（status
  open，附盲解答案与归因），**不回填**；
- 每批写 data/verification/verify_manifest_dv2_<batch>.json：batch /
  generator_model_family / generator_family_evidence（仓内证据路径）/
  solver_model_family / judge_model_family / counts / disagree_rate / applied；
- --sync-known-issue-count：回填后全库重扫 verification.agents==1 的 unique
  id 数，原子更新 tests/data/test_itembank_v2_data.py 的 KNOWN_ISSUE_COUNT。

单批 disagree_rate > 0.15 时拒绝 --apply（TC-7 红线：停批归因，不硬磨）。
"""
import argparse
import json
import os
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from xuexing.dual_verify import (  # noqa: E402
    backfill_item,
    verify_item,
)
from xuexing.itembank_v2 import validate_bank_v2  # noqa: E402

KNOWN_FILE = os.path.join(ROOT, "tests", "data", "test_itembank_v2_data.py")


def load_scope(data_dir, subject, grade, forms, itypes):
    path = os.path.join(data_dir, "items", f"{subject}_grade{grade}_items.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    scope = [
        it for it in data["items"]
        if len((it.get("verification") or {}).get("agents", [])) == 1
        and (not forms or it.get("form") in forms)
        and (not itypes or it.get("item_type") in itypes)
    ]
    return path, data, scope


def main() -> int:
    ap = argparse.ArgumentParser(description="批次双代理复验（agree 回填 / disagree 队列 / dv2 manifest）")
    ap.add_argument("--batch", required=True, help="批次名，如 math_grade11_dv2a")
    ap.add_argument("--subject", required=True)
    ap.add_argument("--grade", required=True, type=int)
    ap.add_argument("--forms", default="", help="逗号分隔 form 白名单（须与盲解范围一致）")
    ap.add_argument("--item-types", default="", help="逗号分隔 item_type 白名单（须与盲解范围一致）")
    ap.add_argument("--solver-agent", required=True)
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--generator-model-family", required=True,
                    help="批内主体生成方模型族描述（逐题签名以库内原签名为准）")
    ap.add_argument("--generator-family-evidence", required=True,
                    help="仓内证据路径（相对仓库根），证明生成方模型族")
    ap.add_argument("--solver-model-family", required=True)
    ap.add_argument("--judge-model-family", default="none")
    ap.add_argument("--apply", action="store_true", help="回填 agree（ disagree_rate>0.15 拒绝）")
    ap.add_argument("--sync-known-issue-count", action="store_true")
    ap.add_argument("--data-dir", default=os.path.join(ROOT, "data"))
    ap.add_argument("--date", default=date.today().isoformat())
    args = ap.parse_args()
    forms = {x.strip() for x in args.forms.split(",") if x.strip()}
    itypes = {x.strip() for x in args.item_types.split(",") if x.strip()}

    path, data, scope = load_scope(args.data_dir, args.subject, args.grade, forms, itypes)
    if not scope:
        print("NOTHING-TO-VERIFY（该范围无单代理题）")
        return 0
    with open(args.ledger, encoding="utf-8") as f:
        ledger = json.load(f)
    if ledger.get("agent_id") != args.solver_agent:
        raise SystemExit(f"ledger agent_id {ledger.get('agent_id')!r} != --solver-agent {args.solver_agent!r}")
    answers = ledger.get("answers") or {}
    scope_ids = [it["id"] for it in scope]
    missing = [i for i in scope_ids if i not in answers]
    if missing:
        raise SystemExit(f"ledger 缺 {len(missing)} 题盲解（先补齐再批验），如 {missing[:5]}")

    vdir = os.path.join(args.data_dir, "verification")
    agree, disagree, incomplete = [], [], []
    gen_counter = {}
    for it in scope:
        # 逐题原生归因：第一代理 = 该题既有单代理签名（key 通道语义：其独立
        # 解题产物即库内标答）；绝不跨题共用签名。
        gen0 = it["verification"]["agents"][0]
        gen_counter[gen0] = gen_counter.get(gen0, 0) + 1
        result = verify_item(it, {
            gen0: it["answer"],
            args.solver_agent: answers[it["id"]],
        })
        row = {
            "id": it["id"], "form": it.get("form"),
            "generator_agent": gen0,
            "bank_answer": it["answer"], "solver_answer": answers[it["id"]],
            "verdict": result["verdict"],
        }
        if result["verdict"] == "agree":
            agree.append((it, row))
        elif result["verdict"] == "disagree":
            disagree.append((it, row))
        else:
            incomplete.append((it, row))

    total = len(scope)
    disagree_rate = len(disagree) / total if total else 0.0
    print(f"SCOPE {total} AGREE {len(agree)} DISAGREE {len(disagree)} INCOMPLETE {len(incomplete)} "
          f"DISAGREE_RATE {disagree_rate:.4f}")

    applied = False
    if args.apply:
        if disagree_rate > 0.15:
            print(f"REFUSE-APPLY disagree_rate {disagree_rate:.4f} > 0.15（TC-7 红线：停批归因，不硬磨）")
            return 1
        by_id = {it["id"]: it for it in data["items"]}
        for it, _row in agree:
            by_id[it["id"]] = backfill_item(it, {
                "agents": [it["verification"]["agents"][0], args.solver_agent],
                "answers_agree": True,
            })
        data["items"] = [by_id[orig["id"]] for orig in data["items"]]
        # 全库 v2 校验兜底（回填只动 verification 键）
        errs = validate_bank_v2(data["items"])
        bad = [e for e in errs if "verification" in e]
        if bad:
            raise SystemExit(f"回填后 v2 校验出现 verification 类错误: {bad[:5]}")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        applied = True
        print(f"APPLIED {len(agree)} agree 题已回填 {path}")

    if disagree:
        queue_path = os.path.join(vdir, f"arbitration_queue_dv2_{args.batch}.json")
        queue = {
            "batch": args.batch,
            "queue": [
                dict(row, status="open") for _it, row in disagree
            ],
        }
        with open(queue_path, "w", encoding="utf-8") as f:
            json.dump(queue, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"QUEUE {queue_path} ({len(disagree)} 条 open，未回填)")

    manifest = {
        "batch": args.batch,
        "date": args.date,
        "scope": {"subject": args.subject, "grade": args.grade,
                  "forms": sorted(forms) if forms else "all",
                  "item_types": sorted(itypes) if itypes else "all"},
        "generator_model_family": args.generator_model_family,
        "generator_family_evidence": args.generator_family_evidence,
        "generator_agents": gen_counter,
        "solver_model_family": args.solver_model_family,
        "judge_model_family": args.judge_model_family,
        "solver_agent": args.solver_agent,
        "counts": {"agree": len(agree), "disagree": len(disagree), "incomplete": len(incomplete)},
        "disagree_rate": round(disagree_rate, 4),
        "applied": applied,
    }
    manifest_path = os.path.join(vdir, f"verify_manifest_dv2_{args.batch}.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"MANIFEST {manifest_path}")

    if args.sync_known_issue_count and applied:
        single_total = 0
        items_dir = os.path.join(args.data_dir, "items")
        for name in sorted(os.listdir(items_dir)):
            if not name.endswith("_items.json"):
                continue
            with open(os.path.join(items_dir, name), encoding="utf-8") as f:
                single_total += sum(
                    1 for it in json.load(f)["items"]
                    if len((it.get("verification") or {}).get("agents", [])) == 1
                )
        with open(KNOWN_FILE, encoding="utf-8") as f:
            text = f.read()
        import re
        new_text, n = re.subn(
            r"^KNOWN_ISSUE_COUNT = \d+",
            f"KNOWN_ISSUE_COUNT = {single_total}",
            text, count=1, flags=re.M,
        )
        if n != 1:
            raise SystemExit("KNOWN_ISSUE_COUNT 常量定位失败")
        marker = (f"# 2026-10-08 dv2 批 {args.batch}：agree {len(agree)} 回填后全库复扫。\n")
        if marker not in new_text:
            new_text = new_text.replace(
                f"KNOWN_ISSUE_COUNT = {single_total}",
                f"KNOWN_ISSUE_COUNT = {single_total}\n{marker}", 1,
            )
        with open(KNOWN_FILE, "w", encoding="utf-8") as f:
            f.write(new_text)
        print(f"KNOWN_ISSUE_COUNT -> {single_total}")
    print("DV2-BATCH-OK" if (applied or not args.apply) else "DV2-BATCH-DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
