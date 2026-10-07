"""数据测试：题目来源门（签署测试卡 TC-2，2026-10-08，裁定 D-6）。

owner 裁定（2026-10-08 D-6）：题库坚持 100% 原创——全库每道题的 source
只能是 original（人工原创）或 llm_generated（LLM 生成+校验）。出现
adapted、真题类来源、空值或缺失一律失败。真题/第三方题只允许作为卷型
统计参考，永不进入题干；将来如需放开必须重新签署。

只用数据测试实现，不改冻结模块 itembank_v2 的契约与实现。
测试文件名含 source_gate，供 `pytest -k source_gate` 选中。
"""
import glob
import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_ALLOWED_SOURCES = {"original", "llm_generated"}


def _all_items():
    items = []
    for path in sorted(glob.glob(str(_ROOT / "data" / "items" / "*_items.json"))):
        with open(path, encoding="utf-8") as f:
            items.extend(json.load(f)["items"])
    return items


def test_real_bank_sources_are_original_only():
    counter: dict[str, int] = {}
    for it in _all_items():
        src = it.get("source")
        assert src in _ALLOWED_SOURCES, (
            f"{it['id']}: source={src!r} 不在原创类白名单 {_ALLOWED_SOURCES}"
        )
        counter[src] = counter.get(src, 0) + 1
    assert set(counter) == _ALLOWED_SOURCES, f"来源键恰为两类，实得 {set(counter)}"
    assert sum(counter.values()) == len(_all_items())


def test_adapted_source_fails_on_copy():
    """内存副本中把某题 source 改为 adapted 时，门判定必须失败。"""
    items = [dict(it) for it in _all_items()]
    assert items, "题库不应为空"
    items[0]["source"] = "adapted"
    bad = [it["id"] for it in items if it.get("source") not in _ALLOWED_SOURCES]
    assert bad == [items[0]["id"]]


def test_missing_or_empty_source_fails_on_copy():
    """source 缺失或为空时，门判定必须失败。"""
    items = [dict(it) for it in _all_items()]
    assert items, "题库不应为空"
    del items[0]["source"]
    items[1]["source"] = ""
    bad = [it["id"] for it in items if it.get("source") not in _ALLOWED_SOURCES]
    assert len(bad) == 2
