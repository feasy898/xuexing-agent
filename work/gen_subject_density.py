"""补题脚本：扫描每 KP 当前题数，对 <3 的 KP 启动补题出题员。
用法：python work/gen_subject_density.py <subject>
"""
import glob
import json
import os
import re
import subprocess
import sys

ROOT = os.path.abspath(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)


def main():
    sub = sys.argv[1]
    DIR_CAND = f"data/verification/candidates_{sub[:3]}_density"
    os.makedirs(DIR_CAND, exist_ok=True)

    # 找出 <3 题的 KP
    items_per_kp = {}
    for f in glob.glob(f"data/items/{sub}_grade*.json"):
        for it in json.load(open(f, encoding="utf-8"))["items"]:
            for k in it.get("kps", []):
                items_per_kp[k] = items_per_kp.get(k, 0) + 1
    deficient = sorted([(k, v) for k, v in items_per_kp.items() if v < 3])
    print(f"{sub}: {len(deficient)} KP < 3 题（需补足到 ≥3）")

    # 写候选批出题任务给主会话
    out_path = f"docs/research/k12/density_tasks_{sub}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "subject": sub,
                "candidates_dir": DIR_CAND,
                "deficient_kps": [{"id": k, "current_count": v, "need": 3 - v} for k, v in deficient],
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    print(f"任务写入 {out_path}")


if __name__ == "__main__":
    main()
