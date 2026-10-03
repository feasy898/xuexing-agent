# Grade 3 English questions (32 KPs × 2 = 64 questions)

GRADE3_Q = [
    # kp_eng3_pha3_26letters: 26字母识别
    {"kp":"kp_eng3_pha3_26letters","form":"multiple_choice","item_type":"choice",
     "stem":"下列 26 个英文字母中，含有相同元音音素 /iː/ 的一组是（　　）\nA. A H J K  \nB. B C D E  \nC. F L M N  \nD. S U V W",
     "options":["A. A H J K","B. B C D E","C. F L M N","D. S U V W"],
     "answer":"B","solution":"B / C / D / E 的字母名称音均含元音 /iː/。","difficulty":0.30},
    {"kp":"kp_eng3_pha3_26letters","form":"spelling","item_type":"fill",
     "stem":"写出字母 \"b\" 的大写形式和字母 \"G\" 的小写形式：大写 b = ____；小写 G = ____",
     "answer":"B, g","solution":"b 的大写是 B，G 的小写是 g。","difficulty":0.45},

    # kp_eng3_pha3_word_stress: 单词重音
    {"kp":"kp_eng3_pha3_word_stress","form":"listening","item_type":"choice",
     "stem":"听教师读下列词，指出哪个词的重音在第一音节（　　）\nA. 'apple  \nB. ba'nana  \nC. to'morrow  \nD. 'beautiful",
     "options":["A. 'apple","B. ba'nana","C. to'morrow","D. 'beautiful"],
     "answer":"A","solution":"apple 重音在第一音节 ap-；其余三词重音在第二音节。","difficulty":0.30},
    {"kp":"kp_eng3_pha3_word_stress","form":"listening","item_type":"fill",
     "stem":"听单词 \"apple\" 的标准读音，写出这个单词有几个音节：____",
     "answer":"2","solution":"apple 拆为 ap-ple 共 2 个音节。","difficulty":0.45},

    # kp_eng3_voc3_image_meaning: 借助图片理解词义
    {"kp":"kp_eng3_voc3_image_meaning","form":"picture_qa","item_type":"choice",
     "stem":"看图：图中一位医生正在为小朋友检查身体。下列哪一个单词最符合图片？（　　）\nA. teacher  \nB. doctor  \nC. driver  \nD. nurse",
     "options":["A. teacher","B. doctor","C. driver","D. nurse"],
     "answer":"B","solution":"图中是为小朋友看病的医生，对应 doctor。","difficulty":0.30},
    {"kp":"kp_eng3_voc3_image_meaning","form":"picture_qa","item_type":"fill",
     "stem":"看图：图中是一个圆形的橙色水果（橘子）。写出对应的英语单词：____",
     "answer":"orange","solution":"圆形橙色水果是橘子，英文 orange。","difficulty":0.45},

    # kp_eng3_voc3_people_place: 人物与地点
    {"kp":"kp_eng3_voc3_people_place","form":"multiple_choice","item_type":"choice",
     "stem":"你想告诉同学自己去动物园，应说（　　）\nA. I'm going to the park.  \nB. I'm going to the zoo.  \nC. I'm going to the school.  \nD. I'm going to the hospital.",
     "options":["A. I'm going to the park.","B. I'm going to the zoo.","C. I'm going to the school.","D. I'm going to the hospital."],
     "answer":"B","solution":"动物园英文 zoo，句型 I'm going to the zoo.","difficulty":0.30},
    {"kp":"kp_eng3_voc3_people_place","form":"picture_qa","item_type":"fill",
     "stem":"看图：图中有一位正在给学生上课的女性。请写出她的职业英语：____",
     "answer":"teacher","solution":"给学生上课的女性职业是 teacher。","difficulty":0.45},

    # kp_eng3_voc3_number_quantity: 基数词与数量
    {"kp":"kp_eng3_voc3_number_quantity","form":"multiple_choice","item_type":"choice",
     "stem":"图中有 5 个苹果，下列哪一句描述正确？（　　）\nA. I have three apples.  \nB. I have five apples.  \nC. I have fifteen apples.  \nD. I have fifty apples.",
     "options":["A. I have three apples.","B. I have five apples.","C. I have fifteen apples.","D. I have fifty apples."],
     "answer":"B","solution":"5 个苹果对应 five apples。","difficulty":0.30},
    {"kp":"kp_eng3_voc3_number_quantity","form":"fill","item_type":"fill",
     "stem":"写出 12 的英文单词（基数词形式）：____",
     "answer":"twelve","solution":"12 的英文基数词是 twelve。","difficulty":0.45},

    # kp_eng3_gra3_be_verbs: be动词
    {"kp":"kp_eng3_gra3_be_verbs","form":"multiple_choice","item_type":"choice",
     "stem":"补全句子：I ____ a pupil.（　　）\nA. am  \nB. is  \nC. are  \nD. be",
     "options":["A. am","B. is","C. are","D. be"],
     "answer":"A","solution":"主语 I 与 am 搭配。","difficulty":0.30},
    {"kp":"kp_eng3_gra3_be_verbs","form":"multiple_choice","item_type":"choice",
     "stem":"补全句子：They ____ my friends.（　　）\nA. am  \nB. is  \nC. are  \nD. be",
     "options":["A. am","B. is","C. are","D. be"],
     "answer":"C","solution":"主语 They 与 are 搭配。","difficulty":0.45},

    # kp_eng3_gra3_simple_present: 一般现在时
    {"kp":"kp_eng3_gra3_simple_present","form":"multiple_choice","item_type":"choice",
     "stem":"补全句子（描述习惯）：She ____ to school every day.（　　）\nA. go  \nB. goes  \nC. going  \nD. went",
     "options":["A. go","B. goes","C. going","D. went"],
     "answer":"B","solution":"主语第三人称单数 She，动词用 goes。","difficulty":0.30},
    {"kp":"kp_eng3_gra3_simple_present","form":"multiple_choice","item_type":"choice",
     "stem":"下列哪一句用于描述经常性动作？（　　）\nA. I am reading now.  \nB. I read books every day.  \nC. I will read tomorrow.  \nD. I read yesterday.",
     "options":["A. I am reading now.","B. I read books every day.","C. I will read tomorrow.","D. I read yesterday."],
     "answer":"B","solution":"every day 表经常性，配合一般现在时。","difficulty":0.45},

    # kp_eng3_gra3_present_progressive: 现在进行时
    {"kp":"kp_eng3_gra3_present_progressive","form":"multiple_choice","item_type":"choice",
     "stem":"补全句子：Look! The dog ____.（　　）\nA. run  \nB. runs  \nC. is running  \nD. ran",
     "options":["A. run","B. runs","C. is running","D. ran"],
     "answer":"C","solution":"Look! 提示动作正在发生，用现在进行时 is running。","difficulty":0.30},
    {"kp":"kp_eng3_gra3_present_progressive","form":"fill","item_type":"fill",
     "stem":"写出 \"play\" 的现在分词形式：____",
     "answer":"playing","solution":"play 的现在分词为 play + ing = playing。","difficulty":0.45},

    # kp_eng3_gra3_article_plural: 冠词与复数
    {"kp":"kp_eng3_gra3_article_plural","form":"multiple_choice","item_type":"choice",
     "stem":"补全句子：This is ____ apple. It's ____ red apple.（　　）\nA. a / an  \nB. an / a  \nC. a / a  \nD. an / an",
     "options":["A. a / an","B. an / a","C. a / a","D. an / an"],
     "answer":"B","solution":"apple 以元音音素开头，前用 an；red 以辅音音素开头，前用 a。","difficulty":0.30},
    {"kp":"kp_eng3_gra3_article_plural","form":"fill","item_type":"fill",
     "stem":"写出 \"box\" 的复数形式：____",
     "answer":"boxes","solution":"box 以 x 结尾，复数加 -es 变 boxes。","difficulty":0.45},

    # kp_eng3_gra3_pronoun_possessive: 人称代词与物主代词
    {"kp":"kp_eng3_gra3_pronoun_possessive","form":"multiple_choice","item_type":"choice",
     "stem":"补全句子：This is my book. Please give it to ____.（　　）\nA. I  \nB. me  \nC. my  \nD. mine",
     "options":["A. I","B. me","C. my","D. mine"],
     "answer":"B","solution":"give sth to sb 用宾格 me。","difficulty":0.30},
    {"kp":"kp_eng3_gra3_pronoun_possessive","form":"multiple_choice","item_type":"choice",
     "stem":"补全句子：____ book is new.（　　）\nA. I  \nB. Me  \nC. My  \nD. Mine",
     "options":["A. I","B. Me","C. My","D. Mine"],
     "answer":"C","solution":"后接 book 名词，需用形容词性物主代词 My。","difficulty":0.45},

    # kp_eng3_dis3_types_basic: 语篇基本类型
    {"kp":"kp_eng3_dis3_types_basic","form":"multiple_choice","item_type":"choice",
     "stem":"下列语篇最可能是哪一种？\"Tom: How are you? Lily: I'm fine, thank you.\"（　　）\nA. 配图故事  \nB. 对话  \nC. 说明文  \nD. 通知",
     "options":["A. 配图故事","B. 对话","C. 说明文","D. 通知"],
     "answer":"B","solution":"含 Tom 与 Lily 两人发言，是典型对话语篇。","difficulty":0.30},
    {"kp":"kp_eng3_dis3_types_basic","form":"fill","item_type":"fill",
     "stem":"下列语篇属于哪种类型？\"Notice: Sports Day is on Friday.\" ____",
     "answer":"Notice","solution":"该语篇为通知（Notice）。","difficulty":0.45},

    # kp_eng3_prg3_greet_farewell: 问候与告别
    {"kp":"kp_eng3_prg3_greet_farewell","form":"oral_qa","item_type":"choice",
     "stem":"晚上睡觉前对爸妈说，最合适的英语是（　　）\nA. Good morning.  \nB. Good evening.  \nC. Good night.  \nD. Hello.",
     "options":["A. Good morning.","B. Good evening.","C. Good night.","D. Hello."],
     "answer":"C","solution":"晚间告别睡觉用 Good night.。","difficulty":0.30},
    {"kp":"kp_eng3_prg3_greet_farewell","form":"fill","item_type":"fill",
     "stem":"补全对话：A: Good afternoon, Mum. B: ____ , dear.",
     "answer":"Good afternoon","solution":"下午见面回应用 Good afternoon。","difficulty":0.45},

    # kp_eng3_prg3_respond_praise: 回应赞扬
    {"kp":"kp_eng3_prg3_respond_praise","form":"oral_qa","item_type":"choice",
     "stem":"老师夸奖你：\"Your drawing is beautiful!\" 你最合适的回应是（　　）\nA. No.  \nB. Thank you.  \nC. Goodbye.  \nD. Sit down.",
     "options":["A. No.","B. Thank you.","C. Goodbye.","D. Sit down."],
     "answer":"B","solution":"面对赞扬用 Thank you. 回应最得体。","difficulty":0.30},
    {"kp":"kp_eng3_prg3_respond_praise","form":"fill","item_type":"fill",
     "stem":"补全对话：Teacher: You're great!  Student: ____",
     "answer":"Thank you.","solution":"对赞扬的得体回应：Thank you.","difficulty":0.45},

    # kp_eng3_cul3_name_order: 中英姓名差异
    {"kp":"kp_eng3_cul3_name_order","form":"multiple_choice","item_type":"choice",
     "stem":"英语姓名 \"Lily Smith\"，其中 \"Smith\" 是（　　）\nA. 名（first name）  \nB. 姓（last name）  \nC. 中间名  \nD. 昵称",
     "options":["A. 名（first name）","B. 姓（last name）","C. 中间名","D. 昵称"],
     "answer":"B","solution":"英语姓名姓在后，Smith 是姓。","difficulty":0.30},
    {"kp":"kp_eng3_cul3_name_order","form":"fill","item_type":"fill",
     "stem":"写出 \"王小红\" 在英语姓名顺序中的英文形式：____",
     "answer":"Xiaohong Wang","solution":"英语姓在前名在后：王 Xiaohong Wang。","difficulty":0.45},

    # kp_eng3_cul3_symbols_festivals: 中外文化标志与节日
    {"kp":"kp_eng3_cul3_symbols_festivals","form":"multiple_choice","item_type":"choice",
     "stem":"下列哪一个是西方国家的重要节日？（　　）\nA. 春节  \nB. 中秋节  \nC. 圣诞节  \nD. 端午节",
     "options":["A. 春节","B. 中秋节","C. 圣诞节","D. 端午节"],
     "answer":"C","solution":"圣诞节是西方重要节日。","difficulty":0.30},
    {"kp":"kp_eng3_cul3_symbols_festivals","form":"fill","item_type":"fill",
     "stem":"写出英语 \"Christmas\" 对应的中文节日：____",
     "answer":"圣诞节","solution":"Christmas 是圣诞节。","difficulty":0.45},

    # kp_eng3_lis3_class_command: 课堂指令
    {"kp":"kp_eng3_lis3_class_command","form":"listening","item_type":"choice",
     "stem":"听教师说 \"Listen to me, please.\" 你应做的是（　　）\nA. 说话  \nB. 安静听老师讲  \nC. 跑出教室  \nD. 唱歌",
     "options":["A. 说话","B. 安静听老师讲","C. 跑出教室","D. 唱歌"],
     "answer":"B","solution":"Listen to me 指安静听老师讲。","difficulty":0.30},
    {"kp":"kp_eng3_lis3_class_command","form":"fill","item_type":"fill",
     "stem":"听指令 \"____ your book, please.\"（打开），填入听到的动词：____",
     "answer":"Open","solution":"指令动词为 Open。","difficulty":0.45},

    # kp_eng3_lis3_detail: 听懂主要信息
    {"kp":"kp_eng3_lis3_detail","form":"listening","item_type":"choice",
     "stem":"听短对话 \"A: What's your name? B: My name is Tom. A: How old are you? B: I'm nine.\" 关于 Tom 的信息，正确的是（　　）\nA. 他十岁  \nB. 他叫 Tom，九岁  \nC. 他是老师  \nD. 他喜欢英",
     "options":["A. 他十岁","B. 他叫 Tom，九岁","C. 他是老师","D. 他喜欢英"],
     "answer":"B","solution":"对话中 Tom 自报名字和年龄九岁。","difficulty":0.30},
    {"kp":"kp_eng3_lis3_detail","form":"listening","item_type":"fill",
     "stem":"听短对话：A: Where are you from? B: I'm from ____ (Beijing/Shanghai). 请写出城市英文：____",
     "answer":"Beijing","solution":"句中应为 Beijing（北京）。","difficulty":0.45},

    # kp_eng3_lis3_weekly_: 每周视听30分钟
    {"kp":"kp_eng3_lis3_weekly_","form":"solve","item_type":"solve",
     "stem":"你周一到周五每天看 6 分钟英语动画，周末不看。一周总视听时长是多少分钟？是否达到一级\"每周 30 分钟\"要求？请简要回答：____",
     "answer":"30 分钟，刚好达标。","solution":"5×6 = 30 分钟，达到一级要求。","difficulty":0.30,
     "writing_prompt":None},

    # kp_eng3_red3_predict: 读前预测
    {"kp":"kp_eng3_red3_predict","form":"comprehension","item_type":"choice",
     "stem":"看到一篇阅读的标题 \"A Day at the Zoo\" 并配有长颈鹿图片。下列哪一项最可能是文章的主要内容？（　　）\nA. 去海里游泳  \nB. 在动物园度过一天  \nC. 在图书馆读书  \nD. 野餐",
     "options":["A. 去海里游泳","B. 在动物园度过一天","C. 在图书馆读书","D. 野餐"],
     "answer":"B","solution":"标题 + 图片提示这是关于动物园的一天。","difficulty":0.30},
    {"kp":"kp_eng3_red3_predict","form":"fill","item_type":"fill",
     "stem":"阅读标题 \"My New Friend\"，预测文中会介绍 ____（写出 1 个相关词）：____",
     "answer":"friend","solution":"文章主题是新朋友，会介绍朋友的特征。","difficulty":0.45},

    # kp_eng3_red3_intro_text: 介绍类语篇
    {"kp":"kp_eng3_red3_intro_text","form":"comprehension","item_type":"choice",
     "stem":"阅读短文：\"Hi, I'm Lily. I'm nine. I like apples.\" 这篇短文主要介绍的内容是（　　）\nA. Lily 的年龄和喜好  \nB. Lily 的家人  \nC. Lily 的学校  \nD. Lily 的老师",
     "options":["A. Lily 的年龄和喜好","B. Lily 的家人","C. Lily 的学校","D. Lily 的老师"],
     "answer":"A","solution":"短文提到年龄 9 岁和喜欢苹果，是自我介绍类。","difficulty":0.30},
    {"kp":"kp_eng3_red3_intro_text","form":"comprehension","item_type":"fill",
     "stem":"阅读短文，回答问题 \"How old is she?\"：\"She is ____.\"",
     "answer":"nine","solution":"短文说 I'm nine，所以九岁。","difficulty":0.45},

    # kp_eng3_vie3_sign_menu: 提示牌菜单
    {"kp":"kp_eng3_vie3_sign_menu","form":"picture_qa","item_type":"choice",
     "stem":"看图：图中是一个红色的圆形禁止标志，中间有一条斜线。最可能的含义是（　　）\nA. 注意  \nB. 禁止  \nC. 允许  \nD. 入口",
     "options":["A. 注意","B. 禁止","C. 允许","D. 入口"],
     "answer":"B","solution":"红色圆形斜线标志通常表\"禁止\"。","difficulty":0.30},
    {"kp":"kp_eng3_vie3_sign_menu","form":"fill","item_type":"fill",
     "stem":"看菜单：Menu: cake $5, juice $3, milk $2. 一杯 juice 的价格是 ____ 美元：____",
     "answer":"3","solution":"juice $3，3 美元。","difficulty":0.45},

    # kp_eng3_red3_1500_: 累计阅读量
    {"kp":"kp_eng3_red3_1500_","form":"solve","item_type":"solve",
     "stem":"一级课标要求小学阶段累计课外阅读量达到 ____ 词（请填写数字范围中的较小值）：____",
     "answer":"1500","solution":"一级课标要求累计课外阅读 1500~2000 词。","difficulty":0.30,"writing_prompt":None},

    # kp_eng3_spk3_greet_farewell: 互致问候/道别
    {"kp":"kp_eng3_spk3_greet_farewell","form":"oral_qa","item_type":"fill",
     "stem":"补全对话：A: Hi, I'm Tom. ____ (B 回应并问候)",
     "answer":"Hi, I'm Lily.","solution":"B 应回应问候并自我介绍。","difficulty":0.30},
    {"kp":"kp_eng3_spk3_greet_farewell","form":"oral_qa","item_type":"choice",
     "stem":"放学时和同学道别，最合适的是（　　）\nA. Good night.  \nB. See you.  \nC. How are you?  \nD. Thank you.",
     "options":["A. Good night.","B. See you.","C. How are you?","D. Thank you."],
     "answer":"B","solution":"放学道别用 See you. 最合适。","difficulty":0.45},

    # kp_eng3_spk3_read_aloud: 大声朗读
    {"kp":"kp_eng3_spk3_read_aloud","form":"oral_qa","item_type":"choice",
     "stem":"朗读对话时，下列哪种做法不合适？（　　）\nA. 声音响亮  \nB. 注意语调  \nC. 含含糊糊带过  \nD. 正确发音",
     "options":["A. 声音响亮","B. 注意语调","C. 含含糊糊带过","D. 正确发音"],
     "answer":"C","solution":"朗读应做到清晰正确，含糊带过不合适。","difficulty":0.30},
    {"kp":"kp_eng3_spk3_read_aloud","form":"fill","item_type":"fill",
     "stem":"朗读短句 \"Hello, I'm Lily.\" 时，\"Lily\" 的语调应使用 ____ 调：____",
     "answer":"降","solution":"句末用降调。","difficulty":0.45},

    # kp_eng3_spk3_daily_life: 介绍日常起居
    {"kp":"kp_eng3_spk3_daily_life","form":"oral_qa","item_type":"solve",
     "stem":"用英语写一句话介绍自己早上起床时间，不少于 4 个词：____",
     "answer":"I get up at seven.","solution":"介绍作息可用 I get up at ….","difficulty":0.30,
     "writing_prompt":None},
    {"kp":"kp_eng3_spk3_daily_life","form":"oral_qa","item_type":"fill",
     "stem":"补全句子描述三餐：I have ____ and milk for breakfast.",
     "answer":"bread","solution":"早餐常见搭配 bread and milk。","difficulty":0.45},

    # kp_eng3_wri3_letters_words: 字母单词句子书写
    {"kp":"kp_eng3_wri3_letters_words","form":"spelling","item_type":"fill",
     "stem":"改正下列单词的大小写错误：\"london\" → ____；\"CHINA\" → ____",
     "answer":"London, China","solution":"专有名词首字母大写：London / China。","difficulty":0.30},
    {"kp":"kp_eng3_wri3_letters_words","form":"spelling","item_type":"fill",
     "stem":"句末标点填空：\"How are you ____?\"",
     "answer":"?","solution":"疑问句末用问号。","difficulty":0.45},

    # kp_eng3_wri3_imitation: 仿写句子
    {"kp":"kp_eng3_wri3_imitation","form":"solve","item_type":"solve",
     "stem":"仿照例句 \"I like red apples.\" 写出 1 个含 like 的句子，不少于 4 个词：____",
     "answer":"I like blue pens.","solution":"仿写可换主语、宾语和颜色，如 I like blue pens.","difficulty":0.30,"writing_prompt":None},

    # kp_eng3_wri3_card_letter: 贺卡邀请卡
    {"kp":"kp_eng3_wri3_card_letter","form":"solve","item_type":"solve",
     "stem":"写一张生日贺卡至少 2 句（不少于 10 个英文词），格式：称呼 + 祝贺 + 署名：____",
     "answer":"Happy birthday, Tom! Love, Lily.","solution":"生日贺卡基本格式：Happy birthday + 称呼 + 署名。","difficulty":0.30,
     "writing_prompt":None},
    {"kp":"kp_eng3_wri3_card_letter","form":"fill","item_type":"fill",
     "stem":"补全邀请卡：\"You are ____ to my party!\"（邀请）",
     "answer":"welcome","solution":"常用句型 You are welcome to ….","difficulty":0.45},

    # kp_eng3_lsm3_meta_plan: 制订并执行学习计划
    {"kp":"kp_eng3_lsm3_meta_plan","form":"solve","item_type":"solve",
     "stem":"教师让你制订一个简单的英语学习计划。请写出 1 条计划内容（不少于 5 个英文词）：____",
     "answer":"I read English for 10 minutes every day.","solution":"计划示例：每天读英语 10 分钟。","difficulty":0.30,
     "writing_prompt":None},
    {"kp":"kp_eng3_lsm3_meta_plan","form":"choice","item_type":"choice",
     "stem":"\"制订学习计划\"应包括下列哪项？（　　）\nA. 任意改变时间  \nB. 明确要做的事和时间  \nC. 不告诉任何人  \nD. 只在周末学习",
     "options":["A. 任意改变时间","B. 明确要做的事和时间","C. 不告诉任何人","D. 只在周末学习"],
     "answer":"B","solution":"计划应明确做什么和什么时间做。","difficulty":0.45},

    # kp_eng3_lsm3_cog_old_new: 新旧知识联系
    {"kp":"kp_eng3_lsm3_cog_old_new","form":"solve","item_type":"solve",
     "stem":"已学 apple（一种水果），新学 banana。请用英语写 1 句话把新旧词联系起来（不少于 4 个词）：____",
     "answer":"Apple and banana are fruit.","solution":"把两个旧词用 and 联系起来并归类 fruit。","difficulty":0.30,
     "writing_prompt":None},
    {"kp":"kp_eng3_lsm3_cog_old_new","form":"choice","item_type":"choice",
     "stem":"\"新旧知识联系\"的学习策略不包括下列哪项？（　　）\nA. 用旧词解释新词  \nB. 比喻和对比  \nC. 完全丢弃旧词  \nD. 用熟悉的句型套新词",
     "options":["A. 用旧词解释新词","B. 比喻和对比","C. 完全丢弃旧词","D. 用熟悉的句型套新词"],
     "answer":"C","solution":"完全丢弃旧词不是好的学习策略。","difficulty":0.45},

    # kp_eng3_lsm3_com_slow_repeat: 请对方说慢或重复
    {"kp":"kp_eng3_lsm3_com_slow_repeat","form":"oral_qa","item_type":"fill",
     "stem":"补全对话：A: I can't follow you. B: ____ ? (请对方说慢一些)",
     "answer":"Could you speak slowly, please?","solution":"礼貌请求放慢：Could you speak slowly, please?","difficulty":0.30},
    {"kp":"kp_eng3_lsm3_com_slow_repeat","form":"oral_qa","item_type":"choice",
     "stem":"没听懂老师英语时，下列哪一项最合适？（　　）\nA. 不说  \nB. 请老师说慢一些或重复  \nC. 大声喊  \nD. 离开教室",
     "options":["A. 不说","B. 请老师说慢一些或重复","C. 大声喊","D. 离开教室"],
     "answer":"B","solution":"请对方说慢一些或再说一遍是有效策略。","difficulty":0.45},

    # kp_eng3_lsm3_emo_interest: 对英语有兴趣
    {"kp":"kp_eng3_lsm3_emo_interest","form":"oral_qa","item_type":"solve",
     "stem":"你喜欢参加哪类英语活动能让你保持学习兴趣（写 1 个活动，不少于 3 个英文词）：____",
     "answer":"English songs and games.","solution":"保持兴趣的活动如唱歌、游戏、表演等。","difficulty":0.30,"writing_prompt":None},
    {"kp":"kp_eng3_lsm3_emo_interest","form":"choice","item_type":"choice",
     "stem":"下列哪种做法最有助于保持英语学习兴趣？（　　）\nA. 死记硬背  \nB. 参加英语歌曲表演  \nC. 只听不读  \nD. 完全不开口",
     "options":["A. 死记硬背","B. 参加英语歌曲表演","C. 只听不读","D. 完全不开口"],
     "answer":"B","solution":"歌曲表演能调动兴趣并增强自信。","difficulty":0.45},

    # Additional questions to ensure 2 questions per KP
    {"kp":"kp_eng3_lis3_weekly_","form":"listening","item_type":"fill",
     "stem":"一级课标要求小学阶段每周课外视听不少于 ____ 分钟（填写数字）：____",
     "answer":"30","solution":"一级要求每周课外视听不少于 30 分钟。","difficulty":0.45},
    {"kp":"kp_eng3_red3_1500_","form":"comprehension","item_type":"choice",
     "stem":"一级课标要求小学阶段课外阅读量累计达 ____ 词（　　）\nA. 500~1000  \nB. 1500~2000  \nC. 4000~5000  \nD. 10000~15000",
     "options":["A. 500~1000","B. 1500~2000","C. 4000~5000","D. 10000~15000"],
     "answer":"B","solution":"一级要求课外阅读 1500~2000 词。","difficulty":0.45},
    {"kp":"kp_eng3_wri3_imitation","form":"solve","item_type":"solve",
     "stem":"仿照例句 \"I can swim.\" 写出 1 个含 can 的仿写句（不少于 4 个英文词）：____",
     "answer":"I can dance.","solution":"仿写 can + 动词原形 即可。","difficulty":0.45,"writing_prompt":None},
]