"""契约：paper_spec —— 卷型定义与校验（load_spec / score_blueprint）。

自封闭：全部夹具为字面 dict、无 IO、无随机；错误行为统一经 PaperSpecError
（ValueError 子类）上报；确定性条款用 json.dumps 逐位比对锁死。
"""
import copy
import dataclasses
import json

import pytest

from xuexing.paper_spec import (
    PaperSpec,
    PaperSpecError,
    SectionSpec,
    load_spec,
    score_blueprint,
)


def _spec_dict(**over):
    base = {
        "subject": "math",
        "stage": "grade7",
        "usage": "diagnostic",
        "duration_min": 60,
        "total_points": 10,
        "sections": [
            {"title": "一、选择题", "form": "choice", "count": 4, "points_each": 1},
            {"title": "二、解答题", "form": "solve", "count": 2, "points_each": 3},
        ],
    }
    base.update(over)
    return base


def _ids(n, prefix="q"):
    return [f"{prefix}{i}" for i in range(1, n + 1)]


# ---------- load_spec：合法构造 ----------


def test_load_spec_valid_minimal():
    spec = load_spec(_spec_dict())
    assert isinstance(spec, PaperSpec)
    assert dataclasses.is_dataclass(spec)
    assert spec.subject == "math"
    assert spec.stage == "grade7"
    assert spec.usage == "diagnostic"
    assert spec.duration_min == 60
    assert spec.total_points == 10
    assert isinstance(spec.sections, tuple) and len(spec.sections) == 2
    first, second = spec.sections
    assert isinstance(first, SectionSpec)
    assert (first.title, first.form, first.count, first.points_each) == ("一、选择题", "choice", 4, 1)
    assert first.difficulty_band is None and first.kp_scope is None
    assert (second.title, second.form, second.count, second.points_each) == ("二、解答题", "solve", 2, 3)
    # 单节卷型同样合法
    single = load_spec(_spec_dict(total_points=3,
                                  sections=[{"title": "全卷", "form": "fill", "count": 3,
                                             "points_each": 1}]))
    assert single.total_points == 3 and len(single.sections) == 1


def test_load_spec_optional_section_fields_and_unknown_keys_ignored():
    spec = load_spec({
        "subject": "math", "stage": "grade8", "usage": "homework",
        "duration_min": 45, "total_points": 4, "note": "卷型备注（多余键忽略）",
        "sections": [
            {"title": "甲", "form": "fill", "count": 2, "points_each": 2,
             "difficulty_band": [0.2, 0.8], "kp_scope": ["kp-a", "kp-b"], "tags": ["x"]},
        ],
    })
    section = spec.sections[0]
    # list 入参固化为 tuple（不可变快照）
    assert section.difficulty_band == (0.2, 0.8)
    assert section.kp_scope == ("kp-a", "kp-b")
    # 难度带也接受 tuple 入参；边界值 0/1 合法
    spec2 = load_spec(_spec_dict(
        sections=[{"title": "甲", "form": "fill", "count": 1, "points_each": 10,
                   "difficulty_band": (0, 1)}]))
    assert spec2.sections[0].difficulty_band == (0, 1)


def test_paper_spec_error_is_value_error():
    assert issubclass(PaperSpecError, ValueError)


def test_non_dict_spec_rejected():
    for bad in (42, "spec", None, [], ()):
        with pytest.raises(PaperSpecError, match="spec must be a dict"):
            load_spec(bad)


# ---------- load_spec：字段校验 ----------


def test_required_str_fields():
    for key in ("subject", "stage", "usage"):
        for bad in (None, "", "   ", 42, ["math"]):
            with pytest.raises(PaperSpecError, match=f"spec.{key} must be a non-blank str"):
                load_spec(_spec_dict(**{key: bad}))
        # 缺失键同样落入类型门（got None）
        data = _spec_dict()
        del data[key]
        with pytest.raises(PaperSpecError, match=f"spec.{key} must be a non-blank str, got None"):
            load_spec(data)


def test_duration_min_rules():
    assert load_spec(_spec_dict(duration_min=1)).duration_min == 1
    for bad in (0, -5, True, 60.0, "60", None, float("nan")):
        with pytest.raises(PaperSpecError, match="spec.duration_min must be an int > 0"):
            load_spec(_spec_dict(duration_min=bad))


def test_total_points_rules():
    assert load_spec(_spec_dict(total_points=10)).total_points == 10
    assert load_spec(_spec_dict(total_points=12.5, sections=[
        {"title": "甲", "form": "fill", "count": 5, "points_each": 2.5}])).total_points == 12.5
    for bad in (0, -1, True, "10", None, float("inf")):
        with pytest.raises(PaperSpecError, match="spec.total_points must be a number > 0"):
            load_spec(_spec_dict(total_points=bad))


def test_sections_non_empty_list():
    for bad in ([], None, "x", {}, 42, ()):
        with pytest.raises(PaperSpecError, match="spec.sections must be a non-empty list"):
            load_spec(_spec_dict(sections=bad))


def test_section_field_rules():
    def one(**over):
        sec = {"title": "甲", "form": "fill", "count": 1, "points_each": 10}
        sec.update(over)
        return _spec_dict(sections=[sec])

    for bad in ("", "  ", 5, None):
        with pytest.raises(PaperSpecError, match=r"sections\[1\].title must be a non-blank str"):
            load_spec(one(title=bad))
        with pytest.raises(PaperSpecError, match=r"sections\[1\].form must be a non-blank str"):
            load_spec(one(form=bad))
    for bad in (0, -1, True, "3", 1.0, None):
        with pytest.raises(PaperSpecError, match=r"sections\[1\].count must be an int >= 1"):
            load_spec(one(count=bad))
    for bad in (0, -1, True, "3", None):
        with pytest.raises(PaperSpecError, match=r"sections\[1\].points_each must be a number > 0"):
            load_spec(one(points_each=bad))
    # 节必须为 dict；消息带 1 起节号（第二节）
    with pytest.raises(PaperSpecError, match=r"sections\[2\] must be a dict"):
        load_spec(_spec_dict(sections=[{"title": "甲", "form": "fill", "count": 4,
                                        "points_each": 1}, "乙"]))
    with pytest.raises(PaperSpecError, match=r"sections\[3\]"):
        load_spec(_spec_dict(sections=[
            {"title": "甲", "form": "fill", "count": 10, "points_each": 1},
            {"title": "乙", "form": "fill", "count": 0, "points_each": 1},
            42,
        ]))


def test_difficulty_band_rules():
    def one(**over):
        sec = {"title": "甲", "form": "fill", "count": 1, "points_each": 10}
        sec.update(over)
        return _spec_dict(sections=[sec])

    for bad in ([0.2], [0.2, 0.8, 0.9], [0.8, 0.2], [-0.1, 0.5], [0, 1.5],
                ["0.2", 0.8], [True, 0.5], "0.2,0.8", 0.5, None):
        with pytest.raises(PaperSpecError, match="difficulty_band must be a pair"):
            load_spec(one(difficulty_band=bad))
    # 缺失不报；合法值（含 lo == hi）通过
    assert load_spec(one()).sections[0].difficulty_band is None
    assert load_spec(one(difficulty_band=[0.5, 0.5])).sections[0].difficulty_band == (0.5, 0.5)


def test_kp_scope_rules():
    def one(**over):
        sec = {"title": "甲", "form": "fill", "count": 1, "points_each": 10}
        sec.update(over)
        return _spec_dict(sections=[sec])

    for bad in ([], "kp-a", ["a", ""], ["a", 5], [None], 42):
        with pytest.raises(PaperSpecError, match="kp_scope must be a non-empty list of non-blank str"):
            load_spec(one(kp_scope=bad))
    assert load_spec(one(kp_scope=["kp-a"])).sections[0].kp_scope == ("kp-a",)


def test_points_sum_must_equal_total():
    with pytest.raises(PaperSpecError, match=r"spec sections points sum 10 != total_points 11"):
        load_spec(_spec_dict(total_points=11))
    # 小数分值：2×2.5 == 5.0 == 5
    assert load_spec(_spec_dict(total_points=5, sections=[
        {"title": "甲", "form": "fill", "count": 2, "points_each": 2.5}])).total_points == 5
    # 门控：节级字段非法时不叠加和消息（只报节级错）
    with pytest.raises(PaperSpecError, match=r"sections\[1\].points_each must be a number > 0"):
        load_spec(_spec_dict(total_points=10, sections=[
            {"title": "甲", "form": "fill", "count": 10, "points_each": "x"}]))


def test_errors_accumulated_then_raised():
    # 多个违规一次报全（"; " 连接），而非首个即抛
    with pytest.raises(PaperSpecError) as excinfo:
        load_spec({"subject": "", "stage": 7, "duration_min": 0, "sections": []})
    message = str(excinfo.value)
    assert "spec.subject must be a non-blank str" in message
    assert "spec.stage must be a non-blank str" in message
    assert "spec.duration_min must be an int > 0" in message
    assert "spec.sections must be a non-empty list" in message
    # 空 sections 时不叠加无意义的分和消息
    assert "points sum" not in message


def test_load_spec_purity():
    data = _spec_dict(sections=[
        {"title": "甲", "form": "fill", "count": 2, "points_each": 2,
         "difficulty_band": [0.2, 0.8], "kp_scope": ["kp-a"]},
        {"title": "乙", "form": "solve", "count": 2, "points_each": 3},
    ])
    snapshot = copy.deepcopy(data)
    spec = load_spec(data)
    assert data == snapshot  # 入参不被修改
    # 固化的 tuple 快照与入参 list 不别名：事后改动入参不影响 spec
    data["sections"][0]["difficulty_band"].append(0.9)
    data["sections"][0]["kp_scope"].append("kp-z")
    assert spec.sections[0].difficulty_band == (0.2, 0.8)
    assert spec.sections[0].kp_scope == ("kp-a",)


# ---------- score_blueprint：装订闭式 ----------


def test_score_blueprint_basic_binding():
    spec = load_spec(_spec_dict())
    ids = _ids(6)
    bp = score_blueprint(spec, ids)

    assert set(bp) == {"subject", "stage", "usage", "duration_min", "total_points",
                       "question_count", "sections"}
    assert bp["subject"] == "math" and bp["stage"] == "grade7" and bp["usage"] == "diagnostic"
    assert bp["duration_min"] == 60 and bp["total_points"] == 10
    assert bp["question_count"] == 6

    sections = bp["sections"]
    assert len(sections) == 2
    first, second = sections
    assert set(first) == {"section_no", "title", "form", "count", "points_each",
                          "section_points", "questions"}
    assert (first["section_no"], first["title"], first["form"]) == (1, "一、选择题", "choice")
    assert (first["count"], first["points_each"], first["section_points"]) == (4, 1, 4)
    assert (second["section_no"], second["title"], second["form"]) == (2, "二、解答题", "solve")
    assert (second["count"], second["points_each"], second["section_points"]) == (2, 3, 6)

    # 小题号全卷连续 1..N；题序 = 节序 × 节内消费序；每题分值 = 该大题 points_each
    flat = [q for sec in sections for q in sec["questions"]]
    assert [q["question_no"] for q in flat] == [1, 2, 3, 4, 5, 6]
    assert [q["item_id"] for q in flat] == ids
    assert [q["points"] for q in flat] == [1, 1, 1, 1, 3, 3]
    assert all(set(q) == {"question_no", "item_id", "points"} for q in flat)
    # 卷面分值闭式：大题分值和 == total_points == 小题分值和
    assert sum(sec["section_points"] for sec in sections) == bp["total_points"]
    assert sum(q["points"] for q in flat) == bp["total_points"]
    # spec 中未设置的可选字段不回显（无 difficulty_band / kp_scope 键）
    assert "difficulty_band" not in first and "kp_scope" not in first


def test_score_blueprint_echoes_optional_fields_as_fresh_copies():
    spec = load_spec(_spec_dict(sections=[
        {"title": "甲", "form": "fill", "count": 2, "points_each": 2,
         "difficulty_band": [0.2, 0.8], "kp_scope": ["kp-a", "kp-b"]},
        {"title": "乙", "form": "solve", "count": 2, "points_each": 3},
    ]))
    bp = score_blueprint(spec, _ids(4))
    first = bp["sections"][0]
    assert first["difficulty_band"] == [0.2, 0.8]
    assert first["kp_scope"] == ["kp-a", "kp-b"]
    # 回显是拷贝：改输出不污染 spec
    first["kp_scope"].append("kp-z")
    first["difficulty_band"][0] = 9.9
    assert spec.sections[0].kp_scope == ("kp-a", "kp-b")
    assert spec.sections[0].difficulty_band == (0.2, 0.8)


def test_score_blueprint_count_mismatch_raises():
    spec = load_spec(_spec_dict())
    with pytest.raises(PaperSpecError, match=r"paper_item_ids too few: need 6, got 5"):
        score_blueprint(spec, _ids(5))
    with pytest.raises(PaperSpecError, match=r"paper_item_ids too few: need 6, got 0"):
        score_blueprint(spec, [])
    with pytest.raises(PaperSpecError, match=r"paper_item_ids too many: need 6, got 7"):
        score_blueprint(spec, _ids(7))
    with pytest.raises(PaperSpecError, match=r"paper_item_ids too many: need 6, got 12"):
        score_blueprint(spec, _ids(6) + _ids(6, prefix="z"))


def test_score_blueprint_item_id_surface():
    spec = load_spec(_spec_dict())
    # 元素必须为 strip 后非空的 str
    for bad_ids in ([ "q1", "q2", "q3", "q4", "q5", ""],
                    ["q1", "q2", "q3", "q4", "q5", "  "],
                    ["q1", "q2", "q3", "q4", "q5", 6],
                    ["q1", "q2", "q3", "q4", "q5", None],
                    ["q1", "q2", "q3", "q4", "q5", ["q6"]]):
        with pytest.raises(PaperSpecError, match="paper_item_ids elements must be non-blank str"):
            score_blueprint(spec, bad_ids)
    # 序列表面：str / set / int 均拒（只吃 list/tuple）
    for bad_surface in ("q1q2q3q4q5q6", {1, 2}, 42, None):
        with pytest.raises(PaperSpecError, match="paper_item_ids must be a list or tuple"):
            score_blueprint(spec, bad_surface)
    # tuple 序列合法；同一 id 重复出现按出现次数分别编号（不去重）
    bp = score_blueprint(spec, ("a", "a", "a", "a", "a", "a"))
    assert [q["item_id"] for q in bp["sections"][0]["questions"]] == ["a", "a", "a", "a"]
    assert bp["question_count"] == 6


def test_score_blueprint_spec_type_gate():
    with pytest.raises(PaperSpecError, match="score_blueprint: spec must be a PaperSpec"):
        score_blueprint(_spec_dict(), _ids(6))
    with pytest.raises(PaperSpecError, match="score_blueprint: spec must be a PaperSpec"):
        score_blueprint(None, _ids(6))


def test_score_blueprint_purity_and_determinism():
    spec = load_spec(_spec_dict(sections=[
        {"title": "甲", "form": "fill", "count": 2, "points_each": 2,
         "difficulty_band": [0.2, 0.8], "kp_scope": ["kp-a"]},
        {"title": "乙", "form": "solve", "count": 2, "points_each": 3},
    ]))
    ids = _ids(4)
    spec_snapshot = copy.deepcopy(spec)
    ids_snapshot = copy.deepcopy(ids)
    first = score_blueprint(spec, ids)
    assert spec == spec_snapshot and ids == ids_snapshot  # 入参不被修改
    # 同输入同输出（json.dumps 逐位可复现）
    second = score_blueprint(spec, ids)
    assert first == second
    assert json.dumps(first, ensure_ascii=False, sort_keys=True) == json.dumps(
        second, ensure_ascii=False, sort_keys=True)
    # 输出全量 JSON 可序列化
    json.dumps(first, ensure_ascii=False)
    # 改输出不影响 spec 与后续调用
    first["sections"][0]["questions"][0]["item_id"] = "tampered"
    assert score_blueprint(spec, ids) == second
    assert spec == spec_snapshot


def test_score_blueprint_single_section_multi_count():
    spec = load_spec(_spec_dict(total_points=9, sections=[
        {"title": "全卷", "form": "fill", "count": 3, "points_each": 3}]))
    bp = score_blueprint(spec, ["x", "y", "z"])
    assert bp["question_count"] == 3
    sec = bp["sections"][0]
    assert sec["section_no"] == 1 and sec["section_points"] == 9
    assert [q["question_no"] for q in sec["questions"]] == [1, 2, 3]
    assert [q["item_id"] for q in sec["questions"]] == ["x", "y", "z"]
    assert all(q["points"] == 3 for q in sec["questions"])
