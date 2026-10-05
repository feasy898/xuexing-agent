# -*- coding: utf-8 -*-
"""第一学段（1-3 年级）课标覆盖检查（临时脚本，gap 补齐前后各跑一次）。

用 src 内置的 xuexing.standard_coverage.check_coverage_dicts：
  kp_dicts = data/knowledge/math_grade{1,2,3}.json 的 knowledge_points 合并（按 1→2→3 原序）
  topics   = data/curriculum/math_standard_2022_topics_grade1_3.json

输出：coverage_rate、uncovered_topic_ids、unmatched_kp_ids、
      每个 topic 的覆盖 KP 列表、每个 KP 命中的 topic 列表。
"""
import io
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))

from xuexing.standard_coverage import check_coverage_dicts  # noqa: E402

TOPICS_PATH = os.path.join(REPO, "data", "curriculum", "math_standard_2022_topics_grade1_3.json")
KP_PATHS = [os.path.join(REPO, "data", "knowledge", "math_grade%d.json" % n) for n in (1, 2, 3)]


def load(path):
    with io.open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def main():
    topics_data = load(TOPICS_PATH)
    kp_dicts = []
    for path in KP_PATHS:
        kp_dicts.extend(load(path)["knowledge_points"])

    report = check_coverage_dicts(kp_dicts, topics_data)
    topic_name = {t.id: "%s/%s/%s" % (t.domain, t.theme, t.name) for t in report.topics}

    print("total topics: %d | total KPs: %d" % (len(report.topics), len(report.matches)))
    print("coverage_rate: %r" % report.coverage_rate)
    print("is_complete: %r" % report.is_complete())
    print("uncovered_topic_ids (%d): %s" % (len(report.uncovered_topic_ids), list(report.uncovered_topic_ids)))
    print("unmatched_kp_ids (%d): %s" % (len(report.unmatched_kp_ids), list(report.unmatched_kp_ids)))

    cov = {}
    for m in report.matches:
        for tid in m.topic_ids:
            cov.setdefault(tid, []).append(m.kp_id)
    print("\n--- per-topic covering KPs ---")
    for t in report.topics:
        kps = cov.get(t.id, [])
        print("%s  %s  <-  %s" % (t.id, t.name, ",".join(kps) if kps else "<UNCOVERED>"))
    print("\n--- per-KP matched topics ---")
    for m in report.matches:
        if not m.topic_ids:
            print("%s  <UNMATCHED>" % m.kp_id)


if __name__ == "__main__":
    main()
