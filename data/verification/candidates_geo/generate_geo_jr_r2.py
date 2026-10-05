#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
geo_jr R2 batch — 补齐初中地理（7-9 年级）候选题库。

输入：geo_jr_r2_data_[a-e].py 中的题面数据（Q[kp_id] = [item, ...]）
行为：在既有 geo_jr_public/full/ledger_gen 三文件基础上「同序追加」，重新落盘。

题面字段（full）：id, item_type, form, stem, options?, kps(1个), difficulty, answer, solution, source
public = full 去掉 answer / solution
ledger: agent_id/solver/method 按 R2 批要求，answers 覆盖全部题目 id
"""
import importlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
KP_LIST = ROOT / "data" / "knowledge" / "geo_jr_kp_list.txt"

# ---------------------------------------------------------------- 载入题面数据
Q = {}
MODULES = ["a", "b", "c", "d", "e"]
for m in MODULES:
    try:
        mod = importlib.import_module(f"geo_jr_r2_data_{m}")
    except ModuleNotFoundError:
        print(f"[warn] module geo_jr_r2_data_{m}.py not found, skipped")
        continue
    for kp_id, items in mod.Q.items():
        if kp_id in Q:
            raise SystemExit(f"ERROR: KP {kp_id} defined in two modules")
        Q[kp_id] = items
print(f"loaded {len(Q)} KPs, {sum(len(v) for v in Q.values())} new items")

# ---------------------------------------------------------------- KP 顺序
all_kp_ids = [ln.split("|")[0].strip() for ln in KP_LIST.read_text(encoding="utf-8").splitlines() if ln.strip()]
kp_set = set(all_kp_ids)

# ---------------------------------------------------------------- 既有题目
pub_path = HERE / "geo_jr_public.json"
full_path = HERE / "geo_jr_full.json"
base_full_path = HERE / "geo_jr_r2_base_full.json"
# 基线 = R1 批的 6 道题（快照见 geo_jr_r2_base_full.json），保证脚本可重复执行
old_full = json.loads(base_full_path.read_text(encoding="utf-8"))
old_public = [{k: v for k, v in it.items() if k not in ("answer", "solution")} for it in old_full]
assert len(old_public) == len(old_full), "public/full length mismatch"
next_no = max(int(it["id"].rsplit("_", 1)[1]) for it in old_full) + 1
print(f"baseline items: {len(old_full)}, next id: geo_jr_{next_no:04d}")

# ---------------------------------------------------------------- 新题：按 KP 清单顺序编号
new_full = []
for kp_id in all_kp_ids:
    for it in Q.get(kp_id, []):
        item = {
            "id": f"geo_jr_{next_no:04d}",
            "item_type": it["item_type"],
            "form": it["form"],
            "stem": it["stem"].strip(),
            "kps": [kp_id],
            "difficulty": it["difficulty"],
        }
        if it["item_type"] == "choice":
            item["options"] = it["options"]
        item["answer"] = it["answer"]
        item["solution"] = it["solution"].strip()
        item["source"] = "llm_generated"
        new_full.append(item)
        next_no += 1

items = old_full + new_full
public = [{k: v for k, v in it.items() if k not in ("answer", "solution")} for it in items]

# ---------------------------------------------------------------- 校验
errors = []
ids = [it["id"] for it in items]
if len(ids) != len(set(ids)):
    errors.append("duplicate ids")
stems = [it["stem"] for it in items]
if len(stems) != len(set(stems)):
    dup = {s for s in stems if stems.count(s) > 1}
    errors.append(f"duplicate stems: {list(dup)[:3]}")
for it in items:
    p = f"{it['id']}: "
    if it["item_type"] not in ("choice", "fill", "solve"):
        errors.append(f"{p}bad item_type")
    if len(it["kps"]) != 1:
        errors.append(f"{p}kps must be exactly 1")
    elif it["kps"][0] not in kp_set:
        errors.append(f"{p}unknown kp {it['kps'][0]}")
    if not (0.2 <= it["difficulty"] <= 0.85):
        errors.append(f"{p}difficulty out of [0.2,0.85]: {it['difficulty']}")
    if it["item_type"] == "choice":
        opts = it.get("options") or []
        if len(opts) != 4:
            errors.append(f"{p}choice needs exactly 4 options, got {len(opts)}")
        labels = [o.strip().split(".")[0].strip() for o in opts]
        if it["answer"].strip() not in labels:
            errors.append(f"{p}answer {it['answer']!r} not among {labels}")
    if not it.get("answer", "").strip():
        errors.append(f"{p}empty answer")
    if it["id"] not in {x["id"] for x in public if x["id"] == it["id"]}:
        errors.append(f"{p}missing in public")

# 与既有题库（高中 geo_hs + data/items）比对，避免抄题
def bigrams(s):
    s = "".join(s.split())
    return {s[i:i + 2] for i in range(len(s) - 1)}

ref_stems = []
for p in [HERE / "geo_hs_public.json", HERE / "geo_hs_full.json"]:
    if p.exists():
        ref_stems += [i["stem"] for i in json.loads(p.read_text(encoding="utf-8"))]
for p in (ROOT / "data" / "items").glob("geography_grade*_items.json"):
    ref_stems += [i["stem"] for i in json.loads(p.read_text(encoding="utf-8"))["items"]]
ref_stems = [s for s in ref_stems if s not in set(stems)]
ref_bg = [(s, bigrams(s)) for s in ref_stems]
max_j = 0.0
near = []
for it in new_full:
    bg = bigrams(it["stem"])
    if not bg:
        continue
    best, best_s = 0.0, ""
    for s, rb in ref_bg:
        inter = len(bg & rb)
        if not inter:
            continue
        j = inter / len(bg | rb)
        if j > best:
            best, best_s = j, s
    if best > max_j:
        max_j = best
    if best >= 0.5:
        near.append((it["id"], round(best, 3), best_s[:40]))
print(f"stem similarity vs existing bank: max jaccard={max_j:.3f}; >=0.5: {near[:5]}")

# KP 覆盖统计
from collections import Counter
cnt = Counter(it["kps"][0] for it in items)
print(f"total items: {len(items)}; KPs covered: {len(cnt)}/{len(all_kp_ids)}")
print("items per KP histogram:", dict(sorted(Counter(cnt.values()).items())))
print("type mix:", dict(Counter(it["item_type"] for it in items)))
print("form mix:", dict(Counter(it["form"] for it in items)))

if errors:
    print("VALIDATION ERRORS:")
    for e in errors[:40]:
        print("  -", e)
    sys.exit(1)

# ---------------------------------------------------------------- 落盘
pub_path.write_text(json.dumps(public, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
full_path.write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

ledger = {
    "agent_id": "geo-gen-w1jr-20261003-r2",
    "solver": "MiniMax-M3.1-Flash",
    "method": "generator self-answer, R2 batch",
    "answers": {it["id"]: it["answer"] for it in items},
}
(HERE / "geo_jr_ledger_gen.json").write_text(
    json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

print("written:")
for name in ("geo_jr_public.json", "geo_jr_full.json", "geo_jr_ledger_gen.json"):
    p = HERE / name
    print(f"  {name}: {p.stat().st_size} bytes")
