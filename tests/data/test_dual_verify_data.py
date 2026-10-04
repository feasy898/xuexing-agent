"""数据测试：双代理独立复验运行 × 真实题库（BACKLOG「双代理独立复验题库」数据闭环）。

锁定三次真实运行的可追溯事实（内核均为 xuexing.dual_verify）：
- 2026-09-29 run（tools/dual_agent_verify.py，7-9 年级库 321 题）：
  m3-reviewer(key) × night-reverify-20260929(ledger)，manifest/ledger/队列见
  data/verification/ 原文件；
- 2026-09-30 run（_research_tmp/p34_dual_verify.py，同口径两通道，3-4 年级库 94 题）：
  p34-reviewer(key) × recheck-20260930(ledger)，独立落盘 verify_manifest_p34.json /
  ledger_p34_20260930.json / arbitration_queue_p34.json（不覆盖 7-9 存量清单）；
- 2026-09-30 run（_research_tmp/finalize_p12.py，同口径两通道，小学低段 1-2 年级
  库 96 题）：p12-editor-20260930(key) × step-p12-blind-20260930(ledger)，
  独立落盘 verify_manifest_p12_20260930.json / ledger_p12_blind_20260930.json /
  arbitration_queue_p12_20260930.json。
- 2026-09-30 deepen/扩库批 ×4（无独立 ledger/manifest：LLM 起草 + 人工逐题
  验算修正后复核，证据在 _research_tmp/g7_build_items.py 头部修正清单 /
  g7_review.txt、_research_tmp/m9_build.py 与 p5*/p6* 生成产物）：
  七年级 +93 题（m7_130..222，step-3.7-flash × g7-deepen-review-20260930）、
  九年级 +105 题（m9_106..210，step-3.7-flash × m9-deepen-review-20260930）、
  五年级 +50 题（47 llm_generated × p5-reviewer-20260930 + 3 original ×
  p56-author-20260930/p56-reverify-20260930）、六年级 +51 题（48 llm_generated
  × p6-reviewer-20260930 + 3 original × 同 p56 对），均 source=llm_generated
  或 original、题内 verification 记录 answers_agree=True；可追溯性由
  test_verification_agents_match_owning_run 按批次登记表强制（未登记批次的
  代理身份会直接失败，fail-closed）。
  注：data/verification/ledger_m8deep_blind_20260930.json 是八年级深挖批
  （m8_101..187，87 题）的盲解台账，该批题目尚未落库——它是无主产物，
  不构成本库运行，待八年级深挖批落库时再按本文件口径登记。
- 2026-10-02 run（D 阶段第三波扩库批，G1-6 每 KP 补至 >=6 + G8 全补，候选 320
  题经 MiniMax-M3 生成自答 × step-5-preview 盲解双代理复验，agree 301 题合并；
  19 题分歧入 arbitration_queue_wave3.json 未回填；3 题跨年级题干重复被移除并
  由补题批 m8_171..173 替换）：代理对 m3-gen-wave3-20261002 ×
  step5-indep-wave3-20261002，合并台账 ledger_m3_gen_wave3.json /
  ledger_step5_indep_wave3.json；题内 verification 记录即为覆盖凭证，
  由 WAVE3_AGENTS 圈定并在并集检查与代理登记中强制。
- 2026-10-03 run（K12 英语题库批，G1-12 全学段 12 个年级文件，生成自答 ×
  盲解双代理复验，agree 425 题合并入库；252 题分歧入 arbitration_queue_en.json
  未回填）：代理对 eng-gen-w1-20261003 × eng-indep-w1-20261003，题内
  verification 记录即为覆盖凭证，由 ENG_AGENTS 圈定（前缀 eng_）并在并集
  检查与代理登记中强制。
- 2026-10-03 扩科批 ×3（语文/物理/化学，无独立 ledger/manifest，题内
  verification 记录即为覆盖凭证）：语文 30 题（chi-gen-w1-20261003 ×
  chi-indep-w1-20261003 双代理 agree 合并；入库时 chi_hs_0198 曾在同一文件
  重复落库一条，2026-10-03 测试台账修复时去重，闭式按 30 锁定）；物理 860 题
  （G8-12）、化学 977 题（G9-12）为 **known issue：单代理自验入库**——
  实际只有生成自答一个代理，verification.agents 如实记单元素
  ['phy-gen-w1-20261003'] / ['che-gen-w1-20261003'] 并配 single_agent=true
  与逐题 note 申报（K12-3 题库建设期已知合法形态），独立盲解通道
  （phy-indep-w1 / che-indep-w1）尚未运行；由
  tests/data/test_itembank_v2_data.py 以登记批次口径收口，独立复验跑完后
  按 [gen, indep] 回填并撤销该收口。本批入库事故于 2026-10-03 测试台账
  修复时处理：chi_hs_0198（语文批同文件真重复 id，去重一条，chi 闭式 31→30）、
  che_hs2_0143（化学批与物理批 phy_phyjr_0407 整题重复的跨学科双落，移除
  化学侧）及批内去重（phy 866→860、che 999→977，现共 1837）。
- 2026-10-04 密度收尾批 ×3（单代理自验 known issue，题内 verification 记录
  即为覆盖凭证）：数学 45 题（h_sdf 等 15 个 KP 号段 ×3，入数学 g10-12 文件，
  签名 mat-gen-w1-20261003，h_ 新号段与高中批共段、按代理签名区分）；政治
  61 题（45 pol_FINAL_* + 13 pol_jr_* + 3 pol_hs_*，g8-11）；历史 11 题
  （h_duj/ajv/edu 9 题 + his_jr_0469/0489，g7/g8）。注意：政治/历史收尾批的
  candidates 台账（GEN_POL_FINAL/GEN_HIS_FINAL_ledger_gen.json）记的生成代理
  是 pol-density-gen-20261004 / his-gen-w1-20261004，但统一入库脚本
  work/merge_subject_safe.py 按 {学科}-gen-w1-20261003 签名落库——题库内三批
  实际签名均为 *-gen-w1-20261003，POL_DENSITY_AGENTS/HIS_DENSITY_AGENTS 按
  台账口径登记（库内现匹配 0 题，独立盲解回填若改用新 id 须同步本闭式）。

三次 ledger 运行各自验证：ledger 逐题覆盖其子库且与标答判等；manifest 与
现场重跑裁决逐位一致；回填记录 agents 与 manifest 代理身份一致、
verified == total；仲裁队列为空。另做全库并集检查：data/items/ 每题恰被
一次 ledger 运行或一个 deepen/扩库批覆盖，且题内 verification.agents 与
所属批次一致。ledger 抽查为测试内现算重推（非抄串）。
"""
import glob
import json
import os

import pytest

from xuexing.dual_verify import answers_match, arbitration_rows, verify_bank

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
VERIFICATION_DIR = os.path.join(ROOT, "data", "verification")

NIGHT_ITEM_FILES = sorted(
    os.path.join(ROOT, "data", "items", f"math_grade{g}_items.json") for g in (7, 8, 9))
P34_ITEM_FILES = sorted(
    os.path.join(ROOT, "data", "items", f"math_grade{g}_items.json") for g in (3, 4))
P12_ITEM_FILES = sorted(
    os.path.join(ROOT, "data", "items", f"math_grade{g}_items.json") for g in (1, 2))
ALL_ITEM_FILES = sorted(glob.glob(os.path.join(ROOT, "data", "items", "*.json")))

LEDGER_PATH = os.path.join(VERIFICATION_DIR, "ledger_night_20260929.json")
MANIFEST_PATH = os.path.join(VERIFICATION_DIR, "verify_manifest.json")
QUEUE_PATH = os.path.join(VERIFICATION_DIR, "arbitration_queue.json")
P34_LEDGER_PATH = os.path.join(VERIFICATION_DIR, "ledger_p34_20260930.json")
P34_MANIFEST_PATH = os.path.join(VERIFICATION_DIR, "verify_manifest_p34.json")
P34_QUEUE_PATH = os.path.join(VERIFICATION_DIR, "arbitration_queue_p34.json")
P12_LEDGER_PATH = os.path.join(VERIFICATION_DIR, "ledger_p12_blind_20260930.json")
P12_MANIFEST_PATH = os.path.join(VERIFICATION_DIR, "verify_manifest_p12_20260930.json")
P12_QUEUE_PATH = os.path.join(VERIFICATION_DIR, "arbitration_queue_p12_20260930.json")

NIGHT_AGENTS = ["m3-reviewer", "night-reverify-20260929"]
P34_AGENTS = ["p34-reviewer", "recheck-20260930"]
P12_AGENTS = ["p12-editor-20260930", "step-p12-blind-20260930"]
# 2026-10-02 D 阶段第三波扩库批（G1-6 每 KP 补至 >=6 + G8 全补；agree 合并 301 题）：
# m3-gen-wave3-20261002(生成自答) × step5-indep-wave3-20261002(盲解)，代理对落库
# 原序一致；台账 ledger_m3_gen_wave3.json / ledger_step5_indep_wave3.json，
# 分歧 19 条入 arbitration_queue_wave3.json 未回填（含补题批 disputed=0）。
WAVE3_AGENTS = ["m3-gen-wave3-20261002", "step5-indep-wave3-20261002"]
WAVE3_PREFIXES = ("p1_", "p2_", "p3_", "p4_", "p5_", "p6_", "m8_")


def _is_wave3(it):
    return it.get("verification", {}).get("agents") == WAVE3_AGENTS


# 2026-10-03 K12 高中数学题库批（G1=0 高一必修/高二选必一、G2=11 必修二/选必二、
# G3=12 选必三；候选 393 题经 agree 合并 377 题、16 分歧未回填）：
# hsg-gen-w1-20261003(生成自答) × hsg-indep-w1-20261003(盲解)，代理对落库原序一致。
HS_MATH_AGENTS = ["hsg-gen-w1-20261003", "hsg-indep-w1-20261003"]
HS_MATH_PREFIX = "h_"


def _is_hs_math(it):
    return it.get("verification", {}).get("agents") == HS_MATH_AGENTS


# 2026-10-03 K12 英语题库批（G1-12 全学段 12 个年级文件；候选生成 × 盲解
# agree 合并 425 题入库，分歧 252 条入 arbitration_queue_en.json 未回填）：
# eng-gen-w1-20261003(生成自答) × eng-indep-w1-20261003(盲解)，代理对落库
# 原序一致；题内 verification 记录即为覆盖凭证。
ENG_AGENTS = ["eng-gen-w1-20261003", "eng-indep-w1-20261003"]
ENG_PREFIX = "eng_"


def _is_english(it):
    return it.get("verification", {}).get("agents") == ENG_AGENTS


# 2026-10-03 K12 英语密度补齐批（GEN_ENG_DENSITY_01，known issue：单代理自验）：
# eng_dens01_0001..0828（276 deficient KP × 3），共用生成代理 eng-gen-w1-20261003
# 的单元素签名 + single_agent=true 逐题申报；待 eng-indep 独立盲解回填后改登记
# 为 [gen, indep] 并同步本闭式（与 phy 密度批同形态）。
ENG_DENSITY_AGENTS = ["eng-gen-w1-20261003"]


def _is_english_density(it):
    return it.get("verification", {}).get("agents") == ENG_DENSITY_AGENTS


# 2026-10-03 K12 语文批（扩科首落，30 题）：chi-gen-w1-20261003(生成自答) ×
# chi-indep-w1-20261003(盲解)，双代理 agree 合并入库，代理对落库原序一致；
# chi_hs_0198 入库时曾同文件重复一条（真重复 id），2026-10-03 去重后按 30 锁定。
CHI_AGENTS = ["chi-gen-w1-20261003", "chi-indep-w1-20261003"]
CHI_PREFIX = "chi_"


def _is_chi(it):
    return it.get("verification", {}).get("agents") == CHI_AGENTS


# 2026-10-03 物理/化学扩科批（known issue：单代理自验入库，独立盲解未跑）。
# 按实际落库记录登记：verification.agents 为单元素 ['phy-gen-w1-20261003'] /
# ['che-gen-w1-20261003']，配合 single_agent=true 与逐题 note 如实申报「只有
# 生成自答一个代理」（K12-3 题库建设期已知合法形态；曾短暂记 [gen, gen] 同名
# 重复，2026-10-03 台账修复时改为单元素如实记录）。待 phy-indep-w1 /
# che-indep-w1 独立盲解运行并回填后，改登记为 [gen, indep] 并同步本闭式。
# 题内 verification 记录即为覆盖凭证；v2 门与 known-issue 收口见
# tests/data/test_itembank_v2_data.py。
PHY_AGENTS = ["phy-gen-w1-20261003"]
PHY_PREFIX = "phy_"


def _is_phy(it):
    return it.get("verification", {}).get("agents") == PHY_AGENTS


CHE_AGENTS = ["che-gen-w1-20261003"]
CHE_PREFIX = "che_"


def _is_che(it):
    return it.get("verification", {}).get("agents") == CHE_AGENTS


BIO_AGENTS = ["bio-gen-w1-20261003"]
BIO_PREFIX = "bio_"


def _is_bio(it):
    return it.get("verification", {}).get("agents") == BIO_AGENTS


# 2026-10-03 K12 历史批（单代理自验 known issue）+ 2026-10-04 密度收尾批 11 题
#（h_duj/ajv/edu 9 题 + his_jr_0469/0489，g7/g8）：收尾批 candidates 台账记
# his-gen-w1-20261004（GEN_HIS_FINAL_ledger_gen.json），但入库脚本
# work/merge_subject_safe.py 统一按 his-gen-w1-20261003 落库——题库内两批共用
# HIS_AGENTS 签名，id 前缀 his_ 或 h_（收尾批新号段 h_duj/ajv/edu 用 h_）。
HIS_AGENTS = ["his-gen-w1-20261003"]
HIS_PREFIXES = ("his_", "h_")


def _is_his(it):
    return it.get("verification", {}).get("agents") == HIS_AGENTS


# 2026-10-04 数学密度收尾批（单代理自验 known issue）：45 题入数学 g10-12
# 文件（h_sdf 等 15 个 KP 号段 ×3），签名 mat-gen-w1-20261003；题内 verification
# 记录即为覆盖凭证。
MAT_AGENTS = ["mat-gen-w1-20261003"]
MAT_PREFIX = "h_"


def _is_mat(it):
    return it.get("verification", {}).get("agents") == MAT_AGENTS


# 2026-10-04 仲裁批 ×2（单代理=仲裁员，known issue 形态：分歧题经第三方逐题
# 裁决后按 final_answer 入库，note 逐题申报 verdict 与答案替换情况）：英语
# arbitration_queue_en.json 的 252 分歧（eng-arb-step5，K12-3-arb-eng）；数学
# 高中批 arbitration_queue_hs.json 的 16 分歧中 13 题入库（math-arb-glm53-
# 20261004，K12-3-arb-mat；h_svc_002 both_wrong 弃——正方体中 DC 与 A₁B₁ 均
# 与 AB 相等，选择题双正确选项；h_sva_003 / h_dzi_003 与 GEN_MATH_FINAL 收尾
# 批撞 id 跳过）。仲裁产出：candidates_english/GEN_ENG_DENSITY_01_arbitrated.json
# 与 candidates_final/GEN_MATH_FINAL_arbitrated.json。
ENG_ARB_AGENTS = ["eng-arb-step5-20261004"]
MAT_ARB_AGENTS = ["math-arb-glm53-20261004"]


def _is_eng_arb(it):
    return it.get("verification", {}).get("agents") == ENG_ARB_AGENTS


def _is_mat_arb(it):
    return it.get("verification", {}).get("agents") == MAT_ARB_AGENTS


POL_AGENTS = ["pol-gen-w1-20261003"]
POL_PREFIX = "pol_"
# 2026-10-04 政治密度收尾批 61 题（45 pol_FINAL_* + 13 pol_jr_* + 3 pol_hs_*，
# g8-11）：candidates 台账记 pol-density-gen-20261004（GEN_POL_FINAL_ledger_
# gen.json），但入库脚本统一按 pol-gen-w1-20261003 落库——题库内该批与政治
# 主批共用 POL_AGENTS 签名（已并入 _is_pol 圈定）；POL_DENSITY_AGENTS 按台账
# 口径登记（库内现匹配 0 题），独立盲解回填若改用该 id 须同步本闭式。
POL_DENSITY_AGENTS = ["pol-density-gen-20261004"]
# 同上：历史密度收尾批台账 id，库内实际共用 HIS_AGENTS（见 HIS_AGENTS 注释），
# 现匹配 0 题、仅作台账口径登记。
HIS_DENSITY_AGENTS = ["his-gen-w1-20261004"]


def _is_pol(it):
    return it.get("verification", {}).get("agents") in (POL_AGENTS, POL_DENSITY_AGENTS)


def _is_pol_den(it):
    return it.get("verification", {}).get("agents") == POL_DENSITY_AGENTS


def _is_his_den(it):
    return it.get("verification", {}).get("agents") == HIS_DENSITY_AGENTS


SCI_AGENTS = ["sci-gen-w1-20261003"]
SCI_PREFIX = "sci_"


def _is_sci(it):
    return it.get("verification", {}).get("agents") == SCI_AGENTS


CHI_AGENTS = ["chi-gen-w1-20261003"]
CHI_AGENTS_DUAL = ["chi-gen-w1-20261003", "chi-indep-w1-20261003"]
CHI_PREFIX = "chi_"


def _is_chi(it):
    return it.get("verification", {}).get("agents") in (CHI_AGENTS, CHI_AGENTS_DUAL)


GEO_AGENTS_HS = ["geo-gen-w1-20261003"]
GEO_AGENTS_JR = ["geo-gen-w1jr-20261003"]
GEO_AGENTS = (GEO_AGENTS_HS, GEO_AGENTS_JR)
GEO_PREFIX = "geo_"


def _is_geo(it):
    ag = it.get("verification", {}).get("agents")
    return ag in (GEO_AGENTS_HS, GEO_AGENTS_JR)


# deepen/扩库批（代理对与落库记录原序一致；未登记批次落库即失败，fail-closed）
DEEPEN_AGENTS_BY_GRADE = {
    "m7": [["step-3.7-flash", "g7-deepen-review-20260930"]],
    "m9": [["step-3.7-flash", "m9-deepen-review-20260930"]],
    # 五/六年级：llm 生成题走 reviewer 对，3+3 道 original 题走 p56 作者/复验对
    "p5": [["step-3.7-flash", "p5-reviewer-20260930"],
           ["p56-author-20260930", "p56-reverify-20260930"]],
    "p6": [["step-3.7-flash", "p6-reviewer-20260930"],
           ["p56-author-20260930", "p56-reverify-20260930"]],
    "geo": [GEO_AGENTS_HS, GEO_AGENTS_JR],
    "pol": [POL_AGENTS],
    "his": [HIS_AGENTS],
    "sci": [SCI_AGENTS],
    "chi": [CHI_AGENTS, CHI_AGENTS_DUAL],
}


def _load_items(paths):
    assert paths, "no item files found under data/items/"
    items = []
    for path in paths:
        with open(path, encoding="utf-8") as f:
            items.extend(json.load(f)["items"])
    return items


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _answers_by_item(items, key_agent, ledger_agent, ledger_answers):
    out = {}
    for it in items:
        out[it["id"]] = {
            key_agent: it["answer"],  # key 通道：独立审题员的解题产物即标答
            ledger_agent: ledger_answers.get(it["id"]),
        }
    return out


@pytest.fixture(scope="module")
def night_items():
    return _load_items(NIGHT_ITEM_FILES)


@pytest.fixture(scope="module")
def night_bank(night_items, ledger):
    """night 运行的子库 = 现库中台账覆盖的存量题（2026-09-29 时点的 7-9 库）；
    其后 g7/m9 deepen 批扩出的题不属于该运行，由并集检查与代理登记表覆盖。"""
    ids = set(ledger["answers"])
    return [it for it in night_items if it["id"] in ids]


@pytest.fixture(scope="module")
def p34_items():
    # 2026-10-02 wave3 扩库批的 3-4 年级新题不属于本运行，按代理身份剔除
    return [it for it in _load_items(P34_ITEM_FILES) if not _is_wave3(it)]


@pytest.fixture(scope="module")
def all_items():
    return _load_items(ALL_ITEM_FILES)


@pytest.fixture(scope="module")
def ledger():
    return _load(LEDGER_PATH)


@pytest.fixture(scope="module")
def manifest():
    return _load(MANIFEST_PATH)


@pytest.fixture(scope="module")
def queue():
    return _load(QUEUE_PATH)


@pytest.fixture(scope="module")
def p34_ledger():
    return _load(P34_LEDGER_PATH)


@pytest.fixture(scope="module")
def p34_manifest():
    return _load(P34_MANIFEST_PATH)


@pytest.fixture(scope="module")
def p34_queue():
    return _load(P34_QUEUE_PATH)


@pytest.fixture(scope="module")
def p12_items():
    # 2026-10-02 wave3 扩库批的 1-2 年级新题不属于本运行，按代理身份剔除
    return [it for it in _load_items(P12_ITEM_FILES) if not _is_wave3(it)]


@pytest.fixture(scope="module")
def p12_ledger():
    return _load(P12_LEDGER_PATH)


@pytest.fixture(scope="module")
def p12_manifest():
    return _load(P12_MANIFEST_PATH)


@pytest.fixture(scope="module")
def p12_queue():
    return _load(P12_QUEUE_PATH)


# ---------- 运行产物存在 ----------

def test_run_artifacts_exist():
    for p in (LEDGER_PATH, MANIFEST_PATH, QUEUE_PATH,
              P34_LEDGER_PATH, P34_MANIFEST_PATH, P34_QUEUE_PATH,
              P12_LEDGER_PATH, P12_MANIFEST_PATH, P12_QUEUE_PATH):
        assert os.path.exists(p), f"missing run artifact: {p}"


# ---------- 2026-09-29 run（7-9 年级存量 321 题；扩库后子库按台账圈定） ----------

def test_night_ledger_covers_real_bank(night_items, ledger):
    assert ledger["agent_id"] == "night-reverify-20260929"
    # 闭式：该运行覆盖 2026-09-29 存量 321 题；g7/m9 deepen 扩库后 7-9 库为
    # 519 题，扩出部分归 deepen 批（见并集检查），台账不得含库外孤儿 id
    assert len(ledger["answers"]) == 321
    assert set(ledger["answers"]) <= {it["id"] for it in night_items}
    assert all(isinstance(v, str) and v.strip() for v in ledger["answers"].values())


def test_night_manifest_matches_live_rerun(night_bank, ledger, manifest):
    answers = _answers_by_item(night_bank, "m3-reviewer", "night-reverify-20260929",
                               ledger["answers"])
    report = verify_bank(night_bank, answers)
    assert manifest["items_total"] == len(night_bank) == 321
    assert manifest["counts"] == report.counts()
    assert manifest["agreed_item_ids"] == list(report.agreed_item_ids)
    assert manifest["disputed_item_ids"] == list(report.disputed_item_ids)
    assert manifest["incomplete_item_ids"] == list(report.incomplete_item_ids)
    assert sorted(a["id"] for a in manifest["agents"]) == NIGHT_AGENTS
    specs = {a["id"]: a["spec"] for a in manifest["agents"]}
    assert specs["m3-reviewer"] == "key"  # key 通道如实披露
    assert specs["night-reverify-20260929"].startswith("ledger:")


def test_night_backfilled_records_traceable(night_bank, manifest):
    expected_agents = sorted(a["id"] for a in manifest["agents"])
    for it in night_bank:
        rec = it.get("verification")
        assert isinstance(rec, dict), f"{it['id']}: missing verification record"
        assert rec.get("agents") == expected_agents, it["id"]
        assert rec.get("answers_agree") is True, it["id"]
    verified = sum(1 for it in night_bank if isinstance(it.get("verification"), dict))
    assert verified == len(night_bank)


def test_night_arbitration_queue_closed_form(night_bank, ledger, queue):
    answers = _answers_by_item(night_bank, "m3-reviewer", "night-reverify-20260929",
                               ledger["answers"])
    live_rows = [dict(r) for r in arbitration_rows(night_bank, answers)]
    assert queue["queue"] == live_rows
    # 2026-09-29 运行闭式：321 题双通道判等全部一致，无人工仲裁待办
    assert live_rows == [], (
        "出现分歧：先人工仲裁（改标答或改台账），重跑 tools/dual_agent_verify.py "
        "后再同步本闭式；分歧未仲裁前对应题不得回填 verification"
    )


def test_ledger_spot_checks_independently_recomputed(night_items, ledger):
    by_id = {it["id"]: it for it in night_items}
    # (id, 现算表达式) —— 测试内独立重推，台账与库内标答须同时等于该值
    checks = [
        ("m7_106", str(int(25 / 50 * 360))),            # 扇形圆心角 25/50×360°
        ("m8_36", str(5**2 - 2 * 3)),                   # x²+y²=(x+y)²-2xy
        ("m8_55", str(int((6**2 + 8**2) ** 0.5))),      # 勾股定理斜边
        ("m8_83", str(int((6 + 8) / 2))),               # 偶数个数据的中位数
        ("m9_14", str(2 + 5)),                          # x₁x₂+x₁+x₂
        ("m9_32", str(-1 + 4 + 5)),                     # y=-x²+4x+5 在 x=1（顶点不在 [0,1]）
        ("m9_59", str(int(6 * 360 / 36))),              # S=nπR²/360 → n=6π·360/(36π)
        ("m9_77", str(int(64 / 1.6))),                  # p=64/V，V=1.6
    ]
    missing = [iid for iid, _ in checks if iid not in by_id]
    assert missing == [], f"抽查题不在库中: {missing}"
    for iid, expected in checks:
        assert by_id[iid]["answer"] == expected, f"{iid}: 标答 {by_id[iid]['answer']!r} != 现算 {expected!r}"
        assert ledger["answers"][iid] == expected, f"{iid}: 台账 {ledger['answers'][iid]!r} != 现算 {expected!r}"


def test_ledger_is_derived_not_copied(night_items, ledger):
    """台账至少一条表面形与标答不同而判等：证明走的是规则表等值而非逐字复制。"""
    by_id = {it["id"]: it for it in night_items}
    divergent = [
        iid for iid, ans in ledger["answers"].items()
        if ans != by_id[iid]["answer"] and answers_match(by_id[iid]["answer"], ans, by_id[iid]["item_type"], by_id[iid].get("options"))
    ]
    assert "m9_30" in divergent  # 台账按推导序写 (3,0)和(-1,0)，标答 (-1,0)和(3,0)
    assert divergent, "台账与标答逐字全同：失去独立推导证据"


# ---------- 2026-09-30 run（3-4 年级 94 题，同口径平行闭式） ----------

def test_p34_ledger_covers_real_bank(p34_items, p34_ledger):
    assert p34_ledger["agent_id"] == "recheck-20260930"
    assert set(p34_ledger["answers"]) == {it["id"] for it in p34_items}
    assert all(isinstance(v, str) and v.strip() for v in p34_ledger["answers"].values())


def test_p34_manifest_matches_live_rerun(p34_items, p34_ledger, p34_manifest):
    answers = _answers_by_item(p34_items, "p34-reviewer", "recheck-20260930",
                               p34_ledger["answers"])
    report = verify_bank(p34_items, answers)
    assert p34_manifest["items_total"] == len(p34_items)
    assert p34_manifest["counts"] == report.counts()
    assert p34_manifest["agreed_item_ids"] == list(report.agreed_item_ids)
    assert p34_manifest["disputed_item_ids"] == list(report.disputed_item_ids)
    assert p34_manifest["incomplete_item_ids"] == list(report.incomplete_item_ids)
    assert sorted(a["id"] for a in p34_manifest["agents"]) == P34_AGENTS
    specs = {a["id"]: a["spec"] for a in p34_manifest["agents"]}
    assert specs["p34-reviewer"] == "key"  # key 通道如实披露
    assert specs["recheck-20260930"].startswith("ledger:")


def test_p34_backfilled_records_traceable(p34_items, p34_manifest):
    expected_agents = sorted(a["id"] for a in p34_manifest["agents"])
    for it in p34_items:
        rec = it.get("verification")
        assert isinstance(rec, dict), f"{it['id']}: missing verification record"
        assert rec.get("agents") == expected_agents, it["id"]
        assert rec.get("answers_agree") is True, it["id"]
    verified = sum(1 for it in p34_items if isinstance(it.get("verification"), dict))
    assert verified == len(p34_items)


def test_p34_arbitration_queue_closed_form(p34_items, p34_ledger, p34_queue):
    answers = _answers_by_item(p34_items, "p34-reviewer", "recheck-20260930",
                               p34_ledger["answers"])
    live_rows = [dict(r) for r in arbitration_rows(p34_items, answers)]
    assert p34_queue["queue"] == live_rows
    # 2026-09-30 运行闭式：94 题双通道判等全部一致，无人工仲裁待办
    assert live_rows == [], (
        "出现分歧：先人工仲裁（改标答或改台账），重跑 _research_tmp/p34_dual_verify.py "
        "后再同步本闭式；分歧未仲裁前对应题不得回填 verification"
    )


def test_p34_ledger_spot_checks_independently_recomputed(p34_items, p34_ledger):
    by_id = {it["id"]: it for it in p34_items}
    # (id, 现算表达式) —— 测试内独立重推，台账与库内标答须同时等于该值
    checks = [
        ("p3_014", str(125 * 4)),               # 三位数乘一位数
        ("p3_027", str(20 * 30)),               # 估算 24≈20、32≈30
        ("p3_043", str(435 - 168)),             # 连续退位减法
        ("p4_011", str(240 * 35)),              # 因数末尾有0
        ("p4_015", str(23 * 15 + 8)),           # 有余数除法验算
        ("p4_027", str(100 * 45 + 2 * 45)),     # 分配律简算
        ("p4_041", str((28 - 10 * 2) // 2)),    # 鸡兔同笼假设法（全是鸡，补腿差）
        ("p4_047", str(10 + 10 + 5)),           # 等腰三角形周长（腰=10）
    ]
    missing = [iid for iid, _ in checks if iid not in by_id]
    assert missing == [], f"抽查题不在库中: {missing}"
    for iid, expected in checks:
        assert by_id[iid]["answer"] == expected, f"{iid}: 标答 {by_id[iid]['answer']!r} != 现算 {expected!r}"
        assert p34_ledger["answers"][iid] == expected, f"{iid}: 台账 {p34_ledger['answers'][iid]!r} != 现算 {expected!r}"


# ---------- 2026-09-30 run（小学低段 1-2 年级 96 题，同口径平行闭式） ----------

def test_p12_ledger_covers_real_bank(p12_items, p12_ledger):
    assert p12_ledger["agent_id"] == "step-p12-blind-20260930"
    assert set(p12_ledger["answers"]) == {it["id"] for it in p12_items}
    assert all(isinstance(v, str) and v.strip() for v in p12_ledger["answers"].values())


def test_p12_manifest_matches_live_rerun(p12_items, p12_ledger, p12_manifest):
    answers = _answers_by_item(p12_items, "p12-editor-20260930", "step-p12-blind-20260930",
                               p12_ledger["answers"])
    report = verify_bank(p12_items, answers)
    assert p12_manifest["items_total"] == len(p12_items)
    assert p12_manifest["counts"] == report.counts()
    assert p12_manifest["agreed_item_ids"] == list(report.agreed_item_ids)
    assert p12_manifest["disputed_item_ids"] == list(report.disputed_item_ids)
    assert p12_manifest["incomplete_item_ids"] == list(report.incomplete_item_ids)
    assert sorted(a["id"] for a in p12_manifest["agents"]) == P12_AGENTS
    specs = {a["id"]: a["spec"] for a in p12_manifest["agents"]}
    assert specs["p12-editor-20260930"] == "key"  # key 通道如实披露
    assert specs["step-p12-blind-20260930"].startswith("ledger:")


def test_p12_backfilled_records_traceable(p12_items, p12_manifest):
    expected_agents = sorted(a["id"] for a in p12_manifest["agents"])
    for it in p12_items:
        rec = it.get("verification")
        assert isinstance(rec, dict), f"{it['id']}: missing verification record"
        assert rec.get("agents") == expected_agents, it["id"]
        assert rec.get("answers_agree") is True, it["id"]
    verified = sum(1 for it in p12_items if isinstance(it.get("verification"), dict))
    assert verified == len(p12_items)


def test_p12_arbitration_queue_closed_form(p12_items, p12_ledger, p12_queue):
    answers = _answers_by_item(p12_items, "p12-editor-20260930", "step-p12-blind-20260930",
                               p12_ledger["answers"])
    live_rows = [dict(r) for r in arbitration_rows(p12_items, answers)]
    assert p12_queue["queue"] == live_rows
    # 2026-09-30 运行闭式：96 题双通道判等全部一致，无人工仲裁待办
    #（首轮运行曾有 2 分歧：p1_047 仲裁改标答、p2_023 改题干锁表述后重跑盲解）
    assert live_rows == [], (
        "出现分歧：先人工仲裁（改标答或改台账），重跑 _research_tmp/finalize_p12.py "
        "后再同步本闭式；分歧未仲裁前对应题不得回填 verification"
    )


def test_p12_ledger_spot_checks_independently_recomputed(p12_items, p12_ledger):
    by_id = {it["id"]: it for it in p12_items}
    # (id, 现算表达式) —— 测试内独立重推，台账与库内标答须同时等于该值
    checks = [
        ("p1_009", str(9 + 4)),        # 凑十法 9+4
        ("p1_016", str(16 - 9)),       # 退位减 16-9
        ("p1_033", str(8 + 2)),        # 数列规律 2、4、6、8（+2）
        ("p1_046", str(4 + 1 + 3)),    # 排队：前4人+小刚+后3人
        ("p2_002", str(45 - 18)),      # 笔算退位减 45-18
        ("p2_008", str(6 * 7)),        # 表内乘法 六七四十二
        ("p2_016", str(56 // 8)),      # 用口诀求商
        ("p2_025", str(9 * 5)),        # 分针指9=9大格×5分
        ("p2_037", str(6 - 1)),        # 刻度1到6：末端减起点
    ]
    missing = [iid for iid, _ in checks if iid not in by_id]
    assert missing == [], f"抽查题不在库中: {missing}"
    for iid, expected in checks:
        assert by_id[iid]["answer"] == expected, f"{iid}: 标答 {by_id[iid]['answer']!r} != 现算 {expected!r}"
        assert p12_ledger["answers"][iid] == expected, f"{iid}: 台账 {p12_ledger['answers'][iid]!r} != 现算 {expected!r}"


# ---------- 各运行与 deepen 批的并集：全库每题恰属一批、互不交叉 ----------

def test_runs_cover_own_banks_without_overlap(all_items, ledger, p34_ledger, p12_ledger):
    night_ids = set(ledger["answers"])
    p34_ids = set(p34_ledger["answers"])
    p12_ids = set(p12_ledger["answers"])
    all_ids = {it["id"] for it in all_items}
    chi_ids = {it["id"] for it in all_items if _is_chi(it)}
    phy_ids = {it["id"] for it in all_items if _is_phy(it)}
    che_ids = {it["id"] for it in all_items if _is_che(it)}
    eng_ids = {it["id"] for it in all_items if _is_english(it)}
    eng_dens_ids = {it["id"] for it in all_items if _is_english_density(it)}
    # 2026-10-02 wave3 扩库批：按题内 verification 代理身份圈定（agree 合并才落库）
    wave3_ids = {it["id"] for it in all_items if _is_wave3(it)}
    assert len(all_items) == len(all_ids), "duplicate item id across files"
    assert not (night_ids & p34_ids) and not (night_ids & p12_ids) \
        and not (p34_ids & p12_ids), "两运行覆盖重叠"
    assert not (wave3_ids & (night_ids | p34_ids | p12_ids)), "wave3 与存量运行重叠"
    assert all(i.startswith(WAVE3_PREFIXES) for i in wave3_ids), \
        "wave3 批只允许落在 p1-p6/m8 段"
    assert p34_ids == {i for i in all_ids if i.startswith(("p3_", "p4_"))} - wave3_ids, (
        "p34 运行须恰好覆盖全部 3-4 年级存量题（wave3 扩出部分除外）")
    assert p12_ids == {i for i in all_ids if i.startswith(("p1_", "p2_"))} - wave3_ids, (
        "p12 运行须恰好覆盖全部 1-2 年级存量题（wave3 扩出部分除外）")
    # 7-9 库 = night 存量 321 + g7 deepen 93（m7_130..222）+ m9 deepen 105
    #（m9_106..210）；deepen 批无独立台账，题内 verification 记录即为覆盖凭证；
    # m8 的 wave3 扩出部分归 wave3 批
    m_ids = {i for i in all_ids if i.startswith(("m7_", "m8_", "m9_"))}
    deepen_ids = m_ids - night_ids - wave3_ids
    assert night_ids | deepen_ids | (m_ids & wave3_ids) == m_ids, (
        "night/deepen/wave3 须合并覆盖全部 7-9 年级题")
    assert len(night_ids) == 321 and len(p34_ids) == 94 and len(p12_ids) == 96
    assert len(deepen_ids) == 198, (
        "deepen 批规模变化（现 198=93+105）：新增批次须先登记 "
        "DEEPEN_AGENTS_BY_GRADE 并在本闭式同步")
    # 五/六年级扩库批 101 题（3+3 original × p56 对 + 47+48 llm × reviewer）
    # 不在任何 ledger 运行内，由代理登记表覆盖（见下一测试）
    p56_ids = {i for i in all_ids if i.startswith(("p5_", "p6_"))} - wave3_ids
    assert len(p56_ids) == 101
    # 2026-10-02 wave3 批闭式：G1-6+G8 双代理 agree 合并恰 301 题
    #（320 生成 - 19 分歧未回填 - 3 跨年级题干重复移除 + 3 补题替换）
    assert len(wave3_ids) >= 301, (
        "wave3 批规模变化：扩库/移除/补题后须同步本闭式")
    # 2026-10-03 K12 高中数学批闭式：候选 393 → agree 377 入库、16 分歧未回填
    hs_ids = {it["id"] for it in all_items if _is_hs_math(it)}
    assert len(hs_ids) >= 376, (
        "K12 高中批规模变化（现 376）：新增批次须先登记 HS_MATH_AGENTS 并在本闭式同步")
    assert all(i.startswith(HS_MATH_PREFIX) for i in hs_ids), "高中批题 id 前缀须为 h_"
    assert not (hs_ids & (night_ids | p34_ids | p12_ids | wave3_ids)), "高中批与既有批次重叠"
    # 2026-10-03 K12 英语批闭式：生成 × 盲解 agree 合并恰 425 题入库、
    # 分歧 252 条未回填（arbitration_queue_en.json）
    assert len(eng_ids) >= 425, (
        "英语批规模变化（现 425）：新增批次须先登记 ENG_AGENTS 并在本闭式同步")
    assert all(i.startswith(ENG_PREFIX) for i in eng_ids), "英语批题 id 前缀须为 eng_"
    assert not (eng_ids & (night_ids | p34_ids | p12_ids | wave3_ids | hs_ids)), (
        "英语批与既有批次重叠")
    # 2026-10-03 K12 英语密度补齐批闭式（单代理自验 known issue，见
    # ENG_DENSITY_AGENTS 登记）：276 deficient KP × 3 = 828 题下限式断言
    assert len(eng_dens_ids) >= 828, (
        "英语密度批规模异常（< 828）：扩库须先登记 ENG_DENSITY_AGENTS 并同步")
    assert all(i.startswith(ENG_PREFIX) for i in eng_dens_ids), (
        "英语密度批题 id 前缀须为 eng_")
    assert not (eng_dens_ids & (night_ids | p34_ids | p12_ids | wave3_ids | hs_ids | eng_ids)), (
        "英语密度批与既有批次重叠")
    # 2026-10-03 K12 物理/化学批闭式（单代理自验 known issue，见文件头）：
    # phy 860 题（G8-12）、che 977 题（G9-12）；批内去重与跨批双落移除
    # （che_hs2_0143 与 phy_phyjr_0407 整题重复，移除化学侧）后按现状锁定；
    # 独立盲解回填前按现状锁定题量
    phy_ids = {it["id"] for it in all_items if _is_phy(it)}
    che_ids = {it["id"] for it in all_items if _is_che(it)}
    assert len(phy_ids) >= 860 and len(che_ids) >= 977, (
        "物理/化学批规模变化（现 phy=860、che=977）：扩库须先登记代理身份并在"
        "本闭式同步；独立盲解回填后改登记为 [gen, indep]")
    assert all(i.startswith(PHY_PREFIX) for i in phy_ids), "物理批题 id 前缀须为 phy_"
    assert all(i.startswith(CHE_PREFIX) for i in che_ids), "化学批题 id 前缀须为 che_"
    # chi_ids 在 671 行定义；此段仅做物理/化学与存量批不重叠断言
    assert not ((phy_ids | che_ids)
                & (night_ids | p34_ids | p12_ids | wave3_ids | hs_ids | eng_ids)), (
        "物理/化学批与既有批次重叠")
    # 2026-10-03 K12 生物批闭式（单代理自验 known issue）：G7-12，dedup 去重后 452 题。
    # 题号前缀含 bio_jr/bio_hs（出题员 tag）但 K12-3f 修正 id 后统一 prefix bio_
    bio_ids = {it["id"] for it in all_items if _is_bio(it)}
    assert len(bio_ids) >= 452, (
        "生物批规模变化（现 452）：扩库须先登记代理身份并在本闭式同步；"
        "独立盲解回填后改登记为 [gen, indep]")
    assert all(i.startswith(BIO_PREFIX) for i in bio_ids), "生物批题 id 前缀须为 bio_"
    assert not (bio_ids & (night_ids | p34_ids | p12_ids | wave3_ids | hs_ids | eng_ids | chi_ids | phy_ids | che_ids)), (
        "生物批与既有批次重叠")
    # 2026-10-03 K12 历史批闭式（单代理自验 known issue）：下限式断言；2026-10-04
    # 密度收尾批 11 题共用本签名（h_duj/ajv/edu 新号段用 h_，见 HIS_PREFIXES）
    his_ids = {it["id"] for it in all_items if _is_his(it)}
    assert len(his_ids) >= 1000, (
        "历史批规模异常（< 1000）：扩库须先登记代理身份并在本闭式同步；"
        "独立盲解回填后改登记为 [gen, indep]")
    assert all(i.startswith(HIS_PREFIXES) for i in his_ids), "历史批题 id 前缀须为 his_/h_"
    assert not (his_ids & (night_ids | p34_ids | p12_ids | wave3_ids | hs_ids | eng_ids | chi_ids | phy_ids | che_ids | bio_ids)), (
        "历史批与既有批次重叠")
    # 2026-10-03 K12 地理批闭式（单代理自验 known issue）：下限式断言
    geo_ids = {it["id"] for it in all_items if _is_geo(it)}
    assert len(geo_ids) >= 300, (
        "地理批规模异常（< 300）：扩库须先登记 GEO_AGENTS_HS/HS 并在本闭式同步；"
        "独立盲解回填后改登记为 [gen, indep]")
    assert all(i.startswith(GEO_PREFIX) for i in geo_ids), "地理批题 id 前缀须为 geo_"
    assert not (geo_ids & (night_ids | p34_ids | p12_ids | wave3_ids | hs_ids | eng_ids | chi_ids | phy_ids | che_ids | bio_ids | his_ids)), (
        "地理批与既有批次重叠")
    # 2026-10-03 K12 政治批闭式（单代理自验 known issue）：G6-12，dedup 去重后 1160 题。
    # 2026-10-03 K12 政治批闭式（单代理自验 known issue）：下限式断言（扩库只增不减）
    pol_ids = {it["id"] for it in all_items if _is_pol(it)}
    assert len(pol_ids) >= 1000, (
        "政治批规模异常（< 1000）：扩库须先登记 POL_AGENTS 并在本闭式同步；"
        "独立盲解回填后改登记为 [gen, indep]")
    assert all(i.startswith(POL_PREFIX) for i in pol_ids), "政治批题 id 前缀须为 pol_"
    assert not (pol_ids & (night_ids | p34_ids | p12_ids | wave3_ids | hs_ids | eng_ids | chi_ids | phy_ids | che_ids | bio_ids | his_ids | geo_ids)), (
        "政治批与既有批次重叠")
    # 2026-10-03 K12 小学科学批闭式（单代理自验 known issue）：下限式断言
    sci_ids = {it["id"] for it in all_items if _is_sci(it)}
    assert len(sci_ids) >= 500, (
        "小学科学批规模异常（< 500）：扩库须先登记 SCI_AGENTS 并在本闭式同步；"
        "独立盲解回填后改登记为 [gen, indep]")
    assert all(i.startswith(SCI_PREFIX) for i in sci_ids), "小学科学批题 id 前缀须为 sci_"
    assert not (sci_ids & (night_ids | p34_ids | p12_ids | wave3_ids | hs_ids | eng_ids | chi_ids | phy_ids | che_ids | bio_ids | his_ids | geo_ids | pol_ids)), (
        "小学科学批与既有批次重叠")
    # 2026-10-04 密度收尾批 ×3 闭式（单代理自验 known issue，见文件头）：数学 45
    # 题（mat-gen-w1-20261003，h_ 新号段）；政治 61 题与历史 11 题在题库内共用
    # POL_AGENTS/HIS_AGENTS 签名（已计入上方 pol_ids/his_ids），台账口径的
    # pol-density-gen-20261004 / his-gen-w1-20261004 现库内匹配 0 题、留作独立
    # 盲解回填改号时的 fail-closed 登记。下限式断言，不锁死具体数。
    mat_ids = {it["id"] for it in all_items if _is_mat(it)}
    pol_den_ids = {it["id"] for it in all_items if _is_pol_den(it)}
    his_den_ids = {it["id"] for it in all_items if _is_his_den(it)}
    assert len(mat_ids) >= 45, (
        "数学密度收尾批规模异常（< 45）：扩库须先登记 MAT_AGENTS 并在本闭式同步")
    assert all(i.startswith(MAT_PREFIX) for i in mat_ids), (
        "数学密度收尾批题 id 前缀须为 h_")
    assert not (mat_ids & (night_ids | p34_ids | p12_ids | wave3_ids | hs_ids | eng_ids | eng_dens_ids | chi_ids | phy_ids | che_ids | bio_ids | his_ids | geo_ids | pol_ids | sci_ids)), (
        "数学密度收尾批与既有批次重叠")
    assert all(i.startswith(POL_PREFIX) for i in pol_den_ids), (
        "政治密度收尾批（若以台账 id 落库）题 id 前缀须为 pol_")
    assert all(i.startswith(HIS_PREFIXES) for i in his_den_ids), (
        "历史密度收尾批（若以台账 id 落库）题 id 前缀须为 his_/h_")
    assert not ((pol_den_ids | his_den_ids)
                & (night_ids | p34_ids | p12_ids | wave3_ids | hs_ids | eng_ids | eng_dens_ids | chi_ids | phy_ids | che_ids | bio_ids | his_ids | geo_ids | pol_ids | sci_ids | mat_ids)), (
        "政治/历史密度收尾批与既有批次重叠")
    # 2026-10-04 仲裁批 ×2 闭式（单代理=仲裁员，见 ENG_ARB_AGENTS/MAT_ARB_AGENTS
    # 登记）：英语 252 题、数学 13 题（16 分歧 − 1 both_wrong − 2 撞 id）；
    # 下限式断言，不锁死具体数。
    eng_arb_ids = {it["id"] for it in all_items if _is_eng_arb(it)}
    mat_arb_ids = {it["id"] for it in all_items if _is_mat_arb(it)}
    assert len(eng_arb_ids) >= 250, (
        "英语仲裁批规模异常（< 250）：扩库须先登记 ENG_ARB_AGENTS 并在本闭式同步")
    assert all(i.startswith(ENG_PREFIX) for i in eng_arb_ids), (
        "英语仲裁批题 id 前缀须为 eng_")
    assert len(mat_arb_ids) >= 13, (
        "数学仲裁批规模异常（< 13）：扩库须先登记 MAT_ARB_AGENTS 并在本闭式同步")
    assert all(i.startswith(MAT_PREFIX) for i in mat_arb_ids), (
        "数学仲裁批题 id 前缀须为 h_")
    assert not ((eng_arb_ids | mat_arb_ids)
                & (night_ids | p34_ids | p12_ids | wave3_ids | hs_ids | eng_ids | eng_dens_ids | chi_ids | phy_ids | che_ids | bio_ids | his_ids | geo_ids | pol_ids | sci_ids | mat_ids | pol_den_ids | his_den_ids)), (
        "仲裁批与既有批次重叠")
    chi_ids = {it["id"] for it in all_items if _is_chi(it)}
    assert len(chi_ids) >= 1600, (
        "语文批规模异常（< 1600）：扩库须先登记 CHI_AGENTS 并在本闭式同步；"
        "独立盲解回填后改登记为 [gen, indep]")
    assert all(i.startswith(CHI_PREFIX) for i in chi_ids), "语文批题 id 前缀须为 chi_"
    assert not (chi_ids & (night_ids | p34_ids | p12_ids | wave3_ids | hs_ids | eng_ids | phy_ids | che_ids | bio_ids | his_ids | geo_ids | pol_ids | sci_ids)), (
        "语文批与既有批次重叠")
    # 全库划分：每题恰属一个 ledger 运行或一个扩库批
    assert (
        night_ids | p34_ids | p12_ids | deepen_ids | p56_ids | wave3_ids | hs_ids
        | eng_ids | eng_dens_ids | chi_ids | phy_ids | che_ids | bio_ids | his_ids | geo_ids | pol_ids | sci_ids
        | mat_ids | pol_den_ids | his_den_ids | eng_arb_ids | mat_arb_ids
    ) == all_ids


def test_verification_agents_match_owning_run(all_items, ledger):
    night_ids = set(ledger["answers"])
    for it in all_items:
        rec = it.get("verification")
        assert isinstance(rec, dict) and rec.get("answers_agree") is True, it["id"]
        iid = it["id"]
        if iid in night_ids:
            assert rec["agents"] == NIGHT_AGENTS, iid
        elif rec["agents"] == HS_MATH_AGENTS:
            assert iid.startswith(HS_MATH_PREFIX), iid
        elif rec["agents"] == ENG_AGENTS:
            assert iid.startswith(ENG_PREFIX), iid
        elif rec["agents"] == ENG_DENSITY_AGENTS:
            assert iid.startswith(ENG_PREFIX), iid
            assert rec.get("single_agent") is True, iid  # 单代理批必须带标记申报
        elif rec["agents"] == CHI_AGENTS:
            assert iid.startswith(CHI_PREFIX), iid
        elif rec["agents"] == PHY_AGENTS:
            assert iid.startswith(PHY_PREFIX), iid
            assert rec.get("single_agent") is True, iid  # 单代理批必须带标记申报
        elif rec["agents"] == CHE_AGENTS:
            assert iid.startswith(CHE_PREFIX), iid
            assert rec.get("single_agent") is True, iid
        elif rec["agents"] == BIO_AGENTS:
            assert iid.startswith(BIO_PREFIX), iid
            assert rec.get("single_agent") is True, iid
        elif rec["agents"] == HIS_AGENTS:
            assert iid.startswith(HIS_PREFIXES), iid
            assert rec.get("single_agent") is True, iid
        elif rec["agents"] == MAT_AGENTS:
            assert iid.startswith(MAT_PREFIX), iid
            assert rec.get("single_agent") is True, iid  # 2026-10-04 数学密度收尾批
        elif rec["agents"] == ENG_ARB_AGENTS:
            assert iid.startswith(ENG_PREFIX), iid
            assert rec.get("single_agent") is True, iid  # 2026-10-04 英语仲裁批（仲裁员单代理）
        elif rec["agents"] == MAT_ARB_AGENTS:
            assert iid.startswith(MAT_PREFIX), iid
            assert rec.get("single_agent") is True, iid  # 2026-10-04 数学仲裁批（仲裁员单代理）
        elif rec["agents"] == POL_DENSITY_AGENTS:
            assert iid.startswith(POL_PREFIX), iid
            assert rec.get("single_agent") is True, iid  # 2026-10-04 政治收尾批台账 id（现库内 0 题）
        elif rec["agents"] == HIS_DENSITY_AGENTS:
            assert iid.startswith(HIS_PREFIXES), iid
            assert rec.get("single_agent") is True, iid  # 2026-10-04 历史收尾批台账 id（现库内 0 题）
        elif rec["agents"] in (CHI_AGENTS, CHI_AGENTS_DUAL):
            assert iid.startswith(CHI_PREFIX), iid
            if rec["agents"] == CHI_AGENTS:
                assert rec.get("single_agent") is True, iid
            # CHI_AGENTS_DUAL 是早期双代理入库（30 题），已带 verification.answers_agree=True，无须 single_agent
        elif rec["agents"] == WAVE3_AGENTS:
            assert iid.startswith(WAVE3_PREFIXES), iid
        elif iid.startswith(("p3_", "p4_")):
            assert rec["agents"] == P34_AGENTS, iid
        elif iid.startswith(("p1_", "p2_")):
            assert rec["agents"] == P12_AGENTS, iid
        else:
            grade = iid.split("_", 1)[0]
            allowed = DEEPEN_AGENTS_BY_GRADE.get(grade)
            assert allowed is not None, (
                f"{iid}: deepen 批 {grade} 未登记代理身份（先登记再落库）")
            assert rec["agents"] in allowed, iid
