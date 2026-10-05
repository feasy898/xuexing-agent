"""OMR 答题卡对接规范的确定性内核（regen/wave3 盲重写）。

唯一权威契约：specs/frozen/omr_sheet.spec.md（定稿 v1）。三段职责：

- ``build_answer_sheet``：Paper + bank -> answer-sheet.json 内容侧文档
  （卷面题号 1..N 贯穿全卷 -> ``q<题号>`` 列名 -> 气泡值表 -> 选项内容；
  choice 题机读（omr），fill/solve 题 manual 不出涂点）。
- ``parse_omr_results``：OMRChecker Results CSV 文本 -> 行 dict 列表。
- ``to_responses``：一张卡（行 dict）按 answer-sheet 映射还原为 ``Response`` 列表。

行为契约：映射闭式、学生面安全（不含答案/解析/题干）、漂移硬失败（一律
``OMRError``，绝不静默错位判分）、纯函数（无 IO、无随机、无时钟）。

依赖：标准库 ``csv``/``io``/``re`` + ``xuexing.types.Response``（仅此一个类型，
绝对导入；不 import 其他任何 xuexing 模块，跨模块一致性由契约测试在测试侧锁定）。
"""

import csv
import io
import re

from xuexing.types import Response

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


# ------------------------------------------------------------------ 常量

OMR_VERSION = "1"
FIELD_PREFIX = "q"
MODE_OMR = "omr"
MODE_MANUAL = "manual"
BLOCK_DIRECTION = "horizontal"
MAX_BUBBLES = 26
RESULTS_FILE_ID_COLUMN = "file_id"

# 内部值域（非公开，行为面一部分）：合法题型恰为此三种；未知题型在映射期即报错。
_LEGAL_ITEM_TYPES = ("choice", "fill", "solve")

_BOM = "\ufeff"
_POSITIONAL_LABELS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

# parse_option 显式标签形态：行首单个 ASCII 字母 + 分隔符（. ． 、 ) ）之一）
# + 可选 [ \t]* + 正文至串尾（re.S 允许正文含换行）。
_OPTION_LABEL_RE = re.compile(r"^([A-Za-z])[.．、)）][ \t]*(.*)$", re.S)

# natural_sort_key：OMRChecker custom_sort_output_columns 同款。
_NATURAL_SORT_RE = re.compile(r"([^\d]+)(\d*)")


class OMRError(ValueError):
    """本模块唯一异常类型；所有校验失败均抛它。"""


# ------------------------------------------------------------------ 内部工具

def _is_strict_int(value) -> bool:
    """int 且非 bool（bool 是 int 子类，一律按非 int 处理）。"""
    return isinstance(value, int) and not isinstance(value, bool)


def _build_bank_index(bank) -> dict:
    """bank 索引：id -> 题目对象；表面校验 + 重复 id 硬失败。"""
    items_getter = getattr(bank, "items", None)
    if not callable(items_getter):
        raise OMRError("bank 缺少可调用的 items()")
    raw_items = items_getter()
    try:
        iterator = iter(raw_items)
    except TypeError:
        raise OMRError("bank.items() 返回值不可迭代")
    index = {}
    for item in iterator:
        item_id = getattr(item, "id", None)
        if not isinstance(item_id, str) or not item_id:
            raise OMRError("bank 题 id 必须是非空 str")
        if item_id in index:
            raise OMRError("bank 题 id 重复: %r" % (item_id,))
        index[item_id] = item
    return index


def _choice_option_gate(item):
    """§3.6 choice 选项门。

    返回 ``(parsed, raw_options)``：``parsed`` 为按位次解出的
    ``[(标签, strip 后正文), ...]``；``raw_options`` 为 bank 选项原文表
    （供 to_responses 单涂支取原文全串作 learner_answer）。
    """
    options = getattr(item, "options", None)
    if not isinstance(options, (list, tuple)):
        raise OMRError("choice 题 options 必须是 list/tuple")
    if len(options) < 2:
        raise OMRError("choice 题 options 至少 2 项")
    parsed = []
    seen_labels = set()
    for position, raw in enumerate(options):
        label, text = parse_option(raw, position)
        if label in seen_labels:
            raise OMRError("选项标签重复（含回退撞显式）: %r" % (label,))
        seen_labels.add(label)
        parsed.append((label, text))
    if len(parsed) > MAX_BUBBLES:
        raise OMRError("选项数超过 MAX_BUBBLES=%d" % MAX_BUBBLES)
    return parsed, list(options)


def _resolve_answer_index(item, parsed) -> int:
    """答案解析（仅单涂支触发）：先标签趟、再正文趟，均不中即 OMRError。"""
    answer = getattr(item, "answer", None)
    if not isinstance(answer, str):
        raise OMRError("item.answer 必须是 str")
    target = answer.strip().upper()
    for index, (label, _text) in enumerate(parsed):
        if label == target:
            return index
    for index, (_label, text) in enumerate(parsed):
        if text.strip().upper() == target:
            return index
    raise OMRError("item.answer 无法按标签或正文解析: %r" % (answer,))


def _close_field_block(blocks, numbers, bubbles) -> None:
    """封段：段名 block<K> 按已封段数连续编号（封段时确定）；气泡表取段首题副本。"""
    blocks.append({
        "name": "block%d" % (len(blocks) + 1),
        "field_labels": parse_field_ranges(numbers),
        "bubble_values": list(bubbles),
        "direction": BLOCK_DIRECTION,
    })


# ------------------------------------------------------------------ 公开 API

def parse_option(option_text: str, position: int) -> "tuple[str, str]":
    """选项字符串 -> (标签, 选项正文)。

    先 strip；显式标签（单个 ASCII 字母 + ``.`` ``．`` ``、`` ``)`` ``）`` 之一
    + 可选空白 + 正文）优先，标签归一大写、正文 strip（可为空串）；否则按位次
    回退 A-Z，整串作正文。
    """
    if not isinstance(option_text, str):
        raise OMRError("option_text 必须是 str")
    if not _is_strict_int(position):
        raise OMRError("position 必须是 int（不接受 bool/float）")
    if position < 0 or position > MAX_BUBBLES - 1:
        raise OMRError("position 必须在 [0, %d]" % (MAX_BUBBLES - 1))
    stripped = option_text.strip()
    if not stripped:
        raise OMRError("option_text strip 后为空")
    match = _OPTION_LABEL_RE.match(stripped)
    if match is not None:
        return match.group(1).upper(), match.group(2).strip()
    return _POSITIONAL_LABELS[position], stripped


def field_label(number: int) -> str:
    """卷面题号 -> OMR 列名 ``FIELD_PREFIX + str(number)``。"""
    if not _is_strict_int(number) or number < 1:
        raise OMRError("number 必须是 >= 1 的 int（不接受 bool/float/str/None）")
    return FIELD_PREFIX + str(number)


def parse_field_ranges(numbers) -> "list[str]":
    """题号集合 -> 最短 OMRChecker fieldLabels 字段串列表。

    输入去重升序；连续段 a..b（a < b）输出 "qa..b"（含两端端点），孤立号输出
    "qa"；空列表容忍返回 []。
    """
    if not isinstance(numbers, (list, tuple)):
        raise OMRError("numbers 必须是 list/tuple")
    unique = set()
    for value in numbers:
        if not _is_strict_int(value) or value < 1:
            raise OMRError("题号必须是 >= 1 的 int（不接受 bool）")
        unique.add(value)
    ordered = sorted(unique)
    ranges = []
    i = 0
    while i < len(ordered):
        j = i
        while j + 1 < len(ordered) and ordered[j + 1] == ordered[j] + 1:
            j += 1
        start, end = ordered[i], ordered[j]
        if start < end:
            ranges.append(FIELD_PREFIX + str(start) + ".." + str(end))
        else:
            ranges.append(FIELD_PREFIX + str(start))
        i = j + 1
    return ranges


def natural_sort_key(label) -> list:
    r"""列名 -> 自然排序键 [前缀: str, 数字: int]。

    取 ``([^\d]+)(\d*)`` findall 首个匹配组；无数字尾缀数字位为 0；
    findall 为空（如 "123"，无任何非数字前缀）时按参考裁定返回 ["", 0]。
    """
    if not isinstance(label, str) or not label:
        raise OMRError("label 必须是非空 str")
    matches = _NATURAL_SORT_RE.findall(label)
    if not matches:
        return ["", 0]
    prefix, digits = matches[0]
    return [prefix, int(digits) if digits else 0]


def build_answer_sheet(paper, bank) -> dict:
    """Paper + bank -> answer-sheet.json 内容侧文档（恰 9 键）。

    校验顺序冻结：V1 paper 表面 -> V2 bank 索引 -> V3 sections 规整化 ->
    V4 逐节逐题（题号 1..N 贯穿全卷）-> V5 空卷门 -> V6 列名切段。
    sections 为空时回退 paper.item_ids 作单一隐式节；sections 非空时不读取
    paper.item_ids。输出全部为新构造容器，与入参无别名；kp_name 校验后丢弃。
    """
    # V1 paper 表面
    paper_id = getattr(paper, "paper_id", None)
    title = getattr(paper, "title", None)
    if not isinstance(paper_id, str):
        raise OMRError("paper.paper_id 必须是 str（缺失亦拒）")
    if not isinstance(title, str):
        raise OMRError("paper.title 必须是 str（缺失亦拒）")
    sections = getattr(paper, "sections", None)
    if not isinstance(sections, (list, tuple)):
        raise OMRError("paper.sections 必须是 list/tuple（缺失属性亦拒）")

    # V2 bank 索引
    bank_index = _build_bank_index(bank)

    # V3 sections 规整化（kp_name 校验后即丢弃，不出现在输出）
    section_id_lists = []
    if len(sections) == 0:
        fallback_ids = getattr(paper, "item_ids", None)
        if not isinstance(fallback_ids, (list, tuple)):
            raise OMRError("sections 为空时 paper.item_ids 必须是 list/tuple")
        for item_id in fallback_ids:
            if not isinstance(item_id, str) or not item_id:
                raise OMRError("卷面题 id 必须是非空 str")
        section_id_lists.append(list(fallback_ids))
    else:
        for section in sections:
            if not isinstance(section, dict):
                raise OMRError("section 条目必须是 dict")
            item_ids = section.get("item_ids")
            if not isinstance(item_ids, (list, tuple)):
                raise OMRError("section.item_ids 必须是 list/tuple")
            for item_id in item_ids:
                if not isinstance(item_id, str) or not item_id:
                    raise OMRError("卷面题 id 必须是非空 str")
            if "kp_name" in section and not isinstance(section["kp_name"], str):
                raise OMRError("section.kp_name 若存在必须是 str")
            section_id_lists.append(list(item_ids))

    # V4 逐节逐题（卷面顺序展开；跨节题号连续）
    questions = []
    question_sections = []  # 与 questions 平行：每题所属节序号
    omr_count = 0
    manual_count = 0
    for section_index, item_ids in enumerate(section_id_lists):
        for item_id in item_ids:
            item = bank_index.get(item_id)
            if item is None:
                raise OMRError("未知 item id: %r" % (item_id,))
            number = len(questions) + 1
            item_type = getattr(item, "item_type", None)
            if item_type == "choice":
                parsed, _raw_options = _choice_option_gate(item)
                questions.append({
                    "number": number,
                    "item_id": item_id,
                    "mode": MODE_OMR,
                    "field_label": field_label(number),
                    "bubble_values": [label for label, _text in parsed],
                    "options": [
                        {"label": label, "text": text}
                        for label, text in parsed
                    ],
                })
                omr_count += 1
            elif item_type in _LEGAL_ITEM_TYPES:  # fill / solve
                questions.append({
                    "number": number,
                    "item_id": item_id,
                    "mode": MODE_MANUAL,
                    "field_label": None,
                    "bubble_values": [],
                    "options": [],  # 题目 options 即便有值也忽略
                })
                manual_count += 1
            else:
                raise OMRError("未知 item_type: %r" % (item_type,))
            question_sections.append(section_index)

    # V5 空卷门
    if not questions:
        raise OMRError("空卷：一题都没有")

    # V6 outputColumns + fieldBlocks 切段
    omr_labels = [q["field_label"] for q in questions if q["mode"] == MODE_OMR]
    output_columns = sorted(omr_labels, key=natural_sort_key)

    field_blocks = []
    current_section = None
    current_bubbles = None  # 段首题气泡表副本
    current_numbers = []  # 段内题号
    for question, section_index in zip(questions, question_sections):
        if question["mode"] != MODE_OMR:
            # 遇 manual 题断段（手工题只占题号不出列）
            if current_numbers:
                _close_field_block(field_blocks, current_numbers, current_bubbles)
                current_numbers = []
                current_bubbles = None
                current_section = None
            continue
        # 延续条件：同节 + 气泡表相同 + 连续 omr 题；跨节/气泡表不同均断段
        if (current_numbers and current_section == section_index
                and current_bubbles == question["bubble_values"]):
            current_numbers.append(question["number"])
        else:
            if current_numbers:
                _close_field_block(field_blocks, current_numbers, current_bubbles)
            current_section = section_index
            current_bubbles = list(question["bubble_values"])
            current_numbers = [question["number"]]
    if current_numbers:
        _close_field_block(field_blocks, current_numbers, current_bubbles)

    return {
        "format_version": OMR_VERSION,
        "paper_id": paper_id,
        "title": title,
        "question_count": len(questions),
        "omr_count": omr_count,
        "manual_count": manual_count,
        "questions": questions,
        "output_columns": output_columns,
        "field_blocks": field_blocks,
    }


def parse_omr_results(csv_text: str) -> "list[dict]":
    """OMRChecker Results CSV 文本 -> 行 dict 列表。

    剥除首个字符处的单个 BOM；csv 默认方言解析；空行（产出空 list 的行）跳过；
    首个非空行为表头（每格非空 str、列名互异、必含 file_id）；数据行宽必须等于
    表头宽，file_id 单元格 strip 后非空。每行产出
    ``{"file_id": 原文, "values": {除 file_id 外每列: 原文}}``；score 照录字符串；
    不排序、不去重、不聚合、不做数值解析；表头之后无数据行 -> []。
    """
    if not isinstance(csv_text, str):
        raise OMRError("csv_text 必须是 str")
    if csv_text[:1] == _BOM:
        csv_text = csv_text[1:]

    rows = []
    for row in csv.reader(io.StringIO(csv_text)):
        if not row:  # 空行（csv.reader 产出空 list）跳过
            continue
        rows.append(row)

    if not rows:
        raise OMRError("无表头：空文本或仅空行")

    header = rows[0]
    for cell in header:
        if not isinstance(cell, str) or cell == "":
            raise OMRError("表头存在空单元格")
    if len(set(header)) != len(header):
        raise OMRError("表头列名重复")
    if RESULTS_FILE_ID_COLUMN not in header:
        raise OMRError("表头缺少 %s 列" % RESULTS_FILE_ID_COLUMN)
    file_id_index = header.index(RESULTS_FILE_ID_COLUMN)

    parsed_rows = []
    for row in rows[1:]:
        if len(row) != len(header):
            raise OMRError("数据行宽度（%d）与表头列数（%d）不一致"
                           % (len(row), len(header)))
        file_id_cell = row[file_id_index]
        if not isinstance(file_id_cell, str) or not file_id_cell.strip():
            raise OMRError("file_id 单元格 strip 后为空")
        values = {}
        for column_index, column_name in enumerate(header):
            if column_index == file_id_index:
                continue
            values[column_name] = row[column_index]
        parsed_rows.append({"file_id": file_id_cell, "values": values})
    return parsed_rows


def to_responses(row, sheet, bank) -> "list[Response]":
    """一张卡的 OMR 涂点 -> Response 列表（manual 题跳过，response_ms 恒 None）。

    校验顺序冻结：V1 sheet 表面（dict / format_version=="1" / questions 为
    list/tuple）-> V2 row 表面（values 为 str->str dict）-> V3 bank 索引 ->
    V4 逐题还原（number/重复、item_id、mode、field_label/重复、bank 在位、
    题型 choice、选项门、气泡表逐项相等）-> 涂点三路
    （未涂=判错不伪造、单涂=原文全串+两趟答案解析、多涂=恒错留大写拼接证）。
    """
    # V1 sheet 表面
    if not isinstance(sheet, dict):
        raise OMRError("sheet 必须是 dict")
    if sheet.get("format_version") != OMR_VERSION:
        raise OMRError("sheet format_version 必须为 %r，不做自动迁移"
                       % (OMR_VERSION,))
    questions = sheet.get("questions")
    if not isinstance(questions, (list, tuple)):
        raise OMRError("sheet.questions 必须是 list/tuple")

    # V2 row 表面（额外列原样容忍，还原不使用；row 其余键忽略）
    if not isinstance(row, dict):
        raise OMRError("row 必须是 dict")
    values = row.get("values")
    if not isinstance(values, dict):
        raise OMRError("row['values'] 必须是 dict")
    for key, cell in values.items():
        if not isinstance(key, str) or not isinstance(cell, str):
            raise OMRError("row['values'] 的键与值都必须是 str")

    # V3 bank 索引
    bank_index = _build_bank_index(bank)

    # V4 逐题还原（仅 sheet["questions"] 顺序）
    responses = []
    seen_numbers = set()
    seen_labels = set()
    for question in questions:
        if not isinstance(question, dict):
            raise OMRError("question 必须是 dict")
        number = question.get("number")
        if not _is_strict_int(number) or number < 1:
            raise OMRError("question.number 必须是 >= 1 的 int（禁 bool）")
        if number in seen_numbers:
            raise OMRError("question.number 重复: %r" % (number,))
        seen_numbers.add(number)
        item_id = question.get("item_id")
        if not isinstance(item_id, str) or not item_id:
            raise OMRError("question.item_id 必须是非空 str")
        mode = question.get("mode")
        if mode == MODE_MANUAL:
            continue  # manual 题不产 Response
        if mode != MODE_OMR:
            raise OMRError("未知 mode: %r" % (mode,))
        column_name = question.get("field_label")
        if not isinstance(column_name, str) or not column_name:
            raise OMRError("omr 题 field_label 必须是非空 str")
        if column_name in seen_labels:
            raise OMRError("omr 题 field_label 重复: %r" % (column_name,))
        seen_labels.add(column_name)

        item = bank_index.get(item_id)
        if item is None:
            raise OMRError("sheet/bank 漂移：题 %r 不在 bank" % (item_id,))
        if getattr(item, "item_type", None) != "choice":
            raise OMRError("sheet/bank 漂移：题 %r 在 bank 中非 choice"
                           % (item_id,))
        parsed, raw_options = _choice_option_gate(item)
        labels = [label for label, _text in parsed]
        bubble_values = question.get("bubble_values")
        if (not isinstance(bubble_values, (list, tuple))
                or len(bubble_values) != len(labels)
                or any(actual != expected
                       for actual, expected in zip(bubble_values, labels))):
            raise OMRError("sheet/bank 漂移：气泡表与 bank 选项标签表不一致")

        # 涂点三路
        if column_name not in values:
            raise OMRError("缺少 OMR 列: %r" % (column_name,))
        cell = values[column_name]
        if not isinstance(cell, str):
            raise OMRError("OMR 单元格非 str: %r" % (column_name,))
        normalized = cell.strip().upper()
        for character in normalized:
            if character not in labels:
                raise OMRError("未知涂点字符 %r（列 %r）"
                               % (character, column_name))

        if normalized == "":
            # 未涂：无作答证据，判错但不伪造内容
            responses.append(Response(item_id=item_id, correct=False,
                                      learner_answer=None, response_ms=None))
        elif len(normalized) == 1:
            # 单涂：learner_answer 为 bank options 原文全串；答案按标签趟/正文趟解析
            marked_index = labels.index(normalized)
            answer_index = _resolve_answer_index(item, parsed)
            responses.append(Response(
                item_id=item_id,
                correct=(marked_index == answer_index),
                learner_answer=raw_options[marked_index],
                response_ms=None,
            ))
        else:
            # 多涂：恒错，不猜；大写拼接串留证据
            responses.append(Response(item_id=item_id, correct=False,
                                      learner_answer=normalized,
                                      response_ms=None))
    return responses
