"""课标覆盖检查器（契约：specs/frozen/standard_coverage.spec.md）。

把知识点的 ``standard_ref`` 与课标主题清单（``domains -> themes -> topics``
三层结构，每个条目携带 ``aliases`` 检索关键词）做**纯子串**对照，产出双向缺口：

* 覆盖缺口 ``uncovered_topic_ids``：清单中没有任何 KP 命中的条目；
* 归属缺口 ``unmatched_kp_ids``：``standard_ref`` 归属不到任何条目的 KP。

本模块是纯函数模块：无文件/网络 IO、无随机、无系统时钟、无环境读取、
无全局可变状态；同输入同输出。条目侧输出恒按清单原序，KP 侧输出恒按输入原序。

依赖约束（契约 §2）：唯一 import 是标准库 ``dataclasses``；**不 import**
``xuexing.types`` 或任何其他 xuexing 模块——KP 一律按鸭子类型只读 ``.id`` 与
``.standard_ref``。禁止相对导入；注解一律直写真实对象（不使用 PEP 563 注解延迟
求值，否则注入门装载下 dataclass 解析会失败）。
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
    """清单或 KP 数据非法时抛出；本模块唯一异常类型。"""


@dataclass
class Topic:
    """课标条目（topic 层的扁平化记录，``domain``/``theme`` 由层级注入）。"""

    id: str
    name: str
    domain: str
    theme: str
    requirement: str
    aliases: tuple


@dataclass
class KPMatch:
    """单个 KP 的归属结果：命中的条目 id（清单原序、条目内去重）。"""

    kp_id: str
    topic_ids: tuple


@dataclass
class CoverageReport:
    """双向缺口对照报告；六个字段均为 tuple（不可变）。"""

    topics: tuple
    matches: tuple
    uncovered_topic_ids: tuple
    unmatched_kp_ids: tuple
    matched_kp_ids: tuple
    covered_topic_ids: tuple

    @property
    def coverage_rate(self) -> float:
        """条目级覆盖率 = 被覆盖条目数 / 条目总数（IEEE 754 除法唯一结果）。"""
        return len(self.covered_topic_ids) / len(self.topics)

    def is_complete(self) -> bool:
        """双向均无缺口时为 True。"""
        return not self.uncovered_topic_ids and not self.unmatched_kp_ids


class _KPRef:
    """``check_coverage_dicts`` 的鸭子适配器：只提供 ``.id`` 与 ``.standard_ref``。"""

    __slots__ = ("id", "standard_ref")

    def __init__(self, kp_id, standard_ref):
        self.id = kp_id
        self.standard_ref = standard_ref


def _require_text(container, key, what):
    """取 ``container[key]`` 并校验为非空白字符串；**不做 strip**，原值返回。"""
    if key not in container:
        raise StandardCoverageError("%s: missing key %r" % (what, key))
    value = container[key]
    if not isinstance(value, str) or value.strip() == "":
        raise StandardCoverageError(
            "%s: key %r must be a non-blank string" % (what, key)
        )
    return value


def parse_topics(data):
    """解析课标主题清单 dict，返回拍平后的 ``Topic`` 列表。

    拍平序 = domains 原序 -> themes 原序 -> topics 原序（深度优先，不排序、
    不去重、不跨层归并）。不改输入；同输入两次解析结果逐字段相等。
    """
    if not isinstance(data, dict):
        raise StandardCoverageError("topics data must be a dict")
    domains = data.get("domains")
    if not isinstance(domains, list) or not domains:
        raise StandardCoverageError("topics data: 'domains' must be a non-empty list")

    topics = []
    seen_ids = set()
    seen_aliases = set()
    for domain in domains:
        if not isinstance(domain, dict):
            raise StandardCoverageError("each domain entry must be a dict")
        domain_name = _require_text(domain, "domain", "domain entry")
        themes = domain.get("themes")
        if not isinstance(themes, list) or not themes:
            raise StandardCoverageError(
                "domain %r: 'themes' must be a non-empty list" % (domain_name,)
            )
        for theme in themes:
            if not isinstance(theme, dict):
                raise StandardCoverageError(
                    "domain %r: each theme entry must be a dict" % (domain_name,)
                )
            theme_name = _require_text(theme, "theme", "theme entry")
            topic_list = theme.get("topics")
            if not isinstance(topic_list, list) or not topic_list:
                raise StandardCoverageError(
                    "theme %r/%r: 'topics' must be a non-empty list"
                    % (domain_name, theme_name)
                )
            for topic in topic_list:
                if not isinstance(topic, dict):
                    raise StandardCoverageError(
                        "theme %r/%r: each topic entry must be a dict"
                        % (domain_name, theme_name)
                    )
                where = "topic in theme %r/%r" % (domain_name, theme_name)
                topic_id = _require_text(topic, "id", where)
                name = _require_text(topic, "name", where)
                requirement = _require_text(topic, "requirement", where)
                if topic_id in seen_ids:
                    raise StandardCoverageError(
                        "duplicate topic id %r (topic ids must be globally unique)"
                        % (topic_id,)
                    )
                raw_aliases = topic.get("aliases")
                if not isinstance(raw_aliases, list) or not raw_aliases:
                    raise StandardCoverageError(
                        "topic %r: 'aliases' must be a non-empty list" % (topic_id,)
                    )
                aliases = []
                for alias in raw_aliases:
                    if (
                        not isinstance(alias, str)
                        or alias.strip() == ""
                        or alias != alias.strip()
                    ):
                        raise StandardCoverageError(
                            "topic %r: every alias must be a non-blank string "
                            "without leading/trailing whitespace" % (topic_id,)
                        )
                    if alias in seen_aliases:
                        raise StandardCoverageError(
                            "duplicate alias %r (aliases must be globally unique)"
                            % (alias,)
                        )
                    seen_aliases.add(alias)
                    aliases.append(alias)
                seen_ids.add(topic_id)
                topics.append(
                    Topic(
                        topic_id,
                        name,
                        domain_name,
                        theme_name,
                        requirement,
                        tuple(aliases),
                    )
                )
    return topics


def match_ref(ref, topics):
    """单个 ``standard_ref`` 的归属：命中条目 id 元组（清单原序、条目内去重）。

    命中判据：条目任一 alias 是 ``ref`` 的连续子串（``alias in ref``，
    大小写敏感、不做归一化/分词/模糊化）。
    """
    topic_list = list(topics)
    if not topic_list:
        raise StandardCoverageError("topics must be a non-empty sequence")
    if ref is None:
        return ()
    if not isinstance(ref, str):
        raise StandardCoverageError(
            "standard_ref must be a str or None, got %s" % (type(ref).__name__,)
        )
    if ref.strip() == "":
        return ()
    hits = []
    for topic in topic_list:
        for alias in topic.aliases:
            if alias in ref:
                hits.append(topic.id)
                break
    return tuple(hits)


def check_coverage(kps, topics):
    """KP 对象序列 x 条目清单 -> :class:`CoverageReport`。

    KP 按鸭子类型只读 ``.id`` 与 ``.standard_ref``；缺属性时原生
    ``AttributeError`` 传播（不包装）。不改入参。
    """
    topic_list = list(topics)
    if not topic_list:
        raise StandardCoverageError("topics must be a non-empty sequence")
    kp_list = list(kps)

    matches = []
    matched_kp_ids = []
    unmatched_kp_ids = []
    seen_ids = set()
    covered = set()
    for kp in kp_list:
        kp_id = kp.id
        if not isinstance(kp_id, str) or kp_id.strip() == "":
            raise StandardCoverageError(
                "kp.id must be a non-blank string, got %r" % (kp_id,)
            )
        if kp_id in seen_ids:
            raise StandardCoverageError("duplicate kp id %r" % (kp_id,))
        ref = kp.standard_ref
        if ref is None:
            ref = ""
        if not isinstance(ref, str):
            raise StandardCoverageError(
                "kp %r: standard_ref must be a str or None, got %s"
                % (kp_id, type(ref).__name__)
            )
        seen_ids.add(kp_id)
        topic_ids = match_ref(ref, topic_list)
        matches.append(KPMatch(kp_id, topic_ids))
        if topic_ids:
            matched_kp_ids.append(kp_id)
            covered.update(topic_ids)
        else:
            unmatched_kp_ids.append(kp_id)

    topic_ids_in_order = [topic.id for topic in topic_list]
    covered_topic_ids = tuple(tid for tid in topic_ids_in_order if tid in covered)
    uncovered_topic_ids = tuple(
        tid for tid in topic_ids_in_order if tid not in covered
    )
    return CoverageReport(
        tuple(topic_list),
        tuple(matches),
        uncovered_topic_ids,
        tuple(unmatched_kp_ids),
        tuple(matched_kp_ids),
        covered_topic_ids,
    )


def check_coverage_dicts(kp_dicts, topics_data):
    """knowledge json 形状的便捷入口：dict 列表 + 清单 dict -> :class:`CoverageReport`。

    等价于 ``check_coverage(kps, parse_topics(topics_data))``。
    """
    topics = parse_topics(topics_data)
    if not isinstance(kp_dicts, (list, tuple)):
        raise StandardCoverageError(
            "kp_dicts must be a list or tuple, got %s" % (type(kp_dicts).__name__,)
        )
    adapted = []
    for entry in kp_dicts:
        if not isinstance(entry, dict):
            raise StandardCoverageError(
                "each kp_dict entry must be a dict, got %s" % (type(entry).__name__,)
            )
        kp_id = entry.get("id")
        if not isinstance(kp_id, str) or kp_id.strip() == "":
            raise StandardCoverageError(
                "kp_dict entry must carry a non-blank string 'id', got %r" % (kp_id,)
            )
        adapted.append(_KPRef(kp_id, entry.get("standard_ref")))
    return check_coverage(adapted, topics)
