"""Generate en_hs2 candidate files (public, full, ledger) from items_data.json."""
import json
import os

BASE = r"D:\new-workspace\学情agent\xuexing-agent\data\verification\candidates_en"

with open(os.path.join(BASE, "items_data.json"), "r", encoding="utf-8") as f:
    items = json.load(f)

print(f"Loaded {len(items)} items.")

public_list = []
full_list = []
ledger = {
    "agent_id": "eng-gen-w1-20261003",
    "solver": "MiniMax-M3",
    "method": "generator self-answer",
    "answers": {}
}

seen = set()
kp_to_items = {}
for idx, it in enumerate(items, start=1):
    eid = f"eng_hs2_{idx:04d}"
    if eid in seen:
        raise SystemExit(f"Duplicate id: {eid}")
    seen.add(eid)
    kp = it["kp"]
    kp_to_items.setdefault(kp, []).append(eid)

    pub = {
        "id": eid,
        "item_type": it["item_type"],
        "form": it["form"],
        "stem": it["stem"],
        "kps": [kp],
        "difficulty": it["difficulty"],
        "source": "llm_generated",
    }
    if it.get("options"):
        pub["options"] = it["options"]
    public_list.append(pub)

    full = dict(pub)
    full["answer"] = it["answer"]
    full["solution"] = it["solution"]
    # Writing / open_write forms: include writing_prompt
    if it["form"] in ("essay", "continuation", "narrative", "open_write", "summary"):
        full["writing_prompt"] = it["stem"]
    full_list.append(full)
    ledger["answers"][eid] = it["answer"]

# Validate all KP ids exist in english_grade12.json
with open(r"D:\new-workspace\学情agent\xuexing-agent\data\knowledge\english_grade12.json", "r", encoding="utf-8") as f:
    kp_data = json.load(f)
valid_kp_set = {kp["id"] for kp in kp_data["knowledge_points"]}
for kp, eids in kp_to_items.items():
    if kp not in valid_kp_set:
        raise SystemExit(f"Unknown KP: {kp} (items: {eids})")

# Coverage: which KPs in english_grade12 have NO items?
covered_kps = set(kp_to_items.keys())
missing_kps = sorted(valid_kp_set - covered_kps)
print(f"Covered {len(covered_kps)} KPs out of {len(valid_kp_set)}.")
if missing_kps:
    print(f"MISSING KPs (no items): {missing_kps}")
print(f"Items per KP distribution:")
from collections import Counter
counts = Counter(len(v) for v in kp_to_items.values())
print(f"  items-per-KP histogram: {dict(counts)}")

with open(os.path.join(BASE, "en_hs2_public.json"), "w", encoding="utf-8") as f:
    json.dump(public_list, f, ensure_ascii=False, indent=2)
with open(os.path.join(BASE, "en_hs2_full.json"), "w", encoding="utf-8") as f:
    json.dump(full_list, f, ensure_ascii=False, indent=2)
with open(os.path.join(BASE, "en_hs2_ledger_gen.json"), "w", encoding="utf-8") as f:
    json.dump(ledger, f, ensure_ascii=False, indent=2)

print(f"\nWrote:")
print(f"  en_hs2_public.json: {len(public_list)} items")
print(f"  en_hs2_full.json: {len(full_list)} items")
print(f"  en_hs2_ledger_gen.json: {len(ledger['answers'])} answers")

# Difficulty distribution check
diffs = [it["difficulty"] for it in items]
print(f"\nDifficulty range: {min(diffs):.2f} – {max(diffs):.2f}")
print(f"All difficulties in 0.40-0.85 for high school: {all(0.40 <= d <= 0.85 for d in diffs)}")