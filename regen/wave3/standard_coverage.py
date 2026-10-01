"""standard_coverage —— 课标覆盖检查器（契约盲重写实例）。

把知识点的 ``standard_ref`` 与课标主题清单（``domains → themes → topics`` 三层
结构，每个条目携带 ``aliases`` 检索关键词）做对照，产出**双向缺口**：清单中没有
任何 KP 引用的条目（覆盖缺口）与 ``standard_ref`` 归属不到任何条目的 KP（归属
缺口），外加逐 KP 归属表与条目级覆盖率。

行为契约（specs/frozen/standard_coverage.spec.md，冻结 v1）：
- 纯子串匹配：条目任一 alias 是 ref 的连续子串即归属该条目（大小写敏感、
  不做任何归一化/分词/模糊化）。
- 双向缺口分划：matched/unmatched 与 covered/uncovered 各自完备且不相交。
- 确定性排序：条目类输出恒按清单原序，KP 类输出恒按输入原序。
- 全模块纯函数：无 IO、无随机、无时钟，同输入同输出。
"""

from dataclasses import dataclass

__all__ = [
    "StandardCoverageError",
    "Topic",
    "KPMatch",
    "CoverageReport",
    "parse_topics",
    "match_ref",
    "check_coverage",
    "check_coverage_dicts",
]


class StandardCoverageError(ValueError):
    """本模块唯一异常类型（ValueError 直接子类）；契约内一切校验失败都抛它。"""


@dataclass
class Topic:
    id: str
    name: str
    domain: str
    theme: str
    requirement: str
    aliases: tuple  # 检索关键词，非空 tuple


@dataclass
class KPMatch:
    kp_id: str
    topic_ids: tuple  # 清单原序、条目内去重后的命中条目 id


@dataclass
class CoverageReport:
    topics: tuple  # 输入清单的 Topic 对象元组（清单原序）
    matches: tuple  # 每 KP 恰一项，输入原序
    uncovered_topic_ids: tuple  # 无任何 KP 命中的条目 id（覆盖缺口），清单原序
    unmatched_kp_ids: tuple  # 零命中的 KP id（归属缺口），输入原序
    matched_kp_ids: tuple  # 有命中的 KP id，输入原序
    covered_topic_ids: tuple  # 被至少一个 KP 命中的条目 id，清单原序

    @property
    def coverage_rate(self) -> float:
        """len(covered_topic_ids) / len(topics)，IEEE 754 除法唯一结果。"""
        return len(self.covered_topic_ids) / len(self.topics)

    def is_complete(self) -> bool:
        """双向均无缺口时为 True；恒返回 bool。"""
        return not self.uncovered_topic_ids and not self.unmatched_kp_ids


def _is_nonblank_str(value) -> bool:
    """value 为 str 且 strip 后非空（不做 strip 透传，仅判定）。"""
    return isinstance(value, str) and value.strip() != ""


def _hit_ids(ref: str, topics) -> tuple:
    """ref 对清单的命中条目 id 元组：清单原序；条目任一 alias 是 ref 的连续
    子串即命中（大小写敏感），同条目多 alias 命中只记一次。"""
    return tuple(
        t.id for t in topics if any(alias in ref for alias in t.aliases)
    )


def _parse_topic(entry, domain_name, theme_name, seen_topic_ids, seen_aliases) -> Topic:
    """校验并拍平单个 topic 条目；任一校验失败抛 StandardCoverageError。"""
    if not isinstance(entry, dict):
        raise StandardCoverageError("每个 topic 必须是 dict")
    topic_id = entry.get("id")
    if not _is_nonblank_str(topic_id):
        raise StandardCoverageError("topic id 必须是非空白字符串")
    if topic_id in seen_topic_ids:
        raise StandardCoverageError(f"topic id 跨条目重复：{topic_id!r}")
    name = entry.get("name")
    if not _is_nonblank_str(name):
        raise StandardCoverageError("topic name 必须是非空白字符串")
    requirement = entry.get("requirement")
    if not _is_nonblank_str(requirement):
        raise StandardCoverageError("topic requirement 必须是非空白字符串")
    aliases = entry.get("aliases")
    if not isinstance(aliases, list) or not aliases:
        raise StandardCoverageError("aliases 必须是非空 list")
    alias_list = []
    for alias in aliases:
        if not isinstance(alias, str) or alias == "" or alias != alias.strip():
            raise StandardCoverageError(f"alias 必须是无首尾空白的非空字符串：{alias!r}")
        if alias in seen_aliases:
            raise StandardCoverageError(f"alias 跨条目重复：{alias!r}")
        seen_aliases.add(alias)
        alias_list.append(alias)
    seen_topic_ids.add(topic_id)
    return Topic(
        id=topic_id,
        name=name,
        domain=domain_name,
        theme=theme_name,
        requirement=requirement,
        aliases=tuple(alias_list),
    )


def parse_topics(data) -> list[Topic]:
    """解析课标主题清单 dict，返回拍平后的 Topic 列表。

    拍平序 = domains 原序 → themes 原序 → topics 原序（深度优先，不排序、
    不重排）。domain/theme 由所在层级注入；aliases list 转 tuple；
    其余字段原值透传（不做 strip）。纯函数：不改输入。
    """
    if not isinstance(data, dict):
        raise StandardCoverageError("课标清单 data 必须是 dict")
    domains = data.get("domains")
    if not isinstance(domains, list) or not domains:
        raise StandardCoverageError("domains 必须是非空 list")
    seen_topic_ids = set()
    seen_aliases = set()
    topics = []
    for domain_entry in domains:
        if not isinstance(domain_entry, dict):
            raise StandardCoverageError("每个 domain 必须是 dict")
        domain_name = domain_entry.get("domain")
        if not _is_nonblank_str(domain_name):
            raise StandardCoverageError("domain 名必须是非空白字符串")
        themes = domain_entry.get("themes")
        if not isinstance(themes, list) or not themes:
            raise StandardCoverageError("themes 必须是非空 list")
        for theme_entry in themes:
            if not isinstance(theme_entry, dict):
                raise StandardCoverageError("每个 theme 必须是 dict")
            theme_name = theme_entry.get("theme")
            if not _is_nonblank_str(theme_name):
                raise StandardCoverageError("theme 名必须是非空白字符串")
            topic_entries = theme_entry.get("topics")
            if not isinstance(topic_entries, list) or not topic_entries:
                raise StandardCoverageError("topics 必须是非空 list")
            for topic_entry in topic_entries:
                topics.append(
                    _parse_topic(
                        topic_entry, domain_name, theme_name,
                        seen_topic_ids, seen_aliases,
                    )
                )
    return topics


def match_ref(ref, topics) -> tuple[str, ...]:
    """单个 standard_ref 的归属：命中条目 id 元组（清单原序、条目内去重）。

    校验次序（绑定）：先查 topics 为空（先于 ref 一切检查）；ref is None →
    ()；ref 非 str → StandardCoverageError；ref 全空白 → ()。
    """
    if not topics:
        raise StandardCoverageError("条目清单 topics 不能为空")
    if ref is None:
        return ()
    if not isinstance(ref, str):
        raise StandardCoverageError(
            f"standard_ref 必须是 str 或 None，得到 {type(ref).__name__}"
        )
    if ref.strip() == "":
        return ()
    return _hit_ids(ref, topics)


def check_coverage(kps, topics) -> CoverageReport:
    """KP 对象序列 × 条目清单 → 对照报告。

    topics 为空先于任何 KP 检查抛 StandardCoverageError；kps 内部单遍物化为
    list（不可迭代 → 原生 TypeError 传播）。每个 KP 按鸭子类型只读 .id 与
    .standard_ref（缺属性 → 原生 AttributeError 传播）。逐 KP 校验按输入序
    遇首个非法即抛。不改入参。
    """
    if not topics:
        raise StandardCoverageError("条目清单 topics 不能为空")
    kp_list = list(kps)
    seen_kp_ids = set()
    matches = []
    matched_kp_ids = []
    unmatched_kp_ids = []
    covered = set()
    for kp in kp_list:
        kp_id = kp.id
        if not isinstance(kp_id, str) or kp_id.strip() == "":
            raise StandardCoverageError("kp.id 必须是非空白字符串")
        if kp_id in seen_kp_ids:
            raise StandardCoverageError(f"kp.id 重复：{kp_id!r}")
        seen_kp_ids.add(kp_id)
        ref = kp.standard_ref
        if ref is None:
            ref = ""
        elif not isinstance(ref, str):
            raise StandardCoverageError("kp.standard_ref 必须是 str 或 None")
        topic_ids = _hit_ids(ref, topics)
        matches.append(KPMatch(kp_id=kp_id, topic_ids=topic_ids))
        if topic_ids:
            matched_kp_ids.append(kp_id)
            covered.update(topic_ids)
        else:
            unmatched_kp_ids.append(kp_id)
    return CoverageReport(
        topics=tuple(topics),
        matches=tuple(matches),
        uncovered_topic_ids=tuple(t.id for t in topics if t.id not in covered),
        unmatched_kp_ids=tuple(unmatched_kp_ids),
        matched_kp_ids=tuple(matched_kp_ids),
        covered_topic_ids=tuple(t.id for t in topics if t.id in covered),
    )


class _KpView:
    """knowledge json 条目的鸭子接口适配（仅暴露 .id / .standard_ref）。"""

    __slots__ = ("id", "standard_ref")

    def __init__(self, kp_id, standard_ref) -> None:
        self.id = kp_id
        self.standard_ref = standard_ref


def check_coverage_dicts(kp_dicts, topics_data) -> CoverageReport:
    """knowledge json 形状的便捷入口。

    处理次序（绑定）：先 parse_topics(topics_data)（清单非法先抛，两者同时
    非法时清单错先抛）；再校验 kp_dicts 须为 list 或 tuple；逐条目校验
    dict 形态与非空白 str 的 id；``standard_ref`` 键可省略（缺省 = None = 空），
    其类型合法性交由 check_coverage 的 ref 校验；其余键忽略。
    """
    topics = parse_topics(topics_data)
    if not isinstance(kp_dicts, (list, tuple)):
        raise StandardCoverageError("kp_dicts 必须是 list 或 tuple")
    adapted = []
    for entry in kp_dicts:
        if not isinstance(entry, dict):
            raise StandardCoverageError("kp_dicts 每个条目必须是 dict")
        if "id" not in entry:
            raise StandardCoverageError("kp_dicts 条目缺少 id 键")
        entry_id = entry["id"]
        if not isinstance(entry_id, str) or entry_id.strip() == "":
            raise StandardCoverageError("kp_dicts 条目 id 必须是非空白字符串")
        adapted.append(_KpView(entry_id, entry.get("standard_ref")))
    return check_coverage(adapted, topics)
