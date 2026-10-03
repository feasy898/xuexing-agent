# -*- coding: utf-8 -*-
"""Independent post-hoc verification of the built sci_prim artefacts.

Re-reads the three JSON files from disk and re-checks every hard requirement
from the ask, WITHOUT reusing build_sci_prim.py's in-memory state:
  1. id format sci_prim_NNNN, unique, contiguous
  2. kps: exactly 1 KP id per item, must exist in the KP registry files
  3. quota: every registered KP has exactly 2 items (463 KPs -> 926 items)
  4. difficulty band by grade (1-2: 0.20-0.50, 3-4: 0.30-0.60, 5-6: 0.40-0.70)
  5. no choice items for grade 1-2 (教基厅函〔2021〕34号)
  6. choice items have exactly 4 options labelled A-D, answer within ABCD
  7. observe items have observe_guide; non-observe must not
  8. public file has NO answer/solution/observe_guide; full file has all
  9. public and full are in the same order with identical id/stem/kps/difficulty
 10. ledger answers match the full file exactly
 11. source == 'llm_generated' everywhere; no empty fields
 12. no stray latin words / replacement chars in Chinese content fields
"""
import json
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))

ID_RE = re.compile(r"^sci_prim_(\d{4})$")
BAND = {1: (0.20, 0.50), 2: (0.20, 0.50), 3: (0.30, 0.60),
        4: (0.30, 0.60), 5: (0.40, 0.70), 6: (0.40, 0.70)}
# Latin tokens that are legitimate in this subject and must not be flagged
LATIN_OK = {"DNA", "dna"}


def fail(errs, msg):
    errs.append(msg)


def main():
    errs = []
    reg = {}
    for g in (1, 2, 3, 4, 5, 6):
        p = os.path.join(REPO, "data", "knowledge", "science_grade%d.json" % g)
        for k in json.load(open(p, encoding="utf-8"))["knowledge_points"]:
            reg[k["id"]] = k["grade"]

    pub = json.load(open(os.path.join(HERE, "sci_prim_public.json"), encoding="utf-8"))
    full = json.load(open(os.path.join(HERE, "sci_prim_full.json"), encoding="utf-8"))
    led = json.load(open(os.path.join(HERE, "sci_prim_ledger_gen.json"), encoding="utf-8"))

    # ---- 9. order/identity parity ----
    if len(pub) != len(full):
        fail(errs, "public/full length mismatch %d vs %d" % (len(pub), len(full)))
    for a, b in zip(pub, full):
        if a["id"] != b["id"] or a["stem"] != b["stem"] or a["kps"] != b["kps"] \
                or a["difficulty"] != b["difficulty"] or a["item_type"] != b["item_type"]:
            fail(errs, "public/full parity broken at %s" % a["id"])

    # ---- 8. field presence ----
    for it in pub:
        for forbidden in ("answer", "solution", "observe_guide"):
            if forbidden in it:
                fail(errs, "%s: public must not carry %s" % (it["id"], forbidden))
    for it in full:
        for need in ("answer", "solution"):
            if not it.get(need):
                fail(errs, "%s: full missing %s" % (it["id"], need))
        if it["item_type"] == "observe" and not it.get("observe_guide"):
            fail(errs, "%s: observe without observe_guide" % it["id"])

    # ---- 10. ledger parity ----
    if led.get("answers") != {it["id"]: it["answer"] for it in full}:
        fail(errs, "ledger answers != full answers")
    for key in ("agent_id", "solver", "method", "answers"):
        if key not in led:
            fail(errs, "ledger missing key %s" % key)

    # ---- per-item checks ----
    seen_ids = set()
    kp_count = Counter()
    grade_type = Counter()
    diff_by_grade = {}
    for it in full:
        iid = it["id"]
        m = ID_RE.match(iid)
        if not m:
            fail(errs, "%s: bad id format" % iid)
        if iid in seen_ids:
            fail(errs, "%s: duplicate id" % iid)
        seen_ids.add(iid)

        kps = it.get("kps")
        if not isinstance(kps, list) or len(kps) != 1:
            fail(errs, "%s: kps must be a 1-element list" % iid)
            continue
        kp = kps[0]
        if kp not in reg:
            fail(errs, "%s: unregistered kp %s" % (iid, kp))
            continue
        g = reg[kp]
        kp_count[kp] += 1
        grade_type[(g, it["item_type"])] += 1

        lo, hi = BAND[g]
        d = it["difficulty"]
        if not (isinstance(d, (int, float)) and lo <= d <= hi):
            fail(errs, "%s: difficulty %.2f outside grade-%d band" % (iid, d, g))
        diff_by_grade.setdefault(g, []).append(d)

        if it["item_type"] not in ("choice", "fill", "solve", "observe"):
            fail(errs, "%s: bad item_type %s" % (iid, it["item_type"]))
        if g <= 2 and it["item_type"] == "choice":
            fail(errs, "%s: grade %d must not use choice" % (iid, g))
        if it["item_type"] == "choice":
            opts = it.get("options")
            if not opts or len(opts) != 4:
                fail(errs, "%s: choice needs exactly 4 options" % iid)
            else:
                for j, o in enumerate(opts):
                    if not o.startswith("ABCD"[j]):
                        fail(errs, "%s: option %d label %r" % (iid, j, o[:8]))
                if it["answer"] not in ("A", "B", "C", "D"):
                    fail(errs, "%s: answer %r not in ABCD" % (iid, it["answer"]))
        elif it.get("options"):
            fail(errs, "%s: non-choice must not carry options" % iid)

        if it.get("source") != "llm_generated":
            fail(errs, "%s: source != llm_generated" % iid)
        if not it["stem"].strip():
            fail(errs, "%s: empty stem" % iid)

        # ---- 12. stray latin / mojibake in Chinese content ----
        texts = [it["stem"], it["answer"], it["solution"]] + (it.get("options") or [])
        for t in texts:
            if "\ufffd" in t:
                fail(errs, "%s: replacement char in text" % iid)
            for tok in re.findall(r"[A-Za-z]{2,}", t):
                if tok not in LATIN_OK:
                    fail(errs, "%s: stray latin token %r" % (iid, tok))

    # ---- 3. quota ----
    for kp in reg:
        if kp_count.get(kp, 0) != 2:
            fail(errs, "%s: has %d items (expected 2)" % (kp, kp_count.get(kp, 0)))
    for kp in kp_count:
        if kp not in reg:
            fail(errs, "%s: item references unknown kp" % kp)

    # ---- contiguous ids ----
    nums = sorted(int(ID_RE.match(i).group(1)) for i in seen_ids if ID_RE.match(i))
    if nums and nums != list(range(1, len(nums) + 1)):
        fail(errs, "ids not contiguous from 1 (gap found)")

    print("items            : %d" % len(full))
    print("KPs in registry  : %d" % len(reg))
    print("KPs covered      : %d" % len(kp_count))
    print("items per KP     : %s" % dict(Counter(kp_count.values())))
    print("id range         : %s .. %s" % (min(nums), max(nums)))
    for g in (1, 2, 3, 4, 5, 6):
        t = {k: v for (gg, k), v in sorted(grade_type.items()) if gg == g}
        lo, hi = BAND[g]
        if g in diff_by_grade:
            print("grade %d: n=%3d types=%s diff=[%.2f,%.2f] band=[%.2f,%.2f]"
                  % (g, len(diff_by_grade[g]), dict(t),
                     min(diff_by_grade[g]), max(diff_by_grade[g]), lo, hi))
    print("choice in g1-2   : %d (must be 0)"
          % sum(v for (gg, k), v in grade_type.items() if gg <= 2 and k == "choice"))

    if errs:
        print("\nFAILED (%d):" % len(errs))
        for e in errs[:60]:
            print("  " + e)
        return 2
    print("\nALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
