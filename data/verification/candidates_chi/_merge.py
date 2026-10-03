# -*- coding: utf-8 -*-
import json, sys, io, collections

base = r'D:\new-workspace\学情agent\xuexing-agent\data\verification\candidates_chi'
sys.path.insert(0, base)
from _ans1 import A1
from _ans2 import A2

A = dict(A1)
A.update(A2)

src = json.load(io.open(base + r'\chi_jr_public.json', encoding='utf-8'))
ids = [x['id'] for x in src]

missing = [i for i in ids if i not in A]
extra = [k for k in A if k not in ids]
print('src items:', len(ids), 'answers:', len(A))
print('missing:', len(missing), missing[:20])
print('extra:', len(extra), extra[:20])
if missing or extra:
    raise SystemExit(1)

# sanity: choice items must be a single A-D letter
byid = {x['id']: x for x in src}
bad = []
for i in ids:
    it = byid[i]
    a = A[i]
    if it['item_type'] == 'choice':
        if a not in ('A', 'B', 'C', 'D'):
            bad.append((i, a))
    if not isinstance(a, str) or not a.strip():
        bad.append((i, repr(a)))
print('bad format:', len(bad), bad[:10])

out = {
    "agent_id": "chi-indep-w1-20261003",
    "solver": "step-5-preview",
    "method": "blind: only stem+options, independent solve",
    "answers": {i: A[i] for i in ids},
}
p = base + r'\chi_jr_ledger_indep.json'
with io.open(p, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

# verify written file
chk = json.load(io.open(p, encoding='utf-8'))
assert list(chk['answers'].keys()) == ids, 'key order/coverage mismatch'
print('written:', p, 'answers in file:', len(chk['answers']))
c = collections.Counter(byid[i]['item_type'] for i in ids)
print('by item_type:', dict(c))
print('choice answers distribution:', collections.Counter(A[i] for i in ids if byid[i]['item_type'] == 'choice'))
