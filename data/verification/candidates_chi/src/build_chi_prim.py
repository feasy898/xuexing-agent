# -*- coding: utf-8 -*-
"""构建 chi_prim 批次候选输出：public / full / ledger_gen 三件套。
用法：python build_chi_prim.py
输入：src/q_g1.py src/q_g2.py src/q_g3.py（一、二、三年级，1-3 题/KP）
输出：chi_prim_public.json / chi_prim_full.json / chi_prim_ledger_gen.json
"""
import importlib.util, json, os, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = HERE
for _ in range(6):  # 向上找含 data/knowledge 的仓库根
    if os.path.isdir(os.path.join(REPO, "data", "knowledge")):
        break
    REPO = os.path.dirname(REPO)
else:
    raise SystemExit("未找到仓库根（data/knowledge）")
sys.path.insert(0, HERE)

AGENT_ID = "chi-gen-w1-20261003"
SOLVER = "MiniMax-M3"
METHOD = "generator self-answer"
TAG = "prim"
SOURCE = "llm_generated"

# ---------- 载入题目（顺序：1 年级 → 2 年级 → 3 年级） ----------
def load(mod):
    spec = importlib.util.spec_from_file_location(mod, os.path.join(HERE, mod + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.ITEMS

g1, g2, g3 = load("q_g1"), load("q_g2"), load("q_g3")
raw = [("kp_chi1", it) for it in g1] + [("kp_chi2", it) for it in g2] + [("kp_chi3", it) for it in g3]

# ---------- 注册 KP 全集 ----------
KP = {}
for g in (1, 2, 3):
    p = os.path.join(REPO, "data", "knowledge", "chinese_grade%d.json" % g)
    d = json.load(open(p, encoding="utf-8"))
    for k in d["knowledge_points"]:
        KP[k["id"]] = k  # {grade, name, cluster, standard_ref...}

FORMS = {"choice", "dictation", "cloze", "correction", "comprehension",
         "translation", "segmentation", "connection", "applied-writing",
         "transcription", "commentary", "essay"}
TYPES = {"choice", "fill", "solve"}
WP_KEYS = {"题目材料", "字数", "评分维度"}

# ---------- 组装 ----------
public, full, answers = [], [], {}
ids_seen = set()
problems = []

for i, (prefix, it) in enumerate(raw, 1):
    iid = "chi_%s_%04d" % (TAG, i)
    assert iid not in ids_seen, "id 重复：%s" % iid
    ids_seen.add(iid)

    kp, t, f, s, a, sol = it["kp"], it["t"], it["f"], it["s"], it["a"], it["sol"]
    d = it["d"]; o = it.get("o"); wp = it.get("wp")

    # —— 校验 ——
    if kp not in KP:
        problems.append("%s: kp 未注册 %s" % (iid, kp)); continue
    if t not in TYPES: problems.append("%s: item_type 非法 %s" % (iid, t))
    if f not in FORMS: problems.append("%s: form 非法 %s" % (iid, f))
    if not (0.2 <= d <= 0.85): problems.append("%s: difficulty 越界 %s" % (iid, d))
    if not (0.2 <= d <= 0.6): problems.append("%s: 小学低段 difficulty 应在 0.2-0.6，实为 %s" % (iid, d))
    if t == "choice":
        if not (isinstance(o, list) and len(o) == 4):
            problems.append("%s: choice 选项必须 4 项" % iid)
        if a not in ("A", "B", "C", "D"):
            problems.append("%s: choice answer 必须是 A/B/C/D，实为 %r" % (iid, a))
    else:
        if o: problems.append("%s: 非 choice 不应带 options" % iid)
        if not (isinstance(a, str) and a.strip()):
            problems.append("%s: fill/solve answer 必须是非空中文串" % iid)
    if not (isinstance(sol, str) and len(sol.strip()) >= 10):
        problems.append("%s: solution 过短" % iid)
    # 学段归属与 KP 所在年级一致（1-3 年级全是小学低段）
    gk = KP[kp]["grade"]
    if gk not in (1, 2, 3):
        problems.append("%s: kp 不属于 1-3 年级：%s" % (iid, kp))
    if f == "essay":
        if t != "solve": problems.append("%s: essay 应为 solve" % iid)
        if not (isinstance(wp, dict) and WP_KEYS <= set(wp.keys())):
            problems.append("%s: essay 缺少 writing_prompt（题目材料/字数/评分维度）" % iid)
        else:
            if len(sol) > 100:
                problems.append("%s: 作文 solution 超 100 字（%d）" % (iid, len(sol)))
            if len(sol) < 40:
                problems.append("%s: 作文 solution 不足 50 字（%d）" % (iid, len(sol)))
    elif wp:
        problems.append("%s: 非 essay 不应带 writing_prompt" % iid)

    # —— 组装 ——
    kps = [kp]
    p_item = {"id": iid, "item_type": t, "form": f, "stem": s, "kps": kps,
              "difficulty": d, "source": SOURCE}
    f_item = {"id": iid, "item_type": t, "form": f, "stem": s, "kps": kps,
              "difficulty": d, "answer": a, "solution": sol, "source": SOURCE}
    if t == "choice":
        p_item["options"] = o; f_item["options"] = o
    if wp: f_item["writing_prompt"] = wp
    public.append(p_item); full.append(f_item)
    answers[iid] = a

if problems:
    print("校验失败：")
    for p in problems: print("  -", p)
    sys.exit(1)

ledger = {"agent_id": AGENT_ID, "solver": SOLVER, "method": METHOD, "answers": answers}

OUT = os.path.dirname(HERE)  # .../data/verification/candidates_chi

def dump(obj, name):
    path = os.path.join(OUT, name)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    return path

p1 = dump(public, "chi_prim_public.json")
p2 = dump(full, "chi_prim_full.json")
p3 = dump(ledger, "chi_prim_ledger_gen.json")

# ---------- 汇总报告 ----------
cnt_kp = collections.Counter(x["kps"][0] for x in full)
under = [k for k in KP if cnt_kp.get(k, 0) < 2]
over = [k for k in KP if cnt_kp.get(k, 0) > 3]
print("items/grade: g1=%d g2=%d g3=%d total=%d" % (len(g1), len(g2), len(g3), len(full)))
print("KP 覆盖: %d/%d；每题 <2 条: %s；每题 >3 条: %s" % (len(cnt_kp), len(KP), under, over))
print("item_type: %s" % dict(collections.Counter(x["item_type"] for x in full)))
print("form: %s" % dict(collections.Counter(x["form"] for x in full)))
print("difficulty: min=%s max=%s" % (min(x["difficulty"] for x in full), max(x["difficulty"] for x in full)))
print("essay(writing_prompt) items: %d" % sum(1 for x in full if "writing_prompt" in x))
print("written:\n  %s\n  %s\n  %s" % (p1, p2, p3))
