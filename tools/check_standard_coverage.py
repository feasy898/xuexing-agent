"""课标覆盖检查器：knowledge json 的 standard_ref 与课标主题清单对照，报告缺口。

用法：
  python tools/check_standard_coverage.py                          # 全年级（math 默认）
  python tools/check_standard_coverage.py --grades 7,8             # 只查指定年级子库
  python tools/check_standard_coverage.py --format json            # 机读报告
  python tools/check_standard_coverage.py \
      --curriculum data/curriculum/physics_standard_topics.json \
      --knowledge 'data/knowledge/physics_grade*.json'             # 自定义课标/知识库

对照双向缺口：
  覆盖缺口 = 清单条目没有任何 KP 的 standard_ref 归属到它；
  归属缺口 = KP 的 standard_ref 归属不到清单任何条目。
退出码：0=全归属且全覆盖；1=有缺口（清单见 stdout）；2=输入/数据错误。
"""
import argparse
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from xuexing.standard_coverage import (  # noqa: E402
    StandardCoverageError,
    check_coverage_dicts,
)

DEFAULT_CURRICULUM = os.path.join(ROOT, "data", "curriculum", "math_standard_2022_topics.json")
DEFAULT_KNOWLEDGE_DIR = os.path.join(ROOT, "data", "knowledge")
DEFAULT_KNOWLEDGE_GLOB = os.path.join(ROOT, "data", "knowledge", "math_grade*.json")


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _expand_knowledge_paths(spec):
    """展开 --knowledge：支持目录、单文件、glob 三种形态，返回路径列表（排序）。"""
    if os.path.isdir(spec):
        return sorted(glob.glob(os.path.join(spec, "*.json")))
    return sorted(glob.glob(spec))


def _grade_band_from_knowledge(paths):
    """按每个 knowledge 文件的 grade_band 字段汇总年级（去重、排序）。"""
    grades: list[int] = []
    seen: set[int] = set()
    for path in paths:
        data = _load(path)
        band = data.get("grade_band")
        if not isinstance(band, list) or not band:
            raise StandardCoverageError(
                f"missing or empty grade_band in knowledge file: {path}"
            )
        for g in band:
            gi = int(g)
            if gi in seen:
                continue
            seen.add(gi)
            grades.append(gi)
    if not grades:
        raise StandardCoverageError("no grades resolved from knowledge files")
    return sorted(grades)


def _merge_kps(grades, knowledge_paths):
    """合并 knowledge_points；跨文件重复 id 视为数据错误。"""
    merged = []
    seen: dict[str, str] = {}
    for path in knowledge_paths:
        data = _load(path)
        for kp in data["knowledge_points"]:
            kp_id = kp.get("id")
            if kp_id in seen:
                raise StandardCoverageError(
                    f"duplicate kp id across files: {kp_id} "
                    f"({seen[kp_id]} & {path})"
                )
            seen[kp_id] = path
            merged.append(kp)
    return merged


def _report_text(rep, grades, n_kps, knowledge_paths):
    lines = []
    lines.append(f"课标覆盖检查：库={len(knowledge_paths)} 个知识文件 / {n_kps} 个知识点 × "
                 f"清单={len(rep.topics)} 条（{', '.join(sorted({t.domain for t in rep.topics}))}）")
    by_domain = {}
    for t in rep.topics:
        by_domain.setdefault(t.domain, []).append(t)
    counts = {m.kp_id: m.topic_ids for m in rep.matches}
    names = {t.id: t.name for t in rep.topics}
    for domain, topics in by_domain.items():
        lines.append(f"== {domain}")
        for t in topics:
            owners = [kp_id for kp_id, ids in counts.items() if t.id in ids]
            mark = "x" if owners else "!"
            detail = f"{len(owners)} 个知识点" if owners else "覆盖缺口：无知识点引用"
            lines.append(f"  [{mark}] {t.id} {t.name}（{t.theme}）— {detail}")
    if rep.unmatched_kp_ids:
        lines.append("== 归属缺口（standard_ref 归属不到任何条目）")
        for kp_id in rep.unmatched_kp_ids:
            lines.append(f"  [!] {kp_id}")
    else:
        lines.append("== 归属缺口：无")
    if rep.uncovered_topic_ids:
        lines.append("== 覆盖缺口（清单条目无知识点引用）")
        for tid in rep.uncovered_topic_ids:
            lines.append(f"  [!] {tid} {names[tid]}")
    else:
        lines.append("== 覆盖缺口：无")
    lines.append(f"覆盖率：{len(rep.covered_topic_ids)}/{len(rep.topics)} = "
                 f"{rep.coverage_rate:.1%}")
    lines.append("COVERAGE OK" if rep.is_complete() else "COVERAGE FAILED")
    return "\n".join(lines)


def _report_json(rep, grades, n_kps, knowledge_paths):
    by_kp = {m.kp_id: m.topic_ids for m in rep.matches}
    out = {
        "grades": grades,
        "knowledge_files": [os.path.relpath(p, ROOT) for p in knowledge_paths],
        "kp_count": n_kps,
        "topic_count": len(rep.topics),
        "coverage_rate": rep.coverage_rate,
        "complete": rep.is_complete(),
        "uncovered_topic_ids": list(rep.uncovered_topic_ids),
        "unmatched_kp_ids": list(rep.unmatched_kp_ids),
        "topics": [
            {
                "id": t.id,
                "name": t.name,
                "domain": t.domain,
                "theme": t.theme,
                "covered": t.id not in rep.uncovered_topic_ids,
                "matched_kp_ids": [k for k, ids in by_kp.items() if t.id in ids],
            }
            for t in rep.topics
        ],
        "matches": [{"kp_id": m.kp_id, "topic_ids": list(m.topic_ids)} for m in rep.matches],
    }
    return json.dumps(out, ensure_ascii=False, indent=2)


def main():
    ap = argparse.ArgumentParser(description="课标覆盖检查器")
    ap.add_argument("--curriculum", default=DEFAULT_CURRICULUM,
                    help="课标主题清单 json（默认 data/curriculum/math_standard_2022_topics.json）")
    ap.add_argument("--knowledge-dir", default=DEFAULT_KNOWLEDGE_DIR,
                    help="knowledge 年级文件所在目录（默认 data/knowledge；与 --knowledge 互斥）")
    ap.add_argument("--knowledge", default=None,
                    help="knowledge 年级文件 glob（默认 math_grade*.json；按文件 grade_band 取年级）")
    ap.add_argument("--grades", default="7,8,9",
                    help="参与的年级，逗号分隔（默认 7,8,9；--knowledge 给定时被 grade_band 覆盖）")
    ap.add_argument("--format", choices=["text", "json"], default="text")
    args = ap.parse_args()
    try:
        # 解析 knowledge 文件：--knowledge 优先，否则按 --knowledge-dir + 旧 _merge_kps 路径
        if args.knowledge:
            knowledge_paths = _expand_knowledge_paths(args.knowledge)
            if not knowledge_paths:
                raise StandardCoverageError(
                    f"--knowledge 展开为空：{args.knowledge}"
                )
            grades = _grade_band_from_knowledge(knowledge_paths)
        else:
            grades = [int(g.strip()) for g in args.grades.split(",") if g.strip()]
            if not grades:
                raise StandardCoverageError("--grades is empty")
            knowledge_paths = [
                os.path.join(args.knowledge_dir, f"math_grade{g}.json")
                for g in grades
            ]
            for p in knowledge_paths:
                if not os.path.exists(p):
                    raise StandardCoverageError(f"missing knowledge file: {p}")
        kps = _merge_kps(grades, knowledge_paths)
        rep = check_coverage_dicts(kps, _load(args.curriculum))
    except StandardCoverageError as e:
        print(f"INPUT ERROR: {e}")
        return 2
    except (OSError, json.JSONDecodeError) as e:
        print(f"INPUT ERROR: {e}")
        return 2
    if args.format == "json":
        print(_report_json(rep, grades, len(kps), knowledge_paths))
    else:
        print(_report_text(rep, grades, len(kps), knowledge_paths))
    return 0 if rep.is_complete() else 1


if __name__ == "__main__":
    sys.exit(main())
