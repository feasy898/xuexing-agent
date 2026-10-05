# Grade 5 English questions (31 KPs × 2 = 62 questions)

GRADE5_Q = [
    # kp_eng5_pha5_blend_word: 拼读规则拼读单词
    {"kp":"kp_eng5_pha5_blend_word","form":"listening","item_type":"choice",
     "stem":"借助拼读规则，下列哪个字母组合通常发 /iː/ 音？（　　）\nA. ea  \nB. sh  \nC. th  \nD. ch",
     "options":["A. ea","B. sh","C. th","D. ch"],
     "answer":"A","solution":"ea 组合常发 /iː/，如 eat / read。","difficulty":0.35},
    {"kp":"kp_eng5_pha5_blend_word","form":"listening","item_type":"fill",
     "stem":"拼读单词：写出字母 b / i / k / e 拼成的单词：____",
     "answer":"bike","solution":"b-i-k-e 拼成 bike。","difficulty":0.50},

    # kp_eng5_pha5_stress_feeling: 句中重读表情感
    {"kp":"kp_eng5_pha5_stress_feeling","form":"listening","item_type":"choice",
     "stem":"朗读 \"I love apples!\" 时，对哪个词重读最能表达喜爱？（　　）\nA. I  \nB. love  \nC. apples  \nD. 不需要重读",
     "options":["A. I","B. love","C. apples","D. 不需要重读"],
     "answer":"C","solution":"重读 apples 表特别喜欢苹果。","difficulty":0.35},
    {"kp":"kp_eng5_pha5_stress_feeling","form":"listening","item_type":"fill",
     "stem":"朗读 \"I don't LIKE it.\" 时，重读 LIKE 表示 ____ 情感：____",
     "answer":"不喜欢","solution":"重读 LIKE 表不喜欢。","difficulty":0.50},

    # kp_eng5_voc5_context_accumulate: 语境中积累词汇
    {"kp":"kp_eng5_voc5_context_accumulate","form":"comprehension","item_type":"choice",
     "stem":"句子 \"Tom is very happy today\" 中 \"happy\" 最可能的意思是（　　）\nA. 伤心的  \nB. 开心的  \nC. 累的  \nD. 饿的",
     "options":["A. 伤心的","B. 开心的","C. 累的","D. 饿的"],
     "answer":"B","solution":"very happy 在句中表\"非常开心\"。","difficulty":0.35},
    {"kp":"kp_eng5_voc5_context_accumulate","form":"fill","item_type":"fill",
     "stem":"在语境中猜词：\"She often helps me. She is helpful.\" helpful 的中文意思：____",
     "answer":"有帮助的","solution":"helpful = 有帮助的。","difficulty":0.50},

    # kp_eng5_voc5_chunks: 习惯用语与固定搭配
    {"kp":"kp_eng5_voc5_chunks","form":"multiple_choice","item_type":"choice",
     "stem":"\"How are you?\" 的固定回答是（　　）\nA. I'm ten.  \nB. I'm fine, thanks.  \nC. I'm from China.  \nD. Goodbye.",
     "options":["A. I'm ten.","B. I'm fine, thanks.","C. I'm from China.","D. Goodbye."],
     "answer":"B","solution":"How are you 的标准回应 I'm fine, thanks.。","difficulty":0.35},
    {"kp":"kp_eng5_voc5_chunks","form":"fill","item_type":"fill",
     "stem":"补全固定搭配：have a look / take a ____ (拍照)",
     "answer":"photo","solution":"take a photo 拍照。","difficulty":0.50},

    # kp_eng5_gra5_sent_structure: 简单句基本结构
    {"kp":"kp_eng5_gra5_sent_structure","form":"multiple_choice","item_type":"choice",
     "stem":"\"She bought a book yesterday.\" 的基本结构是（　　）\nA. 主+谓  \nB. 主+谓+宾+状  \nC. 主+系+表  \nD. There be",
     "options":["A. 主+谓","B. 主+谓+宾+状","C. 主+系+表","D. There be"],
     "answer":"B","solution":"She(主) bought(谓) a book(宾) yesterday(状)。","difficulty":0.35},
    {"kp":"kp_eng5_gra5_sent_structure","form":"fill","item_type":"fill",
     "stem":"指出 \"There are 30 students in our class.\" 的真正主语：____",
     "answer":"students","solution":"There be 结构中真正主语是 students。","difficulty":0.50},

    # kp_eng5_gra5_past_simple: 一般过去时
    {"kp":"kp_eng5_gra5_past_simple","form":"multiple_choice","item_type":"choice",
     "stem":"将 \"I watch TV every day.\" 改为一般过去时（　　）\nA. I watch TV yesterday.  \nB. I watched TV yesterday.  \nC. I watching TV yesterday.  \nD. I watches TV yesterday.",
     "options":["A. I watch TV yesterday.","B. I watched TV yesterday.","C. I watching TV yesterday.","D. I watches TV yesterday."],
     "answer":"B","solution":"watch 的过去式 watched 加 yesterday。","difficulty":0.35},
    {"kp":"kp_eng5_gra5_past_simple","form":"fill","item_type":"fill",
     "stem":"写出动词 \"go\" 的过去式：____",
     "answer":"went","solution":"go 的过去式是不规则 went。","difficulty":0.50},

    # kp_eng5_gra5_future_simple: 一般将来时
    {"kp":"kp_eng5_gra5_future_simple","form":"multiple_choice","item_type":"choice",
     "stem":"补全句子：I ____ visit my grandma tomorrow.（　　）\nA. am  \nB. will  \nC. was  \nD. did",
     "options":["A. am","B. will","C. was","D. did"],
     "answer":"B","solution":"tomorrow 提示用一般将来时 will。","difficulty":0.35},
    {"kp":"kp_eng5_gra5_future_simple","form":"fill","item_type":"fill",
     "stem":"写出 \"will + 动词原形\" 的一般将来时结构助动词：____",
     "answer":"will","solution":"一般将来时用 will + 动词原形。","difficulty":0.50},

    # kp_eng5_gra5_compare_adj: 形容词副词比较级
    {"kp":"kp_eng5_gra5_compare_adj","form":"multiple_choice","item_type":"choice",
     "stem":"补全句子：Lily is ____ than Tom.（　　）\nA. tall  \nB. taller  \nC. tallest  \nD. more tall",
     "options":["A. tall","B. taller","C. tallest","D. more tall"],
     "answer":"B","solution":"than 提示用比较级 taller。","difficulty":0.35},
    {"kp":"kp_eng5_gra5_compare_adj","form":"fill","item_type":"fill",
     "stem":"写出 \"big\" 的比较级：____",
     "answer":"bigger","solution":"big 的比较级双写 g 加 er：bigger。","difficulty":0.50},

    # kp_eng5_dis5_story_frame: 故事类语篇结构
    {"kp":"kp_eng5_dis5_story_frame","form":"comprehension","item_type":"choice",
     "stem":"故事类语篇通常包括（　　）\nA. 开头、经过、结局  \nB. 时间、数据、结论  \nC. 论点、论据、结论  \nD. 标题、目录、索引",
     "options":["A. 开头、经过、结局","B. 时间、数据、结论","C. 论点、论据、结论","D. 标题、目录、索引"],
     "answer":"A","solution":"故事类语篇由开头、经过、结局构成。","difficulty":0.35},
    {"kp":"kp_eng5_dis5_story_frame","form":"fill","item_type":"fill",
     "stem":"写出故事语篇结构的三个部分：开头、____、结局",
     "answer":"经过","solution":"故事结构：开头、经过、结局。","difficulty":0.50},

    # kp_eng5_dis5_exposition: 说明文说明顺序
    {"kp":"kp_eng5_dis5_exposition","form":"comprehension","item_type":"choice",
     "stem":"说明文常用的说明顺序是（　　）\nA. 时间顺序  \nB. 空间顺序  \nC. 总分总 / 时间 / 空间  \nD. 随机顺序",
     "options":["A. 时间顺序","B. 空间顺序","C. 总分总 / 时间 / 空间","D. 随机顺序"],
     "answer":"C","solution":"说明文常用总分总、时间或空间顺序。","difficulty":0.35},
    {"kp":"kp_eng5_dis5_exposition","form":"fill","item_type":"fill",
     "stem":"说明文 \"How to make tea?\" 通常采用 ____ 顺序说明：____",
     "answer":"时间","solution":"做茶步骤按时间顺序。","difficulty":0.50},

    # kp_eng5_prg5_shopping: 购物情境
    {"kp":"kp_eng5_prg5_shopping","form":"oral_qa","item_type":"fill",
     "stem":"补全购物对话：A: ____ can I help you? B: I'd like an apple, please.",
     "answer":"What","solution":"店员常用 What can I help you? 招呼客人。","difficulty":0.35},
    {"kp":"kp_eng5_prg5_shopping","form":"oral_qa","item_type":"choice",
     "stem":"在商店买两斤苹果时，最合适的英语是（　　）\nA. I want apples.  \nB. I'd like two kilos of apples, please.  \nC. Apples, now!  \nD. Give me apples.",
     "options":["A. I want apples.","B. I'd like two kilos of apples, please.","C. Apples, now!","D. Give me apples."],
     "answer":"B","solution":"I'd like + 数量单位 + 商品是购物标准表达。","difficulty":0.50},

    # kp_eng5_prg5_respond_invite: 回应邀请祝愿
    {"kp":"kp_eng5_prg5_respond_invite","form":"oral_qa","item_type":"fill",
     "stem":"补全对话：A: Happy birthday! B: ____",
     "answer":"Thank you!","solution":"对生日祝福回应 Thank you!","difficulty":0.35},
    {"kp":"kp_eng5_prg5_respond_invite","form":"oral_qa","item_type":"choice",
     "stem":"朋友邀请你参加派对，最合适的回应是（　　）\nA. No, never.  \nB. Sure, I'd love to.  \nC. Goodbye.  \nD. I'm fine.",
     "options":["A. No, never.","B. Sure, I'd love to.","C. Goodbye.","D. I'm fine."],
     "answer":"B","solution":"Sure, I'd love to. 是得体回应邀请的表达。","difficulty":0.50},

    # kp_eng5_cul5_etiquette: 跨文化礼仪
    {"kp":"kp_eng5_cul5_etiquette","form":"multiple_choice","item_type":"choice",
     "stem":"在西方国家的正式场合，见面时较常见的礼节是（　　）\nA. 鞠躬  \nB. 握手  \nC. 拥抱很长时间  \nD. 脱鞋",
     "options":["A. 鞠躬","B. 握手","C. 拥抱很长时间","D. 脱鞋"],
     "answer":"B","solution":"西方国家正式场合常以握手问候。","difficulty":0.35},
    {"kp":"kp_eng5_cul5_etiquette","form":"fill","item_type":"fill",
     "stem":"写出英文 \"shake hands\" 的中文意思：____",
     "answer":"握手","solution":"shake hands 握手。","difficulty":0.50},

    # kp_eng5_cul5_festival_meaning: 中外节日
    {"kp":"kp_eng5_cul5_festival_meaning","form":"multiple_choice","item_type":"choice",
     "stem":"感恩节（Thanksgiving）主要流行于（　　）\nA. 中国  \nB. 美国  \nC. 日本  \nD. 印度",
     "options":["A. 中国","B. 美国","C. 日本","D. 印度"],
     "answer":"B","solution":"感恩节是美国重要节日。","difficulty":0.35},
    {"kp":"kp_eng5_cul5_festival_meaning","form":"fill","item_type":"fill",
     "stem":"写出英语 \"Mid-Autumn Festival\" 的中文：____",
     "answer":"中秋节","solution":"Mid-Autumn Festival 是中秋节。","difficulty":0.50},

    # kp_eng5_cul5_literature: 童话寓言
    {"kp":"kp_eng5_cul5_literature","form":"comprehension","item_type":"choice",
     "stem":"\"The Tortoise and the Hare\"（龟兔赛跑）告诉我们的道理是（　　）\nA. 骄傲使人进步  \nB. 持之以恒才能成功  \nC. 跑得快最重要  \nD. 兔子最聪明",
     "options":["A. 骄傲使人进步","B. 持之以恒才能成功","C. 跑得快最重要","D. 兔子最聪明"],
     "answer":"B","solution":"龟兔赛跑寓意坚持不懈才能成功。","difficulty":0.35},
    {"kp":"kp_eng5_cul5_literature","form":"fill","item_type":"fill",
     "stem":"\"The Tortoise and the ____\" 中空缺角色是 ____",
     "answer":"Hare","solution":"龟兔赛跑的另一位主角是 Hare（兔子）。","difficulty":0.50},

    # kp_eng5_cul5_contributors: 中外贡献人物
    {"kp":"kp_eng5_cul5_contributors","form":"multiple_choice","item_type":"choice",
     "stem":"下列哪一位是发明电灯的科学家？（　　）\nA. Edison  \nB. Newton  \nC. Shakespeare  \nD. Lincoln",
     "options":["A. Edison","B. Newton","C. Shakespeare","D. Lincoln"],
     "answer":"A","solution":"Edison 爱迪生发明了电灯。","difficulty":0.35},
    {"kp":"kp_eng5_cul5_contributors","form":"fill","item_type":"fill",
     "stem":"写出英语 \"invent\" 对应的中文（与 Edison 有关）：____",
     "answer":"发明","solution":"invent = 发明。","difficulty":0.50},

    # kp_eng5_cul5_countries_info: 世界主要国家
    {"kp":"kp_eng5_cul5_countries_info","form":"multiple_choice","item_type":"choice",
     "stem":"\"Sydney Opera House\" 位于（　　）\nA. USA  \nB. UK  \nC. Australia  \nD. France",
     "options":["A. USA","B. UK","C. Australia","D. France"],
     "answer":"C","solution":"悉尼歌剧院位于澳大利亚。","difficulty":0.35},
    {"kp":"kp_eng5_cul5_countries_info","form":"fill","item_type":"fill",
     "stem":"写出 \"Australia\" 的中文：____",
     "answer":"澳大利亚","solution":"Australia = 澳大利亚。","difficulty":0.50},

    # kp_eng5_lis5_daily_command: 日常指令
    {"kp":"kp_eng5_lis5_daily_command","form":"listening","item_type":"choice",
     "stem":"听指令：\"Open your books to page 12.\" 你需要做的是（　　）\nA. 关上书  \nB. 翻到第 12 页  \nC. 把书丢掉  \nD. 撕书",
     "options":["A. 关上书","B. 翻到第 12 页","C. 把书丢掉","D. 撕书"],
     "answer":"B","solution":"to page 12 指翻到第 12 页。","difficulty":0.35},
    {"kp":"kp_eng5_lis5_daily_command","form":"listening","item_type":"fill",
     "stem":"听指令并补全：\"____ your books to page ____.\"",
     "answer":"Open, 12","solution":"指令为 Open your books to page 12.。","difficulty":0.50},

    # kp_eng5_lis5_plot: 归纳主要情节
    {"kp":"kp_eng5_lis5_plot","form":"listening","item_type":"choice",
     "stem":"听故事：\"A boy lost his dog. He looked for it everywhere. Finally, he found it at home.\" 故事的主要情节顺序是（　　）\nA. 找狗 → 丢狗 → 找到  \nB. 丢狗 → 找狗 → 找到  \nC. 找到 → 丢狗 → 找狗  \nD. 找狗 → 找到 → 丢狗",
     "options":["A. 找狗 → 丢狗 → 找到","B. 丢狗 → 找狗 → 找到","C. 找到 → 丢狗 → 找狗","D. 找狗 → 找到 → 丢狗"],
     "answer":"B","solution":"按听到内容，情节顺序为\"丢 → 找 → 找到\"。","difficulty":0.35},
    {"kp":"kp_eng5_lis5_plot","form":"listening","item_type":"fill",
     "stem":"听故事回答：Where did he find his dog?  At ____.",
     "answer":"home","solution":"故事最后说 at home。","difficulty":0.50},

    # kp_eng5_vie5_multimodal: 多模态语篇
    {"kp":"kp_eng5_vie5_multimodal","form":"comprehension","item_type":"choice",
     "stem":"海报中通常会包含（　　）\nA. 图片 + 标题 + 关键信息  \nB. 只有文字  \nC. 只有图片  \nD. 杂乱无章",
     "options":["A. 图片 + 标题 + 关键信息","B. 只有文字","C. 只有图片","D. 杂乱无章"],
     "answer":"A","solution":"海报由图、标题和关键信息构成。","difficulty":0.35},
    {"kp":"kp_eng5_vie5_multimodal","form":"fill","item_type":"fill",
     "stem":"英语书封面通常包含 ____ 与作者名（写 1 个）：____",
     "answer":"title","solution":"书封面常含书名 title。","difficulty":0.50},

    # kp_eng5_red5_4000_: 累计阅读 4000~5000
    {"kp":"kp_eng5_red5_4000_","form":"solve","item_type":"solve",
     "stem":"二级课标要求小学高段累计课外阅读量不少于 ____ 词（写出 1 个数字）：____",
     "answer":"4000","solution":"二级要求课外阅读 4000~5000 词。","difficulty":0.35,"writing_prompt":None},

    # kp_eng5_spk5_retell: 复述语篇
    {"kp":"kp_eng5_spk5_retell","form":"oral_qa","item_type":"solve",
     "stem":"听短文后复述大意（不少于 4 个英文词）：A boy helps his mum cook dinner. 然后复述：____",
     "answer":"A boy helps his mum.","solution":"复述可抓住人物和事件：A boy helps his mum.","difficulty":0.35,"writing_prompt":None},

    # kp_eng5_spk5_topic_talk: 围绕主题交流
    {"kp":"kp_eng5_spk5_topic_talk","form":"oral_qa","item_type":"solve",
     "stem":"围绕 \"My hobby\" 主题说 2 句（不少于 8 个英文词）：____",
     "answer":"My hobby is reading. I read every day.","solution":"围绕主题可谈喜好与频率。","difficulty":0.35,"writing_prompt":None},

    # kp_eng5_spk5_speech_plus: 二级＋主题演讲
    {"kp":"kp_eng5_spk5_speech_plus","form":"oral_qa","item_type":"solve",
     "stem":"做简短主题演讲 \"My favourite season\" 至少 2 句（不少于 10 个英文词）：____",
     "answer":"My favourite season is spring. It's warm and nice.","solution":"主题演讲可包含喜好与原因。","difficulty":0.35,"writing_prompt":None},

    # kp_eng5_wri5_pic_paragraph: 看图写连贯描述
    {"kp":"kp_eng5_wri5_pic_paragraph","form":"solve","item_type":"solve",
     "stem":"看图：图中小朋友在公园里放风筝。用 2~3 句话描述图片（不少于 15 个英文词）：____",
     "answer":"This is a park. A boy flies a kite. He is happy.","solution":"看图描述地点、动作、心情。","difficulty":0.35,"writing_prompt":None},

    # kp_eng5_wri5_diary: 写日记
    {"kp":"kp_eng5_wri5_diary","form":"solve","item_type":"solve",
     "stem":"写一篇日记记录今天最开心的事（不少于 3 句，不少于 15 个英文词），格式：日期 + 内容：____",
     "answer":"Today is sunny. I played football with my friends. I was very happy.","solution":"日记要素：日期、天气、事件、心情。","difficulty":0.35,"writing_prompt":None},

    # kp_eng5_wri5_narration: 写一段记叙文
    {"kp":"kp_eng5_wri5_narration","form":"solve","item_type":"solve",
     "stem":"写一段完整记叙文，主题 \"A happy day\" 至少 4 句（不少于 30 个英文词）：____",
     "answer":"Last Sunday, I went to the park with my family. We flew a kite. We had a picnic. We were very happy.","solution":"记叙文四要素：时间、地点、人物、事件。","difficulty":0.35,"writing_prompt":None},

    # kp_eng5_lsm5_preview_review: 预习复习
    {"kp":"kp_eng5_lsm5_preview_review","form":"solve","item_type":"solve",
     "stem":"写出 1 条复习策略（不少于 5 个英文词）：____",
     "answer":"I review English words every week.","solution":"复习策略示例：每周复习单词。","difficulty":0.35,"writing_prompt":None},

    # kp_eng5_lsm5_cog_old_experience: 已有语言积累完成新任务
    {"kp":"kp_eng5_lsm5_cog_old_experience","form":"solve","item_type":"solve",
     "stem":"你会用 \"would like\" 来表达\"想要\"，现在学新短语 \"feel like\"。请写 1 句用 \"feel like\" 表\"想要\"的句子（不少于 4 个英文词）：____",
     "answer":"I feel like juice.","solution":"feel like + 名词 表\"想要\"。","difficulty":0.35,"writing_prompt":None},

    # kp_eng5_lsm5_com_nonverbal: 非语言线索
    {"kp":"kp_eng5_lsm5_com_nonverbal","form":"solve","item_type":"solve",
     "stem":"听到外教一边说 \"great\" 一边竖大拇指。你应理解的非语言含义是 ____：____",
     "answer":"赞扬","solution":"竖大拇指 + great 表示赞扬。","difficulty":0.35,"writing_prompt":None},

    # kp_eng5_lsm5_emo_positive: 保持积极态度
    {"kp":"kp_eng5_lsm5_emo_positive","form":"solve","item_type":"solve",
     "stem":"面对英语考试失利，下列哪种态度属于积极？（　　）\nA. 永远放弃  \nB. 下次更努力  \nC. 怨天尤人  \nD. 抄答案",
     "options":["A. 永远放弃","B. 下次更努力","C. 怨天尤人","D. 抄答案"],
     "answer":"B","solution":"积极的态度是总结经验，下次更努力。","difficulty":0.35},

    # Additional questions to ensure 2 per KP
    {"kp":"kp_eng5_lsm5_preview_review","form":"solve","item_type":"solve",
     "stem":"写出你的英语课后复习策略（不少于 5 个英文词）：____",
     "answer":"I review new words every week.","solution":"复习策略示例。","difficulty":0.50,"writing_prompt":None},
    {"kp":"kp_eng5_lsm5_cog_old_experience","form":"choice","item_type":"choice",
     "stem":"运用已有语言积累学习新内容，下列哪种做法最有效？（　　）\nA. 抛弃旧词  \nB. 用旧词帮助理解新词  \nC. 不看不读  \nD. 只查词典",
     "options":["A. 抛弃旧词","B. 用旧词帮助理解新词","C. 不看不读","D. 只查词典"],
     "answer":"B","solution":"用旧词辅助理解新词符合认知策略。","difficulty":0.50},
    {"kp":"kp_eng5_lsm5_com_nonverbal","form":"choice","item_type":"choice",
     "stem":"外教一边说 \"Sit down, please\" 一边做向下挥手动作，动作的作用是（　　）\nA. 干扰  \nB. 辅助理解  \nC. 完全没有用  \nD. 装饰",
     "options":["A. 干扰","B. 辅助理解","C. 完全没有用","D. 装饰"],
     "answer":"B","solution":"非语言线索能辅助理解。","difficulty":0.50},
    {"kp":"kp_eng5_lsm5_emo_positive","form":"solve","item_type":"solve",
     "stem":"面对英语学习困难，写出 1 个保持自信的方法（不少于 4 个英文词）：____",
     "answer":"I try my best every day.","solution":"保持自信的方法如每天都努力尝试。","difficulty":0.50,"writing_prompt":None},
    {"kp":"kp_eng5_red5_4000_","form":"comprehension","item_type":"choice",
     "stem":"二级课标要求小学高段课外阅读量累计达 ____ 词（　　）\nA. 1500~2000  \nB. 4000~5000  \nC. 10000~15000  \nD. 30000 以上",
     "options":["A. 1500~2000","B. 4000~5000","C. 10000~15000","D. 30000 以上"],
     "answer":"B","solution":"二级要求 4000~5000 词。","difficulty":0.50},
    {"kp":"kp_eng5_spk5_retell","form":"oral_qa","item_type":"solve",
     "stem":"听短文：\"Today is Lily's birthday. Her friends come to her party. They sing a song together.\" 复述大意（不少于 4 个英文词）：____",
     "answer":"Lily has a birthday party.","solution":"复述抓住人物和事件。","difficulty":0.50,"writing_prompt":None},
    {"kp":"kp_eng5_spk5_topic_talk","form":"oral_qa","item_type":"choice",
     "stem":"围绕 \"My favourite food\" 主题交流，下列哪种开头最合适？（　　）\nA. Goodbye.  \nB. My favourite food is noodles.  \nC. I am ten.  \nD. Sit down.",
     "options":["A. Goodbye.","B. My favourite food is noodles.","C. I am ten.","D. Sit down."],
     "answer":"B","solution":"围绕主题开篇直接点明喜好。","difficulty":0.50},
    {"kp":"kp_eng5_spk5_speech_plus","form":"oral_qa","item_type":"solve",
     "stem":"做主题演讲 \"My family\" 至少 2 句（不少于 10 个英文词）：____",
     "answer":"My family is happy. There are four people.","solution":"主题演讲可介绍家庭成员和感受。","difficulty":0.50,"writing_prompt":None},
    {"kp":"kp_eng5_wri5_pic_paragraph","form":"solve","item_type":"solve",
     "stem":"看图：图中小朋友在海边堆沙堡。再多写 2 句描述图中的细节（不少于 12 个英文词）：____",
     "answer":"There is a big castle. The boy is very happy.","solution":"可补充景物、人物感受。","difficulty":0.50,"writing_prompt":None},
    {"kp":"kp_eng5_wri5_diary","form":"solve","item_type":"solve",
     "stem":"再写一段日记续写：今天我和家人去公园做了什么？至少 2 句（不少于 10 个英文词）：____",
     "answer":"We played games. We took many photos.","solution":"日记续写可谈活动与感受。","difficulty":0.50,"writing_prompt":None},
    {"kp":"kp_eng5_wri5_narration","form":"solve","item_type":"solve",
     "stem":"再写一段记叙文续写：A happy day 的中间发生了什么？至少 2 句（不少于 15 个英文词）：____",
     "answer":"We had a picnic. We ate good food and laughed a lot.","solution":"记叙文续写可补充经过细节。","difficulty":0.50,"writing_prompt":None},
]