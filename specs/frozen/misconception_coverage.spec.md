# misconception_coverage 模块规格（冻结契约）

> 本文档是唯一权威契约。任何实现（参考实现或重生成实例）只要通过 tests/contract/ 全部测试
> 且满足本文全部条款，即为合格实现。实现算法自由，行为不允许偏离。
>
> **版本**：定稿 v1（第三波冻结）。标注「〔测试裁定〕」的行为由
> `tests/contract/test_misconception_coverage_contract.py`（20 项）直接断言；标注「〔参考裁定〕」
> 的行为契约测试未仲裁，按参考实现 `src/xuexing/misconception_coverage.py` 冻结并在当地注明
> 本冻结轮的实测证据。本文自包含，不引用仓库内其他规格文档。
>
> 冻结基线：参考实现 + 契约测试全量实测于 2026-10-02，CPython 3.12.10 x64
> （`python -m pytest tests/contract/test_misconception_coverage_contract.py -q` → **20 passed**）；
> 装载门实测（`XX_IMPL_DIR=<副本目录> XX_MODULES=misconception_coverage python -m pytest
> tests/contract/test_misconception_coverage_contract.py -q`）：参考实现精确副本 → 20 passed；
> 另跑仓库外行为探针 P1–P18 验证本文参考裁定点（18/18 通过，探针脚本不入库）。

## 1. 目的

misconception_coverage 是误解库覆盖审计器（误解库扩充管线的确定性内核）：把误解库**文件
dict**（`{"misconceptions": [...], "exemptions": [...]}`）解析校验为条目/豁免对象
（`parse_bank`），再对给定 KP id 清单逐个核对「误解条数 ≥ `min_per_kp` 或显式声明该 KP 无
误解」，产出确定性报告 `MisconceptionReport`（逐 KP 计数、缺口 KP、豁免 KP、已覆盖 KP、
总数，`audit` / `audit_dicts`）。行为契约：**解析纪律**（字段级校验规则见 §3.4，全部错误
一种异常类型）、**交叉一致性**（条目 id 跨输入全局唯一、条目/豁免引用未知 KP、豁免与已有
误解矛盾、同 KP 内 signature 跨条目重复都是数据错误）、**纯度与确定性**（无 IO、无随机、
无时钟；所有输出序列 tuple 化且顺序 = KP 输入原序 / 文件内原序，同输入同输出）。

## 2. 允许的依赖与装载约束

- Python 标准库：**仅 `dataclasses`**（参考实现唯一 import：
  `src/xuexing/misconception_coverage.py:18` `from dataclasses import dataclass`）
- **不 import `xuexing.types`，也不 import 任何其他 xuexing 模块**（无例外）。但 `audit` 的
  `entries` 是鸭子类型：调用方传入的 `xuexing.types.Misconception` 实例
  （`id: str, kp_id: str, description: str, hint: str, signature: list[str]`，
  `src/xuexing/types.py:124-132`）必须与本模块 `MisconceptionEntry` 被**同等接受**并产出
  相等报告（I14）——这是入参形状约定，不构成 import
- 禁止：第三方库、文件/网络 IO、随机、系统时钟、环境读取、全局可变状态

重生成实例的装载约束（自包含实测，2026-10-02，CPython 3.12.10；注入机制：
`tests/conftest.py:22-34` 以顶层模块名 `_regen_misconception_coverage` 经
`spec_from_file_location` 装载 `<impl_dir>/misconception_coverage.py` 并顶替
`sys.modules["xuexing.misconception_coverage"]`）：
- **禁止 `from __future__ import annotations`**：实测在参考副本首行加入该语句后，装载即败——
  `AttributeError: 'NoneType' object has no attribute '__dict__'`（CPython 3.12.10
  `dataclasses.py:749` `_is_type` → `sys.modules.get(cls.__module__).__dict__`，经
  `dataclasses.py:983` `_process_class` 触发：注入注册名 `xuexing.misconception_coverage`
  ≠ dataclass 的 `__module__` `_regen_misconception_coverage`，`.get` 得 `None`）。
  注解直接写真实对象（`tuple`、`int`、`str`）。
- **绝对导入 + 真实对象注解实测可装载**：参考实现精确副本经注入门装载后契约测试 20 passed。
- 本模块无包内导入需求（只 import 标准库）；若写相对导入（`from .types import ...`）同样
  违反装载门。

## 3. 公开 API

模块必须暴露以下 7 个名字（契约测试
`from xuexing.misconception_coverage import Exemption, MisconceptionCoverageError,
MisconceptionEntry, MisconceptionReport, audit, audit_dicts, parse_bank`，与参考实现
`__all__` 逐项一致，`src/xuexing/misconception_coverage.py:20-28`）。

### 3.1 `MisconceptionCoverageError`

```python
class MisconceptionCoverageError(ValueError): ...
```

本模块**唯一**异常类型，`ValueError` 直接子类（`issubclass` 断言：
test_parse_bank_rejections，tests:133）。契约内任何校验失败都抛它，不抛其他异常类型
（§6）。

### 3.2 `MisconceptionEntry` 与 `Exemption`

```python
@dataclass
class MisconceptionEntry:
    id: str
    kp_id: str
    description: str
    hint: str
    signature: tuple      # 典型错误答案；解析产物恒为 tuple[str, ...]

@dataclass
class Exemption:
    kp_id: str
    reason: str           # 「该 KP 无误解」的非空理由
```

- 两个都是 dataclass：支持按位置与按键构造；**构造时不校验**（全部校验在 `parse_bank` /
  `audit` 内）〔参考裁定：探针 P4 构造 `MisconceptionEntry(id=7, ...)` 不抛，错误发生在
  `audit`〕；dataclass 逐字段相等是本模块对象比较的唯一方式。
- `MisconceptionEntry.signature` 与 `xuexing.types.Misconception.signature` 同域不同形：
  解析产物是 tuple（文件里是 list，`parse_bank` 负责 list→tuple），`Misconception` 原生
  是 list；`audit` 内部对两者统一 `tuple()` 化（§3.5）。

### 3.3 `MisconceptionReport`

```python
@dataclass
class MisconceptionReport:
    kp_ids: tuple                 # 输入 KP 清单（原序、去重后全集）
    counts: tuple                 # 每 KP 恰一项 (kp_id, count)，输入原序
    deficient_kp_ids: tuple       # 条数 < min_per_kp 且未豁免的 KP（缺口），输入原序
    exempt_kp_ids: tuple          # 显式声明无误解的 KP，输入原序
    covered_kp_ids: tuple         # 条数 >= min_per_kp 的 KP，输入原序
    min_per_kp: int
    total_misconceptions: int

    def is_complete(self) -> bool:
        return not self.deficient_kp_ids
```

- 六个序列字段**全部是 tuple**（含 `counts` 的每个元素也是 tuple）——测试以
  `rep.deficient_kp_ids.append(...)` / `rep.counts[0].append(...)` 必抛 `AttributeError`
  钉死（test_audit_purity，tests:252-255）〔测试裁定〕。
- `counts` 对**每个**输入 KP 恰一项（含 0 条与豁免 KP 的 0 项）〔测试裁定：
  test_audit_closed_form `counts == (("k1",2),("k2",1),("k3",0))`；参考裁定：探针 P11/P17
  无条目时每 KP 记 0、豁免 KP counts 记 0〕。
- `total_misconceptions` = entries 总数（条目 id 全局唯一已校验，故 = 全局 id 集合大小）
  〔测试裁定：test_audit_partitions `rep.total_misconceptions == len(entries)`；参考裁定：
  实现取 `len(seen_entry_ids)`，`src/xuexing/misconception_coverage.py:245`〕。
- `is_complete()` 返回 `bool`（`not deficient_kp_ids` 的求值结果）〔测试裁定 `is False` /
  `is True`（tests:148/156/188）；参考裁定：探针 P15 `type(...) is bool`〕。对空 KP 宇宙
  为 True（I13）。

### 3.4 `parse_bank`

```python
def parse_bank(data) -> tuple[list[MisconceptionEntry], list[Exemption]]
```

解析误解库文件 dict，返回 `(entries, exemptions)` 两个**list**（文件内原序；非 tuple）。
`data` 形状：`{"misconceptions": [...], "exemptions": [...]（可选，缺省为空列表）}`。
**校验规则（按序执行；每一项失败都抛 `MisconceptionCoverageError`）**：

1. `data` 必须是 dict；
2. 必须含 `"misconceptions"` 键；`data["misconceptions"]` 必须是 list；
3. `data.get("exemptions", [])` 必须是 list（缺省 `[]` 合法）；
4. 逐条目（文件内原序）：必须是 dict；`id` 经 id 校验（非空 str 且**无首尾空白**）；
   id 在**本文件内**全局唯一；`kp_id` 经 id 校验；`description`/`hint` 经文本校验
   （非空白 str，内部空白自由）；`signature` 必须是非空 list，每个元素是无首尾空白的
   非空 str 且**条目内去重**；产物 `signature` 为 tuple（保序）；
5. 逐豁免（文件内原序）：必须是 dict；`kp_id` 经 id 校验；`kp_id` 在**豁免列表内**唯一；
   `reason` 经文本校验。

容忍（不抛错）：空 `misconceptions` list（空库合法，缺口交由 `audit` 报告）；
条目/豁免 dict 的**额外键**（只读约定键，其余忽略）〔参考裁定：探针 P8〕；
`parse_bank` **不做**「豁免 KP 与已有误解矛盾」检查——该检查只属于 `audit`
（§3.5）〔参考裁定：实现 `src/xuexing/misconception_coverage.py:159-167` 无此分支〕。

**输入输出例子**（全部〔测试裁定〕，test_parse_bank_fields_and_order /
test_parse_bank_exemptions_default_empty，tests:69-84）：

```python
bank_data = {
    "misconceptions": [
        {"id": "e1", "kp_id": "k1", "description": "符号错：-3+5 算成 -8",
         "hint": "异号相加取绝对值大者的符号。", "signature": ["-8"]},
        {"id": "e2", "kp_id": "k2", "description": "去括号漏变号",
         "hint": "括号前是负号，每一项都变号。", "signature": ["5-a-3"]},
    ],
    "exemptions": [{"kp_id": "k3", "reason": "纯约定内容，无典型错误模式可归纳"}],
}
entries, exemptions = parse_bank(bank_data)
# entries[0].id == "e1"；entries[0].kp_id == "k1"
# entries[0].description == "符号错：-3+5 算成 -8"（原样透传）
# entries[0].signature == ("-8",)      # list -> tuple
# [e.id for e in entries] == ["e1", "e2"]          # 文件内原序
# exemptions == [Exemption(kp_id="k3", reason="纯约定内容，无典型错误模式可归纳")]
del bank_data["exemptions"]
# parse_bank(bank_data) -> (entries, [])           # 缺省为空列表
```

### 3.5 `audit`

```python
def audit(kp_ids, entries, exemptions=(), min_per_kp: int = 2) -> MisconceptionReport
```

- `kp_ids`：**任意可迭代对象**，元素为非空且无首尾空白的 str〔测试裁定 list 用法；
  参考裁定：探针 P5 生成器可用〕；重复 KP id 抛错。
- `entries`：**鸭子类型**，元素只需有 `.id`（非空 str，strip 后非空）与 `.kp_id`
  （命中 `kp_ids` 清单）；`.signature` 可选，缺省按空 tuple 处理〔参考裁定：探针
  P2/P3/P4〕。`MisconceptionEntry` 与 `xuexing.types.Misconception`（signature 为 list）
  均 accepted，内部统一 `tuple()` 化（`src/xuexing/misconception_coverage.py:208`）。
- `exemptions`：鸭子类型，元素只需有 `.kp_id`（命中清单）；`audit` **不读** `.reason`
  〔参考裁定：探针 P6——只有 `.kp_id` 的对象也能通过 `audit`；`.reason` 必填是
  `parse_bank` 侧规则〕。
- `min_per_kp`：必须是 `int`（`bool` 不算）且 `>= 1`〔测试裁定〕。

**校验顺序（绑定条款；〔参考裁定〕——全部失败同为一种异常类型，次序只在探查上可观察）**：
`min_per_kp` → `kp_ids`（逐元素 id 校验 + 重复检查）→ `entries`（id 非空/全局唯一 →
`kp_id` 命中清单）→ `exemptions`（未知 KP → 重复 → 与已有误解矛盾）→ 同 KP 内 signature
跨条目唯一性 → 构建报告。

**报告构造**：`counts` 按 `kp_ids` 输入原序每 KP 一项；`deficient` = 条数 < `min_per_kp`
且未豁免；`exempt` = 豁免清单 ∩ 输入原序；`covered` = 条数 ≥ `min_per_kp`（豁免 KP 条数为 0
时**不**进 covered，也**不**进 deficient）；三个集合两两不交、并集 = KP 全集（I5）。

**输入输出例子**（全部〔测试裁定〕：fixtures `kp_ids=["k1","k2","k3"]`、`e1/e2` 属 k1、
`e3` 属 k2、k3 豁免；test_audit_closed_form / test_audit_min_per_kp，tests:138-160）：

```python
rep = audit(["k1", "k2", "k3"], entries, exemptions)            # min_per_kp 默认 2
# rep.kp_ids == ("k1", "k2", "k3")
# rep.counts == (("k1", 2), ("k2", 1), ("k3", 0))
# rep.covered_kp_ids == ("k1",)；rep.deficient_kp_ids == ("k2",)   # k3 豁免不进缺口
# rep.exempt_kp_ids == ("k3",)；rep.min_per_kp == 2
# rep.total_misconceptions == 3；rep.is_complete() is False
rep1 = audit(["k1", "k2", "k3"], entries, exemptions, min_per_kp=1)
# covered == ("k1", "k2")；deficient == ()；is_complete() is True
rep3 = audit(["k1", "k2", "k3"], entries, exemptions, min_per_kp=3)
# deficient == ("k1", "k2")          # k1 只有 2 条也成缺口；counts 不变
```

**鸭子类型等价例子**〔测试裁定，test_audit_accepts_types_misconception，tests:271-279〕：
`audit(kp_ids, [Misconception(id="d1", kp_id="k1", description="d", hint="h",
signature=["s1"]), Misconception(id="d2", kp_id="k2", ..., signature=["s2"])], exemptions)`
与用同参数 `MisconceptionEntry` 构造的报告**逐字段相等**。

### 3.6 `audit_dicts`

```python
def audit_dicts(kp_dicts, bank_data, min_per_kp: int = 2) -> MisconceptionReport
```

knowledge json 形状（dict 列表）× 误解库文件 dict 的便捷入口。**校验顺序（绑定条款）**：
先校验 `kp_dicts`（必须是 list 或 tuple〔参考裁定：探针 P7 tuple 接受；错误消息文案
不作承诺〕；每个元素必须是 dict 且 `"id"` 经 id 校验——非空 str 且无首尾空白，
与 §3.4 同规则），再 `parse_bank(bank_data)`（解析错误原样抛出），最后把解析产物交给
`audit`（重复 KP id 由 `audit` 的重复检查抛出）。

**输入输出例子**（〔测试裁定〕，test_dicts_entry_equivalence，tests:284-290）：

```python
rep = audit_dicts([{"id": "k1"}, {"id": "k2"}, {"id": "k3"}], bank_data)
# 等价于 audit(["k1","k2","k3"],
#              [_entry("e1","k1",["-8"]), _entry("e2","k2",["5-a-3"])],
#              [Exemption("k3", "纯约定内容，无典型错误模式可归纳")])
# rep.counts == (("k1", 1), ("k2", 1), ("k3", 0))；rep.is_complete() is False
```

## 4. 不变量（编号列出，全部可被契约测试检验）

- I1 **解析字段映射与原序**：`parse_bank` 输出条目/豁免为文件内原序的 dataclass 列表；
  `signature` list→tuple 且元素保序；`exemptions` 缺省为空列表
  （test_parse_bank_fields_and_order、test_parse_bank_exemptions_default_empty）。
- I2 **解析纯度与确定性**：`parse_bank` 不改输入 dict，两次调用结果逐字段相等
  （test_parse_bank_pure_and_deterministic）。
- I3 **解析拒绝域**：§3.4 步骤 1–5 的每类非法输入（22 种 mutate + 5 种整体非法输入）
  都抛 `MisconceptionCoverageError`；空 `misconceptions` list 合法
  （test_parse_bank_rejections）。
- I4 **报告闭式**：§3.5 例子中的每个报告字段值与手算一致（同输入同报告）
  （test_audit_closed_form）。
- I5 **三分划**：`covered ∪ deficient ∪ exempt == set(kp_ids)` 且两两不交；
  `total_misconceptions == len(entries)`；`dict(counts)` 逐 KP 计数
  （test_audit_partitions）。
- I6 **输入原序**：`kp_ids`/`counts`/`deficient`/`exempt`/`covered` 全部按 KP 输入原序
  （输入反转则输出序列反转）（test_audit_input_order）。
- I7 **阈值语义**：`min_per_kp` 升降只改 `covered`/`deficient` 划分与 `is_complete()`，
  不改 `counts`；`min_per_kp=1` 时 `deficient == ()`、`is_complete()` 为 True
  （test_audit_min_per_kp）。
- I8 **豁免语义**：豁免 KP 无条数要求（0 条即合法豁免，不进缺口）；豁免 KP 已有误解 /
  引用未知 KP / 同一 KP 重复豁免均抛错（test_audit_exemption_semantics）。
- I9 **交叉一致性**：条目 id 跨输入全局唯一（列表自身翻倍、跨 KP 追加同 id 都抛错）；
  条目引用未知 KP 抛错，但 KP 清单多出而无条目引用时只是缺口不是错误
  （test_audit_entry_id_global_unique、test_audit_unknown_kp_reference）。
- I10 **signature 每 KP 唯一**：同一 KP 内 signature 跨条目重复抛错（归因歧义）；
  同一 signature 落到不同 KP 合法（test_audit_signature_unique_per_kp）。
- I11 **输入纪律**：`kp_ids` 元素重复 / 空串 / 首尾空白 / 非 str 抛错；`min_per_kp` 为
  bool / 非 int / `< 1`（0、-1、"2"、2.0、None、True）抛错
  （test_audit_kpid_validation、test_audit_min_per_kp_validation）。
- I12 **纯度与不可变输出**：`audit` 不改 `kp_ids`/`entries`/`exemptions` 三个入参；报告
  序列字段是 tuple（append 抛 `AttributeError`）（test_audit_purity）。
- I13 **空 KP 宇宙**：`audit([], [], [])` 返回全空 tuple 报告、`total=0`、
  `is_complete()` 为 True（对空集命题诚实为真）；此时任何条目都是未知 KP 引用，抛错
  （test_audit_empty_kp_universe）。
- I14 **鸭子类型兼容**：`xuexing.types.Misconception`（signature 为 list）与
  `MisconceptionEntry` 同参的报告逐字段相等（test_audit_accepts_types_misconception）。
- I15 **入口等价**：`audit_dicts` 与手工构造 entries/exemptions 的 `audit` 报告相等；
  `kp_dicts` 非法（非 list/tuple、元素非 dict、缺/空 `id`）与 bank 非法都抛
  `MisconceptionCoverageError`（test_dicts_entry_equivalence、
  test_dicts_entry_validation）。
- I16 **确定性**：同输入重复调用（`audit` 两种 `min_per_kp`、`audit_dicts`）报告逐字段
  相等（test_determinism）。

## 5. 确定性与随机性

- `parse_bank`/`audit`/`audit_dicts` 是纯函数：输出只依赖入参；禁止 `random`、系统时钟、
  环境读取、文件/网络 IO、全局可变状态。全模块无时间戳字段（无豁免）。
- 顺序的确定性来源：所有输出序列由**有序结构**构建——`kp_ids` 输入原序（`kp_list`）、
  `by_kp` 按 KP 输入序插入、解析产物按文件原序；集合（`seen_kp`、`seen_entry_ids`、
  `exempt_set`、每 KP 的 signature 集）**只用于成员判定，从不被迭代进输出**，故无 hash
  序依赖。
- 无数值运算、无舍入：报告只有整数计数与字符串元组；对象相等即 dataclass 逐字段相等。
- `signature` 跨条目的重复检查按 KP 输入序、条目出现序扫描，首个重复即抛（异常消息
  文案不作承诺，§6）。

## 6. 错误行为

全部非法输入一律抛 `MisconceptionCoverageError`（`ValueError` 直接子类，tests:133 断言）；
契约内输入不抛其他异常类型。异常消息文案**不作承诺**（不是契约面）。

| 非法输入 | 行为 |
|---|---|
| `parse_bank` 的 `data` 非 dict（含 `{}`、`None`、str、list） | 抛 `MisconceptionCoverageError` |
| 缺 `"misconceptions"` 键 / `misconceptions` 非 list（含 `None`） | 抛 `MisconceptionCoverageError` |
| `exemptions` 非 list（如 `"x"`） | 抛 `MisconceptionCoverageError` |
| 条目/豁免非 dict（如 `"not-a-dict"`） | 抛 `MisconceptionCoverageError` |
| 条目 `id`：非 str / 空 / 首尾空白（`" e1"`）/ 文件内重复 | 抛 `MisconceptionCoverageError` |
| 条目 `kp_id`：非 str / 空 / 首尾空白（`"k1 "`） | 抛 `MisconceptionCoverageError` |
| 条目 `description`/`hint`：缺键 / 空 / 纯空白（`"  "`） | 抛 `MisconceptionCoverageError` |
| 条目 `signature`：缺键 / 非 list / 空 list / 元素非 str / 空串 / 首尾空白（`" -8"`）/ 条目内重复 | 抛 `MisconceptionCoverageError` |
| 豁免 `kp_id`：非 str / 空 / 首尾空白 / 豁免列表内重复 | 抛 `MisconceptionCoverageError` |
| 豁免缺 `reason` / `reason` 纯空白 | 抛 `MisconceptionCoverageError` |
| `audit` 的 `min_per_kp`：bool（含 `True`）/ 非 int（`"2"`、`2.0`、`None`）/ `< 1`（`0`、`-1`） | 计算前抛 `MisconceptionCoverageError` |
| `audit` 的 `kp_ids` 元素：非 str（`7`）/ 空串 / 首尾空白（`" k1 "`）/ 清单内重复 | 计算前抛 `MisconceptionCoverageError` |
| `audit` 的 entry `id`：非 str 或空白（含缺 `.id` 属性得 `None`） | 计算前抛 `MisconceptionCoverageError` |
| `audit` 的 entry `id` 跨输入重复（列表翻倍 / 跨 KP 同 id） | 计算前抛 `MisconceptionCoverageError` |
| `audit` 的 entry `.kp_id` 不在 KP 清单（含缺属性得 `None`） | 计算前抛 `MisconceptionCoverageError` |
| `audit` 的豁免：未知 KP / 同一 KP 重复豁免 / 豁免 KP 已有误解 | 计算前抛 `MisconceptionCoverageError` |
| `audit` 的同 KP 内 signature 跨条目重复 | 计算前抛 `MisconceptionCoverageError` |
| `audit_dicts` 的 `kp_dicts` 非 list/tuple / 元素非 dict / `id` 非法（缺键、空串） | 计算前抛 `MisconceptionCoverageError` |
| `audit_dicts` 的 `bank_data` 非法 | 原样抛出 `parse_bank` 的 `MisconceptionCoverageError` |

必须容忍并跳过（不抛错）的合法形态：

- 空 `misconceptions` list（空库；缺口由 `audit` 报告）与空 KP 宇宙（诚实空报告，
  I13）；
- 豁免 KP 条数为 0（合法豁免，不是缺口，I8）；
- 条目/豁免 dict 的额外键；鸭子条目缺 `.signature` 属性（按空 tuple）；`kp_dicts` 传
  tuple；`exemptions` 缺省为空〔以上参考裁定：探针 P2/P6/P7/P8〕；
- KP 清单中存在无任何条目引用的 KP（只是缺口，不是错误，I9）。

## 7. 非目标

- **不做文件/网络 IO**：误解库与 KP 清单一律以 dict / 可迭代对象入参；不读
  `data/misconceptions/*.json`、不写报告。装载是调用方职责。
- **不做 signature 归因匹配**：本模块只校验 signature 的非空/无空白/条目内去重与同 KP
  跨条目唯一性；运行时按 signature 命中误解（attribute_error 匹配）是别的引擎的职责。
- **不做误解内容生成 / 补缺建议**：只报告缺口 KP 清单，不生成候选误解条目、不写扩充
  管线语义。
- **不做跨 KP 的 signature 规则**：跨 KP 允许同一 signature；不引入全局签名空间约束。
- **不做阈值语义扩展**：判定只有「条数 ≥ `min_per_kp`」；无分级、部分达标、权重、
  趋势或严重度。
- **不做描述级质检**：`description`/`hint` 只查非空白；不做相似度、去重、语言检查。
- **不修改、排序、去重输入**：入参原样保留；输出顺序 = 输入原序 / 文件内原序（I6）。
- **不做多租户、持久化、报告聚合**：一次 `audit` 一个 KP 清单一份报告；不跨批次合并。
- **不接 LLM**：无语义判重、无语义缺口解释。
- **不 import 任何 xuexing 模块**（含 `xuexing.types`）：对 `types.Misconception` 只做
  鸭子兼容（I14），禁止 import。
- **不引入第三方库**：依赖仅标准库 `dataclasses`（§2）。
- **不引入随机/时钟**：无 seed、无时间戳、无环境读取（§5）。
