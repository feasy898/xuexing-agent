"""Validate the output files."""
import os
import json

ROOT = r"D:\new-workspace\学情agent\xuexing-agent"
OUT = os.path.join(ROOT, "data", "verification", "candidates_bio")

# Load registered KP ids
all_kp_ids = set()
for g in [10, 11, 12]:
    d = json.load(open(f"{ROOT}/data/knowledge/biology_grade{g}.json"))
    for kp in d["knowledge_points"]:
        all_kp_ids.add(kp["id"])

# Load output files
pub = json.load(open(f"{OUT}/bio_hs_public.json", encoding="utf-8"))
full = json.load(open(f"{OUT}/bio_hs_full.json", encoding="utf-8"))
ledger = json.load(open(f"{OUT}/bio_hs_ledger_gen.json", encoding="utf-8"))

errors = []
warnings = []

# Check counts
if len(pub) != len(full):
    errors.append(f"public/full count mismatch: {len(pub)} vs {len(full)}")

# Check ids match between public and full
pub_ids = [it["id"] for it in pub]
full_ids = [it["id"] for it in full]
if pub_ids != full_ids:
    errors.append("public and full item orders/ids differ")

# Check ledger has all ids
ledger_ids = set(ledger["answers"].keys())
pub_set = set(pub_ids)
if ledger_ids != pub_set:
    errors.append(f"ledger keys don't match public ids: missing={pub_set-ledger_ids}, extra={ledger_ids-pub_set}")

# Check ledger agent_id format
if not ledger.get("agent_id", "").startswith("bio-"):
    warnings.append(f"agent_id should start with bio-: {ledger.get('agent_id')}")

# Check each item
choice_count = 0
fill_count = 0
solve_count = 0
mcq_multi_count = 0
diffs = []
seen_ids = set()
kp_usage = {}

for it in pub:
    iid = it["id"]
    if iid in seen_ids:
        errors.append(f"duplicate id: {iid}")
    seen_ids.add(iid)

    # kps
    kps = it.get("kps", [])
    if len(kps) != 1:
        errors.append(f"{iid}: kps length {len(kps)} != 1")
    else:
        kid = kps[0]
        if kid not in all_kp_ids:
            errors.append(f"{iid}: KP id {kid} not registered")
        kp_usage[kid] = kp_usage.get(kid, 0) + 1

    # item_type
    it_type = it.get("item_type")
    if it_type == "choice":
        choice_count += 1
        opts = it.get("options")
        if not opts or len(opts) < 4 or len(opts) > 6:
            errors.append(f"{iid}: choice needs 4-6 options, got {len(opts) if opts else 0}")
        # answer valid?
        full_it = next(f for f in full if f["id"] == iid)
        ans = full_it.get("answer", "")
        if it.get("form") == "mcq_single":
            if ans not in {"A","B","C","D","E","F"}:
                errors.append(f"{iid}: single-choice answer {ans} invalid")
        elif it.get("form") == "mcq_multi":
            mcq_multi_count += 1
            if it.get("answer_mode") != "subset":
                errors.append(f"{iid}: mcq_multi needs answer_mode=subset")
            # validate answer is comma-separated letters within options
            valid_letters = set(chr(ord("A")+i) for i in range(len(opts)))
            parts = [p.strip() for p in ans.split(",")]
            for p in parts:
                if p not in valid_letters:
                    errors.append(f"{iid}: mcq_multi answer '{p}' not in options")
    elif it_type == "fill":
        fill_count += 1
        if "____" not in it["stem"]:
            errors.append(f"{iid}: fill should have ____ blank")
        full_it = next(f for f in full if f["id"] == iid)
        if not full_it.get("answer"):
            errors.append(f"{iid}: fill missing answer")
    elif it_type == "solve":
        solve_count += 1
        full_it = next(f for f in full if f["id"] == iid)
        if not full_it.get("answer"):
            errors.append(f"{iid}: solve missing answer")
    else:
        errors.append(f"{iid}: unknown item_type {it_type}")

    # difficulty in range
    d = it.get("difficulty", 0)
    diffs.append(d)
    if not (0.40 <= d <= 0.85):
        errors.append(f"{iid}: difficulty {d} out of high school range [0.40, 0.85]")

    # id format
    if not iid.startswith("bio_"):
        errors.append(f"{iid}: id should start with bio_")

# KP coverage check
missing_kps = all_kp_ids - set(kp_usage.keys())
if missing_kps:
    errors.append(f"KPs not covered: {missing_kps}")

# Check full file has answer/solution/source
for it in full:
    if "answer" not in it:
        errors.append(f"{it['id']}: full file missing answer")
    if "solution" not in it:
        errors.append(f"{it['id']}: full file missing solution")
    if it.get("source") != "llm_generated":
        errors.append(f"{it['id']}: source must be 'llm_generated'")

print("=" * 60)
print(f"Public items: {len(pub)}")
print(f"Full items:   {len(full)}")
print(f"Choices: {choice_count} | Fills: {fill_count} | Solves: {solve_count}")
print(f"Multi-choice (mcq_multi): {mcq_multi_count}")
print(f"Unique KPs covered: {len(kp_usage)}")
print(f"Difficulty range: {min(diffs)} - {max(diffs)}")
print("=" * 60)
if errors:
    print("ERRORS:")
    for e in errors[:20]:
        print("  -", e)
    print(f"Total errors: {len(errors)}")
else:
    print("VALIDATION PASSED")
if warnings:
    print("WARNINGS:")
    for w in warnings:
        print("  -", w)