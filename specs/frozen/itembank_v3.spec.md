# itembank_v3 模块规格（冻结契约）

> 本文档是唯一权威契约。任何实现（参考实现或重生成实例）只要通过 tests/contract/ 全部测试
> 且满足本文全部条款，即为合格实现。实现算法自由，行为不允许偏离。
>
> **版本**：冻结 v1。标注「〔测试裁定〕」的行为由 `tests/contract/test_itembank_v3_contract.py`
> 直接断言（下文行号简写为 `test:<测试名>`）；本文全部数值例子均为实测值（参考实现
> `src/xuexing/itembank_v3.py` + 上述契约测试，2026-10-02 冻结会话实测，CPython 3.12.10
> x64 / Windows）。

## 1. 目的

itembank_v3 是 **item schema v3 新字段校验层**：在冻结模块 itembank_v2 的
source/verification 字段之上，为题库 item dict 定义五个**可选**新字段并机器强制其
完整性——

- `form`：题型形态标签（严格枚举，见 §3.1；支持选择之外的新题型形态——essay/proof/
  experiment/comprehension/cloze/listening 等）。
- `acceptable_variants`：可接受答案变体表（仅 fill/solve/essay/proof 类可携带；非空
  list、元素为非空白 str、按原始字面值去重）——主答案之外的等价写法，供判分与 LLM
  复验使用。
- `scoring_points`：分步给分点表（`[{point, score}]`，每点分值 > 0）；与
  acceptable_variants **二选一**（互斥），可都无。
- `rubric`：评分量表（`{"total", "dimensions"}`；各维 `max_score` 之和必须恰等
  `total`）；**仅 form 为 essay 时必填**。
- `textbook_ref`：教材出处（`<出版社代码>:<册>:<章>`，如 `pep:g5:u3`）。

**与 itembank_v2 的分层边界（冻结）**：v2 的 source/source_ref/verification 字段
完整性仍由冻结模块 `xuexing.itembank_v2.validate_item_v2` 负责；本模块**不检查**
这些字段，也不 import、不重复实现 v2 逻辑。完整 v3 入库校验 = 调用方对同一 item
先后运行 `validate_item_v2` 与 `validate_item_v3` 并拼接两者消息（消息前缀纪律与
渲染纪律逐字一致，可直接拼接；跨模块锁定见
`test_boundary_with_v2_fields_is_layered`）。

校验器是返回错误消息列表的**全函数**：`validate_item_v3` 对任意输入对象不抛异常、
纯函数（无 IO、无随机、无时钟、不读环境）；`validate_items_v3` 对可迭代入参同样不抛
异常，入参不可迭代时 TypeError 原样传播（§6、I12）。

消息前缀 `p = id 字面渲染`（f-string，无 repr 引号；缺失 → `"<no-id>: "`）与错误
消息中违规值一律 `repr` 渲染的纪律，与 itembank_v2 逐字一致。

## 2. 允许的依赖

- Python 标准库，逐个列出：`math`（`isfinite` 数字门）、`re`（textbook_ref 格式
  正则，模块级编译一次）
- **零 xuexing 依赖**：不需要 `xuexing.types`（校验面向题库 dict，不构造 Item
  对象）；**禁止 import 任何其他 xuexing 模块**（含 itembank_v2——分层边界见 §1；
  一致性由契约测试在测试内 import 对方模块跨模块锁定）
- 禁止：第三方库、文件/网络 IO、`random`、系统时钟、环境读取

**注入装载约束**：重生成实例由测试夹具按单文件以 importlib 装载为顶层模块名
`_regen_itembank_v3` 并顶替 `sys.modules["xuexing.itembank_v3"]`
（tests/conftest.py:22-34），不经过包 `__init__`。因此**不使用**
`from __future__ import annotations`（注解直接写真实对象）、**不使用相对导入**
（顶层名装载时失败）。本模块函数签名无自定义类型注解，不受影响。

输入表面：题库 dict（含 `form`/`acceptable_variants`/`scoring_points`/`rubric`/
`textbook_ref` 等键的任意 dict）。校验只依赖上述键与 `id`（仅消息前缀），其余键
一律忽略（前向兼容——v2 字段与无关键均不归本模块管，见 §1 边界）。

## 3. 公开 API

模块必须暴露以下 6 个名字（契约测试 `from xuexing.itembank_v3 import (SCHEMA_VERSION,
FORM_VALUES, VARIANT_FORMS, TEXTBOOK_REF_RE, validate_item_v3, validate_items_v3)`）。

### 3.1 常量

```python
SCHEMA_VERSION = 3                                               # int
FORM_VALUES = ("choice", "fill", "solve", "essay", "proof",
               "experiment", "comprehension", "cloze", "listening")   # tuple，canonical 顺序
VARIANT_FORMS = ("fill", "solve", "essay", "proof")               # tuple，FORM_VALUES 子序列
TEXTBOOK_REF_RE = re.compile(r"[a-z0-9]+:[a-z0-9]+:[a-z0-9]+")    # fullmatch 锚定
```

`TEXTBOOK_REF_RE` 必须经 `fullmatch` 施加（恰好三段、每段非空的小写 ASCII 字母
数字）。〔测试：test_schema_constants〕

### 3.2 `validate_item_v3`

```python
def validate_item_v3(item) -> list
```

单题 v3 新字段校验。对**任意**输入对象不抛异常，返回 0..n 条错误消息（str 列表）。
非 dict 输入只返回 `["item is not a dict"]`（无前缀）。

消息前缀 `p`：`id` 键存在时按其值**字面渲染**（f-string/str 渲染，不带 repr 引号；
falsy/非 str/dict 照渲染——`id=None` → `"None: "`、`id=""` → `": "`、`id=42` →
`"42: "`、`id={"x": 1}` → `"{'x': 1}: "`）；键缺失 → `"<no-id>: "`。〔测试：
test_id_prefix_rendering〕

**数字门（全文适用）**：凡要求"数"处，一律指 `isinstance(v, (int, float)) and not
isinstance(v, bool) and math.isfinite(v)`——bool 是 int 子类，按非数拒绝；NaN/inf
同拒。凡要求"非空白 str"处，指 `isinstance(v, str) and v.strip() != ""`。

规则目录（**F1→F5 固定顺序累积、不短路**；各规则独立评估实际值）：

| # | 条件（违反则报错） | 错误消息（精确格式） |
|---|---|---|
| F1 | `"form"` 键**存在**，且值不是恰等于 FORM_VALUES 成员的 str（非 str、空串、空白串、未知值、带首尾空白的枚举值同消息；成员判定用**原始值**，不 strip、大小写敏感） | `{p}bad form {v!r}` |
| F2a | `"acceptable_variants"` 与 `"scoring_points"` 两键**同时存在**（与实际取值无关，至多一条） | `{p}acceptable_variants and scoring_points are mutually exclusive` |
| F2b | `"acceptable_variants"` 键存在，且 `item.get("form")`（原始值）不在 VARIANT_FORMS（form 缺失/非法/其余题型同报——变体表只允许 fill/solve/essay/proof 声明携带） | `{p}acceptable_variants requires form in fill/solve/essay/proof` |
| F2c | 键存在且值非 list（tuple/str/dict/None 同拒） | `{p}acceptable_variants must be a list, got {v!r}` |
| F2c' | 键存在且值为空 list | `{p}acceptable_variants must be non-empty` |
| F2d | 仅当通过 F2c/F2c'（非空 list）：逐元素（列表序）非 str、strip 后空、或带首尾空白（`el != el.strip()`） | `{p}bad acceptable_variant {el!r}`（每坏元素一条，列表序） |
| F2e | 仅当通过 F2c/F2c'：全部 str 元素按**原始字面值**判重（不 strip、含 F2d 坏元素），存在相等值即报 | `{p}duplicate acceptable_variants`（至多一条，恒在全部 F2d 消息之后） |
| F3a | `"scoring_points"` 键存在且值非 list | `{p}scoring_points must be a list, got {v!r}` |
| F3a' | 键存在且值为空 list | `{p}scoring_points must be non-empty` |
| F3b-形 | 仅当通过 F3a/F3a'：逐条目（列表序）非 dict，或键集合非恰 `{"point","score"}`（缺失键/多余键同消息，不再拆分） | `{p}bad scoring_point {entry!r}` |
| F3b-point | 条目形状合法但 `point` 非非空白 str | `{p}scoring_point point must be a non-blank str, got {v!r}` |
| F3b-score | 条目形状合法但 `score` 非"有限实数 > 0"（0/负数/bool/字符串/None/NaN/inf 同消息） | `{p}scoring_point score must be a number > 0, got {v!r}` |
| F4a | `item.get("form")` **原始值**恰为 `"essay"` 且 `"rubric"` 键缺失（缺失与键不存在同罪；显式 `null` 报 F4b 而非本条） | `{p}essay requires rubric` |
| F4b | `"rubric"` 键存在且值非 dict，或键集合非恰 `{"total","dimensions"}`（一条结构消息，后续 rubric 检查跳过） | `{p}bad rubric {v!r}` |
| F4b-total | 结构合法但 `total` 非"有限实数 > 0" | `{p}rubric total must be a number > 0, got {v!r}` |
| F4b-dims | 结构合法但 `dimensions` 非非空 list | `{p}rubric dimensions must be a non-empty list, got {v!r}` |
| F4c-形 | 仅当 dimensions 为非空 list：逐维（列表序）非 dict，或键集合非恰 `{"name","max_score","level_descriptors"}` | `{p}bad rubric dimension {entry!r}` |
| F4c-name | 维度形状合法但 `name` 非非空白 str | `{p}rubric dimension name must be a non-blank str, got {v!r}` |
| F4c-max | 维度形状合法但 `max_score` 非"有限实数 > 0" | `{p}rubric dimension max_score must be a number > 0, got {v!r}` |
| F4c-levels | 维度形状合法但 `level_descriptors` 非非空 list | `{p}rubric dimension level_descriptors must be a non-empty list, got {v!r}` |
| F4c-lv-形 | level_descriptors 为非空 list 时逐级（列表序）：非 dict 或键集合非恰 `{"level","min_score","desc"}` | `{p}bad rubric level {entry!r}`（后续该级检查跳过） |
| F4c-lv-level | 该级形状合法但 `level` 非非空白 str | `{p}rubric level must be a non-blank str, got {v!r}` |
| F4c-lv-min | 该级形状合法但 `min_score` 非"有限实数 ≥ 0" | `{p}rubric level min_score must be a number >= 0, got {v!r}` |
| F4c-lv-desc | 该级形状合法但 `desc` 非非空白 str | `{p}rubric level desc must be a non-blank str, got {v!r}` |
| F4c-dup | 全部维消息之后：str 形态的 name 按**原始值**判重（非 str name 不参与），至多一条 | `{p}duplicate rubric dimension names` |
| F4d | **门控**：仅当 `total` 合法且每个维的 `max_score` 均合法时，评估 Σmax_score 与 total 的**精确相等**（有非法分量或 dimensions 非法则跳过不报） | `{p}rubric dimensions max_score sum {sum!r} != total {total!r}` |
| F5 | `"textbook_ref"` 键存在且值非 str 或不过 `TEXTBOOK_REF_RE.fullmatch` | `{p}bad textbook_ref {v!r}` |

**消息序探针**（【测试裁定】）：

- F1→F2a→F2b→F3→F5 全触发：
  `{"id":"x","form":"nope","acceptable_variants":["a"],"scoring_points":[],"textbook_ref":"BAD"}`
  → `["x: bad form 'nope'", "x: acceptable_variants and scoring_points are mutually exclusive",
  "x: acceptable_variants requires form in fill/solve/essay/proof",
  "x: scoring_points must be non-empty", "x: bad textbook_ref 'BAD'"]`
  〔test_rule_accumulation_order〕
- essay 必填门独立于 F1 报错之后求值：`{"form":"essay","acceptable_variants":["a"]}` →
  `["i1: essay requires rubric"]`（F2b 对 essay 放行）〔test_variants_require_allowed_form〕
- 原始值口径：`form=" essay "` → `["i1: bad form ' essay '"]` 且**不**触发 essay 必填门
  〔test_rubric_required_for_essay_only〕
- F2d/F2e 门控与比较域同 v2 的 C2/C3：`[" b"," b"]` → 坏×2 + duplicate；`["a","a "]`
  → 仅 `"a "` 坏元素、**不**判重〔test_variant_duplicate_rules〕

实测探针（与契约测试逐字对应）：

- `validate_item_v3({"id":"i1"})` → `[]`（v3 五字段全缺合法）
- `validate_item_v3({"id":"i1","form":"fill","acceptable_variants":["1/2","0.5"]})` → `[]`
- `validate_item_v3({"id":"i1","form":"essay","rubric":{"total":5,"dimensions":[
  {"name":"甲","max_score":5,"level_descriptors":[{"level":"A","min_score":0,"desc":"起步"}]}]}})` → `[]`
- `validate_item_v3({"id":"i1","textbook_ref":"pep:g5:u3"})` → `[]`

### 3.3 `validate_items_v3`

```python
def validate_items_v3(items) -> list
```

逐题 `validate_item_v3` 并按**输入原序**拼接；不去重、不排序；空输入 → `[]`；非 dict
元素各产 `item is not a dict` 一条后继续。入参须为可迭代对象；**不可迭代时
TypeError 原样传播**（探针：`validate_items_v3(42)` → `TypeError: 'int' object is
not iterable`，§6/I12）；可迭代时对任意元素不抛异常。〔测试：
test_items_v3_accumulates_in_input_order_without_dedup、
test_items_v3_non_iterable_propagates_typeerror〕

## 4. 不变量（编号列出；全部可被契约测试检验）

- I1 **常量冻结**：`SCHEMA_VERSION == 3`；`FORM_VALUES` 恰为 §3.1 九元 tuple；
  `VARIANT_FORMS` 恰为四元 tuple 且为 FORM_VALUES 子序列；`TEXTBOOK_REF_RE`
  fullmatch `pep:g5:u3`。〔测试：test_schema_constants〕
- I2 **全函数**：非 dict 输入（None/int/str/list/bool/float）只返回
  `["item is not a dict"]`；对恶劣输入电池（嵌套容器/错型/空结构）永不抛异常、
  消息全为 str。〔测试：test_non_dict_items、test_never_raises_battery〕
- I3 **字段可选与前向兼容**：五个新字段全部可选；`{}` 与带任意无关/v2 字段的 item
  → `[]`（v2 字段不归本模块管）。〔测试：test_no_v3_fields_passes、
  test_boundary_with_v2_fields_is_layered〕
- I4 **form 严格枚举**：键存在时原始值必须恰为 FORM_VALUES 成员——非 str、空串、
  空白串、未知值、带首尾空白的枚举值、大小写变体全部 `bad form {repr}`（一条）；
  缺键不报。〔测试：test_form_accepts_every_enum_value、test_form_rejections〕
- I5 **变体表三重门**：题型门（仅 fill/solve/essay/proof，form 原始值口径）+ 类型门
  （非空 list，tuple 拒）+ 元素门（非空白无首尾空白 str，逐元素消息）；判重按原始
  字面值、至多一条、居元素消息之后。〔测试：test_variants_require_allowed_form、
  test_variants_type_and_empty、test_variant_element_rules、test_variant_duplicate_rules〕
- I6 **二选一互斥**：`acceptable_variants` 与 `scoring_points` 两键同时存在即报
  互斥（至多一条，与实际取值无关），且各自的值校验照常累积；可都无、仅带其一合法。
  〔测试：test_variants_and_scoring_points_mutually_exclusive〕
- I7 **给分点表形状**：非空 list；条目为键恰 `{point,score}` 的 dict（形状违规一条
  不拆分）；point 非空白 str；score 有限实数 > 0（bool/NaN/inf/字符串同拒）；多条目
  按列表序逐条报。〔测试：test_scoring_points_valid、test_scoring_points_type_and_empty、
  test_scoring_point_entry_rules〕
- I8 **rubric 必填仅限 essay**：form 原始值恰 `"essay"` 且 rubric 键缺失 →
  `essay requires rubric`；其余题型/缺 form 时 rubric 可选（可带、可不带；带了就
  全量校验）。〔测试：test_rubric_required_for_essay_only〕
- I9 **rubric 结构与闭合形状**：rubric 为键恰 `{total,dimensions}` 的 dict；total
  有限实数 > 0；dimensions 非空 list；每维为键恰 `{name,max_score,level_descriptors}`
  的 dict；name 非空白 str 且按原始值判重（至多一条、居全部逐维消息之后）；max_score
  有限实数 > 0；level_descriptors 非空 list、每级为键恰 `{level,min_score,desc}` 的
  dict，level/desc 非空白 str、min_score 有限实数 ≥ 0；**Σmax_score 与 total 精确
  相等**（门控见 F4d）。〔测试：test_rubric_structure_rules、
  test_rubric_dimension_and_level_rules、test_rubric_duplicate_dimension_names、
  test_rubric_sum_rule〕
- I10 **textbook_ref 格式**：三段小写 ASCII 字母数字（`[a-z0-9]+:[a-z0-9]+:[a-z0-9]+`
  fullmatch）——大写、段数不足/超、空段、空白、下划线、非 str 全部
  `bad textbook_ref {repr}`。〔测试：test_textbook_ref_rules〕
- I11 **累积纪律与前缀**：单题消息按 F1→F5 固定顺序、结构门之后的子检查跳过（门控
  语义逐条冻结在 §3.2）；id 缺失 → `<no-id>: `，存在按值字面渲染（含 falsy/非
  str/dict）。〔测试：test_rule_accumulation_order、test_id_prefix_rendering〕
- I12 **bank 语义与域外传播**：validate_items_v3 输入原序累积、不去重不排序、空输入
  → []、非 dict 元素各产一条后继续；不可迭代入参 TypeError **原样传播**——不得捕获、
  吞掉、转为消息列表或返回部分结果（异常文本不冻结，冻结传播语义）。〔测试：
  test_items_v3_accumulates_in_input_order_without_dedup、
  test_items_v3_non_iterable_propagates_typeerror〕
- I13 **纯函数性**：不改入参（含嵌套 dict/list）；同输入同输出；模块级常量不被调用
  污染。〔测试：test_purity_inputs_not_modified_and_repeatable〕

## 5. 确定性与随机性

- 两个公开函数均为纯函数：输出只依赖入参值；禁止 `random`、hash 序、系统时钟、
  环境读取、任何 IO。
- 错误消息中嵌入的违规值一律经 `repr` 渲染（str 值带引号：`'nope'`；非 str 值如
  `42`/`None` 同其 repr——CPython 3.12 x64 下逐位确定）；消息前缀中的 id 经
  f-string 字面渲染（不带引号）。
- §3.2 的消息全等断言与 §4 各条是逐位比对点。

## 6. 错误行为

| 输入情形 | 必须的行为 | 证据 |
|---|---|---|
| `validate_item_v3`，任意输入（含恶劣电池） | **不抛异常**，返回 0..n 条 str 消息 | 【测试：test_never_raises_battery、test_non_dict_items】 |
| `validate_items_v3`，入参可迭代 | 不抛异常，逐元素按 §3.2 处理 | 【测试：test_items_v3_*】 |
| `validate_items_v3`，入参**不可迭代**（int/None 等） | **TypeError 原样传播**——不捕获、不转消息、不返回部分结果 | 【测试：test_items_v3_non_iterable_propagates_typeerror】 |
| 非 dict 元素 / 键缺失 | `item is not a dict` 一条后继续（bank）；规则按"键存在才评估、缺失不报"逐条冻结 | 【测试：test_items_v3_*、§3.2 规则表】 |
| 未知键（含全部 v2 字段） | 忽略（§1 分层边界） | 【测试：test_no_v3_fields_passes、test_boundary_with_v2_fields_is_layered】 |
| 结构门未过（rubric 非 dict/键错；条目/维度/级别形状错） | 一条形状消息，该结构**内部**的子检查跳过（消息序其余部分照常） | 【测试：test_rubric_structure_rules、test_rubric_dimension_and_level_rules、test_scoring_point_entry_rules】 |

错误经消息通道上报。**本模块不抛异常**的精确范围：`validate_item_v3` 对任意输入；
`validate_items_v3` 对可迭代入参——不可迭代入参的 TypeError 传播（I12）是唯一例外。

## 7. 非目标

- **不改冻结模块**：itembank_v2（及 v1 itembank）保持现状；本模块不 import 它、
  不重复其逻辑、不代理其校验（§1 边界）。
- **不管 v1/v2 字段**（item_type/stem/answer/kps/difficulty/source/source_ref/
  verification…）：仍由冻结模块 itembank.py / itembank_v2.py 校验；对同一 item 的
  完整校验由调用方分层拼接。
- **不做判分/变体匹配**：acceptable_variants/scoring_points/rubric 的**使用**（判分、
  给分、LLM 复验比对）属 grading 等下游模块；本模块只校验声明结构的完整性。
- **不验证教材出处真实性**：textbook_ref 只校验格式，不查出版社代码表、不验证
  册章存在性。
- **不归一化、不修复**：不 strip 用户值、不自动去重、不产出修复建议；消息字符串
  列表即终点，无 report dataclass。
- **不扩展评分表语义**：各维 max_score 之和与 total 的关系只做精确相等校验，不
  按维度/级别做任何加权重算。
