"""单元测试：听力音频管线（item.audio 字段 -> 作答页 <audio controls> -> /audio）。

钉住：
- 题库装载：itembank_from_dict 认 audio 字段；缺省为空串（其余题零影响）；
- 作答页渲染：有 audio 的题恰一个 ``<audio controls src="/audio/{文件名}">``、
  标签配平；无 audio 的题零音频标记；打印卷（render_paper_html）绝不渲染音频；
- fail-closed：题库 audio 混进路径分隔符/上级目录/外链/白名单外字符 →
  PaperRenderError，绝不渲染成可疑 src；
- 红线不受影响：带音频题的作答页 redline_report 仍然零违规；
- /audio 静态挂载：mp3 可取（content-type audio/mpeg、字节原样）、缺失 404；
- 真实数据：初中英语题库里 form=listening 恰为 6+1=7 道、每道 audio 字段为
  「{item_id}.mp3」且满足渲染白名单（只依赖入库的题库 JSON，不依赖被
  .gitignore 的 mp3 本体——新 clone 没有 mp3 也能全绿）；
- 生成脚本的朗读文本抽取（listening_material_text）：听力材料标记/印刷题
  截断/说话人标记剥离，纯函数零出网。
"""
from __future__ import annotations

import importlib.util
import os

import pytest

from xuexing.itembank import ItemBank, itembank_from_dict
from xuexing.paper_by_spec import load_stage_bank
from xuexing.paper_render import (
    PaperRenderError,
    check_html_tag_balance,
    redline_report,
    render_exam_form_html,
    render_paper_html,
)
from xuexing.types import Item, KnowledgePoint

from xuexing.paper_by_spec import generate_paper_by_spec

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

_SPEC = {
    "id": "spec_audio_demo",
    "subject": "english",
    "stage": "junior",
    "usage": "final_exam",
    "duration_min": 60,
    "total_points": 3,
    "sections": [
        # 2 题全装订（li_1 带音频、li_2 不带），不依赖选题种子
        {"title": "一、听力", "form": "listening", "count": 2, "points_each": 1.5},
    ],
}


def _listening_item(**overrides) -> Item:
    base = dict(
        id="li_1", item_type="solve",
        stem="听力材料：\nM: Hello there!\nW: Hi!\n\n1. Who says hello?\nA. M\nB. W",
        answer="B", kps=["kp_lis"], difficulty=0.5, form="listening",
        solution="解析：W 说你好",
    )
    base.update(overrides)
    return Item(**base)


def _bank_with(item: Item) -> ItemBank:
    b = ItemBank()
    b.add(item)
    b.add(Item(id="li_2", item_type="solve", stem="无音频听力题", answer="A",
               kps=["kp_lis"], difficulty=0.4, form="listening"))
    return b


def _paper(bank):
    return generate_paper_by_spec(bank, _SPEC, seed=42,
                                  difficulty_target=0.5, spec_id="spec_audio_demo")


# ---------- 题库装载 ----------

def test_itembank_loads_audio_field_and_defaults_blank():
    bank = itembank_from_dict({"items": [
        {"id": "a1", "item_type": "solve", "stem": "题", "answer": "答",
         "kps": ["k"], "difficulty": 0.5, "audio": "a1.mp3"},
        {"id": "a2", "item_type": "solve", "stem": "题", "answer": "答",
         "kps": ["k"], "difficulty": 0.5},
    ]})
    assert bank.get("a1").audio == "a1.mp3"
    assert bank.get("a2").audio == ""  # 缺字段 → 空串（绝大多数题无音频）


# ---------- 作答页渲染 ----------

def test_exam_form_renders_audio_controls_for_audio_item():
    bank = _bank_with(_listening_item(audio="li_1.mp3"))
    paper = _paper(bank)
    html_doc = render_exam_form_html(paper, bank, session_id="s1", learner_id="k1")
    # 有 audio 的题：恰一个控件、src 与题库声明一致
    assert html_doc.count("<audio") == 1
    assert ('<audio class="q-audio" controls preload="none" '
            'src="/audio/li_1.mp3">') in html_doc
    assert not check_html_tag_balance(html_doc)
    # 无 audio 的题：零音频标记
    block2 = html_doc.split('id="q2"')[1]
    assert "<audio" not in block2


def test_print_paper_never_renders_audio():
    """打印卷放不出声音：题库带 audio 也不渲染 <audio>（纸卷红线）。"""
    bank = _bank_with(_listening_item(audio="li_1.mp3"))
    paper = _paper(bank)
    assert "<audio" not in render_paper_html(paper, bank)


@pytest.mark.parametrize("bad", [
    "../evil.mp3",          # 上级目录
    "a/b.mp3",              # 路径分隔符
    "a\\b.mp3",             # 反斜杠
    "http://evil/x.mp3",    # 外链
    ".hidden.mp3",          # 隐藏文件
    "x y.mp3",              # 白名单外字符（空格）
    "x.mp3<script>",        # 标记注入
])
def test_unsafe_audio_path_fail_closed(bad):
    bank = _bank_with(_listening_item(audio=bad))
    paper = _paper(bank)
    with pytest.raises(PaperRenderError):
        render_exam_form_html(paper, bank, session_id="s1", learner_id="k1")


def test_audio_page_redline_still_clean():
    """音频文件名/控件不是作答依据：红线自检仍零违规。"""
    bank = _bank_with(_listening_item(audio="li_1.mp3"))
    paper = _paper(bank)
    html_doc = render_exam_form_html(paper, bank, session_id="s1", learner_id="k1")
    assert redline_report(paper, bank, html_doc, "") == []


# ---------- /audio 静态挂载 ----------

def test_audio_static_route_serves_and_404s(tmp_path):
    from fastapi.testclient import TestClient
    from xuexing.kpgraph import KPGraph
    from xuexing.pedagogy import StrategyLibrary
    from xuexing.server import create_app

    (tmp_path / "hello.mp3").write_bytes(b"ID3fake-mp3-bytes")
    g = KPGraph()
    g.add_kp(KnowledgePoint(id="kp_lis", name="听", subject="english", grade=7,
                            cluster="lis"))
    app = create_app(_bank_with(_listening_item(audio="li_1.mp3")), g,
                     StrategyLibrary(), None,
                     spec_catalog={_SPEC["id"]: _SPEC},
                     stage_bank_loader=lambda s, st: _bank_with(_listening_item(audio="li_1.mp3")),
                     stage_graph_loader=lambda s: g,
                     audio_dir=str(tmp_path))
    client = TestClient(app)
    r = client.get("/audio/hello.mp3")
    assert r.status_code == 200
    assert r.headers["content-type"] == "audio/mpeg"
    assert r.content == b"ID3fake-mp3-bytes"
    assert client.get("/audio/missing.mp3").status_code == 404


# ---------- 真实数据：eng_jr 6+1 道 listening 题全挂 audio ----------

def test_eng_jr_listening_items_all_have_audio():
    bank, _grades = load_stage_bank(os.path.join(ROOT, "data"), "english", "junior")
    rows = [it for it in bank.items() if getattr(it, "form", "") == "listening"]
    assert len(rows) == 7, f"eng_jr listening 应为 6+1=7 道，实得 {len(rows)}"
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")
    for it in rows:
        assert it.audio == f"{it.id}.mp3", f"{it.id} 的 audio 字段异常: {it.audio!r}"
        assert set(it.audio) <= allowed and "/" not in it.audio
    ids = {it.id for it in rows}
    assert "eng_en_jr_0194" in ids                      # 那道「+1」的特殊题
    assert sum(1 for i in ids if i.startswith("english_gap_llm_")) == 6


# ---------- 生成脚本的朗读文本抽取（纯函数、零出网） ----------

def _load_gen():
    path = os.path.join(ROOT, "tools", "gen_listening_audio.py")
    spec = importlib.util.spec_from_file_location("gen_listening_audio", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_listening_material_text_extracts_material_only():
    gen = _load_gen()
    stem = ("图书馆借书\n听力材料：\nM: Hey, Wang Mei!\nW: Hi!\n\n"
            "1. Who greets first?\nA. M\nB. W")
    text = gen.listening_material_text(stem)
    assert "Hey, Wang Mei!" in text
    assert "图书馆借书" not in text       # 标题行不是材料
    assert "听力材料" not in text          # 标记行不是材料
    assert "1. Who greets first?" not in text  # 印刷题不进音频
    assert "M: " not in text and "W: " not in text  # 说话人标记剥离


def test_listening_material_text_no_marker_reads_whole_stem():
    gen = _load_gen()
    text = gen.listening_material_text("M: Only dialogue here.\nW: Yes.")
    assert "Only dialogue here." in text and "Yes." in text


def test_listening_material_text_stops_at_questions_marker():
    gen = _load_gen()
    stem = ("校园广播（听力材料）：\nAttention! Canteen closed.\n\n"
            "请根据以上广播内容回答：\n1. When?\nA. Mon\nB. Tue")
    text = gen.listening_material_text(stem)
    assert "Canteen closed" in text
    assert "请根据" not in text and "When?" not in text


def test_manifest_text_sources_are_annotated():
    """清单里 6 道 stem 来源 + 1 道 authored（0194 题面无材料，如实标注）。"""
    gen = _load_gen()
    manifest = gen.load_manifest()
    assert manifest["model"] == "stepaudio-2.5-tts"
    files = manifest["files"]
    assert len(files) == 7
    sources = {v["text_source"] for v in files.values()}
    assert sources == {"stem", "authored"}
    authored = [k for k, v in files.items() if v["text_source"] == "authored"]
    assert authored == ["eng_en_jr_0194.mp3"]
    for fname, v in files.items():
        assert v["sha256"] and len(v["sha256"]) == 64
        assert v["text_sha256"] == gen.sha256_hex(v["text"].encode("utf-8"))
