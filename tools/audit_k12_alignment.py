"""K12-5 比对审计工具：无真题下的「全课标教材对齐」口径。"""
import json
import glob
import os
import re
from collections import defaultdict, Counter

ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
RES_DIR = os.path.join(ROOT, "docs", "research", "k12")
ITEMS_DIR = os.path.join(ROOT, "data", "items")
KN_DIR = os.path.join(ROOT, "data", "knowledge")
CUR_DIR = os.path.join(ROOT, "data", "curriculum")

SUBJECT_PREFIX = {
    "math": "math", "chi": "chi", "eng": "english", "phy": "physics", "che": "chemistry",
    "bio": "biology", "his": "history", "geo": "geography", "pol": "politics",
    "sci": "science", "p": "math", "m": "math", "h": "math",
}


def subject_of(kp_id):
    m = re.match(r"^kp_([a-z]+)(\d+)", kp_id)
    if not m:
        return "?"
    return SUBJECT_PREFIX.get(m.group(1), m.group(1))


def load_json(path):
    if not os.path.exists(path):
        return None
    return json.load(open(path, encoding="utf-8"))


def all_items():
    items = []
    for f in glob.glob(os.path.join(ITEMS_DIR, "*_grade*.json")):
        for it in load_json(f)["items"]:
            items.append(it)
    return items


def all_kps():
    kps = set()
    for f in glob.glob(os.path.join(KN_DIR, "*_grade*.json")):
        for kp in load_json(f)["knowledge_points"]:
            kps.add(kp["id"])
    return kps


def kp_coverage_by_subject():
    items = all_items()
    cov = defaultdict(Counter)
    for it in items:
        for k in it.get("kps", []):
            cov[subject_of(k)][k] += 1
    return cov


def audit_form_coverage_per_kp(threshold=3):
    cov = kp_coverage_by_subject()
    out = {}
    for subj, cnts in cov.items():
        out[subj] = {
            "total_kp": len(cnts),
            "kp_with_0_items": [k for k, v in cnts.items() if v == 0],
            "kp_with_lt_3_items": [k for k, v in cnts.items() if v < threshold],
            "median_items": sorted(cnts.values())[len(cnts) // 2] if cnts else 0,
        }
    return out


def audit_kp_alignment():
    subjects = set()
    for f in glob.glob(os.path.join(KN_DIR, "*_grade*.json")):
        m = re.search(r"/([a-z]+)_grade", f)
        if m:
            subjects.add(SUBJECT_PREFIX.get(m.group(1), m.group(1)))
    out = {}
    for s in subjects:
        kn = glob.glob(os.path.join(KN_DIR, f"{s}_grade*.json"))
        cur = glob.glob(os.path.join(CUR_DIR, f"{s}_*.json"))
        cur_files = [c for c in cur if "specs" not in c]
        out[s] = {
            "knowledge_files": len(kn),
            "curriculum_files": len(cur_files),
            "has_curriculum": bool(cur_files),
        }
    return out


def main():
    print("=" * 60)
    print("K12-5 比对审计报告（无真题下的「全课标教材对齐」口径）")
    print("=" * 60)
    items = all_items()
    kps = all_kps()
    print(f"\n## 1. 全库规模")
    print(f"题库总量: {len(items)} 题")
    print(f"图谱总量: {len(kps)} KP")

    print("\n## 2. 学科 KP 与课标对齐")
    align = audit_kp_alignment()
    print(f"  {'学科':10s}: KP 文件 / 课标文件")
    for s, info in sorted(align.items()):
        cur_str = "✅" if info["has_curriculum"] else "❌"
        print(f"  {s:10s}: {info['knowledge_files']} / {cur_str} ({info['curriculum_files']})")

    print("\n## 3. 题型覆盖审计（每 KP 题数下限 3）")
    cov = audit_form_coverage_per_kp(threshold=3)
    total_kp = total_lt3 = total_med = 0
    for s, info in sorted(cov.items()):
        total_kp += info["total_kp"]
        total_lt3 += len(info["kp_with_lt_3_items"])
        total_med += info["median_items"]
        rate = len(info["kp_with_lt_3_items"]) / info["total_kp"] if info["total_kp"] else 0
        print(f"  {s:10s}: {info['total_kp']:4d} KP / 0 题 {len(info['kp_with_0_items']):3d} / <3 {len(info['kp_with_lt_3_items']):3d} ({rate*100:5.1f}%) / 中位数 {info['median_items']}")

    overall = (total_kp - total_lt3) / total_kp if total_kp else 0
    print(f"\n## 4. 结论（owner 第 2 问：题型覆盖 ≥98%）")
    print(f"  全库 KP {total_kp} / 题 <3 的 KP {total_lt3} / 覆盖达 {overall*100:.1f}%")
    print(f"  目标 ≥98%；差距 {total_lt3} 道 KP 题（每 KP 需补足 ≥3 题）")

    out_path = os.path.join(ROOT, "docs", "audits", "k12-5_alignment_audit.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(
            {
                "items_total": len(items),
                "kps_total": len(kps),
                "subject_alignment": align,
                "kp_coverage_by_subject": cov,
                "overall_coverage_rate": overall,
                "owner_target": 0.98,
                "gap_kps_under_3": total_lt3,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
        f.write("\n")
    print(f"\n报告已写入 {out_path}")


if __name__ == "__main__":
    main()
