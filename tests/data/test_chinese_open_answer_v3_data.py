"""数据测试：语文开放答案题结构化与第二代理记录（签署测试卡 TC-8）。

staged 口径（2026-10-08 第一批 g8dictfill01：grade8 dictation/fill 17 题单
代理，15 题结构化、9 题第二代理 agree 回填、8 题入 chiopen 队列；作文
rubric+calibration 未启动）。阶段推进时同步更新本文件常量，与 PM-STATE
登记的剩余数一致——不虚报。

测试名含 chinese_open，供 `pytest -k chinese_open` 选中。
"""
import json
import os
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

# staged 常量（每批后同步；与 PM-STATE 登记一致）
CHIOPEN_OPEN_TOTAL = 1846          # 语文无选项开放题总数
CHIOPEN_STRUCTURED = 15            # 已补 acceptable_variants/scoring_points
CHIOPEN_V3_ERR_ESSAY = 238         # 作文类缺 rubric（待 rubric 批处理）
CHIOPEN_ESSAY_CALIBRATED = 0       # 已完成 rubric+校准的作文数
CHIOPEN_BLIND_AGENT = "minimax-m3-blind-chiopen-20261008"
CHIOPEN_STRUCT_AGENT = "kimi3-struct-chiopen-20261008"
CHIOPEN_AGREE_IDS = {
    "chi_chi_jr_0171", "chi_chi_jr_0174", "chi_chi_jr_0197",
    "chi_chi_jr_0245", "chi_chi_jr_0250", "chi_chi_jr_0254",
    "chi_chi_jr_0255", "chi_chi_jr_0275", "chi_chi_jr_0281",
}


def _chinese_items():
    out = []
    cdir = _ROOT / "data" / "items"
    for path in sorted(cdir.glob("chinese_*_items.json")):
        with open(path, encoding="utf-8") as f:
            out.extend(json.load(f)["items"])
    return out


def _grade8_file():
    path = _ROOT / "data" / "items" / "chinese_grade8_items.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)["items"]


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


def test_chinese_open_processed_subset_v3_clean():
    """已结构化的题（chiopen_struct 台账）经冻结映射探针 v3 零报错。"""
    ledger = json.loads((_ROOT / "data" / "verification" / "chiopen_struct_g8dictfill01.json")
                        .read_text(encoding="utf-8"))
    by_id = {it["id"]: it for it in _grade8_file()}
    assert ledger["batch"] == "g8dictfill01"
    assert len(ledger["records"]) == CHIOPEN_STRUCTURED
    for rec in ledger["records"]:
        it = by_id[rec["id"]]
        errs = validate_item_v3(dict(it, form=CHINESE_OPEN_FORM_MAP.get(it["form"], it["form"])))
        assert errs == [], (rec["id"], errs)


def test_chinese_open_stage_counts_registered():
    """staged 常量与库内实况一致（不虚报：推进批次须同步更新常量）。"""
    items = _chinese_items()
    open_items = [it for it in items if not it.get("options")]
    assert len(open_items) == CHIOPEN_OPEN_TOTAL
    missing = [it for it in open_items
               if not any(k in it for k in ("acceptable_variants", "scoring_points", "rubric"))]
    assert len(missing) == CHIOPEN_OPEN_TOTAL - CHIOPEN_STRUCTURED
    v3_err = [it for it in open_items
              if validate_item_v3(dict(it, form=CHINESE_OPEN_FORM_MAP.get(it["form"], it["form"])))]
    assert len(v3_err) == CHIOPEN_V3_ERR_ESSAY
    assert all(it["form"] in ("essay", "applied-writing") for it in v3_err)


def test_chinese_open_second_agent_records_legal():
    """agree 题的第二代理 = 登记的 minimax 盲解签名，single_agent 标记消失。"""
    for it in _grade8_file():
        if it["id"] not in CHIOPEN_AGREE_IDS:
            continue
        rec = it["verification"]
        assert rec["answers_agree"] is True
        assert len(rec["agents"]) == 2
        assert rec["agents"][1] == CHIOPEN_BLIND_AGENT
        assert "single_agent" not in rec
    # 反向：无其余题冒用该盲解签名
    for it in _chinese_items():
        agents = (it.get("verification") or {}).get("agents") or []
        if len(agents) == 2 and agents[1] == CHIOPEN_BLIND_AGENT:
            assert it["id"] in CHIOPEN_AGREE_IDS, it["id"]


def test_chinese_open_queue_structure_legal():
    qpath = _ROOT / "data" / "verification" / "arbitration_queue_chiopen_g8dictfill01.json"
    queue = json.loads(qpath.read_text(encoding="utf-8"))
    assert queue["batch"] == "g8dictfill01"
    assert all(r.get("status") == "open" for r in queue["queue"])
    assert not (CHIOPEN_AGREE_IDS & {r["id"] for r in queue["queue"]})


def test_chinese_open_essay_calibration_pending_registered():
    """作文 rubric+calibration 未启动：CALIB 挂账如实（当前 0 题已校准）。"""
    items = _chinese_items()
    essays = [it for it in items
              if it["form"] in ("essay", "applied-writing") and not it.get("options")]
    assert len(essays) == CHIOPEN_V3_ERR_ESSAY
    calibrated = [it for it in essays
                  if len(it.get("calibration_samples") or []) >= 3]
    assert len(calibrated) == CHIOPEN_ESSAY_CALIBRATED
