"""误解库覆盖审计器（盲重写实例 · 第三波 · 第 1 轮）。

唯一权威契约：``specs/frozen/misconception_coverage.spec.md``（定稿 v1）。

模块职责（spec §1）：把误解库文件 dict 解析校验为条目/豁免对象（``parse_bank``），
再对给定 KP id 清单逐个核对「误解条数 >= min_per_kp 或显式声明该 KP 无误解」，
产出确定性报告 ``MisconceptionReport``（``audit`` / ``audit_dicts``）。

装载与依赖约束（spec §2）：
- 仅依赖标准库 ``dataclasses``；不 import ``xuexing.types`` 或任何其他 xuexing 模块；
- 全部注解写真实对象（禁止字符串化注解，即禁止文件头 future annotations 语句）：
  经 ``spec_from_file_location`` 以顶层模块名注入装载时，字符串化注解会令
  dataclass 处理期触发 AttributeError（CPython 3.12 ``_is_type`` 路径）；
- 无文件/网络 IO、无随机、无系统时钟、无环境读取、无全局可变状态（spec §5/§7）。

对 ``xuexing.types.Misconception`` 只做鸭子兼容（spec I14）：``audit`` 的入参条目
只需具备 ``.id`` / ``.kp_id``（及可选 ``.signature``）属性，本模块从不 import 它。
"""

from dataclasses import dataclass

__all__ = [
    "Exemption",
    "MisconceptionCoverageError",
    "MisconceptionEntry",
    "MisconceptionReport",
    "audit",
    "audit_dicts",
    "parse_bank",
]


class MisconceptionCoverageError(ValueError):
    """本模块全部校验失败的统一异常类型（spec §3.1：ValueError 直接子类）。"""


@dataclass
class MisconceptionEntry:
    """单条误解条目（spec §3.2）。

    构造函数不抛任何字段错、不挂 ``__post_init__`` 字段校验；一切字段级校验
    只发生在 ``parse_bank`` / ``audit``。``signature`` 解析产物恒为 tuple
    （文件形状是 list，由 ``parse_bank`` 负责 list -> tuple）。
    """

    id: str
    kp_id: str
    description: str
    hint: str
    signature: tuple


@dataclass
class Exemption:
    """「该 KP 无误解」的显式豁免声明（spec §3.2）。"""

    kp_id: str
    reason: str


@dataclass
class MisconceptionReport:
    """覆盖审计报告（spec §3.3）：六个序列字段全部为 tuple，顺序 = KP 输入原序。"""

    kp_ids: tuple
    counts: tuple
    deficient_kp_ids: tuple
    exempt_kp_ids: tuple
    covered_kp_ids: tuple
    min_per_kp: int
    total_misconceptions: int

    def is_complete(self) -> bool:
        """无缺口 KP 即完备；``not tuple`` 恒为 bool，空 KP 宇宙诚实为真（I13）。"""
        return not self.deficient_kp_ids


# ---------------------------------------------------------------------------
# 内部校验助手（异常消息文案不作契约承诺，spec §6）
# ---------------------------------------------------------------------------


def _require_id(value, what):
    """id 校验：非空 str 且无首尾空白（spec §3.4 步骤 4/5、§3.5）。"""
    if not isinstance(value, str):
        raise MisconceptionCoverageError(
            f"{what} 必须是非空 str，得到 {type(value).__name__}: {value!r}")
    if not value or value != value.strip():
        raise MisconceptionCoverageError(f"{what} 不得为空串或含首尾空白: {value!r}")


def _require_text(value, what):
    """文本校验：非空白 str，内部空白自由（spec §3.4 步骤 4/5）。"""
    if not isinstance(value, str):
        raise MisconceptionCoverageError(
            f"{what} 必须是 str，得到 {type(value).__name__}: {value!r}")
    if not value.strip():
        raise MisconceptionCoverageError(f"{what} 不得为空或纯空白: {value!r}")


def parse_bank(data) -> tuple[list[MisconceptionEntry], list[Exemption]]:
    """解析误解库文件 dict，返回 ``(entries, exemptions)`` 两个 list（文件内原序）。

    校验规则与容忍形态见 spec §3.4：字段级校验失败一律抛
    ``MisconceptionCoverageError``；条目/豁免 dict 的额外键静默忽略；空
    ``misconceptions`` list 合法；**不做**「豁免 KP 与已有误解矛盾」检查（该检查
    只属于 ``audit``）。纯函数：不改输入 dict，两次调用结果逐字段相等（I2）。
    """
    if not isinstance(data, dict):
        raise MisconceptionCoverageError(
            f"误解库数据必须是 dict，得到 {type(data).__name__}")
    if "misconceptions" not in data:
        raise MisconceptionCoverageError('误解库数据缺少 "misconceptions" 键')
    raw_entries = data["misconceptions"]
    if not isinstance(raw_entries, list):
        raise MisconceptionCoverageError(
            f'"misconceptions" 必须是 list，得到 {type(raw_entries).__name__}')
    raw_exemptions = data.get("exemptions", [])
    if not isinstance(raw_exemptions, list):
        raise MisconceptionCoverageError(
            f'"exemptions" 必须是 list，得到 {type(raw_exemptions).__name__}')

    entries = []
    seen_entry_ids = set()
    for index, raw_entry in enumerate(raw_entries):
        if not isinstance(raw_entry, dict):
            raise MisconceptionCoverageError(
                f"misconceptions[{index}] 必须是 dict，"
                f"得到 {type(raw_entry).__name__}")
        entry_id = raw_entry.get("id")
        _require_id(entry_id, f"misconceptions[{index}].id")
        if entry_id in seen_entry_ids:
            raise MisconceptionCoverageError(f"误解条目 id 在文件内重复: {entry_id!r}")
        seen_entry_ids.add(entry_id)
        kp_id = raw_entry.get("kp_id")
        _require_id(kp_id, f"misconceptions[{index}].kp_id")
        _require_text(raw_entry.get("description"),
                      f"misconceptions[{index}].description")
        _require_text(raw_entry.get("hint"), f"misconceptions[{index}].hint")
        signature = raw_entry.get("signature")
        if not isinstance(signature, list) or not signature:
            raise MisconceptionCoverageError(
                f"misconceptions[{index}].signature 必须是非空 list，得到 {signature!r}")
        signature_items = []
        seen_signature_items = set()
        for item in signature:
            if not isinstance(item, str):
                raise MisconceptionCoverageError(
                    f"misconceptions[{index}].signature 元素必须是 str: {item!r}")
            if not item or item != item.strip():
                raise MisconceptionCoverageError(
                    f"misconceptions[{index}].signature 元素不得为空串"
                    f"或含首尾空白: {item!r}")
            if item in seen_signature_items:
                raise MisconceptionCoverageError(
                    f"misconceptions[{index}].signature 条目内重复: {item!r}")
            seen_signature_items.add(item)
            signature_items.append(item)
        entries.append(MisconceptionEntry(
            id=entry_id,
            kp_id=kp_id,
            description=raw_entry["description"],
            hint=raw_entry["hint"],
            signature=tuple(signature_items),
        ))

    exemptions = []
    seen_exempt_kps = set()
    for index, raw_exemption in enumerate(raw_exemptions):
        if not isinstance(raw_exemption, dict):
            raise MisconceptionCoverageError(
                f"exemptions[{index}] 必须是 dict，"
                f"得到 {type(raw_exemption).__name__}")
        exempt_kp = raw_exemption.get("kp_id")
        _require_id(exempt_kp, f"exemptions[{index}].kp_id")
        if exempt_kp in seen_exempt_kps:
            raise MisconceptionCoverageError(f"同一 KP 重复豁免: {exempt_kp!r}")
        seen_exempt_kps.add(exempt_kp)
        _require_text(raw_exemption.get("reason"), f"exemptions[{index}].reason")
        exemptions.append(Exemption(
            kp_id=exempt_kp,
            reason=raw_exemption["reason"],
        ))

    return entries, exemptions


def audit(kp_ids, entries, exemptions=(), min_per_kp: int = 2) -> MisconceptionReport:
    """对 KP id 清单做误解覆盖审计，返回确定性 ``MisconceptionReport``（spec §3.5）。

    - ``kp_ids``：可迭代对象，只迭代一次；元素逐个按 id 校验，清单内重复抛错。
    - ``entries``：鸭子类型，元素只需有 ``.id`` / ``.kp_id`` 属性；``.signature``
      若存在须可 ``tuple()`` 化（缺失则按空 tuple 处理）；同一 KP 内 signature
      逐元素跨条目唯一（归因歧义即数据错误，I10）；id 跨输入全局唯一（I9）。
    - ``exemptions``：元素只需有 ``.kp_id`` 属性（不读 ``.reason``）；引用未知 KP、
      同一 KP 重复豁免、豁免 KP 名下已有误解均抛错（I8）。
    - ``min_per_kp``：必须是非 bool 的 int 且 >= 1。

    报告构造（I4/I5/I6）：``counts`` 按输入原序每 KP 恰一项；``deficient`` =
    条数 < min_per_kp 且未豁免；``exempt`` = 豁免集 ∩ 输入原序；``covered`` =
    条数 >= min_per_kp；三分划两两不交、并集 = KP 全集。
    """
    if isinstance(min_per_kp, bool) or not isinstance(min_per_kp, int) or min_per_kp < 1:
        raise MisconceptionCoverageError(
            f"min_per_kp 必须是 >= 1 的 int（bool 不算），得到 {min_per_kp!r}")

    kp_list = []
    seen_kp = set()
    for kp in kp_ids:
        _require_id(kp, "kp_ids 元素")
        if kp in seen_kp:
            raise MisconceptionCoverageError(f"KP 清单内元素重复: {kp!r}")
        seen_kp.add(kp)
        kp_list.append(kp)

    counts_by_kp = {}
    signature_seen_by_kp = {}
    seen_entry_ids = set()
    total_misconceptions = 0
    for entry in entries:
        total_misconceptions += 1
        entry_id = getattr(entry, "id", None)
        _require_id(entry_id, "条目 .id")
        if entry_id in seen_entry_ids:
            raise MisconceptionCoverageError(f"误解条目 id 跨输入重复: {entry_id!r}")
        seen_entry_ids.add(entry_id)
        entry_kp = getattr(entry, "kp_id", None)
        if entry_kp not in seen_kp:
            raise MisconceptionCoverageError(f"误解条目引用未知 KP: {entry_kp!r}")
        counts_by_kp[entry_kp] = counts_by_kp.get(entry_kp, 0) + 1
        if hasattr(entry, "signature"):
            signature_items = tuple(entry.signature)
        else:
            signature_items = ()
        seen_signature = signature_seen_by_kp.setdefault(entry_kp, set())
        for item in signature_items:
            if item in seen_signature:
                raise MisconceptionCoverageError(
                    f"同一 KP 内 signature 跨条目重复: KP={entry_kp!r}, "
                    f"signature={item!r}")
            seen_signature.add(item)

    exempt_kps = set()
    for exemption in exemptions:
        exempt_kp = getattr(exemption, "kp_id", None)
        if exempt_kp not in seen_kp:
            raise MisconceptionCoverageError(f"豁免引用未知 KP: {exempt_kp!r}")
        if exempt_kp in exempt_kps:
            raise MisconceptionCoverageError(f"同一 KP 重复豁免: {exempt_kp!r}")
        if counts_by_kp.get(exempt_kp, 0) > 0:
            raise MisconceptionCoverageError(f"豁免 KP 名下已有误解条目: {exempt_kp!r}")
        exempt_kps.add(exempt_kp)

    return MisconceptionReport(
        kp_ids=tuple(kp_list),
        counts=tuple((kp, counts_by_kp.get(kp, 0)) for kp in kp_list),
        deficient_kp_ids=tuple(
            kp for kp in kp_list
            if counts_by_kp.get(kp, 0) < min_per_kp and kp not in exempt_kps),
        exempt_kp_ids=tuple(kp for kp in kp_list if kp in exempt_kps),
        covered_kp_ids=tuple(
            kp for kp in kp_list if counts_by_kp.get(kp, 0) >= min_per_kp),
        min_per_kp=min_per_kp,
        total_misconceptions=total_misconceptions,
    )


def audit_dicts(kp_dicts, bank_data, min_per_kp: int = 2) -> MisconceptionReport:
    """knowledge json dict 列表 × 误解库文件 dict 的便捷入口（spec §3.6）。

    校验顺序为绑定条款：先校验 ``kp_dicts``（必须是 list 或 tuple；每个元素必须是
    dict 且 ``"id"`` 经 id 校验），再 ``parse_bank(bank_data)``（解析错误原样抛出），
    最后交 ``audit``（重复 KP id 由 audit 的重复检查抛出）。
    """
    if not isinstance(kp_dicts, (list, tuple)):
        raise MisconceptionCoverageError(
            f"kp_dicts 必须是 list 或 tuple，得到 {type(kp_dicts).__name__}")
    kp_list = []
    for index, kp_dict in enumerate(kp_dicts):
        if not isinstance(kp_dict, dict):
            raise MisconceptionCoverageError(
                f"kp_dicts[{index}] 必须是 dict，得到 {type(kp_dict).__name__}")
        kp_id = kp_dict.get("id")
        _require_id(kp_id, f"kp_dicts[{index}].id")
        kp_list.append(kp_id)
    entries, exemptions = parse_bank(bank_data)
    return audit(kp_list, entries, exemptions, min_per_kp)
