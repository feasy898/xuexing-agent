#!/usr/bin/env python
"""学科级图谱装载自检（验收门：10 学科全 OK）。

无参数运行：以 data/knowledge 的实际划分为准，逐学科调用生产装载入口
xuexing.load_kpgraph_subject（学科目录级合并装载），每学科打印一行

    学科名: KP数 边数 OK

「OK」= 合并建图成功且 validate() 为空（无未知 prereq / 缺边 / 未声明边）
且 topological_order() 可用（无环——出卷 blueprint 与诊断路径依赖拓扑闭包）。
任一学科失败则该行以 FAIL 结尾并 exit 1；全部成功 exit 0。
"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))

from xuexing import load_kpgraph_subject  # noqa: E402
from xuexing.kpgraph_subject import discover_subjects  # noqa: E402

KNOWLEDGE_DIR = os.path.join(ROOT, "data", "knowledge")


def main() -> int:
    subjects = discover_subjects(KNOWLEDGE_DIR)
    if not subjects:
        print(f"no subject knowledge files found in {KNOWLEDGE_DIR}")
        return 1
    all_ok = True
    for subject in subjects:
        try:
            graph = load_kpgraph_subject(KNOWLEDGE_DIR, subject)
            n_kps = len(graph.kps())
            n_edges = sum(len(graph.children(kp.id)) for kp in graph.kps())
            errs = graph.validate()
            if errs:
                all_ok = False
                print(f"{subject}: {n_kps} {n_edges} FAIL validate: {errs[0]}")
                continue
            graph.topological_order()  # 环图在此抛 KPGraphError
            print(f"{subject}: {n_kps} {n_edges} OK")
        except Exception as e:  # noqa: BLE001
            all_ok = False
            print(f"{subject}: 0 0 FAIL {type(e).__name__}: {e}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
