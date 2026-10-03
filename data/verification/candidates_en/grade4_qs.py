# Grade 4 English questions (32 KPs × 2 = 64 questions)

GRADE4_Q = [
    # kp_eng4_pha4_decode: 拼读规则
    {"kp":"kp_eng4_pha4_decode","form":"listening","item_type":"choice",
     "stem":"借助拼读规则，下列哪个单词可读作 /kæt/？（　　）\nA. cat  \nB. dog  \nC. kite  \nD. fish",
     "options":["A. cat","B. dog","C. kite","D. fish"],
     "answer":"A","solution":"/k/+/æ/+/t/ 拼出 cat。","difficulty":0.30},
    {"kp":"kp_eng4_pha4_decode","form":"listening","item_type":"fill",
     "stem":"拼读单词：写出字母 c / a / t 拼成的英文单词：____",
     "answer":"cat","solution":"c-a-t 拼成 cat。","difficulty":0.45},

    # kp_eng4_pha4_stress_copy: 重音模仿
    {"kp":"kp_eng4_pha4_stress_copy","form":"listening","item_type":"choice",
     "stem":"\"computer\" 一词中，重读音节是（　　）\nA. com-  \nB. -pu-  \nC. -ter  \nD. 都不重读",
     "options":["A. com-","B. -pu-","C. -ter","D. 都不重读"],
     "answer":"B","solution":"computer 重音在第二音节 -pu-。","difficulty":0.30},
    {"kp":"kp_eng4_pha4_stress_copy","form":"listening","item_type":"fill",
     "stem":"在单词 \"afternoon\" 中标出重音的位置（用 ′ 标在重读音节前）：____",
     "answer":"afternoon′","solution":"afternoon 重音在第二音节 noon。","difficulty":0.45},

    # kp_eng4_voc4_subjects: 学科与课程
    {"kp":"kp_eng4_voc4_subjects","form":"multiple_choice","item_type":"choice",
     "stem":"\"I have maths, English and music today.\" 说话者最可能在说（　　）\nA. 喜欢的食物  \nB. 今天的课程  \nC. 家庭成员  \nD. 喜欢的运动",
     "options":["A. 喜欢的食物","B. 今天的课程","C. 家庭成员","D. 喜欢的运动"],
     "answer":"B","solution":"maths/English/music 都是学科。","difficulty":0.30},
    {"kp":"kp_eng4_voc4_subjects","form":"fill","item_type":"fill",
     "stem":"补全句子：My favourite ____ is English.（学科）____",
     "answer":"subject","solution":"favorite subject 表示\"最喜欢的学科\"。","difficulty":0.45},

    # kp_eng4_voc4_transport: 交通工具
    {"kp":"kp_eng4_voc4_transport","form":"picture_qa","item_type":"choice",
     "stem":"看图：图中有两节相连的轨道车，车厢很长。下列哪个词最匹配？（　　）\nA. bus  \nB. bike  \nC. train  \nD. ship",
     "options":["A. bus","B. bike","C. train","D. ship"],
     "answer":"C","solution":"轨道上多节相连的车是 train。","difficulty":0.30},
    {"kp":"kp_eng4_voc4_transport","form":"fill","item_type":"fill",
     "stem":"写出 1 个有轮子的陆地交通工具：____",
     "answer":"bike","solution":"bike / bus / car / taxi 等皆可。","difficulty":0.45},

    # kp_eng4_voc4_verb_phrase: 动词短语
    {"kp":"kp_eng4_voc4_verb_phrase","form":"multiple_choice","item_type":"choice",
     "stem":"\"get up\" 的意思是（　　）\nA. 坐下  \nB. 起床  \nC. 出门  \nD. 上车",
     "options":["A. 坐下","B. 起床","C. 出门","D. 上车"],
     "answer":"B","solution":"get up = 起床。","difficulty":0.30},
    {"kp":"kp_eng4_voc4_verb_phrase","form":"fill","item_type":"fill",
     "stem":"翻译短语 \"go to school\" 为中文：____",
     "answer":"去学校","solution":"go to school 意为\"去学校\"。","difficulty":0.45},

    # kp_eng4_gra4_yesno: 一般疑问句
    {"kp":"kp_eng4_gra4_yesno","form":"multiple_choice","item_type":"choice",
     "stem":"把陈述句 \"You are a student.\" 改为一般疑问句（　　）\nA. Are you a student?  \nB. Is you a student?  \nC. Do you are a student?  \nD. You are a student?",
     "options":["A. Are you a student?","B. Is you a student?","C. Do you are a student?","D. You are a student?"],
     "answer":"A","solution":"含 are 的陈述句改一般疑问句将 are 提前。","difficulty":0.30},
    {"kp":"kp_eng4_gra4_yesno","form":"fill","item_type":"fill",
     "stem":"补全一般疑问句：____ you like apples?",
     "answer":"Do","solution":"实义动词一般疑问句借助 do / does；主语 you 用 Do。","difficulty":0.45},

    # kp_eng4_gra4_plural: 可数名词复数
    {"kp":"kp_eng4_gra4_plural","form":"multiple_choice","item_type":"choice",
     "stem":"下列复数形式正确的是（　　）\nA. childs  \nB. child  \nC. children  \nD. childes",
     "options":["A. childs","B. child","C. children","D. childes"],
     "answer":"C","solution":"child 的复数是不规则形式 children。","difficulty":0.30},
    {"kp":"kp_eng4_gra4_plural","form":"fill","item_type":"fill",
     "stem":"写出 \"baby\" 的复数形式：____",
     "answer":"babies","solution":"baby 改 y 为 i 加 es 变 babies。","difficulty":0.45},

    # kp_eng4_gra4_time_prep: 时间介词
    {"kp":"kp_eng4_gra4_time_prep","form":"multiple_choice","item_type":"choice",
     "stem":"\"We have a party ____ Friday afternoon.\" 横线处应填（　　）\nA. in  \nB. on  \nC. at  \nD. by",
     "options":["A. in","B. on","C. at","D. by"],
     "answer":"B","solution":"具体某一天下午用介词 on。","difficulty":0.30},
    {"kp":"kp_eng4_gra4_time_prep","form":"fill","item_type":"fill",
     "stem":"补全句子：I get up ____ 7 o'clock ____ the morning.",
     "answer":"at, in","solution":"钟点前用 at；早中晚上午前用 in。","difficulty":0.45},

    # kp_eng4_gra4_present_vs_ing: 一般现在时 vs 现在进行时
    {"kp":"kp_eng4_gra4_present_vs_ing","form":"multiple_choice","item_type":"choice",
     "stem":"区分时态：\"She often reads books.\" 是（　　）\nA. 一般现在时  \nB. 现在进行时  \nC. 一般过去时  \nD. 一般将来时",
     "options":["A. 一般现在时","B. 现在进行时","C. 一般过去时","D. 一般将来时"],
     "answer":"A","solution":"often 表习惯，对应一般现在时。","difficulty":0.30},
    {"kp":"kp_eng4_gra4_present_vs_ing","form":"fill","item_type":"fill",
     "stem":"用括号内动词的恰当形式填空：Listen! She ____ (sing) now.",
     "answer":"is singing","solution":"Listen! 提示用现在进行时 is singing。","difficulty":0.45},

    # kp_eng4_gra4_svo: 简单句基本句型
    {"kp":"kp_eng4_gra4_svo","form":"multiple_choice","item_type":"choice",
     "stem":"句子 \"I love English.\" 的基本句型是（　　）\nA. 主谓  \nB. 主谓宾  \nC. 主系表  \nD. 主谓宾宾",
     "options":["A. 主谓","B. 主谓宾","C. 主系表","D. 主谓宾宾"],
     "answer":"B","solution":"I (主) love (谓) English (宾) 是主谓宾结构。","difficulty":0.30},
    {"kp":"kp_eng4_gra4_svo","form":"fill","item_type":"fill",
     "stem":"指出句子 \"She is a teacher.\" 中的表语：____",
     "answer":"a teacher","solution":"a teacher 是系动词 is 后的表语。","difficulty":0.45},

    # kp_eng4_dis4_story_structure: 配图故事结构
    {"kp":"kp_eng4_dis4_story_structure","form":"comprehension","item_type":"choice",
     "stem":"配图故事通常按怎样的结构组织？（　　）\nA. 背景 → 高潮 → 结尾  \nB. 开头 → 中间 → 结尾  \nC. 倒叙 → 插叙 → 顺序  \nD. 没有结构",
     "options":["A. 背景 → 高潮 → 结尾","B. 开头 → 中间 → 结尾","C. 倒叙 → 插叙 → 顺序","D. 没有结构"],
     "answer":"B","solution":"配图故事通常按开头、中间、结尾组织。","difficulty":0.30},
    {"kp":"kp_eng4_dis4_story_structure","form":"fill","item_type":"fill",
     "stem":"故事由 ① ____、② ____ 和 ③ ____ 三部分构成（写出 3 个关键词）：____",
     "answer":"开头, 中间, 结尾","solution":"故事由开头、中间、结尾构成。","difficulty":0.45},

    # kp_eng4_dis4_intro_elements: 介绍类语篇基本要素
    {"kp":"kp_eng4_dis4_intro_elements","form":"comprehension","item_type":"choice",
     "stem":"介绍一个朋友时，最不需要的内容是（　　）\nA. 名字  \nB. 年龄  \nC. 喜好  \nD. 暗号",
     "options":["A. 名字","B. 年龄","C. 喜好","D. 暗号"],
     "answer":"D","solution":"介绍朋友通常说名字、年龄、爱好等，\"暗号\"不属于介绍要素。","difficulty":0.30},
    {"kp":"kp_eng4_dis4_intro_elements","form":"fill","item_type":"fill",
     "stem":"介绍类语篇的基本要素常包括：____、年龄和外貌（写出第一要素）：____",
     "answer":"名字","solution":"介绍类语篇通常先介绍名字，再介绍年龄外貌。","difficulty":0.45},

    # kp_eng4_prg4_request_allow: 请求与许可
    {"kp":"kp_eng4_prg4_request_allow","form":"oral_qa","item_type":"fill",
     "stem":"补全对话：A: ____ I go now? B: Yes, you can.",
     "answer":"May","solution":"请求许可用 May I …? 句型。","difficulty":0.30},
    {"kp":"kp_eng4_prg4_request_allow","form":"oral_qa","item_type":"choice",
     "stem":"想请求老师让你喝水，最得体的表达是（　　）\nA. I want water.  \nB. May I drink some water, please?  \nC. Give me water.  \nD. Water, now!",
     "options":["A. I want water.","B. May I drink some water, please?","C. Give me water.","D. Water, now!"],
     "answer":"B","solution":"May I …, please? 是礼貌请求许可的标准句型。","difficulty":0.45},

    # kp_eng4_prg4_apologise: 道歉
    {"kp":"kp_eng4_prg4_apologise","form":"oral_qa","item_type":"fill",
     "stem":"补全对话：A: I'm ____ for being late.（道歉）B: That's OK.",
     "answer":"sorry","solution":"I'm sorry for … 是标准道歉句型。","difficulty":0.30},
    {"kp":"kp_eng4_prg4_apologise","form":"oral_qa","item_type":"choice",
     "stem":"你无意中撞到同学，应说（　　）\nA. I'm sorry.  \nB. Goodbye.  \nC. Thank you.  \nD. Let's go.",
     "options":["A. I'm sorry.","B. Goodbye.","C. Thank you.","D. Let's go."],
     "answer":"A","solution":"撞到他人应说 I'm sorry 表示歉意。","difficulty":0.45},

    # kp_eng4_cul4_school_compare: 中外学校生活
    {"kp":"kp_eng4_cul4_school_compare","form":"comprehension","item_type":"choice",
     "stem":"下列哪一项可能与中国学校生活不同？（　　）\nA. 有教室  \nB. 有老师  \nC. 一些国家学生穿校服上学  \nD. 学校没有钟",
     "options":["A. 有教室","B. 有老师","C. 一些国家学生穿校服上学","D. 学校没有钟"],
     "answer":"C","solution":"不同国家学生着装习俗不同，校服为典型差异点。","difficulty":0.30},
    {"kp":"kp_eng4_cul4_school_compare","form":"fill","item_type":"fill",
     "stem":"写出英语 \"school uniform\" 对应的中文：____",
     "answer":"校服","solution":"school uniform 意为校服。","difficulty":0.45},

    # kp_eng4_cul4_table_manner: 中西餐桌礼仪
    {"kp":"kp_eng4_cul4_table_manner","form":"multiple_choice","item_type":"choice",
     "stem":"西方国家餐桌礼仪中，下列哪种做法常见？（　　）\nA. 用筷子吃面条  \nB. 喝汤时不出声  \nC. 用手直接抓食物  \nD. 把骨头吐在桌上",
     "options":["A. 用筷子吃面条","B. 喝汤时不出声","C. 用手直接抓食物","D. 把骨头吐在桌上"],
     "answer":"B","solution":"西餐礼仪中通常喝汤不出声。","difficulty":0.30},
    {"kp":"kp_eng4_cul4_table_manner","form":"fill","item_type":"fill",
     "stem":"写出英文单词 \"fork\" 的中文意思：____",
     "answer":"叉子","solution":"fork 是西餐常用餐具叉子。","difficulty":0.45},

    # kp_eng4_cul4_sport_game: 中外体育运动
    {"kp":"kp_eng4_cul4_sport_game","form":"multiple_choice","item_type":"choice",
     "stem":"下列哪项是源自英国的著名运动？（　　）\nA. 乒乓球  \nB. 足球  \nC. 武术  \nD. 太极",
     "options":["A. 乒乓球","B. 足球","C. 武术","D. 太极"],
     "answer":"B","solution":"现代足球起源于英国。","difficulty":0.30},
    {"kp":"kp_eng4_cul4_sport_game","form":"fill","item_type":"fill",
     "stem":"写出英语 \"football\" 对应的中文：____",
     "answer":"足球","solution":"football = 足球。","difficulty":0.45},

    # kp_eng4_lis4_specific_info: 有针对性获取信息
    {"kp":"kp_eng4_lis4_specific_info","form":"listening","item_type":"choice",
     "stem":"听短对话：\"A: What time does the film start? B: At 7 p.m.\" 你获取到的关键信息是（　　）\nA. 电影名  \nB. 电影开始时间  \nC. 电影院位置  \nD. 票价",
     "options":["A. 电影名","B. 电影开始时间","C. 电影院位置","D. 票价"],
     "answer":"B","solution":"对话问的 What time，回答是 7 p.m.。","difficulty":0.30},
    {"kp":"kp_eng4_lis4_specific_info","form":"listening","item_type":"fill",
     "stem":"听对话：A: How much is the book? B: It's ____ yuan. (听写价格)",
     "answer":"12","solution":"价格数字需听写，此处取常见 12 yuan。","difficulty":0.45},

    # kp_eng4_lis4_attitude: 语调判断态度
    {"kp":"kp_eng4_lis4_attitude","form":"listening","item_type":"choice",
     "stem":"听到对方用降调说 \"Great!\"，最可能表达的态度是（　　）\nA. 询问  \nB. 兴奋/肯定  \nC. 抱歉  \nD. 犹豫",
     "options":["A. 询问","B. 兴奋/肯定","C. 抱歉","D. 犹豫"],
     "answer":"B","solution":"降调 \"Great!\" 通常表肯定或兴奋。","difficulty":0.30},
    {"kp":"kp_eng4_lis4_attitude","form":"listening","item_type":"fill",
     "stem":"听对话：对方用升调说 \"Really?\"，最可能是在 ____（表惊讶还是完全同意）：____",
     "answer":"表惊讶","solution":"升调 Really? 通常表惊讶或不太相信。","difficulty":0.45},

    # kp_eng4_lis4_weekly30_g: 每周30分钟视听
    {"kp":"kp_eng4_lis4_weekly30_g","form":"solve","item_type":"solve",
     "stem":"一级课标要求一至二年级视听每周不少于 20 分钟；一级开始要求每周不少于 30 分钟。请写出你每周安排英语视听的时间计划（不少于 5 个英文词）：____",
     "answer":"I watch English for 30 minutes every week.","solution":"计划示例：每周 30 分钟英语视听。","difficulty":0.30,"writing_prompt":None},

    # kp_eng4_red4_main_detail: 读懂关键细节
    {"kp":"kp_eng4_red4_main_detail","form":"comprehension","item_type":"choice",
     "stem":"短文：\"Tom is ten. He likes maths. He goes to school by bus.\" 关于 Tom，下列哪项错误？（　　）\nA. Tom 十岁  \nB. Tom 喜欢数学  \nC. Tom 走路去学校  \nD. Tom 坐公交去学校",
     "options":["A. Tom 十岁","B. Tom 喜欢数学","C. Tom 走路去学校","D. Tom 坐公交去学校"],
     "answer":"C","solution":"短文说 by bus 不是 on foot。","difficulty":0.30},
    {"kp":"kp_eng4_red4_main_detail","form":"comprehension","item_type":"fill",
     "stem":"阅读短文回答：How does Tom go to school?  He goes to school by ____.",
     "answer":"bus","solution":"短文 by bus 坐公交。","difficulty":0.45},

    # kp_eng4_red4_notice_apply: 应用文完成任务
    {"kp":"kp_eng4_red4_notice_apply","form":"comprehension","item_type":"choice",
     "stem":"通知：\"School trip on Friday. Meet at the gate at 8 a.m.\" 集合地点是（　　）\nA. 教室  \nB. 大门口  \nC. 食堂  \nD. 操场",
     "options":["A. 教室","B. 大门口","C. 食堂","D. 操场"],
     "answer":"B","solution":"at the gate 指大门口。","difficulty":0.30},
    {"kp":"kp_eng4_red4_notice_apply","form":"comprehension","item_type":"fill",
     "stem":"通知集合时间为 ____ a.m.（听读时间）：____",
     "answer":"8","solution":"通知写 8 a.m.。","difficulty":0.45},

    # kp_eng4_red4_pic_predict_check: 图文互证
    {"kp":"kp_eng4_red4_pic_predict_check","form":"comprehension","item_type":"choice",
     "stem":"短文 \"The girl is reading a book\" 配有图片：小女孩在看书。图文是否一致？（　　）\nA. 一致  \nB. 不一致  \nC. 图片缺失  \nD. 信息矛盾",
     "options":["A. 一致","B. 不一致","C. 图片缺失","D. 信息矛盾"],
     "answer":"A","solution":"文字描述与图片一致。","difficulty":0.30},
    {"kp":"kp_eng4_red4_pic_predict_check","form":"comprehension","item_type":"fill",
     "stem":"用图文互证方法判断：\"The boy is playing football\" 配图为小孩 ____（举球/踢足球/游泳）：____",
     "answer":"踢足球","solution":"短文与图片应同为踢足球。","difficulty":0.45},

    # kp_eng4_spk4_read_dialogue: 朗读对话
    {"kp":"kp_eng4_spk4_read_dialogue","form":"oral_qa","item_type":"choice",
     "stem":"朗读对话时，下列哪种做法不正确？（　　）\nA. 语速适中  \nB. 注意角色语调  \nC. 含糊带过  \nD. 正确停顿",
     "options":["A. 语速适中","B. 注意角色语调","C. 含糊带过","D. 正确停顿"],
     "answer":"C","solution":"朗读应清晰，不应含糊带过。","difficulty":0.30},
    {"kp":"kp_eng4_spk4_read_dialogue","form":"fill","item_type":"fill",
     "stem":"补全对话角色 A 的台词：A: How are you? B: ____",
     "answer":"I'm fine, thank you.","solution":"标准回应 I'm fine, thank you. / I'm OK.","difficulty":0.45},

    # kp_eng4_spk4_personal_profile: 介绍个人信息
    {"kp":"kp_eng4_spk4_personal_profile","form":"oral_qa","item_type":"solve",
     "stem":"用 2 句话介绍自己（不少于 10 个英文词），包括年龄和爱好：____",
     "answer":"I'm ten. I like drawing.","solution":"介绍可用 I'm + 年龄 + I like ….","difficulty":0.30,"writing_prompt":None},
    {"kp":"kp_eng4_spk4_personal_profile","form":"oral_qa","item_type":"choice",
     "stem":"介绍自己时应包含下列哪项内容？（　　）\nA. 只说颜色  \nB. 名字/年龄/喜好  \nC. 同学的缺点  \nD. 只说数字",
     "options":["A. 只说颜色","B. 名字/年龄/喜好","C. 同学的缺点","D. 只说数字"],
     "answer":"B","solution":"自我介绍通常含名字年龄喜好等。","difficulty":0.45},

    # kp_eng4_spk4_describe_thing: 描述图片或事物
    {"kp":"kp_eng4_spk4_describe_thing","form":"oral_qa","item_type":"solve",
     "stem":"看图：图中是一只小黄狗。请用英语描述这只狗（不少于 4 个英文词）：____",
     "answer":"It's a small yellow dog.","solution":"描述事物可用 It's + 形容词 + 名词。","difficulty":0.30,"writing_prompt":None},
    {"kp":"kp_eng4_spk4_describe_thing","form":"oral_qa","item_type":"choice",
     "stem":"描述事物时不应包含下列哪一项？（　　）\nA. 颜色  \nB. 大小  \nC. 位置  \nD. 同学的秘密",
     "options":["A. 颜色","B. 大小","C. 位置","D. 同学的秘密"],
     "answer":"D","solution":"描述事物不涉及他人隐私。","difficulty":0.45},

    # kp_eng4_wri4_paragraph_simple: 写几句连贯的话
    {"kp":"kp_eng4_wri4_paragraph_simple","form":"solve","item_type":"solve",
     "stem":"用英语写 2 句连贯的话介绍你的朋友，不少于 10 个英文词：____",
     "answer":"My friend is Tom. He is ten.","solution":"写几句连贯的话介绍朋友。","difficulty":0.30,"writing_prompt":None},

    # kp_eng4_wri4_letter_simple: 简单书信明信片
    {"kp":"kp_eng4_wri4_letter_simple","form":"solve","item_type":"solve",
     "stem":"写一张明信片给朋友，至少 2 句（不少于 10 个英文词），含称呼与署名：____",
     "answer":"Dear Tom, I'm in Hainan. Love, Lily.","solution":"明信片格式 Dear …, 内容, Love, 署名。","difficulty":0.30,"writing_prompt":None},
    {"kp":"kp_eng4_wri4_letter_simple","form":"fill","item_type":"fill",
     "stem":"明信片常用开头称呼：____ Tom,（写出 1 个）",
     "answer":"Dear","solution":"明信片开头常写 Dear ….","difficulty":0.45},

    # kp_eng4_wri4_punct_case: 标点与大小写
    {"kp":"kp_eng4_wri4_punct_case","form":"spelling","item_type":"fill",
     "stem":"改正错误：\"i am from china.\" → ____",
     "answer":"I am from China.","solution":"句首和专有名词首字母大写：I am from China.","difficulty":0.30},
    {"kp":"kp_eng4_wri4_punct_case","form":"spelling","item_type":"fill",
     "stem":"句子末尾补标点：\"What is your name ____?\"",
     "answer":"?","solution":"疑问句末用问号。","difficulty":0.45},

    # kp_eng4_lsm4_plan_daily: 每日打卡计划
    {"kp":"kp_eng4_lsm4_plan_daily","form":"solve","item_type":"solve",
     "stem":"为自己制订每日英语听说读打卡计划（不少于 5 个英文词）：____",
     "answer":"I read English for 15 minutes every day.","solution":"计划示例：每天读英语 15 分钟。","difficulty":0.30,"writing_prompt":None},

    # kp_eng4_lsm4_word_sort: 分类整理单词
    {"kp":"kp_eng4_lsm4_word_sort","form":"solve","item_type":"solve",
     "stem":"把单词 apple / cat / dog / banana 按水果与动物分成两组（每组至少 1 个，写出分类）：____",
     "answer":"Fruit: apple, banana; Animals: cat, dog.","solution":"apple/banana 是水果，cat/dog 是动物。","difficulty":0.30,"writing_prompt":None},

    # kp_eng4_lsm4_joyful_participate: 带着兴趣参与
    {"kp":"kp_eng4_lsm4_joyful_participate","form":"solve","item_type":"solve",
     "stem":"写出 1 个你愿意主动参加的英语活动（不少于 4 个英文词）：____",
     "answer":"English drama club.","solution":"活动如 drama club / story time / singing group。","difficulty":0.30,"writing_prompt":None},

    # Additional questions to ensure 2 questions per KP
    {"kp":"kp_eng4_lis4_weekly30_g","form":"listening","item_type":"fill",
     "stem":"一级课标要求每周课外视听不少于 ____ 分钟（填写数字）：____",
     "answer":"30","solution":"一级要求每周视听不少于 30 分钟。","difficulty":0.45},
    {"kp":"kp_eng4_lsm4_plan_daily","form":"solve","item_type":"solve",
     "stem":"写出 1 条你的英语听说读打卡计划（不少于 5 个英文词）：____",
     "answer":"I read English for 10 minutes every day.","solution":"每日打卡示例。","difficulty":0.45,"writing_prompt":None},
    {"kp":"kp_eng4_lsm4_word_sort","form":"choice","item_type":"choice",
     "stem":"分类整理单词表时，下列哪个分类最合理？（　　）\nA. 按颜色  \nB. 按主题（如食物、动物）  \nC. 按字母大小写  \nD. 随机",
     "options":["A. 按颜色","B. 按主题","C. 按字母大小写","D. 随机"],
     "answer":"B","solution":"按主题分类更利于记忆。","difficulty":0.45},
    {"kp":"kp_eng4_wri4_paragraph_simple","form":"fill","item_type":"fill",
     "stem":"写出连接句与句的常用词（至少 1 个），用于把几句写连贯：____",
     "answer":"and","solution":"常用连接词 and / but / because。","difficulty":0.45},
    {"kp":"kp_eng4_lsm4_joyful_participate","form":"choice","item_type":"choice",
     "stem":"带着兴趣参与英语活动，下列哪种活动最能调动参与？（　　）\nA. 抄单词  \nB. 英语故事表演  \nC. 只听不读  \nD. 只看英文视频",
     "options":["A. 抄单词","B. 英语故事表演","C. 只听不读","D. 只看英文视频"],
     "answer":"B","solution":"故事表演能调动参与兴趣。","difficulty":0.45},
]