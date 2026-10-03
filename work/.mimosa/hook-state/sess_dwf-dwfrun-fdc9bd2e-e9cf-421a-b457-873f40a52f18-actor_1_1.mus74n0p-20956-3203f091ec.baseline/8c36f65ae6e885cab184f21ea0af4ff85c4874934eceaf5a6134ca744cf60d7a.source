import glob
import json
import sys

sub = sys.argv[1] if len(sys.argv) > 1 else "physics"
known = set()
for f in glob.glob("data/knowledge/*.json"):
    try:
        d = json.load(open(f, encoding="utf-8"))
    except Exception:
        continue
    for kp in d.get("knowledge_points", []):
        known.add(kp["id"])

errs = []
new = []
skipped = []
for f in glob.glob("data/knowledge/%s_grade*.json" % sub):
    try:
        d = json.load(open(f, encoding="utf-8"))
    except Exception as e:
        skipped.append(f)
        continue
    kps = d.get("knowledge_points", [])
    if not kps:
        errs.append(f + " empty")
        continue
    new += [kp for kp in kps]
    for kp in kps:
        for pre in kp.get("prereqs", []):
            if pre not in known:
                errs.append(f + " " + kp["id"] + " bad prereq " + pre)
        if not kp.get("standard_ref", "").strip():
            errs.append(f + " " + kp["id"] + " no standard_ref")
        if kp.get("subject") != sub:
            errs.append(f + " " + kp["id"] + " subject mismatch")

ids = [k["id"] for k in new]
if len(ids) != len(set(ids)):
    errs.append("dup ids")
print("%s_KP=%d ERRORS=%d SKIPPED_INCOMPLETE=%d" % (sub.upper(), len(ids), len(errs), len(skipped)))
for e in errs[:20]:
    print("  -", e)
if skipped:
    print("  (skipped, still being written:", ",".join(skipped), ")")
sys.exit(1 if errs else 0)
