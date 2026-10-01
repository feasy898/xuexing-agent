"""omr_sheet —— OMR 光学标记识别答题卡对接的确定性内核。

契约：specs/frozen/omr_sheet.spec.md（定稿 v1）。本文件是按该契约的独立盲写实现。

三段职责：
- ``build_answer_sheet(paper, bank)``：Paper + bank → answer-sheet.json 内容侧文档
  （卷面题号 1..N → OMR 列名 ``q<题号>`` → 气泡值表 → 选项内容）。像素几何不在本模块。
- ``parse_omr_results(csv_text)``：OMRChecker Results CSV 文本 → 行 dict 列表。
- ``to_responses(row, sheet, bank)``：一张卡按 sheet 映射还原为 ``Response`` 列表。

行为契约：映射闭式、学生面安全（文档不含答案/题干/解析）、漂移硬失败（sheet/bank 任一
漂移一律 ``OMRError``，绝不静默错位判分）、纯函数（无 IO/无随机/无时钟）。

装载约束（契约 §2）：本文件以顶层模块名被 ``spec_from_file_location`` 装载并顶替
``sys.modules["xuexing.omr_sheet"]``，故禁止相对导入、禁止 ``from __future__ import
annotations``（注解直接写真实对象）。
"""

import csv
import io
import re

from xuexing.types import Response


OMR_VERSION = "1"
FIELD_PREFIX = "q"
MODE_OMR = "omr"
MODE_MANUAL = "manual"
BLOCK_DIRECTION = "horizontal"
MAX_BUBBLES = 26
RESULTS_FILE_ID_COLUMN = "file_id"

_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_ITEM_TYPES = ("choice", "fill", "solve")
_BOM = "\ufeff"
# 显式选项标签：单个 ASCII 字母 + 分隔符 + 可选 [ \t] + 正文至串尾（正文可含换行）
_OPTION_LABEL_RE = re.compile(r"([A-Za-z])[.．、)）][ \t]*(.*)\Z", re.S)
# OMRChecker custom_sort_output_columns 同款自然排序键
_NATURAL_RE = re.compile(r"([^\d]+)(\d*)")


class OMRError(ValueError):
    """本模块唯一异常类型：所有校验失败（契约 §6）均抛它。"""


__all__ = [
    "OMRError",
    "OMR_VERSION",
    "FIELD_PREFIX",
    "MODE_OMR",
    "MODE_MANUAL",
    "BLOCK_DIRECTION",
    "MAX_BUBBLES",
    "RESULTS_FILE_ID_COLUMN",
    "parse_option",
    "field_label",
    "parse_field_ranges",
    "natural_sort_key",
    "build_answer_sheet",
    "parse_omr_results",
    "to_responses",
]


# ---------------------------------------------------------------- 内部小工具


def _is_plain_int(value) -> bool:
    """int 且非 bool（``True``/``False`` 一律拒）。"""
    return isinstance(value, int) and not isinstance(value, bool)


def _is_nonempty_str(value) -> bool:
    return isinstance(value, str) and value != ""


def _field_range(start: int, end: int) -> str:
    """连续段字段串：孤立号 ``"q3"``、连续段 ``"q1..4"``（含两端端点）。"""
    if start == end:
        return FIELD_PREFIX + str(start)
    return FIELD_PREFIX + str(start) + ".." + str(end)


def _bank_index(bank) -> dict:
    """bank 表面：``items`` 可调用、返回值可迭代、题 id 非空 str 且不重复。"""
    items_attr = getattr(bank, "items", None)
    if not callable(items_attr):
        raise OMRError("bank.items 必须是可调用的 items()")
    try:
        pending = iter(items_attr())
    except TypeError as exc:
        raise OMRError("bank.items() 的返回值必须可迭代") from exc
    index: dict = {}
    for item in pending:
        item_id = getattr(item, "id", None)
        if not _is_nonempty_str(item_id):
            raise OMRError("bank 题目 id 必须是非空 str")
        if item_id in index:
            raise OMRError("bank 题目 id 重复: " + item_id)
        index[item_id] = item
    return index


def _choice_table(item) -> tuple:
    """choice 选项门 → ``(标签表, 正文表, 原文选项表)``；任一违反抛 ``OMRError``。"""
    options = getattr(item, "options", None)
    if not isinstance(options, (list, tuple)):
        raise OMRError("choice 题目 options 必须是 list/tuple")
    if len(options) < 2:
        raise OMRError("choice 题目 options 至少 2 项")
    if len(options) > MAX_BUBBLES:
        raise OMRError("choice 题目 options 超过 MAX_BUBBLES")
    labels: list = []
    texts: list = []
    for position, raw in enumerate(options):
        label, text = parse_option(raw, position)
        if label in labels:
            raise OMRError("choice 选项标签重复: " + label)
        labels.append(label)
        texts.append(text)
    return labels, texts, options


def _answer_index(item, labels: list, texts: list) -> int:
    """答案解析：先标签趟，后正文趟；两趟不中即题目坏，硬失败。"""
    answer = getattr(item, "answer", None)
    if not isinstance(answer, str):
        raise OMRError("item.answer 必须是 str")
    target = answer.strip().upper()
    for position, label in enumerate(labels):
        if label == target:
            return position
    for position, text in enumerate(texts):
        if text.strip().upper() == target:
            return position
    raise OMRError("item.answer 无法解析为选项: " + answer)


# ---------------------------------------------------------------- 公开 API


def parse_option(option_text, position) -> tuple[str, str]:
    """选项字符串 → ``(标签, 选项正文)``（与 paper_layout.parse_option 同闭式）。"""
    if not isinstance(option_text, str):
        raise OMRError("option_text 必须是 str")
    if not _is_plain_int(position):
        raise OMRError("position 必须是 int（bool/float 一律拒）")
    if position < 0 or position > MAX_BUBBLES - 1:
        raise OMRError("position 必须落在 [0, 25]")
    text = option_text.strip()
    if text == "":
        raise OMRError("option_text strip 后为空")
    matched = _OPTION_LABEL_RE.match(text)
    if matched is not None:
        return (matched.group(1).upper(), matched.group(2).strip())
    return (_ALPHABET[position], text)


def field_label(number) -> str:
    """卷面题号 → OMR 列名（``"q" + str(number)``）。"""
    if not _is_plain_int(number):
        raise OMRError("number 必须是 int（bool/float/str/None 一律拒）")
    if number < 1:
        raise OMRError("number 必须 >= 1")
    return FIELD_PREFIX + str(number)


def parse_field_ranges(numbers) -> list[str]:
    """题号集合 → 最短 OMRChecker fieldLabels 字段串列表（去重升序、连续段含端点）。"""
    if not isinstance(numbers, (list, tuple)):
        raise OMRError("numbers 必须是 list/tuple")
    for number in numbers:
        if not _is_plain_int(number):
            raise OMRError("numbers 元素必须是 int（bool 一律拒）")
        if number < 1:
            raise OMRError("numbers 元素必须 >= 1")
    if not numbers:
        return []
    ordered = sorted(set(numbers))
    ranges: list = []
    start = ordered[0]
    previous = ordered[0]
    for number in ordered[1:]:
        if number == previous + 1:
            previous = number
            continue
        ranges.append(_field_range(start, previous))
        start = number
        previous = number
    ranges.append(_field_range(start, previous))
    return ranges


def natural_sort_key(label) -> list:
    """列名 → 自然排序键 ``[前缀: str, 数字: int]``。"""
    if not isinstance(label, str) or label == "":
        raise OMRError("label 必须是非空 str")
    matches = _NATURAL_RE.findall(label)
    if not matches:
        return ["", 0]
    prefix, digits = matches[0]
    return [prefix, int(digits) if digits else 0]


def build_answer_sheet(paper, bank) -> dict:
    """Paper + bank → answer-sheet.json 内容侧文档（9 键，学生面无答案/题干）。"""
    # V1 paper 表面
    paper_id = getattr(paper, "paper_id", None)
    if not isinstance(paper_id, str):
        raise OMRError("paper.paper_id 必须是 str")
    title = getattr(paper, "title", None)
    if not isinstance(title, str):
        raise OMRError("paper.title 必须是 str")
    sections = getattr(paper, "sections", None)
    if not isinstance(sections, (list, tuple)):
        raise OMRError("paper.sections 必须是 list/tuple")

    # V2 bank 索引
    index = _bank_index(bank)

    # V3 sections 规整化（sections 空 → paper.item_ids 作单一隐式节）
    if len(sections) == 0:
        fallback_ids = getattr(paper, "item_ids", None)
        if not isinstance(fallback_ids, (list, tuple)):
            raise OMRError("sections 为空时 paper.item_ids 必须是 list/tuple")
        sec_list = [_validated_ids({"item_ids": fallback_ids})]
    else:
        sec_list = [_validated_ids(entry) for entry in sections]

    # V4 逐节逐题（卷面顺序展开，题号 1..N 贯穿全卷）
    questions: list = []
    question_sections: list = []
    for section_index, item_ids in enumerate(sec_list):
        for item_id in item_ids:
            item = index.get(item_id)
            if item is None:
                raise OMRError("卷面引用了 bank 中不存在的题号: " + item_id)
            item_type = getattr(item, "item_type", None)
            number = len(questions) + 1
            if item_type == "choice":
                labels, texts, _raw_options = _choice_table(item)
                questions.append(
                    {
                        "number": number,
                        "item_id": item_id,
                        "mode": MODE_OMR,
                        "field_label": FIELD_PREFIX + str(number),
                        "bubble_values": list(labels),
                        "options": [
                            {"label": label, "text": text}
                            for label, text in zip(labels, texts)
                        ],
                    }
                )
            elif item_type in _ITEM_TYPES:
                questions.append(
                    {
                        "number": number,
                        "item_id": item_id,
                        "mode": MODE_MANUAL,
                        "field_label": None,
                        "bubble_values": [],
                        "options": [],
                    }
                )
            else:
                raise OMRError("未知 item_type: " + repr(item_type))
            question_sections.append(section_index)

    # V5 空卷门
    if not questions:
        raise OMRError("空卷：一题都没有")

    # V6 outputColumns + fieldBlocks 切段
    omr_labels = [q["field_label"] for q in questions if q["mode"] == MODE_OMR]
    output_columns = sorted(omr_labels, key=natural_sort_key)
    field_blocks = _field_blocks(questions, question_sections)

    return {
        "format_version": OMR_VERSION,
        "paper_id": paper_id,
        "title": title,
        "question_count": len(questions),
        "omr_count": len(omr_labels),
        "manual_count": len(questions) - len(omr_labels),
        "questions": questions,
        "output_columns": output_columns,
        "field_blocks": field_blocks,
    }


def parse_omr_results(csv_text) -> list[dict]:
    """OMRChecker Results CSV 文本 → 行 dict 列表。"""
    if not isinstance(csv_text, str):
        raise OMRError("csv_text 必须是 str")
    text = csv_text
    if text.startswith(_BOM):
        text = text[1:]

    rows = [row for row in csv.reader(io.StringIO(text)) if row]
    if not rows:
        raise OMRError("CSV 无表头")

    header = rows[0]
    for name in header:
        if not _is_nonempty_str(name):
            raise OMRError("表头单元格必须非空")
    if len(set(header)) != len(header):
        raise OMRError("表头列名重复")
    if RESULTS_FILE_ID_COLUMN not in header:
        raise OMRError("表头缺 " + RESULTS_FILE_ID_COLUMN + " 列")
    file_index = header.index(RESULTS_FILE_ID_COLUMN)

    parsed: list = []
    for row in rows[1:]:
        if len(row) != len(header):
            raise OMRError("数据行宽必须等于表头宽")
        file_id = row[file_index]
        if not isinstance(file_id, str) or file_id.strip() == "":
            raise OMRError("file_id 单元格 strip 后必须非空")
        values: dict = {}
        for column_index, name in enumerate(header):
            if column_index == file_index:
                continue
            values[name] = row[column_index]
        parsed.append({"file_id": file_id, "values": values})
    return parsed


def to_responses(row, sheet, bank) -> list[Response]:
    """一张卡的 OMR 涂点 → ``Response`` 列表（未涂/单涂/多涂三路，manual 题跳过）。"""
    # V1 sheet 表面
    if not isinstance(sheet, dict):
        raise OMRError("sheet 必须是 dict")
    if sheet.get("format_version") != OMR_VERSION:
        raise OMRError("sheet.format_version 必须是 " + OMR_VERSION)
    questions = sheet.get("questions")
    if not isinstance(questions, (list, tuple)):
        raise OMRError("sheet.questions 必须是 list/tuple")

    # V2 row 表面
    if not isinstance(row, dict):
        raise OMRError("row 必须是 dict")
    values = row.get("values")
    if not isinstance(values, dict):
        raise OMRError("row.values 必须是 dict")
    for key, value in values.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise OMRError("row.values 键值都必须是 str")

    # V3 bank 索引
    index = _bank_index(bank)

    # V4 逐题还原
    responses: list = []
    seen_numbers: set = set()
    seen_labels: set = set()
    for question in questions:
        if not isinstance(question, dict):
            raise OMRError("sheet.questions 元素必须是 dict")
        number = question.get("number")
        if not _is_plain_int(number) or number < 1:
            raise OMRError("question.number 必须是 >= 1 的 int（bool 一律拒）")
        if number in seen_numbers:
            raise OMRError("question.number 重复: " + str(number))
        seen_numbers.add(number)
        item_id = question.get("item_id")
        if not _is_nonempty_str(item_id):
            raise OMRError("question.item_id 必须非空 str")
        mode = question.get("mode")
        if mode == MODE_MANUAL:
            continue
        if mode != MODE_OMR:
            raise OMRError("未知 question.mode: " + repr(mode))
        label = question.get("field_label")
        if not _is_nonempty_str(label):
            raise OMRError("omr 题 field_label 必须非空 str")
        if label in seen_labels:
            raise OMRError("omr 题 field_label 重复: " + label)
        seen_labels.add(label)
        item = index.get(item_id)
        if item is None:
            raise OMRError("sheet 题号不在 bank 中: " + item_id)
        if getattr(item, "item_type", None) != "choice":
            raise OMRError("sheet 标 omr 而 bank 题型非 choice: " + item_id)
        labels, texts, raw_options = _choice_table(item)
        declared = question.get("bubble_values")
        if not isinstance(declared, (list, tuple)) or len(declared) != len(labels):
            raise OMRError("question.bubble_values 与 bank 标签表长度不一致: " + item_id)
        for position, value in enumerate(declared):
            if value != labels[position]:
                raise OMRError("question.bubble_values 与 bank 标签表不一致: " + item_id)

        if label not in values:
            raise OMRError("Results 行缺少 OMR 列: " + label)
        cell = values[label]
        if not isinstance(cell, str):
            raise OMRError("OMR 单元格必须非 str: " + label)
        normalized = cell.strip().upper()
        for char in normalized:
            if char not in labels:
                raise OMRError("未知涂点字符: " + repr(char))

        if normalized == "":
            responses.append(
                Response(item_id=item_id, correct=False, learner_answer=None, response_ms=None)
            )
        elif len(normalized) == 1:
            marked_position = labels.index(normalized)
            answer_position = _answer_index(item, labels, texts)
            responses.append(
                Response(
                    item_id=item_id,
                    correct=marked_position == answer_position,
                    learner_answer=raw_options[marked_position],
                    response_ms=None,
                )
            )
        else:
            responses.append(
                Response(item_id=item_id, correct=False, learner_answer=normalized, response_ms=None)
            )
    return responses


# ---------------------------------------------------------------- 私有辅助


def _validated_ids(section) -> list:
    """section 条目规整化：dict + item_ids list/tuple + id 非空 str + kp_name 若存在为 str。"""
    if not isinstance(section, dict):
        raise OMRError("section 条目必须是 dict")
    item_ids = section.get("item_ids")
    if not isinstance(item_ids, (list, tuple)):
        raise OMRError("section.item_ids 必须是 list/tuple")
    if "kp_name" in section and not isinstance(section["kp_name"], str):
        raise OMRError("section.kp_name 必须是 str")
    for item_id in item_ids:
        if not _is_nonempty_str(item_id):
            raise OMRError("section.item_ids 元素必须非空 str")
    return list(item_ids)


def _field_blocks(questions: list, question_sections: list) -> list:
    """切段：同节 + 气泡表相同 + 连续 omr 题才延续；manual / 跨节 / 气泡表不同断段。"""
    blocks: list = []
    current_numbers: list = []
    current_bubbles: list = []
    current_section: object = None
    open_block = False
    for question, section_index in zip(questions, question_sections):
        if question["mode"] != MODE_OMR:
            open_block = False
            current_section = None
            continue
        if (
            open_block
            and section_index == current_section
            and question["bubble_values"] == current_bubbles
        ):
            current_numbers.append(question["number"])
        else:
            current_numbers = [question["number"]]
            current_bubbles = list(question["bubble_values"])
            blocks.append((current_numbers, current_bubbles))
            open_block = True
        current_section = section_index
    return [
        {
            "name": "block" + str(position),
            "field_labels": parse_field_ranges(numbers),
            "bubble_values": bubbles,
            "direction": BLOCK_DIRECTION,
        }
        for position, (numbers, bubbles) in enumerate(blocks, start=1)
    ]
