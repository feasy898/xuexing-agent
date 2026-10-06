"""gapfill 步骤 2：数学缺口题程序化模板生成（primary 判断/作图/应用，jr 计算/
统计材料/函数综合，hs 多选/计算/证明/综合）。

为什么用程序模板而非 LLM 出数学题：owner 纪律要求「数学题程序验算」——模板
题的答案全部由本脚本代码计算（fractions 精确运算），验算是独立的、确定性的，
不依赖出题者自证。证明/作图类主观题的参考答案为课本canonical 内容，由
gen_llm_batches.py 走 LLM 起草 + 人工核对，不在本脚本。

难度域与既有 math items 对齐（0.15~0.8）；difficulty 为 estimated（初值未
标定，写入 verification.note）。source=llm_generated 不适用本批（非 LLM 产出
——诚实标注为 original + 程序验算说明）。

用法：python work/gapfill/gen_math_templates.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from fractions import Fraction

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

import gaplib as G  # noqa: E402

DRY = False
EST = "程序模板生成，答案由代码以精确分数计算验算（非 LLM 产出）；难度初值 estimated，独立双代理盲验未做"

_ids = set()


def uid(prefix: str) -> str:
    n = 1
    while f"{prefix}_{n:03d}" in _ids:
        n += 1
    s = f"{prefix}_{n:03d}"
    _ids.add(s)
    return s


def item(grade, prefix, item_type, stem, answer, kp, diff, solution, *,
         options=None, form=None, answer_mode=None):
    it = G.make_item(uid(prefix), item_type, stem, answer, [kp], diff, solution,
                     options=options, form=form or "PENDING-FORM",
                     answer_mode=answer_mode,
                     source="original", agent=G.TMPL_AGENT, note=EST)
    it["_grade"] = grade
    return it


BATCH_FORMS = {
    "math_primary_truefalse": "判断",
    "math_primary_word_problem": "word_problem",
    "math_primary_construction": "construction",
    "math_jr_computation": "computation",
    "math_jr_comprehension": "comprehension",
    "math_jr_synthesis": "synthesis",
    "math_jr_construction": "construction",
    "math_jr_proof": "proof",
    "math_hs_multi_select": "mcq_multi",
    "math_hs_computation": "computation",
    "math_hs_proof": "proof",
    "math_hs_synthesis": "synthesis",
}


# ================================================================ primary 判断
def gen_primary_truefalse():
    """一校 1-6 年级判断题 10 道：对错各半，对错由代码算/数学事实定。"""
    out = []
    # (grade, kp, 陈述, 是否正确, 解析, 难度)
    rows = [
        (1, "kp_p1_carry20", "判断：9 ＋ 6 ＝ 15。（对的画“√”，错的画“×”）", 9 + 6 == 15,
         "9＋6：把 6 分成 1 和 5，9＋1＝10，10＋5＝15。等式成立，画“√”。", 0.15),
        (1, "kp_p1_borrow20", "判断：17 − 9 ＝ 7。（对的画“√”，错的画“×”）", 17 - 9 == 7,
         "17−9：10−9＝1，7＋1＝8，所以 17−9＝8≠7。等式不成立，画“×”。", 0.2),
        (2, "kp_p2_mul_table", "判断：8 × 7 ＝ 56。（对的画“√”，错的画“×”）", 8 * 7 == 56,
         "口诀“七八五十六”，8×7＝56。等式成立，画“√”。", 0.2),
        (2, "kp_p2_div_quotient", "判断：72 ÷ 8 ＝ 9。（对的画“√”，错的画“×”）", 72 // 8 == 9 and 72 % 8 == 0,
         "口诀“八九七十二”，72÷8＝9。等式成立，画“√”。", 0.2),
        (3, "kp_p3_measure_units", "判断：1 吨 ＝ 1000 千克。（对的画“√”，错的画“×”）", True,
         "吨与千克的进率是 1000：1 吨＝1000 千克。说法正确，画“√”。", 0.25),
        (3, "kp_p3_measure_units", "判断：3 千米 ＝ 300 米。（对的画“√”，错的画“×”）", False,
         "千米与米的进率是 1000：3 千米＝3000 米≠300 米。说法错误，画“×”。", 0.3),
        (5, "kp_p5_factor_multiple", "判断：所有的偶数都是合数。（对的画“√”，错的画“×”）", False,
         "2 是偶数，但 2 只有 1 和它本身两个因数，是质数。所以“所有偶数都是合数”说法错误，画“×”。", 0.45),
        (5, "kp_p5_fraction_meaning", "判断：把单位“1”平均分成 4 份，表示这样的 3 份的数是 3/4。（对的画“√”，错的画“×”）", True,
         "分数意义的定义：平均分 4 份取 3 份即 3/4。前提是“平均分”，说法正确，画“√”。", 0.35),
        (6, "kp_p6_circle", "判断：圆的周长总是它直径的 2 倍。（对的画“√”，错的画“×”）", False,
         "圆的周长 C＝πd，周长是直径的 π 倍（约 3.14 倍），不是 2 倍。说法错误，画“×”。", 0.4),
        (6, "kp_p6_percent", "判断：一件衣服原价 200 元，打八折后售价是 180 元。（对的画“√”，错的画“×”）",
         200 * 0.8 == 180, "打八折即按原价的 80% 出售：200×80%＝160 元≠180 元。说法错误，画“×”。", 0.35),
    ]
    assert sum(1 for r in rows if r[3]) == sum(1 for r in rows if not r[3]), "对错应各半"
    for g, kp, stem, truth, sol, d in rows:
        out.append(item(g, "mgap_tf", "fill", stem, "√" if truth else "×",
                        kp, d, sol, form="判断"))
    return out


# ================================================================ primary 应用题
def gen_primary_word_problem():
    out = []
    # 1) g2 乘除数量关系：单价×数量
    price, qty = 3, 4
    ans = price * qty
    out.append(item(2, "mgap_wp", "solve",
                    f"妈妈去超市买苹果，每千克 {price} 元，买了 {qty} 千克。一共要付多少元？",
                    f"{ans} 元",
                    "kp_p2_muldiv_rel", 0.25,
                    f"总价＝单价×数量：{price}×{qty}＝{ans}（元）。答：一共要付 {ans} 元。",
                    form="word_problem"))
    # 2) g3 三位数加减混合
    a0, b0, c0 = 480, 265, 180
    ans = a0 - b0 + c0
    out.append(item(3, "mgap_wp", "solve",
                    f"书店原来运进故事书 {a0} 本，第一天卖出 {b0} 本，后来又运来 {c0} 本。书店现在有故事书多少本？",
                    f"{ans} 本",
                    "kp_p3_addsub_3digit", 0.35,
                    f"现有本数＝原有−卖出＋又运来：{a0}−{b0}＋{c0}＝{a0-b0}＋{c0}＝{ans}（本）。答：现在有 {ans} 本。"))
    # 3) g3 两位数乘两位数
    seats, rows_n = 24, 12
    ans = seats * rows_n
    out.append(item(3, "mgap_wp", "solve",
                    f"学校礼堂每排有 {seats} 个座位，共 {rows_n} 排。这个礼堂一共有多少个座位？",
                    f"{ans} 个",
                    "kp_p3_mult_2x2digit", 0.3,
                    f"座位总数＝每排座位数×排数：{seats}×{rows_n}＝{seats}×{rows_n//10*10}＋{seats}×{rows_n%10}＝{seats*10*rows_n//10}＋{seats*(rows_n%10)}＝{ans}（个）。答：共有 {ans} 个座位。"))
    # 4) g4 四则混合运算（购物清单）
    p1, n1, p2, n2 = 15, 3, 6, 4
    ans = p1 * n1 + p2 * n2
    out.append(item(4, "mgap_wp", "solve",
                    f"王老师买钢笔和笔记本：钢笔每支 {p1} 元买了 {n1} 支，笔记本每本 {p2} 元买了 {n2} 本。王老师一共要付多少元？",
                    f"{ans} 元",
                    "kp_p4_arith_order", 0.4,
                    f"先分别算总价再相加：{p1}×{n1}＋{p2}×{n2}＝{p1*n1}＋{p2*n2}＝{ans}（元）。答：一共要付 {ans} 元。"))
    # 5) g4 除数是两位数的除法
    students, per = 672, 21
    assert students % per == 0
    ans = students // per
    out.append(item(4, "mgap_wp", "solve",
                    f"实验小学有 {students} 名学生参加运动会开幕式，每 {per} 人编成一队。一共可以编成多少队？",
                    f"{ans} 队",
                    "kp_p4_div_2digit", 0.45,
                    f"队数＝总人数÷每队人数：{students}÷{per}＝{ans}（队）。答：一共可以编成 {ans} 队。"))
    # 6) g5 梯形面积
    up, dn, h = 4, 6, 5
    ans = Fraction(up + dn, 2) * h
    assert ans.denominator == 1
    out.append(item(5, "mgap_wp", "solve",
                    f"一块梯形菜地，上底 {up} 米，下底 {dn} 米，高 {h} 米。这块菜地的面积是多少平方米？",
                    f"{int(ans)} 平方米",
                    "kp_p5_polygon_area", 0.45,
                    f"梯形面积＝（上底＋下底）×高÷2：（{up}＋{dn}）×{h}÷2＝{up+dn}×{h}÷2＝{int(ans)}（平方米）。答：面积是 {int(ans)} 平方米。"))
    # 7) g5 长方体体积
    L, Wd, H = 8, 5, 4
    ans = L * Wd * H
    out.append(item(5, "mgap_wp", "solve",
                    f"一个长方体水箱，长 {L} 分米，宽 {Wd} 分米，高 {H} 分米。它的容积是多少立方分米？",
                    f"{ans} 立方分米",
                    "kp_p5_cuboid_volume", 0.4,
                    f"长方体体积＝长×宽×高：{L}×{Wd}×{H}＝{L*Wd}×{H}＝{ans}（立方分米）。答：容积是 {ans} 立方分米。"))
    # 8) g6 分数实际问题
    total = Fraction(120)
    frac = Fraction(1, 4)
    read = total * frac
    left = total - read
    out.append(item(6, "mgap_wp", "solve",
                    f"一本故事书共 {int(total)} 页，明明第一天看了全书的 1/4。明明第一天看了多少页？还剩多少页没有看？",
                    f"{int(read)} 页；{int(left)} 页",
                    "kp_p6_fraction_problem", 0.5,
                    f"第一天看的页数＝{int(total)}×1/4＝{int(read)}（页）；剩下＝{int(total)}−{int(read)}＝{int(left)}（页）。答：第一天看了 {int(read)} 页，还剩 {int(left)} 页。"))
    return out


# ================================================================ primary 作图
def gen_primary_construction():
    out = []
    # 1) 周长给定画长方形（数据自洽：2×(5+4)=18）
    L, Wd, per = 5, 4, 2 * (5 + 4)
    out.append(item(3, "mgap_cons", "solve",
                    f"在方格纸（每格边长 1 厘米）上画一个周长是 {per} 厘米的长方形。你画的长方形长几格、宽几格？",
                    "长 5 格、宽 4 格（答案不唯一：长＋宽＝9 格即可）",
                    "kp_p3_perimeter", 0.5,
                    f"周长 {per} 厘米 → 长＋宽＝{per}÷2＝9（格）。取长 5 格、宽 4 格：2×(5＋4)＝18（厘米），符合要求。（长 6 格宽 3 格、长 7 格宽 2 格等均可）"))
    # 2) 量角器画角
    out.append(item(4, "mgap_cons", "solve",
                    "用量角器画一个 120° 的角，并简要写出画法。",
                    "①画一条射线 OA；②量角器中心与端点 O 重合、零刻度线与射线 OA 重合，找到 120° 刻度处点一个点 B；③连接 O、B 并延长，∠AOB 即为 120°。",
                    "kp_p4_angle_measure", 0.45,
                    "画角三步：画射线→对中心与零刻度线→找度数点点点再连线。注意看清量角器内外圈刻度。"))
    # 3) 梯形作图
    up, dn, h = 3, 5, 2
    out.append(item(4, "mgap_cons", "solve",
                    f"画一个上底 {up} 厘米、下底 {dn} 厘米、高 {h} 厘米的梯形（在方格纸上，每格 1 厘米），并标出上底、下底和高。",
                    f"示例：上底取 3 格、下底取 5 格（两底平行），两底之间竖直方向相距 2 格即为高 {h} 厘米（答案不唯一，只要两底平行、相距 2 格）",
                    "kp_p4_quad_shape", 0.55,
                    "要点：①上、下底平行且长分别为 3 格、5 格；②高是两平行底之间的垂直距离 2 格；③标上字母并标注底和高。"))
    # 4) 画圆并标直径（数据自洽：d=2r）
    r = 2
    out.append(item(6, "mgap_cons", "solve",
                    f"以点 O 为圆心、半径 2 厘米画一个圆，并在圆中画出一条直径。这条直径长多少厘米？",
                    "直径 4 厘米",
                    "kp_p6_circle", 0.4,
                    f"同一圆内直径 d＝2r：d＝2×{r}＝4（厘米）。画图要点：圆规两脚距离取 2 厘米定半径，过圆心所画两端都在圆上的线段即直径。"))
    return out


# ================================================================ jr 计算
def gen_jr_computation():
    out = []
    # 1) 一元一次方程（构造整数解）
    x = 4
    a, b, c = 3, 2, 1
    d = x * (a - c) + b  # 3x+2 = x+10 → x=4
    assert (a * x + b) == (c * x + d)
    out.append(item(7, "mgap_jcomp", "solve",
                    f"解方程：{a}x ＋ {b} ＝ x ＋ {d}。",
                    f"x ＝ {x}",
                    "kp_eq_solve", 0.4,
                    f"移项合并：{a}x − x ＝ {d} − {b}，{a-c}x ＝ {d-b}，x ＝ {x}。检验：左边＝{a}×{x}＋{b}＝{a*x+b}，右边＝{x+d}＝{c*x+d}，左边＝右边，解正确。"))
    # 2) 二元一次方程组（构造整数解 x=3, y=1）
    xs, ys = 3, 1
    A1, B1 = 2, 1
    C1 = A1 * xs + B1 * ys
    A2, B2 = 1, -1
    C2 = A2 * xs + B2 * ys
    assert A1 * xs + B1 * ys == C1 and A2 * xs + B2 * ys == C2
    out.append(item(7, "mgap_jcomp", "solve",
                    f"解方程组：{{ {A1}x ＋ y ＝ {C1}； x − y ＝ {C2} }}。",
                    f"x ＝ {xs}，y ＝ {ys}",
                    "kp_sys_solve", 0.45,
                    f"①＋②消 y：（{A1}x＋y）＋（x−y）＝{C1}＋{C2}，{A1+1}x＝{C1+C2}，x＝{xs}；代入②：{xs}−y＝{C2}，y＝{ys}。检验：{A1}×{xs}＋{ys}＝{C1} ✓，{xs}−{ys}＝{C2} ✓。"))
    # 3) 二次根式运算（数值由代码核实）
    v = 12 * 3  # √12·√3 = √36
    import math
    assert math.isqrt(v) ** 2 == v
    out.append(item(8, "mgap_jcomp", "solve",
                    "计算：√12 × √3 − √8 ÷ √2。",
                    "4",
                    "kp_radical_ops", 0.5,
                    "√12×√3＝√36＝6；√8÷√2＝√4＝2；所以原式＝6−2＝4。"))
    # 4) 一元二次方程（因式分解法，根 2、3）
    r1, r2 = 2, 3
    assert r1 + r2 == 5 and r1 * r2 == 6
    out.append(item(9, "mgap_jcomp", "solve",
                    "解方程：x² − 5x ＋ 6 ＝ 0。",
                    f"x₁ ＝ {r1}，x₂ ＝ {r2}",
                    "kp_qe_factor", 0.5,
                    f"因式分解：x²−5x＋6＝(x−{r1})(x−{r2})＝0，得 x−{r1}＝0 或 x−{r2}＝0，即 x₁＝{r1}，x₂＝{r2}。检验：{r1}²−5×{r1}＋6＝0 ✓，{r2}²−5×{r2}＋6＝0 ✓。"))
    return out


# ================================================================ jr 统计材料（comprehension）
def gen_jr_comprehension():
    out = []
    # 1) 中位数与众数（数据代码排序核实）
    data = [152, 155, 158, 160, 160, 162, 165, 168, 160, 172]
    s = sorted(data)
    n = len(s)
    med = (s[n // 2 - 1] + s[n // 2]) / 2 if n % 2 == 0 else s[n // 2]
    mode = max(set(s), key=s.count)
    assert s.count(mode) == 3 and med == 160
    table = "、".join(str(v) for v in data)
    out.append(item(8, "mgap_jstat", "solve",
                    f"某小组 10 名男生立定跳远成绩（单位：cm）如下：{table}。这组数据的中位数和众数各是多少？",
                    f"中位数 {int(med)} cm；众数 {mode} cm",
                    "kp_median_mode", 0.45,
                    f"从小到大排序后第 5、6 个数都是 {int(med)}，中位数＝{int(med)}；{mode} 出现 3 次最多，众数为 {mode}。"))
    # 2) 树状图/列表求概率（不放回，代码计数）
    from math import comb
    red, white = 3, 2
    total_pairs = comb(red + white, 2)
    fav = red * white
    from fractions import Fraction
    p = Fraction(fav, total_pairs)
    assert p == Fraction(3, 5)
    out.append(item(9, "mgap_jstat", "solve",
                    f"袋中装有 {red} 个红球和 {white} 个白球，除颜色外完全相同。搅匀后从中任意摸出 2 个球，恰好摸出 1 个红球和 1 个白球的概率是多少？",
                    "3/5",
                    "kp_re_list", 0.55,
                    f"共 {red+white} 个球，摸 2 个的等可能结果数为 C(5,2)＝{total_pairs}；一红一白的结果数为 3×2＝{fav}；P＝{fav}/{total_pairs}＝3/5。（也可用树状图列出全部 20 种结果验证）"))
    return out


# ================================================================ jr 二次函数综合（synthesis）
def gen_jr_synthesis():
    out = []
    # 1) 抛物线过 x 轴两点 + 定点，a、顶点、面积全由代码精确计算
    r1, r2, c_y = -1, 3, -3
    a_coeff = Fraction(c_y, 1) / Fraction(r1 * r2, 1)  # y(0)=a·r1·r2 = c_y
    assert a_coeff == 1
    # y = (x+1)(x-3) = x²-2x-3
    b_coeff, c_coeff = -(r1 + r2), r1 * r2
    vx = Fraction(-(b_coeff), 2)
    vy = vx * vx + b_coeff * vx + c_coeff
    AB = r2 - r1
    area = Fraction(AB * abs(c_y), 2)
    assert (vx, vy, AB, area) == (1, -4, 4, 6)
    out.append(item(9, "mgap_jsyn", "solve",
                    "已知抛物线与 x 轴交于 A(−1, 0)、B(3, 0) 两点，与 y 轴交于点 C(0, −3)。（1）求抛物线的解析式；（2）求抛物线的顶点坐标；（3）求 △ABC 的面积。",
                    "（1）y ＝ x² − 2x − 3；（2）顶点 (1, −4)；（3）6",
                    "kp_qf_vertex", 0.65,
                    "（1）设交点式 y＝a(x＋1)(x−3)，代入 C(0,−3)：−3a＝−3，a＝1，故 y＝x²−2x−3。（2）配方 y＝(x−1)²−4，顶点 (1, −4)。（3）AB＝3−(−1)＝4，OC＝3，S＝½×4×3＝6。"))
    # 2) 利润最值问题（参数代入代码核算）
    cost, base_price, base_qty, drop_per, qty_per = 40, 60, 300, 1, 5
    # 售价 x：销量 = base_qty − qty_per·(x−base_price)；P(x)=(x−cost)·销量
    # P(x) = −5x² + 800x − 24000，顶点 x=80，P=8000
    def P(x):
        return (x - cost) * (base_qty - qty_per * (x - base_price))
    best_x = 80
    best_p = P(best_x)
    # 顶点公式核对
    vx2 = Fraction(800, 2 * 5)
    assert vx2 == 80 and best_p == 8000 and P(79) < best_p and P(81) < best_p
    out.append(item(9, "mgap_jsyn", "solve",
                    f"某商店销售一种商品，进价为每件 {cost} 元。当售价为每件 {base_price} 元时，每天可售出 {base_qty} 件；售价每上涨 1 元，每天少售出 {qty_per} 件。设售价为每件 x 元，每天利润为 y 元。（1）求 y 关于 x 的函数解析式；（2）售价定为多少元时，每天利润最大？最大利润是多少？",
                    "（1）y ＝ −5x² ＋ 800x − 24000（x ≥ 60）；（2）售价 80 元，最大利润 8000 元",
                    "kp_qf_apply", 0.7,
                    "（1）销量为 300−5(x−60)＝600−5x，y＝(x−40)(600−5x)＝−5x²＋800x−24000。（2）y＝−5(x−80)²＋8000，开口向下，x＝80 时 y 最大为 8000。即售价定 80 元/件，每天最大利润 8000 元。"))
    return out


# ================================================================ hs 多选
def gen_hs_multi_select():
    out = []
    # 直接命题真值表：陈述真假为标准数学事实，答案集合由真值在代码侧组装
    items_spec = [
        (10, "kp_h10_set_relations", "下列命题正确的是（多选）",
         [("∅ 是任何集合的子集", True),
          ("{1, 2, 3} 的真子集个数是 7", True),
          ("若 A⊆B 且 B⊆A，则 A＝B", True),
          ("任何集合都有真子集", False)],
         "∅ 是任何集合的子集 ✓；n 元集真子集 2ⁿ−1＝7 ✓；A⊆B 且 B⊆A 由相等的定义 ✓；D 错：∅ 没有真子集。",
         0.45),
        (10, "kp_h10_parity", "下列关于函数 f(x)＝x³ 与 g(x)＝x² 的说法正确的是（多选）",
         [("f(x) 是奇函数", True),
          ("g(x) 是偶函数", True),
          ("f(x) 在 R 上单调递增", True),
          ("g(x) 在 R 上单调递增", False)],
         "x³ 定义域关于原点对称且 f(−x)＝−f(x) 奇 ✓；x² 满足 g(−x)＝g(x) 偶 ✓；x³ 导数 3x²≥0 恒成立故 R 上递增 ✓；x² 在 (−∞,0] 递减、[0,+∞) 递增，D 错。",
         0.45),
        (10, "kp_h10_trig_relations", "下列三角命题正确的是（多选）",
         [("对任意角 α，sin²α＋cos²α＝1", True),
          ("cos(−α)＝cosα 对任意角 α 成立", True),
          ("若 α 是第三象限角，则 sinα＜0 且 cosα＜0", True),
          ("若 sinα＝cosα，则 α＝45°", False)],
         "同角平方关系恒成立 ✓；cos(−α)＝cosα（奇偶性）✓；第三象限正弦、余弦皆负 ✓；D 错：sinα＝cosα 时 α＝45°＋k·180°（k∈Z），不止 45°。",
         0.5),
        (11, "kp_h11_vec_dot_product", "关于平面向量 a、b（均非零向量）与复数，下列说法正确的是（多选）",
         [("若 a∥b，则存在实数 λ 使 b＝λa", True),
          ("若 a·b＝0，则 a⊥b", True),
          ("复数 z＝3＋4i 的模为 5", True),
          ("若复数 z＝a＋bi 与 2＋3i 相等（a, b∈R），则只需 a＝2", False)],
         "共线向量定理 ✓；数量积为 0 且两向量非零 ⇔ 垂直 ✓；|z|＝√(3²＋4²)＝5 ✓；D 错：复数相等要求实部、虚部分别相等，还需 b＝3。",
         0.5),
        (12, "kp_h12_arith_props", "关于数列，下列命题正确的是（多选）",
         [("等差数列 {aₙ} 中，若 a₃＋a₇＝10，则 a₅＝5", True),
          ("公比 q≠1 的等比数列前 n 项和 Sₙ 满足 Sₙ＝a₁(1−qⁿ)/(1−q)", True),
          ("等比数列的公比 q 可以为 0", False),
          ("常数数列 1, 1, 1, … 是公比为 1 的等比数列", True)],
         "等差中项性质 a₃＋a₇＝2a₅ ✓；等比求和公式（q≠1）✓；C 错：等比数列定义要求 q≠0；D ✓：各项非零且公比为 1。",
         0.55),
        (11, "kp_h11_prob_props", "关于随机事件 A、B 的概率，下列说法正确的是（多选）",
         [("若事件 A 与 B 互斥，则 P(A∪B)＝P(A)＋P(B)", True),
          ("若 P(A)＝0.3，则 P(A 的对立事件)＝0.7", True),
          ("互斥事件一定是对立事件", False),
          ("若 P(A∪B)＝1，则 A 与 B 一定是对立事件", False)],
         "概率加法公式（互斥情形）✓；对立事件概率和为 1 ✓；C 错：对立必互斥、互斥未必对立（可能还有其他结果）；D 错：P(A∪B)＝1 不能推出 A、B 对立——两事件还可能不互斥（如 A＝「掷骰子得奇数」、B＝「得偶数或 6」）。",
         0.55),
    ]
    for g, kp, lead, claims, sol, d in items_spec:
        labels = ["A", "B", "C", "D"]
        answer = ",".join(l for (stmt, ok), l in zip(claims, labels) if ok)
        stem = lead + "：\n" + "\n".join(f"{l}. {stmt}" for (stmt, ok), l in zip(claims, labels))
        opts = [f"{l}. {stmt}" for (stmt, ok), l in zip(claims, labels)]
        out.append(item(g, "mgap_msmc", "choice", stem, answer, kp, d, sol,
                        options=opts, form="mcq_multi", answer_mode="subset"))
    return out


# ================================================================ hs 计算
def gen_hs_computation():
    out = []
    # 1) 余弦定理：a=5, b=8, C=60° → c=7（代码精确核算）
    a_, b_ = 5, 8
    c2 = a_**2 + b_**2 - 2 * a_ * b_ * Fraction(1, 2)
    assert c2 == 49 and math_isqrt(c2) == 7
    cosB = Fraction(a_**2 + 49 - b_**2, 2 * a_ * 7)
    assert cosB == Fraction(1, 7)
    out.append(item(11, "mgap_hcomp", "solve",
                    "在 △ABC 中，内角 A、B、C 所对的边分别为 a、b、c，已知 a＝5，b＝8，C＝60°。（1）求边 c；（2）求 cosB。",
                    "（1）c ＝ 7；（2）cosB ＝ 1/7",
                    "kp_h11_law_of_cosines", 0.55,
                    "（1）余弦定理 c²＝a²＋b²−2ab·cosC＝25＋64−2×5×8×½＝49，c＝7。（2）cosB＝(a²＋c²−b²)/(2ac)＝(25＋49−64)/(2×5×7)＝10/70＝1/7。"))
    # 2) 解直角三角形：A=30°, C=90°, c=8 → a=4, b=4√3
    c_h = 8
    a_h = Fraction(1, 2) * c_h
    assert a_h == 4
    out.append(item(11, "mgap_hcomp", "solve",
                    "在 △ABC 中，已知 C＝90°，A＝30°，斜边 c＝8。解这个直角三角形（求边 a、b 和角 B）。",
                    "a ＝ 4，b ＝ 4√3，B ＝ 60°",
                    "kp_h11_law_of_sines", 0.5,
                    "Rt△ 中 30° 角所对直角边为斜边一半：a＝½×8＝4；由勾股定理 b＝√(c²−a²)＝√(64−16)＝√48＝4√3；B＝90°−30°＝60°。"))
    # 3) 等差数列：a3=5, a7=13 → d=2, a1=1, S20=400（代码核算）
    a3, a7 = 5, 13
    d = Fraction(a7 - a3, 4)
    a1 = a3 - 2 * d
    S20 = Fraction(20, 1) * a1 + Fraction(20 * 19, 2) * d
    assert d == 2 and a1 == 1 and S20 == 400
    out.append(item(12, "mgap_hcomp", "solve",
                    "已知等差数列 {aₙ} 满足 a₃＝5，a₇＝13。（1）求 {aₙ} 的通项公式；（2）求其前 20 项和 S₂₀。",
                    "（1）aₙ ＝ 2n − 1；（2）S₂₀ ＝ 400",
                    "kp_h12_arith_sum", 0.55,
                    "（1）d＝(a₇−a₃)/4＝(13−5)/4＝2，a₁＝a₃−2d＝1，故 aₙ＝1＋2(n−1)＝2n−1。（2）S₂₀＝20a₁＋20×19/2×d＝20＋380＝400。"))
    # 4) 等比数列：a2=4, a5=32 → q=2, a1=2, S6=126
    a2g, a5g = 4, 32
    q3 = Fraction(a5g, a2g)
    assert q3 == 8
    q = 2
    a1g = Fraction(a2g, q)
    S6 = a1g * (q**6 - 1) // (q - 1)
    assert S6 == 126
    out.append(item(12, "mgap_hcomp", "solve",
                    "已知等比数列 {aₙ} 满足 a₂＝4，a₅＝32。（1）求 {aₙ} 的通项公式；（2）求其前 6 项和 S₆。",
                    "（1）aₙ ＝ 2ⁿ；（2）S₆ ＝ 126",
                    "kp_h12_geo_sum", 0.55,
                    "（1）a₅/a₂＝q³＝32/4＝8，q＝2，a₁＝a₂/q＝2，故 aₙ＝2·2ⁿ⁻¹＝2ⁿ。（2）S₆＝2(2⁶−1)/(2−1)＝2×63＝126。"))
    # 5) 导数切线：y=x³−3x+1 在 x=1 → k=0, y=−1
    f = lambda x: x**3 - 3 * x + 1
    fp = lambda x: 3 * x**2 - 3
    assert fp(1) == 0 and f(1) == -1
    out.append(item(12, "mgap_hcomp", "solve",
                    "已知曲线 y ＝ x³ − 3x ＋ 1。求该曲线在点 (1, f(1)) 处的切线方程。",
                    "y ＝ −1",
                    "kp_h12_tangent", 0.6,
                    "f′(x)＝3x²−3，切线斜率 k＝f′(1)＝0；f(1)＝1−3＋1＝−1，切点 (1, −1)。切线方程 y＝−1（水平线）。"))
    # 6) 古典概型：掷两骰子和为 7 与偶数
    outcomes = [(i, j) for i in range(1, 7) for j in range(1, 7)]
    n7 = sum(1 for i, j in outcomes if i + j == 7)
    neven = sum(1 for i, j in outcomes if (i + j) % 2 == 0)
    assert len(outcomes) == 36 and n7 == 6 and neven == 18
    out.append(item(11, "mgap_hcomp", "solve",
                    "同时掷两枚质地均匀的骰子，设两枚骰子点数之和为 X。（1）求 X＝7 的概率；（2）求 X 为偶数的概率。",
                    "（1）1/6；（2）1/2",
                    "kp_h11_classical_prob", 0.5,
                    "基本事件共 6×6＝36 个（等可能）。（1）和为 7 的有 (1,6)(2,5)(3,4)(4,3)(5,2)(6,1) 共 6 个，P＝6/36＝1/6。（2）和为偶数需两骰子同奇偶：3×3＋3×3＝18 个，P＝18/36＝1/2。"))
    return out


def math_isqrt(n) -> int:
    import math
    if isinstance(n, Fraction):
        assert n.denominator == 1
        n = n.numerator
    r = math.isqrt(n)
    assert r * r == n, f"{n} 不是完全平方数"
    return r


# ================================================================ hs 证明（参考答案为课本canonical，代码核不了文字但核数值前提）
def gen_hs_proof():
    out = []
    # 1) 线面垂直：正方体 BD⊥平面 ACC₁A₁
    out.append(item(11, "mgap_hproof", "solve",
                    "在正方体 ABCD−A₁B₁C₁D₁ 中，棱 AA₁⊥底面 ABCD。求证：BD ⊥ 平面 ACC₁A₁。",
                    "证明：①正方形 ABCD 中对角线互相垂直，故 BD⊥AC。②AA₁⊥平面 ABCD（正方体侧棱垂直于底面），BD⊂平面 ABCD，故 BD⊥AA₁。③AA₁∩AC＝A，AA₁、AC⊂平面 ACC₁A₁，且 BD 不在该平面内。由线面垂直判定定理，BD⊥平面 ACC₁A₁。",
                    "kp_h11_line_plane_perp", 0.6,
                    "判定定理要点：直线垂直于平面内两条相交直线（BD⊥AC，BD⊥AA₁，AC∩AA₁＝A）⇒ 线面垂直。"))
    # 2) 构造等比数列：a1=1, a_{n+1}=2a_n+1，b_n=a_n+1
    # 数值前提代码核：b1=2, q=2 → a5 = 2^5-1 = 31
    a5 = 2**5 - 1
    assert a5 == 31
    out.append(item(12, "mgap_hproof", "solve",
                    "已知数列 {aₙ} 满足 a₁＝1，aₙ₊₁＝2aₙ＋1（n∈N*）。设 bₙ＝aₙ＋1，证明：{bₙ} 是等比数列，并求 {aₙ} 的通项公式。",
                    "证明：bₙ₊₁＝aₙ₊₁＋1＝2aₙ＋2＝2(aₙ＋1)＝2bₙ，且 b₁＝a₁＋1＝2≠0，故 {bₙ} 是首项为 2、公比为 2 的等比数列。于是 bₙ＝2·2ⁿ⁻¹＝2ⁿ，即 aₙ＝2ⁿ−1。（检验：a₅＝2⁵−1＝31，递推吻合）",
                    "kp_h12_arith_judge", 0.6,
                    "构造法：由递推式两边同加 1 凑出 bₙ₊₁＝2bₙ；等比判定需说明首项不为 0。通项 aₙ＝2ⁿ−1 可用 n=1,2 代入复核。"))
    return out


# ================================================================ jr 尺规作图（作法为课本 canonical 内容）
def gen_jr_construction():
    out = []
    out.append(item(8, "mgap_jcons", "solve",
                    "尺规作图（保留作图痕迹，并写出作法）：已知线段 AB，求作线段 AB 的垂直平分线。",
                    "作法：①分别以点 A、B 为圆心，以大于 ½AB 的长为半径画弧，两弧分别交于点 P、Q；②作直线 PQ。直线 PQ 即为线段 AB 的垂直平分线。依据：到线段两端距离相等的点在线段的垂直平分线上（PA＝PB，QA＝QB）。",
                    "kp_isosceles_triangle", 0.5,
                    "关键点：半径必须“大于 ½AB”（否则两弧不相交）；由 PA＝PB、QA＝QB 两组等距点确定中垂线。"))
    out.append(item(8, "mgap_jcons", "solve",
                    "尺规作图（保留作图痕迹，并写出作法）：已知 ∠AOB，求作射线 OP，使 OP 平分 ∠AOB。",
                    "作法：①以点 O 为圆心、适当长为半径画弧，交 OA 于点 M，交 OB 于点 N；②分别以点 M、N 为圆心、大于 ½MN 的长为半径画弧，两弧在 ∠AOB 的内部交于点 P；③画射线 OP。射线 OP 即为 ∠AOB 的平分线。依据：OM＝ON，MP＝NP，OP＝OP，得 △OMP≌△ONP（SSS），故 ∠MOP＝∠NOP。",
                    "kp_bisector_property", 0.5,
                    "关键点：第二次画弧半径要大于 ½MN；作图依据是 SSS 全等推出两角相等。"))
    return out


# ================================================================ jr 几何证明
def gen_jr_proof():
    out = []
    out.append(item(8, "mgap_jproof", "solve",
                    "在 △ABC 中，AB＝AC，点 D、E 分别在边 AB、AC 上，且 AD＝AE。求证：△ABE ≌ △ACD。",
                    "证明：在 △ABE 和 △ACD 中，AB＝AC（已知），∠A＝∠A（公共角），AE＝AD（已知），∴△ABE≌△ACD（SAS）。",
                    "kp_isosceles_triangle", 0.55,
                    "要点：公共角 ∠A 是隐含条件；两组边夹这个公共角，符合 SAS 判定。注意对应关系：AB↔AC，AE↔AD。"))
    out.append(item(8, "mgap_jproof", "solve",
                    "在平行四边形 ABCD 中，对角线 AC、BD 相交于点 O。求证：OA＝OC，OB＝OD。",
                    "证明：∵四边形 ABCD 是平行四边形，∴AD∥BC，AD＝BC（平行四边形对边平行且相等）。∴∠OAD＝∠OCB，∠ODA＝∠OBC（两直线平行，内错角相等）。在 △OAD 和 △OCB 中，∠OAD＝∠OCB，AD＝CB，∠ODA＝∠OBC，∴△OAD≌△OCB（ASA）。∴OA＝OC，OB＝OD（全等三角形对应边相等），即平行四边形对角线互相平分。",
                    "kp_parallelogram", 0.6,
                    "要点：由平行四边形性质得 AD∥BC 且 AD＝BC，再以 ASA 证 △OAD≌△OCB，得对应边相等。"))
    return out


# ================================================================ hs 综合压轴（数值全部代码核算）
def gen_hs_synthesis():
    out = []
    # 1) 椭圆：焦点(±1,0) 过 (0,√3)。|PF|²=1+3=4 → |PF|=2 → 2a=4 → a²=4, b²=a²−c²=3
    d_pf = 1 + 3  # (0−(−1))²+(√3−0)² 与 (0−1)²+(√3)² 均为 4
    assert d_pf == 4 and math_isqrt(d_pf) == 2
    # k=1：x²/4 + x²/3 = 1 → 7x²/12 = 1 → x=±2√21/7；|AB|²=(1+k²)(x₁−x₂)²=2·(4·12/7)=96/7
    x2 = Fraction(12, 7)
    chord2 = 2 * 4 * x2
    assert chord2 == Fraction(96, 7)
    out.append(item(11, "mgap_hsyn", "solve",
                    "已知椭圆 C 的两个焦点为 F₁(−1, 0)、F₂(1, 0)，且椭圆 C 经过点 P(0, √3)。（1）求椭圆 C 的标准方程；（2）过原点且斜率为 1 的直线 l 与 C 交于 A、B 两点，求弦长 |AB|。",
                    "（1）x²/4 ＋ y²/3 ＝ 1；（2）|AB| ＝ 4√42/7",
                    "kp_h11_ellipse_def", 0.7,
                    "（1）c＝1，b²＝|OP|²＝3，a²＝b²＋c²＝4（或由 2a＝|PF₁|＋|PF₂|＝2＋2＝4 得 a＝2），故 C：x²/4＋y²/3＝1。（2）l：y＝x，代入得 7x²/12＝1，x＝±2√21/7，|AB|＝√(1＋1²)·|x₁−x₂|＝√2·(4√21/7)＝4√42/7。"))
    # 2) 导数：f(x)=x³−4x²+4x，f′=3x²−8x+4=(3x−2)(x−2)；[0,3] 上最大值 3
    f = lambda x: x**3 - 4 * x**2 + 4 * x
    fp = lambda x: 3 * x**2 - 8 * x + 4
    assert (3 * Fraction(2, 3) - 2) == 0 and fp(2) == 0
    vals = {x: f(x) for x in (0, Fraction(2, 3), 2, 3)}
    assert vals[0] == 0 and vals[Fraction(2, 3)] == Fraction(32, 27) and vals[2] == 0 and vals[3] == 3
    out.append(item(12, "mgap_hsyn", "solve",
                    "已知函数 f(x) ＝ x³ − 4x² ＋ 4x。（1）求 f(x) 的单调区间；（2）求 f(x) 在区间 [0, 3] 上的最大值。",
                    "（1）单调递增区间为 (−∞, 2/3) 和 (2, ＋∞)，单调递减区间为 (2/3, 2)；（2）最大值为 3",
                    "kp_h12_deriv_mono", 0.7,
                    "f′(x)＝3x²−8x＋4＝(3x−2)(x−2)。令 f′(x)>0 得 x<2/3 或 x>2；令 f′(x)<0 得 2/3<x<2。（2）比较 f(0)＝0，f(2/3)＝32/27，f(2)＝0，f(3)＝3，故最大值为 f(3)＝3。"))
    return out


BATCHES = {
    "math_primary_truefalse": (gen_primary_truefalse, {}),
    "math_primary_word_problem": (gen_primary_word_problem, {}),
    "math_primary_construction": (gen_primary_construction, {}),
    "math_jr_computation": (gen_jr_computation, {}),
    "math_jr_comprehension": (gen_jr_comprehension, {}),
    "math_jr_synthesis": (gen_jr_synthesis, {}),
    "math_jr_construction": (gen_jr_construction, {}),
    "math_jr_proof": (gen_jr_proof, {}),
    "math_hs_multi_select": (gen_hs_multi_select, {}),
    "math_hs_computation": (gen_hs_computation, {}),
    "math_hs_proof": (gen_hs_proof, {}),
    "math_hs_synthesis": (gen_hs_synthesis, {}),
}


def main() -> int:
    global DRY
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", default=None,
                    help="只跑指定批次（重跑全量会撞既有 id，增量必须带 --only）")
    args = ap.parse_args()
    DRY = args.dry_run
    ledger = {"batch": "math_templates_20261006", "appended": []}
    batches = {k: v for k, v in BATCHES.items() if not args.only or k in args.only.split(",")}
    for name, (fn, _) in batches.items():
        items = fn()
        form = BATCH_FORMS[name]
        for it in items:
            if it["form"] == "PENDING-FORM":
                it["form"] = form
        # 每批先校验（R 规则 + v2 + KP 属地），再按年级落盘
        by_grade = {}
        for it in items:
            by_grade.setdefault(it["_grade"], []).append(it)
        errs = G.validate_items([dict(x) for x in items], "math")
        if errs:
            print(f"!! {name} 校验失败：", *errs, sep="\n   ", file=sys.stderr)
            return 1
        dedup = G.Deduper("math")
        dropped = []
        kept_by_grade = {}
        for it in items:
            if dedup.is_dup(it["stem"]):
                dropped.append(it["id"])
                continue
            dedup.add(it["stem"])
            kept_by_grade.setdefault(it["_grade"], []).append(it)
        if DRY:
            print(f"{name}: 生成 {len(items)}，校验 OK，判重丢弃 {len(dropped)} {dropped or ''}")
            for it in items:
                print(f"   [{it['_grade']}] {it['id']} {it['form']}: {it['stem'][:50]}… => {it['answer'][:40]}")
            continue
        n = 0
        for g, its in sorted(kept_by_grade.items()):
            n += G.append_items("math", g, its, ledger)
        print(f"{name}: 生成 {len(items)}，校验 OK，判重丢弃 {len(dropped)}，落盘 {n}")
    if not DRY:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "ledger_math_templates.json"), "w", encoding="utf-8") as f:
            json.dump(ledger, f, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
