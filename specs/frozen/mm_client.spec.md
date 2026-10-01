# mm_client 模块规格（冻结契约）

> 本文档是唯一权威契约。任何实现（参考实现或重生成实例）只要通过 tests/contract/ 全部测试
> 且满足本文全部条款，即为合格实现。实现算法自由，行为不允许偏离。
>
> 标注「〔测试裁定〕」的行为由 `tests/contract/test_mm_client_contract.py` 直接断言；
> 标注「〔参考裁定〕」的行为契约测试未仲裁，按参考实现 `src/xuexing/mm_client.py` 冻结。
> 本文自包含：不引用仓库内其他规格文档；全部常量、字节闭式、守卫次序在本文内完整定义。
>
> 冻结基线：参考实现 + 契约测试全量实测于 2026-10-02，CPython 3.12.10 x64
> （`python -m pytest tests/contract/test_mm_client_contract.py -q` → **28 passed,
> 1 skipped**，skip 为 env-gated 冒烟用例）。端点/模型/voice 常量以
> `docs/multimodal-api.md`（2026-09-29 阶跃 API 实测矩阵）为事实来源。契约套件零网络：
> 传输一律注入 MockTransport，DNS 一律注入解析桩；key 一律用哨兵值 `"sk-SENTINEL-1"`。

## 1. 目的

mm_client 是学情 agent 的多模态客户端：把 chat（文本）、vision（图像理解，与 chat
同一端点）、tts（语音合成）、asr（语音转写）四能力收敛到**一个可注入的传输出口**
（Transport 协议单口发出）。行为契约：**端点白名单六重门**（https + api.stepfun.com
+ 无 userinfo + 显式端口必须 443 + 解析 IP 逐个阻断私网/环回/链路本地/保留/组播/
未指定）、**key 纪律**（只从环境变量按优先序读取、strip 后只进内存、任何错误消息
绝不回显 key）、**单一错误家族 LLMError**（HTTP 失败、响应形状错、参数非法、白名单
违规、key 缺失全部归族）、**请求构造纯函数化**（同输入同字节；multipart 用固定边界
常量 BOUNDARY，无隐藏随机；不读时钟）。参考实现零 xuexing 依赖、纯标准库；
HttpTransport 是唯一网络豁免（仅参考，不在契约覆盖内，见 §3.3/§7）。

## 2. 允许的依赖与装载约束

- Python 标准库，**逐个列出**（冻结参考实现的 import 面）：
  `base64`、`ipaddress`、`json`、`math`、`os`、`socket`、`urllib.error`、
  `urllib.parse`、`urllib.request`、`typing`（仅 `Callable`/`Mapping`/`Optional`/
  `Protocol`/`Sequence`）
- **`xuexing.types`：不依赖**（参考实现 import 面无任何 xuexing 符号；本规格无
  Profile/Response 等类型条款）
- 禁止：其他 xuexing 模块（**无例外**）、第三方库（参考实现无任何第三方 import）
- 文件 IO：**无**。网络 IO：仅 `HttpTransport.post`（stdlib urllib 单次 POST，
  〔参考裁定〕无契约覆盖）；其余 API 禁止任何 IO
- 环境读取：仅 `api_key(env=None)` 的默认路径读 `os.environ`（显式注入点，I3）
- 禁止：随机源、系统时钟（timeout 是显式构造参数，常量 `DEFAULT_TIMEOUT = 60.0`）

重生成实例的装载约束（实测，2026-10-02：`tests/conftest.py:23-34` 以顶层模块名
`_regen_mm_client` 经 `spec_from_file_location` 装载 `<impl_dir>/mm_client.py` 并顶替
`sys.modules["xuexing.mm_client"]`；用只抛标记异常的桩文件实测，装载即替位生效）：

- **禁止相对导入**（`from .types import ...` 等）：实测在 `exec_module` 处抛
  `ImportError: attempted relative import with no known parent package`（桩文件
  `from . import types` 在 conftest 收集期即失败）。
- 绝对导入 stdlib 实测可装载。本模块不含 dataclass，`from __future__ import
  annotations` 仅为标注延迟求值，参考实现即使用、基线全绿；重生成实例可用可不用。

## 3. 公开 API

模块必须暴露以下 **24 个模块级公开名字**（与参考实现 `__all__` 逐项一致；契约测试
`from xuexing.mm_client import ...` 覆盖其中 22 个，`Transport`/`HttpTransport`
由源码面与冒烟用例覆盖），外加 **MMClient 的 4 个公开方法**（chat/vision/tts/asr），
合计 **28 项公开 API**。

### 3.1 冻结常量与异常

全部取值为冻结条款〔测试裁定 `test_frozen_constants`（tests/contract/
test_mm_client_contract.py:61-80）〕：

| 名字 | 冻结值 |
|---|---|
| `BASE_URL` | `"https://api.stepfun.com"` |
| `ALLOWED_HOST` | `"api.stepfun.com"` |
| `ENDPOINTS` | `{"chat": "https://api.stepfun.com/step_plan/v1/chat/completions", "tts": "https://api.stepfun.com/step_plan/v1/audio/speech", "asr": "https://api.stepfun.com/v1/audio/transcriptions"}`（注意 asr **不在** `step_plan` 路径下） |
| `MODEL_CHAT` | `"step-5-preview"`（文本/视觉主力，vision 唯一可用） |
| `MODEL_TTS` | `"stepaudio-2.5-tts"` |
| `MODEL_ASR` | `"stepaudio-2.5-asr"` |
| `TTS_VOICE` | `"linjiajiejie"` |
| `TTS_FORMAT` | `"mp3"` |
| `KEY_ENV_VARS` | `("XX_LLM_API_KEY", "STEPFUN_API_KEY")`（优先序，从左到右） |
| `DEFAULT_TIMEOUT` | `60.0`（float） |
| `BOUNDARY` | `"xuexing-mm-boundary-v1"`（非空 str、不以 `"--"` 开头；固定边界即无隐藏随机） |
| `JSON_CONTENT_TYPE` | `"application/json"` |
| `MULTIPART_CONTENT_TYPE` | `"multipart/form-data; boundary=" + BOUNDARY` |
| `IMAGE_MIME` | `{"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp", "gif": "image/gif"}`（大小写敏感；`jpg`/`jpeg` 同 mime） |
| `LLMError` | `class LLMError(RuntimeError)` —— 本模块**唯一异常家族**（key 缺失、白名单违规、参数非法、HTTP 失败、响应形状错全部归族）；安全条款：任何错误消息不得包含 api key 值〔测试裁定 `assert issubclass(LLMError, RuntimeError)`〕 |

模块内部维护 `ENDPOINTS` 的 URL→能力反向映射（`_CAP_BY_URL`，私有）：MockTransport
按请求 URL 查表选择应答，未知 URL 落 404 支（§3.3）。

### 3.2 纯函数：key 纪律、白名单守卫、请求构造

#### 3.2.1 `api_key(env: Optional[Mapping[str, str]] = None) -> str`

按 `KEY_ENV_VARS` 顺序取**第一个 strip 后非空**的 str 值，返回 strip 后的值。
`env=None` 读 `os.environ`；候选值非 `str` 视为缺失跳过（`None` 为〔测试裁定〕；
`int` 等其余非 str 类型按同一 `isinstance` 检查跳过，为〔参考裁定〕）；
全缺 → `LLMError`，消息含 `not set` 与两个变量名、**不含任何候选值**。

实测〔测试裁定 `test_api_key_priority_strip_and_missing`（:91-100）〕：

- `api_key({"XX_LLM_API_KEY": " k1 ", "STEPFUN_API_KEY": "k2"})` → `"k1"`（优先序）
- `api_key({"XX_LLM_API_KEY": "  ", "STEPFUN_API_KEY": " k2 "})` → `"k2"`（空白跳过）
- `api_key({"XX_LLM_API_KEY": None, "STEPFUN_API_KEY": "k2"})` → `"k2"`（非 str 跳过）
- `api_key({})` → `LLMError`：消息含 `"not set"`、`"XX_LLM_API_KEY"`、
  `"STEPFUN_API_KEY"`，且 `"k1"` 不出现在消息中（不回显）
- `monkeypatch` 后 `api_key()`（env=None）同样读 os.environ 并遵循同一优先序
  〔测试裁定 `test_api_key_reads_os_environ_by_default`（:103-112）〕

#### 3.2.2 `check_url(url: str, *, resolve: Optional[Callable[[str], list[str]]] = None) -> None`

端点白名单守卫，**六重门按序执行**（任一不过 → `LLMError`；全过静默返回 `None`）：

1. `url` 必须是非空 `str`；
2. `urlparse(url).scheme == "https"`；
3. 无 userinfo（`parsed.username`/`parsed.password` 均 `None`）；
4. `parsed.hostname == ALLOWED_HOST`（`hostname` 属性已小写化，故 host 比较
   **大小写不敏感**；后缀伪装如 `api.stepfun.com.evil.com` 拒绝）；
5. 显式端口必须为 443（`parsed.port is None` 即无显式端口时放过；端口串非法时
   `parsed.port` 抛的 `ValueError` 被包装为 `LLMError`）；
6. `resolve(host)` 返回的每个 IP 逐个经 `ipaddress.ip_address` 解析，且
   `is_private / is_loopback / is_link_local / is_reserved / is_multicast /
   is_unspecified` 全部为假（**公私混合列表任一坏即全拒**）。

`resolve=None` 时走系统 DNS（`socket.getaddrinfo`，去重保序；**参考路径，无契约
覆盖**〔参考裁定〕）；`resolve` 抛出的任意非 `LLMError` 异常统一包装为
`LLMError("resolve failed ...")`；返回空列表、非 str 元素、不可解析串均 `LLMError`。

实测〔测试裁定 `test_check_url_accepts_public_v4_v6_and_case_insensitive_host`
（:117-120）〕：`check_url("https://api.stepfun.com/x", resolve=lambda h: ["8.8.8.8"])`
→ `None`；`check_url("https://API.STEPFUN.COM/v1/a", resolve=lambda h: ["2606:4700::1111"])`
→ `None`；`check_url("https://api.stepfun.com:443/x", ...)` → `None`。
拒绝样例〔测试裁定 `test_check_url_rejects_scheme_host_port_userinfo_and_garbage`
（:123-138）、`test_check_url_blocks_private_address_families`（:141-155）、
`test_check_url_resolver_failures`（:158-167）〕：`http://`/`ftp://` scheme、
`evil.com`、`api.stepfun.com.evil.com`、`:8443`、`user:pass@` 与仅 username、
`"not a url"`、`""`、`42`、`None`；12 个私网族地址（`10.0.0.5`、`127.0.0.1`、
`169.254.1.9`、`198.51.100.23`、`172.16.0.9`、`fe80::1`、`::1`、`0.0.0.0`、
`224.0.0.1`、`240.0.0.1`、`255.255.255.255`、`fc00::9`）各自单独即拒；
`["8.8.8.8", "10.0.0.5"]` 混合拒；resolver 抛 `OSError`、返回 `[]`、
`["not-an-ip"]`、`[b"8.8.8.8"]`、`["8.8.8.8", ""]` 均拒。

#### 3.2.3 `data_url(image: bytes, image_format: str) -> str`

非空 `bytes` → `"data:{mime};base64,{b64}"`（`base64.b64encode(image).decode("ascii")`）；
`image_format` 必须先为 `str` 且命中 `IMAGE_MIME`。

实测〔测试裁定 `test_data_url_closed_forms_and_guards`（:172-184）〕：
`data_url(b"\x00", "png")` → `"data:image/png;base64,AA=="`；
`data_url(b"abc", "jpeg")` 与 `data_url(b"abc", "jpg")` 同为
`"data:image/jpeg;base64,YWJj"`（别名同 mime）；
`data_url(b"\x89PNG\r\n\x1a\n", "png")` → `"data:image/png;base64,iVBORw0KGgo="`；
`("", "png")`/`(None, "png")`/`(5, "png")` 与 `"bmp"`/`""`/`"PNG"`/`None`/`5`
格式 → `LLMError`。

#### 3.2.4 `vision_content(prompt: str, images: Sequence, image_format: str = "png") -> list[dict]`

返回多段 content：**恰一个 text 段在最前** `{"type": "text", "text": prompt}`，
其后每图一个 `{"type": "image_url", "image_url": {"url": u}}`，**按入参序**。
`prompt` 必须为非空白 str；`images` 必须为非空 `list`/`tuple`；每个元素是 `bytes`
（经 `data_url(img, image_format)` 编码）或以 `"data:image/"` 开头的 str
（**原样透传**，不受 image_format 影响），否则 `LLMError`。

实测〔测试裁定 `test_vision_content_shape_and_guards`（:187-204）〕：
`vision_content("看图", [b"\x01\x02", "data:image/png;base64,AAA"])` →

```python
[{"type": "text", "text": "看图"},
 {"type": "image_url", "image_url": {"url": "data:image/png;base64,AQI="}},
 {"type": "image_url", "image_url": {"url": "data:image/png;base64,AAA"}}]
```

`image_format="jpeg"` 时 bytes 图编码为 `"data:image/jpeg;base64,AQI="`（按次生效）；
`("", [b"x"])`/`("  ", ...)`/`(None, ...)`/`(5, ...)`、`[]`/`()`/`"abc"`/`None`/`5`/
`[""]`/`["http://x/y.png"]`/`["data:text/html,x"]`/`[b""]`/`[5]`/
`["data:image/png;base64,AAA", 42]`、`image_format="bmp"` → `LLMError`。

#### 3.2.5 `multipart_body(fields: Mapping[str, str], file_field: str, filename: str, file_bytes: bytes, *, boundary: str = BOUNDARY) -> tuple[bytes, str]`

确定性 multipart 构造：`fields` 普通字段（**无** Content-Type 头部）+ 恰一个文件字段
（带 `filename` 与 `Content-Type: application/octet-stream`），按
`fields` 迭代序 → 文件字段 → 结尾 delimiter 组装。返回 `(请求体 bytes,
"multipart/form-data; boundary={boundary}")`。`boundary` 与任何字段**键**/值、
`filename`、`file_bytes`（**字节子串**，不限位置）碰撞 → `LLMError`（防结构碰撞）。

实测〔测试裁定 `test_multipart_body_closed_form_and_collision_guards`（:207-240）〕：
`multipart_body({"model": "stepaudio-2.5-asr"}, "file", "answer.wav", b"RIFFMOCKWAV")`
→ 字节闭式（逐字节相等）：

```
--xuexing-mm-boundary-v1\r\n
Content-Disposition: form-data; name="model"\r\n
\r\n
stepaudio-2.5-asr\r\n
--xuexing-mm-boundary-v1\r\n
Content-Disposition: form-data; name="file"; filename="answer.wav"\r\n
Content-Type: application/octet-stream\r\n
\r\n
RIFFMOCKWAV\r\n--xuexing-mm-boundary-v1--\r\n
```

同输入两次调用字节相等（同输入同字节）；`{"m": BOUNDARY}`（字段值碰撞）、
`b"--" + BOUNDARY.encode()`（文件体碰撞）、`BOUNDARY + ".wav"`（filename 碰撞）、
空文件体/空 file_field/空 filename/`boundary=""`、`fields` 非映射、`{5: "x"}`
非 str 键、`"str-not-bytes"` 文件 → `LLMError`。

### 3.3 传输（唯一网络出口）

#### 3.3.1 `Transport`（Protocol）

结构协议（鸭子类型，不 import 其定义模块）：`post(url, *, headers, body,
content_type, timeout) -> tuple[int, bytes]`（HTTP 状态码, 响应体字节）。
MMClient 只要求注入对象有可调用的 `post`（§3.4）。

#### 3.3.2 `MockTransport`

确定性 mock 传输（契约测试零网络）。类属性 `DEFAULT_REPLIES`（冻结应答表，
**不得被实例覆盖污染**）：

| cap | 应答 |
|---|---|
| `"chat"` | `(200, b'{"choices": [{"message": {"content": "\u6a21\u62df\u56de\u7b54"}}]}')`（UTF-8、`ensure_ascii=False`） |
| `"tts"` | `(200, b"ID3MOCKMP3")` |
| `"asr"` | `(200, b'{"text": "\u6a21\u62df\u8f6c\u5199"}')` |

- `MockTransport(replies=None)`：`self.replies` 自 `DEFAULT_REPLIES` 拷贝后按参更新
  （实例覆盖生效且不改类默认——测试断言覆盖后 `DEFAULT_REPLIES["tts"]` 仍为
  `(200, b"ID3MOCKMP3")`）。
- `post(...)` 把每次请求追加进 `self.calls`：字典恰五键
  `{"url", "headers"（dict 拷贝）, "body"（bytes 拷贝）, "content_type", "timeout"}`。
- 按 `_CAP_BY_URL` 查 URL → cap 选应答；**未知 URL → `(404, b'{"error":"mock: unknown url"}')`**。

实测〔测试裁定 `test_mock_transport_defaults_recording_and_unknown_url`
（:245-263）〕：默认 chat 应答即上表；`mt.calls[0]` 恰为上述五键字典；
未知 URL 得 `(404, ...)` 404 体。

#### 3.3.3 `HttpTransport`

生产传输，**仅参考、无契约测试覆盖**（唯一被契约套件接触的点是 env-gated 冒烟用例
`test_smoke_real_stepfun_api`（:530-543），默认 skip）。按参考实现冻结其行为
〔参考裁定〕：`post` 前先跑一次 `check_url`（与 MMClient 内守卫互为双保险，
`__init__(*, resolve=None)` 可注入解析器）；stdlib `urllib.request` 单次 POST；
`HTTPError` → 返回 `(code, body)` **不抛**（先于 `URLError` 捕获，因前者是后者子类）；
`URLError`/`OSError`/`TimeoutError` → `LLMError`。非冒烟场景契约套件不触达。

### 3.4 `MMClient`

```python
class MMClient:
    def __init__(self, transport: Transport, *, model: str = MODEL_CHAT,
                 tts_model: str = MODEL_TTS, asr_model: str = MODEL_ASR,
                 voice: str = TTS_VOICE, timeout: float = DEFAULT_TIMEOUT,
                 env: Optional[Mapping[str, str]] = None,
                 resolve: Optional[Callable[[str], list[str]]] = None) -> None
```

四能力客户端：chat / vision / tts / asr。传输注入，**key 构造时解析（fail-fast）**。

**构造校验按序执行**（任一不过 → `LLMError`；〔参考裁定〕整体次序，组合输入先命中
项契约未仲裁）〔测试裁定 `test_client_construction_guards_fail_fast`（:268-284）
逐类断言〕：

1. `transport` 必须提供可调用的 `post`（鸭子类型，`callable(getattr(...))`）；
2. `model`/`tts_model`/`asr_model`/`voice` 必须为非空白 str；
3. `timeout` 必须为正有限数（`int`/`float`，**bool 拒绝**；`inf`/`nan`/`<= 0`/
   非数字拒绝）；
4. `api_key(env)` 取 key —— 缺失在**构造期**即抛（fail-fast），key 只存内存
   （`self._key`，无公开访问器），绝不进日志/错误消息。

**公开属性**（五个）：`model`、`tts_model`、`asr_model`、`voice`、`timeout`
（`float(timeout)` 化，int 5 → `5.0`）。`_transport`/`_key`/`_resolve` 私有。
默认值即冻结常量（测试断言五元组 == `(MODEL_CHAT, MODEL_TTS, MODEL_ASR,
TTS_VOICE, DEFAULT_TIMEOUT)`）〔测试裁定 `test_client_defaults_and_attributes`
（:287-294）〕。

**内部请求管线** `_post(cap, body, content_type)`〔参考裁定整体存在性，见下〕：
参考实现会在每次请求前调用 `check_url(ENDPOINTS[cap], resolve=self._resolve)`，
与 `HttpTransport` 内部前向 `check_url` 互为双保险。**此调用契约测试未仲裁**——
`ENDPOINTS` 已是冻结常量，重生成实例可自由决定是否在 `_post` 内重复校验
（保留则属纵深防御，省略亦不影响 28 项契约测试全绿）。其后是契约化步骤：
headers 恰两键 `{"Authorization": f"Bearer {self._key}", "Content-Type": content_type}` →
`transport.post(url, headers=..., body=..., content_type=..., timeout=self.timeout)`
→ 非 200 → `LLMError(f"mm http {status}")`。

> 〔参考裁定〕`_post` 内的 check_url 调用不被现有契约测试仲裁：全部客户端用例都经
> 解析桩注入（`tests/contract/test_mm_client_contract.py:52-56`），去掉该调用 28 项
> 仍全绿。本冻结按参考实现钉死（实测：注入必败 resolver 时 `chat("hi")` 抛
> `LLMError: resolve failed...` 且 transport 零调用）。

#### `chat(text: str, *, system: Optional[str] = None) -> str`

`text` 与非 None 的 `system` 必须为非空白 str。messages 装配：`system` 非 None 时
`{"role": "system", "content": system}` 在前，随后恒有 `{"role": "user", "content": text}`；
payload `{"model": self.model, "messages": messages}` 以
`json.dumps(payload, ensure_ascii=False).encode("utf-8")` 出字节（**默认分隔符**，
字节级闭式）。响应经 chat 应答解析（§3.2/§6）返回 content str。

实测〔测试裁定 `test_client_chat_closed_form_request_and_reply`（:299-314）、
`test_client_chat_system_message_and_determinism`（:317-329）〕：
`client.chat("你好")` → `"模拟回答"`，且唯一一次 transport 调用四要素为
`url == ENDPOINTS["chat"]`、`headers == {"Authorization": "Bearer sk-SENTINEL-1",
"Content-Type": "application/json"}`、`body == json.dumps({"model": "step-5-preview",
"messages": [{"role": "user", "content": "你好"}]}, ensure_ascii=False).encode("utf-8")`、
`timeout == 60.0`；带 `system="你是数学老师"` 时 system 段在前；同输入两次调用
请求字节相等、 headers 相等。

#### `vision(prompt: str, images: Sequence, *, image_format: str = "png") -> str`

委托 `vision_content(prompt, images, image_format)` 构造 content，payload
`{"model": self.model, "messages": [{"role": "user", "content": content}]}`，
**与 chat 同一端点（`ENDPOINTS["chat"]`）**、同一 JSON 序列化与应答解析（响应形状错误消息同样为 `'bad chat response'`，与 `chat` 方法一致
〔测试裁定 `test_client_bad_response_bodies`（tests/contract/
test_mm_client_contract.py:464-480）〕）。

实测〔测试裁定 `test_client_vision_payload_and_shared_endpoint`（:345-363）〕：
`client.vision("图里是什么颜色？", [b"\x89PNG\r\n\x1a\n"])` → `"模拟回答"`，
请求 URL 为 chat 端点，`messages[0]["content"]` 为 text 段 + 各图 image_url 段；
`image_format="jpg"` 时 bytes 图编码为 `image/jpeg`，data URL 段原样透传。

#### `tts(text: str, *, voice: Optional[str] = None, response_format: str = TTS_FORMAT) -> bytes`

`text` 非空白 str；`voice` 为 None 时取 `self.voice`；`voice`/`response_format`
必须为非空白 str。payload `{"model": self.tts_model, "input": text, "voice": v,
"response_format": response_format}`，JSON 序列化同 chat。**200 响应体字节原样返回，
不解析**（I11 唯一宽容点：非音频形状的 200 体也照返）。

实测〔测试裁定 `test_client_tts_closed_form_request_and_raw_reply`（:380-394）、
`test_client_tts_returns_200_body_verbatim`（:397-399）〕：
`client.tts("九九乘法表")` → `b"ID3MOCKMP3"`，URL 为 tts 端点，payload 恰
`{"model": MODEL_TTS, "input": "九九乘法表", "voice": TTS_VOICE,
"response_format": TTS_FORMAT}`；`voice="other-voice", response_format="wav"`
按次生效；注入 `(200, b'{"not":"audio"}')` 时 `client.tts("任意")` →
`b'{"not":"audio"}'`。

#### `asr(audio: bytes, *, filename: str = "audio.wav") -> str`

`audio` 必须为非空 `bytes`；`filename` 必须为非空白 str（默认 `"audio.wav"`）。
请求体 = `multipart_body({"model": self.asr_model}, "file", filename, audio)[0]`，
content_type = 其 multipart 返回值；响应必须为 JSON 对象且 `text` 为 str，
否则 `LLMError`。

实测〔测试裁定 `test_client_asr_closed_form_request_and_reply`（:420-432）〕：
`client.asr(b"RIFFMOCKWAV", filename="answer.wav")` → `"模拟转写"`，URL 为 asr 端点，
headers `Content-Type == MULTIPART_CONTENT_TYPE`，body 与
`multipart_body({"model": MODEL_ASR}, "file", "answer.wav", b"RIFFMOCKWAV")[0]`
同字节；`client.asr(b"x")` 用默认 filename，体中出现
`filename="audio.wav"`。

## 4. 不变量（编号列出，全部可被契约测试检验）

- I1 **常量冻结**：§3.1 全部常量/异常取值为冻结条款；`LLMError` 是 `RuntimeError`
  子类（`test_frozen_constants`）。
- I2 **端点自过白名单**：`ENDPOINTS` 每个 URL 都被 `check_url`（注入公网解析桩）
  接受，且均以 `"https://" + ALLOWED_HOST` 开头（`test_endpoints_pass_own_whitelist`）。
- I3 **key 纪律**：`KEY_ENV_VARS` 优先序 + strip + 非 str 跳过；全缺 → `LLMError`
  且消息含变量名、不含任何候选值；`env=None` 默认读 `os.environ`
  （`test_api_key_priority_strip_and_missing`、`test_api_key_reads_os_environ_by_default`）。
- I4 **白名单六重门**：公网 v4/v6、大写 host、显式 `:443` 放过；scheme/host 伪装/
  非 443 端口/userinfo/垃圾/空串/非 str、12 个私网族地址、公私混合、resolver 失败/
  空/非 str/非法地址输出，一律 `LLMError`（四个 `test_check_url_*`）。
- I5 **构造纯函数闭式与防碰撞**：`data_url`/`vision_content`/`multipart_body`
  字节级闭式（§3.2 例）；同输入同字节；boundary 与字段值/filename/file_bytes
  碰撞全拒（三个构造测试）。
- I6 **MockTransport 确定性**：默认应答表冻结；`calls` 恰五键记录；未知 URL
  → `(404, ...)`；实例 `replies` 覆盖不污染 `DEFAULT_REPLIES`
  （`test_mock_transport_defaults_recording_and_unknown_url`）。
- I7 **构造 fail-fast**：transport 无可调用 `post`、key 缺失、model/tts_model/
  asr_model/voice 空白、timeout 非正有限数（含 bool/字符串/None）均构造期
  `LLMError`；默认属性五元组与 `timeout` float 化
  （`test_client_construction_guards_fail_fast`、`test_client_defaults_and_attributes`）。
- I8 **chat 闭式请求与应答**：四要素（URL/headers 恰两键/body 字节闭式/timeout
  透传）、system 段装配次序、同输入同字节同 headers、解析返回 content str
  （两个 chat 测试）。
- I9 **守卫失败零出网**：chat/vision/tts/asr 的一切入参守卫失败时
  `transport.calls == []`（不发出任何请求）（四个 `test_client_*_guards_no_transport_call`）。
- I10 **vision 共享 chat 端点**：同一 URL、同一 `MODEL_CHAT`、多段 content 形状、
  `image_format` 按次生效、data URL 透传
  （`test_client_vision_payload_and_shared_endpoint`）。
- I11 **tts 原样返回**：200 响应体字节原样返回、绝不解析（唯一宽容点）
  （`test_client_tts_returns_200_body_verbatim`）。
- I12 **asr 闭式请求与应答**：请求体与 `multipart_body` 同字节、默认 filename、
  `text` 必须为 str（`test_client_asr_closed_form_request_and_reply`）。
- I13 **错误归族与 key 不回显**：非 200 → `LLMError` 且消息含状态码（实测
  `"mm http 500"`）；坏 chat 响应体（非 JSON/非对象/缺 choices/message/content/
  content 非 str）→ 消息含 `"bad chat response"`；坏 asr 响应体 → `"bad asr response"`；
  哨兵 key 不出现在任何错误消息；请求确实发出过（错误来自响应侧）
  （`test_client_http_and_shape_errors_never_leak_key`、`test_client_bad_response_bodies`）。
- I14 **key 优先序贯穿 Authorization**：`env` 优先序 + strip 体现在 Bearer 头
  （`"Bearer sk-A"`，回落 `"Bearer sk-B"`）
  （`test_client_env_priority_in_authorization_header`）。
- I15 **纯函数性**：四能力调用后全部入参深对比不变（text/prompt/images/audio/
  filename）；请求构造无隐藏随机/时钟（`test_inputs_not_mutated_across_all_four_capabilities`）。

## 5. 确定性与随机性

- **请求构造全部纯函数**：`_json_bytes` 固定 `json.dumps(payload, ensure_ascii=False)`
  （默认分隔符 `", "`/`": "`，UTF-8 编码）；multipart 用固定边界常量 `BOUNDARY`
  （无隐藏随机）；同 `(payload)`/同 multipart 入参 → 同字节（I5/I8）。
- **不读时钟**：`timeout` 是显式构造参数（默认常量 `DEFAULT_TIMEOUT = 60.0`），
  模块无任何时钟读取；无时间戳字段（无豁免）。
- **无随机源**：禁止 `random` 及任何熵源；`MockTransport`/`DEFAULT_REPLIES` 无随机。
- **环境读取唯一入口**：`api_key(env=None)` 默认读 `os.environ`（I3）；`env` 显式
  注入时完全不碰环境。其余 API 不读环境。
- **网络**：契约套件零网络（传输全 mock、DNS 全桩）。真网络只发生在 `HttpTransport`
  路径与冒烟用例（env-gated：`XX_MM_SMOKE=1` 且环境含 key 才真调，默认 skip）；
  `_system_resolve`（`resolve=None` 默认）为参考路径，无契约覆盖。
- **字节/浮点可复现性**：base64 与 UTF-8 编码唯一；`float(timeout)` 为 IEEE 唯一
  结果；私网判定用 CPython `ipaddress` 库语义（六属性）。§3 中每个字节闭式都是
  逐位比对点。

## 6. 错误行为

异常类型**一律 `LLMError`**（`RuntimeError` 子类，模块唯一家族，I1）；触发时机如下
（消息文案除明文引用外不作承诺；唯一跨全部条款的硬约束：消息不得包含 api key 值）：

| 非法输入 | 行为（异常类型与时机） |
|---|---|
| `api_key`：两变量全缺或 strip 后空白 | 调用即抛 `LLMError`（含变量名、不含值） |
| `api_key`：候选值非 str（`None` 等） | 容忍，视为缺失跳过〔参考裁定，测试覆盖 `None`〕 |
| `check_url`：非 str/空串 | 调用即抛 `LLMError` |
| `check_url`：scheme ≠ `https` | 调用即抛 `LLMError` |
| `check_url`：含 userinfo | 调用即抛 `LLMError` |
| `check_url`：host ≠ `api.stepfun.com`（含后缀伪装） | 调用即抛 `LLMError` |
| `check_url`：显式端口非 443 / 端口串非法 | 调用即抛 `LLMError`（端口串经 `ValueError` 包装） |
| `check_url`：resolver 抛异常 / 返回空 / 非 str / 不可解析地址 | 调用即抛 `LLMError` |
| `check_url`：解析 IP 属私网/环回/链路本地/保留/组播/未指定任一（混合列表任一坏即全拒） | 调用即抛 `LLMError` |
| `data_url`：image 非 bytes 或空 | 调用即抛 `LLMError` |
| `data_url`：image_format 非 str 或不在 `IMAGE_MIME`（大小写敏感） | 调用即抛 `LLMError` |
| `vision_content`：prompt 非空白 str；images 非 list/tuple 或空；元素非 bytes 且非 `"data:image/"` 前缀 str；image_format 非法 | 调用即抛 `LLMError` |
| `multipart_body`：file_field/filename/boundary 空白；file_bytes 非 bytes/空；fields 非 Mapping 或键值非 str；boundary 与字段键/值、filename、file_bytes（字节子串）碰撞 | 调用即抛 `LLMError` |
| `MMClient.__init__`：transport 无可调用 post；model/tts_model/asr_model/voice 非空白 str；timeout 非正有限数/bool/非数字；key 缺失 | **构造期**抛 `LLMError`（fail-fast） |
| `chat`/`vision`/`tts`/`asr`：text/prompt/system/voice/response_format/audio/filename/images/image_format 非法 | **传输前**抛 `LLMError`（零出网，I9） |
| HTTP 响应非 200（chat/tts/asr 任一） | 传输后抛 `LLMError`（消息含状态码，实测 `"mm http 500"`） |
| chat 响应体：非 UTF-8 JSON / 非 JSON 对象 / 缺 `choices`/`message`/`content` / content 非 str | 抛 `LLMError`（消息含 `"bad chat response"`） |
| asr 响应体：非 JSON / 非对象 / `text` 缺失或非 str | 抛 `LLMError`（消息含 `"bad asr response"`） |
| tts 200 响应体：任意字节 | **容忍**，原样返回（I11 唯一宽容点，不解析不报错） |
| `HttpTransport`（参考路径，无契约覆盖）：`URLError`/`OSError`/`TimeoutError` | 抛 `LLMError`；`HTTPError` → 返回 `(code, body)` 不抛〔参考裁定〕 |

## 7. 非目标

- **不做流式/增量响应**：单次 POST 单响应，无 SSE/分块解析。
- **不做重试、退避、限流、缓存、连接池**：一次失败即归族 `LLMError` 上抛。
- **不做多 key 轮换/配额管理**：key 只按 `KEY_ENV_VARS` 优先序取第一个，不轮换。
- **不做请求签名/证书固定/TLS 终止**：安全模型 = 端点白名单六重门 + 私网 IP 阻断
  + key 不进消息；不加密、不验签。
- **不做响应语义深解析**：chat 只取 `choices[0].message.content`；tts 不校验音频
  格式（原样字节）；asr 只取 `text`；不解析 usage/tool_calls/时间戳等附加字段。
- **不做端点/模型动态发现**：端点、模型、voice、format 全是冻结常量，不枚举、不探测。
- **不做日志与遥测**：模块无 logging 调用；key 绝不进日志/错误消息（安全条款）。
- **不管生产传输细节**：`HttpTransport` 仅参考、不在契约覆盖内；重生成实例只需
  满足 Transport 协议语义并提供 `MockTransport` 契约行为。
- **不扩展第五能力**：vision 复用 chat 端点，不引入新端点/新协议；四能力外的
  多模态调用（如图生图、视频）不在本模块。
- **不引入随机与时钟**（§5）；不做绝对日历/时区处理（模块无时间戳字段）。
- `vision_content` 的 `image_format` 校验仅在遇到 `bytes` 元素时通过
  `data_url(img, image_format)` 间接触发；**纯 `data:image/...` 前缀 str 入参**
  （如 `["data:image/png;base64,AAA"]`）时该参数不被校验、实现可自由决定是否
  触发 `LLMError`（契约测试未覆盖，参考实现按惰性校验实现）。
