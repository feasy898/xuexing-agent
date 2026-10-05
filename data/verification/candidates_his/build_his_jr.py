# -*- coding: utf-8 -*-
"""Build his_jr batch (初中历史 grade7/8/9) from hand-authored data modules.

Data module contract:  DATA_FILES = [name, ...] in order; each module exposes
ITEMS = [ (kp_id, item_type, form, difficulty, stem, options|None, answer, solution), ... ]

Outputs (same order in public & full):
  his_jr_public.json   -> no answer / no solution
  his_jr_full.json     -> with answer / solution
  his_jr_ledger_gen.json
"""
import importlib
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "src"))
sys.path.insert(0, REPO)

DATA_FILES = [
    "h_g7a", "h_g7b", "h_g7c", "h_g7d", "h_g7e", "h_g7f",
    "h_g8a", "h_g8b", "h_g8c", "h_g8d", "h_g8e",
    "h_g9a", "h_g9b", "h_g9c", "h_g9d", "h_g9e",
]

LETTERS = "ABCDEFGH"



# ---- answer-key rebalancing (deterministic cyclic rotation of options) ----
# Rationale: hand-authored items over-place the correct option at A. For every
# single-choice item we cyclically rotate the option list so the key letter falls
# on the least-used letter so far (ties -> earliest letter). Option labels are
# regenerated, the answer is remapped, and every standalone option-letter token
# in the solution (e.g. "选B。", "A、C错误") is remapped with the same mapping.
# Letters glued inside latin runs (WTO, ECFA...) are protected by the look-around.
import re as _re

_OPT_PREFIX = _re.compile(r"^([A-F])\.\s*")
_STANDALONE = _re.compile(r"(?<![A-Za-z])([A-F])(?![A-Za-z])")

def _rebalance_choice(opts, answer, solution, usage):
    n = len(opts)
    contents = []
    for j, o in enumerate(opts):
        m = _OPT_PREFIX.match(o)
        if not m or m.group(1) != LETTERS[j]:
            raise ValueError("bad option prefix: %r" % o[:10])
        contents.append(o[m.end():])
    i = LETTERS.index(answer)
    # target letter: least used so far (ties -> earliest)
    t = min(range(n), key=lambda j: (usage[LETTERS[j]], j))
    k = (t - i) % n
    if k == 0:
        usage[LETTERS[t]] += 1
        return opts, answer, solution, 0
    new_opts = [LETTERS[j] + ". " + contents[(j - k) % n] for j in range(n)]
    mapping = {LETTERS[p]: LETTERS[(p + k) % n] for p in range(n)}
    for ch in _STANDALONE.finditer(solution):
        if ch.group(1) not in mapping:
            raise ValueError("solution references letter outside option range")
    new_sol = _STANDALONE.sub(lambda m: mapping[m.group(1)], solution)
    usage[LETTERS[t]] += 1
    return new_opts, LETTERS[t], new_sol, k

def load_registry():
    reg = {}
    for g in (7, 8, 9):
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
    usage = Counter()
    rotated = 0
    for src, it in rows:
        kp, item_type, form, diff, stem, options, answer, solution = it
        n += 1
        if item_type == "choice" and form != "mcq_multi":
            options, answer, solution, k = _rebalance_choice(options, answer, solution, usage)
            rotated += (1 if k else 0)
        iid = "his_jr_%04d" % n
        if iid in ids:
            errors.append("dup id %s" % iid)
        ids.add(iid)
        if kp not in reg:
            errors.append("%s: unknown kp %s" % (iid, kp))
        kp_counter[kp] += 1
        if item_type not in ("choice", "fill", "solve"):
            errors.append("%s: bad item_type %s" % (iid, item_type))
        g = reg[kp]["grade"] if kp in reg else 7
        if not (0.30 <= diff <= 0.75):
            errors.append("%s: difficulty %.2f out of 初中 range" % (iid, diff))
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
        elif item_type == "choice":
            if answer not in LETTERS[:len(options or "")]:
                errors.append("%s: answer %r not among options" % (iid, answer))
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
        full_item = dict(base)
        full_item["source"] = "llm_generated"
        full_item["answer"] = answer
        full_item["solution"] = solution
        # keep key order stable: answer/solution after source
        full_item = {
            "id": full_item["id"], "item_type": full_item["item_type"], "form": full_item["form"],
            "stem": full_item["stem"], "kps": full_item["kps"], "difficulty": full_item["difficulty"],
            "source": full_item["source"],
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

    # ---- coverage report (not an error: quota check) ----
    covered = len(kp_counter)
    print("items=%d  kps_covered=%d / %d" % (len(full), covered, len(reg)))
    dist = Counter((reg[k]["grade"], cnt) for k, cnt in kp_counter.items())
    per_kp = Counter(kp_counter.values())
    print("items per kp distribution:", dict(per_kp))
    print("by grade:", dict(sorted(dist.items())))
    miss = [k for k in reg if k not in kp_counter]
    if miss:
        print("KPs with 0 items (%d): %s" % (len(miss), miss))
    print("item_type:", dict(Counter(it["item_type"] for it in public)))
    print("form:", dict(Counter(it["form"] for it in public)))
    print("rebalanced(rotated) single-choice items: %d" % rotated)
    print("single-choice key distribution:", dict(sorted(Counter(
        it["answer"] for it in full if it["item_type"] == "choice" and it["form"] != "mcq_multi").items())))
    print("difficulty: min=%.2f max=%.2f" % (min(it["difficulty"] for it in public),
                                             max(it["difficulty"] for it in public)))

    if errors:
        print("VALIDATION ERRORS (%d):" % len(errors), file=sys.stderr)
        for e in errors[:60]:
            print("  " + e, file=sys.stderr)
        return 2

    for fn, obj in (("his_jr_public.json", public), ("his_jr_full.json", full),
                    ("his_jr_ledger_gen.json", ledger)):
        with open(os.path.join(HERE, fn), "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=1)
        print("wrote", fn, os.path.getsize(os.path.join(HERE, fn)), "bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
