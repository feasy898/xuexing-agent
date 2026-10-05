import json, os, sys

dir = 'xuexing-agent/data/knowledge'
files = [
    'geography_grade7.json',
    'geography_grade8.json',
    'geography_grade10.json',
    'geography_grade11.json',
    'geography_grade12.json',
]

all_kps = {}
missing = []
empty_fields = []
total_kps = 0

# Pass 1: load all KPs and collect IDs
for f in files:
    fp = os.path.join(dir, f)
    with open(fp, 'r', encoding='utf-8') as fh:
        data = json.load(fh)
    print(f"{f}: {len(data['knowledge_points'])} KPs")
    total_kps += len(data['knowledge_points'])
    for kp in data['knowledge_points']:
        all_kps[kp['id']] = kp

# Pass 2: validate
for f in files:
    fp = os.path.join(dir, f)
    with open(fp, 'r', encoding='utf-8') as fh:
        data = json.load(fh)
    for kp in data['knowledge_points']:
        # duplicate check
        if sum(1 for k in all_kps.values() if k['id'] == kp['id']) > 1:
            missing.append(f"dup: {kp['id']} in {f}")
        for field in ['id','name','subject','grade','cluster','description','standard_ref','prereqs','textbook_ref']:
            val = kp.get(field)
            if val is None or (isinstance(val, str) and val.strip() == ''):
                empty_fields.append(f"{kp['id']} missing {field}")
        for p in kp.get('prereqs', []):
            if p not in all_kps:
                missing.append(f"missing prereq: {p} (from {kp['id']})")

print(f"Total KPs: {total_kps}")
print(f"Unique IDs: {len(all_kps)}")
if missing:
    print("MISSING PREREQS/DUPES:")
    for x in missing:
        print("  " + x)
else:
    print("No missing prereqs or duplicates")
if empty_fields:
    print("EMPTY FIELDS:")
    for x in empty_fields:
        print("  " + x)
else:
    print("No empty required fields")

sys.exit(0 if not missing and not empty_fields else 1)
