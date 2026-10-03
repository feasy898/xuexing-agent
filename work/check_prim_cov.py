import json
import sys

sys.path.insert(0, "src")
from xuexing.standard_coverage import check_coverage_dicts

PAIRS = [
    ("math_standard_2022_topics_grade1_3.json", [1, 2, 3]),
    ("math_standard_2022_topics_grade4_6.json", [4, 5, 6]),
]

for f, grades in PAIRS:
    d = json.load(open("data/curriculum/" + f, encoding="utf-8"))
    kps = []
    for g in grades:
        kps += json.load(open("data/knowledge/math_grade%d.json" % g, encoding="utf-8"))["knowledge_points"]
    r = check_coverage_dicts(kps, d)
    print(
        "%s: rate=%.2f uncovered=%d unmatched=%d"
        % (f, r.coverage_rate, len(r.uncovered_topic_ids), len(r.unmatched_kp_ids))
    )
    if r.uncovered_topic_ids:
        print("   uncovered:", r.uncovered_topic_ids)
    if r.unmatched_kp_ids:
        print("   unmatched:", r.unmatched_kp_ids)
