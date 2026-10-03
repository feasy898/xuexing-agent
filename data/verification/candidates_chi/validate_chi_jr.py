# -*- coding: utf-8 -*-
"""validate_chi_jr.py —— 对 chi_jr 候选题四项产出的独立校验（对照 ask 硬性要求）。"""
import json, os, re
from collections import Counter

BASE = os.path.dirname(os.path.abspath(__file__))
KNOW = os.path.join(BASE, "..", "..", "..", "data", "knowledge")

with open(os.path.join(BASE, "chi_jr_public.json"), encoding="utf-8") as f:
    public = json.load(f)
with open(os.path.join(BASE, "chi_jr_full.json"), encoding="utf-8") as f:
    full = json.load(f)
with open(os.path.join(BASE, "chi_jr_ledger_gen.json"), encoding="utf-8") as f:
    ledger = json.load(f)

print(f"public: {len(public)} items | full: {len(full)} items | ledger: {len(ledger['answers'])} answers")

# T1 ledger 结构
assert ledger["agent_id"] == "chi-gen-w1-20261003" and ledger["solver"] == "MiniMax-M3"
assert ledger["method"] == "generator self-answer" and isinstance(ledger["answers"], dict)
print("✓ ledger 结构（agent_id/solver/method/answers 为字典）")

# T2 id 唯一、三份同序
pub_ids = [i["id"] for i in public]
full_ids = [i["id"] for i in full]
assert pub_ids == full_ids == list(ledger["answers"].keys()), "顺序不一致"
assert len(set(pub_ids)) == len(pub_ids), "id 重复"
assert all(re.fullmatch(r"chi_chi_jr_\d{4}", i) for i in pub_ids), "id 格式不符"
print(f"✓ id 形如 chi_chi_jr_XXXX，三份文件同序且唯一（共 {len(pub_ids)} 题）")

# T3 public 不含答案/解析
leaks = [i["id"] for i in public if "answer" in i or "solution" in i or "writing_prompt" in i]
assert not leaks, leaks
print("✓ public.json 无 answer/solution/writing_prompt 泄漏")

# T4 full 有 answer + solution，作文有 writing_prompt
assert all("answer" in i and "solution" in i for i in full)
ess = [i for i in full if i["form"] == "essay"]
assert all("writing_prompt" in i and set(("题目", "字数", "评分维度")) <= set(i["writing_prompt"]) for i in ess)
assert all(50 <= len(i["solution"]) <= 100 for i in ess), "作文 solution 需 50-100 字"
print(f"✓ full.json 每题都有 answer/solution；{len(ess)} 篇作文含题目/字数/评分维度，且评分要点 50-100 字")

# T5 KP 注册与唯一
valid = set()
for g in (7, 8, 9):
    valid |= {k["id"] for k in json.load(open(os.path.join(KNOW, f"chinese_grade{g}.json"), encoding="utf-8"))["knowledge_points"]}
for i in public:
    assert len(i["kps"]) == 1 and i["kps"][0] in valid, i["id"]
cnt = Counter(i["kps"][0] for i in public)
assert set(cnt) == valid, f"未覆盖 {len(valid - set(cnt))} 个 KP"
assert all(2 <= v <= 3 for v in cnt.values()), f"配额越界 {[ (k,v) for k,v in cnt.items() if not 2<=v<=3 ]}"
print(f"✓ 每个 KP 1 个且已注册；{len(cnt)}/189 个 KP 全覆盖，每题 KP 2-3 题配额")

# T6 难度（初中 0.30-0.75）
bad = [(i["id"], i["difficulty"]) for i in public if not 0.30 <= i["difficulty"] <= 0.75]
assert not bad, bad
print(f"✓ difficulty 全部落在 0.30-0.75（实际 {min(i['difficulty'] for i in public)}-{max(i['difficulty'] for i in public)}）")

# T7 choice 四选项 + 答案 ABCD
ch = [i for i in public if i["item_type"] == "choice"]
assert all(len(i.get("options", [])) == 4 and all(o.startswith(("A.", "B.", "C.", "D.")) for o in i["options"]) for i in ch)
assert all(ledger["answers"][i["id"]] in ("A", "B", "C", "D") for i in ch)
print(f"✓ {len(ch)} 道选择题均为 4 选项（A./B./C./D.），答案 ∈ ABCD")

# T8 fill/solve 中文短答案
fs = [i for i in public if i["item_type"] in ("fill", "solve")]
assert all(isinstance(ledger["answers"][i["id"]], str) and 0 < len(ledger["answers"][i["id"]]) <= 400 for i in fs)
assert all(not re.search(r"[A-Za-z]{4,}", ledger["answers"][i["id"]]) for i in fs), "fill/solve 答案应中文"
print(f"✓ {len(fs)} 道 fill/solve 答案均为中文短字符串（≤400 字）")

# T9 ledger 与 full 答案一致
mis = [(i["id"], i["answer"], ledger["answers"][i["id"]]) for i in full if i["answer"] != ledger["answers"].get(i["id"])]
assert not mis, mis[:5]
print("✓ ledger 答案与 full.json 完全一致")

# T10 source
assert all(i["source"] == "llm_generated" for i in public)
print("✓ source 全部为 llm_generated")

print("\n==== 题型/学段分布 ====")
print("item_type:", dict(Counter(i["item_type"] for i in public)))
print("form:", dict(Counter(i["form"] for i in public)))
print("学段:", dict(Counter("七" if i["kps"][0].startswith("kp_chi7") else "八" if i["kps"][0].startswith("kp_chi8") else "九" for i in public)))
print(f"作文 {len(ess)} 篇，含命题/半命题/材料/话题/仿写/读后感/演讲稿/游记/现代诗等形态")
print("\n✅ chi_jr 批次全部校验通过")
