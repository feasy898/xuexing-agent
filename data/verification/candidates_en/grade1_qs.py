# Grade 1 English questions (14 KPs × 2 = 28 questions)
# Each entry: (form, item_type, stem, options_or_none, answer, solution, difficulty, writing_prompt)

GRADE1_Q = [
    # kp_eng1_pha1_song: 字母歌与字母名称音
    {
        "kp": "kp_eng1_pha1_song",
        "form": "listening",
        "item_type": "choice",
        "stem": "听录音：教师依次读出三个字母 B / D / P 的名称音。下列哪一个字母的名称音和 \"bee / diː / piː\" 对应？（　　）\nA. 三个字母分别对应 B / D / P  \nB. 三个字母分别对应 P / B / D  \nC. 三个字母分别对应 D / P / B  \nD. 三个字母分别对应 B / P / D",
        "options": [
            "A. 三个字母分别对应 B / D / P",
            "B. 三个字母分别对应 P / B / D",
            "C. 三个字母分别对应 D / P / B",
            "D. 三个字母分别对应 B / P / D"
        ],
        "answer": "A",
        "solution": "英语字母 B / D / P 的名称音分别为 /biː/ /diː/ /piː/，与 A 选项顺序一致。",
        "difficulty": 0.3
    },
    {
        "kp": "kp_eng1_pha1_song",
        "form": "listening",
        "item_type": "fill",
        "stem": "字母歌跟唱题。听教师按字母表顺序读出 26 个字母名，写出第 5、第 10、第 15 个字母的名称音对应的字母（大写）：\n(1) 第 5 个：____　(2) 第 10 个：____　(3) 第 15 个：____",
        "answer": "E, J, O",
        "solution": "26 个字母按顺序第 5、10、15 个分别为 E、J、O。",
        "difficulty": 0.35
    },

    # kp_eng1_pha1_rhythm_repeat: 语音语调跟读模仿
    {
        "kp": "kp_eng1_pha1_rhythm_repeat",
        "form": "listening",
        "item_type": "choice",
        "stem": "听录音，模仿跟读 \"Good morning, Miss Li!\" 一句。下列关于这句话语调的说法，正确的是（　　）\nA. \"Good morning\" 整体用降调，\"Miss Li!\" 用升调  \nB. \"Good morning\" 整体用升调，\"Miss Li!\" 用降调  \nC. 两个部分都用平调  \nD. 两个部分都用降调",
        "options": [
            "A. \"Good morning\" 整体用降调，\"Miss Li!\" 用升调",
            "B. \"Good morning\" 整体用升调，\"Miss Li!\" 用降调",
            "C. 两个部分都用平调",
            "D. 两个部分都用降调"
        ],
        "answer": "B",
        "solution": "问候语 \"Good morning\" 整体用升调表问候，被称呼的 \"Miss Li!\" 用降调称呼对方。",
        "difficulty": 0.3
    },
    {
        "kp": "kp_eng1_pha1_rhythm_repeat",
        "form": "listening",
        "item_type": "fill",
        "stem": "听句子 \"I am a pupil.\" 一遍后跟读。请按所听到的语调在 \"am\" 与 \"pupil\" 之间用 ↑ 或 ↓ 标出语调走向：I [____] am a pupil [____].",
        "answer": "↑, ↓",
        "solution": "陈述句中 \"I am a pupil\" 主语 \"I\" 略升调，句末 \"pupil\" 用降调。",
        "difficulty": 0.4
    },

    # kp_eng1_voc1_greeting: 问候与告别
    {
        "kp": "kp_eng1_voc1_greeting",
        "form": "multiple_choice",
        "item_type": "choice",
        "stem": "早上到校遇见老师，最合适的英语表达是（　　）\nA. Good night.  \nB. Good morning.  \nC. Goodbye.  \nD. Thank you.",
        "options": [
            "A. Good night.",
            "B. Good morning.",
            "C. Goodbye.",
            "D. Thank you."
        ],
        "answer": "B",
        "solution": "早上见面问候用 Good morning；A 用于晚上告别，C 用于告别，D 用于感谢。",
        "difficulty": 0.2
    },
    {
        "kp": "kp_eng1_voc1_greeting",
        "form": "picture_qa",
        "item_type": "fill",
        "stem": "看图：图中小朋友正与朋友挥手分别。请写出 1 个合适的英语告别语：____",
        "answer": "Goodbye.",
        "solution": "图中小朋友在挥手分别，最合适的告别表达是 Goodbye. / Bye. / See you.",
        "difficulty": 0.2
    },

    # kp_eng1_voc1_school: 学校生活词块
    {
        "kp": "kp_eng1_voc1_school",
        "form": "picture_qa",
        "item_type": "choice",
        "stem": "看图：教室里一位女士在给同学们上课。下列哪一个单词最符合图片？（　　）\nA. doctor  \nB. teacher  \nC. driver  \nD. nurse",
        "options": [
            "A. doctor",
            "B. teacher",
            "C. driver",
            "D. nurse"
        ],
        "answer": "B",
        "solution": "在教室里给同学们上课的人是老师，对应单词 teacher。",
        "difficulty": 0.2
    },
    {
        "kp": "kp_eng1_voc1_school",
        "form": "picture_qa",
        "item_type": "choice",
        "stem": "看图：桌上放着一支用于书写的细长物品。下列哪一个单词对应图片？（　　）\nA. book  \nB. bag  \nC. pen  \nD. ruler",
        "options": [
            "A. book",
            "B. bag",
            "C. pen",
            "D. ruler"
        ],
        "answer": "C",
        "solution": "用于书写的细长物品是 pen。",
        "difficulty": 0.2
    },

    # kp_eng1_lis1_class_command: 听懂课堂简短指令
    {
        "kp": "kp_eng1_lis1_class_command",
        "form": "listening",
        "item_type": "choice",
        "stem": "听指令并选出正确反应。教师说：\"Stand up, please.\" 你应该（　　）\nA. 坐下  \nB. 起立  \nC. 打开书  \nD. 拍手",
        "options": [
            "A. 坐下",
            "B. 起立",
            "C. 打开书",
            "D. 拍手"
        ],
        "answer": "B",
        "solution": "Stand up 意为\"起立\"，与之对应的反应是站起来。",
        "difficulty": 0.2
    },
    {
        "kp": "kp_eng1_lis1_class_command",
        "form": "listening",
        "item_type": "fill",
        "stem": "听指令并补全空缺的单词。教师说：\"______ your book, please.\" 请填入听到的动词：____ your book, please.",
        "answer": "Open",
        "solution": "课堂常用指令 \"Open your book, please.\" 表示\"请打开书\"。",
        "difficulty": 0.25
    },

    # kp_eng1_lis1_story: 听懂小故事
    {
        "kp": "kp_eng1_lis1_story",
        "form": "listening",
        "item_type": "choice",
        "stem": "听教师讲小故事 \"A cat and a dog\"，故事结尾是 \"They are friends now.\" 故事的主题最可能是（　　）\nA. 猫和狗打架  \nB. 猫和狗成为朋友  \nC. 猫把狗赶走  \nD. 狗追赶猫",
        "options": [
            "A. 猫和狗打架",
            "B. 猫和狗成为朋友",
            "C. 猫把狗赶走",
            "D. 狗追赶猫"
        ],
        "answer": "B",
        "solution": "结尾 \"They are friends now.\" 表明猫和狗最终成为朋友。",
        "difficulty": 0.3
    },
    {
        "kp": "kp_eng1_lis1_story",
        "form": "listening",
        "item_type": "fill",
        "stem": "听故事 \"The hungry caterpillar\" 的开头：\"One day a small caterpillar is hungry. He eats one apple.\" 根据故事，写出 caterpillar 一词对应的中文意思：____",
        "answer": "毛毛虫",
        "solution": "caterpillar 指毛毛虫（吃苹果的小动物）。",
        "difficulty": 0.3
    },

    # kp_eng1_spk1_song_rhyme: 演唱歌曲歌谣
    {
        "kp": "kp_eng1_spk1_song_rhyme",
        "form": "oral_qa",
        "item_type": "solve",
        "stem": "请跟唱学过的字母歌谣，并回答：歌谣中字母 \"B\" 之后的下一个字母是哪一个？写出该字母的大写形式：____",
        "answer": "C",
        "solution": "字母表顺序中 B 之后是 C。",
        "difficulty": 0.25,
        "writing_prompt": None
    },
    {
        "kp": "kp_eng1_spk1_song_rhyme",
        "form": "oral_qa",
        "item_type": "fill",
        "stem": "跟唱 \"Twinkle, twinkle, little star\" 一句后，补全空格处的歌词：\"Twinkle, twinkle, little ____, How I wonder what you are.\"",
        "answer": "star",
        "solution": "歌词原文为 \"Twinkle, twinkle, little star, How I wonder what you are.\"。",
        "difficulty": 0.3
    },

    # kp_eng1_spk1_picture_word: 根据图片说单词
    {
        "kp": "kp_eng1_spk1_picture_word",
        "form": "picture_qa",
        "item_type": "fill",
        "stem": "看图：图上有一只小猫在睡觉。请写出图中小动物的英语单词：____",
        "answer": "cat",
        "solution": "图中是一只猫，对应单词 cat。",
        "difficulty": 0.2
    },
    {
        "kp": "kp_eng1_spk1_picture_word",
        "form": "picture_qa",
        "item_type": "fill",
        "stem": "看图：图上有一个红苹果，旁边写着 \"It's red.\"。请用一句话完整说出图中的颜色（不少于 3 个单词）：____",
        "answer": "It's red.",
        "solution": "描述颜色可用句型 \"It's + 颜色.\"。",
        "difficulty": 0.3
    },

    # kp_eng1_spk1_greet_pair: 互致问候
    {
        "kp": "kp_eng1_spk1_greet_pair",
        "form": "oral_qa",
        "item_type": "fill",
        "stem": "补全对话。A: Hi, I'm Tom. B: ____ (回应问候并报出自己的名字)",
        "answer": "Hi, I'm Lily.",
        "solution": "回应问候并自我介绍：Hi, I'm ….",
        "difficulty": 0.3
    },
    {
        "kp": "kp_eng1_spk1_greet_pair",
        "form": "oral_qa",
        "item_type": "choice",
        "stem": "下午与同学分别时，最合适的英语表达是（　　）\nA. Good morning.  \nB. Good afternoon, bye.  \nC. Good night.  \nD. Hello.",
        "options": [
            "A. Good morning.",
            "B. Good afternoon, bye.",
            "C. Good night.",
            "D. Hello."
        ],
        "answer": "B",
        "solution": "下午告别用 Good afternoon, bye. 最合适。",
        "difficulty": 0.3
    },

    # kp_eng1_spk1_game_talk: 英语游戏中交流
    {
        "kp": "kp_eng1_spk1_game_talk",
        "form": "oral_qa",
        "item_type": "fill",
        "stem": "在 \"猜动物\" 游戏中，同伴说：\"It has four legs. It says 'woof'.\" 请写出答案：____",
        "answer": "dog",
        "solution": "四条腿、叫声 woof 的动物是 dog。",
        "difficulty": 0.25
    },
    {
        "kp": "kp_eng1_spk1_game_talk",
        "form": "oral_qa",
        "item_type": "fill",
        "stem": "在 \"Simon says\" 游戏中，教师说 \"Simon says touch your nose.\" 请写出你应碰触的身体部位：____",
        "answer": "nose",
        "solution": "touch your nose 指碰触鼻子，鼻子英文是 nose。",
        "difficulty": 0.2
    },

    # kp_eng1_vie1_cartoon: 看英语动画片
    {
        "kp": "kp_eng1_vie1_cartoon",
        "form": "picture_qa",
        "item_type": "choice",
        "stem": "观看英语小动画：主人公每天早上对妈妈说 \"Good morning, Mum.\"。这个场景最可能发生的时间是（　　）\nA. 晚上睡觉前  \nB. 早上起床后  \nC. 中午吃饭时  \nD. 下午放学后",
        "options": [
            "A. 晚上睡觉前",
            "B. 早上起床后",
            "C. 中午吃饭时",
            "D. 下午放学后"
        ],
        "answer": "B",
        "solution": "Good morning 用于早上问候，与\"早上起床后\"的场景一致。",
        "difficulty": 0.25
    },
    {
        "kp": "kp_eng1_vie1_cartoon",
        "form": "picture_qa",
        "item_type": "fill",
        "stem": "观看英语动画片段：主人公唱 \"Hello, hello, what's your name?\" 请写出向对方询问名字的英语句子：____",
        "answer": "What's your name?",
        "solution": "询问对方名字的英语是 What's your name?",
        "difficulty": 0.3
    },

    # kp_eng1_prg1_greet: 问候与告别的得体表达
    {
        "kp": "kp_eng1_prg1_greet",
        "form": "oral_qa",
        "item_type": "choice",
        "stem": "在学校走廊遇见外教，最得体的问候是（　　）\nA. (大声喊) Hi! Hi! Hi!  \nB. (微笑点头) Hello, Mr Brown.  \nC. (扭头不理)  \nD. (直接跑过去) Bye!",
        "options": [
            "A. (大声喊) Hi! Hi! Hi!",
            "B. (微笑点头) Hello, Mr Brown.",
            "C. (扭头不理)",
            "D. (直接跑过去) Bye!"
        ],
        "answer": "B",
        "solution": "遇见师长应礼貌称呼并问候，Hello, Mr Brown. 最得体。",
        "difficulty": 0.3
    },
    {
        "kp": "kp_eng1_prg1_greet",
        "form": "oral_qa",
        "item_type": "fill",
        "stem": "放学时同学对你说：\"See you tomorrow!\" 你最合适的英语回应是：____",
        "answer": "See you!",
        "solution": "对 See you tomorrow 的得体回应是 See you.",
        "difficulty": 0.25
    },

    # kp_eng1_lsm1_confident: 敢于开口
    {
        "kp": "kp_eng1_lsm1_confident",
        "form": "oral_qa",
        "item_type": "solve",
        "stem": "口语练习时，你把 \"apple\" 说成了 \"abple\"，老师请同伴纠正。最合适的态度是（　　）\nA. 怕出错再也不开口  \nB. 改正后继续大胆朗读  \nC. 拒绝再读  \nD. 嘲笑说错的同学",
        "answer": "B",
        "solution": "敢于开口、不怕出错是学习英语的好习惯，改正后继续大胆朗读。",
        "difficulty": 0.25,
        "writing_prompt": None
    },
    {
        "kp": "kp_eng1_lsm1_confident",
        "form": "oral_qa",
        "item_type": "fill",
        "stem": "老师请同学上台用英语介绍自己。一位同学紧张地说：\"I… I'm… I'm Lily.\" 他的发言体现的最重要学习策略是：____",
        "answer": "敢于开口，不怕出错",
        "solution": "紧张仍坚持说英语，体现敢于开口、不怕出错的学习态度。",
        "difficulty": 0.3
    },

    # kp_eng1_lsm1_picture_word_link: 借助图片实物建立词物联系
    {
        "kp": "kp_eng1_lsm1_picture_word_link",
        "form": "picture_qa",
        "item_type": "fill",
        "stem": "教师出示实物：一根香蕉。请写出香蕉对应的英语单词：____",
        "answer": "banana",
        "solution": "实物香蕉对应英文单词 banana。",
        "difficulty": 0.2
    },
    {
        "kp": "kp_eng1_lsm1_picture_word_link",
        "form": "picture_qa",
        "item_type": "choice",
        "stem": "看图：图中是一只小狗在啃骨头。下列哪一项最准确地把图、英文和中文对应起来？（　　）\nA. 图—cat—猫  \nB. 图—dog—狗  \nC. 图—bird—鸟  \nD. 图—fish—鱼",
        "options": [
            "A. 图—cat—猫",
            "B. 图—dog—狗",
            "C. 图—bird—鸟",
            "D. 图—fish—鱼"
        ],
        "answer": "B",
        "solution": "图中是狗，对应英文 dog、中文\"狗\"。",
        "difficulty": 0.2
    },
]