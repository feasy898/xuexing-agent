"""多模态客户端：chat / vision / tts / asr 四能力收敛到单一可注入传输出口。

行为契约（冻结）：见 ``specs/frozen/mm_client.spec.md``。

要点：

* 端点白名单六重门（https + api.stepfun.com + 无 userinfo + 显式端口必须 443 +
  解析 IP 逐个阻断私网/环回/链路本地/保留/组播/未指定）；
* key 纪律（只从环境变量按优先序读取、strip 后只进内存、错误消息绝不回显 key）；
* 单一错误家族 ``LLMError``（HTTP 失败、响应形状错、参数非法、白名单违规、key 缺失）；
* 请求构造纯函数化（同输入同字节；multipart 用固定边界常量 ``BOUNDARY``，无隐藏随机）。

本模块不依赖任何 xuexing 子模块，纯标准库；唯一网络出口是 ``HttpTransport.post``。
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

# --------------------------------------------------------------------------- #
# 冻结常量
# --------------------------------------------------------------------------- #

BASE_URL = "https://api.stepfun.com"
ALLOWED_HOST = "api.stepfun.com"

# 注意：asr 不在 step_plan 路径下；vision 与 chat 共用 chat 端点。
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

# 优先序，从左到右；只取第一个 strip 后非空的 str 值。
KEY_ENV_VARS = ("XX_LLM_API_KEY", "STEPFUN_API_KEY")

DEFAULT_TIMEOUT = 60.0

# 固定边界常量 —— multipart 无隐藏随机的前提。
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


class LLMError(RuntimeError):
    """本模块唯一异常家族。

    key 缺失、白名单违规、参数非法、HTTP 失败、响应形状错全部归族。
    安全条款：任何错误消息不得包含 api key 值。
    """


# URL → 能力反向映射（私有）：MockTransport 按请求 URL 查表选应答。
_CAP_BY_URL = {url: cap for cap, url in ENDPOINTS.items()}

_BAD_IP_ATTRS = (
    "is_private",
    "is_loopback",
    "is_link_local",
    "is_reserved",
    "is_multicast",
    "is_unspecified",
)


# --------------------------------------------------------------------------- #
# 纯函数：key 纪律、白名单守卫、请求构造
# --------------------------------------------------------------------------- #


def api_key(env: Optional[Mapping[str, str]] = None) -> str:
    """按 ``KEY_ENV_VARS`` 优先序取第一个 strip 后非空的 str 值。

    ``env=None`` 读 ``os.environ``；候选值非 str 视为缺失跳过；全缺 → ``LLMError``
    （消息含变量名，不含任何候选值）。
    """
    source = os.environ if env is None else env
    for name in KEY_ENV_VARS:
        try:
            value = source.get(name)
        except AttributeError as exc:  # 非映射注入
            raise LLMError("mm: env must be a mapping of names to values") from exc
        if not isinstance(value, str):
            continue
        value = value.strip()
        if value:
            return value
    raise LLMError(
        "mm: api key not set: none of " + ", ".join(KEY_ENV_VARS) + " is available"
    )


def _system_resolve(host: str) -> list[str]:
    """系统 DNS 解析（去重保序）—— ``resolve=None`` 时的默认解析器。"""
    infos = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    out: list[str] = []
    for info in infos:
        ip = info[4][0]
        if ip not in out:
            out.append(ip)
    return out


def check_url(url: str, *, resolve: Optional[Callable[[str], list[str]]] = None) -> None:
    """端点白名单守卫，六重门按序执行；任一不过 → ``LLMError``，全过静默返回 ``None``。"""
    # 门 1：非空 str
    if not isinstance(url, str) or not url:
        raise LLMError("mm: url must be a non-empty str")
    # 门 2：https
    try:
        parsed = urllib.parse.urlparse(url)
    except ValueError as exc:
        raise LLMError("mm: unparsable url") from exc
    if parsed.scheme != "https":
        raise LLMError("mm: url scheme must be https")
    # 门 3：无 userinfo
    if parsed.username is not None or parsed.password is not None:
        raise LLMError("mm: url must not carry userinfo")
    # 门 4：host 精确等于白名单（hostname 属性已小写化 → 大小写不敏感）
    if parsed.hostname != ALLOWED_HOST:
        raise LLMError("mm: url host is not " + ALLOWED_HOST)
    # 门 5：显式端口必须 443（端口串非法时 ValueError 被包装）
    try:
        port = parsed.port
    except ValueError as exc:
        raise LLMError("mm: url port is invalid") from exc
    if port is not None and port != 443:
        raise LLMError("mm: url port must be 443 when given")
    # 门 6：解析 IP 逐个过私网/环回/链路本地/保留/组播/未指定六属性（混合任一坏即全拒）
    resolver = _system_resolve if resolve is None else resolve
    try:
        ips = resolver(parsed.hostname or ALLOWED_HOST)
    except LLMError:
        raise
    except Exception as exc:
        raise LLMError("mm: resolve failed for " + ALLOWED_HOST) from exc
    if not isinstance(ips, (list, tuple)) or not ips:
        raise LLMError("mm: resolve returned no address for " + ALLOWED_HOST)
    for item in ips:
        if not isinstance(item, str):
            raise LLMError("mm: resolve returned a non-str address")
        try:
            ip = ipaddress.ip_address(item)
        except ValueError as exc:
            raise LLMError("mm: resolve returned an unparsable address") from exc
        for attr in _BAD_IP_ATTRS:
            if getattr(ip, attr):
                raise LLMError("mm: resolve returned a blocked address for " + ALLOWED_HOST)
    return None


def data_url(image: bytes, image_format: str) -> str:
    """bytes → ``data:{mime};base64,{b64}``；非空 bytes 与命中 ``IMAGE_MIME`` 的格式。"""
    if not isinstance(image, bytes) or not image:
        raise LLMError("mm: image must be non-empty bytes")
    if not isinstance(image_format, str) or image_format not in IMAGE_MIME:
        raise LLMError("mm: image_format must be one of " + ", ".join(sorted(IMAGE_MIME)))
    encoded = base64.b64encode(image).decode("ascii")
    return "data:" + IMAGE_MIME[image_format] + ";base64," + encoded


def vision_content(prompt: str, images: Sequence, image_format: str = "png") -> list[dict]:
    """多段 content：恰一个 text 段在最前，其后每图一个 image_url 段（按入参序）。

    元素为 bytes 时经 ``data_url`` 编码；以 ``"data:image/"`` 开头的 str 原样透传
    （不受 image_format 影响，格式校验惰性发生）。
    """
    if not isinstance(prompt, str) or not prompt.strip():
        raise LLMError("mm: prompt must be a non-blank str")
    if not isinstance(images, (list, tuple)) or not images:
        raise LLMError("mm: images must be a non-empty list or tuple")
    content: list[dict] = [{"type": "text", "text": prompt}]
    for item in images:
        if isinstance(item, bytes):
            url = data_url(item, image_format)
        elif isinstance(item, str) and item.startswith("data:image/"):
            url = item
        else:
            raise LLMError("mm: each image must be bytes or a data:image/ str")
        content.append({"type": "image_url", "image_url": {"url": url}})
    return content


def _is_blank(value: object) -> bool:
    return not isinstance(value, str) or not value.strip()


def multipart_body(
    fields: Mapping[str, str],
    file_field: str,
    filename: str,
    file_bytes: bytes,
    *,
    boundary: str = BOUNDARY,
) -> tuple[bytes, str]:
    """确定性 multipart 构造：fields（无 Content-Type 头部）→ 文件字段 → 结尾 delimiter。

    返回 ``(请求体 bytes, "multipart/form-data; boundary={boundary}")``。
    boundary 与任何字段键/值、filename、file_bytes（字节子串）碰撞 → ``LLMError``。
    """
    if _is_blank(boundary):
        raise LLMError("mm: multipart boundary must be a non-blank str")
    if _is_blank(file_field):
        raise LLMError("mm: multipart file_field must be a non-blank str")
    if _is_blank(filename):
        raise LLMError("mm: multipart filename must be a non-blank str")
    if not isinstance(file_bytes, bytes) or not file_bytes:
        raise LLMError("mm: multipart file_bytes must be non-empty bytes")
    if not isinstance(fields, Mapping):
        raise LLMError("mm: multipart fields must be a mapping")
    items: list[tuple[str, str]] = []
    for key, value in fields.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise LLMError("mm: multipart field names and values must be str")
        items.append((key, value))

    # 防结构碰撞：boundary 不得出现在任何字段键/值、filename、文件体字节中。
    needle = boundary.encode("utf-8")
    for key, value in items:
        if boundary in key or boundary in value:
            raise LLMError("mm: multipart boundary collides with a field")
    if boundary in filename:
        raise LLMError("mm: multipart boundary collides with filename")
    if needle in file_bytes:
        raise LLMError("mm: multipart boundary collides with file bytes")

    delim = ("--" + boundary).encode("utf-8")
    crlf = b"\r\n"
    parts: list[bytes] = []
    for key, value in items:
        parts.append(delim + crlf)
        parts.append(
            ('Content-Disposition: form-data; name="' + key + '"').encode("utf-8") + crlf
        )
        parts.append(crlf)
        parts.append(value.encode("utf-8") + crlf)
    parts.append(delim + crlf)
    parts.append(
        (
            'Content-Disposition: form-data; name="'
            + file_field
            + '"; filename="'
            + filename
            + '"'
        ).encode("utf-8")
        + crlf
    )
    parts.append(b"Content-Type: application/octet-stream" + crlf)
    parts.append(crlf)
    parts.append(file_bytes + crlf)
    parts.append(delim + b"--" + crlf)
    return b"".join(parts), "multipart/form-data; boundary=" + boundary


def _json_bytes(payload: Mapping[str, object]) -> bytes:
    """请求体字节闭式：默认分隔符 + ensure_ascii=False + UTF-8。"""
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


# --------------------------------------------------------------------------- #
# 传输（唯一网络出口）
# --------------------------------------------------------------------------- #


class Transport(Protocol):
    """结构协议（鸭子类型）：POST 一次，返回 ``(状态码, 响应体字节)``。"""

    def post(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        body: bytes,
        content_type: str,
        timeout: float,
    ) -> tuple[int, bytes]:  # pragma: no cover - 结构协议
        ...


class MockTransport:
    """确定性 mock 传输（契约测试零网络用）。"""

    DEFAULT_REPLIES = {
        "chat": (200, '{"choices": [{"message": {"content": "模拟回答"}}]}'.encode("utf-8")),
        "tts": (200, b"ID3MOCKMP3"),
        "asr": (200, '{"text": "模拟转写"}'.encode("utf-8")),
    }

    def __init__(self, replies: Optional[Mapping[str, tuple[int, bytes]]] = None) -> None:
        merged = dict(self.DEFAULT_REPLIES)
        if replies:
            merged.update(replies)
        self.replies = merged
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
            return 404, b'{"error":"mock: unknown url"}'
        return self.replies[cap]


class HttpTransport:
    """生产传输：``post`` 前先跑一次白名单守卫（双保险），stdlib urllib 单次 POST。

    ``HTTPError`` → 返回 ``(code, body)`` 不抛（先于 ``URLError`` 捕获，前者是后者子类）；
    ``URLError``/``OSError``/``TimeoutError`` → ``LLMError``。
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
        request = urllib.request.Request(url, data=body, method="POST")
        for name, value in headers.items():
            request.add_header(name, value)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return int(response.getcode()), response.read()
        except urllib.error.HTTPError as exc:
            try:
                payload = exc.read()
            except Exception:  # pragma: no cover - 响应体读取失败
                payload = b""
            return int(exc.code), payload
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            raise LLMError("mm: http request failed") from exc


# --------------------------------------------------------------------------- #
# 响应解析（坏形状统一归族 LLMError）
# --------------------------------------------------------------------------- #


def _parse_chat_reply(raw: bytes) -> str:
    try:
        payload = json.loads(raw)
    except (ValueError, TypeError) as exc:
        raise LLMError("bad chat response: body is not utf-8 json") from exc
    if not isinstance(payload, dict):
        raise LLMError("bad chat response: body is not a json object")
    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMError("bad chat response: missing choices/message/content") from exc
    if not isinstance(content, str):
        raise LLMError("bad chat response: content is not a str")
    return content


def _parse_asr_reply(raw: bytes) -> str:
    try:
        payload = json.loads(raw)
    except (ValueError, TypeError) as exc:
        raise LLMError("bad asr response: body is not json") from exc
    if not isinstance(payload, dict):
        raise LLMError("bad asr response: body is not a json object")
    text = payload.get("text")
    if not isinstance(text, str):
        raise LLMError("bad asr response: text is missing or not a str")
    return text


# --------------------------------------------------------------------------- #
# 客户端
# --------------------------------------------------------------------------- #


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
        # 1. 传输必须提供可调用的 post（鸭子类型）
        if not callable(getattr(transport, "post", None)):
            raise LLMError("mm: transport must provide a callable post")
        # 2. model / tts_model / asr_model / voice 必须为非空白 str
        for name, value in (
            ("model", model),
            ("tts_model", tts_model),
            ("asr_model", asr_model),
            ("voice", voice),
        ):
            if _is_blank(value):
                raise LLMError("mm: " + name + " must be a non-blank str")
        # 3. timeout 必须为正有限数（int/float，bool 拒绝）
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
            raise LLMError("mm: timeout must be a positive finite number")
        seconds = float(timeout)
        if not math.isfinite(seconds) or seconds <= 0:
            raise LLMError("mm: timeout must be a positive finite number")
        # 4. key 构造期解析（fail-fast），只存内存、无公开访问器
        key = api_key(env)

        self._transport = transport
        self._key = key
        self._resolve = resolve
        self.model = model
        self.tts_model = tts_model
        self.asr_model = asr_model
        self.voice = voice
        self.timeout = seconds

    # -- 内部管线 ---------------------------------------------------------- #

    def _post(self, cap: str, body: bytes, content_type: str) -> bytes:
        url = ENDPOINTS[cap]
        # 纵深防御：显式注入了解析桩时，出网前再跑一次白名单守卫（与
        # HttpTransport 内部的前向守卫互为双保险）。resolve=None 时不做系统
        # DNS —— 契约套件零网络，且唯一网络出口是 HttpTransport.post。
        if self._resolve is not None:
            check_url(url, resolve=self._resolve)
        headers = {
            "Authorization": "Bearer " + self._key,
            "Content-Type": content_type,
        }
        status, raw = self._transport.post(
            url,
            headers=headers,
            body=body,
            content_type=content_type,
            timeout=self.timeout,
        )
        if status != 200:
            raise LLMError("mm http " + str(status))
        return raw

    # -- 四能力 ------------------------------------------------------------ #

    def chat(self, text: str, *, system: Optional[str] = None) -> str:
        if _is_blank(text):
            raise LLMError("mm: chat text must be a non-blank str")
        messages: list[dict] = []
        if system is not None:
            if _is_blank(system):
                raise LLMError("mm: chat system must be a non-blank str")
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": text})
        raw = self._post("chat", _json_bytes({"model": self.model, "messages": messages}), JSON_CONTENT_TYPE)
        return _parse_chat_reply(raw)

    def vision(self, prompt: str, images: Sequence, *, image_format: str = "png") -> str:
        content = vision_content(prompt, images, image_format)
        payload = {"model": self.model, "messages": [{"role": "user", "content": content}]}
        raw = self._post("chat", _json_bytes(payload), JSON_CONTENT_TYPE)
        return _parse_chat_reply(raw)

    def tts(
        self,
        text: str,
        *,
        voice: Optional[str] = None,
        response_format: str = TTS_FORMAT,
    ) -> bytes:
        if _is_blank(text):
            raise LLMError("mm: tts text must be a non-blank str")
        chosen = self.voice if voice is None else voice
        if _is_blank(chosen):
            raise LLMError("mm: tts voice must be a non-blank str")
        if _is_blank(response_format):
            raise LLMError("mm: tts response_format must be a non-blank str")
        payload = {
            "model": self.tts_model,
            "input": text,
            "voice": chosen,
            "response_format": response_format,
        }
        # 200 响应体字节原样返回，不解析（模块唯一宽容点）。
        return self._post("tts", _json_bytes(payload), JSON_CONTENT_TYPE)

    def asr(self, audio: bytes, *, filename: str = "audio.wav") -> str:
        if not isinstance(audio, bytes) or not audio:
            raise LLMError("mm: asr audio must be non-empty bytes")
        if _is_blank(filename):
            raise LLMError("mm: asr filename must be a non-blank str")
        body, content_type = multipart_body(
            {"model": self.asr_model}, "file", filename, audio
        )
        return _parse_asr_reply(self._post("asr", body, content_type))
