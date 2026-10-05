# -*- coding: utf-8 -*-
"""Add second items for KPs that currently have only 1, plus a few 3rd items."""
import json, os
from collections import defaultdict

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

# ============== Grade 7 supplements ==============
# For KPs that currently have 1 item

# kp_eng7_cul7_etiquette
items.append(fill_item(
    "eng_en_jr_0147",
    "填空：在英语国家拜访朋友前常用的礼貌表达是 '______ your visit in advance'。",
    "Confirm", "kp_eng7_cul7_etiquette", 0.45,
    "拜访前确认时间/方式符合英语国家礼仪：confirm your visit in advance。"
))

# kp_eng7_cul7_health_view
items.append(choice_item(
    "eng_en_jr_0148",
    "面对突发疾病，下列做法最符合珍爱生命的态度是（　　）",
    [
        "A. 隐瞒不告诉任何人",
        "B. 及时告诉家长或老师并就医",
        "C. 自己吃药不看医生",
        "D. 故意加重病情"
    ],
    "B", "kp_eng7_cul7_health_view", 0.35,
    "及时告知成年人并就医是珍爱生命的体现。"
))

# kp_eng7_cul7_role_models
items.append(solve_item(
    "eng_en_jr_0149",
    "请用 2-3 句话介绍一位你敬佩的中外人物，并说明原因。",
    "I admire Dr Yuan Longping. He developed hybrid rice and helped feed people around the world. He worked very hard and never stopped trying. He is a great scientist and a kind person.",
    "kp_eng7_cul7_role_models", 0.45,
    "介绍要点：人物 + 事迹 + 优秀品格 + 敬佩原因，语句连贯。",
    form="essay"
))

# kp_eng7_dis7_dialogue_monologue
items.append(fill_item(
    "eng_en_jr_0150",
    "填空：日常对话通常由两方或多方 ______ 说话，而独白通常是一方连续 ______。",
    "轮流/讲述", "kp_eng7_dis7_dialogue_monologue", 0.4,
    "对话(dialogue)是双方或多方交替发言，独白(monologue)是一方连续讲述。"
))

# kp_eng7_dis7_narration_purpose
items.append(choice_item(
    "eng_en_jr_0151",
    "下列哪一项最可能是一篇记叙文的写作目的（　　）",
    [
        "A. 介绍飞机的飞行原理",
        "B. 讲述一次难忘的旅行经历",
        "C. 列举不同国家的首都",
        "D. 论证网络利弊"
    ],
    "B", "kp_eng7_dis7_narration_purpose", 0.4,
    "B 涉及时间、地点、事件、感受，是记叙文典型写作目的。"
))

# kp_eng7_gra7_choice_question
items.append(fill_item(
    "eng_en_jr_0152",
    "填空：Would you like tea ______ coffee?",
    "or", "kp_eng7_gra7_choice_question", 0.35,
    "tea 与 coffee 是两个并列选项，用 or 连接构成选择疑问句。"
))

# kp_eng7_gra7_form_meaning_use
items.append(fill_item(
    "eng_en_jr_0153",
    "简答：语法学习中，'形式'指什么？请写出一个例句体现所学语法点的形式。",
    "She has finished her homework.",
    "kp_eng7_gra7_form_meaning_use", 0.5,
    "形式指语法结构（has finished）；例句体现现在完成时 have/has + 过去分词的结构形式。"
))

# kp_eng7_lis7_continuous_cmd
items.append(fill_item(
    "eng_en_jr_0154",
    "听到连续指令 'Take out your book, turn to page 5 and read after me.'，请写出你的反应动作。",
    "Take out my book, turn to page 5 and read after the teacher.", "kp_eng7_lis7_continuous_cmd", 0.35,
    "对连续指令作恰当反应：依次执行三个动作。",
    form="oral_qa"
))

# kp_eng7_lis7_spoken_gist
items.append(fill_item(
    "eng_en_jr_0155",
    "听力听后填空：这段口语材料的主题是 ______ (school life / travel / sports)。\n原文：'I usually get up at 6:30 and have breakfast with my family. Then I take the school bus...'",
    "school life", "kp_eng7_lis7_spoken_gist", 0.35,
    "关键词 get up / breakfast / school bus 指向 school life。"
))

# kp_eng7_lis7_visual_support
items.append(solve_item(
    "eng_en_jr_0156",
    "看图（一张同学们在操场踢球的图片）并听 'The students are playing football on the playground.'，请写出你理解到的关键信息。",
    "The students are playing football on the playground.",
    "kp_eng7_lis7_visual_support", 0.35,
    "结合图片（操场、踢球）与录音信息写出关键句。",
    form="oral_qa"
))

# kp_eng7_lsm7_goal_plan
items.append(choice_item(
    "eng_en_jr_0157",
    "制定英语学习目标时，下列哪一项最具体可行（　　）",
    [
        "A. 'My English will be perfect.'",
        "B. 'I will learn 5 new words every day this week.'",
        "C. 'I will study harder someday.'",
        "D. 'I want to be the best.'"
    ],
    "B", "kp_eng7_lsm7_goal_plan", 0.4,
    "B 有具体、可衡量、可执行的目标，符合 SMART 原则。"
))

# kp_eng7_lsm7_group_coop
items.append(fill_item(
    "eng_en_jr_0158",
    "填空：在小组合作学习中，每个人都应该承担 ______，并主动与同伴 ______。",
    "责任/交流", "kp_eng7_lsm7_group_coop", 0.4,
    "小组合作要求每个成员承担责任并积极交流。"
))

# kp_eng7_lsm7_motivation
items.append(choice_item(
    "eng_en_jr_0159",
    "降低英语学习焦虑的有效做法是（　　）",
    [
        "A. 完全不复习，盲目自信",
        "B. 制定小目标，多用兴趣材料",
        "C. 一直和别人比较",
        "D. 遇到困难就放弃"
    ],
    "B", "kp_eng7_lsm7_motivation", 0.35,
    "小目标+兴趣材料能保持动机、降低焦虑。"
))

# kp_eng7_lsm7_note_taking
items.append(fill_item(
    "eng_en_jr_0160",
    "填空：有效记笔记的常用方法包括记录关键词、使用 ______ 和画图示。",
    "缩写", "kp_eng7_lsm7_note_taking", 0.4,
    "有效记笔记包括关键词、缩写、图示等。"
))

# kp_eng7_lsm7_reading_strategies
items.append(solve_item(
    "eng_en_jr_0161",
    "阅读时遇到生词 (如 'enormous')，请写出 2 种可行的猜词策略。",
    "1. Look at the context to guess the meaning. 2. Look at the word parts: 'e-' means very, 'norm' relates to normal, so 'enormous' means very big.",
    "kp_eng7_lsm7_reading_strategies", 0.45,
    "常用猜词策略：上下文 + 构词法（前缀、词根）。",
    form="open_write"
))

# kp_eng7_prg7_intercultural
items.append(choice_item(
    "eng_en_jr_0162",
    "在英语国家做客时，主人说 'Would you like some more?'，下列哪种回应最得体（　　）",
    [
        "A. No, no, I'm fine.",
        "B. Yes, please. / No, thank you.",
        "C. Why?",
        "D. I don't know."
    ],
    "B", "kp_eng7_prg7_intercultural", 0.4,
    "得体回应：接受时说 Yes, please.；婉拒时说 No, thank you.。"
))

# kp_eng7_prg7_understand_feeling
items.append(fill_item(
    "eng_en_jr_0163",
    "听力听后填空：说话人说 'I'm so proud of you!' 时，表达的情感是 ______。",
    "自豪/骄傲", "kp_eng7_prg7_understand_feeling", 0.4,
    "proud of you 表达自豪、欣慰。"
))

# kp_eng7_red7_40k
items.append(fill_item(
    "eng_en_jr_0164",
    "填空：七年级课外阅读累计词量应不少于 ______ 词。",
    "4万", "kp_eng7_red7_40k", 0.3,
    "七年级课外阅读累计量 4 万词以上。"
))

# kp_eng7_red7_predict
items.append(fill_item(
    "eng_en_jr_0165",
    "看图（一张学生在操场上跑步的图片），预测文章最可能讲的主题：______",
    "校园运动/锻炼", "kp_eng7_red7_predict", 0.3,
    "图片中操场与跑步指向'校园运动'主题。"
))

# kp_eng7_red7_skim
items.append(fill_item(
    "eng_en_jr_0166",
    "填空：略读时主要关注每段的 ______ 和文章的 ______，不必逐字阅读。",
    "首句/主旨", "kp_eng7_red7_skim", 0.3,
    "略读关注段落首句（主题句）与全文主旨。"
))

# kp_eng7_red7_summarise_eval
items.append(fill_item(
    "eng_en_jr_0167",
    "用一句话概括下列短文主旨：'Mr Smith lost his dog. After three days, he found it. He was very happy.'",
    "Mr Smith lost his dog but found it after three days and felt very happy.", "kp_eng7_red7_summarise_eval", 0.45,
    "概括要点：人物+事件+结果，体现 who/what/how it ended。"
))

# kp_eng7_red7_written_main
items.append(fill_item(
    "eng_en_jr_0168",
    "填空：阅读书面语篇时，理解'整体意义'主要靠抓 ______ 与段落的 ______。",
    "主旨/主题句", "kp_eng7_red7_written_main", 0.35,
    "理解整体意义靠抓主旨和段落主题句。"
))

# kp_eng7_spk7_discourse
items.append(fill_item(
    "eng_en_jr_0169",
    "在朗读中，重音通常用于强调句子中的 ______。",
    "关键词", "kp_eng7_spk7_discourse", 0.35,
    "重音用于强调关键词（key words）。"
))

# kp_eng7_spk7_read_retell
items.append(solve_item(
    "eng_en_jr_0170",
    "朗读下列短文并复述大意：'Last Monday, our class went on a field trip. We visited a farm and learned about planting vegetables. We had a great time.'",
    "Last Monday, our class went on a field trip. We visited a farm and learned about planting vegetables. We had a great time.",
    "kp_eng7_spk7_read_retell", 0.5,
    "复述要点：时间(Monday) → 事件(field trip) → 地点(farm) → 学习内容(vegetables) → 感受(great)。",
    form="oral_qa"
))

# kp_eng7_spk7_topic_comm
items.append(solve_item(
    "eng_en_jr_0171",
    "你的英国笔友 Tom 想了解你的家庭。请用 2-3 句话向他介绍。",
    "There are four people in my family: my father, my mother, my sister and me. We often have dinner together. I love my family very much.",
    "kp_eng7_spk7_topic_comm", 0.45,
    "介绍家庭：人数+成员+家庭活动+感受。",
    form="oral_qa"
))

# kp_eng7_vie7_multimodal_meaning
items.append(fill_item(
    "eng_en_jr_0172",
    "看一张图（一位行人走在斑马线上、绿灯亮起），其主要传达的非文字信息是 ______。",
    "安全通行", "kp_eng7_vie7_multimodal_meaning", 0.35,
    "斑马线+绿灯图示传达'可安全通行'的信息。"
))

# kp_eng7_wri7_context_sentences
items.append(solve_item(
    "eng_en_jr_0173",
    "请围绕主题 'My Best Friend' 写 3-5 个意义连贯的语句。",
    "My best friend is Lily. She is kind and always helps me. We often read books together after school. I feel lucky to have such a good friend.",
    "kp_eng7_wri7_context_sentences", 0.45,
    "语句围绕同一主题展开，衔接自然，使用 We / She / I 等代词保持连贯。",
    form="open_write"
))

# kp_eng7_wri7_greeting_invite
items.append(solve_item(
    "eng_en_jr_0174",
    "请写一张英文生日贺卡给你的好朋友 Jack。",
    "Dear Jack, Happy Birthday! I hope you have a wonderful day and a great year ahead. Wishing you good health and lots of happiness. Your friend, Tom.",
    "kp_eng7_wri7_greeting_invite", 0.45,
    "生日贺卡要素：称呼+祝福+表达关心+署名。",
    form="essay"
))

# kp_eng7_wri7_story
items.append(solve_item(
    "eng_en_jr_0175",
    "请编写一个情节较为完整的小故事（不少于 50 词），主题：A Rainy Day。",
    "It was a rainy day last Saturday. I stayed at home and read a book. My mother made hot tea for me. In the afternoon, we watched a movie together. I enjoyed the warm and quiet day very much.",
    "kp_eng7_wri7_story", 0.55,
    "故事要素齐全：背景(雨天)→活动(读书、看电影)→感受(温暖)，情节完整。",
    form="narrative"
))

# kp_eng7_cul7_heritage (already 1)
items.append(fill_item(
    "eng_en_jr_0176",
    "填空：长城被列为 ______ 遗产（中文）。",
    "世界文化", "kp_eng7_cul7_heritage", 0.35,
    "长城是中国著名的世界文化遗产。"
))

# ============== Grade 8 supplements ==============

# kp_eng8_lis8_broadcast
items.append(choice_item(
    "eng_en_jr_0177",
    "收听 VOA / BBC 慢速英语时，下列哪项做法最有助于提高听力（　　）",
    [
        "A. 一遍听不懂就放弃",
        "B. 反复听并对照文本记录要点",
        "C. 只听自己喜欢的节目",
        "D. 永远不查生词"
    ],
    "B", "kp_eng8_lis8_broadcast", 0.45,
    "反复听+对照文本+记要点是高效练习方法。"
))

# kp_eng8_red8_100k
items.append(fill_item(
    "eng_en_jr_0178",
    "填空：八年级课外阅读累计词量应不少于 ______ 词。",
    "10万", "kp_eng8_red8_100k", 0.3,
    "八年级课外阅读累计量 10 万词以上。"
))

# kp_eng8_spk8_read_story
items.append(solve_item(
    "eng_en_jr_0179",
    "请流利朗读下面这段故事并复述大意：'A clever crow was thirsty. She saw a jar with a little water. She put stones into the jar until the water rose up. Then she drank.'",
    "A clever crow was thirsty. She saw a jar with a little water. She put stones into the jar until the water rose up. Then she drank.",
    "kp_eng8_spk8_read_story", 0.55,
    "复述要点：人物(clever crow)→问题(thirsty)→办法(stones)→结果(drank)。",
    form="oral_qa"
))

# kp_eng8_spk8_speech
items.append(solve_item(
    "eng_en_jr_0180",
    "请准备一段约 1 分钟的英语演讲，主题：Why Reading Is Important。",
    "Good afternoon, everyone. Reading is important for many reasons. First, reading helps us learn new ideas and words. Second, it makes us think more deeply. Third, reading brings us into different worlds. I hope everyone enjoys reading. Thank you!",
    "kp_eng8_spk8_speech", 0.55,
    "演讲要素：问候→主题→三点理由→总结→礼貌结尾。",
    form="oral_qa"
))

# kp_eng8_wri8_draft_revise
items.append(solve_item(
    "eng_en_jr_0181",
    "下面这篇作文需要修改，请列出至少两条具体修改建议：\n\n初稿：'My hobby. I like play football. It is fun. I play it every day.'",
    "修改建议：① 开头点明主题 'My hobby is playing football.' ② 用动名词 playing 而非 play ③ 增加细节（时间、地点、感受）。",
    "kp_eng8_wri8_draft_revise", 0.55,
    "修改要点：主题明确、语法正确、细节充分、结尾呼应。",
    form="open_write"
))

# kp_eng8_dis8_horiz_structure
items.append(fill_item(
    "eng_en_jr_0182",
    "填空：横向结构指围绕同一主题从多个 ______ 展开，纵向结构指按 ______ 或逻辑层层推进。",
    "方面/时间", "kp_eng8_dis8_horiz_structure", 0.5,
    "横向：同一主题的多个并列方面；纵向：时间或逻辑顺序推进。"
))

# kp_eng8_prg8_relation_appropriate
items.append(fill_item(
    "eng_en_jr_0183",
    "填空：在交际中照顾对方的身份与情感距离，需要注意礼貌用语、称谓与 ______。",
    "语气", "kp_eng8_prg8_relation_appropriate", 0.4,
    "照顾身份与情感距离要注意称谓、礼貌用语与语气。"
))

# kp_eng8_cul8_customs_compare
items.append(choice_item(
    "eng_en_jr_0184",
    "关于中外饮食习惯，下列说法正确的是（　　）",
    [
        "A. 中国人吃饭都用筷子",
        "B. 英美人吃饭都用筷子",
        "C. 中餐与西餐在餐具、主食、口味上都有不同",
        "D. 中国人从不吃牛肉"
    ],
    "C", "kp_eng8_cul8_customs_compare", 0.4,
    "C 客观反映了中外饮食差异；A、B、D 过于绝对。"
))

# kp_eng8_cul8_art_implication
items.append(fill_item(
    "eng_en_jr_0185",
    "填空：电影《阿凡达》中纳威人骑着斑溪兽飞翔的画面，其蕴含的主题之一是 ______ 与 ______。",
    "自由/保护自然", "kp_eng8_cul8_art_implication", 0.5,
    "该画面蕴含自由与自然保护等主题。"
))

# kp_eng8_cul8_labor_values
items.append(choice_item(
    "eng_en_jr_0186",
    "下列关于'工匠精神'的描述，最恰当的是（　　）",
    [
        "A. 追求速度、不顾质量",
        "B. 精益求精、专注执着",
        "C. 频繁跳槽",
        "D. 只看重结果不看过程"
    ],
    "B", "kp_eng8_cul8_labor_values", 0.45,
    "工匠精神强调精益求精、专注执着，是劳动精神的具体体现。"
))

# kp_eng8_lsm8_goal_monitoring
items.append(fill_item(
    "eng_en_jr_0187",
    "填空：'目标—监控—反思'中，'反思'指学习后对 ______ 和策略进行回顾总结。",
    "过程", "kp_eng8_lsm8_goal_monitoring", 0.4,
    "反思指学习后对过程、策略与结果进行总结。"
))

# kp_eng8_lsm8_grammar_pattern
items.append(solve_item(
    "eng_en_jr_0188",
    "请写出'现在完成时'的基本结构，并用一句英文举例。",
    "Structure: have/has + past participle. Example: I have finished my homework.",
    "kp_eng8_lsm8_grammar_pattern", 0.5,
    "总结规律并在新情境中运用：现在完成时 have/has + 过去分词。",
    form="open_write"
))

# kp_eng8_lsm8_monitor_appropriacy
items.append(choice_item(
    "eng_en_jr_0189",
    "给老师发邮件，下列称呼最得体的是（　　）",
    [
        "A. Hi!",
        "B. Dear Ms Wang,",
        "C. Hey teacher!",
        "D. Yo!"
    ],
    "B", "kp_eng8_lsm8_monitor_appropriacy", 0.35,
    "正式邮件应用 Dear + 姓氏/称谓。"
))

# kp_eng8_lsm8_persist_attitude
items.append(choice_item(
    "eng_en_jr_0190",
    "面对英语学习中的挫折，下列哪种做法最能体现坚持的态度（　　）",
    [
        "A. 一次失败就放弃",
        "B. 分析失败原因并继续努力",
        "C. 假装不在意",
        "D. 责怪老师"
    ],
    "B", "kp_eng8_lsm8_persist_attitude", 0.4,
    "分析原因+继续努力是面对挫折的正确做法。"
))

# kp_eng8_thm8_science_tech
items.append(choice_item(
    "eng_en_jr_0191",
    "下列哪一项是科技给生活带来的负面影响（　　）",
    [
        "A. 通讯更便利",
        "B. 信息更易获取",
        "C. 部分人沉迷手机影响视力与睡眠",
        "D. 学习资源更丰富"
    ],
    "C", "kp_eng8_thm8_science_tech", 0.45,
    "沉迷手机影响健康是科技的负面影响。"
))

# kp_eng8_thm8_identity
items.append(choice_item(
    "eng_en_jr_0192",
    "体现'身份认同与文化自信'的合适做法是（　　）",
    [
        "A. 盲目崇拜外国文化",
        "B. 主动介绍中华文化并取其精华",
        "C. 完全否定本民族文化",
        "D. 只学外语不学中文"
    ],
    "B", "kp_eng8_thm8_identity", 0.4,
    "主动介绍中华文化同时取长补短，体现文化自信。"
))

# kp_eng8_red8_main_idea_q
items.append(solve_item(
    "eng_en_jr_0193",
    "请用一句话概括下面短文的主旨大意：\n\n'Today, more and more people use shared bikes. They are cheap and good for the environment. However, some people leave them everywhere, which is a problem.'",
    "共享单车既环保又便宜，但乱停放是亟待解决的问题。",
    "kp_eng8_red8_main_idea_q", 0.5,
    "主旨兼顾两方面：优点（环保、便宜） + 问题（乱停放），概括要平衡。",
    form="comprehension"
))

# ============== Grade 9 supplements ==============

# kp_eng9_lis9_selective_note
items.append(solve_item(
    "eng_en_jr_0194",
    "假设你在听一段关于学校运动会的英语广播，请用 5 个关键词做记录（如活动名称、时间、地点、项目、结果）。",
    "Sports Day; next Friday; school playground; relay race; first prize.",
    "kp_eng9_lis9_selective_note", 0.5,
    "有选择地记录关键信息：人物/活动/时间/地点/结果。",
    form="listening"
))

# kp_eng9_red9_structure
items.append(fill_item(
    "eng_en_jr_0195",
    "填空：分析书面语篇的基本结构时，需要先识别各段的 ______ 和 ______。",
    "主题句/作用", "kp_eng9_red9_structure", 0.45,
    "通过段落主题句与段落在全文中的作用来分析结构。"
))

# kp_eng9_vie9_nonverbal_resource
items.append(fill_item(
    "eng_en_jr_0196",
    "一段视频中老师皱眉、停顿后说 'Are you sure?'，可推断其态度或意图是 ______。",
    "质疑/不确定", "kp_eng9_vie9_nonverbal_resource", 0.45,
    "皱眉+停顿+ Are you sure? 共同传达质疑、不确定的情感。"
))

# kp_eng9_spk9_opinion_reason
items.append(solve_item(
    "eng_en_jr_0197",
    "请用 3-4 句话表达你对'中学生是否应该做家务'的观点并说明理由。",
    "I think middle school students should help with housework. Doing chores teaches us to be responsible. It also helps our parents who are very busy. Housework is part of life skills, so it is good for us.",
    "kp_eng9_spk9_opinion_reason", 0.55,
    "观点句+理由 2 条+总结，体现思辨。",
    form="oral_qa"
))

# kp_eng9_spk9_oral_summary
items.append(solve_item(
    "eng_en_jr_0198",
    "请口头转述下面这段话的主要信息：\n\n'Mr Wang is a teacher from China. He went to the UK last year. He taught Chinese at a school there. He found the students were very interested in Chinese culture.'",
    "王老师去年去英国在一所学校教中文，学生们对中国文化很感兴趣。",
    "kp_eng9_spk9_oral_summary", 0.5,
    "转述要点：人物(Mr Wang)、地点(UK)、活动(teach Chinese)、发现(students interested)。",
    form="oral_qa"
))

# kp_eng9_wri9_draft_modify_finish
items.append(solve_item(
    "eng_en_jr_0199",
    "请独立完成下面的写作任务（不少于 60 词）：My Hobby。",
    "My hobby is collecting stamps. I started collecting stamps when I was eight. Each stamp tells a story about a country or an event. Through collecting, I learn about history and different cultures. It brings me a lot of joy.",
    "kp_eng9_wri9_draft_modify_finish", 0.6,
    "独立起草要点：开头点明爱好→开始时间→具体内容→收获与感受，结构完整。",
    form="essay"
))

# kp_eng9_wri9_chart_caption
items.append(solve_item(
    "eng_en_jr_0200",
    "你画了一张漫画，画面：一位小学生帮盲人过马路。请用 3-5 句话写出说明。",
    "In the picture, a primary school student sees a blind person near the road. He walks up to him and helps him cross the road safely. The blind man smiles and says 'Thank you, little boy.' The picture shows that kindness is everywhere if we care.",
    "kp_eng9_wri9_chart_caption", 0.55,
    "看图说明要素：人物+场景+动作+对话+寓意。",
    form="picture_qa"
))

# kp_eng9_dis9_argument_structure
items.append(fill_item(
    "eng_en_jr_0201",
    "填空：说理类语篇通常由论点、论据和 ______ 三部分构成。",
    "论证", "kp_eng9_dis9_argument_structure", 0.45,
    "论点+论据+论证是议论文的三要素。"
))

# kp_eng9_prg9_speech_style
items.append(fill_item(
    "eng_en_jr_0202",
    "填空：正式语体通常使用较复杂的句式和 ______ 词语，而非正式语体更接近 ______ 口语。",
    "书面/日常", "kp_eng9_prg9_speech_style", 0.4,
    "正式语体用书面词语；非正式语体接近日常口语。"
))

# kp_eng9_red9_150k
items.append(fill_item(
    "eng_en_jr_0203",
    "填空：九年级课外阅读累计词量应不少于 ______ 词。",
    "15万", "kp_eng9_red9_150k", 0.3,
    "九年级课外阅读累计量 15 万词以上。"
))

# kp_eng9_lsm9_plan_exam
items.append(choice_item(
    "eng_en_jr_0204",
    "中考复习计划中，下列哪项安排更合理（　　）",
    [
        "A. 临考前一周才开始",
        "B. 均匀分布各阶段任务，每周一个小目标",
        "C. 只复习喜欢的科目",
        "D. 完全不模拟训练"
    ],
    "B", "kp_eng9_lsm9_plan_exam", 0.45,
    "均匀分布+小目标+模拟训练是较合理的复习计划。"
))

# kp_eng9_lsm9_topic_plan
items.append(solve_item(
    "eng_en_jr_0205",
    "请按主题列出 3 个主题，每个主题下 2 个英语词汇（主题如：School Life）。",
    "1. School Life: classroom, textbook. 2. Food and Health: vegetable, fruit. 3. Environment: pollution, protect.",
    "kp_eng9_lsm9_topic_plan", 0.5,
    "按主题组织词汇，主题之间相对独立、每主题内词汇相关。",
    form="open_write"
))

# kp_eng9_lsm9_anxiety_control
items.append(choice_item(
    "eng_en_jr_0206",
    "下列哪种做法有助于降低考试焦虑（　　）",
    [
        "A. 考试前一天熬夜",
        "B. 深呼吸、积极自我暗示",
        "C. 完全不做准备",
        "D. 与他人过度比较"
    ],
    "B", "kp_eng9_lsm9_anxiety_control", 0.4,
    "深呼吸+积极暗示是有效降低焦虑的方法。"
))

# kp_eng9_thm9_volunteer
items.append(choice_item(
    "eng_en_jr_0207",
    "下列哪种行为属于志愿服务（　　）",
    [
        "A. 在社区打扫卫生",
        "B. 在家睡觉",
        "C. 玩游戏",
        "D. 逛街购物"
    ],
    "A", "kp_eng9_thm9_volunteer", 0.4,
    "在社区打扫卫生是无偿为公共利益服务的行为，属于志愿服务。"
))

# kp_eng9_thm9_env_protect
items.append(choice_item(
    "eng_en_jr_0208",
    "下列做法符合'保护环境'主题的是（　　）",
    [
        "A. 随手乱扔垃圾",
        "B. 节约用电",
        "C. 大量使用一次性筷子",
        "D. 砍伐森林"
    ],
    "B", "kp_eng9_thm9_env_protect", 0.35,
    "节约用电减少能源消耗，符合环保理念。"
))

# kp_eng9_cul9_country_profile
items.append(fill_item(
    "eng_en_jr_0209",
    "填空：Australia 的首都是 ______.",
    "Canberra", "kp_eng9_cul9_country_profile", 0.4,
    "澳大利亚的首都是 Canberra（堪培拉），不是 Sydney 或 Melbourne。"
))

# kp_eng9_cul9_health_finance_view
items.append(choice_item(
    "eng_en_jr_0210",
    "关于'健康观念'与'理财观念'的关系，下列说法正确的是（　　）",
    [
        "A. 完全无关",
        "B. 健康饮食需要合理消费，二者相互促进",
        "C. 只有健康重要",
        "D. 只有理财重要"
    ],
    "B", "kp_eng9_cul9_health_finance_view", 0.45,
    "健康与理财密切相关：理性消费可以支持健康饮食。"
))

print(f"Supplement items: {len(items)}")

# Save supplement
with open(os.path.join(OUT_DIR, "_temp_supplement.json"), "w", encoding="utf-8") as f:
    json.dump(items, f, ensure_ascii=False, indent=2)
print(f"Saved {len(items)} items to _temp_supplement.json")
