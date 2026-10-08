"""chiopen 确定性收尾：结构化台账 + 盲解台账 -> 题库落库+裁决回填（TC-8 工作流模式）。

与 tools/chiopen_structure_batch.py 的 API 直调模式互补：本工具只做确定性部分——
- 入参：--struct-ledger（工作流子代理产出的结构化分片合并件，records=[{id,
  acceptable_variants?|scoring_points?}]）与 --blind-ledger（盲解分片合并件，
  {"agent_id","answers"}）；
- 落库：结构化字段写入题目（acceptable_variants 或 scoring_points 二选一，
  form 原值不动）；
- 裁决：盲答（归一化）命中标答或任一变体 -> agree，回填 verification
  [原签名, 盲解签名]；否则进 arbitration_queue_chiopen_<batch>.json；
- manifest：verify_manifest_chiopen_<batch>.json（method=keypoint-judge）。
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(0, os.path.join(ROOT, "src"))

from xuexing.itembank_v2 import validate_bank_v2  # noqa: E402

FORM_MAP = {
    "dictation": "fill", "transcription": "fill", "correction": "fill",
    "translation": "fill", "connection": "fill", "applied-writing": "essay",
}
VARIANT_FORMS = ("fill", "dictation", "transcription", "translation")


def normalize(text):
    import re
    t = str(text or "").strip().lower()
    t = re.sub(r"[\s，。；：、！？“”‘’（）《》〈〉—\-·.,;:!?'\"()\[\]{}<>]", "", t)
    table = str.maketrans(
        "０１２３４５６７８９ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ",
        "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")
    return t.translate(table)


def main() -> int:
    ap = argparse.ArgumentParser(description="chiopen 结构化+盲解台账的确定性落库与裁决")
    ap.add_argument("--batch", required=True)
    ap.add_argument("--grade", required=True, type=int)
    ap.add_argument("--struct-ledger", required=True)
    ap.add_argument("--blind-ledger", required=True)
    ap.add_argument("--blind-agent", required=True)
    ap.add_argument("--date", required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--data-dir", default=os.path.join(ROOT, "data"))
    args = ap.parse_args()

    structs = {r["id"]: r for r in json.load(open(args.struct_ledger, encoding="utf-8"))["records"]}
    blind = json.load(open(args.blind_ledger, encoding="utf-8"))["answers"]

    path = os.path.join(args.data_dir, "items", f"chinese_grade{args.grade}_items.json")
    data = json.load(open(path, encoding="utf-8"))
    by_id = {it["id"]: it for it in data["items"]}

    # 幂等护栏：只处理仍为单代理且尚无结构化字段的题（已收口题不重复盖章）
    scope_ids = [i for i, it in by_id.items()
                 if i in structs
                 and len((it.get("verification") or {}).get("agents", [])) == 1
                 and not any(k in it for k in ("acceptable_variants", "scoring_points", "rubric"))]
    skipped = sorted(i for i in structs if i not in scope_ids)
    if skipped:
        print(f"SKIP {len(skipped)} 题（已双代理/已结构化/库外）如: {skipped[:5]}")
    structs = {i: structs[i] for i in scope_ids}
    bad_struct = [i for i in structs if i not in by_id]
    if bad_struct:
        raise SystemExit(f"struct ledger 含库外 id: {bad_struct[:5]}")
    missing_blind = [i for i in structs if i not in blind]
    if missing_blind:
        raise SystemExit(f"blind ledger 缺 {len(missing_blind)} 题盲答: {missing_blind[:5]}")

    agree, open_rows, struct_applied = [], [], []
    for item_id, rec in structs.items():
        it = by_id[item_id]
        variants = rec.get("acceptable_variants")
        points = rec.get("scoring_points")
        catalogued = False
        if isinstance(variants, list) and variants and all(
                isinstance(x, str) and x.strip() for x in variants):
            if normalize(it["answer"]) not in {normalize(x) for x in variants}:
                raise SystemExit(f"{item_id}: acceptable_variants 未包含标答归一化形式")
            if it.get("form") not in VARIANT_FORMS:
                raise SystemExit(f"{item_id}: form={it.get('form')} 不允许 acceptable_variants 口径")
            it["acceptable_variants"] = list(dict.fromkeys(variants))
            catalogued = True
        elif isinstance(points, list) and points and all(
                isinstance(x, dict) and str(x.get("point", "")).strip()
                and isinstance(x.get("score"), (int, float)) and x["score"] > 0 for x in points):
            it["scoring_points"] = [{"point": str(x["point"]), "score": x["score"]}
                                    for x in points]
            catalogued = True
        if not catalogued:
            raise SystemExit(f"{item_id}: 结构化记录非法（variants/points 恰一非空且合法）")
        struct_applied.append(item_id)
        ans = blind.get(item_id)
        hit = ans is not None and normalize(ans) in {
            normalize(it["answer"]), *(normalize(v) for v in (variants or []))}
        row = {"id": item_id, "form": it.get("form"),
               "bank_answer": it["answer"], "solver_answer": ans,
               "verdict": "agree" if hit else "disagree"}
        (agree if hit else open_rows).append(
            row if hit else dict(row, status="open"))

    if args.apply:
        for row in agree:
            target = by_id[row["id"]]
            target["verification"] = {
                "agents": [target["verification"]["agents"][0], args.blind_agent],
                "answers_agree": True,
            }
        errs = validate_bank_v2(data["items"])
        bad = [e for e in errs if "verification" in e]
        if bad:
            raise SystemExit(f"回填后 v2 校验 verification 类错误: {bad[:5]}")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"APPLIED 结构化 {len(struct_applied)} 题 + 第二代理 {len(agree)} 题 -> {path}")

    vdir = os.path.join(args.data_dir, "verification")
    queue_path = os.path.join(vdir, f"arbitration_queue_chiopen_{args.batch}.json")
    if open_rows:
        with open(queue_path, "w", encoding="utf-8") as f:
            json.dump({"batch": args.batch, "queue": open_rows}, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"QUEUE {queue_path} ({len(open_rows)} open，未回填)")
    manifest = {
        "batch": args.batch, "date": args.date,
        "scope": {"grade": args.grade, "mode": "workflow-subagent-struct+blind"},
        "blind_agent": args.blind_agent,
        "method": "keypoint-judge",
        "counts": {"agree": len(agree), "disagree": len(open_rows),
                   "structured": len(struct_applied)},
        "applied": bool(args.apply),
    }
    mpath = os.path.join(vdir, f"verify_manifest_chiopen_{args.batch}.json")
    with open(mpath, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"MANIFEST {mpath}")
    print(f"AGREE {len(agree)} OPEN {len(open_rows)} STRUCTURED {len(struct_applied)}")
    print("CHIOPEN-APPLY-OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
