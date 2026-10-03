import json
import sys

sys.path.insert(0, "src")
from xuexing.standard_coverage import check_coverage_dicts

FILES = {
    "math_standard_2022_topics_grade1_3.json": [1, 2, 3],
    "math_standard_2022_topics_grade4_6.json": [4, 5, 6],
}

for f, grades in FILES.items():
    p = "data/curriculum/" + f
    d = json.load(open(p, encoding="utf-8"))
    changed = False
    for dom in d.get("domains", []):
        if "domain" not in dom and "name" in dom:
            dom["domain"] = dom.pop("name")
            changed = True
        for th in dom.get("themes", []):
            if "theme" not in th and "name" in th:
                th["theme"] = th.pop("name")
                changed = True
    if changed:
        with open(p, "w", encoding="utf-8", newline="\n") as fo:
            json.dump(d, fo, ensure_ascii=False, indent=2)
            fo.write("\n")
    kps = []
    for g in grades:
        kps += json.load(open("data/knowledge/math_grade%d.json" % g, encoding="utf-8"))["knowledge_points"]
    try:
        r = check_coverage_dicts(kps, d)
        print(
            "%s: changed=%s rate=%.2f uncovered=%d unmatched=%d"
            % (f, changed, r.coverage_rate, len(r.uncovered_topic_ids), len(r.unmatched_kp_ids))
        )
        print("   uncovered:", r.uncovered_topic_ids)
        print("   unmatched:", r.unmatched_kp_ids)
    except Exception as e:
        print("%s: PARSE FAIL %s" % (f, e))
