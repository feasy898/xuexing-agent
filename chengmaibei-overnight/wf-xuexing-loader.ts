/* 工作流：学情 agent 学科级知识图谱装载器 —— 三路独立实现 + 确定性验收 + 独立评审选优
 * 背景：data/knowledge 下 83 个图谱文件中 71 个因跨年级先序断边无法通过生产装载器
 * load_kpgraph 加载（报 unknown endpoint in edge）。数学已有 math_all.json 学科级合并先例。
 */

interface Candidate {
  /** 实现方案一句话（学科合并装载 / 数据回填 / 装载器放宽等） */
  approach: string;
  /** 改动文件数 */
  filesChanged: number;
  /** 改动行数（约） */
  linesChanged: number;
  /** pytest 结果摘要，如 "767 passed, 2 skipped" */
  pytestSummary: string;
  /** 10 学科装载检查是否全 OK */
  subjectsOk: boolean;
  /** worktree 内提交 hash */
  commit: string;
  /** 风险与备注，一段话 */
  risks: string;
}

interface GateResult {
  /** 候选编号 A/B/C */
  cand: string;
  /** check_subject_load.py 退出码 */
  checkExit: number;
  /** pytest 退出码 */
  pytestExit: number;
  /** pytest 输出末尾几行 */
  pytestTail: string;
}

interface Judgement {
  /** 优选顺序，如 ["B","A","C"] */
  ranking: string[];
  /** 获胜候选编号 */
  winner: string;
  /** 选优理由，三句话以内，含对落选方案的一句话点评 */
  rationale: string;
}

const REPO = "/home/pan-ding/workspace/学情agent/xuexing-agent";
const VENV = "/tmp/venv-xx";
const run = (cmd: string) => world.run("bash", ["-c", cmd], { timeoutMs: 600000 });

artifact.table("cand", {
  title: "三路候选对比",
  key: "cand",
  columns: [
    { field: "cand", label: "候选" },
    { field: "approach", label: "方案" },
    { field: "subjectsOk", label: "学科装载" },
    { field: "pytestSummary", label: "pytest" },
  ],
});

phase("准备三份候选工作区与共享环境");
const prep = await run(
  [
    `set -e`,
    `cd ${REPO}`,
    `test -z "$(git status --porcelain)" || { echo "MAIN_REPO_DIRTY"; git status --porcelain | head -5; exit 9; }`,
    `git worktree prune`,
    `for c in A B C; do git worktree add --force -B cand$c /tmp/xx-$c HEAD >/dev/null 2>&1 || true; done`,
    `if [ ! -x ${VENV}/bin/python ]; then python3 -m venv ${VENV}; fi`,
    `${VENV}/bin/pip install -q -i https://pypi.tuna.tsinghua.edu.cn/simple fastapi uvicorn httpx pytest 2>&1 | tail -1`,
    `cd ${REPO} && ${VENV}/bin/python -m pytest -q > /tmp/xx-baseline.log 2>&1; echo "BASELINE_EXIT=$?"; tail -2 /tmp/xx-baseline.log`,
  ].join("\n"),
);
log("环境就绪。基线测试：\n" + prep.stdout.split("\n").slice(-3).join("\n"));

phase("三路独立实现装载器");
const card = (cand: string) => [
  `你是学情 agent 项目的开发者，独立完成一项装载器任务（候选 ${cand} 路，与其他两路互不可见、方案不必相同）。`,
  ``,
  `【工作区】只在 /tmp/xx-${cand}（仓库 ${REPO} 的 git worktree，分支 cand${cand}）内工作；严禁改动主仓 ${REPO} 本体；严禁 git push；Python 一律用 ${VENV}/bin/python。`,
  ``,
  `【问题】data/knowledge/ 下 83 个知识图谱 json 中 71 个无法通过生产装载器 load_kpgraph（位于 src/xuexing/ 下，自行定位）加载，报 KPGraphError: unknown endpoint in edge——单年级文件的 prereqs 引用了其他年级的知识点（例：chinese_grade2 引用 kp_chi1_tell_story）。数学学科已有 math_all.json 学科级合并文件先例，可参考。`,
  ``,
  `【目标】让全部 10 学科（以 data/knowledge 实际划分为准）的图谱可被生产代码装载并支撑出卷/诊断。方案自由选择或混合，例如：a) 学科目录级合并装载函数（全年级 KP 并集后建图）；b) 修复数据回填断边；c) 装载器允许悬空外部引用并显式收集报告。以最小侵入、不破坏既有行为为准。`,
  ``,
  `【验收门（必须全部满足，并如实自测）】`,
  `1. 新增学科级装载入口（函数名自定，如 load_kpgraph_subject），放置在与 load_kpgraph 同层；`,
  `2. 在 worktree 根写 check_subject_load.py：无参数运行，逐学科调用新入口，打印"学科名: KP数 边数 OK"共 10 行且全 OK，exit 0；`,
  `3. ${VENV}/bin/python -m pytest -q 通过数不低于基线（767 passed 量级）且 0 failed；`,
  `4. tools/validate_knowledge.py 保持 10 学科全 OK（如你增强了它，需自带负向探针：伪造一个缺失端点的文件应能被查出）；`,
  `5. 在 worktree 内 git add 相关文件并 git commit -m "loader: <你的方案一句话>"（单次提交，不含无关文件）。`,
  ``,
  `【纪律】不改 specs/frozen/ 冻结契约；不删测试不弱化断言；不引入第三方依赖（标准库+现有依赖）；若验收门客观无法达成，直接如实说明并提交最接近的成果，不许伪造通过。`,
  ``,
  `【返回】按 Candidate 结构返回：approach/filesChanged/linesChanged/pytestSummary/subjectsOk/commit(完整hash)/risks。`,
].join("\n");

const settled = await Promise.allSettled(
  ["A", "B", "C"].map((c) => agent(`装载器实现-${c}路`).ask<Candidate>(card(c))),
);
const results: Candidate[] = settled.map((s, i) =>
  s.status === "fulfilled"
    ? { cand: ["A", "B", "C"][i], ...s.value }
    : {
        approach: "该路代理失败",
        filesChanged: 0,
        linesChanged: 0,
        pytestSummary: "n/a",
        subjectsOk: false,
        commit: "",
        risks: String(s.reason).slice(0, 300),
      },
);
const cands = ["A", "B", "C"];
for (let i = 0; i < 3; i++) report({ cand: cands[i], ...results[i] }, "cand");
log("三路实现收束：" + results.map((r) => r.approach).join(" | "));

phase("逐候选取确定性验收");
const gates: GateResult[] = [];
for (const c of cands) {
  const g = await run(
    [
      `cd /tmp/xx-${c}`,
      `${VENV}/bin/python check_subject_load.py > /tmp/xx-${c}-check.log 2>&1; echo "CHECK_EXIT=$?"`,
      `tail -3 /tmp/xx-${c}-check.log`,
      `${VENV}/bin/python -m pytest -q > /tmp/xx-${c}-pytest.log 2>&1; echo "PYTEST_EXIT=$?"`,
      `tail -3 /tmp/xx-${c}-pytest.log`,
    ].join("\n"),
  );
  gates.push({
    cand: c,
    checkExit: /CHECK_EXIT=0/.test(g.stdout) ? 0 : 1,
    pytestExit: /PYTEST_EXIT=0/.test(g.stdout) ? 0 : 1,
    pytestTail: g.stdout.split("\n").slice(-4).join(" "),
  });
  log(`候选 ${c} 确定性验收：check=${gates[gates.length - 1]?.checkExit} pytest=${gates[gates.length - 1]?.pytestExit}`);
}

phase("独立评审三个候选");
const judge = agent("装载器评审员", {
  system:
    "你是严格的代码评审员，只依据证据判断，不迎合任何一方。若发现候选伪造验收（声称通过但门未过），直接点破。无法决出唯一胜者时如实说明并列出权衡。",
});
const judgement = await judge.ask<Judgement>(
  [
    `三个候选各自在 /tmp/xx-A、/tmp/xx-B、/tmp/xx-C（分支 candA/B/C，基于同一 HEAD 各一次提交）独立实现了"学情 agent 学科级知识图谱装载器"。`,
    `确定性验收结果（脚本实测，非代理自述）：${JSON.stringify(gates)}`,
    `候选自述：${JSON.stringify(results)}`,
    ``,
    `请你：1) 逐个读三个 worktree 的完整 diff（git -C /tmp/xx-X diff HEAD~1 HEAD）与关键源码；2) 核对自述与 diff 是否一致；3) 按以下标准排序：验收门全过（硬性，未过者出局）＞ 不破坏冻结契约与既有行为（767 基线）＞ 方案通用性（学科无关、未来新增年级文件自动兼容、不靠手写枚举）＞ 侵入面与代码/测试质量。`,
    `不要修改任何文件，不要运行 git push。返回 Judgement：ranking（优选顺序）/winner/rationale（含对落选方案的一句话点评）.`,
  ].join("\n"),
);

phase("汇总产出对比报告");
const stat = await run(
  cands.map((c) => `echo "== cand${c} =="; git -C /tmp/xx-${c} show --stat --oneline HEAD 2>/dev/null | head -8`).join("\n"),
);
const tableMd = [
  `# 学情装载器三路扇出对比`,
  ``,
  `| 候选 | 方案 | 学科装载 | pytest | 改动 |`,
  `|---|---|---|---|---|`,
  ...results.map((r, i) => `| ${cands[i]} | ${r.approach} | ${r.subjectsOk ? "OK" : "FAIL"} | ${r.pytestSummary} | ${r.filesChanged}文件/${r.linesChanged}行 |`),
  ``,
  `## 确定性验收`,
  ...gates.map((g) => `- 候选${g.cand}: check_exit=${g.checkExit} pytest_exit=${g.pytestExit} ${g.pytestTail}`),
  ``,
  `## 评审结论`,
  `优选顺序：${judgement.ranking.join(" > ")}；胜者：${judgement.winner}`,
  judgement.rationale,
  ``,
  `## 各候选提交明细`,
  "```",
  stat.stdout,
  "```",
].join("\n");
await artifact.markdown("report", tableMd, {
  title: "学情装载器三路对比报告",
  description: "三路独立实现、确定性验收与评审选优的完整记录",
  primary: true,
});

return {
  conclusion: `三路扇出完成，评审胜者=候选${judgement.winner}。${judgement.rationale}`,
  winner: judgement.winner,
  ranking: judgement.ranking,
  gates,
  candidates: results,
  baseline: prep.stdout.split("\n").slice(-3).join(" "),
  verified: ["每候选取 check_subject_load.py 与全量 pytest 的脚本级退出码", "评审员独立读取三份完整 diff"],
  notCovered: ["胜者合入主仓与最终推送由主会话执行"],
};
