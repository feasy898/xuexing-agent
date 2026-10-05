"""盲重写自检 harness（第三波 · mm_ingest）。

装载方式复制 spec §2 的注入机制：以顶层模块名 `_regen_mm_ingest` 经
`spec_from_file_location` 装载 regen/wave3b/mm_ingest.py 并顶替
`sys.modules["xuexing.mm_ingest"]`。检查项全部来自 mm_ingest.spec.md 的闭式例子与
不变量 I1..I17；不读 tests/、不读参考实现 mm_ingest.py。
"""
import copy
import importlib.util
import json
import math
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from xuexing.types import Response, to_dict as _tdict  # noqa: E402  (spec §2 允许的唯一依赖)

IMPL = ROOT / "regen" / "wave3b" / "mm_ingest.py"

spec_obj = importlib.util.spec_from_file_location("_regen_mm_ingest", IMPL)
mod = importlib.util.module_from_spec(spec_obj)
sys.modules["_regen_mm_ingest"] = mod
spec_obj.loader.exec_module(mod)
sys.modules["xuexing.mm_ingest"] = mod

RESULTS = []


def check(name, ok, info=""):
    RESULTS.append((name, bool(ok), info))
    print(("PASS " if ok else "FAIL ") + name + ((" | " + str(info)) if info else ""))


def expect_error(name, fn, exc=mod.IngestError):
    try:
        fn()
    except exc as e:  # noqa: BLE001
        check(name, True, f"{type(e).__name__}: {e}")
        return e
    except BaseException as e:  # noqa: BLE001
        check(name, False, f"wrong exc {type(e).__name__}: {e}")
        return None
    check(name, False, "no exception raised")
    return None


# ---------------- fixtures（鸭子类型） ----------------

class It:
    def __init__(self, id, item_type, options=None, answer="", stem="", solution=""):
        self.id = id
        self.item_type = item_type
        self.options = list(options or [])
        self.answer = answer
        self.stem = stem
        self.solution = solution


C1 = It("c1", "choice", ["A. 0", "B. -2/3", "C. +1.5", "D. 2026"], "B. -2/3",
        stem="stem-c1", solution="SOL-c1")
F1 = It("f1", "fill", [], "-300元", stem="有理数填空", solution="SOL-f1")
S1 = It("s1", "solve", [], "x=12", stem="一元一次方程", solution="SOL-s1")
C2 = It("c2", "choice", ["2", "3"], "3", stem="stem-c2", solution="SOL-c2")
BANK_ITEMS = [C1, F1, S1, C2]


class Bank:
    def __init__(self, items=None, mode="ok"):
        self._items = BANK_ITEMS if items is None else items
        self.mode = mode

    def items(self):
        if self.mode == "typeerror":
            raise TypeError("nope")
        if self.mode == "notiterable":
            return 5
        return self._items


class Paper:
    def __init__(self, sections, item_ids=None, paper_id="p1", title="有理数"):
        self.paper_id = paper_id
        self.title = title
        self.sections = sections
        self.item_ids = [] if item_ids is None else item_ids


class Client:
    def __init__(self, text=None, mode="ok"):
        self.calls = []
        self.text = text
        self.mode = mode

    def vision(self, prompt, images, image_format="png"):
        self.calls.append({"prompt": prompt, "images": list(images),
                           "image_format": image_format})
        if self.mode == "raise":
            raise RuntimeError("llm down")
        return self.text


class Grader:
    def __init__(self, mode="ok"):
        self.calls = []
        self.mode = mode

    def __call__(self, item, learner_answer):
        self.calls.append((item.id, learner_answer))
        if self.mode == "raise":
            raise ValueError("grading boom")
        if learner_answer is None:
            return Response(item.id, False, None, None)
        if item.item_type == "choice":
            correct = learner_answer.strip().upper() == item.answer.strip().upper() \
                or learner_answer.strip().upper() == "B"
            return Response(item.id, bool(correct), learner_answer, None)
        return Response(item.id, True, learner_answer, None)


P3 = Paper([{"item_ids": ["c1", "f1", "s1"], "name": "第一大题"}], item_ids=["c1", "f1", "s1"])
P4 = Paper([], item_ids=["c1", "f1", "s1", "c2"])
IMG = b"\x89PNG-bytes"


# ---------------- I1 常量冻结 ----------------

check("I1 INGEST_VERSION", mod.INGEST_VERSION == "1", mod.INGEST_VERSION)
check("I1 MIN_CONFIDENCE", mod.MIN_CONFIDENCE == 0.9, mod.MIN_CONFIDENCE)
check("I1 IMAGE_FORMATS",
      mod.IMAGE_FORMATS == ("png", "jpg", "jpeg", "webp", "gif"), mod.IMAGE_FORMATS)
check("I1 REVIEW_REASONS",
      mod.REVIEW_REASONS == ("unknown_number", "duplicate_number", "missing_number",
                             "low_confidence", "answer_form"), mod.REVIEW_REASONS)
check("I1 REASON_* 字面量",
      (mod.REASON_UNKNOWN_NUMBER == "unknown_number"
       and mod.REASON_DUPLICATE_NUMBER == "duplicate_number"
       and mod.REASON_MISSING_NUMBER == "missing_number"
       and mod.REASON_LOW_CONFIDENCE == "low_confidence"
       and mod.REASON_ANSWER_FORM == "answer_form"))
check("I1 IngestError 是 ValueError 直接子类",
      issubclass(mod.IngestError, ValueError)
      and mod.IngestError.__bases__ == (ValueError,), mod.IngestError.__bases__)
PUBLIC = ["IMAGE_FORMATS", "INGEST_VERSION", "MIN_CONFIDENCE", "REASON_ANSWER_FORM",
          "REASON_DUPLICATE_NUMBER", "REASON_LOW_CONFIDENCE", "REASON_MISSING_NUMBER",
          "REASON_UNKNOWN_NUMBER", "REVIEW_REASONS", "IngestError", "IngestResult",
          "ReviewItem", "build_transcribe_prompt", "ingest_photo", "option_labels",
          "parse_transcript"]
missing = [n for n in PUBLIC if not hasattr(mod, n)]
check("§3 16 个公开名字齐备", not missing, f"missing={missing}")
import inspect  # noqa: E402
sig = inspect.signature(mod.ingest_photo)
check("§3.7 签名",
      list(sig.parameters) == ["image", "paper", "bank", "client", "grader",
                               "image_format", "min_confidence"]
      and sig.parameters["image_format"].kind is inspect.Parameter.KEYWORD_ONLY
      and sig.parameters["min_confidence"].kind is inspect.Parameter.KEYWORD_ONLY
      and sig.parameters["min_confidence"].default == 0.9
      and sig.parameters["image_format"].default == "png", str(sig))

# ---------------- I3 option_labels ----------------

check("I3 闭式 A..D", mod.option_labels(C1) == ["A", "B", "C", "D"], mod.option_labels(C1))
check("I3 闭式 回退", mod.option_labels(C2) == ["A", "B"], mod.option_labels(C2))
odd = It("odd", "choice", ["b. 一", "c）二", "d．三", "e、四"], "B")
check("I3 闭式 分隔符+归一", mod.option_labels(odd) == ["B", "C", "D", "E"], mod.option_labels(odd))
twenty_six = It("x26", "choice", [f"opt{i}" for i in range(26)], "opt0")
check("§3.4 恰 26 项回退 A..Z",
      mod.option_labels(twenty_six) == list("ABCDEFGHIJKLMNOPQRSTUVWXYZ"))
check("I3 幂等/纯函数", mod.option_labels(C1) == mod.option_labels(C1))


class NoOptions:
    id = "no"


expect_error("I3 守卫 options 缺失", lambda: mod.option_labels(NoOptions()))
expect_error("I3 守卫 options 非 list/tuple",
             lambda: mod.option_labels(type("X", (), {"options": "AB"})()))
expect_error("I3 守卫 len<2", lambda: mod.option_labels(It("o", "choice", ["only"], "only")))
expect_error("I3 守卫 len=27",
             lambda: mod.option_labels(It("o", "choice", [f"o{i}" for i in range(27)], "o0")))
expect_error("I3 守卫 非 str 选项",
             lambda: mod.option_labels(It("o", "choice", ["A", 3], "A")))
expect_error("I3 守卫 空白选项",
             lambda: mod.option_labels(It("o", "choice", ["A", "   "], "A")))
expect_error("I3 守卫 标签重复",
             lambda: mod.option_labels(It("o", "choice", ["A. 一", "a. 二"], "A")))

# ---------------- I4 prompt 冻结 + 卫生 ----------------

SPEC_LINES = (ROOT / "specs" / "frozen" / "mm_ingest.spec.md").read_text(encoding="utf-8").split("\n")
expected_prompt = "\n".join(line[2:] for line in SPEC_LINES[198:210])
got_prompt = mod.build_transcribe_prompt(P3, Bank())
check("I4 §3.5 闭式逐字节相等", got_prompt == expected_prompt,
      f"got={got_prompt!r}" if got_prompt != expected_prompt else "byte-equal")
check("I4 重复调用相等（确定性）",
      mod.build_transcribe_prompt(P3, Bank()) == got_prompt)
check("I4 无尾随换行", not got_prompt.endswith("\n"), repr(got_prompt[-8:]))
four = Paper([{"item_ids": ["c1", "f1", "s1", "c2"], "name": "有理数"},
              {"item_ids": [], "name": "一元一次方程"}], item_ids=[])
p4 = mod.build_transcribe_prompt(four, Bank())
must_have = ["A/B/C/D", "A/B", "1. choice 选项 A/B/C/D", "2. fill", "3. solve", "4. choice 选项 A/B"]
must_not = ["stem-c1", "-300元", "x=12", "SOL-", "B. -2/3", "2026", "+1.5", "有理数",
            "一元一次方程", "stem", "solution", "0.0"]
check("I4 prompt 含题号/题型/标签", all(s in p4 for s in must_have),
      [s for s in must_have if s not in p4])
check("I4 prompt 无 stem/答案/解析/选项正文/节名",
      not any(s in p4 for s in must_not), [s for s in must_not if s in p4])

# ---------------- I8 parse_transcript ----------------

pt = mod.parse_transcript
check("I8 闭式 1", pt('{"answers": [{"number": 1, "answer": "B", "confidence": 0.97}]}')
      == [{"number": 1, "answer": "B", "confidence": 0.97}])
fenced = '```json\n{"answers": [{"number": 2, "answer": null, "confidence": 1}]}\n```'
r = pt(fenced)
check("I8 闭式 围栏+int→float", r == [{"number": 2, "answer": None, "confidence": 1.0}]
      and isinstance(r[0]["confidence"], float), r)
check("I8 闭式 未知键忽略",
      pt('{"answers": [{"number": 1, "answer": "B", "confidence": 1, "extra": "x"}]}')
      == [{"number": 1, "answer": "B", "confidence": 1.0}])
check("I8 闲话容忍", pt('好的：{"answers": []} 完毕') == [])
check("I8 输出 entry 恰三键", all(set(e) == {"number", "answer", "confidence"} for e in pt(
    '{"answers":[{"number":1,"answer":"B","confidence":1}]}')))
check("I8 空 answers 合法", pt('{"answers": []}') == [])

BAD = [
    ("非 str", 123),
    ("空串", "   "),
    ("无花括号", "no json here"),
    ("右括号在前", "} {"),
    ("JSON 解析失败", '{"answers": ['),
    ("两个独立对象", '{"answers": []} {"answers": []}'),
    ("顶层非 dict", '["answers"]'),
    ("缺 answers", '{"items": []}'),
    ("answers 非 list", '{"answers": {}}'),
    ("entry 非 dict", '{"answers": [1]}'),
    ("缺 number", '{"answers": [{"answer": "B", "confidence": 1}]}'),
    ("缺 answer", '{"answers": [{"number": 1, "confidence": 1}]}'),
    ("缺 confidence", '{"answers": [{"number": 1, "answer": "B"}]}'),
    ("number=0", '{"answers": [{"number": 0, "answer": "B", "confidence": 1}]}'),
    ("number=-1", '{"answers": [{"number": -1, "answer": "B", "confidence": 1}]}'),
    ("number='1'", '{"answers": [{"number": "1", "answer": "B", "confidence": 1}]}'),
    ("number=True", '{"answers": [{"number": true, "answer": "B", "confidence": 1}]}'),
    ("number=1.5", '{"answers": [{"number": 1.5, "answer": "B", "confidence": 1}]}'),
    ("number=null", '{"answers": [{"number": null, "answer": "B", "confidence": 1}]}'),
    ("answer=42", '{"answers": [{"number": 1, "answer": 42, "confidence": 1}]}'),
    ("answer=[]", '{"answers": [{"number": 1, "answer": [], "confidence": 1}]}'),
    ("answer={}", '{"answers": [{"number": 1, "answer": {}, "confidence": 1}]}'),
    ("confidence=-0.1", '{"answers": [{"number": 1, "answer": "B", "confidence": -0.1}]}'),
    ("confidence=1.1", '{"answers": [{"number": 1, "answer": "B", "confidence": 1.1}]}'),
    ("confidence='0.9'", '{"answers": [{"number": 1, "answer": "B", "confidence": "0.9"}]}'),
    ("confidence=True", '{"answers": [{"number": 1, "answer": "B", "confidence": true}]}'),
    ("confidence=null", '{"answers": [{"number": 1, "answer": "B", "confidence": null}]}'),
    ("confidence=inf", '{"answers": [{"number": 1, "answer": "B", "confidence": Infinity}]}'),
    ("confidence=nan", '{"answers": [{"number": 1, "answer": "B", "confidence": NaN}]}'),
]
for label, payload in BAD:
    expect_error(f"I8 拒绝 {label}", lambda p=payload: pt(p))
check("I8 非法输入计数(我的清单)", True, f"{len(BAD)} 类全部抛 IngestError")

# ---------------- I5/I6/I7 ingest 主流程 ----------------

TRANSCRIPT = json.dumps({"answers": [
    {"number": 1, "answer": "B", "confidence": 0.97},
    {"number": 2, "answer": "-300元", "confidence": 0.95},
    {"number": 4, "answer": "x", "confidence": 0.8},
    {"number": 9, "answer": "42", "confidence": 0.99},
    {"number": 2, "answer": None, "confidence": 0.3},
]}, ensure_ascii=False)
client = Client(TRANSCRIPT)
grader = Grader()
res = mod.ingest_photo(IMG, P4, Bank(), client, grader)
check("I6 恰好一次 vision", len(client.calls) == 1, len(client.calls))
call = client.calls[0]
check("I6 调用形状 prompt/images/image_format",
      call["prompt"] == mod.build_transcribe_prompt(P4, Bank())
      and call["images"] == [IMG] and call["images"][0] is IMG
      and call["image_format"] == "png", call)
check("I5 线上 prompt 逐字节 == build_transcribe_prompt",
      call["prompt"] == mod.build_transcribe_prompt(P4, Bank()))
client2 = Client(TRANSCRIPT)
mod.ingest_photo(IMG, P4, Bank(), client2, Grader(), image_format="jpeg")
check("I6 image_format 透传", client2.calls[0]["image_format"] == "jpeg"
      and client2.calls[0]["images"] == [IMG])
check("I9/I13 responses == [Response(c1, True, 'B. -2/3', None)]",
      res.responses == [Response("c1", True, "B. -2/3", None)],
      [_tdict(r) for r in res.responses])
got_pairs = [(r.reason, r.number) for r in res.review]
want_pairs = [(mod.REASON_DUPLICATE_NUMBER, 2), (mod.REASON_LOW_CONFIDENCE, 4),
              (mod.REASON_UNKNOWN_NUMBER, 9), (mod.REASON_DUPLICATE_NUMBER, 2),
              (mod.REASON_MISSING_NUMBER, 3)]
check("I9 review (reason, number) 序列", got_pairs == want_pairs, got_pairs)
got_triples = [(r.item_id, r.answer, r.confidence) for r in res.review]
want_triples = [("f1", "-300元", 0.95), ("c2", "x", 0.8), (None, "42", 0.99),
                ("f1", None, 0.3), ("s1", None, None)]
check("I9 review (item_id, answer, confidence) 序列", got_triples == want_triples, got_triples)
check("I9 grader.calls == [('c1', 'B. -2/3')]", grader.calls == [("c1", "B. -2/3")], grader.calls)
details = [r.detail for r in res.review]
check("§3.2 detail 子串", all(s in details[0] for s in ["transcribed 2 times"])
      and "not on paper" in details[2] and "min_confidence" in details[1]
      and "missing from transcript" in details[4], details)
check("§3.2 unknown item_id 恒 None", all(r.item_id is None for r in res.review
                                          if r.reason == mod.REASON_UNKNOWN_NUMBER))
check("§3.2 missing answer/confidence 恒 None",
      all(r.answer is None and r.confidence is None for r in res.review
          if r.reason == mod.REASON_MISSING_NUMBER))
check("I9 每条 entry 至多一个 reason",
      sum(1 for r in res.review) == 5 and len(res.responses) == 1, (len(res.review), len(res.responses)))

# detail 完整文案
check("§3.2 detail 完整文案",
      details[0] == "number 2 transcribed 2 times"
      and details[1] == "confidence 0.8 < min_confidence 0.9"
      and details[2] == "number 9 is not on paper (1..4)"
      and details[4] == "number 3 missing from transcript", details)

# I10 空白作答
blank = json.dumps({"answers": [
    {"number": 1, "answer": "B", "confidence": 0.95},
    {"number": 2, "answer": "   ", "confidence": 0.95},
    {"number": 3, "answer": None, "confidence": 0.95},
]}, ensure_ascii=False)
g2 = Grader()
r2 = mod.ingest_photo(IMG, P3, Bank(), Client(blank), g2)
check("I10 空白/null 交 grader(item, None)",
      g2.calls == [("c1", "B. -2/3"), ("f1", None), ("s1", None)], g2.calls)
check("I10 空白作答不伪造、不进复核",
      r2.review == [] and [r.learner_answer for r in r2.responses] == ["B. -2/3", None, None],
      [_tdict(r) for r in r2.responses])

# I11 choice 形态门
def form_case(ans):
    payload = json.dumps({"answers": [{"number": 1, "answer": ans, "confidence": 0.95}]},
                         ensure_ascii=False)
    gg = Grader()
    out = mod.ingest_photo(IMG, P3, Bank(), Client(payload), gg)
    # 只看第 1 题的条目级复核（同卷第 2/3 题未转写 → missing_number，属预期）
    entry_review = [(r.reason, r.detail) for r in out.review
                    if r.reason != mod.REASON_MISSING_NUMBER]
    return gg.calls, entry_review


check("I11 'b' 归一命中标签", form_case("b")[0] == [("c1", "B. -2/3")], form_case("b"))
check("I11 ' B ' 归一命中标签", form_case(" B ")[0] == [("c1", "B. -2/3")])
check("I11 'A' 命中 A 选项原文", form_case("A")[0] == [("c1", "A. 0")], form_case("A"))
for bad in ["E", "AB", "B. -2/3", "A.", "3"]:
    calls, rev = form_case(bad)
    check(f"I11 形态 '{bad}' → answer_form 复核、零 grader",
          calls == [] and len(rev) == 1 and rev[0][0] == mod.REASON_ANSWER_FORM, (calls, rev))
check("§3.2 answer_form detail 格式",
      form_case("AB")[1][0][1] ==
      "choice answer must be a single bubble label in ['A', 'B', 'C', 'D'], got 'AB'",
      form_case("AB")[1][0][1])
# c2 无显式标签：单字符 "3" 是答案形态门而不是标签命中
c2_payload = json.dumps({"answers": [{"number": 4, "answer": "3", "confidence": 0.95}]},
                        ensure_ascii=False)
g3 = Grader()
r3 = mod.ingest_photo(IMG, P4, Bank(), Client(c2_payload), g3)
entry3 = [(r.reason, r.number) for r in r3.review if r.reason != mod.REASON_MISSING_NUMBER]
check("I11/§6 c2 标签 A/B：'3' 非标签 → answer_form 复核、零 grader",
      g3.calls == [] and entry3 == [(mod.REASON_ANSWER_FORM, 4)], (g3.calls, entry3))
c2_b = json.dumps({"answers": [{"number": 4, "answer": "b", "confidence": 0.95}]},
                  ensure_ascii=False)
g3b = Grader()
mod.ingest_photo(IMG, P4, Bank(), Client(c2_b), g3b)
check("I11 c2 'b' → 选项原文 '3'", g3b.calls == [("c2", "3")], g3b.calls)

# fill/solve 原文透传（前后空白也透传）
fws = json.dumps({"answers": [{"number": 2, "answer": " -300 元 ", "confidence": 0.95}]},
                 ensure_ascii=False)
g4 = Grader()
mod.ingest_photo(IMG, P3, Bank(), Client(fws), g4)
check("§3.7 fill 原文透传不 strip", g4.calls == [("f1", " -300 元 ")], g4.calls)

# I12 置信度门边界
def conf_case(entries, **kw):
    payload = json.dumps({"answers": entries}, ensure_ascii=False)
    gg = Grader()
    out = mod.ingest_photo(IMG, P4, Bank(), Client(payload), gg, **kw)
    return gg.calls, [(r.reason, r.number) for r in out.review]


check("I12 ==门限通过",
      conf_case([{"number": 1, "answer": "B", "confidence": 0.9}])[0] == [("c1", "B. -2/3")])
check("I12 min_confidence=0.0 边界",
      conf_case([{"number": 4, "answer": "A", "confidence": 0.0}],
                min_confidence=0.0)[0] == [("c2", "2")])
one_q = conf_case([{"number": 1, "answer": "B", "confidence": 0.99}], min_confidence=1.0)
check("I12 min_confidence=1.0 → low_confidence（题 1）",
      one_q[0] == [] and one_q[1][0] == (mod.REASON_LOW_CONFIDENCE, 1), one_q)

# I13 排序 / 纯复核
rev_only = json.dumps({"answers": [{"number": 9, "answer": "x", "confidence": 0.1}]}, ensure_ascii=False)
g5 = Grader()
r5 = mod.ingest_photo(IMG, P4, Bank(), Client(rev_only), g5)
check("I13 纯复核转写：responses 空、grader 零调用",
      r5.responses == [] and g5.calls == [] and len(r5.review) == 5, r5.to_dict())
sorted_payload = json.dumps({"answers": [
    {"number": 3, "answer": "y", "confidence": 0.95},
    {"number": 1, "answer": "B", "confidence": 0.95},
    {"number": 2, "answer": "-300元", "confidence": 0.95}]}, ensure_ascii=False)
g6 = Grader()
r6 = mod.ingest_photo(IMG, P3, Bank(), Client(sorted_payload), g6)
check("I13 responses 按卷面题号升序",
      [r.item_id for r in r6.responses] == ["c1", "f1", "s1"], [r.item_id for r in r6.responses])
check("I13 判分调用按转写序", g6.calls == [("s1", "y"), ("c1", "B. -2/3"), ("f1", "-300元")], g6.calls)

# I14 空转写 + 异常传播
c7 = Client('{"answers": []}')
g7 = Grader()
r7 = mod.ingest_photo(IMG, P3, Bank(), c7, g7)
check("I14 空转写：全缺号升序、恰一次出网、零 grader",
      c7.calls.__len__() == 1 and g7.calls == [] and r7.responses == []
      and [(r.reason, r.number) for r in r7.review]
      == [(mod.REASON_MISSING_NUMBER, 1), (mod.REASON_MISSING_NUMBER, 2),
          (mod.REASON_MISSING_NUMBER, 3)], [r.to_dict() for r in r7.review])
c8 = Client(TRANSCRIPT, mode="raise")
try:
    mod.ingest_photo(IMG, P4, Bank(), c8, Grader())
    check("I14 client 异常原样传播", False, "no raise")
except RuntimeError as e:
    check("I14 client 异常原样传播", str(e) == "llm down" and not isinstance(e, mod.IngestError),
          f"{type(e).__name__}: {e}")
good = json.dumps({"answers": [{"number": 1, "answer": "B", "confidence": 0.95}]})
try:
    mod.ingest_photo(IMG, P3, Bank(), Client(good), Grader(mode="raise"))
    check("I14 grader 异常原样传播", False, "no raise")
except ValueError as e:
    check("I14 grader 异常原样传播", str(e) == "grading boom" and not isinstance(e, mod.IngestError),
          f"{type(e).__name__}: {e}")

# I15 确定性 / 不改入参
snap_sections = copy.deepcopy(P4.sections)
snap_opts = [list(i.options) for i in BANK_ITEMS]
snap_ans = [i.answer for i in BANK_ITEMS]
c9, c10 = Client(TRANSCRIPT), Client(TRANSCRIPT)
out1 = mod.ingest_photo(IMG, P4, Bank(), c9, Grader())
out2 = mod.ingest_photo(IMG, P4, Bank(), c10, Grader())
check("I15 同输入两次 to_dict 相等", out1.to_dict() == out2.to_dict())
check("I15 入参未被修改",
      P4.sections == snap_sections
      and [list(i.options) for i in BANK_ITEMS] == snap_opts
      and [i.answer for i in BANK_ITEMS] == snap_ans
      and c9.calls[0]["images"][0] == IMG)

# I16 to_dict 形状
ri = mod.ReviewItem(number=1, item_id="c1", answer="B", confidence=0.9,
                    reason="low_confidence", detail="d")
check("I16 ReviewItem.to_dict 六字段",
      ri.to_dict() == {"number": 1, "item_id": "c1", "answer": "B", "confidence": 0.9,
                       "reason": "low_confidence", "detail": "d"}, ri.to_dict())
ir = mod.IngestResult(responses=[Response("c1", True, "B. -2/3", None)], review=[ri])
check("I16 IngestResult.to_dict 形状",
      ir.to_dict() == {"responses": [{"item_id": "c1", "correct": True,
                                      "learner_answer": "B. -2/3", "response_ms": None}],
                       "review": [ri.to_dict()]}, ir.to_dict())

# I17 注入 grader 语义（fake grader 形状对齐 grading.grade_to_response 的产出）
check("I17 choice 交选项原文全串（探针 P1 标答=选项全文）",
      conf_case([{"number": 1, "answer": "D", "confidence": 0.95}])[0] == [("c1", "D. 2026")])
check("§3.7 标答=选项全文合法（探针 P1）",
      mod.build_transcribe_prompt(Paper([{"item_ids": ["c1"]}]), Bank()) is not None)

# I7 V1–V5 守卫（零出网）
def guard(name, **kw):
    cc = Client(TRANSCRIPT)
    args = {"image": IMG, "paper": P4, "bank": Bank(), "client": cc, "grader": Grader()}
    args.update(kw)
    e = expect_error(name, lambda: mod.ingest_photo(**args))
    return cc, e


class NoVision:
    pass


class BadVision:
    vision = "not callable"


for nm, kw in [
    ("V1 client 无 vision", {"client": NoVision()}),
    ("V1 client=None", {"client": None}),
    ("V1 client.vision 不可调用", {"client": BadVision()}),
    ("V2 grader 不可调用", {"grader": "nope"}),
    ("V2 grader=None", {"grader": None}),
    ("V3 image=None", {"image": None}),
    ("V3 image=''", {"image": ""}),
    ("V3 image=bytearray", {"image": bytearray(b"ab")}),
    ("V4 image_format='PNG'", {"image_format": "PNG"}),
    ("V4 image_format='bmp'", {"image_format": "bmp"}),
    ("V5 min_confidence=True", {"min_confidence": True}),
    ("V5 min_confidence='0.9'", {"min_confidence": "0.9"}),
    ("V5 min_confidence=1.1", {"min_confidence": 1.1}),
    ("V5 min_confidence=-0.1", {"min_confidence": -0.1}),
    ("V5 min_confidence=nan", {"min_confidence": float("nan")}),
    ("V5 min_confidence=inf", {"min_confidence": float("inf")}),
]:
    cc, e = guard(nm, **kw)
    check(f"{nm} → 零出网", cc.calls == [], cc.calls)

check("V3 空 bytes 拒绝", isinstance(
    expect_error("V3 image=b''", lambda: mod.ingest_photo(b"", P4, Bank(), Client(), Grader())),
    mod.IngestError))
c_ok = Client(TRANSCRIPT)
mod.ingest_photo(IMG, P4, Bank(), c_ok, Grader())
check("V3 非空 bytes 通过（走到出网）", len(c_ok.calls) == 1, c_ok.calls)

# I7 V6–V8 + 空卷门（零出网）
bad_items = {
    "V6 paper_id 非 str": (Paper([{"item_ids": ["c1"]}], paper_id=1), Bank()),
    "V6 title 非 str": (Paper([{"item_ids": ["c1"]}], title=None), Bank()),
    "V6 bank 无 items": (Paper([{"item_ids": ["c1"]}]), object()),
    "V6 bank.items 不可调用": (Paper([{"item_ids": ["c1"]}]), type("B", (), {"items": 5})()),
    "V6 bank.items 返回不可迭代": (Paper([{"item_ids": ["c1"]}]), Bank(mode="notiterable")),
    "V6 bank.items 抛 TypeError": (Paper([{"item_ids": ["c1"]}]), Bank(mode="typeerror")),
    "V6 bank item id 非 str": (Paper([{"item_ids": ["c1"]}]),
                               Bank(items=[It(5, "choice", ["A", "B"], "A")])),
    "V6 bank item id 空白": (Paper([{"item_ids": ["c1"]}]),
                              Bank(items=[It("  ", "choice", ["A", "B"], "A")])),
    "V6 bank id 重复": (Paper([{"item_ids": ["c1"]}]),
                        Bank(items=[C1, It("c1", "choice", ["A", "B"], "A")])),
    "V6 sections 非 list/tuple": (Paper("sections"), Bank()),
    "V6 空 sections 且 item_ids 非 list": (Paper([], item_ids="c1"), Bank()),
    "V7 section 非 dict": (Paper([["c1"]]), Bank()),
    "V7 section.item_ids 非 list": (Paper([{"item_ids": "c1"}]), Bank()),
    "V6 题 id 非 str": (Paper([{"item_ids": [5]}]), Bank()),
    "V6 题 id 空白": (Paper([{"item_ids": [" "]}]), Bank()),
    "V6 题 id 不在 bank": (Paper([{"item_ids": ["zz"]}]), Bank()),
    "V6 item_type='essay'": (Paper([{"item_ids": ["e1"]}]),
                             Bank(items=[It("e1", "essay", [], "x")])),
    "V8 choice options 非 list": (Paper([{"item_ids": ["c1"]}]),
                                  Bank(items=[It("c1", "choice", None, "A")])),
    "V8 choice options len<2": (Paper([{"item_ids": ["c1"]}]),
                                Bank(items=[It("c1", "choice", ["A"], "A")])),
    "V8 choice options len 27": (Paper([{"item_ids": ["c1"]}]),
                                 Bank(items=[It("c1", "choice", [f"o{i}" for i in range(27)], "o0")])),
    "V8 choice 选项非 str": (Paper([{"item_ids": ["c1"]}]),
                             Bank(items=[It("c1", "choice", ["A", 7], "A")])),
    "V8 choice 标签重复": (Paper([{"item_ids": ["c1"]}]),
                           Bank(items=[It("c1", "choice", ["A. 一", "a. 二"], "A")])),
    "V8 choice 标答非 str": (Paper([{"item_ids": ["c1"]}]),
                              Bank(items=[It("c1", "choice", ["A", "B"], 5)])),
    "V8 choice 标答既非标签也非选项全文": (Paper([{"item_ids": ["c1"]}]),
                                          Bank(items=[It("c1", "choice", ["A", "B"], "Z")])),
    "空卷门 sections 空 + item_ids 空": (Paper([], item_ids=[]), Bank()),
    "空卷门 节内 item_ids 空": (Paper([{"item_ids": []}]), Bank()),
    "空卷门 全部节空": (Paper([{"item_ids": []}, {"item_ids": []}]), Bank()),
}
for nm, (pp, bb) in bad_items.items():
    cc = Client(TRANSCRIPT)
    expect_error(nm, lambda p=pp, b=bb: mod.ingest_photo(IMG, p, b, cc, Grader()))
    check(f"{nm} → 零出网", cc.calls == [], cc.calls)

# build_transcribe_prompt 独立承担同一套卷面守卫
expect_error("§3.5 prompt 也走 V6–V8",
             lambda: mod.build_transcribe_prompt(Paper([], item_ids=[]), Bank()))

# 转写非法在出网之后（client 已调恰好一次）
c11 = Client("not json at all")
expect_error("§6 转写非法在出网之后抛", lambda: mod.ingest_photo(IMG, P3, Bank(), c11, Grader()))
check("§6 转写非法时 client 仍恰好一次", len(c11.calls) == 1, c11.calls)

# 纯度自检：模块只 import 允许的名字
src = IMPL.read_text(encoding="utf-8")
banned = ["import os", "import random", "import time", "import datetime", "import os.path",
          "from xuexing", "import xuexing", "__future__", "open(", "environ", "urllib",
          "requests", "httpx", "datetime.now", "time.time", "random."]
hits = [b for b in banned if b in src.replace("from xuexing.types import Response, to_dict", "")]
check("§2 无禁用 import / 无 IO / 无时钟随机", not hits, hits)
check("§2 绝对导入 xuexing.types",
      "from xuexing.types import Response, to_dict" in src)
check("§2 无相对导入", "from ." not in src.replace("from .. ", ""))
check("§2 无 __future__", "__future__" not in src)
check("§2 注解为真实对象（无字符串注解）",
      "-> \"" not in src and ": \"" not in src)
imports = sorted({n.split(".")[0] for node in __import__("ast").walk(__import__("ast").parse(src))
                  for n in ([a.name for a in node.names] if isinstance(node, __import__("ast").Import)
                            else ([node.module or ""] if isinstance(node, __import__("ast").ImportFrom)
                                  else []))})
check("§2 import 清单 = json/math/re/dataclasses/typing/xuexing.types",
      set(imports) <= {"json", "math", "re", "dataclasses", "typing", "xuexing"}, imports)

print()
bad = [n for n, ok, _ in RESULTS if not ok]
print(f"TOTAL {len(RESULTS)} checks, FAILED {len(bad)}")
for n in bad:
    print("  FAILED:", n)
sys.exit(1 if bad else 0)
