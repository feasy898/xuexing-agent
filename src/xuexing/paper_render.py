"""paper_render —— 卷型卷成品渲染（家长/学校可读的打印友好 HTML 与纯文本备用）。

消费 xuexing.paper_by_spec.generate_paper_by_spec 的「大题-小题」结构卷 + 题库，
产出**自包含**成品卷：HTML（内联 CSS、A4 打印分页、卷头卷尾）与纯文本简版。
渲染是纯函数（无 IO、无随机、无时钟），同输入同输出。

红线（出卷侧，本模块的存在前提）：学生卷绝不携带作答依据。两个渲染函数对题库
Item **只读 stem 与 options 两个字段**——answer（答案）/ solution（解析）及题库
JSON 中的 source/verification 等字段一次都不触碰；``redline_report`` 是红线自检
器（按字段名取值、在产物中扫其出现），是唯一按名字引用这两个字段的函数。所有
动态文本经 ``html.escape`` 转义后才进入标记，题面含 ``<>&"'"`` 也只会按字面显示，
不产生任何可执行标记。CSS 类名刻意避开 answer / solution 词根（作答框用
``reply-box``），使「输出无 answer 词根」可被机器扫描。

打印分页（诚实的实现边界）：``@page { size: A4 }`` + ``@bottom-center { content:
counter(page) … }`` 是标准 CSS 分页媒体语法——支持 margin-box 的浏览器（Firefox、
Chromium 131+）自动打页码；不支持时由 ``position: fixed`` 的页脚条在打印时每页
重复显示卷名与满分（无页码）。绝无 JavaScript、无外链资源，单文件即印。

端点取舍（见 server.py）：渲染走独立 ``GET /papers/by-spec/{spec_id}/render.html``
（纯文本姊妹路径 ``render.txt``），不塞进 POST /papers/by-spec 的 JSON 响应——
交付物是给人打印的文档，浏览器/学校系统直接打开 URL 即得 text/html，零客户端
胶水；且 by-spec 出卷对 (spec_id, seed, difficulty_target) 确定性，GET 幂等语义
诚实，机器客户端的结构 JSON 也保持精瘦。
"""
from __future__ import annotations

import html
from math import isfinite

__all__ = [
    "PaperRenderError",
    "SUBJECT_LABELS",
    "STAGE_LABELS",
    "USAGE_LABELS",
    "FORBIDDEN_TOKENS",
    "human_paper_title",
    "format_points",
    "render_paper_html",
    "render_paper_text",
    "redline_report",
    "check_html_tag_balance",
]


class PaperRenderError(ValueError):
    """paper_render 渲染失败（卷面结构非法/题目缺失/题面空白）。"""


# 卷面人话标题的字段译名（未知值原样回显，转义后输出，绝不抛异常）。
SUBJECT_LABELS = {
    "math": "数学", "chinese": "语文", "english": "英语", "physics": "物理",
    "chemistry": "化学", "biology": "生物", "history": "历史",
    "geography": "地理", "politics": "政治", "science": "科学",
}
STAGE_LABELS = {"primary": "小学", "junior": "初中", "high": "高中"}
USAGE_LABELS = {"unit_test": "单元测试", "final_exam": "期末考试"}

# 红线自证：成品卷任何位置不允许出现的词根/标签（供验收门与测试扫描）。
# ASCII 词根 answer/solution 覆盖字段名泄漏；中文标签覆盖注释性泄漏。
FORBIDDEN_TOKENS = ("answer", "solution", "评分要点", "参考答案", "标准答案")

# HTML 空元素（无需闭配）；标签配平检查与渲染输出共用这份认知。
_VOID_TAGS = frozenset({
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
})

_REPLY_HEIGHTS = {"choice": "8mm", "fill": "8mm", "solve": "48mm"}
_REPLY_DEFAULT_HEIGHT = "30mm"
_TEXT_REPLY_LINE = "＿" * 18


def _esc(text) -> str:
    """动态文本 -> 转义后的 HTML 片段。非 str 先按 str() 收编再转义。"""
    return html.escape(text if isinstance(text, str) else str(text),
                       quote=True)


def _label(mapping: dict, value) -> str:
    return mapping.get(value, value if isinstance(value, str) else str(value))


def format_points(x) -> str:
    """分值 -> 卷面数字串：整数值去小数尾（3.0 -> "3"），7.5 -> "7.5"。"""
    if isinstance(x, float) and isfinite(x) and x.is_integer():
        return str(int(x))
    return str(x)


def human_paper_title(paper: dict) -> str:
    """卷面结构 -> 人话标题（"初中物理期末考试卷"）。缺译名的字段原样回显。"""
    return "".join([
        _label(STAGE_LABELS, paper.get("stage", "")),
        _label(SUBJECT_LABELS, paper.get("subject", "")),
        _label(USAGE_LABELS, paper.get("usage", "")),
        "卷",
    ])


def _validate_paper(paper: dict) -> dict:
    """卷面结构 fail-closed 校验：任一形态违规抛 PaperRenderError（渲染端
    不猜、不补、不降级——宁可不渲染也不渲染错卷）。返回原 dict 便于链式。"""
    if not isinstance(paper, dict):
        raise PaperRenderError(f"paper must be a dict, got {paper!r}")
    for key in ("spec_id", "subject", "stage", "usage"):
        if not isinstance(paper.get(key), str):
            raise PaperRenderError(f"paper.{key} must be a str, got {paper.get(key)!r}")
    if not isinstance(paper.get("spec_id"), str) or not paper["spec_id"].strip():
        raise PaperRenderError(f"paper.spec_id must be non-blank, got {paper.get('spec_id')!r}")
    duration = paper.get("duration_min")
    if not (isinstance(duration, int) and not isinstance(duration, bool) and duration > 0):
        raise PaperRenderError(f"paper.duration_min must be an int > 0, got {duration!r}")
    total = paper.get("total_points")
    if not (isinstance(total, (int, float)) and not isinstance(total, bool)
            and isfinite(total) and total > 0):
        raise PaperRenderError(f"paper.total_points must be a number > 0, got {total!r}")
    sections = paper.get("sections")
    if not isinstance(sections, list) or not sections:
        raise PaperRenderError(f"paper.sections must be a non-empty list, got {sections!r}")
    n_questions = 0
    for i, sec in enumerate(sections):
        if not isinstance(sec, dict):
            raise PaperRenderError(f"paper.sections[{i}] must be a dict, got {sec!r}")
        if not isinstance(sec.get("title"), str):
            raise PaperRenderError(f"paper.sections[{i}].title must be a str, got {sec.get('title')!r}")
        for key in ("count", "points_each", "section_points"):
            if not (isinstance(sec.get(key), (int, float))
                    and not isinstance(sec.get(key), bool) and isfinite(sec[key])):
                raise PaperRenderError(
                    f"paper.sections[{i}].{key} must be a finite number, got {sec.get(key)!r}")
        questions = sec.get("questions")
        if not isinstance(questions, list):
            raise PaperRenderError(f"paper.sections[{i}].questions must be a list, got {questions!r}")
        for j, q in enumerate(questions):
            if not isinstance(q, dict):
                raise PaperRenderError(
                    f"paper.sections[{i}].questions[{j}] must be a dict, got {q!r}")
            no = q.get("question_no")
            if not (isinstance(no, int) and not isinstance(no, bool)):
                raise PaperRenderError(
                    f"paper.sections[{i}].questions[{j}].question_no must be an int, got {no!r}")
            if not (isinstance(q.get("item_id"), str) and q["item_id"].strip()):
                raise PaperRenderError(
                    f"paper.sections[{i}].questions[{j}].item_id must be non-blank str, "
                    f"got {q.get('item_id')!r}")
            pts = q.get("points")
            if not (isinstance(pts, (int, float)) and not isinstance(pts, bool)
                    and isfinite(pts) and pts > 0):
                raise PaperRenderError(
                    f"paper.sections[{i}].questions[{j}].points must be a number > 0, got {pts!r}")
            n_questions += 1
    declared = paper.get("question_count")
    if declared != n_questions:
        raise PaperRenderError(
            f"paper.question_count {declared!r} != actual question total {n_questions}")
    return paper


def _item_for(bank, item_id: str, question_no: int):
    """题库取题 + 学生卷侧最小校验：只读 stem/options，题缺失/题面空白即抛
    （渲染端 fail-closed；红线：answer/solution 在此根本不可见）。"""
    item = bank.get(item_id)
    if item is None:
        raise PaperRenderError(f"question {question_no}: item not in bank: {item_id}")
    stem = getattr(item, "stem", None)
    if not (isinstance(stem, str) and stem.strip()):
        raise PaperRenderError(f"question {question_no}: item {item_id} has blank stem")
    return item


_CSS = """  @page {
    size: A4;
    margin: 16mm 15mm 20mm;
    @bottom-center {
      content: "第 " counter(page) " 页 / 共 " counter(pages) " 页";
      font-size: 9pt;
      color: #555;
    }
  }
  * { box-sizing: border-box; }
  body {
    max-width: 210mm;
    margin: 0 auto;
    padding: 10mm 12mm;
    font-family: "SimSun", "Songti SC", "Noto Serif CJK SC", serif;
    font-size: 10.5pt;
    line-height: 1.7;
    color: #111;
  }
  .paper-head { text-align: center; margin-bottom: 6mm; }
  .paper-title { font-size: 16pt; font-weight: 700; margin: 0 0 3mm; letter-spacing: 1px; }
  .paper-meta { font-size: 10pt; color: #333; margin-bottom: 2mm; }
  .paper-meta span { margin: 0 1.5mm; }
  .paper-note {
    font-size: 9.5pt; color: #444; text-align: left;
    border: 1px solid #bbb; border-radius: 2px;
    padding: 2mm 3mm; margin: 0 0 5mm;
  }
  .section { margin-bottom: 6mm; }
  .section-title {
    font-size: 12pt; font-weight: 700;
    margin: 0 0 3mm; padding-bottom: 1mm;
    border-bottom: 1px solid #999;
  }
  .section-points { font-size: 10.5pt; font-weight: 400; }
  .question { margin: 0 0 4mm; page-break-inside: avoid; break-inside: avoid; }
  .q-head { margin-bottom: 1mm; }
  .q-no { font-weight: 700; margin-right: 1mm; }
  .q-points { color: #444; margin-right: 1.5mm; }
  .q-stem { white-space: pre-wrap; }
  .q-options { margin: 1mm 0 0 7mm; }
  .q-option { display: block; margin: 0.5mm 0; }
  .reply-box {
    border: 1px solid #999; border-radius: 2px;
    margin-top: 2mm;
  }
  .blank-line { border-bottom: 1px solid #333; height: 8mm; margin-top: 2mm; }
  .page-footer {
    margin-top: 10mm; padding-top: 2mm;
    border-top: 1px solid #bbb;
    text-align: center; font-size: 9pt; color: #555;
  }
  @media print {
    body { padding: 0; }
    .page-footer { position: fixed; bottom: 0; left: 0; right: 0; margin: 0;
                   border-top: none; }
    .section-title { page-break-after: avoid; }
  }
"""


def _reply_html(item_type: str, has_options: bool) -> str:
    """题面之后的作答区：有选项的选择题不设（选项即作答载体）；无选项题按
    item_type 给出作答框（solve 高框、fill/choice 短线、其余中框）。"""
    if has_options:
        return ""
    height = _REPLY_HEIGHTS.get(item_type, _REPLY_DEFAULT_HEIGHT)
    if item_type == "fill":
        return '      <div class="blank-line"></div>\n'
    return f'      <div class="reply-box" style="height: {height};"></div>\n'


def render_paper_html(paper: dict, bank) -> str:
    """卷面结构 + 题库 -> 自包含打印友好 HTML 文档（UTF-8，无 JS/外链）。

    结构保证：小题号用骨架里的 question_no（全卷连续）；每题分值独立成
    ``<span class="q-points">``（验收门按出现次数/合计复核）；选择题选项
    逐项竖排；解答/填空题留作答框。红线见模块 docstring。
    """
    _validate_paper(paper)
    title = human_paper_title(paper)
    esc_spec = _esc(paper["spec_id"])
    total_s = format_points(paper["total_points"])
    duration = paper["duration_min"]
    n_q = paper["question_count"]

    parts = [
        "<!DOCTYPE html>\n",
        '<html lang="zh-CN">\n<head>\n<meta charset="utf-8">\n',
        f"<title>{_esc(title)}</title>\n",
        f"<!-- 成品卷：由 xuexing.paper_render 渲染；卷型 {esc_spec}，"
        f"seed {paper.get('seed', '')}，difficulty_target "
        f"{paper.get('difficulty_target', '')}。红线：本卷不含任何作答依据。 -->\n",
        f"<style>\n{_CSS}</style>\n</head>\n<body>\n",
        # 卷头：标题 / 总分 / 时长 / 题数 / 卷型 / 满分注意
        '<header class="paper-head">\n',
        f'  <h1 class="paper-title">{_esc(title)}</h1>\n',
        '  <div class="paper-meta">'
        f'<span>满分 {total_s} 分</span>'
        f'<span>考试时长 {duration} 分钟</span>'
        f'<span>共 {n_q} 题</span>'
        f'<span>卷型 {esc_spec}</span></div>\n',
        '  <p class="paper-note">满分注意：本卷满分 '
        f'{total_s} 分，考试时长 {duration} 分钟。请按题号顺序作答：选择题写出'
        '所选选项的字母；填空题把结论写在横线上；解答题在预留的作答框内写出'
        '必要过程，字迹工整、卷面整洁。</p>\n',
        "</header>\n",
    ]

    for sec in paper["sections"]:
        parts.extend([
            '<section class="section">\n',
            f'  <h2 class="section-title">{_esc(sec["title"])}'
            f'<span class="section-points">（每题 {format_points(sec["points_each"])} 分，'
            f'共 {format_points(sec["section_points"])} 分）</span></h2>\n',
        ])
        for q in sec["questions"]:
            item = _item_for(bank, q["item_id"], q["question_no"])
            stem = item.stem.strip()
            options = [str(o) for o in (getattr(item, "options", None) or [])]
            parts.append(f'  <div class="question" id="q{q["question_no"]}">\n')
            parts.append(
                '    <div class="q-head">'
                f'<span class="q-no">{q["question_no"]}.</span>'
                f'<span class="q-points">（{format_points(q["points"])}分）</span>'
                f'<span class="q-stem">{_esc(stem)}</span></div>\n')
            if options:
                parts.append('    <div class="q-options">\n')
                for opt in options:
                    parts.append(f'      <div class="q-option">{_esc(opt.strip())}</div>\n')
                parts.append("    </div>\n")
            parts.append(_reply_html(getattr(item, "item_type", ""), bool(options)))
            parts.append("  </div>\n")
        parts.append("</section>\n")

    parts.extend([
        f'<footer class="page-footer">{_esc(title)} · 满分 {total_s} 分 · '
        f"共 {n_q} 题</footer>\n",
        "</body>\n</html>\n",
    ])
    return "".join(parts)


def redline_report(paper: dict, bank, html_doc: str, text_doc: str) -> list:
    """红线自检 -> 违规列表（空列表 = 干净）。供验收门/测试/调用方复核：
    (a) 词根级：两份产物任何位置（含类名/注释）不得出现 FORBIDDEN_TOKENS；
    (b) 值级：把全部已选题的 stem/options 文本剔除后，残余（= 渲染层自己生成
        的全部文字）中不得出现任何已选题的 answer/solution 字段值——len>=2
        才扫（单字母选项标签 "B" 会被选项文本无害命中）。违规非空 = 渲染层
        把作答依据带进了学生卷。题干自带答案属题库数据质量，不在本报告
        （剔除 stem 后天然不误报，验收门另行 DATA-WARN 提示）。"""
    violations = []
    low = html_doc.lower() + text_doc.lower()
    for tok in FORBIDDEN_TOKENS:
        if tok.lower() in low:
            violations.append(f"全卷出现禁用词根 {tok!r}")
    if violations:
        return violations  # 词根已击穿，值级扫描不必再做
    stems_html, stems_text, items = [], [], []
    for sec in paper["sections"]:
        for q in sec["questions"]:
            item = bank.get(q["item_id"])
            if item is None:
                continue
            items.append((q["question_no"], item))
            stems_html.append(_esc(item.stem.strip()))
            stems_text.append(item.stem.strip())
            for opt in (getattr(item, "options", None) or []):
                stems_html.append(_esc(str(opt).strip()))
                stems_text.append(str(opt).strip())
    residual_html = html_doc
    for s in sorted(stems_html, key=len, reverse=True):
        residual_html = residual_html.replace(s, "")
    residual_text = text_doc
    for s in sorted(stems_text, key=len, reverse=True):
        residual_text = residual_text.replace(s, "")
    for no, item in items:
        for fname in ("answer", "solution"):
            val = str(getattr(item, fname, "") or "").strip()
            if len(val) < 2:
                continue
            if val in residual_text:
                violations.append(
                    f"text: 第 {no} 题（{item.id}）{fname} 字段值 {val!r} 泄入渲染产物")
            if val in residual_html or _esc(val) in residual_html:
                violations.append(
                    f"html: 第 {no} 题（{item.id}）{fname} 字段值 {val!r} 泄入渲染产物")
    return violations


def render_paper_text(paper: dict, bank) -> str:
    """卷面结构 + 题库 -> 纯文本简版（无标记、无分页；HTML 不可用时的备用）。
    与 HTML 同一次装订：同题序、同题号、同分值。"""
    _validate_paper(paper)
    title = human_paper_title(paper)
    total_s = format_points(paper["total_points"])
    lines = [
        title,
        f"卷型 {paper['spec_id']}（seed {paper.get('seed', '')}）"
        f" · 满分 {total_s} 分 · 考试时长 {paper['duration_min']} 分钟"
        f" · 共 {paper['question_count']} 题",
        "满分注意：请按题号顺序作答——选择题写所选选项字母，填空题把结论写在"
        "横线上，解答题写出必要过程。",
        "",
    ]
    for sec in paper["sections"]:
        lines.append(
            f"{sec['title']}（每题 {format_points(sec['points_each'])} 分，"
            f"共 {format_points(sec['section_points'])} 分）")
        for q in sec["questions"]:
            item = _item_for(bank, q["item_id"], q["question_no"])
            lines.append(f"  {q['question_no']}.（{format_points(q['points'])}分）"
                         f"{item.stem.strip()}")
            for opt in (getattr(item, "options", None) or []):
                lines.append(f"     {str(opt).strip()}")
            if not (getattr(item, "options", None) or []):
                lines.append(f"     {_TEXT_REPLY_LINE}")
        lines.append("")
    return "\n".join(lines)


def check_html_tag_balance(doc: str) -> list:
    """HTML 文档 -> 标签配平错误列表（空列表 = 配平）。供验收门与测试使用：
    逐开标签入栈、闭标签核对；空元素免闭配；多余闭标签/未闭合/交叉嵌套都报。"""
    from html.parser import HTMLParser

    errors: list = []
    stack: list = []

    class _Checker(HTMLParser):
        def handle_starttag(self, tag, attrs):
            if tag not in _VOID_TAGS:
                stack.append((tag, self.getpos()))

        def handle_startendtag(self, tag, attrs):  # <tag/> 自闭形式
            pass

        def handle_endtag(self, tag):
            if tag in _VOID_TAGS:
                return
            if not stack:
                errors.append(f"line {self.getpos()[0]}: closing </{tag}> with empty stack")
                return
            top, pos = stack[-1]
            if top == tag:
                stack.pop()
                return
            names = [t for t, _ in stack]
            if tag in names:
                errors.append(
                    f"line {self.getpos()[0]}: </{tag}> crosses unclosed <{top}> "
                    f"opened at line {pos[0]}")
                while stack and stack[-1][0] != tag:
                    stack.pop()
                if stack:
                    stack.pop()
            else:
                errors.append(f"line {self.getpos()[0]}: stray closing </{tag}>, "
                              f"expected </{top}> (opened at line {pos[0]})")

    checker = _Checker(convert_charrefs=True)
    checker.feed(doc)
    checker.close()
    for tag, pos in stack:
        errors.append(f"unclosed <{tag}> opened at line {pos[0]}")
    return errors
