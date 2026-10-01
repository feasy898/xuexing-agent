# xuexing-agent —— 学情诊断 Agent

> 接手文档 ｜ 任务卡见 [TASK.md](TASK.md) ｜ 项目原始自述见 [README-upstream.md](README-upstream.md)

## 项目是什么

「确定性内核 + LLM Agent 壳」的中小学（现数学 1–9 年级）学情诊断软件：出诊断卷 → 作答（含拍照/口述多模态采集）→ 认知诊断 → 学习路线与复习调度。设计形态为 REST API + 小程序/静态卷/机构三渠道（API 起服已就绪：runbook + 冒烟 14/14；三渠道接入待 owner 裁定）。

本项目的独特方法论是**契约驱动重生成**：原型即 oracle → 冻结契约（`specs/frozen/` 25 份）→ 子代理只读规格盲重写 → 连续两轮 100% 通过才算契约完备。这是「spec/eval 才是核心资产」理念的项目级实践场。

## 架构一句话

确定性内核（题库/知识库/诊断/调度全部可离线确定性运行，709 个测试覆盖）+ 薄 LLM 壳（多模态采集与讲解生成，默认 mock、零网络隔离，`XX_MM_SMOKE=1` 才开启真调）。

## 构建与运行

- 环境：**Python 3.12**（必须；3.11 会踩 3.12 语法特性报错）。建议项目内建 venv：
  ```bash
  python3.12 -m venv .venv
  .venv/bin/pip install -r requirements.txt
  ```
- 全量测试：`.venv/bin/python -m pytest`（pytest.ini 已含 `-q`，无需重复加）
- 知识库校验：`.venv/bin/python tools/validate_knowledge.py`
- 契约测试：`.venv/bin/python tools/run_contract.py`
- API 起服（产品化第一站）：按 [docs/runbook.md](docs/runbook.md) 注入知识库后 `.venv/bin/uvicorn xuexing.server:create_app --factory`（冒烟脚本 `tools/smoke_api.py`，14/14 端点通过）

## 验收基线（2026-10-02 第三波收口实测）

| 门 | 命令 | 基线 |
|---|---|---|
| G0-1 全量测试 | `.venv/bin/python -m pytest` | **709 passed, 2 skipped, 0 failed, exit 0（本机实测 10.5s）** |
| G0-2 知识库校验 | `tools/validate_knowledge.py` | **VALIDATION OK: 189 kps, 1111 items（全部双代理验证）, 343 misconceptions (>= 2 per kp or exempt, 58 exempt), 52 archetypes, schema v2 source ok, 1111/1111 items dual-agent-verified** |
| G0-3 契约测试 | `tools/run_contract.py` | 全绿 exit 0 |
| G0-4 凭据零入库 | `git ls-files | grep -i '\.env$'` | 空（`.env` 已 gitignore；key 只从环境变量读） |
| G0-5 零网络默认 | 不设 `XX_MM_SMOKE` 跑三件套 | 断网环境可通过（多模态默认 mock；沿用 10-01 结论，本轮未单列复测） |

> 版本：**v0.3.0**（tag = 545392d 第三波终版入库；HEAD 239a136 为 P 阶段文档收口）。第三波盲重写两轮全过（GLM-5.3-Flash / MiniMax-M3.1-Flash 异模型，b571523 / 058fe72）。

## 已知问题

1. **渠道接入未开始（P-3 WAITING_HUMAN）**：三渠道（小程序/静态卷/机构）优先级与合规时机待 owner 裁定，裁定前不扩做渠道；合规五关（双减/生成式 AI 备案/PIPL/未成年人模式/教育 App 备案）未启动，裁定前不采集任何真实学生数据。API 侧已就绪：`docs/runbook.md` 成文、起服冒烟 14/14 端点通过（2026-10-02）。
2. **仲裁队列 19 条分歧未回填**：第三波双代理复验的 19 条 disagree 题（归因 wrong_key=0 / wrong_solve=6，见 `data/verification/arbitration_queue_wave3_annotated.json`）未入库，待人工裁定。
3. **多模态真调**：阶跃（StepFun）API 凭据需自备环境变量（`STEPFUN_API_KEY`/`XX_LLM_API_KEY`），默认集永远走 mock；mm 五模块 + 第三波契约均以 mock/离线门控验收，真调未执行。
4. 第三波遗留 aspirational 指标：母题库仍为 52（原 BACKLOG 曾列 100+ 未纳入本轮验收）；全库均值 ~5.9 题/KP（原注 6-10 未严格达成）。是否补量待 owner 定优先级。
