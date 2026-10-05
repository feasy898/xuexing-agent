"""Fix difficulty gaps in question modules.
For each KP, ensure the second question has a higher difficulty than the first.
Re-write difficulty values to spread the gradient.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Reload modules to ensure latest
import importlib
import grade1_qs, grade2_qs, grade3_qs, grade4_qs, grade5_qs, grade6_qs

ALL_MODULES = [grade1_qs, grade2_qs, grade3_qs, grade4_qs, grade5_qs, grade6_qs]

# Per-grade difficulty rules
GRADE_DIFF = {
    1: (0.20, 0.40),   # grade 1: easy
    2: (0.20, 0.45),
    3: (0.25, 0.50),
    4: (0.25, 0.55),
    5: (0.30, 0.60),
    6: (0.35, 0.60),
}

# A small function that gives the second question a higher difficulty
import re

def adjust_module(mod, grade):
    lo, hi = GRADE_DIFF[grade]
    # Group by KP
    by_kp = {}
    for i, q in enumerate(mod.Q if hasattr(mod, 'Q') else []):
        pass
    # Build new difficulty list
    items = []
    kp_indices = {}
    for i, q in enumerate(mod.GRADE_Q if hasattr(mod, 'GRADE_Q') else []):
        pass

# We need to modify the modules' GRADE_Q list directly. Each module has its own GRADE_Q.

def fix_module(filepath, grade):
    """Read module, group by KP, ensure 2 difficulties spread gradient."""
    import re
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # We'll do simple text manipulation: find each {"kp":"X",..."difficulty":D,}
    # and increase difficulty for 2nd question of each KP
    lo, hi = GRADE_DIFF[grade]
    # Parse: match each entry block - using non-greedy with proper escaping
    pattern = re.compile(
        r'(\{"kp":\s*"(kp_eng\d+_[^"]+)".*?"difficulty":\s*)(\d+\.?\d*)',
        re.DOTALL
    )

    # We need to track per-KP encounter
    matches = list(pattern.finditer(content))
    # Group by KP and figure out which is first / second
    seen = {}
    edits = []  # (start, end, new_diff_str)
    for m in matches:
        kp = m.group(2)
        seen[kp] = seen.get(kp, 0) + 1
        idx = seen[kp]  # 1 for first, 2 for second
        # Choose new difficulty
        if idx == 1:
            new_diff = lo + 0.05
        else:
            new_diff = min(hi, lo + 0.20)  # higher
        # Locate just the digits and replace
        diff_start = m.start(3)
        diff_end = m.end(3)
        edits.append((diff_start, diff_end, f"{new_diff:.2f}"))

    # Apply edits in reverse order to keep offsets stable
    new_content = content
    for start, end, val in reversed(edits):
        new_content = new_content[:start] + val + new_content[end:]

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    return len(edits)


def main():
    files = [
        ('grade1_qs.py', 1),
        ('grade2_qs.py', 2),
        ('grade3_qs.py', 3),
        ('grade4_qs.py', 4),
        ('grade5_qs.py', 5),
        ('grade6_qs.py', 6),
    ]
    for fname, grade in files:
        path = Path(__file__).resolve().parent / fname
        n = fix_module(str(path), grade)
        print(f'{fname}: adjusted {n} difficulty values')


if __name__ == '__main__':
    main()