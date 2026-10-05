import glob
import json
import re

known = {}  # grade -> {"__ids__": set, token: set(kp_ids)}
for f in sorted(glob.glob("data/knowledge/english_grade*.json")):
    g = int(re.search(r"grade(\d+)", f).group(1))
    bucket = known.setdefault(g, {"__ids__": set()})
    for kp in json.load(open(f, encoding="utf-8"))["knowledge_points"]:
        bucket["__ids__"].add(kp["id"])
        # 用 kp_id 切片与 name 切片建索引
        for t in re.findall(r"[a-z_]+", kp["id"].lower()):
            if len(t) > 3 and t not in ("kp", "eng", "grade"):
                bucket.setdefault(t, []).append(kp["id"])
        for t in re.findall(r"[a-z_]+", kp.get("name", "").lower()):
            if len(t) > 3:
                bucket.setdefault(t, []).append(kp["id"])

fixed_total = 0
deleted_total = 0
for pf in sorted(glob.glob("data/verification/candidates_en/*_public.json")):
    pub = json.load(open(pf, encoding="utf-8"))
    full_path = pf.replace("_public.json", "_full.json")
    full = json.load(open(full_path, encoding="utf-8"))
    new_pub = []
    new_full = []
    fixed = 0
    deleted = 0
    for p, fu in zip(pub, full):
        kps = p.get("kps", [])
        new_kps = []
        for k in kps:
            # KP id 形如 kp_eng10_lis10_xxx —— 第二个数字是年级
            nums = re.findall(r"\d+", k)
            g = int(nums[1]) if len(nums) >= 2 else None
            if g is None or g not in known:
                continue
            if k in known[g].get("__ids__", set()):
                new_kps.append(k)
                continue
            toks = [t for t in re.findall(r"[a-z_]+", k.lower()) if len(t) > 3 and t not in ("kp", "eng", "grade" + str(g))]
            cands = set()
            for t in toks:
                cands.update(known[g].get(t, []))
            cands = {c for c in cands if c in known[g].get("__ids__", set())}
            if cands:
                new_kps.append(sorted(cands)[0])
                fixed += 1
            else:
                deleted += 1
        if new_kps:
            p2 = dict(p)
            p2["kps"] = new_kps
            new_pub.append(p2)
            fu2 = dict(fu)
            fu2["kps"] = new_kps
            new_full.append(fu2)
    if fixed or deleted:
        with open(pf, "w", encoding="utf-8", newline="\n") as f:
            json.dump(new_pub, f, ensure_ascii=False, indent=2)
            f.write("\n")
        with open(full_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(new_full, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print("%s fixed=%d dropped=%d before=%d after=%d" % (pf.split("/")[-1], fixed, deleted, len(pub), len(new_pub)))
        fixed_total += fixed
        deleted_total += deleted
print("--- total: bad_fixed=%d bad_dropped=%d" % (fixed_total, deleted_total))
