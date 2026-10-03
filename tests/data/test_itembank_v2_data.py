"""数据测试：题库 schema v2 × 真实题库（data/items/ 侧闭环）。

口径与 tools/validate_knowledge.py 一致（合并 data/items/*.json 全部题目）：
- 全库通过 v2 完整性门（source 枚举 / 改编溯源 / LLM 验证记录）——唯一例外
  是 2026-10-03 物理/化学扩科批的「单代理自验」known issue（1837 题，
  verification.agents 如实记单元素 ['phy-gen-w1-20261003'] /
  ['che-gen-w1-20261003']，配 single_agent=true 抑制 C1 的 >=2 agents 要求，
  逐题带 note 申报；这是 K12-3 题库建设期已知合法形态），按登记批次收口：
  单代理通道只属于登记批次（缺口题集锁定，不得漂移、不得新增），批次外不得
  使用 single_agent 标记；独立盲解通道跑完并回填 [gen, indep] 后撤销该收口；
- 来源闭式：初中 321 题为 M3 知识注入的原创题（commit ab541ec，source=original）；
  2026-09-30 落库的小学中段 94 题（p3_*/p4_*）为 step-3.7-flash 起草、人工逐题
  验算修正的 LLM 生成题（source=llm_generated，verification 由 2026-09-30 双代理
  运行回填，可追溯性由 tests/data/test_dual_verify_data.py 强制）；无改编题
  （引入改编题时须附真实 source_ref 并更新此闭式）；
- 验证记录：三次双代理运行回填 321+94+96 全库（低段 1-2 年级 96 题见
  2026-09-30 p12 运行）；此处只锁「记录存在且通过 v2 门」（单代理自验批按
  登记口径以 single_agent=true 计入 verified，缺口由 note 申报 + 批次登记收口）；
- 算术闭式抽查：12 题按 id 逐一独立重算（表达式在测试内现算，非抄答案）。
"""
import glob
import json
import os

import pytest

from test_dual_verify_data import CHE_AGENTS, PHY_AGENTS
from xuexing.itembank_v2 import validate_bank_v2, source_counts, verification_stats

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ITEM_FILES = sorted(glob.glob(os.path.join(ROOT, "data", "items", "*.json")))

MIN_TOTAL_ITEMS = 300  # 规模下限（只防清空/截断，不锁增长）
EXPECTED_LLM_GENERATED = 94  # 小学 LLM 生成题下限（本批次 3-4 年级 94 题；其他小学批次另计）

# 已知缺口（known issue）收口登记：物理 860 + 化学 977 = 1837 题（phy G8-12 /
# che G9-12；批内去重 phy 866→860、che 999→977，跨批双落 che_hs2_0143 与
# phy_phyjr_0407 整题重复已移除化学侧）。批次身份以
# tests/data/test_dual_verify_data.py 的登记常量为单一事实源；题内
# verification.note 必须逐题如实申报，缺申报即失败。
KNOWN_ISSUE_AGENTS = (PHY_AGENTS, CHE_AGENTS)
KNOWN_ISSUE_COUNT = 860 + 977  # phy 860（G8-12 dedup 后）+ che 977（G9-12 dedup 后）
# 题内实际申报串 = 盲解延期申报 + 转单元素如实记录时追加的「single-agent
# generation」标注（2026-10-03 落库形态，逐题一致）
DEFERRED_NOTE = ("single-agent generation, blind verification deferred"
                 " | single-agent generation")

# 已知单代理批次：单元素 agents 是 PHY_AGENTS[0] 或 CHE_AGENTS[0]
KNOWN_SINGLE_AGENT_IDS = {PHY_AGENTS[0], CHE_AGENTS[0]}


def _known_issue_ids(items):
    """登记内已知缺口题集：verification.agents 为单元素且等于登记的代理 id。"""
    return {
        it["id"] for it in items
        if tuple(it.get("verification", {}).get("agents", [])) in {(a,) for a in KNOWN_SINGLE_AGENT_IDS}
    }


@pytest.fixture(scope="module")
def all_items():
    assert ITEM_FILES, "no item files found under data/items/"
    items = []
    for path in ITEM_FILES:
        with open(path, encoding="utf-8") as f:
            items.extend(json.load(f)["items"])
    return items


def test_real_bank_passes_v2_gate(all_items):
    assert len(all_items) >= MIN_TOTAL_ITEMS
    # known-issue 批次（单代理自验）之外 v2 门必须零违规（fail-closed：新批次
    # 再出现任何违规——含新的同名重复代理——都直接失败）
    known = _known_issue_ids(all_items)
    rest = [it for it in all_items if it["id"] not in known]
    errs = validate_bank_v2(rest)
    assert errs == [], f"schema v2 violations outside known issue: {errs[:10]}"


def test_single_agent_known_issue_scope_closed(all_items):
    """known-issue 收口闭式：单代理题集恰为登记的 phy/che 批（phy 860 +
    che 977 = 1837，agents 单元素 + single_agent=true），题集不得漂移；全库
    v2 门零违规（登记批以 single_agent=true 抑制 C1 的 >=2 agents 要求）；
    缺口题必须逐题带申报 note 且确实带标记；批次之外不得使用 single_agent
    通道。独立盲解回填 [gen, indep] 后本豁免撤销、恢复全量双代理口径。"""
    known = _known_issue_ids(all_items)
    assert len(known) == KNOWN_ISSUE_COUNT, (
        "known-issue 批次规模变化：扩库/移除/独立盲解回填后须同步 KNOWN_ISSUE_COUNT")
    # 全库零违规：登记批以 single_agent=true 通过 C1，因此任何 "needs >=2
    # agents" / duplicate-agent 违规都意味着**未登记**的单代理落库 → 直接失败
    errs = validate_bank_v2(all_items)
    assert errs == [], f"schema v2 violations (unregistered single-agent or other): {errs[:10]}"
    by_id = {it["id"]: it for it in all_items}
    undeclared = [iid for iid in known
                  if by_id[iid].get("verification", {}).get("note") != DEFERRED_NOTE
                  or by_id[iid].get("verification", {}).get("single_agent") is not True]
    assert undeclared == [], (
        f"单代理自验未逐题申报（note={DEFERRED_NOTE!r} + single_agent=true）: "
        f"{undeclared[:10]}")
    # fail-closed：single_agent 通道只属于登记批次，批次外出现标记即失败
    flagged_outside = [it["id"] for it in all_items
                       if (it.get("verification") or {}).get("single_agent")
                       and it["id"] not in known]
    assert flagged_outside == [], (
        f"登记批次外出现 single_agent 标记: {flagged_outside[:10]}")


def test_real_provenance_original_plus_verified_llm(all_items):
    counts = source_counts(all_items)
    assert counts["adapted"] == 0, "改编题入库须附真实 source_ref 并更新本断言"
    assert counts["llm_generated"] >= EXPECTED_LLM_GENERATED, (
        "小学 LLM 生成题（须附双代理 verification）出现缺口")
    # 全部 llm_generated 题必须带通过记录（v2 门已强制，这里显式复核覆盖数；
    # 单代理自验批按登记口径（single_agent=true）同样计入 verified）
    total, verified = verification_stats(all_items)
    assert total == len(all_items) and verified == total
    assert counts["original"] == len(all_items) - counts["llm_generated"]


def test_real_verification_records_honest(all_items):
    total, verified = verification_stats(all_items)
    assert total == len(all_items)
    # 2026-09-29 双代理运行回填后：全库带通过记录；记录真实性（ledger/manifest
    # 逐题可追溯、非伪造）由 test_dual_verify_data.py 独立强制。
    # 物理/化学单代理自验批（1837 题，agents 单元素 + single_agent=true +
    # 逐题 note 申报）是 K12-3 题库建设期已知合法形态，按登记口径计入
    # verified（verification_stats 判定 = C1..C4 零消息，single_agent 抑制
    # C1 的 >=2 agents 要求）；批次收口（不得漂移、批次外禁用该通道）由
    # test_single_agent_known_issue_scope_closed 强制，待独立盲解回填
    # [gen, indep] 后仍保持 verified == total。
    assert verified == total, (
        "验证覆盖缺口：登记批次外出现未通过题，或登记批记录形态漂移"
        "（缺 single_agent/note 申报）；扩库或回填后须同步本断言"
    )


def test_real_closed_form_spot_checks(all_items):
    by_id = {it["id"]: it for it in all_items}
    # (id, 现算表达式) —— 独立重算，与库内 answer 逐字比对
    checks = [
        ("m7_010", str((-3) + 5)),                      # (-3)+5
        ("m7_019", str(-(2**2) + (-3) * 2)),            # -2²+(-3)×2（先乘方后取负）
        ("m7_040", str(25 + 15 / 60)),                  # 25°15′ = 25.25°
        ("m8_4", str(90 - 35)),                         # 直角三角形锐角互余
        ("m8_5", str(50 + 60)),                         # 外角 = 不相邻两内角之和
        ("m8_24", str(-4 + 3)),                         # 关于 y 轴对称：a=-4, b=3
        ("m8_25", str(9 * 2 + 4)),                      # 腰=9（4+4<9 不成三角形）
        ("m9_5", str(1 + (6 // 2) ** 2)),               # x²+6x=1 → (x+3)²=1+9
        ("m9_7", str(2**2 - 4 * 1 * (-3))),             # Δ = b²-4ac
        ("m9_14", str(2 + 5)),                          # x₁x₂+x₁+x₂ = 2+5
        ("m9_15", str(3**2 - 2 * (-2))),                # α²+β² = (α+β)²-2αβ
        ("m9_20", str(2)),                              # m²-m=2 且 m≠-1
    ]
    missing = [iid for iid, _ in checks if iid not in by_id]
    assert missing == [], f"抽查题不在库中: {missing}"
    assert 4 + 4 < 9  # m8_25 的腰只能是 9 的前提（三角形不等式）
    for iid, expected in checks:
        assert by_id[iid]["answer"] == expected, f"{iid}: {by_id[iid]['answer']!r} != {expected!r}"
