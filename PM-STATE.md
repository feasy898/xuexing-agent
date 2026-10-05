# PM-STATE — 学情诊断 Agent 开发台账

> 更新：2026-10-02 契约第三波 + D 扩量 + P 阶段收口会话。本文件是断点续作的权威依据：任何新会话从这里恢复上下文。

## 产品愿景（一句话）

有目的地出诊断卷 → 作答 → 认知诊断画知识地图 → 学习路线与教学策略（多媒体/互动/游戏化）
→ 持续调整。确定性内核（状态机+引擎+REST API）+ LLM Agent 壳。渠道：小程序 / 静态卷文件 / 机构接入。

## 开发方法论（用户指定的核心流程）

1. **原型即 oracle**：胶水代码+开源库先做出能跑、测试全绿的原型（M1 ✅）。
2. **spec+eval 迭代**：把原型拆模块，写规格（specs/frozen/*.spec.md）+ 契约测试（tests/contract/），
   冻结契约。
3. **契约内重生成**：子代理只读规格+契约测试重写模块实现（不得读参考实现），
   用 `python tools/run_contract.py --impl-dir <dir>` 判定。
4. **重生成质量反向迭代 spec+eval**：重生成失败 → 归因（规格歧义/评测缺口/生成错误）→ 修规格或评测 → 再重生成。
5. **达标判据**：每个模块连续两轮独立重生成 100% 通过契约测试 → 契约视为完备。
6. **终版入库**：达标后再重生成一次，全绿的那份实现替换/对照入库为正式软件（`src/xuexing/` 为参考实现基线）。

## 里程碑状态

| # | 里程碑 | 状态 | 证据 |
|---|---|---|---|
| M0 | 环境+脚手架 | ✅ | Python 3.12.10, deps OK, git init |
| M1 | 原型 v0 = oracle | ✅ | `9ab7789`，`python -m pytest` = 110 passed（63 常规 + 47 契约） |
| M1.5 | 契约测试框架 | ✅ | tests/contract + tools/run_contract.py（支持 --impl-dir 注入重生成实例） |
| M2 | 工作流#1：规格起草→对抗评审→冻结→重生成3轮→测试门 | ✅ | 8/8 模块连续三轮重生成 100% 通过（world.run 门控），相似度 0.07-0.69 无抄袭；对抗评审修复 46 处歧义；specs/frozen/ 共 2395 行已提交（7503b8e）。诊断规格含"闭式手算+独立引擎300用例逐位对拍"级探针 |
| M4a | 注入器提升根 conftest + run_contract --suite full | ✅ | 56 项测试在参考实现与 round3 实例上双绿 |
| M4b | 终版重生成工作流 | ✅ | 8/8 一次性通过契约+集成+数据 56 项联合门，相似度 0.08-0.65 |
| M4c | 终版实例替换 src/xuexing/ | ✅ | 110 测试全绿；commit d162578；**tag v0.1.0**。spec 驱动闭环完成：oracle→冻结→契约内重生成→终版入库 |
| M3 | 工作流#2：知识注入 | ✅ | commit ab541ec：101 知识点（带课标出处）、321 题（每知识点≥3 道、独立审题员验算）、65 误解模式、52 母题模式；validate_knowledge 通过；抽样 5 题人工验算正确 | 
| M5 | night-iteration + 契约冻结第二波 | ✅ **整夜完成** | 夜间 13 项迭代（KT/蓝图/判分/母题/课标/误解/schema v2/server API/双代理复验 321-321/版面/xAPI/OMR/多租户）+ 契约冻结第二波（8/8 新规格冻结、各 3 轮重生成全过）；终版替换 src → commit c0a116f → **tag v0.2.0 → 558 测试全绿、BACKLOG 清零** |
| M6 | 契约第三波 + 知识注入第三波 + P 阶段（runbook/冒烟） | ✅ **2026-10-02 收口** | C：9 模块清单冻结（tag `wave3-contracts-list`，9839a3f）→ 9 份契约冻结（specs/frozen 16→25，028eafa/1776b3a）→ 两轮盲重写全过（第 1 轮 GLM-5.3-Flash b571523，第 2 轮 MiniMax-M3.1-Flash 异模型独立盲写 058fe72）→ 终版入库 **tag `v0.3.0`**（545392d）。D：MiniMax-M3 原创命题 320（ce192fa）→ 双代理 agree 301 合并、19 分歧入仲裁队列未回填（431648c/9bca515/e3ae481）→ **题库 810→1111，1111/1111 dual-agent-verified**。P：`docs/runbook.md` 成文 + `tools/smoke_api.py` 起服冒烟 14/14 端点通过（239a136）；全量 **709 测试全绿**。渠道路线 P-3 保持 WAITING_HUMAN |

## 当前状态（下一会话从这里开始）

- **v0.4.0 已收口（2026-10-04，tag 已推 GitHub）**：K12 全量建设完成——10 学科 4318 KP、题库 17134 题（去重后）、母题 600+ 条十学科全覆盖、卷型库 21 实例、题型覆盖 99.5%（超 owner 98% 目标）。剩余尾巴：validate 的 173 条 coverage 进度项（bio 97/math 17/eng10 culture 等 KP <3 题）与语文 1626 道开放答案题 LLM 校准，均已登记待下一批次。

- 仓库在 **v0.3.0**（tag = 545392d「C-5 第三波终版入库」；其后为 P 阶段文档收口与 K12 立项文档），契约第三波 + D 扩量 + P runbook/冒烟全部收口；远端 github.com/feasy898/xuexing-agent 已同步（59 提交 + 双 tag）。
- 2026-10-02 实测基线：`python -m pytest` → **709 passed, 2 skipped, 0 failed**；`tools/validate_knowledge.py` → **VALIDATION OK: 189 kps, 1111 items, 343 misconceptions (58 exempt), 52 archetypes, 1111/1111 dual-agent-verified**；`tools/run_contract.py` → exit 0；`git ls-files` 无 `.env`。本地 tag：`v0.3.0`、`wave3-contracts-list`。
- **当前主线（2026-10-02 owner 新使命）：K12 全量建设**——9 学科 × 小一～高三 × 课标全对齐 × 卷子生成为核心，验收四指标（KP 全入 / 题型覆盖 ≥98% / 答案三层准确性 / 加权对齐+海南默认 profile），阶段 K12-0..6 详见 TASK.md §4 与 BACKLOG「K12 全量建设」节。StepFun step_plan 凭据在 `.env`（已验证可用）。
- 待办（等 owner / 下一批）：
  **P-3 三渠道路线裁定 = WAITING_HUMAN（不可代签，裁定前不扩做渠道）**；
  仲裁队列 19 条分歧待人工裁定（`data/verification/arbitration_queue_wave3_annotated.json`，归因 wrong_solve=6，未回填）；
  数学初中母题 52→100+ 与全库 6 题/KP 加密（K12-3 后排期）。
- 恢复协议：读本文件 → `python -m pytest`（应 709 passed）→ 读 TASK.md §4 K12 阶段 →
  按学科流水线跑 K12 工作流（研究→图谱→题库→卷型→审计）→ 每次完成通知后审查+提交+发下一项。

## 模块与契约清单（重生成范围）

| 模块 | 参考实现 | 契约测试 | 范围 |
|---|---|---|---|
| kpgraph | src/xuexing/kpgraph.py | tests/contract/test_kpgraph_contract.py | 重生成 |
| itembank | src/xuexing/itembank.py | tests/contract/test_itembank_contract.py | 重生成 |
| diagnosis | src/xuexing/diagnosis.py | tests/contract/test_diagnosis_contract.py | 重生成 |
| paper | src/xuexing/paper.py | tests/contract/test_paper_contract.py | 重生成 |
| scheduler | src/xuexing/scheduler.py | tests/contract/...scheduler_pedagogy... | 重生成 |
| pedagogy | src/xuexing/pedagogy.py | （同上文件） | 重生成 |
| route | src/xuexing/route.py | tests/contract/test_route_contract.py | 重生成 |
| agent_shell | src/xuexing/agent_shell.py | tests/contract/test_agent_shell_contract.py | 重生成 |
| server | src/xuexing/server.py | tests/unit/test_server.py | 不重生成（薄胶水层） |

## 重生成实现的硬性约束（写进每个生成器 prompt）

- 单文件 `<module>.py`；只允许 import 标准库 + `from xuexing.types import ...`（绝对导入）；
- 必须暴露该模块契约测试用到的全部公开 API（类/函数签名一致）；
- **禁止阅读** src/xuexing/<module>.py 与 tests/unit、tests/integration（契约测试除外）；
- 同输入必须同输出（除 Profile.updated_at / paper_id 的时间戳类字段外无隐藏随机性）；
- paper.py 允许 `random.Random(seed)`（seed 外部传入，确定性由 seed 保证）。

## 已定语义决策（冻结，勿反复）

1. 诊断引擎是"行为契约"不是"算法契约"：单调性/猜测感知/确定性/先序一致性必须满足，内部算法自由。
2. 先序平滑规则：**直接证据优先**。间接补证只对无直接证据的前序生效；间接折价只对有直接证据的前序生效；
   无证据链路不衰减。
3. 选题指标：预测答对概率最接近 0.5（最大信息量代理），并列取 id 最小；约束：未做过/主知识点在 scope/
   per-KP cap/难度带。
4. 组卷：blueprint {kp: n}，池=主知识点题按 |difficulty-target| 排序取前 2n 再 seed 洗牌取 n。
5. SM-2 变体调度（FSRS 是升级路径，契约不变）；rating 0-3；interval ∈ [1,365]，ease ∈ [1.3,3.0]。
6. 策略选择：priority 降序第一个条件匹配者胜；无匹配抛 StrategyError；库必须含无条件的兜底策略。
7. 路线：薄弱点全覆盖 + 拓扑有效；优先级 = 后代数×缺口；已达标知识点生成复习日程。

## 已知问题 / 风险

- Mimosa 扫描提示若干 low + 1 条 high（test_kt_contract.py:248“路径穿越”）：**已人工复核为误报**——该行是 pytest `tmp_path` 沙箱内写 CSV 夹具（`tmp_path / "seq.csv"`），属标准测试实践，无真实穿越风险；扫描器启发式无法识别 tmp_path 沙箱。其余 low 均为固定种子确定性用途（测试+组卷洗牌）。每次提交的低危提示已评估接受。
- `.zcode/`、`_research_tmp/`、`nul` 已 gitignore（调研子代理的临时产物，报告已沉淀到 docs/）。
- 契约重生成的"禁读参考实现"靠指令约束（子代理有全盘读权限），诚信依赖 persona + 事后抽查
  （重生成实现若与参考实现逐字雷同视为违规，在分析阶段检查）。

## 恢复指南（新会话从这里开始）

1. `cd D:\workspace\学情agent && python -m pytest` 应 110 passed。
2. 看 `ListWorkflowRuns` / `.zcode` 确认 M2 工作流状态。
3. M2 完成后：审查 specs/frozen/*.spec.md，`git add specs && git commit`，然后提交 M3 知识注入工作流。
4. M4：把通过矩阵里连续两轮 100% 的模块做终版重生成，全绿后 `git tag v0.1.0`。

- Mimosa「硬编码凭据」新增 1 处（test_mm_ingest_contract.py 的 _SENTINEL_ENV 常量）：**已人工复核为误报**——
  值是 sentinel-token-1（非机密占位，供 MMClient mock 传输层读取，不对应任何真实凭据），已按凭据纪律
  做过价值去化（sk-* → sentinel-*）；扫描器按 env 名+字面值模式匹配无法区分哨兵与真凭据，接受并记录。
