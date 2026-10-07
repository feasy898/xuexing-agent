"""静态卷包导出 CLI（签署测试卡 TC-4，2026-10-08）。

用法:
  python tools/export_static_paper.py --spec-id spec_phy_jr_final \
      [--seed 42] [--out-dir out/static_paper/spec_phy_jr_final_seed42] \
      [--data-dir data]

输出目录六个文件（学生卷 html/txt、教师卷、题号-KP 对照与纸面自诊地图、
OMR 答题卡、manifest）。确定性：同 (spec_id, seed) 重跑逐字节一致；
out/ 已被 gitignore，不会误入库。

退出码: 0=成功；2=用法/卷型错误；1=构建失败（fail-closed，不产残卷）。
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

try:  # Windows 控制台中文输出保护
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

from xuexing.paper_by_spec import (  # noqa: E402
    PaperBySpecError,
    generate_paper_by_spec,
    load_spec_catalog,
    load_stage_bank,
)
from xuexing.paper_spec import PaperSpecError  # noqa: E402
from xuexing.static_paper import (  # noqa: E402
    CONTENT_FILES,
    StaticPaperError,
    build_bundle,
)


def load_item_records(data_dir, subject, stage_grades):
    """学段内各年级题库原始 dict -> {item_id: record}（verification 判定用）。"""
    records = {}
    for grade in stage_grades:
        path = os.path.join(data_dir, "items", f"{subject}_grade{grade}_items.json")
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            for it in json.load(f)["items"]:
                records[it["id"]] = it
    return records


def load_kp_index(data_dir, subject, stage_grades):
    """学段内各年级知识文件 -> {kp_id: {name, cluster}}（kp_map 用）。"""
    index = {}
    for grade in stage_grades:
        path = os.path.join(data_dir, "knowledge", f"{subject}_grade{grade}.json")
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            for kp in json.load(f)["knowledge_points"]:
                index[kp["id"]] = {
                    "name": str(kp.get("name", "")),
                    "cluster": str(kp.get("cluster", "")),
                }
    return index


def load_profile(data_dir):
    path = os.path.join(data_dir, "curriculum", "cold_start_profile_v0.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    ap = argparse.ArgumentParser(description="静态卷包导出（零网络、确定性）")
    ap.add_argument("--spec-id", required=True)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out-dir", default="")
    ap.add_argument("--data-dir", default=os.path.join(ROOT, "data"))
    args = ap.parse_args()

    catalog_path = os.path.join(args.data_dir, "curriculum", "paper_specs.json")
    catalog = load_spec_catalog(catalog_path)
    raw = catalog.get(args.spec_id)
    if raw is None:
        print(f"SPEC-NOT-FOUND {args.spec_id}（共 {len(catalog)} 套卷型）")
        return 2

    bank, grades = load_stage_bank(args.data_dir, raw["subject"], raw["stage"])
    paper = generate_paper_by_spec(bank, raw, seed=args.seed, spec_id=args.spec_id)
    paper["paper_id"] = f"{args.spec_id}_seed{args.seed}"
    paper["stage_grades"] = list(grades)

    records = load_item_records(args.data_dir, raw["subject"], grades)
    kp_index = load_kp_index(args.data_dir, raw["subject"], grades)
    profile = load_profile(args.data_dir)
    bundle = build_bundle(paper, bank, records, kp_index, profile)

    out_dir = args.out_dir or os.path.join(
        ROOT, "out", "static_paper", f"{args.spec_id}_seed{args.seed}"
    )
    os.makedirs(out_dir, exist_ok=True)
    for name in CONTENT_FILES + ("manifest.json",):
        with open(os.path.join(out_dir, name), "w", encoding="utf-8", newline="") as f:
            f.write(bundle[name])

    m = bundle["manifest"]
    print(f"SPEC {m['spec_id']} SEED {m['seed']}")
    print(f"PROFILE_VERSION {m['profile_version']}")
    print(f"ITEMS {len(m['items'])} DUAL {sum(1 for i in m['items'] if i['verification']=='dual')} SINGLE {sum(1 for i in m['items'] if i['verification']=='single')}")
    print(f"MAX_BAND_DEVIATION {m['difficulty']['max_deviation']} THRESHOLD {m['difficulty']['threshold']}")
    print(f"RELEASABLE {str(m['releasable']).lower()} REASON {m['releasable_reason']}")
    print(f"OUT_DIR {out_dir}")
    print("STATIC-PAPER-EXPORT-OK")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (PaperBySpecError, PaperSpecError, StaticPaperError) as e:
        print(f"EXPORT-FAILED {e}")
        sys.exit(1)
