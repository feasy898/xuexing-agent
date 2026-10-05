"""知识库验证器：图谱/题库/误解库/母题库的合并完整性检查。

用法：python tools/validate_knowledge.py [--min-items-per-kp 3] [--min-mc-per-kp 2]
退出码 0=通过；非 0=有错误（错误清单打印到 stdout）。

多学科化（2026-10-02）：知识文件按 data/knowledge/<subject>_grade<N>.json
扫描（subject∈小写英文、N∈1..12）；按 subject 分组校验：每个学科有
SUBJECT_GRADE_RANGES 定义的『开设年级档位』，落库年级须落在档内，档内断
档按学科语义判定（math CORE_GRADES=7..9 缺位=错；其他学科=pending；
完全未建档=pending 不报错）；grade 合法域 1..12；题库与母题 glob 保持
学科无关（按文件名前缀归类 subject）。输出按 subject 汇总，math 行保持
现有文案格式（保证现有测试断言不破）。
"""
import argparse
import glob
import json
import os
import re
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from xuexing.itembank import itembank_from_dict  # noqa: E402
from xuexing.itembank_v2 import validate_bank_v2, verification_stats  # noqa: E402
from xuexing.kpgraph import kpgraph_from_dict  # noqa: E402
from xuexing.misconception_coverage import audit, parse_bank  # noqa: E402

KNOWLEDGE_DIR = os.path.join(ROOT, "data", "knowledge")
ITEMS_DIR = os.path.join(ROOT, "data", "items")
MC_DIR = os.path.join(ROOT, "data", "misconceptions")
ARCH_DIR = os.path.join(ROOT, "data", "archetypes")

# math 的 CORE_GRADES 语义：7-9 缺文件 = 错误；1-6 缺文件 = pending（待落库）。
# 其他 subject 走档位规则（缺档 = pending；落库出档 = 错）。
MATH_CORE_GRADES = frozenset((7, 8, 9))

# 学科开设年级档位：每个学科各年级对应一个学段（小学/初中/高中），
# 落库年级必须落在该档内，档内断档按学科语义判定。
# 默认未登记学科视为 1..12 全段开通。
SUBJECT_GRADE_RANGES = {
    "math":      (1, 12),
    "chinese":   (1, 12),
    "english":   (1, 12),
    "politics":  (1, 12),   # 小学道法 1-6 + 初中道法 7-9 + 高中思政 10-12
    "science":   (1, 6),    # 小学科学
    "physics":   (8, 12),   # 初中物理 8-9 + 高中物理 10-12
    "chemistry": (9, 12),   # 初中化学 9 + 高中化学 10-12
    "biology":   (7, 12),   # 初中生物 7-9 + 高中生物 10-12
    "history":   (7, 12),   # 初中历史 7-9 + 高中历史 10-12
    "geography": (7, 12),   # 初中地理 7-9 + 高中地理 10-12
}

# 学科文件命名规范：<subject>_grade<N>{_items|_archetypes|_misconceptions}.json
SUBJECT_KNOWLEDGE_RE = re.compile(r"^(?P<subject>[a-z]+)_grade(?P<grade>\d+)\.json$")
SUBJECT_ITEM_RE = re.compile(r"^(?P<subject>[a-z]+)_grade(?P<grade>\d+)_items\.json$")
SUBJECT_ARCH_RE = re.compile(r"^(?P<subject>[a-z]+)_grade(?P<grade>\d+)_archetypes\.json$")
# 误解库命名有三种：
#   <subject>_misconceptions.json（无年级，兼容 math_misconceptions.json）/
#   <subject>_grade<N>_misconceptions.json（按年级拆分）/
#   <subject>_grade<N>_misconceptions_extra.json（按年级补集）
SUBJECT_MC_RE = re.compile(
    r"^(?P<subject>[a-z]+)(?:_grade(?P<grade>\d+))?_misconceptions"
    r"(?:_extra)?\.json$"
)


def _discover_subjects(directory, regex):
    """扫描目录下学科文件 → {subject: [(grade, path)]}（subject 排序）。"""
    out = defaultdict(list)
    for path in sorted(glob.glob(os.path.join(directory, "*.json"))):
        m = regex.match(os.path.basename(path))
        if not m:
            continue
        subject = m.group("subject")
        grade = int(m.group("grade")) if m.groupdict().get("grade") else None
        out[subject].append((grade, path))
    return out


def _discover_mc_subjects(directory):
    """误解库：subject + 所在 grade 集（无年级文件关联全部年级）。"""
    out = defaultdict(lambda: {"files": [], "grades": set()})
    for path in sorted(glob.glob(os.path.join(directory, "*.json"))):
        m = SUBJECT_MC_RE.match(os.path.basename(path))
        if not m:
            continue
        subject = m.group("subject")
        grade = m.group("grade")
        out[subject]["files"].append(path)
        if grade is not None:
            out[subject]["grades"].add(int(grade))
    return out


def _validate_subject_grades(subject, grade_paths, errors):
    """学科开设年级档位内的连续性检查。

    规则：
    - 完全未建档（无文件）→ 返回 pending 列表空、不报错，由调用方登记为
      pending 学科；
    - 落库年级必须落在该学科开设档（SUBJECT_GRADE_RANGES）内，否则报 1
      条错（年级出档）；
    - math 保留原 CORE_GRADES 语义：核心 7-9 缺位 = 错；非核心 1-6 缺位
      = pending；
    - 其他学科档内缺位 = pending（K12 建设期允许部分年级落库）。
    """
    grades_present = sorted(g for g, _ in grade_paths if g is not None)
    if not grades_present:
        # 完全未建档：调用方单独登记为 pending 学科，此处不报错
        return []

    band = SUBJECT_GRADE_RANGES.get(subject)
    if band is None:
        band_start, band_end = 1, 12
    else:
        band_start, band_end = band

    # 1) 落库年级必须落在该学科开设档内
    for g in grades_present:
        if not (band_start <= g <= band_end):
            errors.append(
                f"subject {subject!r}: grade {g} outside offered band "
                f"{band_start}..{band_end}"
            )

    # 2) 档内连续性
    in_band = [g for g in grades_present if band_start <= g <= band_end]
    missing_in_band = [
        g for g in range(band_start, band_end + 1) if g not in in_band
    ]

    if subject == "math":
        # math 保留原语义：核心 7-9 缺位 = 错；非核心 1-6 缺位 = pending
        core_missing = [g for g in missing_in_band if g in MATH_CORE_GRADES]
        for g in core_missing:
            errors.append(f"missing core knowledge file: math_grade{g}.json")
        return [g for g in missing_in_band if g not in MATH_CORE_GRADES]

    # 其他学科：档内缺位视为 pending（K12 建设期允许部分年级落库）
    return missing_in_band


def _load_kp_subject(subject, grade_paths, errors):
    """加载单学科全部年级文件 → (merged_kps, kp_ids, pending_grades, seen_kp)。"""
    pending = _validate_subject_grades(subject, grade_paths, errors)
    merged_kps = []
    seen_kp = {}
    for grade, path in grade_paths:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        for kp in data["knowledge_points"]:
            if kp["id"] in seen_kp:
                errors.append(
                    f"duplicate kp id across files: {kp['id']} "
                    f"({seen_kp[kp['id']]} & {path})"
                )
                continue
            seen_kp[kp["id"]] = path
            merged_kps.append(kp)
            if not str(kp.get("standard_ref", "")).strip():
                errors.append(f"{kp['id']}: empty standard_ref")
            if not str(kp.get("description", "")).strip():
                errors.append(f"{kp['id']}: empty description")
            if not kp.get("cluster"):
                errors.append(f"{kp['id']}: empty cluster")
            kp_grade = int(kp.get("grade", 0))
            if not 1 <= kp_grade <= 12:
                errors.append(f"{kp['id']}: grade {kp_grade} out of 1..12")
            if kp_grade != grade:
                errors.append(
                    f"{kp['id']}: kp grade {kp_grade} != file grade {grade} ({path})"
                )
    return merged_kps, set(seen_kp), pending, seen_kp


def _load_subject_items(subject, item_paths, errors):
    """加载单学科题库 → items list, seen_item, seen_stem（学科内去重）。

    同时加载 data/items/_coverage_exemptions.json：列出 KP 的题目『正在
    采集中』豁免清单，仅豁免主知识点题数检查（K12 建设期允许仅图谱/
    误解完整但题目仍在迭代）。exemption 文件不存在则豁免集为空。
    """
    items = []
    seen_stem = {}
    seen_item = {}
    for path in item_paths:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        for it in data["items"]:
            if it["id"] in seen_item:
                errors.append(
                    f"duplicate item id: {it['id']} ({seen_item[it['id']]} & {path})"
                )
                continue
            seen_item[it["id"]] = path
            stem = str(it.get("stem", "")).strip()
            if stem in seen_stem:
                errors.append(f"duplicate stem: {it['id']} == {seen_stem[stem]}")
            else:
                seen_stem[stem] = it["id"]
            items.append(it)
    # 加载题目采集豁免清单（学科无关，所有豁免都对当前 subject 生效）
    item_exempt_kp_ids: set[str] = set()
    exempt_path = os.path.join(ROOT, "data", "coverage_exemptions.json")
    if os.path.exists(exempt_path):
        try:
            with open(exempt_path, encoding="utf-8") as f:
                edata = json.load(f)
            for ex in edata.get("exemptions", []):
                kp_id = ex.get("kp_id")
                if isinstance(kp_id, str) and kp_id.strip():
                    item_exempt_kp_ids.add(kp_id)
        except Exception as e:  # noqa: BLE001
            errors.append(f"item coverage exemption {exempt_path}: {e}")
    return items, seen_item, seen_stem, item_exempt_kp_ids


def _validate_items_for_subject(items, kp_ids, errors, min_items_per_kp, exempt_kp_ids=None):
    """单学科题库校验：schema v2 + 主知识点覆盖率。

    exempt_kp_ids：在误解库内已声明『无误解』豁免的 KP，同时豁免本题库的
    主知识点覆盖率（K12 建档期允许仅声明暂无题目/误解但已纳入图谱）。
    """
    if not items:
        return
    bank = itembank_from_dict({"items": items})
    errs = bank.validate_all(valid_kp_ids=kp_ids)
    errors.extend(f"itembank: {e}" for e in errs)
    errors.extend(f"item v2: {e}" for e in validate_bank_v2(items))
    primary_count = {}
    for it in items:
        kps = it.get("kps") or []
        if kps:
            primary_count[kps[0]] = primary_count.get(kps[0], 0) + 1
    skip = exempt_kp_ids or set()
    for kp_id in sorted(kp_ids):
        if kp_id in skip:
            continue
        n = primary_count.get(kp_id, 0)
        if n < min_items_per_kp:
            errors.append(
                f"coverage: {kp_id} has {n} primary items (< {min_items_per_kp})"
            )


def _load_subject_mc(subject, mc_info, kp_ids, errors, min_mc_per_kp):
    """加载单学科误解库 → entries, exemptions, mc_ids, exempt_kp_ids。"""
    all_entries = []
    all_exemptions = []
    for path in mc_info["files"]:
        tag = os.path.basename(path)
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        try:
            entries, exemptions = parse_bank(data)
        except Exception as e:  # noqa: BLE001
            errors.append(f"misconception bank {tag}: {e}")
            continue
        all_entries.extend(entries)
        all_exemptions.extend(exemptions)
    mc_ids = {e.id for e in all_entries}
    exempt_kp_ids: set[str] = set()
    if kp_ids:
        try:
            rep = audit(kp_ids, all_entries, all_exemptions, min_per_kp=min_mc_per_kp)
            exempt_kp_ids = set(rep.exempt_kp_ids)
            errors.extend(
                f"misconception coverage: {kp} has {count} (< {min_mc_per_kp}, "
                f"且无'无误解'声明)"
                for kp, count in rep.counts
                if kp in rep.deficient_kp_ids
            )
        except Exception as e:  # noqa: BLE001
            errors.append(f"misconception coverage: {e}")
    return all_entries, all_exemptions, mc_ids, exempt_kp_ids


def _load_subject_arch(subject, arch_paths, kp_ids, errors):
    """加载单学科母题库 → total count, per-file counts。"""
    seen_arch = set()
    total = 0
    per_file = []
    for path in arch_paths:
        tag = os.path.basename(path)
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        count = 0
        for a in data.get("archetypes", []):
            if a["id"] in seen_arch:
                errors.append(f"duplicate archetype id: {a['id']}")
            seen_arch.add(a["id"])
            for field in ("name", "pattern", "example"):
                if not str(a.get(field, "")).strip():
                    errors.append(f"{a['id']}: empty {field}")
            if not a.get("kp_ids"):
                errors.append(f"{a['id']}: no kp_ids")
            for k in a.get("kp_ids", []):
                if k not in kp_ids:
                    errors.append(f"{a['id']}: unknown kp {k}")
            if not a.get("variant_axes"):
                errors.append(f"{a['id']}: no variant_axes")
            count += 1
        per_file.append((tag, count))
        if count < 6:
            errors.append(f"{tag}: only {count} archetypes (< 6)")
        total += count
    return total, per_file


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-items-per-kp", type=int, default=3)
    ap.add_argument("--min-mc-per-kp", type=int, default=2,
                    help="每个知识点最少的典型误解条数（或显式声明无误解）")
    args = ap.parse_args()
    errors: list[str] = []

    # ---------- 1) 知识点图谱：扫描 data/knowledge/<subject>_grade<N>.json ----------
    knowledge_subjects = _discover_subjects(KNOWLEDGE_DIR, SUBJECT_KNOWLEDGE_RE)
    if not knowledge_subjects:
        errors.append("no subject knowledge files found")

    # 按学科聚合：subject → {merged_kps, kp_ids, pending_grades, seen_kp, items, mc, arch, ...}
    subjects_state: dict[str, dict] = {}
    for subject in sorted(knowledge_subjects):
        grade_paths = knowledge_subjects[subject]
        merged_kps, kp_ids, pending, seen_kp = _load_kp_subject(
            subject, grade_paths, errors
        )
        # 单学科图谱结构校验
        graph = None
        if merged_kps:
            try:
                graph = kpgraph_from_dict({"knowledge_points": merged_kps})
                errs = graph.validate()
                errors.extend(f"kpgraph[{subject}]: {e}" for e in errs)
            except Exception as e:  # noqa: BLE001
                errors.append(f"kpgraph[{subject}] build failed: {e}")
        subjects_state[subject] = {
            "merged_kps": merged_kps,
            "kp_ids": kp_ids,
            "pending_grades": pending,
            "seen_kp": seen_kp,
            "graph": graph,
            "items": [],
            "seen_item": {},
            "seen_stem": {},
            "mc_entries": [],
            "mc_exemptions": [],
            "mc_ids": set(),
            "arch_total": 0,
            "arch_files": [],
        }

    # ---------- 2) 题库：data/items/*.json 全量（glob 通配，按文件名前缀归类学科） ----------
    item_subjects = _discover_subjects(ITEMS_DIR, SUBJECT_ITEM_RE)
    if not item_subjects:
        errors.append("no item files found")
    for subject, grade_paths in item_subjects.items():
        if subject not in subjects_state:
            errors.append(
                f"item file for subject {subject!r} without knowledge file"
            )
            continue
        paths = [p for _, p in grade_paths]
        items, seen_item, seen_stem, item_exempt = _load_subject_items(
            subject, paths, errors
        )
        subjects_state[subject]["items"] = items
        subjects_state[subject]["seen_item"] = seen_item
        subjects_state[subject]["seen_stem"] = seen_stem
        subjects_state[subject]["item_exempt_kp_ids"] = item_exempt

    # ---------- 3) 误解库：data/misconceptions/*.json（按文件名前缀归类学科） ----------
    mc_subjects = _discover_mc_subjects(MC_DIR)
    if not mc_subjects:
        errors.append("no misconception files found")
    for subject, mc_info in mc_subjects.items():
        if subject not in subjects_state:
            errors.append(
                f"misconception file for subject {subject!r} without knowledge file"
            )
            continue
        entries, exemptions, mc_ids, exempt_kp_ids = _load_subject_mc(
            subject, mc_info, subjects_state[subject]["kp_ids"], errors,
            args.min_mc_per_kp,
        )
        subjects_state[subject]["mc_entries"] = entries
        subjects_state[subject]["mc_exemptions"] = exemptions
        subjects_state[subject]["mc_ids"] = mc_ids
        subjects_state[subject]["exempt_kp_ids"] = exempt_kp_ids

    # ---------- 4) 母题库：data/archetypes/*.json（按文件名前缀归类学科） ----------
    arch_subjects = _discover_subjects(ARCH_DIR, SUBJECT_ARCH_RE)
    if not arch_subjects:
        errors.append("no archetype files found")
    for subject, grade_paths in arch_subjects.items():
        if subject not in subjects_state:
            errors.append(
                f"archetype file for subject {subject!r} without knowledge file"
            )
            continue
        paths = [p for _, p in grade_paths]
        total, per_file = _load_subject_arch(
            subject, paths, subjects_state[subject]["kp_ids"], errors
        )
        subjects_state[subject]["arch_total"] = total
        subjects_state[subject]["arch_files"] = per_file

    # ---------- 覆盖率校验：每学科主知识点题数 + 误解归属 ----------
    for subject, st in subjects_state.items():
        kp_ids = st["kp_ids"]
        items = st["items"]
        if items and kp_ids:
            # 豁免集 = 误解库『无误解』豁免 ∪ 题库『题目采集中』豁免
            skip = (st.get("exempt_kp_ids") or set()) | (
                st.get("item_exempt_kp_ids") or set()
            )
            _validate_items_for_subject(
                items, kp_ids, errors, args.min_items_per_kp,
                exempt_kp_ids=skip,
            )
        # 题内误解 id 须在该学科误解库内
        for it in items:
            for m in it.get("misconceptions", []):
                if m not in st["mc_ids"]:
                    errors.append(
                        f"{it['id']}: unknown misconception {m} (subject={subject})"
                    )

    # ---------- 输出 ----------
    if errors:
        print(f"VALIDATION FAILED: {len(errors)} errors")
        for e in errors[:80]:
            print(f"  - {e}")
        if len(errors) > 80:
            print(f"  ... and {len(errors) - 80} more")
        return 1

    # 按 subject 汇总。math 行保持现有文案格式以保证既有断言不破；
    # 其他 subject 走统一文案。
    for subject in sorted(subjects_state):
        st = subjects_state[subject]
        kp_count = len(st["kp_ids"])
        item_count = len(st["items"])
        mc_count = len(st["mc_ids"])
        exempt_count = len(st["mc_exemptions"])
        arch_count = st["arch_total"]
        total_items_v, verified_items_v = verification_stats(st["items"])
        pending = st["pending_grades"]
        pending_str = (
            f", grades {','.join(map(str, pending))} pending"
            if pending else ""
        )
        if subject == "math":
            # math 行保持现有文案格式（现有断言锁定的逐字）
            print(
                f"VALIDATION OK: {kp_count} kps, {item_count} items, "
                f"{mc_count} misconceptions (>= {args.min_mc_per_kp} per kp "
                f"or exempt, {exempt_count} exempt), {arch_count} archetypes, "
                f"schema v2 source ok, {verified_items_v}/{total_items_v} "
                f"items dual-agent-verified{pending_str}"
            )
        else:
            print(
                f"VALIDATION OK: subject={subject} — {kp_count} kps, "
                f"{item_count} items, {mc_count} misconceptions "
                f"(>= {args.min_mc_per_kp} per kp or exempt, {exempt_count} exempt), "
                f"{arch_count} archetypes, {verified_items_v}/{total_items_v} "
                f"items dual-agent-verified{pending_str}"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
