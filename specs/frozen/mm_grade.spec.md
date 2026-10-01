# mm_grade 模块规格（冻结契约）

> 本文档是唯一权威契约。任何实现（参考实现或重生成实例）只要通过 tests/contract/ 全部测试
> 且满足本文全部条款，即为合格实现。实现算法自由，行为不允许偏离。
>
> **版本**：冻结 v1（第三波）。标注「〔测试裁定〕」的行为由
> `tests/contract/test_mm_grade_contract.py`（31 项）直接断言；标注「〔参考裁定〕」的行为
> 契约测试未仲裁，按参考实现 `src/xuexing/mm_grade.py` 冻结。本文自包含：不引用仓库内
> 其他规格文档，全部常量、schema、守卫顺序与冻结规则在本文内完整定义。
>
> 冻结基线：参考实现 + 契约测试全量实测于 2026-10-02，CPython 3.12.10 x64
> （`.venv/Scripts/python.exe -m pytest tests/contract/test_mm_grade_contract.py`
> → **31 passed**）。

## 1. 目的

mm_grade 是主观解答题（solve）手写作答照片的 **VLM 辅助判分确定性内核**：注入的 VLM 客户端
（鸭子参数 `client`，其表面由 `mm_client.MMClient` 满足）恰好一次转写学生解答步骤
（schema 冻结）→ 本地确定性分步给分规则（参考解切分、双向包含匹配、贪心配对，规则全部
冻结）→ 产出 `GradeSuggestion`（分步给分建议 + 复核原因）。人机协同复核闭环：干净建议
（`reasons` 为空）走 `suggest_response` 产出 `Response`；需复核建议（低置信 / 缺答案 /
步骤不齐 / 自相矛盾）走 `confirm_review` 由人给出终审，两条路**互斥**——每条建议恰好
一条路可走。判分诚实性：VLM prompt 只含题面（stem）与转写指令，**绝不含** answer/solution
（防止 VLM 抄参考答案进学生步骤）；给分完全在本地按冻结规则计算，VLM 不判分。宁可交人，
不猜：低置信步骤不计分只标记；步骤不齐记 `partial_match`；缺最终答案记
`final_answer_missing`；步骤全对但答案判错记 `contradiction`——任一命中即 `needs_review`。

## 2. 允许的依赖与装载约束

- Python 标准库，逐个列出：`json`（转写 JSON 解析）、`math`（`isfinite` 校验）、
  `re`（步骤序号标记 / 空白正则）、`dataclasses`（仅 `dataclass`）、
  `typing`（仅 `Optional`）
- `xuexing.types` —— **必须绝对导入** `from xuexing.types import Response`，且**只允许
  使用 `Response` 这一个类型**（`item_id: str`、`correct: bool`、
  `learner_answer: Optional[str] = None`、`response_ms: Optional[int] = None`；
  `src/xuexing/types.py:48-55`）
- 禁止：其他 xuexing 模块（**无例外**——`client` 与 `answer_grader` 都是注入的鸭子参数，
  不 import 其定义模块；一致性由契约测试在测试内 import 对方模块跨模块锁定）、第三方库、
  文件/网络 IO、全局可变状态
- 禁止：随机、系统时钟、环境读取（全模块无时间戳字段，无豁免）

重生成实例的装载约束（据参考实现 `src/xuexing/mm_grade.py:22-24` 的自述，注入机制见
`tests/conftest.py:31-34`，以顶层模块名 `_regen_mm_grade` 经 `spec_from_file_location`
装载并顶替 `sys.modules["xuexing.mm_grade"]`）：

- **禁止 `from __future__ import annotations`**（字符串化注解曾崩 dataclasses 探测）；
- **禁止相对导入**（注入装载为顶层模块名，相对导入在装载时失败）；
- 注解直接写真实对象（`Optional[str]` 等），装载环境不做延迟求值。

## 3. 公开 API

模块必须暴露以下 **19 个名字**（契约测试 `from xuexing.mm_grade import GRADE_VERSION,
IMAGE_FORMATS, MIN_CONFIDENCE, REASON_CONTRADICTION, REASON_FINAL_ANSWER_MISSING,
REASON_LOW_CONFIDENCE, REASON_PARTIAL_MATCH, REVIEW_REASONS, GradeError,
build_grade_prompt, confirm_review, grade_solution, match_key, parse_transcription,
solution_steps, steps_match, suggest_response`，另在测试函数内 import `GradeSuggestion,
StepScore`；并从 `xuexing.types import Response`）。

### 3.1 常量与异常（9 个名字，值一律冻结）

- `GradeError(ValueError)`：本模块唯一异常类型（**ValueError 直接子类**）
  〔测试裁定 `test_frozen_constants`〕。
- `GRADE_VERSION = "1"`（str）〔测试裁定〕。
- `MIN_CONFIDENCE = 0.9`：步骤级置信度门，`grade_solution` 的 `min_confidence` 默认值
  〔测试裁定〕。
- `IMAGE_FORMATS = ("png", "jpg", "jpeg", "webp", "gif")`（tuple，顺序与大小写均冻结）；
  与 `mm_client.IMAGE_MIME` 键集相等（`src/xuexing/mm_client.py:76-82`）
  〔测试裁定 `test_image_formats_match_mm_client_mime_keys`〕。
- `REASON_LOW_CONFIDENCE = "low_confidence"`：有步骤置信度低于门限。
- `REASON_FINAL_ANSWER_MISSING = "final_answer_missing"`：转写未发现最终答案。
- `REASON_PARTIAL_MATCH = "partial_match"`：建议得分 < 满分（步骤不齐）。
- `REASON_CONTRADICTION = "contradiction"`：步骤全配对但最终答案判错。
- `REVIEW_REASONS = (REASON_LOW_CONFIDENCE, REASON_FINAL_ANSWER_MISSING,
  REASON_PARTIAL_MATCH, REASON_CONTRADICTION)`：复核原因词表，**值与顺序冻结**；
  `suggestion.reasons` 严格按此顺序、无重复〔测试裁定〕。

### 3.2 `solution_steps(solution) -> list[str]`

参考解文本 → 步骤列表（本地确定性切分，判分侧唯一步骤来源）。冻结规则：按行切分
（`splitlines`，容忍 `\r\n`）→ 逐行去首尾空白 → 剥**一个**行首序号标记
`^[（(]?[0-9一二三四五六七八九十]{1,3}[、.．:：)）]\s*`（可选全/半角开括号 + 1..3 位
ASCII 数字或中文数字 + 恰一个分隔符 + 紧随空白）→ 再 strip → 丢空行。非 str →
`GradeError`；切不出步骤（空串 / 全空白）→ `[]`（拒绝由调用方守卫负责）。

**例子**〔测试裁定 `test_solution_steps_closed_forms`〕：
`solution_steps("解：设乙队每天修 x 米。\n(1) 列方程：3x + 30 = 480。\n2. 解方程得 x = 150。\n答：乙队每天修 150 米。")`
→ `["解：设乙队每天修 x 米。", "列方程：3x + 30 = 480。", "解方程得 x = 150。", "答：乙队每天修 150 米。"]`；
`solution_steps("第一行\r\n2.第二行\r\n")` → `["第一行", "第二行"]`；
`solution_steps("（一）验证。")` → `["验证。"]`；`solution_steps("十、总结")` → `["总结"]`；
`solution_steps("   \n  ")` / `solution_steps("")` → `[]`；`solution_steps(42)` → `GradeError`。

### 3.3 `match_key(text) -> str`

匹配键：全角折叠（码点 ∈ `[0xFF01, 0xFF5E]` → `chr(cp − 0xFEE0)`；`U+3000` → 半角空格）
→ 删除**全部**空白（`\s+`）→ 小写化。不做尾部标点剥离（双向包含已吸收标点差异）。
非 str → `GradeError`。

**例子**〔测试裁定 `test_match_key_closed_forms`〕：`match_key("Ｘ＝１５０")` → `"x=150"`；
`match_key("a  b　c")` → `"abc"`；`match_key("解：设乙队每天修 X 米。")` →
`"解:设乙队每天修x米。"`；`match_key("")` → `""`；`match_key(7)` → `GradeError`。

### 3.4 `steps_match(ref_text, student_text) -> bool`

双向包含（冻结）：`v == match_key(s)` 或 `match_key(r) in match_key(s)` 或
`match_key(s) in match_key(r)`。任一侧键为空（空白 / 空串步骤）→ `False`（空白步骤永不匹配）。
任一侧非 str → `GradeError`。

**例子**〔测试裁定 `test_steps_match_closed_forms`〕：
`steps_match("x = 150。", "x=150。")` → `True`；`steps_match("x = 150。", "所以x=150。")` → `True`；
`steps_match("解：设乙队每天修 x 米。", "设乙队每天修x米")` → `True`；
`steps_match("Ｘ＝１５０", "x=150")` → `True`；`steps_match("x = 150。", "x=45")` → `False`；
`steps_match("x = 150。", "  ")` → `False`；`steps_match("", "x=150")` → `False`；
`steps_match(5, "x=150")` → `GradeError`。

### 3.5 `build_grade_prompt(item) -> str`

solve 题 → 确定性 VLM 转写提示词。**只含题面，绝不含 answer/solution**。先跑与
`grade_solution` 相同的题目表面守卫（§3.8-V6），非法题目 → `GradeError`。返回文本恒为
下列 9 行以 `"\n"` 连接（文本逐字节冻结，prompt 版本由 `GRADE_VERSION` 承载）：

```text
你是阅卷助手。下面是一道主观解答题的题面，请从学生手写作答照片中逐行转写学生的解答过程。
只输出一个 JSON 对象，不要输出任何其他文字。
输出 JSON schema（冻结）：{"steps": [{"text": 学生某一步书写内容的原样转写, "confidence": 0 到 1 的数字}], "final_answer": 学生最终答案字符串或 null}
规则：
1. 只转写学生实际书写的内容，按书写顺序逐行转写；不补全、不改写、不自己计算。
2. text 是该步原样转写；confidence 是你对该步转写的置信度，取 0 到 1。
3. 学生写了最终答案则原样转写为 final_answer；没有写输出 null。
题面：
<item.stem 原样>
```

**例子**〔测试裁定 `test_prompt_closed_form`、`test_prompt_hygiene_no_reference_material`〕：
对题面 `"甲乙两队合修一条 480 米的路，乙队修了 3 天后还剩 30 米没修完，乙队平均每天修多少米？"`，
`build_grade_prompt(item)` 恒等于上表（`item.stem` 在末行），两次调用逐字节相等；prompt 中
**不得**出现标答 `"x=150"`、参考解片段 `"解：设乙队"` / `"3x + 30 = 480"` / `"解方程得"` /
`"列方程"` / `"答：乙队每天修"`；`build_grade_prompt(CHOICE)`（`item_type="choice"`）→ `GradeError`。

### 3.6 `parse_transcription(text) -> dict`

VLM 回复文本 → `{"steps": [{"text": str, "confidence": float}, ...], "final_answer": str | None}`。

冻结处理：文本先 `strip()`；取**首个 `"{"` 到最后一个 `"}"`** 的切片做 JSON 解析
（前后闲话 / 代码围栏容忍）；切片范围非法或 JSON 解析失败 → `GradeError`；顶层必须是
`dict`；`steps` 必须存在且为 `list`（空 list 合法）。每条步骤必须为 `dict` 且必含
`text`（str）与 `confidence`（[0,1] 的**有限**数字，拒 `bool`，int 规整为 float）两键，
未知键忽略；空白 `text` 合法（评分侧永不匹配）。`final_answer` 可选：缺席 / `null` /
空白串 → `None`；非 str 非 null → `GradeError`。

**例子**〔测试裁定 `test_parse_transcription_closed_forms`〕：
`parse_transcription('{"steps": [{"text": "x=150", "confidence": 1}]}')` →
`{"steps": [{"text": "x=150", "confidence": 1.0}], "final_answer": None}`（`confidence` 为 float，
输出步骤 dict 的键集恰为 `{"text", "confidence"}`）；
`parse_transcription("```json\n" + '{"steps": [], "final_answer": "  "}' + "\n``` 前后闲话")` →
`{"steps": [], "final_answer": None}`；`parse_transcription('{"steps": []}')` →
`{"steps": [], "final_answer": None}`。

### 3.7 数据形状（2 个 dataclass）

```python
@dataclass
class StepScore:
    index: int                  # 参考步骤下标（0 起，参考解切分序）
    ref_text: str               # 参考步骤原文（切分后）
    student_text: Optional[str] # 配对到的学生步骤原文；未配对 None
    awarded: int                # 1=配对计 1 分；0=未配对不计分
```

```python
@dataclass
class GradeSuggestion:
    item_id: str
    steps: list                 # list[StepScore]，参考步骤序
    max_points: int             # 满分 = 参考步骤数
    suggested_points: int       # 建议得分（配对数）
    final_answer: Optional[str] # 转写最终答案（空白已规整为 None）
    final_answer_correct: bool  # answer_grader(item, final_answer) 的判定
    flagged_steps: list         # list[str]：低于置信度门的学生步骤原文（转写序）
    reasons: list               # list[str]：REVIEW_REASONS 词表序、无重复
    needs_review: bool          # == bool(reasons)
```

- `StepScore.to_dict()` 键集恰为 `{"index", "ref_text", "student_text", "awarded"}`；
  `GradeSuggestion.to_dict()` 键集恰为 `{"item_id", "steps", "max_points",
  "suggested_points", "final_answer", "final_answer_correct", "flagged_steps",
  "reasons", "needs_review"}`，其中 `steps` 为各 `StepScore.to_dict()` 的列表，
  `flagged_steps` / `reasons` 为拷贝；输出必须可 `json.dumps` 序列化
  〔测试裁定 `test_step_score_and_suggestion_to_dict_shapes`〕。
- dataclass 逐字段相等（`a == b`）是确定性判定方式〔测试裁定
  `test_grade_solution_determinism_same_input_same_output`〕。

### 3.8 `grade_solution(item, image, client, answer_grader, *, image_format="png", min_confidence=MIN_CONFIDENCE) -> GradeSuggestion`

VLM 辅助判分管线。**守卫顺序冻结（任一失败抛 `GradeError`，且零次 `client.vision` 调用）**：

| 编号 | 守卫 |
|---|---|
| V1 | `client` 有 callable `vision` |
| V2 | `answer_grader` callable |
| V3 | `image` 为非空 `bytes` |
| V4 | `image_format in IMAGE_FORMATS`（大小写敏感，`"PNG"` 拒） |
| V5 | `min_confidence` 为 [0,1] 的有限数字（拒 `bool`） |
| V6 | 题目表面：`id` 非空 str → `item_type == "solve"` → `stem` 非空 str → `answer` 非空 str → `solution` 为 str 且切出 ≥ 1 步 |

通过 V1–V6 后：

1. **恰好一次出网**：`raw = vision_fn(_render_grade_prompt(stem), [image], image_format=image_format)`
   —— 线上 prompt 逐字节等于 `build_grade_prompt(item)`，images 恰为 `[image]`，
   `image_format` 原样透传。
2. `parse_transcription(raw)`：任何解析失败 → `GradeError`，且 **`answer_grader` 不被调用**。
3. **恰好一次答案判定**：`verdict = answer_grader(item, final_answer)`（`final_answer` 可为
   `None`——**无证据也诚实判定一次，不伪造**）；返回值必须为 `bool`，否则 `GradeError`。
4. **分步给分（规则冻结）**：`confidence < min_confidence` 的学生步骤**不参与匹配**、
   原文按转写序进 `flagged_steps`；其余（trusted）步骤按参考步骤序贪心配对——每个参考
   步骤取转写序中**第一个未被占用且 `steps_match`** 的学生步骤，配对计 1 分，每个学生步骤
   **至多用一次**；多余学生步骤不扣分也不标记。`max_points = len(ref_steps)`，
   `suggested_points = Σawarded`。
5. **复核路由（按 `REVIEW_REASONS` 词表序累积）**：有 `flagged_steps` → `low_confidence`；
   `final_answer is None` → `final_answer_missing`；`suggested < max_points` → `partial_match`；
   `suggested == max_points and verdict is False` → `contradiction`。`reasons` 非空即
   `needs_review`。`partial_match` 与 `contradiction` 互斥（建议分不可能既等于又小于满分）。
6. `client` / `answer_grader` 抛出的异常**原样传播**（不包装、不吞）。

**例子**〔测试裁定 `test_grade_solution_full_match_clean_auto`〕：参考解切出 4 步（§3.2），
转写 4 步全置信 1.0 且 `final_answer="x=150"`、判定器返回 `answer == "x=150"` →
`item_id="s1"`、`max_points=4`、`suggested_points=4`、`awarded=[1,1,1,1]`、
`index=[0,1,2,3]`、`final_answer_correct is True`、`flagged_steps=[]`、`reasons=[]`、
`needs_review is False`；`client.vision` 恰 1 次且 prompt/images/image_format 为
`(build_grade_prompt(item), [image], "png")`，`answer_grader` 恰 1 次调用 `("s1", "x=150")`；
`to_dict()` 与另一次同输入调用逐字段相等。

### 3.9 `suggest_response` 与 `confirm_review`（闭环两路，互斥）

```python
def suggest_response(suggestion, response_ms=None) -> Response
def confirm_review(suggestion, correct, learner_answer=None, response_ms=None) -> Response
```

- `suggest_response`：干净建议（`needs_review` 为 `False`）→
  `Response(item_id=..., correct=True, learner_answer=suggestion.final_answer,
  response_ms=response_ms)`。干净建议按构造必是「步骤全配对 + 最终答案在场且判对」，
  故 `correct` 恒 `True`。`needs_review=True` 的建议 → `GradeError`（必须走人审）。
- `confirm_review`：需复核建议（`needs_review` 为 `True`）→
  `Response(item_id=..., correct=correct, learner_answer=<传入值或 suggestion.final_answer>,
  response_ms=response_ms)`。`correct` 必须为 `bool`；`learner_answer` 缺省（`None`）记录
  转写的 `final_answer`，传入非 `None` 值则按人审改写记录。`needs_review=False` 的干净
  建议 → `GradeError`（防止人审路径静默绕过自动结论）。
- 两者的 `suggestion` 必须暴露非空 str `item_id` 与 bool `needs_review`，否则 `GradeError`。

**例子**〔测试裁定 `test_confirm_review_human_path_and_gate`、
`test_suggest_response_gate_on_needs_review`〕：部分配对（前 2 步）的建议
`needs_review=True` → `confirm_review(s, True)` == `Response("s1", True, "x=150", None)`；
`confirm_review(s, False)` == `Response("s1", False, "x=150", None)`；
`confirm_review(s, True, learner_answer="x=150（抄错行）")` == `Response("s1", True, "x=150（抄错行）", None)`；
`confirm_review(s, True, response_ms=1234)` == `Response("s1", True, "x=150", 1234)`；
`confirm_review(s, 1)` → `GradeError`；干净建议 `confirm_review(clean, True)` → `GradeError`；
`needs_review=True` 时 `suggest_response(s)` → `GradeError`；`suggest_response(object())`
（无 bool `needs_review`）→ `GradeError`。

## 4. 不变量（编号列出，全部可被契约测试检验）

- I1 **常量冻结**：`GRADE_VERSION == "1"`、`MIN_CONFIDENCE == 0.9`、
  `IMAGE_FORMATS == ("png", "jpg", "jpeg", "webp", "gif")`、`REVIEW_REASONS` 为四元组
  `("low_confidence", "final_answer_missing", "partial_match", "contradiction")`、
  四个 `REASON_*` 与 `REVIEW_REASONS` 逐项相等、`issubclass(GradeError, ValueError)`；
  `IMAGE_FORMATS` 排序后与 `mm_client.IMAGE_MIME` 键集排序后相等。
  〔测试裁定 `test_frozen_constants`、`test_image_formats_match_mm_client_mime_keys`〕
- I2 **prompt 冻结文本与判分卫生**：`build_grade_prompt(item)` 是 §3.5 的 9 行文本，
  `item.stem` 出现且为末行，**不含** `item.answer` 及其子串形态、不含 `item.solution` 的
  步骤片段；同输入两次调用逐字节相等；非 solve 题目被 V6 拒。
  〔测试裁定 `test_prompt_closed_form`、`test_prompt_hygiene_no_reference_material`〕
- I3 **转写 schema 冻结**：`parse_transcription` 只接受 §3.6 的形状（首 `{` 至末 `}` 切片、
  顶层 dict、`steps` 为 list、每步 `text`/`confidence` 两键必填且 `confidence` ∈ [0,1] 有限
  数字拒 bool、int 规整 float、未知键忽略、`final_answer` 可选且空白 → `None`）；其余全部
  违例抛 `GradeError`。〔测试裁定 `test_parse_transcription_closed_forms`、
  `test_parse_transcription_guards`〕
- I4 **参考解切分与匹配规则冻结**：`solution_steps` 按行 + 剥**一个**行首序号标记 + 丢空行；
  `match_key` = 全角折叠 → 删全部空白 → 小写；`steps_match` = 双向包含且任一侧空键 → `False`。
  〔测试裁定 `test_solution_steps_closed_forms`、`test_match_key_closed_forms`、
  `test_steps_match_closed_forms`〕
- I5 **分步给分规则冻结**：`max_points == 参考步骤数`；低于门限的学生步骤只进
  `flagged_steps` 不参与匹配（门限为**含等于**：`confidence == min_confidence` 参与匹配）；
  贪心配对按参考步骤序、每参考步骤取转写序最前未占用匹配者、每学生步骤至多用一次；
  多余学生步骤不扣分不标记；`suggested_points == Σawarded`。
  〔测试裁定 `test_grade_solution_partial_match_flags_review`、
  `test_grade_solution_low_confidence_excluded_and_flagged`、
  `test_grade_solution_confidence_boundary_is_inclusive`、
  `test_grade_solution_greedy_uses_each_student_step_once`、
  `test_grade_solution_extra_student_steps_not_penalized`、
  `test_grade_solution_answer_only_still_review`〕
- I6 **出网与判定恰好一次、失败纪律**：守卫失败零出网；成功后 `client.vision` 恰一次
  （prompt == `build_grade_prompt(item)`、`images == [image]`、`image_format` 透传）、
  `answer_grader` 恰一次（`(item, final_answer)`，含 `final_answer is None`）；解析失败时
  `answer_grader` 不被调用；`answer_grader` 返回非 `bool` → `GradeError`；注入对象抛出的
  异常原样传播（不包装、不吞）。〔测试裁定
  `test_grade_solution_single_vision_call_passthrough`、
  `test_grade_solution_parse_failure_one_call_no_grader`、
  `test_grade_solution_answer_grader_must_return_bool`、
  `test_grade_solution_exceptions_propagate_unwrapped`、
  `test_grade_solution_guards_fail_before_any_network_call`〕
- I7 **复核路由词表序与互斥**：`reasons` 按 `REVIEW_REASONS` 序、无重复；
  `partial_match`（`suggested < max_points`）与 `contradiction`
  （`suggested == max_points and verdict is False`）互斥并发；
  `needs_review == bool(reasons)`。〔测试裁定
  `test_grade_solution_low_confidence_excluded_and_flagged`、
  `test_grade_solution_final_answer_missing`、
  `test_grade_solution_contradiction_when_full_but_wrong`、
  `test_grade_solution_reason_order_and_completeness`〕
- I8 **闭环两路互斥**：干净建议只能走 `suggest_response`（`correct` 恒 `True`、
  `learner_answer` 为转写 `final_answer`）；需复核建议只能走 `confirm_review`
  （`correct` 必须为 `bool`、`learner_answer` 缺省记录转写答案）；走错路即 `GradeError`。
  〔测试裁定 `test_grade_solution_full_match_clean_auto`、
  `test_confirm_review_human_path_and_gate`、`test_suggest_response_gate_on_needs_review`〕
- I9 **确定性与纯度**：同输入（含注入的 client 回复文本与 grader）两次
  `grade_solution` 的 `to_dict()` 与 dataclass 相等；不修改入参 `item.solution` 与 `image`
  （字节快照前后相等）。〔测试裁定
  `test_grade_solution_determinism_same_input_same_output`、
  `test_grade_solution_inputs_not_mutated`〕
- I10 **数据形状与 JSON 可序列化**：`StepScore.to_dict()` / `GradeSuggestion.to_dict()`
  键集恰为 §3.7 所列，`json.dumps(data, ensure_ascii=False)` 不抛。
  〔测试裁定 `test_step_score_and_suggestion_to_dict_shapes`〕
- I11 **跨模块锁定（被测模块零 import）**：`grading.grade` 作 `answer_grader` 时
  分步给分走通（方程解字面判对 / `"x=45"` 判错 → `contradiction`；`10/12 ≡ 5/6` 数值等值
  判对；`final=None` 交 `grade(item, None)` 判 `False` → `final_answer_missing +
  contradiction`）；`MMClient` + `MockTransport` 全 mock 端到端跑通，线上请求体
  `messages[0].content[0]` 逐字节等于 `{"type": "text", "text": build_grade_prompt(item)}`，
  URL 为 `ENDPOINTS["chat"]`，转写 JSON 被结构化解析并进入冻结规则给分。
  〔测试裁定 `test_cross_module_grading_grade_as_answer_grader`、
  `test_end_to_end_mm_client_mock_transport_wire_prompt`〕

## 5. 确定性与随机性

- 全模块纯函数：无 IO、无随机、无时钟、不读环境，同输入同输出。**唯一的外部交互是注入的
  `client.vision` 恰好一次调用**——模块的确定性是相对于该次调用的返回文本而言的；prompt 由
  `item` 确定性渲染（`build_grade_prompt` 同输入逐字节相等）。
- 禁止：`random`、hash 序、`datetime.now`/`time`、`os.environ`、文件读写、全局可变状态、
  可变默认参数。无时间戳字段，无豁免字段。
- 浮点/整数可复现性：`confidence` 经 `float()` 规整；`min_confidence` 边界为
  `confidence < min_confidence`（IEEE 比较）；`suggested_points` 为整数和。§3.2–§3.9 中
  每个输入输出例子都是逐位对照点。
- `parse_transcription` 的 JSON 解析取「首个 `{` 至最后一个 `}`」切片，该切片策略是确定性
  条款（不是启发式容错的可选实现）。

## 6. 错误行为

异常类型一律 `GradeError`（`ValueError` 直接子类），**唯一例外**是注入的 `client.vision`
与 `answer_grader` 自身抛出的异常——按 §3.8 第 6 条**原样传播**（不包装、不吞）。

| 非法输入 | 行为 |
|---|---|
| `solution_steps(42)` 等非 str | `GradeError` |
| `match_key(7)` 等非 str | `GradeError` |
| `steps_match` 任一侧非 str（如 `(5, "x=150")`） | `GradeError` |
| `steps_match` 任一侧键为空（`""` / 空白） | 容忍，返回 `False` |
| `build_grade_prompt` / `grade_solution` 的 `item` 非 solve（如 `item_type="choice"`） | `GradeError`（V6，零出网） |
| `item.id` 非 str 或空白 | `GradeError`（V6，零出网） |
| `item.stem` 非 str 或空白 | `GradeError`（V6，零出网） |
| `item.answer` 非 str 或空白 | `GradeError`（V6，零出网） |
| `item.solution` 非 str（如 `42`） | `GradeError`（V6，零出网） |
| `item.solution` 为 str 但切不出步骤（`""` / `" \n "`） | `GradeError`（V6，零出网） |
| `client` 无 callable `vision` | `GradeError`（V1，零出网） |
| `answer_grader` 非 callable（`None` / `"grader"`） | `GradeError`（V2，零出网） |
| `image` 为空 bytes 或非 bytes（`None` / `"img"`） | `GradeError`（V3，零出网） |
| `image_format` 不在 `IMAGE_FORMATS`（`"bmp"` / `"PNG"` 大小写敏感） | `GradeError`（V4，零出网） |
| `min_confidence` 非 [0,1] 有限数字（`-0.1` / `1.5` / `True` / `"0.9"` / `nan`） | `GradeError`（V5，零出网） |
| `parse_transcription` 入参非 str（`None`） | `GradeError`（已出网 1 次，`answer_grader` 未调用） |
| `parse_transcription` 收到空/全空白文本、无 JSON 对象（`"no braces"`、`"{"`、`"}"`）、JSON 解析失败（`"not json {bad} tail"`） | `GradeError` |
| `parse_transcription` 顶层非 dict（`"[1]"`） | `GradeError` |
| `parse_transcription` 缺 `steps` 或 `steps` 非 list（`"{}"`、`'{"steps": {}}'`） | `GradeError` |
| `parse_transcription` 步骤非 dict（`'{"steps": [5]}'`）、缺 `text`/`confidence`、`text` 非 str、`confidence` 非 [0,1] 有限数字（`-0.1` / `1.1` / `"0.9"` / `True` / `None` / `inf` / `nan`） | `GradeError` |
| `parse_transcription` 的 `final_answer` 非 str 非 null（如 `42`） | `GradeError` |
| `parse_transcription` 的 `final_answer` 为空白串（`"  "`）或缺席或 `null` | 容忍，规整为 `None` |
| `parse_transcription` 未知顶层/步骤内键（`extra` / `junk`） | 容忍，忽略 |
| `parse_transcription` 的 `steps` 为空 list | 容忍，得 `{"steps": [], "final_answer": ...}` |
| `answer_grader` 返回非 `bool`（如 `"yes"`） | `GradeError`（已出网 1 次） |
| `client.vision` 抛 `RuntimeError` | 原样传播 `RuntimeError`（不包装） |
| `answer_grader` 抛 `ValueError` | 原样传播 `ValueError`（不包装） |
| `suggest_response(needs_review=True 的建议)` | `GradeError` |
| `suggest_response(object())` 等无 bool `needs_review` 的鸭子对象 | `GradeError` |
| `confirm_review(needs_review=False 的干净建议, ...)` | `GradeError` |
| `confirm_review(..., correct=1)` 等非 bool | `GradeError` |
| `suggestion.item_id` 非 str 或为空 | `GradeError` |

## 7. 非目标

- **不做 OCR / 图像前处理**：`image` 只作为不透明 `bytes` 传给注入的 `client.vision`；
  不裁剪、不二值化、不压缩、不旋转、不识别手写字体。
- **自身不出网、不调度客户端**：模块内无任何网络代码；真实请求只发生在注入的 `client`
  （其 prompt、URL、鉴权、重试、限流全部归 `mm_client`，不在本模块）。
- **不做答案等值判定**：`final_answer_correct` 完全由注入的 `answer_grader` 决定；本模块
  不解析数值/分数/单位/方程，不做 `5/6 ≡ 10/12` 这类等值（那属 `grading` 的职责，
  本模块不 import 它）。
- **不靠 VLM 判分**：VLM 只做转写；给分 100% 在本地按 §3.8 第 4/5 步的冻结规则计算。
  给分规则不得改成调用 VLM 打分。
- **不管 choice / fill / 其他题型**：`item_type` 必须恰为 `"solve"`；客观题由 `grading`
  确定性直判，不进 VLM。
- **不给低置信步骤部分分**：低于门限的步骤只标记不计分，不做「按置信度折算分数」。
- **不给半分 / 不做连续分**：给分粒度为「每个参考步骤 0 或 1」的整数分，无半分、无权重步。
- **不惩罚多余学生步骤**：多余转写步骤不扣分、不标记、不计入任何原因。
- **不重排 / 合并 / 去重参考或学生步骤**：输出顺序恒为参考解切分序；学生步骤只按转写序
  参与贪心配对。
- **不做行首序号标记的智能纠错**：`_STEP_MARKER_RE` 冻结；已知边界——行首以「12.5」这类
  小数开头的正文会被误剥（按非目标处理，参考解不应这样书写）。
- **不做持久化 / 复核队列 / 复核人分配**：只产出 `needs_review` 标记与 `Response`；
  队列存储、复核人路由、批改流转不在本模块。
- **不变更 prompt 版本或 schema**：`GRADE_VERSION` 恒为 `"1"`，§3.5 文本与 §3.6 schema
  逐字节冻结；加字段/改文案 = 换契约。
- **不引入第三方库、文件/网络 IO、随机、时钟、环境读取**；不做全局可变状态。
