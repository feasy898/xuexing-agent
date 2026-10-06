# xuexing-agent 运行手册（runbook）

> 阶段 P 交付（TASK.md P-2）｜ 2026-10-02 实测定稿 ｜ 面向接手部署的工程师：命令可复制即用。
> Windows 与 Linux 命令双写：Windows 用 `.venv\Scripts\`，Linux 用 `.venv/bin/`。
> **断网可跑**的部分均标注【离线】；需要联网的只有 §1 依赖安装一步。
> 所有「预期输出」均为 2026-10-02 在本仓实跑所得（Python 3.12.10 / fastapi 0.142.2 / uvicorn 0.54.0）。

---

## 1. 环境构建

**Python 3.12 必须**（README.md:17：3.11 会踩 3.12 语法特性报错）。依赖清单见 `requirements.txt`（共 4 行：`fastapi>=0.110`、`uvicorn>=0.29`、`httpx>=0.27`、`pytest>=8.0`）。

先确认解释器版本：

```bat
:: Windows
py -3.12 --version        # 或 python --version，需输出 Python 3.12.x
```

```bash
# Linux
python3.12 --version      # 需输出 Python 3.12.x
```

在仓库根创建 venv 并安装依赖（**需联网**，仅此一步）：

```bat
:: Windows
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

```bash
# Linux
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

验证：

```bat
.venv\Scripts\python -c "import fastapi, uvicorn, httpx, pytest; print('deps ok')"
```

```bash
.venv/bin/python -c "import fastapi, uvicorn, httpx, pytest; print('deps ok')"
```

预期输出：`deps ok`。以下所有命令均假定当前目录为仓库根。

## 2. 验收基线三件套（G0-1/2/3）

TASK.md §2.0 的贯穿底线门。判定标准统一为 **exit 0**。三件全部【离线】可跑。

| 门 | Windows | Linux | 实测预期输出（2026-10-02） |
|---|---|---|---|
| G0-1 全量测试 | `.venv\Scripts\python -m pytest` | `.venv/bin/python -m pytest` | `709 passed, 2 skipped, 1 warning in 26.51s`，exit 0 |
| G0-2 知识库校验 | `.venv\Scripts\python tools\validate_knowledge.py` | `.venv/bin/python tools/validate_knowledge.py` | `VALIDATION OK: 189 kps, 1111 items, 343 misconceptions (>= 2 per kp or exempt, 58 exempt), 52 archetypes, schema v2 source ok, 1111/1111 items dual-agent-verified`，exit 0 |
| G0-3 契约测试 | `.venv\Scripts\python tools\run_contract.py` | `.venv/bin/python tools/run_contract.py` | 点号进度到 100% 后**没有**统计末行（见 §7 坑 1），exit 0 |

两条配套底线（TASK.md §2.0，本日同过）：

- **G0-4 凭据零入库**：`git ls-files | grep -i "\.env$"` → 空输出（grep 退出码 1），【离线】。
- **G0-5 零网络默认**：不设 `XX_MM_SMOKE` 环境变量时，上面三件套全部走 mock、无网络调用；本日实测即在此条件下通过。

注意：G0-2 的题数是**移动目标**。README.md:32 的基线为 810 题（2026-10-01），D 波注入（提交 `9bca515`，题库 810→1111）后本日实测 1111 题。判定看 `VALIDATION OK` 与 `dual-agent-verified` 全量，不背 810 这个数。

## 3. API 起服

### 3.1 关键事实：create_app 是带参工厂，不能裸 `--factory`

`src/xuexing/server.py:120-125` 的签名是：

```python
def create_app(bank: ItemBank, graph: KPGraph, strategies: StrategyLibrary,
               misconceptions: list[Misconception] | None = None) -> FastAPI:
```

`bank / graph / strategies` **必填**（misconceptions 可选），uvicorn 的 `--factory` 只会无参调用它。README.md:25 的 `uvicorn xuexing.server:create_app --factory` 写法**会直接失败**，实测报错：

```
ERROR:    Error loading ASGI app factory: create_app() missing 3 required positional arguments: 'bank', 'graph', and 'strategies'
```

起服前必须先注入知识库。注入点与 `tests/conftest.py:47-67` 同源：

| create_app 参数 | 数据文件 | 装载函数 |
|---|---|---|
| `bank` | `data/items/math_grade7_items.json` | `xuexing.load_itembank` |
| `graph` | `data/knowledge/math_grade7.json` | `xuexing.load_kpgraph` |
| `strategies` | `data/pedagogy/strategies.json` | `xuexing.load_strategies` |
| `misconceptions` | `data/misconceptions/math_misconceptions.json` | `Misconception(**mc)` 逐条 |

### 3.2 推荐用法：tools/smoke_api.py --serve

工具自带上述注入（`tools/smoke_api.py` 的 `load_app()`），无需 PYTHONPATH、无需额外文件。【离线注入，起服后监听本地端口】

```bat
:: Windows
.venv\Scripts\python tools\smoke_api.py --serve --host 127.0.0.1 --port 8000
```

```bash
# Linux
.venv/bin/python tools/smoke_api.py --serve --host 127.0.0.1 --port 8000
```

启动成功标志（实测输出）：

```
知识库注入完成：items=222 kps=37 bank=data\items\math_grade7_items.json
起服：http://127.0.0.1:8000  （Ctrl+C 停止；只读冒烟见 docs/runbook.md §6）
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

另开终端验证任一只读端点 200（TASK.md P-1 的 curl 判据，实测）：

```bat
curl http://127.0.0.1:8000/orgs
:: → {"orgs":[]}   （HTTP 200）
```

停止：服务终端按 **Ctrl+C**。

> 想换注入子库：当前工具钉住 grade7（与测试夹具一致）。换 8/9 年级需改 `tools/smoke_api.py` 顶部的 `BANK_PATH / GRAPH_PATH / MISCONCEPTIONS_PATH`（文件都在 `data/` 下同名规律）。

### 3.3 手动等价写法（自建无参入口）

若想用 uvicorn CLI 而不经工具，在仓库根建一个 `run_server.py`（**示例，仓库未收录该文件**）：

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))
from tools.smoke_api import load_app  # 复用同一注入逻辑

app = load_app()  # 模块级 app 对象，uvicorn 直接挂载，不需要 --factory
```

然后：

```bat
.venv\Scripts\python -m uvicorn run_server:app --host 127.0.0.1 --port 8000
```

```bash
.venv/bin/python -m uvicorn run_server:app --host 127.0.0.1 --port 8000
```

### 3.4 多租户：X-Org-Id 头

依据 `src/xuexing/server.py:9-13` 与 `src/xuexing/multitenant.py`：

- **全部有状态端点**接受可选请求头 `X-Org-Id`：`/learners/{id}/responses|profile|plan|next_item|reviews`、`/trace`、`/recommend`。
- 缺省 / 空串 / 纯空白 → 归并到内置机构 `"default"`（`multitenant.py:21-30` `resolve_org`）；不做大小写折叠、不做 Unicode 规范化，其余值去首尾空白后原样使用。
- 会话存储与选题计数按 `(org, learner_id)` 分域：**同一 learner_id 在不同机构下完全隔离**；不带头的请求行为与单租户时代逐字节一致（`server.py:12-13`）。
- 无状态端点（`/papers/diagnostic`、`/blueprint`、`/grade`、`/attribute`、`/itembank/v2/validate`、`/coverage/standard`）**忽略**该头。
- `GET /orgs` 只读枚举机构命名空间（org、learner 均升序，`server.py:211-217`）。

curl 示例（org-a 下保存画像，缺省域看不到——离线冒烟第 13 项同口径，实测通过）：

```bat
curl -X POST http://127.0.0.1:8000/trace -H "Content-Type: application/json" -H "X-Org-Id: org-a" -d "{\"learner_id\":\"stu-1\",\"events\":[{\"item_id\":\"m7_010\",\"correct\":true,\"day\":0.0}]}"
curl -i http://127.0.0.1:8000/learners/stu-1/profile                        rem → 404（default 域无此人）
curl -i -H "X-Org-Id: org-a" http://127.0.0.1:8000/learners/stu-1/profile   rem → 200
```

## 4. 端点速查表

共 **17 个端点**（`src/xuexing/server.py` 实读；错误映射全局固定：领域 `ValueError`→400、资源缺失→404、pydantic 形态违规→422、绝不 500，`server.py:6-7`）。示例值取自 `tests/integration/test_module_apis.py`（grade7 真实数据，可直接对 §3.2 起的服务粘贴）。15–17 为卷型出卷族（2026-10-06 新增/补记），由离线门 `tools/check_paper_spec.py`（结构）与 `tools/check_paper_render.py`（成品渲染）覆盖，不在 §6 的 15 项冒烟内。

| # | 方法 路径 | 请求体 / 参数示例 | 关键响应字段 |
|---|---|---|---|
| 1 | POST `/papers/diagnostic` | `{"blueprint": {"kp_rational_add": 2, "kp_eq_solve": 1}, "seed": 42}`（另有缺省 `title="诊断卷"`、`difficulty_target=0.5`） | `paper_id` `title` `blueprint` `item_ids`（长度=蓝图合计） `sections` |
| 2 | POST `/learners/{id}/responses` | `{"responses": [{"item_id": "m7_010", "correct": true, "learner_answer": "2"}]}`（`learner_answer` 可省）【X-Org-Id】 | `learner_id` `mastery`（kp→0..1） `clusters`（簇→均分） |
| 3 | GET `/learners/{id}/profile` | 路径参数即可【X-Org-Id】 | `learner_id` `mastery` `evidence`（kp→证据数） `updated_at` `confidence`；未诊断 → 404 |
| 4 | GET `/learners/{id}/plan` | 路径参数即可【X-Org-Id】 | `learner_id` `steps[]`（`kp_id` `strategy_id` `rationale` `target_mastery` `recommended_item_ids`） `reviews[]`（`kp_id` `due` `interval_days` `ease`） `created_at` |
| 5 | GET `/learners/{id}/next_item` | query 可选 `scope=kp1,kp2`、`per_kp_cap=3`【X-Org-Id】 | `item_id`；枯竭时 `{"item_id": null, "reason": "exhausted"}` |
| 6 | POST `/learners/{id}/reviews` | `{"rating": 2, "days_since_last": 0}`；rating ∉ 0–3 → 400 | `kp_id` `due`（ISO 日期） `interval_days` `ease`；注意 `kp_id` 实际等于 `learner_id`（`server.py:208` 把 learner_id 传给 schedule 的 kp_id 形参，胶水层怪癖，见 §7 坑 9） |
| 7 | GET `/orgs` | 无 | `orgs[]`（`org_id` `learner_ids[]`），均升序 |
| 8 | POST `/attribute` | **query 参数**（非 JSON 体）：`?item_id=m7_010&learner_answer=5` | `misconception_id`（签名命中返回 `"mc_sign_neg"`，未命中/空答案为 `null`）；题不存在 404 |
| 9 | POST `/trace` | `{"learner_id": "stu-1", "events": [{"item_id": "m7_010", "correct": true, "day": 0.0}, {"item_id": "m7_011", "correct": false, "day": 3.0}]}`（`learner_id` 省略则不存画像；缺省 `prior=0.5`、`half_life_days=7.0`）【X-Org-Id】 | `learner_id`（null 或回显） `profile_saved` `snapshots[]`（`day` `item_id` `correct` `mastery` `evidence`）；day 降序 / `prior` ∉ (0,1) / `half_life_days` ≤ 0 → 400；题库外事件静默跳过不推时钟 |
| 10 | POST `/blueprint` | `{"targets": ["kp_rational_add", "kp_eq_solve"], "budget": 3}`（可选 `ratios`，缺省 `{"记忆":0.4,"理解":0.4,"应用":0.2}`） | `targets`（排序去重） `budget` `ratios` `allocation` `dimension_totals` `counts`（可直接喂端点 1） `per_dimension[]`；targets 未知/budget 超池 → 400 |
| 11 | POST `/grade` | 原子：`{"item_id": "m7_010", "learner_answer": "2"}`；批量：`{"answers": [{"item_id": "m7_010", "learner_answer": "2"}, {"item_id": "m7_013", "learner_answer": "6"}]}`（并存时批量优先；批量原子——先全量验存在再判分） | 原子 → `item_id` `correct` `learner_answer` `response_ms`；批量 → `mode:"batch"` `n` `results[]`（同原子字段）；未知题 404（m7_013 标答 `-6`，答 `6` 判错） |
| 12 | POST `/recommend` | kp 模式：`{"kp_id": "kp_rational_add", "limit": 2}`；画像模式：`{"learner_id": "stu-1", "mastery_threshold": 0.65}`；`attach: true` 返回带推荐的完整计划【X-Org-Id】 | kp → `mode:"kp"` `kp_id` `item_ids[]`（误解绑定题 Tier1 在前）；profile → `mode:"profile"` `recommendations[]`（最弱 kp 优先）；plan → `mode:"plan"` `plan`。皆空 400；未知 kp → 200 空列表；未知 learner → 404；`limit` ≤ 0 或 `mastery_threshold` ∉ (0,1) → 400 |
| 13 | POST `/itembank/v2/validate` | `{"items": [...]}`（元素可为任意 JSON 值，校验器是全函数，**恒 200**） | `valid` `errors[]`（如 `"i2: llm_generated requires verification"`、`"item is not a dict"`） `counts{original,adapted,llm_generated}` `total` `verified` |
| 14 | POST `/coverage/standard` | `{"kp_dicts": [{"id": "k1", "standard_ref": "…"}], "topics": {课标清单 JSON}}`（清单可取 `data/curriculum/math_standard_2022_topics.json`） | `coverage_rate` `is_complete` `uncovered_topic_ids`（覆盖缺口） `unmatched_kp_ids`（归属缺口） `matched_kp_ids` `covered_topic_ids` `matches[]`（`kp_id` `topic_ids`）；别名重复/清单为空 → 400，`kp_dicts` 非列表 → 422 |

| 15 | POST `/papers/by-spec` | `{"spec_id": "spec_phy_jr_final", "seed": 42}`（可选 `difficulty_target=0.5`；`learner_id` 仅回显） | `spec_id` `seed` `subject` `stage` `usage` `duration_min` `total_points` `question_count` `sections[]`（大题-小题层级：`title` `form` `count` `points_each` `section_points` `questions[]{question_no,item_id,points}`，小题号全卷连续） `item_ids`；未知卷型 404；卷型分值矛盾（V8）/同型题不足/学段无题库 → 400（fail-closed） |
| 16 | GET `/papers/by-spec/{spec_id}/render.html` | query 可选 `seed=42`、`difficulty_target=0.5`（与端点 15 同参数出同一份卷） | **自包含打印友好 HTML**（`text/html`；内联 CSS、`@page A4` 分页、卷头=卷型标题/满分/时长/满分注意、大题标题带每题分值、选项竖排、解答/填空留作答区、页脚页码；学生卷红线：不含任何作答依据，全卷无 answer/solution 字样）；未知卷型 404，领域错 400，query 形态错 422 |
| 17 | GET `/papers/by-spec/{spec_id}/render.txt` | 同端点 16 | 纯文本简版（`text/plain`；同一次装订同题序，HTML 不可用时的备用） |

【X-Org-Id】= 接受可选多租户头（见 §3.4）。错误对照速记：400 = 语义错（内核 ValueError），404 = 资源不存在，422 = JSON 形态错。

## 5. 环境变量

| 变量 | 作用 | 不设时的默认行为 |
|---|---|---|
| `STEPFUN_API_KEY` | 阶跃星辰 API key，多模态真调用（chat/vision/tts/asr）。key 读取链见 `mm_client.py:71`：`XX_LLM_API_KEY` → `STEPFUN_API_KEY`，取第一个非空值 | 缺 key 时多模态客户端抛 `LLMError`（不回显 key）；但**REST 服务与三件套完全不需要它** |
| `STEPFUN_BASE_URL` | 仅在 `.env.example:4` 登记（`https://api.stepfun.com/step_plan/v1`）。**当前代码不读取该变量**：`mm_client.py:58` 硬编码 `BASE_URL = "https://api.stepfun.com"`（端点白名单冻结，见 docs/multimodal-api.md） | 无效果（如实登记：改它不会改变任何行为） |
| `XX_LLM_API_KEY` | 软件内 LLM 客户端（`agent_shell.py:85-95` `OpenAICompatClient`）的默认 key 环境变量；多模态 key 链第一位 | 缺失时 `OpenAICompatClient.complete` 抛 `LLMError: env XX_LLM_API_KEY not set`；服务端 `/attribute` 用的是 `MockLLM`（`server.py:224`），不受影响 |
| `XX_MM_SMOKE` | 多模态**真调门**：仅当 `=1` 且环境含 key 时，mm_client / tts_reader 的冒烟用例才真调 API（`tests/contract/test_mm_client_contract.py:521-531`、`test_tts_reader_contract.py:467-478`） | 不设或 ≠1 → 永远 mock、零网络（G0-5 的实现机制），断网可跑全部验收 |

其他事实：

- **`.env` 不入库**：`.gitignore` 含 `.env`、`.env.*` 并豁免 `!.env.example`。G0-4 判定：`git ls-files | grep -i "\.env$"` → 空。真实 key 只从环境变量读，不落盘、不进日志。
- **REST 服务面零凭据依赖**：`server.py` 不 import 任何 mm/LLM 客户端，14 个端点全部确定性运行；无 key、无 `.env` 也能完成 §3 起服与 §6 冒烟。
- 另有一个非凭据的注入开关 `XX_IMPL_DIR` / `XX_MODULES`：`tools/run_contract.py --impl-dir <dir>` 重生成判定用（`run_contract.py:66-67`），日常部署不用。

## 6. 冒烟

> **冒烟实测结论（2026-10-02）**：覆盖 **14 个端点** + 1 项多租户专项（共 15 项检查），**15/15 全过**、exit 0。13 项端点主调用 200；按设计的 4xx 同轮验证通过——离线冒烟内：reviews `rating 9`→400、grade 未知题→404、多租户缺省域查画像→404；起服 curl 实测（2026-10-02，§6.2 流程）：grade 未知题→404、trace 形态违规→422。全程零网络、不占端口，断网环境可复跑。命令与完整输出见 §6.1。

### 6.1 离线冒烟（默认模式，【离线】断网可跑）

```bat
.venv\Scripts\python tools\smoke_api.py
```

```bash
.venv/bin/python tools/smoke_api.py
```

进程内 httpx `ASGITransport` 经 `AsyncClient` 直连 `create_app()` 应用（不占端口、零网络），按 §4 逐个调用全部 **14 个端点** + 1 项多租户 X-Org-Id 专项（共 **15 项**），收集状态码与关键响应字段。**本工具不设 `XX_MM_SMOKE`、不发任何网络请求**（`/attribute` 的 LLM 兜底走 `MockLLM`，`server.py:224`）。实测输出（2026-10-02）：

```
离线冒烟（httpx ASGITransport 进程内直连，零网络不占端口）：15 项（14 端点 + 1 多租户专项；bank=math_grade7_items.json items=222 kps=37）
  [01/15] POST /papers/diagnostic              PASS  200 | item_ids×3 title='诊断卷'
  [02/15] POST /learners/smoke-1/responses     PASS  200 | mastery×37 clusters×10
  [03/15] GET /learners/smoke-1/profile        PASS  200 | mastery×37 confidence×37
  [04/15] GET /learners/smoke-1/plan           PASS  200 | steps×37 reviews×0 首个策略=s_retrieval
  [05/15] GET /learners/smoke-1/next_item      PASS  200 | item_id=m7_006
  [06/15] POST /learners/smoke-1/reviews       PASS  200 | kp_id=smoke-1 due=2026-10-04 interval=2 (rating 9 → 400 按设计；kp_id 即 learner_id，server.py:208)
  [07/15] GET /orgs                            PASS  200 | orgs=['default']
  [08/15] POST /attribute                      PASS  200 | misconception_id=mc_sign_neg（签名命中，MockLLM 路径）
  [09/15] POST /trace                          PASS  200 | profile_saved=True snapshots×2
  [10/15] POST /blueprint                      PASS  200 | counts={'kp_eq_solve': 2, 'kp_rational_add': 1} dimensions=['应用', '理解', '记忆']
  [11/15] POST /grade                          PASS  200 | 原子 correct=True；批量 n=3 判定=[True,True,False]（ghost → 404 按设计）
  [12/15] POST /recommend                      PASS  200 | kp 模式 item_ids×6；画像最弱 kp=kp_rational_add
  [13/15] POST /itembank/v2/validate           PASS  200 | valid=True total=222 counts={'original': 129, 'adapted': 0, 'llm_generated': 93}
  [14/15] POST /coverage/standard              PASS  200 | coverage_rate=0.429 未覆盖条目×16
  [15/15] X-Org-Id 多租户隔离（trace/orgs × org-a）   PASS  200/404 | org-a 与 default 隔离；/orgs 可见 org-a
SMOKE_OK 15/15
```

预期：末行 `SMOKE_OK 15/15`，exit 0。有失败时打印 `SMOKE_FAIL <n>/15` 与失败端点清单，exit 1。

### 6.2 起服冒烟（P-1 流程：起服 → curl → 停止）

```bat
:: 终端 1（Windows）
.venv\Scripts\python tools\smoke_api.py --serve --port 8000
```

```bash
# 终端 1（Linux）
.venv/bin/python tools/smoke_api.py --serve --port 8000
```

```bat
:: 终端 2 —— 只读 200（实测）
curl -i http://127.0.0.1:8000/orgs
:: → HTTP 200, {"orgs":[]}

:: 写路径（实测）：trace 存画像
curl -X POST http://127.0.0.1:8000/trace -H "Content-Type: application/json" ^
  -d "{\"learner_id\":\"curl-1\",\"events\":[{\"item_id\":\"m7_010\",\"correct\":true,\"day\":0.0}]}"
:: → {"learner_id":"curl-1","profile_saved":true,"snapshots":[...]}

:: 错误映射（实测）：未知题 404；形态违规 422
curl -s -o NUL -w "%{http_code}" -X POST http://127.0.0.1:8000/grade -H "Content-Type: application/json" -d "{\"item_id\":\"ghost\",\"learner_answer\":\"x\"}"
:: → 404
curl -s -o NUL -w "%{http_code}" -X POST http://127.0.0.1:8000/trace -H "Content-Type: application/json" -d "{\"events\":[{\"item_id\":123,\"correct\":true,\"day\":0.0}]}"
:: → 422
```

（Linux 侧把 `-o NUL` 换成 `-o /dev/null`，`^` 续行符换成 `\`。）

停止：终端 1 **Ctrl+C**。全程无网络外呼，符合 G0-5。

## 7. 已知坑

1. **pytest 双 `-q` 吃掉统计行**（worklog.md:7 留痕，本日复现）：`pytest.ini` 已含 `addopts = -q`，命令行再补一个 `-q` 会双重安静、末行 `N passed` 消失——`tools/run_contract.py:78` 自己又传了 `-q`，所以 G0-3 输出只有进度点没有统计行，属预期。脚本取数用单 `-q` 或 `-rA`/junitxml，不要 grep "passed"。
2. **Python 3.11 不兼容**（README.md:17）：源码用了 3.12 语法特性，3.11 直接语法报错。装 3.12；可用 `py -3.12`（Win）/`python3.12`（Linux）钉住版本。
3. **`uvicorn xuexing.server:create_app --factory` 起不来**（README.md:25 写法已过时）：`create_app` 必填 `bank/graph/strategies`，实测报 `missing 3 required positional arguments`。走 §3.2 / §3.3 的注入路径。
4. **`/attribute` 是 query 参数不是 JSON 体**（`server.py:220` 的裸标量签名）：`POST /attribute?item_id=…&learner_answer=…`，发 JSON body 会 422。
5. **G0-2 数字会漂**：README 基线 810 题（10-01）≠ 本日实测 1111 题（D 波扩量，提交 `9bca515`）。判定认 `VALIDATION OK` + 双代理全量字样，版本对不上先重跑再对台账。
6. **README「已知问题 5」已过时**：`%TEMP%joint_gate_out.txt` 已不在 git 追踪（`git ls-files` grep 无命中），无需清理。
7. **G0-1 有一条无害 warning**：fastapi 0.142.2 + httpx 0.28.1 组合下 `TestClient` 触发 `StarletteDeprecationWarning`（"install httpx2"），不影响判定；pytest 输出里可见、忽略即可（`tools/smoke_api.py` 已改用 httpx `ASGITransport`，自身无此告警）。
8. **grade7 语义断言钉题**：`tools/smoke_api.py` 的判分/归因检查钉住 `m7_010`（标答 `2`）、`m7_013`（标答 `-6`）与误解 `mc_sign_neg`（签名含 `5`）。未来注入批次重划 grade7 子库时若这些题变动，需同步改 `smoke_api.py`，否则冒烟会如实报 FAIL。
9. **reviews 端点的 `kp_id` 其实是 learner_id**：`server.py:208` 调 `schedule(learner_id, …)` 把 learner_id 传进 schedule 的 `kp_id` 形参，响应 `kp_id` 字段因此等于路径里的 learner_id（冒烟第 6 项实测 `kp_id=smoke-1`）。内核 `schedule` 本身没错（`scheduler.py:24-31`），是胶水层字段穿线怪癖；消费该字段做按知识点统计会踩坑。
10. **httpx 0.28 的 `ASGITransport` 仅 async**：同步 `httpx.Client(transport=ASGITransport(...))` 报 `'ASGITransport' object has no attribute 'handle_request'`（本日实测）。进程内直连要用 `httpx.AsyncClient` + `asyncio.run`，`tools/smoke_api.py` 即此写法。

---

*本手册由阶段 P 会话于 2026-10-02 撰写；全部命令与输出均当日在本仓实测（G0-1/2/3、G0-4、离线冒烟、起服 curl、factory 直启失败复现）。*
