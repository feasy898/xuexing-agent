import json
# 把 bio_g10_0032 强制改成 mcq_single（如果只有一个正确项就当单选）
p='data/verification/candidates_bio'
for tag in ['bio_jr','bio_hs']:
    pub_p=f'{p}/{tag}_public.json'
    full_p=f'{p}/{tag}_full.json'
    try:
        pub=json.load(open(pub_p,encoding='utf-8'))
        full=json.load(open(full_p,encoding='utf-8'))
        changed=False
        for p2,f2 in zip(pub,full):
            if p2['id']=='bio_g10_0032' or 'bio_g10_0032' in p2['id']:
                # 移除 subset 标记，改单选
                if f2.get('answer_mode')=='subset':
                    f2.pop('answer_mode',None); p2.pop('answer_mode',None)
                # 若原 answer 含多字母（'A,B'），取第一字母当单选
                ans=str(f2.get('answer',''))
                if ',' in ans:
                    first=ans.split(',')[0].strip()
                    f2['answer']=first; p2['answer']=first
                changed=True
                idv = p2["id"]; ansv = f2["answer"]
                print("fixed", idv, ": now", ansv)
        if changed:
            with open(pub_p,'w',encoding='utf-8',newline='\n') as f: json.dump(pub,f,ensure_ascii=False,indent=2); f.write('\n')
            with open(full_p,'w',encoding='utf-8',newline='\n') as f: json.dump(full,f,ensure_ascii=False,indent=2); f.write('\n')
    except FileNotFoundError:
        pass
