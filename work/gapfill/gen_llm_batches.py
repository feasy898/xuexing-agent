"""gapfill 步骤 3：LLM 缺口题生成（glm-4-flash，单代理，如实标注）。

批次清单与数量口径：每缺口类型补足到「该卷型需求量×2」；数学模板题
（gen_math_templates.py）之外的 6 道数学主观题也走本脚本——由 LLM 起草，
但题干与关键结论在 prompt 里由本脚本指定，落盘前逐项核对 key_results。
听力/连线类按 owner 预期可少补，本脚本对每题独立出题、独立校验，失败的
如实计入丢弃，不降级凑数。

verification 如实：source=llm_generated；agents=[gapfill-gen-20261006]，
single_agent=true，dual_agent=false；difficulty 为 LLM 初值（estimated），
独立双代理盲验未做——全部写入 verification.note。

用法：
  python work/gapfill/gen_llm_batches.py gen   # 生成候选 work/gapfill/candidates_llm.json 并全量打印供人工核
  python work/gapfill/gen_llm_batches.py apply # 校验+去重后并入 data/items（fail-closed）
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

LLM_NOTE = ("glm-4-flash 单代理生成（single_agent=true，dual_agent=false），"
            "difficulty 为 LLM 初值 estimated；独立双代理盲验未做")

# ------------------------------------------------------------------ 批次定义
# 每个任务：(batch, subject, grade, kp, item_type, form, 指令, 附加JSON要求, 需要核对的关键结果)
JOBS = [
    # 注：数学 6 道主观题（jr 尺规作图×2 / jr 几何证明×2 / hs 综合压轴×2）不走
    # LLM——起草中发现 glm-4-flash 会写出 |PF₁|=√2 这类中间步错误，owner 纪律
    # 要求数学答案程序验算，故改由 gen_math_templates.py 以代码可核内容命题。
    # —— 语文 ——
    ("chi_jr_moxie", "chinese", 7, "kp_chi7_poem_dictation", "fill", "fill",
     "古诗文情境默写填空（初中七年级，只允许使用部编版七年级教材内的篇目：《观沧海》《次北固山下》《闻王昌龄左迁龙标遥有此寄》《天净沙·秋思》《论语》十二章《望岳》《登飞来峰》《游山西村》《己亥杂诗》等）。题干给情境，答案为连续的名句原文，不要杜撰。默写题答案必须逐字准确。",
     {"stem_spec": "两空情境默写，用①②标空，并注明出处篇目",
      "key_results": []},
     ""),
    ("chi_jr_moxie", "chinese", 8, "kp_chi8_tangpoem5", "fill", "fill",
     "古诗文情境默写填空（初中八年级，只允许使用部编版八年级上册《唐诗五首》篇目：《野望》《黄鹤楼》《使至塞上》《渡荆门送别》《钱塘湖春行》，或《三峡》《答谢中书书》《记承天寺夜游》）。题干给情境，答案为连续的名句原文，不要杜撰。默写题答案必须逐字准确。",
     {"stem_spec": "两空情境默写，用①②标空，并注明出处篇目",
      "key_results": []},
     ""),
    ("chi_jr_mingzhu", "chinese", 7, "kp_chi7_book_xiyou", "fill", "cloze",
     "名著阅读填空（《西游记》）。围绕情节/人物/主题命 2 个空，答案短而确定，不要杜撰情节。",
     {"stem_spec": "填空题干，用①②标空",
      "key_results": []},
     ""),
    ("chi_jr_mingzhu", "chinese", 8, "kp_chi8_book_hongxing", "fill", "cloze",
     "名著阅读填空（《红星照耀中国》，埃德加·斯诺）。围绕作者/纪实内容/人物命 2 个空，答案短而确定，不要杜撰。",
     {"stem_spec": "填空题干，用①②标空",
      "key_results": []},
     ""),
    ("chi_jr_languse", "chinese", 9, "kp_chi9_kaodian_zeng", "fill", "fill",
     "语言运用填空（中考积累与运用专项）：病句修改或成语使用。给出一个明确有误的句子（病因唯一、改法确定）要求修改；或给语境选填成语。答案必须唯一确定。",
     {"stem_spec": "病句修改题，用①②标空（填病因与改法或改正后的短语）",
      "key_results": []},
     ""),
    ("chi_jr_languse", "chinese", 9, "kp_chi9_kaodian_zeng", "fill", "fill",
     "语言运用填空（中考积累与运用专项）：成语使用辨析。给出一句话，其中含下划线成语，判断使用是否恰当并说明理由；或给两空选填恰当成语。答案必须唯一确定。",
     {"stem_spec": "成语使用题，用①②标空",
      "key_results": []},
     ""),
    ("chi_hs_moxie", "chinese", 10, "kp_chi10_dictation_high", "fill", "fill",
     "名篇名句情境默写（高中，只允许使用新课标必背篇目：《劝学》《师说》《赤壁赋》《登泰山记》《静女》《涉江采芙蓉》《虞美人·春花秋月何时了》《念奴娇·赤壁怀古》等）。题干给情境，答案为连续名句原文，不要杜撰。默写答案必须逐字准确。",
     {"stem_spec": "两空情境默写，用①②标空，并注明出处篇目",
      "key_results": []},
     ""),
    ("chi_hs_moxie", "chinese", 12, "kp_chi12_gk_dictation", "fill", "fill",
     "高考名篇名句情境默写（只允许使用新课标 72 篇中的篇目：《离骚》《蜀道难》《琵琶行》《锦瑟》《书愤》《拟行路难》《陈情表》《项脊轩志》等）。题干给情境，答案为连续名句原文，不要杜撰。默写答案必须逐字准确。",
     {"stem_spec": "两空情境默写，用①②标空，并注明出处篇目",
      "key_results": []},
     ""),
    ("chi_hs_languse", "chinese", 10, "kp_chi10_languse", "fill", "fill",
     "语言文字运用填空（高中）：病句辨析与修改。给出一个病因明确（搭配不当/成分残缺/语序不当之一）的病句，要求先填病因再填修改后的正确说法。答案必须唯一确定。",
     {"stem_spec": "病句修改，用①②标空（①病因 ②改法）",
      "key_results": []},
     ""),
    ("chi_hs_languse", "chinese", 10, "kp_chi10_languse", "fill", "fill",
     "语言文字运用填空（高中）：成语与标点综合。给一段 60 字左右的短文，设两空：①选填最恰当的成语（四选一，选项写进题干）；②判断某处标点使用是否正确并说明。答案必须唯一确定。",
     {"stem_spec": "成语+标点两空，用①②标空",
      "key_results": []},
     ""),
    # —— 英语 ——
    ("eng_jr_listening", "english", 7, "kp_eng7_lis7_visual_support", "solve", "listening",
     "初中英语听力题（七年级，语速慢、词汇量 ≤600）。生成一段 6~8 轮的校园生活对话（M:/W: 逐行写），对话后设 3 个问题。题干结构：第一行中文情景提示；然后「听力材料：」+英文对话全文；最后列出问题 1~3（英文，各配 A/B/C 三个选项，选项写进题干）。答案必须能且只能从对话文本推出，不要杜撰。",
     {"stem_spec": "听力对话+3 问（含选项），问题用 1./2./3. 编号",
      "key_results": []},
     ""),
    ("eng_jr_listening", "english", 7, "kp_eng7_lis7_visual_support", "solve", "listening",
     "初中英语听力题（七年级，独白）。生成一段 5~7 句的英语独白（主题：家庭/日常作息），独白后设 3 个问题（各配 A/B/C 选项，选项写进题干）。答案必须能且只能从独白文本推出。",
     {"stem_spec": "听力独白+3 问（含选项）",
      "key_results": []},
     ""),
    ("eng_jr_listening", "english", 8, "kp_eng8_lis8_broadcast", "solve", "listening",
     "初中英语听力题（八年级，广播/通知）。生成一段英文校园广播稿（6~8 句），后设 3 个问题（各配 A/B/C 选项，选项写进题干）。答案必须能且只能从广播文本推出。",
     {"stem_spec": "校园广播+3 问（含选项）",
      "key_results": []},
     ""),
    ("eng_jr_listening", "english", 8, "kp_eng8_lis8_broadcast", "solve", "listening",
     "初中英语听力题（八年级，电话对话）。生成一段 6~8 轮英文电话对话（主题：约时间/活动安排），后设 3 个问题（各配 A/B/C 选项，选项写进题干）。答案必须能且只能从对话文本推出。",
     {"stem_spec": "电话对话+3 问（含选项）",
      "key_results": []},
     ""),
    ("eng_jr_listening", "english", 8, "kp_eng8_lis8_broadcast", "solve", "listening",
     "初中英语听力题（八年级，采访对话）。生成一段 6~8 轮英文采访对话（记者采访学生爱好/运动），后设 3 个问题（各配 A/B/C 选项，选项写进题干）。答案必须能且只能从对话文本推出。",
     {"stem_spec": "采访对话+3 问（含选项）",
      "key_results": []},
     ""),
    ("eng_jr_listening", "english", 9, "kp_eng9_voc9_1600_master", "solve", "listening",
     "初中英语听力题（九年级，语速中等，词汇 ≤1600）。生成一段 7~9 轮英文对话（主题：志愿活动/环保），后设 3 个问题（各配 A/B/C 选项，选项写进题干）。答案必须能且只能从对话文本推出。",
     {"stem_spec": "对话+3 问（含选项）",
      "key_results": []},
     ""),
    ("eng_jr_listening", "english", 9, "kp_eng9_voc9_1600_master", "solve", "listening",
     "初中英语听力题（九年级，短文独白）。生成一段 6~8 句英文独白（主题：学习方法/名人故事），后设 3 个问题（各配 A/B/C 选项，选项写进题干）。答案必须能且只能从独白文本推出。",
     {"stem_spec": "独白+3 问（含选项）",
      "key_results": []},
     ""),
    ("eng_hs_seven", "english", 10, "kp_eng10_red10_structure_read", "solve", "seven_to_five_sequence",
     "高考英语七选五（必修一难度，约 300 词说明文）。生成一篇结构清晰的英语短文，从其中挖掉 5 句（用①~⑤标空），另写 2 个干扰句，共 7 个选项 A~G（每个选项必须与原文挖掉句逐字一致）。答案为 5 个字母按①~⑤顺序用连字符连接。干扰项要与正确项话题相近但有明确排除理由。",
     {"stem_spec": "短文（含①~⑤空）+ 7 选项列表",
      "key_results": []},
     ""),
    ("eng_hs_seven", "english", 10, "kp_eng10_dis10_explicit_cohesion", "solve", "seven_to_five_sequence",
     "高考英语七选五（衔接手段主题）。生成一篇约 300 词英语短文（主题：学习方法/健康生活），挖 5 空（①~⑤），共 7 选项 A~G，其中含指代衔接（this/they）与逻辑连接词线索。答案为 5 字母连字符串。",
     {"stem_spec": "短文+7 选项",
      "key_results": []},
     ""),
    ("eng_hs_seven", "english", 10, "kp_eng10_red10_structure_read", "solve", "seven_to_five_sequence",
     "高考英语七选五。生成一篇约 300 词英语说明文（主题：时间管理），挖 5 空（①~⑤），共 7 选项 A~G。总-分-总结构，每空对应一个段落主题句或总结句。答案为 5 字母连字符串。",
     {"stem_spec": "短文+7 选项",
      "key_results": []},
     ""),
    ("eng_hs_seven", "english", 11, "kp_eng11_red11_implied", "solve", "seven_to_five_sequence",
     "高考英语七选五（选择性必修难度，约 320 词）。生成一篇英语短文（主题：人际沟通/情感管理），挖 5 空（①~⑤），共 7 选项 A~G，需要根据上下文隐含意义推断。答案为 5 字母连字符串。",
     {"stem_spec": "短文+7 选项",
      "key_results": []},
     ""),
    ("eng_hs_seven", "english", 11, "kp_eng11_spk11_cohesion", "solve", "seven_to_five_sequence",
     "高考英语七选五。生成一篇约 320 词英语短文（主题：数字时代的专注力），挖 5 空（①~⑤），共 7 选项 A~G，用代词衔接与词汇复现作线索。答案为 5 字母连字符串。",
     {"stem_spec": "短文+7 选项",
      "key_results": []},
     ""),
    ("eng_hs_seven", "english", 11, "kp_eng11_red11_implied", "solve", "seven_to_five_sequence",
     "高考英语七选五。生成一篇约 320 词英语短文（主题：青少年志愿服务），挖 5 空（①~⑤），共 7 选项 A~G。答案为 5 字母连字符串。",
     {"stem_spec": "短文+7 选项",
      "key_results": []},
     ""),
    ("eng_hs_seven", "english", 12, "kp_eng12_red12_structure_deep", "solve", "seven_to_five_sequence",
     "高考英语七选五（高三难度，约 330 词）。生成一篇英语议论文（主题：AI 与学习），挖 5 空（①~⑤），共 7 选项 A~G，含观点-论据-结论结构。答案为 5 字母连字符串。",
     {"stem_spec": "短文+7 选项",
      "key_results": []},
     ""),
    ("eng_hs_seven", "english", 12, "kp_eng12_dis12_implicit_cohesion", "solve", "seven_to_five_sequence",
     "高考英语七选五。生成一篇约 330 词英语短文（主题：城市绿色空间），挖 5 空（①~⑤），共 7 选项 A~G，隐性衔接（语义场/复现）为线索。答案为 5 字母连字符串。",
     {"stem_spec": "短文+7 选项",
      "key_results": []},
     ""),
    ("eng_hs_seven", "english", 12, "kp_eng12_red12_structure_deep", "solve", "seven_to_five_sequence",
     "高考英语七选五。生成一篇约 330 词英语说明文（主题：睡眠与记忆），挖 5 空（①~⑤），共 7 选项 A~G。答案为 5 字母连字符串。",
     {"stem_spec": "短文+7 选项",
      "key_results": []},
     ""),
    # —— 生物 ——
    ("bio_jr_cloze", "biology", 7, "kp_bio7_photosynthesis_experiment", "fill", "cloze",
     "初中生物非选择题填空（七年级，光合作用探究实验：萨克斯/普利斯特利/绿色植物在光下制造有机物）。围绕实验变量、条件、产物设 2~3 个空，答案为课本原词。",
     {"stem_spec": "实验题干，空用①②③标注",
      "key_results": []},
     ""),
    ("bio_jr_cloze", "biology", 7, "kp_bio7_ecosystem_components", "fill", "cloze",
     "初中生物非选择题填空（七年级，生态系统的组成）。给一个具体生态系统（如草原/稻田），围绕生物部分三种类别与非生物部分设 2~3 个空，答案为课本原词。",
     {"stem_spec": "情境题干，空用①②③标注",
      "key_results": []},
     ""),
    ("bio_jr_cloze", "biology", 7, "kp_bio7_food_chain_web", "fill", "cloze",
     "初中生物非选择题填空（七年级，食物链与食物网）。给出具体食物链（如草→兔→鹰），围绕书写规则（起点/箭头方向/数量变化）设 2~3 个空，答案短而确定。",
     {"stem_spec": "题干，空用①②③标注",
      "key_results": []},
     ""),
    ("bio_jr_cloze", "biology", 8, "kp_bio8_dominant_recessive", "fill", "cloze",
     "初中生物非选择题填空（八年级，基因的显性与隐性）。用常规符号（A/a）设 2~3 个空：显隐性判断、基因型书写，答案唯一。",
     {"stem_spec": "题干，空用①②③标注",
      "key_results": []},
     ""),
    ("bio_jr_cloze", "biology", 8, "kp_bio8_specific_immunity", "fill", "cloze",
     "初中生物非选择题填空（八年级，特异性免疫与非特异性免疫：抗原/抗体/第三道防线）。设 2~3 个空，答案为课本原词。",
     {"stem_spec": "题干，空用①②③标注",
      "key_results": []},
     ""),
    ("bio_jr_cloze", "biology", 8, "kp_bio8_epidemic_links", "fill", "cloze",
     "初中生物非选择题填空（八年级，传染病流行的三个环节）。给一个具体传染病（如流感），围绕传染源/传播途径/易感人群设 2~3 个空，答案唯一。",
     {"stem_spec": "题干，空用①②③标注",
      "key_results": []},
     ""),
    ("bio_jr_cloze", "biology", 9, "kp_bio9_inquiry_experiment", "fill", "cloze",
     "初中生物非选择题填空（九年级综合：对照实验设计）。给一个探究情境（如光对鼠妇分布的影响），围绕变量唯一性/对照设置/实验结论设 2~3 个空，答案唯一。",
     {"stem_spec": "题干，空用①②③标注",
      "key_results": []},
     ""),
    ("bio_jr_cloze", "biology", 9, "kp_bio9_diagram_comprehension", "fill", "cloze",
     "初中生物非选择题填空（九年级综合识图：生态系统物质循环或遗传图解）。用文字描述图示信息后设 2~3 个空，答案唯一。",
     {"stem_spec": "题干，空用①②③标注",
      "key_results": []},
     ""),
    ("bio_hs_solve", "biology", 10, "kp_bio10_segregation_law", "solve", "solve",
     "高中生物非选择题（必修二，基因分离定律）。给具体杂交实验（如高茎豌豆自交/测交），设 2~3 小问：基因型推断、比例计算、概率计算，答案唯一（比例要核实自洽）。",
     {"stem_spec": "题干+（1）（2）（3）小问",
      "key_results": []},
     ""),
    ("bio_hs_solve", "biology", 10, "kp_bio10_cell_respiration", "solve", "solve",
     "高中生物非选择题（必修一，细胞呼吸）。围绕有氧呼吸三阶段场所/产物或实验测气体变化设 2~3 小问，答案为课本表述或唯一数值。",
     {"stem_spec": "题干+小问",
      "key_results": []},
     ""),
    ("bio_hs_solve", "biology", 10, "kp_bio10_photosynthesis", "solve", "solve",
     "高中生物非选择题（必修一，光合作用）。围绕光反应/暗反应场所与物质变化或影响光合因素实验设 2~3 小问，答案唯一。",
     {"stem_spec": "题干+小问",
      "key_results": []},
     ""),
    ("bio_hs_solve", "biology", 11, "kp_bio11_reflex_arc_hs", "solve", "solve",
     "高中生物非选择题（选择性必修一，反射弧与兴奋传导）。给具体反射情境，围绕感受器/效应器判断、兴奋传导方向、电位变化设 2~3 小问，答案唯一。",
     {"stem_spec": "题干+小问",
      "key_results": []},
     ""),
    ("bio_hs_solve", "biology", 11, "kp_bio11_blood_sugar_regulation", "solve", "solve",
     "高中生物非选择题（选择性必修一，血糖平衡调节）。围绕胰岛素/胰高血糖素的作用与糖尿病机理设 2~3 小问，答案为课本表述。",
     {"stem_spec": "题干+小问",
      "key_results": []},
     ""),
    ("bio_hs_solve", "biology", 12, "kp_bio12_energy_flow", "solve", "solve",
     "高中生物非选择题（选择性必修二，生态系统能量流动）。给具体食物链，围绕同化量/传递效率 10%~20%/能量流动特点设 2~3 小问，涉及计算的答案必须数值自洽。",
     {"stem_spec": "题干+小问",
      "key_results": []},
     ""),
    ("bio_hs_solve", "biology", 12, "kp_bio12_material_cycle", "solve", "solve",
     "高中生物非选择题（选择性必修二，碳循环）。围绕碳的存在形式/循环途径/温室效应设 2~3 小问，答案为课本表述。",
     {"stem_spec": "题干+小问",
      "key_results": []},
     ""),
    ("bio_hs_solve", "biology", 12, "kp_bio12_ecosystem_stability", "solve", "solve",
     "高中生物非选择题（选择性必修二，生态系统的稳定性）。围绕抵抗力/恢复力稳定性与具体措施设 2~3 小问，答案唯一。",
     {"stem_spec": "题干+小问",
      "key_results": []},
     ""),
    # —— 地理 ——
    ("geo_hs_solve", "geography", 10, "kp_geo10_natural_hazards", "solve", "solve",
     "高考地理选考题（自然灾害模块）。给一个具体区域灾害情境（如华南台风/西南滑坡），设 2 小问：成因分析、防灾措施。答案要点明确可给分。",
     {"stem_spec": "材料情境+（1）（2）两问",
      "key_results": []},
     ""),
    ("geo_hs_solve", "geography", 11, "kp_geo11_pollution_governance", "solve", "solve",
     "高考地理选考题（环境保护模块）。给一个具体环境问题情境（如湖泊富营养化/城市黑臭水体），设 2 小问：主要成因、治理措施。答案要点明确可给分。",
     {"stem_spec": "材料情境+（1）（2）两问",
      "key_results": []},
     ""),
    # —— 小学道法 连线 ——
    ("pol_prim_match", "politics", 1, "kp_pol1_safety_sign", "fill", "matching",
     "小学一年级道德与法治连线题：左栏 4 个安全标志/情境（文字描述，如「红色圆形中间一道白杠」），右栏 4 个含义（如「禁止通行」），连线后答案形如「1-B；2-A；3-D；4-C」。左右必须一一对应且无歧义。",
     {"stem_spec": "左栏 1~4、右栏 A~D，答案给出对应串",
      "key_results": []},
     ""),
    ("pol_prim_match", "politics", 2, "kp_pol2_traffic_sign", "fill", "matching",
     "小学二年级道德与法治连线归类题：左栏 4 个交通信号/标志（文字描述），右栏 4 个通行规则，连线答案形如「1-C；2-D；3-A；4-B」。必须一一对应无歧义。",
     {"stem_spec": "左栏 1~4、右栏 A~D",
      "key_results": []},
     ""),
    ("pol_prim_match", "politics", 3, "kp_pol3_safety_emergency", "fill", "matching",
     "小学三年级道德与法治连线题：左栏 4 种突发情况（火灾/溺水/迷路/雷电），右栏 4 种正确应对办法，连线答案形如「1-D；2-C；3-A；4-B」。应对办法必须是安全常识中的正确做法。",
     {"stem_spec": "左栏 1~4、右栏 A~D",
      "key_results": []},
     ""),
    ("pol_prim_match", "politics", 6, "kp_pol6_occupy_respect", "fill", "matching",
     "小学六年级道德与法治连线归类题：左栏 4 种职业劳动者（农民/医生/教师/环卫工人），右栏 4 句对应贡献描述，连线答案形如「1-A；2-D；3-B；4-C」。一一对应无歧义。",
     {"stem_spec": "左栏 1~4、右栏 A~D",
      "key_results": []},
     ""),
    # —— 小学科学 实验探究 ——
    ("sci_prim_experiment", "science", 3, "kp_sci3_soluble", "solve", "experiment",
     "小学三年级科学实验探究简答题：溶解实验（食盐/沙在水中的溶解对比）。围绕「怎样判断物体能否溶解」「加快溶解的方法」设 2 小问，答案语言儿童化、要点明确。",
     {"stem_spec": "实验情境+2 小问",
      "key_results": []},
     ""),
    ("sci_prim_experiment", "science", 4, "kp_sci4_water_purify", "solve", "experiment",
     "小学四年级科学实验探究简答题：水的净化（过滤实验）。围绕「过滤需要的器材」「过滤时要注意什么」设 2 小问，答案要点明确。",
     {"stem_spec": "实验情境+2 小问",
      "key_results": []},
     ""),
    ("sci_prim_experiment", "science", 5, "kp_sci5_sound_pitch", "solve", "experiment",
     "小学五年级科学实验探究简答题：声音的高低（音调）与物体振动快慢。给一个具体实验（敲击长短不同的尺子/琴弦），围绕「改变什么条件」「听到什么变化」「得出什么结论」设 2~3 小问。",
     {"stem_spec": "实验情境+2~3 小问",
      "key_results": []},
     ""),
    ("sci_prim_experiment", "science", 6, "kp_sci6_experiment_design", "solve", "experiment",
     "小学六年级科学实验探究简答题：设计对照实验（如绿豆发芽与水分/光照的关系）。围绕「研究的问题」「改变的条件（变量）」「保持相同的条件」「实验组与对照组」设 2~3 小问，答案体现变量唯一性。",
     {"stem_spec": "情境+2~3 小问",
      "key_results": []},
     ""),
]

PROMPT_TMPL = """你是一名严谨的 K12 命题专家。请为以下命题任务出一道题，只输出一个 JSON 对象（不要 markdown 围栏、不要多余文字）。

【学科/学段】{subject} {grade} 年级
【知识点】{kp_id} {kp_name}：{kp_desc}
【题型】{form}（item_type={item_type}）
【命题要求】{task}
【题干结构】{stem_spec}
【难度】difficulty 取 0~1 小数（0.2 简单 / 0.5 中等 / 0.7 较难），与学段匹配。
{extra}

【输出 JSON 字段】
{{
 "stem": "题干（中文或按学科要求）",
 "answer": "参考答案（确定、可批改）",
 "solution": "解析/给分要点（说明为什么这个答案对，或按点给分说明）",
 "difficulty": 0.0
}}

硬性要求：
1. 答案必须与题干自洽：从题干出发唯一可得（客观题干扰项要有合理排除理由）。
2. 题干不得包含答案本身。
3. 知识范围不得超出【知识点】与【学段】。
4. {dedup_hint}"""


def build_prompt(job):
    batch, subject, grade, kp, item_type, form, task, spec, _ref = job
    pool = G.kp_pool(subject, grade)
    kp_name, kp_desc = pool[kp]
    extra = ""
    if _ref:
        extra = "【内容基准（答案要点必须覆盖）】\n" + _ref
    if form in ("fill", "cloze"):
        dedup_hint = "若为填空，答案用中文分号或换行分点，与空一一对应。"
    elif form == "listening":
        dedup_hint = "听力材料以「M:/W:」或叙述句逐行给出，问题中每个选项独占一行，形如「A. …」。"
    elif form == "seven_to_five_sequence":
        dedup_hint = "7 个选项以「A. …」~「G. …」逐行列在题干末尾；answer 字段填形如「C-E-A-B-D」的顺序串。"
    elif form == "matching":
        dedup_hint = "answer 字段填形如「1-B；2-A；3-D；4-C」的连线结果。"
    else:
        dedup_hint = "解答题按小问给出参考答案，逐问给分要点。"
    return PROMPT_TMPL.format(subject=subject, grade=grade, kp_id=kp, kp_name=kp_name,
                              kp_desc=kp_desc[:200], form=form, item_type=item_type,
                              task=task, stem_spec=spec["stem_spec"], extra=extra,
                              dedup_hint=dedup_hint)


_KEY_TRANS = str.maketrans({
    "＋": "+", "＝": "=", "－": "-", "（": "(", "）": ")", "，": ",",
    "　": " ", "\u00a0": " ", "·": "·",
})


def _norm(s: str) -> str:
    return "".join(s.translate(_KEY_TRANS).split())


def check_math_keys(item, spec):
    """数学题：脚本指定的关键结论必须出现在 answer 或 solution 中
    （归一化空白与全角运算符后做包含匹配）。"""
    hay = _norm(str(item["answer"]) + " " + str(item["solution"]))
    missing = [k for k in spec.get("key_results", []) if _norm(k) not in hay]
    return missing


def gen_all(only: str | None):
    tasks = [j for j in JOBS if not only or j[0] == only]
    cands = []
    seq = 0
    for job in tasks:
        batch, subject, grade, kp, item_type, form, task, spec, _ref = job
        pool = G.kp_pool(subject, grade)
        dedup = G.Deduper(subject)
        attempt = 0
        ok = False
        while attempt < 3 and not ok:
            attempt += 1
            prompt = build_prompt(job)
            if attempt > 1:
                prompt += "\n\n注意：前一次输出不合格（未通过校验），请更严格地按要求重出。"
            try:
                data = G.llm_json(prompt, temperature=0.4)
                stem, answer = str(data["stem"]).strip(), str(data["answer"]).strip()
                solution = str(data.get("solution", "")).strip()
                diff = float(data.get("difficulty", 0.5))
                assert stem and answer, "空题干/答案"
                assert 0.0 <= diff <= 1.0, f"难度越界 {diff}"
                if dedup.is_dup(stem):
                    raise ValueError("与既有题干 3-gram 重合（判重）")
                missing = check_math_keys({"answer": answer, "solution": solution}, spec)
                if missing:
                    raise ValueError(f"关键结论缺失: {missing}")
                seq += 1
                it = G.make_item(f"{subject}_gap_llm_{seq:03d}",
                                 item_type, stem, answer, [kp], diff, solution,
                                 form=form, answer_mode=None,
                                 source="llm_generated", agent=G.GEN_AGENT,
                                 note=LLM_NOTE)
                it["_grade"] = grade
                it["_batch"] = batch
                errs = G.validate_items([dict(it)], subject)
                if errs:
                    raise ValueError("校验失败: " + "; ".join(errs))
                cands.append(it)
                dedup.add(stem)
                ok = True
            except Exception as e:  # noqa: BLE001
                print(f"  … {batch} 第 {attempt} 次尝试失败：{e}", file=sys.stderr)
        if not ok:
            print(f"  !! {batch} 三次尝试均失败，如实计入丢弃", file=sys.stderr)
    with open(CAND, "w", encoding="utf-8") as f:
        json.dump(cands, f, ensure_ascii=False, indent=2)
    print(f"候选 {len(cands)} / 任务 {len(tasks)} -> {CAND}")
    for it in cands:
        print("=" * 70)
        print(f"[{it['_batch']}] {it['id']} ({it['form']}, kp={it['kps'][0]}, d={it['difficulty']})")
        print("题干：", it["stem"])
        print("答案：", it["answer"])
        print("解析：", it["solution"][:300])


def apply_all():
    with open(CAND, encoding="utf-8") as f:
        cands = json.load(f)
    ledger = {"batch": "llm_gapfill_20261006", "appended": []}
    by_key = {}
    seen_stems = {}
    for it in cands:
        subject = it["id"].split("_")[0]
        dedup = seen_stems.setdefault(subject, G.Deduper(subject))
        if dedup.is_dup(it["stem"]):
            print(f"  丢弃（判重）{it['id']}")
            continue
        dedup.add(it["stem"])
        errs = G.validate_items([dict(it)], subject)
        if errs:
            print(f"  丢弃（校验失败 {errs}）{it['id']}")
            continue
        by_key.setdefault((subject, it.pop("_grade")), []).append(it)
    n = 0
    for (subject, grade), items in sorted(by_key.items()):
        n += G.append_items(subject, grade, items, ledger)
        print(f"{subject} grade{grade}: +{len(items)}")
    with open(os.path.join(HERE, "ledger_llm.json"), "w", encoding="utf-8") as f:
        json.dump(ledger, f, ensure_ascii=False, indent=2)
    print(f"共落盘 {n} 题")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["gen", "apply"])
    ap.add_argument("--only", default=None)
    args = ap.parse_args()
    if args.cmd == "gen":
        gen_all(args.only)
    else:
        apply_all()
    return 0


if __name__ == "__main__":
    sys.exit(main())
