"""gapfill 步骤 1：数学题库 form 缺失键迁移。

背景（2026-10-06 补缺口径）：paper_specs 卷型门对「有具体 form 的题」要求命中
FORM_ALIASES 等价类，form 缺失才按 item_type 粗类回退（paper_by_spec.py 顶注）。
但 math 全库 1487 题没有 form 键，itembank_from_dict 把缺省 form 读成
"choice"（specs/frozen/itembank.spec.md §R9b-m 冻结契约），导致：
1) item_type=fill 的 763 题 form 被读成 "choice"——既进不了填空大题（fill=0
   的直接原因），反而会冒充选择题进选择大题（题型保真漏洞）；
2) item_type=solve 的题同理进不了解答等价类。

本脚本不动物擎（冻结契约不动），只做数据侧标注：缺 form 的题按 item_type
补 form 键——choice→"choice"（与现 loader 缺省逐字一致，行为零变化）、
fill→"fill"、solve→"solve"（均为 FORM_ALIASES 已收录写法）。已带非空 form
的题一字不动。

用法：python work/gapfill/migrate_math_form.py [--dry-run]
"""
import argparse
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FORM_BY_TYPE = {"choice": "choice", "fill": "fill", "solve": "solve"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    total = 0
    for path in sorted(glob.glob(os.path.join(ROOT, "data/items/math_grade*_items.json"))):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        changed = 0
        skipped = 0
        for it in data["items"]:
            if it.get("form"):  # 已有非空 form：一字不动
                skipped += 1
                continue
            form = FORM_BY_TYPE.get(it["item_type"])
            if form is None:
                print(f"  !! {it['id']}: 未知 item_type {it['item_type']!r}，跳过",
                      file=sys.stderr)
                continue
            it["form"] = form
            changed += 1
        if changed and not args.dry_run:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.write("\n")
        print(f"{os.path.basename(path)}: 补 form {changed} 题，已有 form 跳过 {skipped}")
        total += changed
    print(f"TOTAL 补 form {total} 题{'（dry-run 未写盘）' if args.dry_run else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
