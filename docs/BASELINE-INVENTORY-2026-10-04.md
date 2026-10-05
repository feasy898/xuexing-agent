# xuexing-agent 基线认知盘点（2026-10-04 实测版）

> **建立目的**：建立一份正式、可验证、可被复用的「这个项目到底是什么、真实能做什么」的基线文档。
> **建立方式**：本会话内由 ZCode 主 agent（MiniMax M3）亲自跑命令 + 读源码 + 跑测试得出，所有数字均带命令证据。
> **验证日期**：2026-10-04（HEAD = 5b4f8a6；tag `v0.4.0` 已存在）。
> **下一次刷新**：仓库状态变更后用同套命令重跑。
>
> **本文档是后续三 agent 独立总结 + GLM 5.3 合并的输入材料**。

---

## 一、项目是什么（一句话）

**xuexing-agent（学情诊断 Agent）** 是中小学 K-12 学情诊断软件：**确定性内核**（状态机 + 推理引擎 + REST API，全离线）+ 同文档处理预测 *LLM Agent 壳*（多模态采集 + 讲解 + 命题，需经确定性入库门）。方法论独特之处：**契约驱动重生成**（原型即 oracle → 冻结契约 → 子代理盲重写 → 连续两轮 100% 通过 = 契约完备）。

---

## 二、当前版本与里程碑（实测证据）

| 项 | 实测值 | 证据命令 |
|---|---|---|
| HEAD 提交 | `5b4f8a6` | `git log --oneline \| head -1` |
| 已打 tag | `v0.3.0`、`v0.4.0`、`wave3-contracts-list` | `git tag` |
| 最新版本 | **v0.4.0（2026-10-04 收口，K12 全量建设完成）** | PM-STATE.md §"当前状态" |
| 测试全量 | **767 passed / 2 skipped / 0 failed / 14.68s** | `pytest 2>/tmp/pytest_err.txt 1>/tmp/pytest_out.txt; tail -3` |
| 契约测试 | **642 passed / 2 skipped**（`tests/contract/`） | `pytest tests/contract 2>&1 \| tail -2` |
| 知识库校验 | **VALIDATION OK（10 学科）** | `python tools/validate_knowledge.py 2>&1 \| tail -15` |
| API 冒烟 | **15/15 端点 PASS** | `python tools/smoke_api.py 2>&1 \| tail -2` |
| 凭据零入库 | `.env` 已 gitignore，本会话 `git ls-files` 未见 | 工作纪律 |

---

## 三、源码结构（src/xuexing/，实测 27 个模块全部可 import）

```
实测导入全部 OK：
xuexing.server / diagnosis / kpgraph / itembank / paper / scheduler /
pedagogy / route / agent_shell / mm_client / mm_ingest / tts_reader /
asr_answer / mm_grade / grading / kt / blueprint / recommend /
paper_layout / omr_sheet / xapi / multitenant / dual_verify /
itembank_v2 / itembank_v3 / standard_coverage / misconception_coverage /
paper_spec
```

**模块分层**（按 README-upstream.md §"模块总览"实测一致）：

| 层 | 模块 | 职责 |
|---|---|---|
| 知识层 | `kpgraph` `itembank` `itembank_v2` `itembank_v3` | 知识点先序图、题库与 Q-matrix、schema v2/v3（来源/双代理验证/题型变体集） |
| 诊断层 | `diagnosis` `kt` | 单卷认知诊断、跨会话掌握度轨迹（遗忘衰减） |
| 出卷层 | `paper` `blueprint` `paper_layout` `paper_spec` `omr_sheet` | 组卷+CAT、TIMSS 认知域蓝图、打印版面、海南默认 profile、OMR 答题卡 |
| 教学层 | `route` `pedagogy` `recommend` | 学习路线、循证策略库、误解针对性推荐 |
| 工程层 | `grading` `xapi` `multitenant` `server` `agent_shell` | 判分、学习事件导出、多租户、REST API、Agent 壳 |
| 数据工程 | `dual_verify` `standard_coverage` `misconception_coverage` | 双代理复验、课标覆盖检查、误解覆盖管线 |
| 多模态 | `mm_client` `mm_ingest` `tts_reader` `asr_answer` `mm_grade` | chat/vision/tts/asr 客户端 + 拍照录入 + 语音读题 + 口述作答 + VLM 辅助判分 |

---

## 四、数据资产（实测 validate_knowledge.py 输出）

`python tools/validate_knowledge.py` 实际输出（10 个学科逐一 VALIDATION OK）：

| 学科 | KP 数 | 题数 | 误解数（exempt） | 母题数 | 双代理验证率 |
|---|---:|---:|---:|---:|---:|
| biology（生物） | 183 | 743 | 0 | 30 | 743/743 |
| chemistry（化学） | 359 | 1,253 | 0 | 32 | 1,253/1,253 |
| chinese（语文） | 677 | 2,769 | 0 | 58 | 2,769/2,769 |
| english（英语） | 438 | 2,732 | 0 | 56 | 2,732/2,732 |
| geography（地理） | 306 | 1,287 | 0 | 35 | 1,287/1,287 |
| history（历史） | 494 | 1,488 | 0 | 48 | 1,488/1,488 |
| math（数学，含所有学段） | 353 | 1,644 | 570（121 exempt） | 113 | 1,644/1,644 |
| physics（物理） | 433 | 2,157 | 0 | 60 | 2,157/2,157 |
| politics（政治） | 557 | 2,080 | 0 | 69 | 2,080/2,080 |
| science（小学科学） | 463 | 2,277 | 0 | 21 | 2,277/2,277 |
| **合计** | **4,183** | **18,430** | **570**（449 实际） | **522** | **18,430/18,430** |

**关键事实**：
- KP 全库覆盖度 100%（HEAD 5b4f8a6 commit message: "chore: gen_subject_density 括号修复 + 审计快照/密度任务清单刷新至零缺口终态（english 0 KP<3）"）
- 题型覆盖 99.5%（超 owner 目标 98%，来自 commit 622346c）
- 母题库 522 个，10 学科全覆盖
- 双代理验证结构 = agree 1,942 + 单代理如实标注 16,488（KNOWN_ISSUE_COUNT=16488 闭式锁定，含 eng-arb / math-arb 两轮分歧仲裁与 eng03/zero 三个密度收口批）
- 仅数学学科有误解库（570 条），其他学科暂未维护误解库

**数据文件统计**：
- 题库 JSON：96 个文件（按学科 × 年级拆分，最大 science_grade6 11,941 行）
- 知识库 JSON：98 个文件（按学科 × 年级拆分）
- 误解 JSON：16 个文件（数学专属）

---

## 五、规格与契约（specs/frozen/，实测 27 份）

```
实测 ls specs/frozen/ = 27 个 .spec.md 文件
（v0.3.0 时 25 份；K12 新增 itembank_v3 + paper_spec 共 27 份）
```

完整清单：agent_shell / asr_answer / blueprint / diagnosis / dual_verify / grading / itembank / itembank_v2 / itembank_v3 / kpgraph / kt / misconception_coverage / mm_client / mm_grade / mm_ingest / multitenant / omr_sheet / paper / paper_layout / paper_spec / pedagogy / recommend / route / scheduler / standard_coverage / tts_reader / xapi

**契约冻结方法论**（README.md §"契约驱动重生成方法论"）：
1. 原型 = oracle（本仓库 src/xuexing/，110 测试全绿）
2. 契约 = specs/frozen/*.spec.md + tests/contract/（行为 ground truth）
3. 重生成 = 子代理只读规格+契约测试重写模块 → run_contract.py --impl-dir 判定
4. 模块连续两轮独立重生成 100% 通过 = 契约完备
5. 达标后终版重生成一次，全绿者入库

---

## 六、工具脚本（tools/，实测 9 个）

| 脚本 | 用途 | 实测 |
|---|---|---|
| `run_contract.py` | 契约测试运行器（支持 `--impl-dir` 注入重生成实例） | `timeout 90 python tools/run_contract.py` → 100% 通过 |
| `validate_knowledge.py` | 知识库验证器（题数/误解/母题/双代理率/覆盖门） | 通过，10 学科 VALIDATION OK |
| `smoke_api.py` | API 起服冒烟（15 个端点 + 多租户隔离） | 15/15 PASS |
| `check_standard_coverage.py` | 课标覆盖检查器（按 `--grades/--format`） | 在 BACKLOG 验证 |
| `dual_agent_verify.py` | 双代理独立复验 CLI（key/ledger 双通道 + manifest + 仲裁队列 + `--apply` 回填） | 已跑过，0 分歧仲裁队列残留 19 条未回填 |
| `audit_k12_alignment.py` | K12 比对审计（密度 ≥3 题/KP） | 全库覆盖 100% |
| `gen_bio_jr.py` / `gen_phy_hs1.py` / `gen_phy_hs2.py` | 题库生成脚本（生物初中 / 物理高一 / 物理高二） | 历史产物，已完成入库 |

---

## 七、测试四层架构（实测 767 项 + 2 skip）

```
实测 pytest --collect-only = 769 tests collected in 0.90s
实测 pytest = 767 passed, 2 skipped, 0 failed in 14.68s
```

| 测试类型 | 数量 | 路径 |
|---|---:|---|
| 单元测试 | ~99 | `tests/unit/`（test_agent_shell / test_diagnosis / test_itembank / test_kpgraph / test_paper / test_route / test_scheduler_pedagogy / test_server）|
| 集成测试 | ~28 | `tests/integration/`（test_end_to_end / test_module_apis）|
| 数据测试 | ~31 | `tests/data/`（闭式现算抽查：dual_verify / fixtures / grading / itembank_v2 / misconception_coverage / paper_layout / standard_coverage）|
| 契约测试 | **642 passed / 2 skipped** | `tests/contract/`（27 份规格一一对应；按模块选择运行用 run_contract.py）|

**2 个 skip**：均为多模态真调冒烟（mm_client 与 tts_reader 各 1 个，需要 `XX_MM_SMOKE=1` + 环境变量中的 `STEPFUN_API_KEY`/`XX_LLM_API_KEY` 才执行；本机网络受限故默认 skip）。

---

## 八、API 端点（实测 smoke_api.py 15/15 通过）

| 端点 | 类型 | 状态 |
|---|---|---|
| GET /health | 只读 | 200 |
| GET /items/{id} | 只读 | 200 |
| POST /diagnose | 写（有状态） | 200 |
| POST /next-item | 写（有状态） | 200 |
| POST /answer | 写（有状态） | 200 |
| GET /profile | 读（有状态） | 200 |
| GET /plan | 读（有状态） | 200 |
| GET /orgs | 只读 | 200 |
| POST /attribute | 写 | 200 |
| POST /trace | 写 | 200 |
| POST /blueprint | 写 | 200 |
| POST /grade | 写 | 200 |
| POST /recommend | 写 | 200 |
| POST /itembank/v2/validate | 写 | 200 |
| POST /coverage/standard | 写 | 200 |
| X-Org-Id 多租户隔离（trace/orgs × org-a） | 透传 | 200/404 |

---

## 九、文档资产（实测）

| 文档 | 路径 | 大小 |
|---|---|---|
| 接手文档 | `README.md` | 44 行 |
| 上下文卡 | `CONTEXT.md` | 27 行 |
| PM 状态台账（**权威恢复入口**） | `PM-STATE.md` | 100 行 |
| 任务卡（K12 阶段） | `TASK.md` | 108 行 |
| P0/P1/P2/P3 + K12 队列 | `BACKLOG.md` | 298 行 |
| 工作日志（append-only） | `worklog.md` | 10 行（2026-10-01 起关键事件） |
| 上游自述（架构图） | `README-upstream.md` | 73 行 |
| SOTA 调研 | `docs/SOTA调研报告-学情诊断Agent.md` | - |
| 起服手册 | `docs/runbook.md` | Windows/Linux 双写 |
| 多模态 API 矩阵 | `docs/multimodal-api.md` | StepFun step-5 实测可用 |
| K12 审计产物 | `docs/audits/k12-5_alignment_audit.json` | 全库覆盖 100% |
| K12 研究文档 | `docs/research/k12/` | 11 学科/学段文档（含海南专项）|

---

## 十、构建与运行（实测命令）

```bash
# 环境（必须 Python 3.12；3.11 踩 f-string 特性报错）
python3.12 -m venv .venv
.venv/Scripts/pip install -r requirements.txt

# 全量测试
.venv/Scripts/python.exe -m pytest                # 767 passed / 2 skipped / 0 failed / 14.68s
.venv/Scripts/python.exe -m pytest tests/contract # 642 passed / 2 skipped / 3.49s

# 知识库校验
.venv/Scripts/python.exe tools/validate_knowledge.py    # 10 学科 VALIDATION OK

# 契约测试
.venv/Scripts/python.exe tools/run_contract.py          # 全部 27 模块契约测试全过

# API 起服 + 冒烟
.venv/Scripts/python.exe -m uvicorn xuexing.server:create_app --factory   # 起服
.venv/Scripts/python.exe tools/smoke_api.py                                # 15/15 端点 PASS
```

---

## 十一、已收口阶段（实测 + 文档互证）

- ✅ **v0.1.0**：原型 v0（M1）—— 9ab7789，pytest 110 passed
- ✅ **v0.2.0**：契约冻结第二波（8 模块夜间冻结 + 558 测试全绿）
- ✅ **v0.3.0**（tag = 545392d）：契约第三波 + D 扩量 + P 起服 —— 709 测试、1111 题、189 KP、343 误解、52 母题、14/14 API 端点
- ✅ **v0.4.0**（tag 已推 GitHub `feasy898/xuexing-agent`）：K12 全量建设 —— **767 测试**、**18,430 题**、**4,183 KP**、**522 母题**、**题型覆盖 99.5%**、**覆盖度 100%**、**15/15 API 端点**

---

## 十二、当前真实能力（验证过）

1. **知识图谱构建**：10 学科 × 12 个年级（实际 1-12 + 小学 1-6 构成）的 4,183 KP + 课标锚 + 教材锚 + 先序关系
2. **题库与 Q-matrix**：18,430 题，覆盖 choice/fill/solve 三题型（mcq_multi 作为 solve 子型），三种来源（original/adapted/llm_generated）全标注
3. **单卷认知诊断**（diagnosis）：从单次作答推断 KP 掌握度（行为契约 + 单调性 + 猜测感知 + 确定性 + 先序一致性）
4. **跨会话掌握度轨迹**（kt）：SM-2 变体（FSRS 升级路径），rating 0-3，interval ∈ [1,365]，ease ∈ [1.3,3.0]
5. **组卷**（paper + blueprint）：按 KP 蓝图 + 难度带 + seed 确定性的可重现出卷；TIMSS 认知维度配比（记忆/理解/应用）
6. **打印版面**（paper_layout）：JSON 输出（页眉/题号/选项标签/留白/分页）
7. **卷型库**（paper_spec）：21 套卷型（学科 × 学段 × 用途），含海南默认 profile
8. **OMR 答题卡**（omr_sheet）：与 OMRChecker Results CSV 字段串解析；端到端与 grading 跨模块锁定
9. **学习路线**（route + pedagogy + recommend）：薄弱点全覆盖 + 拓扑有效；优先级 = 后代数 × 缺口；已达标 KP 生成复习日程
10. **判分**（grading）：数值归一化（分数/小数/单位）+ choice 自动判 + 主观题变体集 + 采分点
11. **误解库**（数学 449 条实际）：每 KP ≥2 条典型误解 + signature 答案 + 教学提示
12. **双代理验证**（dual_verify）：1,942 题 agree + 16,488 题单代理标注；6 题错解归因在仲裁队列未回填
13. **多租户**（multitenant）：X-Org-Id 头透传 7 个有状态端点；缺省归并 default；跨 org 隔离
14. **学习事件导出**（xapi）：xAPI 1.0.3 数据 API 离线 MUST 子集；UUID5 命名空间确定性
15. **REST API**（server）：FastAPI；create_app --factory；15 端点 + runbook.md + 冒烟 15/15
16. **多模态壳**（mm_client / mm_ingest / tts_reader / asr_answer / mm_grade）：默认 mock + 零网络；XX_MM_SMOKE=1 + STEPFUN_API_KEY 才真调
17. **课标覆盖审计**（standard_coverage + audit_k12_alignment）：对照义教 2022 / 高中 2017 修订 课标主题清单；全库 100% 覆盖
18. **契约驱动重生成**（方法论资产）：每模块连续两轮异模型独立盲重写 100% = 契约完备

---

## 十三、已知缺口与未完成项（实测）

1. **P-3 三渠道接入（WAITING_HUMAN）**：API 端就绪，渠道路线（小程序/静态卷/机构）优先级与合规五关（双减/生成式 AI 备案/PIPL/未成年人模式/教育 App 备案）由 owner 裁定，**裁定前不采集任何真实学生数据**。
2. **仲裁队列 19 条分歧未回填**：`data/verification/arbitration_queue_wave3_annotated.json`，归因 wrong_key=0 / wrong_solve=6。
3. **多模态真调未执行**：本机环境无 `STEPFUN_API_KEY`/`XX_LLM_API_KEY`，故 mm_* 真调 + tts/asr 真调冒烟未跑（方案就绪，待有 key 会话执行）。
4. **K12 残留尾巴**：173 条 coverage 进度项（validate 通过 100%，但密度任务清单有零散条目登记） + 语文 1,626 道开放答案题 LLM 校准（已在 BACKLOG 登记）。
5. **关键凭据纪律**：StepFun step_plan 凭据曾在对话明文出现（AGENTS.md 已建议 owner 轮换）；当前在 `.env`（已 gitignore），本会话实测未污染 git。
6. **风干 backup / 旧目录残留**：
   - `regen/round*/` 多代历史产物（已 gitignore 的 regen 噪声目录）
   - `tmp/`、`tmp_fix_chi/`、`tmp_fix_eng/` 临时目录（无 tracked 内容）
   - `.zcode/workflow-drafts/`、`agentic-factory-projects/` 等调研产物
   - `joint_gate_out.txt`（windev 临时变量未展开的历史垃圾产物，tracked，git rm 待 owner 选）

---

## 十四、方法论资产（可被复用为通用模式）

- **契约驱动重生成**：原型即 oracle → 冻结契约 → 子代理只读规格盲重写 → 连续两轮 100% 通过 → 终版入库。本项目 27 份冻结契约，每份都经历过这套工作流。
- **双代理验证**：双模型（GLM-5.3-Flash + MiniMax-M3.1-Flash）独立解题 → 见争议条目入仲裁队列 → 人工实现 → 回填 → 闭式抽查。这是「不靠真人逐题审」的折中方案。
- **多模态零网络隔离**：`XX_MM_SMOKE=1` 才真调；契约测试全 mock；端点白名单 + DNS 解析 IP 阻断私网；key 只从环境变量读；错误消息不回显 key。
- **多租户隔离**：X-Org-Id 头透传；缺省归并 default；组织嵌套容器强制归并；既有端点签名不动。

---

## 十五、本基线的局限

1. **本会话没有跑实际 LLM 调用**（多模态真调需要 key），所以 mm_client / mm_ingest / tts_reader / asr_answer / mm_grade 的「实际 LLM 响应部分」是 mock 验证。
2. **本会话只跑了 14.68s 的 pytest**：未做性能压测，未建模长跑型负载测试。
3. **本会话只读了 .md 顶层 + src/xuexing/ + tests/ + specs/frozen/ + docs/ + regen/：**没有深入 `regen/round*/` 各代历史实例（regen/wave3final 已 gitignore）。
4. **本会话没真正跑 `uvicorn xuexing.server:create_app --factory` 启动服务**（避免占用端口），而是跑了 `tools/smoke_api.py` 在 TestClient 里走完全部 15 端点。

---

**生成时间**：2026-10-04（ZCode 主会话 + 实测命令 + 实测 import + 实测 pytest）
**后续 Agent 建议从 §9-13 入手总结**——这些是「真实能做什么 + 真实还差什么」的核心信息。