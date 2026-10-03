import json
import glob
import os

total_removed = 0
for f in sorted(glob.glob("data/items/*.json")):
    d = json.load(open(f, encoding="utf-8"))
    seen = set()
    new = []
    for it in d["items"]:
        if it["id"] in seen:
            continue
        seen.add(it["id"])
        new.append(it)
    if len(new) < len(d["items"]):
        removed = len(d["items"]) - len(new)
        d["items"] = new
        with open(f, "w", encoding="utf-8", newline="\r\n") as wf:
            json.dump(d, wf, ensure_ascii=False, indent=2)
            wf.write("\n")
        total_removed += removed
        print(os.path.basename(f), "removed", removed)
total = sum(
    len(json.load(open(f, encoding="utf-8"))["items"])
    for f in glob.glob("data/items/*.json")
    if os.path.exists(f)
)
print(f"removed {total_removed}, bank_total={total}")
