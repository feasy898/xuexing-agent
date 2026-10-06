"""知识地图样本生成——供人工视检（验收 c）。

构造三学科学习者（与 tools/check_kmap.py 同一构造路径：math/chinese/english
合并图谱 + 确定性对半作答），渲染自包含 HTML 到 out/kmap_sample/。默认样本
为语文（677 KP 全量渲染，大学科聚合策略的最难case）；--subject 可选其他学科，
--overview 附带跨学科总览。样本文件自带生成参数说明，可重现比对。

机器校验走 tools/check_kmap.py（渲染门）；本工具只负责落盘样本。

用法：
  python tools/render_kmap_sample.py                         # 默认语文地图
  python tools/render_kmap_sample.py --subject math
  python tools/render_kmap_sample.py --overview               # 附带总览页
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

from fastapi.testclient import TestClient  # noqa: E402

import importlib.util

_spec = importlib.util.spec_from_file_location(
    "_check_kmap", os.path.join(ROOT, "tools", "check_kmap.py"))
_check_kmap = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_check_kmap)


def main() -> int:
    ap = argparse.ArgumentParser(description="知识地图样本生成（人工视检用）")
    ap.add_argument("--subject", default="chinese",
                    help="样本学科（默认 chinese：677 KP 全量渲染最难case）")
    ap.add_argument("--overview", action="store_true",
                    help="额外生成跨学科总览页样本")
    ap.add_argument("--data-dir", default=os.path.join(ROOT, "data"))
    ap.add_argument("--out-dir",
                    default=os.path.join(ROOT, "out", "kmap_sample"))
    args = ap.parse_args()

    app, bank, app_graph, subject_graphs, _strategies = (
        _check_kmap._build_fixture_app(args.data_dir))
    client = TestClient(app)
    n = _check_kmap._post_responses(client, bank)
    profile = client.get(f"/learners/{_check_kmap._LEARNER}/profile").json()

    targets = [(args.subject, f"{args.subject}_knowledge_map.html")]
    if args.overview:
        targets.append(("", "knowledge_map_overview.html"))

    os.makedirs(args.out_dir, exist_ok=True)
    written = []
    for subject, filename in targets:
        params = {"subject": subject} if subject else {}
        r = client.get(f"/learners/{_check_kmap._LEARNER}/knowledge-map.html",
                       params=params)
        if r.status_code != 200:
            print(f"渲染失败 subject={subject!r}: {r.status_code} {r.text[:200]}")
            return 1
        out_path = os.path.join(args.out_dir, filename)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("<!-- 样本：GET /learners/{id}/knowledge-map.html"
                    f"?subject={subject or '(总览)'} ｜ 构造学习者="
                    f"{_check_kmap._LEARNER}（三学科合并图谱，{n} 条确定性对半作答）"
                    f" ｜ 画像 updated_at={profile['updated_at']}"
                    " ｜ 重现：python tools/render_kmap_sample.py -->\n"
                    + r.text)
        size_kb = os.path.getsize(out_path) / 1024
        written.append((out_path, size_kb))
        print(f"已写入 {out_path}（{size_kb:.0f} KB）")

    print("\n人工视检要点：页头学习者/学科/数据更新时间；热力红→绿、"
          "透明度=置信度、红描边=薄弱；薄弱 top10 建议动作；大学科"
          "年级→章→KP 折叠展开与锚点跳转；空态与图例。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
