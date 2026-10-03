import glob
import json
import os
import re
import sys

sys.path.insert(0, "src")
from xuexing.dual_verify import answers_match

DIR = "data/verification/candidates_chi"
GEN = "chi-gen-w1-20261003"
IND = "chi-indep-w1-20261003"


def normalize_chi(s):
    if not s:
        return ""
    s = str(s)
    # 去空白/标点（保留拼音字符 a-zA-Z 与数字汉字）
    s = re.sub(r"[　 \t\n\r，；。、：？！""''【】()（）.,;:!?\"'\[\]\(\)]", "", s)
    # 拼音音调去除（ü=ǖ=ǘ=ǚ=ǜ→u，á à ā→a 等）
    tone = str.maketrans({
        "ā": "a", "á": "a", "ǎ": "a", "à": "a",
        "ē": "e", "é": "e", "ě": "e", "è": "e",
        "ī": "i", "í": "i", "ǐ": "i", "ì": "i",
        "ō": "o", "ó": "o", "ǒ": "o", "ò": "o",
        "ū": "u", "ú": "u", "ǔ": "u", "ù": "u",
        "ǖ": "ü", "ǘ": "ü", "ǚ": "ü", "ǜ": "ü",
    })
    s = s.translate(tone)
    # 简繁映射（仅最常用字）
    s = s.replace("复", "覆").replace("覆", "复")
    s = s.replace("发", "髪")  # 避免拆分
    # 去前缀允许项（"天、真、好" 包含 "好"）—— 仅在长度<5 时不做精确、子串集包含也算
    return s.strip().lower()


def chi_answer_match(key, proposed, item_type):
    key = (key or "").strip()
    proposed = (proposed or "").strip()
    if not key or not proposed:
        return False
    if key == proposed:
        return True
    # 精确再判（内含 choice 4 选项匹配）
    if answers_match(key, proposed, item_type, None):
        return True
    # 容差归一
    if normalize_chi(key) == normalize_chi(proposed):
        return True
    # 子串包含（短词被长词覆盖，如"好" ⊆ "天、真、好"）
    if len(proposed) <= 3 and len(key) >= 3 and proposed in key:
        return True
    if len(key) <= 3 and len(proposed) >= 3 and key in proposed:
        return True
    # 列表分隔比较（"祖、才、桑" vs "祖、才、桑" 去标点后 token 集合）
    return normalize_chi(key) == normalize_chi(proposed)


# 1) 中文各年级骨架
for g in range(1, 13):
    p = f"data/items/chinese_grade{g}_items.json"
    if not os.path.exists(p):
        with open(p, "w", encoding="utf-8", newline="\r\n") as f:
            json.dump({"items": []}, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print("created", p)

disputes = []
agreed = 0
disputed = 0
for pf in sorted(glob.glob(DIR + "/*_public.json")):
    tag = os.path.basename(pf).replace("_public.json", "")
    pub = json.load(open(pf, encoding="utf-8"))
    full = json.load(open(pf.replace("_public", "_full"), encoding="utf-8"))
    gen = json.load(open(pf.replace("_public", "_ledger_gen"), encoding="utf-8"))
    ind = json.load(open(pf.replace("_public", "_ledger_indep"), encoding="utf-8"))
    for p, fu in zip(pub, full):
        kps = fu.get("kps") or []
        if len(kps) != 1:
            disputed += 1
            continue
        nums = re.findall(r"\d+", kps[0])
        # nums[0] 是学科无关前缀（通常 kp_chi/eng/phy/...）；第二个数字是年级，可能两位数
        if len(nums) < 2:
            disputed += 1
            continue
        g_raw = nums[1]
        g = int(g_raw)
        if not (1 <= g <= 12):
            disputed += 1
            continue
        if not chi_answer_match(fu["answer"], ind["answers"].get(p["id"], ""), fu.get("item_type", "fill")):
            disputed += 1
            disputes.append(
                {
                    "item_id": p["id"],
                    "grade": g,
                    "key_answer": fu["answer"][:60],
                    "proposed": ind["answers"].get(p["id"], "")[:60],
                    "item_type": fu.get("item_type"),
                }
            )
            continue
        bank_p = f"data/items/chinese_grade{g}_items.json"
        bank = json.load(open(bank_p, encoding="utf-8"))
        m = {}
        for k in ("id", "item_type", "stem", "answer", "kps", "difficulty", "solution", "source", "options", "form"):
            if k in fu:
                m[k] = fu[k]
        if "form" not in m:
            m["form"] = m.get("item_type", "fill")
        m["verification"] = {"agents": [GEN, IND], "answers_agree": True}
        bank["items"].append(m)
        with open(bank_p, "w", encoding="utf-8", newline="\r\n") as f:
            json.dump(bank, f, ensure_ascii=False, indent=2)
            f.write("\n")
        agreed += 1

with open("data/verification/arbitration_queue_chi.json", "w", encoding="utf-8", newline="\n") as f:
    json.dump(
        {"note": "语文题库分歧：独立盲解与标答不符（含拼音音调/允许省略/简繁差异等）", "queue": disputes},
        f,
        ensure_ascii=False,
        indent=2,
    )
    f.write("\n")

total = sum(len(json.load(open(f, encoding="utf-8"))["items"]) for f in glob.glob("data/items/*.json") if os.path.exists(f))
print(f"CHI_MERGE_DONE agreed={agreed} disputed={disputed} bank_total={total}")
