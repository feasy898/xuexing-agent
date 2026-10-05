# -*- coding: utf-8 -*-
"""Build sci_prim batch (小学科学 1-6 年级 · 教科版2017) from hand-authored data modules.

Data module contract:
    ITEMS = [ (kp_id, item_type, form, difficulty, stem,
               options|None, answer, solution, observe_guide|None), ... ]

Outputs (same order in public & full):
  sci_prim_public.json   -> no answer / no solution / no observe_guide
  sci_prim_full.json     -> with answer / solution / observe_guide
  sci_prim_ledger_gen.json
"""
import importlib
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, REPO)

DATA_FILES = ["s_g1", "s_g2", "s_g3a", "s_g3b", "s_g4a", "s_g4b",
              "s_g5a", "s_g5b", "s_g5c", "s_g6a", "s_g6b", "s_g6c"]
TAG = "sci_prim"
LETTERS = "ABCDEFGH"

# difficulty band by grade band (ask requirement)
DIFF_BAND = {1: (0.20, 0.50), 2: (0.20, 0.50),
             3: (0.30, 0.60), 4: (0.30, 0.60),
             5: (0.40, 0.70), 6: (0.40, 0.70)}
ITEM_TYPES = ("choice", "fill", "solve", "observe")


def load_registry():
    reg = {}
    for g in (1, 2, 3, 4, 5, 6):
        p = os.path.join(REPO, "data", "knowledge", "science_grade%d.json" % g)
        d = json.load(open(p, encoding="utf-8"))
        for k in d["knowledge_points"]:
            reg[k["id"]] = k
    return reg


def main():
    reg = load_registry()
    rows = []
    for name in DATA_FILES:
        mod = importlib.import_module(name)
        for it in mod.ITEMS:
            rows.append((name, it))

    errors = []
    if len(rows) < 2:
        print("FATAL: no items", file=sys.stderr)
        return 1

    public, full = [], []
    ids = set()
    kp_counter = Counter()
    n = 0
    for src, it in rows:
        kp, item_type, form, diff, stem, options, answer, solution, guide = it
        n += 1
        iid = "%s_%04d" % (TAG, n)
        if iid in ids:
            errors.append("dup id %s" % iid)
        ids.add(iid)
        if kp not in reg:
            errors.append("%s: unknown kp %s" % (iid, kp))
            kp_counter[kp] += 1
            continue
        kp_counter[kp] += 1
        grade = reg[kp]["grade"]
        lo, hi = DIFF_BAND[grade]
        if item_type not in ITEM_TYPES:
            errors.append("%s: bad item_type %s" % (iid, item_type))
        if not (lo <= diff <= hi):
            errors.append("%s: difficulty %.2f outside grade-%d band [%.2f,%.2f]"
                          % (iid, diff, grade, lo, hi))
        if not stem or len(stem) < 8:
            errors.append("%s: stem too short" % iid)
        if grade <= 2 and item_type == "choice":
            errors.append("%s: grade-%d must not use choice (教基厅函〔2021〕34号)" % (iid, grade))
        if item_type == "choice":
            if not options or len(options) != 4:
                errors.append("%s: choice needs exactly 4 options, got %s"
                              % (iid, options and len(options)))
            else:
                for j, o in enumerate(options):
                    if not o.startswith(LETTERS[j]):
                        errors.append("%s: option %d label problem %r" % (iid, j, o[:10]))
                if answer not in LETTERS[:4]:
                    errors.append("%s: answer %r not in ABCD" % (iid, answer))
        else:
            if options:
                errors.append("%s: non-choice must not have options" % iid)
        if item_type == "observe":
            if not guide or len(guide) < 10:
                errors.append("%s: observe item needs observe_guide" % iid)
        else:
            if guide:
                errors.append("%s: non-observe must not have observe_guide" % iid)
        if not answer or not str(answer).strip():
            errors.append("%s: empty answer" % iid)
        if not solution or len(str(solution)) < 8:
            errors.append("%s: solution too short" % iid)

        pub = {
            "id": iid,
            "item_type": item_type,
            "form": form,
            "stem": stem,
            "kps": [kp],
            "difficulty": diff,
        }
        if options:
            pub["options"] = options
        pub["source"] = "llm_generated"
        public.append(pub)

        f = dict(pub)
        if guide:
            f["observe_guide"] = guide
        f["answer"] = answer
        f["solution"] = solution
        full.append(f)

    ledger = {
        "agent_id": "sci-gen-w1-20261003",
        "solver": "MiniMax-M3",
        "method": "generator self-answer",
        "answers": {it["id"]: it["answer"] for it in full},
    }

    # ---- coverage report ----
    covered = len(kp_counter)
    print("items=%d  kps_covered=%d / %d" % (len(full), covered, len(reg)))
    print("items per kp distribution:", dict(Counter(kp_counter.values())))
    print("by grade:", dict(sorted(Counter((reg[k]["grade"], c) for k, c in kp_counter.items()).items())))
    miss = [k for k in reg if k not in kp_counter]
    if miss:
        print("KPs with 0 items (%d): %s" % (len(miss), miss))
    print("item_type:", dict(Counter(it["item_type"] for it in public)))
    print("form:", dict(Counter(it["form"] for it in public)))
    ds = [it["difficulty"] for it in public]
    print("difficulty: min=%.2f max=%.2f" % (min(ds), max(ds)))

    if errors:
        print("VALIDATION ERRORS (%d):" % len(errors), file=sys.stderr)
        for e in errors[:80]:
            print("  " + e, file=sys.stderr)
        return 2

    for fn, obj in (("sci_prim_public.json", public),
                    ("sci_prim_full.json", full),
                    ("sci_prim_ledger_gen.json", ledger)):
        with open(os.path.join(HERE, fn), "w", encoding="utf-8") as fh:
            json.dump(obj, fh, ensure_ascii=False, indent=1)
        print("wrote", fn, os.path.getsize(os.path.join(HERE, fn)), "bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
