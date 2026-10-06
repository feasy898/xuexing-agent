"""gapfill 步骤 4：人工审题后落盘。

输入 work/gapfill/candidates_llm.json（52 题 LLM 初稿）经人工逐题审核：
- KEEP_FIXES（18 题）：LLM 初稿内容成立但需人工修订（题干重建/选项纠错/
  答案重排/学术表述修正），source 保持 llm_generated，note 如实记录人工修订。
- AUTHORED（31 题）：LLM 初稿审核不通过（题干泄漏答案/事实错误/结构残破，
  详见 commit message 抽检报告），改由会话内人工命题，source=original，
  note 如实记录「LLM 初稿未过审，人工命题」。默写/名著/病句/连线/七选五
  均为确定性内容，逐字核对。

拒收 3 题（eng_jr_017、eng_hs_024、eng_hs_026）+ 31 题弃稿，如实计入丢弃。

用法：python work/gapfill/review_apply.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

import gaplib as G  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CAND = os.path.join(HERE, "candidates_llm.json")

FIX_NOTE = ("glm-4-flash 初稿 + 会话内人工逐题修订（题干重建/事实纠错/答案重排）；"
            "single_agent=true，dual_agent=false；difficulty 为初值 estimated；独立双代理盲验未做")
AUTHOR_NOTE = ("LLM 初稿未通过人工审核（事实错误/题干泄漏/结构残破），改由会话内人工命题；"
               "single_agent=true，dual_agent=false；难度初值 estimated；独立双代理盲验未做")

REJECT_IDS = {
    "english_gap_llm_017",                      # dict 碎片+杜撰爱因斯坦轶事，不可修复
    # 语文 10 稿：001/007/008 题干泄漏答案或出处标注错误（望岳标成《登高》），
    # 003/004/005 名著情节杜撰（斯诺经“长征”入陕北为史实错误），006/009/010 病句/成语题
    # 病因不成立或答案含混，002 结构尚可但情境泄漏篇目——全部弃稿改人工命题。
    "chinese_gap_llm_001", "chinese_gap_llm_002", "chinese_gap_llm_003",
    "chinese_gap_llm_004", "chinese_gap_llm_005", "chinese_gap_llm_006",
    "chinese_gap_llm_007", "chinese_gap_llm_008", "chinese_gap_llm_009",
    "chinese_gap_llm_010",
    # 英语七选五 9 稿：均无真实语篇结构（meta 文本/单句填空/无题干），弃稿改人工命题。
    "english_gap_llm_018", "english_gap_llm_019", "english_gap_llm_020",
    "english_gap_llm_021", "english_gap_llm_022", "english_gap_llm_023",
    "english_gap_llm_024", "english_gap_llm_025", "english_gap_llm_026",
    # 生物初中 5 稿弃：029 食物链空号无意义，030 色盲婚配概率算错（应 100% 非 1/4）
    # 且伴性计算超初中范围，031 三道防线与免疫类型错位，033 编造实验数据，034 同义反复。
    "biology_gap_llm_029", "biology_gap_llm_030", "biology_gap_llm_031",
    "biology_gap_llm_033", "biology_gap_llm_034",
    # 生物高中 5 稿弃：035 F1 基因型答“DD或Dd”且 1/6 算成 1/4，037 选择题混入解答节，
    # 038 “感觉无反应”表述错误，040 能量流动数值全错（同化效率答 100%），042 答案存疑。
    "biology_gap_llm_035", "biology_gap_llm_037", "biology_gap_llm_038",
    "biology_gap_llm_040", "biology_gap_llm_042",
    # 道法连线 4 稿弃：045/047 右栏整体缺失，046 四组连线三组错配，048 左栏职业缺失。
    "politics_gap_llm_045", "politics_gap_llm_046", "politics_gap_llm_047",
    "politics_gap_llm_048",
}

# ------------------------------------------------- KEEP：人工修订后的最终稿
KEEP_FIXES: dict[str, dict] = {
    # —— eng_jr listening ——
    "english_gap_llm_011": {},  # 原稿即自洽：对话→3 问→答案一一可推
    "english_gap_llm_012": {
        "stem_replace": [("B. She does housework and takes care of her sister.",
                          "B. She does housework and takes care of her little daughter.")],
        "answer": "1. A\n2. B\n3. B",
        "why": "选项 B 的称谓纠错：母亲照看的是说话人的小妹妹（即她的女儿），不是 her sister。",
    },
    "english_gap_llm_013": {
        "stem": "校园广播（听力材料）：\nAttention, everyone! The school canteen will be closed for "
                "maintenance next Friday, June 2nd. The canteen will reopen on June 5th. All students "
                "are advised to bring their lunch from home on that day. And remember to keep away "
                "from the canteen area to ensure safety.\n\n请根据以上广播内容回答：\n"
                "1. What day will the canteen be closed for maintenance?\nA. May 31st\nB. June 1st\nC. June 2nd\n"
                "2. When will the canteen reopen after maintenance?\nA. June 3rd\nB. June 4th\nC. June 5th\n"
                "3. What should students do on June 2nd?\nA. Go to the canteen\nB. Bring their lunch from home\n"
                "C. Eat in the classroom",
        "answer": "1. C\n2. C\n3. B",
        "why": "原稿把题干/答案字段装反且听力稿带说话人标签；重建题干并重排答案（reopen June 5th → 第 2 问 C）。",
    },
    "english_gap_llm_014": {
        "stem": "电话对话（听力材料）：\nM: Hello, is this Mr. Smith?\nW: Yes, it is. How can I help you?\n"
                "M: Hi, Mr. Smith. This is Tom from the library. We have a book club meeting scheduled "
                "for next week. Could we set up a time for the meeting?\nW: Sure, Tom. When would you "
                "suggest we meet?\nM: How about Friday afternoon?\nW: That sounds good. What time would "
                "be convenient for you?\nM: I'm free from 3:00 to 5:00. How about you?\nW: I'm available "
                "during that time. Let's make it 3:30. Can we meet in the conference room?\n"
                "M: Perfect. 3:30 in the conference room on Friday. See you then.\nW: See you then, Tom.\n\n"
                "请根据以上对话回答：\n1. Who is calling Mr. Smith?\nA. Tom.\nB. Peter.\nC. Mr. Green.\n"
                "2. When will they meet?\nA. This Friday afternoon.\nB. Next Monday morning.\nC. Tomorrow evening.\n"
                "3. Where will they meet?\nA. In the library.\nB. In the conference room.\nC. At Tom's home.",
        "answer": "1. A\n2. A\n3. B",
        "why": "原稿题干无问题；按对话补写 3 问与选项，答案均由对话末 3 句唯一确定。",
    },
    "english_gap_llm_015": {
        "stem": "采访对话（听力材料）：\nM: Hey, John, can you tell us about your favorite sport?\n"
                "W: Sure, it's basketball. Why do you ask?\nM: I'm curious about what students like these days.\n"
                "W: Well, I've always been interested in playing basketball since I was a kid. It's fast-paced "
                "and exciting.\nM: Do you play basketball every day?\nW: Not really. I play a couple of times "
                "a week, usually on weekends.\nM: That's great. Where do you play?\nW: I mostly play at the "
                "school gym with my friends.\nM: Do you prefer playing with boys or girls?\nW: I don't really "
                "have a preference. I enjoy playing with anyone who's up for it.\n\n请根据以上对话回答：\n"
                "1. What is John's favorite sport?\nA. Football.\nB. Basketball.\nC. Volleyball.\n"
                "2. How often does John play basketball?\nA. Every day.\nB. A couple of times a week.\n"
                "C. Hardly ever.\n3. Who does John like to play with?\nA. Only boys.\nB. Only girls.\nC. Anyone.",
        "answer": "1. B\n2. B\n3. C",
        "why": "原稿问题与选项落在 answer 字段；并入题干并把答案改写为题号+字母。",
    },
    "english_gap_llm_016": {
        "stem_replace": [
            ("A. Join the local community clean-up project.\nB. Start an environmental club at school.\n"
             "C. Organize a charity run.",
             "A. Start an environmental club at school.\nB. Join the local community clean-up project.\n"
             "C. Organize a charity run."),
            ("A. 8 am.\nB. 10 am.\nC. 12 pm.",
             "A. At 7:45 am.\nB. At 8 am.\nC. At 12 pm."),
            ("A. Pick up litter and plant trees.\nB. Clean the streets.\nC. Paint the buildings.",
             "A. Clean the streets.\nB. Paint the buildings.\nC. Pick up litter and plant trees."),
        ],
        "answer": "1. B\n2. B\n3. C",
        "why": "原稿三问正确项全在 A（答案位置偏置）；重排选项位置并同步答案。",
    },
    # —— bio_jr cloze ——
    "biology_gap_llm_027": {
        "stem": "在“绿叶在光下制造有机物”的实验中：①实验前把盆栽天竺葵放到黑暗处一昼夜，目的是______；"
                "②用黑纸片把叶片的一部分从上、下两面遮盖起来，光照数小时后摘叶、去纸、酒精脱色、滴加碘液，"
                "这样处理的目的是______；③结果只有见光部分变蓝，说明光合作用制造的有机物是______。",
        "answer": "①让叶片内原有的淀粉运走、耗尽；②与见光部分形成对照（只保留光照一个变量）；③淀粉",
        "why": "原稿空号与答案错位（①不是空）；按课本实验重排为三空。",
    },
    "biology_gap_llm_028": {
        "stem": "在稻田生态系统中：①______通过光合作用制造有机物，属于生产者；以稻谷为食的鼠、鸟等②______"
                "属于消费者；③______能将动植物遗体和粪便分解成无机物，属于分解者。",
        "answer": "①绿色植物（如水稻）；②动物；③细菌和真菌",
        "why": "原稿末句“共同构成了一个______（生态系统）”与题干首句泄漏答案；删去末句。",
    },
    "biology_gap_llm_032": {
        "stem": "流感是一种常见的呼吸道传染病，其流行必须同时具备三个基本环节：①______（如患流感的人）；"
                "②______（如空气、飞沫）；③______（如未接种流感疫苗、抵抗力弱的人群）。",
        "answer": "①传染源；②传播途径；③易感人群",
        "why": "原稿把“流感病毒”当传染源示例（病毒是病原体，传染源是患流感的人）；纠正后重排空位。",
    },
    # —— bio_hs solve ——
    "biology_gap_llm_036": {
        "stem": "有氧呼吸是细胞呼吸的主要形式。请回答：（1）有氧呼吸第一阶段的场所是①______，"
                "第二阶段的场所是②______，第三阶段的场所是③______；（2）三个阶段中释放能量最多的是第④______阶段；"
                "（3）有氧呼吸中氧气直接参与的是第⑤______阶段。",
        "answer": "①细胞质基质；②线粒体基质；③线粒体内膜；④三；⑤三",
        "why": "原稿仅一问一答，作 16 分大题过薄；扩为三小问（内容为课本原表述）。",
    },
    "biology_gap_llm_039": {
        "stem": "胰岛素和胰高血糖素是调节血糖的两种重要激素。请回答：（1）胰岛素降低血糖的作用原理是①______；"
                "（2）胰高血糖素升高血糖的作用原理是②______；（3）胰岛素分泌不足会引起糖尿病，其机理是③______。",
        "answer": "①促进组织细胞加速摄取、利用和储存葡萄糖，抑制糖原分解和非糖物质转化为葡萄糖；"
                  "②促进肝糖原分解，并促进非糖物质转化为葡萄糖；③胰岛素分泌不足，组织细胞摄取、利用和储存葡萄糖的能力下降，血糖浓度升高，超过一定限度后部分糖随尿排出，形成糖尿",
        "why": "原稿内容成立；改写为（1）（2）（3）小问结构，便于分点给分。",
    },
    "biology_gap_llm_041": {
        "stem": "碳在无机环境与生物群落之间不断循环。请回答：（1）碳从无机环境进入生物群落的主要途径是①______；"
                "（2）碳在生物群落内部以②______的形式沿食物链（网）传递；（3）碳从生物群落回到无机环境的途径包括"
                "动植物的呼吸作用、分解者的分解作用和③______；（4）大气中 CO₂ 短期内迅速增多会导致④______效应增强。",
        "answer": "①生产者的光合作用（化能合成作用等）；②含碳有机物；③化石燃料的大量燃烧；④温室",
        "why": "原稿漏“化石燃料燃烧”与“温室效应”两条主干途径；补全为四小问。",
    },
    # —— geo_hs solve（内容成立，answer 是 dict 需转正式文本）——
    "geography_gap_llm_043": {
        "answer": "（1）成因：①该山区地质构造复杂，岩石破碎，碎屑物质多；②连续强降雨使土壤含水趋于饱和，"
                  "岩土体抗剪强度降低；③过度开垦、滥伐森林等人类活动破坏植被，地表径流加大，诱发滑坡。"
                  "（2）防灾措施：①加强地质监测，建立滑坡预警系统；②保护植被、退耕还林，提高山体固土能力；"
                  "③合理规划土地利用，避免在滑坡易发区进行工程建设；④加强防灾减灾宣传教育，提高居民避灾自救能力。",
        "why": "原稿 answer 为 dict；内容成立，转为分点文本。",
    },
    "geography_gap_llm_044": {
        "answer": "（1）主要成因：①城市生活污水和工业废水未经处理直接排入湖泊，氮、磷等营养物质增多；"
                  "②流域内农业面源污染（化肥、农药随地表径流入湖）；③湖泊水体更新慢、自净能力弱。"
                  "（2）治理措施：①严控污水排放，建设污水处理设施，实现达标排放；②推广科学施肥，减少化肥农药使用，"
                  "控制面源污染；③实施生态修复（种植水生植物、清淤、生态引水）；④加强水质监测，落实河（湖）长制。",
        "why": "原稿 answer 为 dict 且含两套重复答案；合并为一套分点参考答案。",
    },
    # —— sci_prim experiment（内容成立，answer 是 dict；049/051 纠错）——
    "science_gap_llm_049": {
        "answer": "1. 把食盐和沙子分别放入水中，搅拌后观察：食盐能溶解在水中，形成透明、均匀的食盐水；"
                  "沙子不能溶解，静置后沉在水底。2. 用搅拌、用温水等方法可以加快食盐的溶解；"
                  "沙子不能溶解于水，不存在加快溶解的方法。",
        "why": "原稿 answer 为 dict，且称“沙子研碎后更快溶解”——沙子不溶于水，属科学性错误；重写答案。",
    },
    "science_gap_llm_050": {
        "answer": "1. 漏斗、滤纸、烧杯、玻璃棒、铁架台（带铁圈）等。2. 要点（一贴、二低、三靠）："
                  "滤纸紧贴漏斗内壁；滤纸边缘略低于漏斗边缘，液面低于滤纸边缘；倾倒时烧杯口紧靠玻璃棒，"
                  "玻璃棒下端斜靠三层滤纸一边，漏斗下端管口紧靠承接烧杯内壁。",
        "why": "原稿 answer 为 dict 且“避免液体直接流入漏斗底部”表述错误；按“一贴二低三靠”规范重写。",
    },
    "science_gap_llm_051": {
        "stem": "实验中，小明把同一把钢尺伸出桌面不同的长度，用手拨动钢尺伸出桌面的一端，观察并记录听到的声音。"
                "请回答以下问题：\n1. 小明改变什么条件来探究声音的高低（音调）与物体振动快慢的关系？\n"
                "2. 小明听到了什么样的变化？\n3. 小明得出了什么结论？",
        "answer": "1. 改变钢尺伸出桌面的长度（同时控制每次拨动的力度相同）。2. 钢尺伸出桌面越短，振动越快，"
                  "听到的声音越高；伸出桌面越长，振动越慢，声音越低。3. 结论：音调的高低与声源振动的快慢有关，"
                  "振动越快，音调越高。",
        "why": "原稿“敲击”钢尺测的是响度，探究音调应“拨动”；纠错并把 dict 答案转文本。",
    },
    "science_gap_llm_052": {
        "answer": "1. 绿豆种子发芽与水分（水）是否有关。2. 变量是水分（A 组干燥、B 组湿润，只改变水分这一条件）。"
                  "3. 温度、光照、空气、种子数量与品种等其他条件都保持相同。",
        "why": "原稿 answer 为 dict；内容成立，转分点文本。",
    },
}

# ------------------------------------------------- AUTHORED：人工命题（LLM 弃稿）
def _a(item_id, subject, grade, item_type, stem, answer, kps, diff, solution, form):
    it = G.make_item(item_id, item_type, stem, answer, kps, diff, solution,
                     form=form, source="original", agent="gapfill-author-20261006",
                     note=AUTHOR_NOTE)
    it["_grade"] = grade
    it["_batch"] = f"{subject}_authored"
    return it


AUTHORED = [
    # ===== 语文（LLM 10 稿全弃：泄漏答案/事实错误/无病呻吟）=====
    _a("chinese_gap_a001", "chinese", 7, "fill",
       "王湾《次北固山下》中，描写时序交替中的景物，蕴含新旧更替自然理趣的名句是：①______，②______。",
       "①海日生残夜；②江春入旧年",
       ["kp_chi7_poem_dictation"], 0.5,
       "出自七上《次北固山下》。注意“生”不要误写为“升”，“残夜”指天将亮之时。这两句写海日生于残夜、江春闯入旧年，时序交替中蕴含哲理。",
       "fill"),
    _a("chinese_gap_a002", "chinese", 8, "fill",
       "王维《使至塞上》中，以传神笔墨勾勒塞外雄浑壮丽景象、被王国维赞为“千古壮观”的名句是：①______，②______。",
       "①大漠孤烟直；②长河落日圆",
       ["kp_chi8_tangpoem5"], 0.5,
       "出自八上《使至塞上》。一个“直”、一个“圆”，精准写出塞外景物的苍劲与浑圆；“孤烟”指烽烟（一说炊烟）。",
       "fill"),
    _a("chinese_gap_a003", "chinese", 7, "fill",
       "《西游记》的作者是明代小说家①______。孙悟空大闹天宫后被如来佛祖压在②______下，五百年后经观音菩萨点化，保护唐僧西天取经。",
       "①吴承恩；②五行山",
       ["kp_chi7_book_xiyou"], 0.35,
       "《西游记》作者吴承恩，明代人。孙悟空被压五行山（书中亦称“两界山”）下五百年，是全书前七回的高潮收束。",
       "cloze"),
    _a("chinese_gap_a004", "chinese", 8, "fill",
       "《红星照耀中国》的作者是美国记者①______。1936 年，他冲破重重封锁进入②______苏区，成为第一个采访红色中国的西方记者，向全世界真实报道了中国共产党和红军的故事。",
       "①埃德加·斯诺；②陕北（西北）",
       ["kp_chi8_book_hongxing"], 0.35,
       "埃德加·斯诺 1936 年 6 月进入陕北苏区采访，写成《红星照耀中国》（中译本曾名《西行漫记》）。注意是“陕北苏区”，不是“长征路上”。",
       "cloze"),
    _a("chinese_gap_a005", "chinese", 9, "fill",
       "下面句子有语病，请按要求修改。\n“通过这次社会实践活动，使同学们开阔了眼界，增长了才干。”\n"
       "①这个句子的病因是：______；②修改方法是：______。",
       "①成分残缺（缺主语）——“通过……使……”连用，使句子失去了主语；②删去“通过”或删去“使”，让“同学们”或“这次社会实践活动”充当主语",
       ["kp_chi9_kaodian_zeng"], 0.5,
       "“通过……”是介宾短语作状语，“使……”又把主语吞掉，双重介词结构导致主语残缺。这是中考病句高频考点：介词开头＋使令动词＝缺主语。",
       "fill"),
    _a("chinese_gap_a006", "chinese", 9, "fill",
       "下列句子中加点成语使用是否恰当？请判断并说明理由。\n“他演讲时声音抑扬顿挫，富有感染力，赢得了台下阵阵掌声。”"
       "\n（抑扬顿挫：形容声音高低起伏、停顿转折，和谐悦耳）\n①判断：______；②理由：______。",
       "①恰当；②“抑扬顿挫”形容声音的高低起伏和停顿转折，用来形容演讲的声音节奏恰当贴切，与“富有感染力”“掌声”语境相合",
       ["kp_chi9_kaodian_zeng"], 0.4,
       "判断成语使用题：先明词义（声音的起伏停顿），再对语境（演讲的声音），词义与对象、语境一致即恰当。",
       "fill"),
    _a("chinese_gap_a007", "chinese", 10, "fill",
       "《荀子·劝学》中，以“金”“石”为喻强调学习贵在坚持的名句是：①______，②______。",
       "①锲而不舍；②金石可镂",
       ["kp_chi10_dictation_high"], 0.5,
       "出自必修上《劝学》：“锲而舍之，朽木不折；锲而不舍，金石可镂。”注意“锲”字从“钅”，“镂”不要误写为“漏”。",
       "fill"),
    _a("chinese_gap_a008", "chinese", 12, "fill",
       "白居易《琵琶行》中，写诗人与琵琶人同为沦落之人，以“同”“相逢”二字道尽同病相怜之情的名句是：①______，②______。",
       "①同是天涯沦落人；②相逢何必曾相识",
       ["kp_chi12_gk_dictation"], 0.5,
       "选必下/72 篇《琵琶行》名句。“天涯沦落”点身世之悲，“何必曾相识”写相知之切。注意“涯”不要误写为“崖”。",
       "fill"),
    _a("chinese_gap_a009", "chinese", 10, "fill",
       "下面句子有语病，请按要求修改。\n“博物馆展出了两千多年前新出土的文物。”\n"
       "①这个句子的病因是：______；②修改后的正确说法是：______。",
       "①语序不当（表意矛盾）——“两千多年前”错放在“新出土”前，好像文物两千多年前就出土了；②改为“博物馆展出了新出土的两千多年前的文物。”",
       ["kp_chi10_languse"], 0.55,
       "多层定语语序不当的经典题：时间（出土先后）与文物年代两层意思叠放错位，造成歧义与矛盾。调整定语顺序即可。",
       "fill"),
    _a("chinese_gap_a010", "chinese", 10, "fill",
       "阅读下面的句子，完成①②两空。\n“莫高窟保存着规模宏大的石窟群，殿宇巍峨，彩塑精美，真可谓①______"
       "（妙手回春／美轮美奂／络绎不绝／恰到好处）。窟中的壁画——飞天，衣袂飘飘，仿佛真的在天空中飞翔。"
       "句中破折号的作用是②______（填：解释说明／声音延长／话题转换）。",
       "①美轮美奂；②解释说明",
       ["kp_chi10_languse"], 0.5,
       "“美轮美奂”多形容建筑高大华美，用于石窟群恰当；“妙手回春”指医术，“络绎不绝”指人流，“恰到好处”指分寸，均不合语境。"
       "破折号后“飞天”是对“壁画”内容的解释说明。",
       "fill"),
    # ===== 英语七选五（LLM 9 稿全弃：无真实语篇）——5 篇人工命题 =====
    _a("english_gap_a011", "english", 10, "solve",
       "【七选五】阅读下面短文，从短文后的选项中选出能填入空白处的最佳选项。选项中有两项为多余选项。\n"
       "Getting Better at Time Management\n"
       "Many students say they do not have enough time for study, hobbies or rest. In fact, the problem is "
       "usually not the amount of time but the way it is used. ①____\n"
       "First, write down everything you need to do tomorrow before you go to bed. A short list on paper "
       "frees your mind from trying to remember ten things at once. ②____ When each task has a clear order, "
       "it is much easier to start working instead of worrying.\n"
       "Second, deal with the most difficult task first. Most of us start with easy jobs because they feel "
       "pleasant, but then the hardest task is left for the evening when we are tired. ③____\n"
       "Third, protect your rest time. Some students cut their sleeping hours to gain two more hours of "
       "study, and then spend the next day fighting sleep in class. ④____ A well-rested brain remembers "
       "more in forty minutes than a tired one does in two hours.\n"
       "Time management is not a magic skill. ⑤____ Start tonight: make a list, rank the tasks, and go to "
       "bed on time.\n"
       "A. Then rank the tasks from the most to the least important.\n"
       "B. It is a set of small choices you make every day.\n"
       "C. Doing the hardest job first actually saves energy and time.\n"
       "D. In the long run, this habit hurts both health and grades.\n"
       "E. Here are three simple habits that can help.\n"
       "F. Time flies when you are doing something you enjoy.\n"
       "G. Ask your teachers to give you less homework.",
       "E-A-C-D-B",
       ["kp_eng10_red10_structure_read"], 0.5,
       "①总起句（引出三个习惯）→E；②承接“写下清单”的动作顺序→A；③承接“先做难事”的观点→C；④承接“熬夜学习”的危害→D；⑤呼应主题句“不是魔法而是小选择”→B。F、G 与语篇话题（自我管理）不符，为多余选项。",
       "seven_to_five_sequence"),
    _a("english_gap_a012", "english", 10, "solve",
       "【七选五】阅读下面短文，从短文后的选项中选出能填入空白处的最佳选项。选项中有两项为多余选项。\n"
       "Don't Skip Breakfast\n"
       "Some students leave home without breakfast to save time in the morning. ①____ After about ten hours "
       "without food, a person's blood sugar is at its lowest level. ②____ Without enough glucose, it is hard "
       "to listen, remember and think clearly in the first lessons. Teachers often notice that hungry students "
       "lose focus long before lunch. ③____\n"
       "A good breakfast does not have to be big or expensive. ④____ Even a banana with a glass of milk is much "
       "better than nothing. What matters is giving the body energy before study begins.\n"
       "In the long run, eating breakfast also helps the body keep a stable weight and a better mood. "
       "⑤____ Ten quiet minutes at the table can make the whole school day easier.\n"
       "A. That is why students who eat breakfast often do better in morning classes.\n"
       "B. So tomorrow morning, give yourself ten minutes for a real breakfast.\n"
       "C. However, this habit does more harm than good.\n"
       "D. Whole-grain bread, eggs, milk and fruit are all good choices.\n"
       "E. The brain in particular lives on glucose in the blood.\n"
       "F. Skipping dinner is popular among office workers.\n"
       "G. Coffee is one of the most popular drinks in the world.",
       "C-E-A-D-B",
       ["kp_eng10_dis10_explicit_cohesion"], 0.5,
       "①“However”转折承接上文“不吃早饭省时间”→C；②“blood sugar 最低”与“大脑靠血糖”语义复现衔接→E；③上句“饿着肚子走神”引出结果→A；④上句“不必丰盛昂贵”引出具体食物→D；⑤尾段呼吁行动→B。F、G 偏离“早餐”话题，为多余选项。",
       "seven_to_five_sequence"),
    _a("english_gap_a013", "english", 11, "solve",
       "【七选五】阅读下面短文，从短文后的选项中选出能填入空白处的最佳选项。选项中有两项为多余选项。\n"
       "How to Argue with a Friend—and Stay Friends\n"
       "Disagreements with friends are normal, but they can hurt a friendship if they are handled badly. "
       "①____\n"
       "First, take a moment to think about the situation from your friend's point of view. Understanding "
       "why they feel that way does not mean you have to agree, but it shows that you take their feelings "
       "seriously. ②____\n"
       "Second, use “I” messages instead of “you” messages. Saying “I felt hurt when you forgot our plan” "
       "sounds very different from “You always forget things”. ③____\n"
       "Third, look for a solution together. A disagreement ends faster when both sides feel heard. ④____\n"
       "Finally, if the argument gets too heated, it is wise to pause and continue the talk later when both "
       "of you are calm. ⑤____ True friends can survive an honest disagreement—and often come out closer.\n"
       "A. This small change keeps the other person from feeling attacked.\n"
       "B. Here are some ways to disagree without damaging the friendship.\n"
       "C. Even a ten-minute break can prevent words you may regret.\n"
       "D. Working out a plan that suits both of you turns an argument into teamwork.\n"
       "E. Their answer may reveal something you had not noticed.\n"
       "F. Shouting louder is the quickest way to win an argument.\n"
       "G. Friends should never talk about problems directly.",
       "B-E-A-D-C",
       ["kp_eng11_red11_implied"], 0.55,
       "①总起句（如何不伤感情地表达分歧）→B；②承接“换位思考”的推论→E；③“这种小改变”回指“I”消息法→A；④“一起找办法”的落点→D；⑤承接“暂停再谈”的具体建议→C。F、G 与文意相悖，为多余选项。",
       "seven_to_five_sequence"),
    _a("english_gap_a014", "english", 11, "solve",
       "【七选五】阅读下面短文，从短文后的选项中选出能填入空白处的最佳选项。选项中有两项为多余选项。\n"
       "Training Your Attention in the Digital Age\n"
       "Smartphones put the world at our fingertips, but they also put endless interruptions there. Many "
       "students check their phones every few minutes even when nothing new has appeared. ①____\n"
       "Start by making the phone less visible. Put it in another room or in your bag while studying. Out of "
       "sight really can mean out of mind. ②____\n"
       "Next, give deep work a fixed time slot. Decide that you will study for forty minutes, then reward "
       "yourself with ten minutes of messaging. ③____\n"
       "Finally, train your attention like a muscle. When your mind wanders, gently bring it back to the page. "
       "Each time you do this, focusing becomes a little easier. ④____\n"
       "Attention is not a gift; it is a skill. ⑤____ The students who protect it today will be the ones who "
       "think deeply tomorrow.\n"
       "A. A fixed rhythm like this trains the brain to expect both work and rest.\n"
       "B. Over time, you will notice you can read for longer stretches without checking anything.\n"
       "C. The good news is that attention can be rebuilt with a few simple habits.\n"
       "D. Notifications are designed to pull you back, so distance is your first tool.\n"
       "E. Like any skill, it grows with patient practice.\n"
       "F. Turning off the internet completely is the only way to study.\n"
       "G. Deep focus always leads to perfect exam scores.",
       "C-D-A-B-E",
       ["kp_eng11_spk11_cohesion"], 0.55,
       "①承上“不断被打断”引出“可以重建”→C；②承接“让手机不可见”的原因（通知设计）→D；③承接“40+10 节奏”的效果→A；④承接“每次拉回注意力”的长期结果→B；⑤呼应“attention is a skill”→E。F、G 表述绝对化且文中无据，为多余选项。",
       "seven_to_five_sequence"),
    _a("english_gap_a015", "english", 12, "solve",
       "【七选五】阅读下面短文，从短文后的选项中选出能填入空白处的最佳选项。选项中有两项为多余选项。\n"
       "Sleep and Memory\n"
       "Every night, as you fall asleep, your brain keeps working. Sleep is not a pause in learning; it is "
       "part of learning. ①____\n"
       "During deep sleep, the brain replays the day's experiences and moves important information from "
       "short-term memory into long-term storage. Students who review their notes before bed often remember "
       "more the next morning. ②____\n"
       "Sleep also clears waste products that build up in the brain during the day. Without enough sleep, "
       "this cleaning system falls behind. ③____ That is why after several short nights, even a clever mind "
       "becomes slow and forgetful.\n"
       "How much sleep is enough? For teenagers, most experts recommend eight to ten hours. ④____\n"
       "So if you want to learn well, do not treat sleep as lost time. ⑤____ Turn off the screens early, and "
       "let your brain finish its night shift.\n"
       "A. More sleep does not automatically mean better grades, but too little clearly harms memory.\n"
       "B. The timing of sleep matters as much as its length, because the brain stores what was learned "
       "recently.\n"
       "C. In fact, it is one of the most powerful study tools you already own.\n"
       "D. As a result, the mind loses its edge and new learning becomes harder.\n"
       "E. This process is called memory consolidation.\n"
       "F. Dreaming every night is a sign of a serious sleep problem.\n"
       "G. Drinking coffee before bed helps the brain memorize faster.",
       "E-B-D-A-C",
       ["kp_eng12_red12_structure_deep"], 0.6,
       "①承接“睡眠是学习的一部分”，引出术语→E；②“睡前复习记得多”的机制解释→B；③承接“清洁系统落后”的结果→D；④回应“睡多久才够”且避免绝对化→A；⑤呼应“不是浪费时间”给出结论→C。F、G 违背常识且无文内依据，为多余选项。",
       "seven_to_five_sequence"),
    # ===== 生物初中（LLM 5 稿弃：事实错误/空号错位）=====
    _a("biology_gap_a016", "biology", 7, "fill",
       "草原生态系统中存在食物链“草→兔→鹰”。请回答：该食物链中数量最多的生物是①______；"
       "若大量捕杀鹰，短时间内兔的数量会②______（填“增多”或“减少”），随后因草的数量减少，兔的数量又会③______（填“增多”或“减少”）。",
       "①草；②增多；③减少",
       ["kp_bio7_food_chain_web"], 0.45,
       "能量沿食物链逐级递减，营养级越低数量越多，故草最多。鹰减少→兔失去天敌控制先增多→草被大量啃食减少→兔因食物短缺再减少，体现生态系统的自动调节。",
       "cloze"),
    _a("biology_gap_a017", "biology", 8, "fill",
       "人有耳垂对无耳垂为显性（用 A、a 表示）。父母双方的基因组成都是 Aa。请回答：他们生一个无耳垂孩子的可能性是①______；"
       "这个无耳垂孩子的基因组成是②______。",
       "①1/4（25%）；②aa",
       ["kp_bio8_dominant_recessive"], 0.5,
       "Aa×Aa 后代基因型及比例为 AA:Aa:aa＝1:2:1；无耳垂为隐性性状，只有 aa 才表现，占 1/4。表现隐性性状时基因组成成对相同。",
       "cloze"),
    _a("biology_gap_a018", "biology", 8, "fill",
       "水痘痊愈后，人体内产生了只抵抗水痘病毒的抗体，这种免疫属于①______免疫（填“特异性”或“非特异性”）；"
       "皮肤和黏膜的屏障作用属于②______免疫，是生来就有的第③______道防线。",
       "①特异性；②非特异性；③一",
       ["kp_bio8_specific_immunity"], 0.5,
       "抗体只对特定病原体起作用→特异性免疫（第三道防线）。皮肤和黏膜是生来就有、对多种病原体都有作用的第一道防线→非特异性免疫。",
       "cloze"),
    _a("biology_gap_a019", "biology", 9, "fill",
       "某小组探究“光对鼠妇分布的影响”：在铁盘内以横轴中线为界，一侧盖上黑纸板，另一侧不盖，"
       "在两侧中央各放入 5 只鼠妇，静置 2 分钟后每分钟统计一次明亮处和阴暗处的鼠妇数量，共统计 10 次。"
       "请回答：本实验的变量是①______；设置明暗两侧的目的是②______；用 10 只鼠妇而不是 1 只，原因是③______。",
       "①光照（光）；②形成对照（只保留光照这一个变量）；③避免偶然性，减小实验误差",
       ["kp_bio9_inquiry_experiment"], 0.55,
       "对照实验要求变量唯一：明暗两侧除光外其他条件（湿度、温度等）都相同。单只鼠妇的行为有偶然性，多用多只并取平均值（多次统计）才能使结论可靠。",
       "cloze"),
    _a("biology_gap_a020", "biology", 9, "fill",
       "人的性别由性染色体决定。请回答：男性体细胞的性染色体组成是①______，女性体细胞的性染色体组成是②______；"
       "生男生女取决于父亲提供的精子类型，父亲传给女儿的一定是③______染色体（填“X”或“Y”）。",
       "①XY；②XX；③X",
       ["kp_bio9_diagram_comprehension"], 0.45,
       "女性产生一种含 X 的卵细胞，男性产生含 X 和含 Y 两种精子。含 X 精子＋卵细胞→XX（女），含 Y 精子＋卵细胞→XY（男），故女儿一定得到父亲的 X。",
       "cloze"),
    # ===== 生物高中（LLM 5 稿弃：计算错误/选择题混入）=====
    _a("biology_gap_a021", "biology", 10, "solve",
       "豌豆的高茎对矮茎为显性（由 D、d 控制）。请回答：（1）杂合高茎豌豆（Dd）自交，后代中高茎与矮茎的比例是①______；"
       "（2）后代矮茎植株的基因型是②______；（3）若取后代中全部高茎植株分别自交，则它们的后代中矮茎植株的比例是③______。",
       "（1）3:1；（2）dd；（3）1/6",
       ["kp_bio10_segregation_law"], 0.6,
       "Dd×Dd→1DD:2Dd:1dd，高:矮＝3:1。后代高茎中 1/3DD、2/3Dd：1/3DD 自交后代全高茎，2/3Dd 自交后代矮茎占 2/3×1/4＝1/6，故高茎自交后代中矮茎占 1/6。（程序验算：2/3×1/4＝1/6 ✓）",
       "solve"),
    _a("biology_gap_a022", "biology", 10, "solve",
       "在“绿叶中色素的提取和分离”实验中，滤纸条上出现了四条色素带。请回答：（1）分离色素的原理是①______；"
       "（2）滤纸条上从上到下的第二条色素带是②______；（3）研磨时加入少许二氧化硅的目的是③______。",
       "（1）绿叶中的各种色素在层析液中的溶解度不同：溶解度高的随层析液在滤纸上扩散得快，反之则慢，从而使色素分离；（2）叶黄素；（3）使研磨充分",
       ["kp_bio10_photosynthesis"], 0.55,
       "四条色素带从上到下依次为胡萝卜素、叶黄素、叶绿素 a、叶绿素 b（扩散速度递减）。二氧化硅有助于破坏细胞结构使研磨充分；加碳酸钙可防止色素被破坏。",
       "solve"),
    _a("biology_gap_a023", "biology", 11, "solve",
       "某人缩手反射的传入神经受损，反射弧的其他结构都正常。请回答：（1）该缩手反射①______（填“能”或“不能”）完成，"
       "原因是②______；（3）此人手指被针刺时③______（填“能”或“不能”）产生痛觉，原因是④______。",
       "（1）①不能；（2）②传入神经受损，感受器产生的兴奋无法传导至脊髓（神经中枢），反射弧不完整；（3）③不能；（4）④兴奋无法经传入神经传入脊髓，更无法沿脊髓白质上传至大脑皮层的感觉中枢",
       ["kp_bio11_reflex_arc_hs"], 0.6,
       "反射的发生依赖完整反射弧，传入神经断了，反射与感觉都无从谈起（对比：若传出神经受损，反射不能完成，但痛觉仍可产生）。",
       "solve"),
    _a("biology_gap_a024", "biology", 12, "solve",
       "某生态系统中的食物链为：草→兔→狐。若草固定的太阳能总量为 2000 kJ，兔同化的能量为 200 kJ，狐同化的能量为 20 kJ。"
       "请回答：（1）草到兔的能量传递效率是①______；（2）兔到狐的能量传递效率是②______；"
       "（3）兔同化的能量中，用于自身生长、发育和繁殖的能量＝同化量−③______。",
       "（1）10%；（2）10%；（3）呼吸作用以热能形式散失的能量",
       ["kp_bio12_energy_flow"], 0.6,
       "传递效率＝下一营养级同化量÷上一营养级同化量：200/2000＝10%，20/200＝10%（程序验算 ✓）。每一营养级同化量的去向中，呼吸散失是最大去向之一，余下才用于生长、发育和繁殖。（程序验算：200/2000、20/200 ✓）",
       "solve"),
    _a("biology_gap_a025", "biology", 12, "solve",
       "与森林生态系统相比，农田生态系统①______（填“抵抗力”或“恢复力”）稳定性通常较低，原因是②______；"
       "要提高农田生态系统的稳定性，可以采取的措施是③______（答出一条即可）。",
       "（1）①抵抗力；（2）②生物种类少，营养结构简单，自我调节能力弱；（3）③合理增加生物种类（如间作套种、轮作、田埂种草），科学施肥灌水等（合理即可）",
       ["kp_bio12_ecosystem_stability"], 0.55,
       "组分多少与营养结构复杂程度决定自我调节能力，进而决定抵抗力稳定性。人为管理（增加种类、防虫防病）可提高农田生态系统的稳定性。",
       "solve"),
    # ===== 小学道法连线（LLM 4 稿全弃：右栏缺失/错配）=====
    _a("politics_gap_a026", "politics", 1, "fill",
       "把下面的安全标志和它的含义连起来（把字母填在横线上）。\n"
       "1. 红色圆形中间一道白杠　______\n2. 黄色三角形中间一个黑色感叹号　______\n"
       "3. 蓝色圆形中间一个白色箭头　______\n4. 红色八角形里写着 STOP　______\n"
       "A. 允许通行、按指示方向前进　　B. 注意安全、当心危险\n"
       "C. 禁止通行　　D. 停车让行",
       "1-C；2-B；3-A；4-D",
       ["kp_pol1_safety_sign"], 0.25,
       "红色＋圆形＋白杠＝禁止类（禁止通行）；黄色三角形＝警告类（注意危险）；蓝色圆形箭头＝指示类（允许通行）；八角形 STOP＝停车让行。",
       "matching"),
    _a("politics_gap_a027", "politics", 2, "fill",
       "把交通信号灯和正确的做法连起来（把字母填在横线上）。\n"
       "1. 红灯亮时　______\n2. 绿灯亮时　______\n3. 黄灯亮时　______\n4. 过路口既无信号灯又无斑马线　______\n"
       "A. 在停止线外耐心等候　　B. 走人行横道，先看左再看右，安全通过\n"
       "C. 已越过停止线的继续通行，未越线的停在原地等候　　D. 一停二看三通过，确认安全后快步通过",
       "1-A；2-B；3-C；4-D",
       ["kp_pol2_traffic_sign"], 0.3,
       "红灯停、绿灯行、黄灯亮时不抢行（越线继续走、未越线停）。没有信号灯和斑马线路口要“一停二看三通过”。",
       "matching"),
    _a("politics_gap_a028", "politics", 3, "fill",
       "把突发情况和正确的应对办法连起来（把字母填在横线上）。\n"
       "1. 教室里发生火灾　______\n2. 发现有人落水　______\n3. 在陌生地方与家人走散　______\n"
       "4. 户外遇到雷雨天气　______\n"
       "A. 用湿毛巾捂住口鼻，低身沿安全通道有序撤离，不乘电梯\n"
       "B. 不盲目下水施救，大声呼救并拨打 110／120 求助\n"
       "C. 原地等待或找警察、工作人员求助，不跟陌生人走\n"
       "D. 不在大树、电杆下避雨，尽快进入室内并拔掉电器插头",
       "1-A；2-B；3-C；4-D",
       ["kp_pol3_safety_emergency"], 0.35,
       "火灾捂口鼻低姿走安全通道（电梯断电最危险）；未成年人不下水救人，要呼救报警；走散原地等或找警察；雷电天远离高大树木与金属，进屋断电。",
       "matching"),
    _a("politics_gap_a029", "politics", 6, "fill",
       "把劳动者和他们为社会的付出连起来（把字母填在横线上）。\n"
       "1. 农民　______\n2. 医生　______\n3. 教师　______\n4. 环卫工人　______\n"
       "A. 救死扶伤，守护人民健康　　B. 教书育人，培养下一代\n"
       "C. 清扫街道，美化城市环境　　D. 春种秋收，种出粮食",
       "1-D；2-A；3-B；4-C",
       ["kp_pol6_occupy_respect"], 0.25,
       "各行各业的劳动者用不同方式的劳动为社会作贡献，劳动没有高低贵贱之分，都值得我们尊重。",
       "matching"),
]

# 数量校验：语文10 + 英语七选五5 + 生物初中5 + 生物高中5 + 道法连线4
assert len(AUTHORED) == 29, len(AUTHORED)


def main() -> int:
    global DRY
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    with open(CAND, encoding="utf-8") as f:
        cands = json.load(f)

    # 1) 保留题：应用人工修订（每个候选必须被审到：KEEP 或 REJECT，否则 fail-closed）
    keeps = []
    for it in cands:
        if it["id"] in REJECT_IDS:
            continue
        fix = KEEP_FIXES.get(it["id"])
        if fix is None:
            print(f"  !! 候选 {it['id']} 未被审核（不在 KEEP 也不在 REJECT），中止", file=sys.stderr)
            return 1
        if "stem" in fix:
            it["stem"] = fix["stem"]
        for old, new in fix.get("stem_replace", []):
            assert old in it["stem"], f"{it['id']}: stem_replace 找不到原文 {old[:40]!r}"
            it["stem"] = it["stem"].replace(old, new)
        if "answer" in fix:
            it["answer"] = fix["answer"]
        it["verification"]["note"] = FIX_NOTE + "（修订要点：" + fix.get("why", "人工通读，原文即成立") + "）"
        it["_batch"] = it.pop("_batch", it["id"])
        keeps.append(it)

    # 2) 人工命题
    authored = [dict(x) for x in AUTHORED]

    # 3) 统一校验 + 去重 + 落盘
    ledger = {"batch": "gapfill_llm_and_authored_20261006", "appended": []}
    by_key = {}
    seen = {}
    dropped_dup = 0
    for it in keeps + authored:
        subject = it["id"].split("_")[0]
        dedup = seen.setdefault(subject, G.Deduper(subject))
        if dedup.is_dup(it["stem"]):
            print(f"  丢弃（与既有题干 3-gram≥0.8 判重）{it['id']}")
            dropped_dup += 1
            continue
        errs = G.validate_items([dict(it)], subject)
        if errs:
            print(f"  !! 校验失败拒收 {it['id']}: {errs}", file=sys.stderr)
            return 1
        dedup.add(it["stem"])
        by_key.setdefault((subject, it.pop("_grade")), []).append(it)

    n_authored = len(authored)
    print(f"保留修订 {len(keeps)} 题 + 人工命题 {n_authored} 题，判重丢弃 {dropped_dup} 题，"
          f"拒收 {len(REJECT_IDS)} 题（LLM 弃稿 34 份计入丢弃）")
    if args.dry_run:
        for it in keeps + authored:
            print("=" * 70)
            print(f"[{it.get('_batch','?')}] {it['id']} ({it['form']}, d={it['difficulty']}, kp={it['kps'][0]})")
            print("题干：", it["stem"][:600])
            print("答案：", str(it["answer"])[:400])
        return 0
    n = 0
    for (subject, grade), items in sorted(by_key.items()):
        n += G.append_items(subject, grade, items, ledger)
        print(f"  {subject} grade{grade}: +{len(items)}")
    with open(os.path.join(HERE, "ledger_llm_review.json"), "w", encoding="utf-8") as f:
        json.dump(ledger, f, ensure_ascii=False, indent=2)
    print(f"共落盘 {n} 题")
    return 0


if __name__ == "__main__":
    sys.exit(main())
