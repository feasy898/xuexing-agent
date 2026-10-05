# asr_answer 模块规格（冻结契约）

> 本文档是唯一权威契约。任何实现（参考实现或重生成实例）只要通过 tests/contract/ 全部测试
> 且满足本文全部条款，即为合格实现。实现算法自由，行为不允许偏离。
>
> **版本**：冻结 v1（第三波冻结）。标注「〔测试裁定〕」的行为由
> `tests/contract/test_asr_answer_contract.py`（25 项）直接断言；标注「〔参考裁定〕」的行为
> 契约测试未仲裁，按参考实现 `src/xuexing/asr_answer.py` 冻结，并在当地注明本轮实测证据。
> 未标注裁定的实测例子同样取自参考实现并有测试对照。本文自包含：不引用仓库内其他规格文档。
>
> 冻结基线：参考实现 + 契约测试全量实测于 2026-10-02，CPython 3.12.10 x64
> （`.venv/Scripts/python.exe -m pytest tests/contract/test_asr_answer_contract.py -q`
> → **25 passed**）。

## 1. 目的

asr_answer 是口述作答的确定性内核（BACKLOG P3「asr_answer 口述作答」）：把学生语音
（音频字节）经**注入的** ASR 客户端恰好一次转写成文本后，用**确定性**口语答案抽取
（清洗规则表 + 口语数字文法，全部闭式、手算可复核）得到候选答案，交给**注入的**判分器
产出作答结果。行为契约：**抽取不偷看题目**（`clean_transcript`/`spoken_to_math`/
`extract_answer` 只吃转写文本，与 item 无关，不用标答反推答案）、**不伪造作答**
（清洗后可抽取内容为空时交 `grader(item, None)`，与未作答语义一致）、**出网纪律**
（守卫全过时 `client.asr` 恰好一次；守卫失败零次）、**判分衔接**（与 `grading` 的数值/
字面/选项判分语义跨模块锁定）。全模块纯函数：无 IO、无随机、无时钟、不读环境
（唯一外部效果是一次注入的 `client.asr` 调用）；模块间零 import——`client` 与 `grader`
都是注入鸭子参数，与 `mm_client`/`grading` 的一致性由契约测试在测试内 import 对方模块
跨模块锁定（I5/I7）。

## 2. 允许的依赖

- Python 标准库：参考实现只 import `re`（`asr_answer.py:20`），且全模块无一处 `re.`
  调用（本轮 `grep -n "re\." src/xuexing/asr_answer.py` 无命中）——全角折叠是手写循环
  （`asr_answer.py:85-95`）。故标准库对本模块**零必需**：合格实现可以不 import 任何
  标准库；若 import，只允许标准库。
- `xuexing.types`：本模块**不 import**（参考实现的 import 清单与契约测试的 import 清单
  均无 `xuexing.types`）。`item` 与判分结果（`Response`）都是调用方传入/返回的鸭子对象，
  只按 §3.5 的属性表面使用，不得 import 其定义模块。
- 禁止：其他 xuexing 模块（**无例外**——不 import `mm_client`/`grading`/`mm_ingest`
  等任何同包模块；跨模块一致性由契约测试锁定）、第三方库、文件/网络 IO、全局可变状态、
  随机源、系统时钟、环境变量读取。
- 装载约束（本轮实测，注入机制见 `tests/conftest.py:22-34`：`XX_IMPL_DIR` 下
  `<module>.py` 以顶层模块名 `_regen_asr_answer` 经 `spec_from_file_location` 装载并顶替
  `sys.modules["xuexing.asr_answer"]`）：
  - **禁止相对导入**：实测桩模块 `from .types import Response` 在装载期抛
    `ImportError: attempted relative import with no known parent package`
    （`tests/conftest.py:34` `exec_module` 处）。
  - `from __future__ import annotations` 对本模块装载无影响（本模块无 dataclass）：实测
    带该语句的桩模块可正常装载，测试失败全部是行为断言而非装载错误。参考实现按同族约定
    不写它（`asr_answer.py:18-19`），本规格不设禁令。

## 3. 公开 API

模块必须暴露以下 10 个名字（契约测试以
`from xuexing.asr_answer import ASRError, ASR_VERSION, DEFAULT_FILENAME, EDGE_CHARS,
HEAD_FILLERS, SPOKEN_OPERATORS, asr_answer, clean_transcript, extract_answer, spoken_to_math`
导入，`test_asr_answer_contract.py:15-26`）。

### 3.1 常量与异常

- `ASRError(ValueError)`：本模块唯一异常类型，`ValueError` 的**直接**子类
  （`asr_answer.py:36-37`）〔测试裁定 `test_frozen_constants:89`〕。
- `ASR_VERSION = "1"`（`str`）：版本印记常量，值逐字符冻结〔测试裁定:87〕。参考实现中
  不被任何函数引用、也不出现在任何输出字段中（实测：源码无引用点）；本规格只承诺其导出
  值与类型，不承诺任何派生语义。
- `DEFAULT_FILENAME = "audio.wav"`（`str`）：`asr_answer` 的 `filename` 缺省值，同时与
  `mm_client.MMClient.asr` 的 `filename` 缺省**跨模块相等**——契约测试以
  `inspect.signature(MMClient.asr).parameters["filename"].default` 取值并断言
  `DEFAULT_FILENAME == default == "audio.wav"`〔测试裁定:109-113〕。
- `EDGE_CHARS = frozenset(...)`：`clean_transcript` 的上下缘可剥离字符集合，成员为
  `\"'“”‘’。，、…·.,;:!?()嗯呃唉哦噢喔吧了呢啦咯嘛呀哈啊`（全角折叠**之后**的形态）。
  集合语义——只做成员判断，不承诺迭代顺序〔测试裁定:91-92〕。
- `HEAD_FILLERS`（`tuple[str, ...]`）：句首引导语词表，**值与顺序都冻结**，且长度
  **非增序**（契约测试逐项断言元组相等，并断言 `[len(f) for f in HEAD_FILLERS] ==
  sorted(..., reverse=True)`）。因长度非增，`clean_transcript` 的「表中首个前缀命中」
  即**最长前缀命中**，等长时按表序决胜〔测试裁定:94-101〕。冻结表：

  ```text
  我认为答案是, 我觉得答案是, 我的答案是, 所以答案是,
  我选的是, 答案等于, 答案是, 选的是,
  答案, 选择, 所以, 我选, 等于, 就是,
  答, 得, 选
  ```

- `SPOKEN_OPERATORS`（`tuple[tuple[str, str], ...]`）：口语算符 → 数学符号映射表，
  **值与顺序都冻结**；匹配按表序取首个前缀命中，因表本身按长度非增排列，等价于
  **前缀最长优先**（`乘以` 先于 `乘`；表内无「除」单词项，「除以」是唯一以「除」开头
  的表项）。
  冻结表：`("等于","="), ("乘以","*"), ("除以","/"), ("乘","*"), ("加","+"), ("减","-")`
  〔测试裁定:103-106〕。注意「除」单词**不入表**（「三除五」歧义大，不透传也不转换）。

### 3.2 `clean_transcript(text) -> str`

ASR 转写文本 → 清洗后的口语串。**冻结流程（顺序为绑定条款）**（`asr_answer.py:110-130`）：

1. 非 `str` 入参 → `ASRError`〔测试裁定 `test_non_str_inputs_raise_asr_error:235-239`〕。
2. **全角折叠**：码点 ∈ `[0xFF01, 0xFF5E]` 的字符映射为 `chr(cp − 0xFEE0)`，
   `U+3000` 全角空格 → 半角空格，其余字符原样保留。与 `grading.normalize_answer` 的
   N1 **同闭式**（逐行对照：`asr_answer.py:85-95` vs `grading.py:66-76`）；只做折叠，
   **不做** grading 的 N2 内部空白折叠、N3 尾部剥离、N4 千分位逗号、N5 小写化。
3. **首尾空白剥离**（Python `str.strip()` 语义；**仅在进入循环前做一次**，循环本身
   **不**含 `.strip()`）。
4. **循环到不动点**（绑定条款）：
   - 状态 `s` 初始为第 3 步的结果；
   - 每次迭代（按序）：
     a) 剥 `s` 的**上下缘**字符：左端从下标 0 起连续跳过 `EDGE_CHARS` 成员，右端从
        下标 `len(s)-1` 起连续跳过 `EDGE_CHARS` 成员，**两侧各剥一段连续的同集合字符**，
        不接触内部；
     b) **只剥一个**句首引导语：按 `HEAD_FILLERS` 表序遍历，**首个**前缀命中即剥
        （长度非增序 ⇒ 等价于最长命中；等长时按表序决胜），命中即跳出；无命中则不动；
     c) 再剥一次上下缘（同 a 步骤）；
   - 若本次迭代结束时 `s` 与迭代开始时**相等**，返回 `s`（不动点）；否则继续循环。
5. 引导语**只在头部**剥、标点**只在上下缘**剥——`「x等于3」` 的「等于」不在头部、
   `「-2」` 的负号不在缘集合，核心内容不被触碰。

行为对照〔测试裁定 `test_clean_transcript_fold_and_edges:118-126`〕：
`clean_transcript("Ｂ。") == "B"`、`clean_transcript("（Ａ）") == "A"`、
`clean_transcript("３．５。") == "3.5"`、`clean_transcript("“负二”") == "负二"`、
`clean_transcript("五。。") == "五"`、`clean_transcript("嗯，答案是三。吧") == "三"`、
`clean_transcript("  十二  ") == "十二"`、`clean_transcript("　五　") == "五"`。

引导语表全行对照〔测试裁定 `test_clean_transcript_head_fillers_table:129-140`〕：
`("我认为答案是八","八")`、`("我觉得答案是B","B")`、`("我的答案是负二","负二")`、
`("所以答案是五","五")`、`("我选的是C","C")`、`("答案等于四十","四十")`、
`("答案是三点五","三点五")`、`("选的是A","A")`、`("答案40","40")`、`("选择B","B")`、
`("所以十","十")`、`("我选D","D")`、`("等于七","七")`、`("就是二分之一","二分之一")`、
`("答：-2","-2")`、`("得六","六")`、`("选B了","B")`。

核心内容保护〔测试裁定 `test_clean_transcript_preserves_core_content:143-148`〕：
`clean_transcript("x=3") == "x=3"`、`clean_transcript("x等于3") == "x等于3"`、
`clean_transcript("-2") == "-2"`、`clean_transcript("0.5") == "0.5"`、
`clean_transcript("1 1/2") == "1 1/2"`（内部空白不折叠）。

〔参考裁定〕以下闭式由第 4 步的循环规则唯一确定（手算可复核）：

- **半角空格不在 `EDGE_CHARS` 中**，故循环内 `_strip_edges` 不会跨越空格；首尾空白
  一旦在第 3 步未被消化，第 4 步循环也**不再**额外 `.strip()`，因此返回值**可能残留
  首尾空白**：`clean_transcript("嗯 三") == " 三"`（前导空格）、
  `clean_transcript("答案 是三") == " 是三"`。`extract_answer` 末尾的 `.strip()` 才是
  把它们抹掉的一步（`extract_answer("嗯 三") == "3"`）。
- **多段引导语被连续剥**至不动点：`clean_transcript("答案答案是三") == "三"`、
  `clean_transcript("答得选") == ""`（空串也是合法不动点，函数返回 `""`，由
  `extract_answer` 翻成 `None`）。

### 3.3 `spoken_to_math(text) -> str`

口语串 → 数学记号串。**逐位置扫描，优先级为绑定条款**（`asr_answer.py:239-265`）：

1. 非 `str` 入参 → `ASRError`〔测试裁定 `test_non_str_inputs_raise_asr_error`〕。
2. **数表达式**（`_number`，最大匹配，见下方文法）命中 → 追加其串形式、前进到其结束下标；
3. 否则**口语算符**（`SPOKEN_OPERATORS` 表序前缀匹配，因表序 = 最长优先）→ 追加符号；
4. 否则**当前字符原样透传**、前进一位。
5. **不做全角折叠**（折叠只发生在 `clean_transcript`）：本函数对每个字符判定为「数字/
   单位/算符/其他」后**直接透传原码点**，不做 `[0xFF01,0xFF5E] → 半角` 折叠
   〔参考裁定：本轮实测 `spoken_to_math("Ｂ") == "Ｂ"`〕；全角作答的折叠是
   `extract_answer` 管线第一步 `clean_transcript` 的功劳
   （`extract_answer("选择Ｂ") == "B"`〔测试裁定:360〕）。
6. **不求值**：`spoken_to_math("三加五") == "3+5"` 而不是 `8`〔测试裁定:190〕；
   单位词（厘米/升/元/平方米……）与未知文本透传，交判分器的单位门/字面支
   （`spoken_to_math("5平方米") == "5平方米"`〔测试裁定:196〕）。

**口语数字文法（冻结，闭式手算可复核）**（`asr_answer.py:69-78`、`135-236`）：

- 数字字符 = `零〇一二两三四五六七八九` + ASCII `0-9`，按位累积（`两`=2）。
- `十/百/千` 为**段内单位**，缺系数按 1：`十二`=12、`十`=10。
- `万/亿` 为**大段单位**，必须有非零前值；孤立「万/亿」不是数，逐字符透传
  （`spoken_to_math("万三") == "万3"`〔参考裁定，实测〕）。
- `零` 作占位；**显式单位文法（不约算）**：`一百五` = **105**（不是口语约算的 150）。
- `点` → 逐位小数：`三点一四`=3.14、`零点零五`=0.05。
- `分之` → 分数（分母整数、分子可带小数）：`三分之二`=2/3、`二十分之十三`=13/20。
- `又` → 带分数，整数部与分数之间以**单个半角空格**分隔：
  `一又二分之一`=`1 1/2`、`二又三分之一`=`2 1/3`。
- `百分之` → 百分数（追加 `%`）：`百分之五十`=50%、`百分之十二点五`=12.5%。
- `负` → **恰修饰一次**的前缀负号：`负二`=-2、`负百分之五十`=-50%；
  `负负二` → `负-2`（第一个「负」后面跟的不是数，透传；第二个构成 `-2`）
  〔测试裁定:200〕；孤立「负」透传〔测试裁定:197〕。
- 数表达式内部优先级：`百分之` → `又`（带分数）→ `分之`（分数）→ 整数/小数。

文法全表对照〔测试裁定 `test_spoken_to_math_integers:153-163`〕：
`十二`=12、`二十三`=23、`一百零五`=105、`两千零三十`=2030、`十`=10、`零`=0、`两`=2、
`一万零一十`=10010、`3分之2`=`2/3`（ASCII 数字入文法）、`103`=103。
〔测试裁定 `test_spoken_to_math_decimals_and_fractions:166-175`〕：
`三点一四`=3.14、`零点五`=0.5、`二点五`=2.5、`零点零五`=0.05、`三分之二`=2/3、
`十分之一`=1/10、`二十分之十三`=13/20、`一又二分之一`=`1 1/2`、`二又三分之一`=`2 1/3`。
〔测试裁定 `test_spoken_to_math_percent_negative:178-185`〕：`百分之五十`=50%、
`百分之百`=100%、`百分之十二点五`=12.5%、`负二`=-2、`负零点五`=-0.5、
`负三分之二`=-2/3、`负百分之五十`=-50%。
〔测试裁定 `test_spoken_to_math_operators_and_passthrough:188-200`〕：
`x等于3`=`x=3`、`三加五`=`3+5`、`10减4`=`10-4`、`二乘以三`=`2*3`、`2乘3`=`2*3`、
`六除以二`=`6/2`、`B`=`B`、`5平方米`=`5平方米`、`负`=`负`、`点`=`点`、`万`=`万`、
`负负二`=`负-2`。

〔参考裁定：以下闭式由冻结文法唯一确定，手算可复核〕

- `三又五` → `3又5`：「又」后面不是分数文法（缺 `分之` 分子），回落为整数前缀 + 「又」
  单字符透传。
- `百分之负五十` → `100分之-50`：`百分之` 后面必须紧跟一个合法 `decimal_prefix`，否则
  整条百分数支不命中、回到「百」段内单位读数 + 后续逐字符透传（`百` 段内单位得 100，
  `分`/`之` 非字符集 → 透传，`负五十` 由 `_number` 的「负 + 数」规则合成 `-50`）。
- `一千万` → `10000000`：整数前缀一次性消费「一千」×`万` 大段单位，得 10,000,000。
- `三点五零` → `3.50`：整数前缀给 3；遇 `点` 进入小数分支，**逐位**消费 `五`/`零`，
  末尾的 `零` 不折叠也不剥。
- 〔参考裁定，与上述同源：`spoken_to_math("万三") == "万3"`（孤立大段单位，无前置整数，透传）〕

> 这五条都不是任意行为——任何严格按本节文法的实现都会得到同样的字符串。盲实现者只要把
> 文法按子句抄齐，无需猜测。

### 3.4 `extract_answer(text) -> str | None`

ASR 转写文本 → 候选答案串；**清洗后可抽取内容为空 → `None`**（无作答证据，不伪造）。
冻结流程（`asr_answer.py:270-280`）：

1. 非 `str` 入参 → `ASRError`〔测试裁定 `test_non_str_inputs_raise_asr_error`〕。
2. `clean_transcript(text)`（折叠/上下缘/句首引导语）→ `spoken_to_math(...)`
   （口语数字/算符 → 数学记号）→ `str.strip()` → 空串则 `None`。
3. **只依赖转写文本，与题目无关**（签名无 item 参数，不偷看标答）。
4. 部分可抽取时做**机械转换 + 诚实判错**：不清洗句子结构、不猜测、不反向补齐。

行为对照〔测试裁定 `test_extract_answer_pipeline_closed_forms:205-216`〕：
`("答案是负二","-2")`、`("嗯，答案是三。吧","3")`、`("我认为答案是八","8")`、
`("我的答案是负二","-2")`、`("所以答案是五","5")`、`("答案等于四十","40")`、
`("答案是三点五","3.5")`、`("所以十","10")`、`("等于七","7")`、
`("就是二分之一","1/2")`、`("得六","6")`、`("两点五升","2.5升")`、
`("十二点五厘米","12.5厘米")`、`("我选的是B","B")`、`("x等于3","x=3")`、`("选B","B")`。
无作答证据〔测试裁定 `test_extract_answer_none_when_no_evidence:219-226`〕：
`extract_answer("   ") is None`、`extract_answer("") is None`、
`extract_answer("嗯吧呢") is None`（纯语气词）、`extract_answer("答案") is None`
（纯引导语）；部分可抽取：`extract_answer("负三分之二的绝对值") == "-2/3的绝对值"`。

### 3.5 `asr_answer(audio, item, client, grader, *, filename=DEFAULT_FILENAME)`

口述作答管线入口（`asr_answer.py:285-309`）。`item` 与判分结果均为鸭子对象：`item`
**不校验、不透出、原样交给 grader**；grader 的返回值**原样返回**（不包装、不改写）。

**守卫检查顺序冻结为绑定条款**（任一失败抛 `ASRError`，且 `client.asr` 零次调用、
grader 零次调用）〔参考裁定：测试只断言「抛 `ASRError` + 零出网」
（`test_asr_answer_guards_zero_calls:268-289`），不测序；但本规格把序列本身作为契约面，
多守卫同时失败时**先命中者抛错**——即按 V1 → V2 → V3 → V4 顺序检查〕：

| 序 | 守卫 | 失败判据（绑定） | 错误消息（参考实现；非契约面，但含可观察特征） |
|---|---|---|---|
| V1 | `client` 必须有 callable 的 `asr` 属性 | `getattr(client, "asr", None)` **不可调用**（缺属性、属性为 `None`、属性为不可调用对象——包括方法被设为 `None` 的情况） | `"client must provide a callable asr()"`（不嵌入类型名） |
| V2 | `grader` 必须 callable | `callable(grader)` 为假（`grader is None`、`grader` 是 `int`/`str`/`bytes` 等） | `"grader must be callable"`（不嵌入类型名） |
| V3 | `audio` 必须非空 `bytes` | **`isinstance(audio, bytes) is False`** **或** `len(audio) == 0`（`None`/`int`/`str`/`bytearray`/`memoryview`/空 `bytes` 全部拒绝） | 含 `type(audio).__name__` 片段（参考实现：`f"audio must be non-empty bytes, got {type(audio).__name__}"`） |
| V4 | `filename` 必须非空白 `str` | **`isinstance(filename, str) is False`** **或** `filename.strip() == ""`（`""`/`"   "`/`None`/`int`/`bytes` 全部拒绝） | `"filename must be a non-blank str"`（不嵌入类型名） |

**注**：当前契约测试只对**单一**守卫失败形态断言；上表的「错误消息」列是**参考实现当前
冻结的文案**——本规格不把文案作为契约面，但 V3 文案会嵌入 `type(audio).__name__` 的
现象属于**可外部观测**的事实：当多守卫同时失败时（例如 `client` 缺 `asr` 且 `audio`
非 `bytes`），哪一条命中由 V1 → V2 → V3 → V4 顺序唯一决定，因此**仅 V1/V2/V4** 命中
的消息不会嵌入类型名，**仅 V3** 命中会嵌入 `type(audio).__name__`。

**随后（守卫全过）**：

1. `transcript = client.asr(audio, filename=filename)` —— **恰好一次**出网（唯一注入口），
   `audio` 位置实参、`filename` 关键字实参；`audio` 对象**原样传递**（不复制、不改写、
   不转换；`asr_answer.py:305`）。
2. 回写非 `str` → `ASRError`（此时已出网一次，但 grader 不被调用）
   〔测试裁定 `test_asr_answer_non_str_transcript:292-298`〕。
3. `return grader(item, extract_answer(transcript))` —— 抽取结果交判分器；转写空白/
   纯语气词 ⇒ `extract_answer` 返回 `None` ⇒ `grader(item, None)`（不伪造作答）
   〔测试裁定 `test_asr_answer_blank_transcript_hands_none:261-265`〕。
4. `client.asr` 抛出的异常**原样传播**（不包装成 `ASRError`），grader 不被调用
   〔测试裁定 `test_asr_answer_client_exception_propagates:301-306`〕；**grader 自身抛出的
   异常同样原样传播**〔参考裁定：本轮实测 `KeyError` 不被包装，模块不捕获、不包装、
   不改写异常链〕——即模块**从不**捕获 `client.asr` 或 `grader` 的异常，二者抛什么就
   抛什么（仅 `ASRError` 路径才是本模块自行抛出的）。

行为对照〔测试裁定 `test_asr_answer_happy_path_exact_call_shape:244-251`〕：
`asr_answer(b"AUDIO-BYTES-01", FILL_NEG2, MockASR("答案是负二"), RecGrader())` →
返回 `"GRADED"`（grader 返回值原样透传）、`client.calls == [{"audio": b"AUDIO-BYTES-01",
"filename": "audio.wav"}]`（恰好一次）、`grader.calls == [(FILL_NEG2, "-2")]`。
〔测试裁定 `test_asr_answer_filename_passthrough:254-258`〕：`filename="answer.mp3"`
时 `client.calls[0]["filename"] == "answer.mp3"`。

〔参考裁定：以下行为虽未被契约测试逐条断言，但由 §3.5 的绑定条款唯一决定，手算可复核〕

- **`filename` 空白判定只针对 `filename.strip()` 为空**：非空串内含首尾空白被**接受**
  并**原样**传给 `client.asr`（不 `.strip()`，不改写），即
  `asr_answer(b"...", item, client, grader, filename="  a.wav  ")` 时
  `client.calls[0]["filename"] == "  a.wav  "`。
- **`audio` 类型严格性**：V3 用 `isinstance(audio, bytes)` 判定，**`bytearray`** /
  **`memoryview`** 不被认作 `bytes`，**与空 `bytes` 同样拒收**——本模块不支持任何非
  `bytes` 的 buffer 协议类型。
- **`filename` 只能以关键字传入**：签名为 `asr_answer(audio, item, client, grader, *,
  filename=...)`，`*` 之后无位置参数；若调用方写 `asr_answer(b"...", item, client,
  grader, "x.wav")`，Python 解释器在绑定阶段抛 `TypeError`（消息形如
  `asr_answer() takes 4 positional arguments but 5 were given`）——这是 Python 自身的
  参数绑定机制，**不是**本模块的守卫，不属于 `ASRError` 路径。

## 4. 不变量（编号列出，全部可被契约测试检验）

- I1 **常量与异常冻结**：`ASR_VERSION == "1"`、`DEFAULT_FILENAME == "audio.wav"`、
  `ASRError` 是 `ValueError` 直接子类、`EDGE_CHARS` 的集合成员、`HEAD_FILLERS` 的值与
  长度非增序、`SPOKEN_OPERATORS` 的值与最长优序列，全部逐项冻结；`DEFAULT_FILENAME` 与
  `mm_client.MMClient.asr` 的 `filename` 缺省跨模块相等。
  〔测试裁定 `test_frozen_constants`、`test_default_filename_matches_mm_client_signature`〕
- I2 **抽取与题目无关（诚实性）**：`clean_transcript`/`spoken_to_math`/`extract_answer`
  签名只接受转写文本，行为亦只依赖转写文本；同一转写配任何 item 抽取结果恒同，不用标答
  反推答案。〔测试裁定 `test_extraction_is_item_independent`〕
- I3 **出网纪律**：守卫全过时 `client.asr` 被调用**恰好一次**，形状为
  `client.asr(audio, filename=filename)`（位置实参 + 关键字实参，`audio` 原样不改写）；
  `filename` 缺省 `"audio.wav"`，显式值原样透传。
  〔测试裁定 `test_asr_answer_happy_path_exact_call_shape`、
  `test_asr_answer_filename_passthrough`〕
- I4 **失败纪律**：V1–V4 任一失败 → `ASRError` 且 `client.asr` 零次调用、grader 零次调用
  （12 个非法调用形态全部覆盖）；转写回写非 `str` → 已一次出网但 grader 不被调用；
  client 抛出的异常原样传播不包装；三个抽取函数对 `None`/`int`/`bytes`/`list` 一律
  `ASRError`。〔测试裁定 `test_asr_answer_guards_zero_calls`、
  `test_asr_answer_non_str_transcript`、`test_asr_answer_client_exception_propagates`、
  `test_non_str_inputs_raise_asr_error`〕
- I5 **判分衔接（跨模块锁定）**：`asr_answer` 把 `(item, extract_answer(转写))` 原样交给
  grader、返回值原样返回；抽取结果满足 `grading` 语义闭式——`parse_numeric` 独立复核
  数值等值（`负二`→-2.0、`一又二分之一`→1.5、`百分之五十`→0.5、`三分之二`→2/3、
  `一万零一十`→10010.0）、`grade_fill` 真/假闭式成立（含单位答案 `两点五升` 判对、
  `二` 配 `-2` 判错）、`grade_choice` 标签/全角折叠同判（`选B` 真、`我选的是A` 假、
  `选择Ｂ` 真）、`grade` 对 `x=3` 字面直配为真而 `等于3`（引导语剥离后只剩 `3`）诚实
  判假；`grade_to_response` 产出字段正确，空白转写 ≡ 未作答
  （`learner_answer is None and correct is False`）。
  〔测试裁定 `test_numeric_equivalence_with_grading_parse_numeric`、
  `test_grade_fill_cross_module_closed_forms`、`test_grade_choice_and_solve_cross_module`、
  `test_asr_answer_with_grading_grade_to_response`〕
- I6 **抽取三段管线闭式**（子条款逐条可被对应测试检验）：
  - (a) `clean_transcript` = 全角折叠（grading N1 同闭式，不折叠内部空白、不小写化）
    → 首尾空白剥离 → 循环到不动点（剥上下缘 → 剥一个句首引导语 → 再剥上下缘）；
  - (b) 引导语只在头部剥、只剥表中首个（最长）前缀命中，标点只在上下缘剥，
    `x=3`/`x等于3`/`-2`/`0.5`/`1 1/2` 核心内容不被触碰；
  - (c) `spoken_to_math` 逐位置扫描，优先级 = 数表达式（最大匹配）> 口语算符
    （最长优先）> 单字符透传；单位词与未知文本透传；不求值；
  - (d) 口语数字文法闭式（§3.3）：缺系数按 1、`万/亿` 须有非零前值、`一百五`=105
    不约算、`点`=逐位小数、`分之`=分数、`又`=带分数（空格分隔）、
    `百分之`=百分数、`负`=恰一次前缀；
  - (e) 孤立记号（`负`/`点`/`万`）透传不成数字，`负负二`→`负-2`；
  - (f) `extract_answer` = `clean_transcript` → `spoken_to_math` → 首尾空白剥离 →
    空则 `None`；纯语气词/纯引导语 ⇒ `None`。
  〔测试裁定 `test_clean_transcript_fold_and_edges`、
  `test_clean_transcript_head_fillers_table`、
  `test_clean_transcript_preserves_core_content`、`test_spoken_to_math_integers`、
  `test_spoken_to_math_decimals_and_fractions`、`test_spoken_to_math_percent_negative`、
  `test_spoken_to_math_operators_and_passthrough`、
  `test_extract_answer_pipeline_closed_forms`、
  `test_extract_answer_none_when_no_evidence`〕
- I7 **端到端跨模块形状**：注入真 `MMClient`（`MockTransport`）时恰好一次 HTTP 调用，
  URL = `ENDPOINTS["asr"]`、`Authorization == "Bearer <key>"`、
  `content_type` 以 `multipart/form-data; boundary=` 开头、body 含 `name="model"` 与
  `MODEL_ASR`、`filename="audio.wav"`、音频字节原样入 body；同输入两次请求体**逐字节
  相同**。〔测试裁定 `test_end_to_end_mm_client_mock_transport`〕
- I8 **确定性与纯度**：全模块纯函数，同输入同输出（连跑两次的 client 调用记录、grader
  记录、返回值三者相等）；入参不被修改（audio 字节快照前后相等）；无随机、无时钟、
  无环境读取、无 IO（唯一外部效果是一次注入的 `client.asr` 调用）。
  〔测试裁定 `test_asr_answer_deterministic_and_inputs_unmutated`〕

## 5. 确定性与随机性

- 四个公开函数都是纯函数：输出只依赖入参。禁止 `random`、hash 序、系统时钟、环境读取、
  文件/网络 IO、全局可变状态；模块内**无任何算术运算**（抽取全程为字符串操作，不产生
  浮点中间值），故无舍入/容差/逐位浮点对照问题——每个抽取结果都是逐字符确定的串。
- 唯一的非确定性来源在模块外：注入的 `client.asr`。模块对它的纪律是 §3.5 的「守卫全过
  恰好一次 + 回写类型校验 + 异常原样传播」；**不重试、不缓存**（同音频两次进入 = 两次
  `client.asr` 调用）、不分片、不流式。
- 确定性判定方式：连跑两次，`(client.calls, grader.calls, 返回值)` 三元组相等
  （`test_asr_answer_deterministic_and_inputs_unmutated`）；端到端场景下两次 multipart
  请求体逐字节相等（`test_end_to_end_mm_client_mock_transport`）。

## 6. 错误行为

| 非法输入 / 情形 | 行为（异常类型与触发时机） |
|---|---|
| `clean_transcript`/`spoken_to_math`/`extract_answer` 的入参非 `str`（`None`/`int`/`bytes`/`list` 等任意非 `str`） | 进入函数体**立即**抛 `ASRError`（`ValueError` 子类），无任何前置处理；按 Python 习惯推荐 `isinstance(text, str)` 即可覆盖全部非 `str` |
| V1：`client` 无 callable 的 `asr` 属性（缺属性、属性为 `None`、属性不可调用） | 守卫期抛 `ASRError`；`client.asr` 零次调用、grader 零次调用 |
| V2：`grader` 不可调用（`None`/`int`/`str`/`bytes` 等） | 守卫期抛 `ASRError`；client 零次调用 |
| V3：`audio` 非 `bytes` 或空 `bytes`（`None`/`b""`/`int`/`str`；`bytearray`/`memoryview` 同样拒绝） | 守卫期抛 `ASRError`；client 零次调用 |
| V4：`filename` 非 `str` 或 `strip()` 后为空（`""`/`"   "`/`None`/`bytes`/`int`） | 守卫期抛 `ASRError`；client 零次调用 |
| `client.asr` 回写非 `str`（`None`/`bytes`/`int` 等） | **出网一次之后**抛 `ASRError`；grader 不被调用 |
| `client.asr` 抛出任何异常（如 `RuntimeError`/`KeyError`） | **原样传播**，不包装成 `ASRError`；grader 不被调用 |
| grader 抛出任何异常（如 `KeyError`/`ValueError`/自定义异常） | **原样传播**（模块不捕获、不包装、不改写异常链）；非 `ASRError` |
| 转写为空白 / 纯语气词 / 纯引导语 | **容忍**，不抛错：`extract_answer` → `None` ⇒ `grader(item, None)`（不伪造作答） |
| 转写含单位词、未知文本、孤立记号（`负`/`点`/`万`）、非答案句式 | **容忍**，机械转换后透传，交判分器字面支/单位门诚实判错 |
| `item` 为任意对象（含 `None`） | **不校验**，原样交 grader；模块不读 `item` 任何属性 |
| `filename` 以位置实参传入（`asr_answer(b"...", item, client, grader, "x.wav")`） | Python 参数绑定阶段抛 `TypeError`（非 `ASRError`，本模块不参与校验） |

异常类型一律 `ASRError`（`ValueError` 直接子类）；非 `ASRError` 的出口有且仅有三处：
(a) `client.asr` 自身抛出的异常（原样传播）、(b) `grader` 自身抛出的异常（原样传播）、
(c) `filename` 位置传参导致的 `TypeError`（Python 自身机制）。**异常消息文案不作承诺**
（不是契约面），但 §3.5 的 V1/V2/V3/V4 错误消息**含可观察特征**（见该节）：V3 消息嵌入
`type(audio).__name__`，V1/V2/V4 不嵌入；多守卫失败按 V1 → V2 → V3 → V4 顺序**先命中
者抛错**。

## 7. 非目标

- **不做语音识别本身**：不加载 ASR 模型、不发网络请求、不做音频预处理（重采样/格式
  转换/静音检测 VAD/音量归一）；转写完全由注入的 `client.asr` 完成。
- **不做表达式求值**：`三加五` → `3+5` 而不是 `8`；不解方程、不化简、不合并同类项。
- **不猜得数、不做语义判分**：判分（数值等值/字面/单位门/选项解析/`Response` 产出）全部
  由注入的 grader 完成；抽取只做机械转换。
- **不做单位换算**：`5平方米`、`2.5升` 原样透传，单位语义归判分器。
- **不偷看题目与标答**：抽取签名与行为均与 item 无关；不用标答反推、不做句式猜测
  （`等于3` 剥引导语后只剩 `3`，与 `x=3` 判错是冻结的可预期代价，不是缺陷）。
- **不做口语约算**：`一百五` 冻结为 `105`，不实现「一百五 ≈ 150」的口语约算读法；
  「除」不入算符表（歧义大）。
- **不做多语言/方言/中英混读扩展**：口语数字文法只覆盖 §3.3 的封闭集合。
- **不缓存、不重试、不分片**：无 ASR 结果缓存、无低置信度重试、无 confidence 门限
  （转写置信度概念不在本模块）、无流式/增量转写。
- **不做会话状态与持久化**：无跨调用状态、无文件/数据库写入、无题卷级批量接口。
- **不 import 任何其他 xuexing 模块**：`mm_client`/`grading`/`mm_ingest`/`types` 都只以
  注入鸭子对象或测试内跨模块断言的形式出现；跨模块一致性由契约测试锁定，不由本模块
  代码保证。
