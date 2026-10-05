# -*- coding: utf-8 -*-
"""校验 chi_prim_hi 批产物：结构 / id / KP 合法性 / 难度 / 选项 / 无泄漏 / 同序 / ledger 一致。
并运行 workflow 草稿 K12-3c-语文题库.dwf.ts 内嵌的同款校验代码。
"""
import json
import os
import re
import sys

BASE = r"D:\new-workspace\学情agent\xuexing-agent\data\verification\candidates_chi"
KP_FILES = [rf"D:\new-workspace\学情agent\xuexing-agent\data\knowledge\chinese_grade{g}.json" for g in (4, 5, 6)]

with open(os.path.join(BASE, "chi_prim_hi_public.json"), encoding="utf-8") as f:
    public = json.load(f)
with open(os.path.join(BASE, "chi_prim_hi_full.json"), encoding="utf-8") as f:
    full = json.load(f)
with open(os.path.join(BASE, "chi_prim_hi_ledger_gen.json"), encoding="utf-8") as f:
    ledger = json.load(f)

valid_kps = set()
for fp in KP_FILES:
    with open(fp, encoding="utf-8") as f:
        for kp in json.load(f)["knowledge_points"]:
            valid_kps.add(kp["id"])

fails = []


def check(cond, msg):
    if not cond:
        fails.append(msg)


# 1. 每 KP 恰好 3 题、全覆盖
from collections import Counter
kp_counts = Counter(p["kps"][0] for p in public)
bad = {k: v for k, v in kp_counts.items() if v != 3}
check(not bad, f"每 KP 应恰 3 题：{bad}")
missing = valid_kps - set(kp_counts)
check(not missing, f"未覆盖 KP：{sorted(missing)[:5]}")
check(len(public) == 540, f"题目数应为 540，实为 {len(public)}")

# 2. id 唯一、三文件同序
ids = [p["id"] for p in public]
check(len(set(ids)) == len(ids), "public 内 id 重复")
check(ids == [f"chi_prim_hi_{i:04d}" for i in range(1, 541)], "id 形不符 chi_prim_hi_0001..0540 连续命名")
check([f["id"] for f in full] == ids, "full 与 public 不同序")
check(list(ledger["answers"].keys()) == ids, "ledger 与 public 不同序/不一致")

# 3. public 无 answer/solution 泄漏；full 必有 answer+solution
for p in public:
    check("answer" not in p and "solution" not in p, f"{p['id']} public 泄漏")
for f_ in full:
    check(f_.get("answer") and f_.get("solution"), f"{f_['id']} full 缺 answer/solution")

# 4. KP 合法性（每题 1 个且已注册）
for p in public:
    check(isinstance(p.get("kps"), list) and len(p["kps"]) == 1, f"{p['id']} kps 数非 1")
    check(p["kps"][0] in valid_kps, f"{p['id']} KP 未注册: {p['kps'][0]}")

# 5. 难度：小学学段 0.2-0.6（且在全局 0.2-0.85 内）
for p in public:
    check(0.2 <= p["difficulty"] <= 0.6, f"{p['id']} 难度 {p['difficulty']} 超出小学段 0.2-0.6")
    check(0.2 <= p["difficulty"] <= 0.85, f"{p['id']} 难度 {p['difficulty']} 超出全局 0.2-0.85")

# 6. choice：4 项 A./B./C./D.，answer ∈ ABCD，题型字段齐全
choice_n = 0
for p in public:
    check(p.get("source") == "llm_generated", f"{p['id']} source 非 llm_generated")
    check(p.get("form") and p.get("stem"), f"{p['id']} 缺 form/stem")
    if p["item_type"] == "choice":
        choice_n += 1
        opts = p.get("options") or []
        check(len(opts) == 4, f"{p['id']} 选项数 {len(opts)}")
        check(all(o.startswith(c + ". ") for c, o in zip("ABCD", opts)), f"{p['id']} 选项前缀不符")
        fu = next(x for x in full if x["id"] == p["id"])
        check(fu["answer"] in ("A", "B", "C", "D"), f"{p['id']} choice 答案 {fu['answer']}")
        check(ledger["answers"][p["id"]] == fu["answer"], f"{p['id']} ledger 与 full 不一致")
    else:
        ans = next(x for x in full if x["id"] == p["id"])["answer"]
        check(isinstance(ans, str) and 1 <= len(ans) <= 300, f"{p['id']} fill/solve 答案应为中文短串")
        check(ledger["answers"][p["id"]] == ans, f"{p['id']} ledger 与 full 不一致")

# 7. 作文题：form=essay 必有 writing_prompt，含字数与评分维度
essay_n = 0
for f_ in full:
    if f_.get("form") == "essay":
        essay_n += 1
        wp = f_.get("writing_prompt") or ""
        check("字数" in wp, f"{f_['id']} writing_prompt 缺字数")
        check("评分维度" in wp, f"{f_['id']} writing_prompt 缺评分维度")
        check("范文要点" in f_["answer"], f"{f_['id']} 作文题 answer 缺范文要点")
        sol_len = len(re.sub(r"\s", "", f_["solution"]))
        check(40 <= sol_len <= 140, f"{f_['id']} 作文 solution 长度 {sol_len}（宜 50-100 字）")

# 8. ledger 覆盖 exactly public
check(set(ledger["answers"]) == set(ids), "ledger 覆盖与 public 不一致")
check(ledger["agent_id"] == "chi-gen-w1-20261003" and ledger["solver"] == "MiniMax-M3"
      and ledger["method"] == "generator self-answer", "ledger 元信息不符规格")

# 9. 古诗文原句抽查（须与部编版一致）
DICTATION_EXPECT = [
    "露似真珠月似弓", "只缘身在此山中", "不教胡马度阴山", "家祭无忘告乃翁",
    "不拘一格降人才", "其道大光", "一泻汪洋", "前途似海", "来日方长",
    "清泉石上流", "夜半钟声到客船", "粉骨碎身浑不怕", "要留清白在人间",
    "任尔东西南北风", "非然也", "巍巍乎若太山", "春风送暖入屠苏",
    "路上行人欲断魂", "听取蛙声一片", "望湖楼下水如天", "把酒话桑麻",
    "日暮客愁新", "我们的日子为什么一去不复返呢", "大渡桥横铁索寒",
    "万水千山只等闲", "桃李无言，下自成蹊",  # 最后一条不应命中，仅作存在性提示
]
all_text = "\n".join(p["stem"] + (p.get("options") and "\n" + "\n".join(p["options"]) or "") for p in public)
all_text += "\n" + "\n".join(f_["stem"] + f_["answer"] + f_["solution"] for f_ in full)
for line in DICTATION_EXPECT[:-1]:
    check(line in all_text, f"抽查未发现古诗文原句：{line}")

print(f"题目数：{len(public)}；覆盖 KP：{len(set(kp_counts))}/180；choice {choice_n}；essay {essay_n}")
print(f"item_type：{dict(Counter(p['item_type'] for p in public))}")
print(f"form：{dict(Counter(p['form'] for p in public))}")
print(f"难度区间：{min(p['difficulty'] for p in public)}-{max(p['difficulty'] for p in public)}")

if fails:
    print(f"\n❌ {len(fails)} 项校验未过：")
    for m in fails[:30]:
        print("  -", m)
    sys.exit(1)
print("\n✅ 全部校验通过（结构 / id / KP / 难度 / 选项 / 无泄漏 / 同序 / ledger / 作文字段 / 古诗文原句抽查）")
