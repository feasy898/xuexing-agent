"""误解库覆盖审计器（误解库扩充管线的确定性内核）。

契约：``specs/frozen/misconception_coverage.spec.md``（第三波冻结定稿 v1）。

行为契约三条：

* **解析纪律** —— ``parse_bank`` 把误解库文件 dict 解析为 ``MisconceptionEntry`` /
  ``Exemption`` 对象，字段级校验失败一律抛 ``MisconceptionCoverageError``；
* **交叉一致性** —— 条目 id 跨输入全局唯一、条目/豁免不得引用未知 KP、豁免不得与已有
  误解矛盾、同 KP 内 signature 跨条目唯一；
* **纯度与确定性** —— 无 IO、无随机、无时钟，全局可变状态；输出序列一律 tuple 化，
  顺序 = KP 输入原序 / 文件内原序，同输入同输出。

依赖仅标准库 ``dataclasses``（spec §2 / §7）：不 import 任何 xuexing 模块（包括
``xuexing.types``）；``audit`` 只按鸭子类型接受 ``xuexing.types.Misconception``（spec I14）。
本模块**禁用** ``__future__`` 的延迟注解（spec §2 装载门），所有注解写真实对象
（``tuple`` / ``int`` / ``str``）。
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
    """本模块校验失败的统一异常类型（``ValueError`` 直接子类，spec §3.1 / §6）。"""


@dataclass
class MisconceptionEntry:
    """一条误解条目；构造函数不做任何字段校验（spec §3.2）。"""

    id: str
    kp_id: str
    description: str
    hint: str
    signature: tuple


@dataclass
class Exemption:
    """一条「该 KP 无误解」豁免声明；构造函数不做任何字段校验（spec §3.2）。"""

    kp_id: str
    reason: str


@dataclass
class MisconceptionReport:
    """一次覆盖审计的确定性报告；六个序列字段全部是 tuple（spec §3.3）。"""

    kp_ids: tuple
    counts: tuple
    deficient_kp_ids: tuple
    exempt_kp_ids: tuple
    covered_kp_ids: tuple
    min_per_kp: int
    total_misconceptions: int

    def is_complete(self) -> bool:
        """无缺口 KP 时为 True；空 KP 宇宙下亦为 True（spec I13）。"""
        return not self.deficient_kp_ids


# 鸭子条目缺 ``.signature`` 属性时的哨兵（spec §3.5：缺属性按空 tuple 处理）
_MISSING = object()


def _fail(label, detail):
    raise MisconceptionCoverageError(f"{label} {detail}")


def _check_id(value, label):
    """id 纪律：非空 str 且无首尾空白；原样返回（spec §3.4 步骤 4/5、§3.5）。"""
    if not isinstance(value, str):
        _fail(label, f"必须是 str，实际是 {type(value).__name__}")
    if value == "" or value != value.strip():
        _fail(label, f"不得为空串或含首尾空白：{value!r}")
    return value


def _check_text(value, label):
    """文本纪律：非空白 str，内部空白自由，原样透传（spec §3.4 步骤 4/5）。"""
    if not isinstance(value, str):
        _fail(label, f"必须是 str，实际是 {type(value).__name__}")
    if value.strip() == "":
        _fail(label, f"不得为空或纯空白：{value!r}")
    return value


def _iterate(obj, label):
    """把入参当可迭代对象迭代一次；不可迭代时并入统一异常（spec §6）。"""
    try:
        return iter(obj)
    except TypeError as exc:
        raise MisconceptionCoverageError(
            f"{label} 必须可迭代，实际是 {type(obj).__name__}"
        ) from exc


def parse_bank(data):
    """解析误解库文件 dict，返回 ``(entries, exemptions)`` 两个 list（文件内原序）。

    校验按 spec §3.4 步骤 1-5 的次序执行，每一项失败都抛
    ``MisconceptionCoverageError``；不修改入参（I2）。额外键静默忽略。
    """
    if not isinstance(data, dict):
        _fail("data", f"必须是 dict，实际是 {type(data).__name__}")
    if "misconceptions" not in data:
        _fail("data", "缺少 'misconceptions' 键")

    raw_entries = data["misconceptions"]
    if not isinstance(raw_entries, list):
        _fail("data['misconceptions']", f"必须是 list，实际是 {type(raw_entries).__name__}")

    raw_exemptions = data.get("exemptions", [])
    if not isinstance(raw_exemptions, list):
        _fail("data['exemptions']", f"必须是 list，实际是 {type(raw_exemptions).__name__}")

    entries = []
    seen_entry_ids = set()
    for pos, item in enumerate(raw_entries):
        where = f"misconceptions[{pos}]"
        if not isinstance(item, dict):
            _fail(where, f"必须是 dict，实际是 {type(item).__name__}")

        entry_id = _check_id(item.get("id"), f"{where}.id")
        if entry_id in seen_entry_ids:
            _fail(f"{where}.id", f"文件内重复：{entry_id!r}")
        seen_entry_ids.add(entry_id)

        kp_id = _check_id(item.get("kp_id"), f"{where}.kp_id")
        description = _check_text(item.get("description"), f"{where}.description")
        hint = _check_text(item.get("hint"), f"{where}.hint")

        signature = item.get("signature")
        if not isinstance(signature, list):
            _fail(f"{where}.signature", f"必须是 list，实际是 {type(signature).__name__}")
        if not signature:
            _fail(f"{where}.signature", "不得为空 list")
        seen_signature = set()
        for pos_sig, pattern in enumerate(signature):
            _check_id(pattern, f"{where}.signature[{pos_sig}]")
            if pattern in seen_signature:
                _fail(f"{where}.signature[{pos_sig}]", f"条目内重复：{pattern!r}")
            seen_signature.add(pattern)

        entries.append(
            MisconceptionEntry(
                id=entry_id,
                kp_id=kp_id,
                description=description,
                hint=hint,
                signature=tuple(signature),
            )
        )

    exemptions = []
    seen_exempted = set()
    for pos, item in enumerate(raw_exemptions):
        where = f"exemptions[{pos}]"
        if not isinstance(item, dict):
            _fail(where, f"必须是 dict，实际是 {type(item).__name__}")

        kp_id = _check_id(item.get("kp_id"), f"{where}.kp_id")
        if kp_id in seen_exempted:
            _fail(f"{where}.kp_id", f"豁免列表内重复：{kp_id!r}")
        seen_exempted.add(kp_id)

        reason = _check_text(item.get("reason"), f"{where}.reason")
        exemptions.append(Exemption(kp_id=kp_id, reason=reason))

    return entries, exemptions


def audit(kp_ids, entries, exemptions=(), min_per_kp=2):
    """按 KP 清单核对误解覆盖度，产出 ``MisconceptionReport``（spec §3.5）。

    ``kp_ids`` 为任意可迭代对象（只迭代一次）；``entries`` / ``exemptions`` 只需
    鸭子属性（``.id`` / ``.kp_id`` / ``.signature``）。不修改任一入参（I12）。
    """
    if isinstance(min_per_kp, bool) or not isinstance(min_per_kp, int):
        _fail("min_per_kp", f"必须是 int（bool 不算），实际是 {type(min_per_kp).__name__}")
    if min_per_kp < 1:
        _fail("min_per_kp", f"必须 >= 1，实际是 {min_per_kp}")

    kp_list = []
    kp_set = set()
    for pos, kp_id in enumerate(_iterate(kp_ids, "kp_ids")):
        _check_id(kp_id, f"kp_ids[{pos}]")
        if kp_id in kp_set:
            _fail(f"kp_ids[{pos}]", f"清单内重复：{kp_id!r}")
        kp_set.add(kp_id)
        kp_list.append(kp_id)

    counts_by_kp = {kp_id: 0 for kp_id in kp_list}
    signatures_by_kp = {kp_id: [] for kp_id in kp_list}
    seen_entry_ids = set()
    total = 0

    for pos, entry in enumerate(_iterate(entries, "entries")):
        where = f"entries[{pos}]"
        entry_id = _check_id(getattr(entry, "id", None), f"{where}.id")
        if entry_id in seen_entry_ids:
            _fail(f"{where}.id", f"跨输入全局重复：{entry_id!r}")
        seen_entry_ids.add(entry_id)

        kp_id = _check_id(getattr(entry, "kp_id", None), f"{where}.kp_id")
        if kp_id not in kp_set:
            _fail(f"{where}.kp_id", f"引用未知 KP：{kp_id!r}")

        raw_signature = getattr(entry, "signature", _MISSING)
        if raw_signature is _MISSING:
            signature = ()
        else:
            try:
                signature = tuple(raw_signature)
            except TypeError as exc:
                # spec §7：该边界不在契约保证内；此处并入统一异常类型。
                raise MisconceptionCoverageError(
                    f"{where}.signature 必须可被 tuple() 化"
                ) from exc
            if not signature:
                _fail(f"{where}.signature", "tuple() 化后不得为空")

        known = signatures_by_kp[kp_id]
        for pattern in signature:
            if pattern in known:
                _fail(f"{where}.signature", f"KP {kp_id!r} 内 signature 跨条目重复：{pattern!r}")
            known.append(pattern)

        counts_by_kp[kp_id] += 1
        total += 1

    exempt_set = set()
    for pos, exemption in enumerate(_iterate(exemptions, "exemptions")):
        where = f"exemptions[{pos}]"
        kp_id = _check_id(getattr(exemption, "kp_id", None), f"{where}.kp_id")
        if kp_id not in kp_set:
            _fail(f"{where}.kp_id", f"引用未知 KP：{kp_id!r}")
        if kp_id in exempt_set:
            _fail(f"{where}.kp_id", f"同一 KP 重复豁免：{kp_id!r}")
        if counts_by_kp[kp_id] > 0:
            _fail(f"{where}.kp_id", f"已存在误解条目的 KP 不得豁免：{kp_id!r}")
        exempt_set.add(kp_id)

    # 三个集合两两不交、并集 = KP 全集；顺序一律 KP 输入原序（spec I5 / I6）
    counts = tuple((kp_id, counts_by_kp[kp_id]) for kp_id in kp_list)
    exempt_kp_ids = tuple(kp_id for kp_id in kp_list if kp_id in exempt_set)
    covered_kp_ids = tuple(
        kp_id
        for kp_id in kp_list
        if kp_id not in exempt_set and counts_by_kp[kp_id] >= min_per_kp
    )
    deficient_kp_ids = tuple(
        kp_id
        for kp_id in kp_list
        if kp_id not in exempt_set and counts_by_kp[kp_id] < min_per_kp
    )

    return MisconceptionReport(
        kp_ids=tuple(kp_list),
        counts=counts,
        deficient_kp_ids=deficient_kp_ids,
        exempt_kp_ids=exempt_kp_ids,
        covered_kp_ids=covered_kp_ids,
        min_per_kp=min_per_kp,
        total_misconceptions=total,
    )


def audit_dicts(kp_dicts, bank_data, min_per_kp=2):
    """knowledge json（KP dict 列表）× 误解库文件 dict 的便捷入口（spec §3.6）。

    绑定次序：先校验 ``kp_dicts``，再 ``parse_bank(bank_data)``（错误原样抛出），
    最后交 ``audit``（重复 KP id 由 audit 的重复检查抛）。
    """
    if not isinstance(kp_dicts, (list, tuple)):
        _fail("kp_dicts", f"必须是 list 或 tuple，实际是 {type(kp_dicts).__name__}")

    kp_list = []
    for pos, kp_dict in enumerate(kp_dicts):
        where = f"kp_dicts[{pos}]"
        if not isinstance(kp_dict, dict):
            _fail(where, f"必须是 dict，实际是 {type(kp_dict).__name__}")
        kp_list.append(_check_id(kp_dict.get("id"), f"{where}.id"))

    entries, exemptions = parse_bank(bank_data)
    return audit(kp_list, entries, exemptions, min_per_kp=min_per_kp)
