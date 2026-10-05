"""修复 pol_prim 候选：给 choice 题的裸文本选项加 A. B. C. D. 前缀。
"""
import json
import string

DIR = "data/verification/candidates_pol"

for tag in ["pol_prim", "pol_jr"]:
    pub_p = f"{DIR}/{tag}_public.json"
    full_p = f"{DIR}/{tag}_full.json"
    pub = json.load(open(pub_p, encoding="utf-8"))
    full = json.load(open(full_p, encoding="utf-8"))
    changed = 0
    for i, (p, f) in enumerate(zip(pub, full)):
        if f.get("item_type") != "choice":
            continue
        opts = p.get("options") or []
        if not opts:
            continue
        # 检查是否已有 A. 前缀
        first = str(opts[0]).lstrip()
        if first[:2].startswith("A.") or first[:3].startswith("A."):
            continue
        # 给所有选项加字母前缀
        new_opts = []
        for j, o in enumerate(opts):
            if j < 26:
                letter = string.ascii_uppercase[j]
                new_opts.append(f"{letter}. {o}")
            else:
                new_opts.append(o)
        pub[i]["options"] = new_opts
        # 同步 full.json
        full[i]["options"] = new_opts
        changed += 1
    if changed:
        with open(pub_p, "w", encoding="utf-8", newline="\n") as wf:
            json.dump(pub, wf, ensure_ascii=False, indent=2)
            wf.write("\n")
        with open(full_p, "w", encoding="utf-8", newline="\n") as wf:
            json.dump(full, wf, ensure_ascii=False, indent=2)
            wf.write("\n")
        print(f"{tag}: fixed {changed} choice items")
print("done")
