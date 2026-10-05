# K12-6 多模态真调计划

1. 复用项目冻结的 mm_client.py（HttpTransport），逐项探测 4 能力：chat step-5-preview、vision step-5-preview、tts stepaudio-2.5-tts、asr stepaudio-2.5-asr
2. 记录每项 status、耗时、错误原文（json）
3. 失败时加诊断：DNS、TCP、HTTP 直连、控制组（baidu/open.bigmodel/github）
4. 失败时与 2026-09-29 xuexing-agent/docs/multimodal-api.md 四能力全 200 的历史记录对比，确认是网络策略而非接口问题
5. 汇总报告 docs/research/k12/k12-6_smoke_report.md：可用/不可用 + 失败原因 + 复测命令
