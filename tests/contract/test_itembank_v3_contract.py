"""契约：itembank_v3 —— item schema v3 新字段（form / acceptable_variants /
scoring_points / rubric / textbook_ref）严格校验。

自封闭：全部夹具为字面 dict，不依赖 data/。只测公开 API 行为（错误消息全等、
累积顺序、bank 语义、纯函数性），不测内部实现。

与冻结模块 itembank_v2 的边界（规格 §1）：v3 **不检查** source/verification 等 v2
字段——完整 v3 入库校验 = 同一 item 先后跑 validate_item_v2 与 validate_item_v3
并拼接消息（test_boundary_with_v2_fields_is_layered 跨模块锁定该边界）。
"""
import copy

import pytest

from xuexing.itembank_v3 import (
    FORM_VALUES,
    SCHEMA_VERSION,
    TEXTBOOK_REF_RE,
    VARIANT_FORMS,
    validate_item_v3,
    validate_items_v3,
)


def _item(**over):
    base = {
        "id": "i1",
        "item_type": "fill",
        "stem": "s",
        "answer": "a",
        "kps": ["kp"],
        "difficulty": 0.5,
    }
    base.update(over)
    return base


def _rubric(dims, total):
    return {"total": total, "dimensions": dims}


def _dim(name="甲", max_score=5, levels=None):
    if levels is None:
        levels = [{"level": "A", "min_score": 4, "desc": "优"},
                  {"level": "B", "min_score": 0, "desc": "良"}]
    return {"name": name, "max_score": max_score, "level_descriptors": levels}


# ---------- 常量与全函数门 ----------


def test_schema_constants():
    assert SCHEMA_VERSION == 3
    assert FORM_VALUES == (
        "choice", "fill", "solve", "essay", "proof", "experiment",
        "comprehension", "cloze", "listening",
    )
    assert isinstance(FORM_VALUES, tuple)
    assert VARIANT_FORMS == ("fill", "solve", "essay", "proof")
    assert isinstance(VARIANT_FORMS, tuple)
    assert set(VARIANT_FORMS) <= set(FORM_VALUES)
    assert TEXTBOOK_REF_RE.fullmatch("pep:g5:u3") is not None


def test_non_dict_items():
    for bad in (None, 42, "x", ["a"], True, 3.14):
        assert validate_item_v3(bad) == ["item is not a dict"]


def test_no_v3_fields_passes():
    assert validate_item_v3(_item()) == []
    # v2 字段与无关多余键一律不归本模块管（边界测试见文末跨模块条）
    assert validate_item_v3(_item(source="scraped", notes="x", verification="no")) == []


# ---------- F1 form ----------


def test_form_accepts_every_enum_value():
    for form in FORM_VALUES:
        if form == "essay":
            # essay 通过 F1，但 F4 必填门要求同题带合法 rubric
            assert validate_item_v3(_item(form=form, rubric=_rubric([_dim()], 5))) == []
        else:
            assert validate_item_v3(_item(form=form)) == []
    # 缺键 = 未声明形态，合法（可选字段）
    assert validate_item_v3(_item()) == []


def test_form_rejections():
    for bad in (None, 42, "", "   ", "Choice", " choice ", "listening ", ["fill"], {"f": 1}):
        assert validate_item_v3(_item(form=bad)) == [f"i1: bad form {bad!r}"]


# ---------- F2 acceptable_variants ----------


def test_variants_valid_on_allowed_forms():
    assert validate_item_v3(_item(form="fill", acceptable_variants=["1/2", "0.5"])) == []
    assert validate_item_v3(_item(form="solve", acceptable_variants=["x=1"])) == []
    assert validate_item_v3(_item(form="proof", acceptable_variants=["因为 AB∥CD"])) == []
    # essay 合法携带变体，但同题必须带 rubric（F4 门）
    assert validate_item_v3(
        _item(form="essay", acceptable_variants=["略"], rubric=_rubric([_dim()], 5))
    ) == []
    # 单元素、含内部空白的元素合法
    assert validate_item_v3(_item(form="fill", acceptable_variants=["1 / 2"])) == []


def test_variants_require_allowed_form():
    gate = ["i1: acceptable_variants requires form in fill/solve/essay/proof"]
    assert validate_item_v3(_item(form="choice", acceptable_variants=["a"])) == gate
    assert validate_item_v3(_item(form="listening", acceptable_variants=["a"])) == gate
    # form 缺失 = 未声明为可变体题型，同样不允许携带
    assert validate_item_v3(_item(acceptable_variants=["a"])) == gate
    # form 非法时报 F1 + F2b 两条（固定序）
    assert validate_item_v3(_item(form=42, acceptable_variants=["a"])) == [
        "i1: bad form 42",
        "i1: acceptable_variants requires form in fill/solve/essay/proof",
    ]
    # essay 通过题型门，但 rubric 必填门照报（F2 通过、F4 报错）
    assert validate_item_v3(_item(form="essay", acceptable_variants=["a"])) == [
        "i1: essay requires rubric"
    ]


def test_variants_type_and_empty():
    for bad in (("a", "b"), "ab", None, {"a": 1}, 42):
        assert validate_item_v3(
            _item(form="fill", acceptable_variants=bad)
        ) == [f"i1: acceptable_variants must be a list, got {bad!r}"]
    assert validate_item_v3(_item(form="fill", acceptable_variants=[])) == [
        "i1: acceptable_variants must be non-empty"
    ]


def test_variant_element_rules():
    assert validate_item_v3(_item(form="fill", acceptable_variants=[" 1/2", "", 5, "0.5"])) == [
        "i1: bad acceptable_variant ' 1/2'",
        "i1: bad acceptable_variant ''",
        "i1: bad acceptable_variant 5",
    ]
    assert validate_item_v3(_item(form="fill", acceptable_variants=["0.5", "1/2 "])) == [
        "i1: bad acceptable_variant '1/2 '"
    ]
    assert validate_item_v3(_item(form="fill", acceptable_variants=[None, True, ["x"]])) == [
        "i1: bad acceptable_variant None",
        "i1: bad acceptable_variant True",
        "i1: bad acceptable_variant ['x']",
    ]


def test_variant_duplicate_rules():
    assert validate_item_v3(_item(form="fill", acceptable_variants=["a", "a"])) == [
        "i1: duplicate acceptable_variants"
    ]
    assert validate_item_v3(_item(form="fill", acceptable_variants=["a", "b", "a"])) == [
        "i1: duplicate acceptable_variants"
    ]
    # 判重比较域 = 原始字面值（不 strip）："a" != "a " → 不判重（只报坏元素）
    assert validate_item_v3(_item(form="fill", acceptable_variants=["a", "a "])) == [
        "i1: bad acceptable_variant 'a '"
    ]
    # 坏元素消息在前、判重消息在后（与 v2 的 C2→C3 同构）
    assert validate_item_v3(_item(form="fill", acceptable_variants=[" b", " b"])) == [
        "i1: bad acceptable_variant ' b'",
        "i1: bad acceptable_variant ' b'",
        "i1: duplicate acceptable_variants",
    ]
    assert validate_item_v3(_item(form="fill", acceptable_variants=["a", "a", " b"])) == [
        "i1: bad acceptable_variant ' b'",
        "i1: duplicate acceptable_variants",
    ]


# ---------- F3 scoring_points ----------


def test_scoring_points_valid():
    assert validate_item_v3(_item(scoring_points=[
        {"point": "设未知数", "score": 2},
        {"point": "列方程", "score": 3},
    ])) == []
    # 分值可为小数；与题型无关（任何 form 都可带）
    assert validate_item_v3(_item(form="choice", scoring_points=[{"point": "p", "score": 0.5}])) == []


def test_scoring_points_type_and_empty():
    for bad in (("a",), "x", None, {"point": "p", "score": 1}, 42):
        assert validate_item_v3(
            _item(scoring_points=bad)
        ) == [f"i1: scoring_points must be a list, got {bad!r}"]
    assert validate_item_v3(_item(scoring_points=[])) == ["i1: scoring_points must be non-empty"]


def test_scoring_point_entry_rules():
    # 形状门：非 dict / 键集合非恰 {point,score}（缺失或多余键同消息，不再拆分）
    for bad in (42, ["point", "score"], {"point": "p"}, {"score": 1},
                {"point": "p", "score": 1, "extra": 0}):
        assert validate_item_v3(_item(scoring_points=[bad])) == [f"i1: bad scoring_point {bad!r}"]
    # point 必须为非空白 str
    for bad in ("", "   ", 5, None, ["p"]):
        assert validate_item_v3(_item(scoring_points=[{"point": bad, "score": 1}])) == [
            f"i1: scoring_point point must be a non-blank str, got {bad!r}"
        ]
    # score 必须为有限实数且 > 0（bool/ NaN / inf / 字符串同拒）
    for bad in (0, -1, True, False, "3", None, float("nan"), float("inf")):
        assert validate_item_v3(_item(scoring_points=[{"point": "p", "score": bad}])) == [
            f"i1: scoring_point score must be a number > 0, got {bad!r}"
        ]
    # 同一条目 point/score 双坏 → 按 point → score 序两条
    assert validate_item_v3(_item(scoring_points=[{"point": "", "score": 0}])) == [
        "i1: scoring_point point must be a non-blank str, got ''",
        "i1: scoring_point score must be a number > 0, got 0",
    ]
    # 多条目按列表序逐条报
    assert validate_item_v3(_item(scoring_points=[
        {"point": "ok", "score": 1},
        {"point": "", "score": 1},
        "bad",
    ])) == [
        "i1: scoring_point point must be a non-blank str, got ''",
        "i1: bad scoring_point 'bad'",
    ]


def test_variants_and_scoring_points_mutually_exclusive():
    both = ["i1: acceptable_variants and scoring_points are mutually exclusive"]
    assert validate_item_v3(_item(form="fill", acceptable_variants=["a"],
                                  scoring_points=[{"point": "p", "score": 1}])) == both
    # 可都无
    assert validate_item_v3(_item(form="fill")) == []
    # 仅带其一且合法（已在其它条覆盖）；互斥消息之后各自的值校验照常累积
    assert validate_item_v3(_item(form="fill", acceptable_variants="x", scoring_points=[])) == [
        "i1: acceptable_variants and scoring_points are mutually exclusive",
        "i1: acceptable_variants must be a list, got 'x'",
        "i1: scoring_points must be non-empty",
    ]


# ---------- F4 rubric ----------


def test_rubric_required_for_essay_only():
    missing = ["i1: essay requires rubric"]
    assert validate_item_v3(_item(form="essay")) == missing
    assert validate_item_v3(_item(form="essay", rubric=None)) == ["i1: bad rubric None"]
    # 合法 rubric 过门（多维度、小数分值、和 == total）
    ok = _rubric([_dim("甲", 2), _dim("乙", 3)], 5)
    assert validate_item_v3(_item(form="essay", rubric=ok)) == []
    # 非 essay 或缺 form 时 rubric 可选：不带不报，带也全量校验
    assert validate_item_v3(_item(form="choice")) == []
    assert validate_item_v3(_item(form="choice", rubric=ok)) == []
    assert validate_item_v3(_item(rubric=ok)) == []
    # form 成员判定用原始值：" essay " 不是 essay（不 strip 归一化）
    assert validate_item_v3(_item(form=" essay ")) == ["i1: bad form ' essay '"]


def test_rubric_structure_rules():
    for bad in ("x", [], 42, None, {"total": 5}, {"dimensions": []},
                {"total": 5, "dimensions": [], "extra": 1}):
        assert validate_item_v3(_item(rubric=bad)) == [f"i1: bad rubric {bad!r}"]
    for bad in (0, -1, True, "5", None, float("nan")):
        assert validate_item_v3(_item(rubric={"total": bad, "dimensions": [_dim()]})) == [
            f"i1: rubric total must be a number > 0, got {bad!r}"
        ]
    for bad in ("x", [], {}, None, 42):
        assert validate_item_v3(_item(rubric={"total": 5, "dimensions": bad})) == [
            f"i1: rubric dimensions must be a non-empty list, got {bad!r}"
        ]


def test_rubric_dimension_and_level_rules():
    base = lambda dims: {"total": 5, "dimensions": dims}
    # 维度形状门
    for bad in ("x", 42, {"name": "甲", "max_score": 5}, {"name": "甲", "max_score": 5,
                "level_descriptors": [], "x": 1}):
        assert validate_item_v3(_item(rubric=base([bad]))) == [f"i1: bad rubric dimension {bad!r}"]
    # name / max_score
    assert validate_item_v3(_item(rubric=base([_dim(name="")]))) == [
        "i1: rubric dimension name must be a non-blank str, got ''"
    ]
    assert validate_item_v3(_item(rubric=base([_dim(name=7)]))) == [
        "i1: rubric dimension name must be a non-blank str, got 7"
    ]
    for bad in (0, -1, True, "2", None):
        assert validate_item_v3(_item(rubric=base([_dim(max_score=bad)]))) == [
            f"i1: rubric dimension max_score must be a number > 0, got {bad!r}"
        ]
    # level_descriptors 必须为非空 list（None 也不能借默认构造蒙混——直接手写 dict）
    for bad in ("x", [], None, {}):
        dim = {"name": "甲", "max_score": 5, "level_descriptors": bad}
        assert validate_item_v3(_item(rubric={"total": 5, "dimensions": [dim]})) == [
            f"i1: rubric dimension level_descriptors must be a non-empty list, got {bad!r}"
        ]
    # 逐级：形状门 → level → min_score → desc
    for bad in ("x", 42, {"level": "A", "min_score": 0}, {"level": "A", "min_score": 0,
                "desc": "d", "x": 1}):
        assert validate_item_v3(_item(rubric=base([_dim(levels=[bad])]))) == [
            f"i1: bad rubric level {bad!r}"
        ]
    assert validate_item_v3(_item(rubric=base([_dim(levels=[{"level": "", "min_score": 0,
                                                            "desc": "d"}])]))) == [
        "i1: rubric level must be a non-blank str, got ''"
    ]
    assert validate_item_v3(_item(rubric=base([_dim(levels=[{"level": "A", "min_score": -1,
                                                            "desc": "d"}])]))) == [
        "i1: rubric level min_score must be a number >= 0, got -1"
    ]
    assert validate_item_v3(_item(rubric=base([_dim(levels=[{"level": "A", "min_score": True,
                                                            "desc": "d"}])]))) == [
        "i1: rubric level min_score must be a number >= 0, got True"
    ]
    assert validate_item_v3(_item(rubric=base([_dim(levels=[{"level": "A", "min_score": 0,
                                                            "desc": "  "}])]))) == [
        "i1: rubric level desc must be a non-blank str, got '  '"
    ]
    # min_score = 0 合法（>= 0 闭端）
    assert validate_item_v3(_item(rubric=_rubric(
        [_dim("甲", 5, [{"level": "A", "min_score": 0, "desc": "起步"}])], 5))) == []


def test_rubric_duplicate_dimension_names():
    dup = ["i1: duplicate rubric dimension names"]
    assert validate_item_v3(_item(rubric=_rubric([_dim("甲"), _dim("甲")], 10))) == dup
    assert validate_item_v3(_item(rubric=_rubric([_dim("甲"), _dim("乙"), _dim("甲")], 15))) == dup
    assert validate_item_v3(_item(rubric=_rubric([_dim("甲"), _dim("乙")], 10))) == []
    # 非 str name 不参与判重；判重消息恒在全部逐维消息之后
    assert validate_item_v3(_item(rubric=_rubric(
        [_dim(levels=[{"level": "", "min_score": 0, "desc": "d"}]), _dim(name=7), _dim("甲"),
         _dim("甲")], 20))) == [
        "i1: rubric level must be a non-blank str, got ''",
        "i1: rubric dimension name must be a non-blank str, got 7",
        "i1: duplicate rubric dimension names",
    ]


def test_rubric_sum_rule():
    # 和 != total（精确相等比较）
    assert validate_item_v3(_item(rubric=_rubric([_dim("甲", 2), _dim("乙", 3)], 6))) == [
        "i1: rubric dimensions max_score sum 5 != total 6"
    ]
    # 和 == total：整数与干净小数均可（5.0 == 5）
    assert validate_item_v3(_item(rubric=_rubric([_dim("甲", 2), _dim("乙", 3)], 5))) == []
    assert validate_item_v3(_item(rubric=_rubric([_dim("甲", 2.5), _dim("乙", 2.5)], 5))) == []
    assert validate_item_v3(_item(rubric=_rubric([_dim("甲", 5)], 5.0))) == []
    # 门控：max_score 有非法分量时不评估和（只报分量错，不叠加和错）
    assert validate_item_v3(_item(rubric=_rubric([_dim("甲", 2), _dim("乙", 0)], 2))) == [
        "i1: rubric dimension max_score must be a number > 0, got 0"
    ]
    # 门控：total 非法时不评估和
    assert validate_item_v3(_item(rubric=_rubric([_dim("甲", 2), _dim("乙", 3)], "5"))) == [
        "i1: rubric total must be a number > 0, got '5'"
    ]


# ---------- F5 textbook_ref ----------


def test_textbook_ref_rules():
    for good in ("pep:g5:u3", "bnup:g9:u12", "a1:b2:c3", "rj:g8:u10"):
        assert validate_item_v3(_item(textbook_ref=good)) == []
    for bad in ("PEP:g5:u3", "pep:g5", "pep:g5:u3:x", "pep::u3", "pep:g5:", "pep:g5:u3 ",
                " pep:g5:u3", "pep:g5:u_3", "pep-g5-u3", "", 42, None, ["pep:g5:u3"]):
        assert validate_item_v3(_item(textbook_ref=bad)) == [f"i1: bad textbook_ref {bad!r}"]


# ---------- 累积顺序 / 前缀 / 全函数 ----------


def test_rule_accumulation_order():
    # F1 → F2a → F2b → F3 → F5 全触发时的固定消息序
    assert validate_item_v3(_item(
        id="x", form="nope", acceptable_variants=["a"], scoring_points=[], textbook_ref="BAD"
    )) == [
        "x: bad form 'nope'",
        "x: acceptable_variants and scoring_points are mutually exclusive",
        "x: acceptable_variants requires form in fill/solve/essay/proof",
        "x: scoring_points must be non-empty",
        "x: bad textbook_ref 'BAD'",
    ]
    # essay + 坏 rubric + 坏 textbook_ref：F4a → F4b/c/d → F5
    assert validate_item_v3(_item(
        id="y", form="essay", textbook_ref="bad", rubric={"total": 6, "dimensions": [_dim("甲", 2)]}
    )) == [
        "y: rubric dimensions max_score sum 2 != total 6",
        "y: bad textbook_ref 'bad'",
    ]


def test_id_prefix_rendering():
    assert validate_item_v3({"form": 42}) == ["<no-id>: bad form 42"]
    assert validate_item_v3({"id": None, "form": 42}) == ["None: bad form 42"]
    assert validate_item_v3({"id": 42, "form": 42}) == ["42: bad form 42"]
    assert validate_item_v3({"id": "", "form": 42}) == [": bad form 42"]
    assert validate_item_v3({"id": {"x": 1}, "form": 42}) == ["{'x': 1}: bad form 42"]


def test_never_raises_battery():
    nasty = [
        {},
        {"form": {}},
        {"form": ["choice"]},
        {"acceptable_variants": {}},
        {"acceptable_variants": [{}]},
        {"scoring_points": [{"point": {"a": 1}, "score": {"b": 2}}]},
        {"rubric": {"total": {"a": 1}, "dimensions": [{"name": {"b": 2}, "max_score": [1],
                                                       "level_descriptors": [{"level": 1,
                                                                              "min_score": "x",
                                                                              "desc": None}]}]}},
        {"textbook_ref": {}},
        {"id": {"x": 1}, "form": 9.5, "acceptable_variants": 3.14, "scoring_points": True,
         "rubric": [], "textbook_ref": ()},
        {"form": "essay", "rubric": {"total": 1, "dimensions": [_dim(), "x"]}},
    ]
    for item in nasty:
        result = validate_item_v3(item)
        assert isinstance(result, list)
        assert all(isinstance(e, str) for e in result)
        # 全函数性：任何输入都必须有结论性输出（合法夹具零消息）
        if item == {}:
            assert result == []


# ---------- bank 级 ----------


def test_items_v3_accumulates_in_input_order_without_dedup():
    bad1 = _item(id="b1", form=42)
    bad2 = _item(id="b2", textbook_ref="X")
    ok = _item(id="ok", form="fill", acceptable_variants=["a"])
    assert validate_items_v3([bad1, bad2, ok]) == (
        validate_item_v3(bad1) + validate_item_v3(bad2) + validate_item_v3(ok))
    assert validate_items_v3([]) == []
    # 不去重：同一坏题出现两次，消息重复两次
    assert validate_items_v3([bad1, bad1]) == validate_item_v3(bad1) * 2
    # 非 dict 元素各产一条后继续
    assert validate_items_v3([None, {"form": 42}, 7]) == [
        "item is not a dict",
        "<no-id>: bad form 42",
        "item is not a dict",
    ]


def test_items_v3_non_iterable_propagates_typeerror():
    with pytest.raises(TypeError):
        validate_items_v3(42)


# ---------- 纯函数性 ----------


def test_purity_inputs_not_modified_and_repeatable():
    items = [
        _item(id="p1", form="fill", acceptable_variants=["a", " b"]),
        _item(id="p2", form="essay", rubric={"total": 5, "dimensions": [_dim(), _dim("乙", 0)]}),
        _item(id="p3", scoring_points=[{"point": "p", "score": 1}], textbook_ref="pep:g5:u3"),
    ]
    snapshot = copy.deepcopy(items)
    first = validate_items_v3(items)
    assert items == snapshot  # 入参不被修改（含嵌套 dict/list）
    assert validate_items_v3(items) == first  # 同输入同输出
    # 模块级常量不被调用污染
    assert FORM_VALUES[0] == "choice"


# ---------- 与冻结模块 itembank_v2 的边界（跨模块锁定） ----------


def test_boundary_with_v2_fields_is_layered():
    from xuexing.itembank_v2 import validate_item_v2

    # v3 干净但 v2 脏：v3 不检查 v2 字段（source/verification 归 v2 管）
    item = _item(id="m", source="scraped", form="fill", acceptable_variants=["a"])
    assert validate_item_v3(item) == []
    assert validate_item_v2(item) == ["m: bad source 'scraped'"]
    # 两者都干净：完整 v3 入库校验 = 消息拼接后为空
    ok = _item(id="n", source="original", form="fill", acceptable_variants=["a"],
               textbook_ref="pep:g5:u3")
    assert validate_item_v3(ok) == []
    assert validate_item_v2(ok) == []
    assert validate_item_v3(ok) + validate_item_v2(ok) == []
