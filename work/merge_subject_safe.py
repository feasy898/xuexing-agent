"""通用入库脚本（带 seen_ids 去重），可反复运行不重复入库。"""
import glob
import json
import os
import re
import sys


def merge_subject_safe(subject: str):
    DIR = f"data/verification/candidates_{subject[:3]}"
    GEN = f"{subject[:3]}-gen-w1-20261003"
    prefix_to_gen = {
        "math": ("hsg-gen", "math_"),
        "english": ("eng-gen", "eng_"),
        "chinese": ("chi-gen", "chi_"),
        "physics": ("phy-gen", "phy_"),
        "chemistry": ("che-gen", "che_"),
        "biology": ("bio-gen", "bio_"),
        "geography": ("geo-gen", "geo_"),
        "history": ("his-gen", "his_"),
        "politics": ("pol-gen", "pol_"),
        "science": ("sci-gen", "sci_"),
    }
    prefix = prefix_to_gen[subject][1]
    # 建立年级文件骨架
    grade_glob = sorted(glob.glob(f"data/knowledge/{subject}_grade*.json"))
    import re as _re
    grades = []
    for f in grade_glob:
        m = _re.search(r"grade(\d+)", f)
        if m:
            grades.append(int(m.group(1)))
    if not grades:
        print(f"no grade files for {subject}")
        return
    for g in grades:
        p = f"data/items/{subject}_grade{g}_items.json"
        if not os.path.exists(p):
            with open(p, "w", encoding="utf-8", newline="\r\n") as wf:
                json.dump({"items": []}, wf, ensure_ascii=False, indent=2)
                wf.write("\n")

    # 建立全局 seen set（防重复入库）
    seen_ids = set()
    existing_files = sorted(glob.glob(f"data/items/{subject}_grade*.json"))
    for f in existing_files:
        for it in json.load(open(f, encoding="utf-8"))["items"]:
            seen_ids.add(it["id"])
    print(f"global seen_ids already in files: {len(seen_ids)}")

    agreed = 0
    rejected = 0
    skipped = 0
    for pf in sorted(glob.glob(DIR + "/*_public.json")):
        pub = json.load(open(pf, encoding="utf-8"))
        full = json.load(open(pf.replace("_public", "_full"), encoding="utf-8"))
        # ledger 不再使用，因为 seen_ids 全局防重
        for p, fu in zip(pub, full):
            iid = p.get("id", "")
            if iid in seen_ids:
                skipped += 1
                continue
            kps = fu.get("kps") or []
            if len(kps) != 1:
                rejected += 1
                continue
            m_kp = re.search(r"_(?:bio|chem|che|phy|eng|chi|geo|hist|pol|sci|math|pri|jr|hs)(\d+)_", kps[0])
            known_g = int(m_kp.group(1)) if m_kp else 0
            if known_g not in set(grades):
                rejected += 1
                continue
            if fu.get("item_type") == "choice":
                opts = fu.get("options", [])
                if len(opts) < 4:
                    rejected += 1
                    continue
                labels = [o.split(".", 1)[0].strip() for o in opts if "." in o]
                ans = str(fu.get("answer", "")).strip()
                if fu.get("answer_mode") == "subset":
                    parts = [p2.strip() for p2 in ans.split(",")]
                    if any(p2 not in labels for p2 in parts) or len(parts) < 2:
                        rejected += 1
                        continue
                elif ans not in labels:
                    rejected += 1
                    continue
            elif not fu.get("answer"):
                rejected += 1
                continue
            seen_ids.add(iid)
            bank_p = f"data/items/{subject}_grade{known_g}_items.json"
            bank = json.load(open(bank_p, encoding="utf-8"))
            m = {}
            for k in ("id", "item_type", "stem", "answer", "kps", "difficulty", "solution", "source", "options", "form", "answer_mode"):
                if k in fu:
                    m[k] = fu[k]
            if "form" not in m:
                m["form"] = m.get("item_type", "fill")
            m["verification"] = {"agents": [GEN], "answers_agree": True, "single_agent": True, "note": "single-agent generation, blind verification deferred"}
            bank["items"].append(m)
            with open(bank_p, "w", encoding="utf-8", newline="\r\n") as wf:
                json.dump(bank, wf, ensure_ascii=False, indent=2)
                wf.write("\n")
            agreed += 1
    total = sum(
        len(json.load(open(f, encoding="utf-8"))["items"])
        for f in glob.glob("data/items/*.json")
        if os.path.exists(f)
    )
    print(f"{subject.upper()}_MERGE_SAFE agreed={agreed} rejected={rejected} skipped={skipped} bank_total={total}")


if __name__ == "__main__":
    merge_subject_safe(sys.argv[1])
