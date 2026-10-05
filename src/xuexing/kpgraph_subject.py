"""学科级知识点图谱装载器（subject-level loader）。

问题：单年级文件 data/knowledge/<subject>_grade<N>.json 的 prereqs 会引用其他
年级的知识点（例：chinese_grade2 引用一年级 kp_chi1_tell_story），逐文件
load_kpgraph 时报 KPGraphError: unknown endpoint in edge（83 个文件中 71 个
因此无法装载）。

方案（目录级合并装载，参照 math_all.json 学科级合并先例）：把一个学科全部
年级文件的 knowledge_points 取并集后一次性交给 kpgraph_from_dict 建图，跨年级
prereq 在并集中自然找到端点。数学学科的 math_all.json 即该合并结果的人工
先例（已逐字段比对与本装载器的合并结果完全一致）。文件命名约定与
tools/validate_knowledge.py 的 SUBJECT_KNOWLEDGE_RE 保持同一正则（因此
math_grade11b/12b.json、math_all.json 等非 <subject>_grade<N>.json 命名的
文件不参与合并，与验证器的学科口径一致）。

为什么独立成模块而不写进 kpgraph.py：specs/frozen/kpgraph.spec.md §2 冻结了
kpgraph 模块的依赖与 IO（除 load_kpgraph 读单一 path 外禁止任何文件 IO），
本装载器需要目录扫描与多文件读取，故放在同层（src/xuexing/ 包内）的兄弟
模块，构图完全经由 kpgraph 的冻结公开 API（kpgraph_from_dict），不复制任何
构建逻辑，也不改动 kpgraph.py 既有行为。

确定性：文件按名字典序读取；无随机源、无时钟；同输入同输出。
"""

from __future__ import annotations

import glob
import json
import os
import re

from xuexing.kpgraph import KPGraph, KPGraphError, kpgraph_from_dict

__all__ = [
    "SUBJECT_KNOWLEDGE_RE",
    "discover_subject_files",
    "discover_subjects",
    "load_kpgraph_subject",
]

# 与 tools/validate_knowledge.py 的 SUBJECT_KNOWLEDGE_RE 同一命名约定：
# <subject>_grade<N>.json。math_all.json、math_grade11b.json 等不匹配，
# 避免与年级文件重复入图（口径与知识库验证器一致）。
SUBJECT_KNOWLEDGE_RE = re.compile(r"^(?P<subject>[a-z]+)_grade(?P<grade>\d+)\.json$")


def discover_subjects(directory: str) -> list[str]:
    """目录下出现的学科名集合（升序）；无匹配文件返回 []。"""
    subjects: set[str] = set()
    for path in glob.glob(os.path.join(directory, "*.json")):
        m = SUBJECT_KNOWLEDGE_RE.match(os.path.basename(path))
        if m is not None:
            subjects.add(m.group("subject"))
    return sorted(subjects)


def discover_subject_files(directory: str, subject: str) -> list[str]:
    """某学科的全部年级文件（<subject>_grade<N>.json），按文件名字典序。"""
    files: list[str] = []
    for path in sorted(glob.glob(os.path.join(directory, "*.json"))):
        m = SUBJECT_KNOWLEDGE_RE.match(os.path.basename(path))
        if m is not None and m.group("subject") == subject:
            files.append(path)
    return files


def load_kpgraph_subject(directory: str, subject: str) -> KPGraph:
    """学科级装载：合并 directory 下 subject 全部年级文件后一次性建图。

    单文件解析与 kpgraph_from_dict 的冻结语义完全一致（缺 knowledge_points /
    节点缺 id,name → 原生 KeyError；结构非列表/非 dict → 原生 TypeError；
    跨文件重复 id、未知 prereq、自引用 → KPGraphError），逐文件 load_kpgraph
    能过的输入本入口必能过，且额外解析跨年级引用。
    学科在 directory 下没有任何年级文件 → KPGraphError（fail-fast，消息含
    学科名与目录）。
    """
    files = discover_subject_files(directory, subject)
    if not files:
        raise KPGraphError(
            f"no knowledge files for subject {subject!r} in {directory}"
        )
    merged: list[dict] = []
    for path in files:
        with open(path, encoding="utf-8") as f:
            merged.extend(json.load(f)["knowledge_points"])
    return kpgraph_from_dict({"knowledge_points": merged})
