import glob
import json
import re

pat = re.compile(r"_grade(\d+)\.json$")
bad_files = 0
total_mismatch = 0
for f in sorted(glob.glob("data/knowledge/*_grade*.json")):
    m = pat.search(f)
    if m is None:
        continue
    g = int(m.group(1))
    try:
        d = json.load(open(f, encoding="utf-8"))
    except Exception as e:
        print("BROKEN", f, str(e)[:60])
        bad_files += 1
        continue
    mism = [kp["id"] for kp in d.get("knowledge_points", []) if kp.get("grade") != g]
    if mism:
        total_mismatch += len(mism)
        print("%-45s file_grade=%d mismatched=%d e.g. %s" % (f.split("/")[-1], g, len(mism), mism[:2]))
print("--- broken files:", bad_files, " total mismatched KP:", total_mismatch)
