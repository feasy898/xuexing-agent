"""Validate en_hs2 candidate files against the ask requirements."""
import json
import os

BASE = r"D:\new-workspace\学情agent\xuexing-agent\data\verification\candidates_en"

with open(os.path.join(BASE, "en_hs2_public.json"), "r", encoding="utf-8") as f:
    public = json.load(f)
with open(os.path.join(BASE, "en_hs2_full.json"), "r", encoding="utf-8") as f:
    full = json.load(f)
with open(os.path.join(BASE, "en_hs2_ledger_gen.json"), "r", encoding="utf-8") as f:
    ledger = json.load(f)

print(f"public.json: {len(public)} items")
print(f"full.json:   {len(full)} items")
print(f"ledger.json: {len(ledger['answers'])} answers")

# === Test 1: id uniqueness and same-order ===
pub_ids = [it["id"] for it in public]
full_ids = [it["id"] for it in full]
ledger_ids = list(ledger["answers"].keys())
assert pub_ids == full_ids == ledger_ids, "ID order mismatch!"
assert len(pub_ids) == len(set(pub_ids)), "Duplicate IDs in public!"
print(f"✓ IDs identical in same order across all three files. Total {len(pub_ids)} unique IDs.")

# === Test 2: public has no answer/solution ===
leaks = [it["id"] for it in public if "answer" in it or "solution" in it]
assert not leaks, f"public leaked answer/solution for {leaks}"
print(f"✓ public.json has NO answer/solution leakage ({len(leaks)} leaks).")

# === Test 3: full has answer + solution ===
missing_ans = [it["id"] for it in full if "answer" not in it or "solution" not in it]
assert not missing_ans, f"full missing answer/solution for {missing_ans}"
print(f"✓ full.json has answer + solution on all {len(full)} items.")

# === Test 4: KP validity ===
with open(r"D:\new-workspace\学情agent\xuexing-agent\data\knowledge\english_grade12.json", "r", encoding="utf-8") as f:
    kp_data = json.load(f)
valid_kps = {kp["id"] for kp in kp_data["knowledge_points"]}
bad_kps = []
for it in public:
    if not it["kps"]:
        bad_kps.append((it["id"], "empty kps"))
        continue
    if len(it["kps"]) != 1:
        bad_kps.append((it["id"], f"kps length {len(it['kps'])}"))
    if it["kps"][0] not in valid_kps:
        bad_kps.append((it["id"], f"unknown KP {it['kps'][0]}"))
assert not bad_kps, f"bad KPs: {bad_kps}"
print(f"✓ All {len(public)} items reference exactly 1 valid KP from english_grade12.json.")

# === Test 5: difficulty in 0.40-0.85 (high school) ===
bad_diff = [(it["id"], it["difficulty"]) for it in public if not (0.40 <= it["difficulty"] <= 0.85)]
assert not bad_diff, f"out-of-range difficulty: {bad_diff}"
print(f"✓ All difficulties in 0.40–0.85 (high school range).")

# === Test 6: choice items have 4 options A/B/C/D ===
bad_opts = []
for it in public:
    if it["item_type"] == "choice":
        if not it.get("options"):
            bad_opts.append((it["id"], "no options"))
            continue
        if len(it["options"]) != 4:
            bad_opts.append((it["id"], f"{len(it['options'])} options"))
        for o in it["options"]:
            if not (o.startswith("A.") or o.startswith("B.") or o.startswith("C.") or o.startswith("D.")):
                bad_opts.append((it["id"], f"option prefix: {o[:5]}"))
assert not bad_opts, f"bad options: {bad_opts[:5]}"
choice_count = sum(1 for it in public if it["item_type"] == "choice")
print(f"✓ All {choice_count} choice items have 4 options with A./B./C./D. prefix.")

# === Test 7: choice items answer ∈ {A,B,C,D} ===
bad_choice = [(it["id"], it["answer"]) for it in full if it["item_type"] == "choice" and it["answer"] not in ("A","B","C","D")]
assert not bad_choice, f"bad choice answer: {bad_choice}"
print(f"✓ All choice answers in {{A,B,C,D}}.")

# === Test 8: writing forms have writing_prompt ===
bad_wp = []
for it in full:
    if it["form"] in ("essay", "continuation", "narrative", "open_write", "summary"):
        if not it.get("writing_prompt"):
            bad_wp.append((it["id"], it["form"]))
assert not bad_wp, f"writing items missing writing_prompt: {bad_wp}"
wp_count = sum(1 for it in full if it.get("writing_prompt"))
print(f"✓ All {wp_count} writing/narrative/summary items include writing_prompt.")

# === Test 9: form distribution ===
from collections import Counter
print(f"\nForm distribution: {dict(Counter(it['form'] for it in public))}")
print(f"item_type distribution: {dict(Counter(it['item_type'] for it in public))}")

# === Test 10: KP coverage (each KP has 1-3 items) ===
from collections import Counter
kp_counts = Counter()
for it in public:
    kp_counts[it["kps"][0]] += 1
violations = {kp: c for kp, c in kp_counts.items() if not (1 <= c <= 3)}
assert not violations, f"KPs with wrong item counts: {violations}"
print(f"✓ Each KP has 1–3 items.")

# === Test 11: source field ===
src_bad = [it["id"] for it in public if it.get("source") != "llm_generated"]
assert not src_bad, f"non-llm_generated source: {src_bad}"
print(f"✓ All items have source='llm_generated'.")

# === Test 12: ledger contains ALL ids ===
ledger_set = set(ledger_ids)
pub_set = set(pub_ids)
assert ledger_set == pub_set, f"ledger / public mismatch: only-in-ledger={ledger_set-pub_set}, only-in-public={pub_set-ledger_set}"
print(f"✓ Ledger contains exactly the same {len(ledger_set)} IDs as public.")

# === Test 13: ledger answers match full answers ===
mismatches = [(it["id"], it["answer"], ledger["answers"][it["id"]]) for it in full if it["answer"] != ledger["answers"].get(it["id"])]
assert not mismatches, f"ledger vs full mismatch: {mismatches[:5]}"
print(f"✓ All ledger answers match full answers.")

print(f"\n✅ ALL VALIDATIONS PASSED. Batch en_hs2 ready: {len(public)} items, {len(set(it['kps'][0] for it in public))} KPs covered.")