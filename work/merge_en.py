import glob
import json
import os
import re
import sys

sys.path.insert(0, "src")
from xuexing.dual_verify import answers_match

DIR = "data/verification/candidates_en"
GEN = "eng-gen-w1-20261003"
IND = "eng-indep-w1-20261003"

# 1) 创建英文各年级 items 文件骨架
for g in range(1, 13):
    p = f"data/items/english_grade{g}_items.json"
    if not os.path.exists(p):
        with open(p, "w", encoding="utf-8", newline="\r\n") as f:
            json.dump({"items": []}, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print("created", p)

disputes = []
agreed = 0
disputed = 0
for pf in sorted(glob.glob(DIR + "/*_public.json")):
    tag = os.path.basename(pf).replace("_public.json", "")
    pub = json.load(open(pf, encoding="utf-8"))
    full = json.load(open(pf.replace("_public", "_full"), encoding="utf-8"))
    gen = json.load(open(pf.replace("_public", "_ledger_gen"), encoding="utf-8"))
    ind = json.load(open(pf.replace("_public", "_ledger_indep"), encoding="utf-8"))
    for p, fu in zip(pub, full):
        kps = fu.get("kps") or []
        if len(kps) != 1:
            disputed += 1
            continue
        nums = re.findall(r"\d+", kps[0])
        if len(nums) < 2:
            disputed += 1
            continue
        g = int(nums[1])
        ok = answers_match(
            fu["answer"],
            ind["answers"].get(p["id"], ""),
            fu.get("item_type", "fill"),
            fu.get("options"),
        )
        if not ok:
            disputed += 1
            disputes.append(
                {
                    "item_id": p["id"],
                    "grade": g,
                    "key_answer": fu["answer"],
                    "proposed": ind["answers"].get(p["id"]),
                }
            )
            continue
        bank_p = f"data/items/english_grade{g}_items.json"
        bank = json.load(open(bank_p, encoding="utf-8"))
        m = {}
        for k in ("id", "item_type", "stem", "answer", "kps", "difficulty", "solution", "source", "options", "form"):
            if k in fu:
                m[k] = fu[k]
        if "form" not in m:
            m["form"] = m.get("item_type", "fill")
        m["verification"] = {"agents": [GEN, IND], "answers_agree": True}
        bank["items"].append(m)
        with open(bank_p, "w", encoding="utf-8", newline="\r\n") as f:
            json.dump(bank, f, ensure_ascii=False, indent=2)
            f.write("\n")
        agreed += 1

with open("data/verification/arbitration_queue_en.json", "w", encoding="utf-8", newline="\n") as f:
    json.dump(
        {"note": "英语题库分歧：独立盲解与标答不符；仲裁前不回填", "queue": disputes},
        f,
        ensure_ascii=False,
        indent=2,
    )
    f.write("\n")

total = sum(len(json.load(open(f, encoding="utf-8"))["items"]) for f in glob.glob("data/items/*.json") if os.path.exists(f))
print(f"EN_MERGE_DONE agreed={agreed} disputed={disputed} bank_total={total}")
