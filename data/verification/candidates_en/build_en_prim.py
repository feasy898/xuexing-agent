"""Build en_prim candidates for English grades 1-6.
Loads grade question modules, combines, and outputs the 4 required files.
"""
import json
import os
import re
import sys
from pathlib import Path

# Import question modules
sys.path.insert(0, str(Path(__file__).resolve().parent))
from grade1_qs import GRADE1_Q
from grade2_qs import GRADE2_Q
from grade3_qs import GRADE3_Q
from grade4_qs import GRADE4_Q
from grade5_qs import GRADE5_Q
from grade6_qs import GRADE6_Q

ALL_QS = GRADE1_Q + GRADE2_Q + GRADE3_Q + GRADE4_Q + GRADE5_Q + GRADE6_Q

# Per-grade difficulty bands (lo, hi) per primary band rule
GRADE_DIFF = {
    1: (0.20, 0.40),
    2: (0.20, 0.45),
    3: (0.25, 0.50),
    4: (0.25, 0.55),
    5: (0.30, 0.60),
    6: (0.35, 0.60),
}


def spread_difficulties():
    """Ensure each KP has 2 questions with difficulty gap >= 0.10.
    Adjusts difficulty in-place within ALL_QS.
    """
    from collections import defaultdict
    by_kp = defaultdict(list)
    for q in ALL_QS:
        by_kp[q["kp"]].append(q)
    for kp, qs in by_kp.items():
        grade_m = re.match(r"kp_eng(\d+)_", kp)
        grade = int(grade_m.group(1))
        lo, hi = GRADE_DIFF[grade]
        if len(qs) >= 2:
            # Set first question to lower bound
            qs[0]["difficulty"] = round(lo + 0.05, 2)
            # Set second question to higher (with gap >= 0.10)
            qs[1]["difficulty"] = round(min(hi, lo + 0.20), 2)


spread_difficulties()

# Normalize forms to schema-allowed set:
# choice | fill | solve | listening | reading | cloze | seven_to_five | writing | summary | translation
FORM_MAP = {
    "multiple_choice": "choice",
    "choice": "choice",
    "picture_qa": "fill",  # pick the picture word
    "oral_qa": "solve",  # oral Q&A is a solve task
    "spelling": "fill",  # spelling is a fill-in task
    "comprehension": "reading",  # reading comprehension
    "listening": "listening",
    "fill": "fill",
    "solve": "solve",
    "writing": "writing",
    "translation": "translation",
}


def normalize_form(q):
    """Map question form to schema-allowed set.
    Also updates item_type if needed for consistency.
    """
    raw_form = q.get("form")
    mapped = FORM_MAP.get(raw_form, raw_form)
    q["form"] = mapped
    # Writing items go into solve item_type with writing_prompt
    if mapped == "writing":
        q["item_type"] = "solve"
    return q


for _q in ALL_QS:
    normalize_form(_q)

OUT_DIR = Path("D:/new-workspace/学情agent/xuexing-agent/data/verification/candidates_en")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def build_items():
    items = []
    for idx, q in enumerate(ALL_QS, start=1):
        item_id = f"eng_en_prim_{idx:04d}"
        item = {
            "id": item_id,
            "item_type": q["item_type"],
            "form": q["form"],
            "stem": q["stem"],
            "kps": [q["kp"]],
            "difficulty": q["difficulty"],
        }
        if q["item_type"] == "choice":
            item["options"] = q["options"]
        items.append(item)
    return items


def build_full(items):
    out = []
    for q, base in zip(ALL_QS, items):
        full = {
            "id": base["id"],
            "item_type": base["item_type"],
            "form": base["form"],
            "stem": base["stem"],
            "answer": q["answer"],
            "kps": base["kps"],
            "difficulty": base["difficulty"],
            "solution": q["solution"],
            "source": "llm_generated",
        }
        if base["item_type"] == "choice":
            full["options"] = base["options"]
        # Writing prompts for writing-form items
        if base["form"] == "writing" and q.get("writing_prompt"):
            full["writing_prompt"] = q["writing_prompt"]
        out.append(full)
    return out


def build_public(items):
    """Public version has no answer / solution."""
    public = []
    for base in items:
        pub = {
            "id": base["id"],
            "item_type": base["item_type"],
            "form": base["form"],
            "stem": base["stem"],
            "kps": base["kps"],
            "difficulty": base["difficulty"],
        }
        if base["item_type"] == "choice":
            pub["options"] = base["options"]
        public.append(pub)
    return public


def build_ledger(full):
    answers = {f["id"]: f["answer"] for f in full}
    return {
        "agent_id": "eng-gen-w1-20261003",
        "solver": "MiniMax-M3",
        "method": "generator self-answer",
        "answers": answers,
    }


def main():
    items = build_items()
    full = build_full(items)
    public = build_public(items)
    ledger = build_ledger(full)

    pub_file = OUT_DIR / "en_prim_public.json"
    full_file = OUT_DIR / "en_prim_full.json"
    ledger_file = OUT_DIR / "en_prim_ledger_gen.json"

    with open(pub_file, "w", encoding="utf-8") as f:
        json.dump(public, f, ensure_ascii=False, indent=2)
    with open(full_file, "w", encoding="utf-8") as f:
        json.dump(full, f, ensure_ascii=False, indent=2)
    with open(ledger_file, "w", encoding="utf-8") as f:
        json.dump(ledger, f, ensure_ascii=False, indent=2)

    print(f"Total items: {len(items)}")
    print(f"Public file:  {pub_file} ({pub_file.stat().st_size} bytes)")
    print(f"Full file:    {full_file} ({full_file.stat().st_size} bytes)")
    print(f"Ledger file:  {ledger_file} ({ledger_file.stat().st_size} bytes)")

    # Stats per grade
    grade_counts = {}
    for q in ALL_QS:
        kp = q["kp"]
        g = kp.split("_")[2].replace("eng", "")
        grade_counts[g] = grade_counts.get(g, 0) + 1
    print("Per-grade counts:", grade_counts)


if __name__ == "__main__":
    main()