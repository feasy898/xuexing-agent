# -*- coding: utf-8 -*-
"""补齐后自检：JSON 合法性 / 覆盖率 / prereqs / id 唯一性 / math_all 一致性。"""
import glob
import json
import sys
import io

sys.path.insert(0, 'D:/new-workspace/学情agent/xuexing-agent/src')
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from xuexing.standard_coverage import check_coverage_dicts

ROOT = 'D:/new-workspace/学情agent/xuexing-agent'
NEW_IDS = ['kp_p4_bignum_rewrite', 'kp_p4_optimize',
           'kp_p5_common_factor_multiple', 'kp_p5_combination']

failures = []

# ---------- 1) 全部 math 年级 JSON 可解析 + id 唯一（math_all 是合并视图，不参与唯一性扫描） ----------
all_ids = {}
for path in sorted(glob.glob(f'{ROOT}/data/knowledge/math_grade*.json')):
    data = json.load(open(path, encoding='utf-8'))  # 解析失败会抛异常
    for kp in data.get('knowledge_points', []):
        if kp['id'] in all_ids:
            failures.append(f"duplicate kp id: {kp['id']} ({all_ids[kp['id']]} & {path})")
        all_ids[kp['id']] = path
merged = json.load(open(f'{ROOT}/data/knowledge/math_all.json', encoding='utf-8'))['knowledge_points']
all_ids.update({k['id']: 'math_all.json' for k in merged})  # prereq 允许引用合并视图内 id
print(f'[1] math 年级 JSON 解析通过，年级文件 kp={len(all_ids) - len(merged)}，math_all={len(merged)}，'
      f'年级文件 id 重复数={sum(1 for f in failures if f.startswith("duplicate"))}')

# ---------- 2) 新 KP 字段齐全、落在正确年级文件末尾、prereqs 均已存在 ----------
grade_files = {g: json.load(open(f'{ROOT}/data/knowledge/math_grade{g}.json', encoding='utf-8'))
               for g in (4, 5, 6)}
for nid, g in [('kp_p4_bignum_rewrite', 4), ('kp_p4_optimize', 4),
               ('kp_p5_common_factor_multiple', 5), ('kp_p5_combination', 5)]:
    kps = grade_files[g]['knowledge_points']
    hit = [i for i, k in enumerate(kps) if k['id'] == nid]
    assert len(hit) == 1, f'{nid} not found exactly once in grade{g}'
    kp = kps[hit[0]]
    for field in ('id', 'name', 'subject', 'grade', 'cluster', 'description', 'standard_ref'):
        assert str(kp.get(field, '')).strip(), f'{nid}: empty {field}'
    assert kp['grade'] == g and kp['subject'] == 'math'
    for pr in kp.get('prereqs', []):
        if pr not in all_ids:
            failures.append(f'{nid}: prereq {pr} 不存在于任何知识文件')
    print(f"[2] {nid} @ grade{g} 数组第 {hit[0] + 1}/{len(kps)} 位，prereqs={kp.get('prereqs')} OK")

# ---------- 3) 全库 prereqs 悬挂引用检查（math 文件） ----------
for path in sorted(glob.glob(f'{ROOT}/data/knowledge/math_*.json')):
    for kp in json.load(open(path, encoding='utf-8')).get('knowledge_points', []):
        for pr in kp.get('prereqs', []):
            if pr not in all_ids:
                failures.append(f"{kp['id']} ({path}): 悬挂 prereq {pr}")
print('[3] 全库 prereq 悬挂引用检查完成')

# ---------- 4) math_all 合并视图与年级文件逐字段一致（p4/p5/p6） ----------
allk = {k['id']: k for k in json.load(open(f'{ROOT}/data/knowledge/math_all.json', encoding='utf-8'))['knowledge_points']}
for g in (4, 5, 6):
    for kp in grade_files[g]['knowledge_points']:
        if allk.get(kp['id']) != kp:
            failures.append(f"math_all 与 grade{g} 不一致: {kp['id']}")
print(f'[4] math_all 含 p4/p5/p6 全部 {sum(len(v["knowledge_points"]) for v in grade_files.values())} 条且逐字段一致')

# ---------- 5) 覆盖检查（主判定：grades 4-6 KP x grade4_6 课标清单） ----------
topics = json.load(open(f'{ROOT}/data/curriculum/math_standard_2022_topics_grade4_6.json', encoding='utf-8'))
kps = [kp for g in (4, 5, 6) for kp in grade_files[g]['knowledge_points']]
rep = check_coverage_dicts(kps, topics)
print(f"[5] kps={len(kps)} topics={len(rep.topics)} covered={len(rep.covered_topic_ids)} "
      f"coverage_rate={rep.coverage_rate:.4f}")
print('    uncovered:', rep.uncovered_topic_ids)
print('    unmatched:', rep.unmatched_kp_ids)
if rep.coverage_rate < 0.95:
    failures.append(f"coverage_rate {rep.coverage_rate:.4f} < 0.95")
if rep.unmatched_kp_ids:
    failures.append(f"仍有 unmatched KP: {rep.unmatched_kp_ids}")

# 11 个原 uncovered topic 现在的命中 KP
by_topic = {}
for m in rep.matches:
    for tid in m.topic_ids:
        by_topic.setdefault(tid, []).append(m.kp_id)
for tid in ('t01_bignum', 't12_common', 't13_multiple', 't20_perim', 't21_area', 't24_poly_area',
            't28_pos_dir', 't30_motion', 't31_table', 't36_optimize', 't40_combo'):
    print(f'    {tid}: {by_topic.get(tid, [])}')

# ---------- 6) 第一学段清单不受影响（grade1_3 KPs x grade1_3 topics，回归对照） ----------
topics13 = json.load(open(f'{ROOT}/data/curriculum/math_standard_2022_topics_grade1_3.json', encoding='utf-8'))
kps13 = []
for g in (1, 2, 3):
    kps13.extend(json.load(open(f'{ROOT}/data/knowledge/math_grade{g}.json', encoding='utf-8'))['knowledge_points'])
rep13 = check_coverage_dicts(kps13, topics13)
print(f"[6] 第一学段回归：rate={rep13.coverage_rate:.4f} uncovered={len(rep13.uncovered_topic_ids)} "
      f"unmatched={len(rep13.unmatched_kp_ids)}（未改动 1-3 年级文件，仅对照）")

print()
if failures:
    print('FAILURES:')
    for f in failures:
        print(' -', f)
    sys.exit(1)
print('ALL CHECKS PASSED')
