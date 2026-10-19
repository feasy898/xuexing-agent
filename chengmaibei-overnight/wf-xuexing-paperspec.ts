/* 工作流：学情 卷型库接入出卷 三路扇出 */
interface Cand { approach: string; endpoint: string; testSummary: string; commit: string; risks: string; }
interface Gate { cand: string; specExit: number; pytestExit: number; tail: string; }
interface Judge { ranking: string[]; winner: string; rationale: string; }
const REPO = "/home/pan-ding/workspace/学情agent/xuexing-agent";
const VENV = "/tmp/venv-xx";
const run = (c: string) => world.run("bash", ["-c", c], { timeoutMs: 900000 });
artifact.table("cand", { title: "卷型接入三路对比", key: "cand",
  columns: [{field:"cand",label:"候选"},{field:"approach",label:"方案"},{field:"specExit",label:"卷型出卷门"},{field:"pytestExit",label:"pytest"}] });

phase("准备三路工作区");
await run(`set -e
cd ${REPO} && test -z "$(git status --porcelain)" || { echo DIRTY; exit 9; }
git worktree prune
for c in A B C; do git worktree add --force -B pscand$c /tmp/ps-$c HEAD >/dev/null 2>&1 || true; done
echo ok`);

phase("三路独立实现卷型出卷");
const card = (c: string) => [
  `你是学情 agent 开发者，独立实现"卷型库驱动的出卷"（候选 ${c} 路）。工作区 /tmp/ps-${c}（分支 pscand${c}），Python 用 ${VENV}/bin/python，严禁改主仓/push。`,
  ``,
  `【背景】data/paper_specs/（或 data/ 下，自行定位）有 21 套卷型（大题结构/分值/题型/时长，海南为默认 profile）——owner 明令"以卷子生成为核心（符合学校惯例、家长可理解）"，但当前 /papers/diagnostic 端点只按 blueprint 计数出题，卷型数据零消费（src/tools/tests 无一引用 paper_specs）。`,
  `【目标】新增端点 POST /papers/by-spec：入参 spec_id（+learner_id/难度等可选），按卷型的阶段/题型/分值/知识点范围约束选题组卷；输出试卷结构含大题-小题层级、分值合计=卷型总分、时长；html/文本渲染可后置。`,
  `【方案空间】选题策略自由（如：按卷型各阶段从题库按知识点分布+难度抽题，保分值精确凑整），但必须：分值结构逐大题与 spec 一致；题目来自既有题库；无合适题时如实报缺（fail-closed，不用别题型凑数充绿）。`,
  `【验收门】`,
  `1. 对至少 3 套真实卷型（含海南 profile 的）出卷：大题数/各题型数量/分值合计逐项==spec，exit 0；写 tools/check_paper_spec.py（无参跑全部卷型出卷并断言结构，作为确定性门）；`,
  `2. ${VENV}/bin/python -m pytest 全量不低于基线(776) 零失败；`,
  `3. 新增 API 测试（server 测试风格沿用）；既有端点零回归；`,
  `4. git commit -m "papers: <方案一句话>"，不 push。`,
  `【返回】Cand: approach/endpoint(路由与方法)/testSummary/commit/risks。`,
].join("\n");
const settled = await Promise.allSettled(["A","B","C"].map((c) => agent(`卷型实现-${c}路`).ask<Cand>(card(c))));
const cands = ["A","B","C"];
const results = settled.map((s,i)=> s.status==="fulfilled"? s.value : {approach:"失败",endpoint:"-",testSummary:"-",commit:"",risks:String(s.reason).slice(0,200)});
for (let i=0;i<3;i++) report({cand:cands[i]!,...results[i]!},"cand");

phase("逐候选取确定性验收");
const gates: Gate[] = [];
for (const c of cands) {
  const g = await run(`cd /tmp/ps-${c} && export PATH=${VENV}/bin:$PATH
python tools/check_paper_spec.py >/tmp/ps-${c}-chk.log 2>&1; echo SPEC_EXIT=$?
tail -2 /tmp/ps-${c}-chk.log
python -m pytest >/tmp/ps-${c}-pt.log 2>&1; echo PYTEST_EXIT=$?
tail -1 /tmp/ps-${c}-pt.log`);
  gates.push({cand:c, specExit:/SPEC_EXIT=0/.test(g.stdout)?0:1, pytestExit:/PYTEST_EXIT=0/.test(g.stdout)?0:1, tail:g.stdout.split("\n").slice(-3).join(" ")});
  log(`${c}: spec=${gates[gates.length-1]!.specExit} pytest=${gates[gates.length-1]!.pytestExit}`);
}

phase("独立评审");
const j = await agent("卷型评审员",{system:"严格评审，防作弊（改 spec 数据凑绿/跳过缺题不算失败/硬编码 spec_id 均不合格）。"}).ask<Judge>(
  `三候选在 /tmp/ps-A|B|C（分支 pscandA/B/C）实现了卷型出卷。门禁：${JSON.stringify(gates)}；自述：${JSON.stringify(results)}。读三份完整 diff（git -C /tmp/ps-X diff HEAD~1 HEAD），按：门全过＞结构精确性与fail-closed＞选题策略合理性（知识点覆盖/难度分布）＞侵入面与测试质量 排序。返回 Judge。`);
await run(cands.map(c=>`git -C /tmp/ps-${c} show --stat --oneline HEAD | head -6`).join("\n"));
phase("汇总");
await artifact.markdown("report", `# 卷型出卷三路扇出\n\n| 候选 | 方案 | spec门 | pytest |\n|---|---|---|---|\n${cands.map((c,i)=>`| ${c} | ${results[i]!.approach} | ${gates[i]!.specExit===0?"绿":"红"} | ${gates[i]!.pytestExit===0?"绿":"红"} |`).join("\n")}\n\n评审：${j.winner} 胜。${j.rationale}`, { title: "卷型出卷三路对比", primary: true });
return { conclusion: `胜者=${j.winner}`, winner: j.winner, gates, candidates: results, verified: ["check_paper_spec.py 与全量 pytest 脚本级门"], notCovered: ["合入与 push 由主会话执行"] };
