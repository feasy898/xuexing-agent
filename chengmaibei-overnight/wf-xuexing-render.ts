/* 工作流：学情 卷面渲染层（家长可理解的成品卷 HTML） */
interface R { verdict: string; outputs: string; test: string; risks: string; }
const REPO = "/home/pan-ding/workspace/学情agent/xuexing-agent";
const VENV = "/tmp/venv-xx";
const run = (c: string) => world.run("bash", ["-c", c], { timeoutMs: 900000 });
phase("渲染层实施");
const a = agent("卷面渲染工程师", { system: "务实的后端工程师；产出物要真实可打印可读；绝不把答案/解析渲染进学生卷。" });
const r = await a.ask<R>([
  `任务：给学情出卷加"成品卷渲染层"——把 POST /papers/by-spec 的结构卷渲染成家长/学校可理解的打印友好 HTML（及纯文本备用）。`,
  ``,
  `【仓】${REPO}（git 工作树，commit 不 push）。venv=${VENV}。现状：/papers/by-spec 返回大题-小题结构（fd66816+8887ccc，9 套卷型可出卷），题面文本在题库 items（stem/options 等，自行探明字段）。`,
  `【要求】`,
  `1. 渲染端点：POST /papers/by-spec 响应加 render（或独立 GET /papers/by-spec/{spec_id}/render.html，二选一，说明理由）；输出自包含 HTML（内联 CSS，A4 打印分页、卷头：卷型标题/总分/时长/满分注意、大题标题"一、选择题（每题3分）"、题面+选择题选项竖排、解答题留答题框、小题号连续、页脚页码）。纯文本版简版。`,
  `2. 红线：答案/解析/评分要点字段绝不渲染（出卷侧）；HTML 转义防注入（题面含 <>&）。`,
  `3. 验收：a) 3 套 OK 卷型渲染出合法 HTML（工具校验：题数=结构数、分值出现次数、无 answer 字段词根、基本标签配平）；b) 渲染样本 1 份存 tests/fixtures 或 out 下供人工视检；c) pytest 全量 ≥801 零失败（新增≥6 测：渲染结构/转义/红线无泄漏/404 等）；d) smoke_api 15/15。`,
  `4. git commit（单次），不 push。`,
  `【返回】R: verdict/outputs(端点+样本路径)/test/risks。`,
].join("\n"));
phase("门禁复核");
const g = await run(`cd ${REPO} && export PATH=${VENV}/bin:$PATH && python -m pytest 2>&1 | tail -1 && python tools/smoke_api.py 2>&1 | tail -1`);
log(g.stdout);
phase("汇总");
await artifact.markdown("report", `# 卷面渲染层\n\n- ${r.verdict}\n- 产物：${r.outputs}\n- 测试：${r.test}\n- 风险：${r.risks}`, { title: "卷面渲染报告", primary: true });
return { conclusion: r.verdict, detail: r, verified: ["全量 pytest+smoke 复核"], notCovered: ["人工视检样本（交付后 owner 可看）"] };
