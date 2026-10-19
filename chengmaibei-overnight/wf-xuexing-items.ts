/* 工作流：学情 题库缺口补题（打通 12 套 SKIP 卷型） */
interface R { verdict: string; added: string; gateGain: string; test: string; risks: string; }
const REPO = "/home/pan-ding/workspace/学情agent/xuexing-agent";
const VENV = "/tmp/venv-xx";
const run = (c: string) => world.run("bash", ["-c", c], { timeoutMs: 900000 });
phase("补题实施");
const a = agent("题库补给工程师", { system: "严谨的题库工程师：质量优先于数量；每题过结构校验+去重+答案自洽；诚实标注生成性质；绝不虚报 verified 状态。" });
const r = await a.ask<R>([
  `任务：定向补齐题库缺口，把 12 套 SKIP 卷型尽可能转为可出卷（目标 ≥6 套转 OK）。`,
  ``,
  `【仓】${REPO}（commit 不 push）。venv=${VENV}。LLM：eval "$(/home/pan-ding/workspace/agent-tools/llm-env zhipu)"（glm-4-flash，OpenAI 兼容），key 不回显。`,
  `【缺口清单】（check_paper_spec.py 的 FAIL-CLOSED 输出为权威）：math_primary/math_jr 填空 0、math_hs 多选 0、eng_hs 七选五缺 4、bio_hs 与 geo_hs solve 0、chi_jr/chi_hs 填空族 0、eng_jr 听力差 3、bio_jr cloze 0、pol_primary 连线 0、sci_prim 实验 0。另修一处数据伤：che_jr_0110 题干自带答案（改写题干）。`,
  `【补题纪律】`,
  `1. 每类先生成再校验：JSON 结构与既有 items 完全同构（字段/枚举/难度域）、kp 挂到同学科同学段真实 KP id（从图谱取）、答案自洽（数学题程序验算或公式复核；选择题干扰项合理性抽查）、与既有题库去重（题干 n-gram≥0.8 视为重复丢弃）；`,
  `2. verification 字段如实：source=llm-generated、single_agent=true、dual_agent=false（不虚标）；难度初值可标记 estimated；`,
  `3. 数量克制：每缺口类型补足到"该卷型需求量×2"即可（总量 ≤300 题），听力/连线类 LLM 难出好的可少补并如实说明；`,
  `4. 对齐课标：内容范围参考 docs/research/k12/ 对应学科文档的年级章节表。`,
  `【验收】`,
  `1. check_paper_spec.py：OK 套数 9→目标≥15（若听力类补不动如实报告卡点）；FAIL-CLOSED 仅剩真实难补类；`,
  `2. validate_knowledge.py 10 学科仍 OK；pytest 全量零失败；smoke 15/15；`,
  `3. 新增 items 的抽检报告（每类型抽 3 题人工可读题面+答案合理性附在 commit message 或 worklog）；`,
  `4. git commit 单次，不 push。`,
  `【返回】R: verdict/added(逐类型补题数+丢弃数)/gateGain(OK 套数变化)/test/risks。`,
].join("\n"));
phase("复核");
const g = await run(`cd ${REPO} && export PATH=${VENV}/bin:$PATH && python tools/check_paper_spec.py 2>&1 | tail -2 && python -m pytest 2>&1 | tail -1`);
log(g.stdout);
await artifact.markdown("report", `# 题库补齐\n\n- ${r.verdict}\n- 补题：${r.added}\n- 卷型：${r.gateGain}\n- ${r.risks}`, { title: "补题报告", primary: true });
return { conclusion: r.verdict, detail: r, verified: ["check_paper_spec+pytest 复核"], notCovered: ["人工复核抽检报告"] };
