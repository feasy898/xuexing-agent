"""知识地图渲染门——可视化层验收（无参运行，exit 0 = 门通过）。

为什么需要本工具：GET /learners/{learners}/knowledge-map.html 的交付物是给人看
的自包含 HTML（owner 原话「根据错误就可以绘制知识地图」的"绘制"字面交付），
需要与 tools/check_paper_render.py 同款的离线门：真实构造学习者作答后，对
多个学科真实渲染并逐项机器校验。

构造方式（"构造作答后"路径）：以 math/chinese/english 三学科全年级知识图谱
合并建图、对应年级题库合并成库，注入 create_app 后 POST 确定性作答（对半
正确/错误），得到覆盖三学科的学习者画像——三个学科地图都有真实数据可绘。

逐学科地图判定（math / chinese / english 各一遍）：
- OK —— 以下断言全过：
  (1) HTTP 200 且 content-type text/html，DOCTYPE/charset 在位；
  (2) 自包含：无 http(s) 外链 / <script / <link / src= / css url()；
  (3) 标签配平（paper_render.check_html_tag_balance 零错误）；
  (4) KP 数出现=profile 数：画像在本学科的每个知识点恰出现一次，
      data-m 值与 GET /learners/{id}/profile 逐字一致；图谱全量 KP
      均有芯片（画像外灰显，不编造数据）；
  (5) 薄弱 top10 与数据一致：与 build_plan（GET /plan 同引擎同入参）
      前 10 步逐位相同，每行 data-m 与画像一致且 < 0.65，建议动作在位；
  (6) 体积：chinese（677 KP 全量渲染）< 2MB。
总览页判定：200 / 配平 / 自包含 / 三学科入口与页头字段在位。
空态判定：未知学习者 404；仅 math 作答的学习者查 chinese（覆盖但零证据）
与查 physics（画像无交集）均得诚实空态页而非编造地图。

门通过条件（exit 0）：全部判定完毕、UNEXPECTED==0、三学科地图均 OK。
纯校验不落盘；人工视检样本用 tools/render_kmap_sample.py 生成到 out/。

用法：python tools/check_kmap.py [--learner kmap-check] [--data-dir data]
"""
import argparse
import json
import os
import re
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

try:  # Windows 控制台中文输出保护
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

from fastapi.testclient import TestClient  # noqa: E402

from xuexing import (  # noqa: E402
    ItemBank,
    load_itembank,
    load_kpgraph_subject,
    load_strategies,
)
from xuexing.kpgraph import kpgraph_from_dict
from xuexing.kpgraph_subject import discover_subjects
from xuexing.paper_render import check_html_tag_balance
from xuexing.route import build_plan
from xuexing.server import create_app
from xuexing.types import Profile

MASTERY_THRESHOLD = 0.65
WEAK_TOP_N = 10
SIZE_LIMIT_BYTES = 2 * 1024 * 1024

EXTERNAL_REF_RE = re.compile(
    r"https?://|<script|<link\b|\bsrc=|url\(", re.IGNORECASE)
CHIP_RE = re.compile(
    r'<li class="kp[^"]*" id="kp-([A-Za-z0-9_]+)" data-kp="\1"'
    r'(?: data-m="([0-9.]+)" data-c="([0-9.]+)" data-ev="(\d+)")?')
WEAK_ROW_RE = re.compile(
    r'<li class="weak-row" data-rank="(\d+)" data-kp="([A-Za-z0-9_]+)" '
    r'data-m="([0-9.]+)"')

CHECK_SUBJECTS = ["math", "chinese", "english"]
# 作答混合的年级题库（确定性选题来源；覆盖小学/初中两端）
FIXTURE_ITEM_GRADES = {"math": [7], "chinese": [1], "english": [1]}


def _merged_subject_graph(data_dir, subject):
    return load_kpgraph_subject(os.path.join(data_dir, "knowledge"), subject)


def _merged_bank(data_dir, subject, grades):
    bank = ItemBank()
    for g in grades:
        path = os.path.join(
            data_dir, "items", f"{subject}_grade{g}_items.json")
        for item in load_itembank(path).items():
            bank.add(item)
    return bank


def _build_fixture_app(data_dir):
    """三学科合并图谱 + 对应年级题库 -> (app, 合并 bank, 合并 graph)。"""
    graph_kps, bank = [], ItemBank()
    subject_graphs = {}
    for subject in CHECK_SUBJECTS:
        sg = _merged_subject_graph(data_dir, subject)
        subject_graphs[subject] = sg
        graph_kps.extend(
            {"id": kp.id, "name": kp.name, "subject": kp.subject,
             "grade": kp.grade, "cluster": kp.cluster,
             "description": kp.description, "standard_ref": kp.standard_ref,
             "prereqs": list(kp.prereqs)}
            for kp in sg.kps())
        for item in _merged_bank(
                data_dir, subject, FIXTURE_ITEM_GRADES[subject]).items():
            bank.add(item)
    app_graph = kpgraph_from_dict({"knowledge_points": graph_kps})
    strategies = load_strategies(
        os.path.join(data_dir, "pedagogy", "strategies.json"))
    app = create_app(bank, app_graph, strategies,
                     kmap_knowledge_dir=os.path.join(data_dir, "knowledge"))
    return app, bank, app_graph, subject_graphs, strategies


def _post_responses(client, bank, n_per_subject=8):
    """确定性作答：每学科按题库顺序取前 n_per_subject 题、对半答对/答错。"""
    picked = {"math": [], "chinese": [], "english": []}
    for item in bank.items():
        for subject, prefix in _SUBJECT_ITEM_PREFIX.items():
            if item.id.startswith(prefix) and len(picked[subject]) < n_per_subject:
                picked[subject].append(item)
    responses = []
    for subject in sorted(picked):
        for i, item in enumerate(picked[subject]):
            responses.append({"item_id": item.id, "correct": i % 2 == 0})
    r = client.post(f"/learners/{_LEARNER}/responses",
                    json={"responses": responses})
    if r.status_code != 200:
        raise RuntimeError(f"构造作答失败: {r.status_code} {r.text[:200]}")
    return sum(len(v) for v in picked.values())


_SUBJECT_ITEM_PREFIX = {"math": "m7_", "chinese": "chi_", "english": "eng_"}
_LEARNER = "kmap-check"


class Gate:
    def __init__(self):
        self.failures = []
        self.unexpected = []

    def check(self, label, ok, detail=""):
        print(f"  [{'OK' if ok else 'FAIL'}] {label}" + (f" —— {detail}" if detail else ""))
        if not ok:
            self.failures.append(f"{label}: {detail}")
        return ok

    def guard(self, label, fn):
        try:
            return fn()
        except Exception as e:  # 断言外异常一律 UNEXPECTED，判门失败
            self.unexpected.append(f"{label}: {type(e).__name__}: {e}")
            print(f"  [UNEXPECTED] {label} —— {type(e).__name__}: {e}")
            return None


def _check_self_containment(gate, label, doc):
    gate.check(f"{label}: DOCTYPE/charset 在位",
               doc.startswith("<!DOCTYPE html>") and 'charset="utf-8"' in doc)
    m = EXTERNAL_REF_RE.search(doc)
    gate.check(f"{label}: 无外部资源引用", m is None,
               "" if m is None else f"命中 {m.group(0)!r} @ {m.start()}")
    errs = check_html_tag_balance(doc)
    gate.check(f"{label}: 标签配平", not errs, "; ".join(map(str, errs[:3])))


def _check_subject_map(gate, client, profile, subject, subject_graph, strategies,
                       size_limit=None):
    label = f"{subject} 地图"
    r = client.get(f"/learners/{_LEARNER}/knowledge-map.html",
                   params={"subject": subject})
    if not gate.check(f"{label}: HTTP 200 text/html",
                      r.status_code == 200
                      and r.headers["content-type"].startswith("text/html"),
                      f"status={r.status_code}"):
        return None
    doc = r.text
    _check_self_containment(gate, label, doc)

    in_subject = {kp: f"{v:.6f}" for kp, v in profile["mastery"].items()
                  if subject_graph.has(kp)}
    chips = gate.guard(f"{label}: 芯片解析",
                       lambda: [(m.group(1), m.group(2)) for m in CHIP_RE.finditer(doc)])
    if chips is None:
        return None
    all_ids = [c[0] for c in chips]
    gate.check(f"{label}: 图谱全量 KP 均有芯片（画像外灰显）",
               len(all_ids) == len(subject_graph.kps()) and len(set(all_ids)) == len(all_ids),
               f"chips={len(all_ids)} graph={len(subject_graph.kps())}")
    got = {kp: m for kp, m in chips if m is not None}
    gate.check("  KP 数出现=profile 数（每画像点恰一次、值逐字一致）",
               got == in_subject,
               f"有值芯片={len(got)} 画像点={len(in_subject)}"
               + ("" if got == in_subject else
                  f"；首处差异={next((k for k in set(got) | set(in_subject)
                                    if got.get(k) != in_subject.get(k)), '?')}"))

    # 薄弱 top10 与数据一致（/plan 同引擎同入参重算）
    p_obj = Profile(learner_id=profile["learner_id"], mastery=profile["mastery"],
                    evidence=profile["evidence"], updated_at=profile["updated_at"])
    plan = build_plan(p_obj, None, subject_graph, strategies, date.today(),
                      mastery_threshold=MASTERY_THRESHOLD)
    expect_steps = plan.steps[:WEAK_TOP_N]
    rows = gate.guard(f"{label}: 薄弱行解析",
                      lambda: [(int(m.group(1)), m.group(2), m.group(3))
                               for m in WEAK_ROW_RE.finditer(doc)])
    if rows is not None:
        gate.check("  薄弱 top10 与 build_plan 前 10 步逐位一致",
                   [kp for _r, kp, _m in rows] == [s.kp_id for s in expect_steps],
                   f"rows={len(rows)} plan_steps={len(expect_steps)}")
        bad = [kp for _r, kp, m in rows
               if m != f"{profile['mastery'][kp]:.6f}"
               or profile["mastery"][kp] >= MASTERY_THRESHOLD]
        gate.check("  薄弱行 data-m 与画像一致且均 < 0.65", not bad, str(bad[:3]))
        gate.check("  建议动作在位（策略名+依据）",
                   doc.count('<span class="wr-action">建议：<b>') == len(rows)
                   and "建议：" in doc)

    if size_limit is not None:
        size = len(doc.encode("utf-8"))
        gate.check(f"{label}: 体积 < {size_limit // (1024 * 1024)}MB"
                   "（大学科全量渲染聚合策略）",
                   size < size_limit, f"{size / 1024:.0f} KB, KP={len(subject_graph.kps())}")
    return doc


def main() -> int:
    global _LEARNER
    ap = argparse.ArgumentParser(description="知识地图渲染门（exit 0 = 通过）")
    ap.add_argument("--data-dir", default=os.path.join(ROOT, "data"))
    ap.add_argument("--learner", default=_LEARNER)
    args = ap.parse_args()
    _LEARNER = args.learner

    gate = Gate()
    print(f"== 知识地图渲染门 ==\n数据目录: {args.data_dir}\n构造三学科合并图谱…")
    app, bank, app_graph, subject_graphs, strategies = _build_fixture_app(args.data_dir)
    client = TestClient(app)
    subjects_all = discover_subjects(os.path.join(args.data_dir, "knowledge"))
    print(f"图谱学科: {', '.join(subjects_all)}；合并图 KP="
          f"{len(app_graph.kps())}，题库题数={len(bank.items())}")

    n = _post_responses(client, bank)
    print(f"构造作答: learner={_LEARNER} responses={n}")
    profile = client.get(f"/learners/{_LEARNER}/profile").json()
    measured = sum(1 for v in profile["evidence"].values() if v > 0)
    print(f"画像: KP={len(profile['mastery'])} 有证据={measured} "
          f"updated_at={profile['updated_at']}\n")

    docs = {}
    for subject in CHECK_SUBJECTS:
        print(f"-- 学科地图 {subject} --")
        docs[subject] = gate.guard(
            f"{subject} 地图渲染", lambda s=subject: _check_subject_map(
                gate, client, profile, s, subject_graphs[s], strategies,
                size_limit=SIZE_LIMIT_BYTES if s == "chinese" else None))

    print("-- 跨学科总览 --")
    r = client.get(f"/learners/{_LEARNER}/knowledge-map.html")
    if gate.check("总览: HTTP 200 text/html",
                  r.status_code == 200
                  and r.headers["content-type"].startswith("text/html")):
        ov = r.text
        _check_self_containment(gate, "总览", ov)
        gate.check("总览: 全部学科有入口卡片",
                   all(f"subject={s}" in ov for s in subjects_all),
                   f"subjects={len(subjects_all)}")
        gate.check("总览: 页头学习者与数据更新时间",
                   _LEARNER in ov and profile["updated_at"] in ov)

    print("-- 空态（如实，不编造） --")
    gate.check("未知学习者 -> 404",
               client.get(f"/learners/nobody-{_LEARNER}/knowledge-map.html"
                          ).status_code == 404)
    client.post(f"/learners/{_LEARNER}-empty/responses", json={"responses": []})
    no_ev = client.get(f"/learners/{_LEARNER}-empty/knowledge-map.html",
                       params={"subject": "chinese"})
    if gate.check("空学习者查已覆盖零证据学科 -> 200 空态页",
                  no_ev.status_code == 200):
        gate.check("  空态文案如实（无作答证据）",
                   "暂无数据" in no_ev.text and "无作答证据" in no_ev.text)
        _check_self_containment(gate, "空态页", no_ev.text)
    no_ov = client.get(f"/learners/{_LEARNER}-empty/knowledge-map.html",
                       params={"subject": "physics"})
    if gate.check("画像无交集学科 -> 200 空态页", no_ov.status_code == 200):
        gate.check("  空态文案如实（无交集）",
                   "暂无数据" in no_ov.text and "无交集" in no_ov.text)

    print("")
    if gate.unexpected:
        print(f"门失败：UNEXPECTED={len(gate.unexpected)}")
        for u in gate.unexpected:
            print(f"  - {u}")
        return 1
    ok_maps = sum(1 for d in docs.values() if d is not None)
    if gate.failures or ok_maps < len(CHECK_SUBJECTS):
        print(f"门失败：FAIL={len(gate.failures)}，OK 学科地图={ok_maps}/"
              f"{len(CHECK_SUBJECTS)}（验收门：三学科地图全过）")
        for f in gate.failures:
            print(f"  - {f}")
        return 1
    print(f"门通过：三学科地图 OK（KP 数出现=profile 数、薄弱 top10 与数据一致、"
          f"标签配平、无外部资源引用、chinese<2MB），总览与空态 OK。exit 0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
