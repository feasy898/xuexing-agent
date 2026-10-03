# Grade 2 English questions (12 KPs × 2 = 24 questions)

GRADE2_Q = [
    # kp_eng2_pha2_order: 字母表顺序与大小写书写
    {
        "kp": "kp_eng2_pha2_order",
        "form": "listening",
        "item_type": "choice",
        "stem": "下列 4 个大小写字母配对中，书写规范且匹配正确的是（　　）\nA. b—B  \nB. d—D  \nC. p—P  \nD. q—Q",
        "options": [
            "A. b—B",
            "B. d—D",
            "C. p—P",
            "D. q—Q"
        ],
        "answer": "C",
        "solution": "PEP 字母写法中只有小写 p 与大写 P 的笔画结构最匹配，b/B、d/D、q/Q 都不一致。",
        "difficulty": 0.3
    },
    {
        "kp": "kp_eng2_pha2_order",
        "form": "spelling",
        "item_type": "fill",
        "stem": "按字母表顺序，写出 G 后面的 3 个连续字母（大写）：____",
        "answer": "H, I, J",
        "solution": "字母表顺序中 G 后是 H、I、J。",
        "difficulty": 0.3
    },

    # kp_eng2_pha2_syllable: 单词音节与拍读
    {
        "kp": "kp_eng2_pha2_syllable",
        "form": "listening",
        "item_type": "choice",
        "stem": "下列单词中音节数与其他三个不同的是（　　）\nA. cat  \nB. dog  \nC. apple  \nD. book",
        "options": [
            "A. cat",
            "B. dog",
            "C. apple",
            "D. book"
        ],
        "answer": "C",
        "solution": "cat、dog、book 都是单音节，apple 是双音节。",
        "difficulty": 0.3
    },
    {
        "kp": "kp_eng2_pha2_syllable",
        "form": "listening",
        "item_type": "fill",
        "stem": "听教师拍读单词 \"banana\"（ba-na-na），写出这个单词共有几个音节：____",
        "answer": "3",
        "solution": "banana 拆分为 ba-na-na 共 3 个音节。",
        "difficulty": 0.35
    },

    # kp_eng2_voc2_clothes: 衣物与日用品
    {
        "kp": "kp_eng2_voc2_clothes",
        "form": "picture_qa",
        "item_type": "choice",
        "stem": "看图：图中小朋友头上戴着一件遮阳的衣物。下列哪一个单词对应图片？（　　）\nA. shoes  \nB. coat  \nC. hat  \nD. bag",
        "options": [
            "A. shoes",
            "B. coat",
            "C. hat",
            "D. bag"
        ],
        "answer": "C",
        "solution": "戴在头上遮阳的衣物是 hat。",
        "difficulty": 0.2
    },
    {
        "kp": "kp_eng2_voc2_clothes",
        "form": "picture_qa",
        "item_type": "choice",
        "stem": "看图：图中的鞋是红色的。补全句子：The ____ are red.（　　）\nA. coat  \nB. shoes  \nC. hat  \nD. bag",
        "options": [
            "A. coat",
            "B. shoes",
            "C. hat",
            "D. bag"
        ],
        "answer": "B",
        "solution": "鞋是复数形式 shoes，与 are 保持一致。",
        "difficulty": 0.25
    },

    # kp_eng2_lis2_command_seq: 听连续多步指令
    {
        "kp": "kp_eng2_lis2_command_seq",
        "form": "listening",
        "item_type": "choice",
        "stem": "听教师指令：\"Open your book. Point to the pen.\" 下列执行顺序正确的是（　　）\nA. 先指笔，再打开书  \nB. 先打开书，再指笔  \nC. 只打开书  \nD. 只指笔",
        "options": [
            "A. 先指笔，再打开书",
            "B. 先打开书，再指笔",
            "C. 只打开书",
            "D. 只指笔"
        ],
        "answer": "B",
        "solution": "指令的顺序是先 \"Open your book\" 后 \"Point to the pen\"。",
        "difficulty": 0.3
    },
    {
        "kp": "kp_eng2_lis2_command_seq",
        "form": "listening",
        "item_type": "fill",
        "stem": "听指令：\"Stand up. Open your book.\" 补全第二个动词：Stand up. ____ your book.",
        "answer": "Open",
        "solution": "第二句动词为 Open（打开）。",
        "difficulty": 0.3
    },

    # kp_eng2_lis2_story_seq: 听懂小故事的事件顺序
    {
        "kp": "kp_eng2_lis2_story_seq",
        "form": "listening",
        "item_type": "choice",
        "stem": "听故事 \"The Lost Cat\" 的三段顺序：① The cat is lost. ② Mum finds the cat. ③ Tom looks for the cat. 正确的事件顺序是（　　）\nA. ①②③  \nB. ③①②  \nC. ②③①  \nD. ①③②",
        "options": [
            "A. ①②③",
            "B. ③①②",
            "C. ②③①",
            "D. ①③②"
        ],
        "answer": "D",
        "solution": "事件顺序应为\"猫走丢 → Tom 去找 → Mum 找到猫\"，即①③②。",
        "difficulty": 0.35
    },
    {
        "kp": "kp_eng2_lis2_story_seq",
        "form": "listening",
        "item_type": "fill",
        "stem": "听故事：\"First, Tom is sad. Next, he looks for the cat. Finally, Mum finds it.\" 故事最后作者的心情最可能是：____",
        "answer": "happy",
        "solution": "猫被找到后，Tom 应感到开心，对应英文 happy。",
        "difficulty": 0.35
    },

    # kp_eng2_spk2_intro_family: 介绍自己的家庭
    {
        "kp": "kp_eng2_spk2_intro_family",
        "form": "oral_qa",
        "item_type": "fill",
        "stem": "补全句子介绍家人：\"This is my ____. He is my father.\"（写出一个表示家庭身份的词）____",
        "answer": "dad",
        "solution": "介绍父亲可用 dad / father。",
        "difficulty": 0.25
    },
    {
        "kp": "kp_eng2_spk2_intro_family",
        "form": "oral_qa",
        "item_type": "choice",
        "stem": "你想向同学介绍你的妈妈，下列哪句最合适？（　　）\nA. This is my mum. She is nice.  \nB. He is my mum.  \nC. She is my dad.  \nD. This is my mum. He is tall.",
        "options": [
            "A. This is my mum. She is nice.",
            "B. He is my mum.",
            "C. She is my dad.",
            "D. This is my mum. He is tall."
        ],
        "answer": "A",
        "solution": "介绍妈妈用 This is my mum，搭配代词 she 描述。",
        "difficulty": 0.3
    },

    # kp_eng2_spk2_sing_alone: 独立演唱英语歌曲
    {
        "kp": "kp_eng2_spk2_sing_alone",
        "form": "oral_qa",
        "item_type": "fill",
        "stem": "学唱字母歌时，写出其中一句歌词（任写一个完整小节，不少于 4 个词）：____",
        "answer": "A B C D E F G",
        "solution": "字母歌经典歌词 A B C D E F G。",
        "difficulty": 0.3
    },
    {
        "kp": "kp_eng2_spk2_sing_alone",
        "form": "oral_qa",
        "item_type": "choice",
        "stem": "下列哪一项最适合作为演唱 \"If You're Happy\" 时的动作？（　　）\nA. 拍手（clap your hands）  \nB. 坐下  \nC. 睡觉  \nD. 吃饭",
        "options": [
            "A. 拍手（clap your hands）",
            "B. 坐下",
            "C. 睡觉",
            "D. 吃饭"
        ],
        "answer": "A",
        "solution": "\"If You're Happy\" 经典动作是 clap your hands 拍手。",
        "difficulty": 0.25
    },

    # kp_eng2_spk2_story_perform: 表演小故事
    {
        "kp": "kp_eng2_spk2_story_perform",
        "form": "oral_qa",
        "item_type": "solve",
        "stem": "在表演小故事 \"The Very Hungry Caterpillar\" 时，你扮演 caterpillar。请写一句你的台词（不少于 3 个英文单词）：____",
        "answer": "I'm so hungry!",
        "solution": "扮演毛毛虫可用 I'm so hungry! 等台词。",
        "difficulty": 0.3,
        "writing_prompt": None
    },
    {
        "kp": "kp_eng2_spk2_story_perform",
        "form": "oral_qa",
        "item_type": "fill",
        "stem": "表演故事时同伴说：\"Hello, I'm a little cat.\" 你扮演小狗，最合适的回应是：____",
        "answer": "Hello, I'm a little dog.",
        "solution": "回应介绍应保持角色一致：Hello, I'm a little dog.",
        "difficulty": 0.3
    },

    # kp_eng2_vie2_20min: 每周英语视听
    {
        "kp": "kp_eng2_vie2_20min",
        "form": "picture_qa",
        "item_type": "choice",
        "stem": "下列哪项安排最符合\"每周英语视听不少于 20 分钟\"的要求？（　　）\nA. 每天看 3 分钟英语动画  \nB. 每周只听一次，每次 5 分钟  \nC. 每周 4 次，每次听看 5 分钟英语  \nD. 从不看英语动画",
        "options": [
            "A. 每天看 3 分钟英语动画",
            "B. 每周只听一次，每次 5 分钟",
            "C. 每周 4 次，每次听看 5 分钟英语",
            "D. 从不看英语动画"
        ],
        "answer": "C",
        "solution": "每周 4 次 × 5 分钟 = 20 分钟，达标且分散进行更合理。",
        "difficulty": 0.3
    },
    {
        "kp": "kp_eng2_vie2_20min",
        "form": "oral_qa",
        "item_type": "fill",
        "stem": "完成句子，描述你的英语视听计划：\"I watch English cartoon for ____ minutes every week.\"",
        "answer": "20",
        "solution": "预备级要求每周视听不少于 20 分钟。",
        "difficulty": 0.25
    },

    # kp_eng2_prg2_thanks: 致谢与回应致谢
    {
        "kp": "kp_eng2_prg2_thanks",
        "form": "oral_qa",
        "item_type": "fill",
        "stem": "补全对话。A: Thank you for your book.  A1: ____ (回应致谢)",
        "answer": "You're welcome.",
        "solution": "回应致谢的得体说法是 You're welcome. / That's OK.",
        "difficulty": 0.25
    },
    {
        "kp": "kp_eng2_prg2_thanks",
        "form": "oral_qa",
        "item_type": "choice",
        "stem": "同学帮你捡起掉在地上的铅笔，你最合适的英语回应是（　　）\nA. Thank you.  \nB. Goodbye.  \nC. Good morning.  \nD. I'm sorry.",
        "options": [
            "A. Thank you.",
            "B. Goodbye.",
            "C. Good morning.",
            "D. I'm sorry."
        ],
        "answer": "A",
        "solution": "获得帮助应说 Thank you. 表感谢。",
        "difficulty": 0.2
    },

    # kp_eng2_lsm2_link_oldnew: 新旧知识之间建立联系
    {
        "kp": "kp_eng2_lsm2_link_oldnew",
        "form": "oral_qa",
        "item_type": "fill",
        "stem": "你学过 apple，现在学 banana。用一句新方法两个词编一句口诀（不少于 4 个英文词）：____",
        "answer": "Apple and banana.",
        "solution": "把新旧词用 and 连接形成口诀，如 Apple and banana.",
        "difficulty": 0.3
    },
    {
        "kp": "kp_eng2_lsm2_link_oldnew",
        "form": "oral_qa",
        "item_type": "choice",
        "stem": "学习新词 \"tiger\" 时，下列哪项最能帮助你联系已学词？（　　）\nA. 只记单词表  \nB. 与已学 \"cat\" 对比：cat 小，tiger 大  \nC. 不看不读  \nD. 只抄写字母",
        "options": [
            "A. 只记单词表",
            "B. 与已学 \"cat\" 对比：cat 小，tiger 大",
            "C. 不看不读",
            "D. 只抄写字母"
        ],
        "answer": "B",
        "solution": "在新旧词之间建立形象对比，能帮助理解和记忆。",
        "difficulty": 0.3
    },

    # kp_eng2_lsm2_interest: 保持英语学习兴趣
    {
        "kp": "kp_eng2_lsm2_interest",
        "form": "oral_qa",
        "item_type": "solve",
        "stem": "老师要在班级开展英语活动，下列哪一项最有助于保持同学们的英语学习兴趣？（　　）\nA. 只做抄写作业  \nB. 只听写单词  \nC. 英语歌曲合唱比赛  \nD. 不安排任何活动",
        "options": [
            "A. 只做抄写作业",
            "B. 只听写单词",
            "C. 英语歌曲合唱比赛",
            "D. 不安排任何活动"
        ],
        "answer": "C",
        "solution": "英语歌曲合唱比赛既能调动兴趣又能让大家开口说英语。",
        "difficulty": 0.25,
        "writing_prompt": None
    },
    {
        "kp": "kp_eng2_lsm2_interest",
        "form": "oral_qa",
        "item_type": "fill",
        "stem": "写出 1 个你喜欢参加的英语学习活动：____",
        "answer": "English songs",
        "solution": "如 English songs / English games / English stories。",
        "difficulty": 0.2
    },
]