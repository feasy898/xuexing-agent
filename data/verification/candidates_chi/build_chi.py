# -*- coding: utf-8 -*-
"""生成 chi_prim_hi 批候选題三件套：_public.json / _full.json / _ledger_gen.json。
数据来源：chi_data_g4a/g4b/g5a/g5b/g6a/g6b.py（原创命题，共 540 题，覆盖 KP 180 个）。
id 规则：chi_prim_hi_<四位序号>（同批唯一，与批次 tag 一致）。
"""
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chi_data_g4a import G4A
from chi_data_g4b import G4B
from chi_data_g5a import G5A
from chi_data_g5b import G5B
from chi_data_g6a import G6A
from chi_data_g6b import G6B

BASE = r"D:\new-workspace\学情agent\xuexing-agent\data\verification\candidates_chi"
TAG = "chi_prim_hi"
AGENT_ID = "chi-gen-w1-20261003"

ITEMS = G4A + G4B + G5A + G5B + G6A + G6B

# 载入 KP 白名单（四年级五、六年级三个文件）
valid_kps = set()
for g in (4, 5, 6):
    with open(rf"D:\new-workspace\学情agent\xuexing-agent\data\knowledge\chinese_grade{g}.json", encoding="utf-8") as f:
        kp_data = json.load(f)
    for kp in kp_data["knowledge_points"]:
        valid_kps.add(kp["id"])

public_list, full_list = [], {}
answers = {}
seen_ids = set()
errors = []

for idx, it in enumerate(ITEMS, start=1):
    eid = f"{TAG}_{idx:04d}"
    if eid in seen_ids:
        errors.append(f"重复 id: {eid}")
    seen_ids.add(eid)

    kp = it["kp"]
    if kp not in valid_kps:
        errors.append(f"{eid} 未知 KP: {kp}")

    stem = it["stem"]
    pub = {
        "id": eid,
        "item_type": it["item_type"],
        "form": it["form"],
        "stem": stem,
        "kps": [kp],
        "difficulty": it["difficulty"],
        "source": "llm_generated",
    }
    if it["item_type"] == "choice":
        opts = it.get("options") or []
        if len(opts) != 4:
            errors.append(f"{eid} 选项数 {len(opts)}")
        pub["options"] = opts
        # 与兄弟批次一致：题干内行文同时呈现选项，便于盲解阅读
        pub["stem"] = stem + "\n" + "\n".join(opts)
        if it["answer"] not in ("A", "B", "C", "D"):
            errors.append(f"{eid} 选择答案非法: {it['answer']}")
    full = dict(pub)
    full["answer"] = it["answer"]
    full["solution"] = it["solution"]
    if it["form"] == "essay":
        wp = it.get("writing_prompt")
        if not wp:
            errors.append(f"{eid} 作文题缺 writing_prompt")
        else:
            full["writing_prompt"] = wp
    full_list[eid] = full
    public_list.append(pub)
    answers[eid] = it["answer"]

# —— 附加校验（fail-fast） ——
if errors:
    for e in errors[:20]:
        print("ERROR:", e)
    raise SystemExit(f"共 {len(errors)} 处错误")

difficulty_bad = [p["id"] for p in public_list if not (0.2 <= p["difficulty"] <= 0.6)]
if difficulty_bad:
    raise SystemExit(f"小学学段难度超出 0.2-0.6：{difficulty_bad[:5]}")
public_leak = [p["id"] for p in public_list if "answer" in p or "solution" in p]
if public_leak:
    raise SystemExit(f"public 泄漏 answer/solution：{public_leak[:5]}")
kp_counter = Counter(p["kps"][0] for p in public_list)
bad_cov = {k: c for k, c in kp_counter.items() if c != 3}
if bad_cov:
    raise SystemExit(f"每个 KP 应恰有 3 题：{bad_cov}")
covered = set(kp_counter)
missing = sorted(valid_kps - covered)
if missing:
    raise SystemExit(f"未覆盖 KP：{missing}")

ledger = {"agent_id": AGENT_ID, "solver": "MiniMax-M3", "method": "generator self-answer", "answers": answers}

out_public = os.path.join(BASE, f"{TAG}_public.json")
out_full = os.path.join(BASE, f"{TAG}_full.json")
out_ledger = os.path.join(BASE, f"{TAG}_ledger_gen.json")
with open(out_public, "w", encoding="utf-8") as f:
    json.dump(public_list, f, ensure_ascii=False, indent=2)
with open(out_full, "w", encoding="utf-8") as f:
    json.dump([full_list[p["id"]] for p in public_list], f, ensure_ascii=False, indent=2)
with open(out_ledger, "w", encoding="utf-8") as f:
    json.dump(ledger, f, ensure_ascii=False, indent=2)

print(f"写出完成：{len(public_list)} 题，{len(covered)}/180 KP 各 3 题")
print(f"  {out_public}")
print(f"  {out_full}")
print(f"  {out_ledger}")
print("\nitem_type 分布:", dict(Counter(p["item_type"] for p in public_list)))
print("form 分布:", dict(Counter(p["form"] for p in public_list)))
print("难度区间:", min(p["difficulty"] for p in public_list), "-", max(p["difficulty"] for p in public_list))
