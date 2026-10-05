"""xuexing.asr_answer —— 口述作答确定性内核（第三波契约盲重写）。

纯函数模块：无 IO、无随机、无时钟、无环境读取、无全局可变状态；不引用任何
标准库或其他包内模块（client 与 grader 均为注入鸭子参数）。唯一外部效果是
守卫全过后恰好一次注入的 ``client.asr`` 调用。抽取全程只做字符串操作，
不对答案做任何数值求值。
"""

ASR_VERSION = "1"

DEFAULT_FILENAME = "audio.wav"

# clean_transcript 的上下缘可剥离字符集合（全角折叠之后的形态）；只做成员判断。
EDGE_CHARS = frozenset("\"'“”‘’。，、…·.,;:!?()嗯呃唉哦噢喔吧了呢啦咯嘛呀哈啊")

# 句首引导语词表：值与顺序都冻结，长度非增序 ⇒ 表序首个前缀命中即最长前缀命中。
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

# 口语算符 → 数学符号映射表：值与顺序都冻结，表序 = 前缀最长优先；
# 「除」单词不入表（歧义大，不透传转换，逐字符透传）。
SPOKEN_OPERATORS = (
    ("等于", "="),
    ("乘以", "*"),
    ("除以", "/"),
    ("乘", "*"),
    ("加", "+"),
    ("减", "-"),
)


class ASRError(ValueError):
    """本模块唯一异常类型（ValueError 的直接子类）。"""


# ------------------------------------------------------------ 转写清洗 --


def _fold_fullwidth(text):
    """全角折叠：码点 [0xFF01, 0xFF5E] → 半角；U+3000 → 半角空格；其余原样。

    只做折叠：不做内部空白折叠、不做尾部剥离、不处理千分位逗号、不小写化。
    """
    out = []
    for ch in text:
        cp = ord(ch)
        if 0xFF01 <= cp <= 0xFF5E:
            out.append(chr(cp - 0xFEE0))
        elif cp == 0x3000:
            out.append(" ")
        else:
            out.append(ch)
    return "".join(out)


def _strip_edges(s):
    """剥上下缘：左端、右端各剥一段连续的 EDGE_CHARS 成员，不接触内部。"""
    begin = 0
    end = len(s)
    while begin < end and s[begin] in EDGE_CHARS:
        begin += 1
    while end > begin and s[end - 1] in EDGE_CHARS:
        end -= 1
    return s[begin:end]


def _strip_one_head_filler(s):
    """只剥一个句首引导语：按 HEAD_FILLERS 表序遍历，首个前缀命中即剥。"""
    for filler in HEAD_FILLERS:
        if s.startswith(filler):
            return s[len(filler):]
    return s


def clean_transcript(text):
    """ASR 转写文本 → 清洗后的口语串。

    冻结流程（顺序为绑定条款）：非 str 入参抛 ASRError → 全角折叠 →
    首尾空白剥离（仅一次）→ 循环到不动点（剥上下缘 → 剥一个句首引导语 →
    再剥上下缘）。引导语只在头部剥、标点只在上下缘剥，核心内容不被触碰。
    """
    if not isinstance(text, str):
        raise ASRError(f"clean_transcript expects str, got {type(text).__name__}")
    s = _fold_fullwidth(text).strip()
    while True:
        before = s
        s = _strip_edges(s)
        s = _strip_one_head_filler(s)
        s = _strip_edges(s)
        if s == before:
            return s


# ------------------------------------------------- 口语数字 → 数学记号 --

_ASCII_DIGITS = "0123456789"
_ZERO_CHARS = frozenset("零〇")
_DIGIT_CHARS = {
    "零": "0",
    "〇": "0",
    "一": "1",
    "二": "2",
    "两": "2",
    "三": "3",
    "四": "4",
    "五": "5",
    "六": "6",
    "七": "7",
    "八": "8",
    "九": "9",
    "0": "0",
    "1": "1",
    "2": "2",
    "3": "3",
    "4": "4",
    "5": "5",
    "6": "6",
    "7": "7",
    "8": "8",
    "9": "9",
}
# 段内单位 → 段内位 rank（千=3、百=2、十=1；个位为 0）。
_UNIT_POSITIONS = {"十": 1, "百": 2, "千": 3}


def _parse_segment(s, i):
    """解析一段（不含 万/亿）的口语整数 → (数字串, 结束下标)；不命中 → None。

    显式单位文法（不约算）：数字字符按位累积；十/百/千 为段内单位，缺系数
    按 1；零 作占位；一百五 = 105。ASCII 数字串整体照抄。
    """
    n = len(s)
    if i < n and s[i] in _ASCII_DIGITS:
        j = i
        while j < n and s[j] in _ASCII_DIGITS:
            j += 1
        return (s[i:j], j)
    slots = {}
    highest = None
    j = i
    consumed = False

    def place(rank, char):
        slots[rank] = char
        nonlocal highest
        if highest is None or rank > highest:
            highest = rank

    while j < n:
        ch = s[j]
        if ch in _UNIT_POSITIONS:
            place(_UNIT_POSITIONS[ch], "1")
            j += 1
            consumed = True
        elif ch in _ZERO_CHARS:
            place(0, "0")
            j += 1
            consumed = True
        elif ch in _DIGIT_CHARS:
            digit = _DIGIT_CHARS[ch]
            if j + 1 < n and s[j + 1] in _UNIT_POSITIONS:
                place(_UNIT_POSITIONS[s[j + 1]], digit)
                j += 2
            else:
                place(0, digit)
                j += 1
            consumed = True
        else:
            break
    if not consumed:
        return None
    digits = []
    p = highest
    while p >= 0:
        digits.append(slots.get(p, "0"))
        p -= 1
    return ("".join(digits), j)


def _parse_lower_groups(s, i):
    """解析 亿 之后的低位部分 [段 万] [段] → (8 位宽数字串, 结束下标)。"""
    r = _parse_segment(s, i)
    if r is None:
        return None
    high, j = r
    if j < len(s) and s[j] == "万":
        r2 = _parse_segment(s, j + 1)
        if r2 is None:
            return (high.rjust(4, "0") + "0000", j + 1)
        return (high.rjust(4, "0") + r2[0].rjust(4, "0"), r2[1])
    return ("0000" + high.rjust(4, "0"), j)


def _parse_integer(s, i):
    """解析口语整数（含 万/亿 大段单位，须有非零前值）→ (数字串, 结束下标)。"""
    r = _parse_segment(s, i)
    if r is None:
        return None
    value, j = r
    n = len(s)
    if j < n and s[j] == "亿":
        if value.strip("0") == "":
            return (value, j)
        r2 = _parse_lower_groups(s, j + 1)
        if r2 is None:
            return (value + "00000000", j + 1)
        return (value + r2[0], r2[1])
    if j < n and s[j] == "万":
        if value.strip("0") == "":
            return (value, j)
        r2 = _parse_segment(s, j + 1)
        if r2 is None:
            return (value + "0000", j + 1)
        return (value + r2[0].rjust(4, "0"), r2[1])
    return (value, j)


def _parse_frac_digits(s, i):
    """小数点后逐位数字（中数字与 ASCII 皆可，逐位照抄）→ 至少一位。"""
    out = []
    j = i
    n = len(s)
    while j < n and s[j] in _DIGIT_CHARS:
        out.append(_DIGIT_CHARS[s[j]])
        j += 1
    if not out:
        return None
    return ("".join(out), j)


def _parse_decimal(s, i):
    """整数 [点 逐位小数] → (数字串, 结束下标)；整数部分必需。"""
    r = _parse_integer(s, i)
    if r is None:
        return None
    value, j = r
    if j < len(s) and s[j] == "点":
        f = _parse_frac_digits(s, j + 1)
        if f is not None:
            return (value + "." + f[0], f[1])
    return (value, j)


def _parse_fraction(s, i):
    """分母 分之 分子 → (分子/分母, 结束下标)；分母为整数、分子可带小数。"""
    r = _parse_integer(s, i)
    if r is None:
        return None
    den, j = r
    if not s.startswith("分之", j):
        return None
    num = _parse_decimal(s, j + 2)
    if num is None:
        return None
    return (num[0] + "/" + den, num[1])


def _parse_number_core(s, i):
    """数表达式主体。内部优先级：百分之 → 又（带分数）→ 分之（分数）→ 整数/小数。

    百分之 后必须紧跟合法 整数[点小数]，否则整条百分数支不命中，回到
    段内单位读数（百 = 100）+ 后续逐字符透传。
    """
    n = len(s)
    if s.startswith("百分之", i):
        r = _parse_decimal(s, i + 3)
        if r is not None:
            return (r[0] + "%", r[1])
    r = _parse_integer(s, i)
    if r is None:
        return None
    value, j = r
    if j < n and s[j] == "点":
        f = _parse_frac_digits(s, j + 1)
        if f is not None:
            return (value + "." + f[0], f[1])
    if s.startswith("分之", j):
        num = _parse_decimal(s, j + 2)
        if num is not None:
            return (num[0] + "/" + value, num[1])
        return (value, j)
    if j < n and s[j] == "又":
        frac = _parse_fraction(s, j + 1)
        if frac is not None:
            return (value + " " + frac[0], frac[1])
        return (value, j)
    return (value, j)


def _parse_number(s, i):
    """「负」前缀（恰修饰一次）+ 数表达式主体；不命中 → None（孤立「负」透传）。"""
    if i < len(s) and s[i] == "负":
        r = _parse_number_core(s, i + 1)
        if r is None:
            return None
        return ("-" + r[0], r[1])
    return _parse_number_core(s, i)


def spoken_to_math(text):
    """口语串 → 数学记号串（逐位置扫描，不求值、不做全角折叠）。

    每个位置的优先级：数表达式（最大匹配）→ 口语算符（表序 = 最长优先）→
    当前字符原样透传。
    """
    if not isinstance(text, str):
        raise ASRError(f"spoken_to_math expects str, got {type(text).__name__}")
    out = []
    i = 0
    n = len(text)
    while i < n:
        r = _parse_number(text, i)
        if r is not None:
            out.append(r[0])
            i = r[1]
            continue
        hit = False
        for spoken, symbol in SPOKEN_OPERATORS:
            if text.startswith(spoken, i):
                out.append(symbol)
                i += len(spoken)
                hit = True
                break
        if not hit:
            out.append(text[i])
            i += 1
    return "".join(out)


# ---------------------------------------------------------- 抽取入口 --


def extract_answer(text):
    """ASR 转写文本 → 候选答案串；清洗后可抽取内容为空 → None（不伪造作答）。

    冻结管线：clean_transcript → spoken_to_math → str.strip() → 空则 None。
    只依赖转写文本，与题目无关。
    """
    if not isinstance(text, str):
        raise ASRError(f"extract_answer expects str, got {type(text).__name__}")
    answer = spoken_to_math(clean_transcript(text)).strip()
    if answer == "":
        return None
    return answer


# ---------------------------------------------------------- 管线入口 --


def asr_answer(audio, item, client, grader, *, filename=DEFAULT_FILENAME):
    """口述作答管线入口。

    守卫顺序冻结为 V1(client.asr 可调用) → V2(grader 可调用) →
    V3(audio 非空 bytes) → V4(filename 非空白 str)，任一失败抛 ASRError 且
    零出网、零判分。守卫全过后：恰好一次 client.asr(audio, filename=filename)，
    回写非 str 抛 ASRError（此时已出网一次、grader 不被调用）；随后
    grader(item, extract_answer(transcript)) 原样返回。client.asr / grader
    抛出的异常一律原样传播，本模块从不捕获、不包装、不改写异常链。
    """
    asr = getattr(client, "asr", None)
    if not callable(asr):
        raise ASRError("client must provide a callable asr()")
    if not callable(grader):
        raise ASRError("grader must be callable")
    if not isinstance(audio, bytes) or len(audio) == 0:
        raise ASRError(f"audio must be non-empty bytes, got {type(audio).__name__}")
    if not isinstance(filename, str) or filename.strip() == "":
        raise ASRError("filename must be a non-blank str")
    transcript = client.asr(audio, filename=filename)
    if not isinstance(transcript, str):
        raise ASRError(f"asr must return str, got {type(transcript).__name__}")
    return grader(item, extract_answer(transcript))
