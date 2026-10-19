# 接续卡 · 学情 agent（xuexing 学情诊断 Agent）

> 迁移日 2026-10-01 ｜ 源 windev-01 D:/workspace/学情agent ｜ 目标 /opt/gpumachine/projects/xuexing-agent

## 当前状态
- git HEAD `a558e08` Wave3-5（2026-09-30，+27 测试）。**无 remote——全部历史只在本地 .git（随迁 2.4M）**。建议接手后立即在 cnb/github 建远端并推送（owner 裁定仓库归属）。
- 工作区不干净是**预期状态**：9 个 M（math_grade7/9 题库、math_all 知识、misconceptions、4 个 data 测试、validate_knowledge.py）+ 26 个 untracked（**math_grade1-6 全套题库/知识/误解数据 + arbitration_queue P12/P34 仲裁队列**）——Wave3-5 之后正在铺 1-6 年级数据，尚未提交。迁移为 tar 全包，**这些活数据已原样带到 GPU 端**。
- GPU 端验证（Python 3.12.13 venv）：`pytest -q` → 13 failed——**与本机逐一相同名单**（dual_verify 5 + misconception_coverage 4 + paper_layout 1 + module_apis 2 + recommend_contract 1），系 Wave3-5 后数据铺装未收口的**项目自身状态，非迁移损失**；3.11 下亦同 13 个。

## 最近做了什么（PM-STATE.md 是断点续作权威依据）
- Wave3 多模态线：d5a5463 mm_client（阶跃四能力）→ 97f328c mm_ingest 拍照录入 → 9350f69 tts_reader 读题 → 159daba asr_answer 口述判分 → a558e08 mm_grade VLM 判分（分步给分规则冻结+人机协同复核闭环）。
- 方法论：原型即 oracle → spec+eval → 契约内重生成（`python tools/run_contract.py`）→ 终版入库。

## 下一步待办
1. 从 PM-STATE.md 恢复上下文；BACKLOG.md P0 队列按序推进。
2. 收口 13 个失败测试（1-6 年级数据与 dual_verify/misconception 快照重新对齐后应转绿）——这正是工作区未提交改动的目的。
3. 把 1-6 年级数据+仲裁队列提交入 git（数据收口后）。
4. 建远端推全量历史。

## 依赖环境（GPU 已装好）
- Python 3.12.13 venv 已建于项目内 `.venv`（fastapi/uvicorn/httpx/pytest 已装，走阿里镜像）。
- 开发基准本机为 Python 3.12.10——GPU 3.12.13 兼容；**不要用系统 python3（3.11）跑本仓**（peidian 同款 f-string 3.12 特性风险）。

## 如何运行
```bash
cd /opt/gpumachine/projects/xuexing-agent
. .venv/bin/activate
python -m pytest -q                  # 全套（当前基线：13 failed 为已知未收口）
python tools/run_contract.py         # 契约测试
python tools/validate_knowledge.py   # 知识库校验
uvicorn xuexing.server:create_app --factory   # 启动 API（需先注入知识库）
```
