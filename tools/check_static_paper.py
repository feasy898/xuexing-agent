"""静态卷包校验门（签署测试卡 TC-4，2026-10-08）。

对卷型库全部卷型逐套判定（无参运行，exit 0 = 门通过）：
- OK —— 出卷成功、卷包构建两遍逐字节一致（确定性）、verify_bundle 九点
  全过（学生卷红线零违规、Σ分值==总分、题号五处一致、kp_map 对应、
  零外链零回传元素、固定文案逐字在位且「真题」不出文案外、单代理标签
  与 releasable 联动、manifest 哈希自洽、画像版本一致）；
- SKIP —— 出卷被拒且属已知 fail-closed 类（同 check_paper_spec 分类），
  如实打印原因；
- UNEXPECTED —— 其他异常，任何一条判门失败（exit 1）。

门通过条件（exit 0）：全部卷型判定完毕、UNEXPECTED==0、OK>=3，末行
「STATIC-PAPER-CHECK-OK」。纯校验不落盘；落盘样本用 export_static_paper。
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
    StaticPaperError,
    build_bundle,
    verify_bundle,
)

EXPECTED_REASON_PREFIXES = (
    "not enough eligible items",
    "has no bank form mapping",
    "no item files for subject",
    "unknown stage",
    "Σcount×points_each",
)

BUNDLE_FILES_OK_THRESHOLD = 3


def _build(data_dir, raw, spec_id, seed):
    bank, grades = load_stage_bank(data_dir, raw["subject"], raw["stage"])
    paper = generate_paper_by_spec(bank, raw, seed=seed, spec_id=spec_id)
    paper["paper_id"] = f"{spec_id}_seed{seed}"
    paper["stage_grades"] = list(grades)
    records = {}
    for grade in grades:
        path = os.path.join(data_dir, "items", f"{raw['subject']}_grade{grade}_items.json")
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                for it in json.load(f)["items"]:
                    records[it["id"]] = it
    kp_index = {}
    for grade in grades:
        path = os.path.join(data_dir, "knowledge", f"{raw['subject']}_grade{grade}.json")
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                for kp in json.load(f)["knowledge_points"]:
                    kp_index[kp["id"]] = {
                        "name": str(kp.get("name", "")),
                        "cluster": str(kp.get("cluster", "")),
                    }
    with open(os.path.join(data_dir, "curriculum", "cold_start_profile_v0.json"), encoding="utf-8") as f:
        profile = json.load(f)
    bundle = build_bundle(paper, bank, records, kp_index, profile)
    return paper, bank, profile, bundle


def main() -> int:
    ap = argparse.ArgumentParser(description="静态卷包校验门（对全部卷型逐套判定）")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--data-dir", default=os.path.join(ROOT, "data"))
    args = ap.parse_args()
    data_dir = args.data_dir

    catalog = load_spec_catalog(os.path.join(data_dir, "curriculum", "paper_specs.json"))
    ok = fail = skip = unexpected = 0
    releasable_count = 0
    for spec_id in sorted(catalog):
        raw = catalog[spec_id]
        try:
            paper, bank, profile, bundle = _build(data_dir, raw, spec_id, args.seed)
        except (PaperBySpecError, PaperSpecError) as e:
            reason = str(e)
            if any(reason.startswith(p) or p in reason for p in EXPECTED_REASON_PREFIXES):
                skip += 1
                print(f"SKIP {spec_id}: {reason}")
                continue
            unexpected += 1
            print(f"UNEXPECTED {spec_id}: {reason}")
            continue
        except Exception as e:  # noqa: BLE001
            unexpected += 1
            print(f"UNEXPECTED {spec_id}: {type(e).__name__}: {e}")
            continue
        try:
            rebuild = _build(data_dir, raw, spec_id, args.seed)[3]
            if any(bundle[name] != rebuild[name]
                   for name in list(bundle.keys()) if name != "manifest"):
                fail += 1
                print(f"FAIL {spec_id}: 两次构建不逐字节一致（确定性被破坏）")
                continue
            errors = verify_bundle(bundle, paper, bank, profile)
            if errors:
                fail += 1
                print(f"FAIL {spec_id}: {len(errors)} 项违规: " + "; ".join(errors[:3]))
                continue
            m = bundle["manifest"]
            ok += 1
            releasable_count += 1 if m["releasable"] else 0
            print(
                f"OK {spec_id}: items={len(m['items'])} "
                f"dual={sum(1 for i in m['items'] if i['verification']=='dual')} "
                f"max_dev={m['difficulty']['max_deviation']:.3f} "
                f"releasable={str(m['releasable']).lower()}"
            )
        except Exception as e:  # noqa: BLE001
            unexpected += 1
            print(f"UNEXPECTED {spec_id}: {type(e).__name__}: {e}")

    print(f"判定总数={len(catalog)} OK={ok} FAIL={fail} SKIP={skip} UNEXPECTED={unexpected}")
    print(f"RELEASABLE={releasable_count}")
    if unexpected == 0 and fail == 0 and ok >= BUNDLE_FILES_OK_THRESHOLD:
        print("STATIC-PAPER-CHECK-OK（全部卷型判定完毕、零 UNEXPECTED 零 FAIL、可离线分发）")
        return 0
    print("STATIC-PAPER-CHECK-FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(main())
