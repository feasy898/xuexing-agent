## 2026-10-19 第二批(清理前抢救)

随 stray-copies-20261019 第二次提交追加:

### gpu-handover/(原位于 anolis-gpu-01:/opt/gpumachine/,已整目录删除)
- projects/continue-cards/xuexing-agent.md —— 2026-10-01 windev-01→GPU 迁移接续卡
- handover/xuexing-scan{,-rescan}/ —— 迁移前凭证/大文件/内网命中扫描报告
- handover/assemble/rules-xuexing.txt —— 组装规则
- handover/agentic-factory-projects/xuexing-agent/ —— 无 .git 的工作快照(math g1-g9 数据等)
- factory-tests/tests/cases/L4-02-xuexing-agent.sh —— GPU 验收脚本
  (governance-machine:/opt/factory-tests/ 下有逐字节相同副本,一并删除)

### factory-tests-golden/(原位于 governance-machine:/opt/factory-tests/,已删除)
- tests/golden/cases/GC-SW-02-xuexing-blind-regen.yaml —— 盲重生成 golden 用例

### chengmaibei-overnight/(原位于 本机 workspace/澄迈杯/AGENTS/overnight-20261005/,已删除)
- wf-xuexing-{loader,items,kmap,paperspec,answerloop,render}.ts —— 学情工作流脚本

### GPU 独立开发线(分支归档,非本分支内容)
与本地 main 无共同祖先的并行历史,已按 refs 原样推为归档分支:
- archive/gpu-projects-main(6f59b5a)、archive/gpu-projects-handover-snapshot(2ad8719)
- archive/gpu-work-main(2983280)、archive/gpu-work-handover-snapshot(0a0b5d5)
- tags:gpu-proj/v0.1.0、gpu-proj/v0.2.0、gpu-work/v0.1.0、gpu-work/v0.2.0
