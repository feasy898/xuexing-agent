# -*- coding: utf-8 -*-
"""候选题生成：公共构造器（chi_hs 批次）。
题型内核三型：choice / fill / solve；form 标签遵循 docs/research/k12/chinese.md §3。
"""

KP_SET = set()
for _g in (10, 11, 12):
    import json as _json
    with open('data/knowledge/chinese_grade%d.json' % _g, encoding='utf-8') as _f:
        KP_SET.update(k['id'] for k in _json.load(_f)['knowledge_points'])


def _base(kp, item_type, form, stem, diff):
    assert kp in KP_SET, '未注册 KP: %s' % kp
    assert 0.4 <= diff <= 0.85, ('高中 difficulty 越界', kp, diff)
    return {'item_type': item_type, 'form': form, 'stem': stem, 'kps': [kp], 'difficulty': round(float(diff), 2)}


def C(kp, stem, options, ans, sol, diff, form='choice'):
    """选择题：options 为 4 个字符串（不带前缀），ans ∈ ABCD。"""
    assert len(options) == 4
    assert ans in 'ABCD'
    it = _base(kp, 'choice', form, stem, diff)
    it['options'] = ['%s. %s' % (l, t) for l, t in zip('ABCD', options)]
    it['answer'] = ans
    it['solution'] = sol
    return it


def F(kp, stem, ans, sol, diff, form='dictation'):
    """填空/简写题。"""
    it = _base(kp, 'fill', form, stem, diff)
    it['answer'] = ans
    it['solution'] = sol
    return it


def S(kp, stem, ans, sol, diff, form='comprehension'):
    """解答题（简答/翻译/鉴赏/应用写作）。"""
    it = _base(kp, 'solve', form, stem, diff)
    it['answer'] = ans
    it['solution'] = sol
    return it


def E(kp, stem, word_count, dims, ans, sol, diff=0.82, form='essay'):
    """作文题：writing_prompt = 题干材料 + 字数 + 评分维度；answer = 范文要点；solution = 50-100 字评分要点。"""
    it = _base(kp, 'solve', form, stem, diff)
    it['writing_prompt'] = '材料：%s｜字数：%s｜评分维度：%s' % (stem, word_count, dims)
    it['answer'] = ans
    it['solution'] = sol
    return it
