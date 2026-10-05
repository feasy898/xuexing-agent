# -*- coding: utf-8 -*-
"""History KP files self-check: JSON validity, id uniqueness, prereq resolution, field non-emptiness, counts."""
import json, glob, io, sys, re, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
base = os.path.dirname(os.path.abspath(__file__))
files = ['history_grade%d.json' % n for n in (7, 8, 9, 10, 11, 12)]
all_kps = {}
errors = []
counts = {}

for fn in files:
    path = os.path.join(base, fn)
    try:
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        errors.append('%s: JSON parse error: %s' % (fn, e))
        continue
    if data.get('subject') != 'history':
        errors.append('%s: subject is %r' % (fn, data.get('subject')))
    band = data.get('grade_band')
    grade = band[0] if band else None
    if band != [7] and fn == 'history_grade7.json': pass
    kps = data.get('knowledge_points', [])
    counts[fn] = len(kps)
    for kp in kps:
        kid = kp.get('id', '')
        if kid in all_kps:
            errors.append('DUPLICATE id %s (%s and %s)' % (kid, all_kps[kid], fn))
        all_kps[kid] = fn
        if not re.match(r'^kp_hist%d_[a-z0-9_]+$' % (grade or 0), kid):
            errors.append('%s: bad id format %r (grade=%s)' % (fn, kid, grade))
        if kp.get('subject') != 'history':
            errors.append('%s/%s: wrong subject' % (fn, kid))
        if kp.get('grade') != grade:
            errors.append('%s/%s: grade mismatch (%s)' % (fn, kid, kp.get('grade')))
        for fld in ('name', 'cluster', 'description', 'standard_ref', 'textbook_ref'):
            v = kp.get(fld, '')
            if not isinstance(v, str) or not v.strip():
                errors.append('%s/%s: empty field %s' % (fn, kid, fld))
        pr = kp.get('prereqs')
        if pr is None or not isinstance(pr, list):
            errors.append('%s/%s: prereqs missing/not list' % (fn, kid))

# prereq resolution against the union of history files
for fn in files:
    try:
        with open(os.path.join(base, fn), encoding='utf-8') as f:
            kps = json.load(f)['knowledge_points']
    except Exception:
        continue
    for kp in kps:
        for p in kp.get('prereqs', []):
            if p not in all_kps:
                errors.append('%s/%s: unresolved prereq %r' % (fn, kp['id'], p))
            elif p == kp['id']:
                errors.append('%s/%s: self prereq' % (fn, kp['id']))

# id conflicts with the rest of the knowledge library
hist_ids = set(all_kps)
for path in glob.glob(os.path.join(base, '*.json')):
    if os.path.basename(path) in files or os.path.basename(path).startswith('_check'):
        continue
    try:
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        continue
    for kp in data.get('knowledge_points', []):
        if kp.get('id') in hist_ids:
            errors.append('COLLISION with library: %s in %s' % (kp['id'], os.path.basename(path)))

print('--- per-file KP counts vs research doc §2.3 ranges ---')
# research doc per-册 ranges collapsed to per-year
ranges = {
    'history_grade7.json':  (110, 150),   # 七上60-80 + 七下50-70
    'history_grade8.json':  (90, 125),    # 八上50-70 + 八下40-55
    'history_grade9.json':  (105, 145),   # 九上55-75 + 九下50-70
    'history_grade10.json': (100, 130),   # 高一(纲要上下)
    'history_grade11.json': (75, 110),    # 高二(选必3册)
    'history_grade12.json': (30, 50),     # 高三(复习)
}
total = 0
for fn in files:
    c = counts.get(fn, 0)
    lo, hi = ranges[fn]
    total += c
    dev = '' if lo <= c <= hi else '  <-- outside range (within +-20%%: %d..%d)' % (int(lo * 0.8), hi)
    print('%s: %d (target %d-%d)%s' % (fn, c, lo, hi, dev))
print('TOTAL: %d (research doc total 510-710)' % total)

print('--- errors: %d ---' % len(errors))
for e in errors[:40]:
    print('  ' + e)
print('OK' if not errors else 'FAILED')
