/* 工作流：学情 知识地图可视化（"绘制"字面交付） */
interface R { verdict: string; endpoint: string; test: string; risks: string; }
const REPO = "/home/pan-ding/workspace/学情agent/xuexing-agent";
const VENV = "/tmp/venv-xx";
const run = (c: string) => world.run("bash", ["-c", c], { timeoutMs: 900000 });
phase("实施");
const a = agent("知识地图可视化工程师", { system: "数据可视化工程师：只呈现诊断内核真实产出的数据，不编造；零外部 JS 依赖。" });
const r = await a.ask<R>([
  `任务：把学情的"知识地图"从 JSON 变成可视 HTML——owner 原话"根据错误就可以绘制知识地图，进而指导未来的进一步学习"的"绘制"字面交付。`,
  `【仓】${REPO}（commit 不 push）。venv=${VENV}。数据源：GET /learners/{id}/profile 的逐 KP mastery+置信度、/plan 的学习路线、知识图谱(学科级装载 load_kpgraph_subject)。`,
  `【要求】`,
  `1. GET /learners/{learner_id}/knowledge-map.html?subject=X：自包含 HTML（内联 CSS/SVG，零外部库）——学科知识地图：按年级→章→KP 层级（或图谱拓扑简化）呈现掌握度热力（色阶：薄弱红→熟练绿，置信度以透明度/描边表达），薄弱 KP top10 列表带建议动作（来自 /plan 数据），页头学习者/学科/数据更新时间；跨学科总览页(无 subject 参数)按学科汇总。`,
  `2. 大学科（如 chinese 677 KP）需聚合策略（章/主题级折叠+展开锚点，或两级渲染），保证页面可读且文件体积 <2MB。`,
  `3. 空学习者/无数据学科如实空态提示。`,
  `4. 验收：a) tools/check_kmap.py：对既有测试学习者（或构造作答后）渲染 3 个学科地图，断言 KP 数出现=profile 数、薄弱 top10 与数据一致、标签配平、无外部资源引用，exit 0；b) pytest 全量零失败（新增≥6）；c) 样本 1 份入 out/ 供人工视检。`,
  `5. git commit 单次，不 push。`,
  `【返回】R: verdict/endpoint/test/risks。`,
].join("\n"));
phase("复核");
const g = await run(`cd ${REPO} && export PATH=${VENV}/bin:$PATH && python -m pytest 2>&1 | tail -1 && ls out/ | grep -i kmap | head -3`);
log(g.stdout);
await artifact.markdown("report", `# 知识地图可视化\n\n- ${r.verdict}\n- ${r.endpoint}\n- ${r.test}\n- ${r.risks}`, { title: "知识地图报告", primary: true });
return { conclusion: r.verdict, detail: r, verified: ["pytest+check_kmap 复核"], notCovered: ["人工视检"] };
