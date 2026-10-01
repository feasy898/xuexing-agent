# mm_ingest 模块规格（冻结契约）

> 本文档是唯一权威契约。任何实现（参考实现或重生成实例）只要通过 tests/contract/ 全部测试
> 且满足本文全部条款，即为合格实现。实现算法自由，行为不允许偏离。
>
> **版本**：冻结 v1（第三波）。标注「〔测试裁定〕」的行为由
> `tests/contract/test_mm_ingest_contract.py`（26 项）直接断言；标注「〔参考裁定〕」的行为
> 契约测试未仲裁，按参考实现 `src/xuexing/mm_ingest.py` 冻结并在当地注明本冻结轮的实测
> 探针（P1–P6，CPython 3.12.10 x64）。本文自包含：全部常量、schema、管线顺序在本文内
> 完整定义，不引用仓库内其他规格文档。
>
> 冻结基线：参考实现 + 契约测试全量实测于 2026-10-02，CPython 3.12 x64
> （`python -m pytest tests/contract/test_mm_ingest_contract.py -q` → 26 passed）。

## 1. 目的

mm_ingest 是拍照录入管线（BACKLOG P3「mm_ingest 拍照录入管线」）的确定性内核：一张学生
作答照片 → VLM 结构化转写（题号→学生答案 JSON，schema 冻结）→ 确定性校验（题号∈卷面、
答案形态、置信度门）→ **注入的 grader**（与 `grading.grade_to_response` 同签名）产出
`Response`；不可信条目（未知题号/重复题号/低置信/形态不符/卷面缺号）**不猜测、不静默
判分**，进人机协同复核队列。卷面题号 1..N 与 omr_sheet/paper_layout 同一编号语义
（sections 顺序展开、空 sections 回退 `paper.item_ids`）；选项标签解析与
`omr_sheet.parse_option` 同闭式。学生面卫生：VLM prompt 只含题号/题型/choice 标签，
绝不含 stem/answer/solution/选项正文。模块间零 import：client（`mm_client.MMClient`
满足其表面）与 grader 都是注入的鸭子类型参数，一致性由契约测试在测试内 import 对方
模块跨模块锁定。全模块纯函数：无 IO、无随机、无时钟、不读环境，同输入同输出。

## 2. 允许的依赖

- Python 标准库（逐个列出，全部来自参考实现的 import 清单）：
  - `json`（`parse_transcript` 的 JSON 解析）
  - `math`（`math.isfinite` 置信度/门限的有限性判定）
  - `re`（选项标签正则 `_OPT_RE`）
  - `dataclasses`（`ReviewItem`/`IngestResult` 两个 dataclass）
  - `typing`（仅 `Optional` 注解）
- `xuexing.types` —— **必须绝对导入**：`from xuexing.types import Response, to_dict`；
  只允许使用这两个名字（`Response` 为判分产出类型，`to_dict` 为
  `IngestResult.to_dict` 的序列化 helper）
- 禁止：其他 xuexing 模块（**无例外**——client/grader/bank/paper/item 一律鸭子类型注入，
  不 import 其定义模块）、第三方库、文件/网络 IO、全局可变状态
- 禁止：随机、系统时钟、环境读取（全模块无时间戳字段，无豁免）

注入对象只按成员调用（鸭子类型，不 import 其定义模块）：

- `client.vision(prompt, images, image_format="png") -> str`（prompt 位置参数，
  images 为单图 list，image_format 关键字参数；返回转写文本）
- `grader(item, learner_answer) -> Response`（可调用对象；与
  `grading.grade_to_response` 同签名；`learner_answer` 可为 None）
- `bank.items() -> Iterable[item]`
- `paper`：只读属性 `paper_id`、`title`、`sections`、`item_ids`
- `item`：只读属性 `id`、`item_type`、`options`、`answer`

重生成实例的装载约束（自包含实测，2026-10-02，CPython 3.12.10 x64；注入机制：
`tests/conftest.py:22-34` 以顶层模块名 `_regen_mm_ingest` 经 `spec_from_file_location`
装载 `<impl_dir>/mm_ingest.py` 并顶替 `sys.modules["xuexing.mm_ingest"]`；本冻结轮
探针复现）：

- **禁止相对导入**（`from .types import ...`）：实测在 `exec_module` 处抛
  `ImportError: attempted relative import with no known parent package`（探针 LP1）。
- **禁止 `from __future__ import annotations`**：实测在 dataclass 处理阶段抛
  `AttributeError: 'NoneType' object has no attribute '__dict__'`——CPython 3.12
  `dataclasses` 按 `sys.modules.get(cls.__module__)` 解析字符串注解，注入模块注册名是
  `xuexing.mm_ingest` 而 dataclass 的 `__module__` 是 `_regen_mm_ingest`，`.get` 得
  `None`（探针 LP2）。注解直接写真实对象（`list`、`Optional[str]`）。
- **绝对导入 + 真实对象注解实测可装载**：探针 LP3 以
  `from xuexing.types import Response, to_dict` + `@dataclass class R: n: int; s: Optional[str] = None`
  经注入方式装载并正常构造、序列化成功。

## 3. 公开 API

模块必须暴露以下 16 个名字（契约测试
`from xuexing.mm_ingest import IMAGE_FORMATS, INGEST_VERSION, MIN_CONFIDENCE,
REASON_ANSWER_FORM, REASON_DUPLICATE_NUMBER, REASON_LOW_CONFIDENCE,
REASON_MISSING_NUMBER, REASON_UNKNOWN_NUMBER, REVIEW_REASONS, IngestError,
IngestResult, ReviewItem, build_transcribe_prompt, ingest_photo, option_labels,
parse_transcript`）。

### 3.1 常量与异常

- `INGEST_VERSION = "1"`〔测试裁定 `test_frozen_constants`〕
- `MIN_CONFIDENCE = 0.9`：`ingest_photo` 的缺省置信度门；`confidence < 门限` 进复核
  〔测试裁定〕
- `IMAGE_FORMATS = ("png", "jpg", "jpeg", "webp", "gif")`：合法图片格式元组（确切
  顺序冻结；大小写敏感）。与 `mm_client.IMAGE_MIME` 键集相等（跨模块锁定）：
  `tuple(sorted(IMAGE_FORMATS)) == tuple(sorted(IMAGE_MIME.keys()))`，实测
  `IMAGE_MIME` 键集为 `{'png','jpg','jpeg','webp','gif'}`〔测试裁定
  `test_frozen_constants`、`test_image_formats_match_mm_client_mime_keys`〕
- `REASON_UNKNOWN_NUMBER = "unknown_number"`：转写题号不在卷面 1..N
- `REASON_DUPLICATE_NUMBER = "duplicate_number"`：同一题号被转写多次
- `REASON_MISSING_NUMBER = "missing_number"`：卷面题号在转写中完全缺席
- `REASON_LOW_CONFIDENCE = "low_confidence"`：`confidence < min_confidence`
- `REASON_ANSWER_FORM = "answer_form"`：答案形态与题型不符（不可信不猜）
- `REVIEW_REASONS = ("unknown_number", "duplicate_number", "missing_number",
  "low_confidence", "answer_form")`：五个常量的值即按此顺序组成的元组；
  五个常量逐一等于其对应字符串字面量〔测试裁定 `test_frozen_constants`〕
- `IngestError(ValueError)`：本模块唯一异常类型（`ValueError` **直接**子类），
  覆盖本模块一切校验失败〔测试裁定 `issubclass(IngestError, ValueError)`〕

### 3.2 `ReviewItem`

```python
@dataclass
class ReviewItem:
    number: int                  # 转写题号；missing_number 时为卷面缺号
    item_id: Optional[str]       # 卷内号给 item_id；unknown_number 恒 None
    answer: Optional[str]        # 转写原文；missing_number 恒 None
    confidence: Optional[float]  # 转写置信度；missing_number 恒 None
    reason: str                  # 恰一个，词表见 REVIEW_REASONS
    detail: str

    def to_dict(self) -> dict    # 六字段原样成 dict
```

`to_dict()` 输出恰为 `{"number", "item_id", "answer", "confidence", "reason",
"detail"}` 六键〔测试裁定 `test_review_item_and_ingest_result_to_dict_shapes`：
`ReviewItem(number=1, item_id="c1", answer="B", confidence=0.9,
reason="low_confidence", detail="d").to_dict() == {"number": 1, "item_id": "c1",
"answer": "B", "confidence": 0.9, "reason": "low_confidence", "detail": "d"}`〕。

各 reason 的字段与 detail 冻结格式（detail 为可观测输出字段；测试对四种 reason 的
detail 断言子串——见不变量 I8；完整文案按参考实现冻结）：

| reason | number | item_id | answer | confidence | detail 格式 |
|---|---|---|---|---|---|
| `unknown_number` | 转写题号 | `None` | 转写原文 | 转写置信度 | `f"number {number} is not on paper (1..{N})"` |
| `duplicate_number` | 转写题号 | 卷内 item_id | 转写原文 | 转写置信度 | `f"number {number} transcribed {count} times"` |
| `low_confidence` | 转写题号 | 卷内 item_id | 转写原文 | 转写置信度 | `f"confidence {confidence} < min_confidence {min_confidence}"` |
| `answer_form` | 转写题号 | 卷内 item_id | 转写原文 | 转写置信度 | `f"choice answer must be a single bubble label in {labels}, got {answer!r}"` |
| `missing_number` | 卷面题号 | 卷内 item_id | `None` | `None` | `f"number {number} missing from transcript"` |

### 3.3 `IngestResult`

```python
@dataclass
class IngestResult:
    responses: list  # list[Response]，按卷面题号升序
    review: list     # list[ReviewItem]，条目级（转写序）+ 缺号（题号升序）

    def to_dict(self) -> dict
```

`to_dict()` 返回 `{"responses": [to_dict(r) for r in self.responses], "review":
[item.to_dict() for item in self.review]}`（`to_dict` 来自 `xuexing.types`，递归
dataclass 序列化）〔测试裁定：`IngestResult(responses=[Response("c1", True,
"B. -2/3", None)], review=[item]).to_dict() == {"responses": [{"item_id": "c1",
"correct": True, "learner_answer": "B. -2/3", "response_ms": None}], "review":
[item.to_dict()]}`〕。

### 3.4 `option_labels(item) -> list[str]`

choice 题的选项标签列（与 `omr_sheet.parse_option` 同闭式，跨模块锁定）：

- 逐选项取 `item.options[i]`，`strip()` 后匹配正则
  `([A-Za-z])[.．、)）][ \t]*(.*)\Z`（`re.S`）：命中 → 标签为捕获字母**归一大写**
  （`"b. 一"`→`"B"`，`"c）二"`→`"C"`，`"d．三"`→`"D"`，`"e、四"`→`"E"`）；
  未命中 → 按位回退 `_FALLBACK_LABELS[i]`（`"ABCDEFGHIJKLMNOPQRSTUVWXYZ"`，
  即第 i 个选项得第 i 个字母）。
- 与 `omr_sheet.parse_option` 逐项相等：`option_labels(item) ==
  [parse_option(o, i)[0] for i, o in enumerate(item.options)]`〔测试裁定
  `test_option_labels_matches_omr_sheet_parse_option`〕。
- 守卫（任一违反 → `IngestError`）〔测试裁定 `test_option_labels_guards`〕：
  `options` 非 list/tuple、属性缺失、长度 < 2、长度 > 26（`_MAX_BUBBLES`）、含非
  str 或空白串、解析出的标签有重复。恰 26 个无显式标签选项 → 回退列
  `["A".."Z"]`〔参考裁定，探针 P2；测试只覆盖 27 个的拒绝支〕。
- 例子〔测试裁定 `test_option_labels_closed_forms`〕：
  `option_labels(C1)`，`C1.options == ["A. 0", "B. -2/3", "C. +1.5", "D. 2026"]`
  → `["A", "B", "C", "D"]`；`C2.options == ["2", "3"]` → `["A", "B"]`（无显式标签
  按位回退）；`["b. 一", "c）二", "d．三", "e、四"]` → `["B", "C", "D", "E"]`
  （标签归一大写）。

### 3.5 `build_transcribe_prompt(paper, bank) -> str`

卷面 → 确定性 VLM 转写提示词（只含题号/题型/choice 标签，I4 卫生）。内部先经
卷面表面校验（同 §3.7 的 V6–V8 与空卷门，失败抛 `IngestError`），再渲染**冻结文本**：

```
你是阅卷录入助手。下面是一张学生作答照片对应的卷面题目清单，请逐题转写学生答案。
只输出一个 JSON 对象，不要输出任何其他文字。
输出 JSON schema（冻结）：{"answers": [{"number": 题号整数, "answer": 学生答案字符串或 null, "confidence": 0 到 1 的数字}]}
规则：
1. 卷面共 {n} 道题，题号 1..{n}，每个题号在 answers 中恰好出现一次。
2. choice 题：answer 只输出被选选项的标签字母（A-Z 之一）；未作答输出 null。
3. fill/solve 题：answer 按照片原样转写学生书写内容；未作答输出 null。
4. confidence 是你对该条转写的置信度，取 0 到 1。
卷面题目清单：
```

随后每题一行：`f"{number}. {item_type}"`，choice 题追加 `" 选项 " + "/".join(labels)`；
各行以 `"\n"` 连接（文本恰以清单末行结束，无尾随换行）。

- 闭式例子〔测试裁定 `test_prompt_closed_form_three_questions`〕：三题卷
  （`item_ids=["c1","f1","s1"]`，c1 标签 A/B/C/D）的 prompt 恰为（逐字节相等，
  重复调用结果相同）：

  ```
  你是阅卷录入助手。下面是一张学生作答照片对应的卷面题目清单，请逐题转写学生答案。
  只输出一个 JSON 对象，不要输出任何其他文字。
  输出 JSON schema（冻结）：{"answers": [{"number": 题号整数, "answer": 学生答案字符串或 null, "confidence": 0 到 1 的数字}]}
  规则：
  1. 卷面共 3 道题，题号 1..3，每个题号在 answers 中恰好出现一次。
  2. choice 题：answer 只输出被选选项的标签字母（A-Z 之一）；未作答输出 null。
  3. fill/solve 题：answer 按照片原样转写学生书写内容；未作答输出 null。
  4. confidence 是你对该条转写的置信度，取 0 到 1。
  卷面题目清单：
  1. choice 选项 A/B/C/D
  2. fill
  3. solve
  ```

- 学生面卫生〔测试裁定 `test_prompt_hygiene_no_answer_material`〕：四题卷的
  prompt 含 `"A/B/C/D"` 与 `"A/B"`，且**不含** stem（`"stem-c1"`）、答案
  （`"-300元"`、`"x=12"`）、解析（`"SOL-"`）、选项正文（`"B. -2/3"`、`"2026"`、
  `"+1.5"`）、节名（`"有理数"`、`"一元一次方程"`）。

### 3.6 `parse_transcript(text) -> list[dict]`

VLM 回复文本 → `[{"number": int, "answer": str|None, "confidence": float}…]`
（schema 冻结）：

- `text` 非 str → `IngestError`；`strip()` 后为空 → `IngestError`〔测试裁定〕。
- 切片闭式：首个 `"{"` 到最后一个 `"}"`（`stripped[start:end+1]`）做 JSON 解析
  （前后闲话、```json 围栏容忍）；无 `"{"` 或 `"}` 不在起点之后 → `IngestError`；
  JSON 解析失败（含两个独立 JSON 对象）→ `IngestError`〔测试裁定
  `test_parse_transcript_closed_forms` 的围栏/闲话例、`test_parse_transcript_guards`；
  参考裁定双对象例见探针 P10〕。
- 顶层必须是 dict 且含 `"answers"` list；entry 必须是 dict 且三键必填
  （`number`/`answer`/`confidence`），未知键忽略〔测试裁定〕。
- `number`：`_is_int`（int 且非 bool）且 `>= 1`，否则 `IngestError`
  （`0`、`-1`、`"1"`、`True`、`1.5`、`None` 全部拒绝）〔测试裁定〕。
- `answer`：`str` 或 `None`，否则 `IngestError`（`42`、`[]`、`{}` 拒绝）〔测试裁定〕。
- `confidence`：`_is_number`（int/float 且非 bool）、`math.isfinite`、且落在
  `[0.0, 1.0]`，否则 `IngestError`（`-0.1`、`1.1`、`"0.9"`、`True`、`None`、
  `inf`、`nan` 全部拒绝）；输出规整为 `float`〔测试裁定〕。
- 输出 entry 恰三键 `{"number", "answer", "confidence"}`〔测试裁定〕。
- 例子〔测试裁定 `test_parse_transcript_closed_forms`〕：
  - `'{"answers": [{"number": 1, "answer": "B", "confidence": 0.97}]}'` →
    `[{"number": 1, "answer": "B", "confidence": 0.97}]`
  - 围栏文本 `"```json\n{\"answers\": [{\"number\": 2, \"answer\": null,
    \"confidence\": 1}]}\n```"` → `[{"number": 2, "answer": None,
    "confidence": 1.0}]`（int 规整为 float）
  - 未知键忽略：`'{"answers": [{"number": 1, "answer": "B", "confidence": 1,
    "extra": "x"}]}'` → `[{"number": 1, "answer": "B", "confidence": 1.0}]`

### 3.7 `ingest_photo(image, paper, bank, client, grader, *, image_format="png", min_confidence=MIN_CONFIDENCE) -> IngestResult`

拍照录入管线主入口。**校验顺序 V1..V8 冻结**（任一失败抛 `IngestError` 且零次
client 调用）：

- V1 `client` 表面：`client.vision` 存在且可调用，否则 `IngestError`
- V2 `grader` 表面：`grader` 可调用，否则 `IngestError`
- V3 `image`：非空 `bytes`（`bytearray` 也拒绝〔参考裁定，探针 P4〕）
- V4 `image_format`：∈ `IMAGE_FORMATS`（**大小写敏感**，`"PNG"` 拒绝）
- V5 `min_confidence`：`_is_number`（拒 bool）且 `math.isfinite` 且
  `0.0 <= min_confidence <= 1.0`，否则 `IngestError`
- V6–V8 卷面表面（`_paper_questions`，顺序为绑定条款）：
  1. `paper.paper_id`、`paper.title` 必须为 str
  2. `bank` 必须暴露可调用 `items()`；其返回必须可迭代（`items()` 调用或迭代本身
     抛 `TypeError` → `IngestError`〔参考裁定，探针 P5；测试只覆盖返回不可迭代
     对象 `5` 一支〕）；item `id` 必须为非空白 str 且 bank 内不重复
  3. `paper.sections` 必须为 list/tuple；空 sections → 回退单一隐式节
     `[{"item_ids": paper.item_ids}]`（此时 `paper.item_ids` 必须为 list/tuple）；
     每个 section 必须为 dict 且 `item_ids` 为 list/tuple；题 id 必须为非空白 str
  4. 逐题：id 必须能在 bank 索引查到（未知题 id → `IngestError`）；
     `item_type` ∈ `("choice", "fill", "solve")`（其余如 `"essay"` → `IngestError`）；
     choice 题另经 `option_labels` 守卫 + `item.answer` 必须为 str + 去空白大写后的
     标答必须 ∈ 标签列或等于某选项原文（去空白大写）〔参考裁定：标答存选项**全文**
     （如 `"B. -2/3"`）亦合法，探针 P1；测试只覆盖标答既非标签也非选项全文
     （`"Z"`）的拒绝支〕
  5. **空卷门**：展开后零题 → `IngestError("empty paper: no questions to ingest")`
     （sections 空且 item_ids 空、或节内 item_ids 空，均触发）

随后：

- **恰好一次出网**（唯一注入口）：`prompt = build_transcribe_prompt(paper, bank)`
  的等价渲染，`raw = client.vision(prompt, [image], image_format=image_format)`
  （prompt 位置参数 str；images 恒为 `[image]` 单元素 list；image_format 关键字
  透传）〔测试裁定 `test_ingest_single_vision_call_image_and_format_passthrough`、
  `test_prompt_exact_bytes_over_mm_client_mock_wire`〕。
- `entries = parse_transcript(raw)`（此步在出网**之后**；转写非法 → `IngestError`，
  但 client 已被调用恰好一次）。
- client/grader 抛出的异常**原样传播，不包装**（`RuntimeError("llm down")` 仍是
  `RuntimeError`；grader 的 `ValueError("grading boom")` 仍是 `ValueError`——
  不被转换为 `IngestError`）〔测试裁定
  `test_ingest_client_and_grader_exceptions_propagate_unwrapped`〕。
- 路由（逐条目，**优先级冻结**：`unknown_number` > `duplicate_number` >
  `low_confidence` > `answer_form`）：
  1. 题号不在卷面 1..N → `unknown_number` 复核（`item_id=None`），不再看其余条件；
  2. 该题号在转写中出现 >1 次 → `duplicate_number` 复核（**每个副本各产一条**）；
  3. `confidence < min_confidence`（严格小于；**等于门限通过**）→
     `low_confidence` 复核；
  4. `answer` 为 `None` 或去空白后为空（VLM 显式 null/空白串）→ 交
     `grader(item, None)` 产出 Response（无作答证据恒判错，**不伪造内容、不进复核**）；
  5. choice 题：`token = answer.strip().upper()`；`len(token) == 1` 且 `token` ∈
     标签列 → 取该标签下标，`grader(item, options[idx])`（grader 收到**选项原文
     全串**）；否则 → `answer_form` 复核（`E`、`AB`、`B. -2/3`、`A.`、`3` 等一律
     复核，不猜）；
  6. fill/solve 题：`grader(item, answer)`（**原文透传，不 strip**〔参考裁定，
     探针 P3；测试只覆盖全空白串走 None 支〕）。
- **缺号**：转写里完全没出现的卷面题号 → `missing_number` 复核，按卷面题号**升序**
  排在全部条目级复核之后。
- **产出排序**：`responses` 按卷面题号升序（判分调用按转写序发生，产出在末尾统一
  排序）；`review` 顺序 = 条目级（转写序）+ 缺号（升序）。
- 闭式例子〔测试裁定 `test_ingest_routes_happy_duplicate_low_unknown_missing`〕：
  四题卷（1=c1 choice A-D、2=f1 fill、3=s1 solve、4=c2 choice A/B），转写

  ```json
  {"answers": [
    {"number": 1, "answer": "B", "confidence": 0.97},
    {"number": 2, "answer": "-300元", "confidence": 0.95},
    {"number": 4, "answer": "x", "confidence": 0.8},
    {"number": 9, "answer": "42", "confidence": 0.99},
    {"number": 2, "answer": null, "confidence": 0.3}]}
  ```

  → `responses == [Response("c1", True, "B. -2/3", None)]`（choice 交选项原文
  全串）；`review` 的 `(reason, number)` 序列恰为
  `[(duplicate_number, 2), (low_confidence, 4), (unknown_number, 9),
  (duplicate_number, 2), (missing_number, 3)]`（条目级按转写序、duplicate 优先于
  low_confidence、缺号排最后）；review 的
  `(item_id, answer, confidence)` 序列恰为
  `[("f1", "-300元", 0.95), ("c2", "x", 0.8), (None, "42", 0.99),
  ("f1", None, 0.3), ("s1", None, None)]`；`client` 被调恰好 1 次；
  `grader.calls == [("c1", "B. -2/3")]`（每个 Response 恰好一次 grader，review
  条目零 grader）。
- 闭式例子〔测试裁定 `test_ingest_min_confidence_boundary_and_custom`〕：
  `{"number": 1, "answer": "B", "confidence": 0.9}` 配缺省门 0.9 → 通过（等于
  门限不判低置信）；`{"number": 4, "answer": "A", "confidence": 0.0}` 配
  `min_confidence=0.0` → 通过（`0.0 < 0.0` 不成立）；
  `{"number": 1, "answer": "B", "confidence": 0.99}` 配 `min_confidence=1.0` →
  `low_confidence` 复核。

## 4. 不变量（编号列出，全部可被契约测试检验）

- I1 **常量冻结**：`INGEST_VERSION == "1"`、`MIN_CONFIDENCE == 0.9`、
  `IMAGE_FORMATS == ("png","jpg","jpeg","webp","gif")`、`REVIEW_REASONS` 恰为五
  字符串元组且五个 `REASON_*` 常量逐一等于其字面量、`IngestError` 是 `ValueError`
  直接子类。〔测试裁定 `test_frozen_constants`〕
- I2 **图片格式跨模块锁定**：`tuple(sorted(IMAGE_FORMATS)) ==
  tuple(sorted(mm_client.IMAGE_MIME.keys()))`（测试内 import `xuexing.mm_client`
  断言；被测模块自身零 import）。〔测试裁定
  `test_image_formats_match_mm_client_mime_keys`〕
- I3 **选项标签闭式**：显式标签（单 ASCII 字母 + `.．、)）` 分隔符）归一为大写、
  无显式标签按位回退 A..Z；与 `omr_sheet.parse_option` 逐项相等；守卫（非 list/
  <2/>26/非 str/空白/标签重复/属性缺失）一律 `IngestError`。〔测试裁定
  `test_option_labels_closed_forms`、`test_option_labels_guards`、
  `test_option_labels_matches_omr_sheet_parse_option`〕
- I4 **prompt 冻结与学生面卫生**：prompt 为逐字节冻结文本（`n` 与 choice 标签行为
  仅有的变量位），同输入重复调用相等；只含题号/题型/choice 标签，绝不含 stem/
  answer/solution/选项正文/节名。〔测试裁定
  `test_prompt_closed_form_three_questions`、`test_prompt_hygiene_no_answer_material`〕
- I5 **端到端 prompt 逐字节一致**：经真实 `MMClient`+`MockTransport` 跑通时，线上
  发出的 prompt 逐字节等于 `build_transcribe_prompt(paper, bank)`，转写 JSON 被
  结构化解析并进入判分。〔测试裁定 `test_prompt_exact_bytes_over_mm_client_mock_wire`〕
- I6 **恰好一次出网与调用形状**：每次成功 `ingest_photo` 恰一次
  `client.vision(prompt, [image], image_format=...)`；prompt 为 str、images 为单图
  list、image_format 透传（`"jpeg"` 等合法变更生效）。〔测试裁定
  `test_ingest_single_vision_call_image_and_format_passthrough`〕
- I7 **校验先于出网**：V1–V8 全部守卫（含卷面表面 20 项非法形态与空卷门）失败时抛
  `IngestError` 且 client 零调用。〔测试裁定
  `test_ingest_v_guards_fail_before_any_network_call`、
  `test_ingest_paper_bank_surface_guards_zero_network`〕
- I8 **转写 schema 冻结**：`parse_transcript` 的切片、类型、值域条款按 §3.6 执行；
  合法闭式例逐位相等，全部 12 类非法输入（含 bool 混入 number/confidence）抛
  `IngestError`。〔测试裁定 `test_parse_transcript_closed_forms`、
  `test_parse_transcript_guards`〕
- I9 **路由优先级与复核队列形状**：每条 entry 至多一个 reason，优先级
  unknown > duplicate > low_confidence > answer_form；duplicate 每个副本各一条；
  review = 条目级（转写序）+ 缺号（卷面题号升序，排最后）；`missing_number` 的
  answer/confidence 恒 None，`unknown_number` 的 item_id 恒 None。〔测试裁定
  `test_ingest_routes_happy_duplicate_low_unknown_missing`、
  `test_ingest_empty_transcript_all_missing_in_order`、
  `test_ingest_review_only_transcript_zero_grader_calls`〕
- I10 **空白作答交 grader 不伪造**：`answer` 为 null/空白串 → `grader(item, None)`
  产出 Response（不进复核、不编造答案内容）；判分调用按转写序发生。〔测试裁定
  `test_ingest_blank_answers_become_null_responses`〕
- I11 **choice 形态门**：单字符标签（strip+大写）命中标签列 → grader 收该下标选项
  原文全串（`"b"` 与 c2 的 `"3"`）；其余形态一律 `answer_form` 复核、零 grader
  调用；fill/solve 原文透传。〔测试裁定 `test_ingest_choice_form_gate`、
  `test_cross_module_grading_grade_to_response_equality`〕
- I12 **置信度门边界**：`confidence == min_confidence` 通过、严格小于才复核；
  `min_confidence` 为 [0,1] 的合法自定义值（含 0.0 与 1.0 边界）。〔测试裁定
  `test_ingest_min_confidence_boundary_and_custom`〕
- I13 **responses 题号升序**：产出按卷面题号升序（非转写序）；review 条目零 grader
  调用；纯复核转写下 responses 为空、grader 零调用。〔测试裁定
  `test_ingest_responses_sorted_by_paper_number`、
  `test_ingest_review_only_transcript_zero_grader_calls`〕
- I14 **异常传播纪律**：client/grader 抛出的异常原样穿透（不包装为 `IngestError`）；
  空转写 `{"answers": []}` 不抛错，全卷面缺号进复核且仍恰一次出网。〔测试裁定
  `test_ingest_client_and_grader_exceptions_propagate_unwrapped`、
  `test_ingest_empty_transcript_all_missing_in_order`〕
- I15 **确定性与纯度**：同输入两次 `ingest_photo` 的 `to_dict()` 相等（responses
  与 review 逐字段相等）；不修改入参（paper.sections、item.options、item.answer、
  image 快照前后相等）。〔测试裁定
  `test_ingest_determinism_same_input_same_output`、`test_ingest_inputs_not_mutated`〕
- I16 **数据形状**：`ReviewItem.to_dict` 恰六字段；`IngestResult.to_dict` 的
  responses 经 `xuexing.types.to_dict` 序列化。〔测试裁定
  `test_review_item_and_ingest_result_to_dict_shapes`〕
- I17 **跨模块判分语义锁定**：注入 `grading.grade_to_response` 时，管线产出的
  Response 等于直接对 (item, 选项原文全串 | 作答原文) 调用它；空白转写
  （`grader(item, None)`）与 `omr_sheet` 未涂气泡同语义
  （`correct=False, learner_answer=None`）。〔测试裁定
  `test_cross_module_grading_grade_to_response_equality`、
  `test_cross_module_omr_blank_mark_semantics`〕

## 5. 确定性与随机性

- 全部公开函数为纯函数：输出只依赖入参；禁止 `random`、hash 序、系统时钟、环境
  读取、文件/网络 IO、全局可变状态。全模块无时间戳字段（无豁免）。
- `ingest_photo` 对外部非确定性（VLM 真实输出）的唯一接口是注入的
  `client.vision` 与 `grader`：给定相同的转写文本（脚本化 client）与相同的 grader，
  两次调用结果逐字段相等；管线的确定性指「同一转写文本 → 同一 responses/review」。
- 数值可复现性：`confidence` 经 `float()` 规整（IEEE 唯一结果）；置信度门为严格
  `<` 比较（等于门限通过）；无 round、无阈值自适应。
- 卷面题号 1..N 由 sections 顺序展开决定（空 sections 回退 `paper.item_ids`），
  同一 paper/bank 输入得到同一编号表面；`_section_lists`/`_bank_index` 均产出拷贝，
  不修改入参（I15）。

## 6. 错误行为

| 非法输入 | 行为 |
|---|---|
| `client.vision` 缺失/不可调用 | 计算前（V1）抛 `IngestError`，零出网 |
| `grader` 不可调用 | 计算前（V2）抛 `IngestError`，零出网 |
| `image` 非 bytes / 空 bytes（`b""`）/`None`/str；`bytearray` | 计算前（V3）抛 `IngestError`，零出网〔bytearray 参考裁定，探针 P4〕 |
| `image_format` ∉ `IMAGE_FORMATS`（含 `"PNG"` 大小写变体、`"bmp"`） | 计算前（V4）抛 `IngestError`，零出网 |
| `min_confidence` ∉ [0,1] / 非有限 / bool / str | 计算前（V5）抛 `IngestError`，零出网 |
| `paper.paper_id`/`paper.title` 非 str | V6 抛 `IngestError`，零出网 |
| `bank` 无 `items()` / `items()` 返回不可迭代 / item id 非非空 str / bank 内 id 重复 | V6 抛 `IngestError`，零出网〔`items()` 内部 TypeError 转 `IngestError` 为参考裁定，探针 P5〕 |
| `paper.sections` 非 list/tuple；空 sections 时 `item_ids` 非 list/tuple；节非 dict；节内 `item_ids` 非 list/tuple；题 id 非非空 str | V6/V7 抛 `IngestError`，零出网 |
| 题 id 不在 bank；`item_type` ∉ {choice, fill, solve}；choice 选项守卫违反；choice 标答非 str 或既非标签也非选项原文 | V7/V8 抛 `IngestError`，零出网〔标答=选项全文合法为参考裁定，探针 P1〕 |
| 空卷（展开后零题，含 sections 空 + item_ids 空、节内 item_ids 空） | 空卷门抛 `IngestError`，零出网 |
| 转写文本非法（非 str/空/无 JSON 对象/解析失败/顶层非 dict/缺 answers/entry 非 dict/缺必填键/number 非 int≥1（含 bool）/answer 非 str·null/confidence 非 [0,1] 有限数字（含 bool）） | 出网**之后**抛 `IngestError`（client 已被调用恰好一次） |
| 转写题号不在卷面 1..N | **容忍**，`unknown_number` 复核（不猜不判） |
| 同一题号转写多次 | **容忍**，每个副本一条 `duplicate_number` 复核 |
| 卷面题号在转写中缺席 | **容忍**，`missing_number` 复核（升序排在条目级之后） |
| `confidence < min_confidence` | **容忍**，`low_confidence` 复核 |
| choice 答案非单字符命中标签（`"E"`/`"AB"`/`"B. -2/3"`/`"A."`/`"3"`） | **容忍**，`answer_form` 复核 |
| choice 标签大小写/带空白（`"b"`、`" B "` 语义由 strip+upper 归一） | **容忍**，归一后命中即判 |
| 答案 null/空白串 | **容忍**，交 `grader(item, None)` 恒判错、不伪造 |
| `client.vision` 抛异常（如 `RuntimeError`） | **原样传播**，不包装、不重试 |
| `grader` 抛异常（如 `ValueError`） | **原样传播**，不包装 |

异常类型一律 `IngestError`（`ValueError` 直接子类）——**唯一例外**是 client/grader
自身抛出的异常按原类型传播，本模块不转换、不吞掉。异常消息文案不作承诺（不是契约
面）；但 `ReviewItem.detail` 是可观测输出字段，其格式按 §3.2 表冻结（契约测试对四种
reason 断言子串，`answer_form` 的 detail 文案为参考裁定）。

## 7. 非目标

- **不做真实 VLM 调用/OCR**：client 是注入鸭子类型，模块自身不发任何网络请求；
  图像解码、格式转换、压缩、多页拼合一概不做（`image` 只按 `bytes` 原样透传）。
- **不猜答案**：不可信条目（未知题号/重复/低置信/形态不符/缺号）一律进复核队列，
  不猜测判分、不静默丢弃。
- **不做判分语义**：choice 标签→选项原文的映射与 fill/solve 原文透传之后即交给注入
  grader；数值归一化、单位门、字面等值等判分规则属 `grading` 模块，不在本模块。
- **不做卷面渲染与 OMR 涂卡识别**：与 `omr_sheet`/`paper_layout` 只共享题号编号语义
  （sections 顺序展开、空 sections 回退 `item_ids`）与选项标签闭式；答题卡生成、
  气泡定位、填涂识别不在本模块。
- **不做转写重试/多轮对话**：每次 `ingest_photo` 恰好一次 `vision` 调用，转写非法
  即抛 `IngestError`，不重试、不修补 JSON。
- **不做置信度学习/阈值自适应**：`min_confidence` 是入参（缺省 0.9），模块不统计、
  不调整门限。
- **不做复核队列的持久化与调度**：队列是本进程内的内存列表，顺序按本规格冻结
  （条目级转写序 + 缺号升序）；不写文件/数据库、不做去重/合并/优先级重排。
- **不做多图/批量**：一次调用处理一张图、一份卷面、一个转写响应；images 恒为
  `[image]` 单元素 list。
- **不做并发/异步/超时**：全同步纯函数表面，无线程/协程/重试/退避。
- **不做学生身份/会话状态**：模块不知道学习者是谁，不读环境、不留全局状态。
