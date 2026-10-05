"""归一化所有单代理入库批的 note 字段 = DEFERRED_NOTE。
"""
import glob
import json

DEFERRED = "single-agent generation, blind verification deferred"
fixed = 0
for f in sorted(glob.glob("data/items/*.json")):
    d = json.load(open(f, encoding="utf-8"))
    changed = False
    for it in d["items"]:
        v = it.get("verification")
        if not isinstance(v, dict):
            continue
        if not v.get("single_agent"):
            continue
        # 各种容差归一到标准 note
        cur = v.get("note", "")
        # 如果包含 DEFERRED 的核心串，且长度大于标准，去掉多余管道
        if cur and cur != DEFERRED and DEFERRED in cur:
            v["note"] = DEFERRED
            changed = True
            fixed += 1
    if changed:
        with open(f, "w", encoding="utf-8", newline="\r\n") as wf:
            json.dump(d, wf, ensure_ascii=False, indent=2)
            wf.write("\n")
        print(f"fixed {f.split(chr(92))[-1]}")
print(f"total fixed: {fixed}")
