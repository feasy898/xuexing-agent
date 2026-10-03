# -*- coding: utf-8 -*-
"""Build his_hs batch (高中历史 grade10/11/12) from hand-authored data modules.

Data module contract:  DATA_FILES = [name, ...] in order; each module exposes
ITEMS = [ (kp_id, item_type, form, difficulty, stem, options|None, answer, solution), ... ]

Outputs (same order in public & full):
  his_hs_public.json   -> no answer / no solution
  his_hs_full.json     -> with answer / solution
  his_hs_ledger_gen.json
"""
import importlib
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(HERE, "src"))
sys.path.insert(0, REPO)

DATA_FILES = [
    "h_hs10a", "h_hs10b", "h_hs10c", "h_hs10d", "h_hs10e", "h_hs10f",
    "h_hs11a", "h_hs11b", "h_hs11c",
    "h_hs12a", "h_hs12b",
]

LETTERS = "ABCDEFGH"


def load_registry():
    reg = {}
    for g in (10, 11, 12):
        p = os.path.join(REPO, "data", "knowledge", "history_grade%d.json" % g)
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
        kp, item_type, form, diff, stem, options, answer, solution = it
        n += 1
        iid = "his_hs_%04d" % n
        if iid in ids:
            errors.append("dup id %s" % iid)
        ids.add(iid)
        if kp not in reg:
            errors.append("%s: unknown kp %s" % (iid, kp))
        kp_counter[kp] += 1
        if item_type not in ("choice", "fill", "solve"):
            errors.append("%s: bad item_type %s" % (iid, item_type))
        g = reg[kp]["grade"] if kp in reg else 10
        if not (0.40 <= diff <= 0.85):
            errors.append("%s: difficulty %.2f out of 高中 range" % (iid, diff))
        if not stem or len(stem) < 6:
            errors.append("%s: stem too short" % iid)
        if item_type == "choice":
            if not options or not (4 <= len(options) <= 6):
                errors.append("%s: choice needs 4-6 options, got %s" % (iid, options and len(options)))
            else:
                for o in options:
                    if not o.startswith(LETTERS[:len(options)][0]) and not o[0] in LETTERS[:len(options)]:
                        errors.append("%s: option label problem %r" % (iid, o[:8]))
        else:
            if options:
                errors.append("%s: non-choice must not have options" % iid)
        if form == "mcq_multi":
            parts = [p for p in str(answer).split(",") if p]
            if len(parts) < 2:
                errors.append("%s: mcq_multi needs >=2 answers" % iid)
            else:
                for p in parts:
                    if p not in LETTERS[:len(options or "")]:
                        errors.append("%s: mcq_multi answer %r invalid" % (iid, p))
                if parts != sorted(parts):
                    errors.append("%s: mcq_multi answer not ascending: %r" % (iid, answer))
        elif item_type == "choice":
            if answer not in LETTERS[:len(options or "")]:
                errors.append("%s: answer %r not among options" % (iid, answer))
        else:
            if not answer or not str(answer).strip():
                errors.append("%s: empty answer" % iid)
            if not solution or not str(solution).strip():
                errors.append("%s: empty solution" % iid)
        base = {
            "id": iid,
            "item_type": item_type,
            "form": form,
            "stem": stem,
            "kps": [kp],
            "difficulty": diff,
        }
        if options:
            base["options"] = options
        if form == "mcq_multi":
            base["answer_mode"] = "subset"
        pub = dict(base)
        pub["source"] = "llm_generated"
        public.append(pub)
        full_item = {
            "id": iid,
            "item_type": item_type,
            "form": form,
            "stem": stem,
            "kps": [kp],
            "difficulty": diff,
            "source": "llm_generated",
        }
        if options:
            full_item["options"] = options
        if form == "mcq_multi":
            full_item["answer_mode"] = "subset"
        full_item["answer"] = answer
        full_item["solution"] = solution
        full.append(full_item)

    ledger = {
        "agent_id": "his-gen-w1-20261003",
        "solver": "GLM-5.3",
        "method": "generator self-answer",
        "answers": {it["id"]: it["answer"] for it in full},
    }

    # ---- coverage report (quota check: every KP 2-3 items) ----
    covered = len(kp_counter)
    print("items=%d  kps_covered=%d / %d" % (len(full), covered, len(reg)))
    per_kp = Counter(kp_counter.values())
    print("items per kp distribution:", dict(sorted(per_kp.items())))
    bad_quota = {k: c for k, c in kp_counter.items() if not (2 <= c <= 3)}
    if bad_quota:
        print("KPs violating 2-3 quota (%d): %s" % (len(bad_quota), bad_quota))
    miss = [k for k in reg if k not in kp_counter]
    if miss:
        print("KPs with 0 items (%d): %s" % (len(miss), miss))
    by_grade = Counter((reg[k]["grade"], c) for k, c in kp_counter.items() if k in reg)
    print("by grade:", dict(sorted(by_grade.items())))
    print("item_type:", dict(Counter(it["item_type"] for it in public)))
    print("form:", dict(Counter(it["form"] for it in public)))
    print("difficulty: min=%.2f max=%.2f" % (
        min(it["difficulty"] for it in public),
        max(it["difficulty"] for it in public)))

    if errors:
        print("VALIDATION ERRORS (%d):" % len(errors), file=sys.stderr)
        for e in errors[:80]:
            print("  " + e, file=sys.stderr)
        return 2

    for fn, obj in (("his_hs_public.json", public), ("his_hs_full.json", full),
                    ("his_hs_ledger_gen.json", ledger)):
        with open(os.path.join(HERE, fn), "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=1)
        print("wrote", fn, os.path.getsize(os.path.join(HERE, fn)), "bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
