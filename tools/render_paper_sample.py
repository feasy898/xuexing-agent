"""成品卷渲染样本生成——供人工视检（验收 b）。

按卷型真实出卷并渲染自包含 HTML + 纯文本简版，写到 out/ 下（默认
out/paper_render_sample/{spec_id}_seed{seed}.html / .txt）。样本文件头部注释
自带生成参数（卷型/seed/difficulty_target），可用同参数重新生成比对。

机器校验走 tools/check_paper_render.py（渲染门）；本工具只负责落盘样本。

用法：
  python tools/render_paper_sample.py                        # 默认初中物理期末
  python tools/render_paper_sample.py --spec-id spec_his_jr_final --seed 7
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
    generate_paper_by_spec,
    load_spec_catalog,
    load_stage_bank,
)
from xuexing.paper_render import render_paper_html, render_paper_text  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="成品卷渲染样本生成（人工视检用）")
    ap.add_argument("--spec-id", default="spec_phy_jr_final")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--difficulty-target", type=float, default=0.5)
    ap.add_argument("--data-dir", default=os.path.join(ROOT, "data"))
    ap.add_argument("--out-dir", default=os.path.join(ROOT, "out", "paper_render_sample"))
    args = ap.parse_args()

    catalog = load_spec_catalog(os.path.join(args.data_dir, "curriculum", "paper_specs.json"))
    if args.spec_id not in catalog:
        print(f"spec not found: {args.spec_id}（可用：{', '.join(sorted(catalog))}）")
        return 1
    raw = catalog[args.spec_id]
    bank, _grades = load_stage_bank(args.data_dir, raw["subject"], raw["stage"])
    paper = generate_paper_by_spec(bank, raw, seed=args.seed,
                                   difficulty_target=args.difficulty_target,
                                   spec_id=args.spec_id)
    html_doc = render_paper_html(paper, bank)
    text_doc = render_paper_text(paper, bank)

    os.makedirs(args.out_dir, exist_ok=True)
    base = f"{args.spec_id}_seed{args.seed}"
    html_path = os.path.join(args.out_dir, base + ".html")
    text_path = os.path.join(args.out_dir, base + ".txt")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_doc)
    with open(text_path, "w", encoding="utf-8") as f:
        f.write(text_doc)
    print(f"样本已生成（spec={args.spec_id} seed={args.seed} "
          f"difficulty_target={args.difficulty_target} 小题×{paper['question_count']}）：")
    print(f"  {os.path.relpath(html_path, ROOT)}  （浏览器打开即可打印视检）")
    print(f"  {os.path.relpath(text_path, ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
