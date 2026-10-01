"""xuexing.mm_client —— 盲重写实例（regen/wave3）。

唯一权威契约：specs/frozen/mm_client.spec.md（冻结基线 2026-10-02）。

纯标准库、零 xuexing 依赖；chat / vision / tts / asr 四能力收敛到单一可注入
Transport 出口。行为契约：端点白名单六重门（https + 白名单 host + 无 userinfo
+ 显式端口必须 443 + 解析 IP 逐个阻断私网族）；key 纪律（只从环境变量按优先序
读取、strip 后只进内存、任何错误消息绝不回显 key）；单一异常家族 LLMError；
请求构造纯函数化（同输入同字节；multipart 固定边界；无随机、不读时钟）。
"""

from __future__ import annotations

import base64
import ipaddress
import json
import math
import os
import socket
import urllib.error
import urllib.parse
import urllib.request
from typing import Callable, Mapping, Optional, Protocol, Sequence

__all__ = [
    "BASE_URL",
    "ALLOWED_HOST",
    "ENDPOINTS",
    "MODEL_CHAT",
    "MODEL_TTS",
    "MODEL_ASR",
    "TTS_VOICE",
    "TTS_FORMAT",
    "KEY_ENV_VARS",
    "DEFAULT_TIMEOUT",
    "BOUNDARY",
    "JSON_CONTENT_TYPE",
    "MULTIPART_CONTENT_TYPE",
    "IMAGE_MIME",
    "LLMError",
    "api_key",
    "check_url",
    "data_url",
    "vision_content",
    "multipart_body",
    "Transport",
    "MockTransport",
    "HttpTransport",
    "MMClient",
]

# ---------------------------------------------------------------------------
# 冻结常量（spec §3.1）
# ---------------------------------------------------------------------------

BASE_URL = "https://api.stepfun.com"
ALLOWED_HOST = "api.stepfun.com"
ENDPOINTS = {
    "chat": "https://api.stepfun.com/step_plan/v1/chat/completions",
    "tts": "https://api.stepfun.com/step_plan/v1/audio/speech",
    "asr": "https://api.stepfun.com/v1/audio/transcriptions",
}
MODEL_CHAT = "step-5-preview"
MODEL_TTS = "stepaudio-2.5-tts"
MODEL_ASR = "stepaudio-2.5-asr"
TTS_VOICE = "linjiajiejie"
TTS_FORMAT = "mp3"
KEY_ENV_VARS = ("XX_LLM_API_KEY", "STEPFUN_API_KEY")
DEFAULT_TIMEOUT = 60.0
BOUNDARY = "xuexing-mm-boundary-v1"
JSON_CONTENT_TYPE = "application/json"
MULTIPART_CONTENT_TYPE = "multipart/form-data; boundary=" + BOUNDARY
IMAGE_MIME = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
    "gif": "image/gif",
}

# ENDPOINTS 的 URL → 能力反向映射（MockTransport 按请求 URL 查表选应答）。
_CAP_BY_URL = {url: cap for cap, url in ENDPOINTS.items()}


class LLMError(RuntimeError):
    """本模块唯一异常家族；任何错误消息不得包含 api key 值。"""


# ---------------------------------------------------------------------------
# 内部纯函数助手
# ---------------------------------------------------------------------------


def _json_bytes(payload: Mapping) -> bytes:
    """确定性 JSON 字节：ensure_ascii=False + 默认分隔符 + UTF-8（spec §5）。"""
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def _require_non_blank_str(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LLMError(f"{name} must be a non-blank str")
    return value


def _system_resolve(host: str) -> list:
    """系统 DNS 解析（resolve=None 的默认参考路径，无契约覆盖〔参考裁定〕）。

    getaddrinfo 全部结果去重保序；失败归族 LLMError("resolve failed ...")。
    """
    try:
        infos = socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
    except OSError as exc:
        raise LLMError(f"resolve failed: {exc}") from exc
    seen: list = []
    for info in infos:
        addr = info[4][0]
        if addr not in seen:
            seen.append(addr)
    return seen


def _parse_chat_response(raw: object) -> str:
    """chat 应答解析：只取 choices[0].message.content（str），否则归族报错。"""
    if not isinstance(raw, (bytes, bytearray)):
        raise LLMError("bad chat response: body is not bytes")
    try:
        data = json.loads(bytes(raw).decode("utf-8"))
    except ValueError:
        # UnicodeDecodeError 与 JSONDecodeError 均为 ValueError 子类
        raise LLMError("bad chat response: body is not valid utf-8 json")
    if not isinstance(data, dict):
        raise LLMError("bad chat response: expected a json object")
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise LLMError("bad chat response: missing choices")
    first = choices[0]
    if not isinstance(first, dict):
        raise LLMError("bad chat response: choices[0] is not an object")
    message = first.get("message")
    if not isinstance(message, dict):
        raise LLMError("bad chat response: missing message")
    content = message.get("content")
    if not isinstance(content, str):
        raise LLMError("bad chat response: missing content")
    return content


def _parse_asr_response(raw: object) -> str:
    """asr 应答解析：JSON 对象且 text 为 str，否则归族报错。"""
    if not isinstance(raw, (bytes, bytearray)):
        raise LLMError("bad asr response: body is not bytes")
    try:
        data = json.loads(bytes(raw).decode("utf-8"))
    except ValueError:
        raise LLMError("bad asr response: body is not valid utf-8 json")
    if not isinstance(data, dict):
        raise LLMError("bad asr response: expected a json object")
    text = data.get("text")
    if not isinstance(text, str):
        raise LLMError("bad asr response: missing text")
    return text


# ---------------------------------------------------------------------------
# 纯函数公开 API（spec §3.2）
# ---------------------------------------------------------------------------


def api_key(env: Optional[Mapping[str, str]] = None) -> str:
    """按 KEY_ENV_VARS 优先序取第一个 strip 后非空的 str 值，返回 strip 后的值。

    env=None 读 os.environ；候选值非 str 视为缺失跳过；全缺抛 LLMError
    （消息含两个变量名与 "not set"，绝不回显任何候选值）。
    """
    source = os.environ if env is None else env
    for name in KEY_ENV_VARS:
        try:
            value = source[name]
        except (KeyError, TypeError):
            continue
        if not isinstance(value, str):
            continue
        stripped = value.strip()
        if stripped:
            return stripped
    raise LLMError(
        "api key not set: expected one of KEY_ENV_VARS "
        "(XX_LLM_API_KEY, STEPFUN_API_KEY) in environment"
    )


def check_url(url: str, *, resolve: Optional[Callable[[str], list[str]]] = None) -> None:
    """端点白名单守卫：六重门按序执行，任一不过抛 LLMError，全过静默返回 None。"""
    # 门 1：非空 str
    if not isinstance(url, str) or not url:
        raise LLMError("check_url: url must be a non-empty str")
    parsed = urllib.parse.urlparse(url)
    # 门 2：scheme 必须 https
    if parsed.scheme != "https":
        raise LLMError(f"check_url: scheme must be https, got {parsed.scheme!r}")
    # 门 3：无 userinfo（空串 userinfo 也非 None，同样拒绝）
    if parsed.username is not None or parsed.password is not None:
        raise LLMError("check_url: userinfo is not allowed")
    # 门 4：host 白名单（hostname 属性已小写化 → 大小写不敏感；后缀伪装拒绝）
    host = parsed.hostname
    if host != ALLOWED_HOST:
        raise LLMError(f"check_url: host not allowed: {host!r}")
    # 门 5：显式端口必须 443；端口串非法（parsed.port 抛 ValueError）包装为 LLMError
    try:
        port = parsed.port
    except ValueError as exc:
        raise LLMError(f"check_url: invalid port in url: {exc}") from exc
    if port is not None and port != 443:
        raise LLMError(f"check_url: explicit port must be 443, got {port}")
    # 门 6：解析 IP 逐个经六属性阻断私网/环回/链路本地/保留/组播/未指定
    if resolve is None:
        addresses = _system_resolve(host)
    else:
        try:
            addresses = resolve(host)
        except LLMError:
            raise
        except Exception as exc:
            raise LLMError(f"resolve failed: {exc}") from exc
    if isinstance(addresses, (str, bytes)):
        raise LLMError("check_url: resolver returned a non-address value")
    try:
        address_list = list(addresses)
    except TypeError as exc:
        raise LLMError("check_url: resolver returned a non-iterable") from exc
    if not address_list:
        raise LLMError("check_url: resolver returned no addresses")
    for item in address_list:
        if not isinstance(item, str):
            raise LLMError("check_url: resolver returned a non-str address")
        try:
            addr = ipaddress.ip_address(item)
        except ValueError as exc:
            raise LLMError(f"check_url: unparseable address {item!r}") from exc
        if (
            addr.is_private
            or addr.is_loopback
            or addr.is_link_local
            or addr.is_reserved
            or addr.is_multicast
            or addr.is_unspecified
        ):
            raise LLMError(f"check_url: blocked non-public address {item}")
    return None


def data_url(image: bytes, image_format: str) -> str:
    """非空 bytes → "data:{mime};base64,{b64}"；image_format 命中 IMAGE_MIME。"""
    if not isinstance(image, (bytes, bytearray)) or not image:
        raise LLMError("data_url: image must be non-empty bytes")
    if not isinstance(image_format, str) or image_format not in IMAGE_MIME:
        raise LLMError(
            f"data_url: image_format must be one of {sorted(IMAGE_MIME)} (case sensitive)"
        )
    mime = IMAGE_MIME[image_format]
    encoded = base64.b64encode(bytes(image)).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def vision_content(
    prompt: str, images: Sequence, image_format: str = "png"
) -> list[dict]:
    """多段 content：恰一个 text 段在最前，其后每图一个 image_url 段，按入参序。

    每个元素是 bytes（经 data_url(img, image_format) 编码，惰性校验格式）或以
    "data:image/" 开头的 str（原样透传，不受 image_format 影响）。
    """
    _require_non_blank_str(prompt, "vision_content: prompt")
    if not isinstance(images, (list, tuple)) or not images:
        raise LLMError("vision_content: images must be a non-empty list or tuple")
    content: list[dict] = [{"type": "text", "text": prompt}]
    for image in images:
        if isinstance(image, (bytes, bytearray)):
            url = data_url(bytes(image), image_format)
        elif isinstance(image, str) and image.startswith("data:image/"):
            url = image
        else:
            raise LLMError(
                "vision_content: each image must be non-empty bytes "
                "or a str starting with 'data:image/'"
            )
        content.append({"type": "image_url", "image_url": {"url": url}})
    return content


def multipart_body(
    fields: Mapping[str, str],
    file_field: str,
    filename: str,
    file_bytes: bytes,
    *,
    boundary: str = BOUNDARY,
) -> tuple[bytes, str]:
    """确定性 multipart 构造：普通字段（无 Content-Type）+ 恰一个文件字段
    （带 filename 与 Content-Type: application/octet-stream），按 fields 迭代序
    → 文件字段 → 结尾 delimiter。返回 (请求体 bytes, "multipart/form-data;
    boundary={boundary}")。boundary 与任何字段键/值、filename、file_bytes
    （字节子串）碰撞 → LLMError（防结构碰撞）。
    """
    if not isinstance(file_field, str) or not file_field.strip():
        raise LLMError("multipart_body: file_field must be a non-blank str")
    if not isinstance(filename, str) or not filename.strip():
        raise LLMError("multipart_body: filename must be a non-blank str")
    if not isinstance(boundary, str) or not boundary.strip():
        raise LLMError("multipart_body: boundary must be a non-blank str")
    if not isinstance(file_bytes, (bytes, bytearray)) or not file_bytes:
        raise LLMError("multipart_body: file_bytes must be non-empty bytes")
    if not hasattr(fields, "items"):
        raise LLMError("multipart_body: fields must be a mapping of str to str")
    try:
        items = list(fields.items())
    except Exception as exc:  # 非 Mapping 的 items() 调用失败
        raise LLMError("multipart_body: fields must be a mapping of str to str") from exc
    for key, value in items:
        if not isinstance(key, str) or not isinstance(value, str):
            raise LLMError("multipart_body: fields keys and values must be str")
    file_payload = bytes(file_bytes)
    boundary_bytes = boundary.encode("utf-8")
    # 防结构碰撞：boundary 不得出现在任何字段键/值、filename、文件体（字节子串）
    for key, value in items:
        if boundary in key or boundary in value:
            raise LLMError("multipart_body: boundary collides with a field key or value")
    if boundary in filename:
        raise LLMError("multipart_body: boundary collides with filename")
    if boundary_bytes in file_payload:
        raise LLMError("multipart_body: boundary collides with file bytes")
    delimiter = b"--" + boundary_bytes
    out = bytearray()
    for key, value in items:
        out += delimiter + b"\r\n"
        out += (
            'Content-Disposition: form-data; name="' + key + '"\r\n\r\n' + value + "\r\n"
        ).encode("utf-8")
    out += delimiter + b"\r\n"
    out += (
        'Content-Disposition: form-data; name="' + file_field
        + '"; filename="' + filename + '"\r\n'
    ).encode("utf-8")
    out += b"Content-Type: application/octet-stream\r\n\r\n"
    out += file_payload
    out += b"\r\n" + delimiter + b"--\r\n"
    return bytes(out), "multipart/form-data; boundary=" + boundary


# ---------------------------------------------------------------------------
# 传输（唯一网络出口，spec §3.3）
# ---------------------------------------------------------------------------


class Transport(Protocol):
    """结构协议：post(url, *, headers, body, content_type, timeout) ->
    (HTTP 状态码, 响应体字节)。"""

    def post(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        body: bytes,
        content_type: str,
        timeout: float,
    ) -> tuple[int, bytes]:
        ...


class MockTransport:
    """确定性 mock 传输（契约套件零网络）。

    类属性 DEFAULT_REPLIES 为冻结应答表；实例 replies 自其拷贝后按参更新，
    实例覆盖不污染类默认。每次 post 追加五键记录进 self.calls；
    未知 URL → (404, b'{"error":"mock: unknown url"}')。
    """

    DEFAULT_REPLIES = {
        "chat": (200, '{"choices": [{"message": {"content": "模拟回答"}}]}'.encode("utf-8")),
        "tts": (200, b"ID3MOCKMP3"),
        "asr": (200, '{"text": "模拟转写"}'.encode("utf-8")),
    }

    def __init__(self, replies: Optional[Mapping[str, tuple[int, bytes]]] = None) -> None:
        self.replies = dict(self.DEFAULT_REPLIES)
        if replies:
            self.replies.update(replies)
        self.calls: list[dict] = []

    def post(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        body: bytes,
        content_type: str,
        timeout: float,
    ) -> tuple[int, bytes]:
        self.calls.append(
            {
                "url": url,
                "headers": dict(headers),
                "body": bytes(body),
                "content_type": content_type,
                "timeout": timeout,
            }
        )
        cap = _CAP_BY_URL.get(url)
        if cap is None:
            return (404, b'{"error":"mock: unknown url"}')
        return self.replies.get(cap, (404, b'{"error":"mock: unknown url"}'))


class HttpTransport:
    """生产传输（仅参考、无契约覆盖〔参考裁定〕）。

    post 前先跑一次 check_url（与 MMClient 内守卫互为双保险）；stdlib urllib
    单次 POST；HTTPError → 返回 (code, body) 不抛（先于 URLError 捕获，因前者
    是后者子类）；URLError/OSError/TimeoutError → LLMError。
    """

    def __init__(self, *, resolve: Optional[Callable[[str], list[str]]] = None) -> None:
        self._resolve = resolve

    def post(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        body: bytes,
        content_type: str,
        timeout: float,
    ) -> tuple[int, bytes]:
        check_url(url, resolve=self._resolve)
        request = urllib.request.Request(
            url, data=bytes(body), headers=dict(headers), method="POST"
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return int(response.status), response.read()
        except urllib.error.HTTPError as exc:  # URLError 子类，必须先捕获
            try:
                error_body = exc.read()
            except Exception:
                error_body = b""
            return int(exc.code), error_body
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            raise LLMError(f"mm http transport failed: {exc}") from exc


# ---------------------------------------------------------------------------
# MMClient（spec §3.4）
# ---------------------------------------------------------------------------


class MMClient:
    """四能力客户端：chat / vision / tts / asr。传输注入，key 构造时解析（fail-fast）。"""

    def __init__(
        self,
        transport: Transport,
        *,
        model: str = MODEL_CHAT,
        tts_model: str = MODEL_TTS,
        asr_model: str = MODEL_ASR,
        voice: str = TTS_VOICE,
        timeout: float = DEFAULT_TIMEOUT,
        env: Optional[Mapping[str, str]] = None,
        resolve: Optional[Callable[[str], list[str]]] = None,
    ) -> None:
        # 1. transport 必须提供可调用的 post（鸭子类型）
        if not callable(getattr(transport, "post", None)):
            raise LLMError("MMClient: transport must provide a callable post")
        # 2. model/tts_model/asr_model/voice 必须为非空白 str
        self.model = _require_non_blank_str(model, "MMClient: model")
        self.tts_model = _require_non_blank_str(tts_model, "MMClient: tts_model")
        self.asr_model = _require_non_blank_str(asr_model, "MMClient: asr_model")
        self.voice = _require_non_blank_str(voice, "MMClient: voice")
        # 3. timeout 必须为正有限数（int/float，bool 拒绝）
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
            raise LLMError("MMClient: timeout must be a positive finite number")
        timeout_f = float(timeout)
        if not math.isfinite(timeout_f) or timeout_f <= 0:
            raise LLMError("MMClient: timeout must be a positive finite number")
        self.timeout = timeout_f
        # 4. key 构造期解析（fail-fast），只存内存，绝不进日志/错误消息
        self._key = api_key(env)
        self._transport = transport
        self._resolve = resolve

    def _post(self, cap: str, body: bytes, content_type: str) -> bytes:
        """内部请求管线：白名单自校验（纵深防御〔参考裁定钉死〕）→ 恰两键
        headers → transport.post → 非 200 抛 LLMError(f"mm http {status}")。"""
        url = ENDPOINTS[cap]
        check_url(url, resolve=self._resolve)
        headers = {
            "Authorization": f"Bearer {self._key}",
            "Content-Type": content_type,
        }
        status, response = self._transport.post(
            url,
            headers=headers,
            body=body,
            content_type=content_type,
            timeout=self.timeout,
        )
        if status != 200:
            raise LLMError(f"mm http {status}")
        return response

    def chat(self, text: str, *, system: Optional[str] = None) -> str:
        """文本对话：system 非 None 时在前，恒有 user 段；JSON 闭式请求；
        应答取 choices[0].message.content。"""
        _require_non_blank_str(text, "chat: text")
        if system is not None:
            _require_non_blank_str(system, "chat: system")
        messages: list[dict] = []
        if system is not None:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": text})
        payload = {"model": self.model, "messages": messages}
        raw = self._post("chat", _json_bytes(payload), JSON_CONTENT_TYPE)
        return _parse_chat_response(raw)

    def vision(
        self, prompt: str, images: Sequence, *, image_format: str = "png"
    ) -> str:
        """图像理解：与 chat 同一端点、同一序列化与应答解析；content 由
        vision_content 构造。"""
        content = vision_content(prompt, images, image_format)
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": content}],
        }
        raw = self._post("chat", _json_bytes(payload), JSON_CONTENT_TYPE)
        return _parse_chat_response(raw)

    def tts(
        self,
        text: str,
        *,
        voice: Optional[str] = None,
        response_format: str = TTS_FORMAT,
    ) -> bytes:
        """语音合成：voice 为 None 取 self.voice；200 响应体字节原样返回不解析
        （I11 唯一宽容点）。"""
        _require_non_blank_str(text, "tts: text")
        resolved_voice = (
            self.voice if voice is None else _require_non_blank_str(voice, "tts: voice")
        )
        _require_non_blank_str(response_format, "tts: response_format")
        payload = {
            "model": self.tts_model,
            "input": text,
            "voice": resolved_voice,
            "response_format": response_format,
        }
        return self._post("tts", _json_bytes(payload), JSON_CONTENT_TYPE)

    def asr(self, audio: bytes, *, filename: str = "audio.wav") -> str:
        """语音转写：multipart 闭式请求体；应答必须为 JSON 对象且 text 为 str。"""
        if not isinstance(audio, (bytes, bytearray)) or not audio:
            raise LLMError("asr: audio must be non-empty bytes")
        _require_non_blank_str(filename, "asr: filename")
        body, content_type = multipart_body(
            {"model": self.asr_model}, "file", filename, bytes(audio)
        )
        raw = self._post("asr", body, content_type)
        return _parse_asr_response(raw)
