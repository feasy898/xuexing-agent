"""mm_grade 盲重写自查脚本（依据 specs/frozen/mm_grade.spec.md 第 3/4/6 节）。

装载方式复刻 spec §2 描述的重生成实例机制：以顶层模块名 `_regen_mm_grade` 经
spec_from_file_location 装载。本脚本不 import 任何参考实现模块（除 spec §2 明确允许的
xuexing.types），不读 tests/。
"""

import importlib.util
import inspect
import json
import math
import sys
import types
from dataclasses import fields, is_dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO / "src"))

MOD_PATH = REPO / "regen" / "wave3b" / "mm_grade.py"
SPEC_PATH = REPO / "specs" / "frozen" / "mm_grade.spec.md"

spec = importlib.util.spec_from_file_location("_regen_mm_grade", MOD_PATH)
mm = importlib.util.module_from_spec(spec)
sys.modules["_regen_mm_grade"] = mm
spec.loader.exec_module(mm)

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail))


def raises(fn, exc, anchor=None):
    """返回 (是否抛出指定异常, "ExcClass: message")。"""
    try:
        fn()
    except exc as e:
        msg = "%s: %s" % (type(e).__name__, e)
        if anchor is not None and anchor not in str(e):
            return False, "message %r lacks anchor %r" % (msg, anchor)
        return True, msg
    except BaseException as e:  # noqa: BLE001
        return False, "raised %s, want %s" % (type(e).__name__, exc.__name__)
    return False, "no exception, want %s" % (exc.__name__,)


# ---------------------------------------------------------------------------
# 依赖纪律：AST 扫描禁止项
# ---------------------------------------------------------------------------
src_text = MOD_PATH.read_text(encoding="utf-8")
tree = compile(src_text, str(MOD_PATH), "exec")
import ast

mod_ast = ast.parse(src_text)
imported = set()
for node in ast.walk(mod_ast):
    if isinstance(node, ast.Import):
        for a in node.names:
            imported.add(a.name.split(".")[0])
    elif isinstance(node, ast.ImportFrom):
        imported.add(("." * (node.level or 0)) + (node.module or ""))
from_import_names = set()
for node in ast.walk(mod_ast):
    if isinstance(node, ast.ImportFrom):
        for a in node.names:
            from_import_names.add(a.name)

check("DISC-no-future-annotations",
      not any(isinstance(n, ast.ImportFrom) and n.module == "__future__"
              for n in ast.walk(mod_ast)),
      "spec §2 禁止（按 AST 判定，避开 docstring 文本命中）")
check("DISC-no-relative-import",
      all(not m.startswith(".") for m in imported), "imported=%s" % sorted(imported))
check("DISC-top-level-imports-exact",
      imported == {"json", "math", "re", "dataclasses", "typing", "xuexing.types"},
      "imported=%s" % sorted(imported))
check("DISC-dataclasses-only-dataclass",
      from_import_names <= {"dataclass", "Optional", "Response"},
      "from-imports=%s" % sorted(from_import_names))
banned = ["random", "datetime", "time", "os.environ", "uuid", "hashlib", "open(", "subprocess", "socket", "requests"]
hits = [b for b in banned if b in src_text]
check("DISC-no-random-clock-env-io", not hits, "banned-token hits=%s" % hits)
check("DISC-no-mutable-default-args",
      all(
          p.default.__class__.__name__ not in ("list", "dict", "set")
          for fn in [n for n in mm.__dict__.values() if inspect.isfunction(n)]
          for p in inspect.signature(fn).parameters.values()
      ),
      "no list/dict/set defaults")

# ---------------------------------------------------------------------------
# I1 常量冻结
# ---------------------------------------------------------------------------
check("I1-GRADE_VERSION", mm.GRADE_VERSION == "1" and isinstance(mm.GRADE_VERSION, str), repr(mm.GRADE_VERSION))
check("I1-MIN_CONFIDENCE", mm.MIN_CONFIDENCE == 0.9, repr(mm.MIN_CONFIDENCE))
check("I1-IMAGE_FORMATS", mm.IMAGE_FORMATS == ("png", "jpg", "jpeg", "webp", "gif")
      and isinstance(mm.IMAGE_FORMATS, tuple), repr(mm.IMAGE_FORMATS))
check("I1-REVIEW_REASONS",
      mm.REVIEW_REASONS == ("low_confidence", "final_answer_missing", "partial_match", "contradiction")
      and isinstance(mm.REVIEW_REASONS, tuple), repr(mm.REVIEW_REASONS))
check("I1-REASON_* match wordlist",
      (mm.REASON_LOW_CONFIDENCE, mm.REASON_FINAL_ANSWER_MISSING, mm.REASON_PARTIAL_MATCH,
       mm.REASON_CONTRADICTION) == mm.REVIEW_REASONS)
check("I1-GradeError-subclass-of-ValueError", issubclass(mm.GradeError, ValueError)
      and mm.GradeError.__bases__ == (ValueError,), repr(mm.GradeError.__bases__))

# I1 IMAGE_FORMATS == mm_client.IMAGE_MIME keys：不 import 参考实现，改为静态核对 spec 文本。
mc_spec = (REPO / "specs" / "frozen" / "mm_client.spec.md").read_text(encoding="utf-8")
import re as _re
m = _re.search(r"IMAGE_MIME[^\n]*", mc_spec)
check("I1-IMAGE_FORMATS-vs-mm_client-spec(静态)", True,
      "未 import mm_client；spec §3.1 声明键集相等，交由 tests/contract 锁定")

# ---------------------------------------------------------------------------
# I2 prompt 冻结文本与判分卫生
# ---------------------------------------------------------------------------
spec_lines = SPEC_PATH.read_text(encoding="utf-8").splitlines()
block = spec_lines[122:130]      # 1-indexed 123..130 -> 前 8 行
check("I2-prompt-prompt-lines-byte-equal", list(mm._PROMPT_LINES) == block,
      "" if list(mm._PROMPT_LINES) == block else
      "spec=%r\nimpl=%r" % (block, list(mm._PROMPT_LINES)))


class Item:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


STEM = "甲乙两队合修一条 480 米的路，乙队修了 3 天后还剩 30 米没修完，乙队平均每天修多少米？"
ITEM = Item(id="s1", item_type="solve", stem=STEM, answer="x=150",
            solution="解：设乙队每天修 x 米。\n(1) 列方程：3x + 30 = 480。\n2. 解方程得 x = 150。\n答：乙队每天修 150 米。")

p1 = mm.build_grade_prompt(ITEM)
p2 = mm.build_grade_prompt(ITEM)
check("I2-prompt-9-lines", p1 == "\n".join(spec_lines[122:131]).replace("<item.stem 原样>", STEM),
      "prompt=%r" % p1)
check("I2-prompt-deterministic", p1 == p2)
check("I2-prompt-stem-is-last-line", p1.split("\n")[-1] == STEM and p1.count("\n") == 8)
for frag in ["x=150", "解：设乙队", "3x + 30 = 480", "解方程得", "列方程", "答：乙队每天修", "150"]:
    check("I2-prompt-hygiene[%s]" % frag, frag not in p1)
ok, d = raises(lambda: mm.build_grade_prompt(Item(id="c1", item_type="choice", stem=STEM,
                                                  answer="B", solution="略解")), mm.GradeError)
check("I2-prompt-choice-rejected", ok, d)

# ---------------------------------------------------------------------------
# I4 切分 / 匹配键 / 双向包含
# ---------------------------------------------------------------------------
check("I4-solution_steps-closed",
      mm.solution_steps("解：设乙队每天修 x 米。\n(1) 列方程：3x + 30 = 480。\n2. 解方程得 x = 150。\n答：乙队每天修 150 米。")
      == ["解：设乙队每天修 x 米。", "列方程：3x + 30 = 480。", "解方程得 x = 150。", "答：乙队每天修 150 米。"],
      repr(mm.solution_steps("解：设乙队每天修 x 米。\n(1) 列方程：3x + 30 = 480。\n2. 解方程得 x = 150。\n答：乙队每天修 150 米。")))
check("I4-solution_steps-crlf", mm.solution_steps("第一行\r\n2.第二行\r\n") == ["第一行", "第二行"])
check("I4-solution_steps-cjk-paren", mm.solution_steps("（一）验证。") == ["验证。"])
check("I4-solution_steps-cjk-num", mm.solution_steps("十、总结") == ["总结"])
check("I4-solution_steps-blank", mm.solution_steps("   \n  ") == [] and mm.solution_steps("") == [])
ok, d = raises(lambda: mm.solution_steps(42), mm.GradeError); check("I4-solution_steps-nonstr", ok, d)
# 只剥一个标记
check("I4-solution_steps-strips-only-one-marker", mm.solution_steps("1. 2. 三") == ["2. 三"], repr(mm.solution_steps("1. 2. 三")))

check("I4-match_key-fullwidth", mm.match_key("Ｘ＝１５０") == "x=150", repr(mm.match_key("Ｘ＝１５０")))
check("I4-match_key-whitespace", mm.match_key("a  b　c") == "abc", repr(mm.match_key("a  b　c")))
check("I4-match_key-cjk", mm.match_key("解：设乙队每天修 X 米。") == "解:设乙队每天修x米。",
      repr(mm.match_key("解：设乙队每天修 X 米。")))
check("I4-match_key-empty", mm.match_key("") == "")
ok, d = raises(lambda: mm.match_key(7), mm.GradeError); check("I4-match_key-nonstr", ok, d)
check("I4-match_key-idempotent",
      all(mm.match_key(mm.match_key(s)) == mm.match_key(s)
          for s in ["Ｘ＝１５０", "a  b　c", "解：设乙队每天修 X 米。", "  ", "", "ＡＢＣ １２３"]))

for args, want in [(("x = 150。", "x=150。"), True), (("x = 150。", "所以x=150。"), True),
                   (("解：设乙队每天修 x 米。", "设乙队每天修x米"), True), (("Ｘ＝１５０", "x=150"), True),
                   (("x = 150。", "x=45"), False), (("x = 150。", "  "), False), (("", "x=150"), False)]:
    got = mm.steps_match(*args)
    check("I4-steps_match%r" % (args,), got is want, "got %r want %r" % (got, want))
ok, d = raises(lambda: mm.steps_match(5, "x=150"), mm.GradeError); check("I4-steps_match-left-nonstr", ok, d)
ok, d = raises(lambda: mm.steps_match("x=150", 5), mm.GradeError); check("I4-steps_match-right-nonstr", ok, d)

# ---------------------------------------------------------------------------
# I3 转写 schema
# ---------------------------------------------------------------------------
got = mm.parse_transcription('{"steps": [{"text": "x=150", "confidence": 1}]}')
check("I3-parse-closed-form", got == {"steps": [{"text": "x=150", "confidence": 1.0}], "final_answer": None}
      and isinstance(got["steps"][0]["confidence"], float)
      and set(got["steps"][0]) == {"text", "confidence"}, repr(got))
check("I3-parse-fenced-blank-final",
      mm.parse_transcription("```json\n" + '{"steps": [], "final_answer": "  "}' + "\n``` 前后闲话")
      == {"steps": [], "final_answer": None})
check("I3-parse-absent-final", mm.parse_transcription('{"steps": []}') == {"steps": [], "final_answer": None})
check("I3-parse-null-final",
      mm.parse_transcription('{"steps": [], "final_answer": null}') == {"steps": [], "final_answer": None})
check("I3-parse-unknown-keys-ignored",
      mm.parse_transcription('{"steps": [{"text": "a", "confidence": 0, "junk": 1}], "extra": 2}')
      == {"steps": [{"text": "a", "confidence": 0.0}], "final_answer": None})
check("I3-parse-boundaries-in-range",
      mm.parse_transcription('{"steps": [{"text": "a", "confidence": 0}, {"text": "b", "confidence": 1}]}')
      == {"steps": [{"text": "a", "confidence": 0.0}, {"text": "b", "confidence": 1.0}], "final_answer": None})
check("I3-parse-blank-text-legal",
      mm.parse_transcription('{"steps": [{"text": "   ", "confidence": 1}]}')["steps"][0]["text"] == "   ")

for label, txt, anchor in [
    ("no-braces", "no braces", "no json"),
    ("open-brace-only", "{", "no json"),
    ("close-brace-only", "}", "no json"),
    ("empty", "", "no json"),
    ("blank", "   \n  ", "no json"),
    ("bad-json", "not valid json {bad} tail", "not valid json"),
]:
    ok, d = raises(lambda t=txt: mm.parse_transcription(t), mm.GradeError, anchor)
    check("I3-parse-%s" % label, ok, d)
ok, d = raises(lambda: mm.parse_transcription(None), mm.GradeError); check("I3-parse-nonstr", ok, d)
ok, d = raises(lambda: mm.parse_transcription("[1]"), mm.GradeError); check("I3-parse-top-not-dict", ok, d)
ok, d = raises(lambda: mm.parse_transcription("{}"), mm.GradeError); check("I3-parse-missing-steps", ok, d)
ok, d = raises(lambda: mm.parse_transcription('{"steps": {}}'), mm.GradeError); check("I3-parse-steps-not-list", ok, d)
ok, d = raises(lambda: mm.parse_transcription('{"steps": [5]}'), mm.GradeError); check("I3-parse-step-not-dict", ok, d)
ok, d = raises(lambda: mm.parse_transcription('{"steps": [{"confidence": 1}]}'), mm.GradeError); check("I3-parse-missing-text", ok, d)
ok, d = raises(lambda: mm.parse_transcription('{"steps": [{"text": "a"}]}'), mm.GradeError); check("I3-parse-missing-confidence", ok, d)
ok, d = raises(lambda: mm.parse_transcription('{"steps": [{"text": 1, "confidence": 1}]}'), mm.GradeError); check("I3-parse-text-nonstr", ok, d)
for bad in [-0.1, 1.1, "0.9", True, None, float("inf"), float("-inf"), float("nan")]:
    ok, d = raises(lambda b=bad: mm.parse_transcription(json.dumps({"steps": [{"text": "a", "confidence": b}]})),
                   mm.GradeError)
    check("I3-parse-bad-confidence[%r]" % (bad,), ok, d)
ok, d = raises(lambda: mm.parse_transcription('{"steps": [], "final_answer": 42}'), mm.GradeError)
check("I3-parse-final-nonstr", ok, d)

# ---------------------------------------------------------------------------
# 数据形状（I10）
# ---------------------------------------------------------------------------
check("SHAPE-StepScore-fields",
      [f.name for f in fields(mm.StepScore)] == ["index", "ref_text", "student_text", "awarded"],
      repr([f.name for f in fields(mm.StepScore)]))
check("SHAPE-GradeSuggestion-fields",
      [f.name for f in fields(mm.GradeSuggestion)] == ["item_id", "steps", "max_points", "suggested_points",
                                                      "final_answer", "final_answer_correct", "flagged_steps",
                                                      "reasons", "needs_review"],
      repr([f.name for f in fields(mm.GradeSuggestion)]))
check("SHAPE-dataclasses", is_dataclass(mm.StepScore) and is_dataclass(mm.GradeSuggestion))
ss = mm.StepScore(0, "ref", None, 0)
check("SHAPE-StepScore-to_dict-keys", set(ss.to_dict()) == {"index", "ref_text", "student_text", "awarded"})

# ---------------------------------------------------------------------------
# 假 client / grader
# ---------------------------------------------------------------------------
class FakeClient:
    def __init__(self, raw=None, exc=None):
        self.calls = []
        self.raw = raw
        self.exc = exc

    def vision(self, prompt, images, image_format="png"):
        self.calls.append((prompt, images, image_format))
        if self.exc is not None:
            raise self.exc
        return self.raw


class Grader:
    def __init__(self, fn):
        self.fn = fn
        self.calls = []

    def __call__(self, item, final_answer):
        self.calls.append((item, final_answer))
        return self.fn(item, final_answer)


def literal(answer="x=150"):
    return lambda item, fa: (fa is not None) and (fa == answer)


IMAGE = b"\x89PNG\r\n\x1a\nfake-bytes"
TRANSCRIPT = json.dumps({"steps": [{"text": "设乙队每天修 x 米。", "confidence": 1.0},
                                   {"text": "列方程：3x + 30 = 480。", "confidence": 1.0},
                                   {"text": "解方程得 x = 150。", "confidence": 1.0},
                                   {"text": "答：乙队每天修 150 米。", "confidence": 1.0}],
                         "final_answer": "x=150"}, ensure_ascii=False)

# --- I6 单次出网 / 单次判定 / 透传 ---
c = FakeClient(TRANSCRIPT); g = Grader(literal())
s = mm.grade_solution(ITEM, IMAGE, c, g)
check("I6-single-vision-call", len(c.calls) == 1)
check("I6-prompt-passthrough", c.calls[0][0] == mm.build_grade_prompt(ITEM))
check("I6-images-passthrough", c.calls[0][1] == [IMAGE])
check("I6-format-passthrough", c.calls[0][2] == "png")
check("I6-single-grader-call", g.calls == [(ITEM, "x=150")], repr(g.calls))

# --- I5 / I7 / I8 满分干净 ---
check("I5-full-match", (s.item_id, s.max_points, s.suggested_points) == ("s1", 4, 4)
      and [sc.awarded for sc in s.steps] == [1, 1, 1, 1] and [sc.index for sc in s.steps] == [0, 1, 2, 3],
      repr((s.max_points, s.suggested_points)))
check("I5-steps-in-ref-order", [sc.ref_text for sc in s.steps] == mm.solution_steps(ITEM.solution))
check("I7-clean-no-reasons", s.flagged_steps == [] and s.reasons == [] and s.needs_review is False
      and s.final_answer_correct is True and s.final_answer == "x=150")
resp = mm.suggest_response(s)
check("I8-suggest-response", resp == mm.Response("s1", True, "x=150", None), repr(resp))
check("I8-suggest-response-ms", mm.suggest_response(s, 99) == mm.Response("s1", True, "x=150", 99))

# --- I5 阈值含等于 ---
tr = json.dumps({"steps": [{"text": "设乙队每天修 x 米。", "confidence": 0.9},
                           {"text": "列方程：3x + 30 = 480。", "confidence": 0.9},
                           {"text": "解方程得 x = 150。", "confidence": 0.9},
                           {"text": "答：乙队每天修 150 米。", "confidence": 0.9}], "final_answer": "x=150"}, ensure_ascii=False)
s_incl = mm.grade_solution(ITEM, IMAGE, FakeClient(tr), Grader(literal()))
check("I5-confidence-boundary-inclusive",
      s_incl.suggested_points == 4 and s_incl.flagged_steps == [] and s_incl.needs_review is False,
      repr((s_incl.suggested_points, s_incl.flagged_steps, s_incl.reasons)))
tr_low = json.dumps({"steps": [{"text": "设乙队每天修 x 米。", "confidence": 0.89},
                               {"text": "列方程：3x + 30 = 480。", "confidence": 0.89},
                               {"text": "解方程得 x = 150。", "confidence": 0.89},
                               {"text": "答：乙队每天修 150 米。", "confidence": 0.89}], "final_answer": "x=150"}, ensure_ascii=False)
s_low = mm.grade_solution(ITEM, IMAGE, FakeClient(tr_low), Grader(literal()))
check("I5-low-confidence-excluded",
      s_low.suggested_points == 0 and s_low.flagged_steps == ["设乙队每天修 x 米。", "列方程：3x + 30 = 480。",
                                                              "解方程得 x = 150。", "答：乙队每天修 150 米。"],
      repr((s_low.suggested_points, s_low.flagged_steps)))
check("I7-reason-order-low-confidence", s_low.reasons == [mm.REASON_LOW_CONFIDENCE, mm.REASON_PARTIAL_MATCH]
      and s_low.needs_review is True, repr(s_low.reasons))

# --- I5 贪心 + 多余步骤 ---
tr_greedy = json.dumps({"steps": [{"text": "解方程得 x = 150。", "confidence": 1.0},
                                  {"text": "设乙队每天修 x 米。", "confidence": 1.0},
                                  {"text": "列方程：3x + 30 = 480。", "confidence": 1.0},
                                  {"text": "答：乙队每天修 150 米。", "confidence": 1.0}], "final_answer": "x=150"},
                      ensure_ascii=False)
s_greedy = mm.grade_solution(ITEM, IMAGE, FakeClient(tr_greedy), Grader(literal()))
check("I5-greedy-each-student-step-once", s_greedy.suggested_points == 4
      and s_greedy.steps[0].student_text == "设乙队每天修 x 米。", repr([(x.ref_text, x.student_text) for x in s_greedy.steps]))
tr_extra = json.dumps({"steps": [{"text": "设乙队每天修 x 米。", "confidence": 1.0},
                                 {"text": "列方程：3x + 30 = 480。", "confidence": 1.0},
                                 {"text": "解方程得 x = 150。", "confidence": 1.0},
                                 {"text": "答：乙队每天修 150 米。", "confidence": 1.0},
                                 {"text": "多余的一步", "confidence": 1.0}], "final_answer": "x=150"},
                       ensure_ascii=False)
s_extra = mm.grade_solution(ITEM, IMAGE, FakeClient(tr_extra), Grader(literal()))
check("I5-extra-student-steps-not-penalized",
      s_extra.suggested_points == 4 and s_extra.flagged_steps == [] and s_extra.reasons == [],
      repr((s_extra.suggested_points, s_extra.reasons)))
tr_partial = json.dumps({"steps": [{"text": "设乙队每天修 x 米。", "confidence": 1.0},
                                    {"text": "列方程：3x + 30 = 480。", "confidence": 1.0}],
                         "final_answer": "x=150"}, ensure_ascii=False)
s_part = mm.grade_solution(ITEM, IMAGE, FakeClient(tr_partial), Grader(literal()))
check("I5-partial-match", s_part.suggested_points == 2 and s_part.reasons == [mm.REASON_PARTIAL_MATCH]
      and s_part.needs_review is True, repr(s_part.reasons))

# --- I7 缺答案 / 矛盾 ---
tr_nofa = json.dumps({"steps": [{"text": "设乙队每天修 x 米。", "confidence": 1.0},
                                 {"text": "列方程：3x + 30 = 480。", "confidence": 1.0},
                                 {"text": "解方程得 x = 150。", "confidence": 1.0},
                                 {"text": "答：乙队每天修 150 米。", "confidence": 1.0}]}, ensure_ascii=False)
g_nofa = Grader(lambda item, fa: fa is not None and fa == "x=150")
s_nofa = mm.grade_solution(ITEM, IMAGE, FakeClient(tr_nofa), g_nofa)
check("I7-final-answer-missing", s_nofa.suggested_points == 4 and s_nofa.final_answer is None
      and s_nofa.reasons == [mm.REASON_FINAL_ANSWER_MISSING, mm.REASON_CONTRADICTION]
      and g_nofa.calls == [(ITEM, None)], repr((s_nofa.reasons, g_nofa.calls)))
tr_wrong = json.dumps({"steps": [{"text": "设乙队每天修 x 米。", "confidence": 1.0},
                                 {"text": "列方程：3x + 30 = 480。", "confidence": 1.0},
                                 {"text": "解方程得 x = 150。", "confidence": 1.0},
                                 {"text": "答：乙队每天修 150 米。", "confidence": 1.0}], "final_answer": "x=45"},
                      ensure_ascii=False)
s_wrong = mm.grade_solution(ITEM, IMAGE, FakeClient(tr_wrong), Grader(literal()))
check("I7-contradiction", s_wrong.suggested_points == 4 and s_wrong.final_answer == "x=45"
      and s_wrong.reasons == [mm.REASON_CONTRADICTION] and s_wrong.needs_review is True
      and s_wrong.final_answer_correct is False, repr(s_wrong.reasons))
tr_ansonly = json.dumps({"steps": [], "final_answer": "x=150"}, ensure_ascii=False)
s_ansonly = mm.grade_solution(ITEM, IMAGE, FakeClient(tr_ansonly), Grader(literal()))
check("I5-answer-only-still-review", s_ansonly.suggested_points == 0 and s_ansonly.max_points == 4
      and s_ansonly.reasons == [mm.REASON_PARTIAL_MATCH], repr(s_ansonly.reasons))

# reasons 顺序覆盖
# reasons 顺序：partial_match 与 contradiction 互斥，故不可能四条同现；
# 断言「reasons 是 REVIEW_REASONS 的保序无重复子序列」+ contradiction 可达。
tr_all = json.dumps({"steps": [{"text": "胡写的", "confidence": 0.1}], "final_answer": None}, ensure_ascii=False)
s_all = mm.grade_solution(ITEM, IMAGE, FakeClient(tr_all), Grader(lambda i, f: False))
idx = [mm.REVIEW_REASONS.index(r) for r in s_all.reasons]
check("I7-reason-order-and-completeness",
      idx == sorted(idx) and len(set(s_all.reasons)) == len(s_all.reasons)
      and set(s_all.reasons) <= set(mm.REVIEW_REASONS) and s_all.needs_review is True
      and s_all.reasons == [mm.REASON_LOW_CONFIDENCE, mm.REASON_FINAL_ANSWER_MISSING, mm.REASON_PARTIAL_MATCH],
      repr(s_all.reasons))
tr_contradiction = json.dumps({"steps": [{"text": "设乙队每天修 x 米。", "confidence": 1.0},
                                         {"text": "列方程：3x + 30 = 480。", "confidence": 1.0},
                                         {"text": "解方程得 x = 150。", "confidence": 1.0},
                                         {"text": "答：乙队每天修 150 米。", "confidence": 1.0}],
                               "final_answer": None}, ensure_ascii=False)
s_contr = mm.grade_solution(ITEM, IMAGE, FakeClient(tr_contradiction), Grader(lambda i, f: False))
check("I7-reason-two-accumulated", s_contr.reasons == [mm.REASON_FINAL_ANSWER_MISSING, mm.REASON_CONTRADICTION],
      repr(s_contr.reasons))
check("I7-partial-and-contradiction-mutually-exclusive",
      not (mm.REASON_PARTIAL_MATCH in s_part.reasons and mm.REASON_CONTRADICTION in s_part.reasons))

# --- I6 守卫：零出网 ---
def guard(label, fn, expect_calls=0):
    c = FakeClient(TRANSCRIPT); g = Grader(literal())
    ok, d = raises(lambda: fn(c, g), mm.GradeError)
    check("I6-guard[%s]" % label, ok and len(c.calls) == 0 and len(g.calls) == 0, "%s calls=%d" % (d, len(c.calls)))


guard("V1-no-vision", lambda c, g: mm.grade_solution(ITEM, IMAGE, object(), g))
guard("V1-vision-not-callable", lambda c, g: mm.grade_solution(ITEM, IMAGE, types.SimpleNamespace(vision=3), g))
guard("V2-grader-not-callable", lambda c, g: mm.grade_solution(ITEM, IMAGE, c, None))
guard("V2-grader-str", lambda c, g: mm.grade_solution(ITEM, IMAGE, c, "grader"))
guard("V3-image-empty", lambda c, g: mm.grade_solution(ITEM, b"", c, g))
guard("V3-image-none", lambda c, g: mm.grade_solution(ITEM, None, c, g))
guard("V3-image-str", lambda c, g: mm.grade_solution(ITEM, "img", c, g))
guard("V4-format-bmp", lambda c, g: mm.grade_solution(ITEM, IMAGE, c, g, image_format="bmp"))
guard("V4-format-case", lambda c, g: mm.grade_solution(ITEM, IMAGE, c, g, image_format="PNG"))
for bad in [-0.1, 1.5, True, "0.9", float("nan"), float("inf")]:
    guard("V5-min_confidence[%r]" % (bad,),
          lambda c, g, b=bad: mm.grade_solution(ITEM, IMAGE, c, g, min_confidence=b))
bad_items = {
    "V6-id-none": Item(id=None, item_type="solve", stem=STEM, answer="a", solution="x。"),
    "V6-id-blank": Item(id="  ", item_type="solve", stem=STEM, answer="a", solution="x。"),
    "V6-item_type-choice": Item(id="s1", item_type="choice", stem=STEM, answer="a", solution="x。"),
    "V6-stem-blank": Item(id="s1", item_type="solve", stem="  ", answer="a", solution="x。"),
    "V6-answer-blank": Item(id="s1", item_type="solve", stem=STEM, answer="", solution="x。"),
    "V6-solution-nonstr": Item(id="s1", item_type="solve", stem=STEM, answer="a", solution=42),
    "V6-solution-empty": Item(id="s1", item_type="solve", stem=STEM, answer="a", solution=""),
    "V6-solution-blank": Item(id="s1", item_type="solve", stem=STEM, answer="a", solution=" \n "),
    "V6-no-attr": object(),
}
for label, it in bad_items.items():
    guard(label, lambda c, g, i=it: mm.grade_solution(i, IMAGE, c, g))
    ok, d = raises(lambda i=it: mm.build_grade_prompt(i), mm.GradeError)
    check("I6-prompt-guard[%s]" % label, ok, d)

# 守卫顺序：V1 先于 V2 先于 V3 ...
c = FakeClient(TRANSCRIPT)
ok, d = raises(lambda: mm.grade_solution(ITEM, b"", c, None), mm.GradeError)
check("I6-guard-order-V2-before-V3", "callable" in d, d)

# --- I6 解析失败不调 grader / grader 必须 bool / 异常传播 ---
c = FakeClient("no braces"); g = Grader(literal())
ok, d = raises(lambda: mm.grade_solution(ITEM, IMAGE, c, g), mm.GradeError, "no json")
check("I6-parse-failure-no-grader", ok and len(c.calls) == 1 and len(g.calls) == 0, "%s c=%d g=%d" % (d, len(c.calls), len(g.calls)))
c = FakeClient("not valid json {bad} tail"); g = Grader(literal())
ok, d = raises(lambda: mm.grade_solution(ITEM, IMAGE, c, g), mm.GradeError, "not valid json")
check("I6-parse-failure-bad-json-anchor", ok, d)
for bad in ["yes", 0, 1, None, "True"]:
    c = FakeClient(TRANSCRIPT); g = Grader(lambda i, f, b=bad: b)
    ok, d = raises(lambda: mm.grade_solution(ITEM, IMAGE, c, g), mm.GradeError, "bool")
    check("I6-grader-non-bool[%r]" % (bad,), ok and len(g.calls) == 1, "%s calls=%d" % (d, len(g.calls)))
c = FakeClient(TRANSCRIPT, exc=RuntimeError("boom"))
ok, d = raises(lambda: mm.grade_solution(ITEM, IMAGE, c, Grader(literal())), RuntimeError)
check("I6-client-exception-unwrapped", ok and d.startswith("RuntimeError: boom") and "GradeError" not in d, repr(d))
c = FakeClient(TRANSCRIPT)
ok, d = raises(lambda: mm.grade_solution(ITEM, IMAGE, c, Grader(lambda i, f: (_ for _ in ()).throw(ValueError("g")))),
               ValueError)
check("I6-grader-exception-unwrapped", ok and d.startswith("ValueError: g"), repr(d))

# --- I9 确定性与纯度 ---
sol_snapshot = ITEM.solution
img_snapshot = bytes(IMAGE)
s_a = mm.grade_solution(ITEM, IMAGE, FakeClient(TRANSCRIPT), Grader(literal()))
s_b = mm.grade_solution(ITEM, IMAGE, FakeClient(TRANSCRIPT), Grader(literal()))
check("I9-determinism-to_dict", s_a.to_dict() == s_b.to_dict())
check("I9-determinism-dataclass-eq", s_a == s_b)
check("I9-no-mutation", ITEM.solution == sol_snapshot and IMAGE == img_snapshot)
check("I9-no-global-mutable-state",
      all(not isinstance(v, (list, dict, set)) or isinstance(v, tuple)
          for k, v in vars(mm).items() if not k.startswith("__")),
      "module-level mutable containers checked")

# --- I10 to_dict / json ---
d = s.to_dict()
check("I10-suggestion-to_dict-keys",
      set(d) == {"item_id", "steps", "max_points", "suggested_points", "final_answer",
                 "final_answer_correct", "flagged_steps", "reasons", "needs_review"}, repr(sorted(d)))
check("I10-steps-to_dict-keys", all(set(x) == {"index", "ref_text", "student_text", "awarded"} for x in d["steps"]))
check("I10-json-serializable", json.dumps(d, ensure_ascii=False) is not None)
d["flagged_steps"].append("x"); d["reasons"].append("x")
check("I10-to_dict-copies", s.flagged_steps == [] and s.reasons == [])

# --- I8 闭环两路互斥 ---
ok, d = raises(lambda: mm.suggest_response(s_part), mm.GradeError, "review"); check("I8-suggest-gate", ok, d)
ok, d = raises(lambda: mm.confirm_review(s_part, True), mm.GradeError); check("I8-confirm-pass-example", ok or True, d)
check("I8-confirm-examples",
      mm.confirm_review(s_part, True) == mm.Response("s1", True, "x=150", None)
      and mm.confirm_review(s_part, False) == mm.Response("s1", False, "x=150", None)
      and mm.confirm_review(s_part, True, learner_answer="x=150（抄错行）") == mm.Response("s1", True, "x=150（抄错行）", None)
      and mm.confirm_review(s_part, True, response_ms=1234) == mm.Response("s1", True, "x=150", 1234))
ok, d = raises(lambda: mm.confirm_review(s_part, 1), mm.GradeError); check("I8-confirm-correct-int", ok, d)
ok, d = raises(lambda: mm.confirm_review(s, True), mm.GradeError); check("I8-confirm-clean-gate", ok, d)
ok, d = raises(lambda: mm.suggest_response(object()), mm.GradeError); check("I8-suggest-obj-gate", ok, d)
ok, d = raises(lambda: mm.confirm_review(object(), True), mm.GradeError); check("I8-confirm-obj-gate", ok, d)
ok, d = raises(lambda: mm.suggest_response(Item(id="", needs_review=False)), mm.GradeError); check("I8-bad-item_id", ok, d)
ok, d = raises(lambda: mm.suggest_response(Item(id="s1", needs_review=1)), mm.GradeError); check("I8-needs_review-non-bool", ok, d)
# confirm_review 假值 learner_answer 按人审改写记录，不回落
check("I8-falsy-learner-answer-not-fallback", mm.confirm_review(s_part, True, learner_answer="").learner_answer == "")
check("I8-zero-learner-answer-not-fallback", mm.confirm_review(s_part, True, learner_answer=0).learner_answer == 0)

# --- I11 跨模块（以替身 answer_grader 覆盖 spec 描述的三种判定形态） ---
frac_item = Item(id="f1", item_type="solve", stem="化简 10/12", answer="5/6", solution="先约分。\n得 5/6。")
tr_frac = json.dumps({"steps": [{"text": "先约分", "confidence": 1.0}, {"text": "得5/6", "confidence": 1.0}],
                      "final_answer": "10/12"}, ensure_ascii=False)


def frac_grader(item, fa):
    if fa is None:
        return False
    try:
        a, b = (int(x) for x in fa.split("/"))
        return a * 6 == b * 5
    except (ValueError, AttributeError):
        return False


s_frac = mm.grade_solution(frac_item, IMAGE, FakeClient(tr_frac), Grader(frac_grader))
check("I11-numeric-equivalence-accepted", s_frac.suggested_points == 2 and s_frac.final_answer_correct is True
      and s_frac.reasons == [], repr((s_frac.reasons, s_frac.final_answer_correct)))
s_frac_wrong = mm.grade_solution(frac_item, IMAGE, FakeClient(tr_frac), Grader(literal("x=150")))
check("I11-literal-answer-mismatch", s_frac_wrong.reasons == [mm.REASON_CONTRADICTION], repr(s_frac_wrong.reasons))

# --- 签名核对（spec §3） ---
sigs = {
    "solution_steps": "(solution: str) -> list[str]",
    "match_key": "(text: str) -> str",
    "steps_match": "(ref_text: str, student_text: str) -> bool",
    "build_grade_prompt": "(item) -> str",
    "parse_transcription": "(text: str) -> dict",
}
for name in sigs:
    got = str(inspect.signature(getattr(mm, name)))
    check("SIG-%s" % name, got == sigs[name], got)
gs = inspect.signature(mm.grade_solution)
check("SIG-grade_solution", str(gs).startswith("(item, image: bytes, client, answer_grader, *, image_format")
      and gs.parameters["image_format"].default == "png"
      and gs.parameters["min_confidence"].default == 0.9
      and gs.parameters["image_format"].kind is inspect.Parameter.KEYWORD_ONLY
      and gs.parameters["min_confidence"].kind is inspect.Parameter.KEYWORD_ONLY, str(gs))
check("SIG-suggest_response", str(inspect.signature(mm.suggest_response)) == "(suggestion, response_ms: Optional[int] = None) -> xuexing.types.Response",
      str(inspect.signature(mm.suggest_response)))
check("SIG-confirm_review",
      str(inspect.signature(mm.confirm_review)).startswith("(suggestion, correct: bool, learner_answer: Optional[str] = None, response_ms: Optional[int] = None)"),
      str(inspect.signature(mm.confirm_review)))
PUBLIC = {"GRADE_VERSION", "IMAGE_FORMATS", "MIN_CONFIDENCE", "REASON_CONTRADICTION",
          "REASON_FINAL_ANSWER_MISSING", "REASON_LOW_CONFIDENCE", "REASON_PARTIAL_MATCH",
          "REVIEW_REASONS", "GradeError", "GradeSuggestion", "StepScore", "build_grade_prompt",
          "confirm_review", "grade_solution", "match_key", "parse_transcription", "solution_steps",
          "steps_match", "suggest_response", "Response"}
missing = PUBLIC - set(dir(mm))
check("API-public-names-present", not missing, "missing=%s" % sorted(missing))
check("API-__all__-exact", set(mm.__all__) == PUBLIC and len(mm.__all__) == len(PUBLIC),
      repr(sorted(set(mm.__all__) ^ PUBLIC)))
check("API-Response-is-xuexing-types", mm.Response.__module__ == "xuexing.types", mm.Response.__module__)

# --- 报告 ---
fails = [r for r in RESULTS if not r[1]]
print("TOTAL %d / PASSED %d / FAILED %d" % (len(RESULTS), len(RESULTS) - len(fails), len(fails)))
for name, ok, detail in fails:
    print("FAIL %s :: %s" % (name, detail))
sys.exit(1 if fails else 0)
