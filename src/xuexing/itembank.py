"""itembank — 题库模块：Item 内存存储、按 id/知识点检索、两级校验与 JSON 载入。

实现依据冻结契约 specs/frozen/itembank.spec.md。仅依赖标准库与 xuexing.types；
全模块确定性（无随机、无时钟），除 load_itembank 外无文件 IO 与全局状态。
"""
from __future__ import annotations

import json
import re

from xuexing.types import Item

__all__ = ["ItemBankError", "ItemBank", "load_itembank", "itembank_from_dict",
           "MCQ_MULTI", "ANSWER_MODES", "split_multi_answer"]

# 多选形态标签：只有该值走「answer 是标签集合」语义，其余 form 一律按单选判定。
MCQ_MULTI = "mcq_multi"
# answer_mode 取值域（冻结枚举）。
ANSWER_MODES = ("exact", "subset")
# 多选答案分隔符：ASCII/全角逗号、顿号、分号、中文「和」（历史写法）。
# 刻意不含空白——选项全文形如「A. 甲正确」自带空格，按空白切会把标签与正文劈开。
_MULTI_SEP_RE = re.compile(r"[,，、;；]+|和")


def split_multi_answer(answer: str) -> list[str]:
    """把多选答案拆成标签列表；无分隔符时原样单元素返回。不 strip 大小写以外的形态。"""
    return [p for p in (part.strip() for part in _MULTI_SEP_RE.split(answer)) if p]


class ItemBankError(ValueError):
    """题库操作错误（如重复 id）。ValueError 的直接子类。"""


class ItemBank:
    """内存题库。add 不做校验；校验只发生在 validate_item / validate_all。"""

    def __init__(self) -> None:
        self._items: dict[str, Item] = {}

    def add(self, item: Item) -> None:
        if item.id in self._items:
            raise ItemBankError(f"duplicate item id: {item.id}")
        self._items[item.id] = item

    def get(self, item_id: str) -> Item | None:
        return self._items.get(item_id)

    def has(self, item_id: str) -> bool:
        return item_id in self._items

    def items(self) -> list[Item]:
        # id 码点升序；每次返回新列表，修改返回值不影响库内数据。
        return [self._items[k] for k in sorted(self._items)]

    def by_kp(self, kp_id: str, primary_only: bool = False) -> list[Item]:
        out: list[Item] = []
        for it in self.items():
            if primary_only:
                if it.kps and it.kps[0] == kp_id:
                    out.append(it)
            elif kp_id in it.kps:
                out.append(it)
        return out

    def validate_item(self, item: Item) -> list[str]:
        # 规则目录与累加顺序固定（R1..R9c）。R1 不短路：id 假值时其余消息
        # 前缀仍按字面 f"{item.id}: " 渲染。
        errs: list[str] = []
        if not item.id:
            errs.append("missing id")
        p = f"{item.id}: "
        if item.item_type not in ("choice", "fill", "solve"):
            errs.append(f"{p}bad item_type {item.item_type!r}")
        if not item.stem.strip():
            errs.append(f"{p}empty stem")
        if not item.answer.strip():
            errs.append(f"{p}empty answer")
        if not item.kps:
            errs.append(f"{p}no kp tags")
        # 越域谓词冻结为链式比较：NaN/±Inf 使两段均 False，not False → 必须报错。
        if not (0.0 <= item.difficulty <= 1.0):
            errs.append(f"{p}difficulty out of [0,1]")
        if not (0.0 <= item.discrimination <= 1.0):
            errs.append(f"{p}discrimination out of [0,1]")
        if item.guess is not None and not (0.0 <= item.guess <= 1.0):
            errs.append(f"{p}guess out of [0,1]")
        if item.item_type == "choice":
            opts = item.options
            if len(opts) < 2:
                # R9a 违反时跳过 R9b，但 R9c 独立执行。
                errs.append(f"{p}choice needs >=2 options")
            else:
                ans = item.answer.strip()
                labels = [o.strip().split(".")[0].strip() for o in opts]
                texts = [o.strip() for o in opts]
                if item.form == MCQ_MULTI:
                    # R9b-m：多选按「拆分后每一项都在 labels 集内」判定。
                    parts = split_multi_answer(ans)
                    if not parts:
                        errs.append(f"{p}mcq_multi answer has no option label")
                    elif len(set(parts)) != len(parts):
                        errs.append(f"{p}mcq_multi answer repeats a label")
                    elif any(part not in labels for part in parts):
                        errs.append(f"{p}answer not among options")
                elif ans not in labels and ans not in texts:
                    errs.append(f"{p}answer not among options")
            stripped = [o.strip() for o in opts]
            if len(set(stripped)) != len(stripped):
                errs.append(f"{p}duplicate options")
        if item.answer_mode not in ANSWER_MODES:
            errs.append(f"{p}bad answer_mode {item.answer_mode!r}")
        return errs

    def validate_all(self, valid_kp_ids: set[str] | None = None) -> list[str]:
        # 遍历序 = id 升序；每题先题目错误、后 unknown kp 错误；
        # valid_kp_ids=None 完全跳过 kp 检查；先去重再整体升序。
        errs: list[str] = []
        for it in self.items():
            errs.extend(self.validate_item(it))
            if valid_kp_ids is not None:
                for k in it.kps:
                    if k not in valid_kp_ids:
                        errs.append(f"{it.id}: unknown kp {k}")
        return sorted(set(errs))


def load_itembank(path: str) -> ItemBank:
    """读 utf-8 JSON 文件。文件缺失 → OSError，JSON 非法 → json.JSONDecodeError。"""
    with open(path, encoding="utf-8") as f:
        return itembank_from_dict(json.load(f))


def itembank_from_dict(data: dict) -> ItemBank:
    """从含 "items" 列表的字典构造题库。

    未知键静默忽略（禁 Item(**it) 式实现）；必填字段缺失 → KeyError；
    类型强制失败时异常原样传播（不包装、不回退缺省值）。
    """
    bank = ItemBank()
    for it in data["items"]:
        bank.add(Item(
            id=it["id"],
            item_type=it["item_type"],
            stem=it["stem"],
            answer=str(it["answer"]),
            kps=list(it["kps"]),
            difficulty=float(it["difficulty"]),
            solution=it.get("solution", ""),
            options=list(it["options"]) if "options" in it else [],
            discrimination=float(it["discrimination"]) if "discrimination" in it else 0.6,
            guess=it.get("guess"),
            misconceptions=list(it["misconceptions"]) if "misconceptions" in it else [],
            form=it.get("form", "choice"),
            answer_mode=it.get("answer_mode", "exact"),
            audio=str(it.get("audio", "") or ""),
        ))
    return bank
