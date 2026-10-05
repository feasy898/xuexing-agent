"""asr_answer —— 口述作答的确定性内核（契约：specs/frozen/asr_answer.spec.md，冻结 v1 第三波）。

设计要点（逐条对应冻结契约）：

* **纯函数**：四个公开函数无 IO、无随机、无时钟、不读环境。唯一的外部效果是
  ``asr_answer`` 中一次注入的 ``client.asr`` 调用。
* **不偷看题目**：``clean_transcript`` / ``spoken_to_math`` / ``extract_answer`` 的签名
  与行为都只依赖转写文本，与 ``item`` 无关。
* **不伪造作答**：清洗后可抽取内容为空时 ``extract_answer`` 返回 ``None``，
  ``asr_answer`` 据此调用 ``grader(item, None)``。
* **零 xuexing 依赖**：不 import 任何同包模块；``client`` / ``grader`` / ``item`` 都是
  注入的鸭子对象。
"""

__all__ = [
    "ASRError",
    "ASR_VERSION",
    "DEFAULT_FILENAME",
    "EDGE_CHARS",
    "HEAD_FILLERS",
    "SPOKEN_OPERATORS",
    "asr_answer",
    "clean_transcript",
    "extract_answer",
    "spoken_to_math",
]


class ASRError(ValueError):
    """本模块唯一异常类型（``ValueError`` 的直接子类）。"""


# --------------------------------------------------------------------------- #
# 3.1 常量：值、类型与顺序全部冻结
# --------------------------------------------------------------------------- #

ASR_VERSION = "1"
DEFAULT_FILENAME = "audio.wav"

# 上下缘可剥离字符集合：全角折叠**之后**的形态（标点 + 语气小词）。
# 集合语义——只做成员判断，实现不迭代本集合。
EDGE_CHARS = frozenset("\"'“”‘’。，、…·.,;:!?()嗯呃唉哦噢喔吧了呢啦咯嘛呀哈啊")

# 句首引导语词表：值与顺序都冻结；长度非增序 ⇒「表中首个前缀命中」即最长命中，
# 等长按表序决胜。注意 "答案是" 是三字引导语（答+案+是），剥它即连「是」一起剥掉。
HEAD_FILLERS = (
    "我认为答案是",
    "我觉得答案是",
    "我的答案是",
    "所以答案是",
    "我选的是",
    "答案等于",
    "答案是",
    "选的是",
    "答案",
    "选择",
    "所以",
    "我选",
    "等于",
    "就是",
    "答",
    "得",
    "选",
)

# 口语算符 → 数学符号：值与顺序冻结；表序即最长前缀优先（"乘以" 先于 "乘"）。
# "除" 单字不入表（"三除五" 歧义大，不透传也不转换）。
SPOKEN_OPERATORS = (
    ("等于", "="),
    ("乘以", "*"),
    ("除以", "/"),
    ("乘", "*"),
    ("加", "+"),
    ("减", "-"),
)


# --------------------------------------------------------------------------- #
# 口语数字文法（§3.3，闭式手算可复核）
# --------------------------------------------------------------------------- #

_DIGIT_VALUES = {
    "零": 0,
    "〇": 0,
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "0": 0,
    "1": 1,
    "2": 2,
    "3": 3,
    "4": 4,
    "5": 5,
    "6": 6,
    "7": 7,
    "8": 8,
    "9": 9,
}

# 段内单位：缺系数按 1。
_SMALL_UNITS = {"十": 10, "百": 100, "千": 1000}
# 大段单位：必须有非零前值；孤立「万/亿」不是数。
_BIG_UNITS = {"万": 10000, "亿": 100000000}

_DECIMAL_POINT = "点"
_PERCENT = "百分之"
_MIXED = "又"
_FRACTION = "分之"
_NEGATIVE = "负"

_SPAN = (0xFF01, 0xFF5E)
_SPAN_SHIFT = 0xFEE0
_IDEOGRAPHIC_SPACE = 0x3000


# --------------------------------------------------------------------------- #
# 内部读数器：统一返回 (串, 结束下标) 或 None
# --------------------------------------------------------------------------- #


def _read_int_prefix(s, i):
    """整数前缀：数字字符按位累积 + 段内单位 + 大段单位。显式单位文法，不约算。"""
    total = 0
    section = 0
    digit = 0
    j = i
    n = len(s)
    while j < n:
        ch = s[j]
        value = _DIGIT_VALUES.get(ch)
        if value is not None:
            digit = digit * 10 + value
            j += 1
            continue
        small = _SMALL_UNITS.get(ch)
        if small is not None:
            section += (digit if digit else 1) * small
            digit = 0
            j += 1
            continue
        big = _BIG_UNITS.get(ch)
        if big is not None:
            chunk = section + digit
            if chunk == 0:
                break  # 孤立「万/亿」不并入整数前缀，交给逐字符透传
            total += chunk * big
            section = 0
            digit = 0
            j += 1
            continue
        break
    if j == i:
        return None
    return str(total + section + digit), j


def _read_decimal(s, i):
    """整数/小数：`点` 之后逐位消费数字（末尾的零不折叠也不剥）。"""
    prefix = _read_int_prefix(s, i)
    if prefix is None:
        return None
    text, j = prefix
    if s[j:j + 1] == _DECIMAL_POINT:
        k = j + 1
        digits = []
        while k < len(s):
            value = _DIGIT_VALUES.get(s[k])
            if value is None:
                break
            digits.append(str(value))
            k += 1
        if digits:
            return text + "." + "".join(digits), k
        # 「点」后无数位：不吞掉「点」，回落到纯整数，由主循环透传。
    return text, j


def _read_fraction(s, i):
    """分数：<整数>分之<整数|小数> → "分子/分母"。"""
    denominator = _read_int_prefix(s, i)
    if denominator is None:
        return None
    den_text, j = denominator
    if s[j:j + len(_FRACTION)] != _FRACTION:
        return None
    numerator = _read_decimal(s, j + len(_FRACTION))
    if numerator is None:
        return None
    num_text, k = numerator
    return num_text + "/" + den_text, k


def _read_mixed(s, i):
    """带分数：<整数>又<分数> → "整数 分子/分母"（单个半角空格分隔）。"""
    whole = _read_int_prefix(s, i)
    if whole is None:
        return None
    whole_text, j = whole
    if s[j:j + len(_MIXED)] != _MIXED:
        return None
    fraction = _read_fraction(s, j + len(_MIXED))
    if fraction is None:
        return None
    frac_text, k = fraction
    return whole_text + " " + frac_text, k


def _read_number_core(s, i):
    """数表达式核心，优先级：百分之 → 又（带分数）→ 分之（分数）→ 整数/小数。"""
    if s.startswith(_PERCENT, i):
        value = _read_decimal(s, i + len(_PERCENT))
        if value is not None:
            return value[0] + "%", value[1]
    for reader in (_read_mixed, _read_fraction, _read_decimal):
        found = reader(s, i)
        if found is not None:
            return found
    return None


def _read_number(s, i):
    """数表达式：`负` 恰修饰一次——其后必须紧跟一个合法的数核心，否则「负」透传。"""
    if s.startswith(_NEGATIVE, i):
        core = _read_number_core(s, i + len(_NEGATIVE))
        if core is not None:
            return "-" + core[0], core[1]
    return _read_number_core(s, i)


def _read_operator(s, i):
    """口语算符：按表序取首个前缀命中（表序即最长优先）。"""
    for word, symbol in SPOKEN_OPERATORS:
        if s.startswith(word, i):
            return symbol, i + len(word)
    return None


# --------------------------------------------------------------------------- #
# 3.2 / 3.3 / 3.4 抽取三段管线
# --------------------------------------------------------------------------- #


def _fold_fullwidth(text):
    """全角折叠：码点 ∈ [0xFF01, 0xFF5E] → 半角，U+3000 → 半角空格，其余原样。"""
    out = []
    for ch in text:
        cp = ord(ch)
        if _SPAN[0] <= cp <= _SPAN[1]:
            out.append(chr(cp - _SPAN_SHIFT))
        elif cp == _IDEOGRAPHIC_SPACE:
            out.append(" ")
        else:
            out.append(ch)
    return "".join(out)


def _strip_edges(s):
    """剥上下缘：两侧各剥一段连续的 EDGE_CHARS 成员，不接触内部。"""
    start = 0
    end = len(s)
    while start < end and s[start] in EDGE_CHARS:
        start += 1
    while end > start and s[end - 1] in EDGE_CHARS:
        end -= 1
    return s[start:end]


def _strip_head_filler(s):
    """只剥一个句首引导语：表序首个前缀命中即剥（长度非增 ⇒ 最长命中）。"""
    for filler in HEAD_FILLERS:
        if s.startswith(filler):
            return s[len(filler):]
    return s


def clean_transcript(text):
    """ASR 转写文本 → 清洗后的口语串（全角折叠 + 首尾剥离 + 剥引导语至不动点）。"""
    if not isinstance(text, str):
        raise ASRError("text must be a str, got {}".format(type(text).__name__))
    s = _fold_fullwidth(text).strip()
    while True:
        previous = s
        s = _strip_edges(s)
        s = _strip_head_filler(s)
        s = _strip_edges(s)
        if s == previous:
            return s


def spoken_to_math(text):
    """口语串 → 数学记号串（逐位置扫描：数表达式 > 口语算符 > 单字符透传，不求值）。"""
    if not isinstance(text, str):
        raise ASRError("text must be a str, got {}".format(type(text).__name__))
    out = []
    i = 0
    n = len(text)
    while i < n:
        number = _read_number(text, i)
        if number is not None:
            out.append(number[0])
            i = number[1]
            continue
        operator = _read_operator(text, i)
        if operator is not None:
            out.append(operator[0])
            i = operator[1]
            continue
        out.append(text[i])
        i += 1
    return "".join(out)


def extract_answer(text):
    """ASR 转写文本 → 候选答案串；清洗后可抽取内容为空则返回 ``None``（不伪造作答）。"""
    if not isinstance(text, str):
        raise ASRError("text must be a str, got {}".format(type(text).__name__))
    answer = spoken_to_math(clean_transcript(text)).strip()
    return answer if answer else None


# --------------------------------------------------------------------------- #
# 3.5 管线入口
# --------------------------------------------------------------------------- #


def asr_answer(audio, item, client, grader, *, filename=DEFAULT_FILENAME):
    """口述作答管线：守卫 V1→V2→V3→V4 → 恰好一次 ``client.asr`` → 抽取 → 交 grader。"""
    asr = getattr(client, "asr", None)
    if not callable(asr):  # V1
        raise ASRError("client must provide a callable asr()")
    if not callable(grader):  # V2
        raise ASRError("grader must be callable")
    if not isinstance(audio, bytes) or len(audio) == 0:  # V3
        raise ASRError("audio must be non-empty bytes, got {}".format(type(audio).__name__))
    if not isinstance(filename, str) or filename.strip() == "":  # V4
        raise ASRError("filename must be a non-blank str")

    transcript = asr(audio, filename=filename)  # 恰好一次出网，audio 原样透传
    if not isinstance(transcript, str):
        raise ASRError("client.asr must return a str transcript, got {}".format(
            type(transcript).__name__))

    return grader(item, extract_answer(transcript))
