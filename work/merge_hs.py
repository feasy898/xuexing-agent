import glob
import json
import os
import sys

sys.path.insert(0, "src")
from xuexing.dual_verify import answers_match

DIR = "data/verification/candidates_hs"
GEN = "hsg-gen-w1-20261003"
IND = "hsg-indep-w1-20261003"

# 1) 高中题库文件骨架（10-12 年级此前无题库）
for g in (10, 11, 12):
    p = f"data/items/math_grade{g}_items.json"
    if not os.path.exists(p):
        with open(p, "w", encoding="utf-8", newline="\r\n") as f:
            json.dump({"items": []}, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print("created", p)

tags = sorted(
    os.path.basename(f).replace("_public.json", "")
    for f in glob.glob(DIR + "/*_public.json")
)
disputes = []
agreed = 0
disputed = 0
for tag in tags:
    grade = 10 if tag.startswith("h10") else (11 if tag.startswith("h11") else 12)
    full = json.load(open(f"{DIR}/{tag}_full.json", encoding="utf-8"))
    gen = json.load(open(f"{DIR}/{tag}_ledger_gen.json", encoding="utf-8"))
    ind = json.load(open(f"{DIR}/{tag}_ledger_indep.json", encoding="utf-8"))
    bank_path = f"data/items/math_grade{grade}_items.json"
    bank = json.load(open(bank_path, encoding="utf-8"))
    added = 0
    for it in full:
        ok = answers_match(it["answer"], ind["answers"].get(it["id"], ""), it.get("item_type", "fill"), it.get("options"))
        if ok:
            m = {k: it[k] for k in ("id", "item_type", "stem", "answer", "kps", "difficulty", "solution", "source")}
            if it.get("options") is not None:
                m["options"] = it["options"]
            m["verification"] = {"agents": [gen["agent_id"], ind["agent_id"]], "answers_agree": True}
            bank["items"].append(m)
            added += 1
            agreed += 1
        else:
            disputes.append(
                {
                    "item_id": it["id"],
                    "grade": grade,
                    "key_answer": it["answer"],
                    "proposed": ind["answers"].get(it["id"]),
                    "item_type": it.get("item_type"),
                    "stem": it["stem"],
                }
            )
            disputed += 1
    with open(bank_path, "w", encoding="utf-8", newline="\r\n") as f:
        json.dump(bank, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"{tag}: agreed={added}")

with open("data/verification/arbitration_queue_hs.json", "w", encoding="utf-8", newline="\n") as f:
    json.dump({"note": "高中题库分歧：独立盲解与标答不符；仲裁前不回填", "queue": disputes}, f, ensure_ascii=False, indent=2)
    f.write("\n")

total = sum(len(json.load(open(f, encoding="utf-8"))["items"]) for f in glob.glob("data/items/*.json"))
print(f"HS_MERGE agreed={agreed} disputed={disputed} bank_total={total}")
