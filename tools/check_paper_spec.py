"""卷型库驱动的出卷——确定性结构门（无参运行，exit 0 = 门通过）。

为什么需要本工具：owner 裁定「以卷子生成为核心（符合学校惯例、家长可理解）」，
data/curriculum/paper_specs.json 的 21 套卷型（海南默认 profile）此前零消费。
本工具是 POST /papers/by-spec（内核 xuexing.paper_by_spec）的离线确定性门：
无参跑全部卷型出卷并逐项断言卷面结构与卷型一致。

逐卷型判定（与验收口径一一对应）：
- OK —— 出卷成功，逐项断言：大题数==spec；逐大题 标题/形态/题数/每题分值/
  大题分值==spec；小题号全卷连续 1..N；逐小题分值==所在大题 points_each；
  分值合计（Σ小题分==Σ大题分）==卷型 total_points；时长==spec；题目全部来自
  既有题库、全卷无重复、逐题题型保真（同型判定可复算，无别题型凑数）。
- FAIL-CLOSED —— 出卷被拒且原因属已知类：卷型分值自相矛盾（Σcount×
  points_each != total_points，paper_spec V8）、学段无题库文件、题型无等价
  类映射、同型题不足。如实报缺，不降级凑题——这是设计行为，逐条打印原因。
- UNEXPECTED —— 其他异常：任何一条都判门失败（exit 1）。

门通过条件（exit 0）：21 套卷型全部判定完毕、UNEXPECTED==0、OK>=3（验收
门 1：至少 3 套真实卷型逐项==spec，海南 profile 的都算）。

用法：python tools/check_paper_spec.py [--seed 42] [--data-dir data]
"""
import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

try:  # Windows 控制台中文输出保护
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

from xuexing.paper_by_spec import (  # noqa: E402
    PaperBySpecError,
    generate_paper_by_spec,
    load_spec_catalog,
    load_stage_bank,
    matches_form,
)
from xuexing.paper_spec import PaperSpecError  # noqa: E402

# 已知 fail-closed 原因前缀 → 分类标签（之外的异常一律 UNEXPECTED，判门失败）
EXPECTED_REASON_PREFIXES = (
    ("spec sections points sum", "spec-分值自相矛盾(V8)"),
    ("no item files", "学段无题库文件"),
    ("has no bank form mapping", "题型无等价类映射"),
    ("not enough eligible items", "同型题不足"),
)

MIN_OK = 3  # 验收门 1：至少 3 套真实卷型逐项==spec


def assert_structure(paper, raw, bank):
    """OK 判定的逐项断言（任何一条不符抛 AssertionError）。"""
    assert paper["spec_id"] == raw["id"]
    assert paper["subject"] == raw["subject"]
    assert paper["stage"] == raw["stage"]
    assert paper["usage"] == raw["usage"]
    assert paper["duration_min"] == raw["duration_min"], "时长不一致"
    assert paper["total_points"] == raw["total_points"], "卷型总分不一致"
    # 大题数、逐大题结构与 spec 一致
    assert len(paper["sections"]) == len(raw["sections"]), "大题数不一致"
    for sec, raw_sec in zip(paper["sections"], raw["sections"]):
        assert sec["title"] == raw_sec["title"], f"大题标题不一致: {sec['title']!r}"
        assert sec["form"] == raw_sec["form"], f"大题形态不一致: {sec['title']!r}"
        assert sec["count"] == raw_sec["count"], f"大题题数不一致: {sec['title']!r}"
        assert sec["points_each"] == raw_sec["points_each"], f"每题分值不一致: {sec['title']!r}"
        assert sec["section_points"] == raw_sec["count"] * raw_sec["points_each"]
        assert len(sec["questions"]) == raw_sec["count"]
        # 题型保真：逐题可复算同型判定（无别题型凑数）
        for q in sec["questions"]:
            item = bank.get(q["item_id"])
            assert item is not None, f"题目不在题库: {q['item_id']}"
            assert matches_form(item, raw_sec["form"]), \
                f"题型不符: {q['item_id']} 不属于 {raw_sec['form']}"
    # 小题号全卷连续、逐小题分值落位
    expected_nos = list(range(1, paper["question_count"] + 1))
    nos = [q["question_no"] for sec in paper["sections"] for q in sec["questions"]]
    assert nos == expected_nos, "小题号不连续"
    # 分值合计 == 卷型总分（Σ小题分 == Σ大题分 == total_points）
    question_points = sum(q["points"] for sec in paper["sections"]
                          for q in sec["questions"])
    section_points = sum(sec["section_points"] for sec in paper["sections"])
    assert question_points == section_points == raw["total_points"], \
        f"分值合计 {question_points}/{section_points} != {raw['total_points']}"
    # 全卷题序无重复、平铺题序与装订一致
    flat = [q["item_id"] for sec in paper["sections"] for q in sec["questions"]]
    assert paper["item_ids"] == flat
    assert len(set(flat)) == len(flat), "题目重复"
    assert paper["question_count"] == len(flat) == sum(s["count"] for s in raw["sections"])


def classify_reason(message: str) -> str | None:
    # PaperSpecError 的分和消息自成一个完整句子；PaperBySpecError 以「section N
    # (标题, form=…): 原因…」开头——故按子串定位原因，而非前缀。
    for needle, label in EXPECTED_REASON_PREFIXES:
        if needle in message:
            return label
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="卷型库驱动出卷的确定性结构门")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--difficulty-target", type=float, default=0.5)
    ap.add_argument("--data-dir", default=os.path.join(ROOT, "data"))
    args = ap.parse_args()

    catalog_path = os.path.join(args.data_dir, "curriculum", "paper_specs.json")
    catalog = load_spec_catalog(catalog_path)
    banks = {}  # (subject, stage) -> (bank, grades)，同进程复用

    ok, fail_closed, unexpected = [], [], []
    for spec_id, raw in catalog.items():
        try:
            key = (raw["subject"], raw["stage"])
            if key not in banks:
                banks[key] = load_stage_bank(args.data_dir, raw["subject"], raw["stage"])
            bank, grades = banks[key]
            paper = generate_paper_by_spec(
                bank, raw, seed=args.seed, difficulty_target=args.difficulty_target,
                spec_id=spec_id)
            assert_structure(paper, raw, bank)
            q = paper["question_count"]
            ok.append(f"{spec_id}  大题×{len(paper['sections'])} 小题×{q} "
                      f"总分{paper['total_points']} 时长{paper['duration_min']}min "
                      f"题库年级{grades}")
        except (PaperSpecError, PaperBySpecError) as e:
            label = classify_reason(str(e))
            if label is None:
                unexpected.append(f"{spec_id}  {type(e).__name__}: {e}")
            else:
                fail_closed.append(f"{spec_id}  [{label}] {e}")
        except Exception as e:  # noqa: BLE001  断言失败/其他异常都算门失败
            unexpected.append(f"{spec_id}  {type(e).__name__}: {e}")

    print(f"卷型库 {catalog_path}：{len(catalog)} 套（seed={args.seed} "
          f"difficulty_target={args.difficulty_target}）")
    print(f"\n== OK 出卷成功且逐项==spec（{len(ok)} 套） ==")
    for line in ok:
        print(f"  OK           {line}")
    print(f"\n== FAIL-CLOSED 如实报缺（{len(fail_closed)} 套） ==")
    for line in fail_closed:
        print(f"  FAIL-CLOSED  {line}")
    if unexpected:
        print(f"\n== UNEXPECTED（{len(unexpected)} 套，判门失败） ==")
        for line in unexpected:
            print(f"  UNEXPECTED   {line}")

    verdict_lines = [f"OK={len(ok)}", f"FAIL-CLOSED={len(fail_closed)}",
                     f"UNEXPECTED={len(unexpected)}", f"判定总数={len(catalog)}"]
    gate = (
        len(ok) + len(fail_closed) + len(unexpected) == len(catalog)
        and not unexpected
        and len(ok) >= MIN_OK
    )
    print("\n" + " ".join(verdict_lines))
    if gate:
        print(f"PAPER-SPEC-CHECK-OK（全部卷型判定完毕、零 UNEXPECTED、OK>= {MIN_OK}）")
        return 0
    print("PAPER-SPEC-CHECK-FAIL（门未通过）")
    return 1


if __name__ == "__main__":
    sys.exit(main())
