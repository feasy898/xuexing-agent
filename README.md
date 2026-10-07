# xuexing-agent —— 学情诊断 Agent

> 接手文档 ｜ 任务卡见 [TASK.md](TASK.md) ｜ 项目原始自述见 [README-upstream.md](README-upstream.md)

## 项目是什么

「确定性内核 + LLM Agent 壳」的中小学（K12 全学段：小学一年级～高三；9 门学科 + 小学科学，共 10 学科）学情诊断软件：出诊断卷 → 作答（含拍照/口述多模态采集）→ 认知诊断 → 学习路线与复习调度。设计形态为 REST API + 静态卷/机构/小程序三渠道（API 起服已就绪：runbook + 冒烟 15/15；渠道路线已裁定 = 静态卷优先，见 docs/SIGNOFF-2026-10-08.md）。

本项目的独特方法论是**契约驱动重生成**：原型即 oracle → 冻结契约（`specs/frozen/` 25 份）→ 子代理只读规格盲重写 → 连续两轮 100% 通过才算契约完备。这是「spec/eval 才是核心资产」理念的项目级实践场。

## 架构一句话

确定性内核（题库/知识库/诊断/调度全部可离线确定性运行，912 个测试覆盖）+ 薄 LLM 壳（多模态采集与讲解生成，默认 mock、零网络隔离，`XX_MM_SMOKE=1` 才开启真调）。

## 构建与运行

- 环境：**Python 3.12**（必须；3.11 会踩 3.12 语法特性报错）。建议项目内建 venv：
  ```bash
  python3.12 -m venv .venv
  .venv/bin/pip install -r requirements.txt
  ```
- 全量测试：`.venv/bin/python -m pytest`（pytest.ini 已含 `-q`，无需重复加）
- 知识库校验：`.venv/bin/python tools/validate_knowledge.py`
- 契约测试：`.venv/bin/python tools/run_contract.py`
- API 起服（产品化第一站）：按 [docs/runbook.md](docs/runbook.md) 注入知识库后 `.venv/bin/uvicorn xuexing.server:create_app --factory`（冒烟脚本 `tools/smoke_api.py`，15/15 端点通过）
- 静态卷分发（已裁定渠道）：`tools/export_static_paper.py`（见 [docs/static-paper.md](docs/static-paper.md)，如未生成本卡产物则按 docs/SIGNOFF-2026-10-08.md TC-4 交付）
- 知识地图可视化：`GET /learners/{id}/knowledge-map.html?subject=X` 自包含 HTML（内联 CSS/SVG、零外部库/JS）——按年级→章→KP 热力呈现掌握度（红薄弱→绿熟练，透明度=置信度），薄弱 top10 带建议动作（与 `/plan` 同引擎），页头含学习者/学科/数据更新时间；不带 `subject` 即跨学科总览。渲染门 `tools/check_kmap.py`（exit 0），人工视检样本 `tools/render_kmap_sample.py` → `out/kmap_sample/`

## 验收基线（2026-10-08 实测）

| 门 | 命令 | 基线 |
|---|---|---|
| G0-1 全量测试 | `.venv/bin/python -m pytest` | **912 passed, 2 skipped, 0 failed, exit 0** |
| G0-2 知识库校验 | `tools/validate_knowledge.py` | **VALIDATION OK ×10 学科；合计 4,263 KP / 18,527 题** |
| G0-3 契约测试 | `tools/run_contract.py` | 全绿 exit 0 |
| G0-4 凭据零入库 | `git ls-files | grep -i '\.env$'` | 空（`.env` 已 gitignore；key 只从环境变量读） |
| G0-5 零网络默认 | 不设 `XX_MM_SMOKE` 跑三件套 | 断网环境可通过（多模态默认 mock） |
| 卷型库 | `tools/check_paper_spec.py` | **OK=21 / FAIL-CLOSED=0 / UNEXPECTED=0** |
| 起服冒烟 | `tools/smoke_api.py` | **SMOKE_OK 15/15 端点** |
| 学生作答闭环 | `tools/check_exam_loop.py` | **EXAM-LOOP-OK 17/17** |

> **验证结构如实披露（2026-10-08）**：题库 18,527 题中，双代理 agree 验证 **1,942** 题；单代理验证并如实登记（带 `single_agent` 标记）**16,585** 题（闭式锁定 `KNOWN_ISSUE_COUNT=16585`，见 `tests/data/test_itembank_v2_data.py`）。注意：validate_knowledge 输出的「X/X items dual-agent-verified」计数口径包含单代理登记题，不得据此宣称题库已完成全量双代理验证；双代理补验按签署测试卡 TC-7/TC-8 分批推进（docs/SIGNOFF-2026-10-08.md）。
> 版本：tag `v0.3.0` / `v0.4.0` 在库；HEAD `30bdcf0`（wave3 仲裁 19 条双代理复判收口）。基线实测证据与差距分析见 [docs/GAP-ANALYSIS-2026-10-08.md](docs/GAP-ANALYSIS-2026-10-08.md)；owner 授权签署代理代签的裁定与测试卡见 [docs/SIGNOFF-2026-10-08.md](docs/SIGNOFF-2026-10-08.md)。

## 已知问题

1. **渠道路线已裁定（2026-10-08）**：owner 授权签署代理（opus/alpha）代签 = **A 静态卷文件优先**；本轮不建不部署任何在线渠道；合规五关只产出触发矩阵研究资产（docs/compliance/channel-gates.md），触发条件成立前不办理任何备案。见 docs/SIGNOFF-2026-10-08.md D-1。
2. **双代理验证补齐进行中**：单代理登记题 16,585 道（其中语文无选项开放题 1,846 道单代理 1,832 道）按 TC-7/TC-8 分批双代理复验；disagree 进仲裁队列，只回填 agree。19 条 wave3 仲裁分歧已于 2026-10-06 由 step-5-preview 双代理复判收口（30bdcf0，17 保留/2 改判；题目本身未回填入库）。
3. **多模态真调搁置（D-3 裁定）**：mm 五模块 + 第三波契约均以 mock/离线门控验收；真调冒烟解锁条件 = 运行环境注入 `STEPFUN_API_KEY`（或 `XX_LLM_API_KEY`）且 api.stepfun.com 可达，届时直接 `XX_MM_SMOKE=1 .venv/bin/python -m pytest -k smoke`，无需再签署。
4. **质量扩量已裁定范围（D-4）**：地理 grade9 属年级配置错位（课标/教材不开设，非内容缺口）；生物 grade9 现有 17 题待按课标口径复核；密度加密（6 题/KP）本轮不做。
5. **审计工具已知问题**：`tools/audit_k12_alignment.py` 不识别 `--help`，直接运行会改写 `docs/audits/k12-5_alignment_audit.json`（2026-10-08 实测，已恢复）；其输出与 validate 实况不符，已登记、本轮不修。
