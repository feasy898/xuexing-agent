# -*- coding: utf-8 -*-
"""Assemble all items into the 4 final output files."""
import json, os
from collections import defaultdict

OUT_DIR = "data/verification/candidates_en"

# Load all items
all_items = []
for fname in ["_temp_g7.json", "_temp_g8.json", "_temp_g9.json", "_temp_supplement.json"]:
    with open(os.path.join(OUT_DIR, fname), "r", encoding="utf-8") as f:
        all_items.extend(json.load(f))

# Validate IDs unique
ids_seen = set()
for it in all_items:
    if it["id"] in ids_seen:
        raise ValueError(f"Duplicate ID: {it['id']}")
    ids_seen.add(it["id"])

print(f"Total items: {len(all_items)}")
print(f"Unique IDs: {len(ids_seen)}")

# Sort by id for consistency
all_items.sort(key=lambda x: x["id"])

# Validate fields
required_fields = ["id", "item_type", "stem", "kps", "difficulty", "source"]
for it in all_items:
    for f in required_fields:
        assert f in it, f"Missing field {f} in {it['id']}"
    assert len(it["kps"]) == 1, f"kps must have exactly 1 entry in {it['id']}"
    assert it["difficulty"] >= 0.2 and it["difficulty"] <= 0.85, f"difficulty out of range in {it['id']}: {it['difficulty']}"
    if it["item_type"] == "choice":
        assert "options" in it and len(it["options"]) == 4, f"choice needs 4 options in {it['id']}"
        assert it["answer"] in ["A", "B", "C", "D"], f"answer not in A/B/C/D in {it['id']}"
    assert it["source"] == "llm_generated"

print("All items validated.")

# Build public (no answer/solution)
public_items = []
for it in all_items:
    pub = {
        "id": it["id"],
        "item_type": it["item_type"],
        "form": it["form"],
        "stem": it["stem"],
        "kps": it["kps"],
        "difficulty": it["difficulty"],
        "source": "llm_generated",
    }
    if it["item_type"] == "choice":
        pub["options"] = it["options"]
    public_items.append(pub)

with open(os.path.join(OUT_DIR, "en_jr_public.json"), "w", encoding="utf-8") as f:
    json.dump(public_items, f, ensure_ascii=False, indent=2)
print(f"Saved {len(public_items)} items to en_jr_public.json")

# Build full (with answer, solution, writing_prompt)
full_items = []
for it in all_items:
    full = {
        "id": it["id"],
        "item_type": it["item_type"],
        "form": it["form"],
        "stem": it["stem"],
        "answer": it["answer"],
        "kps": it["kps"],
        "difficulty": it["difficulty"],
        "solution": it["solution"],
        "source": "llm_generated",
    }
    if it["item_type"] == "choice":
        full["options"] = it["options"]
    # Add writing_prompt for writing forms
    if it["form"] in ["essay", "narrative", "open_write", "continuation"]:
        # Use stem itself as the writing prompt description
        full["writing_prompt"] = it["stem"][:120] + ("..." if len(it["stem"]) > 120 else "")
    full_items.append(full)

with open(os.path.join(OUT_DIR, "en_jr_full.json"), "w", encoding="utf-8") as f:
    json.dump(full_items, f, ensure_ascii=False, indent=2)
print(f"Saved {len(full_items)} items to en_jr_full.json")

# Build ledger
ledger = {
    "agent_id": "eng-gen-w1-20261003",
    "solver": "MiniMax-M3",
    "method": "generator self-answer",
    "answers": {},
}
for it in all_items:
    ledger["answers"][it["id"]] = it["answer"]

with open(os.path.join(OUT_DIR, "en_jr_ledger_gen.json"), "w", encoding="utf-8") as f:
    json.dump(ledger, f, ensure_ascii=False, indent=2)
print(f"Saved ledger with {len(ledger['answers'])} answers")

# Cleanup temp files
for fname in ["_temp_g7.json", "_temp_g8.json", "_temp_g9.json", "_temp_supplement.json"]:
    fp = os.path.join(OUT_DIR, fname)
    if os.path.exists(fp):
        os.remove(fp)
print("Temp files removed.")

# Final summary
print()
print("=== Final summary ===")
print(f"Total items: {len(all_items)}")
# Per form
form_count = defaultdict(int)
type_count = defaultdict(int)
grade_count = defaultdict(int)
for it in all_items:
    form_count[it["form"]] += 1
    type_count[it["item_type"]] += 1
    kp_id = it["kps"][0]
    if "kp_eng7" in kp_id:
        grade_count["G7"] += 1
    elif "kp_eng8" in kp_id:
        grade_count["G8"] += 1
    elif "kp_eng9" in kp_id:
        grade_count["G9"] += 1

print(f"By grade: {dict(grade_count)}")
print(f"By item_type: {dict(type_count)}")
print(f"By form: {dict(form_count)}")

# Per KP
kp_count = defaultdict(int)
for it in all_items:
    kp_count[it["kps"][0]] += 1
print(f"KPs with 1 item: {sum(1 for v in kp_count.values() if v == 1)}")
print(f"KPs with 2 items: {sum(1 for v in kp_count.values() if v == 2)}")
print(f"KPs with 3+ items: {sum(1 for v in kp_count.values() if v >= 3)}")
