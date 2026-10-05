# K12-6 多模态真调报告

## 结论
**两接口族在本环境均不可用：vision（step-5-preview）+ audio（stepaudio-2.5-tts / stepaudio-2.5-asr）。**

## 失败原因

### 网络层失败（本沙箱网络策略变化导致，非接口本身问题）

| 探测项 | 模型 | 失败原因 |
|---|---|---|
| DNS | — | 正常：公网 IP `14.103.2.83` + IPv6，白名单六重门通过 |
| TCP 域名连接×3 | — | `TimeoutError: timed out` |
| HTTP 直连 IPv4 | — | `PermissionError [WinError 10013] WSAEACCES`（沙箱出站过滤器按目标主机拒绝） |
| IPv6 | — | 超时 |
| curl 交叉验证 (28) | — | `Connection timed out`，`http_code=000` |
| 对照组（baidu / open.bigmodel.cn / github.com 443） | — | 全部可连 → 阻断按目标主机生效，**不是整体断网** |
| 无代理环境变量 | — | 未配置 |

**无 HTTP 状态码** — 请求从未到达 StepFun 服务端（无 401/403/5xx，是 socket 层失败）；key 有效性本次未验证（未达鉴权层）。

## 失败时的接口可靠性判断

- vision 接口本次不可用，**未取得示例输出**
- **接口本身可信**：xuexing-agent/docs/multimodal-api.md:9-13（2026-09-29）四能力实测全 200，彼时主会话出站未受限
- 本次失败属本沙箱网络策略，**不否证接口本身**

## 复测命令

```bash
# 真调冒烟（在可联网环境运行）
XX_MM_SMOKE=1 .venv/Scripts/python.exe -m pytest tests/contract/test_mm_client_contract.py -k smoke_real
```

## 后续计划

- v0.4.0 收口报告 K12-6 部分标注「K12-6 待真调环境就绪后重测」
- 接口族在本地局域网（h.k-gateway）已实测可用；本沙箱恢复出站后立即重测
