# tts_reader 模块规格（冻结契约）

> 本文档是唯一权威契约。任何实现（参考实现或重生成实例）只要通过 tests/contract/ 全部测试
> 且满足本文全部条款，即为合格实现。实现算法自由，行为不允许偏离。
>
> **版本**：定稿 v1（第三波冻结轮）。
> 标注「〔测试裁定〕」的行为由 `tests/contract/test_tts_reader_contract.py`（26 项，其中
> 1 项 env-gated 冒烟默认 skip，默认运行 25 项）直接断言；标注「〔参考裁定〕」的行为契约
> 测试未仲裁，按参考实现 `src/xuexing/tts_reader.py` 冻结，并在当地注明本冻结轮实测探针
> （P1–P13，CPython 3.12.10 x64）。本文自包含：不引用仓库内其他规格文档；全部常量、
> 闭式值、守卫次序在本文内完整定义。
>
> 冻结基线：参考实现 + 契约测试全量实测于 2026-10-02，CPython 3.12.10 x64
> （`python -m pytest tests/contract/test_tts_reader_contract.py -q` → **25 passed,
> 1 skipped**；skip 项为 `test_smoke_real_stepfun_tts`，需 `XX_MM_SMOKE=1` 且真实
> API key，默认关闭）。

## 1. 目的

tts_reader 是语音读题（BACKLOG P3「tts_reader 语音读题」）的确定性内核：把一道题的
题干与选项渲染成**确定性朗读文本**（choice 题追加「选项L：正文」段；无题号、无作答
提示语，绝不含 `answer`/`solution`），交给**注入的 TTS 客户端**（鸭子表面
`tts(text, voice=…, response_format=…) -> bytes`，即 `mm_client.MMClient.tts` 的
表面）合成音频，并以 `(题目 id, voice)` 为键缓存音频字节——命中零次合成调用，未命中
恰好一次并回填调用方容器。`read_paper` 按卷面题序（sections 顺序展开、空 sections
回退 `paper.item_ids`，与 omr_sheet/paper_layout/mm_ingest 同编号语义）整卷合成，
共享同一缓存。行为契约：**朗读文本闭式可手算复核**、**合成调用次数与形状确定**、
**缓存语义确定**、**守卫失败零出网**、**同输入同输出**。模块间零 import：item/
paper/bank/tts 都是注入鸭子对象；与 mm_client（TTS_VOICE/TTS_FORMAT 常量）及
omr_sheet（parse_option 标签解析）的一致性由契约测试在测试内 import 对方模块跨模块
锁定，本模块自身不 import 任何 xuexing 模块。

## 2. 允许的依赖

- Python 标准库，逐个列出（即参考实现的 import 面）：
  - `hashlib`（`ItemAudio.to_dict` 的 `audio_sha256`）
  - `re`（选项显式标签正则，与 omr_sheet/mm_ingest 同款闭式）
  - `collections.abc` 的 `MutableMapping`（cache 容器表面判定）
  - `dataclasses` 的 `dataclass`（`ItemAudio`）
- **禁止 import `xuexing.types`**：本模块不 import 任何 xuexing 模块（**无例外**）。
  item/paper/bank/tts 一律按成员访问的鸭子类型；契约测试用 `xuexing.types.Paper`
  构造 paper，那只是测试侧注入的物件——其字段表面即本文 §3.6 锁定的鸭子表面，模块
  本身不得 import 它，也不得 import mm_client/omr_sheet。
- 禁止：第三方库、文件/网络 IO（含任何真实合成请求）、随机、系统时钟、环境读取、
  全局可变状态。
- 装载约束（参考实现 `src/xuexing/tts_reader.py:17-19` 以注释冻结）：禁止相对导入；
  禁止 `from __future__ import annotations`——它把 dataclass 字段注解字符串化，重生成
  注入装载（顶层模块名注册）时 `dataclasses` 的 KW_ONLY 探测按
  `sys.modules.get(cls.__module__)` 取模块 dict 会崩溃（与 mm_ingest 同约定）；
  注解直接写真实对象。

## 3. 公开 API

模块必须暴露以下 10 个名字（契约测试
`from xuexing.tts_reader import AUDIO_FORMAT, DEFAULT_VOICE, ITEM_TYPES,
READER_VERSION, ItemAudio, TTSError, build_reading_text, option_labels, read_paper,
synthesize_item`）。

### 3.1 常量与异常

- `TTSError(ValueError)`：模块唯一异常类型（ValueError 直接子类）。
  〔测试裁定 `test_frozen_constants`：`issubclass(TTSError, ValueError)`〕
- `READER_VERSION = "1"`。〔测试裁定〕
- `DEFAULT_VOICE = "linjiajiejie"`：默认音色；与 `mm_client.TTS_VOICE` 相等。
  〔测试裁定 `test_voice_and_format_match_mm_client`〕
- `AUDIO_FORMAT = "mp3"`：合成请求的 `response_format`；与 `mm_client.TTS_FORMAT`
  相等。〔测试裁定，同上〕
- `ITEM_TYPES = ("choice", "fill", "solve")`：合法题型（与 `types.Item.item_type`
  值域一致）。〔测试裁定〕

### 3.2 `option_labels(item) -> list[str]`

choice 题选项标签列。鸭子 item 只用 `item.options`（`item.id` 仅用于错误消息）。
规则（顺序为绑定条款）：

1. `options` 必须为 `list`/`tuple`，且 `2 <= len(options) <= 26`，否则 TTSError。
2. 逐项必须为非空白 `str`，否则 TTSError。
3. 标签：对 `raw.strip()` 匹配正则 `([A-Za-z])[.．、)）][ \t]*(.*)\Z`（`re.S`）；
   命中取 group(1) 并 `.upper()`（小写显式标签归一大写）；未命中按位回退
   `"ABCDEFGHIJKLMNOPQRSTUVWXYZ"[pos]`。
4. 归一后标签不得重复（`len(set(labels)) != len(labels)` → TTSError）。

实测闭式〔测试裁定 `test_option_labels_closed_forms`〕：

| options | 标签列 |
|---|---|
| `["A. 2", "B. 3"]` | `["A", "B"]` |
| `["a. 3", "b．7"]` | `["A", "B"]`（小写显式标签归一大写） |
| `["A. 1", "b. 2", "C）3", "d．4"]` | `["A", "B", "C", "D"]`（四种分隔符均可） |
| `["1", "2"]` | `["A", "B"]`（无显式标签按位回退） |

跨模块锁定〔测试裁定 `test_option_labels_matches_omr_sheet_parse_option`〕：对 C1/C2
`option_labels(item) == [parse_option(o, i)[0] for i, o in enumerate(item.options)]`
（`xuexing.omr_sheet.parse_option`）。

守卫失败一律 TTSError〔测试裁定 `test_option_labels_guards`〕：`<2` 项、`>26` 项、
重复标签（`["A. 1", "A. 2"]`）、空白项（`"   "`）、非 str 项（`5`）、`options=None`、
`options` 属性缺失（`getattr` 得 None → <2 支）。26 为合法上界（探针 P10：26 项通过、
27 项 TTSError）；tuple 型 options 合法（探针 P4）。

### 3.3 `build_reading_text(item) -> str`

一道题 → 确定性朗读文本。鸭子 item 使用：`item.id`（非空白 str）、`item.stem`
（非空白 str）、`item.item_type`（∈ ITEM_TYPES）、choice 时 `item.options`。

拼接规则（顺序为绑定条款）：

1. `segments = [stem.strip()]`。
2. choice：逐项追加 `f"选项{label}：{body}"`，`label` 来自 `option_labels(item)`，
   `body` = 显式标签匹配后的剩余文本 `.strip()`；无显式标签为原文 `.strip()`；
   body 空白 → TTSError。
3. 段间拼接：累积输出非空且**已以句末标点结尾**则不插「。」，否则插「。」；
   句末标点集恰为 `("。", "！", "？", ".", "!", "?")`（`：`、`，`、`…` 等一律视为
   非句末；必须是字符集合语义的**后缀判断**，不是单后缀匹配）。
4. 收尾：最终文本不以句末标点结尾则补「。」。

实测闭式〔测试裁定 `test_reading_text_choice_closed_forms` /
`test_reading_text_fill_solve_closed_forms`〕（fixtures：C1 stem `计算 1+1 等于多少？`
/ options `["A. 2", "B. 3"]`；C2 `比 5 小的数是哪个？` / `["a. 3", "b．7"]`；C3
`3 的相反数` / `["A. -3", "B. 3"]`；F1 fill `比 -3 大的最小整数是多少`；S1 solve
`解方程：2x + 1 = 7，写出完整过程。`）：

| 题 | 朗读文本 |
|---|---|
| C1 | `计算 1+1 等于多少？选项A：2。选项B：3。` |
| C2 | `比 5 小的数是哪个？选项A：3。选项B：7。` |
| C3 | `3 的相反数。选项A：-3。选项B：3。`（stem 无句末标点 → 补「。」） |
| F1 | `比 -3 大的最小整数是多少。` |
| S1 | `解方程：2x + 1 = 7，写出完整过程。`（句末已有「。」不重复） |
| fill `Compute 3-5.` | `Compute 3-5.`（ASCII `.` 亦算句末） |
| fill `列式计算：` | `列式计算：。`（`：` 非句末 → 插入） |

同一题重复调用逐字节相等。守卫失败一律 TTSError〔测试裁定
`test_reading_text_guards`〕：`id` 缺失（`del item.id`）/空白/非 str；`stem` 空白
（`"   "`）/非 str（`42`）；`item_type=None`；域外题型（`"essay"`）；选项正文空白
（`"B. "`）；choice 选项 `<2`。
〔参考裁定〕choice 题 `options` **属性整体缺失**时，参考实现先直接访问
`item.options`（`tts_reader.py:178`）再进入 `option_labels` 校验，抛
**AttributeError**（探针 P11b：`AttributeError: 'It' object has no attribute
'options'`；同一物件单独调 `option_labels` 则抛 TTSError，探针 P11a）。该形态契约
测试未覆盖（`test_reading_text_guards` 的缺属性用例只走 `option_labels`）。

### 3.4 `ItemAudio` 与 `ItemAudio.to_dict()`

```python
@dataclass
class ItemAudio:
    item_id: str
    voice: str
    text: str
    audio: bytes
    from_cache: bool
```

- 支持按位置构造 `ItemAudio("c1", "v", "t", b"ab", False)`；dataclass 逐字段相等。
  〔参考裁定，探针 P9；测试按关键字构造见 `test_item_audio_to_dict_shape`〕
- `to_dict() -> dict`：键序恰为
  `["item_id", "voice", "format", "text", "audio_size", "audio_sha256",
  "from_cache"]`〔测试裁定：`list(aud.to_dict()) == list(expected)` 键序冻结〕。
  字段约束：
  - `format` 恒为常量 `AUDIO_FORMAT`（`"mp3"`），**不是**构造入参；
  - `audio_size = len(audio)`；
  - `audio_sha256 = hashlib.sha256(audio).hexdigest()`（小写十六进制）；
  - **音频字节本身不序列化**；返回值整体 JSON 可序列化
    （`json.dumps(..., ensure_ascii=False)`）。
- 实测闭式〔测试裁定 `test_item_audio_to_dict_shape`〕：
  `ItemAudio(item_id="c1", voice=DEFAULT_VOICE, text=T_C1,
  audio=b"CACHED-AUDIO", from_cache=True).to_dict()` →
  `{"item_id": "c1", "voice": "linjiajiejie", "format": "mp3", "text": T_C1,
  "audio_size": 12, "audio_sha256": "0557b868…d883", "from_cache": True}`
  （SHA 为 `hashlib.sha256(b"CACHED-AUDIO").hexdigest()`，测试内独立复核）。

### 3.5 `synthesize_item(item, tts, *, voice=DEFAULT_VOICE, cache=None) -> ItemAudio`

单题合成。`voice`/`cache` 为关键字专参。守卫次序（编号顺序为绑定条款）：

- **V1**：`voice` 必须为非空白 str（`.strip()` 判空白；**使用原样，不 strip**）。
- **V2**：`tts` 必须提供可调用的 `tts` 成员（鸭子表面）。
- **V3**：`cache` 必须为 `None` 或 `MutableMapping`（`dict`/`UserDict` 等鸭子；
  `list`/`str`/非 Mapping 一律拒绝）。
- **V4**：`build_reading_text(item)`——**缓存命中也照常执行**（text 恒重建）
  〔参考裁定，探针 P13：命中路径上传非法 stem 仍 TTSError〕。

缓存键 = `(item.id, voice)`：

- **命中**：零次合成调用；缓存值必须为非空 `bytes` 否则 TTSError；返回
  `ItemAudio(..., from_cache=True)`，`text` 为本次重建值。
- **未命中**：恰好一次调用 `tts(text, voice=voice, response_format=AUDIO_FORMAT)`
  （关键字传参）；返回音频必须为非空 `bytes` 否则 TTSError 且**不回填缓存**；通过则
  `store[key] = audio`，返回 `ItemAudio(..., from_cache=False)`。
- tts 客户端自身异常**原样传播**（不包装、不改类型），cache 不被触碰。
- `cache=None`：每次调用内部新建空 dict——**无跨调用持久化**（两次调用各自未命中、
  共 2 次合成）。

实测闭式〔测试裁定〕：

- 未命中〔`test_synthesize_miss_calls_tts_once_exact_shape`〕：
  `synthesize_item(C1, tts)` → `("c1", "linjiajiejie", T_C1, b"MOCKMP3-1", False)`；
  `tts.calls == [{"text": T_C1, "voice": "linjiajiejie", "response_format":
  "mp3"}]`。
- 命中〔`test_synthesize_cache_hit_zero_tts_calls`〕：
  `cache={("c1", "linjiajiejie"): b"CACHED-AUDIO"}` → `audio == b"CACHED-AUDIO"`、
  `from_cache is True`、`text == T_C1`、`tts.calls == []`。
- voice 原样进键〔`test_synthesize_cache_key_is_item_id_plus_voice`〕：
  `voice=" vx "` 合法，键为 `("c1", " vx ")`，tts 收到 `voice=" vx "`（不 strip）；
  另一 voice 的缓存键不互蹭（`("c1", "other-voice")` 不命中默认 voice）。
- 回合与隔离〔`test_synthesize_cache_roundtrip_and_none_isolation`〕：同 cache 两次
  调用 → `[False, True]`、`len(tts.calls) == 1`；`cache=None` 两次 → 各 False、
  `len(tts.calls) == 2`。
- 鸭子 MutableMapping〔`test_synthesize_accepts_duck_mutable_mapping`〕：
  `UserDict({("c1", DEFAULT_VOICE): b"CACHED-AUDIO"})` 命中、零调用。
- 非法音频不回填〔`test_synthesize_bad_audio_not_cached`〕：tts 返 `b""` 或
  `"not-bytes"` → TTSError 且 `cache == {}`（各恰好 1 次调用）。
- 〔参考裁定〕命中路径缓存值为 `b""`/`bytearray` → TTSError（探针 P1/P5b；tts 侧
  返 `bytearray` 同样拒绝，探针 P5a）。

### 3.6 `read_paper(paper, bank, tts, *, voice=DEFAULT_VOICE, cache=None) -> list[ItemAudio]`

整卷读题：按卷面题序逐题合成（共享同一 cache），返回按卷面题序的 `ItemAudio` 列表。
`voice`/`cache` 为关键字专参。守卫次序（任一失败**零 tts 调用**）：

- **V1**：`voice` 非空白 str（同 §3.5，原样使用）。
- **V2**：tts 表面（可调用 `tts`）。
- **V3**：cache 表面（None 或 MutableMapping）。
- **V4**：paper 表面——`paper.paper_id`、`paper.title` 必须为 `str`（**不做非空白
  校验，空串接受**〔参考裁定，探针 P2；契约测试只覆盖 `None` 与非 str〕）。
- **V5**：bank 表面——`bank.items` 必须可调用且返回**可迭代**（list/generator 均可，
  探针 P8；返回 `42` → TTSError，探针 P7）；逐题 `id` 必须为非空白 str；bank 内
  id 不得重复（对全部题目生效，含未被卷面引用者）。
- **V6**：sections 规整化 + 逐题 item_type + 空卷门：
  - `paper.sections` 必须为 `list`/`tuple`；每元素必须为 `dict` 且其 `item_ids`
    必须为 `list`/`tuple`；每个 id 必须为非空白 str（额外键如 `kp_id`/`kp_name`
    一律忽略）；
  - **空 sections 回退**：`sections` 长度为 0 时回退 `paper.item_ids`（必须为
    `list`/`tuple`）作为单一隐式节；
  - 卷面引用的 id 必须能在 bank 索引中查到；其 `item_type` 必须 ∈ ITEM_TYPES
    （**只校验卷面引用到的题**——未被引用的题目 item_type 非法不影响〔参考裁定，
    探针 P3〕）；
  - 展开后题目数为 0 → TTSError（空卷门）。
- **V7**：全量朗读文本预校验——对每一道卷面题目调用 `build_reading_text`，任一失败
  → TTSError；即**先校验全卷再合成，首题失败前零出网**〔参考裁定，探针 P12：首题
  合法、次题非法时 `tts.calls == []`〕。

**卷面题序**（与 omr_sheet/paper_layout/mm_ingest 同编号语义）：节序 × 节内
`item_ids` 序；空 sections 回退 `paper.item_ids` 序。卷内同一题出现多次时，第二次起
命中共享缓存（`from_cache=True`、零新增合成）。传入的 `cache` 在本次调用内共享；
`cache=None` 时内部新建（探针 P6：同调用内重复题第二次命中、共 2 次合成）。

实测闭式〔测试裁定〕（fixtures：SECTIONS 两节 `["c1", "f1"]`、`["s1", "c2"]`；
BANK 含 c1/f1/s1/c2；MockTTS 按调用序回 `b"MOCKMP3-<n>"`）：

- 顺序与调用〔`test_read_paper_end_to_end_order_and_calls`〕：
  `[a.item_id for a in audios] == ["c1", "f1", "s1", "c2"]`（sections 展开序）；
  `[a.text ...] == [T_C1, T_F1, T_S1, T_C2]`；
  `[a.audio ...] == [b"MOCKMP3-1", b"MOCKMP3-2", b"MOCKMP3-3", b"MOCKMP3-4"]`；
  4 次调用全部 `voice=DEFAULT_VOICE`、`response_format="mp3"`。
- 卷内重复题〔`test_read_paper_shared_cache_duplicate_item`〕：sections
  `[["c1", "f1"], ["c1", "s1"]]` → `item_ids == ["c1", "f1", "c1", "s1"]`、
  `from_cache == [False, False, True, False]`、`len(tts.calls) == 3`。
- 空 sections 回退〔`test_read_paper_empty_sections_fallback_item_ids`〕：
  `sections=[]`、`item_ids=["f1", "c1"]` → `["f1", "c1"]`、`[T_F1, T_C1]`。
- 跨调用共享 cache 二次零合成〔`test_read_paper_second_pass_zero_calls_via_shared_cache`〕：
  首读后 `set(cache) == {(iid, DEFAULT_VOICE) for iid ∈ {c1, f1, s1, c2}}`；二次读卷
  `tts2.calls == []`、`from_cache` 全 `True`、`(item_id, text, audio)` 逐项与首读相等。
- 确定性与纯度〔`test_read_paper_determinism_and_inputs_not_mutated`〕：同输入两次
  `to_dict()` 列表相等；SECTIONS 与题目对象快照前后相等；cache 按键回填。
- 端到端〔`test_end_to_end_mm_client_mock_transport`〕：注入真 `MMClient`
  （MockTransport 回 `(200, b"ID3MOCKMP3")`）整卷 **4 次**传输调用，url 均为
  `ENDPOINTS["tts"]`，`Content-Type: application/json`，首调 body
  `{"model": MODEL_TTS, "input": T_C1, "voice": DEFAULT_VOICE,
  "response_format": "mp3"}`，4 段音频同为 `b"ID3MOCKMP3"`，
  `audios[0].to_dict()["audio_sha256"] == SHA_STEP`。

## 4. 不变量（编号列出，全部可被契约测试检验）

- I1 **冻结常量与异常层级**：`READER_VERSION="1"`、`DEFAULT_VOICE="linjiajiejie"`、
  `AUDIO_FORMAT="mp3"`、`ITEM_TYPES=("choice", "fill", "solve")`、`TTSError` ⊂
  `ValueError`；`DEFAULT_VOICE`/`AUDIO_FORMAT` 与 mm_client 跨模块相等。
  （`test_frozen_constants`、`test_voice_and_format_match_mm_client`）
- I2 **选项标签闭式**：显式标签（单 ASCII 字母 + `.．、)）`）解析、小写归一大写、
  无标签按位回退 `ABCDEFGHIJKLMNOPQRSTUVWXYZ`；与 `omr_sheet.parse_option`
  跨模块一致。（`test_option_labels_closed_forms`、
  `test_option_labels_matches_omr_sheet_parse_option`）
- I3 **选项表面守卫**：options 为 list/tuple、2..26 项、逐项非空白 str、标签不重复，
  违者 TTSError。（`test_option_labels_guards`）
- I4 **朗读文本闭式**：题干 + choice 的「选项L：正文」段；段间/收尾按句末标点集
  `。！？.!?` 不重复、否则补「。」；同输入同字节。
  （`test_reading_text_choice_closed_forms`、
  `test_reading_text_fill_solve_closed_forms`）
- I5 **朗读文本纯度**：从题干与选项正文构造，绝不含 `item.solution` / `item.answer`；
  无题号、无作答提示语。（`test_reading_text_hygiene_no_answer_material`）
- I6 **朗读文本守卫**：`item.id`/`item.stem` 非空白 str、`item.item_type` ∈
  ITEM_TYPES、选项正文非空白，违者 TTSError。（`test_reading_text_guards`）
- I7 **合成调用形状**：未命中恰好一次 `tts(text, voice=voice,
  response_format="mp3")`，全部关键字实参；voice 原样传递不 strip。
  （`test_synthesize_miss_calls_tts_once_exact_shape`、
  `test_synthesize_cache_key_is_item_id_plus_voice`）
- I8 **缓存语义**：键 = `(item.id, voice)`；命中零调用且 text 恒重建；未命中一次并
  回填调用方容器；非法音频（非 bytes/空）TTSError 且不回填；tts 异常原样传播且
  cache 不动；`cache=None` 无跨调用持久化；鸭子 MutableMapping 接受、list/str 拒绝。
  （`test_synthesize_cache_hit_zero_tts_calls`、
  `test_synthesize_cache_key_is_item_id_plus_voice`、
  `test_synthesize_cache_roundtrip_and_none_isolation`、
  `test_synthesize_accepts_duck_mutable_mapping`、
  `test_synthesize_bad_audio_not_cached`、
  `test_synthesize_tts_exception_propagates_cache_untouched`）
- I9 **ItemAudio/to_dict 冻结形状**：dataclass 五字段；to_dict 七键键序冻结、
  `format` 恒为 AUDIO_FORMAT、sha256 摘要、字节不序列化、JSON 可序列化。
  （`test_item_audio_to_dict_shape`）
- I10 **卷面题序与回退**：节序 × 节内 item_ids 序展开；空 sections 回退
  `paper.item_ids` 单一隐式节；卷内重复题第二次命中共享缓存（只合成一次）。
  （`test_read_paper_end_to_end_order_and_calls`、
  `test_read_paper_shared_cache_duplicate_item`、
  `test_read_paper_empty_sections_fallback_item_ids`）
- I11 **跨调用共享缓存**：同一 cache 容器二次读卷零合成、全 `from_cache`、结果逐项
  相等；键集恰为 `{(iid, voice)}`。
  （`test_read_paper_second_pass_zero_calls_via_shared_cache`）
- I12 **失败零出网**：`synthesize_item`/`read_paper` 的一切守卫（含卷面表面、bank
  表面、逐题类型、空卷门）失败时零 tts 调用、cache 不被污染。
  （`test_synthesize_guards_zero_calls`、`test_read_paper_guards_zero_calls`）
- I13 **端到端注入兼容**：与真 `MMClient` 表面兼容——整卷 N 次 tts 请求、payload
  `{model, input, voice, response_format}`、音频逐题一致。
  （`test_end_to_end_mm_client_mock_transport`）

## 5. 确定性与随机性

- `option_labels`/`build_reading_text`/`synthesize_item`/`read_paper` 均为纯函数：
  输出只依赖入参与注入 tts 的返回值；禁止 `random`、hash 序、系统时钟、环境读取、
  文件/网络 IO。音频字节的唯一来源是注入 tts 的返回值——模块不做任何字节变换、
  不重试、不记录 tts 侧状态（缓存只回填在调用方容器）。
- 唯一可变副作用：显式注入的 cache 容器被回填（按设计）。除此之外不修改任何入参
  （`read_paper` 不动 sections/题目对象，测试以 deepcopy 快照断言）；`cache=None`
  时内部 dict 随调用结束即弃。
- 无时间戳字段（无豁免）：`ItemAudio.to_dict()` 无时间字段，朗读文本不含时间信息。
- 同一 `(item 集合, paper, bank, tts 脚本, voice, cache 状态)` 重复调用逐位相等；
  tts 客户端的确定性由调用方注入保证（MockTTS 按调用序回字节；MMClient 走
  MockTransport）。

## 6. 错误行为

| 非法输入 | 行为（异常类型与时机） |
|---|---|
| `voice` 非 str / 空白 str（`""`、`"   "`、`5`、`None`） | 函数入口 V1 抛 `TTSError` |
| `tts` 无可调用 `tts` 成员（含鸭子缺成员、`object()`、字符串） | V2 抛 `TTSError` |
| `cache` 非 None 且非 MutableMapping（`5`、`["x"]`、`"x"`） | V3 抛 `TTSError` |
| `item.id`/`item.stem` 缺失 / 空白 / 非 str | V4（build_reading_text）`TTSError` |
| `item.item_type` 为 None 或域外值 | V4 `TTSError` |
| `item.options` 非 list/tuple、`<2`、`>26`、含非 str/空白项、标签重复 | `TTSError` |
| choice 选项正文（标签之后）空白 | `TTSError` |
| choice 题 `options` 属性整体缺失 | **`AttributeError`**（参考实现直接属性访问先于校验，§3.3〔参考裁定〕、探针 P11b；契约测试未覆盖，见返回值 ambiguities） |
| 缓存命中但缓存值非 bytes / 空 bytes | `TTSError`（不写回任何值）〔参考裁定，探针 P1/P5b〕 |
| tts 返回值非 bytes / 空 bytes | `TTSError` 且**不回填缓存** |
| `paper.paper_id` / `paper.title` 非 str（`None`、`5` 等） | V4 抛 `TTSError`（空串合法，§3.6〔参考裁定〕） |
| `paper.sections` 非 list/tuple；元素非 dict；`item_ids` 非 list/tuple；id 空白/非 str | V6 抛 `TTSError` |
| sections 空且 `paper.item_ids` 非 list/tuple | V6 抛 `TTSError` |
| 卷面引用 id 在 bank 中不存在 | V6 抛 `TTSError` |
| bank 无 `items()` / 返回不可迭代 / 题目 id 空白非 str / bank 内 id 重复 | V5 抛 `TTSError` |
| 展开后题目数为 0（空节 / 空回退列表） | 空卷门 `TTSError` |
| 任一题朗读文本校验失败（V7） | 合成开始前 `TTSError`，零 tts 调用 |

- 异常类型一律 `TTSError`（ValueError 直接子类），**唯一例外**为上表第 8 行——
  choice 缺 `options` 属性时参考实现泄漏的 `AttributeError`（§3.3/§7；该形态
  契约测试未覆盖，属已知行为分叉点，已在冻结轮 ambiguities 上报）。
- tts 客户端自身抛出的异常**原样传播**（类型与消息不变——实测
  `RuntimeError("tts down")` 穿透且 cache 不被触碰）；模块不重试、不包装。
- 必须容忍的「非错误」输入（不抛错、按语义处理）：sections 中的额外键（`kp_id`/
  `kp_name` 等）；bank 中未被卷面引用的题目（其 item_type 不校验）；`cache=None`。
- 异常消息文案不作承诺（不是契约面）。

## 7. 非目标

- **不做真实音频合成或网络调用**：tts 一律注入；模块零 IO、零网络、零重试。
- **不做音频处理**：不编解码、不转码、不探测时长/格式、不写文件或对象存储；
  音频字节原样透传给调用方（缓存的就是字节本身）。
- **不做语音参数编排**：不生成 SSML，不控语速/音调/音量，不批量多音色并发；
  `voice` 只是字符串参数（且原样使用，不做归一）。
- **不 import 任何 xuexing 模块**（含 `types`/`item`/`bank`/`mm_client`/
  `omr_sheet`）：全部鸭子类型注入；跨模块一致性由契约测试在测试侧锁定，本模块
  不自建依赖。
- **不做答案解析**：朗读文本从题干 + 选项正文构造，绝不注入 `answer`/`solution`；
  不出题号、不出作答提示语、不出讲解。
- **不做选项文本清洗**：只做「标签-正文」分离；不纠错、不翻译、不重排选项、不
  解释选项语义。
- **不做缓存管理**：无淘汰/TTL/预热/持久化/并发控制；cache 只是调用方传入的
  dict-like 容器，本模块只做查找与回填。
- **不做卷面构建或持久化**：不生成/修改 paper 与 bank，不整卷导出、不做跨卷聚合。
- **不做流式/异步/进度回调**：合成是同步逐题调用。
- **不做多模态客户端能力全集**：与 MMClient 的兼容面仅限 `tts(text, voice=…,
  response_format=…) -> bytes`；chat/embedding 等不在本模块。
- **不做冒烟联网验证**：`test_smoke_real_stepfun_tts`（`XX_MM_SMOKE=1`）是测试侧
  env-gated 用例，不在默认契约套件，也不构成本模块行为。
