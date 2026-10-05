# omr_sheet 模块规格（冻结契约）

> 本文档是唯一权威契约。任何实现（参考实现或重生成实例）只要通过 tests/contract/ 全部测试
> 且满足本文全部条款，即为合格实现。实现算法自由，行为不允许偏离。
>
> **版本**：定稿 v1（从参考实现 `src/xuexing/omr_sheet.py` 与契约测试
> `tests/contract/test_omr_sheet_contract.py` 直接冻结）。
> 标注「〔测试裁定〕」的行为由契约测试直接断言；标注「〔参考裁定〕」的行为契约测试未
> 仲裁，按参考实现冻结并在当地注明。本文自包含：不引用仓库内其他规格文档；全部规则、
> 常量、管线顺序在本文内完整定义。
>
> 冻结基线：参考实现 + 契约测试全量实测于 2026-10-02，CPython 3.12.10 x64
> （`.venv/Scripts/python.exe -m pytest tests/contract/test_omr_sheet_contract.py -q`
> → **26 passed**）。

## 1. 目的

omr_sheet 是 OMR（光学标记识别答题卡）对接规范的确定性内核，对外三段职责：

- `build_answer_sheet`：Paper + bank → answer-sheet.json **内容侧**文档——卷面题号
  （1..N 贯穿全卷，与 paper_layout/mm_ingest 同一编号语义）→ 题目 id → OMR 列名
  （`q<题号>`）→ 气泡值表（选项标签 A–Z）→ 选项内容；choice 题机读涂卡（`omr` 模式），
  fill/solve 题不出涂点、标记 `manual` 模式交手工/OCR 录入。附 OMRChecker
  template.json 内容侧信息：`outputColumns`（自然排序）+ `fieldBlocks` 的
  `fieldLabels` 字段串 / `bubbleValues` / `direction`。**像素几何（origin/间距）
  不在本模块范围**。
- `parse_omr_results`：OMRChecker Results CSV 文本 → 行 dict 列表（表头
  `file_id, input_path, output_path, score, <列…>`；题目单元格 = 该题被涂气泡值的
  拼接串，未涂 = 空串，多涂按气泡序拼接如 `"AC"`）。
- `to_responses`：一张卡（行 dict）按 answer-sheet 映射还原为 `Response` 列表——
  未涂 → `learner_answer=None, correct=False`；单涂 → `learner_answer` = 该选项在
  bank `options` 中的**原文全串**（与 `grading.grade_choice` 对显式标签题/位置回退
  标签题都同判，契约测试跨模块锁定）；多涂 → `learner_answer` = 涂点拼接串且一律
  `correct=False`（不猜）；`manual` 题不产 `Response`。

行为契约：**映射闭式**（全部规则可手算复核）、**学生面安全**（文档不含答案/解析/题干）、
**漂移硬失败**（sheet/bank 任一漂移——未知题/题型变/气泡表不一致/缺列/未知涂点——
一律 `OMRError`，绝不静默错位判分）、**纯函数**（无 IO、无随机、无时钟，同输入同输出）。

## 2. 允许的依赖与装载约束

- Python 标准库（逐个列出）：`csv`、`io`、`re`
- `xuexing.types` —— **必须绝对导入**：`from xuexing.types import Response`；
  **只允许用到 `Response` 这一个类型**（构造返回列表用；`types.Paper` 等一律不得
  import——paper 是鸭子类型参数表面，见下）
- 禁止：其他 xuexing 模块（**无例外**——`parse_option` 与 `paper_layout.parse_option`
  同闭式、`to_responses` 与 `grading.grade_choice` 同判等跨模块一致性，由契约测试在
  **测试侧** import 对方模块断言，被测实现侧零 import）、第三方库、文件/网络 IO、
  全局可变状态
- 禁止：随机、系统时钟、环境读取（全模块无时间戳字段，`response_ms` 恒 `None`，无豁免）

鸭子类型注入表面（不 import 其定义模块，按成员调用）：

- `paper`：`paper_id: str` / `title: str` / `sections: list[dict]`（每个 dict 含
  `item_ids: list[str]` 必填、`kp_name: str` 可选、其余键忽略；`sections` 为空时回退
  `paper.item_ids: list[str]` 作单一隐式节）
- `bank`：`items() -> 题目可迭代`；题目对象只用到 `id` / `item_type` / `answer` /
  `options`

装载约束（实测 `tests/conftest.py:18,26-34` 注入门：`omr_sheet` 在 `MODULES` 列表中，
设置 `XX_IMPL_DIR` 后 `<impl_dir>/omr_sheet.py` 以顶层模块名 `_regen_omr_sheet` 经
`spec_from_file_location` 装载并顶替 `sys.modules["xuexing.omr_sheet"]`）：

- **禁止相对导入**（装载为顶层模块名，无父包）
- **禁止 `from __future__ import annotations`**：注解直接写真实对象
  （参考实现源码注释亦如此要求）

## 3. 公开 API

模块必须暴露以下 **15 个名字**（即参考实现 `__all__`；契约测试以
`from xuexing.omr_sheet import OMRError, OMR_VERSION, FIELD_PREFIX, MODE_OMR, MODE_MANUAL, BLOCK_DIRECTION, MAX_BUBBLES, RESULTS_FILE_ID_COLUMN, parse_option, field_label, parse_field_ranges, natural_sort_key, build_answer_sheet, parse_omr_results, to_responses`
导入）：

### 3.1 常量与异常（8 个名字）

| 名字 | 冻结值 | 语义 |
|---|---|---|
| `OMRError` | `ValueError` 直接子类 | 本模块**唯一**异常类型；所有校验失败均抛它（§6）〔测试裁定 `test_frozen_constants`〕 |
| `OMR_VERSION` | `"1"` | answer-sheet.json 的 schema 版本；`to_responses` 只接受该值 |
| `FIELD_PREFIX` | `"q"` | OMR 列名前缀：列名 = `"q" + str(卷面题号)` |
| `MODE_OMR` | `"omr"` | choice 题：机读涂卡 |
| `MODE_MANUAL` | `"manual"` | fill/solve 题：手工/OCR 录入，无涂点 |
| `BLOCK_DIRECTION` | `"horizontal"` | 一题一行气泡横排（OMRChecker QTYPE_MCQ* 同款） |
| `MAX_BUBBLES` | `26` | 气泡值 = 单个大写 ASCII 字母，A–Z 上限 |
| `RESULTS_FILE_ID_COLUMN` | `"file_id"` | OMRChecker Results CSV 的文件标识列名 |

内部值域（非公开，但为行为面的一部分）：合法题型恰为 `("choice", "fill", "solve")`
（与 `types.Item.item_type` 值域一致）；未知题型在映射期即报错〔测试裁定
`test_sheet_build_errors` 的 `"essay"` 用例〕。

### 3.2 `parse_option(option_text, position) -> tuple[str, str]`

选项字符串 → `(标签, 选项正文)`；与 `paper_layout.parse_option` 同闭式（跨模块由
`test_parse_option_matches_paper_layout_on_battery` 锁定）。

**解析规则**（先 `strip`）：

1. 显式标签：匹配「单个 ASCII 字母 + 分隔符（`.` `．` `、` `)` `）` 之一）+
   可选的 `[ \t]*` + 正文至串尾」（正则 `re.S`，正文可含换行）→
   `(标签.upper(), 正文.strip())`；正文**可为空串**。
2. 否则按位置回退：标签 = `"ABCDEFGHIJKLMNOPQRSTUVWXYZ"[position]`，正文 = strip
   后整串（自身）。

**输入门**（均在解析前，全部 `OMRError`）：`option_text` 非 `str`（含 `None`/int/
bytes）；`position` 非 `int` 或为 `bool`（`float` 如 `1.0` 亦拒）；`position` 不在
`[0, 25]`；`strip` 后 `option_text` 为空〔测试裁定 `test_parse_option_input_guards`〕。

例〔测试裁定 `test_parse_option_closed_forms`〕：

| 输入 | 输出 |
|---|---|
| `parse_option("A. 0", 0)` | `("A", "0")` |
| `parse_option("b、题干", 0)` | `("B", "题干")` |
| `parse_option("C）文本", 0)` | `("C", "文本")` |
| `parse_option("D．四", 0)` | `("D", "四")` |
| `parse_option("2", 1)` | `("B", "2")`（无显式标签 → 按位回退） |
| `parse_option("(4,1)", 3)` | `("D", "(4,1)")`（首个字符非单字母+分隔符 → 回退） |
| `parse_option("  B. 2  ", 0)` | `("B", "2")` |
| `parse_option("A.", 0)` | `("A", "")`（显式标签、正文空） |

### 3.3 `field_label(number) -> str`

卷面题号 → OMR 列名：`FIELD_PREFIX + str(number)`。`number` 非 `int`（含 `bool`/
`float`/`str`/`None`）或 `< 1` → `OMRError`〔测试裁定〕。例：
`field_label(1) == "q1"`、`field_label(5) == "q5"`、`field_label(105) == "q105"`。

### 3.4 `parse_field_ranges(numbers) -> list[str]`

题号集合 → 最短 OMRChecker fieldLabels 字段串列表。`numbers` 必须 `list`/`tuple`；
元素必须 `int`（禁 `bool`）且 `≥ 1`。输入**去重升序**后，连续段 `a..b`（`a < b`）输出
`"qa..b"`（**含两端端点**，同 OMRChecker `"q1..10"` 解析为 q1..q10），孤立号输出
`"qa"`。空列表 → `[]`（不报错）〔测试裁定〕。

例：`parse_field_ranges([1, 2, 3, 4]) == ["q1..4"]`；
`parse_field_ranges([1, 3]) == ["q1", "q3"]`；
`parse_field_ranges([1, 2, 4, 5, 6]) == ["q1..2", "q4..6"]`；
`parse_field_ranges([9, 10, 11]) == ["q9..11"]`；
`parse_field_ranges([4, 1, 4, 2]) == ["q1..2", "q4"]`（去重升序）。

### 3.5 `natural_sort_key(label) -> list`

列名 → 自然排序键 `[前缀: str, 数字: int]`（OMRChecker `custom_sort_output_columns`
同款）。`label` 非非空 `str` → `OMRError`。取正则 `([^\d]+)(\d*)` 的 `findall`
**首个匹配组**：前缀 = 首组、数字位 = `int(次组)`（无数字尾缀则为 `0`）。`findall`
返回空列表时（即 `label` 不含任何非数字前缀，如 `"123"`），按实现自由处理
〔参考裁定——契约测试未覆盖此输入面；参考实现返回 `["", 0]`〕。

例：`natural_sort_key("q12") == ["q", 12]`、`natural_sort_key("q1") == ["q", 1]`、
`natural_sort_key("roll") == ["roll", 0]`、`natural_sort_key("q2") <
natural_sort_key("q10")`、`sorted(["q10", "q2", "q1"], key=natural_sort_key) ==
["q1", "q2", "q10"]`。

### 3.6 `build_answer_sheet(paper, bank) -> dict`

**鸭子类型表面**：`paper`（§2）、`bank`（§2）与题目对象（`id`/`item_type`/`answer`/
`options`）。`sections` 为空时回退读取 `paper.item_ids` 作单一隐式节；`sections` 非空时
`paper.item_ids` **不读取、不校验**〔参考裁定——参考实现 V3 仅在 `sec_list` 为空时
`getattr(paper, "item_ids", ...)`〕。

**校验顺序（冻结绑定条款；首个坏点即报错）**：

- **V1 paper 表面**：`paper_id`/`title` 必须 `str`（缺失亦按非 str 拒）；`sections`
  必须 `list`/`tuple`（缺失属性拒）
- **V2 bank 索引**：`bank.items` 必须可调用；`items()` 的返回值必须可迭代（`iter()`
  失败 → `OMRError`）；每题 `id` 必须非空 `str`；`id` 重复 → `OMRError`
- **V3 sections 规整化**：`sections` 为空 → `paper.item_ids` 必须 `list`/`tuple`，
  作 `[{"kp_name": "", "item_ids": [...]}]` 单一隐式节；每个 section 条目必须 `dict`；
  `item_ids` 必须 `list`/`tuple`；每个 id 必须非空 `str`；`kp_name` 若存在必须 `str`
  （**校验后即丢弃，不出现在输出**〔参考裁定——契约测试只断言其类型校验与正常输出〕）
- **V4 逐节逐题**（卷面顺序展开）：`number = len(questions) + 1`（即 1..N 贯穿全卷，
  跨节连续）；未知 item id → `OMRError`；`item_type` 不在 (`choice`,`fill`,`solve`)
  → `OMRError`；`choice` 走 §3.6 选项门；`fill`/`solve` 出 `manual` 三空
- **V5 空卷门**：一题都没有 → `OMRError`
- **V6 outputColumns + fieldBlocks 切段**（见下）

**choice 选项门**：`options` 必须 `list`/`tuple` 且 `≥ 2` 项；逐项按位次 `parse_option`
解出 `(标签, 正文)`；标签必须互不重复（显式撞显式、回退撞显式都算重复）；项数
`≤ MAX_BUBBLES`（26）〔测试裁定 `test_sheet_build_errors`〕。

**输出 dict（恰 9 键，全部新构造容器、无入参别名）**：

- `format_version`: `OMR_VERSION`（`"1"`）；`paper_id`/`title`: paper 透传
- `question_count`/`omr_count`/`manual_count`: `int`，且
  `question_count == omr_count + manual_count`
- `questions`: 卷面顺序 list，每题**恰 6 键** `{number, item_id, mode, field_label,
  bubble_values, options}`：
  - `choice`：`mode="omr"`、`field_label="q<number>"`、`bubble_values` = 标签表
    （`["A","B",…]`）、`options` = `[{"label": …, "text": …}, …]`（`text` 为选项正文
    strip 后，**非**候选答案）
  - `fill`/`solve`：`mode="manual"`、`field_label=None`、`bubble_values=[]`、
    `options=[]`（题目 `options` 即便有值也忽略）
- `output_columns`: 全部 `omr` 题 `field_label` 按 `natural_sort_key` 排序后的 list
  （题号为 1..N 递增，故其必等于 omr 题在 `questions` 中的出现顺序）
- `field_blocks`: 切段规则——按 `questions` 卷面顺序扫描，当前段延续条件为
  「同节 + 气泡表相同 + 连续 omr 题」；遇 `manual` 题、跨节、气泡表不同均**断段**
  （每段恰 4 键）：`{"name": "block<K>"`（K 从 1 按段序连续编号，在封段时确定）,
  `"field_labels": parse_field_ranges(段内题号)`，`"bubble_values": 段首题的气泡表`，
  `"direction": "horizontal"}`；全 `manual` 卷 → `field_blocks == []` 且
  `output_columns == []`

**学生面安全**：输出（JSON 序列化后）不得含 `answer`/`solution`/`stem`/
`misconceptions` 等作答依据字样〔测试裁定 `test_sheet_no_answer_or_stem_leakage`〕。

**例**〔测试裁定 `test_sheet_top_level_shape_and_question_entries` 等〕（夹具：
5 题卷 = c1(choice,4 选项)、f1(fill)、s1(solve)、f2(fill)、c2(choice,2 选项无显式
标签)）：

```python
doc = build_answer_sheet(paper, BANK)
set(doc) == {"format_version","paper_id","title","question_count","omr_count",
             "manual_count","questions","output_columns","field_blocks"}
doc["question_count"] == 5  # omr_count == 2, manual_count == 3
[q["number"] for q in doc["questions"]] == [1,2,3,4,5]
[q["field_label"] for q in doc["questions"]] == ["q1",None,None,None,"q5"]
doc["questions"][0]["bubble_values"] == ["A","B","C","D"]
doc["questions"][0]["options"] == [
    {"label":"A","text":"0"},{"label":"B","text":"-2/3"},
    {"label":"C","text":"+1.5"},{"label":"D","text":"2026"}]
doc["questions"][1] == {"number":2,"item_id":"f1","mode":"manual",
                        "field_label":None,"bubble_values":[],"options":[]}
doc["output_columns"] == ["q1","q5"]
doc["field_blocks"] == [
    {"name":"block1","field_labels":["q1"],
     "bubble_values":["A","B","C","D"],"direction":"horizontal"},
    {"name":"block2","field_labels":["q5"],
     "bubble_values":["A","B"],"direction":"horizontal"}]
```

断段细则〔测试裁定 `test_sheet_field_block_merging_rules`〕：同节同气泡表的连续 omr
题合段（跨节断段、气泡表不同断段、遇手工题断段——手工题只占题号不出列）；例：
同节 `["c4","f1","c4"]`（c4 为 ABCD 的 choice）→ `field_blocks` 为 `[block1:"q1",
block2:"q3"]`（两段气泡表同为 ABCD，但被中间的手工题断开）；两节
`[甲: c4,c4 / 乙: c2x(AB)]` → `[block1:"q1..2" ABCD, block2:"q3" AB]`，
`output_columns == ["q1","q2","q3"]`。

同一题目 id 在卷面重复出现时**按出现次序独立编号**（两次 `c2` → 题号 1、2，列名
`q1`、`q2`），两次映射相等但不是同一对象（无别名）〔测试裁定
`test_sheet_repeated_item_id_numbers_by_occurrence`〕。

### 3.7 `parse_omr_results(csv_text) -> list[dict]`

OMRChecker Results CSV 文本 → 行 dict 列表。`csv_text` 非 `str`（含 bytes/None）→
`OMRError`。处理规则（顺序绑定）：

1. 剥除文本**首个**字符处的 BOM（U+FEFF，仅一个）
2. 经 `csv.reader(io.StringIO(csv_text))` 解析（默认方言：引号单元格含逗号/换行照常
   切分）；`csv.reader` 产出空 list 的行（空行）**跳过**
3. 首个非空行为表头：每格必须非空 `str`；列名互不重复；必含 `file_id` 列
4. 数据行：格子数必须**等于**表头列数（长/短都拒）；`file_id` 单元格 `strip` 后
   必须非空
5. 每行产出 `{"file_id": 单元格原文（不 strip）, "values": {除 file_id 外每一列:
   单元格原文}}`；`values` 的插入序为表头列序
6. 表头之后无数据行 → `[]`（容忍，不报错）

`score` 列照录字符串（判分不靠它）；不做排序、去重、聚合、数值解析〔测试裁定〕。

**例 1**〔测试裁定 `test_parse_results_closed_form_and_row_order`〕：

```python
RESULTS_CSV = (
    "file_id,input_path,output_path,score,q1,q2,q3,q5\r\n"
    "scan001.jpg,in/001.jpg,out/001.jpg,1.0,B,,A,C\r\n"
    "scan002.jpg,in/002.jpg,out/002.jpg,2.0,AC,B,A,\r\n"
)
parse_omr_results(RESULTS_CSV) == [
    {"file_id": "scan001.jpg",
     "values": {"input_path": "in/001.jpg", "output_path": "out/001.jpg",
                "score": "1.0", "q1": "B", "q2": "", "q3": "A", "q5": "C"}},
    {"file_id": "scan002.jpg",
     "values": {"input_path": "in/002.jpg", "output_path": "out/002.jpg",
                "score": "2.0", "q1": "AC", "q2": "B", "q3": "A", "q5": ""}},
]
```

（未涂记空串、多涂按气泡序拼接 `"AC"`；行序 = 文件顺序。）

**例 2**〔测试裁定 `test_parse_results_quoted_cells_bom_and_blank_lines`〕：
`chr(0xFEFF) + "file_id,note,q1\r\n" + "\r\n" + '"scan, 001.jpg","含,逗号",B\r\n'`
→ `[{"file_id": "scan, 001.jpg", "values": {"note": "含,逗号", "q1": "B"}}]`
（BOM 剥除、空行跳过、引号单元格原样解出）。

**例 3**：`parse_omr_results("file_id,q1,q2\r\n") == []`（表头 only）。

### 3.8 `to_responses(row, sheet, bank) -> list[Response]`

一张卡的 OMR 涂点 → `Response` 列表（`xuexing.types.Response`）。

**鸭子类型表面**：

- `row`: `dict`，必含 `"values": dict[str, str]`（键值都必须是 `str`；允许额外列，
  额外列原样容忍但还原不使用）；`row` 的其余键（如 `file_id`）忽略
- `sheet`: `build_answer_sheet` 产出的 dict（只消费 `questions`；`output_columns`/
  `field_blocks`/计数字段不使用也不校验〔参考裁定——契约测试未在这些字段上构造
  输入〕）
- `bank`: 同 §3.6

**校验顺序（冻结绑定条款）**：

- **V1 sheet 表面**：`sheet` 必须 `dict`；`format_version` 必须 `== "1"`（其他一律
  `OMRError`，不做自动迁移）；`questions` 必须 `list`/`tuple`
- **V2 row 表面**：`row` 必须 `dict`；`row["values"]` 必须 `dict`；`values` 的每个
  键、值都必须 `str`
- **V3 bank 索引**：`bank.items` 可调用；每题 `id` 非空 `str`；重复 `id` → `OMRError`
- **V4 逐题还原**（仅 `sheet["questions"]` 顺序）：每个 question 必须 `dict`；
  `number` 必须 `int ≥ 1`（禁 `bool`）且 questions 内不重复；`item_id` 非空 `str`；
  `mode == "manual"` → **跳过不产 `Response`**；其他 `mode` 值 → `OMRError`；
  `field_label` 非空 `str` 且在 omr 题间不重复；`item_id` 必须在 bank 索引中；bank 中
  该题 `item_type` 必须 `"choice"`（sheet 标 `omr` 而 bank 非 choice → 漂移硬失败）；
  choice 选项门同 §3.6；`question["bubble_values"]` 必须逐项等于 bank 选项标签表
  （长度与每项都相等，否则漂移硬失败）

**涂点三路**（`marked = values.get(列名)`；缺列 → `OMRError`；单元格非 `str` →
`OMRError`；`text = marked.strip()`；`normalized = text.upper()`；`normalized` 的
每个字符必须 ∈ 气泡值表，否则未知涂点 `OMRError`）：

| 涂点 | `Response` |
|---|---|
| 空串（未涂） | `correct=False`、`learner_answer=None`、`response_ms=None`（无作答证据，判错但不伪造内容） |
| 单字符 | `correct = (涂点下标 == 答案下标)`；`learner_answer = bank options[涂点下标]` 的**原文全串**（如 `"B. -2/3"`，非标签、非归一化形）；`response_ms=None` |
| 多字符 | `correct=False`（**恒错，不猜**）；`learner_answer = normalized`（大写拼接串，如 `"AC"`，留证据）；`response_ms=None` |

**答案解析（仅单涂支触发）**〔参考裁定——未涂/多涂支不解析 answer，题目 answer 坏也
照常出 Response〕：`item.answer` 必须 `str`（否则 `OMRError`）；`target =
answer.strip().upper()`；先**标签趟**（与气泡标签相等取首个命中），再**正文趟**
（与选项正文 `strip().upper()` 相等）；两趟都不中 → `OMRError`（题目本身坏，
不允许静默全错）。

返回列表 = 各 `omr` 题按 `sheet["questions"]` 顺序的 `Response`（`manual` 题跳过）；
`response_ms` 恒 `None`（本模块不计时）。

**例 1**〔测试裁定 `test_to_responses_closed_form_happy_path`〕（§3.6 的 5 题卷
sheet；c1 答案 `"B"` 走标签路，c2 无显式标签、答案 `"2"` 走正文路）：

```python
to_responses({"file_id": "scan001.jpg", "values": {"q1": "B", "q5": "A"}},
             sheet, BANK) == [
    Response(item_id="c1", correct=True,  learner_answer="B. -2/3",
             response_ms=None),
    Response(item_id="c2", correct=True,  learner_answer="2",
             response_ms=None),
]
# 选错：{"q1": "A", "q5": "B"} -> c1 False/"A. 0"；c2 False/"3"
```

**例 2**〔测试裁定 `test_to_responses_unmarked_multimarked_lowercase`〕：
`{"q1": "b", "q5": ""}` → `[Response("c1", True, "B. -2/3", None)`（小写涂点归一
后单涂，learner_answer 仍是 options 原文），`Response("c2", False, None, None)`
（未涂）`]`；`{"q1": "AC", "q5": "A"}` → 首项
`Response("c1", False, "AC", None)`（多涂恒错、拼接串留证）。

**跨模块锁定**：对契约测试域内 6 组涂点（含未涂/小写/多涂），每个 `Response` 的
`correct == grading.grade_choice(item, response.learner_answer)`〔测试裁定
`test_to_responses_cross_locked_with_grading`〕——单涂的 `learner_answer` 设计为 bank
`options` 原文全串，使两模块对显式标签题与位置回退标签题同判。

## 4. 不变量（编号列出，全部可被契约测试检验）

- I1 **常量冻结**：`OMR_VERSION == "1"`、`FIELD_PREFIX == "q"`、
  `MODE_OMR == "omr" and MODE_MANUAL == "manual"`、`BLOCK_DIRECTION == "horizontal"`、
  `MAX_BUBBLES == 26`、`RESULTS_FILE_ID_COLUMN == "file_id"`、`OMRError` 是
  `ValueError` 直接子类（`test_frozen_constants`）。
- I2 **选项标签解析闭式 + 跨模块同款**：`parse_option` 先 strip、显式标签
  （单 ASCII 字母 + `.．、)）` 分隔符）优先且标签归一大写、正文 strip 可为空串；
  否则按位回退 `A`–`Z`、整串作正文；与 `paper_layout.parse_option` 在
  battery（**13 个输入**）× position {0,5,10,15,20,25} 上逐对相等；
  `option_text` 非 str/空、`position` 非 int（含 bool）或越界一律 `OMRError`
  （`test_parse_option_closed_forms`、`test_parse_option_matches_paper_layout_on_battery`、
  `test_parse_option_input_guards`）。
- I3 **列名/字段串/自然排序闭式**：`field_label(n) == "q"+str(n)`（n 为正 int，
  `True`/`2.0`/`"3"`/`None`/`0`/负拒）；`parse_field_ranges` 去重升序、连续段输出
  含端点 `"qa..b"`、孤立号 `"qa"`、空 list → `[]`、容器非 list/tuple 拒；
  `natural_sort_key` 返回 `[前缀, 数字]`（无数字后缀数字位 0），`q2 < q10`
  （`test_field_label_closed_forms`、`test_parse_field_ranges_closed_forms`、
  `test_natural_sort_key_closed_forms`）。
- I4 **sheet 映射闭环**：顶层恰 9 键、每题恰 6 键；题号 1..N 贯穿全卷、`item_id` 按
  卷面节序展开；`choice → omr` 带气泡表与 `{"label","text"}` 选项、`fill/solve →
  manual` 三空（`field_label=None`、`bubble_values=[]`、`options=[]`）；
  `question_count == omr_count + manual_count`；`output_columns` = omr 题列名的
  自然排序；`field_blocks` 按「同节 + 同气泡表 + 连续 omr」切段（manual/跨节/气泡表
  不同均断段），段名 `block1, block2, …` 顺序编号，`field_labels` 为段内题号字段串，
  `bubble_values` 为段首题气泡表，`direction` 恒 `"horizontal"`；全 manual 卷
  `field_blocks == []`、`output_columns == []`、`omr_count == 0`
  （`test_sheet_top_level_shape_and_question_entries`、
  `test_sheet_output_columns_and_field_blocks_closed`、
  `test_sheet_field_block_merging_rules`）。
- I5 **学生面不泄答案**：`build_answer_sheet` 输出 JSON 序列化后不含
  `answer`/`solution`/`stem`/`misconception`（及 `ANS`/`SOL-`）字样；fill/solve 题
  不出涂点（`test_sheet_no_answer_or_stem_leakage`）。
- I6 **重复题独立编号、无别名**：同一 item id 多次出现按出现次序得递增题号与列名，
  两次选项映射相等但不是同一对象（`test_sheet_repeated_item_id_numbers_by_occurrence`）。
- I7 **build 完整性门**：空卷、未知 item id、未知 item_type、choice 选项 < 2、标签
  重复（含回退撞显式）、选项 > 26、bank 重复 id、paper 表面坏（缺 `sections` 属性、
  `sections` 非 list、条目非 dict、缺 `item_ids`、id 非 str、`kp_name` 非 str）、
  `sections` 空而 `paper.item_ids` 非 list、bank 无 `items()`/`items()` 返回不可
  迭代——一律 `OMRError`（`test_sheet_build_errors`、
  `test_sheet_malformed_paper_and_bank_surfaces_rejected`）。
- I8 **CSV 解析闭式**：BOM 剥除、空行跳过、表头非空互异必含 `file_id`、数据行宽必须
  等于表头、`file_id` strip 后非空；行 dict = `{"file_id": 原文, "values": 其余列
  原文}`；`score` 照录字符串；表头 only → `[]`；行序 = 文件顺序；引号单元格正确切分
  （`test_parse_results_closed_form_and_row_order`、
  `test_parse_results_quoted_cells_bom_and_blank_lines`、
  `test_parse_results_header_only_returns_empty`、`test_parse_results_errors`）。
- I9 **to_responses 三路语义**：未涂 → `(correct=False, learner_answer=None)`；
  单涂 → `learner_answer` = bank options 原文全串且 `correct` = 涂点 vs 答案（答案按
  标签趟、正文趟两路解析）；多涂 → `(correct=False, learner_answer=大写拼接串)`；
  小写涂点归一后判；`manual` 题不产 `Response`；返回序 = sheet omr 题序；
  `response_ms` 恒 `None`（`test_to_responses_closed_form_happy_path`、
  `test_to_responses_unmarked_multimarked_lowercase`、
  `test_to_responses_answers_resolved_by_label_or_text`）。
- I10 **与 grading 跨模块同判**：测试域内每张卡每个 `Response` 的 `correct ==
  grade_choice(item, learner_answer)`（含未涂 `None` 与多涂拼接串情形）
  （`test_to_responses_cross_locked_with_grading`）。
- I11 **漂移硬失败（to_responses）**：缺 OMR 列、未知涂点字符、sheet 非 dict、row 缺
  `values`、`format_version != "1"`、bank 漂移（题型变/气泡表不一致/未知题/重复
  id）、`answer` 无法解析、sheet 结构坏（题号重复/列名重复/未知 mode/number 非法）——
  一律 `OMRError`，绝不静默错位判分（`test_to_responses_errors_and_integrity_gates`）。
- I12 **纯函数/确定性/JSON 兼容**：不修改 paper/bank/row 入参（deepcopy 前后相等）；
  重复调用结果相等（含 `json.dumps(..., sort_keys=True)` 逐位相等）；sheet 与 rows
  均 JSON round-trip 相等（`test_purity_inputs_not_mutated`、
  `test_determinism_and_json_serializable`）。
- I13 **真实卷端到端**：`generate_paper(small_bank, small_graph, {...}, seed=5)` 的
  paper 可直建 sheet——`question_count == len(paper.item_ids) == omr_count +
  manual_count`、`omr_count` = choice 题数、`output_columns` = omr 题列名且按自然
  排序；全对卡（每题涂正确气泡）经 `build_answer_sheet → parse_omr_results →
  to_responses` 全部 `correct`（`test_feeds_generate_paper_end_to_end`）。

## 5. 确定性与随机性

- 全模块纯函数：输出只依赖入参；禁止 `random`、hash 序、系统时钟、环境读取、
  文件/网络 IO、全局可变状态。全模块无时间戳字段（`response_ms` 恒 `None`，
  无任何豁免）。
- `build_answer_sheet` 的输出全部为**新构造容器**（`questions`/`options`/
  `field_blocks` 等与入参 paper/bank 无别名）；`to_responses`/`parse_omr_results`
  不修改入参。
- 确定性判定方式：重复调用 `==` 相等；输出 JSON 可序列化且
  `json.loads(json.dumps(x, ensure_ascii=False)) == x`。
- 无浮点计算（无除法/舍入面）；全部闭式值为整数、字符串与列表/字典结构，
  §3 中每个例子都是逐位对照点。

## 6. 错误行为

异常类型一律 `OMRError`（`ValueError` 直接子类）；契约内输入不抛其他异常。

| 非法输入 | 行为 |
|---|---|
| `parse_option`：`option_text` 非 str / strip 后空 | 抛 `OMRError` |
| `parse_option`：`position` 非 int（含 `bool`、`float`）或 ∉ [0, 25] | 抛 `OMRError` |
| `field_label`：`number` 非 int（含 `bool`）或 < 1 | 抛 `OMRError` |
| `parse_field_ranges`：`numbers` 非 list/tuple；元素非 int（含 `bool`）或 < 1 | 抛 `OMRError` |
| `parse_field_ranges`：空 list | 容忍，返回 `[]` |
| `natural_sort_key`：`label` 非 str 或空 | 抛 `OMRError` |
| `build_answer_sheet`：`paper.paper_id`/`paper.title` 非 str（含缺失） | 抛 `OMRError` |
| `build_answer_sheet`：`paper.sections` 非 list/tuple（含缺失属性） | 抛 `OMRError` |
| `build_answer_sheet`：`bank` 无 `items()` / `items()` 返回不可迭代 | 抛 `OMRError` |
| `build_answer_sheet`：bank 题 `id` 非非空 str / 重复 id | 抛 `OMRError` |
| `build_answer_sheet`：`sections` 空而 `paper.item_ids` 非 list/tuple | 抛 `OMRError` |
| `build_answer_sheet`：section 条目非 dict / `item_ids` 非 list / id 非非空 str / `kp_name` 非 str | 抛 `OMRError` |
| `build_answer_sheet`：未知 item id / 未知 `item_type`（∉ choice/fill/solve） | 抛 `OMRError` |
| `build_answer_sheet`：choice 选项 < 2 / 标签重复 / > 26 | 抛 `OMRError` |
| `build_answer_sheet`：空卷（一题都没有） | 抛 `OMRError` |
| `parse_omr_results`：`csv_text` 非 str（含 bytes、None） | 抛 `OMRError` |
| `parse_omr_results`：无表头（空文本/仅空行） | 抛 `OMRError` |
| `parse_omr_results`：表头空单元格 / 列名重复 / 缺 `file_id` 列 | 抛 `OMRError` |
| `parse_omr_results`：数据行宽 ≠ 表头宽（长/短都拒） | 抛 `OMRError` |
| `parse_omr_results`：`file_id` 单元格 strip 后为空 | 抛 `OMRError` |
| `parse_omr_results`：BOM / 引号单元格 / 空行 | 容忍：剥除、按 csv 语义切分、跳过 |
| `parse_omr_results`：表头之后无数据行 | 容忍，返回 `[]` |
| `to_responses`：`sheet` 非 dict / `format_version != "1"` / `questions` 非 list | 抛 `OMRError` |
| `to_responses`：`row` 非 dict / 缺 `values`（或非 dict）/ `values` 非 str→str | 抛 `OMRError` |
| `to_responses`：`bank` 无 `items()` / 题 id 坏 / 重复 id | 抛 `OMRError` |
| `to_responses`：question 非 dict / `number` 非 int≥1（含 `bool`）或重复 / `item_id` 坏 / 未知 `mode` / `field_label` 坏或重复 | 抛 `OMRError` |
| `to_responses`：sheet/bank 漂移——sheet 题 id 不在 bank / bank 题型非 choice / `bubble_values` ≠ bank 标签表 | 抛 `OMRError` |
| `to_responses`：缺 OMR 列 / 单元格非 str | 抛 `OMRError` |
| `to_responses`：涂点字符 ∉ 气泡值表（未知涂点） | 抛 `OMRError` |
| `to_responses`：`item.answer` 非 str / 标签趟与正文趟都不中 | 抛 `OMRError`（仅单涂支触发；未涂/多涂不解析答案） |
| `to_responses`：未涂 / 多涂 / `manual` 题 / `values` 额外列 | 容忍：按 I9 三路产出、跳过、忽略 |

## 7. 非目标

- **不画答题卡、不做像素几何**：origin/间距/纸张尺寸/OMRChecker template.json 的像素
  参数不在本模块；本模块只出内容侧信息（列名、气泡值表、字段串、方向）。
- **不扫描、不 OCR、不写真**：`parse_omr_results` 只解析文本；`manual` 题的录入走
  人工/OCR 渠道。
- **不判 fill/solve 主观题**：`manual` 题不产 `Response`；其判分归 grading 模块与
  教师/批改端；适配层不越界。
- **不做多选真相/半对/部分分猜测**：单涂才判；多涂恒 `False` 且不猜正确项。
- **不与其他 xuexing 模块互 import**：与 `paper_layout.parse_option` 同闭式、与
  `grading.grade_choice` 同判、吃 `generate_paper` 产出的 paper——这些跨模块一致性
  由契约测试在测试侧锁定，实现侧零 import。
- **不做静默容错/自动纠偏**：sheet/bank 漂移（未知题、题型变、气泡表不一致、缺列、
  未知涂点）一律硬失败；不做降级判分、不跳过错位题。
- **不做学习者身份管理或分数聚合**：`file_id` 只是行标识透传；不解析 `score` 数值、
  不做跨行统计、不汇总体检报告。
- **不计时**：`response_ms` 恒 `None`；无任何时钟读取。
- **不持久化**：不写文件/数据库/网络；`parse_omr_results` 的输入由调用方给文本。
- **不生成 OMRChecker 可执行模板或 Results CSV**：只定义内容侧 schema 与解析语义。
- **不做答案泄露**：学生面文档不含答案/题干/解析/误解标签。
- **不做 schema 版本迁移**：`to_responses` 只接受 `format_version == "1"`，其他一律
  `OMRError`。
- **不做 CSV 清洗**：只在 §3.7 列明的范围内处理 BOM/空行/引号；不去重、不排序、
  不聚合、不修补行长。
