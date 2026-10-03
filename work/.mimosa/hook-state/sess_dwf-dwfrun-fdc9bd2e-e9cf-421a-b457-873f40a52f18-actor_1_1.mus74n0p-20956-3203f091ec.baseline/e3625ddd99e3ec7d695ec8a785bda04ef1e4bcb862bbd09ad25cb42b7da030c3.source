# -*- coding: utf-8 -*-
"""Grade 9 items"""
import json, os

OUT_DIR = "data/verification/candidates_en"

def choice_item(qid, stem, opts, answer, kp, difficulty, solution, form="multiple_choice", item_type="choice"):
    return {"id": qid, "item_type": item_type, "form": form, "stem": stem,
            "answer": answer, "kps": [kp], "difficulty": difficulty,
            "solution": solution, "source": "llm_generated", "options": opts}

def fill_item(qid, stem, answer, kp, difficulty, solution, form="fill", item_type="fill"):
    return {"id": qid, "item_type": item_type, "form": form, "stem": stem,
            "answer": answer, "kps": [kp], "difficulty": difficulty,
            "solution": solution, "source": "llm_generated"}

def solve_item(qid, stem, answer, kp, difficulty, solution, form, item_type="solve", writing_prompt=None):
    item = {"id": qid, "item_type": item_type, "form": form, "stem": stem,
            "answer": answer, "kps": [kp], "difficulty": difficulty,
            "solution": solution, "source": "llm_generated"}
    if writing_prompt:
        item["writing_prompt"] = writing_prompt
    return item

items = []

# ----- kp_eng9_lis9_intent -----
items.append(choice_item(
    "eng_en_jr_0110",
    "说话人说 'Could you possibly open the window?' 时，最可能的意图是（　　）",
    [
        "A. 命令",
        "B. 礼貌请求",
        "C. 抱怨",
        "D. 告知"
    ],
    "B", "kp_eng9_lis9_intent", 0.4,
    "Could you possibly... 是委婉礼貌的请求表达。"
))
items.append(choice_item(
    "eng_en_jr_0111",
    "句子 'It seems we have a problem here.' 中说话者最可能的意图是（　　）",
    [
        "A. 表达乐观",
        "B. 委婉地指出问题",
        "C. 下达命令",
        "D. 表示祝贺"
    ],
    "B", "kp_eng9_lis9_intent", 0.4,
    "It seems... 是英语中委婉指出问题的常用表达。"
))

# ----- kp_eng9_red9_structure -----
items.append(choice_item(
    "eng_en_jr_0112",
    "分析一篇议论文时，判断内容主次的关键是（　　）",
    [
        "A. 看每段长度",
        "B. 看论点的位置与重复出现次数",
        "C. 看插图",
        "D. 看标题长度"
    ],
    "B", "kp_eng9_red9_structure", 0.45,
    "议论文的主次靠论点的位置（首尾/反复出现）来识别。"
))

# ----- kp_eng9_red9_word_from_context_wordform -----
items.append(choice_item(
    "eng_en_jr_0113",
    "句子 'He displayed great courage during the rescue.' 中 'displayed' 最可能的意思是（　　）",
    [
        "A. 隐藏",
        "B. 展示、表现",
        "C. 怀疑",
        "D. 失去"
    ],
    "B", "kp_eng9_red9_word_from_context_wordform", 0.4,
    "display + great courage 语境中意为'展示、表现'。"
))
items.append(fill_item(
    "eng_en_jr_0114",
    "由构词法推断词义：'unfriendly' 中 un- 是______，意为'不友好的'。",
    "否定前缀", "kp_eng9_red9_word_from_context_wordform", 0.4,
    "un- 是常见否定前缀，加在形容词前构成反义词。"
))

# ----- kp_eng9_lis9_selective_note -----
items.append(choice_item(
    "eng_en_jr_0115",
    "听一段较长的材料并做记录时，下列做法最有效（　　）",
    [
        "A. 把每个词都写下来",
        "B. 用缩写、符号记录关键信息",
        "C. 只记日期",
        "D. 不做记录"
    ],
    "B", "kp_eng9_lis9_selective_note", 0.45,
    "有选择地记信息应使用缩写、符号记关键信息。"
))

# ----- kp_eng9_red9_biography_news -----
items.append(choice_item(
    "eng_en_jr_0116",
    "阅读名人传记时，概括人物特点的关键信息是（　　）",
    [
        "A. 出生地邮编",
        "B. 主要经历与典型事迹",
        "C. 朋友数量",
        "D. 饮食偏好"
    ],
    "B", "kp_eng9_red9_biography_news", 0.4,
    "传记的特点由主要经历与典型事迹体现。"
))
items.append(solve_item(
    "eng_en_jr_0117",
    "阅读下面这则报刊文章（节选）后概括作者主要观点：\n\n'Many cities now have bike-sharing systems. People can pick up a bike at one station and return it at another. This is good for the environment and helps people stay healthy.'",
    "作者认为共享单车对环境和健康都有益，值得推广。",
    "kp_eng9_red9_biography_news", 0.5,
    "作者列举 bike-sharing 的两个好处（environment / health），并用 'This is good for...' 直接表达肯定态度。",
    form="comprehension"
))

# ----- kp_eng9_red9_150k -----
items.append(choice_item(
    "eng_en_jr_0118",
    "课标要求九年级课外阅读累计词量至少（　　）",
    [
        "A. 4 万词",
        "B. 10 万词",
        "C. 15 万词以上",
        "D. 20 万词"
    ],
    "C", "kp_eng9_red9_150k", 0.3,
    "义教三级·九年级课外阅读累计量 15 万词以上。"
))

# ----- kp_eng9_vie9_nonverbal_resource -----
items.append(choice_item(
    "eng_en_jr_0119",
    "一段视频中的人物表情严肃、语气沉重，配合字幕 'We lost the game.'，最合理的解读是（　　）",
    [
        "A. 极度开心",
        "B. 失落、沮丧",
        "C. 平静",
        "D. 讽刺"
    ],
    "B", "kp_eng9_vie9_nonverbal_resource", 0.4,
    "表情、语气与'输掉比赛'共同传达失落沮丧。"
))

# ----- kp_eng9_spk9_oral_summary -----
items.append(solve_item(
    "eng_en_jr_0120",
    "请口头概括并转述这段话的主旨大意：\n\n'Yesterday our class held a clean-up activity near the school river. We collected rubbish and put up signs saying \"No littering\". We hope our river will be cleaner in the future.'",
    "我们班昨天在学校附近的河边开展了清洁活动，捡拾垃圾并张贴警示牌，希望河水未来更清澈。",
    "kp_eng9_spk9_oral_summary", 0.45,
    "概括要点：时间(yesterday)、活动(clean-up)、行动(collect rubbish + signs)、希望(cleaner future)。",
    form="oral_qa"
))

# ----- kp_eng9_spk9_opinion_reason -----
items.append(solve_item(
    "eng_en_jr_0121",
    "你如何看待'学生使用智能手机'？请用 2-3 句话表达你的观点并说明理由。",
    "I think students can use smartphones, but only in a smart way. Smartphones help us learn and stay in touch with family. However, we should not use them too much in class.",
    "kp_eng9_spk9_opinion_reason", 0.5,
    "观点（I think...）+ 理由（help us learn...）+ 限制（not too much）。",
    form="oral_qa"
))

# ----- kp_eng9_wri9_draft_modify_finish -----
items.append(solve_item(
    "eng_en_jr_0122",
    "请独立起草、修改并完成下面这篇 60-80 词的作文，主题：A Trip I Will Never Forget。",
    "I'll never forget my trip to Beijing last summer. We visited the Great Wall and the Palace Museum. I was amazed by the long history and beautiful buildings. The local food was also very delicious. I really hope to visit Beijing again with my family.",
    "kp_eng9_wri9_draft_modify_finish", 0.55,
    "独立起草要点：时间地点 → 关键活动 → 感受 → 愿望；要求结构完整、语句通顺。",
    form="essay"
))

# ----- kp_eng9_wri9_chart_caption -----
items.append(solve_item(
    "eng_en_jr_0123",
    "下面是一张你绘制的漫画（画面：一个小男孩在公交车上让座给一位老人）。请用 3-5 句话为这张漫画写出说明。",
    "In the picture, a little boy is on a bus. He sees an old lady standing near him. He quickly stands up and gives his seat to her. The old lady smiles and says 'Thank you'. It shows us that being kind is a beautiful thing.",
    "kp_eng9_wri9_chart_caption", 0.5,
    "看图说明要点：人物+场景+动作+对话+寓意，语句连贯。",
    form="picture_qa"
))

# ----- kp_eng9_gra9_tense_master -----
items.append(choice_item(
    "eng_en_jr_0124",
    "By the time he arrived, the film ______.（　　）",
    [
        "A. started",
        "B. has started",
        "C. had started",
        "D. was starting"
    ],
    "C", "kp_eng9_gra9_tense_master", 0.5,
    "'过去的过去'用过去完成时 had started。"
))
items.append(choice_item(
    "eng_en_jr_0125",
    "I ______ for two hours when the bell rang.（　　）",
    [
        "A. study",
        "B. am studying",
        "C. had been studying",
        "D. have studied"
    ],
    "C", "kp_eng9_gra9_tense_master", 0.55,
    "过去某一时刻（响铃时）之前一直在做某事，用过去完成进行时。"
))

# ----- kp_eng9_gra9_passive_all -----
items.append(choice_item(
    "eng_en_jr_0126",
    "The bridge ______ in 1990.（　　）",
    [
        "A. is built",
        "B. was built",
        "C. built",
        "D. has built"
    ],
    "B", "kp_eng9_gra9_passive_all", 0.4,
    "in 1990 是过去时间，主语 bridge 是动作承受者，用一般过去时被动 was built。"
))
items.append(fill_item(
    "eng_en_jr_0127",
    "填空：The Chinese poem ______ (translate) into many languages now.",
    "is translated", "kp_eng9_gra9_passive_all", 0.45,
    "now 提示一般现在时被动：is translated。"
))

# ----- kp_eng9_gra9_object_clause_master -----
items.append(choice_item(
    "eng_en_jr_0128",
    "He asked me ______ with me.（　　）",
    [
        "A. what is the matter",
        "B. what the matter is",
        "C. what was the matter",
        "D. what the matter was"
    ],
    "C", "kp_eng9_gra9_object_clause_master", 0.5,
    "asked 过去时，从句应用过去的陈述语序：what was the matter。"
))
items.append(choice_item(
    "eng_en_jr_0129",
    "I don't know ______ tomorrow.（　　）",
    [
        "A. what will the weather be like",
        "B. what the weather will be like",
        "C. what the weather will like be",
        "D. what the weather will be"
    ],
    "B", "kp_eng9_gra9_object_clause_master", 0.5,
    "宾语从句用陈述语序：what the weather will be like。"
))

# ----- kp_eng9_gra9_gerund_object -----
items.append(choice_item(
    "eng_en_jr_0130",
    "He enjoys ______ in the sea.（　　）",
    [
        "A. swim",
        "B. to swim",
        "C. swimming",
        "D. swims"
    ],
    "C", "kp_eng9_gra9_gerund_object", 0.45,
    "enjoy 后接动名词作宾语，即 enjoy doing sth.。"
))
items.append(fill_item(
    "eng_en_jr_0131",
    "填空：Would you mind ______ (close) the door?",
    "closing", "kp_eng9_gra9_gerund_object", 0.45,
    "mind 后接动名词：mind doing sth."
))

# ----- kp_eng9_gra9_comparative_superlative -----
items.append(choice_item(
    "eng_en_jr_0132",
    "Mount Qomolangma is ______ mountain in the world.（　　）",
    [
        "A. high",
        "B. higher",
        "C. highest",
        "D. the highest"
    ],
    "D", "kp_eng9_gra9_comparative_superlative", 0.45,
    "in the world 范围用最高级；最高级前需加 the。"
))
items.append(fill_item(
    "eng_en_jr_0133",
    "填空：This book is ______ (interesting) than that one.",
    "more interesting", "kp_eng9_gra9_comparative_superlative", 0.45,
    "interesting 为多音节形容词，比较级 more interesting。"
))

# ----- kp_eng9_dis9_argument_structure -----
items.append(choice_item(
    "eng_en_jr_0134",
    "说理类语篇最常用的论证方法是（　　）",
    [
        "A. 摆事实、讲道理",
        "B. 故事加想象",
        "C. 只用抒情",
        "D. 单纯叙述"
    ],
    "A", "kp_eng9_dis9_argument_structure", 0.45,
    "议论文以事实与道理论证观点。"
))

# ----- kp_eng9_prg9_speech_style -----
items.append(choice_item(
    "eng_en_jr_0135",
    "给校长写正式建议信，最得体的开头是（　　）",
    [
        "A. Hi, Mr Li!",
        "B. Dear Mr Li,",
        "C. Hey, dude!",
        "D. What's up, Li?"
    ],
    "B", "kp_eng9_prg9_speech_style", 0.4,
    "正式信函应用 Dear + 姓/称呼；其它表达过于随意。"
))

# ----- kp_eng9_voc9_1600_master -----
items.append(fill_item(
    "eng_en_jr_0136",
    "写出汉语对应的英语单词：'环境' ______",
    "environment", "kp_eng9_voc9_1600_master", 0.35,
    "环境对应的英文单词为 environment。"
))
items.append(choice_item(
    "eng_en_jr_0137",
    "下列哪一组词汇主题属于九年级综合掌握范围（　　）",
    [
        "A. apple, banana",
        "B. environment, technology, communication",
        "C. cat, dog",
        "D. pen, ruler"
    ],
    "B", "kp_eng9_voc9_1600_master", 0.4,
    "B 组覆盖九年级常见主题（环境、科技、通讯），与课标三级词汇范围一致。"
))

# ----- kp_eng9_voc9_polysemy -----
items.append(choice_item(
    "eng_en_jr_0138",
    "句子 'He runs a small company.' 中 'runs' 的含义是（　　）",
    [
        "A. 跑步",
        "B. 经营、管理",
        "C. 流动",
        "D. 比赛"
    ],
    "B", "kp_eng9_voc9_polysemy", 0.45,
    "run a company 中 run 意为'经营、管理'，是一词多义现象。"
))
items.append(fill_item(
    "eng_en_jr_0139",
    "写出 'bank' 在 'river bank' 语境下的中文含义：______",
    "岸", "kp_eng9_voc9_polysemy", 0.45,
    "bank 在'河边'语境中意为'岸'，区别于'银行'。"
))

# ----- kp_eng9_cul9_country_profile -----
items.append(choice_item(
    "eng_en_jr_0140",
    "下列关于英国（UK）的描述不正确的是（　　）",
    [
        "A. 首都 London",
        "B. 货币 pound",
        "C. 官方语言 English",
        "D. 大熊猫是国宝"
    ],
    "D", "kp_eng9_cul9_country_profile", 0.4,
    "大熊猫是中国的国宝，并非英国。"
))

# ----- kp_eng9_cul9_health_finance_view -----
items.append(solve_item(
    "eng_en_jr_0141",
    "请围绕 'Healthy Lifestyle and Smart Spending' 写一段 60-80 词的短文，谈谈健康生活方式与理性消费的关系。",
    "A healthy lifestyle and smart spending go together. Eating well, doing exercise and sleeping enough keep us strong. At the same time, we should spend money wisely — don't buy junk food or things we don't need. Both health and money need good habits.",
    "kp_eng9_cul9_health_finance_view", 0.55,
    "短文要点：把'健康'与'理财'结合→举例说明→总结观点；体现思辨性。",
    form="essay"
))

# ----- kp_eng9_lsm9_plan_exam -----
items.append(solve_item(
    "eng_en_jr_0142",
    "针对中考英语，请写出一份为期四周的复习计划（简述每周重点与复习策略）。",
    "Week 1: review grammar tenses and do 20 exercises. Week 2: read 3 English passages a day and note new words. Week 3: practise listening and cloze tests every day. Week 4: do mock tests and check weak points.",
    "kp_eng9_lsm9_plan_exam", 0.5,
    "复习计划应分阶段、含重点与策略；四周覆盖语法、阅读、听力、模拟。",
    form="open_write"
))

# ----- kp_eng9_lsm9_topic_plan -----
items.append(choice_item(
    "eng_en_jr_0143",
    "按主题组织语言材料的优点不包括（　　）",
    [
        "A. 利于联想记忆",
        "B. 便于写作时调用",
        "C. 提高词汇系统性",
        "D. 让单词之间无联系"
    ],
    "D", "kp_eng9_lsm9_topic_plan", 0.4,
    "按主题组织可以加强词与词之间的联系，D 与此相反。"
))

# ----- kp_eng9_lsm9_anxiety_control -----
items.append(solve_item(
    "eng_en_jr_0144",
    "考试前你感到紧张，请写出 2 种降低焦虑、保持自信的具体做法。",
    "1. Take a few deep breaths before the exam starts. 2. Tell myself 'I have prepared well, I can do it.' These help me stay calm and confident.",
    "kp_eng9_lsm9_anxiety_control", 0.4,
    "降低焦虑：深呼吸 + 自我积极暗示；具体可行。",
    form="open_write"
))

# ----- kp_eng9_thm9_volunteer -----
items.append(solve_item(
    "eng_en_jr_0145",
    "请围绕 'Volunteer Service' 写一段 60-80 词的短文，谈谈志愿服务的重要性并举例说明。",
    "Volunteer service is very important. It helps people in need and makes our community better. Last summer, I helped clean up the city park with other volunteers. I felt happy to make our city cleaner. I hope more students join us.",
    "kp_eng9_thm9_volunteer", 0.55,
    "主题为'志愿服务与公共服务'，要点：重要性 + 个人经历 + 呼吁参与，结构完整。",
    form="essay"
))

# ----- kp_eng9_thm9_env_protect -----
items.append(solve_item(
    "eng_en_jr_0146",
    "请围绕 'How to Protect Our Environment' 写一段 60-80 词的短文，提出至少三条具体建议。",
    "To protect our environment, we can do many small things. First, we should save water and turn off the lights when we leave a room. Second, we can use cloth bags instead of plastic ones. Third, planting more trees helps make the air cleaner. Let's take action now.",
    "kp_eng9_thm9_env_protect", 0.55,
    "主题为'环境保护与自然生态'，要点：开头点题 + 三条具体建议 + 呼吁行动。",
    form="essay"
))

print(f"Grade 9: {len(items)} items")

# Save grade 9 items
with open(os.path.join(OUT_DIR, "_temp_g9.json"), "w", encoding="utf-8") as f:
    json.dump(items, f, ensure_ascii=False, indent=2)
print(f"Saved {len(items)} items to _temp_g9.json")
