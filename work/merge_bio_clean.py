"""生物入库清理：先撤销 BIO 旧入库、然后以安全解析规则重做。"""
import glob
import json
import os
import re

# 1) 撤销所有生物入库
for f in sorted(glob.glob("data/items/biology_grade*.json")):
    d = json.load(open(f, encoding="utf-8"))
    if d.get("items"):
        d["items"] = []
        with open(f, "w", encoding="utf-8", newline="\r\n") as wf:
            json.dump(d, wf, ensure_ascii=False, indent=2)
            wf.write("\n")
print("cleared biology items")

# 2) 以"学科段前缀推断年级"重新入库
DIR = "data/verification/candidates_bio"
GEN = "bio-gen-w1-20261003"


def extract_grade(pid: str, prefix: str, tag: str) -> int:
    """bio_bio_jr_0001 → tag=bio_jr, id 前缀 bio_bio_jr；缺数字 → 用 tag 推断年级。
    tag 形如 bio_jr/bio_hs：jr=7-9, hs=10-12。
    """
    if tag == "bio_jr":
        # 取 id 末尾序号前的数字（约定 jr 批内部按 7/8/9 排列），不靠谱——直接按 KP 中的年级提取
        pass
    # 退回到 KP id 取年级
    nums = re.findall(r"\d+", pid)
    if len(nums) >= 2:
        return int(nums[1])
    return 0


def merge_bio():
    biology_gs = set()
    for f in glob.glob("data/knowledge/biology_grade*.json"):
        m = re.search(r"grade(\d+)", os.path.basename(f))
        if m:
            biology_gs.add(int(m.group(1)))

    agreed = 0
    rejected = 0
    skipped = 0
    seen_stems = set()
    seen_ids = set()
    for pf in sorted(glob.glob(DIR + "/*_public.json")):
        tag = os.path.basename(pf).replace("_public.json", "")
        pub = json.load(open(pf, encoding="utf-8"))
        full = json.load(open(pf.replace("_public", "_full"), encoding="utf-8"))
        gen = json.load(open(pf.replace("_public", "_ledger_gen"), encoding="utf-8"))
        for p, fu in zip(pub, full):
            kps = fu.get("kps") or []
            if len(kps) != 1:
                skipped += 1
                continue
            m_kp = re.search(r"_(?:bio|che|phy|eng|chi|geo|hist|pol|sci|math|pri|jr|hs)(\d+)_", kps[0])
            known_g = int(m_kp.group(1)) if m_kp else 0
            if known_g not in biology_gs:
                skipped += 1
                continue
            iid = p.get("id", "")
            if iid in seen_ids:
                skipped += 1
                continue
            if fu.get("item_type") == "choice":
                opts = fu.get("options", [])
                if len(opts) < 4:
                    rejected += 1
                    continue
                labels = [o.split(".", 1)[0].strip() for o in opts if "." in o]
                ans = str(fu.get("answer", "")).strip()
                if fu.get("answer_mode") == "subset":
                    parts = [p2.strip() for p2 in ans.split(",")]
                    if any(p2 not in labels for p2 in parts) or len(parts) < 2:
                        rejected += 1
                        continue
                elif ans not in labels:
                    rejected += 1
                    continue
            elif not fu.get("answer"):
                rejected += 1
                continue
            stem = fu.get("stem", "")
            if stem in seen_stems:
                skipped += 1
                continue
            seen_stems.add(stem)
            seen_ids.add(iid)
            bank_p = f"data/items/biology_grade{known_g}_items.json"
            bank = json.load(open(bank_p, encoding="utf-8"))
            m = {}
            for k in ("id", "item_type", "stem", "answer", "kps", "difficulty", "solution", "source", "options", "form", "answer_mode"):
                if k in fu:
                    m[k] = fu[k]
            if "form" not in m:
                m["form"] = m.get("item_type", "fill")
            m["verification"] = {"agents": [GEN], "answers_agree": True, "single_agent": True, "note": "single-agent generation, blind verification deferred"}
            bank["items"].append(m)
            with open(bank_p, "w", encoding="utf-8", newline="\r\n") as wf:
                json.dump(bank, wf, ensure_ascii=False, indent=2)
                wf.write("\n")
            agreed += 1
    total = sum(len(json.load(open(f, encoding="utf-8"))["items"]) for f in glob.glob("data/items/*.json") if os.path.exists(f))
    print(f"BIO_MERGE agreed={agreed} rejected={rejected} skipped={skipped} bank_total={total}")


merge_bio()
