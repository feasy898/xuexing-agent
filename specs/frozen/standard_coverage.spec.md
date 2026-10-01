# standard_coverage 模块规格（冻结契约）

> 本文档是唯一权威契约。任何实现（参考实现或重生成实例）只要通过 tests/contract/ 全部测试
> 且满足本文全部条款，即为合格实现。实现算法自由，行为不允许偏离。
>
> **版本**：定稿 v1（契约第三波冻结）。标注「〔测试裁定〕」的行为由
> `tests/contract/test_standard_coverage_contract.py`（19 项）直接断言；标注「〔参考裁定〕」
> 的行为契约测试未仲裁，按参考实现 `src/xuexing/standard_coverage.py` 冻结并注明出处。
> 本文自包含：不引用仓库内其他规格文档；全部次序、常量、字段在本文内完整定义。
>
> 冻结基线（本冻结轮实跑，CPython 3.12.10 x64）：
> `python -m pytest tests/contract/test_standard_coverage_contract.py -q` → **19 passed**；
> 注入门实测 `XX_IMPL_DIR=<原样拷贝目录> XX_MODULES=standard_coverage python -m pytest
> tests/contract/test_standard_coverage_contract.py -q` → 19 passed。

## 1. 目的

standard_coverage 是课标覆盖检查器：把知识点的 `standard_ref` 与课标主题清单
（`domains → themes → topics` 三层结构，每个条目携带 `aliases` 检索关键词）做对照，
产出**双向缺口**——清单中没有任何 KP 引用的条目（覆盖缺口）+ `standard_ref` 归属不到
任何条目的 KP（归属缺口），外加逐 KP 归属表与条目级覆盖率。行为契约：
**纯子串匹配**（条目任一 alias 是 ref 的连续子串即归属该条目）、**双向缺口分划**
（matched/unmatched 与 covered/uncovered 各自完备且不相交）、**确定性排序**
（条目类输出恒按清单原序，KP 类输出恒按输入原序）、**全模块纯函数**（无 IO、无随机、
无时钟，同输入同输出）。

## 2. 允许的依赖与装载约束

- Python 标准库：`dataclasses`（源码唯一 import 是 `from dataclasses import dataclass`，
  `src/xuexing/standard_coverage.py:15`；不逐个列出其他标准库——源码没有用到）。
- **不 import `xuexing.types`**：KP 对象按鸭子类型只读 `.id` 与 `.standard_ref` 两个属性。
  `xuexing.types.KnowledgePoint`（`src/xuexing/types.py:13-24`，字段含
  `id/name/subject/grade/cluster/description/standard_ref/prereqs`）只是满足该形状的
  一类对象——契约测试用它构造 KP（`tests/contract/test_standard_coverage_contract.py:27,69-71`），
  但本模块不依赖、也不允许依赖其定义模块。
- 禁止：其他 xuexing 模块（无例外）、第三方库、文件/网络 IO、随机、系统时钟、
  环境读取、全局可变状态。

重生成实例的装载约束（注入门 `tests/conftest.py:22-34`：设 `XX_IMPL_DIR` 后
`<impl_dir>/standard_coverage.py` 经 `spec_from_file_location` 以顶层模块名
`_regen_standard_coverage` 装载并顶替 `sys.modules["xuexing.standard_coverage"]`）：

- **禁止相对导入**：装载模块是顶层名 `_regen_standard_coverage`，无父包（同 kt 规格实测
  的 `ImportError` 失败模式；本门与全部模块共用，见 `tests/conftest.py:34`）。
- **禁止 `from __future__ import annotations`**：本冻结轮实测，带该行的变体在本门装载下
  抛 `AttributeError: 'NoneType' object has no attribute '__dict__'`
  （`dataclasses.py:749/983`——注入注册名是 `xuexing.standard_coverage`，而 dataclass 的
  `__module__` 是 `_regen_standard_coverage`，`sys.modules.get` 得 `None`）。
  注解直接写真实对象（本模块注解均为内建 `str`/`tuple`）。
- **原样拷贝经注入门实测可运行**：参考实现 `standard_coverage.py` 未改一字，
  经注入门契约测试 19 passed。

## 3. 公开 API

模块必须暴露以下 8 个名字（契约测试 import 清单，
`tests/contract/test_standard_coverage_contract.py:17-26`）：`StandardCoverageError`、
`Topic`、`KPMatch`、`CoverageReport`、`parse_topics`、`match_ref`、`check_coverage`、
`check_coverage_dicts`（`__all__` 恰为这 8 个）。

### 3.1 `StandardCoverageError(ValueError)`

本模块唯一异常类型，`ValueError` 直接子类（`issubclass` 由
`test_parse_topics_rejections` 断言，tests:132）。契约内一切校验失败都抛它；
除此之外唯一可能出现的原生异常是 §6 表列的 `AttributeError`/`TypeError`。
异常消息文案不是契约面，不作承诺。

### 3.2 `Topic`

```python
@dataclass
class Topic:
    id: str
    name: str
    domain: str
    theme: str
    requirement: str
    aliases: tuple     # 检索关键词，非空 tuple
```

- 支持按位置构造（`Topic("t", "n", "d", "th", "r", ("a",))`）；构造时不校验。
- dataclass 逐字段相等是记录比较方式（`parse_topics` 的纯度/确定性断言即用，
  tests:97-101）。`domain`/`theme` 由所在层级注入（条目自身不携带这两字段的输入键）。

### 3.3 `parse_topics(data) -> list[Topic]`

解析课标主题清单 dict，返回**拍平**后的 `Topic` 列表。

**输入结构（逐层绑定）**：`data` 为 dict，含非空 list `domains`；每个 domain 为 dict，
含非空字符串 `domain`（域名）与非空 list `themes`；每个 theme 为 dict，含非空字符串
`theme` 与非空 list `topics`；每个 topic 为 dict。

**topic 字段校验**（任一失败 → `StandardCoverageError`）：

- `id`/`name`/`requirement`：非空白字符串（`str.strip()` 非空）；**不做 strip**，
  原值进 `Topic`。
- `aliases`：非空 `list`；每个元素为非空字符串且**无首尾空白**
  （`alias != alias.strip()` 即拒）；alias **全局唯一**（跨条目重复即拒）；
  解析时转成 `tuple`（原 list 不改输入对象的值形态）。
- topic `id` **全局唯一**（跨域跨主题重复即拒）。

**输出**：拍平序 = domains 原序 → themes 原序 → topics 原序（深度优先，不排序、
不重排、不跨层归并）。`Topic.domain`/`Topic.theme` 取所处层级名。

实测例（契约夹具 `topic_data`，tests:32-61）〔测试裁定
`test_parse_topics_flatten_order_and_fields`〕：

- `parse_topics(topic_data)` → `[t.id for t in topics] == ["t_lin","t_fun","t_tri","t_cir"]`
  （数与代数在图形与几何前；同域的方程与不等式主题在函数主题前）；
- `topics[0].domain == "数与代数"`、`topics[0].theme == "方程与不等式"`、
  `topics[0].requirement == "能解一元一次方程"`、
  `topics[0].aliases == ("一元一次方程", "列方程")`（list → tuple）；
- `topics[3].domain == "图形与几何"`；全部元素 `isinstance(t, Topic)` 且
  `isinstance(t.aliases, tuple)`。

**纯度**：不改输入（深快照前后相等）；两次解析结果相等（tests:97-101）。

### 3.4 `match_ref(ref, topics) -> tuple[str, ...]`

单个 `standard_ref` 的归属。参数：`ref` 为 `str | None`；`topics` 为非空条目序列。

**校验次序（绑定）**：先查 `topics` 为空（`[]`/`()`）→ `StandardCoverageError`
（先于 ref 一切检查：`match_ref("x", [])` 抛错而非返回 `()`）；`ref is None` →
`()`；`ref` 非 `str` → `StandardCoverageError`；`ref` 全空白 → `()`。

**匹配规则**：条目 `t` 命中 ⟺ `t.aliases` 中存在 `a` 使 `a in ref`（Python 连续子串
判定——**大小写敏感、不做任何归一化/分词/模糊化**）。返回命中条目的 id 元组：
**按 topics 原序**、每条目至多出现一次（同条目多个 alias 都命中只记一次）。

实测例〔测试裁定〕：

- `match_ref("2022课标：能解一元一次方程", topics) == ("t_lin",)`；
  `match_ref("2022课标：能根据实际问题列方程", topics) == ("t_lin",)`（第二 alias 命中，
  tests:141）；
- `match_ref("2022课标：掌握全等三角形与内角和", topics) == ("t_tri",)`（全等、内角和
  两个 alias 同条目，去重为一条，tests:140,146）；
- `match_ref("2022课标：圆与全等三角形内角和", topics) == ("t_tri", "t_cir")`
  ——**清单原序，不是 ref 中出现顺序**（ref 里圆在前，tests:148）；
- 把 t_cir 的 aliases 反转后同一 ref 结果不变（alias 声明序无关，tests:151-155）；
- `match_ref(None/"", "   ", "2022课标：超纲内容", topics) == ()`（tests:159-162）；
  `match_ref(123, topics)` → `StandardCoverageError`（tests:163-164）。

### 3.5 `KPMatch`

```python
@dataclass
class KPMatch:
    kp_id: str
    topic_ids: tuple   # 清单原序、条目内去重后的命中条目 id
```

按位置构造（`KPMatch("z1", ())`，tests:267）；逐字段相等。

### 3.6 `check_coverage(kps, topics) -> CoverageReport`

KP 对象序列 × 条目清单 → 对照报告。

**参数契约**：

- `topics` 为空（`[]`/`()`）→ `StandardCoverageError`（**先于**任何 KP 检查，
  tests:232-234）。
- `kps`：可迭代（参考实现 `list(kps)` 单遍物化，`src/xuexing/standard_coverage.py:181`；
  〔参考裁定〕生成器等一次性可迭代可用，契约测试域为 list）。
- 每个 KP 按鸭子类型读 `.id` 与 `.standard_ref`（`KnowledgePoint` 即满足）。缺属性 →
  **原生 `AttributeError` 传播**，不包装（tests:248-255）。

**逐 KP 校验**（按输入序，遇首个非法即抛）：

- `kp.id` 非 `str` 或空白 → `StandardCoverageError`（tests:229）；
- `kp.id` 与已见 id 重复 → `StandardCoverageError`（tests:225-227）；
- `kp.standard_ref` 为 `None` → 视为空串（未归属）；非 `str` 非 `None` →
  `StandardCoverageError`（tests:248-249 与 src:193-198）。

**匹配**：与 `match_ref` 同一子串规则（每 KP 独立对清单求命中）。

**输出顺序（绑定）**：`matches` 按 `kps` 输入原序；`unmatched_kp_ids` /
`matched_kp_ids` 按输入原序；`uncovered_topic_ids` / `covered_topic_ids` /
`topics` 按清单原序。不改入参（对象与序列都不动）。

**闭式例**（夹具 `kps` = k1..k4，k4 的 ref 为空白 `"  "`）〔测试裁定
`test_check_coverage_closed_form`〕：

```python
rep = check_coverage(kps, topics)
rep.matches == (
    KPMatch(kp_id="k1", topic_ids=("t_lin",)),
    KPMatch(kp_id="k2", topic_ids=("t_tri",)),
    KPMatch(kp_id="k3", topic_ids=("t_fun",)),
    KPMatch(kp_id="k4", topic_ids=()),
)
rep.uncovered_topic_ids == ("t_cir",)          # 覆盖缺口，清单原序
rep.unmatched_kp_ids == ("k4",)                # 归属缺口，输入原序
rep.matched_kp_ids == ("k1", "k2", "k3")
rep.covered_topic_ids == ("t_lin", "t_fun", "t_tri")
rep.topics == tuple(topics)
rep.coverage_rate == 3 / 4                     # == 0.75
rep.is_complete() is False
```

**输入序例**〔测试裁定 `test_check_coverage_kp_input_order`〕：`kps` 反转后
`matches` 序为 `["k4","k3","k2","k1"]`、`unmatched_kp_ids == ("k4",)`、
`matched_kp_ids == ("k3","k2","k1")`——KP 侧输出随输入序，条目侧不变。

**空 KP 库**合法（tests:217-222）：`matches/unmatched/matched == ()`，
`uncovered == ("t_lin","t_fun","t_tri","t_cir")`，`coverage_rate == 0.0`，
`is_complete() is False`。**全命中例**（tests:208-214）：单个 mega KP 的 ref 含全部
四类关键词 → `topic_ids == ("t_lin","t_fun","t_tri","t_cir")`，双侧缺口均为 `()`，
`coverage_rate == 1.0`，`is_complete() is True`。

### 3.7 `CoverageReport`

```python
@dataclass
class CoverageReport:
    topics: tuple              # 输入清单的 Topic 对象元组（清单原序）
    matches: tuple             # 每 KP 恰一项，输入原序
    uncovered_topic_ids: tuple # 无任何 KP 命中的条目 id（覆盖缺口），清单原序
    unmatched_kp_ids: tuple    # 零命中的 KP id（归属缺口），输入原序
    matched_kp_ids: tuple      # 有命中的 KP id，输入原序
    covered_topic_ids: tuple   # 被至少一个 KP 命中的条目 id，清单原序
```

- 六字段均为 `tuple`（不可变：对其 `append` 抛原生 `AttributeError`，
  tests:241-244）；dataclass 逐字段相等是报告比较方式（`test_dicts_entry_equivalence`
  的直接相等断言即用，tests:264）。
- `coverage_rate`（property，非字段）：`len(covered_topic_ids) / len(topics)`，
  IEEE 754 除法唯一结果。经契约入口 `topics` 必非空（构造前置校验保证）；
  **直接构造 `CoverageReport(topics=())` 再取 `coverage_rate` 会抛原生
  `ZeroDivisionError`——该路径不在契约域**〔参考裁定，src:70-73〕。
- `is_complete() -> bool`：`not uncovered_topic_ids and not unmatched_kp_ids`
  （双向均无缺口时为 True；恒返回 bool）。

### 3.8 `check_coverage_dicts(kp_dicts, topics_data) -> CoverageReport`

knowledge json 形状的便捷入口（`kp_dicts` 为 dict 列表，`topics_data` 为
`parse_topics` 接受的清单 dict）。

**处理次序（绑定）**：先 `topics = parse_topics(topics_data)`（清单非法 →
`StandardCoverageError`，tests:282-283）；再校验 `kp_dicts` 须为 `list` 或 `tuple`
（否则 `StandardCoverageError`，src:230-231；tuple 为参考实现行为，测试域为 list）；
逐条目：非 dict → 错；缺 `"id"` 或 id 非非空 str → 错；`"standard_ref"` 可省略
（缺省 = None = 空），为 `str` 或 `None`，其他值 → 错（经 `check_coverage` 的
ref 校验，tests:280-281）；其余键忽略。内部以 dataclass `_KPLike(id, standard_ref)`
适配后转 `check_coverage`。

**入口等价**：`kp_dicts` 由 KP 对象逐字段搬来（`{"id":…, "standard_ref":…}`）时，
`check_coverage_dicts(kp_dicts, topic_data) == check_coverage(kps, topics)`
（逐字段相等，tests:260-264）〔测试裁定〕。缺省 ref 例：`[{"id": "z1"}]` →
`unmatched_kp_ids == ("z1",)` 且 `matches == (KPMatch("z1", ()),)`（tests:266-267）。
空 `kp_dicts`（`[]`）合法：全覆盖缺口（tests:272-273）。

## 4. 不变量（编号列出，全部可被契约测试检验）

- I1 **拍平序与字段透传**：`parse_topics` 输出序 = domains→themes→topics 的原序
  深度优先；`domain`/`theme` 由层级注入；`aliases` list→tuple；其余字段原值透传
  （`test_parse_topics_flatten_order_and_fields`）。
- I2 **清单解析纯度与确定性**：不改输入（深快照相等）；同输入两次解析逐字段相等
  （`test_parse_topics_pure_and_deterministic`）。
- I3 **清单校验全集**：结构逐层存在且非空；topic id/name/requirement 非空字符串；
  aliases 非空列表且元素为无首尾空白的非空字符串；topic id 全局唯一、alias 全局
  唯一；一切失败抛 `StandardCoverageError`（`ValueError` 子类）
  （`test_parse_topics_rejections`，14 种变异 + 4 种顶层非法值全覆盖）。
- I4 **匹配规则**：归属 = 条目任一 alias 是 ref 的连续子串（纯子串、大小写敏感、
  无归一化）；同条目多 alias 命中去重为一条；命中 id 元组按清单原序，与 ref 中
  出现顺序无关、与 alias 声明顺序无关（`test_match_ref_basic`、
  `test_match_ref_dedup_and_topic_list_order`、
  `test_match_ref_alias_declaration_order_irrelevant`）。
- I5 **match_ref 边界**：`ref` 为 None/空串/全空白 → `()`；`topics` 为空 →
  `StandardCoverageError`（先于 ref 检查）；`ref` 非 str → `StandardCoverageError`
  （`test_match_ref_blank_and_type`）。
- I6 **报告闭式值**：`check_coverage` 六字段对夹具的逐位值（§3.6 闭式例）：
  matches 逐 KP 一项、输入原序；uncovered/unmatched/covered/matched 四元组值与
  `coverage_rate == 3/4`、`is_complete() is False`（`test_check_coverage_closed_form`、
  `test_check_coverage_complete`、`test_check_coverage_empty_kps`）。
- I7 **排序规则**：KP 侧输出（matches/unmatched/matched）随 `kps` 输入序；
  条目侧输出（topics/uncovered/covered）恒按清单原序；输入反转不改变条目侧
  （`test_check_coverage_kp_input_order`）。
- I8 **双向分划完备**：`set(matched) | set(unmatched) == KP 全集` 且不相交；
  `set(covered) | set(uncovered) == 条目 id 全集` 且不相交；
  `coverage_rate == len(covered)/len(topics)`（`test_coverage_partitions_and_rate`）。
- I9 **KP 侧校验与容忍**：kp id 空/非 str/重复 → `StandardCoverageError`；
  空 `topics` → `StandardCoverageError`；`standard_ref` 为 None/缺失键 → 容忍视为空；
  ref 非 str 非 None → 拒；**缺 `.standard_ref`/.id 属性 → 原生 `AttributeError`
  传播**（`test_check_coverage_duplicate_kp_id`、`test_check_coverage_empty_topics`、
  `test_check_coverage_none_ref_and_missing_attr`、`test_dicts_entry_validation`）。
- I10 **对照纯度与输出不可变**：`check_coverage` 不改 KP 入参（深快照相等）；
  报告字段为 tuple，`append` 抛 `AttributeError` 且不影响已产出记录
  （`test_check_coverage_purity`）。
- I11 **dict 入口等价与校验**：`check_coverage_dicts` 与 `check_coverage(parse_topics)`
  逐字段相等；`standard_ref` 键缺省视为空；`kp_dicts` 非 list/tuple、条目非 dict、
  id 缺失/空 → `StandardCoverageError`；`topics_data` 非法 → 经 `parse_topics` 拒
  （`test_dicts_entry_equivalence`、`test_dicts_entry_validation`）。
- I12 **确定性**：同 `(kps, topics)` 两次调用报告相等；同 `(kp_dicts, topics_data)`
  两次调用相等（`test_determinism`）。

## 5. 确定性与随机性

- 全部公开函数为纯函数：输出只依赖入参；禁止 `random`、hash 序、系统时钟、
  环境读取、文件/网络 IO、全局可变状态。全模块无时间戳字段（无豁免）。
- 输出形态全部确定化：清单为 `list`、id 元组与报告字段为 `tuple`；顺序规则 =
  条目侧清单原序、KP 侧输入原序（I7）；同输入同输出（I12）。
- 唯一浮点运算 `coverage_rate` 为 IEEE 754 除法唯一结果；§3.6/§3.8 中每个值都是
  逐位比对点。
- `parse_topics` 不做任何排序/去重/合并（唯一性校验除外）；匹配无随机源，
  同一 ref 对同一清单的命中集合唯一。

## 6. 错误行为

| 非法输入 | 行为（时机） |
|---|---|
| `data` 非 dict（`{}`、`None`、`"not-a-dict"`） | `parse_topics` 入口即抛 `StandardCoverageError` |
| 缺 `domains` / `domains` 非 list / 空 `domains` | 同上 |
| domain 非 dict / `domain` 名空白 / `themes` 非 list 或空 | 遍历至该层时抛 `StandardCoverageError` |
| theme 非 dict / `theme` 名空白 / `topics` 非 list 或空 | 同上 |
| topic 非 dict | 同上 |
| topic `id`/`name`/`requirement` 缺失、非 str 或空白 | 同上 |
| `aliases` 非 list / 空 / 含非 str / 含空白串 / 含首尾空白元素 | 同上 |
| topic `id` 跨条目重复 | 同上（全局 id 唯一） |
| alias 跨条目重复 | 同上（全局 alias 唯一） |
| `match_ref` 的 `topics` 为空 | 抛 `StandardCoverageError`，**先于** ref 检查 |
| `match_ref` 的 `ref` 非 str（如 `123`） | 抛 `StandardCoverageError` |
| `match_ref` 的 `ref` 为 None/空串/全空白 | 容忍，返回 `()` |
| `check_coverage` 的 `topics` 为空 | 抛 `StandardCoverageError`，**先于**任何 KP 检查 |
| kp `id` 非 str / 空白 / 与已见 id 重复 | 按输入序遇首个即抛 `StandardCoverageError` |
| kp `standard_ref` 非 str 且非 None | 抛 `StandardCoverageError` |
| kp 缺 `.id` / `.standard_ref` 属性 | **原生 `AttributeError` 传播**（不包装、不吞） |
| `kps` 不可迭代（如 `None`）〔参考裁定，测试未覆盖〕 | 原生 `TypeError` 传播 |
| `check_coverage_dicts` 的 `kp_dicts` 非 list/tuple | 抛 `StandardCoverageError`（清单先解析；两者同时非法时清单错先抛） |
| `kp_dicts` 条目非 dict / 缺 `"id"` / id 空或非 str | 抛 `StandardCoverageError` |
| `kp_dicts` 条目的 `standard_ref` 非 str 非 None | 经 `check_coverage` 抛 `StandardCoverageError` |
| `topics_data` 非法（如 `{"domains": []}`） | 经 `parse_topics` 抛 `StandardCoverageError` |
| `kps` 为 `[]` / `kp_dicts` 为 `[]` | 合法：双侧 KP 类输出空，uncovered = 全清单，rate 0.0 |
| `standard_ref` 键缺省 / None / 空白串 | 容忍，视为空（进 unmatched） |
| 直接构造 `CoverageReport(topics=())` 取 `coverage_rate`〔参考裁定〕 | 原生 `ZeroDivisionError`（契约入口不可达） |

异常类型一律 `StandardCoverageError`（`ValueError` 直接子类）或上表明列的原生
`AttributeError`/`TypeError`/`ZeroDivisionError`；契约内输入不抛其他异常。

## 7. 非目标

- **不做模糊/语义匹配**：仅纯子串（`alias in ref`），大小写敏感；不做归一化、
  分词、同义词、编辑距离、LLM 语义判定；`"圆"` 不命中 `"圆形"` 之外的一切变体
  都不承诺（严格按子串）。
- **不做权重与命中统计**：不记录命中 alias 数、命中次数、匹配位置；一个 KP 对
  一条目只记 id 一次。
- **不做层级聚合**：只输出条目级缺口与总 `coverage_rate`；不产 theme/domain
  维度的子覆盖率、不做「必考/选考」权重或优先级排序。
- **不改写入参数据**：不补全、不清洗、不规范化 `standard_ref`（None/空白即空）；
  不做 KP 排序/去重/合并（重复 kp id 是错误，不是去重信号）。
- **不读文件、不接其他模块**：`topics_data` 由调用方以 dict 传入；不 import
  `xuexing.types`、`xuexing.itembank`、`xuexing.kpgraph` 或任何数据装载器；
  无持久化、无网络。
- **不做下游动作**：只产对照报告；不出推荐、调度、判分、通知。
- **不做多租户/国际化**：无租户维度、无语言分支、无时间/日历概念。
