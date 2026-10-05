"""修复现有题库：agents 双元素同代理 → 单元素 + 补 single_agent=true。
仅对 PHY/CHE/BIO 三批生效（其他批不动）。
"""
import glob
import json

ALLOWED = {
    "phy-gen-w1-20261003",
    "che-gen-w1-20261003",
    "bio-gen-w1-20261003",
}

fixed = 0
for f in sorted(glob.glob("data/items/*.json")):
    d = json.load(open(f, encoding="utf-8"))
    changed = False
    for it in d["items"]:
        v = it.get("verification")
        if not isinstance(v, dict):
            continue
        ag = v.get("agents", [])
        if len(ag) == 2 and ag[0] == ag[1] and ag[0] in ALLOWED:
            v["agents"] = [ag[0]]
            if "single_agent" not in v:
                v["single_agent"] = True
            changed = True
            fixed += 1
    if changed:
        with open(f, "w", encoding="utf-8", newline="\r\n") as wf:
            json.dump(d, wf, ensure_ascii=False, indent=2)
            wf.write("\n")
        print(f"fixed {f.split(chr(92))[-1]}")
print(f"total fixed: {fixed}")
