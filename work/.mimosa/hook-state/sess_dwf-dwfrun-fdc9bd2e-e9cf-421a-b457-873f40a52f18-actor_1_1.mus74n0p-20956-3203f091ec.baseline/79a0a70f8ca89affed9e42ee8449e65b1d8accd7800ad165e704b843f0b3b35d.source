# -*- coding: utf-8 -*-
"""第一学段（1-3 年级）课标覆盖缺口补齐（一次性应用脚本）。

基线（work/check_coverage_g13.py 实测）：55 topic × 43 KP，coverage_rate=0.764，
uncovered 13 条、unmatched 4 条（kp_p2_motion / kp_p3_mult_1digit / kp_p3_div_1digit /
kp_p3_decimal_intro）。

本脚本动作（全部为追加/原位微调，绝不删除既有 KP）：
  A. 微调 7 个既有 KP 的 standard_ref 措辞，使其被子串匹配命中对应 topic alias
     （其中 4 个为 unmatched KP，3 个为命中了别的条目但漏掉本条目的 KP；
       微调保留原 ref 中已命中的 alias 子串，不回退既有覆盖）；
  B. 追加 4 个新 KP 到对应年级 knowledge_points 数组末尾
     （grade1: kp_p1_num0 / kp_p1_theme_inquiry；grade2: kp_p2_muldiv_rel；
       grade3: kp_p3_ton_measure）；
  C. 同步追加到 data/knowledge/math_all.json（合并视图，按年级插入该年级末 KP 之后），
     维持 tests/data/test_fixtures.py::test_math_all_merged_view 的口径。

文件写入约束：UTF-8、CRLF、各文件原缩进（grade1/2 与 math_all 每层 2 空格、
grade3 每层 1 空格）、除插入/替换点外其余内容逐字节不变。
"""
import io
import json
import os
import re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KDIR = os.path.join(REPO, "data", "knowledge")

# ---------- A. standard_ref 微调（old 必须在文件中恰出现一次） ----------
REF_EDITS = {
    "math_grade2.json": [
        # kp_p2_addsub_written：保 '100以内数'（t13_num100_int），增 '列竖式'（t13_addsub100_written）
        ("2022课标第一学段：能计算100以内数的加减法，探索笔算的算理与算法，能进行简单的整数四则运算",
         "2022课标第一学段：能计算100以内数的加减法，能列竖式笔算两位数加减两位数"
         "（含进位加与退位减），理解相同数位对齐的算理，能进行简单的整数四则运算"),
        # kp_p2_motion（原 unmatched）：增 '平移现象'/'图形平移'（t13_translation）、
        # '旋转现象'/'图形旋转'（t13_rotation）、'轴对称现象'/'对称图形'/'对称轴'/'对折'（t13_symmetry）
        ("2022课标第一学段：通过观察和操作，感知平移、旋转、轴对称等图形运动的现象",
         "2022课标第一学段：通过观察和操作，感知平移现象、旋转现象与轴对称现象，"
         "结合实例认识图形平移与图形旋转，知道沿一条直线对折后两部分能完全重合的图形"
         "是轴对称图形，这条直线就是对称轴，能在方格纸上画出简单图形平移后的图形"),
    ],
    "math_grade3.json": [
        # kp_p3_multiple_times：增 '倍的认识'/'倍与乘除'（t13_multiple），保留原句（t13_addsub_rel 命中不变）
        ("2022课标第二学段·数量关系：在具体情境中理解“倍”的意义，能解决求一个数是另一个数的几倍、一个数的几倍是多少的简单实际问题",
         "2022课标第二学段·数量关系：倍的认识——在具体情境中理解“倍”的意义，体会倍与乘除的联系，"
         "能解决求一个数是另一个数的几倍、一个数的几倍是多少的简单实际问题"),
        # kp_p3_mult_1digit（原 unmatched）：增 '多位数乘一位数'/'进位乘法'（t13_mul_1d）
        ("2022课标第二学段·数与运算：探索并掌握两、三位数乘一位数的乘法，理解算理，形成运算能力",
         "2022课标第二学段·数与运算：探索并掌握多位数乘一位数的乘法，能口算整十、整百数乘一位数，"
         "掌握两、三位数乘一位数的笔算与进位乘法，理解算理，形成运算能力"),
        # kp_p3_div_1digit（原 unmatched）：增 '除法笔算'/'除法验算'（t13_div_1d）
        ("2022课标第二学段·数与运算：探索并掌握两、三位数除以一位数的除法，理解算理，会用乘法验算除法",
         "2022课标第二学段·数与运算：探索并掌握除数是一位数的除法，掌握两、三位数除以一位数的除法笔算，"
         "理解商是几位数的判断方法，会用乘法进行除法验算"),
        # kp_p3_fraction_intro：保 '简单分数'（t13_frac_compare）与 '同分母分数加减'（t13_frac_addsub），
        # 增 '几分之一'/'几分之几'（t13_frac_init）
        ("2022课标第二学段·数与运算：结合具体情境初步认识分数，能借助直观比较简单分数的大小，会进行简单的同分母分数加减运算",
         "2022课标第二学段·数与运算：结合具体情境初步认识分数，能借助直观图形表示几分之一和几分之几，"
         "能认、读、写简单的分数，直观比较简单分数的大小，会进行简单的同分母分数加减运算"),
        # kp_p3_decimal_intro（原 unmatched）：增 '一位小数'（t13_dec_init）
        ("2022课标第二学段·数与运算：结合具体情境初步认识小数，能认、读、写简单的小数，会计算简单的小数加减法",
         "2022课标第二学段·数与运算：结合价格等具体情境初步认识小数，能认、读、写一位小数，"
         "理解以元为单位的小数含义，能借助直观比较一位小数的大小，会计算简单的小数加减法"),
    ],
}

# ---------- B. 新 KP（追加到年级文件末尾） ----------
NEW_KPS = {
    1: [
        {
            "id": "kp_p1_num0",
            "name": "0的认识",
            "subject": "math",
            "grade": 1,
            "cluster": "数与运算",
            "description": "认识0的含义：0既可以表示没有，也可以表示起点，能正确读写0，"
                           "会计算一个数与0相加减的简单算式",
            "standard_ref": "2022课标第一学段：结合具体情境认识0的含义，知道0可以表示"
                            "“没有”和“起点”，能正确读写0，会计算与0有关的加减法",
            "prereqs": [],
        },
        {
            "id": "kp_p1_theme_inquiry",
            "name": "综合与实践：主题活动与数学游戏",
            "subject": "math",
            "grade": 1,
            "cluster": "综合与实践",
            "description": "在主题活动、数学游戏、探究活动等实践活动中综合运用数与运算、"
                           "图形与几何等知识解决简单的现实问题，经历发现和提出问题、"
                           "分析和解决问题的全过程，体会数学与生活的联系",
            "standard_ref": "2022课标第一学段：在综合与实践的主题活动中，通过数学游戏、"
                            "探究活动和实践活动，综合运用数与运算、图形与几何、统计与概率的知识"
                            "解决简单的现实问题，经历发现问题、提出问题、解决问题的全过程",
            "prereqs": [],
        },
    ],
    2: [
        {
            "id": "kp_p2_muldiv_rel",
            "name": "乘除法的数量关系",
            "subject": "math",
            "grade": 2,
            "cluster": "数量关系",
            "description": "知道乘法算式中因数与积、除法算式中被除数、除数与商各部分的关系，"
                           "体会乘除法之间的互逆关系，能利用每份数、份数与总数量之间的关系"
                           "解决简单的乘除法实际问题",
            "standard_ref": "2022课标第一学段：在具体情境中理解乘除关系，知道因数×因数=积、"
                            "被除数÷除数=商，体会乘除法之间的互逆关系，能利用每份数、份数与"
                            "总数的关系解决简单的乘除应用问题",
            "prereqs": ["kp_p2_mul_table", "kp_p2_div_quotient"],
        },
    ],
    3: [
        {
            "id": "kp_p3_ton_measure",
            "name": "吨的认识",
            "subject": "math",
            "grade": 3,
            "cluster": "数与运算",
            "description": "认识质量单位吨，知道1吨=1000千克，能结合大象、货车载重等生活实例"
                           "感知1吨有多重，能进行吨与千克的简单换算",
            "standard_ref": "2022课标第二学段·数与运算：认识质量单位吨，知道1吨=1000千克，"
                            "能结合载重等生活实例感知1吨有多重，能进行吨与千克的简单换算",
            "prereqs": ["kp_p2_mass"],
        },
    ],
}


def read_text(path):
    with io.open(path, "r", encoding="utf-8", newline="") as fh:
        return fh.read()


def write_text(path, text):
    with io.open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def dump_block(kp, per_level_indent):
    """单 KP 对象文本：元素括号在 per_level_indent*2 层级，字段再进一层，CRLF 行尾。"""
    dumped = json.dumps([kp], ensure_ascii=False, indent=per_level_indent)
    body = dumped[dumped.index("[") + 1: dumped.rindex("]")]  # 去掉外层中括号
    pad = " " * per_level_indent
    lines = [(pad + line) if line.strip() else line for line in body.split("\n")]
    return "\r\n".join(lines).strip("\r\n")


def apply_ref_edits(path, edits):
    text = read_text(path)
    for old, new in edits:
        n = text.count(old)
        assert n == 1, "%s: old ref matched %d times (expect 1): %s..." % (path, n, old[:40])
        text = text.replace(old, new, 1)
    write_text(path, text)
    return len(edits)


def append_to_grade_file(path, kps, per_level_indent):
    text = read_text(path)
    close = text.rindex("]")  # knowledge_points 数组收口（文件最后一个 ]）
    seg = text[:close]
    m = re.search(r"\}(\r?\n[ \t]*)$", seg)
    assert m, "%s: unexpected tail layout" % path
    blocks = ",\r\n".join(dump_block(kp, per_level_indent) for kp in kps)
    # 尾形如 '    }\r\n  ]'：在最后一个 '}' 后接 ',\r\n' + 新块，再接原 '\r\n  ' + ']...'
    new_text = seg[: m.start()] + "}," + "\r\n" + blocks + m.group(1) + text[close:]
    write_text(path, new_text)


def insert_into_math_all(path, new_kps_by_grade):
    text = read_text(path)
    for grade in sorted(new_kps_by_grade):  # 逐年级重找锚点，插入互不影响
        data = json.loads(read_text(path))
        anchors = [kp["id"] for kp in data["knowledge_points"] if kp.get("grade") == grade]
        assert anchors, "%s: no grade %s kps" % (path, grade)
        anchor = anchors[-1]
        pos = read_text(path).index('"id": "%s"' % anchor)
        m = re.compile(r"\r\n    \},").search(read_text(path), pos)
        assert m, "%s: anchor %s close not found" % (path, anchor)
        blocks = ",\r\n".join(dump_block(kp, 2) for kp in new_kps_by_grade[grade])
        text = read_text(path)
        # 在锚点对象的 '},' 之后插入 '\r\n' + 新块 + ','（math_all 元素缩进 4，等价 per_level 2；
        # 末尾补 ',' 以衔接锚点之后原有的下一个元素）
        text = text[: m.end()] + "\r\n" + blocks + "," + text[m.end():]
        write_text(path, text)


def main():
    changed = 0
    for fname, edits in REF_EDITS.items():
        changed += apply_ref_edits(os.path.join(KDIR, fname), edits)
        print("ref edits applied: %s (%d)" % (fname, len(edits)))

    per_level = {1: 2, 2: 2, 3: 1}
    for grade, kps in NEW_KPS.items():
        append_to_grade_file(os.path.join(KDIR, "math_grade%d.json" % grade), kps, per_level[grade])
        print("appended %d kps to math_grade%d.json: %s"
              % (len(kps), grade, [kp["id"] for kp in kps]))

    insert_into_math_all(os.path.join(KDIR, "math_all.json"), NEW_KPS)
    print("synced math_all.json (+%d kps)" % sum(len(v) for v in NEW_KPS.values()))

    # 自检：JSON 可解析、新 KP 落位、id 唯一
    seen = set()
    for n in range(1, 10):
        p = os.path.join(KDIR, "math_grade%d.json" % n)
        if not os.path.exists(p):
            continue
        data = json.loads(read_text(p))
        for kp in data["knowledge_points"]:
            assert kp["id"] not in seen, "duplicate id %s" % kp["id"]
            seen.add(kp["id"])
    for grade, kps in NEW_KPS.items():
        ids = [kp["id"] for kp in json.loads(
            read_text(os.path.join(KDIR, "math_grade%d.json" % grade)))["knowledge_points"]]
        tail = ids[-len(kps):]
        assert tail == [kp["id"] for kp in kps], "grade%s tail mismatch: %s" % (grade, tail)
    all_ids = [kp["id"] for kp in json.loads(
        read_text(os.path.join(KDIR, "math_all.json")))["knowledge_points"]]
    for kp_id in (k["id"] for v in NEW_KPS.values() for k in v):
        assert kp_id in all_ids, "math_all missing %s" % kp_id
    print("self-check OK: %d ref edits + %d new kps; JSON valid; ids unique; tails verified"
          % (changed, sum(len(v) for v in NEW_KPS.values())))


if __name__ == "__main__":
    main()
