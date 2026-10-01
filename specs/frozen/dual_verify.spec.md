# dual_verify 模块规格（冻结契约）

> 本文档是唯一权威契约。任何实现（参考实现或重生成实例）只要通过 tests/contract/ 全部测试
> 且满足本文全部条款，即为合格实现。实现算法自由，行为不允许偏离。
>
> **版本**：定稿 v1（契约第三波冻结）。标注「〔测试裁定〕」的行为由
> `tests/contract/test_dual_verify_contract.py`（18 项）直接断言；标注「〔参考裁定〕」的行为
> 契约测试未仲裁，按参考实现 `src/xuexing/dual_verify.py` 冻结并在当地注明本冻结轮的实测
> 探针（探针脚本 `.tmp_review_checks/dv_freeze_probe*.py`，2026-10-02，CPython 3.12.10 x64）。
> 本文自包含：不引用仓库内其他规格文档；全部常量、规则表、裁决次序在本文内完整定义。
>
> 冻结基线：参考实现 + 契约测试全量实测于 2026-10-02，CPython 3.12.10 x64 / pytest 9.1.1
> （`python -m pytest tests/contract/test_dual_verify_contract.py -q` → **18 passed**）。

## 1. 目的

dual_verify 是 BACKLOG P2「双代理独立复验题库」的确定性内核：多个代理对同一题给出独立
答案，本模块把「标答 vs 各代理提案」的 verification 级等值比对（归一化、choice 选项解析、
数值等价、单位门、多答案集合无序等值、赋值前缀剥离、字面兜底）折叠成**单题三值裁决**——
`agree`（≥2 个 match 且零 mismatch，产出 verification 记录供回填）/ `disagree`（有具体
提案与标答不符，转人工仲裁，不得回填）/ `incomplete`（证据不足，诚实缺口，不得回填）；
并提供 itembank_v2 合法形状的记录构造、纯回填、全库裁决报告（`DualVerifyReport`）与人工
仲裁队列行。行为契约：**比对规则表可手算复核**（R1–R5，与 grading 判分语义对齐）、
**裁决可解释**（任一 mismatch 压倒 match 多数——分歧即仲裁，不因第三人一致而回填）、
**回填诚实**（只回填 agree）、**顺序闭式**（bank 级输出顺序 = items 输入原序，记录与
statuses 内代理 id 按码点升序）、**同输入同输出**。与 grading / itembank_v2 的行为
一致性由契约测试跨模块断言，实现之间零 import。

## 2. 允许的依赖与装载约束

- Python 标准库，逐个限定：`re`、`dataclasses`（**不得引入其他标准库模块**——参考实现
  仅此两个 import）
- `xuexing.types`：**不使用**（0 个类型。本模块不 import `xuexing.types`，也不 import
  任何其他 xuexing 模块）
- 禁止：其他 xuexing 模块（**无例外**——契约测试可 `import xuexing.grading` /
  `xuexing.itembank_v2` 做跨模块断言，实现不可）、第三方库、文件/网络 IO、全局可变
  状态、随机、系统时钟、环境读取
- 无注入对象：全部入参为内建 dict/list/str/可迭代对象；`verify_bank` /
  `arbitration_rows` 的 `items` 元素只读 `item["id"]`、`item["answer"]`、`item["item_type"]`、
  `item.get("options")`（其余键不触碰）

重生成实例的装载约束（自包含实测，2026-10-02，CPython 3.12.10；注入机制：
`tests/conftest.py:22-34` 以顶层模块名 `_regen_dual_verify` 经 `spec_from_file_location`
装载 `<impl_dir>/dual_verify.py` 并顶替 `sys.modules["xuexing.dual_verify"]`）：

- **禁止相对导入**（`from .types import ...` 等）：实测在 `exec_module` 处抛
  `ImportError: attempted relative import with no known parent package`（探针 Q10）。
- **禁止 `from __future__ import annotations`**：实测在 frozen dataclass 处理阶段抛
  `AttributeError: 'NoneType' object has no attribute '__dict__'`——dataclasses 按
  `sys.modules.get(cls.__module__)` 解析字符串注解时，注入注册名是 `xuexing.dual_verify`
  而 dataclass 的 `__module__` 是 `_regen_dual_verify`，`.get` 得 None（探针 Q9）。
  注解直接写真实对象（`tuple`、`dict`、`str | None` 等）。
- **绝对导入 + 真实对象注解实测可装载**：含全部 15 个公开名字的模块经注入门装载后契约
  测试可正常运行。

## 3. 公开 API

模块必须暴露以下 15 个名字（契约测试以 `from xuexing.dual_verify import ...` 导入，
与参考实现 `__all__` 一致）：`DualVerifyError`、`COMPARISON_TOLERANCE`、`UNIT_ALIASES`、
`VERDICT_AGREE`、`VERDICT_DISAGREE`、`VERDICT_INCOMPLETE`、`normalize_answer`、
`answers_match`、`verify_item`、`verification_record`、`make_record`、`backfill_item`、
`verify_bank`、`arbitration_rows`、`DualVerifyReport`。

### 3.1 常量与异常

- `DualVerifyError(ValueError)`：本模块唯一异常类型（ValueError **直接**子类）；
  契约测试以 `pytest.raises(DualVerifyError)` 断言。〔测试裁定〕
- `COMPARISON_TOLERANCE = 1e-9`：数值等值相对容差，恒有
  `COMPARISON_TOLERANCE == grading.GRADE_TOLERANCE == 1e-9`（跨模块断言）。〔测试裁定
  `test_schema_constants`〕
- `UNIT_ALIASES: dict[str, str]`：单位别名表，键为表层写法（含规范形自身），值为规范
  单位；恒与 `grading.UNIT_ALIASES` **逐键逐值相等**（跨模块断言）。〔测试裁定〕冻结内容
  （28 表层写法 → 23 规范单位）：

  | 规范单位 | 表层写法 |
  |---|---|
  | 千米 | 千米、公里 |
  | 米 / 厘米 / 毫米 | 各自同名 |
  | 平方千米 | 平方千米、平方公里 |
  | 平方米 / 平方分米 / 平方厘米 | 各自同名 |
  | 立方米 / 立方分米 / 立方厘米 | 各自同名 |
  | 公顷 | 公顷 |
  | 吨 / 克 | 各自同名 |
  | 千克 | 千克、公斤 |
  | 元 / 角 / 分 | 各自同名 |
  | 升 / 毫升 | 各自同名 |
  | 小时 | 小时、时 |
  | 分（时间） | 分钟 |
  | 秒 / 度 | 各自同名 |

  表中没有裸的「分米」（只有 平方分米 / 立方分米）。规范形自映射（`UNIT_ALIASES[canon] ==
  canon`）。**只归一别名、不做任何数值换算**（I3 的单位门）。
- `VERDICT_AGREE = "agree"`、`VERDICT_DISAGREE = "disagree"`、
  `VERDICT_INCOMPLETE = "incomplete"`：三值裁决字面。〔测试裁定
  `test_schema_constants`〕
- 裁决状态字面：`"match"` / `"mismatch"` / `"no_answer"`（`verify_item` 返回的 statuses
  元组第二元组，测试逐字断言）。这三个**字面值**属冻结面；暴露它们的常量名（参考实现的
  `ST_MATCH` 等）不在 `__all__`、契约测试不导入，**不属冻结面**——实现可用私有常量或字面量。
- 最长单位后缀长 `= max(len(k) for k in UNIT_ALIASES) = 4`（如 平方公里）；单位剥离按
  后缀宽度 4→1 **最长优先**。〔参考裁定，与参考实现 `_MAX_UNIT_LEN` 一致〕

### 3.2 `normalize_answer(text: str) -> str` —— 归一化规则表 N1–N5

输入必须为 `str`；非 str（None/bool/int/float/list…）→ `DualVerifyError`。〔测试裁定
`test_normalize_rejects_non_str`〕五条规则**按序**执行，与 grading 同语义：

- **N1 全角折叠**：码点 ∈ `[0xFF01, 0xFF5E]` 的字符映射为 `chr(ord(c) − 0xFEE0)`
  （`３`→`3`、`－`→`-`、`，`→`,`、`！`→`!`、`Ａ`→`a`……大小写最终由 N5 统一）；
  `U+3000` 全角空格 → 半角空格。其余原样保留（`。`、`、`、`√`、`∠`、`₁`、`°` 等不在
  折叠范围）。
- **N2 空白折叠**：内部空白串（`\s+` 语义）折叠为单个半角空格，再去首尾空白。
- **N3 尾部剥离**：从右端循环删除 `{'。', '、', ',', '.', ';', '!', '?'}` 及空白字符
  （只剥尾部、不动内部；`"3或7。"`→`"3或7"`、`"　全程　。"`→`"全程"`）。
- **N4 千分位逗号删除**：删除所有「左侧是 ASCII 数字 `0-9`、右侧恰为 3 位 ASCII 数字
  （第 4 位仍是数字则不算）」的逗号（`"1,234"`→`"1234"`；保留坐标 `"(4,1)"`、
  `"12,34"`、`"1,2345"`）。
- **N5 小写化**：`str.lower()`。

本函数与 `grading.normalize_answer` 在规则表上完全一致：契约测试以 13 例电池逐条断言
相等（`"－３００元"、"２X"、"  a   b  "、"1,234"、"（4,1）"、"X>2"、"3或7。"、"ＹＥＳ！"、
"0.50"、"√2"、"ＡＢＣ，ＤＥＦ；１２３"、""、`"　全程　。"`）。〔测试裁定
`test_normalize_matches_grading_on_battery`〕实测输出值（参考实现，2026-10-02）：
`"－３００元"`→`"-300元"`、`"２X"`→`"2x"`、`"1,234"`→`"1234"`、`"X>2"`→`"x>2"`、
`"ＹＥＳ！"`→`"yes"`、`""`→`""`、`"　全程　。"`→`"全程"`。〔参考裁定：测试只断言与
grading 相等，字面输出值由参考实现实测冻结；另以 20000 例随机串对拍
`normalize_answer` vs `grading.normalize_answer` → 0 差异（探针 Q8）〕

### 3.3 `answers_match(key_answer, proposed, item_type="fill", options=None) -> bool`

verification 级标答-提案等值判定。

**校验次序（绑定）**：`key_answer` 非 str → `DualVerifyError`；`proposed` 非 str →
`DualVerifyError`；`item_type` 不在 `("choice", "fill", "solve")` → `DualVerifyError`；
`item_type == "choice"` 时 `options` 非 `list` 或 `len(options) < 2` → `DualVerifyError`
（`options=None` 亦抛）。〔测试裁定 `test_match_input_guards`：`answers_match(42, "2")`、
`answers_match("2", None)`、`answers_match("2", "2", item_type="proof")`、
`answers_match("B", "B", item_type="choice", options=["A. 1"])`、
`answers_match("B", "B", item_type="choice", options=None)` 均抛 `DualVerifyError`〕

**item_type == "choice"（规则 R2）**：

1. `texts = [normalize_answer(o) for o in options]`（元素非 str 在此抛 `DualVerifyError`，
   探针 P10）；
2. `labels = [t.split(".", 1)[0].strip() for t in texts]`（全角句点已被 N1 折叠，同样切分；
   无句点选项的整个归一化文本即标签）；
3. `correct = resolve(normalize_answer(key_answer), labels, texts)`；
   `given = resolve(normalize_answer(proposed), labels, texts)`；
   返回 `correct is not None and correct == given`。
4. `resolve(target, labels, texts)` 两趟全局扫描：**标签趟**——`target` 直接等于
   （`==`，非去空白键）某 label 的最小下标，命中即止；**全文趟**——仅当标签趟未命中，
   `_key(target)` 等于 `_key(texts[i])` 的最小下标 i；两趟都不中 → `None`。
   **标签优先于全文**：即使全文趟能在更小下标命中，也以标签趟结果为准。

**item_type ∈ ("fill", "solve")（规则 R1 → R4 → R5，次序为绑定条款）**：

- **R1 全串归一化等值**：`normalize_answer(key_answer) == normalize_answer(proposed)`
  → True；
- **R4 多答案集合等值**：否则把**原始文本**按全角分隔符 `或|和|、|；|，` 拆成分量
  （ASCII 逗号不拆——坐标 `"(4,1)"` 不受伤），逐分量归一化并剥赋值前缀，做**多重集
  配对**：分量数相等且 `list_a` 每个分量都能在剩余分量中按 first-fit 找到
  component-match → True；数量不等直接 False；
- **R5 字面兜底**：否则 `_key(normalize_answer(key_answer)) ==
  _key(normalize_answer(proposed))`（`_key` = 归一化后删除全部空白，`"2√2+3"` 与
  `"2√2 + 3"` 因此等值）。

**component match（单分量比对，R3，输入均为已归一化文本）**：

1. **单位门**：对两分量各做尾部单位剥离（后缀宽度 4→1 最长优先命中 `UNIT_ALIASES`；
   命中后剩余部 strip 非空 → `(剩余部, 规范单位)`；纯单位词/无命中 → `(原文, None)`）。
   归一单位不等（含一方 None）→ **False**（缺单位、异单位判错；`None == None` 通过；
   别名写法归一到同一规范单位后判等）。
2. 双方数值解析皆成功 → **数值等价**：`abs(a−b) <= COMPARISON_TOLERANCE *
   max(1.0, |a|, |b|)`。
3. 否则 → **字面相等**：`_key` 去空白后相等。

**数值解析文法（ASCII `[0-9]`，全文锚定；与 grading 同）**：按序——百分数（`%` 结尾，
剥 `%` 再 `strip()` 后按下面三条解析，值 ÷100）；带分数 `[+-]?[0-9]+ [0-9]+/[0-9]+`
（整数部与分数部之间恰一个空格；符号取整数部、作用于整体，`"-1 1/2"`→−1.5）；
分数 `[+-]?[0-9]+/[0-9]+`；小数（含 `.5`、`3.`、`1e3`）。分母 0 → 不可解析（None）；
`nan`/`inf`/unicode 数字不匹配文法 → None。

**赋值前缀剥离**（R4 的分量级前处理）：分量归一化文本中，首个 `=` 之前由
「ASCII 字母 / 希腊字母 `U+0370–U+03FF` / `∠`(U+2220) / 下标数字 `U+2080–U+2089` /
上标 `¹²³` / 撇号 `'′`」组成且**总长 ≤6**、`=` 后**至少 1 字符**时剥去该前缀
（`x=5`→`5`、`x₁=7`→`7`、`AB=1`→`1`、`a'b=1`→`1`；`abcdefg=1` 超 6 字符不剥、
`x=` 无后继不剥、`x+y=1` 含 `+` 不剥）。

**choice 未解析不抛错**：`correct is None`（标答无法匹配任何选项的标签/全文）→ 返回
`False`，不抛异常。〔参考裁定，探针 P1：`answers_match("E", "B", item_type="choice",
options=["A. 1","B. 2"])` → `False`；对比 grading 对不可解析标答抛 `GradingError`——
本模块选择「判 False」，契约测试未覆盖此输入对〕

**fill/solve 忽略 `options`**：`item_type ∈ ("fill","solve")` 时 `options` 入参不校验、
不使用（传 `options=42` 也不抛错，探针 P2）。〔参考裁定，契约测试未覆盖〕

**测试裁定的行为表**（options 缺省为 `["A. 1","B. 2","C. 3","D. 4"]` 的标注 `choice`；全部
来自 `test_match_*`）：

| 调用 | 结果 |
|---|---|
| `answers_match("左", "左")` | `True` |
| `answers_match("左", "右")` | `False` |
| `answers_match("25.25", "25.25")` | `True` |
| `answers_match("1/2", "0.5")` | `True`；`answers_match("50%", "1/2")` | `True` |
| `answers_match("1/3", "0.33")` | `False` |
| `answers_match("-300元", "-300元")` | `True` |
| `answers_match("-300元", "-300")` | `False`（单位门：key 带单位、提案缺单位） |
| `answers_match("80平方厘米", "80平方厘米")` | `True` |
| `answers_match("80平方厘米", "80厘米")` | `False`（异单位，无换算） |
| `answers_match("B", "B", item_type="choice", options=opts)` | `True` |
| `answers_match("B. 2", "B", item_type="choice", options=opts)` | `True`（标签优先） |
| `answers_match("B", "b", item_type="choice", options=opts)` | `True`（N5 小写化） |
| `answers_match("A", "B", item_type="choice", options=opts)` | `False` |
| `answers_match("B", "3", item_type="choice", options=opts)` | `False`（`3` 解析不到） |
| `answers_match("3或7", "7或3")` | `True`（多答案无序集合） |
| `answers_match("-2或-8", "-8或-2")` | `True` |
| `answers_match("x=5，y=2", "y=2，x=5")` | `True`（赋值前缀 + 集合） |
| `answers_match("x₁=7或x₂=-1", "x₂=-1或x₁=7")` | `True` |
| `answers_match("16或18", "16或17")` | `False` |
| `answers_match("3或7", "3")` | `False`（数量不等） |
| `answers_match("(4,1)", "(4,1)")` | `True`（ASCII 逗号不拆） |
| `answers_match("(-1,0)和(3,0)", "(3,0)和(-1,0)")` | `True` |
| `answers_match("x>2", "x>2")` | `True`；`answers_match("x>2", "x≥2")` | `False` |
| `answers_match("3.5×10^6", "3.5×10^6")` | `True` |
| `answers_match("2√2+3", "2√2 + 3")` | `True`（R5 空白不敏感兜底） |
| `answers_match("1:3", "1/3")` | `False`（比号不与分数互化） |

补充实测（参考裁定，探针 P5/P23）：`answers_match("x=5", "5")` → `True`（单分量也剥
赋值前缀）；`answers_match("1,234或2,345", "1234或2345")` → `True`（N4 作用于分量）。

### 3.4 `verify_item(item, agent_answers) -> dict`

单题双代理裁决。返回**新构造**的 JSON 形 dict：
`{"item_id": item_id, "verdict": verdict, "statuses": ((agent_id, status), ...)}`——
`statuses` 为 tuple of tuple，按 agent id **码点升序**（`sorted(dict)` 语义，`"B" < "a"`）。

**题目侧校验（先于一切裁决，任一不过 → `DualVerifyError`）**〔测试裁定
`test_verify_item_input_guards`〕：

- `item` 非 dict → 抛（`verify_item("not-a-dict", ...)`）；
- `item["id"]`：非 str、或 `!= strip()`（带首尾空白）、或 strip 后为空 → 抛
  （`_fill(id="  ")`、`{"": ...}`）；
- `item["answer"]`：非 str → 抛；`strip()` 后为空 → 抛（`_fill(answer="  ")`）；
- `item["item_type"]` 不在 `("choice","fill","solve")` → 抛（`_fill(item_type="proof")`）；
- `item_type == "choice"` 时 `item["options"]` 非 list 或 len < 2 → 抛
  （`{"id":"c","item_type":"choice","answer":"A"}` 无 options）。

**入参侧校验**：`agent_answers` 非 dict → `DualVerifyError`（`verify_item(_fill(), ["2","2"])`）；
对 `sorted(agent_answers)` 的**每个** agent id：非 str、或带首尾空白、或空 → `DualVerifyError`
（`{" lead": "2"}`、`{"": "2"}`——即使该代理答案本会是 no_answer，id 校验仍先执行）。

**逐代理判定**：`raw = agent_answers[agent_id]`；`raw` 非 str 或 `raw.strip() == ""`
→ `no_answer`（容忍，非错误）；否则
`answers_match(item["answer"], raw, item["item_type"], item.get("options"))` 为
True → `match`，False → `mismatch`。

**三值裁决（次序为绑定条款）**：`n_mismatch ≥ 1` → `VERDICT_DISAGREE`（mismatch 压倒
match 多数）；否则 `n_match ≥ 2` → `VERDICT_AGREE`；否则 `VERDICT_INCOMPLETE`。
`no_answer` 永不产生 mismatch（1 match + 1 缺席 = incomplete 而非分歧）。

**测试裁定的例子**（`item = _fill()` 即 `{"id":"i1","item_type":"fill","answer":"2",...}`，
tests/contract/test_dual_verify_contract.py:148-174）：

- `verify_item(item, {"solver-a": "2", "solver-b": "2"})` →
  `{"item_id": "i1", "verdict": "agree", "statuses": (("solver-a", "match"), ("solver-b", "match"))}`；
- `verify_item(item, {"solver-a": "2", "solver-b": "3"})` → `verdict == "disagree"`、
  `statuses == (("solver-a", "match"), ("solver-b", "mismatch"))`；
- `verify_item(item, {"a": "2", "b": "3", "c": "2"})` → `"disagree"`（第三人一致不回填）；
- `verify_item(item, {"solver-a": "2"})` 与 `verify_item(item, {})` → `"incomplete"`；
- `verify_item(item, {"solver-a": "2", "solver-b": ""})` → `"incomplete"`、
  `statuses == (("solver-a", "match"), ("solver-b", "no_answer"))`；
- `verify_item(item, {"b": absent})` 对 `absent ∈ (None, 42, ["2"], "   ")` →
  `statuses == (("b", "no_answer"),)`；
- choice 题（`_choice()`，options `["A. 1","B. 2","C. 3","D. 4"]`）：
  `{"a": "B", "b": "B. 2"}` → `agree`；`{"a": "B", "b": "C"}` → `disagree`。

### 3.5 `make_record(agent_ids) / verification_record(verify_result) / backfill_item(item, record)`

**`make_record(agent_ids)`**：由代理 id 的**任意可迭代对象**构造 v2 合法记录。逐个经
「非 str / 带首尾空白 / 空 → `DualVerifyError`」清洗，去重，**码点升序**排序，
≥2 个不同 id，返回 `{"agents": [...], "answers_agree": True}`。<2 个不同 id
→ `DualVerifyError`。〔测试裁定 `test_make_record_sorted_dedup_and_floor`〕

- `make_record(["b", "a"]) == {"agents": ["a", "b"], "answers_agree": True}`；
- `make_record(["c", "a", "b", "a"]) == {"agents": ["a", "b", "c"], "answers_agree": True}`；
- `make_record(["z", "a"])` 过 `validate_item_v2(_fill(verification=rec)) == []`；
- `make_record([])` / `(["only-one"])` / `(("x",))` / `(["a", " a"])` 均抛
  `DualVerifyError`。
- 〔参考裁定〕入参可为任意可迭代（实测 set 输入 `make_record({"b","a"})` →
  `{"agents": ["a","b"], "answers_agree": True}`，探针 P18）。

**`verification_record(verify_result)`**：`verify_item` 结果 → v2 记录或 `None`。
入参非 dict 或缺 `"verdict"` 键 → `DualVerifyError`；`verdict != "agree"`
（disagree/incomplete）→ **`None`**（诚实缺口/分歧不回填）；`agree` →
`make_record(所有 status 为 "match" 的 agent id)`。

- 〔测试裁定 `test_record_only_for_agree_and_passes_itembank_v2`〕
  `verification_record(verify_item(_fill(), {"b": "2", "a": "2"}))` →
  `{"agents": ["a", "b"], "answers_agree": True}`，且
  `validate_item_v2(_fill(verification=rec)) == []`；disagree / 单代理 / 空
  `agent_answers` 三种结果一律 `None`。
- 〔参考裁定〕agree 有 ≥3 个 match 时记录含全部匹配代理：
  `verify_item(item, {"c":"2","a":"2","b":"2"})` → 记录 `{"agents": ["a","b","c"], ...}`
  （探针 P15）；`verification_record({"verdict": "agree"})`（无 statuses 的手工 dict）→
  `DualVerifyError`（make_record 下限，探针 P9）。

**`backfill_item(item, record)`**：纯回填。`item` 非 dict → `DualVerifyError`；
`record is None` → 返回 `dict(item)` 副本（**原样、无 `verification` 键、非同一对象**）；
否则先校验 record（非 dict / `agents` 非 list 或 <2 / agents 元素非 str、带首尾空白或空 /
重复 / `answers_agree` 非恰 `True` → `DualVerifyError`），再返回
`out = dict(item); out["verification"] = {"agents": list(record["agents"]), "answers_agree": True}`。
**入参不被修改**；原件无 `verification` 键时该键**追加在末尾**（原键原序）。

- 〔测试裁定 `test_backfill_pure_and_validated`〕`rec = {"agents": ["a","b"], "answers_agree": True}`：
  `out["verification"] == rec`、`list(out)[:-1] == list(item)`、
  `validate_item_v2(out) == []`、`item == snapshot`（deepcopy 快照不变）；
  `backfill_item(item, None) == item` 且无 `"verification"` 键且 `unchanged is not item`；
  `({"agents": ["a"], ...})`、`answers_agree=False`、缺 `answers_agree`、`"yes"`、`42`
  均抛 `DualVerifyError`。
- 〔参考裁定〕item **已有** `verification` 键时按 dict 赋值语义**就地覆盖**（键位置保持
  原处，不移到末尾），探针 P19；契约测试只覆盖「原件无该键 → 追加末尾」形态。

### 3.6 `verify_bank(items, answers_by_item) -> DualVerifyReport` 与 `DualVerifyReport`

**`verify_bank(items, answers_by_item)`**：`answers_by_item` 非 dict → `DualVerifyError`；
按 **items 输入原序**逐题裁决——`verify_item(item, answers_by_item.get(item["id"], {}))`
（**缺条目按空 dict** → 零 match → `incomplete`）。返回 frozen dataclass
`DualVerifyReport`，字段全部 tuple 化：

- `item_ids: tuple` —— 逐题 `result["item_id"]`（原序）；
- `verdicts: tuple` —— `((item_id, verdict), ...)`（原序）；
- `agreed_item_ids` / `disputed_item_ids` / `incomplete_item_ids: tuple` —— 按裁决分桶（各自原序）；
- `records: tuple` —— `((item_id, record_or_None), ...)`（原序；仅 agree 有记录 dict，
  其余 `None`）。

**`DualVerifyReport.counts()`**：返回 `{"agree": n1, "disagree": n2, "incomplete": n3}`
（三键恒在，值为零也保留）；**每次调用返回新 dict**（改一份不影响下次）。

**测试裁定的例子**〔`test_verify_bank_order_and_closed_form`，fixtures：`i1=fill("2")`、
`i2=fill("3或7")`、`i3=choice("B")`、`i4=fill("5")`；`i1:{"a":"2","b":"2"}`、
`i2:{"a":"7或3","b":"3或7"}`、`i3:{"a":"B","b":"C"}`、i4 缺条目〕：

- `report.item_ids == ("i1", "i2", "i3", "i4")`；
- `report.verdicts == (("i1","agree"), ("i2","agree"), ("i3","disagree"), ("i4","incomplete"))`；
- `agreed_item_ids == ("i1","i2")`、`disputed_item_ids == ("i3",)`、
  `incomplete_item_ids == ("i4",)`；
- `report.records == (("i1", {"agents": ["a","b"], "answers_agree": True}), ("i2", 同上), ("i3", None), ("i4", None))`；
- `report.counts() == {"agree": 2, "disagree": 1, "incomplete": 1}`，且
  `fresh = report.counts(); fresh["agree"] = 999` 后再次 `counts()["agree"] == 2`。

### 3.7 `arbitration_rows(items, answers_by_item) -> tuple[dict, ...]`

人工仲裁队列行。`answers_by_item` 非 dict → `DualVerifyError`；按 items 输入原序、
题内按 agent id 码点升序（statuses 已排序），**仅对 `mismatch` 状态的代理**成行；
每行为四键 dict：`{"item_id": ..., "key_answer": item["answer"]（原样）,
"agent": agent_id, "proposed": 该代理原始提案值（原样）}`。无分歧 → 空 tuple `()`。

〔测试裁定 `test_arbitration_rows_shape_and_order`〕：

- 同 §3.6 fixtures → `rows == ({"item_id": "i3", "key_answer": "B", "agent": "b", "proposed": "C"},)`；
- 同题多代理分歧：`arbitration_rows([_fill("x1","5")], {"x1": {"z":"6","a":"4","m":"5"}})` →
  行序 `[("a","4"), ("z","6")]`（m 是 match 不成行；a、z 按 id 升序）；
- 全库无分歧 → `()`。

## 4. 不变量（编号列出，全部可被契约测试检验）

- I1 **常量冻结**：`COMPARISON_TOLERANCE == 1e-9`（且 `== grading.GRADE_TOLERANCE`）；
  `UNIT_ALIASES == grading.UNIT_ALIASES`（逐键逐值）；三裁决常量恰为
  `("agree","disagree","incomplete")`。〔测试裁定 `test_schema_constants`〕
- I2 **归一化对齐 grading**：`normalize_answer` 与 `grading.normalize_answer` 在 13 例
  规则表电池上逐条相等（另实测 20000 例随机串 0 差异，探针 Q8）；非 str 入参抛
  `DualVerifyError`。〔测试裁定 `test_normalize_matches_grading_on_battery`、
  `test_normalize_rejects_non_str`；参考裁定随机对拍〕
- I3 **fill/solve 比对规则闭包（R1/R3/R4/R5）**：全串归一化等值、单位门（缺单位/异单位
  判错、不换算、别名判等）、数值等价闭包（`1/2`≡`0.5`≡`50%`）、多答案无序集合
  （`3或7`≡`7或3`、`x=5，y=2`≡`y=2，x=5`、数量不等判错）、ASCII 逗号不伤坐标
  （`(4,1)`、`(-1,0)和(3,0)`）、字面兜底空白不敏感（`2√2+3`≡`2√2 + 3`）、
  比号不与分数互化（`1:3`≠`1/3`）、`≥` 与 `>` 不等价。〔测试裁定
  `test_match_literal_and_numeric`、`test_match_multianswer_sets_and_prefixes`、
  `test_match_literal_fallback_for_expressions`〕
- I4 **choice 解析确定性（R2）**：两趟扫描（归一化标签直接 `==` 先于全文去空白键、
  各自取最小下标）；标签/大小写/全文形态互判（`B`≡`b`≡`B. 2` 的标签）；解析不到的提案
  判 False；`item_type` 非法、choice `options` 非 list 或 <2 → `DualVerifyError`。
  〔测试裁定 `test_match_choice_labels_and_fulltext`、`test_match_input_guards`〕
- I5 **三值裁决与 no_answer 语义**：任一 mismatch → `disagree`（压倒 match 多数）；
  零 mismatch 且 `n_match ≥ 2` → `agree`；否则 `incomplete`；`no_answer` 涵盖空串/纯空白/
  非 str 代理答案，永不升级为 mismatch；statuses 按 agent id 码点升序的元组。
  〔测试裁定 `test_verify_item_verdicts`、`test_verify_item_choice_item`〕
- I6 **记录诚实性与 v2 合法性**：仅 `agree` 产出记录（agents 恰为 match 状态的代理、
  去重升序、`answers_agree is True`，`validate_item_v2` 零消息）；`disagree`/`incomplete`
  → `None`；`make_record` 对 <2 个不同 id、非法 id 抛 `DualVerifyError`。〔测试裁定
  `test_record_only_for_agree_and_passes_itembank_v2`、
  `test_make_record_sorted_dedup_and_floor`〕
- I7 **回填纯度**：`backfill_item` 不修改入参（deepcopy 快照相等）；原键原序、`verification`
  追加末尾；`record=None` → 无 `verification` 键的副本；输出记录值恰为
  `{"agents": [...], "answers_agree": True}` 且过 `validate_item_v2`；各类非法 record
  抛 `DualVerifyError`。〔测试裁定 `test_backfill_pure_and_validated`〕
- I8 **bank 级顺序闭式**：报告六个字段全 tuple；`item_ids`/`verdicts`/`records` 与
  分桶 id 元组均按 items 输入原序；`answers_by_item` 缺条目 → 空 dict → `incomplete`、
  record `None`；`counts()` 三键恒定且每次返回新 dict。〔测试裁定
  `test_verify_bank_order_and_closed_form`〕
- I9 **仲裁行形状与顺序**：仅 mismatch 成行；四键 dict（`proposed` 为原始提案值）；
  题序 = items 原序、题内 agent id 升序；无分歧空 tuple。〔测试裁定
  `test_arbitration_rows_shape_and_order`〕
- I10 **纯函数性**：同 `(items, answers_by_item)` 重复调用 `verify_bank`/
  `arbitration_rows` 结果相等（dataclass/元组相等）；入参深拷贝快照不变；输出记录不
  别名入参内部对象（改写首次输出的 `records[0][1]["agents"]` 不影响复跑输出与入参）。
  〔测试裁定 `test_purity_inputs_not_modified_and_repeatable`〕
- I11 **输入守卫**：题目侧（非 dict / 空白 id / 非 str 或空白 answer / 非法 item_type /
  choice options 非 list<2）、入参侧（`agent_answers` 非 dict、agent id 非法）、
  bank 级（`answers_by_item` 非 dict、题 answer 空串）一律 `DualVerifyError`。
  〔测试裁定 `test_verify_item_input_guards`、`test_verify_bank_input_guards`〕

## 5. 确定性与随机性

- 全部公开函数为纯函数：输出只依赖入参；**禁止** `random`、seed 驱动随机（本模块
  没有任何随机源）、系统时钟、环境读取、文件/网络 IO、全局可变状态；无时间戳字段
  （无豁免）。
- 顺序来源全部显式可判：`statuses`/仲裁行内 agent 顺序 = `sorted(agent_answers)`
  的**码点升序**（`"B"` < `"a"`；dict 插入序不影响输出）；报告字段顺序 = items **输入
  原序**；记录 `agents` = 码点升序。不依赖 hash 序。
- 浮点可复现性：数值判等只用 §3.3 的相对容差式（不做 round）；百分数 ÷100、分数
  除法为 IEEE 唯一结果。§3.3 每个 True/False、§3.4–§3.7 每个输出 dict/元组都是逐位
  或逐字段对照点。
- 拷贝隔离：`verify_item`/`verification_record`/`make_record`/`backfill_item` 每次返回
  新 dict/list；`DualVerifyReport.counts()` 每次返回新 dict（I8/I10 的别名测试）。

## 6. 错误行为

| 非法输入 | 行为 |
|---|---|
| `normalize_answer` / `answers_match` 的 `key_answer` / `proposed` 非 str | `DualVerifyError` |
| `answers_match` 的 `item_type` 不在 {choice, fill, solve}（含 None、数字、`"proof"`） | `DualVerifyError` |
| `answers_match` 的 `item_type == "choice"` 且 `options` 非 list 或 len < 2（含 `None`） | `DualVerifyError` |
| `answers_match` choice 的 `options` 元素含非 str | `DualVerifyError`（归一化选项时抛）〔参考裁定 P10〕 |
| `verify_item` 的 `item` 非 dict | `DualVerifyError`（校验先于裁决） |
| `item["id"]` 非 str / 带首尾空白 / 空 | `DualVerifyError` |
| `item["answer"]` 非 str / strip 后为空 | `DualVerifyError` |
| `item["item_type"]` 非法 / choice 的 `options` 非 list 或 <2 | `DualVerifyError` |
| `agent_answers` 非 dict（list、str 等） | `DualVerifyError` |
| agent id 非 str / 带首尾空白 / 空（即使该代理答案是空/非 str） | `DualVerifyError`（先于 no_answer 判定） |
| `agent_answers` 的键不可互相比大小（混合类型，如 `{1: "2", "b": "3"}`） | **`TypeError`**（`sorted` 先于 id 校验）〔参考裁定 P3；契约未覆盖〕 |
| `verify_bank` / `arbitration_rows` 的 `answers_by_item` 非 dict（如 `["nope"]`、`"nope"`） | `DualVerifyError` |
| `verify_bank` / `arbitration_rows` 的 `items` 元素缺 `"id"` 键 | **`KeyError`**（`item["id"]` 在 `verify_item` 校验前求值）〔参考裁定 P4；契约未覆盖〕 |
| `make_record` 的去重后 id < 2 / 含非法 id（`["a", " a"]`） | `DualVerifyError` |
| `verification_record` 入参非 dict / 缺 `"verdict"` 键 | `DualVerifyError` |
| `verification_record` 的 `verdict == "agree"` 但 statuses 中 match 不足 2（手工 dict） | `DualVerifyError`（经 make_record 下限）〔参考裁定 P9〕 |
| `backfill_item` 的 `item` 非 dict / `record` 非法（非 dict、agents 非 list<2、元素非法、重复、`answers_agree` 非恰 True） | `DualVerifyError` |
| 代理答案空串 / 纯空白 / 非 str | **容忍**：`no_answer`（不抛错，见 I5） |
| `answers_by_item` 缺某题条目 | **容忍**：空 dict → `incomplete`、记录 `None` |
| 数值解析失败（`"abc"`、`"3/0"`、`1:3`）、choice 提案/标答解析不到 | **容忍**：走字面兜底或判 `False`（choice 标答不可解析 → `False`，不抛，参考裁定 P1） |

异常类型一律 `DualVerifyError`（ValueError 直接子类）；§6 表中两个非 ValueError 情形
（混合类型 agent 键的 `TypeError`、items 缺 `"id"` 的 `KeyError`）均为参考裁定边界、
契约测试未覆盖（见附录 A）。异常消息文案不作承诺（不是契约面）。

## 7. 非目标

- **不做单位换算**：米/厘米、千米/米之间不折算；只做别名归一后的字符串/单位相等
  （`80平方厘米 ≠ 80厘米`、`-300元 ≠ -300`；`公里`→`千米` 别名判等由 §3.1 表推出）。
- **不解方程、不做过程判分**：`x+y=1` 不被剥前缀；剥前缀只容忍 ≤6 字符的单一变量名
  书写差异（`x=5`≡`5` 属集合等值的书写容忍，不是求解）。
- **不做中文数字/自然语言语义判分**：`两元` 走字面支；"意思对即可"不在确定性内核。
- **不接 LLM / 不做语义判分**：`x>2` 与 `x≥2` 不等价；全部判定为字符串/数值规则。
- **不自动仲裁分歧**：`disagree` 只产出人工仲裁队列行（`arbitration_rows`），不做
  自动改判、投票或置信度折中。
- **不回填 disagree/incomplete**：诚实缺口优先于完整性；只有 `agree`（≥2 match 且
  零 mismatch）才产出记录。
- **不做多选/组合作答判分与部分分**：`answers_match` 输出恒为 bool；一题一次的
  verification 记录只表达"通过/不通过"。
- **不认证代理身份**：`agent_id` 仅作排序键与记录键；不查重跨库代理、不验真伪。
- **不读题库/知识库文件、不持久化**：不 import `itembank`/`itembank_v2` 加载器，
  不写文件/数据库；itembank_v2 校验形状的一致性由契约测试跨模块断言。
- **不重排/去重/清洗输入**：items 与 answers_by_item 按键值原样使用；bank 级输出
  顺序恒为输入原序；不合并同 id 题目。
- **不做流式/增量裁决**：每次 `verify_bank`/`arbitration_rows` 全量重算；无缓存、
  无状态、无版本号/时间戳记录。
- **不做双代理以外的裁决策略**：不实现"代理数 ≠ 2 的加权"、不裁决裁判agent等多种
  格局外的聚合规则；三值裁决语义按 §3.4 冻结。

## 附录 A：冻结证据与契约未裁定的参考行为

**基线**（2026-10-02，CPython 3.12.10 x64 / pytest 9.1.1，win32）：
`python -m pytest tests/contract/test_dual_verify_contract.py -q` → **18 passed**；
`python tools/run_contract.py --modules dual_verify` 走同一判定入口
（`tools/run_contract.py:33` 登记 `dual_verify → test_dual_verify_contract.py`）。

**探针**（`.tmp_review_checks/dv_freeze_probe.py` / `dv_freeze_probe2.py` /
`dv_freeze_probe3.py`，均于参考实现实测）：

| 探针 | 行为（实测值） | 裁定 |
|---|---|---|
| P1 | `answers_match("E","B",item_type="choice",options=["A. 1","B. 2"])` → `False`（标答不可解析不抛错） | 参考裁定（契约未覆盖；grading 对应行为为抛错） |
| P2 | fill/solve 忽略 `options`（`options=42` 不抛） | 参考裁定（契约未覆盖） |
| P3 | `verify_item(item, {1:"2","b":"3"})` → `TypeError`（sorted 混合键） | 参考裁定（契约未覆盖） |
| P4 | `verify_bank([{}], {})` / `arbitration_rows([{}], {})` → `KeyError: 'id'`（而 `verify_item({}, {})` → `DualVerifyError`） | 参考裁定（契约未覆盖） |
| P5 | `answers_match("x=5","5")` → `True`；`answers_match("∠2=45°","45°")` → `False`（`∠₂=45` 下标形才剥，探针 Q2） | 参考裁定；注意参考实现源码注释里的 `∠2=` 例子含 ASCII 数字，与正则字符类（下标数字 U+2080–2089）不一致 |
| P8/Q8 | 20000 例随机串 `normalize_answer` vs `grading.normalize_answer` → 0 差异 | 参考裁定（测试只覆盖 13 例电池） |
| P9 | `verification_record({"verdict":"agree"})` → `DualVerifyError` | 参考裁定 |
| P10 | choice `options=[1,"B. 2"]` → `DualVerifyError` | 参考裁定 |
| P15/P16/P17 | 3 代理全 match → 记录 3 agents；2 match + 2 no_answer → `agree`、记录 2 agents；1 match + 1 mismatch + 1 no_answer → `disagree`、`None` | 参考裁定 |
| P18 | `make_record({"b","a"})`（set 入参）→ 升序记录 | 参考裁定 |
| P19 | item 已有 `verification` 键时 `backfill_item` 就地覆盖（键位置不变） | 参考裁定（契约只覆盖"无键→追加末尾"） |
| P20/P29/P30/P31 | `answers_match("2","   ")` → `False`；`("x=","x")` → `False`；`("abcdefg=1","1")` → `False`（>6 不剥）；`("或","或")` → `True`（全分隔符防御） | 参考裁定 |
| P32 | statuses 按码点升序：`{"B":"2","a":"2"}` → `(("B","match"),("a","match"))` | 参考裁定 |
| P34/Q1–Q7 | `answers_match(42,"2")` → `DualVerifyError`；`x₁=`/`∠₂=`/`AB=`/`a'b=` 前缀剥、`x+y=` 不剥；归一化对规则表输入幂等 | 参考裁定 |
| Q9/Q10 | 注入门下 `from __future__ import annotations` → `AttributeError`；相对导入 → `ImportError`（§2 装载约束） | 实测 |

另注：参考实现 `src/xuexing/dual_verify.py` 的 docstring 引用「行为契约：
specs/drafts/dual_verify.spec.md」，该文档在本仓库中不存在——本冻结契约即其继任者。
