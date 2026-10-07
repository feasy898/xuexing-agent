"""静态卷包内核（签署测试卡 TC-4，2026-10-08；裁定 D-1/D-5/D-6）。

把「按卷型出卷」（paper_by_spec）+「成品卷渲染」（paper_render）+
「OMR 答题卡」（omr_sheet）+「冷启动画像」（cold_start_profile）装订成
可离线分发的静态卷包：学生卷（html/txt）、教师卷（答案/解析/评分要点）、
题号→KP 对照与纸面自诊知识地图、答题卡、manifest（含逐文件 sha256 与
可发布判定）。全程零网络、零数据回传、无时钟（同 spec+seed 逐字节一致）。

卷面固定文案（owner 裁定 D-6/T1-4）：
- 学生卷与教师卷卷头必须含「本卷题目由 AI 辅助生成并经校验」与
  「题目为原创（含 AI 辅助生成并经校验），对齐课标与教材，非真题」；
- 只要含单代理验证题，两卷卷头加「内部样卷·未完成双代理复验」且
  releasable=false（对外可分发卷只能用双代理 agree 题）。

难度配比校验（D-5 T5-3）：成卷实际 basic/medium/hard 占比与画像目标
（= 阶段内各年级条目 difficulty_mix 的算术平均；v0 各条目同为海南 7:2:1）
偏差每档 ≤ MAX_BAND_DEVIATION，超阈值 releasable=false 并在 manifest 写明。

本模块只读输入、不碰数据文件；数据装载在 tools/export_static_paper.py。
"""
import hashlib
import json
from collections import OrderedDict

from xuexing.itembank import ItemBank
from xuexing.cold_start_profile import (  # noqa: F401  (复用画像口径)
    DIFFICULTY_BANDS,
    PROFILE_VERSION,
    to_canonical_json,
)
from xuexing.omr_sheet import OMRError, build_answer_sheet
from xuexing.paper_by_spec import PaperBySpecError  # noqa: F401  (re-export 语义)
from xuexing.paper_render import human_paper_title, redline_report, render_paper_html, render_paper_text

AI_LABEL = "本卷题目由 AI 辅助生成并经校验"
ORIGINAL_NOTICE = "题目为原创（含 AI 辅助生成并经校验），对齐课标与教材，非真题"
SINGLE_AGENT_LABEL = "内部样卷·未完成双代理复验"

# 难度偏差冻结阈值（specs/drafts/static_paper.spec.md §4；改值=改规格+留痕）
MAX_BAND_DEVIATION = 0.15

CONTENT_FILES = ("student.html", "student.txt", "teacher.html", "kp_map.html", "answer_sheet.json")
HTML_FILES = ("student.html", "teacher.html", "kp_map.html")

_EXTERNAL_REF_RE = None  # 延迟编译（见 _external_refs）


class StaticPaperError(ValueError):
    """静态卷包构建/校验失败（卷面非法、题引用缺失、画像是 absent 等）。"""


def is_dual_verified(record) -> bool:
    """原始题目 dict -> 双代理 agree 判定：verification.agents≥2 且 answers_agree is True。"""
    v = (record or {}).get("verification") or {}
    agents = v.get("agents")
    return isinstance(agents, (list, tuple)) and len(agents) >= 2 and v.get("answers_agree") is True


def verified_only_bank(bank, item_records):
    """题库 -> 仅含双代理 agree 题的新题库（--verified-only 选题池）。

    不降级凑题的根基：过滤后题不足由 paper_by_spec 的 fail-closed 选题
    原样报缺（PaperBySpecError），绝不回退到单代理题。
    """
    pool = ItemBank()
    for item in bank.items():
        if is_dual_verified(item_records.get(item.id)):
            pool.add(item)
    return pool


def verified_shortages(sections, bank, item_records):
    """逐大题核对「双代理 agree 题存量」-> 缺口列表（only need > have_verified）。

    sections 为卷型 sections（含 form/count/title）；have_verified 由
    eligible_items(bank, form) 逐题对照原始记录独立重算。空列表 = 全部
    大题的双代理题量都够（该卷型可 --verified-only 出卷）。
    """
    shortages = []
    for section in sections:
        form = section.get("form") if isinstance(section, dict) else section.form
        need = section.get("count") if isinstance(section, dict) else section.count
        title = section.get("title") if isinstance(section, dict) else section.title
        from xuexing.paper_by_spec import eligible_items
        have = sum(
            1 for item in eligible_items(bank, form)
            if is_dual_verified(item_records.get(item.id))
        )
        if need > have:
            shortages.append({
                "section": title,
                "form": form,
                "need": need,
                "have_verified": have,
            })
    return shortages


def band_of(difficulty) -> str:
    """难度系数（越大越容易）-> 档位；区间定义复用 cold_start_profile。

    语义：basic 闭区间 [0.75,1.0]；medium/hard 左闭右开。落在定义外报错。
    """
    d = float(difficulty)
    if 0.75 <= d <= 1.0:
        return "basic"
    if 0.4 <= d < 0.75:
        return "medium"
    if 0.0 <= d < 0.4:
        return "hard"
    raise StaticPaperError(f"difficulty {difficulty!r} 落在难度带定义之外")


def target_mix_for_grades(profile, subject, grades):
    """阶段目标配比 = 阶段内「有画像条目」各年级 difficulty_mix 的算术平均。

    题库文件可能覆盖知识库未建档的年级（如 0 题空壳文件），此类年级无
    画像条目、跳过不计；一个条目都没有才报错（fail-closed）。
    """
    entries = profile.get("entries") or {}
    mixes = []
    missing = []
    for g in grades:
        entry = entries.get(f"{subject}_grade{g}")
        if entry is None:
            missing.append(f"{subject}_grade{g}")
            continue
        mixes.append(entry["difficulty_mix"])
    if not mixes:
        raise StaticPaperError(
            f"profile has no entries for {subject} grades {grades} (missing: {missing})"
        )
    return {
        band: sum(m[band] for m in mixes) / len(mixes) for band in sorted(mixes[0])
    }


def band_shares(items_by_band):
    """各档题数 -> 占比 dict（和为 1；空卷报错）。"""
    total = sum(items_by_band.values())
    if total <= 0:
        raise StaticPaperError("empty paper: no items for band shares")
    return {band: n / total for band, n in sorted(items_by_band.items())}


def _external_refs(html_text):
    """卷包 HTML 的外链/脚本/表单/iframe 引用（命中即违规，零回传红线）。"""
    global _EXTERNAL_REF_RE
    import re
    if _EXTERNAL_REF_RE is None:
        _EXTERNAL_REF_RE = re.compile(
            r"https?://|<script[^>]*src=|<link[^>]*href=|<iframe|<form", re.I
        )
    return _EXTERNAL_REF_RE.findall(html_text)


def _sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _esc(text):
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


class _OmrPaper:
    """omr_sheet.build_answer_sheet 的鸭子适配：sections=/{item_ids}/，题号 1..N 连续。"""

    def __init__(self, paper_id, title, section_item_ids):
        self.paper_id = paper_id
        self.title = title
        self.sections = [{"item_ids": list(ids)} for ids in section_item_ids]


def _notice_block(labels):
    """卷头固定文案块（AI 标识 + 原创声明 + 可选内部样卷标签）。"""
    parts = []
    for label in labels:
        parts.append('<div class="notice-bar">{}</div>\n'.format(_esc(label)))
    return "".join(parts)


def _inject_notice(html_doc, labels):
    anchor = "<body>\n"
    if anchor not in html_doc:
        raise StaticPaperError("render_paper_html 输出缺少 <body> 锚点，无法注入卷头文案")
    return html_doc.replace(anchor, anchor + _notice_block(labels), 1)


def _render_teacher_html(paper, bank, item_records, labels):
    """教师卷：答案/解析/评分要点（仅教师面，不入学生卷）。"""
    title = human_paper_title(paper)
    parts = [
        "<!DOCTYPE html>\n<html lang=\"zh-CN\">\n<head>\n<meta charset=\"utf-8\">\n",
        f"<title>{_esc(title)} · 教师卷</title>\n",
        "<style>body{font-family:sans-serif;margin:24px auto;max-width:820px}"
        ".q{border-bottom:1px solid #ccc;padding:8px 0}"
        ".ans{color:#0645ad}.pts{color:#666}</style>\n</head>\n<body>\n",
        f"<h1>{_esc(title)} · 教师卷</h1>\n",
    ]
    for label in labels:
        parts.append(f"<p>{_esc(label)}</p>\n")
    for sec in paper["sections"]:
        parts.append(f"<h2>{_esc(sec['title'])}</h2>\n")
        for q in sec["questions"]:
            item = bank.get(q["item_id"])
            if item is None:
                raise StaticPaperError(f"卷面引用了题库中不存在的题: {q['item_id']}")
            record = item_records.get(q["item_id"]) or {}
            parts.append('<div class="q">')
            parts.append(
                f"<p><b>第 {_esc(q['question_no'])} 题</b> "
                f"<span class='pts'>({q['points']} 分)</span></p>\n"
            )
            parts.append(f"<p>{_esc(item.stem)}</p>\n")
            for opt in item.options:
                parts.append(f"<p>{_esc(opt)}</p>\n")
            parts.append(f"<p class='ans'>【答案】{_esc(item.answer)}</p>\n")
            solution = str(item.solution or "").strip()
            if solution:
                parts.append(f"<p>【解析】{_esc(solution)}</p>\n")
            sp = record.get("scoring_points")
            if isinstance(sp, list) and sp:
                points_text = "；".join(
                    _esc(p.get("point", "")) + f"（{p.get('score', '')}分）"
                    for p in sp if isinstance(p, dict)
                )
                parts.append(f"<p>【评分要点】{points_text}</p>\n")
            rubric = record.get("rubric")
            if isinstance(rubric, dict) and rubric.get("total") is not None:
                parts.append(
                    f"<p>【评分标准】总分 {_esc(rubric.get('total'))} 分"
                    f"（分维度量表见题库 rubric 字段）</p>\n"
                )
            parts.append("</div>\n")
    parts.append("</body>\n</html>\n")
    return "".join(parts)


def _render_kp_map_html(paper, bank, kp_index):
    """题号→KP 对照 + 纸面自诊知识地图模板（作答者自己勾错题，零回传）。"""
    title = human_paper_title(paper)
    rows = []
    cluster_map = OrderedDict()
    for sec in paper["sections"]:
        for q in sec["questions"]:
            item = bank.get(q["item_id"])
            if item is None:
                raise StaticPaperError(f"卷面引用了题库中不存在的题: {q['item_id']}")
            kp_ids = list(item.kps)
            names = []
            for kp_id in kp_ids:
                info = kp_index.get(kp_id) or {}
                names.append(f"{info.get('name', kp_id)}({kp_id})")
                cluster = str(info.get("cluster", "") or "未分章")
                cluster_map.setdefault(cluster, OrderedDict())
                cluster_map[cluster].setdefault(kp_id, {"name": info.get("name", kp_id), "nos": []})
                cluster_map[cluster][kp_id]["nos"].append(q["question_no"])
            rows.append((q["question_no"], q["points"], "；".join(names) or "（题库未标注 KP）"))
    parts = [
        "<!DOCTYPE html>\n<html lang=\"zh-CN\">\n<head>\n<meta charset=\"utf-8\">\n",
        f"<title>{_esc(title)} · 题号-KP 对照与纸面自诊知识地图</title>\n",
        "<style>body{font-family:sans-serif;margin:24px auto;max-width:820px}"
        "table{border-collapse:collapse}td,th{border:1px solid #999;padding:4px 8px}"
        ".hint{color:#666}</style>\n</head>\n<body>\n",
        f"<h1>{_esc(title)} · 题号-KP 对照</h1>\n",
        "<p class=\"hint\">对照下表找到做错题目的知识点，在「纸面自诊知识地图」"
        "中勾出薄弱知识点即可，本表与答题全程不联网、不回传任何数据。</p>\n",
        "<table><tr><th>题号</th><th>分值</th><th>知识点</th></tr>\n",
    ]
    for no, points, names in rows:
        parts.append(f"<tr><td>{no}</td><td>{points}</td><td>{_esc(names)}</td></tr>\n")
    parts.append("</table>\n<h2>纸面自诊知识地图</h2>\n")
    parts.append("<p class=\"hint\">作答者自用：做错该知识点题目，就把 ☐ 涂成 ☑。打印后手写完成，无需回传。</p>\n")
    for cluster in sorted(cluster_map):
        parts.append(f"<h3>{_esc(cluster)}</h3>\n")
        for kp_id in sorted(cluster_map[cluster]):
            info = cluster_map[cluster][kp_id]
            nos = "、".join(str(n) for n in info["nos"])
            parts.append(
                f"<p>☐ {_esc(info['name'])}（{_esc(kp_id)}）— 相关题号：{nos}</p>\n"
            )
    parts.append("</body>\n</html>\n")
    return "".join(parts)


def build_bundle(paper, bank, item_records, kp_index, profile):
    """卷面骨架+题库+原始题目记录+KP 索引+画像 -> 六文件卷包 dict。

    返回 {"student.html"/"student.txt"/"teacher.html"/"kp_map.html"/
    "answer_sheet.json"/"manifest.json": 文件内容 str, "manifest": manifest dict}。
    同一输入逐字节一致（无时钟、无随机；paper 里的 seed/spec_id 已定）。
    """
    paper_id = paper.get("paper_id")
    if not isinstance(paper_id, str) or not paper_id:
        raise StaticPaperError("paper.paper_id 必须是非空 str")
    flat = [q for sec in paper["sections"] for q in sec["questions"]]
    numbers = [q["question_no"] for q in flat]
    if numbers != list(range(1, len(flat) + 1)):
        raise StaticPaperError(f"卷面题号必须 1..N 连续，实得 {numbers[:5]}...")

    records = []
    item_records = item_records or {}
    for q in flat:
        item = bank.get(q["item_id"])
        if item is None:
            raise StaticPaperError(f"卷面引用了题库中不存在的题: {q['item_id']}")
        record = item_records.get(q["item_id"])
        if record is None:
            raise StaticPaperError(f"缺少题目原始记录（verification 判定需要）: {q['item_id']}")
        records.append((q, item, record))

    has_single = any(not is_dual_verified(rec) for _, _, rec in records)
    labels = [AI_LABEL, ORIGINAL_NOTICE]
    if has_single:
        labels.append(SINGLE_AGENT_LABEL)

    student_html = _inject_notice(render_paper_html(paper, bank), labels)
    notice_head = "".join(f"{label}\n" for label in labels)
    student_text = notice_head + "\n" + render_paper_text(paper, bank)
    teacher_html = _render_teacher_html(paper, bank, item_records, labels)
    kp_map_html = _render_kp_map_html(paper, bank, kp_index)

    omr_paper = _OmrPaper(
        paper_id,
        human_paper_title(paper),
        [[q["item_id"] for q in sec["questions"]] for sec in paper["sections"]],
    )
    try:
        answer_sheet = build_answer_sheet(omr_paper, bank)
    except OMRError as e:
        raise StaticPaperError(f"answer_sheet 构建失败: {e}") from e
    answer_sheet_text = to_canonical_json(answer_sheet)

    contents = OrderedDict(
        (
            ("student.html", student_html),
            ("student.txt", student_text),
            ("teacher.html", teacher_html),
            ("kp_map.html", kp_map_html),
            ("answer_sheet.json", answer_sheet_text),
        )
    )
    files_sha = {name: _sha256(text) for name, text in contents.items()}

    subject = paper["subject"]
    # 阶段年级来自卷型载入方（paper 骨架无年级字段；tools 装载学段题库时已知，
    # 经 paper["stage_grades"] 传入）：画像目标配比 = 阶段内各年级条目均值。
    stage_grades = paper.get("stage_grades")
    if not isinstance(stage_grades, (list, tuple)) or not stage_grades:
        raise StaticPaperError(
            "paper.stage_grades 缺失：build_bundle 需要学段年级列表以取画像目标配比"
        )
    target = target_mix_for_grades(profile, subject, stage_grades)
    actual_counts = {band: 0 for band in sorted(DIFFICULTY_BANDS)}
    for _, item, _rec in records:
        actual_counts[band_of(item.difficulty)] += 1
    actual = band_shares(actual_counts)
    deviation = {band: actual[band] - target[band] for band in sorted(actual)}
    max_dev = max(abs(v) for v in deviation.values())
    within = max_dev <= MAX_BAND_DEVIATION + 1e-9

    releasable = (not has_single) and within
    reasons = []
    if has_single:
        reasons.append("含单代理验证题（未完成双代理复验）")
    if not within:
        reasons.append(f"难度配比偏差超阈值：max|Δ|={max_dev:.3f} > {MAX_BAND_DEVIATION}")
    manifest = {
        "spec_id": paper["spec_id"],
        "seed": paper["seed"],
        "difficulty_target": paper.get("difficulty_target"),
        "profile_version": profile.get("profile_version", PROFILE_VERSION),
        "paper_id": paper_id,
        "items": [
            {
                "no": q["question_no"],
                "id": item.id,
                "kps": list(item.kps),
                "points": q["points"],
                "verification": "dual" if is_dual_verified(rec) else "single",
            }
            for q, item, rec in records
        ],
        "files": files_sha,
        "labels": labels,
        "difficulty": {
            "target_mix": target,
            "actual_mix": actual,
            "deviation": deviation,
            "max_deviation": round(max_dev, 6),
            "threshold": MAX_BAND_DEVIATION,
            "within_threshold": within,
        },
        "releasable": releasable,
        "releasable_reason": "可对外分发" if releasable else "；".join(reasons),
    }
    bundle = OrderedDict(contents)
    bundle["manifest.json"] = to_canonical_json(manifest)
    bundle["manifest"] = manifest
    return bundle


def verify_bundle(bundle, paper, bank, profile):
    """卷包自检 -> 违规列表（空 = 通过）。逐项锁定测试卡 a..i 九点。"""
    errors = []
    manifest = bundle["manifest"]

    # a) 学生卷红线：不泄答案/解析/评分要点
    violations = redline_report(paper, bank, bundle["student.html"], bundle["student.txt"])
    errors.extend(f"student redline: {v}" for v in violations)

    # b) 分值合计
    total = sum(q["points"] for sec in paper["sections"] for q in sec["questions"])
    if total != paper["total_points"]:
        errors.append(f"Σ题分 {total} != 卷型总分 {paper['total_points']}")

    # c) 题号一致（学生卷/教师卷/kp_map/答题卡/manifest 五处）
    numbers = [it["no"] for it in manifest["items"]]
    if numbers != list(range(1, len(numbers) + 1)):
        errors.append("manifest 题号不连续")
    for name in ("student.html", "teacher.html", "kp_map.html"):
        for n in numbers:
            if name == "student.html":
                needle = f'id="q{n}"'
            else:
                needle = f"第 {n} 题" if name == "teacher.html" else f"<td>{n}</td>"
            if needle not in bundle[name]:
                errors.append(f"{name} 缺少题号 {n}（needle={needle!r}）")
    sheet_numbers = [q["number"] for q in json.loads(bundle["answer_sheet.json"])["questions"]]
    if sheet_numbers != numbers:
        errors.append("answer_sheet 题号与 manifest 不一致")

    # d) kp_map 中每题 KP == 该题 kps（整表按行解析，避免分值列数字误匹配）
    import re as _re
    rows = {}
    for m_row in _re.finditer(
        r"<tr><td>(\d+)</td><td>[\d.]+</td><td>(.*?)</td></tr>", bundle["kp_map.html"], _re.S
    ):
        rows[int(m_row.group(1))] = m_row.group(2)
    for it in manifest["items"]:
        row = rows.get(it["no"])
        if row is None:
            errors.append(f"kp_map 缺少题 {it['no']} 的对照行")
            continue
        for kp_id in it["kps"]:
            if kp_id not in row:
                errors.append(f"kp_map 题 {it['no']} 缺少 KP {kp_id}")

    # e) 零外链/脚本/表单/iframe
    for name in HTML_FILES:
        refs = _external_refs(bundle[name])
        if refs:
            errors.append(f"{name} 出现外链/脚本/表单/iframe 引用 x{len(refs)}")

    # f) 固定文案逐字出现；「真题」只出现在固定文案里
    for name in ("student.html", "teacher.html"):
        text = bundle[name]
        if AI_LABEL not in text:
            errors.append(f"{name} 缺少 AI 标识文案")
        if ORIGINAL_NOTICE not in text:
            errors.append(f"{name} 缺少原创声明文案")
        allowed = text.count(ORIGINAL_NOTICE)
        if text.count("真题") != allowed:
            errors.append(f"{name} 「真题」出现在固定文案之外 x{text.count('真题') - allowed}")

    # g) 单代理标签与 releasable 联动
    has_single = any(it["verification"] == "single" for it in manifest["items"])
    if has_single:
        if SINGLE_AGENT_LABEL not in bundle["student.html"] or SINGLE_AGENT_LABEL not in bundle["teacher.html"]:
            errors.append("含单代理题但缺「内部样卷」标签")
        if manifest["releasable"] is not False:
            errors.append("含单代理题却 releasable=true")
    else:
        if SINGLE_AGENT_LABEL in bundle["student.html"] or SINGLE_AGENT_LABEL in bundle["teacher.html"]:
            errors.append("全双代理卷不该有「内部样卷」标签")

    # h) manifest.files 与实际内容哈希一致（确定性由测试另行两次构建锁定）
    for name, sha in manifest["files"].items():
        if _sha256(bundle[name]) != sha:
            errors.append(f"manifest.files[{name}] 哈希不符")

    # i) 画像版本
    if manifest["profile_version"] != profile.get("profile_version"):
        errors.append("manifest.profile_version 与画像不一致")
    return errors
