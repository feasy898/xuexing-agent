import json

pub = json.load(open('data/verification/candidates_hs/h12c_public.json', encoding='utf-8'))
led = json.load(open('data/verification/candidates_hs/h12c_ledger_indep.json', encoding='utf-8'))

pub_ids = [it['id'] for it in pub]
ans = led['answers']

print('public items:', len(pub_ids), 'unique:', len(set(pub_ids)))
print('answer keys:', len(ans))
missing = [i for i in pub_ids if i not in ans]
extra = [k for k in ans if k not in pub_ids]
print('missing:', missing)
print('extra:', extra)
bad = {k: v for k, v in ans.items() if v not in ('A', 'B', 'C', 'D')}
print('non-A/B/C/D values:', bad)
print('agent_id ok:', led['agent_id'] == 'hsg-indep-w1-20261003')
print('COVERAGE COMPLETE:', not missing and not extra and not bad and len(ans) == len(pub_ids))
