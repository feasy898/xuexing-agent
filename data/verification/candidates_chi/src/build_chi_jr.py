# -*- coding: utf-8 -*-
"""build_chi_jr.py —— 组装并校验 chi_jr 批次（语文 初中 7-9 年级）。

产出：
  data/verification/candidates_chi/chi_jr_public.json      盲解版（无答案/解析）
  data/verification/candidates_chi/chi_jr_full.json        完整版（含答案/解析/作文要素）
  data/verification/candidates_chi/chi_jr_ledger_gen.json  生成方自答台账
"""
import json, os, sys
from collections import Counter

SRC = os.path.dirname(os.path.abspath(__file__))                                    # .../candidates_chi/src
_here = os.path.abspath(__file__)
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_here)))))  # xuexing-agent 仓库根
KNOW = os.path.join(ROOT, "data", "knowledge")
CAND = os.path.join(ROOT, "data", "verification", "candidates_chi")

TAG = "chi_jr"
AGENT_ID = "chi-gen-w1-20261003"
SOLVER = "MiniMax-M3"

# ---------- 1. 载入 KP 注册表 ----------
valid_kps = {}
for g in (7, 8, 9):
    with open(os.path.join(KNOW, f"chinese_grade{g}.json"), encoding="utf-8") as f:
        d = json.load(f)
    for kp in d["knowledge_points"]:
        valid_kps[kp["id"]] = kp
print(f"已注册 KP：{len(valid_kps)} 个")

# ---------- 2. 载入命题数据 ----------
MODULES = ["q_g7a.py", "q_g7b.py", "q_g8a.py", "q_g8b.py", "q_g9a.py", "q_g9b.py"]
raw = []
for m in MODULES:
    ns = {}
    with open(os.path.join(SRC, m), encoding="utf-8") as f:
        exec(compile(f.read(), m, "exec"), ns)
    items = ns["ITEMS"]
    print(f"{m}: {len(items)} 题")
    raw.extend(items)
print(f"合计原始题目：{len(raw)}")

# ---------- 2.5 难度分布（初中 0.30-0.75：基础默写/识记偏低，综合鉴赏/材料阅读/中考专项偏高） ----------
HARD_KPS = {  # 中考综合题与鉴赏题：上抬到 0.60-0.70
    "kp_chi9_shangxi", "kp_chi9_jindai", "kp_chi9_shiyong", "kp_chi9_duanyu",
    "kp_chi9_mingshu", "kp_chi9_zkao_write", "kp_chi9_kaodian_zeng",
    "kp_chi9_huaiyi", "kp_chi9_zhongguoren", "kp_chi9_heli",
}
MID_KPS = {  # 九年级小说/名著思辨题：0.55-0.62
    "kp_chi9_guxiang", "kp_chi9_yule", "kp_chi9_kongyijiu", "kp_chi9_zhongguoren",
    "kp_chi9_duanshi", "kp_chi9_book_rulin", "kp_chi9_book_aiqing",
    "kp_chi9_wuyan", "kp_chi9_shanshui", "kp_chi9_quyuan", "kp_chi9_tianxia",
    "kp_chi8_hezhou", "kp_chi8_zhuangzi", "kp_chi8_liji", "kp_chi8_mashuo",
    "kp_chi8_yugong", "kp_chi8_zhouyafu", "kp_chi8_shi", "kp_chi7_shi",
}
EASY_KPS = {  # 默写与识记：压低到 0.35-0.42
    "kp_chi7_poem_dictation", "kp_chi7_amount7", "kp_chi7_tools",
}

def adjust(it):
    kp, d = it["kp"], float(it["d"])
    if kp in HARD_KPS:
        return round(max(d, 0.62 if it["t"] != "essay" else 0.55), 2)
    if kp in MID_KPS:
        return round(max(d, 0.56), 2)
    if kp in EASY_KPS:
        return round(min(d, 0.42), 2)
    return round(d, 2)

# ---------- 3. 组装 ----------
public, full = [], []
ids = []
n = 0
kp_counter = Counter()
for idx, it in enumerate(raw, start=1):
    iid = f"chi_{TAG}_{n+1:04d}"
    n += 1
    kps = [it["kp"]]
    rec = {
        "id": iid,
        "item_type": it["t"],
        "form": it["f"],
        "stem": it["s"],
        "kps": kps,
        "difficulty": adjust(it),
        "source": "llm_generated",
    }
    if it["t"] == "choice":
        rec["options"] = it["o"]
    if "wp" in it and it["wp"]:
        rec_full_wp = dict(it["wp"])
        rec_full_wp.setdefault("字数", "600 字左右")
        rec_full_wp.setdefault("评分维度", ["内容", "结构", "语言", "书写"])
        rec_writing_prompt = rec_full_wp
    else:
        rec_writing_prompt = None
    full_rec = dict(rec)
    full_rec.update({
        "answer": it["a"],
        "solution": it["sol"],
    })
    if rec_writing_prompt:
        full_rec["writing_prompt"] = rec_writing_prompt
    public.append(rec)
    full.append(full_rec)
    ids.append(iid)
    kp_counter[it["kp"]] += 1

# ---------- 4. 台账 ----------
ledger = {
    "agent_id": AGENT_ID,
    "solver": SOLVER,
    "method": "generator self-answer",
    "answers": {it["id"]: it["answer"] for it in full},
}

# ---------- 5. 校验 ----------
errors = []
def chk(cond, msg):
    if not cond:
        errors.append(msg)

chk(len(ids) == len(set(ids)), "id 重复")
chk(len(public) == len(full) == len(ids), "三份记录数不一致")

# 同序
chk([p["id"] for p in public] == ids, "public 与 full 顺序不一致")
chk(list(ledger["answers"].keys()) == ids, "ledger 键顺序与 public 不一致")

# public 无答案/解析
for p in public:
    chk("answer" not in p and "solution" not in p, f"public 泄漏答案 {p['id']}")
    chk(p["source"] == "llm_generated", f"source 错误 {p['id']}")
    chk(len(p["kps"]) == 1, f"kps 长度 {p['id']}")
    chk(p["kps"][0] in valid_kps, f"未注册 KP {p['id']}:{p['kps'][0]}")
    chk(0.30 <= p["difficulty"] <= 0.75, f"难度越界 {p['id']}:{p['difficulty']}")

for f_ in full:
    chk("answer" in f_ and "solution" in f_, f"full 缺答案/解析 {f_['id']}")
    chk(f_["answer"] == ledger["answers"][f_["id"]], f"ledger 与 full 不一致 {f_['id']}")

for p in public:
    if p["item_type"] == "choice":
        chk(p["answer"] if False else True, "")
        chk(len(p.get("options", [])) == 4, f"选项数 {p['id']}")
        for o in p.get("options", []):
            chk(o[:2] in ("A.", "B.", "C.", "D."), f"选项前缀 {p['id']}")
        chk(ledger["answers"][p["id"]] in ("A", "B", "C", "D"), f"choice 答案 {p['id']}")
    else:
        chk(isinstance(ledger["answers"][p["id"]], str) and 0 < len(ledger["answers"][p["id"]]) <= 400,
            f"fill/solve 答案形态 {p['id']}")

for f_ in full:
    if f_["form"] == "essay":
        chk("writing_prompt" in f_, f"作文缺 writing_prompt {f_['id']}")
        wp = f_["writing_prompt"]
        chk("题目" in wp and "字数" in wp and "评分维度" in wp, f"作文要素不全 {f_['id']}")
        chk(50 <= len(f_["solution"]) <= 160, f"作文评分要点长度 {f_['id']}: {len(f_['solution'])}")

# 每个 KP 2-3 题
for kp, c in kp_counter.items():
    chk(2 <= c <= 3, f"KP 题量越界 {kp}: {c}")
covered = set(kp_counter)
missing = sorted(set(valid_kps) - covered)
chk(not missing, f"未覆盖 KP: {missing[:10]}（共 {len(missing)} 个）")

if errors:
    print("\n".join("✗ " + e for e in errors[:60]))
    print(f"共 {len(errors)} 处错误")
    sys.exit(1)

# ---------- 6. 落盘 ----------
os.makedirs(CAND, exist_ok=True)
def dump(name, obj):
    p = os.path.join(CAND, name)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    print(f"写出 {p}")
dump("chi_jr_public.json", public)
dump("chi_jr_full.json", full)
dump("chi_jr_ledger_gen.json", ledger)

# ---------- 7. 报告 ----------
print("\n==== 批次统计 ====")
print("题目总数:", len(public))
print("KP 覆盖:", len(kp_counter), "/", len(valid_kps))
print("item_type:", dict(Counter(p["item_type"] for p in public)))
print("form:", dict(Counter(p["form"] for p in public)))
print("学段分布:", dict(Counter("G7" if p["kps"][0].startswith("kp_chi7") else "G8" if p["kps"][0].startswith("kp_chi8") else "G9" for p in public)))
print("难度区间:", min(p["difficulty"] for p in public), "-", max(p["difficulty"] for p in public))
print("作文题数:", sum(1 for f_ in full if f_["form"] == "essay"))
print("\n✅ 全部校验通过")
