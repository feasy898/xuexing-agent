# -*- coding: utf-8 -*-
"""组装 chi_hs 批次：public / full / ledger 三个文件 + 全量校验。"""
import io, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
os.chdir(ROOT)

import common  # noqa: E402  (读 data/knowledge/chinese_grade1*.json)
import part10a, part10b, part11a, part11b, part12, part_supp  # noqa: E402

OUT_DIR = os.path.join('data', 'verification', 'candidates_chi')
TAG = 'chi_hs'

def build():
    raw = []
    for part in (part10a, part10b, part11a, part11b, part12, part_supp):
        raw.extend(part.ITEMS)
    items, errors = [], []
    for i, it in enumerate(raw, 1):
        it = dict(it)
        it['id'] = '%s_%04d' % (TAG, i)
        it['source'] = 'llm_generated'
        items.append(it)
    return items, errors

def validate(items):
    errs = []
    ids = [it['id'] for it in items]
    if len(set(ids)) != len(ids):
        errs.append('id 重复')
    for it in items:
        if not re.fullmatch(r'chi_hs_\d{4}', it['id']):
            errs.append('%s id 格式错误' % it['id'])
        if it['kps'] and len(it['kps']) != 1:
            errs.append('%s kps 数量 != 1' % it['id'])
        for kp in it['kps']:
            if kp not in common.KP_SET:
                errs.append('%s KP 未注册: %s' % (it['id'], kp))
        d = it['difficulty']
        if not (0.4 <= d <= 0.85):
            errs.append('%s difficulty 越界: %s' % (it['id'], d))
        if it['item_type'] == 'choice':
            if 'options' not in it or len(it['options']) != 4:
                errs.append('%s choice 缺 4 选项' % it['id'])
            else:
                labels = [o[:1] for o in it['options']]
                if labels != ['A', 'B', 'C', 'D']:
                    errs.append('%s 选项标签错误 %s' % (it['id'], labels))
            if it.get('answer') not in ('A', 'B', 'C', 'D'):
                errs.append('%s choice answer 非法: %s' % (it['id'], it.get('answer')))
        else:
            if 'options' in it:
                errs.append('%s 非 choice 不应有 options' % it['id'])
            if not isinstance(it.get('answer'), str) or len(it['answer']) < 2:
                errs.append('%s 非 choice answer 应为中文短串' % it['id'])
        if it.get('form') == 'essay':
            if 'writing_prompt' not in it:
                errs.append('%s essay 缺 writing_prompt' % it['id'])
            elif not isinstance(it['answer'], str) or len(it['answer']) < 20:
                errs.append('%s essay answer 范文要点过短' % it['id'])
            elif not (isinstance(it['solution'], str) and '评分要点' in it['solution']):
                errs.append('%s essay solution 应为评分要点' % it['id'])
            elif not 45 <= len(it['solution'].replace('评分要点：', '')) <= 130:
                errs.append('%s essay solution 长度 %d 不在50-100字量级' % (it['id'], len(it['solution'].replace('评分要点：', ''))))
        elif 'writing_prompt' in it:
            errs.append('%s 非 essay 含 writing_prompt' % it['id'])
        if it.get('source') != 'llm_generated':
            errs.append('%s source 错误' % it['id'])
    return errs

def rebalance(items):
    """选择题答案分布纠偏：B 偏多时，将不引用选项字母的 B 题上一部分对调到 A/D。
    交换 options 顺序并同步 answer；solution/options/stem 全无字母引用者才允许。"""
    def letter_free(it):
        opts = '\n'.join(o[3:] for o in it['options'])
        txt = it['stem'] + '\n' + it['solution'] + '\n' + opts
        # 凡出现"字母+项/标点"或"字母+汉字"（如 “A应是”“C是”），一律视为引用选项字母，不纠偏
        return re.search(r'[ABCD][项、．.:：]', txt) is None and \
               re.search(r'(?<![A-Za-z])[ABCD](?=[\u4e00-\u9fff，。；、）(])', txt) is None
    def swap(it, i, j):
        body = [o[3:] for o in it['options']]
        body[i], body[j] = body[j], body[i]
        it['options'] = ['%s. %s' % (l, t) for l, t in zip('ABCD', body)]

    b_items = [it for it in items if it['item_type'] == 'choice' and it['answer'] == 'B' and letter_free(it)]
    to_a = b_items[: max(0, len(b_items) - 22)]
    to_d = b_items[max(0, len(b_items) - 22):]
    for it in to_a:
        swap(it, 0, 1)
        it['answer'] = 'A'
    for it in to_d:
        swap(it, 1, 3)
        it['answer'] = 'D'
    return len(to_a), len(to_d)

def main():
    items, _ = build()
    errs = validate(items)
    if errs:
        print('校验失败 %d 项：' % len(errs))
        for e in errs[:40]:
            print(' -', e)
        sys.exit(1)

    from collections import Counter
    dist = Counter(it['answer'] for it in items if it['item_type'] == 'choice')
    if dist.get('B', 0) > dist.get('A', 0) + dist.get('D', 0) + dist.get('C', 0):
        pass
    na, nd = rebalance(items)
    errs = validate(items)
    if errs:
        print('纠偏后校验失败 %d 项：' % len(errs))
        for e in errs[:40]:
            print(' -', e)
        sys.exit(1)
    print('答案纠偏：B->A %d 题，B->D %d 题' % (na, nd))
    cnt = Counter(it['kps'][0] for it in items)
    bad = {k: v for k, v in cnt.items() if v < 2 or v > 3}
    print('题目总数：%d' % len(items))
    print('覆盖 KP 数：%d / %d' % (len(cnt), len(common.KP_SET)))
    missing = common.KP_SET - set(cnt)
    if missing:
        print('未覆盖 KP：', sorted(missing))
    if bad:
        print('超配额 KP（2-3）：', bad)
    by_type = Counter(it['item_type'] for it in items)
    by_form = Counter(it['form'] for it in items)
    print('item_type 分布：', dict(by_type))
    print('form 分布：', dict(by_form))
    diffs = [it['difficulty'] for it in items]
    print('difficulty: min=%.2f max=%.2f mean=%.2f' % (min(diffs), max(diffs), sum(diffs) / len(diffs)))
    if missing or bad or len(set(cnt)) != len(common.KP_SET):
        sys.exit(2)

    os.makedirs(OUT_DIR, exist_ok=True)
    pub, full = [], []
    for it in items:
        p = {k: it[k] for k in ('id', 'item_type', 'form', 'stem', 'kps', 'difficulty')}
        if 'options' in it:
            p['options'] = it['options']
        pub.append(p)
        f = {'id': it['id'], 'item_type': it['item_type'], 'form': it['form'],
             'stem': it['stem'], 'answer': it['answer'], 'kps': it['kps'],
             'difficulty': it['difficulty'], 'solution': it['solution'],
             'source': 'llm_generated'}
        if 'options' in it:
            f['options'] = it['options']
        if 'writing_prompt' in it:
            f['writing_prompt'] = it['writing_prompt']
        full.append(f)
    ledger = {'agent_id': 'chi-gen-w1-20261003', 'solver': 'MiniMax-M3',
              'method': 'generator self-answer',
              'answers': {it['id']: it['answer'] for it in items}}

    def dump(name, obj):
        path = os.path.join(OUT_DIR, name)
        with io.open(path, 'w', encoding='utf-8') as fh:
            json.dump(obj, fh, ensure_ascii=False, indent=1)
        print('写出', path)

    dump('%s_public.json' % TAG, pub)
    dump('%s_full.json' % TAG, full)
    dump('%s_ledger_gen.json' % TAG, ledger)

    # 回读一致性校验
    pub2 = json.load(io.open(os.path.join(OUT_DIR, '%s_public.json' % TAG), encoding='utf-8'))
    ful2 = json.load(io.open(os.path.join(OUT_DIR, '%s_full.json' % TAG), encoding='utf-8'))
    led2 = json.load(io.open(os.path.join(OUT_DIR, '%s_ledger_gen.json' % TAG), encoding='utf-8'))
    assert [p['id'] for p in pub2] == [f['id'] for f in ful2], 'public/full 顺序不一致'
    assert led2['answers'] == {f['id']: f['answer'] for f in ful2}, 'ledger 与 full 答案不一致'
    for p, f in zip(pub2, ful2):
        assert 'answer' not in p and 'solution' not in p and 'writing_prompt' not in p, 'public 泄漏答案'
        assert p['stem'] == f['stem'] and p['kps'] == f['kps']
    print('回读校验通过：public 无答案泄漏，full/ledger 一致，共 %d 题' % len(pub2))

if __name__ == '__main__':
    main()
