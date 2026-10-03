"""Build the 3 output JSON files from the question bank."""
import os

ROOT = r"D:\new-workspace\学情agent\xuexing-agent"
OUT = os.path.join(ROOT, "data", "verification", "candidates_bio")

import json

QS = json.load(open(os.path.join(OUT, "_question_bank.json"), encoding="utf-8"))

# Sort KPs by id (preserves grade10 -> grade11 -> grade12 order)
all_kp_ids = sorted(QS.keys())

public_items = []
full_items = []
ledger_answers = {}

seq = 1
for kp_id in all_kp_ids:
    qs = QS[kp_id]
    for q in qs:
        form, stem, options, answer, solution, difficulty = q
        # Tag: first letter from kp grade (e.g. h10/h11/h12)
        if kp_id.startswith("kp_bio10_"):
            tag = "g10"
        elif kp_id.startswith("kp_bio11_"):
            tag = "g11"
        elif kp_id.startswith("kp_bio12_"):
            tag = "g12"
        else:
            tag = "xx"
        item_id = f"bio_{tag}_{seq:04d}"
        seq += 1

        # Map item_type
        if form == "mcq_single":
            it_type = "choice"
        elif form == "mcq_multi":
            it_type = "choice"
        elif form == "fill":
            it_type = "fill"
        elif form == "solve":
            it_type = "solve"
        else:
            it_type = "choice"

        # Public item
        pub = {
            "id": item_id,
            "item_type": it_type,
            "form": form,
            "stem": stem,
            "kps": [kp_id],
            "difficulty": difficulty,
            "source": "llm_generated",
        }
        if it_type == "choice":
            pub["options"] = options
        if form == "mcq_multi":
            pub["answer_mode"] = "subset"
        public_items.append(pub)

        # Full item
        full = dict(pub)
        full["answer"] = answer
        full["solution"] = solution
        # Move source to last position; ensure keys are in expected order
        full.pop("source", None)
        full["source"] = "llm_generated"
        full_items.append(full)

        # Ledger
        ledger_answers[item_id] = answer


# Write public
public_path = os.path.join(OUT, "bio_hs_public.json")
with open(public_path, "w", encoding="utf-8") as f:
    json.dump(public_items, f, ensure_ascii=False, indent=2)
print(f"public -> {public_path}, n={len(public_items)}")

# Write full
full_path = os.path.join(OUT, "bio_hs_full.json")
with open(full_path, "w", encoding="utf-8") as f:
    json.dump(full_items, f, ensure_ascii=False, indent=2)
print(f"full -> {full_path}, n={len(full_items)}")

# Write ledger
ledger = {
    "agent_id": "bio-gen-w1-20261003",
    "solver": "MiniMax-M3",
    "method": "generator self-answer",
    "answers": ledger_answers,
}
ledger_path = os.path.join(OUT, "bio_hs_ledger_gen.json")
with open(ledger_path, "w", encoding="utf-8") as f:
    json.dump(ledger, f, ensure_ascii=False, indent=2)
print(f"ledger -> {ledger_path}, n_answers={len(ledger_answers)}")

# Sanity stats
from collections import Counter
form_dist = Counter()
diff_vals = []
for it in public_items:
    form_dist[it["form"]] += 1
    diff_vals.append(it["difficulty"])
print("Form distribution:", dict(form_dist))
print(f"Difficulty min/max/avg: {min(diff_vals)} / {max(diff_vals)} / {sum(diff_vals)/len(diff_vals):.3f}")
print(f"Multi-choice count: {sum(1 for it in public_items if it.get('answer_mode')=='subset')}")