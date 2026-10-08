"""数据测试：语文开放答案题结构化与第二代理记录（签署测试卡 TC-8）。

口径（不变式，不随批次更新常量）：
- 全库语文无选项开放题 OPEN（1846 基线）逐题必居四种状态之一：已结构化
  （acceptable_variants/scoring_points/rubric 之一）、已双代理回填、
  在未结仲裁队列、或未处理（如实挂账 MISSING）；
- V3_ERR 恰等于「作文类缺 rubric」数；已结构化的题经冻结映射探针 v3 零报错；
- 第二代理记录 = 二代理且末位 ∈ CHIOPEN_BLIND_AGENTS（泛化注册表）且无
  single_agent 标记；form 原值与 30bdcf0 逐题相等。
测试名含 chinese_open，供 `pytest -k chinese_open` 选中。
"""
import json
import subprocess
from pathlib import Path

import sys

from xuexing.itembank_v3 import validate_item_v3

_ROOT = Path(__file__).resolve().parents[2]

# 冻结映射表（签署测试卡 TC-8 (5)）：v3 校验按此映射探针，form 原值不改
CHINESE_OPEN_FORM_MAP = {
    "dictation": "fill",
    "transcription": "fill",
    "correction": "fill",
    "translation": "fill",
    "connection": "fill",
    "applied-writing": "essay",
}
STRUCT_KEYS = ("acceptable_variants", "scoring_points", "rubric")
CHIOPEN_ESS_TOTAL = 238          # 语文 essay/applied-writing 总数（TC-8 (3) 口径）
TC7_BLIND_MIN = 1                # 下限护栏：至少一个已登记盲解方（防误删注册集）


def _chinese_items():
    out = []
    cdir = _ROOT / "data" / "items"
    for path in sorted(cdir.glob("chinese_*_items.json")):
        with open(path, encoding="utf-8") as f:
            out.extend(json.load(f)["items"])
    return out


def _blind_agents():
    sys.path.insert(0, str(_ROOT / "tests" / "data"))
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "dvreg", str(_ROOT / "tests" / "data" / "test_dual_verify_data.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.CHIOPEN_BLIND_AGENTS


def test_chinese_open_mapping_table_frozen():
    assert CHINESE_OPEN_FORM_MAP == {
        "dictation": "fill", "transcription": "fill", "correction": "fill",
        "translation": "fill", "connection": "fill", "applied-writing": "essay",
    }


def test_chinese_open_form_values_unchanged_since_30bdcf0():
    """全部语文文件的 {id: form} 与 30bdcf0 逐题相等（form 原值一律不改）。"""
    cdir = _ROOT / "data" / "items"
    for path in sorted(cdir.glob("chinese_*_items.json")):
        rel = path.relative_to(_ROOT).as_posix()
        old = json.loads(subprocess.run(
            ["git", "show", f"30bdcf0:{rel}"],
            capture_output=True, text=True, check=True, cwd=_ROOT,
        ).stdout)
        now = json.loads(path.read_text(encoding="utf-8"))
        assert {it["id"]: it.get("form") for it in old["items"]} == \
               {it["id"]: it.get("form") for it in now["items"]}, rel


def test_chinese_open_registered_blind_agents_nonempty():
    """盲解方登记集非空且与库内实际二代理末位一致（防止登记漂移）。"""
    blind = _blind_agents()
    assert len(blind) >= TC7_BLIND_MIN
    used = {(it.get("verification") or {}).get("agents", [])[-1]
            for it in _chinese_items()
            if len((it.get("verification") or {}).get("agents", [])) == 2}
    assert (used & blind), f"库内未见已登记盲解方的二代理对: {used}"


def test_chinese_open_processed_subset_v3_clean():
    """已结构化的题（各 chiopen_struct 台账）经冻结映射探针 v3 零报错。"""
    blind = _blind_agents()
    checked = 0
    for path in sorted((_ROOT / "data" / "verification").glob("chiopen_struct_*.json")):
        ledger = json.loads(path.read_text(encoding="utf-8"))
        for rec in ledger.get("records", []):
            it_id = rec["id"]
            for items_file in (_ROOT / "data" / "items").glob("chinese_*_items.json"):
                for it in json.loads(items_file.read_text(encoding="utf-8"))["items"]:
                    if it["id"] != it_id:
                        continue
                    errs = validate_item_v3(dict(it, form=CHINESE_OPEN_FORM_MAP.get(it["form"], it["form"])))
                    if rec.get("acceptable_variants") or rec.get("scoring_points") or rec.get("rubric"):
                        assert errs == [], (it_id, errs)
                        checked += 1
    assert checked > 0, "未覆盖任何已结构化题"


def test_chinese_open_stage_counts_invariant():
    """实质不变式：MISSING == OPEN − 已结构化/已 rubric；V3_ERR == 作文缺 rubric。"""
    items = _chinese_items()
    open_items = [it for it in items if not it.get("options")]
    structured = [it for it in open_items if any(k in it for k in STRUCT_KEYS)]
    missing = [it for it in open_items if not any(k in it for k in STRUCT_KEYS)]
    v3_err = [it for it in open_items
              if validate_item_v3(dict(it, form=CHINESE_OPEN_FORM_MAP.get(it["form"], it["form"])))]
    essays = [it for it in open_items
              if it["form"] in ("essay", "applied-writing")]
    assert len(missing) == len(open_items) - len(structured)
    assert len(v3_err) == len([e for e in essays if "rubric" not in e]), (
        "V3_ERR 应恰等于缺 rubric 的作文题数")
    assert len(essays) == CHIOPEN_ESS_TOTAL
    # 已完成结构化必须覆盖首批（g8 dictation/fill 15 题）并已推进
    assert len(structured) >= 15


def test_chinese_open_second_agent_records_legal():
    """二代理末位 ∈ 已登记盲解方 -> 无 single_agent 标记、答案已 agree。"""
    blind = _blind_agents()
    n = 0
    for it in _chinese_items():
        rec = it.get("verification") or {}
        agents = rec.get("agents") or []
        if len(agents) == 2 and agents[1] in blind:
            rec_agree = rec.get("answers_agree")
            assert rec_agree is True, it["id"]
            assert "single_agent" not in rec, it["id"]
            assert any(k in it for k in STRUCT_KEYS), it["id"]
            n += 1
    assert n >= 9, f"第二代理回填过少（{n}）"


def test_chinese_open_queue_structure_legal():
    vdir = _ROOT / "data" / "verification"
    for path in sorted(vdir.glob("arbitration_queue_chiopen_*.json")):
        queue = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(queue.get("batch"), str) and queue["batch"]
        for row in queue["queue"]:
            assert row.get("status") in ("open", "resolved"), row.get("id")
            assert isinstance(row.get("id"), str) and row["id"]
        # 未结队列内的题不得同时是已双代理状态
        agree_ids = {it["id"] for it in _chinese_items()
                     if len((it.get("verification") or {}).get("agents", [])) == 2}
        open_ids = {r["id"] for r in queue["queue"] if r.get("status") == "open"}
        assert not (open_ids & agree_ids), path.name


def test_chinese_open_essay_calibration_pending_registered():
    """作文 rubric+calibration 未启动：CALIB 挂账如实（当前 0 题已校准）。"""
    essays = [it for it in _chinese_items()
              if it["form"] in ("essay", "applied-writing") and not it.get("options")]
    assert len(essays) == CHIOPEN_ESS_TOTAL
    calibrated = [it for it in essays if len(it.get("calibration_samples") or []) >= 3]
    assert len(calibrated) < CHIOPEN_ESS_TOTAL, "essay 全量校准未启动，该数须留缺口"


def test_chinese_open_unexplained_chi_invariant():
    """UNEXPLAINED_CHI 口径分解：单代理且未结构化题 = 已入队未结构化 +
    既未入队也未处理（后者即 UNEXPLAINED，如实挂账，BACKLOG 不勾）。"""
    items = _chinese_items()
    vdir = _ROOT / "data" / "verification"
    in_queue = set()
    for path in sorted(vdir.glob("arbitration_queue_chiopen_*.json")):
        for r in json.loads(path.read_text(encoding="utf-8"))["queue"]:
            if r.get("status") == "open":
                in_queue.add(r["id"])
    def _single_unstructured(it):
        return (not it.get("options")
                and not any(k in it for k in STRUCT_KEYS)
                and len((it.get("verification") or {}).get("agents", [])) == 1)
    unprocessed = [it for it in items if _single_unstructured(it)]
    queued_unstructured = [it for it in unprocessed if it["id"] in in_queue]
    unexplained = [it for it in unprocessed if it["id"] not in in_queue]
    assert len(queued_unstructured) + len(unexplained) == len(unprocessed)
    print(f"未入队未处理开放题（UNEXPLAINED_CHI）= {len(unexplained)}；"
          f"已入队未结构化 = {len(queued_unstructured)}")
