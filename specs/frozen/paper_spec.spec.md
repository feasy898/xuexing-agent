# paper_spec 模块规格（冻结契约）

> 本文档是唯一权威契约。任何实现（参考实现或重生成实例）只要通过 tests/contract/ 全部测试
> 且满足本文全部条款，即为合格实现。实现算法自由，行为不允许偏离。
>
> **版本**：冻结 v1。标注「〔测试裁定〕」的行为由 `tests/contract/test_paper_spec_contract.py`
> 直接断言（下文简写为 `test:<测试名>`）；本文全部数值例子均为实测值（参考实现
> `src/xuexing/paper_spec.py` + 上述契约测试，2026-10-02 冻结会话实测，CPython 3.12.10
> x64 / Windows）。

## 1. 目的

paper_spec 是**卷型定义与校验**的确定性内核：把"一张卷子的规格"从散落各处的调用
参数收敛为一份可校验、可序列化的声明式 dict——科目/学段/用途/时长/总分 + 若干
**大题**（section：标题、题型形态、题数、每题分值，可选难度带与知识点范围），并在
装载时机器强制其闭合性；随后把已选出的题 id 序列按大题顺序**装订**成带小题号/分值/
大题结构的卷面骨架，供组卷、排版与判分管线消费。

- **它不是组卷器**：题的选择属 paper / blueprint 等模块；本模块只消费"已经选好的
  题 id 序列"，按规格装订。
- **它不是排版器**：打印友好 JSON 属冻结模块 paper_layout（消费 `paper.generate_paper`
  的 Paper 对象）；本模块面向规格声明与装订骨架，不渲染、不分页。
- **它不是判分器**：骨架中的分值只是规格回声，不对任何作答计分。

模块为纯函数：无 IO、无随机、无时钟、不读环境、无全局可变状态；不改任何入参。
唯一异常类型是 `PaperSpecError`（ValueError 直接子类），全部校验失败都经它上报。

## 2. 允许的依赖与装载约束

- Python 标准库，逐个列出：`math`（`isfinite` 数字门）、`dataclasses`（`dataclass`）
- **零 xuexing 依赖**：不需要 `xuexing.types`（PaperSpec/SectionSpec 在本模块内
  定义并冻结，types.py 不动）；禁止 import 任何其他 xuexing 模块
- 禁止：第三方库、文件/网络 IO、`random`、系统时钟、环境读取、全局可变状态

**注入装载约束**：重生成实例由测试夹具按单文件以 importlib 装载为顶层模块名
`_regen_paper_spec` 并顶替 `sys.modules["xuexing.paper_spec"]`
（tests/conftest.py:22-34），不经过包 `__init__`。因此**不使用**
`from __future__ import annotations`（注解直接写真实对象）、**不使用相对导入**
（顶层名装载时失败）。

**数字门（全文适用）**：凡要求"数"处一律指 `isinstance(v, (int, float)) and not
isinstance(v, bool) and math.isfinite(v)`（bool 是 int 子类按非数拒绝；NaN/inf 同拒）；
凡要求"int"处指 `isinstance(v, int) and not isinstance(v, bool)`；凡要求"非空白 str"
处指 `isinstance(v, str) and v.strip() != ""`。

输入表面：`load_spec` 吃 dict（JSON 反序列化产物）；`score_blueprint` 吃
`PaperSpec` + 题 id 序列（list/tuple）。

## 3. 公开 API

模块必须暴露以下 5 个名字（契约测试 `from xuexing.paper_spec import (PaperSpec,
PaperSpecError, SectionSpec, load_spec, score_blueprint)`）。

### 3.1 异常与数据类

```python
class PaperSpecError(ValueError): ...        # 本模块唯一校验异常类型

@dataclass(frozen=True)
class SectionSpec:
    title: str
    form: str
    count: int
    points_each: float                        # 实际接受 int|float
    difficulty_band: tuple | None = None      # 装载时固化为 (lo, hi) 二元 tuple
    kp_scope: tuple | None = None             # 装载时固化为 str tuple

@dataclass(frozen=True)
class PaperSpec:
    subject: str
    stage: str
    usage: str
    duration_min: int
    total_points: float                       # 实际接受 int|float
    sections: tuple                           # SectionSpec tuple，保序
```

两个数据类均 frozen（不可变快照，防调用方事后改动泄漏进卷型）；`difficulty_band`/
`kp_scope`/`sections` 在装载时由入参 list **固化为 tuple**——与入参容器不别名
（改动入参不影响已构造的卷型）。〔测试：test_load_spec_purity、
test_load_spec_optional_section_fields_and_unknown_keys_ignored〕

### 3.2 `load_spec`

```python
def load_spec(data) -> PaperSpec
```

dict -> PaperSpec。校验顺序 V0→V8 冻结；**先累积全部违规消息、一次抛尽**（`"; "`
连接），全部通过才构造返回。任一条失败抛 `PaperSpecError`。

| # | 条件（违反则记消息） | 错误消息（精确格式） |
|---|---|---|
| V0 | data 非 dict（**单独即抛**，不累积） | `spec must be a dict, got {data!r}` |
| V1 | `subject` 缺失/非非空白 str | `spec.subject must be a non-blank str, got {v!r}` |
| V2 | `stage` 缺失/非非空白 str | `spec.stage must be a non-blank str, got {v!r}` |
| V3 | `usage` 缺失/非非空白 str | `spec.usage must be a non-blank str, got {v!r}` |
| V4 | `duration_min` 非 int（bool 拒）或 ≤ 0 | `spec.duration_min must be an int > 0, got {v!r}` |
| V5 | `total_points` 非"有限实数"或 ≤ 0 | `spec.total_points must be a number > 0, got {v!r}` |
| V6 | `sections` 缺失/非 list/空 list | `spec.sections must be a non-empty list, got {v!r}` |
| V7 | 逐节 i（1 起节号入消息）：节非 dict | `spec.sections[{i}] must be a dict, got {v!r}` |
| V7-t | 节 `title` 非非空白 str | `spec.sections[{i}].title must be a non-blank str, got {v!r}` |
| V7-f | 节 `form` 非非空白 str | `spec.sections[{i}].form must be a non-blank str, got {v!r}` |
| V7-c | 节 `count` 非 int（bool 拒）或 < 1 | `spec.sections[{i}].count must be an int >= 1, got {v!r}` |
| V7-p | 节 `points_each` 非"有限实数"或 ≤ 0 | `spec.sections[{i}].points_each must be a number > 0, got {v!r}` |
| V7-d | 节 `difficulty_band` 键存在但非 list/tuple、长度非 2、元素非数、或 ¬(0 ≤ lo ≤ hi ≤ 1) | `spec.sections[{i}].difficulty_band must be a pair of numbers with 0 <= lo <= hi <= 1, got {v!r}` |
| V7-k | 节 `kp_scope` 键存在但非非空 list、或含非非空白 str 元素 | `spec.sections[{i}].kp_scope must be a non-empty list of non-blank str, got {v!r}` |
| V8 | **门控**：仅当 sections 为非空 list 且每节 count/points_each 均合法时，评估 Σ(count×points_each) 与 total_points 的**精确相等** | `spec sections points sum {sum!r} != total_points {total!r}` |

字段缺失一律落入对应类型门（消息中 `got None`），不设"missing"专属消息。节内
**多余键一律忽略**（前向兼容，与冻结模块 paper_layout 的节 dict 语义一致）；
`difficulty_band`/`kp_scope` 键缺省不报。〔测试：
test_required_str_fields、test_duration_min_rules、test_total_points_rules、
test_sections_non_empty_list、test_section_field_rules、test_difficulty_band_rules、
test_kp_scope_rules、test_points_sum_must_equal_total、
test_load_spec_optional_section_fields_and_unknown_keys_ignored〕

实测探针（与契约测试逐字对应）：

- 合法夹具（math/grade7/diagnostic/60 分钟/10 分；选择题 4×1 + 解答题 2×3）→
  PaperSpec，sections 为 2 元 SectionSpec tuple，可选字段为 None
  〔test_load_spec_valid_minimal〕
- 多违规一次报尽：`{"subject": "", "stage": 7, "duration_min": 0, "sections": []}` →
  单条 PaperSpecError 含四条子消息；且空 sections 时**不**叠加无意义的分和消息
  〔test_errors_accumulated_then_raised〕
- `total_points=11`（分和 10）→ `spec sections points sum 10 != total_points 11`
  〔test_points_sum_must_equal_total〕

### 3.3 `score_blueprint`

```python
def score_blueprint(spec, paper_item_ids) -> dict
```

PaperSpec + 题 id 序列 -> 卷面骨架 dict。**装订闭式**：大题按 sections 顺序编号
（`section_no` 从 1 起）；第 i 大题依次消费其 `count` 个题 id；**小题号
`question_no` 全卷连续**从 1 起；每题分值恒为该大题 `points_each`；大题分值
`section_points = count × points_each`；卷面 `question_count` = Σcount。spec 中该节
设置了可选字段时，骨架以**拷贝**回显（`difficulty_band` → list、`kp_scope` → list；
未设置则不回显该键）。

错误时机（均抛 PaperSpecError，按序门控）：spec 非 PaperSpec 实例；序列非 list/tuple
（str/set/int/None 同拒）；元素非 strip 后非空的 str（首个坏元素即抛）；题数与 Σcount
**不相等**（不足/超出分别报，方向区分消息）。

返回顶层 dict，键集合恰为（test:test_score_blueprint_basic_binding）：

```python
{
  "subject": ..., "stage": ..., "usage": ...,       # spec 原值回声
  "duration_min": ..., "total_points": ...,
  "question_count": <Σcount>,
  "sections": [
    {
      "section_no": <1 起大题号>,
      "title": ..., "form": ..., "count": ..., "points_each": ...,
      "section_points": <count × points_each>,
      "questions": [
        {"question_no": <全卷连续小题号>, "item_id": <该次消费的题 id>, "points": <points_each>},
        ...  # 恰 count 条，按消费序
      ],
      "difficulty_band": [lo, hi],   # 仅当 spec 中该节设置（拷贝，非 tuple）
      "kp_scope": [...],             # 仅当 spec 中该节设置（拷贝）
    }, ...
  ],
}
```

section 块键集合恰为上列 7 键 + 设置了才有的可选回显键；question 块键集合恰为
`{"question_no", "item_id", "points"}`。

实测探针（与契约测试逐字对应）：

- 夹具（§3.2）+ `["q1".."q6"]` → `question_count=6`；两节 section_no 1/2；
  小题号 `[1..6]`、item_id `["q1".."q6"]`、分值 `[1,1,1,1,3,3]`；section_points
  4 + 6 == total_points 10；未设置可选字段的节无 `difficulty_band`/`kp_scope` 键
  〔test_score_blueprint_basic_binding〕
- 5 个 id → `paper_item_ids too few: need 6, got 5`；7 个 → `too many: need 6, got 7`
  〔test_score_blueprint_count_mismatch_raises〕
- 同一 id 重复出现按出现次数分别编号（不去重）〔test_score_blueprint_item_id_surface〕

## 4. 不变量（编号列出；全部可被契约测试检验）

- I1 **异常类型**：`PaperSpecError` 是 ValueError 的**直接子类**，是本模块唯一校验
  异常类型。〔测试：test_paper_spec_error_is_value_error〕
- I2 **数据类冻结与快照**：PaperSpec/SectionSpec 为 frozen dataclass；sections 为
  tuple、difficulty_band/kp_scope 装载时固化为 tuple——与入参容器不别名（事后改动
  入参不影响 spec）。〔测试：test_load_spec_purity、
  test_load_spec_optional_section_fields_and_unknown_keys_ignored〕
- I3 **装载校验闭式**：§3.2 规则表 V0→V8 逐条；`subject`/`stage`/`usage` 非空白 str；
  `duration_min` int > 0（bool 拒）；`total_points` 数 > 0；`sections` 非空 list；每节
  `form`/`title` 非空白 str、`count` int ≥ 1（bool 拒）、`points_each` 数 > 0；
  `difficulty_band` 为 0 ≤ lo ≤ hi ≤ 1 的二元数对、`kp_scope` 为非空非空白 str list；
  **Σcount×points_each 与 total_points 精确相等**。〔测试：§3.2 各规则条〕
- I4 **一次报尽**：load_spec 先累积全部违规再以单条 PaperSpecError 抛出（`"; "`
  连接），非首个即停；空 sections 不叠加分和消息。〔测试：
  test_errors_accumulated_then_raised〕
- I5 **多余键忽略**：顶层与节级未知键一律忽略（前向兼容）；可选字段键缺省不报。
  〔测试：test_load_spec_optional_section_fields_and_unknown_keys_ignored〕
- I6 **装订闭式**：section_no 1 起按节序；小题号全卷连续 1..N；题序 = 节序 × 节内
  消费序；每题分值 = 该节 points_each；section_points = count × points_each；Σ
  section_points == Σ小题分值 == total_points。〔测试：
  test_score_blueprint_basic_binding、test_score_blueprint_single_section_multi_count〕
- I7 **可选回显为拷贝**：spec 中设置了的 difficulty_band/kp_scope 在骨架中以 list
  拷贝回显（改输出不污染 spec）；未设置则不出现该键。〔测试：
  test_score_blueprint_echoes_optional_fields_as_fresh_copies〕
- I8 **题数门**：题 id 数 ≠ Σcount 即抛（不足/超出方向区分消息）；元素非非空白 str
  即抛；序列表面只吃 list/tuple；spec 非 PaperSpec 实例即抛。〔测试：
  test_score_blueprint_count_mismatch_raises、test_score_blueprint_item_id_surface、
  test_score_blueprint_spec_type_gate〕
- I9 **顶层形状封闭**：顶层 7 键、section 块 7 键（+设置了才有的回显键）、question
  块 3 键，恰如 §3.3。〔测试：test_score_blueprint_basic_binding〕
- I10 **纯函数性与确定性**：不改 spec 与 paper_item_ids（深照相机比对）；同输入同
  输出；输出全量 JSON 可序列化且 `json.dumps(..., sort_keys=True)` 逐位可复现；改
  输出不影响 spec 与后续调用。〔测试：test_score_blueprint_purity_and_determinism〕
- I11 **不重校验**：score_blueprint 信任 PaperSpec 实例（load_spec 是唯一装载门），
  不重复 §3.2 的字段校验；其唯一自校验是题数门（I8）。〔测试：
  test_score_blueprint_spec_type_gate〕

## 5. 确定性与随机性

- 三个公开函数（load_spec / score_blueprint 及数据类构造）均为纯函数：输出只依赖
  入参值；禁止 `random`、系统时钟、环境读取、任何 IO、hash 序依赖（全部顺序来自
  入参序列）。
- dict 构造序固定；`json.dumps(blueprint, ensure_ascii=False, sort_keys=True)`
  逐位可复现。
- 本模块**没有** seed/时间戳豁免：同输入字节级同输出。

## 6. 错误行为

| 输入情形 | 必须的行为 | 证据 |
|---|---|---|
| `load_spec`，data 非 dict | 单独即抛 PaperSpecError（不累积） | 【测试：test_non_dict_spec_rejected】 |
| `load_spec`，任一字段违规 | 累积全部消息后单条 PaperSpecError（`"; "` 连接） | 【测试：test_errors_accumulated_then_raised】 |
| `load_spec`，合法 dict | 返回 PaperSpec；不改入参；可选 list 入参固化为 tuple | 【测试：test_load_spec_valid_minimal、test_load_spec_purity】 |
| `load_spec`，sections 非空 list 但某节字段非法 | V8 分和门**跳过**（不叠加分和消息，只报节级错） | 【测试：test_points_sum_must_equal_total】 |
| `score_blueprint`，spec 非 PaperSpec / 序列非 list/tuple / 元素非非空白 str | PaperSpecError（按 S 序门控，首个坏元素即抛） | 【测试：test_score_blueprint_spec_type_gate、test_score_blueprint_item_id_surface】 |
| `score_blueprint`，题数 ≠ Σcount | PaperSpecError（`too few` / `too many` 消息区分方向，含 need/got 数值） | 【测试：test_score_blueprint_count_mismatch_raises】 |
| 顶层/节级多余键 | 忽略 | 【测试：test_load_spec_optional_section_fields_and_unknown_keys_ignored】 |

错误消息逐字文本不是契约，但必须含关键标识（非法值 repr / 节号 / need-got 数值）；
契约测试对消息做子串/正则匹配（见各条）。

## 7. 非目标

- **不组卷**：题的选择、难度/知识点约束的满足属 paper / blueprint；本模块只装订
  已选出的题 id 序列。
- **不排版**：不分页、不渲染选项/页眉页脚/留白（paper_layout 的职责）；输出止于
  卷面骨架 dict。
- **不判分**：骨架中的 points 只是规格回声；评分量表使用属 grading 下游。
- **不改其他模块**：types.py 的 Paper / Item、paper.py、paper_layout.py 均保持现状；
  PaperSpec/SectionSpec 在本模块内定义，不进 types.py。
- **不查题库**：不验证 paper_item_ids 对应的题是否存在、题型是否匹配 section.form
  （form 一致性由组卷侧保证；本模块只校验 id 表面形状与题数）。
- **不归一化、不修复**：不 strip 用户值、不自动调总分、不产出修复建议。
- **不承诺跨实现字节一致的错误消息文本**：须含关键标识（§6），逐字文本不是契约。
