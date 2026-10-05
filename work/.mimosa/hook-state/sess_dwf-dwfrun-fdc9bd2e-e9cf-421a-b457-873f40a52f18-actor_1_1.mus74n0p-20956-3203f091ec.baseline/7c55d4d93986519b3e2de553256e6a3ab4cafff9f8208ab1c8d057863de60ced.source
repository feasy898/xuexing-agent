# -*- coding: utf-8 -*-
"""
Generate English junior high (grades 7-9) candidate items per KP.
Output: en_jr_public.json, en_jr_full.json, en_jr_ledger_gen.json
"""
import json, os, sys

OUT_DIR = "data/verification/candidates_en"
os.makedirs(OUT_DIR, exist_ok=True)

# ----- helpers -----
def choice_item(qid, stem, opts, answer, kp, difficulty, solution, form="multiple_choice", item_type="choice"):
    return {
        "id": qid, "item_type": item_type, "form": form, "stem": stem,
        "answer": answer, "kps": [kp], "difficulty": difficulty,
        "solution": solution, "source": "llm_generated", "options": opts,
    }

def fill_item(qid, stem, answer, kp, difficulty, solution, form="fill", item_type="fill"):
    return {
        "id": qid, "item_type": item_type, "form": form, "stem": stem,
        "answer": answer, "kps": [kp], "difficulty": difficulty,
        "solution": solution, "source": "llm_generated",
    }

def solve_item(qid, stem, answer, kp, difficulty, solution, form, item_type="solve", writing_prompt=None):
    item = {
        "id": qid, "item_type": item_type, "form": form, "stem": stem,
        "answer": answer, "kps": [kp], "difficulty": difficulty,
        "solution": solution, "source": "llm_generated",
    }
    if writing_prompt:
        item["writing_prompt"] = writing_prompt
    return item

# ============== GRADE 7 ==============
items = []

# ----- kp_eng7_pha7_meaning (语音的表意功能) -----
items.append(choice_item(
    "eng_en_jr_0001",
    "下列句子中，重音位置不同会改变句子意思的一项是（　　）",
    [
        "A. I didn't say he stole the money. （我没说他偷了钱。）",
        "B. I didn't say he stole the money. （我说的是，他没偷钱。）",
        "C. I didn't say he stole the money. （我没说过偷钱这件事。）",
        "D. I didn't say he stole the money. （我没说他偷了——他是借的。）"
    ],
    "A", "kp_eng7_pha7_meaning", 0.4,
    "重音落在不同单词上，所强调的内容不同，句意也随之改变。这是英语语音的表意功能。"
))
items.append(choice_item(
    "eng_en_jr_0002",
    "在句子 'Are you going to the party?' 中，升调通常表示（　　）",
    [
        "A. 肯定的陈述",
        "B. 询问或不确定",
        "C. 命令",
        "D. 强烈感叹"
    ],
    "B", "kp_eng7_pha7_meaning", 0.35,
    "一般疑问句末尾用升调，表示询问、不确定或请求确认。"
))

# ----- kp_eng7_pha7_phonetics_spelling (音标拼读) -----
items.append(choice_item(
    "eng_en_jr_0003",
    "下列单词中，元音发音不同的是（　　）",
    [
        "A. cake",
        "B. name",
        "C. cat",
        "D. plane"
    ],
    "C", "kp_eng7_pha7_phonetics_spelling", 0.35,
    "cake / name / plane 中 a 发 /eɪ/；cat 中 a 发 /æ/，故选 C。"
))
items.append(fill_item(
    "eng_en_jr_0004",
    "根据音标 /bɪˈkʌz/ 写出对应的单词：______",
    "because", "kp_eng7_pha7_phonetics_spelling", 0.3,
    "/bɪˈkʌz/ 对应的单词为 because，重音在第二个音节。"
))

# ----- kp_eng7_voc7_meaning_function (词义、词性与功能) -----
items.append(choice_item(
    "eng_en_jr_0005",
    "句子 'She runs fast.' 中 'fast' 的词性是（　　）",
    [
        "A. 形容词",
        "B. 副词",
        "C. 名词",
        "D. 动词"
    ],
    "B", "kp_eng7_voc7_meaning_function", 0.35,
    "修饰动词 runs，应为副词 fast（快地）。"
))
items.append(choice_item(
    "eng_en_jr_0006",
    "'book' 在 'I read a book.' 与 'Please book a table.' 中分别是（　　）",
    [
        "A. 都是名词",
        "B. 都是动词",
        "C. 前者是名词，后者是动词",
        "D. 前者是动词，后者是名词"
    ],
    "C", "kp_eng7_voc7_meaning_function", 0.45,
    "a book（书，名词）vs book a table（预订，动词），同一词形在不同语境下词性不同。"
))

# ----- kp_eng7_voc7_1600 (1600词) -----
items.append(fill_item(
    "eng_en_jr_0007",
    "写出下列汉语对应的英语单词：'家庭' ______",
    "family", "kp_eng7_voc7_1600", 0.3,
    "家庭对应的英语单词为 family。"
))
items.append(choice_item(
    "eng_en_jr_0008",
    "下列哪个不是七年级应该掌握的常见词汇（　　）",
    [
        "A. happy",
        "B. family",
        "C. epiphany",
        "D. school"
    ],
    "C", "kp_eng7_voc7_1600", 0.3,
    "happy / family / school 均为初中阶段基础词；epiphany 较为生僻，不在七年级常见词范围。"
))

# ----- kp_eng7_voc7_collocation (固定搭配) -----
items.append(choice_item(
    "eng_en_jr_0009",
    "选出正确搭配：'听音乐' 应为（　　）",
    [
        "A. listen music",
        "B. listen to music",
        "C. hear music",
        "D. hear to music"
    ],
    "B", "kp_eng7_voc7_collocation", 0.3,
    "listen 是不及物动词，表示'听……'需加介词 to，即 listen to music。"
))
items.append(fill_item(
    "eng_en_jr_0010",
    "完成固定搭配：'look ______ the picture'（看图片）",
    "at", "kp_eng7_voc7_collocation", 0.3,
    "look at 为固定搭配，意为'看'。"
))

# ----- kp_eng7_voc7_derive_compound (合成法与派生法) -----
items.append(fill_item(
    "eng_en_jr_0011",
    "写出单词 classroom 的构成方式：它是______法构成的复合词（class + room）。",
    "合成", "kp_eng7_voc7_derive_compound", 0.4,
    "classroom 由 class 与 room 两个独立词直接拼合而成，属于合成法。"
))
items.append(choice_item(
    "eng_en_jr_0012",
    "单词 unhappy 由哪种构词法构成（　　）",
    [
        "A. 合成法",
        "B. 派生法（加前缀 un-）",
        "C. 派生法（加后缀 -y）",
        "D. 转化法"
    ],
    "B", "kp_eng7_voc7_derive_compound", 0.4,
    "un- 是前缀，加在形容词 happy 前构成反义词 unhappy，属于派生法。"
))

# ----- kp_eng7_gra7_form_meaning_use -----
items.append(choice_item(
    "eng_en_jr_0013",
    "下列句子体现了语法的'使用'维度的一项是（　　）",
    [
        "A. 现在完成时表示过去发生并与现在有联系的动作。",
        "B. 现在完成时的结构是 have/has + 过去分词。",
        "C. 现在完成时常与 for / since 连用。",
        "D. 现在完成时在口语中比过去时更常见。"
    ],
    "D", "kp_eng7_gra7_form_meaning_use", 0.5,
    "'使用'指语法在真实语境中的选择与得体性。A 属意义、B 属形式、C 属意义/形式，只有 D 谈使用。"
))

# ----- kp_eng7_gra7_sent_types (句子种类) -----
items.append(choice_item(
    "eng_en_jr_0014",
    "'What a beautiful day!' 属于（　　）",
    [
        "A. 陈述句",
        "B. 疑问句",
        "C. 感叹句",
        "D. 祈使句"
    ],
    "C", "kp_eng7_gra7_sent_types", 0.3,
    "由 What 引导并以感叹号结尾的句子为感叹句。"
))
items.append(fill_item(
    "eng_en_jr_0015",
    "将下列句子改成否定句：'He is a student.' → He ______ a student.",
    "is not", "kp_eng7_gra7_sent_types", 0.3,
    "be 动词 is 后直接加 not 构成否定：He is not a student."
))

# ----- kp_eng7_gra7_tense_simple_present (一般现在时) -----
items.append(choice_item(
    "eng_en_jr_0016",
    "She ______ to school every day.（　　）",
    [
        "A. go",
        "B. goes",
        "C. going",
        "D. went"
    ],
    "B", "kp_eng7_gra7_tense_simple_present", 0.3,
    "主语为第三人称单数 She，一般现在时的实义动词需加 -s/-es，go 加 -es 变 goes。"
))
items.append(fill_item(
    "eng_en_jr_0017",
    "用括号内动词的正确形式填空：They ______ (play) football after school every day.",
    "play", "kp_eng7_gra7_tense_simple_present", 0.3,
    "They 为复数主语，every day 提示习惯性动作，用一般现在时原形 play。"
))

# ----- kp_eng7_gra7_tense_present_perfect (现在完成时) -----
items.append(choice_item(
    "eng_en_jr_0018",
    "I ______ already ______ my homework.（　　）",
    [
        "A. has / finished",
        "B. have / finished",
        "C. had / finished",
        "D. am / finished"
    ],
    "B", "kp_eng7_gra7_tense_present_perfect", 0.35,
    "现在完成时结构：have/has + 过去分词。主语 I 用 have，finish 的过去分词为 finished。"
))
items.append(fill_item(
    "eng_en_jr_0019",
    "用现在完成时填空：She ______ (be) to Beijing twice.",
    "has been", "kp_eng7_gra7_tense_present_perfect", 0.35,
    "主语 She 用 has，twice 提示经历用现在完成时，be 的过去分词为 been。"
))

# ----- kp_eng7_gra7_voice_present (一般现在时被动) -----
items.append(choice_item(
    "eng_en_jr_0020",
    "English ______ in many countries.（　　）",
    [
        "A. is spoken",
        "B. speaks",
        "C. is speak",
        "D. spoken"
    ],
    "A", "kp_eng7_gra7_voice_present", 0.4,
    "主语 English 是动作 speak 的承受者，用一般现在时被动语态 is spoken。"
))
items.append(fill_item(
    "eng_en_jr_0021",
    "改写为被动语态：They clean the classroom every day. → The classroom ______ every day.",
    "is cleaned", "kp_eng7_gra7_voice_present", 0.45,
    "一般现在时被动：主语 The classroom + is + 过去分词 cleaned。every day 提示一般现在时。"
))

# ----- kp_eng7_gra7_nonfinite_infinitive (不定式) -----
items.append(choice_item(
    "eng_en_jr_0022",
    "I want ______ a movie this weekend.（　　）",
    [
        "A. watch",
        "B. watching",
        "C. to watch",
        "D. watched"
    ],
    "C", "kp_eng7_gra7_nonfinite_infinitive", 0.4,
    "want 后接不定式作宾语，即 want to do sth."
))
items.append(fill_item(
    "eng_en_jr_0023",
    "用不定式填空：He works hard ______ (pass) the exam.",
    "to pass", "kp_eng7_gra7_nonfinite_infinitive", 0.4,
    "此处不定式作目的状语，修饰动词 works。"
))

# ----- kp_eng7_gra7_coordinate (并列复合句) -----
items.append(choice_item(
    "eng_en_jr_0024",
    "I like apples ______ oranges.（　　）",
    [
        "A. but",
        "B. and",
        "C. or",
        "D. because"
    ],
    "B", "kp_eng7_gra7_coordinate", 0.3,
    "两个并列的喜欢对象，用 and 连接。"
))
items.append(fill_item(
    "eng_en_jr_0025",
    "用合适的并列连词填空：Hurry up, ______ you will be late.",
    "or", "kp_eng7_gra7_coordinate", 0.4,
    "or 表示'否则'，连接两个并列分句。"
))

# ----- kp_eng7_gra7_adverbial_clause (状语从句) -----
items.append(choice_item(
    "eng_en_jr_0026",
    "______ it rained heavily, we still went out.（　　）",
    [
        "A. Because",
        "B. Although",
        "C. If",
        "D. When"
    ],
    "B", "kp_eng7_gra7_adverbial_clause", 0.4,
    "句意'虽然下大雨，我们仍出门'，应用 Although 引导让步状语从句。"
))
items.append(fill_item(
    "eng_en_jr_0027",
    "用合适连词填空：I will call you ______ I arrive.",
    "when", "kp_eng7_gra7_adverbial_clause", 0.4,
    "时间状语从句用 when 引导。"
))

# ----- kp_eng7_gra7_relative_clause_intro (定语从句) -----
items.append(choice_item(
    "eng_en_jr_0028",
    "The boy ______ is standing there is my brother.（　　）",
    [
        "A. who",
        "B. which",
        "C. whose",
        "D. whom"
    ],
    "A", "kp_eng7_gra7_relative_clause_intro", 0.4,
    "先行词 the boy 为人，且在从句中作主语，用 who。"
))
items.append(fill_item(
    "eng_en_jr_0029",
    "填空：This is the book ______ I bought yesterday.",
    "which", "kp_eng7_gra7_relative_clause_intro", 0.4,
    "先行词 the book 为物，在从句中作 bought 的宾语，用 which。"
))

# ----- kp_eng7_gra7_subject_verb_agree (主谓一致) -----
items.append(choice_item(
    "eng_en_jr_0030",
    "The list of items ______ on the table.（　　）",
    [
        "A. are",
        "B. is",
        "C. were",
        "D. have"
    ],
    "B", "kp_eng7_gra7_subject_verb_agree", 0.45,
    "真正主语为单数 list（介词短语 of items 是定语），谓语用 is。"
))
items.append(fill_item(
    "eng_en_jr_0031",
    "填空：Either he or I ______ wrong.",
    "am", "kp_eng7_gra7_subject_verb_agree", 0.45,
    "either...or... 连接主语时谓语就近一致，I 后用 am。"
))

# ----- kp_eng7_gra7_pronoun_system (代词系统) -----
items.append(choice_item(
    "eng_en_jr_0032",
    "This is my book. ______ is over there.（　　）",
    [
        "A. Your",
        "B. Yours",
        "C. You",
        "D. Your book"
    ],
    "B", "kp_eng7_gra7_pronoun_system", 0.3,
    "句意为'你的（书）在那儿'，用名词性物主代词 yours。"
))
items.append(fill_item(
    "eng_en_jr_0033",
    "填空：Tom hurt ______ while playing football. (he)",
    "himself", "kp_eng7_gra7_pronoun_system", 0.35,
    "Tom 自己受伤了，用反身代词 himself。"
))

# ----- kp_eng7_dis7_narration_purpose (记叙文写作目的) -----
items.append(choice_item(
    "eng_en_jr_0034",
    "下列哪一项不是记叙文的常见写作目的（　　）",
    [
        "A. 讲述个人经历",
        "B. 介绍发明原理",
        "C. 复述事件过程",
        "D. 分享有趣故事"
    ],
    "B", "kp_eng7_dis7_narration_purpose", 0.4,
    "介绍发明原理属于说明文范畴，不属于记叙文。"
))

# ----- kp_eng7_dis7_cohesion (衔接与连贯) -----
items.append(choice_item(
    "eng_en_jr_0035",
    "下列选项中能正确衔接句子 'I was tired. ______, I kept on working.' 的是（　　）",
    [
        "A. Because",
        "B. However",
        "C. So",
        "D. And"
    ],
    "B", "kp_eng7_dis7_cohesion", 0.4,
    "'累'与'继续工作'为转折关系，用 However 衔接。"
))
items.append(fill_item(
    "eng_en_jr_0036",
    "填入合适的过渡词：First, ______ the vegetables. Then put them in the pan.",
    "wash", "kp_eng7_dis7_cohesion", 0.35,
    "按时间顺序，First 后接动词原形 wash 表示动作先后。"
))

# ----- kp_eng7_prg7_request_offer (请求与提供) -----
items.append(choice_item(
    "eng_en_jr_0037",
    "下列句子中礼貌请求帮助的表达是（　　）",
    [
        "A. Give me the book.",
        "B. Could you pass me the book?",
        "C. You should give me the book.",
        "D. Why not give me the book?"
    ],
    "B", "kp_eng7_prg7_request_offer", 0.3,
    "Could you... 是礼貌请求的标准表达。"
))
items.append(fill_item(
    "eng_en_jr_0038",
    "完成对话：A: Would you like some tea? B: ______, please.",
    "Yes", "kp_eng7_prg7_request_offer", 0.3,
    "接受对方的提供用 Yes, please. 回答。"
))

# ----- kp_eng7_prg7_understand_feeling (理解情感态度) -----
items.append(choice_item(
    "eng_en_jr_0039",
    "说话人说 'Well, I suppose it might be okay.' 时，最可能的情感是（　　）",
    [
        "A. 高兴",
        "B. 怀疑或勉强",
        "C. 兴奋",
        "D. 愤怒"
    ],
    "B", "kp_eng7_prg7_understand_feeling", 0.4,
    "suppose / might / well 等词体现说话人犹豫、勉强的态度。"
))

# ----- kp_eng7_prg7_intercultural (跨文化语用) -----
items.append(choice_item(
    "eng_en_jr_0040",
    "在英美文化中，接受别人的赞美时常见的得体回应是（　　）",
    [
        "A. 谦虚地否认（No, I am not good at all.）",
        "B. 微笑并说 'Thank you.'",
        "C. 转移话题",
        "D. 继续自夸"
    ],
    "B", "kp_eng7_prg7_intercultural", 0.45,
    "英语文化中接受赞美时直接说 Thank you 较为得体；过分谦虚反而不自然。"
))

# ----- kp_eng7_cul7_etiquette (待人接物礼仪) -----
items.append(choice_item(
    "eng_en_jr_0041",
    "在英语国家，第一次见面打招呼最常见的方式是（　　）",
    [
        "A. 鞠躬",
        "B. 拥抱",
        "C. 微笑并说 'Hello / Nice to meet you.'",
        "D. 亲吻脸颊"
    ],
    "C", "kp_eng7_cul7_etiquette", 0.3,
    "英语国家日常初次见面多为礼貌问候，不一定拥抱或亲吻。"
))

# ----- kp_eng7_cul7_role_models (代表人物) -----
items.append(choice_item(
    "eng_en_jr_0042",
    "下列哪位不属于具有优秀品格的中外代表人物（　　）",
    [
        "A. Lei Feng (雷锋)",
        "B. Norman Bethune (白求恩)",
        "C. Albert Einstein",
        "D. A fictional cartoon character without story"
    ],
    "D", "kp_eng7_cul7_role_models", 0.4,
    "没有故事背景的虚构卡通人物不属于课标所指的代表人物。"
))

# ----- kp_eng7_cul7_festivals (节日) -----
items.append(choice_item(
    "eng_en_jr_0043",
    "Christmas Day is celebrated on ______ every year.（　　）",
    [
        "A. October 31",
        "B. December 25",
        "C. November 25",
        "D. January 1"
    ],
    "B", "kp_eng7_cul7_festivals", 0.3,
    "圣诞节为每年的 12 月 25 日。"
))
items.append(fill_item(
    "eng_en_jr_0044",
    "写出中秋节对应的英文：______ Festival",
    "Mid-Autumn", "kp_eng7_cul7_festivals", 0.3,
    "中秋节的英文为 Mid-Autumn Festival。"
))

# ----- kp_eng7_cul7_health_view (健康观念) -----
items.append(choice_item(
    "eng_en_jr_0045",
    "下列哪种做法最符合英语国家'珍爱生命'的健康观念（　　）",
    [
        "A. 长时间熬夜玩游戏",
        "B. 规律运动与均衡饮食",
        "C. 不吃早餐只吃零食",
        "D. 独自一人去陌生水域游泳"
    ],
    "B", "kp_eng7_cul7_health_view", 0.35,
    "规律运动、均衡饮食是国际普遍认可的健康生活方式。"
))

# ----- kp_eng7_cul7_heritage (遗产) -----
items.append(choice_item(
    "eng_en_jr_0046",
    "下列哪一项是中国的世界文化遗产（　　）",
    [
        "A. The Great Wall",
        "B. Eiffel Tower",
        "C. Statue of Liberty",
        "D. Sydney Opera House"
    ],
    "A", "kp_eng7_cul7_heritage", 0.3,
    "长城是中国著名的世界文化遗产；B、C、D 分别为法、美、澳。"
))

# ----- kp_eng7_lis7_continuous_cmd (连续指令反应) -----
items.append(choice_item(
    "eng_en_jr_0047",
    "听到连续指令 'Stand up, open your book and turn to page 12.' 后，最恰当的反应是（　　）",
    [
        "A. 立刻坐下",
        "B. 起立并翻到第 12 页",
        "C. 只起立",
        "D. 只翻书"
    ],
    "B", "kp_eng7_lis7_continuous_cmd", 0.3,
    "连续指令需要依次执行三个动作：起立→打开书→翻到第 12 页。"
))

# ----- kp_eng7_lis7_spoken_gist (口语主旨) -----
items.append(choice_item(
    "eng_en_jr_0048",
    "一段口语材料主要讲述作者假期去了海边、晒太阳并吃了海鲜，这段话的主题是（　　）",
    [
        "A. 学校生活",
        "B. 海滨度假",
        "C. 节日庆典",
        "D. 家庭聚会"
    ],
    "B", "kp_eng7_lis7_spoken_gist", 0.35,
    "关键词 beach / sun / seafood 指向海滨度假。"
))

# ----- kp_eng7_lis7_visual_support (视觉辅助理解) -----
items.append(choice_item(
    "eng_en_jr_0049",
    "看图（一张学生在实验室做实验的图片）并听录音 'The students are doing an experiment in the lab.'，可推断场景是（　　）",
    [
        "A. 操场",
        "B. 实验室",
        "C. 教室上课",
        "D. 图书馆"
    ],
    "B", "kp_eng7_lis7_visual_support", 0.3,
    "结合图片中的实验器材与录音中的 lab，可推断场景为实验室。"
))

# ----- kp_eng7_red7_written_main (书面语篇主旨) -----
items.append(choice_item(
    "eng_en_jr_0050",
    "阅读短文标题 'How to Keep Healthy'，文章最可能的主要内容是（　　）",
    [
        "A. 介绍一种新游戏",
        "B. 介绍保持健康的方法",
        "C. 讲述旅行故事",
        "D. 描述一部电影"
    ],
    "B", "kp_eng7_red7_written_main", 0.3,
    "标题直接揭示主题——保持健康的方法。"
))

# ----- kp_eng7_red7_predict (预测) -----
items.append(choice_item(
    "eng_en_jr_0051",
    "看到标题 'A Lost Dog' 与一张小狗的图片，你预测文章最可能讲的是（　　）",
    [
        "A. 狗的品种",
        "B. 走失小狗与寻找的故事",
        "C. 训狗方法",
        "D. 宠物店介绍"
    ],
    "B", "kp_eng7_red7_predict", 0.3,
    "标题与图片都指向'走失的狗'这一故事线索。"
))

# ----- kp_eng7_red7_summarise_eval (概括评价) -----
items.append(choice_item(
    "eng_en_jr_0052",
    "下列最能概括短文主旨的是（　　）",
    [
        "A. A report on a science experiment.",
        "B. A story about kindness between strangers.",
        "C. A guide to using a computer.",
        "D. An advertisement for a sports meet."
    ],
    "B", "kp_eng7_red7_summarise_eval", 0.4,
    "短文围绕陌生人之间的善意展开，最佳概括为 B。"
))

# ----- kp_eng7_red7_40k (七年级 4 万词) -----
items.append(choice_item(
    "eng_en_jr_0053",
    "依据课标，七年级课外阅读累计词量至少应达到（　　）",
    [
        "A. 1 万词",
        "B. 4 万词以上",
        "C. 10 万词",
        "D. 15 万词"
    ],
    "B", "kp_eng7_red7_40k", 0.3,
    "义教三级·七年级课外阅读累计量 4 万词以上。"
))

# ----- kp_eng7_vie7_multimodal_meaning (多模态非文字) -----
items.append(choice_item(
    "eng_en_jr_0054",
    "一张图标显示一只被划掉的香烟，其传达的核心信息是（　　）",
    [
        "A. 欢迎吸烟",
        "B. 禁止吸烟",
        "C. 售卖香烟",
        "D. 讨论吸烟"
    ],
    "B", "kp_eng7_vie7_multimodal_meaning", 0.3,
    "图形 + 划线（禁止符号）传达禁止吸烟的语义。"
))

# ----- kp_eng7_spk7_read_retell (朗读复述) -----
items.append(solve_item(
    "eng_en_jr_0055",
    "朗读并复述：Yesterday I went to the park with my family. We had a picnic under a big tree. My mother made sandwiches and my father played games with us.",
    "Yesterday I went to the park with my family. We had a picnic under a big tree. My mother made sandwiches and my father played games with us.",
    "kp_eng7_spk7_read_retell", 0.4,
    "完整连贯朗读短文并按顺序复述大意：时间(yesterday)→地点(park)→活动(picnic)→细节(sandwiches / games)。",
    form="oral_qa"
))

# ----- kp_eng7_spk7_topic_comm (主题交际) -----
items.append(solve_item(
    "eng_en_jr_0056",
    "假设你的朋友 Tom 想了解你最喜欢的学科，请用 2-3 句话向他介绍。",
    "My favourite subject is English. I think it is very interesting and useful. I like my English teacher because her classes are lively and fun.",
    "kp_eng7_spk7_topic_comm", 0.4,
    "围绕主题用简短表达完成交际：先点出最喜欢学科→说明原因→进一步描述，整体 2-3 句。",
    form="oral_qa"
))

# ----- kp_eng7_spk7_discourse (重音强调) -----
items.append(choice_item(
    "eng_en_jr_0057",
    "句子 'I LOVE this song.' 中大写词用重音强调的是（　　）",
    [
        "A. 主语",
        "B. 谓语动词",
        "C. 宾语",
        "D. 状语"
    ],
    "B", "kp_eng7_spk7_discourse", 0.35,
    "大写 LOVE 表示重音强调谓语动词，以突出情感。"
))

# ----- kp_eng7_wri7_context_sentences (意义连贯语句) -----
items.append(solve_item(
    "eng_en_jr_0058",
    "请围绕主题 'My Hometown' 写 3-5 个意义连贯的句子。",
    "My hometown is a small and beautiful town. There is a clean river and many green trees around it. People here are kind and helpful. I love my hometown very much.",
    "kp_eng7_wri7_context_sentences", 0.45,
    "语句需围绕同一主题展开，注意衔接自然（There is / People here / I love）。",
    form="open_write"
))

# ----- kp_eng7_wri7_story (编写故事) -----
items.append(solve_item(
    "eng_en_jr_0059",
    "请编写一个情节较为完整的小故事（不少于 50 词），主题：A Helpful Stranger。",
    "Last Sunday, I lost my way on my way home. I was very worried. Just then, a kind stranger came over and asked what happened. He showed me the right way and walked with me to the bus stop. I thanked him again and again. He was really a helpful stranger.",
    "kp_eng7_wri7_story", 0.55,
    "故事要素齐全：背景(迷路)→冲突(worried)→解决(stranger 帮忙)→结尾(感谢)，情节完整。",
    form="narrative"
))

# ----- kp_eng7_wri7_greeting_invite (问候邀请) -----
items.append(solve_item(
    "eng_en_jr_0060",
    "请给你的朋友 Lily 写一张生日邀请卡，邀请她参加你的生日聚会。",
    "Dear Lily, I'm having a birthday party at my home this Saturday at 5 p.m. I hope you can come and join us. We'll have cake, music and games. Looking forward to seeing you! Love, Anna.",
    "kp_eng7_wri7_greeting_invite", 0.4,
    "邀请卡要素：称谓、邀请事由、时间地点、表达期待、署名。",
    form="essay"
))

# ----- kp_eng7_lsm7_goal_plan (学习目标) -----
items.append(solve_item(
    "eng_en_jr_0061",
    "请为自己制定一个为期一周的英语学习计划（含目标与具体安排）。",
    "My goal is to improve my English listening this week. I will listen to the textbook audio for 20 minutes every day. I will also read one short English story before bed. At the weekend, I will review the new words I have learned.",
    "kp_eng7_lsm7_goal_plan", 0.45,
    "目标+具体安排+自评/反思，符合'目标—监控—反思'元认知策略。",
    form="open_write"
))

# ----- kp_eng7_lsm7_group_coop (小组合作) -----
items.append(choice_item(
    "eng_en_jr_0062",
    "下列哪种做法最有利于小组合作学习（　　）",
    [
        "A. 一个人承担全部任务",
        "B. 分工明确、互相帮助、定期交流",
        "C. 各自做完后不分享",
        "D. 只做自己感兴趣的部分"
    ],
    "B", "kp_eng7_lsm7_group_coop", 0.35,
    "小组合作的关键是分工明确、互相帮助、定期交流。"
))

# ----- kp_eng7_lsm7_note_taking (记笔记) -----
items.append(choice_item(
    "eng_en_jr_0063",
    "听一段课堂讲解时，下列哪种记笔记方式最有效（　　）",
    [
        "A. 把老师说的每句话一字不漏地记下来",
        "B. 用关键词和简写记要点与例子",
        "C. 只记标题",
        "D. 全凭记忆"
    ],
    "B", "kp_eng7_lsm7_note_taking", 0.35,
    "有效笔记应抓关键词、要点和例子，并使用简写。"
))

# ----- kp_eng7_lsm7_reading_strategies (阅读策略) -----
items.append(choice_item(
    "eng_en_jr_0064",
    "阅读时遇到生词，下列策略最合理的是（　　）",
    [
        "A. 立即停下查字典",
        "B. 根据上下文和构词法先猜测",
        "C. 跳过去不看",
        "D. 立刻放弃阅读"
    ],
    "B", "kp_eng7_lsm7_reading_strategies", 0.3,
    "课标提倡根据上下文、构词法推断生词，必要时再查证。"
))

# ----- kp_eng7_lsm7_motivation (激发动机) -----
items.append(solve_item(
    "eng_en_jr_0065",
    "当你觉得英语单词难记、容易焦虑时，请写出两种降低焦虑、保持学习动机的具体做法。",
    "1. Set small goals, such as learning five new words each day. 2. Listen to English songs or watch short English videos to make learning fun.",
    "kp_eng7_lsm7_motivation", 0.4,
    "降低焦虑可设小目标、用兴趣材料；要点在于具体可行。",
    form="open_write"
))
items.append(choice_item(
    "eng_en_jr_0066",
    "下列哪一项最可能是一段'独白'（　　）",
    [
        "A. 两个人讨论周末计划",
        "B. 一人讲述自己的童年回忆",
        "C. 顾客与售货员的对话",
        "D. 老师与学生的问答"
    ],
    "B", "kp_eng7_dis7_dialogue_monologue", 0.3,
    "独白指单方连续讲话，'讲述自己童年回忆'符合这一形态。"
))

# ----- kp_eng7_gra7_choice_question (选择疑问句) -----
items.append(choice_item(
    "eng_en_jr_0067",
    "下列属于选择疑问句的是（　　）",
    [
        "A. Are you a student?",
        "B. Do you like tea or coffee?",
        "C. What is your name?",
        "D. How old are you?"
    ],
    "B", "kp_eng7_gra7_choice_question", 0.35,
    "由 or 连接两个选项、提供选择的是选择疑问句。"
))

# ----- kp_eng7_red7_skim (略读) -----
items.append(choice_item(
    "eng_en_jr_0068",
    "略读（skimming）的最主要目的是（　　）",
    [
        "A. 弄清每一个细节",
        "B. 把握文章大意",
        "C. 学习每个生词",
        "D. 评价文章观点"
    ],
    "B", "kp_eng7_red7_skim", 0.3,
    "略读强调快速获取主旨大意，不必逐词阅读。"
))

# ----- kp_eng7_thm7_self_life (生活与学习主题) -----
items.append(solve_item(
    "eng_en_jr_0069",
    "请围绕主题 'My School Life' 写一段 40-60 词的短文，介绍你的校园生活。",
    "My school life is busy and colourful. I have six classes every day, and my favourite subject is English. After class, I often play basketball with my classmates. I enjoy talking with my teachers. I love my school life.",
    "kp_eng7_thm7_self_life", 0.45,
    "围绕'生活与学习'主题展开：日常学习 + 课余活动 +个人感受，内容完整连贯。",
    form="essay"
))

# ----- kp_eng7_thm7_self_life 第二题 — cloze-style -----
items.append(choice_item(
    "eng_en_jr_0070",
    "下列话题中，不属于'生活与学习'主题范畴的是（　　）",
    [
        "A. 健康饮食习惯",
        "B. 太空探索",
        "C. 学习方法",
        "D. 校园活动"
    ],
    "B", "kp_eng7_thm7_self_life", 0.4,
    "太空探索属于'人与自然'范畴下的宇宙探索子主题。"
))

print(f"After Grade 7: {len(items)} items")
print("First batch done, will continue with Grade 8 and 9...")

# Save partial for verification
with open(os.path.join(OUT_DIR, "_temp_g7.json"), "w", encoding="utf-8") as f:
    json.dump(items, f, ensure_ascii=False, indent=2)

print(f"Saved {len(items)} items to _temp_g7.json")
