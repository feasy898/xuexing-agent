"""可发布索引生成工具（签署测试卡 TC-5，2026-10-08）。

对卷型库全部卷型逐套核对「双代理 agree 题存量」，产出
data/releases/static_paper_index_v0.json：
  {"profile_version", "generated_by", "seed",
   "entries":[{spec_id, seed, releasable, shortages:[{section, form, need,
   have_verified}], item_count}]}（21 条，按 spec_id 排序）

releasable=true 当且仅当零缺口（每个大题的双代理 agree 题量都够）。
索引只能由本工具重建（确定性），禁止手改；TC-7/TC-8 每批回填后重跑。
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

from xuexing.cold_start_profile import to_canonical_json  # noqa: E402
from xuexing.paper_by_spec import load_spec_catalog, load_stage_bank  # noqa: E402
from xuexing.static_paper import verified_shortages  # noqa: E402


def build_index(data_dir, seed):
    catalog = load_spec_catalog(os.path.join(data_dir, "curriculum", "paper_specs.json"))
    entries = []
    for spec_id in sorted(catalog):
        raw = catalog[spec_id]
        bank, grades = load_stage_bank(data_dir, raw["subject"], raw["stage"])
        records = {}
        for grade in grades:
            path = os.path.join(data_dir, "items", f"{raw['subject']}_grade{grade}_items.json")
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    for it in json.load(f)["items"]:
                        records[it["id"]] = it
        shortages = verified_shortages(raw["sections"], bank, records)
        entries.append({
            "spec_id": spec_id,
            "seed": seed,
            "releasable": not shortages,
            "shortages": shortages,
            "item_count": sum(sec["count"] for sec in raw["sections"]),
        })
    return {
        "profile_version": "v0",
        "generated_by": "tools/build_static_paper_index.py",
        "seed": seed,
        "entries": entries,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="生成静态卷可发布索引（确定性、可重建）")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--data-dir", default=os.path.join(ROOT, "data"))
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    index = build_index(args.data_dir, args.seed)
    text = to_canonical_json(index)
    out = args.out or os.path.join(args.data_dir, "releases", "static_paper_index_v0.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    releasable = sum(1 for e in index["entries"] if e["releasable"])
    print(f"INDEX {out}")
    print(f"ENTRIES {len(index['entries'])} RELEASABLE {releasable}")
    for e in index["entries"]:
        if e["releasable"]:
            print(f"  RELEASABLE {e['spec_id']} items={e['item_count']}")
    print("RELEASE-INDEX-OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
