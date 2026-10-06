"""单元测试：paper_by_spec —— 卷型库驱动的组卷内核。

自闭式夹具（不依赖 data/ 的用例）钉住行为契约：
- 题型等价类只做同型归并：form=判断 且 item_type=choice 的题绝不进选择题大题
  （反泄漏）；无 form 的题按 item_type 粗类回退；
- 任何大题同型题不足/题型无映射 → PaperBySpecError（fail-closed，无部分卷）；
- 选题确定性与 paper.generate_paper 同款（同输入同输出，排名序池进 shuffle）；
- 卷型内部不一致（Σcount×points_each != total_points）在 load_spec 即拒。
真实数据用例只做廉价不变式：卷型库出现的每个 form 都已收录等价类。
"""
import json
import os

import pytest

from xuexing.itembank import ItemBank
from xuexing.paper_by_spec import (
    FORM_ALIASES,
    PaperBySpecError,
    eligible_items,
    generate_paper_by_spec,
    load_spec_catalog,
    load_stage_bank,
    matches_form,
    select_items_for_spec,
    stage_item_paths,
)
from xuexing.paper_spec import PaperSpecError, load_spec
from xuexing.types import Item

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def make_item(item_id, item_type="choice", form="mcq_single", difficulty=0.5, kp="a"):
    return Item(id=item_id, item_type=item_type, stem=f"s-{item_id}", answer="ans",
                kps=[kp], difficulty=difficulty,
                options=["A. 1", "B. 2"] if item_type == "choice" else [],
                form=form)


def mini_spec(sections, total_points=None, subject="demo", stage="junior"):
    total = total_points if total_points is not None else sum(
        s["count"] * s["points_each"] for s in sections)
    return {"id": "spec_mini", "subject": subject, "stage": stage, "usage": "final_exam",
            "duration_min": 60, "total_points": total, "sections": sections}


def spec_bank():
    b = ItemBank()
    b.add(make_item("c1", "choice", "mcq_single", 0.2))
    b.add(make_item("c2", "choice", "mcq_single", 0.5))
    b.add(make_item("c3", "choice", "mcq_single", 0.8))
    b.add(make_item("tf1", "choice", "判断", 0.5))  # 判断题：绝不进 choice
    b.add(make_item("bc1", "choice", None, 0.5))  # 无 form：按 item_type 回退
    b.add(make_item("j1", "solve", "简答", 0.4))
    b.add(make_item("j2", "solve", "solve", 0.6))
    return b


# ---------- 题型等价类：同型归并 + 反泄漏 ----------

def test_matches_form_specific_form_wins_no_leak():
    bank = spec_bank()
    tf = bank.get("tf1")
    assert matches_form(tf, "truefalse")  # 判断等价类收它
    assert not matches_form(tf, "choice")  # item_type=choice 也不能让它进选择题


def test_matches_form_alias_equivalence():
    bank = spec_bank()
    assert matches_form(bank.get("c1"), "choice")  # mcq_single ≡ 单选
    assert matches_form(bank.get("j1"), "solve")  # 简答 ≡ 解答
    assert not matches_form(bank.get("j1"), "choice")  # 主观题不进选择题


def test_matches_form_formless_fallback():
    bank = spec_bank()
    assert matches_form(bank.get("bc1"), "choice")  # 无 form → item_type 粗类
    bc_fill = make_item("bf1", "fill", None)
    assert matches_form(bc_fill, "fill")
    assert not matches_form(bc_fill, "solve")  # 粗类不跨


def test_eligible_items_unknown_form_empty():
    assert eligible_items(spec_bank(), "mime") == []  # 未收录等价类 → 空表


# ---------- 选题：确定性与 fail-closed ----------

def test_select_items_deterministic_and_disjoint():
    bank = spec_bank()
    spec = load_spec(mini_spec([
        {"title": "一、选择", "form": "choice", "count": 2, "points_each": 3},
        {"title": "二、解答", "form": "solve", "count": 2, "points_each": 4},
    ]))
    ids1 = select_items_for_spec(bank, spec, seed=42)
    ids2 = select_items_for_spec(bank, spec, seed=42)
    assert ids1 == ids2  # 同输入同输出
    assert len(ids1) == 4 and len(set(ids1)) == 4  # 全卷无重复
    assert "tf1" not in ids1  # 判断题不入卷


def test_select_items_ranking_keeps_near_target_pool():
    bank = ItemBank()
    for i, d in enumerate((0.0, 0.1, 0.9, 1.0), 1):
        bank.add(make_item(f"c{i}", "choice", "mcq_single", d))
    spec = load_spec(mini_spec([
        {"title": "一、选择", "form": "choice", "count": 1, "points_each": 10},
    ]))
    for seed in range(20):
        picked = select_items_for_spec(bank, spec, seed=seed, difficulty_target=0.0)
        # 排名序池=前 2n=2 道（c1、c2），任何 seed 都只能从中取
        assert picked in (["c1"], ["c2"]), picked


def test_select_items_insufficient_exact_count():
    bank = ItemBank()
    bank.add(make_item("c1", "choice", "mcq_single", 0.5))
    spec = load_spec(mini_spec([
        {"title": "一、选择", "form": "choice", "count": 2, "points_each": 5},
    ]))
    with pytest.raises(PaperBySpecError, match=r"not enough eligible items: need 2, have 1"):
        select_items_for_spec(bank, spec)


def test_select_items_unmapped_form_fail_closed():
    bank = spec_bank()
    spec = load_spec(mini_spec([
        {"title": "一、表演", "form": "mime", "count": 1, "points_each": 10},
    ]))
    with pytest.raises(PaperBySpecError, match="has no bank form mapping"):
        select_items_for_spec(bank, spec)


def test_select_items_difficulty_out_of_range():
    spec = load_spec(mini_spec([
        {"title": "一、选择", "form": "choice", "count": 1, "points_each": 10},
    ]))
    with pytest.raises(PaperBySpecError, match="difficulty_target out of range"):
        select_items_for_spec(spec_bank(), spec, difficulty_target=1.5)


# ---------- 组卷总入口：装订 + V8 fail-closed ----------

def test_generate_paper_by_spec_binds_skeleton():
    bank = spec_bank()
    raw = mini_spec([
        {"title": "一、选择", "form": "choice", "count": 2, "points_each": 3},
        {"title": "二、解答", "form": "solve", "count": 1, "points_each": 4},
    ])
    paper = generate_paper_by_spec(bank, raw, seed=42, spec_id="spec_mini")
    assert paper["spec_id"] == "spec_mini" and paper["seed"] == 42
    assert paper["total_points"] == 10 and paper["question_count"] == 3
    assert [(s["section_no"], s["section_points"]) for s in paper["sections"]] == [(1, 6), (2, 4)]
    nos = [q["question_no"] for s in paper["sections"] for q in s["questions"]]
    assert nos == [1, 2, 3]  # 小题号全卷连续
    assert paper["item_ids"] == [q["item_id"] for s in paper["sections"]
                                 for q in s["questions"]]
    assert sum(q["points"] for s in paper["sections"] for q in s["questions"]) == 10


def test_generate_paper_by_spec_rejects_inconsistent_total():
    raw = mini_spec([
        {"title": "一、选择", "form": "choice", "count": 2, "points_each": 3},
    ], total_points=11)  # 节和 6 != 11
    with pytest.raises(PaperSpecError, match="points sum 6 != total_points 11"):
        generate_paper_by_spec(spec_bank(), raw)


# ---------- 装载：卷型目录与学段题库 ----------

def test_load_spec_catalog_duplicate_id(tmp_path):
    cat = tmp_path / "paper_specs.json"
    cat.write_text(json.dumps({"version": "t", "specs": [
        {"id": "s1", "subject": "demo", "stage": "junior", "usage": "u",
         "duration_min": 60, "total_points": 3,
         "sections": [{"title": "一", "form": "choice", "count": 1, "points_each": 3}]},
        {"id": "s1", "subject": "demo", "stage": "junior", "usage": "u",
         "duration_min": 60, "total_points": 3,
         "sections": [{"title": "一", "form": "choice", "count": 1, "points_each": 3}]},
    ]}), encoding="utf-8")
    with pytest.raises(PaperBySpecError, match="duplicate spec id"):
        load_spec_catalog(str(cat))


def test_stage_item_paths_grade_range(tmp_path):
    items = tmp_path / "items"
    items.mkdir()
    for g in (6, 7, 8, 9, 10):
        (items / f"demo_grade{g}_items.json").write_text('{"items": []}', encoding="utf-8")
    paths = stage_item_paths(str(tmp_path), "demo", "junior")
    assert [os.path.basename(p) for p in paths] == [
        "demo_grade7_items.json", "demo_grade8_items.json", "demo_grade9_items.json"]
    with pytest.raises(PaperBySpecError, match="unknown stage"):
        stage_item_paths(str(tmp_path), "demo", "middle")


def test_load_stage_bank_no_files_fail_closed(tmp_path):
    with pytest.raises(PaperBySpecError, match="no item files"):
        load_stage_bank(str(tmp_path), "ghost", "junior")


def test_load_stage_bank_merges_grades(tmp_path):
    items = tmp_path / "items"
    items.mkdir()
    (items / "demo_grade7_items.json").write_text(json.dumps({"items": [
        {"id": "d7_1", "item_type": "choice", "stem": "s", "answer": "A", "kps": ["a"],
         "difficulty": 0.5, "options": ["A. 1", "B. 2"], "form": "mcq_single"}]}),
        encoding="utf-8")
    (items / "demo_grade8_items.json").write_text(json.dumps({"items": [
        {"id": "d8_1", "item_type": "solve", "stem": "s", "answer": "x", "kps": ["a"],
         "difficulty": 0.5, "form": "简答"}]}), encoding="utf-8")
    bank, grades = load_stage_bank(str(tmp_path), "demo", "junior")
    assert grades == (7, 8)
    assert [it.id for it in bank.items()] == ["d7_1", "d8_1"]


# ---------- 真实数据不变式（廉价） ----------

def test_catalog_forms_all_aliased():
    """卷型库里出现过的每个 form 都已收录等价类——防「未映射题型」悄悄溜进数据。"""
    with open(os.path.join(ROOT, "data", "curriculum", "paper_specs.json"),
              encoding="utf-8") as f:
        specs = json.load(f)["specs"]
    used = {sec["form"] for spec in specs for sec in spec["sections"]}
    assert used <= set(FORM_ALIASES), sorted(used - set(FORM_ALIASES))
