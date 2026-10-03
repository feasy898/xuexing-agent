# -*- coding: utf-8 -*-
"""Lint the hand-authored data modules before building.

Checks per item tuple (kp, item_type, form, diff, stem, options, answer, solution):
  - 8 fields
  - no latin word glued into CJK text (catches drafting slips)
  - options 4-6 for choice, None otherwise; option labels A.. in order
  - answer in labels (choice) / 2+ letters (mcq_multi) / non-empty (fill|solve)
  - difficulty 0.30-0.75
  - stem non-trivial; no duplicate stem within a file
"""
import importlib
import re
import sys
import os
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "src"))
LETTERS = "ABCDEFGH"
CJK = re.compile(r"[\u4e00-\u9fff]")
LATIN = re.compile(r"[A-Za-z]{2,}")

FILES = sys.argv[1:]
if not FILES:
    import build_his_jr
    FILES = build_his_jr.DATA_FILES

errs = 0
total = 0
kps = set()
for name in FILES:
    try:
        mod = importlib.import_module(name)
    except ModuleNotFoundError:
        print("[skip] %s not present yet" % name)
        continue
    seen_stems = set()
    for it in mod.ITEMS:
        total += 1
        if len(it) != 8:
            print("  LEN=%d %s" % (len(it), name)); errs += 1; continue
        kp, itype, form, diff, stem, opts, ans, sol = it
        kps.add(kp)
        tag = "%s/%s" % (name, kp)
        if not isinstance(diff, float) or not (0.30 <= diff <= 0.75):
            print("  DIFF %s %.2f" % (tag, diff)); errs += 1
        for field, txt in (("stem", stem), ("sol", sol)):
            if not txt:
                print("  EMPTY %s %s" % (tag, field)); errs += 1; continue
            for m in LATIN.finditer(txt):
                s, e = m.start(), m.end()
                if CJK.search(txt[max(0, s - 1):s]):
                    print("  LATIN-IN-CJK %s %s: ...%s..." % (tag, field, txt[max(0, s - 12):e + 12]))
                    errs += 1
        if stem in seen_stems:
            print("  DUP-STEM %s" % tag); errs += 1
        seen_stems.add(stem)
        if itype == "choice":
            if not opts or not (4 <= len(opts) <= 6):
                print("  OPTS %s %s" % (tag, opts and len(opts))); errs += 1; continue
            for i, o in enumerate(opts):
                if not o.startswith(LETTERS[i] + "."):
                    print("  LABEL %s: %r" % (tag, o[:10])); errs += 1
            if form == "mcq_multi":
                parts = [p.strip() for p in str(ans).split(",") if p.strip()]
                if len(parts) < 2 or any(p not in LETTERS[:len(opts)] for p in parts):
                    print("  MULTI-ANS %s %r" % (tag, ans)); errs += 1
            elif ans not in LETTERS[:len(opts)]:
                print("  ANS %s %r" % (tag, ans)); errs += 1
        else:
            if opts:
                print("  OPTS-ON-NONCHOICE %s" % tag); errs += 1
            if not ans or not str(ans).strip():
                print("  EMPTY-ANS %s" % tag); errs += 1

per = Counter()
print("files=%d items=%d kps=%d errors=%d" % (len(FILES), total, len(kps), errs))
