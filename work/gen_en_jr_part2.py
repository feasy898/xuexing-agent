# -*- coding: utf-8 -*-
"""Grade 8 items"""
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

# ----- kp_eng8_lis8_gist_detail -----
items.append(choice_item(
    "eng_en_jr_0071",
    "听一段关于学校运动会的短文，其要点不包括（　　）",
    [
        "A. 比赛项目",
        "B. 获奖情况",
        "C. 学生家庭住址",
        "D. 时间地点"
    ],
    "C", "kp_eng8_lis8_gist_detail", 0.4,
    "家庭住址属于个人隐私，不属于运动会广播的要点。"
))
items.append(choice_item(
    "eng_en_jr_0072",
    "在听力中抓住主旨要义的常用做法是（　　）",
    [
        "A. 听清每一个单词",
        "B. 注意开头和结尾的总结性句子",
        "C. 只听人名和数字",
        "D. 一边听一边翻译"
    ],
    "B", "kp_eng8_lis8_gist_detail", 0.4,
    "抓主旨要义关键在听首尾的总结性表达与反复出现的关键词。"
))

# ----- kp_eng8_lis8_feeling_attitude -----
items.append(choice_item(
    "eng_en_jr_0073",
    "说话人说 'I'm afraid we've missed the bus.' 时，最可能的情感是（　　）",
    [
        "A. 兴奋",
        "B. 遗憾/担心",
        "C. 愤怒",
        "D. 惊讶"
    ],
    "B", "kp_eng8_lis8_feeling_attitude", 0.4,
    "I'm afraid... 与 missed the bus 共同传达遗憾与担忧。"
))
items.append(choice_item(
    "eng_en_jr_0074",
    "判断说话者态度变化时，下面哪种语调线索最可靠（　　）",
    [
        "A. 语速始终不变",
        "B. 重音位置和语调升降",
        "C. 用词长短",
        "D. 背景音乐"
    ],
    "B", "kp_eng8_lis8_feeling_attitude", 0.45,
    "重音、语调升降最能反映情感态度变化。"
))

# ----- kp_eng8_lis8_broadcast -----
items.append(choice_item(
    "eng_en_jr_0075",
    "收听主题相关、语速较慢的英语节目时，下列做法不恰当的是（　　）",
    [
        "A. 提前预测主题",
        "B. 听不懂就立刻放弃",
        "C. 记下关键信息",
        "D. 听后复述要点"
    ],
    "B", "kp_eng8_lis8_broadcast", 0.4,
    "听不懂就放弃不利于听力提升，应结合预测、记录与复述策略。"
))

# ----- kp_eng8_red8_organise -----
items.append(choice_item(
    "eng_en_jr_0076",
    "梳理语篇脉络时，下列做法最有效的是（　　）",
    [
        "A. 只看首句",
        "B. 找出段落主题句并归纳每段大意",
        "C. 跳过段落直接看结尾",
        "D. 只关注生词"
    ],
    "B", "kp_eng8_red8_organise", 0.4,
    "通过主题句梳理段落大意，是把握脉络的有效方法。"
))
items.append(fill_item(
    "eng_en_jr_0077",
    "在英语语篇中，表示顺序的常用衔接词有 first, next, then, ______.",
    "finally", "kp_eng8_red8_organise", 0.35,
    "first / next / then / finally 是常见顺序衔接词。"
))

# ----- kp_eng8_red8_chart_interpret -----
items.append(choice_item(
    "eng_en_jr_0078",
    "一张折线图显示某城市 2010-2020 年汽车数量持续上升，最合理的解读是（　　）",
    [
        "A. 该城市人口减少",
        "B. 汽车数量逐年下降",
        "C. 汽车数量逐年上升",
        "D. 与年份无关"
    ],
    "C", "kp_eng8_red8_chart_interpret", 0.4,
    "折线整体上升，对应数量逐年增加。"
))
items.append(fill_item(
    "eng_en_jr_0079",
    "饼图常用于显示各部分占整体的______（百分比）。",
    "比例", "kp_eng8_red8_chart_interpret", 0.35,
    "饼图用于表示各部分占总体的比例（百分比）。"
))

# ----- kp_eng8_red8_novel_news -----
items.append(choice_item(
    "eng_en_jr_0080",
    "阅读英语短篇小说时，下列哪项最能帮助你理解情节（　　）",
    [
        "A. 跳过人物对话",
        "B. 抓住 who / what / when / where / why",
        "C. 只看标题",
        "D. 一字一句翻译"
    ],
    "B", "kp_eng8_red8_novel_news", 0.35,
    "5W（who/what/when/where/why）是理解小说情节的关键信息。"
))
items.append(solve_item(
    "eng_en_jr_0081",
    "阅读下面这则简短报刊文章（约 80 词）后回答：文章主要讲什么？\n\n'Last weekend, students from Sunshine Middle School visited the City Library. They read picture books and learned how to find books on the computer. Ms. Li, the librarian, said reading makes people think and grow.'",
    "Students from Sunshine Middle School visited the City Library and learned about reading and library use.",
    "kp_eng8_red8_novel_news", 0.45,
    "通过5W归纳：Who (students from Sunshine Middle School), What (visited library, learned reading), When (last weekend), Where (City Library)。",
    form="comprehension"
))

# ----- kp_eng8_red8_100k -----
items.append(choice_item(
    "eng_en_jr_0082",
    "课标要求八年级课外阅读累计词量至少（　　）",
    [
        "A. 4 万词以上",
        "B. 10 万词以上",
        "C. 15 万词以上",
        "D. 20 万词以上"
    ],
    "B", "kp_eng8_red8_100k", 0.3,
    "义教三级·八年级课外阅读累计量 10 万词以上。"
))

# ----- kp_eng8_spk8_read_story -----
items.append(solve_item(
    "eng_en_jr_0083",
    "请正确、流利地朗读并讲述这个小故事：'Once a little rabbit wanted to cross a river. He saw a big turtle. The turtle said, \"I can help you.\" The rabbit jumped on the turtle's back. The turtle carried him across the river safely.'",
    "Once a little rabbit wanted to cross a river. He saw a big turtle. The turtle said, 'I can help you.' The rabbit jumped on the turtle's back. The turtle carried him across the river safely.",
    "kp_eng8_spk8_read_story", 0.45,
    "朗读要点：意群停顿 (Once a little rabbit / wanted to cross a river.)；讲述要点按5W展开：who / what / where / how。",
    form="oral_qa"
))

# ----- kp_eng8_spk8_effective_comm -----
items.append(choice_item(
    "eng_en_jr_0084",
    "在特定情境（如医院）下询问某事，最恰当的英语表达是（　　）",
    [
        "A. You there, give me medicine!",
        "B. Excuse me, could you tell me where the doctor's office is?",
        "C. I want medicine.",
        "D. Where medicine?"
    ],
    "B", "kp_eng8_spk8_effective_comm", 0.4,
    "Excuse me, could you tell me... 是英语中礼貌询问的标准表达。"
))
items.append(fill_item(
    "eng_en_jr_0085",
    "在餐厅点餐时，你可以礼貌地问：'______, could I see the menu, please?'",
    "Excuse me", "kp_eng8_spk8_effective_comm", 0.35,
    "Excuse me 用于礼貌引起对方注意。"
))

# ----- kp_eng8_spk8_speech -----
items.append(solve_item(
    "eng_en_jr_0086",
    "请围绕 'My Favourite Hobby' 准备一段 1 分钟的英语主题演讲（含开头、要点、结尾）。",
    "Good morning, everyone. My favourite hobby is reading. I read for about 30 minutes every day. Reading helps me learn new words and ideas. It also makes me think about the world. I hope you can find a hobby you love too. Thank you!",
    "kp_eng8_spk8_speech", 0.5,
    "演讲要素：问候开头→主题明确→要点 2-3 条→呼吁/总结→礼貌结尾。注意语音、停顿与重音。",
    form="oral_qa"
))

# ----- kp_eng8_wri8_draft_revise -----
items.append(solve_item(
    "eng_en_jr_0087",
    "下面是一篇作文初稿，请按'主题—细节—结尾'结构在教师指导下修改并写出修改要点。\n\n初稿：'My weekend. I played. I watched TV. It was fun.'",
    "建议：① 开头点明主题 'My weekend was full of fun.' ② 中间增加细节 (时间、地点、感受) ③ 结尾呼应主题，总结感受。\n改写：My weekend was full of fun. On Saturday morning, I played basketball with my friends in the park. In the afternoon, I watched an interesting movie at home. On Sunday, I helped my mother with housework. I really enjoyed my weekend.",
    "kp_eng8_wri8_draft_revise", 0.5,
    "起草和修改作文：检查主题是否明确、细节是否充分、结尾是否呼应；按'主题—细节—结尾'结构修改。",
    form="open_write"
))

# ----- kp_eng8_gra8_progressive_vs_perfect -----
items.append(choice_item(
    "eng_en_jr_0088",
    "Look! The boys ______ football on the playground.（　　）",
    [
        "A. play",
        "B. are playing",
        "C. have played",
        "D. played"
    ],
    "B", "kp_eng8_gra8_progressive_vs_perfect", 0.4,
    "Look! 是现在进行时的标志词，用 are playing 强调动作正在进行。"
))
items.append(choice_item(
    "eng_en_jr_0089",
    "We ______ this film twice. Let's watch something else.（　　）",
    [
        "A. see",
        "B. are seeing",
        "C. have seen",
        "D. saw"
    ],
    "C", "kp_eng8_gra8_progressive_vs_perfect", 0.4,
    "twice 提示经历；'已经看过两次' 用现在完成时 have seen。"
))

# ----- kp_eng8_gra8_participle_attr -----
items.append(choice_item(
    "eng_en_jr_0090",
    "The ______ (break) window was repaired by Tom.（　　）",
    [
        "A. breaking",
        "B. broken",
        "C. break",
        "D. to break"
    ],
    "B", "kp_eng8_gra8_participle_attr", 0.45,
    "过去分词 broken 作定语，表示'被打碎的窗户'。"
))
items.append(fill_item(
    "eng_en_jr_0091",
    "填空：The ______ (interest) story attracted many readers.",
    "interesting", "kp_eng8_gra8_participle_attr", 0.45,
    "现在分词 interesting 修饰物，作定语表'令人感兴趣的'。"
))

# ----- kp_eng8_gra8_relative_who_whose -----
items.append(choice_item(
    "eng_en_jr_0092",
    "The man ______ car was stolen called the police.（　　）",
    [
        "A. who",
        "B. whom",
        "C. whose",
        "D. which"
    ],
    "C", "kp_eng8_gra8_relative_who_whose", 0.4,
    "先行词 the man 与 car 之间是所属关系，用 whose 引导定语从句。"
))
items.append(fill_item(
    "eng_en_jr_0093",
    "填空：The girl ______ won the prize is my sister.",
    "who", "kp_eng8_gra8_relative_who_whose", 0.35,
    "先行词 the girl 在从句中作主语，用 who。"
))

# ----- kp_eng8_gra8_subordinate_clause -----
items.append(choice_item(
    "eng_en_jr_0094",
    "I don't know ______ he will come tomorrow.（　　）",
    [
        "A. if",
        "B. when",
        "C. whether",
        "D. because"
    ],
    "A", "kp_eng8_gra8_subordinate_clause", 0.45,
    "know 后接宾语从句；'是否来'用 if / whether 引导，if 较口语化。"
))
items.append(choice_item(
    "eng_en_jr_0095",
    "______ he was ill, he still went to school.（　　）",
    [
        "A. Because",
        "B. Although",
        "C. If",
        "D. When"
    ],
    "B", "kp_eng8_gra8_subordinate_clause", 0.4,
    "前后为让步关系，用 Although。"
))

# ----- kp_eng8_dis8_horiz_structure -----
items.append(choice_item(
    "eng_en_jr_0096",
    "下列最能体现语篇'横向结构'的是（　　）",
    [
        "A. 按时间先后讲述故事",
        "B. 围绕同一主题展开多个方面",
        "C. 从原因到结果论述",
        "D. 由总述到分述"
    ],
    "B", "kp_eng8_dis8_horiz_structure", 0.5,
    "横向结构指围绕主题的多个并列方面；A 为时间纵向，C 为因果纵向，D 为总分纵向。"
))

# ----- kp_eng8_prg8_relation_appropriate -----
items.append(choice_item(
    "eng_en_jr_0097",
    "对老师表示关心，下列最得体的表达是（　　）",
    [
        "A. Hey teacher, sit down!",
        "B. Mr Wang, would you like a cup of tea?",
        "C. You, have tea!",
        "D. Hi man!"
    ],
    "B", "kp_eng8_prg8_relation_appropriate", 0.4,
    "称谓得体、Would you like...? 句式礼貌，符合对长辈的身份与情感距离。"
))

# ----- kp_eng8_cul8_customs_compare -----
items.append(choice_item(
    "eng_en_jr_0098",
    "关于中外礼仪，下列说法正确的是（　　）",
    [
        "A. 中国人见面都用拥抱",
        "B. 英美人在正式场合也会保持距离、礼貌握手",
        "C. 中国人从不鞠躬",
        "D. 英美人从不使用 'Please'"
    ],
    "B", "kp_eng8_cul8_customs_compare", 0.4,
    "英美正式场合多握手、保持礼貌距离；其他三项表述过于绝对。"
))

# ----- kp_eng8_cul8_art_implication -----
items.append(choice_item(
    "eng_en_jr_0099",
    "下列作品及其寓意对应正确的是（　　）",
    [
        "A. 《向日葵》—科技发展",
        "B. 《最后的晚餐》—背叛与牺牲",
        "C. 《蒙娜丽莎》—战争与和平",
        "D. 《清明上河图》—太空探索"
    ],
    "B", "kp_eng8_cul8_art_implication", 0.45,
    "达·芬奇《最后的晚餐》体现背叛与牺牲的主题；其他搭配错误。"
))

# ----- kp_eng8_cul8_labor_values -----
items.append(solve_item(
    "eng_en_jr_0100",
    "请围绕'劳动精神与工匠精神'写一段 50-70 词的短文，谈谈你的理解。",
    "Labour spirit means working hard and never giving up. A craftsman pays attention to every detail and tries to do his job better. We should respect every worker and learn from their spirit. As students, we should also be careful and patient with our studies.",
    "kp_eng8_cul8_labor_values", 0.5,
    "短文要点：解释劳动精神 + 工匠精神 + 结合学生身份谈做法，主题鲜明、逻辑清晰。",
    form="essay"
))

# ----- kp_eng8_lsm8_goal_monitoring -----
items.append(choice_item(
    "eng_en_jr_0101",
    "'目标—监控—反思'的元认知循环中，'监控'指的是（　　）",
    [
        "A. 定下大目标",
        "B. 学习中随时检查自己的理解与方法",
        "C. 考完试再总结",
        "D. 完全跟着老师走"
    ],
    "B", "kp_eng8_lsm8_goal_monitoring", 0.4,
    "监控指学习过程中随时检查自己的理解、策略与进度。"
))

# ----- kp_eng8_lsm8_grammar_pattern -----
items.append(choice_item(
    "eng_en_jr_0102",
    "学语法时'举一反三'的关键是（　　）",
    [
        "A. 死记硬背规则",
        "B. 总结规律并在新情境中运用",
        "C. 不学语法只看语感",
        "D. 只做一类题目"
    ],
    "B", "kp_eng8_lsm8_grammar_pattern", 0.4,
    "举一反三即发现语言规律，并在新情境中迁移运用。"
))

# ----- kp_eng8_lsm8_monitor_appropriacy -----
items.append(choice_item(
    "eng_en_jr_0103",
    "在写作中监控语言得体性，下列做法最直接的是（　　）",
    [
        "A. 看字数够不够",
        "B. 检查用词是否符合对象与场合",
        "C. 看是否有标题",
        "D. 看字体是否工整"
    ],
    "B", "kp_eng8_lsm8_monitor_appropriacy", 0.4,
    "得体性指语言要符合交际对象与场合，需在写作中随时检查用词与语气。"
))

# ----- kp_eng8_lsm8_persist_attitude -----
items.append(solve_item(
    "eng_en_jr_0104",
    "面对英语学习中的挫折（如考试成绩不理想），请用 2-3 句话写出保持坚持的具体做法。",
    "When I fail in English, I don't give up. I find out why I made mistakes and try to improve. I keep practising every day and believe I can do better next time.",
    "kp_eng8_lsm8_persist_attitude", 0.4,
    "面对挫折的态度：分析原因 + 持续练习 + 自我鼓励；要点具体积极。",
    form="open_write"
))

# ----- kp_eng8_thm8_science_tech -----
items.append(solve_item(
    "eng_en_jr_0105",
    "请围绕 'Technology in Our Life' 写一段 50-70 词的短文，说明一种你熟悉的科技如何改变生活。",
    "Smartphones have changed our life a lot. With a smartphone, we can talk with friends, read news and find directions easily. However, we should not spend too much time on it. Use technology in a smart way.",
    "kp_eng8_thm8_science_tech", 0.5,
    "主题为'科技与生活'，要点：科技带来的便利 + 适度使用的反思，体现思辨性。",
    form="essay"
))

# ----- kp_eng8_thm8_identity -----
items.append(solve_item(
    "eng_en_jr_0106",
    "请围绕 'Chinese Culture I'm Proud of' 写一段 50-70 词的短文。",
    "I am proud of Chinese culture. The Great Wall shows the wisdom of ancient people. Traditional festivals like the Spring Festival bring families together. I want to introduce our culture to the world.",
    "kp_eng8_thm8_identity", 0.5,
    "主题为'身份认同与文化自信'，要点：文化符号 + 个人感受 + 弘扬意愿，主题鲜明。",
    form="essay"
))

# ----- kp_eng8_red8_main_idea_q -----
items.append(choice_item(
    "eng_en_jr_0107",
    "做主旨大意题时，最可靠的判断依据是（　　）",
    [
        "A. 文章第一句的逐字翻译",
        "B. 综合各段主题句与全文高频词",
        "C. 自己最熟悉的话题",
        "D. 最后一段的长度"
    ],
    "B", "kp_eng8_red8_main_idea_q", 0.4,
    "主旨大意要综合段落主题句与高频词，而非单一信息。"
))

# ----- kp_eng8_red8_word_guess -----
items.append(choice_item(
    "eng_en_jr_0108",
    "句子 'He is an avid reader. He reads several books a week.' 中 'avid' 最可能的意思是（　　）",
    [
        "A. 偶尔的",
        "B. 狂热的、热衷的",
        "C. 疲倦的",
        "D. 严厉的"
    ],
    "B", "kp_eng8_red8_word_guess", 0.45,
    "后文 'several books a week' 说明他阅读量大，故 avid 意为'狂热的'。"
))
items.append(fill_item(
    "eng_en_jr_0109",
    "猜测词义：'The plant withered because of the long drought.' withered 意为______.",
    "枯萎", "kp_eng8_red8_word_guess", 0.45,
    "由因果关系 because of the long drought 可推断 withered 意为'枯萎'。"
))

print(f"Grade 8: {len(items)} items")

# Save grade 8 items
with open(os.path.join(OUT_DIR, "_temp_g8.json"), "w", encoding="utf-8") as f:
    json.dump(items, f, ensure_ascii=False, indent=2)
print(f"Saved {len(items)} items to _temp_g8.json")
