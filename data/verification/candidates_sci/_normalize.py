# -*- coding: utf-8 -*-
"""Reusable structural normaliser for the sci_prim data modules.

Two authoring slips recur when hand-writing item tuples:
  (a) 8-field tuples  -- solve/fill items written as
      (kp, type, form, diff, stem, None, <explanation>, None)
      i.e. the short key-answer slot is missing.
  (b) 10-field tuples -- observe items written with a stray trailing None.

Usage:  python _normalize.py <module> <module> ...
The key answers live in ANSWERS below, keyed by (module, index); they are
authored content, not derived from the explanation text.
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# (module, tuple index) -> short key answer to insert in slot 6
ANSWERS = {
    # ---------------- s_g3a ----------------
    ("s_g3a", 5): "要先弄清防水、导电、强度等性能，才能按用途选对材料。",
    ("s_g3a", 15): "不是漏水，是空气中的水蒸气遇冷凝结成小水滴附在瓶外壁上。",
    ("s_g3a", 19): "不对，盐水透明不能靠颜色判断；应取等量水加入不同量的同种溶质来比较。",
    ("s_g3a", 23): "滤纸贴紧才不会漏液；戳破后泥水直接漏下去，起不到过滤作用。",
    ("s_g3a", 29): "约120次（按每次拍手0.5秒估算：60÷0.5＝120）。",
    ("s_g3a", 33): "小明的手对墙施力，同时墙也对手有反作用力，所以手会感到疼。",
    ("s_g3a", 43): "因为芽向上生长，芽眼朝上才能破土而出、见到阳光。",
    ("s_g3a", 47): "玉米靠风力（花粉又轻又多）；桃树靠昆虫（花大色艳、花粉较粘）。",
    ("s_g3a", 49): "由胚珠发育而来；传粉受精后子房发育成果实，胚珠发育成种子。",
    ("s_g3a", 51): "让种子散布到更广的地方、扩大生长范围，使物种繁衍下去。",
    ("s_g3a", 55): "繁殖速度快、数量多，后代与亲代很相似，能保持优良性状。",
    ("s_g3a", 61): "狼门齿尖锐、犬齿发达适于撕咬；兔门齿宽厚、臼齿宽大适于啃食和磨碎植物。",
    ("s_g3a", 63): "牛吃草不需撕咬，犬齿退化、臼齿宽大；狼需撕咬肉块，犬齿尖锐发达。",
    ("s_g3a", 65): "鱼类、鸟类、爬行类的卵在体外发育靠孵化，所以卵生；哺乳类的胚胎需在母体内发育，所以胎生。",
    ("s_g3a", 67): "需要适宜的温度、湿度和空气；受精卵在蛋内发育成小鸡雏形，破壳而出后长大成成鸡。",
    ("s_g3a", 69): "父亲的精子和母亲的卵细胞结合成受精卵，在母体内发育成胚胎，约十个月后出生。",
    ("s_g3a", 71): "先长后腿、再长前腿，尾巴逐渐消失；由用鳃呼吸变成用肺呼吸，能在陆地生活。",
    ("s_g3a", 74): "鱼在水中、鸟在空中和地面、蛇在陆地；因为它们的呼吸、取食和运动方式不同。",
    ("s_g3a", 78): "猪肉间接来自玉米和大豆；鸡蛋间接来自玉米；青菜直接来自青菜本身。",
    # ---------------- s_g5a ----------------
}


def normalise(mod_name, expect_len):
    path = os.path.join(HERE, mod_name + ".py")
    src = io.open(path, encoding="utf-8").read()
    ns = {}
    exec(compile(src, path, "exec"), ns)
    items = ns["ITEMS"]

    new = []
    fixed_a = fixed_b = 0
    for i, it in enumerate(items):
        if len(it) == 10:
            assert it[9] is None, (mod_name, i)
            it = it[:9]
            fixed_b += 1
        elif len(it) == 8:
            kp, it_type, form, diff, stem, options, explanation, guide = it
            ans = ANSWERS[(mod_name, i)]
            it = (kp, it_type, form, diff, stem, options, ans, explanation, guide)
            fixed_a += 1
        new.append(it)

    bad = [i for i, x in enumerate(new) if len(x) != 9]
    if bad:
        raise SystemExit("%s: still malformed at %s" % (mod_name, bad))
    assert len(new) == expect_len, (mod_name, len(new), expect_len)

    head = src.split("ITEMS = [", 1)[0]
    body = ["ITEMS = ["]
    for it in new:
        body.append(repr(it) + ",")
    body.append("]\n\nassert len(ITEMS) == %d, len(ITEMS)\n" % expect_len)
    io.open(path, "w", encoding="utf-8").write(head + "\n".join(body))
    print("%s: inserted %d answers, dropped %d stray None, %d items"
          % (mod_name, fixed_a, fixed_b, len(new)))


if __name__ == "__main__":
    # usage: python _normalize.py <module>:<expected_item_count> [...]
    for spec in sys.argv[1:]:
        name, _, cnt = spec.partition(":")
        normalise(name, int(cnt))
