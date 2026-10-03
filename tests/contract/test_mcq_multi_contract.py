"""契约：多选子题型 mcq_multi（form="mcq_multi" + answer_mode="subset"）。

一条子题型扩展同时落在三个冻结面上，故本文件把三面钉在同一组用例上：
- itembank：R9b-m 校验（拆分后每项在 labels 集内、项数 >=1、不重复）
- grading：label 集合等值判（顺序无关、部分作答判错、key 解析不到抛 GradingError）
- dual_verify：盲解比对按同一集合语义

非 mcq_multi 的题目行为与本扩展无关，全部沿用单选路径（见各节的回归断言）。
"""
import pytest

from xuexing.dual_verify import answers_match
from xuexing.grading import GradingError, grade_choice
from xuexing.itembank import ANSWER_MODES, ItemBank, split_multi_answer
from xuexing.types import Item

OPTS = ["A. 甲正确", "B. 乙正确", "C. 丙正确", "D. 丁错误"]


def _item(answer, form="mcq_multi", item_id="m1", options=None, answer_mode="subset"):
    return Item(
        id=item_id, item_type="choice", stem="stem", answer=answer,
        kps=["k"], difficulty=0.5, options=OPTS if options is None else options,
        form=form, answer_mode=answer_mode,
    )


# ---------- itembank：R9b-m ----------

def test_multi_answer_splits_on_every_separator():
    assert split_multi_answer("A,D") == ["A", "D"]
    assert split_multi_answer("A 和 D") == ["A", "D"]
    assert split_multi_answer("A、C、D") == ["A", "C", "D"]
    assert split_multi_answer("A, C;D") == ["A", "C", "D"]
    assert split_multi_answer("B") == ["B"]


def test_multi_answer_accepts_labels_and_rejects_rest():
    b = ItemBank()
    assert b.validate_item(_item("A,D")) == []
    assert b.validate_item(_item("A, C, D")) == []
    # 旧的多字母写法在多选形态下同样放行（拆分后每项都在 labels 集内）
    assert b.validate_item(_item("A 和 D")) == []
    assert b.validate_item(_item("A,C,D")) == []
    bad = b.validate_item(_item("A,E"))
    assert [e for e in bad if "answer not among options" in e] == ["m1: answer not among options"]
    assert b.validate_item(_item("A,A")) == ["m1: mcq_multi answer repeats a label"]
    assert b.validate_item(_item("，、")) == ["m1: mcq_multi answer has no option label"]


def test_single_choice_regression_still_rejects_multi_answer():
    b = ItemBank()
    assert b.validate_item(_item("B", form="mcq_single")) == []
    assert b.validate_item(_item("A,D", form="mcq_single")) == ["m1: answer not among options"]
    # 默认形态（form 缺省为 choice）走单选路径
    default = Item(id="d1", item_type="choice", stem="s", answer="A,D", kps=["k"],
                   difficulty=0.5, options=OPTS)
    assert b.validate_item(default) == ["d1: answer not among options"]


def test_answer_mode_enum_is_closed():
    b = ItemBank()
    assert ANSWER_MODES == ("exact", "subset")
    assert b.validate_item(_item("A,D", answer_mode="exact")) == []
    assert b.validate_item(_item("A,D", answer_mode="prefix")) == ["m1: bad answer_mode 'prefix'"]
    # answer_mode 门与题型无关（fill 题同样受门）
    fill = Item(id="f1", item_type="fill", stem="s", answer="x", kps=["k"],
                difficulty=0.5, answer_mode="subset!")
    assert b.validate_item(fill) == ["f1: bad answer_mode 'subset!'"]


# ---------- grading：集合等值 ----------

def test_multi_grading_is_set_equality():
    it = _item("A,D")
    assert grade_choice(it, "A,D") is True
    assert grade_choice(it, "A, D") is True          # 空白归一
    assert grade_choice(it, "D,A") is True           # 顺序无关
    assert grade_choice(it, "a，d") is True          # 大小写 + 全角逗号
    assert grade_choice(it, "A") is False            # 部分作答判错（无部分分）
    assert grade_choice(it, "A,B,D") is False        # 多选一项即错
    assert grade_choice(it, "A,C,D") is False
    assert grade_choice(it, "E") is False            # 未知 token
    assert grade_choice(it, "") is False            # 空白作答
    assert grade_choice(it, None) is False


def test_multi_grading_accepts_full_text_tokens():
    it = _item("A,D")
    assert grade_choice(it, "A.甲正确,D.丁错误") is True   # 按选项全文作答
    assert grade_choice(it, "A. 甲正确, D. 丁错误") is True


def test_multi_grading_raises_on_unresolvable_key():
    with pytest.raises(GradingError):
        grade_choice(_item("A,E"), "A,D")
    with pytest.raises(GradingError):
        grade_choice(_item("A,A"), "A,D")
    with pytest.raises(GradingError):
        grade_choice(_item("，、"), "A,D")


def test_single_choice_regression_still_single():
    it = _item("B", form="mcq_single", answer_mode="exact")
    assert grade_choice(it, "B") is True
    assert grade_choice(it, "B. 乙正确") is True
    assert grade_choice(it, "A") is False
    with pytest.raises(GradingError):        # 标答解析不到：多选不会误吞
        grade_choice(_item("A,D", form="mcq_single", answer_mode="exact"), "A")
    # 鸭子类型题（无 form 属性）默认走单选路径
    duck = Item(id="k1", item_type="choice", stem="s", answer="B", kps=["k"],
                difficulty=0.5, options=OPTS)
    assert grade_choice(duck, "B") is True
    assert grade_choice(duck, "B,D") is False


# ---------- dual_verify：盲解比对同口径 ----------

def test_answers_match_multi_uses_set_equality():
    assert answers_match("A,D", "A,D", "choice", OPTS) is True
    assert answers_match("A,D", "D,A", "choice", OPTS) is True
    assert answers_match("A,D", "A, D", "choice", OPTS) is True
    assert answers_match("A,D", "A", "choice", OPTS) is False
    assert answers_match("A,D", "A,B,D", "choice", OPTS) is False
    assert answers_match("A,D", "A,E", "choice", OPTS) is False
    # 顺序敏感的是单选，不是多选：单选行为零回归
    assert answers_match("B", "B", "choice", OPTS) is True
    assert answers_match("B", "A", "choice", OPTS) is False
    assert answers_match("B", "B. 乙正确", "choice", OPTS) is True
    assert answers_match("E", "B", "choice", OPTS) is False
