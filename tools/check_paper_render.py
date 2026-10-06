"""成品卷渲染门——渲染层验收（无参运行，exit 0 = 门通过）。

为什么需要本工具：POST /papers/by-spec 的结构卷已有确定性结构门
（tools/check_paper_spec.py），成品卷渲染层（xuexing.paper_render，端点
GET /papers/by-spec/{spec_id}/render.html 与 render.txt）需要同款离线门：
对全部能出卷的卷型真实渲染 HTML+纯文本并逐项机器校验。

逐卷型判定：
- OK —— 出卷成功且渲染校验全过，逐项断言：
  (1) 合法性：标签配平（paper_render.check_html_tag_balance 零错误）、
      DOCTYPE/charset 在位、自包含（无 script/link/src/http 外链）、
      A4 打印分页 CSS（@page + size: A4）在位；
  (2) 题数==结构数：HTML 中 id="qN" 的题块数 == 骨架 question_count ==
      Σ大题 count，小题号 1..N 每号恰出现一次且有序；
  (3) 分值出现次数：q-points 分值标注出现次数 == 小题数、逐题分值之和 ==
      卷型总分；大题标注条数 == 大题数、Σ"共X分" == 卷型总分；
  (4) 红线：全卷无 answer/solution 词根与「评分要点/参考答案/标准答案」
      字样；逐小题在自己的题块/文本段内不出现该题 answer/solution 字段值
      （长度>=2 才扫——单字母选项标签 "B" 会被选项文本无害命中，不算泄漏）；
  (5) 纯文本简版：含全部小题号与大题标题，无 HTML 块级标记，红线同(4)。
- SKIP —— 出卷被拒且原因属已知类（同 check_paper_spec 的 FAIL-CLOSED 分类）：
  无卷可渲染是设计行为，如实打印原因。
- UNEXPECTED —— 其他异常：任何一条都判门失败（exit 1）。

门通过条件（exit 0）：全部卷型判定完毕、UNEXPECTED==0、OK>=3（验收门：至少
3 套真实卷型渲染出合法 HTML）。纯校验不落盘；人工视检样本用
tools/render_paper_sample.py 生成到 out/。

用法：python tools/check_paper_render.py [--seed 42] [--data-dir data]
"""
import argparse
import os
import re
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
)
from xuexing.paper_render import (  # noqa: E402
    PaperRenderError,
    check_html_tag_balance,
    redline_report,
    render_paper_html,
    render_paper_text,
)
from xuexing.paper_spec import PaperSpecError  # noqa: E402

# 与 check_paper_spec 同款 fail-closed 分类（之外的异常一律 UNEXPECTED）
EXPECTED_REASON_PREFIXES = (
    ("spec sections points sum", "spec-分值自相矛盾(V8)"),
    ("no item files", "学段无题库文件"),
    ("has no bank form mapping", "题型无等价类映射"),
    ("not enough eligible items", "同型题不足"),
)

MIN_OK = 3  # 验收门：至少 3 套真实卷型渲染出合法 HTML

_Q_BLOCK_RE = re.compile(r'<div class="question" id="q(\d+)">')
_Q_POINTS_RE = re.compile(r'<span class="q-points">（([0-9.]+)分）</span>')
_SECTION_POINTS_RE = re.compile(r'<span class="section-points">（每题 [0-9.]+ 分，共 ([0-9.]+) 分）</span>')
_TEXT_Q_RE = re.compile(r"(?m)^  (\d+)\.（([0-9.]+)分）")


def classify_reason(message: str):
    for needle, label in EXPECTED_REASON_PREFIXES:
        if needle in message:
            return label
    return None


def _selected_items(paper: dict, bank):
    """按卷面顺序取 (question_no, item) 列表（渲染内核已保证题在库）。"""
    out = []
    for sec in paper["sections"]:
        for q in sec["questions"]:
            item = bank.get(q["item_id"])
            if item is not None:
                out.append((q["question_no"], item))
    return out


def data_warnings(paper: dict, bank) -> list:
    """题干自带答案/解析（题库数据质量问题，非渲染层泄漏）-> 提示列表。
    单独分类不判门失败：渲染层对 stem 忠实转义原样呈现，改题干归题库治理。"""
    warns = []
    for no, item in _selected_items(paper, bank):
        stem = item.stem.strip()
        for fname in ("answer", "solution"):
            val = str(getattr(item, fname, "") or "").strip()
            if len(val) >= 2 and val in stem:
                warns.append(f"第 {no} 题（{item.id}）题干自带 {fname} 字段值 {val!r}")
    return warns


def render_side_leaks(html_doc: str, text_doc: str, paper: dict, bank) -> list:
    """渲染侧红线判定（委托内核 redline_report，验收门与单测同一实现）。
    违规列表非空 = 渲染层把作答依据带进了学生卷（判门失败）。"""
    return redline_report(paper, bank, html_doc, text_doc)


def check_rendered(paper: dict, bank) -> list:
    """OK 判定的逐项断言（任何一条不符抛 AssertionError）。返回 (html, text)
    供样本复用——这里只做纯校验，不落盘。"""
    html_doc = render_paper_html(paper, bank)
    text_doc = render_paper_text(paper, bank)
    n_q = paper["question_count"]
    spec_id = paper["spec_id"]

    # (1) 合法性：标签配平 / DOCTYPE / charset / 自包含 / A4 打印 CSS
    errs = check_html_tag_balance(html_doc)
    assert not errs, f"{spec_id}: 标签配平错误 {errs[:3]}"
    assert html_doc.startswith("<!DOCTYPE html>"), f"{spec_id}: 缺 DOCTYPE"
    assert 'charset="utf-8"' in html_doc, f"{spec_id}: 缺 charset"
    for needle in ("<script", "<link", "src=", "http://", "https://", "url("):
        assert needle not in html_doc.lower(), f"{spec_id}: 非自包含，出现 {needle!r}"
    assert "@page" in html_doc and "size: A4" in html_doc, f"{spec_id}: 缺 A4 打印分页 CSS"
    assert "counter(page)" in html_doc, f"{spec_id}: 缺页脚页码 CSS"

    # (2) 题数==结构数：题块数、题号连续且每号恰一次
    ids = [int(m) for m in _Q_BLOCK_RE.findall(html_doc)]
    assert ids == list(range(1, n_q + 1)), \
        f"{spec_id}: 小题号非连续 1..{n_q}（得到 {len(ids)} 块）"
    assert n_q == sum(len(s["questions"]) for s in paper["sections"]) == len(ids), \
        f"{spec_id}: 渲染题块数 {len(ids)} != 骨架题数 {n_q}"

    # (3) 分值出现次数：逐题标注次数==题数、合计==总分；大题标注同理
    pts = [float(m) for m in _Q_POINTS_RE.findall(html_doc)]
    assert len(pts) == n_q, f"{spec_id}: 分值标注 {len(pts)} 处 != 题数 {n_q}"
    assert sum(pts) == float(paper["total_points"]), \
        f"{spec_id}: 分值标注合计 {sum(pts)} != 总分 {paper['total_points']}"
    sec_pts = [float(m) for m in _SECTION_POINTS_RE.findall(html_doc)]
    assert len(sec_pts) == len(paper["sections"]), \
        f"{spec_id}: 大题分值标注 {len(sec_pts)} 处 != 大题数 {len(paper['sections'])}"
    assert sum(sec_pts) == float(paper["total_points"]), \
        f"{spec_id}: 大题分值合计 {sum(sec_pts)} != 总分 {paper['total_points']}"

    # (4) 红线：词根级 + 渲染侧值级泄漏，同一实现走内核 redline_report
    #     （剔除 stem/options 后残余不得含 answer/solution 值；题干自带答案
    #     属题库数据质量，另行 DATA-WARN）。
    violations = render_side_leaks(html_doc, text_doc, paper, bank)
    assert not violations, f"{spec_id}: {violations[:3]}"

    # (5) 纯文本简版：题号齐全有序、大题标题在位、无块级标记（红线已在(4)同查）
    text_nos = [int(m[0]) for m in _TEXT_Q_RE.findall(text_doc)]
    assert text_nos == list(range(1, n_q + 1)), f"{spec_id}: 文本版小题号非连续"
    for sec in paper["sections"]:
        assert sec["title"] in text_doc, f"{spec_id}: 文本版缺大题标题 {sec['title']!r}"
    for tag in ("<div", "<html", "<p>", "<span"):
        assert tag not in text_doc, f"{spec_id}: 文本版含 HTML 标记 {tag!r}"
    return html_doc, text_doc, data_warnings(paper, bank)


def main() -> int:
    ap = argparse.ArgumentParser(description="成品卷渲染门（HTML+纯文本机器校验）")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--difficulty-target", type=float, default=0.5)
    ap.add_argument("--data-dir", default=os.path.join(ROOT, "data"))
    args = ap.parse_args()

    catalog_path = os.path.join(args.data_dir, "curriculum", "paper_specs.json")
    catalog = load_spec_catalog(catalog_path)
    banks = {}  # (subject, stage) -> bank，同进程复用

    ok, skipped, unexpected, data_warns = [], [], [], []
    for spec_id, raw in catalog.items():
        try:
            key = (raw["subject"], raw["stage"])
            if key not in banks:
                banks[key] = load_stage_bank(args.data_dir, raw["subject"], raw["stage"])[0]
            paper = generate_paper_by_spec(
                banks[key], raw, seed=args.seed,
                difficulty_target=args.difficulty_target, spec_id=spec_id)
            html_doc, text_doc, warns = check_rendered(paper, banks[key])
            for w in warns:
                data_warns.append(f"{spec_id}  {w}")
            ok.append(f"{spec_id}  小题×{paper['question_count']} "
                      f"html {len(html_doc)}B text {len(text_doc)}B")
        except (PaperSpecError, PaperBySpecError) as e:
            label = classify_reason(str(e))
            if label is None:
                unexpected.append(f"{spec_id}  {type(e).__name__}: {e}")
            else:
                skipped.append(f"{spec_id}  [{label}] 无卷可渲染（如实报缺）")
        except PaperRenderError as e:
            unexpected.append(f"{spec_id}  PaperRenderError: {e}")
        except AssertionError as e:
            unexpected.append(f"{spec_id}  校验失败: {e}")

    print(f"成品卷渲染门 {catalog_path}：{len(catalog)} 套（seed={args.seed} "
          f"difficulty_target={args.difficulty_target}）")
    print(f"\n== OK 渲染成功且逐项校验通过（{len(ok)} 套） ==")
    for line in ok:
        print(f"  OK           {line}")
    print(f"\n== SKIP 出卷被拒无卷可渲染（{len(skipped)} 套） ==")
    for line in skipped:
        print(f"  SKIP         {line}")
    print(f"\n== DATA-WARN 题干自带作答依据（题库数据质量，非渲染层泄漏，不判门）"
          f"（{len(data_warns)} 条） ==")
    for line in data_warns:
        print(f"  DATA-WARN    {line}")
    if unexpected:
        print(f"\n== UNEXPECTED（{len(unexpected)} 套，判门失败） ==")
        for line in unexpected:
            print(f"  UNEXPECTED   {line}")

    gate = (
        len(ok) + len(skipped) + len(unexpected) == len(catalog)
        and not unexpected
        and len(ok) >= MIN_OK
    )
    print("\n" + f"OK={len(ok)} SKIP={len(skipped)} UNEXPECTED={len(unexpected)} "
                 f"判定总数={len(catalog)}")
    if gate:
        print(f"RENDER-CHECK-OK（全部卷型判定完毕、零 UNEXPECTED、渲染成功 >= {MIN_OK}）")
        return 0
    print("RENDER-CHECK-FAIL（门未通过）")
    return 1


if __name__ == "__main__":
    sys.exit(main())
