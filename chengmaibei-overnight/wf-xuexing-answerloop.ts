/* 工作流：学情 学生作答闭环 三路扇出（意图主环：做完题→绘知识地图） */
interface Cand { approach: string; loop: string; testSummary: string; commit: string; risks: string; }
interface Gate { cand: string; e2eExit: number; pytestExit: number; tail: string; }
interface Judge { ranking: string[]; winner: string; rationale: string; }
const REPO = "/home/pan-ding/workspace/学情agent/xuexing-agent";
const VENV = "/tmp/venv-xx";
const run = (c: string) => world.run("bash", ["-c", c], { timeoutMs: 900000 });
artifact.table("cand", { title: "作答闭环三路对比", key: "cand",
  columns: [{field:"cand",label:"候选"},{field:"approach",label:"方案"},{field:"e2eExit",label:"浏览器环e2e"},{field:"pytestExit",label:"pytest"}] });

phase("准备三路工作区");
await run(`set -e
cd ${REPO} && test -z "$(git status --porcelain)" || { echo DIRTY; exit 9; }
git worktree prune
for c in A B C; do git worktree add --force -B examcand$c /tmp/ex-$c HEAD >/dev/null 2>&1 || true; done
echo ok`);

phase("三路独立实现学生作答闭环");
const card = (c: string) => [
  `你是学情 agent 开发者，独立实现"学生作答闭环"最小 Web 版（候选 ${c} 路）。worktree /tmp/ex-${c}（分支 examcand${c}），venv=${VENV}，禁改主仓/push。`,
  ``,
  `【意图对齐】owner 原话："可以直接出题，学生做完了题目，根据错误就可以绘制知识地图，进而指导未来的进一步学习"。现状：出卷(fd66816)/渲染(f1717a8)/作答 API(/responses)/诊断(/profile)/路线(/plan) 都在，但没有学生能用的作答界面把它们串起来。`,
  `【目标】一个渠道无关的最小作答环（FastAPI 直接伺服，零新依赖，无前端框架——自包含 HTML+原生 JS/form）：`,
  `1. 学生开卷：GET /exam/{spec_id}/start?learner_id=X（可带 seed）→ 会话(内存或复用 jobs 机制)→ 返回可作答卷 HTML（基于既有渲染层改造：选择题 radio、填空 input、解答 textarea，题号 name=item_{no}）；`,
  `2. 提交：POST /exam/{session}/submit（form 或 JSON）→ 客观题即时判分（复用 /grade 口径）→ 落 /responses 等价数据 → 303/链接跳转个人报告页；`,
  `3. 报告页：GET /exam/{session}/report.html → 本次对错逐题 + 知识点掌握更新 + 薄弱点 + 下一步学习建议（消费 /profile、/plan 既有逻辑，页面内联 CSS，家长可读）；`,
  `4. 会话/判分必须复用仓内既有内核（paper_render、grading、diagnosis 的函数），不许另造平行实现。`,
  `【方案空间】会话管理（内存 dict vs 复用多租户 store）、HTML 形态（纯 form 提交 vs fetch+JSON）等自由裁量，取向：最小侵入、与既有契约一致。`,
  `【验收门】`,
  `1. 写 tools/check_exam_loop.py：TestClient 无浏览器全环——start→GET 卷页(断言题数/输入控件数=题数/learner 回显)→构造全对与半错两份作答 submit→断言分数/落库→report 页含对错标记与薄弱知识点；exit 0；`,
  `2. ${VENV}/bin/python -m pytest 全量 ≥819 零失败（新增≥8 测：环各步+404/参数错/会话过期）；`,
  `3. 既有 17 端点零回归（smoke_api 15/15 + 渲染门复跑）；`,
  `4. git commit 单次，不 push。`,
  `【返回】Cand: approach/loop(环路径与页面清单)/testSummary/commit/risks。`,
].join("\n");
const settled = await Promise.allSettled(["A","B","C"].map((c) => agent(`作答闭环-${c}路`).ask<Cand>(card(c))));
const cands = ["A","B","C"];
const results = settled.map((s,i)=> s.status==="fulfilled"? s.value : {approach:"失败",loop:"-",testSummary:"-",commit:"",risks:String(s.reason).slice(0,200)});
for (let i=0;i<3;i++) report({cand:cands[i]!,...results[i]!},"cand");

phase("逐候选取确定性验收");
const gates: Gate[] = [];
for (const c of cands) {
  const g = await run(`cd /tmp/ex-${c} && export PATH=${VENV}/bin:$PATH
python tools/check_exam_loop.py >/tmp/ex-${c}-loop.log 2>&1; echo LOOP_EXIT=$?
tail -2 /tmp/ex-${c}-loop.log
python -m pytest >/tmp/ex-${c}-pt.log 2>&1; echo PYTEST_EXIT=$?
tail -1 /tmp/ex-${c}-pt.log`);
  gates.push({cand:c, e2eExit:/LOOP_EXIT=0/.test(g.stdout)?0:1, pytestExit:/PYTEST_EXIT=0/.test(g.stdout)?0:1, tail:g.stdout.split("\n").slice(-3).join(" ")});
  log(`${c}: loop=${gates[gates.length-1]!.e2eExit} pytest=${gates[gates.length-1]!.pytestExit}`);
}

phase("独立评审");
const j = await agent("作答环评审员",{system:"严格评审。作弊面：判分口径绕过既有 grading、报告页伪造诊断数据、环测试只测 happy path。发现即出局。"}).ask<Judge>(
  `三候选在 /tmp/ex-A|B|C 实现学生作答环。门禁：${JSON.stringify(gates)}；自述：${JSON.stringify(results)}。读三份 diff，按：门全过+复用内核（无平行实现）＞环完整性与失败路径＞页面可读性（学生/家长视角）＞侵入面与测试质量。返回 Judge。`);

phase("汇总");
await artifact.markdown("report", `# 作答闭环三路扇出\n\n| 候选 | 方案 | 环门 | pytest |\n|---|---|---|---|\n${cands.map((c,i)=>`| ${c} | ${results[i]!.approach.slice(0,50)} | ${gates[i]!.e2eExit===0?"绿":"红"} | ${gates[i]!.pytestExit===0?"绿":"红"} |`).join("\n")}\n\n评审：${j.winner} 胜。${j.rationale}`, { title: "作答闭环三路对比", primary: true });
return { conclusion: `胜者=${j.winner}`, winner: j.winner, gates, candidates: results, verified: ["check_exam_loop + 全量 pytest 脚本级门"], notCovered: ["合入与 push 由主会话执行"] };
