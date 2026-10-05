"""从修复后的 candidates 强制覆盖入库文件的 options 和 item_type。"""
import json
import os

DIR_CAND = "data/verification/candidates_sci"


def main():
    cand_files = {}
    for ppath in os.listdir(DIR_CAND):
        if ppath.endswith("_public.json"):
            tag = ppath[:-len("_public.json")]
            pub = json.load(open(os.path.join(DIR_CAND, ppath), encoding="utf-8"))
            full = json.load(open(os.path.join(DIR_CAND, ppath.replace("_public", "_full")), encoding="utf-8"))
            cand_files[tag] = {p_["id"]: (p_, f_) for p_, f_ in zip(pub, full)}

    fixed = 0
    for grade in range(1, 7):
        path = os.path.join("data", "items", f"science_grade{grade}_items.json")
        if not os.path.exists(path):
            continue
        d = json.load(open(path, encoding="utf-8"))
        changed = False
        for it in d["items"]:
            cid = it["id"]
            for tag, by_id in cand_files.items():
                if cid in by_id:
                    p_new, f_new = by_id[cid]
                    for k in ("options", "item_type", "form"):
                        if p_new.get(k) is not None and it.get(k) != p_new.get(k):
                            it[k] = p_new[k]
                            changed = True
                    break
        if changed:
            with open(path, "w", encoding="utf-8", newline="\r\n") as f:
                json.dump(d, f, ensure_ascii=False, indent=2)
                f.write("\n")
            fixed += 1
    print(f"fixed {fixed} science files")


if __name__ == "__main__":
    main()
