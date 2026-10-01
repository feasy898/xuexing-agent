"""dual_verify —— 双代理独立复验题库的确定性内核（盲重写实例）。

唯一权威契约：``specs/frozen/dual_verify.spec.md``。本文件只依据该契约与公开接口
实现，未参考 ``src/xuexing/`` 下任何实现、未读 tests/、未读任何既有 regen 产物。

装载约束（契约 §2，注入门 ``spec_from_file_location`` 装载为顶层模块
``_regen_dual_verify`` 并顶替 ``sys.modules["xuexing.dual_verify"]``）：

* 只 import ``re`` 与 ``dataclasses``，不 import 任何 xuexing 模块；
* 禁止相对导入、禁止 ``from __future__ import annotations``（dataclasses 解析
  字符串注解时按 ``sys.modules.get(cls.__module__)`` 查表会取到 None）；
* 注解一律写真实对象（``str`` / ``bool`` / ``dict`` / ``tuple`` …）。
"""

import re
from dataclasses import dataclass

__all__ = [
    "DualVerifyError",
    "COMPARISON_TOLERANCE",
    "UNIT_ALIASES",
    "VERDICT_AGREE",
    "VERDICT_DISAGREE",
    "VERDICT_INCOMPLETE",
    "normalize_answer",
    "answers_match",
    "verify_item",
    "verification_record",
    "make_record",
    "backfill_item",
    "verify_bank",
    "arbitration_rows",
    "DualVerifyReport",
]


# --------------------------------------------------------------------------
# 异常与常量（契约 §3.1）
# --------------------------------------------------------------------------

class DualVerifyError(ValueError):
    """本模块唯一异常类型（ValueError 直接子类）。"""


#: 数值等值相对容差（恒等于 grading.GRADE_TOLERANCE）。
COMPARISON_TOLERANCE = 1e-9

#: 单位别名表：键为表层写法（含规范形自身），值为规范单位；只归一别名、不做数值换算。
UNIT_ALIASES = {
    "千米": "千米",
    "公里": "千米",
    "米": "米",
    "厘米": "厘米",
    "毫米": "毫米",
    "平方千米": "平方千米",
    "平方公里": "平方千米",
    "平方米": "平方米",
    "平方分米": "平方分米",
    "平方厘米": "平方厘米",
    "立方米": "立方米",
    "立方分米": "立方分米",
    "立方厘米": "立方厘米",
    "公顷": "公顷",
    "吨": "吨",
    "克": "克",
    "千克": "千克",
    "公斤": "千克",
    "元": "元",
    "角": "角",
    "分": "分",
    "升": "升",
    "毫升": "毫升",
    "小时": "小时",
    "时": "小时",
    "分钟": "分",
    "秒": "秒",
    "度": "度",
}

VERDICT_AGREE = "agree"
VERDICT_DISAGREE = "disagree"
VERDICT_INCOMPLETE = "incomplete"

# 逐代理状态字面（冻结面，暴露它们的常量名不属公开 API）。
ST_MATCH = "match"
ST_MISMATCH = "mismatch"
ST_NO_ANSWER = "no_answer"

_ITEM_TYPES = ("choice", "fill", "solve")

# 最长单位后缀长度（4，如「平方公里」）；单位剥离按后缀宽度 4→1 最长优先。
_MAX_UNIT_LEN = max(len(alias) for alias in UNIT_ALIASES)


# --------------------------------------------------------------------------
# 内部工具：正则与字符类
# --------------------------------------------------------------------------

_WHITESPACE_RE = re.compile(r"\s+")
_TRAILING_PUNCT_RE = re.compile(r"[\s。、,.;!?]+$")
_THOUSAND_COMMA_RE = re.compile(r"(?<=[0-9]),(?=[0-9]{3}(?![0-9]))")
_SPACE_RE = re.compile(r"\s")
_COMPONENT_SPLIT_RE = re.compile(r"[或和、；，]")

# 数值解析文法（全文锚定；ASCII [0-9]），按契约 §3.3 顺序：带分数 → 分数 → 小数。
_MIXED_NUMBER_RE = re.compile(r"([+-]?)([0-9]+) ([0-9]+)\s*/\s*([0-9]+)")
_FRACTION_RE = re.compile(r"([+-]?)([0-9]+)\s*/\s*([0-9]+)")
_DECIMAL_RE = re.compile(
    r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?"
)

# 赋值前缀可由 ASCII 字母 / 希腊字母 U+0370–U+03FF / ∠ U+2220 /
# 下标数字 U+2080–U+2089 / 上标 ¹²³ / 撇号 '′ 组成，总长 ≤6。
_ASSIGN_PREFIX_CHARS = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "'′"
    "¹²³"
    "∠"
).union(chr(code) for code in range(0x0370, 0x0400)).union(
    chr(code) for code in range(0x2080, 0x208A)
)
_ASSIGN_PREFIX_MAX_LEN = 6


def _fold_fullwidth(text):
    """N1：全角 ASCII 折叠 + U+3000 全角空格 → 半角空格。"""
    out = []
    for ch in text:
        code = ord(ch)
        if 0xFF01 <= code <= 0xFF5E:
            out.append(chr(code - 0xFEE0))
        elif code == 0x3000:
            out.append(" ")
        else:
            out.append(ch)
    return "".join(out)


def _key(text):
    """去空白键（R5 字面兜底 / choice 全文趟用）。"""
    return _SPACE_RE.sub("", text)


def _is_clean_id(value):
    """标识符类字段（item id / agent id）的合法性与排序前提一致：非空、无首尾空白。"""
    return isinstance(value, str) and value == value.strip() and value.strip() != ""


# --------------------------------------------------------------------------
# 归一化 N1–N5（契约 §3.2）
# --------------------------------------------------------------------------

def normalize_answer(text):
    """按 N1→N5 顺序归一化答案文本；非 str 入参抛 DualVerifyError。"""
    if not isinstance(text, str):
        raise DualVerifyError("normalize_answer expects a str, got " + type(text).__name__)
    value = _fold_fullwidth(text)              # N1 全角折叠
    value = _WHITESPACE_RE.sub(" ", value).strip()   # N2 空白折叠
    value = _TRAILING_PUNCT_RE.sub("", value)        # N3 尾部剥离
    value = _THOUSAND_COMMA_RE.sub("", value)         # N4 千分位逗号删除
    return value.lower()                              # N5 小写化


# --------------------------------------------------------------------------
# 数值解析 / 单位门 / 分量比对（契约 §3.3）
# --------------------------------------------------------------------------

def _parse_plain_number(text):
    """带分数 → 分数 → 小数（不含百分数分支）。不可解析返回 None。"""
    matched = _MIXED_NUMBER_RE.fullmatch(text)
    if matched is not None:
        denominator = int(matched.group(4))
        if denominator == 0:
            return None
        value = int(matched.group(2)) + int(matched.group(3)) / denominator
        return -value if matched.group(1) == "-" else value
    matched = _FRACTION_RE.fullmatch(text)
    if matched is not None:
        denominator = int(matched.group(3))
        if denominator == 0:
            return None
        value = int(matched.group(2)) / denominator
        return -value if matched.group(1) == "-" else value
    if _DECIMAL_RE.fullmatch(text) is not None:
        return float(text)
    return None


def _parse_number(text):
    """数值解析：先判百分数（`%` 结尾，剥后 strip，再按三条文法解析，值 ÷100）。"""
    stripped = text.strip()
    if stripped == "":
        return None
    if stripped.endswith("%"):
        inner = _parse_plain_number(stripped[:-1].strip())
        if inner is None:
            return None
        return inner / 100.0
    return _parse_plain_number(stripped)


def _strip_unit(text):
    """尾部单位剥离（最长优先）：命中且剩余部非空 → (剩余部, 规范单位)；
    纯单位词或无命中 → (原文, None)。只归一别名，不做任何数值换算。"""
    for width in range(_MAX_UNIT_LEN, 0, -1):
        if width > len(text):
            continue
        suffix = text[-width:]
        canonical = UNIT_ALIASES.get(suffix)
        if canonical is None:
            continue
        remainder = text[:-width].strip()
        if remainder:
            return remainder, canonical
        return text, None
    return text, None


def _strip_assignment_prefix(text):
    """剥赋值前缀：首个 `=` 之前全部由允许字符组成、总长 ≤6 且 `=` 后至少 1 字符。"""
    index = text.find("=")
    if index <= 0 or index > _ASSIGN_PREFIX_MAX_LEN:
        return text
    if all(ch in _ASSIGN_PREFIX_CHARS for ch in text[:index]):
        remainder = text[index + 1:]
        if remainder:
            return remainder
    return text


def _component_match(left, right):
    """单分量比对（规则 R3）：单位门 → 数值等价 → 字面相等。入参均为已归一化文本。"""
    left_rest, left_unit = _strip_unit(left)
    right_rest, right_unit = _strip_unit(right)
    if left_unit != right_unit:
        return False
    left_value = _parse_number(left_rest)
    right_value = _parse_number(right_rest)
    if left_value is not None and right_value is not None:
        scale = max(1.0, abs(left_value), abs(right_value))
        return abs(left_value - right_value) <= COMPARISON_TOLERANCE * scale
    return _key(left_rest) == _key(right_rest)


def _prepare_components(raw):
    """原始文本按全角分隔符拆分 → 逐分量归一化 → 剥赋值前缀。"""
    return [
        _strip_assignment_prefix(normalize_answer(part))
        for part in _COMPONENT_SPLIT_RE.split(raw)
    ]


def _multiset_match(left_parts, right_parts):
    """多答案多重集配对：数量不等直接 False，否则按 first-fit 逐个配对。"""
    if len(left_parts) != len(right_parts):
        return False
    pool = list(right_parts)
    for part in left_parts:
        for index, candidate in enumerate(pool):
            if _component_match(part, candidate):
                pool.pop(index)
                break
        else:
            return False
    return True


def _resolve_option(target, labels, texts):
    """choice 选项解析：标签趟（`==` 取最小下标）优先，未命中再走全文趟（去空白键）。"""
    try:
        return labels.index(target)
    except ValueError:
        pass
    target_key = _key(target)
    for index, text in enumerate(texts):
        if _key(text) == target_key:
            return index
    return None


# --------------------------------------------------------------------------
# 比对（契约 §3.3）
# --------------------------------------------------------------------------

def answers_match(key_answer, proposed, item_type="fill", options=None):
    """verification 级标答-提案等值判定。"""
    if not isinstance(key_answer, str):
        raise DualVerifyError("key_answer must be a str")
    if not isinstance(proposed, str):
        raise DualVerifyError("proposed must be a str")
    if item_type not in _ITEM_TYPES:
        raise DualVerifyError("item_type must be one of choice/fill/solve")
    if item_type == "choice":
        if not isinstance(options, list) or len(options) < 2:
            raise DualVerifyError("choice items require a list of at least 2 options")

    if item_type == "choice":
        texts = [normalize_answer(option) for option in options]
        labels = [text.split(".", 1)[0].strip() for text in texts]
        correct = _resolve_option(normalize_answer(key_answer), labels, texts)
        given = _resolve_option(normalize_answer(proposed), labels, texts)
        # 标答解析不到不抛错，判 False。
        return correct is not None and correct == given

    key_normalized = normalize_answer(key_answer)
    proposed_normalized = normalize_answer(proposed)
    if key_normalized == proposed_normalized:                      # R1
        return True
    if _multiset_match(
        _prepare_components(key_answer),
        _prepare_components(proposed),
    ):                                                             # R4
        return True
    return _key(key_normalized) == _key(proposed_normalized)       # R5


# --------------------------------------------------------------------------
# 单题裁决（契约 §3.4）
# --------------------------------------------------------------------------

def verify_item(item, agent_answers):
    """单题双代理裁决，返回新构造的恰三键 dict。"""
    if not isinstance(item, dict):
        raise DualVerifyError("item must be a dict")

    item_id = item.get("id")
    if not _is_clean_id(item_id):
        raise DualVerifyError("item['id'] must be a non-empty str without surrounding blanks")

    answer = item.get("answer")
    if not isinstance(answer, str) or answer.strip() == "":
        raise DualVerifyError("item['answer'] must be a non-blank str")

    item_type = item.get("item_type")
    if item_type not in _ITEM_TYPES:
        raise DualVerifyError("item['item_type'] must be one of choice/fill/solve")

    options = item.get("options")
    if item_type == "choice" and (not isinstance(options, list) or len(options) < 2):
        raise DualVerifyError("choice items require a list of at least 2 options")

    if not isinstance(agent_answers, dict):
        raise DualVerifyError("agent_answers must be a dict")

    # sorted 先于 id 校验：键不可比大小 → TypeError（契约 §6）。
    ordered_ids = sorted(agent_answers)
    for agent_id in ordered_ids:
        if not _is_clean_id(agent_id):
            raise DualVerifyError("agent id must be a non-empty str without surrounding blanks")

    statuses = []
    for agent_id in ordered_ids:
        raw = agent_answers[agent_id]
        if not isinstance(raw, str) or raw.strip() == "":
            statuses.append((agent_id, ST_NO_ANSWER))       # 容忍，绝不升级为 mismatch
        elif answers_match(answer, raw, item_type, item.get("options")):
            statuses.append((agent_id, ST_MATCH))
        else:
            statuses.append((agent_id, ST_MISMATCH))

    n_mismatch = sum(1 for _, status in statuses if status == ST_MISMATCH)
    n_match = sum(1 for _, status in statuses if status == ST_MATCH)
    if n_mismatch >= 1:
        verdict = VERDICT_DISAGREE
    elif n_match >= 2:
        verdict = VERDICT_AGREE
    else:
        verdict = VERDICT_INCOMPLETE

    return {"item_id": item_id, "verdict": verdict, "statuses": tuple(statuses)}


# --------------------------------------------------------------------------
# 记录与回填（契约 §3.5）
# --------------------------------------------------------------------------

def make_record(agent_ids):
    """由代理 id 的任意可迭代对象构造 v2 合法记录（去重 + 码点升序 + ≥2 下限）。"""
    unique = set()
    for agent_id in agent_ids:
        if not _is_clean_id(agent_id):
            raise DualVerifyError("agent id must be a non-empty str without surrounding blanks")
        unique.add(agent_id)
    if len(unique) < 2:
        raise DualVerifyError("a verification record needs at least 2 distinct agents")
    return {"agents": sorted(unique), "answers_agree": True}


def verification_record(verify_result):
    """verify_item 结果 → v2 记录；非 agree 一律 None（诚实缺口 / 分歧不回填）。"""
    if not isinstance(verify_result, dict):
        raise DualVerifyError("verify_result must be a dict")
    if "verdict" not in verify_result:
        raise DualVerifyError("verify_result must carry a 'verdict' key")
    if verify_result["verdict"] != VERDICT_AGREE:
        return None
    statuses = verify_result.get("statuses") or ()
    return make_record(
        agent_id for agent_id, status in statuses if status == ST_MATCH
    )


def backfill_item(item, record):
    """纯回填：不修改入参，record=None 返回无 verification 键的副本。"""
    if not isinstance(item, dict):
        raise DualVerifyError("item must be a dict")
    if record is None:
        return dict(item)

    if not isinstance(record, dict):
        raise DualVerifyError("record must be a dict or None")
    agents = record.get("agents")
    if not isinstance(agents, list) or len(agents) < 2:
        raise DualVerifyError("record['agents'] must be a list of at least 2 ids")
    for agent_id in agents:
        if not _is_clean_id(agent_id):
            raise DualVerifyError("agent id must be a non-empty str without surrounding blanks")
    if len(set(agents)) != len(agents):
        raise DualVerifyError("record['agents'] must not contain duplicates")
    if record.get("answers_agree") is not True:
        raise DualVerifyError("record['answers_agree'] must be True")

    out = dict(item)
    out["verification"] = {"agents": list(agents), "answers_agree": True}
    return out


# --------------------------------------------------------------------------
# 全库裁决（契约 §3.6）
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class DualVerifyReport:
    """全库裁决报告，六个字段全部 tuple 化，顺序恒为 items 输入原序。"""

    item_ids: tuple
    verdicts: tuple
    agreed_item_ids: tuple
    disputed_item_ids: tuple
    incomplete_item_ids: tuple
    records: tuple

    def counts(self):
        """三键恒在（值为零也保留），每次调用返回新 dict。"""
        return {
            VERDICT_AGREE: len(self.agreed_item_ids),
            VERDICT_DISAGREE: len(self.disputed_item_ids),
            VERDICT_INCOMPLETE: len(self.incomplete_item_ids),
        }


def verify_bank(items, answers_by_item):
    """按 items 输入原序逐题裁决，返回 DualVerifyReport。"""
    if not isinstance(answers_by_item, dict):
        raise DualVerifyError("answers_by_item must be a dict")

    item_ids = []
    verdicts = []
    agreed = []
    disputed = []
    incomplete = []
    records = []

    for item in items:
        answers = answers_by_item.get(item["id"], {})   # 缺条目按空 dict → incomplete
        result = verify_item(item, answers)
        item_id = result["item_id"]
        verdict = result["verdict"]
        item_ids.append(item_id)
        verdicts.append((item_id, verdict))
        if verdict == VERDICT_AGREE:
            agreed.append(item_id)
            records.append((item_id, verification_record(result)))
        elif verdict == VERDICT_DISAGREE:
            disputed.append(item_id)
            records.append((item_id, None))
        else:
            incomplete.append(item_id)
            records.append((item_id, None))

    return DualVerifyReport(
        item_ids=tuple(item_ids),
        verdicts=tuple(verdicts),
        agreed_item_ids=tuple(agreed),
        disputed_item_ids=tuple(disputed),
        incomplete_item_ids=tuple(incomplete),
        records=tuple(records),
    )


def arbitration_rows(items, answers_by_item):
    """人工仲裁队列行：仅 mismatch 状态的代理成行，返回 tuple[dict, ...]。"""
    if not isinstance(answers_by_item, dict):
        raise DualVerifyError("answers_by_item must be a dict")

    rows = []
    for item in items:
        answers = answers_by_item.get(item["id"], {})
        result = verify_item(item, answers)
        for agent_id, status in result["statuses"]:
            if status != ST_MISMATCH:
                continue
            rows.append(
                {
                    "item_id": result["item_id"],
                    "key_answer": item["answer"],
                    "agent": agent_id,
                    "proposed": answers[agent_id],
                }
            )
    return tuple(rows)
