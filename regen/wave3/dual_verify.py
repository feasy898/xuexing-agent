"""xuexing.dual_verify —— 双代理独立复验题库的确定性内核（盲重写实例）。

唯一权威契约：specs/frozen/dual_verify.spec.md（冻结 v1，契约第三波）。

装载约束（契约 §2）：仅依赖标准库 ``re`` 与 ``dataclasses``；不 import 任何
xuexing 模块；禁止相对导入与 ``from __future__ import annotations``（注解一律
写真实对象）；无文件/网络 IO、无随机、无系统时钟、无环境读取、无全局可变状态。
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


class DualVerifyError(ValueError):
    """本模块唯一异常类型（ValueError 直接子类）。"""


COMPARISON_TOLERANCE = 1e-9

VERDICT_AGREE = "agree"
VERDICT_DISAGREE = "disagree"
VERDICT_INCOMPLETE = "incomplete"

# verify_item 返回的 statuses 状态字面（冻结面是这三个字面值；常量名不属冻结面）。
_ST_MATCH = "match"
_ST_MISMATCH = "mismatch"
_ST_NO_ANSWER = "no_answer"

_ITEM_TYPES = ("choice", "fill", "solve")

# 单位别名表：28 个表层写法 -> 23 个规范单位（契约 §3.1 冻结表）。
# 只归一别名、不做任何数值换算；规范形自映射；没有裸的「分米」。
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

# 最长单位后缀宽（= 4，如「平方公里」）；单位剥离按宽度 4→1 最长优先。
_MAX_UNIT_LEN = max(len(key) for key in UNIT_ALIASES)

_FULLWIDTH_START = 0xFF01
_FULLWIDTH_END = 0xFF5E
_FULLWIDTH_OFFSET = 0xFEE0

# N3 尾部剥离集合（契约 §3.2 N3：{'。', '、', ',', '.', ';', '!', '?'} 及空白字符）。
_TAIL_PUNCT = frozenset("。、,.;!?")

# N2 内部空白折叠。
_WS_RUN_RE = re.compile(r"\s+")

# N4 千分位逗号：左邻 ASCII 数字、右邻恰 3 个 ASCII 数字且其后一位非数字。
_THOUSANDS_RE = re.compile(r"(?<=[0-9]),(?=[0-9]{3}(?![0-9]))")

# 数值解析文法（契约 §3.3；ASCII [0-9]，全文锚定；带分数整数部与分数部之间恰一个空格、
# 分数斜杠两侧容忍任意 \s* 空白；小数含 .5 / 3. / 科学计数）。
_MIXED_NUMBER_RE = re.compile(r"([+-]?)([0-9]+) ([0-9]+)\s*/\s*([0-9]+)")
_FRACTION_RE = re.compile(r"([+-]?)([0-9]+)\s*/\s*([0-9]+)")
_DECIMAL_RE = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?")

# R4 多答案分量分隔符：全角 或|和|、|；|，（ASCII 逗号不拆）。
_SEPARATOR_RE = re.compile(r"或|和|、|；|，")


def normalize_answer(text: str) -> str:
    """归一化规则表 N1–N5，按序执行（契约 §3.2）。

    N1 全角折叠（[0xFF01,0xFF5E] → ord−0xFEE0；U+3000 → 半角空格）；
    N2 内部空白折叠为单个半角空格并去首尾；N3 尾部标点/空白剥离；
    N4 千分位逗号删除；N5 小写化。非 str 入参抛 DualVerifyError。
    """
    if not isinstance(text, str):
        raise DualVerifyError("normalize_answer 只接受 str 入参")
    chars = []
    for ch in text:
        code = ord(ch)
        if _FULLWIDTH_START <= code <= _FULLWIDTH_END:
            chars.append(chr(code - _FULLWIDTH_OFFSET))
        elif code == 0x3000:
            chars.append(" ")
        else:
            chars.append(ch)
    folded = "".join(chars)
    folded = _WS_RUN_RE.sub(" ", folded).strip()
    folded = _strip_tail(folded)
    folded = _THOUSANDS_RE.sub("", folded)
    return folded.lower()


def _strip_tail(text):
    """N3：只从右端循环删除尾部标点与空白字符，不动内部。"""
    while text:
        last = text[-1]
        if last in _TAIL_PUNCT or last.isspace():
            text = text[:-1]
        else:
            break
    return text


def _squash(text):
    """_key：删除全部空白（R5 / choice 全文趟用）。"""
    return _WS_RUN_RE.sub("", text)


def _parse_number(text):
    """数值解析文法（契约 §3.3）：百分数 → 带分数 → 分数 → 小数，全文锚定。

    解析失败（含分母 0、nan/inf、unicode 数字、非数值文本）返回 None。
    百分数剥 % 后按后三条解析并 ÷100；带分数符号取整数部、作用于整体。
    """
    body = text.strip()
    divisor = 1.0
    if body.endswith("%"):
        body = body[:-1].strip()
        divisor = 100.0
    if not body:
        return None
    mixed = _MIXED_NUMBER_RE.fullmatch(body)
    if mixed is not None:
        sign = -1.0 if mixed.group(1) == "-" else 1.0
        whole = float(mixed.group(2))
        numerator = float(mixed.group(3))
        denominator = float(mixed.group(4))
        if denominator == 0:
            return None
        return sign * (whole + numerator / denominator) / divisor
    fraction = _FRACTION_RE.fullmatch(body)
    if fraction is not None:
        sign = -1.0 if fraction.group(1) == "-" else 1.0
        numerator = float(fraction.group(2))
        denominator = float(fraction.group(3))
        if denominator == 0:
            return None
        return sign * (numerator / denominator) / divisor
    if _DECIMAL_RE.fullmatch(body) is not None:
        return float(body) / divisor
    return None


def _is_prefix_char(ch):
    """赋值前缀可用字符：ASCII 字母 / 希腊 U+0370–03FF / ∠ / 下标数字 / ¹²³ / 撇号。"""
    return (
        "a" <= ch <= "z"
        or "A" <= ch <= "Z"
        or "\u0370" <= ch <= "\u03FF"
        or ch == "\u2220"
        or "\u2080" <= ch <= "\u2089"
        or ch in "\u00b9\u00b2\u00b3"
        or ch in "'\u2032"
    )


def _strip_assignment_prefix(component):
    """R4 分量级前处理：首个 = 之前由前缀字符组成且总长 <=6、= 后至少 1 字符则剥去。

    x=5→5、x₁=7→7、AB=1→1、a'b=1→1；abcdefg=1（>6）不剥、x=（无后继）不剥、
    x+y=1（含 +）不剥；∠2=45°（前缀含 ASCII 数字）不剥。
    """
    eq = component.find("=")
    if eq < 0 or eq > 6 or eq + 1 >= len(component):
        return component
    for ch in component[:eq]:
        if not _is_prefix_char(ch):
            return component
    return component[eq + 1 :]


def _split_unit(component):
    """R3 单位门：后缀宽度 4→1 最长优先命中 UNIT_ALIASES。

    命中且剩余部 strip 非空 → (剩余部, 规范单位)；纯单位词 / 无命中 → (原文, None)。
    """
    for width in range(_MAX_UNIT_LEN, 0, -1):
        if len(component) < width:
            continue
        canonical = UNIT_ALIASES.get(component[-width:])
        if canonical is None:
            continue
        body = component[:-width].strip()
        if body:
            return (body, canonical)
        return (component, None)
    return (component, None)


def _component_match(left, right):
    """R3 单分量比对（输入均为已归一化并剥前缀的文本）：单位门 → 数值等价 → 字面相等。"""
    left_body, left_unit = _split_unit(left)
    right_body, right_unit = _split_unit(right)
    if left_unit != right_unit:
        return False
    left_value = _parse_number(left_body)
    right_value = _parse_number(right_body)
    if left_value is not None and right_value is not None:
        return abs(left_value - right_value) <= COMPARISON_TOLERANCE * max(
            1.0, abs(left_value), abs(right_value)
        )
    return _squash(left_body) == _squash(right_body)


def _split_components(raw):
    """R4：把原始文本按全角分隔符 或|和|、|；|，拆分（ASCII 逗号不拆）。

    全部分量的极端输入（如「或或或」）防御性回退到原串作单分量。
    """
    parts = _SEPARATOR_RE.split(raw)
    if parts and all(part == "" for part in parts):
        return [raw]
    return parts


def _components_match(key_raw, proposed_raw):
    """R4 多答案集合等值：分量数相等且 key 侧每分量 first-fit 配对成功。"""
    key_parts = _split_components(key_raw)
    proposed_parts = _split_components(proposed_raw)
    if len(key_parts) != len(proposed_parts):
        return False
    key_norm = [_strip_assignment_prefix(normalize_answer(part)) for part in key_parts]
    proposed_norm = [
        _strip_assignment_prefix(normalize_answer(part)) for part in proposed_parts
    ]
    consumed = [False] * len(proposed_norm)
    for left in key_norm:
        for index, right in enumerate(proposed_norm):
            if not consumed[index] and _component_match(left, right):
                consumed[index] = True
                break
        else:
            return False
    return True


def _resolve_option(target, labels, texts):
    """R2 resolve：两趟全局扫描——标签趟（直接 ==，最小下标）优先于全文趟（_key，最小下标）。"""
    for index, label in enumerate(labels):
        if target == label:
            return index
    keyed = _squash(target)
    for index, text in enumerate(texts):
        if keyed == _squash(text):
            return index
    return None


def _match_choice(key_answer, proposed, options):
    """R2 choice 等值判定；标答不可解析 → False（不抛错）。"""
    texts = [normalize_answer(option) for option in options]
    labels = [text.split(".", 1)[0].strip() for text in texts]
    correct = _resolve_option(normalize_answer(key_answer), labels, texts)
    given = _resolve_option(normalize_answer(proposed), labels, texts)
    return correct is not None and correct == given


def answers_match(key_answer, proposed, item_type="fill", options=None) -> bool:
    """verification 级标答-提案等值判定（契约 §3.3）。

    校验次序绑定：key_answer 非 str → proposed 非 str → item_type 非法 →
    choice 时 options 非 list 或 len<2，均抛 DualVerifyError。
    choice 走 R2；fill/solve 依序 R1 → R4 → R5（options 忽略、不校验）。
    """
    if not isinstance(key_answer, str):
        raise DualVerifyError("key_answer 必须为 str")
    if not isinstance(proposed, str):
        raise DualVerifyError("proposed 必须为 str")
    if item_type not in _ITEM_TYPES:
        raise DualVerifyError("item_type 必须为 choice/fill/solve 之一")
    if item_type == "choice":
        if not isinstance(options, list) or len(options) < 2:
            raise DualVerifyError("choice 题型要求 options 为含 >=2 元素的 list")
        return _match_choice(key_answer, proposed, options)
    normalized_key = normalize_answer(key_answer)
    normalized_proposed = normalize_answer(proposed)
    if normalized_key == normalized_proposed:  # R1 全串归一化等值
        return True
    if _components_match(key_answer, proposed):  # R4 多答案集合等值
        return True
    return _squash(normalized_key) == _squash(normalized_proposed)  # R5 字面兜底


def _valid_id(value):
    """id/agent id 校验：非 str、带首尾空白、空 → False。"""
    return isinstance(value, str) and value == value.strip() and bool(value.strip())


@dataclass(frozen=True)
class DualVerifyReport:
    """全库裁决报告（frozen dataclass，字段全部 tuple 化，顺序 = items 输入原序）。"""

    item_ids: tuple
    verdicts: tuple
    agreed_item_ids: tuple
    disputed_item_ids: tuple
    incomplete_item_ids: tuple
    records: tuple

    def counts(self) -> dict:
        """三键恒在（值为零也保留）；每次调用返回新 dict。"""
        tally = {
            VERDICT_AGREE: 0,
            VERDICT_DISAGREE: 0,
            VERDICT_INCOMPLETE: 0,
        }
        for _item_id, verdict in self.verdicts:
            tally[verdict] += 1
        return tally


def verify_item(item, agent_answers) -> dict:
    """单题双代理三值裁决（契约 §3.4）。

    题目侧校验先于一切裁决；入参侧先 sorted(agent_answers)（混合键 TypeError）
    再逐个校验 id（先于 no_answer 判定）。返回恰含 item_id / verdict / statuses
    三键的新 dict；statuses 为按 agent id 码点升序的 tuple of tuple。
    """
    if not isinstance(item, dict):
        raise DualVerifyError("item 必须为 dict")
    item_id = item.get("id")
    if not _valid_id(item_id):
        raise DualVerifyError("item['id'] 必须为无首尾空白且非空的 str")
    answer = item.get("answer")
    if not isinstance(answer, str) or not answer.strip():
        raise DualVerifyError("item['answer'] 必须为 strip 后非空的 str")
    item_type = item.get("item_type")
    if item_type not in _ITEM_TYPES:
        raise DualVerifyError("item['item_type'] 必须为 choice/fill/solve 之一")
    options = item.get("options")
    if item_type == "choice" and (not isinstance(options, list) or len(options) < 2):
        raise DualVerifyError("choice 题型要求 item['options'] 为含 >=2 元素的 list")
    if not isinstance(agent_answers, dict):
        raise DualVerifyError("agent_answers 必须为 dict")
    agent_ids = sorted(agent_answers)
    for agent_id in agent_ids:
        if not _valid_id(agent_id):
            raise DualVerifyError("agent id 必须为无首尾空白且非空的 str")

    statuses = []
    n_match = 0
    n_mismatch = 0
    for agent_id in agent_ids:
        raw = agent_answers[agent_id]
        if not isinstance(raw, str) or raw.strip() == "":
            statuses.append((agent_id, _ST_NO_ANSWER))  # 容忍：非 str / 空白 → 缺席
            continue
        if answers_match(answer, raw, item_type, options):
            statuses.append((agent_id, _ST_MATCH))
            n_match += 1
        else:
            statuses.append((agent_id, _ST_MISMATCH))
            n_mismatch += 1

    if n_mismatch >= 1:
        verdict = VERDICT_DISAGREE  # 任一 mismatch 压倒 match 多数
    elif n_match >= 2:
        verdict = VERDICT_AGREE
    else:
        verdict = VERDICT_INCOMPLETE
    return {"item_id": item_id, "verdict": verdict, "statuses": tuple(statuses)}


def make_record(agent_ids) -> dict:
    """由代理 id 的任意可迭代构造 v2 合法记录（契约 §3.5）。

    逐个清洗（非 str / 带首尾空白 / 空 → DualVerifyError），去重、码点升序，
    <2 个不同 id → DualVerifyError。
    """
    distinct = []
    for agent_id in agent_ids:
        if not _valid_id(agent_id):
            raise DualVerifyError("agent id 必须为无首尾空白且非空的 str")
        if agent_id not in distinct:
            distinct.append(agent_id)
    if len(distinct) < 2:
        raise DualVerifyError("verification 记录至少需要 2 个不同 agent id")
    distinct.sort()
    return {"agents": distinct, "answers_agree": True}


def verification_record(verify_result):
    """verify_item 结果 → v2 记录或 None（契约 §3.5）。

    入参非 dict / 缺 verdict 键 → DualVerifyError；verdict != agree → None；
    agree → make_record(所有 match 状态的 agent id)（<2 个 match 时经
    make_record 下限触发 DualVerifyError）。
    """
    if not isinstance(verify_result, dict):
        raise DualVerifyError("verify_result 必须为 dict")
    if "verdict" not in verify_result:
        raise DualVerifyError("verify_result 缺少 'verdict' 键")
    if verify_result["verdict"] != VERDICT_AGREE:
        return None  # 分歧 / 诚实缺口不回填
    statuses = verify_result.get("statuses") or ()
    matched = [agent_id for agent_id, status in statuses if status == _ST_MATCH]
    return make_record(matched)


def _validated_record_agents(record):
    """backfill_item 的 record 校验（record 非 None 时）。"""
    if not isinstance(record, dict):
        raise DualVerifyError("record 必须为 dict")
    agents = record.get("agents")
    if not isinstance(agents, list) or len(agents) < 2:
        raise DualVerifyError("record['agents'] 必须为含 >=2 元素的 list")
    seen = []
    for agent_id in agents:
        if not _valid_id(agent_id):
            raise DualVerifyError("record['agents'] 元素必须为无首尾空白且非空的 str")
        if agent_id in seen:
            raise DualVerifyError("record['agents'] 存在重复 agent id")
        seen.append(agent_id)
    if record.get("answers_agree") is not True:
        raise DualVerifyError("record['answers_agree'] 必须恰为 True")
    return agents


def backfill_item(item, record) -> dict:
    """纯回填（契约 §3.5）：入参不被修改。

    record 为 None → 返回 dict(item) 副本（无回填）；否则校验 record 后返回
    out = dict(item)；out["verification"] = {"agents": [...], "answers_agree": True}
    （原件无该键时追加在末尾；已有该键时按 dict 赋值语义就地覆盖）。
    """
    if not isinstance(item, dict):
        raise DualVerifyError("item 必须为 dict")
    if record is None:
        return dict(item)
    agents = _validated_record_agents(record)
    out = dict(item)
    out["verification"] = {"agents": list(agents), "answers_agree": True}
    return out


def verify_bank(items, answers_by_item) -> DualVerifyReport:
    """全库逐题裁决（契约 §3.6）：按 items 输入原序，缺条目按空 dict。"""
    if not isinstance(answers_by_item, dict):
        raise DualVerifyError("answers_by_item 必须为 dict")
    item_ids = []
    verdicts = []
    agreed = []
    disputed = []
    incomplete = []
    records = []
    for item in items:
        # item["id"] 在 verify_item 校验前求值（缺 'id' 键 → KeyError，契约 §6 参考裁定）。
        result = verify_item(item, answers_by_item.get(item["id"], {}))
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


def arbitration_rows(items, answers_by_item) -> tuple:
    """人工仲裁队列行（契约 §3.7）：仅 mismatch 成行，四键 dict，原序 + id 升序。"""
    if not isinstance(answers_by_item, dict):
        raise DualVerifyError("answers_by_item 必须为 dict")
    rows = []
    for item in items:
        # 同 verify_bank：item["id"] 先求值（缺 'id' 键 → KeyError）。
        agent_answers = answers_by_item.get(item["id"], {})
        result = verify_item(item, agent_answers)
        for agent_id, status in result["statuses"]:
            if status == _ST_MISMATCH:
                rows.append(
                    {
                        "item_id": result["item_id"],
                        "key_answer": item["answer"],  # 原样，不做归一化
                        "agent": agent_id,
                        "proposed": agent_answers[agent_id],  # 原始提案值，原样
                    }
                )
    return tuple(rows)
