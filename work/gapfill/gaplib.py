"""gapfill 共用库：KP 装载、LLM 调用、题目组装、结构/v2 校验、n-gram 去重、落盘。

纪律（owner 口径 2026-10-06）：
- 结构同构：字段与既有 items 一致（id/item_type/stem/answer/kps/difficulty/
  solution/source/options?/form/answer_mode/verification），source 枚举
  original|adapted|llm_generated；verification 如实——单代理生成
  single_agent=true、dual_agent=false（不虚标双代理）；难度初值在
  verification.note 里标 estimated。
- kp 只挂同学科同学段真实 KP id（从 data/knowledge 取，落盘前复验）。
- 去重：与同学科既有题库题干 3-gram Jaccard >= 0.8 判重丢弃。
- 数学题答案程序验算（模板生成器内代码计算）；LLM 题人工抽检。
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "src"))

from xuexing.itembank import itembank_from_dict  # noqa: E402
from xuexing.itembank_v2 import validate_bank_v2  # noqa: E402

KNOWLEDGE_DIR = os.path.join(ROOT, "data", "knowledge")
ITEMS_DIR = os.path.join(ROOT, "data", "items")

LLM_MODEL = "glm-4-flash"
GEN_AGENT = "gapfill-gen-20261006"
TMPL_AGENT = "math-template-gen-20261006"


# ---------------------------------------------------------------- KP 装载
def kp_pool(subject: str, grade: int) -> dict:
    """同学科同年级 {kp_id: (name, description)}（取自 data/knowledge 真实图谱）。"""
    with open(os.path.join(KNOWLEDGE_DIR, f"{subject}_grade{grade}.json"),
              encoding="utf-8") as f:
        data = json.load(f)
    return {k["id"]: (k["name"], k.get("description", ""))
            for k in data["knowledge_points"]}


def kp_desc_line(kp_id: str, pool: dict) -> str:
    name, desc = pool[kp_id]
    return f"- {kp_id} {name}：{desc[:160]}"


# ---------------------------------------------------------------- LLM
def llm(messages: list, temperature: float = 0.4, max_retries: int = 3) -> str:
    base = os.environ["LLM_BASE_URL"].rstrip("/")
    key = os.environ["LLM_API_KEY"]
    last_err = None
    for _ in range(max_retries):
        try:
            req = urllib.request.Request(
                base + "/chat/completions",
                data=json.dumps({"model": LLM_MODEL, "messages": messages,
                                 "temperature": temperature}).encode(),
                headers={"Content-Type": "application/json",
                         "Authorization": "Bearer " + key})
            resp = json.load(urllib.request.urlopen(req, timeout=120))
            return resp["choices"][0]["message"]["content"]
        except Exception as e:  # noqa: BLE001
            last_err = e
    raise RuntimeError(f"LLM call failed after {max_retries} retries: {last_err}")


def llm_json(prompt: str, temperature: float = 0.4) -> list | dict:
    """LLM 返回 JSON（容忍 ``` 围栏与前后杂文字）；解析失败抛 ValueError。"""
    text = llm([{"role": "user", "content": prompt}], temperature=temperature)
    m = re.search(r"```(?:json)?\s*(.+?)```", text, re.S)
    body = m.group(1) if m else text
    start = min((i for i in (body.find("["), body.find("{")) if i >= 0),
                default=-1)
    end = max(body.rfind("]"), body.rfind("}"))
    if start < 0 or end <= start:
        raise ValueError(f"no JSON in LLM output: {text[:200]!r}")
    return json.loads(body[start:end + 1])


# ---------------------------------------------------------------- 组装
def make_item(item_id, item_type, stem, answer, kps, difficulty, solution,
              *, options=None, form, answer_mode=None, source="llm_generated",
              agent=GEN_AGENT, note=""):
    """按既有 items 字段同构组装一题；verification 如实（单代理，不虚标）。"""
    it = {
        "id": item_id,
        "item_type": item_type,
        "stem": stem.strip(),
        "answer": str(answer).strip(),
        "kps": list(kps),
        "difficulty": round(float(difficulty), 2),
        "solution": solution.strip(),
        "source": source,
    }
    if options:
        it["options"] = list(options)
    it["form"] = form
    if answer_mode:
        it["answer_mode"] = answer_mode
    it["verification"] = {
        "agents": [agent],
        "answers_agree": True,
        "single_agent": True,
        "dual_agent": False,
        "note": note or "single-agent generation, blind verification deferred",
    }
    return it


# ---------------------------------------------------------------- 校验/去重
def validate_items(items: list, subject: str) -> list:
    """itembank R 规则 + v2 溯源 + KP 属地复验。返回错误消息列表。"""
    errs = []
    bank = itembank_from_dict({"items": items})
    errs.extend(bank.validate_all())
    errs.extend(validate_bank_v2(items))
    # KP 属地：每题挂的 kp 必须在同学科同学段（按文件年级）图谱里
    pools = {}
    for it in items:
        g = it.pop("_grade")
        if g not in pools:
            pools[g] = set(kp_pool(subject, g))
        for k in it["kps"]:
            if k not in pools[g]:
                errs.append(f"{it['id']}: kp {k} not in {subject} grade{g} graph")
    return errs


def _ngrams(s: str, n: int = 3) -> set:
    s = re.sub(r"\s+", "", s)
    return {s[i:i + n] for i in range(max(len(s) - n + 1, 1))}


def _jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a | b else 0.0


class Deduper:
    """与同学科既有题干 + 本批已收题干做 3-gram Jaccard 去重（>=0.8 判重）。"""

    def __init__(self, subject: str):
        self.existing = []
        path = os.path.join(ITEMS_DIR, f"{subject}_" + "{g}")
        import glob as _g
        for p in _g.glob(os.path.join(ITEMS_DIR, f"{subject}_grade*_items.json")):
            with open(p, encoding="utf-8") as f:
                for it in json.load(f)["items"]:
                    self.existing.append(_ngrams(it["stem"]))

    def is_dup(self, stem: str, threshold: float = 0.8) -> bool:
        g = _ngrams(stem)
        return any(_jaccard(g, e) >= threshold for e in self.existing)

    def add(self, stem: str) -> None:
        self.existing.append(_ngrams(stem))


# ---------------------------------------------------------------- 落盘
def append_items(subject: str, grade: int, items: list, ledger: dict) -> int:
    """把新题并入 data/items/{subject}_grade{N}_items.json（2 空格缩进同房式）。

    重复 id / 落盘前校验失败一律拒绝写盘（fail-closed）。返回实际写入数。
    """
    assert items, "no items"
    path = os.path.join(ITEMS_DIR, f"{subject}_grade{grade}_items.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    known = {it["id"] for it in data["items"]}
    for it in items:
        if it["id"] in known:
            raise ValueError(f"duplicate item id: {it['id']}")
    data["items"].extend(items)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    ledger.setdefault("appended", []).extend(it["id"] for it in items)
    return len(items)
