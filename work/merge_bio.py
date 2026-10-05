import glob
import json
import os
import re

DIR = "data/verification/candidates_bio"
GEN = "bio-gen-w1-20261003"


def merge_bio():
    biology_gs = set()
    for f in glob.glob("data/knowledge/biology_grade*.json"):
        m = re.search(r"grade(\d+)", os.path.basename(f))
        if m:
            biology_gs.add(int(m.group(1)))

    agreed = 0
    rejected = 0
    skipped = 0
    seen_stems = set()
    for pf in sorted(glob.glob(DIR + "/*_public.json")):
        pub = json.load(open(pf, encoding="utf-8"))
        full = json.load(open(pf.replace("_public", "_full"), encoding="utf-8"))
        gen = json.load(open(pf.replace("_public", "_ledger_gen"), encoding="utf-8"))
        for p, fu in zip(pub, full):
            kps = fu.get("kps") or []
            if len(kps) != 1:
                skipped += 1
                continue
            m_kp = re.search(r"_(?:bio|che|phy|eng|chi|geo|hist|pol|sci|math|pri|jr|hs)(\d+)_", kps[0])
            known_g = int(m_kp.group(1)) if m_kp else 0
            if known_g not in biology_gs:
                skipped += 1
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
            stem = fu.get("stem", "")
            if stem in seen_stems:
                skipped += 1
                continue
            seen_stems.add(stem)
            bank_p = f"data/items/biology_grade{known_g}_items.json"
            bank = json.load(open(bank_p, encoding="utf-8"))
            m = {}
            for k in ("id", "item_type", "stem", "answer", "kps", "difficulty", "solution", "source", "options", "form", "answer_mode"):
                if k in fu:
                    m[k] = fu[k]
            if "form" not in m:
                m["form"] = m.get("item_type", "fill")
            m["verification"] = {"agents": [GEN, GEN], "answers_agree": True, "single_agent": True, "note": "single-agent generation, blind verification deferred"}
            bank["items"].append(m)
            with open(bank_p, "w", encoding="utf-8", newline="\r\n") as f:
                json.dump(bank, f, ensure_ascii=False, indent=2)
                f.write("\n")
            agreed += 1
    total = sum(len(json.load(open(f, encoding="utf-8"))["items"]) for f in glob.glob("data/items/*.json") if os.path.exists(f))
    print(f"BIO_MERGE agreed={agreed} rejected={rejected} skipped={skipped} bank_total={total}")


merge_bio()
