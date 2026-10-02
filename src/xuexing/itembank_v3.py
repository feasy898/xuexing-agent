"""itembank_v3 —— item schema v3 新字段校验层（v2 的扩展，不改动 v2）。

唯一权威契约：specs/frozen/itembank_v3.spec.md（冻结 v1）。作为冻结模块
itembank_v2 的**兄弟校验层**：v2 的 source/verification 字段完整性仍由
``xuexing.itembank_v2.validate_item_v2`` 负责（本模块不重复、不代理、不 import 它——
完整 v3 入库校验 = 同一 item 先后跑 v2 与 v3，两者消息拼接）；本模块只校验 v3 在
v2 字段之上新增的五个可选字段：

- ``form``：题型形态标签（严格枚举，非空、成员判定用原始值）；
- ``acceptable_variants``：可接受答案变体表（仅 fill/solve/essay/proof 类可带，
  非空 list、元素为非空白 str、按原始字面值去重）；
- ``scoring_points``：分步给分点表（与 acceptable_variants 二选一、可都无）；
- ``rubric``：评分量表（仅 essay 类必填；各维 max_score 之和 == total）；
- ``textbook_ref``：教材出处（``<出版社代码>:<册>:<章>`` 三段小写字母数字）。

模块纯度：两个公开函数均为纯函数——无 IO、无随机、无时钟、不读环境、无全局可变
状态；消息前缀纪律与错误消息渲染纪律与 itembank_v2 逐字一致（id 字面渲染、
违规值 repr 渲染），使两个校验层的输出可直接拼接消费。

装载约束（与 v2 相同）：本文件可被 spec_from_file_location 以顶层模块名
``_regen_itembank_v3`` 装载并顶替 sys.modules["xuexing.itembank_v3"]，因此不使用
``from __future__ import annotations``、不使用相对导入；本模块零 xuexing 依赖
（不 import 任何同包模块，也不需要 xuexing.types——校验面向题库 dict）。
"""

import math
import re

__all__ = [
    "SCHEMA_VERSION",
    "FORM_VALUES",
    "VARIANT_FORMS",
    "TEXTBOOK_REF_RE",
    "validate_item_v3",
    "validate_items_v3",
]

SCHEMA_VERSION = 3
# 题型形态标签枚举（冻结，canonical 顺序）。form 的成员判定用原始值（不 strip）。
FORM_VALUES = (
    "choice",
    "fill",
    "solve",
    "essay",
    "proof",
    "experiment",
    "comprehension",
    "cloze",
    "listening",
)
# 可携带 acceptable_variants 的题型子集（冻结，FORM_VALUES 的子序列）。
VARIANT_FORMS = ("fill", "solve", "essay", "proof")
# textbook_ref 格式：恰好三段，每段非空的小写 ASCII 字母数字，fullmatch 锚定。
TEXTBOOK_REF_RE = re.compile(r"[a-z0-9]+:[a-z0-9]+:[a-z0-9]+")

_NOT_A_DICT = "item is not a dict"
_DIMENSION_KEYS = frozenset(("name", "max_score", "level_descriptors"))
_LEVEL_KEYS = frozenset(("level", "min_score", "desc"))
_RUBRIC_KEYS = frozenset(("total", "dimensions"))
_SCORING_POINT_KEYS = frozenset(("point", "score"))


def _prefix(item):
    # 与 itembank_v2 逐字一致：id 键存在按值字面渲染（f-string，无 repr 引号；
    # falsy/非 str/dict 照渲染）；键缺失 → "<no-id>: "
    if "id" in item:
        return f"{item['id']}: "
    return "<no-id>: "


def _is_number(value):
    # bool 是 int 子类，一律按非数字拒绝；NaN/inf 同样拒绝（math.isfinite）。
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _is_nonblank_str(value):
    return isinstance(value, str) and value.strip() != ""


# ---------------------------------------------------------------------------
# 规则目录（§3.2：F1→F5 固定顺序累积、不短路；各规则独立评估实际值）
# ---------------------------------------------------------------------------


def _form_errors(item, p, errors):
    """F1 form：可选；键存在时原始值必须恰为 FORM_VALUES 成员（非 str/空白/未知同消息）。"""
    if "form" in item:
        form = item["form"]
        if not (isinstance(form, str) and form in FORM_VALUES):
            errors.append(f"{p}bad form {form!r}")


def _variants_errors(item, p, errors):
    """F2 acceptable_variants：可选；互斥 → 题型门 → 类型 → 元素 → 判重。

    - F2a 互斥：两个键**同时存在**即报（至多一条，与实际取值无关）；
    - F2b 题型门：item.get("form")（原始值）不在 VARIANT_FORMS 即报（form 缺失/
      非法/其余题型同报——变体表只允许 fill/solve/essay/proof 声明携带）；
    - F2c 类型：必须为 list（tuple/str/None 等同拒）；为空 list 同拒；
    - F2d 元素（仅当通过 F2c 的非空 list）：逐元素（列表序）非 str、strip 后空、
      或带首尾空白 → 每坏元素一条（repr 渲染）；
    - F2e 判重（仅当通过 F2c）：全部 str 元素按**原始字面值**判重（不 strip、含
      F2d 坏元素），至多一条且恒在全部 F2d 消息之后。
    """
    if "acceptable_variants" in item and "scoring_points" in item:
        errors.append(f"{p}acceptable_variants and scoring_points are mutually exclusive")
    if "acceptable_variants" not in item:
        return
    if item.get("form") not in VARIANT_FORMS:
        errors.append(f"{p}acceptable_variants requires form in fill/solve/essay/proof")
    variants = item["acceptable_variants"]
    if not isinstance(variants, list):
        errors.append(f"{p}acceptable_variants must be a list, got {variants!r}")
        return
    if not variants:
        errors.append(f"{p}acceptable_variants must be non-empty")
        return
    for el in variants:
        if not _is_nonblank_str(el) or el != el.strip():
            errors.append(f"{p}bad acceptable_variant {el!r}")
    seen = set()
    for el in variants:
        if isinstance(el, str):
            if el in seen:
                errors.append(f"{p}duplicate acceptable_variants")
                break
            seen.add(el)


def _scoring_points_errors(item, p, errors):
    """F3 scoring_points：可选；类型门 → 逐条目（列表序）。

    - F3a 类型：必须为非空 list（tuple/str/None 同拒；空 list 同拒）；
    - F3b 条目（仅当通过 F3a）：非 dict 或键集合非恰 {point,score} →
      ``bad scoring_point {entry!r}``（一条，不再拆分）；随后 point 必须为非空白
      str、score 必须为有限实数且 > 0（bool 是非 int 拒绝口径之外的 number 排除项）。
    """
    if "scoring_points" not in item:
        return
    points = item["scoring_points"]
    if not isinstance(points, list):
        errors.append(f"{p}scoring_points must be a list, got {points!r}")
        return
    if not points:
        errors.append(f"{p}scoring_points must be non-empty")
        return
    for entry in points:
        if not isinstance(entry, dict) or frozenset(entry) != _SCORING_POINT_KEYS:
            errors.append(f"{p}bad scoring_point {entry!r}")
            continue
        point = entry["point"]
        if not _is_nonblank_str(point):
            errors.append(f"{p}scoring_point point must be a non-blank str, got {point!r}")
        score = entry["score"]
        if not (_is_number(score) and score > 0):
            errors.append(f"{p}scoring_point score must be a number > 0, got {score!r}")


def _level_errors(levels, p, errors):
    """level_descriptors 逐条（列表序）：形状门 → level → min_score → desc。"""
    for entry in levels:
        if not isinstance(entry, dict) or frozenset(entry) != _LEVEL_KEYS:
            errors.append(f"{p}bad rubric level {entry!r}")
            continue
        level = entry["level"]
        if not _is_nonblank_str(level):
            errors.append(f"{p}rubric level must be a non-blank str, got {level!r}")
        min_score = entry["min_score"]
        if not (_is_number(min_score) and min_score >= 0):
            errors.append(f"{p}rubric level min_score must be a number >= 0, got {min_score!r}")
        desc = entry["desc"]
        if not _is_nonblank_str(desc):
            errors.append(f"{p}rubric level desc must be a non-blank str, got {desc!r}")


def _rubric_errors(item, p, errors):
    """F4 rubric：可选；form 原始值恰为 "essay" 时必填。

    - F4a 必填门：form == "essay" 且键缺失 → ``essay requires rubric``；
    - F4b 结构（键存在时）：必须为 dict 且键集合恰 {total,dimensions}（否则一条
      ``bad rubric``，后续检查跳过——结构门，与 v2 的 V3b 门同构）；total 必须为
      有限实数 > 0；dimensions 必须为非空 list（后续逐维检查以通过本条为前提）；
    - F4c 逐维（列表序）：形状门（dict 且键恰 {name,max_score,level_descriptors}）
      → name 非空白 str → max_score 有限实数 > 0 → level_descriptors 非空 list
      （再逐条 _level_errors）；全部维消息之后，按 str name 的原始值判重至多一条；
    - F4d 和校验：仅当 total 合法且每个维的 max_score 均合法时，评估各维
      max_score 之和与 total 的**精确相等**（不等才报；有非法分量则跳过不报）。
    """
    if item.get("form") == "essay" and "rubric" not in item:
        errors.append(f"{p}essay requires rubric")
    if "rubric" not in item:
        return
    rubric = item["rubric"]
    if not isinstance(rubric, dict) or frozenset(rubric) != _RUBRIC_KEYS:
        errors.append(f"{p}bad rubric {rubric!r}")
        return
    total = rubric["total"]
    if not (_is_number(total) and total > 0):
        errors.append(f"{p}rubric total must be a number > 0, got {total!r}")
    dimensions = rubric["dimensions"]
    if not isinstance(dimensions, list) or not dimensions:
        errors.append(f"{p}rubric dimensions must be a non-empty list, got {dimensions!r}")
        return
    max_scores_ok = _is_number(total) and total > 0
    str_names = []
    for dim in dimensions:
        if not isinstance(dim, dict) or frozenset(dim) != _DIMENSION_KEYS:
            errors.append(f"{p}bad rubric dimension {dim!r}")
            max_scores_ok = False
            continue
        name = dim["name"]
        if not _is_nonblank_str(name):
            errors.append(f"{p}rubric dimension name must be a non-blank str, got {name!r}")
        else:
            str_names.append(name)
        max_score = dim["max_score"]
        if not (_is_number(max_score) and max_score > 0):
            errors.append(f"{p}rubric dimension max_score must be a number > 0, got {max_score!r}")
            max_scores_ok = False
        levels = dim["level_descriptors"]
        if not isinstance(levels, list) or not levels:
            errors.append(
                f"{p}rubric dimension level_descriptors must be a non-empty list, got {levels!r}"
            )
        else:
            _level_errors(levels, p, errors)
    # 判重：全部 str name 按原始值，至多一条，恒在全部逐维消息之后（与 v2 的 C3 同构）
    seen_names = set()
    for name in str_names:
        if name in seen_names:
            errors.append(f"{p}duplicate rubric dimension names")
            break
        seen_names.add(name)
    if max_scores_ok:
        total_sum = sum(dim["max_score"] for dim in dimensions)
        if total_sum != total:
            errors.append(f"{p}rubric dimensions max_score sum {total_sum!r} != total {total!r}")


def _textbook_ref_errors(item, p, errors):
    """F5 textbook_ref：可选；键存在时必须为 str 且 fullmatch 三段小写字母数字。"""
    if "textbook_ref" in item:
        ref = item["textbook_ref"]
        if not (isinstance(ref, str) and TEXTBOOK_REF_RE.fullmatch(ref)):
            errors.append(f"{p}bad textbook_ref {ref!r}")


def validate_item_v3(item) -> list:
    """单题 v3 新字段校验：F1→F5 固定顺序累积、不短路；非 dict 只返回一条。

    与 itembank_v2 的边界（冻结）：本函数**不检查** source/source_ref/verification
    等 v2 字段——完整 v3 入库校验由调用方对同一 item 先后运行 validate_item_v2 与
    validate_item_v3 并拼接两者消息完成。
    """
    if not isinstance(item, dict):
        return [_NOT_A_DICT]
    p = _prefix(item)
    errors = []
    _form_errors(item, p, errors)
    _variants_errors(item, p, errors)
    _scoring_points_errors(item, p, errors)
    _rubric_errors(item, p, errors)
    _textbook_ref_errors(item, p, errors)
    return errors


def validate_items_v3(items) -> list:
    """逐题 validate_item_v3，按输入原序拼接；不去重不排序；空输入 → []。

    入参须为可迭代对象；不可迭代时 TypeError 原样传播（与 itembank_v2 的可迭代
    消费函数同纪律）；可迭代时对任意元素不抛异常。
    """
    errors = []
    for item in items:
        errors.extend(validate_item_v3(item))
    return errors
