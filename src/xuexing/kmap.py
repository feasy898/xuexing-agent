"""kmap —— 知识地图可视化渲染层（学情"知识地图"从 JSON 到人可读的 HTML）。

owner 原话「根据错误就可以绘制知识地图，进而指导未来的进一步学习」的"绘制"
字面交付：把诊断内核真实产出的画像（逐 KP mastery+置信度，GET /learners/{id}/profile
同源）、学习路线（build_plan，与 GET /learners/{id}/plan 同一引擎同一入参）和
学科级知识图谱（load_kpgraph_subject 装载）渲染成**自包含** HTML——内联 CSS/SVG、
零外部库、零 JavaScript，浏览器直接打开即读。

与 paper_render 同款纪律：
- 渲染是纯函数（无 IO、无随机、无时钟），同输入同输出；唯一"时间"来自
  Profile.updated_at（诊断时刻），本模块不读时钟。
- 所有动态文本经 html.escape 转义后才进入标记；知识点名/章节名含 <>&"'" 也
  只按字面显示，不产生可执行标记。
- 热力色阶：色相 红(掌握0)→绿(掌握1)，置信度以填充透明度表达（0 证据→最淡），
  薄弱（m<0.65，与 route 同阈值）另加红描边；画像外知识点灰色。
- 不编造：画像没有的知识点一律灰色"画像外"，绝不给假掌握度；空学习者/无数据
  学科渲染诚实空态页，不渲染想象中的数据。

聚合策略（大学科可读性）：学科页按 年级→章（cluster）→KP 两级 <details> 折叠
（原生元素，无 JS 锚点展开），顶部另有 SVG 年级×知识点热力条总览；语文 677 KP
全量渲染下文件体积仍在 2MB 量级以下。薄弱 top10 取自学习路线前 10 步
（影响×缺口优先、先序有效，route 契约排序），每步带策略建议动作；路线引擎
异常时如实降级为"掌握度升序+直接策略匹配"，并在页面上注明降级原因。
"""
from __future__ import annotations

import html

from xuexing.paper_render import SUBJECT_LABELS
from xuexing.route import RouteError, build_plan
from xuexing.types import Profile

__all__ = [
    "MASTERY_THRESHOLD",
    "WEAK_TOP_N",
    "build_subject_kmap",
    "build_overview_kmap",
    "render_kmap_html",
]

# 与 route.build_plan 缺省阈值一致；薄弱判定口径与学习路线完全同源。
MASTERY_THRESHOLD = 0.65
WEAK_TOP_N = 10

_GRADE_CN = {1: "一", 2: "二", 3: "三", 4: "四", 5: "五", 6: "六", 7: "七",
             8: "八", 9: "九", 10: "十", 11: "十一", 12: "十二"}


def _grade_label(grade: int) -> str:
    return f"{_GRADE_CN.get(grade, str(grade))}年级"


def _esc(text) -> str:
    return html.escape("" if text is None else str(text), quote=True)


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def mastery_hue(mastery: float) -> int:
    """掌握度 [0,1] -> 色相 [0,140]（0=红 薄弱，140=绿 熟练）。"""
    return round(_clamp01(mastery) * 140)


def heat_fill(mastery: float, confidence: float) -> str:
    """热力填充色：色相编码掌握度，透明度编码置信度（0 证据 -> 最淡 0.35）。"""
    hue = mastery_hue(mastery)
    alpha = round(0.35 + 0.65 * _clamp01(confidence), 3)
    return f"hsla({hue}, 62%, 78%, {alpha})"


def _kp_view(kp, profile: Profile) -> dict:
    """单知识点渲染视图。mastery/confidence 仅在画像含该点时给出（诚实缺省）。"""
    covered = kp.id in profile.mastery
    view = {
        "kp_id": kp.id,
        "name": kp.name,
        "grade": kp.grade,
        "cluster": kp.cluster,
        "anchor": f"kp-{kp.id}",
        "mastery": None,
        "confidence": None,
        "evidence": None,
    }
    if covered:
        m = profile.mastery[kp.id]
        n = profile.evidence.get(kp.id, 0)
        c = profile.confidence(kp.id)
        view["mastery"] = m
        view["confidence"] = round(c, 4)
        view["evidence"] = n
    return view


def _aggregate_grades(graph, profile: Profile) -> tuple[list[dict], dict]:
    """全部图谱知识点按 年级升序→章名升序→kp_id 升序 聚成两级层级。"""
    by_grade: dict[int, dict[str, list]] = {}
    for kp in graph.kps():
        by_grade.setdefault(kp.grade, {}).setdefault(kp.cluster, []).append(
            _kp_view(kp, profile))

    grades: list[dict] = []
    for grade in sorted(by_grade):
        clusters = []
        for cluster in sorted(by_grade[grade]):
            kps = by_grade[grade][cluster]
            clusters.append({"cluster": cluster, "kps": kps})
        grades.append({"grade": grade, "label": _grade_label(grade),
                       "clusters": clusters})

    stats = {"total": 0, "covered": 0, "measured": 0, "weak": 0, "m_sum": 0.0}
    for g in grades:
        g_stats = {"n": 0, "covered": 0, "measured": 0, "weak": 0, "m_sum": 0.0}
        for c in g["clusters"]:
            for v in c["kps"]:
                g_stats["n"] += 1
                if v["mastery"] is not None:
                    g_stats["covered"] += 1
                    g_stats["m_sum"] += v["mastery"]
                    if v["evidence"] > 0:
                        g_stats["measured"] += 1
                    if v["mastery"] < MASTERY_THRESHOLD:
                        g_stats["weak"] += 1
        g["n"] = g_stats["n"]
        g["covered"] = g_stats["covered"]
        g["measured"] = g_stats["measured"]
        g["weak"] = g_stats["weak"]
        g["avg"] = (round(g_stats["m_sum"] / g_stats["covered"], 4)
                    if g_stats["covered"] else None)
        stats["total"] += g_stats["n"]
        stats["covered"] += g_stats["covered"]
        stats["measured"] += g_stats["measured"]
        stats["weak"] += g_stats["weak"]
        stats["m_sum"] += g_stats["m_sum"]
    stats["avg"] = (round(stats["m_sum"] / stats["covered"], 4)
                    if stats["covered"] else None)
    del stats["m_sum"]
    # 折叠策略：小图谱全展开；大图谱只展开第一个有作答证据的年级（其余可点开）
    open_set = set()
    if stats["total"] <= 80:
        open_set = {g["grade"] for g in grades}
    else:
        for g in grades:
            if g["measured"] > 0:
                open_set = {g["grade"]}
                break
    for g in grades:
        g["open"] = g["grade"] in open_set
    return grades, stats


def _suggestions_from_plan(profile: Profile, graph, strategies, bank, today):
    """薄弱 top10 + 建议动作：与 GET /learners/{id}/plan 同一引擎同一入参。

    返回 (weak_top, plan_available, plan_note, reviews_n)。路线引擎异常
    （如先序死锁）时如实降级：掌握度升序直接取前 10，策略逐点匹配，
    plan_note 在页面上注明降级原因——不静默、不编造。"""
    try:
        plan = build_plan(profile, bank, graph, strategies, today,
                          mastery_threshold=MASTERY_THRESHOLD)
    except RouteError as e:
        weak = sorted(
            ((kp_id, m) for kp_id, m in profile.mastery.items()
             if m < MASTERY_THRESHOLD and graph.has(kp_id)),
            key=lambda t: (t[1], t[0]),
        )[:WEAK_TOP_N]
        rows = []
        for kp_id, m in weak:
            kp = graph.get(kp_id)
            try:
                strategy = strategies.select(m, kp.grade)
                s_name, s_id = strategy.name, strategy.id
            except Exception:
                s_name, s_id = "无匹配策略", ""
            rows.append(_suggestion_row(kp_id, kp, profile, s_id, s_name,
                                        f"mastery={m:.2f} < {MASTERY_THRESHOLD}"
                                        "（路线降级：按掌握度升序）",
                                        target_mastery=max(0.85, MASTERY_THRESHOLD + 0.2),
                                        rank=len(rows) + 1))
        note = f"学习路线不可用（{e}）；以下建议按掌握度升序直接匹配策略。"
        return rows, False, note, 0

    rows = []
    for i, step in enumerate(plan.steps[:WEAK_TOP_N], start=1):
        kp = graph.get(step.kp_id)
        strategy = strategies.get(step.strategy_id)
        s_name = strategy.name if strategy is not None else step.strategy_id
        rows.append(_suggestion_row(step.kp_id, kp, profile, step.strategy_id,
                                    s_name, step.rationale,
                                    step.target_mastery, rank=i))
    note = "薄弱 top10 取自学习路线前 %d 步（影响×缺口优先、先序有效；与 GET /plan 同引擎同入参）。" % WEAK_TOP_N
    return rows, True, note, len(plan.reviews)


def _suggestion_row(kp_id, kp, profile: Profile, strategy_id: str,
                    strategy_name: str, rationale: str, target_mastery: float,
                    rank: int) -> dict:
    m = profile.mastery.get(kp_id)
    n = profile.evidence.get(kp_id, 0) if m is not None else 0
    return {
        "rank": rank,
        "kp_id": kp_id,
        "name": kp.name if kp is not None else kp_id,
        "grade": kp.grade if kp is not None else None,
        "cluster": kp.cluster if kp is not None else "",
        "anchor": f"kp-{kp_id}",
        "mastery": m,
        "confidence": round(profile.confidence(kp_id), 4) if m is not None else None,
        "evidence": n,
        "strategy_id": strategy_id,
        "strategy_name": strategy_name,
        "rationale": rationale,
        "target_mastery": target_mastery,
    }


def build_subject_kmap(profile: Profile, graph, strategies, bank, today,
                       subject: str) -> dict:
    """学科知识地图数据层：图谱全量 KP 分级归章 + 画像热力 + 薄弱 top10 建议。

    空态口径（如实，不编造）：
    - 图谱为空 / 画像与学科无交集（no_overlap）；
    - 画像覆盖本学科但所有知识点零作答证据（no_evidence，空学习者）。
    """
    kps = graph.kps()
    data: dict = {
        "mode": "subject",
        "learner_id": profile.learner_id,
        "subject": subject,
        "subject_label": SUBJECT_LABELS.get(subject, subject),
        "updated_at": profile.updated_at,
        "threshold": MASTERY_THRESHOLD,
        "grades": [],
        "weak_top": [],
        "stats": {"total": 0, "covered": 0, "measured": 0, "weak": 0,
                  "avg": None},
        "plan_available": False,
        "plan_note": "",
        "reviews_n": 0,
        "empty": None,
    }
    if not kps:
        data["empty"] = {"reason": "empty_graph",
                         "detail": "该学科知识图谱为空（无知识点）。"}
        return data
    covered_ids = [kp.id for kp in kps if kp.id in profile.mastery]
    if not covered_ids:
        data["empty"] = {
            "reason": "no_overlap",
            "detail": "该学习者画像与本学科知识点无交集（未在本学科诊断过），"
                      "暂无可视化数据。",
        }
        return data
    if all(profile.evidence.get(kp_id, 0) == 0 for kp_id in covered_ids):
        data["empty"] = {
            "reason": "no_evidence",
            "detail": "该学习者画像覆盖本学科，但所有知识点均无作答证据"
                      "（空画像），掌握度仅为先验/平滑值，不足以绘图。",
        }
        return data

    data["grades"], data["stats"] = _aggregate_grades(graph, profile)
    (data["weak_top"], data["plan_available"], data["plan_note"],
     data["reviews_n"]) = _suggestions_from_plan(
        profile, graph, strategies, bank, today)
    return data


def build_overview_kmap(profile: Profile, subjects: list, graph_loader) -> dict:
    """跨学科总览数据层：逐学科汇总（图谱全量 KP / 画像覆盖 / 有证据 / 薄弱）。"""
    rows = []
    any_evidence = False
    tot = {"total": 0, "covered": 0, "measured": 0, "weak": 0}
    for subject in subjects:
        graph = graph_loader(subject)
        kps = graph.kps()
        covered = measured = weak = 0
        m_sum = 0.0
        covered_views = []
        for kp in kps:
            if kp.id in profile.mastery:
                m = profile.mastery[kp.id]
                covered += 1
                m_sum += m
                covered_views.append((m, kp.id))
                if profile.evidence.get(kp.id, 0) > 0:
                    measured += 1
                if m < MASTERY_THRESHOLD:
                    weak += 1
        if measured > 0:
            any_evidence = True
        rows.append({
            "subject": subject,
            "subject_label": SUBJECT_LABELS.get(subject, subject),
            "total": len(kps),
            "covered": covered,
            "measured": measured,
            "weak": weak,
            "avg": round(m_sum / covered, 4) if covered else None,
            "covered_views": sorted(covered_views),  # 掌握度升序，SVG 从红到绿
        })
        tot["total"] += len(kps)
        tot["covered"] += covered
        tot["measured"] += measured
        tot["weak"] += weak
    return {
        "mode": "overview",
        "learner_id": profile.learner_id,
        "subject": "",
        "subject_label": "全部学科",
        "updated_at": profile.updated_at,
        "threshold": MASTERY_THRESHOLD,
        "subjects": rows,
        "any_evidence": any_evidence,
        "stats": tot,
        "empty": None if subjects else {
            "reason": "no_subjects",
            "detail": "数据目录未发现任何学科知识图谱。",
        },
    }


# ======================== HTML 渲染 ========================

_CSS = """
:root { color-scheme: light; }
* { box-sizing: border-box; }
body { font-family: system-ui, -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif;
       margin: 0; background: #f4f5f2; color: #1c1c1c; }
.wrap { max-width: 1120px; margin: 0 auto; padding: 16px 20px 48px; }
header.page { background: #ffffff; border: 1px solid #dcdcd6; border-radius: 10px;
              padding: 14px 18px; margin-bottom: 14px; }
header.page h1 { margin: 0 0 6px; font-size: 20px; }
.meta { font-size: 13px; color: #444; line-height: 1.7; }
.meta b { color: #111; }
.stat-chips { margin-top: 8px; display: flex; flex-wrap: wrap; gap: 6px; }
.stat-chip { font-size: 12px; background: #eef1ea; border: 1px solid #d5dacd;
             border-radius: 999px; padding: 2px 10px; }
.stat-chip.warn { background: #fdecea; border-color: #f2b8b5; }
nav.crumbs { font-size: 13px; margin: 0 0 10px; }
nav.crumbs a { color: #1a5c1a; }
section.card { background: #ffffff; border: 1px solid #dcdcd6; border-radius: 10px;
               padding: 14px 18px; margin-bottom: 14px; }
section.card > h2 { font-size: 16px; margin: 0 0 10px; }
svg#heat-strip { width: 100%; height: auto; display: block; }
ol.weak { list-style: none; margin: 0; padding: 0; }
li.weak-row { border: 1px solid #e4e0da; border-left: 4px solid #c62828;
              border-radius: 6px; padding: 8px 12px; margin-bottom: 8px;
              font-size: 13px; background: #fffdfb; }
li.weak-row .wr-head { font-size: 14px; font-weight: 600; }
li.weak-row a { color: #8a1c1c; }
li.weak-row .wr-nums { color: #555; margin-left: 8px; }
li.weak-row .wr-where { color: #777; margin-left: 8px; }
li.weak-row .wr-action { display: block; margin-top: 4px; color: #333; }
li.weak-row .wr-action b { color: #1a5c1a; }
details.grade { border: 1px solid #e0ded8; border-radius: 8px; margin-bottom: 8px;
                background: #fcfcfa; }
details.grade > summary { cursor: pointer; padding: 8px 12px; font-size: 14px;
                          font-weight: 600; }
details.grade > summary .g-stats { font-weight: 400; color: #666; font-size: 12px;
                                   margin-left: 8px; }
details.cluster { margin: 4px 12px 10px; }
details.cluster > summary { cursor: pointer; font-size: 13px; color: #333;
                            padding: 4px 0; }
ul.kps { list-style: none; margin: 4px 0 8px; padding: 0; display: flex;
         flex-wrap: wrap; gap: 4px; }
li.kp { font-size: 12px; border: 1px solid rgba(0,0,0,0.14); border-radius: 4px;
        padding: 2px 6px; display: inline-flex; gap: 6px; align-items: baseline; }
li.kp .kp-m { font-variant-numeric: tabular-nums; color: #333; }
li.kp.nom { background: #dedede; color: #666; }
li.kp.weak-kp { border-color: #c62828; border-width: 1.5px; }
.subject-cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(330px, 1fr));
                 gap: 10px; }
a.subject-card { display: block; background: #fcfcfa; border: 1px solid #dcdcd6;
                 border-radius: 8px; padding: 10px 12px; text-decoration: none;
                 color: inherit; }
a.subject-card:hover { border-color: #1a5c1a; }
a.subject-card .sc-name { font-size: 14px; font-weight: 600; }
a.subject-card .sc-stats { font-size: 12px; color: #555; margin: 4px 0 6px; }
.empty-notice { background: #fff8e6; border: 1px solid #e6d9a8; border-radius: 8px;
                padding: 18px; font-size: 14px; color: #5c4a12; }
p.legend { font-size: 12px; color: #555; line-height: 1.8; margin: 6px 0 0; }
.swatch { display: inline-block; width: 14px; height: 11px; border-radius: 2px;
          border: 1px solid rgba(0,0,0,0.2); vertical-align: -1px; margin: 0 2px; }
footer.page { font-size: 12px; color: #666; margin-top: 16px; line-height: 1.8; }
""".strip()


def _page_shell(title: str, body: str, extra_head: str = "") -> str:
    return (
        "<!DOCTYPE html>\n"
        '<html lang="zh-CN">\n<head>\n<meta charset="utf-8">\n'
        f"<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        f"<title>{_esc(title)}</title>\n"
        f"<style>\n{_CSS}\n</style>\n{extra_head}</head>\n<body>\n"
        f'<div class="wrap">\n{body}\n</div>\n</body>\n</html>\n'
    )


def _header(data: dict, stats_line: str) -> str:
    return (
        '<header class="page">\n'
        f"<h1>知识地图 · {_esc(data['subject_label'])}</h1>\n"
        '<div class="meta">学习者 <b>' + _esc(data["learner_id"]) + "</b>"
        " ｜ 学科 <b>" + _esc(data["subject_label"]) + "</b>"
        " ｜ 数据更新时间 <b>" + _esc(data["updated_at"] or "（画像未记录时间）") + "</b>"
        " ｜ 薄弱阈值 掌握度 &lt; " + _esc(data["threshold"]) + "</div>\n"
        + (f'<div class="stat-chips">{stats_line}</div>\n' if stats_line else "")
        + "</header>\n"
    )


def _stat_chip(text: str, warn: bool = False) -> str:
    cls = "stat-chip warn" if warn else "stat-chip"
    return f'<span class="{cls}">{text}</span>'


def _legend() -> str:
    sw = "".join(
        f'<span class="swatch" style="background:{heat_fill(i / 4, 1.0)}"></span>'
        for i in range(5)
    )
    faint = f'<span class="swatch" style="background:{heat_fill(0.2, 0.0)}"></span>'
    return (
        '<p class="legend">图例：热力色相 ' + sw
        + "（红=薄弱 0 → 绿=熟练 1）；透明度=置信度" + faint
        + "（无作答证据→置信 0，最淡）；"
        "红色描边=薄弱（掌握度 &lt; 阈值）；"
        '灰色 <span class="swatch" style="background:#dedede"></span>'
        "=画像外（图谱有、学习者画像无，不编造数据）。</p>"
    )


def _footer(note: str = "") -> str:
    provenance = (
        "数据来源：诊断内核画像（逐 KP 掌握度/置信度/证据数）与学习路线引擎"
        "（build_plan，与 GET /learners/{id}/plan 同一实现），知识结构来自学科级"
        "知识图谱装载器。渲染为纯函数确定性输出，本页零外部库、零 JavaScript。"
    )
    return f'<footer class="page">{_esc(provenance)}{(" " + note) if note else ""}</footer>\n'


def _heat_strip_svg(data: dict) -> str:
    """年级×知识点热力条：每年级一行，段=知识点（章内 kp_id 序），
    色相=掌握度、透明度=置信度、红描边=薄弱、灰=画像外。"""
    grades = data["grades"]
    label_w, map_w, row_h, cell_h, top = 56, 820, 20, 14, 6
    height = top + len(grades) * row_h + 8
    parts = [
        f'<svg id="heat-strip" viewBox="0 0 {label_w + map_w} {height}" '
        f'width="{label_w + map_w}" height="{height}" role="img" '
        f'aria-label="年级知识点掌握度热力条">',
        f'<rect x="0" y="0" width="{label_w + map_w}" height="{height}" fill="#ffffff" />',
    ]
    y = top
    for g in grades:
        parts.append(
            f'<text x="0" y="{y + cell_h - 2}" font-size="11" fill="#555">'
            f'{_esc(g["label"])}</text>')
        kps = [v for c in g["clusters"] for v in c["kps"]]
        n = len(kps)
        cw = map_w / n if n else map_w
        x = label_w
        for v in kps:
            if v["mastery"] is None:
                fill, opacity, stroke = "#dedede", "1.0", "none"
                tip = f'{v["name"]}（画像外，无诊断数据）'
            else:
                fill = heat_fill(v["mastery"], v["confidence"])
                opacity = "1.0"
                stroke = "#c62828" if v["mastery"] < MASTERY_THRESHOLD else "none"
                tip = (f'{v["name"]}｜掌握 {v["mastery"]:.3f}｜'
                       f'置信 {v["confidence"]:.2f}｜证据 {v["evidence"]}')
            sw = ' stroke="#c62828" stroke-width="1"' if stroke != "none" else ""
            parts.append(
                f'<rect x="{x:.1f}" y="{y}" width="{cw:.2f}" height="{cell_h}" '
                f'fill="{fill}" fill-opacity="{opacity}"{sw}>'
                f"<title>{_esc(tip)}</title></rect>")
            x += cw
        y += row_h
    parts.append("</svg>")
    return "".join(parts)


def _chip_li(v: dict, weak_ids: set) -> str:
    cls = "kp"
    if v["mastery"] is None:
        cls += " nom"
        title = f'{v["name"]}｜{_esc(v["cluster"])}｜画像外（无诊断数据）'
        return (
            f'<li class="{cls}" id="{_esc(v["anchor"])}" data-kp="{_esc(v["kp_id"])}" '
            f'title="{title}"><span class="kp-name">{_esc(v["name"])}</span></li>')
    if v["mastery"] < MASTERY_THRESHOLD:
        cls += " weak-kp"
    if v["kp_id"] in weak_ids:
        cls += " in-weak-top"
    style = f' style="background:{heat_fill(v["mastery"], v["confidence"])}"'
    title = (
        f'{v["name"]}｜{_esc(v["cluster"])}｜掌握 {v["mastery"]:.6f}'
        f'｜置信 {v["confidence"]:.4f}｜证据 {v["evidence"]}'
        + ("｜无作答证据（先验/平滑值）" if v["evidence"] == 0 else ""))
    return (
        f'<li class="{cls}" id="{_esc(v["anchor"])}" data-kp="{_esc(v["kp_id"])}" '
        f'data-m="{v["mastery"]:.6f}" data-c="{v["confidence"]:.4f}" '
        f'data-ev="{v["evidence"]}" title="{title}"{style}>'
        f'<span class="kp-name">{_esc(v["name"])}</span>'
        f'<span class="kp-m">{v["mastery"]:.3f}</span></li>')


def _render_subject_body(data: dict) -> str:
    stats = data["stats"]
    stats_line = "".join([
        _stat_chip(f"图谱知识点 {stats['total']}"),
        _stat_chip(f"画像覆盖 {stats['covered']}"),
        _stat_chip(f"有作答证据 {stats['measured']}"),
        _stat_chip(f"薄弱（m&lt;{data['threshold']}） {stats['weak']}",
                   warn=stats["weak"] > 0),
    ] + ([] if stats["avg"] is None else
         [_stat_chip(f"覆盖点平均掌握 {stats['avg']:.4f}")]))

    body = [_header(data, stats_line),
            '<nav class="crumbs"><a href="knowledge-map.html">← 返回跨学科总览</a></nav>\n']

    if data["empty"]:
        body.append(
            '<section class="card"><div class="empty-notice">暂无数据：'
            f'{_esc(data["empty"]["detail"])}'
            "（本页如实呈现空态，不以先验值伪造地图。）</div></section>")
        body.append(_footer())
        return "".join(body)

    # 薄弱 top10（建议动作来自 /plan 同源路线）
    body.append('<section class="card" id="weak-top"><h2>薄弱知识点 top10 与建议动作</h2>\n'
                '<ol class="weak">\n')
    for w in data["weak_top"]:
        body.append(
            f'<li class="weak-row" data-rank="{w["rank"]}" data-kp="{_esc(w["kp_id"])}" '
            f'data-m="{w["mastery"]:.6f}">'
            f'<span class="wr-head">#{w["rank"]} '
            f'<a href="#{_esc(w["anchor"])}">{_esc(w["name"])}</a></span>'
            f'<span class="wr-nums">掌握 {w["mastery"]:.3f} ｜ 置信 {w["confidence"]:.2f}'
            f' ｜ 证据 {w["evidence"]}</span>'
            f'<span class="wr-where">{_esc(_grade_label(w["grade"]) if w["grade"] else "")}'
            f' · {_esc(w["cluster"])}</span>'
            f'<span class="wr-action">建议：<b>{_esc(w["strategy_name"])}</b>'
            f' —— {_esc(w["rationale"])}（目标掌握 {_esc(round(w["target_mastery"], 2))}）</span>'
            "</li>\n")
    body.append("</ol>\n"
                f'<p class="legend">{_esc(data["plan_note"])}'
                + (f" 达标知识点 {data['reviews_n']} 项已进入间隔复习日程。"
                   if data["reviews_n"] else "")
                + "</p>\n</section>\n")

    body.append('<section class="card"><h2>年级热力总览</h2>\n'
                + _heat_strip_svg(data) + _legend() + "</section>\n")

    # 年级→章→KP 两级折叠
    body.append('<section class="card" id="grade-map"><h2>年级 → 章 → 知识点</h2>\n')
    for g in data["grades"]:
        open_attr = " open" if g["open"] else ""
        g_stats = (f'{g["n"]} KP · 画像覆盖 {g["covered"]} · 有证据 {g["measured"]}'
                   f' · 薄弱 {g["weak"]}'
                   + (f' · 平均 {g["avg"]:.3f}' if g["avg"] is not None else ""))
        body.append(f'<details class="grade"{open_attr}><summary>'
                    f'{_esc(g["label"])}<span class="g-stats">{_esc(g_stats)}</span>'
                    "</summary>\n")
        weak_ids = {w["kp_id"] for w in data["weak_top"]}
        for c in g["clusters"]:
            body.append(f'<details class="cluster"><summary>{_esc(c["cluster"])}'
                        f'（{len(c["kps"])} KP）</summary>\n<ul class="kps">\n')
            for v in c["kps"]:
                body.append(_chip_li(v, weak_ids) + "\n")
            body.append("</ul>\n</details>\n")
        body.append("</details>\n")
    body.append("</section>\n")
    body.append(_footer())
    return "".join(body)


def _subject_bar_svg(row: dict) -> str:
    """总览页单学科热力条：画像覆盖点按掌握度升序从红到绿，其余灰色。"""
    bar_w, bar_h = 560, 14
    total = row["total"]
    covered = row["covered"]
    parts = [
        f'<svg viewBox="0 0 {bar_w} {bar_h}" width="{bar_w}" height="{bar_h}" '
        f'role="img" aria-label="{_esc(row["subject_label"])}掌握度分布条">',
        f'<rect x="0" y="0" width="{bar_w}" height="{bar_h}" fill="#dedede" rx="3" />',
    ]
    if total > 0 and covered > 0:
        cw = bar_w / total
        x = 0.0
        for m, _kp_id in row["covered_views"]:
            conf = 1.0  # 总览条不编码置信度（逐点置信在学科页）
            parts.append(
                f'<rect x="{x:.1f}" y="0" width="{cw:.2f}" height="{bar_h}" '
                f'fill="{heat_fill(m, conf)}" />')
            x += cw
    parts.append("</svg>")
    return "".join(parts)


def _render_overview_body(data: dict) -> str:
    stats = data["stats"]
    stats_line = "".join([
        _stat_chip(f"学科 {len(data['subjects'])}"),
        _stat_chip(f"图谱知识点 {stats['total']}"),
        _stat_chip(f"画像覆盖 {stats['covered']}"),
        _stat_chip(f"有作答证据 {stats['measured']}"),
        _stat_chip(f"薄弱（m&lt;{data['threshold']}） {stats['weak']}",
                   warn=stats["weak"] > 0),
    ])
    body = [_header(data, stats_line)]

    if data["empty"]:
        body.append(
            '<section class="card"><div class="empty-notice">暂无数据：'
            f'{_esc(data["empty"]["detail"])}</div></section>')
        body.append(_footer())
        return "".join(body)

    if not data["any_evidence"]:
        body.append(
            '<section class="card"><div class="empty-notice">该学习者暂无任何学科'
            "的作答证据（空学习者）：以下汇总中“有作答证据”均为 0，掌握度若显示"
            "也只是先验/平滑值，不构成诊断结论。</div></section>")

    body.append('<section class="card" id="subjects"><h2>分学科汇总'
                '（点击进入学科地图）</h2>\n<div class="subject-cards">\n')
    for row in data["subjects"]:
        if row["covered"] == 0:
            stats_txt = (f'图谱 {row["total"]} KP · 无画像数据'
                         "（该学科暂无诊断数据）")
        else:
            stats_txt = (f'图谱 {row["total"]} KP · 画像覆盖 {row["covered"]}'
                         f' · 有证据 {row["measured"]} · 薄弱 {row["weak"]}'
                         + (f' · 平均 {row["avg"]:.3f}' if row["avg"] is not None else ""))
        body.append(
            f'<a class="subject-card" href="knowledge-map.html?subject={_esc(row["subject"])}">'
            f'<div class="sc-name">{_esc(row["subject_label"])}'
            f'（{_esc(row["subject"])}）</div>'
            f'<div class="sc-stats">{_esc(stats_txt)}</div>'
            + _subject_bar_svg(row) + "</a>\n")
    body.append("</div>\n")
    body.append(_legend())
    body.append("</section>\n")
    body.append(_footer())
    return "".join(body)


def render_kmap_html(data: dict) -> str:
    """知识地图数据 -> 自包含 HTML（内联 CSS/SVG，零外部库，零 JS）。"""
    mode = data.get("mode")
    if mode == "subject":
        body = _render_subject_body(data)
    elif mode == "overview":
        body = _render_overview_body(data)
    else:
        raise ValueError(f"unknown kmap mode: {mode!r}")
    return _page_shell(
        f"知识地图 · {data['subject_label']} · {data['learner_id']}", body)
