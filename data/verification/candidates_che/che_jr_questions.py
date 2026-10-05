# -*- coding: utf-8 -*-
"""che_jr_questions.py —— 411 道化学题（初三）原始数据。
每条记录格式：
  (kp_id, item_type, form, stem, options, answer, solution, difficulty, answer_mode)
- options: list[str] 或 None
- answer: str
  - choice/mcq_single: 单字母 'A' / 'B' / ...
  - choice/mcq_multiple: 多字母用 ',' 分隔，例如 'A,C'
  - fill/solve: 中文短字符串
- answer_mode: 仅多选为 'subset'，其余 None
"""
QUESTIONS = []
def Q(kp, t, form, stem, opts, ans, sol, diff, am=None):
    QUESTIONS.append((kp, t, form, stem, opts, ans, sol, diff, am))

# ===== Cluster 1: 科学探究与化学实验 (21 KPs × 3 = 63 题) =====

# kp_chem9_chem_essence
Q("kp_chem9_chem_essence", "choice", "mcq_single",
  "化学研究的核心层次是（　　）",
  ["宏观物质","分子、原子层次","原子核内部结构","天体运行"],
  "B",
  "化学是在分子、原子层次上研究物质的组成、结构、性质、转化及应用的一门基础学科，故选 B。",
  0.35)
Q("kp_chem9_chem_essence", "choice", "mcq_single",
  "下列选项中不属于化学研究范畴的是（　　）",
  ["新型可降解材料的研发","葡萄糖分子的结构测定","氯化钠在水中的溶解速率","太阳系行星的运动规律"],
  "D",
  "化学研究物质（材料、分子、反应等），不研究天体物理现象。太阳系行星运动属天文学范畴。",
  0.32)
Q("kp_chem9_chem_essence", "fill", "fill_blank",
  "化学是一门在______层次上研究物质的组成、结构、性质、转化及其应用的基础自然科学。",
  None,
  "分子、原子",
  "化学的定义：在分子、原子层次上认识物质和创造物质。",
  0.4)

# kp_chem9_chem_dev_history
Q("kp_chem9_chem_dev_history", "choice", "mcq_single",
  "我国制碱工业的先驱侯德榜先生发明的制碱法被称为（　　）",
  ["索尔维制碱法","侯氏制碱法","氨碱法","联合制碱法"],
  "B",
  "侯德榜先生对氨碱法加以改进，发明了侯氏制碱法，为我国制碱工业作出重大贡献。",
  0.4)
Q("kp_chem9_chem_dev_history", "choice", "mcq_single",
  "下列我国古代成就中，主要利用了化学变化的是（　　）",
  ["指南针的使用","火药的发明与应用","活字印刷术","张衡的地动仪"],
  "B",
  "火药的发明涉及硫黄、硝石、木炭在点燃条件下的化学反应，属于化学变化。",
  0.45)
Q("kp_chem9_chem_dev_history", "fill", "fill_blank",
  "门捷列夫发现了______，使化学研究从零散事实走向系统化。",
  None,
  "元素周期律",
  "门捷列夫发现元素周期律并编制了第一张元素周期表，是化学发展史上的里程碑。",
  0.5)

# kp_chem9_sci_inquiry
Q("kp_chem9_sci_inquiry", "choice", "mcq_single",
  "下列不属于科学探究基本环节的是（　　）",
  ["提出问题","猜想与假设","背诵课本定义","设计实验方案"],
  "C",
  "科学探究包括提出问题、猜想与假设、设计方案、实验、收集证据、得出结论、反思评价与表达交流。背诵不属于科学探究环节。",
  0.4)
Q("kp_chem9_sci_inquiry", "choice", "mcq_single",
  "小明观察到铜绿受热分解，提出铜绿分解可能生成氧化铜、水和二氧化碳。这一环节属于（　　）",
  ["提出问题","猜想与假设","设计实验","得出结论"],
  "B",
  "对铜绿分解产物提出预测性论断，即猜想与假设。",
  0.45)
Q("kp_chem9_sci_inquiry", "fill", "fill_blank",
  "科学探究的完整过程通常包括：提出问题→______→设计方案→实验→收集证据→得出结论→反思评价→表达交流。",
  None,
  "猜想与假设",
  "猜想与假设是科学探究的必经环节，承上启下。",
  0.42)

# kp_chem9_exp_observation
Q("kp_chem9_exp_observation", "choice", "mcq_single",
  "下列描述实验现象的语句中，正确的是（　　）",
  ["铁丝在氧气中燃烧生成四氧化三铁","镁条燃烧发出耀眼白光，生成白色固体","加热碱式碳酸铜产生气体，生成黑色固体和水","硫在氧气中燃烧产生明亮的蓝紫色火焰"],
  "B",
  "A 不能直接描述生成物（应说剧烈燃烧、火星四射、生成黑色固体）；C 缺少水蒸气检验；D 硫在空气中是微弱的淡蓝色火焰。",
  0.55)
Q("kp_chem9_exp_observation", "choice", "mcq_single",
  "做化学实验观察现象时，下列做法正确的是（　　）",
  ["将鼻孔凑近容器口闻气体气味","用手直接接触药品","如实记录并描述现象","为加快反应，将试管口对着自己"],
  "C",
  "化学实验观察要客观记录。A 会吸入有毒气体；B 多数药品有毒或腐蚀性；D 易造成伤害。",
  0.4)
Q("kp_chem9_exp_observation", "fill", "fill_blank",
  "描述实验现象时，一般应按照反应前→______→反应后的顺序观察与记录。",
  None,
  "反应中",
  "科学规范的观察记录应分前—中—后三阶段，便于后续分析。",
  0.4)

# kp_chem9_instruments_glass
Q("kp_chem9_instruments_glass", "choice", "mcq_single",
  "下列仪器中，可直接放在酒精灯火焰上加热的是（　　）",
  ["量筒","烧杯","试管","集气瓶"],
  "C",
  "试管可直接加热；量筒、集气瓶不能加热；烧杯需垫石棉网间接加热。",
  0.35)
Q("kp_chem9_instruments_glass", "choice", "mcq_single",
  "下列仪器中，既可用作反应容器又能直接加热的是（　　）",
  ["量筒","试管","集气瓶","锥形瓶"],
  "B",
  "试管容积小、受热快，可直接加热并盛装少量反应物。",
  0.32)
Q("kp_chem9_instruments_glass", "fill", "fill_blank",
  "用来取用少量粉末状药品的仪器是______。",
  None,
  "药匙（或纸槽）",
  "粉末状药品用药匙或纸槽取用，块状药品用镊子夹取。",
  0.35)

# kp_chem9_instruments_measure
Q("kp_chem9_instruments_measure", "choice", "mcq_single",
  "用 100 mL 量筒量取 80.0 mL 水时，正确的读数方法是（　　）",
  ["视线俯视刻度","视线仰视刻度","视线与凹液面最低处相平","视线与液面最高点相平"],
  "C",
  "量筒读数视线应与量筒内液体凹液面最低处保持水平。",
  0.45)
Q("kp_chem9_instruments_measure", "choice", "mcq_single",
  "用托盘天平称量 5.6 g 药品时，下列操作正确的是（　　）",
  ["药品直接放在左盘","游码归零后，左物右码放置，游码移至 0.6 g 处","称量时用手取放砝码","药品潮湿不需要处理"],
  "B",
  "托盘天平使用规则：左物右码、砝码用镊子夹取、潮湿或腐蚀性药品放玻璃器皿中。",
  0.5)
Q("kp_chem9_instruments_measure", "fill", "fill_blank",
  "量筒无零刻度，从下往上刻度值______。",
  None,
  "依次增大",
  "量筒刻度由下往上递增，但起始刻度不为 0。",
  0.4)

# kp_chem9_reagent_handling
Q("kp_chem9_reagent_handling", "choice", "mcq_single",
  "取用液体药品时，瓶塞应（　　）",
  ["正放在桌面上","倒放在桌面上","拿在手中","随便放置"],
  "B",
  "瓶塞倒放是为了防止污染瓶塞和药品，是三不一要原则之一。",
  0.4)
Q("kp_chem9_reagent_handling", "choice", "mcq_single",
  "下列药品取用操作中，正确的是（　　）",
  ["用药匙直接从试剂瓶中取用多量粉末","倾倒液体时，标签朝向手心","用同一滴管取不同液体","品尝药品味道"],
  "B",
  "A 多量应先倒在纸上；C 易污染；D 化学药品严禁品尝。",
  0.5)
Q("kp_chem9_reagent_handling", "fill", "fill_blank",
  "实验室取用药品的基本原则三不——不能用手接触药品，不要把鼻孔凑近容器口去闻药品的气味，______。",
  None,
  "不得尝任何药品的味道",
  "化学实验室三不原则是安全用药的最基本要求。",
  0.4)

# kp_chem9_reagent_storage
Q("kp_chem9_reagent_storage", "choice", "mcq_single",
  "下列试剂中，应该避光保存的是（　　）",
  ["浓盐酸","氢氧化钠固体","硝酸银溶液","氯化钠固体"],
  "C",
  "硝酸银见光分解，应避光密封保存。浓盐酸密封防挥发，NaOH 密封防潮解和变质。",
  0.5)
Q("kp_chem9_reagent_storage", "choice", "mcq_single",
  "氢氧化钠固体必须密封保存的原因是（　　）",
  ["易燃","易潮解且能与空气中CO2反应而变质","易升华","易爆炸"],
  "B",
  "NaOH 易潮解，并吸收空气中的 CO2 生成 Na2CO3 而变质，故必须密封保存。",
  0.45)
Q("kp_chem9_reagent_storage", "fill", "fill_blank",
  "实验室保存浓盐酸时，应该______，防止氯化氢气体挥发。",
  None,
  "密封",
  "浓盐酸具有挥发性，应密封保存在阴凉处。",
  0.4)

# kp_chem9_heating_ops
Q("kp_chem9_heating_ops", "choice", "mcq_single",
  "使用酒精灯给试管内固体加热时，试管口应（　　）",
  ["向上倾斜","向下倾斜","水平放置","随意摆放"],
  "B",
  "加热固体且反应可能生成水时，试管口应略向下倾斜，防止冷凝水倒流使试管炸裂。",
  0.45)
Q("kp_chem9_heating_ops", "choice", "mcq_single",
  "熄灭酒精灯的正确方法是（　　）",
  ["用嘴吹灭","用灯帽盖灭","用水浇灭","用手扇灭"],
  "B",
  "酒精灯用灯帽盖灭，灯帽可二次盖上以熄灭。吹灭易引燃灯内酒精蒸气。",
  0.35)
Q("kp_chem9_heating_ops", "fill", "fill_blank",
  "酒精灯的火焰分外焰、内焰、焰心三层，温度最高的是______。",
  None,
  "外焰",
  "外焰燃烧最充分，温度最高，加热时用外焰。",
  0.35)

# kp_chem9_glass_rod_funcs
Q("kp_chem9_glass_rod_funcs", "choice", "mcq_single",
  "在过滤操作中，玻璃棒的作用是（　　）",
  ["加速溶解","搅拌防止液滴飞溅","引流","转移固体"],
  "C",
  "过滤时玻璃棒用于引流，使液体沿玻璃棒流入漏斗，防止溅出。",
  0.4)
Q("kp_chem9_glass_rod_funcs", "choice", "mcq_single",
  "蒸发食盐水时使用玻璃棒的主要目的是（　　）",
  ["引流液体","搅拌防止液滴飞溅并使受热均匀","加速反应","降温"],
  "B",
  "蒸发时玻璃棒搅拌防止液滴飞溅，同时使液体受热均匀，避免局部温度过高。",
  0.45)
Q("kp_chem9_glass_rod_funcs", "fill", "fill_blank",
  "测定溶液 pH 时，用______蘸取少量溶液滴在 pH 试纸上。",
  None,
  "玻璃棒",
  "玻璃棒蘸取少量待测液，防止污染和方便操作。",
  0.4)

# kp_chem9_instrument_assembly
Q("kp_chem9_instrument_assembly", "choice", "mcq_single",
  "检查装置气密性的正确方法是（　　）",
  ["用手紧握容器后观察导管口是否有气泡冒出，松开后导管内形成一段水柱","用酒精灯加热容器","用力摇动装置","将装置浸入水中观察是否冒泡"],
  "A",
  "检查气密性的标准方法：手握容器使气体受热膨胀，导管口冒气泡，松手后导管内形成水柱。",
  0.5)
Q("kp_chem9_instrument_assembly", "choice", "mcq_single",
  "洗涤玻璃仪器的正确顺序是（　　）",
  ["直接用清水冲洗即可","先用洗涤剂刷洗，再用清水冲洗","用酒精冲洗","用布擦干即可"],
  "B",
  "一般玻璃仪器先用洗涤剂刷洗，再用清水冲洗干净，必要时用蒸馏水润洗。",
  0.4)
Q("kp_chem9_instrument_assembly", "fill", "fill_blank",
  "连接玻璃导管和橡皮塞时，应先将导管口用水润湿，然后______插入橡皮塞。",
  None,
  "缓慢旋转",
  "用水润湿并缓慢旋转可减小摩擦力，便于连接且不易折断玻璃管。",
  0.45)

# kp_chem9_separation_ops
Q("kp_chem9_separation_ops", "choice", "mcq_single",
  "下列混合物中，适合用过滤方法分离的是（　　）",
  ["食盐和水","酒精和水","泥沙和水","汽油和水"],
  "C",
  "过滤适用于分离不溶性固体与液体。泥沙不溶于水，故可用过滤法。",
  0.35)
Q("kp_chem9_separation_ops", "choice", "mcq_single",
  "过滤操作中需要遵循一贴二低三靠原则，其中二低指的是（　　）",
  ["滤纸边缘低于漏斗边缘；滤液液面低于滤纸边缘","滤纸边缘高于漏斗边缘；液面低于滤纸边缘","烧杯口紧靠玻璃棒","玻璃棒紧靠三层滤纸"],
  "A",
  "过滤原则一贴二低三靠：滤纸紧贴漏斗内壁；滤纸边缘低于漏斗边缘，液面低于滤纸边缘；倾倒时烧杯口紧靠玻璃棒，玻璃棒紧靠三层滤纸，漏斗下端紧靠烧杯内壁。",
  0.55)
Q("kp_chem9_separation_ops", "fill", "fill_blank",
  "蒸发食盐水时，当蒸发皿中出现______时，应停止加热，利用余热将水分蒸干。",
  None,
  "较多固体",
  "蒸发过程中出现较多固体即停止加热，防止温度过高造成固体溅出或分解。",
  0.45)

# kp_chem9_salt_purification
Q("kp_chem9_salt_purification", "choice", "mcq_single",
  "粗盐提纯实验中，下列操作顺序正确的是（　　）",
  ["溶解→过滤→蒸发→计算产率","过滤→溶解→蒸发→计算产率","蒸发→溶解→过滤→计算产率","溶解→蒸发→过滤→计算产率"],
  "A",
  "粗盐提纯步骤：称量→溶解→过滤（除难溶物）→蒸发（结晶）→计算产率。",
  0.45)
Q("kp_chem9_salt_purification", "choice", "mcq_single",
  "粗盐中难溶性杂质去除的主要方法是（　　）",
  ["过滤","蒸发","结晶","蒸馏"],
  "A",
  "难溶性杂质主要通过过滤去除。可溶性杂质用化学方法（如除 Ca2+、Mg2+、SO4 2-）去除。",
  0.4)
Q("kp_chem9_salt_purification", "fill", "fill_blank",
  "粗盐提纯实验中，各步骤都使用玻璃棒，其作用分别是：溶解时______，过滤时引流，蒸发时搅拌。",
  None,
  "搅拌加速溶解",
  "溶解时玻璃棒搅拌加速氯化钠溶解。",
  0.4)

# kp_chem9_control_variable
Q("kp_chem9_control_variable", "choice", "mcq_single",
  "探究反应温度对化学反应速率的影响时，下列设计正确的是（　　）",
  ["用不同温度下、不同浓度的过氧化氢溶液","用相同温度下、不同浓度的过氧化氢溶液","用相同浓度、不同温度的过氧化氢溶液，加入等量催化剂","用相同浓度、相同温度的过氧化氢溶液，但用不同催化剂"],
  "C",
  "探究温度影响应只改变温度一个变量，其他条件（浓度、催化剂等）保持相同。",
  0.55)
Q("kp_chem9_control_variable", "choice", "mcq_single",
  "下列实验中，需要采用控制变量法的是（　　）",
  ["测定空气中氧气含量","探究催化剂对过氧化氢分解速率的影响","粗盐提纯","实验室制取氧气"],
  "B",
  "探究催化剂作用时需保证温度、浓度等条件一致，只改变是否有催化剂。",
  0.5)
Q("kp_chem9_control_variable", "fill", "fill_blank",
  "当一个实验中存在多个变量时，每次只改变其中的______个变量，而其他变量保持不变。",
  None,
  "一",
  "控制变量法核心：单一变量，便于判断因果关系。",
  0.4)

# kp_chem9_hypothesis_design
Q("kp_chem9_hypothesis_design", "choice", "mcq_single",
  "某兴趣小组探究铁生锈的条件，提出下列假设，其中不合理的是（　　）",
  ["铁生锈可能与水有关","铁生锈可能与氧气有关","铁生锈与水、氧气都无关","铁生锈可能与水、氧气同时接触有关"],
  "C",
  "铁生锈确实是水与氧气共同作用的结果。提出假设不能直接否定研究目的。",
  0.5)
Q("kp_chem9_hypothesis_design", "choice", "mcq_single",
  "设计实验方案时，下列做法不科学的是（　　）",
  ["设置对照实验","只改变一个变量","对实验过程不做任何记录","多次重复实验取平均值"],
  "C",
  "实验过程中应详细记录现象和数据，便于后续分析。",
  0.4)
Q("kp_chem9_hypothesis_design", "fill", "fill_blank",
  "在探究可燃物燃烧条件的实验中，可燃物必须同时满足：温度达到可燃物的______且与氧气（或空气）接触。",
  None,
  "着火点",
  "燃烧需要同时具备：可燃物、氧气（空气）、温度达到着火点，三者缺一不可。",
  0.45)

# kp_chem9_evidence_conclusion
Q("kp_chem9_evidence_conclusion", "choice", "mcq_single",
  "由铁丝在氧气中剧烈燃烧、火星四射、生成黑色固体，可以得出的结论是（　　）",
  ["铁丝能在空气中燃烧","铁在氧气中能燃烧，生成物为四氧化三铁","氧气是可燃性气体","铁的熔点很高"],
  "B",
  "实验现象直接支持结论：铁在氧气中燃烧生成黑色固体四氧化三铁。",
  0.45)
Q("kp_chem9_evidence_conclusion", "choice", "mcq_single",
  "下列结论的得出过程中运用了证据推理的是（　　）",
  ["根据质量守恒定律推出化学反应前后元素种类不变","背诵元素周期表","直接抄写实验现象","随机猜测"],
  "A",
  "B、C、D 均不构成证据推理。A 是基于实验事实和定律进行逻辑推演。",
  0.5)
Q("kp_chem9_evidence_conclusion", "fill", "fill_blank",
  "实验探究过程中，根据实验现象和数据，运用分析、比较、归纳等方法得出结论，这一过程称为______。",
  None,
  "证据推理",
  "证据推理是科学探究中基于证据得出结论的思维方式。",
  0.45)

# kp_chem9_error_analysis
Q("kp_chem9_error_analysis", "choice", "mcq_single",
  "用托盘天平称量 NaOH 固体时，将 NaOH 直接放在纸上称量，会导致结果（　　）",
  ["偏大","偏小","无影响","先偏大后偏小"],
  "B",
  "NaOH 易潮解且腐蚀性强，应放在玻璃器皿（如小烧杯）中称量。直接放纸上，部分 NaOH 会粘在纸上且潮解使质量偏小。",
  0.55)
Q("kp_chem9_error_analysis", "choice", "mcq_single",
  "用量筒量取 25 mL 水时，俯视读数，则实际量取水的体积（　　）",
  ["大于 25 mL","小于 25 mL","等于 25 mL","无法判断"],
  "B",
  "俯视时读数大于实际液面刻度，故实际量取的液体体积偏小。",
  0.55)
Q("kp_chem9_error_analysis", "fill", "fill_blank",
  "过滤时如果液面高于滤纸边缘，则滤液会______。",
  None,
  "浑浊",
  "液面高于滤纸边缘时，液体会从滤纸和漏斗之间流下，未经过滤，滤液浑浊。",
  0.5)

# kp_chem9_data_handling
Q("kp_chem9_data_handling", "choice", "mcq_single",
  "为减小实验误差，下列做法正确的是（　　）",
  ["只做一次实验","多次实验取平均值","随意记录数据","不进行数据处理"],
  "B",
  "多次实验取平均值是减小实验误差的有效方法。",
  0.35)
Q("kp_chem9_data_handling", "choice", "mcq_single",
  "下列实验数据记录中，格式规范的是（　　）",
  ["用托盘天平称得 NaCl 5.6 克","量取水 18.4 毫升","pH 约为 7","反应温度 25 度"],
  "A",
  "记录数据应带单位，托盘天平读数至 0.1 g。A 格式规范。",
  0.45)
Q("kp_chem9_data_handling", "fill", "fill_blank",
  "实验报告一般包含实验目的、实验原理、______、实验现象、实验结论和反思等部分。",
  None,
  "实验步骤（或实验用品）",
  "完整的实验报告有助于对实验进行系统分析和交流。",
  0.4)

# kp_chem9_safety_lab
Q("kp_chem9_safety_lab", "choice", "mcq_single",
  "下列化学实验事故的处理方法中，错误的是（　　）",
  ["酒精灯失火用湿布盖灭","浓硫酸沾到皮肤上立即用大量水冲洗，再涂 3%~5% NaHCO3 溶液","碱液溅到眼睛里立即用大量水冲洗","酸液沾到皮肤上立即涂 NaOH 溶液"],
  "D",
  "D 错误：酸液沾到皮肤上应先用大量水冲洗，再涂 3%~5% NaHCO3 溶液，不能用 NaOH（强碱会腐蚀皮肤）。",
  0.55)
Q("kp_chem9_safety_lab", "choice", "mcq_single",
  "实验桌上少量酒精起火，应立即采取的措施是（　　）",
  ["用水浇灭","用沙土盖灭","用湿抹布盖灭","迅速跑开"],
  "C",
  "少量酒精起火可用湿抹布盖灭，隔绝空气灭火。酒精密度比水小，不能用水浇。",
  0.45)
Q("kp_chem9_safety_lab", "fill", "fill_blank",
  "浓硫酸沾到皮肤上，应立即用大量______冲洗，再涂上 3%~5% 的碳酸氢钠溶液。",
  None,
  "水",
  "先用大量水稀释和冲洗，再涂弱碱性溶液中和残留酸。",
  0.45)

# kp_chem9_sci_attitude
Q("kp_chem9_sci_attitude", "choice", "mcq_single",
  "下列做法中不符合科学探究态度的是（　　）",
  ["尊重实验事实，如实记录现象","对异常现象刨根问底","坚持错误结论不改变","善于与他人交流合作"],
  "C",
  "科学探究应坚持实事求是的态度，遇到反证应及时修正结论。",
  0.4)
Q("kp_chem9_sci_attitude", "choice", "mcq_single",
  "下列关于科学探究精神说法正确的是（　　）",
  ["实验失败说明探究毫无意义","科学结论一旦得出就不可更改","要敢于质疑、勇于创新","科学家的工作与普通人无关"],
  "C",
  "科学探究精神包括实事求是、敢于质疑、合作创新等核心要素。",
  0.4)
Q("kp_chem9_sci_attitude", "fill", "fill_blank",
  "科学探究过程中，应该坚持______的态度，对待实验结果和他人观点都要客观公正。",
  None,
  "实事求是",
  "实事求是是科学探究的基本态度。",
  0.4)

# kp_chem9_gas_prep_general
Q("kp_chem9_gas_prep_general", "choice", "mcq_single",
  "实验室制取气体的装置一般由发生装置和收集装置组成。选择发生装置时不需要考虑的因素是（　　）",
  ["反应物的状态","反应条件","生成气体的密度","生成气体的颜色"],
  "D",
  "发生装置选择依据反应物状态和反应条件；收集装置依据气体密度、溶解性以及是否与水反应等。气体颜色与装置选择无关。",
  0.5)
Q("kp_chem9_gas_prep_general", "choice", "mcq_single",
  "下列气体中，既能用向上排空气法又能用排水法收集的是（　　）",
  ["氢气","二氧化碳","氧气","氨气"],
  "C",
  "氧气不易溶于水且密度比空气大，既可排水又可向上排空气法。",
  0.45)
Q("kp_chem9_gas_prep_general", "fill", "fill_blank",
  "实验室制取气体的思路：研究反应物状态、反应条件→确定______→确定收集方法→验证与验满。",
  None,
  "发生装置",
  "气体制备通常包括发生装置和收集装置两部分。",
  0.4)

# ===== Cluster 2: 物质的性质与应用 (43 KPs) =====

# kp_chem9_air_composition
Q("kp_chem9_air_composition", "choice", "mcq_single",
  "空气中按体积分数计算含量最高的气体是（　　）",
  ["氧气","氮气","二氧化碳","稀有气体"],
  "B",
  "空气成分按体积分数：N2 约 78%、O2 约 21%、稀有气体 0.94%、CO2 0.03%、其他气体和杂质 0.03%。",
  0.32)
Q("kp_chem9_air_composition", "choice", "mcq_single",
  "测定空气中氧气含量的实验，下列说法正确的是（　　）",
  ["实验前必须夹紧弹簧夹","红磷燃烧产生大量白烟（白烟是 P2O5 固体小颗粒）","实验结果偏大是因为装置漏气","可以用木炭代替红磷"],
  "B",
  "A：实验前必须检查装置气密性，且打开弹簧夹；C：偏小才是漏气；D：木炭燃烧生成 CO2 气体，瓶内气压变化不大。",
  0.55)
Q("kp_chem9_air_composition", "fill", "fill_blank",
  "测定空气中氧气含量的实验中，红磷燃烧消耗氧气，冷却后打开弹簧夹，烧杯中的水被吸入集气瓶中，进入水的体积约为瓶内空气总体积的______。",
  None,
  "五分之一（1/5）",
  "氧气约占空气体积的 1/5，反应消耗后瓶内压强减小，水被吸入约 1/5 体积。",
  0.4)

# kp_chem9_air_pollution
Q("kp_chem9_air_pollution", "choice", "mcq_single",
  "下列气体中不属于空气污染物的是（　　）",
  ["二氧化硫（SO2）","二氧化氮（NO2）","可吸入颗粒物（PM2.5）","氮气（N2）"],
  "D",
  "目前计入空气质量监测的主要污染物有：SO2、NO2、PM2.5/PM10、O3、CO 等。氮气是空气的主要成分，不属于污染物。",
  0.35)
Q("kp_chem9_air_pollution", "choice", "mcq_single",
  "PM2.5 是指大气中直径小于或等于 2.5 微米的颗粒物，下列关于 PM2.5 的说法错误的是（　　）",
  ["PM2.5 是可吸入颗粒物","PM2.5 直径单位是微米","PM2.5 直径单位是毫米","PM2.5 是空气质量监测的重要指标"],
  "C",
  "PM2.5 中 2.5 的单位是微米（μm），1 μm = 10^-3 mm。",
  0.4)
Q("kp_chem9_air_pollution", "fill", "fill_blank",
  "目前计入我国空气质量监测的主要污染物除 SO2、NO2 外，还包括______、O3、CO 等。",
  None,
  "可吸入颗粒物（PM2.5/PM10）",
  "六大主要污染物：SO2、NO2、PM2.5、PM10、O3、CO。",
  0.4)

# kp_chem9_n2_rare_gases
Q("kp_chem9_n2_rare_gases", "choice", "mcq_single",
  "下列关于氮气用途的叙述，错误的是（　　）",
  ["用作保护气","用于制造硝酸和化肥","用作焊接金属时的保护气","用于供给呼吸"],
  "D",
  "氮气不能供给呼吸（不支持呼吸）。",
  0.4)
Q("kp_chem9_n2_rare_gases", "choice", "mcq_single",
  "稀有气体（氦、氖、氩等）在通电时会发出不同颜色的光，这一性质可用于（　　）",
  ["作保护气","制霓虹灯","填充气球","医疗冷冻"],
  "B",
  "稀有气体通电发光用于制霓虹灯；密度小且化学性质稳定用于填充气球和作保护气。",
  0.4)
Q("kp_chem9_n2_rare_gases", "fill", "fill_blank",
  "氮气的化学性质不活泼，常温下很难与其他物质发生反应，因此常用作______。",
  None,
  "保护气",
  "氮气化学性质稳定，常用作焊接金属、灯泡、食品包装等的保护气。",
  0.4)

# kp_chem9_o2_properties
Q("kp_chem9_o2_properties", "choice", "mcq_single",
  "下列关于氧气物理性质的叙述，正确的是（　　）",
  ["氧气易溶于水","氧气是无色、无味、不易溶于水的气体","氧气能使带火星的木条熄灭","氧气的密度比空气小"],
  "B",
  "氧气不易溶于水，密度比空气略大，能使带火星的木条复燃。",
  0.32)
Q("kp_chem9_o2_properties", "choice", "mcq_single",
  "下列物质在氧气中燃烧，集气瓶底需要预先放少量水或铺一层细沙的是（　　）",
  ["硫","木炭","铁丝","蜡烛"],
  "C",
  "铁丝在氧气中燃烧生成高温熔化物，溅落瓶底易炸裂瓶底，需铺细沙或放少量水。",
  0.5)
Q("kp_chem9_o2_properties", "fill", "fill_blank",
  "氧气能使带火星的木条______，这一性质常用于检验氧气。",
  None,
  "复燃",
  "氧气具有助燃性，能使带火星的木条复燃，是氧气检验的特征反应。",
  0.35)

# kp_chem9_oxidation_types
Q("kp_chem9_oxidation_types", "choice", "mcq_single",
  "下列变化中不属于缓慢氧化的是（　　）",
  ["铁生锈","食物腐烂","蜡烛燃烧","酿酒发酵"],
  "C",
  "蜡烛燃烧是剧烈氧化；其他是缓慢氧化，过程不明显但放出热量。",
  0.4)
Q("kp_chem9_oxidation_types", "choice", "mcq_single",
  "白磷在空气中能自燃，这一过程属于（　　）",
  ["缓慢氧化","自燃","分解反应","物理变化"],
  "B",
  "白磷着火点低（约 40℃），与空气接触后缓慢氧化放出热量，使温度达到着火点而自发燃烧，即自燃。",
  0.45)
Q("kp_chem9_oxidation_types", "fill", "fill_blank",
  "缓慢氧化与剧烈氧化的本质相同，都是物质与______发生的反应，只是反应速率和现象不同。",
  None,
  "氧气（O2）",
  "氧化反应的本质都是与氧结合，区别在于反应速率。",
  0.4)

# kp_chem9_catalyst
Q("kp_chem9_catalyst", "choice", "mcq_single",
  "下列关于催化剂的说法中，正确的是（　　）",
  ["催化剂在反应后质量减少","催化剂能改变其他物质的化学反应速率","催化剂在反应后化学性质发生改变","任何反应都需要催化剂"],
  "B",
  "催化剂能改变化学反应速率，其本身的质量和化学性质在反应前后均不变。",
  0.4)
Q("kp_chem9_catalyst", "choice", "mcq_single",
  "在过氧化氢溶液中加入二氧化锰，下列描述错误的是（　　）",
  ["二氧化锰是催化剂","产生氧气的速率加快","二氧化锰的质量不变","二氧化锰的化学性质改变"],
  "D",
  "二氧化锰作为催化剂，质量和化学性质在反应前后均不变。",
  0.45)
Q("kp_chem9_catalyst", "fill", "fill_blank",
  "在化学反应里能改变其他物质的化学反应速率，而本身的质量和化学性质在反应前后都不改变的物质叫做______。",
  None,
  "催化剂",
  "催化剂定义：改变化学反应速率，反应前后质量和化学性质均不变。",
  0.35)

# kp_chem9_o2_lab_prep
Q("kp_chem9_o2_lab_prep", "choice", "mcq_single",
  "实验室用高锰酸钾制取氧气时，试管口应（　　）",
  ["向上倾斜","向下倾斜","水平放置","垂直放置"],
  "B",
  "为防止高锰酸钾粉末进入导管，试管口应略向下倾斜并塞一团棉花。",
  0.4)
Q("kp_chem9_o2_lab_prep", "choice", "mcq_single",
  "实验室用过氧化氢溶液制取氧气时，通常加入少量二氧化锰，其作用是（　　）",
  ["作反应物","作催化剂","作干燥剂","作指示剂"],
  "B",
  "二氧化锰催化过氧化氢分解，本身质量和化学性质不变。",
  0.35)
Q("kp_chem9_o2_lab_prep", "fill", "fill_blank",
  "实验室用高锰酸钾制取氧气的化学方程式为：2KMnO4 =△= K2MnO4 + MnO2 + O2↑，其中△表示______。",
  None,
  "加热",
  "△ 是化学方程式中表示加热条件的符号。",
  0.4)

# kp_chem9_co2_properties
Q("kp_chem9_co2_properties", "choice", "mcq_single",
  "下列关于二氧化碳物理性质的叙述，错误的是（　　）",
  ["密度比空气大","能溶于水","无色无味","一般情况下不能支持燃烧"],
  "D",
  "D 描述的是化学性质（不支持燃烧），不是物理性质。",
  0.4)
Q("kp_chem9_co2_properties", "choice", "mcq_single",
  "将二氧化碳通入紫色石蕊试液中，溶液变红，其原因是（　　）",
  ["二氧化碳使石蕊变红","二氧化碳与水反应生成碳酸，碳酸使石蕊变红","二氧化碳有酸性","二氧化碳氧化了石蕊"],
  "B",
  "CO2 + H2O → H2CO3，碳酸显酸性使紫色石蕊试液变红。",
  0.45)
Q("kp_chem9_co2_properties", "fill", "fill_blank",
  "将澄清石灰水中通入二氧化碳，石灰水变浑浊，反应方程式为：CO2 + Ca(OH)2 =______。",
  None,
  "CaCO3↓ + H2O",
  "二氧化碳与氢氧化钙反应生成碳酸钙白色沉淀和水。",
  0.5)

# kp_chem9_carbon_allotropes
Q("kp_chem9_carbon_allotropes", "choice", "mcq_single",
  "下列物质中属于碳单质的是（　　）",
  ["一氧化碳","碳酸钙","金刚石","二氧化碳"],
  "C",
  "金刚石、石墨、C60 都是碳单质；CO、CO2、CaCO3 是含碳化合物。",
  0.32)
Q("kp_chem9_carbon_allotropes", "choice", "mcq_single",
  "金刚石和石墨物理性质差异很大的原因是（　　）",
  ["碳原子种类不同","碳原子排列方式不同","碳的化合价不同","分子大小不同"],
  "B",
  "金刚石和石墨都是碳单质，由同种元素组成，但碳原子排列方式不同导致物理性质差异很大。",
  0.5)
Q("kp_chem9_carbon_allotropes", "fill", "fill_blank",
  "由同种元素组成的不同单质称为______。金刚石、石墨、C60 都是碳的______。",
  None,
  "同素异形体；同素异形体",
  "同种元素形成不同单质的现象叫同素异形，对应单质互称同素异形体。",
  0.45)

# kp_chem9_co2_cycle
Q("kp_chem9_co2_cycle", "choice", "mcq_single",
  "下列过程中，能产生二氧化碳的是（　　）",
  ["植物光合作用","人和动物的呼吸作用","氢气在氧气中燃烧","电解水"],
  "B",
  "人和动物的呼吸作用消耗 O2、产生 CO2；植物光合作用消耗 CO2、产生 O2；氢气燃烧只生成水。",
  0.4)
Q("kp_chem9_co2_cycle", "choice", "mcq_single",
  "温室效应加剧的主要原因是（　　）",
  ["大气中 CO2 含量过多","空气中氧气增多","森林减少使吸碳减少（与 A 同时是原因）","A 与 B 共同作用"],
  "D",
  "温室效应加剧由大气中 CO2 等温室气体增多和森林吸收 CO2 减少共同作用造成。",
  0.5)
Q("kp_chem9_co2_cycle", "fill", "fill_blank",
  "大气中 CO2 含量过高会引起温室效应加剧。为减缓温室效应，可以采取的措施之一是______（任写一条合理措施）。",
  None,
  "植树造林（或减少化石燃料燃烧、开发新能源等）",
  "植树造林能增强光合作用吸收 CO2；减少化石燃料燃烧可减少 CO2 排放。",
  0.45)

# kp_chem9_carbon_monoxide
Q("kp_chem9_carbon_monoxide", "choice", "mcq_single",
  "下列关于一氧化碳的叙述，错误的是（　　）",
  ["CO 是无色无味的有毒气体","CO 难溶于水","CO 在空气中燃烧发出蓝色火焰","CO 能使澄清石灰水变浑浊"],
  "D",
  "D 错：CO 不能使澄清石灰水变浑浊（这是 CO2 的特性）。",
  0.45)
Q("kp_chem9_carbon_monoxide", "choice", "mcq_single",
  "下列场所中，需要张贴严禁烟火标志的是（　　）",
  ["面粉加工厂","公园","教室","图书馆"],
  "A",
  "面粉加工厂空气中混有可燃性粉尘，遇明火可能发生爆炸，应严禁烟火。",
  0.4)
Q("kp_chem9_carbon_monoxide", "fill", "fill_blank",
  "CO 还原氧化铜的化学方程式为：CuO + CO =△= Cu + CO2，其中 CO 是______剂（填氧化或还原）。",
  None,
  "还原",
  "CO 在反应中夺取 CuO 中的氧，被氧化，是还原剂。",
  0.5)

# kp_chem9_co2_lab_prep
Q("kp_chem9_co2_lab_prep", "choice", "mcq_single",
  "实验室制取二氧化碳常用的药品是（　　）",
  ["石灰石与稀硫酸","大理石（石灰石）与稀盐酸","碳酸钠与稀盐酸","木炭与氧气"],
  "B",
  "实验室通常用大理石（或石灰石）与稀盐酸反应制 CO2。CaCO3 + 2HCl = CaCl2 + H2O + CO2↑。",
  0.4)
Q("kp_chem9_co2_lab_prep", "choice", "mcq_single",
  "实验室制取 CO2 的发生装置可以与下列哪种气体的发生装置相同（　　）",
  ["用过氧化氢溶液和二氧化锰制氧气","加热高锰酸钾制氧气","加热氯酸钾制氧气","电解水制氧气"],
  "A",
  "用过氧化氢溶液制 O2、CaCO3 与盐酸制 CO2 都是固液常温型发生装置。",
  0.45)
Q("kp_chem9_co2_lab_prep", "fill", "fill_blank",
  "实验室用大理石与稀盐酸制 CO2，反应的化学方程式为：CaCO3 + 2HCl =______。",
  None,
  "CaCl2 + H2O + CO2↑",
  "CaCO3 与 HCl 反应生成氯化钙、水和二氧化碳。",
  0.45)

# kp_chem9_carbonates
Q("kp_chem9_carbonates", "choice", "mcq_single",
  "检验某白色固体是否是碳酸盐，应选用的试剂是（　　）",
  ["稀盐酸和澄清石灰水","稀硫酸和紫色石蕊","硝酸银溶液","氯化钡溶液"],
  "A",
  "碳酸盐与稀盐酸反应产生 CO2 气体，将气体通入澄清石灰水变浑浊，可证明含碳酸根。",
  0.5)
Q("kp_chem9_carbonates", "choice", "mcq_single",
  "下列物质中不属于碳酸盐的是（　　）",
  ["Na2CO3","CaCO3","NaHCO3","NaOH"],
  "D",
  "NaOH 是碱，不含碳酸根。NaHCO3 虽叫碳酸氢钠，但属于碳酸盐家族（含 CO3 2- 或 HCO3-）。",
  0.4)
Q("kp_chem9_carbonates", "fill", "fill_blank",
  "碳酸钙（CaCO3）的俗称有______和大理石。",
  None,
  "石灰石",
  "碳酸钙在自然界中存在形式：石灰石、大理石、白垩等。",
  0.4)

# kp_chem9_water_resources
Q("kp_chem9_water_resources", "choice", "mcq_single",
  "下列做法不利于节约用水的是（　　）",
  ["用淘米水浇花","及时关闭水龙头","工业用水循环使用","长时间不关水龙头刷牙"],
  "D",
  "A、B、C 都是节水措施。D 浪费水资源。",
  0.3)
Q("kp_chem9_water_resources", "choice", "mcq_single",
  "地球表面约有 71% 被水覆盖，但淡水只占其中很少一部分。下列关于水资源的说法正确的是（　　）",
  ["海水可以直接饮用","淡水资源分布不均，部分地区严重缺水","浪费水资源不严重","冰川水也是咸水"],
  "B",
  "海水不能直接饮用；淡水资源分布不均；浪费水严重；冰川水是淡水。",
  0.35)
Q("kp_chem9_water_resources", "fill", "fill_blank",
  "爱护水资源一方面需要节约用水，另一方面需要______。",
  None,
  "防治水体污染",
  "爱护水资源的两条主要途径：节约用水、防治水体污染。",
  0.32)

# kp_chem9_water_purification
Q("kp_chem9_water_purification", "choice", "mcq_single",
  "下列净化水的操作中，净化程度最高的是（　　）",
  ["静置沉淀","过滤","吸附","蒸馏"],
  "D",
  "蒸馏得到的水是几乎纯净的水，净化程度最高。",
  0.35)
Q("kp_chem9_water_purification", "choice", "mcq_single",
  "区分硬水和软水常用的试剂是（　　）",
  ["肥皂水","澄清石灰水","食盐水","蒸馏水"],
  "A",
  "加入肥皂水后，泡沫多的是软水，泡沫少且有浮渣的是硬水。",
  0.4)
Q("kp_chem9_water_purification", "fill", "fill_blank",
  "硬水软化常用的方法是______和煮沸（家庭）。",
  None,
  "蒸馏（或离子交换法）",
  "实验室和工业上常用蒸馏法软化硬水；家庭中可用煮沸法。",
  0.4)

# kp_chem9_solution_concept
Q("kp_chem9_solution_concept", "choice", "mcq_single",
  "下列物质中不属于溶液的是（　　）",
  ["蔗糖水","汽水","牛奶","碘酒"],
  "C",
  "牛奶是乳浊液，不属于溶液。蔗糖水、汽水、碘酒都是均一稳定的混合物，属于溶液。",
  0.4)
Q("kp_chem9_solution_concept", "choice", "mcq_single",
  "溶液的基本特征是（　　）",
  ["不均一、不稳定","均一、稳定","均一但不稳定","不均一但稳定"],
  "B",
  "溶液是均一、稳定的混合物。均一指各部分浓度相同；稳定指不出现沉淀。",
  0.35)
Q("kp_chem9_solution_concept", "fill", "fill_blank",
  "溶液中，溶质是以______（填分子或离子或分子或离子）的形式分散到溶剂中的。",
  None,
  "分子或离子",
  "溶质在溶剂中以分子或离子形式存在，如 NaCl 在水中以 Na+ 和 Cl- 形式分散。",
  0.45)

# kp_chem9_saturated_solution
Q("kp_chem9_saturated_solution", "choice", "mcq_single",
  "下列叙述中，正确的是（　　）",
  ["饱和溶液一定是浓溶液","不饱和溶液一定是稀溶液","同一温度下，相同溶质的饱和溶液比不饱和溶液浓","饱和溶液降温一定能析出晶体"],
  "C",
  "饱和溶液与浓稀无直接关系（氢氧化钙的饱和溶液是稀溶液）；降温不一定会析出晶体（如溶解度随温度升高而增大的物质降温才析出）。",
  0.55)
Q("kp_chem9_saturated_solution", "choice", "mcq_single",
  "使一瓶接近饱和的硝酸钾溶液变成饱和溶液，可采用的方法是（　　）",
  ["加水","升高温度","加入硝酸钾固体","降低温度或恒温蒸发溶剂"],
  "D",
  "硝酸钾溶解度随温度升高而显著增大，降温或恒温蒸发溶剂可使不饱和变饱和。",
  0.45)
Q("kp_chem9_saturated_solution", "fill", "fill_blank",
  "在______温度下，向一定量溶剂里加入某种溶质，当溶质不能继续溶解时，所得溶液叫做这种溶质的饱和溶液。",
  None,
  "一定",
  "饱和溶液定义需指明温度，因为同一溶质在不同温度下的溶解度不同。",
  0.4)

# kp_chem9_solubility_concept
Q("kp_chem9_solubility_concept", "choice", "mcq_single",
  "下列关于固体溶解度的叙述，正确的是（　　）",
  ["溶解度是指某物质在 100 g 溶剂里能溶解的最大质量","20℃时，硝酸钾的溶解度为 31.6 g，表示 20℃时 100 g 水中最多溶解 31.6 g 硝酸钾","溶解度单位是 g/mL","所有固体物质的溶解度都随温度升高而增大"],
  "B",
  "A 错（是 100 g 溶剂，不是 100 g 溶液）；C 错（单位 g，无体积单位）；D 错（如 Ca(OH)2 溶解度随温度升高而减小）。",
  0.55)
Q("kp_chem9_solubility_concept", "choice", "mcq_single",
  "下列物质中，溶解度随温度升高而减小的是（　　）",
  ["硝酸钾","氯化钠","氢氧化钙","蔗糖"],
  "C",
  "大多数固体物质溶解度随温度升高而增大，但氢氧化钙等少数固体随温度升高而减小。",
  0.5)
Q("kp_chem9_solubility_concept", "fill", "fill_blank",
  "气体的溶解度随温度升高而______，随压强增大而增大。",
  None,
  "减小",
  "气体溶解度与温度成反比，与压强成正比。",
  0.35)

# kp_chem9_crystal_methods
Q("kp_chem9_crystal_methods", "choice", "mcq_single",
  "下列混合物适合用结晶法分离的是（　　）",
  ["泥沙和水","硝酸钾和氯化钠（少量）","酒精和水","汽油和水"],
  "B",
  "硝酸钾和氯化钠都溶于水，但溶解度受温度影响差异大，可用结晶法分离（冷却热饱和溶液主要析出 KNO3）。",
  0.5)
Q("kp_chem9_crystal_methods", "choice", "mcq_single",
  "下列结晶方法中，适用于溶解度受温度影响较大的固体物质（如硝酸钾）的是（　　）",
  ["蒸发结晶","冷却热饱和溶液（降温结晶）","过滤","蒸馏"],
  "B",
  "硝酸钾溶解度随温度降低显著减小，应采用降温结晶。",
  0.45)
Q("kp_chem9_crystal_methods", "fill", "fill_blank",
  "从氯化钠溶液中获得氯化钠晶体应采用______结晶。",
  None,
  "蒸发",
  "NaCl 溶解度随温度变化不大，用蒸发结晶。",
  0.45)

# kp_chem9_mass_fraction
Q("kp_chem9_mass_fraction", "choice", "mcq_single",
  "将 25 g 氯化钠完全溶于 75 g 水中，所得溶液中氯化钠的质量分数为（　　）",
  ["25%","33.3%","75%","20%"],
  "A",
  "质量分数 = 溶质质量 / 溶液质量 × 100% = 25/(25+75) × 100% = 25%。",
  0.4)
Q("kp_chem9_mass_fraction", "choice", "mcq_single",
  "配制 100 g 质量分数为 10% 的氯化钠溶液，需要氯化钠和水的质量分别为（　　）",
  ["10 g 氯化钠，90 g 水","90 g 氯化钠，10 g 水","20 g 氯化钠，80 g 水","50 g 氯化钠，50 g 水"],
  "A",
  "NaCl 质量 = 100 g × 10% = 10 g；水质量 = 100 g - 10 g = 90 g。",
  0.35)
Q("kp_chem9_mass_fraction", "fill", "fill_blank",
  "溶质质量分数的计算公式：溶质质量分数 =______× 100%。",
  None,
  "溶质质量 ÷ 溶液质量",
  "质量分数 = 溶质质量 / 溶液质量 × 100%。",
  0.35)

# kp_chem9_solution_prep_lab
Q("kp_chem9_solution_prep_lab", "choice", "mcq_single",
  "配制一定溶质质量分数的氯化钠溶液，主要步骤为（　　）",
  ["计算、称量、溶解","称量、计算、溶解","溶解、计算、称量","计算、溶解、称量"],
  "A",
  "配制步骤：计算（所需溶质和溶剂的质量）→ 称量（用托盘天平）→ 量取（用量筒）→ 溶解（用烧杯和玻璃棒）。",
  0.35)
Q("kp_chem9_solution_prep_lab", "choice", "mcq_single",
  "配制 50 g 5% 的 NaCl 溶液时，下列仪器中不需要的是（　　）",
  ["托盘天平","量筒","烧杯","酒精灯"],
  "D",
  "配制溶液不需加热，故不需要酒精灯。",
  0.4)
Q("kp_chem9_solution_prep_lab", "fill", "fill_blank",
  "配制一定溶质质量分数溶液的步骤：______、称量、量取、溶解。",
  None,
  "计算",
  "配制溶液的第一步是先计算所需溶质和溶剂的质量或体积。",
  0.32)

# kp_chem9_solution_calc
Q("kp_chem9_solution_calc", "choice", "mcq_single",
  "把 100 g 20% 的 NaCl 溶液加水稀释成 100 g 10% 的 NaCl 溶液，需要加水的质量是（　　）",
  ["50 g","100 g","150 g","200 g"],
  "B",
  "稀释前后溶质质量不变：100 g × 20% = 20 g；要稀释为 10% 需总质量 = 20/10% = 200 g；需加水 200 - 100 = 100 g。",
  0.55)
Q("kp_chem9_solution_calc", "choice", "mcq_single",
  "100 g 10% NaCl 溶液与 100 g 20% NaCl 溶液混合，混合后溶液中 NaCl 的质量分数约为（　　）",
  ["10%","12%","15%","20%"],
  "C",
  "混合后 NaCl 总质量 = 100×10% + 100×20% = 30 g；总质量 = 200 g；质量分数 = 30/200 = 15%。",
  0.5)
Q("kp_chem9_solution_calc", "fill", "fill_blank",
  "稀释溶液时，稀释前后溶液中______的质量保持不变。",
  None,
  "溶质",
  "稀释原理：稀释前后溶质质量不变。",
  0.35)

# kp_chem9_metal_properties_alloy
Q("kp_chem9_metal_properties_alloy", "choice", "mcq_single",
  "下列关于金属共性的叙述，错误的是（　　）",
  ["常温下都是固体（汞除外）","大多数有金属光泽","都是良好的导体","延展性相同"],
  "D",
  "不同金属的延展性差异较大（如金延展性最好），不能说完全相同。",
  0.4)
Q("kp_chem9_metal_properties_alloy", "choice", "mcq_single",
  "下列关于合金的说法正确的是（　　）",
  ["合金一定是金属与金属熔合而成","合金的硬度一般比组成它的纯金属小","合金的熔点一般比组成它的纯金属低","钢是铁与碳的非金属化合物"],
  "C",
  "A 错（含碳合金常见）；B 错（硬度一般比纯金属大）；C 对；D 错（钢是铁碳合金）。",
  0.5)
Q("kp_chem9_metal_properties_alloy", "fill", "fill_blank",
  "合金是由一种金属跟其他一种或几种______（填金属或非金属）熔合而成的具有金属特性的物质。",
  None,
  "金属或非金属",
  "合金由金属与金属或金属与非金属熔合而成。",
  0.4)

# kp_chem9_metal_chemical
Q("kp_chem9_metal_chemical", "choice", "mcq_single",
  "下列金属在空气中不能与氧气反应的是（　　）",
  ["镁","铜","铝","锌"],
  "B",
  "常温下铜在空气中几乎不与氧气反应（加热生成氧化铜）。",
  0.4)
Q("kp_chem9_metal_chemical", "choice", "mcq_single",
  "下列金属与稀硫酸反应最剧烈的是（　　）",
  ["镁","锌","铁","铜"],
  "A",
  "金属活动性 Mg > Zn > Fe > Cu，金属越活泼，与酸反应越剧烈。",
  0.45)
Q("kp_chem9_metal_chemical", "fill", "fill_blank",
  "铝制品具有良好抗腐蚀性的原因是铝在空气中易与氧气反应，表面生成一层致密的______。",
  None,
  "氧化铝（Al2O3）薄膜",
  "铝表面生成的致密氧化铝薄膜能阻止铝进一步被氧化。",
  0.5)

# kp_chem9_metal_activity
Q("kp_chem9_metal_activity", "choice", "mcq_single",
  "金属活动性顺序中，铁（Fe）的位置在（　　）",
  ["锌之后、铜之前","铜之后、锌之前","铝之后、铜之前","镁之后、铜之前"],
  "D",
  "金属活动性顺序：K Ca Na Mg Al Zn Fe Sn Pb (H) Cu Hg Ag Pt Au。Fe 在 Mg 之后、Cu 之前。",
  0.4)
Q("kp_chem9_metal_activity", "choice", "mcq_single",
  "下列金属与稀盐酸不反应的是（　　）",
  ["铁","锌","铜","镁"],
  "C",
  "金属活动性顺序中 Cu 位于 H 之后，不能置换酸中的氢。",
  0.4)
Q("kp_chem9_metal_activity", "fill", "fill_blank",
  "判断金属 X 比 Y 活泼的实验依据之一：将 X 放入 Y 的______中，若 X 表面有 Y 析出，则 X 比 Y 活泼。",
  None,
  "盐溶液",
  "活泼金属能把不活泼金属从其盐溶液中置换出来。",
  0.5)

# kp_chem9_metal_experiment
Q("kp_chem9_metal_experiment", "choice", "mcq_single",
  "将铁片浸入硫酸铜溶液中，观察到的现象是（　　）",
  ["铁片表面有红色固体析出，溶液由蓝色变为浅绿色","无明显现象","铁片溶解并产生大量气泡","溶液变成红色"],
  "A",
  "Fe + CuSO4 → FeSO4 + Cu，铁片表面析出红色铜，溶液由蓝色（CuSO4）变成浅绿色（FeSO4）。",
  0.5)
Q("kp_chem9_metal_experiment", "choice", "mcq_single",
  "下列实验中，能比较镁和铁的金属活动性顺序的是（　　）",
  ["将镁条和铁片分别放入等量的稀盐酸中，观察产生气泡的快慢","将镁条和铁片放入硫酸铜溶液中","测量镁条和铁片的密度","观察镁条和铁片的光泽"],
  "A",
  "与酸反应剧烈程度可比较金属活动性，等量等浓度盐酸是控制变量。",
  0.5)
Q("kp_chem9_metal_experiment", "fill", "fill_blank",
  "铝丝浸入硫酸铜溶液中，铝丝表面有______色固体析出，溶液由蓝色变为无色。",
  None,
  "红色（铜）",
  "2Al + 3CuSO4 → Al2(SO4)3 + 3Cu，铝置换出铜。",
  0.55)

# kp_chem9_iron_smelting
Q("kp_chem9_iron_smelting", "choice", "mcq_single",
  "工业上炼铁的主要原料是（　　）",
  ["铁矿石、焦炭、石灰石","铜矿石、焦炭、石灰石","铝土矿、焦炭、石灰石","石灰石、焦炭、空气"],
  "A",
  "工业炼铁的原料：铁矿石（提供铁）、焦炭（提供热量和还原剂 CO）、石灰石（除脉石）。",
  0.4)
Q("kp_chem9_iron_smelting", "choice", "mcq_single",
  "工业上炼铁的主要反应原理是用还原剂 CO 还原铁矿石中的铁，主要反应为（　　）",
  ["3CO + Fe2O3 =高温= 2Fe + 3CO2","Fe2O3 + 3C =高温= 2Fe + 3CO","Fe2O3 + 3CO =高温= 2Fe + 3CO2","Fe2O3 =高温= 2Fe + O2↑"],
  "C",
  "工业炼铁的主要反应是 CO 还原氧化铁：Fe2O3 + 3CO →高温→ 2Fe + 3CO2。",
  0.5)
Q("kp_chem9_iron_smelting", "fill", "fill_blank",
  "工业炼铁中，焦炭的主要作用是提供热量和______（填还原剂或氧化剂）。",
  None,
  "还原剂",
  "焦炭燃烧产生 CO，CO 是主要还原剂。",
  0.4)

# kp_chem9_iron_rust
Q("kp_chem9_iron_rust", "choice", "mcq_single",
  "下列措施中，不能防止铁制品生锈的是（　　）",
  ["在铁制品表面镀锌","将铁制品放在潮湿处","在铁制品表面涂油","将铁制品表面烤蓝"],
  "B",
  "潮湿环境反而加速铁的锈蚀。",
  0.4)
Q("kp_chem9_iron_rust", "choice", "mcq_single",
  "铁生锈实际上是铁与______共同作用发生的反应（　　）",
  ["氧气","二氧化碳","水和氧气","氮气"],
  "C",
  "铁生锈是铁与水和氧气共同作用发生的缓慢氧化。",
  0.35)
Q("kp_chem9_iron_rust", "fill", "fill_blank",
  "防止铁制品生锈的原理主要是使铁与______隔绝。",
  None,
  "氧气和水（同时）",
  "隔绝氧气和水即可防止铁生锈。",
  0.4)

# kp_chem9_metal_image_calc
Q("kp_chem9_metal_image_calc", "choice", "mcq_single",
  "向等质量、等浓度的稀盐酸中分别加入等质量的镁和铁，反应结束后生成氢气的质量关系是（　　）",
  ["镁生成的多","铁生成的多","一样多","无法判断"],
  "A",
  "Mg + 2HCl → MgCl2 + H2↑；Fe + 2HCl → FeCl2 + H2↑。等质量镁和铁，Mg 的相对原子质量小、产生 H2 更多。",
  0.55)
Q("kp_chem9_metal_image_calc", "choice", "mcq_single",
  "向一定量的稀硫酸中加入足量的锌片，下列图像中能正确表示反应过程中溶液质量变化趋势的是（　　）",
  ["先减小后不变","先增大后不变","不变","无法确定"],
  "B",
  "Zn + H2SO4 → ZnSO4 + H2↑。每 65 g Zn 反应进入溶液，2 g H2 离开溶液，溶液质量增加直到反应结束。",
  0.55)
Q("kp_chem9_metal_image_calc", "fill", "fill_blank",
  "等质量、等浓度的稀硫酸分别与足量的铁和锌反应，生成氢气的质量______（填相同或不同）。",
  None,
  "相同",
  "足量金属时，氢气质量由酸决定。等量稀硫酸产生等量 H2。",
  0.5)

# kp_chem9_indicators
Q("kp_chem9_indicators", "choice", "mcq_single",
  "紫色石蕊试液遇酸性溶液变（　　）",
  ["蓝色","红色","无色","紫色"],
  "B",
  "酸性溶液使紫色石蕊变红，碱性溶液使紫色石蕊变蓝。",
  0.3)
Q("kp_chem9_indicators", "choice", "mcq_single",
  "下列溶液能使无色酚酞变红的是（　　）",
  ["稀盐酸","食盐水","石灰水","稀硫酸"],
  "C",
  "石灰水（Ca(OH)2 溶液）显碱性，能使酚酞变红。",
  0.4)
Q("kp_chem9_indicators", "fill", "fill_blank",
  "酸碱指示剂只能测定溶液的酸碱性，不能测定溶液的______。",
  None,
  "酸碱度（pH）",
  "酸碱指示剂只能粗略判断酸碱性，要测定 pH 应用 pH 试纸或 pH 计。",
  0.4)

# kp_chem9_acid_properties
Q("kp_chem9_acid_properties", "choice", "mcq_single",
  "稀释浓硫酸时，下列操作正确的是（　　）",
  ["将水沿器壁慢慢注入浓硫酸中，并不断搅拌","将浓硫酸沿器壁慢慢注入水中，并不断搅拌","将浓硫酸和水快速混合","把浓硫酸倒入量筒中稀释"],
  "B",
  "浓硫酸溶于水放出大量热，密度大易沉底。沿器壁慢慢注入水中并搅拌，散热均匀。",
  0.45)
Q("kp_chem9_acid_properties", "choice", "mcq_single",
  "下列物质中能与稀盐酸反应放出气体的是（　　）",
  ["铜","铁锈（Fe2O3·xH2O）","大理石（CaCO3）","氧化铜"],
  "C",
  "CaCO3 + 2HCl → CaCl2 + H2O + CO2↑，放出 CO2 气体。铁锈与盐酸反应但不放气体。",
  0.4)
Q("kp_chem9_acid_properties", "fill", "fill_blank",
  "稀盐酸和稀硫酸的化学性质相似，是因为它们的溶液中都含有相同的______离子。",
  None,
  "H+（氢离子）",
  "酸的通性源于溶液中的 H+。",
  0.4)

# kp_chem9_base_properties
Q("kp_chem9_base_properties", "choice", "mcq_single",
  "下列气体中，能使澄清石灰水变浑浊的是（　　）",
  ["氧气","二氧化碳","氢气","氮气"],
  "B",
  "CO2 + Ca(OH)2 → CaCO3↓ + H2O，石灰水变浑浊。",
  0.3)
Q("kp_chem9_base_properties", "choice", "mcq_single",
  "下列物质中，能与氢氧化钠溶液反应的是（　　）",
  ["氧化铜（CuO）","二氧化碳（CO2）","氯化钠（NaCl）","铜（Cu）"],
  "B",
  "2NaOH + CO2 → Na2CO3 + H2O，非金属氧化物与碱反应。",
  0.45)
Q("kp_chem9_base_properties", "fill", "fill_blank",
  "氢氧化钠俗名叫______、火碱或烧碱。",
  None,
  "苛性钠",
  "NaOH 俗称：苛性钠、火碱、烧碱。",
  0.35)

# kp_chem9_neutral_ph
Q("kp_chem9_neutral_ph", "choice", "mcq_single",
  "中和反应的实质是（　　）",
  ["H+ 和 OH- 结合生成水分子","酸和碱的反应","生成盐和水","放出热量"],
  "A",
  "中和反应实质是 H+ + OH- → H2O。",
  0.45)
Q("kp_chem9_neutral_ph", "choice", "mcq_single",
  "测定溶液 pH 的正确操作是（　　）",
  ["将 pH 试纸直接浸入待测液","用玻璃棒蘸取少量待测液滴在干燥的 pH 试纸上，将试纸显示的颜色与标准比色卡对照","将待测液滴在 pH 试纸上后，用水冲洗再对照","将 pH 试纸放在空气中观察"],
  "B",
  "pH 测定正确操作：玻璃棒蘸取待测液，滴在干燥 pH 试纸上，对照比色卡读数。",
  0.45)
Q("kp_chem9_neutral_ph", "fill", "fill_blank",
  "酸性溶液的 pH ______7，碱性溶液的 pH ______7（填大于、小于或等于）。",
  None,
  "小于；大于",
  "pH < 7 显酸性；pH = 7 显中性；pH > 7 显碱性。",
  0.4)

# kp_chem9_acid_base_lab
Q("kp_chem9_acid_base_lab", "choice", "mcq_single",
  "下列实验现象描述错误的是（　　）",
  ["稀盐酸与铁锈反应，溶液由无色变为黄色","稀硫酸与氧化铜反应，溶液由无色变为蓝色","氢氧化钠溶液与硫酸铜溶液反应生成蓝色沉淀","石灰水与稀盐酸反应生成白色沉淀"],
  "D",
  "D 错误：石灰水与盐酸反应生成 CaCl2 和 H2O，没有沉淀。",
  0.5)
Q("kp_chem9_acid_base_lab", "choice", "mcq_single",
  "向稀盐酸中加入几滴紫色石蕊试液，溶液变红；再逐滴加入 NaOH 溶液至恰好完全反应，溶液变为（　　）",
  ["蓝色","紫色","红色","无色"],
  "B",
  "恰好中和时溶液呈中性，石蕊在中性溶液中为紫色。",
  0.45)
Q("kp_chem9_acid_base_lab", "fill", "fill_blank",
  "稀盐酸与铁锈（主要成分 Fe2O3·xH2O）反应，溶液由无色变为______色。",
  None,
  "黄",
  "生成 FeCl3 显黄色。",
  0.4)

# kp_chem9_salt_common
Q("kp_chem9_salt_common", "choice", "mcq_single",
  "下列物质中，属于盐的是（　　）",
  ["HCl","NaOH","Na2CO3","H2SO4"],
  "C",
  "盐是由金属离子（或 NH4+）和酸根离子组成的化合物。Na2CO3 是盐。",
  0.35)
Q("kp_chem9_salt_common", "choice", "mcq_single",
  "下列用途中利用了 Na2CO3 性质的是（　　）",
  ["制玻璃","制纯碱不属于","洗涤油污","制烧碱不属于"],
  "A",
  "Na2CO3（纯碱）用途：制玻璃、洗涤剂、洗涤油污、纺织印染等。",
  0.4)
Q("kp_chem9_salt_common", "fill", "fill_blank",
  "碳酸钠 Na2CO3 俗称______，水溶液显______性（填酸、碱或中）。",
  None,
  "纯碱（或苏打）；碱",
  "Na2CO3 俗称纯碱或苏打，水溶液显碱性。",
  0.4)

# kp_chem9_double_decomp_cond
Q("kp_chem9_double_decomp_cond", "choice", "mcq_single",
  "下列复分解反应能发生的是（　　）",
  ["NaCl + KNO3 → NaNO3 + KCl","Na2CO3 + CaCl2 → CaCO3↓ + 2NaCl","HCl + Na2SO4 →","NaOH + KCl →"],
  "B",
  "复分解反应条件：生成物中有沉淀、气体或水之一。CaCO3 是沉淀，反应能发生。A 不生成沉淀气体水；C、D 同理。",
  0.55)
Q("kp_chem9_double_decomp_cond", "choice", "mcq_single",
  "下列各组物质能在水溶液中大量共存的是（　　）",
  ["NaOH 和 H2SO4","Na2CO3 和 HCl","NaCl 和 KNO3","BaCl2 和 Na2SO4"],
  "C",
  "A：中和；B：生成 CO2；D：生成 BaSO4 沉淀；C 无反应。",
  0.5)
Q("kp_chem9_double_decomp_cond", "fill", "fill_blank",
  "复分解反应发生的条件是：生成物中有______、气体或水三者之一。",
  None,
  "沉淀",
  "复分解反应条件：生成沉淀、气体或水。",
  0.4)

# kp_chem9_fertilizer
Q("kp_chem9_fertilizer", "choice", "mcq_single",
  "下列化肥中属于氮肥的是（　　）",
  ["K2SO4","Ca3(PO4)2","CO(NH2)2","KCl"],
  "C",
  "CO(NH2)2 是尿素，含 N，是氮肥。",
  0.4)
Q("kp_chem9_fertilizer", "choice", "mcq_single",
  "检验铵态氮肥（如 NH4Cl）时，下列操作正确的是（　　）",
  ["加 NaOH 溶液共热，将湿润的红色石蕊试纸放在试管口，若变蓝则含 NH4+","加盐酸看是否产生气体","加 AgNO3 溶液","直接加热"],
  "A",
  "NH4+ 与 OH- 共热放出 NH3，NH3 使湿润红色石蕊试纸变蓝。",
  0.5)
Q("kp_chem9_fertilizer", "fill", "fill_blank",
  "氮肥、磷肥、钾肥是三大化肥。含______（填 N、P 或 K）元素的化肥属于氮肥。",
  None,
  "N",
  "氮肥含氮元素（N）。",
  0.3)

# kp_chem9_ion_identity
Q("kp_chem9_ion_identity", "choice", "mcq_single",
  "检验某溶液中含有 SO4 2- 的正确方法是（　　）",
  ["加入 BaCl2 溶液产生白色沉淀，再加稀盐酸沉淀不溶解","加入稀盐酸产生气体","加入 AgNO3 溶液产生白色沉淀","加 NaOH 溶液产生红褐色沉淀"],
  "A",
  "SO4 2- + Ba2+ → BaSO4↓（白色，不溶于稀盐酸），可与 CO3 2-、Cl- 等干扰离子区别。",
  0.5)
Q("kp_chem9_ion_identity", "choice", "mcq_single",
  "检验某溶液中是否含有 Cl-，应选用的试剂是（　　）",
  ["稀盐酸","AgNO3 溶液和稀硝酸","BaCl2 溶液","紫色石蕊试液"],
  "B",
  "Cl- + Ag+ → AgCl↓（白色不溶于稀硝酸）。",
  0.45)
Q("kp_chem9_ion_identity", "fill", "fill_blank",
  "检验 CO3 2- 时，滴加稀盐酸产生气体，将气体通入______，若变浑浊，证明含 CO3 2-。",
  None,
  "澄清石灰水",
  "CO3 2- + 2H+ → H2O + CO2↑；CO2 + Ca(OH)2 → CaCO3↓ + H2O。",
  0.45)

# kp_chem9_naoh_deterioration
Q("kp_chem9_naoh_deterioration", "choice", "mcq_single",
  "下列情况中，NaOH 已变质的是（　　）",
  ["长期暴露在空气中的 NaOH 固体表面出现白色粉末","NaOH 溶液使酚酞变红","NaOH 溶解于水放出大量热","NaOH 与盐酸反应"],
  "A",
  "长期暴露的 NaOH 吸收 CO2 生成 Na2CO3 白色粉末，说明已变质。",
  0.45)
Q("kp_chem9_naoh_deterioration", "choice", "mcq_single",
  "检验 NaOH 是否部分变质的实验方案中，下列试剂最合适的是（　　）",
  ["稀盐酸","澄清石灰水","紫色石蕊","硝酸银溶液"],
  "B",
  "加 Ca(OH)2 产生白色沉淀说明含 Na2CO3；再加 Ca(OH)2 无现象（NaOH 与 Ca(OH)2 不反应，不能共存）。B 选合适。",
  0.55)
Q("kp_chem9_naoh_deterioration", "fill", "fill_blank",
  "NaOH 变质后生成的物质俗称______（填纯碱或石灰石）。",
  None,
  "纯碱",
  "NaOH 变质生成的 Na2CO3 俗称纯碱或苏打。",
  0.4)

# kp_chem9_substance_id
Q("kp_chem9_substance_id", "choice", "mcq_single",
  "除去 CO 中混有的少量 CO2，适宜的方法是（　　）",
  ["通过灼热的氧化铜","通过足量 NaOH 溶液","点燃","通过澄清石灰水"],
  "B",
  "CO2 + 2NaOH → Na2CO3 + H2O，CO 不反应，可除去 CO2。A 会消耗 CO；C 不能除 CO2；D 吸收量少不彻底。",
  0.5)
Q("kp_chem9_substance_id", "choice", "mcq_single",
  "除去 NaCl 固体中混有的少量 Na2CO3，可行的方法是（　　）",
  ["加适量稀盐酸后蒸发结晶","加水溶解后过滤","加水溶解后加 CaCl2 溶液过滤","加 NaOH 溶液"],
  "A",
  "加稀盐酸使 Na2CO3 转化为 NaCl：Na2CO3 + 2HCl → 2NaCl + H2O + CO2↑，然后蒸发结晶。",
  0.55)
Q("kp_chem9_substance_id", "fill", "fill_blank",
  "除去 NaCl 溶液中混有的 Na2SO4，可以加入适量______溶液，再过滤。",
  None,
  "BaCl2",
  "Na2SO4 + BaCl2 → BaSO4↓ + 2NaCl，过滤除去 BaSO4。",
  0.55)

# kp_chem9_property_method
Q("kp_chem9_property_method", "choice", "mcq_single",
  "认识物质性质的一般思路是（　　）",
  ["先观察颜色，再闻气味","先研究物理性质，再研究化学性质","先查阅文献，再做实验","任选一种方法"],
  "B",
  "认识物质性质常按物理性质→化学性质的顺序进行，便于系统掌握。",
  0.4)
Q("kp_chem9_property_method", "choice", "mcq_single",
  "下列研究中属于化学性质研究的是（　　）",
  ["测定水的密度","观察铁的颜色","比较食盐和白糖的溶解性","检验盐酸能否与铁反应"],
  "D",
  "A、B、C 都是物理性质；D 通过化学反应表现，是化学性质。",
  0.35)
Q("kp_chem9_property_method", "fill", "fill_blank",
  "物质不需要发生化学变化就能表现出来的性质叫做______性质。",
  None,
  "物理",
  "物理性质：颜色、状态、密度、熔点、沸点、硬度、溶解性等。",
  0.35)

# kp_chem9_chem_use_safety
Q("kp_chem9_chem_use_safety", "choice", "mcq_single",
  "下列做法中，符合化学品安全使用要求的是（　　）",
  ["浓硫酸沾到皮肤上立即涂 NaOH 中和","家用洁厕灵（盐酸）与 84 消毒液（次氯酸钠）混合使用增强效果","实验室里尝药品的味道","稀释浓硫酸时将浓硫酸沿器壁慢慢注入水中"],
  "D",
  "A：NaOH 强碱会腐蚀皮肤；B：会生成有毒氯气；C：严禁品尝；D 正确。",
  0.5)
Q("kp_chem9_chem_use_safety", "choice", "mcq_single",
  "下列图标中，表示腐蚀品标志的是（　　）",
  ["一个易燃符号","一个腐蚀符号（手和金属被腐蚀）","一个骷髅头","一个圆圈加斜杠"],
  "B",
  "腐蚀品标志：金属和手被腐蚀的图案。",
  0.4)
Q("kp_chem9_chem_use_safety", "fill", "fill_blank",
  "化学品的合理使用应做到：不滥用、不污染环境、不______（任写一条注意事项）。",
  None,
  "随意丢弃（如分类回收处理）",
  "化学品安全使用包括正确使用、妥善储存、分类处理等。",
  0.4)

# kp_chem9_phys_chem_properties
Q("kp_chem9_phys_chem_properties", "choice", "mcq_single",
  "下列性质中属于化学性质的是（　　）",
  ["水的沸点是 100℃","镁条能在空气中燃烧","金属能导电","氧气不易溶于水"],
  "B",
  "镁条燃烧是化学变化中表现的性质，属于化学性质。A、C、D 都是物理性质。",
  0.35)
Q("kp_chem9_phys_chem_properties", "choice", "mcq_single",
  "下列叙述中，前者属于物理性质，后者属于化学性质的是（　　）",
  ["铜能导电；铜能在潮湿空气中生成铜绿","铁的密度大；铁在氧气中燃烧","水是无色液体；水加热变成水蒸气","酒精易挥发；酒精能燃烧"],
  "D",
  "易挥发是物理性质，能燃烧是化学性质。A、B 顺序反；C 加热变化是物理变化。",
  0.55)
Q("kp_chem9_phys_chem_properties", "fill", "fill_blank",
  "物质在______变化中表现出来的性质叫做化学性质。",
  None,
  "化学",
  "化学性质通过化学变化表现，如可燃性、稳定性、氧化性等。",
  0.35)

# ===== Cluster 3: 物质的组成与结构 (28 KPs) =====

# kp_chem9_molecule_concept
Q("kp_chem9_molecule_concept", "choice", "mcq_single",
  "下列关于分子的叙述，错误的是（　　）",
  ["分子在不停地运动","分子之间有间隔","分子是保持化学性质的最小粒子","分子一定比原子大"],
  "D",
  "分子与原子的大小关系不能一概而论（如氢分子比许多原子小）。",
  0.5)
Q("kp_chem9_molecule_concept", "choice", "mcq_single",
  "用分子观点解释下列现象，其中错误的是（　　）",
  ["墙内开花墙外香——分子在不断运动","将 50 mL 水和 50 mL 酒精混合后体积小于 100 mL——分子之间有间隔","气体易压缩——分子很小","湿衣服晾干——分子在不断运动"],
  "C",
  "气体易压缩是因为分子之间间隔大，与分子大小无关。",
  0.5)
Q("kp_chem9_molecule_concept", "fill", "fill_blank",
  "分子是保持物质______性质的最小粒子。",
  None,
  "化学",
  "分子是保持化学性质的最小粒子（注意是化学性质）。",
  0.4)

# kp_chem9_atomic_structure
Q("kp_chem9_atomic_structure", "choice", "mcq_single",
  "原子的中心是原子核，下列关于原子核的叙述正确的是（　　）",
  ["原子核由质子和电子构成","原子核由质子和中子构成","原子核带负电","原子核由电子和中子构成"],
  "B",
  "原子核由质子（带正电）和中子（不带电）构成。",
  0.32)
Q("kp_chem9_atomic_structure", "choice", "mcq_single",
  "在原子中，下列关系正确的是（　　）",
  ["质子数 = 核外电子数","质子数 = 中子数","质子数 = 核电荷数 + 1","核外电子数 = 中子数"],
  "A",
  "原子中：核电荷数 = 质子数 = 核外电子数。中子数不一定等于质子数（存在同位素）。",
  0.4)
Q("kp_chem9_atomic_structure", "fill", "fill_blank",
  "原子由居于原子中心的带______电的原子核和核外带负电的电子构成。",
  None,
  "正",
  "原子核带正电（由质子和中子构成），电子带负电。",
  0.35)

# kp_chem9_relative_atomic_mass
Q("kp_chem9_relative_atomic_mass", "choice", "mcq_single",
  "相对原子质量的定义是（　　）",
  ["一个原子的实际质量","一个原子的质量与一种碳原子（碳-12）质量的 1/12 的比值","原子核质量","电子质量"],
  "B",
  "相对原子质量是以一个碳-12 原子质量的 1/12 为标准，其他原子的质量与它的比值，单位为 1。",
  0.4)
Q("kp_chem9_relative_atomic_mass", "choice", "mcq_single",
  "氧的相对原子质量约为 16，表示（　　）",
  ["一个氧原子的质量是 16 g","一个氧原子的质量是一个碳-12 原子质量 1/12 的 16 倍","氧原子的实际质量是 16","氧的相对原子质量单位是 g"],
  "B",
  "相对原子质量是比值，单位为 1，氧的相对原子质量约 16。",
  0.4)
Q("kp_chem9_relative_atomic_mass", "fill", "fill_blank",
  "相对原子质量的国际单位制符号是______（单位 1）。",
  None,
  "无（单位为 1，常省略）",
  "相对原子质量是无量纲量，单位为 1（常省略不写）。",
  0.4)

# kp_chem9_nucleus_electrons
Q("kp_chem9_nucleus_electrons", "choice", "mcq_single",
  "下列原子结构示意图中，最外层电子数为 8 的是（　　）",
  ["钠（Na）","镁（Mg）","氖（Ne）","铝（Al）"],
  "C",
  "Na、Mg、Al 最外层电子数分别为 1、2、3，氖最外层 8 个电子为稳定结构。",
  0.4)
Q("kp_chem9_nucleus_electrons", "choice", "mcq_single",
  "下列关于核外电子排布的叙述，正确的是（　　）",
  ["电子排布无规律","第一层最多容纳 2 个电子，第二层最多 8 个","最外层电子数一定大于 8","最外层电子数小于 4 的一定是金属"],
  "B",
  "A 错（有规律）；C 错（最外层电子数最多 8，第一层为最外层时为 2）；D 错（H 最外层 1 是非金属）。",
  0.5)
Q("kp_chem9_nucleus_electrons", "fill", "fill_blank",
  "原子结构示意图中，弧线表示______，弧线上的数字表示该层上的电子数。",
  None,
  "电子层",
  "原子结构示意图中的弧线代表不同的电子层。",
  0.4)

# kp_chem9_outermost_property
Q("kp_chem9_outermost_property", "choice", "mcq_single",
  "元素的化学性质主要决定于原子的（　　）",
  ["最外层电子数","核内质子数","核内中子数","原子核大小"],
  "A",
  "元素的化学性质主要由原子最外层电子数决定。",
  0.3)
Q("kp_chem9_outermost_property", "choice", "mcq_single",
  "下列原子中，最外层电子数最少的是（　　）",
  ["氢（H）","氦（He）","锂（Li）","铍（Be）"],
  "C",
  "H 最外层 1 个电子但 K 层只能容纳 2 个；He 2 个；Li 最外层 1 个但 K 层可容 2 仍稳定。Li 最外层 1。",
  0.5)
Q("kp_chem9_outermost_property", "fill", "fill_blank",
  "一般来说，最外层电子数少于 4 的原子在化学反应中易______电子，形成稳定结构。",
  None,
  "失去",
  "金属原子最外层电子数少于 4，反应中易失去电子形成阳离子。",
  0.4)

# kp_chem9_ion_concept
Q("kp_chem9_ion_concept", "choice", "mcq_single",
  "下列符号中表示钠离子的是（　　）",
  ["Na","Na+","Na2+","N a"],
  "B",
  "离子符号：电荷数标在右上角，数字在前，正负号在后。钠离子为 Na+。",
  0.32)
Q("kp_chem9_ion_concept", "choice", "mcq_single",
  "下列关于离子的说法错误的是（　　）",
  ["阳离子带正电，阴离子带负电","离子也是构成物质的一种粒子","离子中质子数一定等于核外电子数","离子所带电荷数与该原子得失电子数有关"],
  "C",
  "C 错：离子中质子数不等于核外电子数。",
  0.4)
Q("kp_chem9_ion_concept", "fill", "fill_blank",
  "带电的______（填原子或原子团）叫做离子。",
  None,
  "原子或原子团",
  "离子是带电的原子或原子团。",
  0.35)

# kp_chem9_ion_groups
Q("kp_chem9_ion_groups", "choice", "mcq_single",
  "下列原子团中，名称为氢氧根的是（　　）",
  ["NO3-","SO4 2-","OH-","CO3 2-"],
  "C",
  "OH- 是氢氧根，NO3- 是硝酸根，SO4 2- 是硫酸根，CO3 2- 是碳酸根。",
  0.32)
Q("kp_chem9_ion_groups", "choice", "mcq_single",
  "下列化学式中含有两种原子团的是（　　）",
  ["NaOH","KNO3","NH4NO3","CaCO3"],
  "C",
  "NH4NO3 含 NH4+（铵根）和 NO3-（硝酸根）。",
  0.45)
Q("kp_chem9_ion_groups", "fill", "fill_blank",
  "化学式中，硫酸根的符号是______（填离子符号）。",
  None,
  "SO4 2-",
  "硫酸根离子：SO4 2-。",
  0.3)

# kp_chem9_molecule_atom_relation
Q("kp_chem9_molecule_atom_relation", "choice", "mcq_single",
  "下列关于分子和原子的叙述，错误的是（　　）",
  ["分子由原子构成","原子可以直接构成物质","分子一定比原子大","化学变化的实质是分子分裂为原子，原子重新组合"],
  "C",
  "分子和原子大小无绝对大小关系。",
  0.45)
Q("kp_chem9_molecule_atom_relation", "choice", "mcq_single",
  "下列变化中，分子本身发生改变的是（　　）",
  ["水受热变成水蒸气","糖溶于水","水通电分解生成氢气和氧气","酒精挥发"],
  "C",
  "C 中水分子分解为氢原子和氧原子，再组合成氢分子和氧分子，分子本身改变。",
  0.4)
Q("kp_chem9_molecule_atom_relation", "fill", "fill_blank",
  "化学变化的微观本质是：分子分裂成原子，原子______（重新组合成新分子或直接构成新物质）。",
  None,
  "重新组合",
  "化学变化微观本质：分子分解，原子重组。",
  0.4)

# kp_chem9_element_concept
Q("kp_chem9_element_concept", "choice", "mcq_single",
  "下列说法中正确的是（　　）",
  ["水是由氢气和氧气组成的","水是由氢元素和氧元素组成的","水是由两个氢原子和一个氧原子构成的","水是由氢分子和氧原子构成的"],
  "B",
  "水由氢元素和氧元素组成，宏观描述元素；微观由水分子构成，每个水分子由 2 个氢原子和 1 个氧原子构成。",
  0.45)
Q("kp_chem9_element_concept", "choice", "mcq_single",
  "地壳中含量最多的金属元素是（　　）",
  ["氧","硅","铝","铁"],
  "C",
  "地壳中元素含量由多到少：O、Si、Al、Fe。Al 是地壳中含量最多的金属元素。",
  0.32)
Q("kp_chem9_element_concept", "fill", "fill_blank",
  "元素是______（填一类原子或单质）原子的总称，元素只讲种类，不讲个数。",
  None,
  "一类",
  "元素是质子数（即核电荷数）相同的一类原子的总称。",
  0.4)

# kp_chem9_element_symbols
Q("kp_chem9_element_symbols", "choice", "mcq_single",
  "下列元素符号书写正确的是（　　）",
  ["铜：Cu","镁：mg","铁：FE","钙：ca"],
  "A",
  "元素符号书写规则：一大二小。镁应写 Mg，铁写 Fe，钙写 Ca。",
  0.32)
Q("kp_chem9_element_symbols", "choice", "mcq_single",
  "下列符号中，既表示一种元素又表示一个原子的是（　　）",
  ["H2","O","H2O","2H"],
  "B",
  "元素符号 O 既表示氧元素，又表示一个氧原子。H2 表示氢气（1 个氢分子）；2H 表示 2 个氢原子。",
  0.4)
Q("kp_chem9_element_symbols", "fill", "fill_blank",
  "元素符号 H 表示______（填氢元素或氢气或两者之一）。",
  None,
  "氢元素，又表示一个氢原子",
  "元素符号既表示一种元素，又表示这种元素的一个原子。",
  0.4)

# kp_chem9_periodic_table_apps
Q("kp_chem9_periodic_table_apps", "choice", "mcq_single",
  "元素周期表中，每一横行称为一个（　　）",
  ["周期","族","区","格"],
  "A",
  "元素周期表：横向为周期（共 7 个周期），纵向为族。",
  0.32)
Q("kp_chem9_periodic_table_apps", "choice", "mcq_single",
  "在元素周期表中，金属元素与非金属元素的分界线附近能找到（　　）",
  ["人畜无害的元素","常温下为气体的元素","半导体材料","稀有气体"],
  "C",
  "分界线附近的元素如 Si、Ge 等常用作半导体材料。",
  0.5)
Q("kp_chem9_periodic_table_apps", "fill", "fill_blank",
  "在元素周期表中，每一纵行称为一个______（除 8、9、10 三列外）。",
  None,
  "族",
  "元素周期表中纵行称为族（8、9、10 三列合称Ⅷ族）。",
  0.35)

# kp_chem9_periodic_table_history
Q("kp_chem9_periodic_table_history", "choice", "mcq_single",
  "发现元素周期律并编制第一张元素周期表的科学家是（　　）",
  ["拉瓦锡","道尔顿","门捷列夫","阿伏伽德罗"],
  "C",
  "门捷列夫于 1869 年发现元素周期律并编制了第一张元素周期表。",
  0.32)
Q("kp_chem9_periodic_table_history", "choice", "mcq_single",
  "门捷列夫预言的类铝、类硅、类硼等元素后来被分别发现为（　　）",
  ["Li、Si、B","Ga、Ge、Sc","Ga、Ge、Si","Sc、Ge、Ga"],
  "B",
  "门捷列夫预言的类硼=钪、类铝=镓、类硅=锗。",
  0.5)
Q("kp_chem9_periodic_table_history", "fill", "fill_blank",
  "元素周期律的发现，使化学研究从______（任写一个特点）走向系统化。",
  None,
  "零散的事实",
  "元素周期律发现使零散的化学知识系统化。",
  0.4)

# kp_chem9_element_health
Q("kp_chem9_element_health", "choice", "mcq_single",
  "下列元素中，人体缺乏会引起骨质疏松的是（　　）",
  ["铁","碘","钙","锌"],
  "C",
  "钙是构成骨骼和牙齿的重要元素，缺乏会引起骨质疏松。",
  0.32)
Q("kp_chem9_element_health", "choice", "mcq_single",
  "下列关于人体必需元素的叙述，错误的是（　　）",
  ["缺铁会引起贫血","缺碘会引起甲状腺肿大","缺锌会引起食欲不振、发育不良","氟摄入越多越好"],
  "D",
  "D 错误：氟过量会引起氟斑牙等，过多有害。",
  0.4)
Q("kp_chem9_element_health", "fill", "fill_blank",
  "人体缺______（填元素名称）会引起贫血。",
  None,
  "铁",
  "铁是合成血红蛋白的重要元素，缺铁会引起缺铁性贫血。",
  0.3)

# kp_chem9_valence
Q("kp_chem9_valence", "choice", "mcq_single",
  "下列化合物中，硫元素化合价为 +6 的是（　　）",
  ["H2S","SO2","SO3","S"],
  "C",
  "SO3 中 O 为 -2，3 个 O 共 -6，所以 S 为 +6。",
  0.4)
Q("kp_chem9_valence", "choice", "mcq_single",
  "下列说法正确的是（　　）",
  ["单质中元素化合价为零","化合物中所有元素化合价都正","化合物中所有元素化合价之和为零","非金属元素化合价都为负"],
  "A",
  "B 错（如 CO2 中 C 为 +4）；C 错（化合物中各元素化合价代数和为零）；D 错（如 H 在 HCl 中为 +1）。",
  0.45)
Q("kp_chem9_valence", "fill", "fill_blank",
  "在化合物里，氢元素通常显______价，氧元素通常显 -2 价。",
  None,
  "+1",
  "H 在化合物中通常为 +1 价（除 NaH 等外）。",
  0.35)

# kp_chem9_formula_writing
Q("kp_chem9_formula_writing", "choice", "mcq_single",
  "下列化学式书写正确的是（　　）",
  ["氧化铝 AlO","氧化钠 NaO","氯化镁 MgCl2","氯化铁 FeCl2"],
  "C",
  "Al 显 +3、O 显 -2：Al2O3；Na 显 +1：Na2O；Fe 显 +3：FeCl3。",
  0.5)
Q("kp_chem9_formula_writing", "choice", "mcq_single",
  "下列物质名称与化学式一致的是（　　）",
  ["氧化钙 CaO2","氯化锌 ZnCl","硫酸铁 FeSO4","氢氧化钠 NaOH"],
  "D",
  "CaO（不是 CaO2）；ZnCl2；Fe2(SO4)3（铁+3）。",
  0.5)
Q("kp_chem9_formula_writing", "fill", "fill_blank",
  "书写化学式时，正价元素一般写在______（填左或右），负价元素写在右。",
  None,
  "左",
  "化学式书写：正价左，负价右。",
  0.35)

# kp_chem9_symbols_meaning
Q("kp_chem9_symbols_meaning", "choice", "mcq_single",
  "化学符号 2H2O 表示（　　）",
  ["2 个氢分子","2 个水分子","4 个氢原子","2 个氧分子"],
  "B",
  "2H2O：系数 2 表示 2 个水分子；每个水分子含 2 个氢原子。",
  0.4)
Q("kp_chem9_symbols_meaning", "choice", "mcq_single",
  "下列符号中，表示 3 个氢原子的是（　　）",
  ["3H2","H3","3H","3H2O"],
  "C",
  "3H 表示 3 个氢原子；3H2 表示 3 个氢分子。",
  0.35)
Q("kp_chem9_symbols_meaning", "fill", "fill_blank",
  "化学式 H2O 中右下角的 2 表示每个水分子中含有______个氢原子。",
  None,
  "2",
  "化学式中元素符号右下角的数字表示每个分子中该原子的个数。",
  0.3)

# kp_chem9_composition_description
Q("kp_chem9_composition_description", "choice", "mcq_single",
  "下列关于物质的组成和构成的描述中，正确的是（　　）",
  ["水是由氢气和氧气组成的","水分子是由氢元素和氧元素组成的","水是由水分子构成的，每个水分子由 2 个氢原子和 1 个氧原子构成","水分子由 2 个氢元素和 1 个氧元素构成"],
  "C",
  "A 错（元素组成不用物质名词）；B 错（分子是微观粒子，由原子构成）；D 错（元素不讲个数）。",
  0.5)
Q("kp_chem9_composition_description", "choice", "mcq_single",
  "宏观描述：水是由______组成的；微观描述：水是由______构成的。",
  ["氢元素和氧元素；水分子","氢气和氧气；水原子","氢和氧；水","水分子；氢元素"],
  "A",
  "宏观：物质由元素组成；微观：物质由分子、原子、离子构成。",
  0.45)
Q("kp_chem9_composition_description", "fill", "fill_blank",
  "宏观上，二氧化碳是由碳元素和______组成的；微观上，每个二氧化碳分子由 1 个碳原子和 2 个氧原子______。",
  None,
  "氧元素；构成",
  "宏观讲元素组成；微观讲分子构成。",
  0.4)

# kp_chem9_relative_molecular_mass
Q("kp_chem9_relative_molecular_mass", "choice", "mcq_single",
  "H2SO4 的相对分子质量是（　　）",
  ["49","82","98","100"],
  "C",
  "H2SO4 = 1×2 + 32 + 16×4 = 2 + 32 + 64 = 98。",
  0.4)
Q("kp_chem9_relative_molecular_mass", "choice", "mcq_single",
  "硝酸铵 NH4NO3 中氮元素的质量分数约为（　　）",
  ["17.7%","35%","45%","50%"],
  "B",
  "NH4NO3 相对分子质量 = 14×2 + 1×4 + 16×3 = 80；氮元素质量分数 = 28/80 = 35%。",
  0.55)
Q("kp_chem9_relative_molecular_mass", "fill", "fill_blank",
  "化合物中某元素的质量分数 =（该元素的相对原子质量 × 原子个数）÷______× 100%。",
  None,
  "相对分子质量",
  "元素质量分数 = 元素质量 / 化合物相对分子质量 × 100%。",
  0.4)

# kp_chem9_particle_models
Q("kp_chem9_particle_models", "choice", "mcq_single",
  "下列微观示意图中，能表示水分子的是（　　）",
  ["一个圆圈","两个相同的圆圈","一个圆圈和一个稍大的圆圈","三个相同的圆圈"],
  "B",
  "水分子（H2O）由 2 个 H 原子和 1 个 O 原子构成。如果圆圈大小相同则不能区分 H 和 O。常见表示为两个小圆加一个大圆，或三原子结构。",
  0.5)
Q("kp_chem9_particle_models", "choice", "mcq_single",
  "在下列微观示意图中，● 表示氧原子，○ 表示氢原子，能表示过氧化氢（H2O2）分子的是（　　）",
  ["○○","●○○","●○●","○●○"],
  "C",
  "H2O2 由 2 个 H 原子和 2 个 O 原子交替排列：H-O-O-H，对应 ●○●。",
  0.55)
Q("kp_chem9_particle_models", "fill", "fill_blank",
  "用微观示意图表示物质时，不同的______（填原子或原子团）用不同的大小或颜色加以区分。",
  None,
  "原子",
  "微观示意图中不同原子用不同大小或颜色区分。",
  0.4)

# kp_chem9_chemical_change_particle
Q("kp_chem9_chemical_change_particle", "choice", "mcq_single",
  "化学变化的微观本质是（　　）",
  ["分子间隔改变","原子重新组合","分子运动加快","分子数目改变"],
  "B",
  "化学变化的微观本质是原子的重新组合（分子分裂为原子，原子重新组合成新分子）。",
  0.4)
Q("kp_chem9_chemical_change_particle", "choice", "mcq_single",
  "在化学变化中，下列说法正确的是（　　）",
  ["分子可分，原子不可分","分子不可分，原子可分","分子和原子都可分","分子和原子都不可分"],
  "A",
  "化学变化中分子可分，原子不可再分（是化学变化中的最小粒子）。",
  0.4)
Q("kp_chem9_chemical_change_particle", "fill", "fill_blank",
  "化学变化中，分子分裂成原子，原子______（填重新组合或消失）成新的分子或直接构成新物质。",
  None,
  "重新组合",
  "化学变化中原子不灭，只是重新组合成新分子。",
  0.35)

# kp_chem9_pure_mixture
Q("kp_chem9_pure_mixture", "choice", "mcq_single",
  "下列物质中属于纯净物的是（　　）",
  ["海水","洁净的空气","冰水混合物","石油"],
  "C",
  "冰和水是同一种物质（H2O），是纯净物。海水中含有 NaCl 等多种物质，是混合物。",
  0.35)
Q("kp_chem9_pure_mixture", "choice", "mcq_single",
  "下列物质中属于混合物的是（　　）",
  ["蒸馏水","高锰酸钾","石灰石","液氧"],
  "C",
  "石灰石主要含 CaCO3，还含其他杂质，是混合物。",
  0.35)
Q("kp_chem9_pure_mixture", "fill", "fill_blank",
  "由同种物质组成的称为______，由不同种物质组成的称为______。",
  None,
  "纯净物；混合物",
  "物质按组成成分的种类可分为纯净物和混合物。",
  0.3)

# kp_chem9_element_compound_oxide
Q("kp_chem9_element_compound_oxide", "choice", "mcq_single",
  "下列物质中属于化合物的是（　　）",
  ["氧气","氢气","二氧化碳","空气"],
  "C",
  "化合物是由不同种元素组成的纯净物。CO2 由 C 和 O 两种元素组成，是化合物。",
  0.32)
Q("kp_chem9_element_compound_oxide", "choice", "mcq_single",
  "下列物质中属于氧化物的是（　　）",
  ["O2","KMnO4","H2O","HCl"],
  "C",
  "氧化物是由两种元素组成且其中一种是氧元素的化合物。H2O 符合；KMnO4 是含氧化合物但有三种元素；HCl 不含氧。",
  0.4)
Q("kp_chem9_element_compound_oxide", "fill", "fill_blank",
  "由______（填同或不同）种元素组成的纯净物叫做化合物。",
  None,
  "不同",
  "化合物由不同种元素组成的纯净物（区别于单质）。",
  0.3)

# kp_chem9_matter_constituent
Q("kp_chem9_matter_constituent", "choice", "mcq_single",
  "下列物质由分子构成的是（　　）",
  ["铁","氯化钠","水","金刚石"],
  "C",
  "水由水分子构成；铁、金刚石由原子构成；氯化钠由 Na+ 和 Cl- 构成。",
  0.35)
Q("kp_chem9_matter_constituent", "choice", "mcq_single",
  "下列物质由离子构成的是（　　）",
  ["铜","二氧化碳","氯化钾","氧气"],
  "C",
  "KCl 是离子化合物，由 K+ 和 Cl- 构成。",
  0.4)
Q("kp_chem9_matter_constituent", "fill", "fill_blank",
  "构成物质的微粒有三种：分子、______和离子。",
  None,
  "原子",
  "分子、原子、离子是构成物质的三种基本微粒。",
  0.3)

# kp_chem9_solution_particle
Q("kp_chem9_solution_particle", "choice", "mcq_single",
  "氯化钠溶于水时，发生的微观过程主要是（　　）",
  ["NaCl 分子扩散到水中","Na+ 和 Cl- 扩散到水中","水分子分解","NaCl 分解为 Na 和 Cl"],
  "B",
  "NaCl 是离子化合物，溶于水时 Na+ 和 Cl- 在水分子的作用下扩散到水中形成自由移动的离子。",
  0.5)
Q("kp_chem9_solution_particle", "choice", "mcq_single",
  "蔗糖溶于水时，蔗糖以（　　）形式分散到水中",
  ["蔗糖分子","蔗糖离子","蔗糖原子","蔗酸根"],
  "A",
  "蔗糖是共价化合物，溶于水以蔗糖分子形式分散。",
  0.4)
Q("kp_chem9_solution_particle", "fill", "fill_blank",
  "溶液中能自由移动的粒子越多，溶液的导电性一般越______（填强或弱）。",
  None,
  "强",
  "溶液中自由移动的离子浓度越大，导电能力越强。",
  0.4)

# kp_chem9_electrolysis_water
Q("kp_chem9_electrolysis_water", "choice", "mcq_single",
  "电解水实验中，正极产生的气体是（　　）",
  ["氧气","氢气","氮气","二氧化碳"],
  "B",
  "电解水正极产生 O2，负极产生 H2。",
  0.3)
Q("kp_chem9_electrolysis_water", "choice", "mcq_single",
  "电解水实验得出的结论，正确的是（　　）",
  ["水由氢气和氧气组成","水由氢元素和氧元素组成","水是一种化合物","B 和 C 都对"],
  "D",
  "电解水生成 H2 和 O2，说明水由氢、氧两种元素组成，是化合物。",
  0.45)
Q("kp_chem9_electrolysis_water", "fill", "fill_blank",
  "电解水的化学方程式为：2H2O =通电= 2H2↑ + O2↑。其中反应物是______。",
  None,
  "水（H2O）",
  "电解水的反应物是水，生成物是氢气和氧气。",
  0.4)

# kp_chem9_electrolysis_calc
Q("kp_chem9_electrolysis_calc", "choice", "mcq_single",
  "电解 36 g 水，理论上可生成氢气和氧气的质量分别为（　　）",
  ["2 g、16 g","4 g、32 g","6 g、48 g","8 g、64 g"],
  "B",
  "电解水质量比 m(H2):m(O2)= 1:8。设 H2 质量为 x，则 O2 = 8x；x + 8x = 36；x = 4 g，O2 = 32 g。",
  0.55)
Q("kp_chem9_electrolysis_calc", "choice", "mcq_single",
  "电解水产生的氢气和氧气的体积比约为（　　）",
  ["1:1","1:2","2:1","8:1"],
  "C",
  "在相同条件下，氢气与氧气体积比为 2:1。",
  0.4)
Q("kp_chem9_electrolysis_calc", "fill", "fill_blank",
  "电解水实验中，正极产生的氧气与负极产生的氢气的体积比约为______。",
  None,
  "1:2",
  "电解水正极 O2 : 负极 H2 体积比 = 1:2。",
  0.35)

# kp_chem9_atom_model_history
Q("kp_chem9_atom_model_history", "choice", "mcq_single",
  "提出原子论的科学家是（　　）",
  ["道尔顿","汤姆森","卢瑟福","玻尔"],
  "A",
  "道尔顿于 1803 年提出近代原子学说。",
  0.4)
Q("kp_chem9_atom_model_history", "choice", "mcq_single",
  "发现电子，并提出汤姆森枣糕模型的科学家是（　　）",
  ["道尔顿","汤姆森","卢瑟福","玻尔"],
  "B",
  "汤姆森在阴极射线实验中发现了电子，并提出枣糕式原子模型。",
  0.4)
Q("kp_chem9_atom_model_history", "fill", "fill_blank",
  "卢瑟福通过______（α 粒子散射实验）实验提出了原子的核式结构模型。",
  None,
  "α 粒子轰击金箔",
  "卢瑟福用 α 粒子轰击金箔，得出原子核式结构模型。",
  0.45)

# kp_chem9_structure_method
Q("kp_chem9_structure_method", "choice", "mcq_single",
  "认识物质结构的方法有（　　）",
  ["通过化学实验和科学探测","仅靠猜想","仅靠背诵","凭直觉"],
  "A",
  "认识物质结构需要通过化学实验和近代物理探测等科学方法。",
  0.35)
Q("kp_chem9_structure_method", "choice", "mcq_single",
  "下列说法不正确的是（　　）",
  ["原子由原子核和核外电子构成","原子核由质子和中子构成","分子由原子构成","电子是带正电的粒子"],
  "D",
  "D 错：电子带负电。",
  0.3)
Q("kp_chem9_structure_method", "fill", "fill_blank",
  "物质结构的研究方法是：通过化学实验和______（如 X 射线衍射）等手段认识物质的微观结构。",
  None,
  "科学探测",
  "研究物质结构需要化学实验和现代科学探测手段。",
  0.4)

# ===== Cluster 4: 物质的化学变化 (31 KPs) =====

# kp_chem9_phys_chem_change
Q("kp_chem9_phys_chem_change", "choice", "mcq_single",
  "下列变化中属于化学变化的是（　　）",
  ["冰雪融化","蜡烛燃烧","水沸腾","玻璃破碎"],
  "B",
  "蜡烛燃烧生成 CO2 和 H2O，有新物质生成，是化学变化。",
  0.3)
Q("kp_chem9_phys_chem_change", "choice", "mcq_single",
  "下列变化中，前者是物理变化后者是化学变化的是（　　）",
  ["湿衣服晾干；食物腐烂","铁生锈；酒精挥发","蜡烛燃烧；冰雪融化","水结冰；火药爆炸"],
  "A",
  "A 中前者是水蒸发（物理变化），后者是缓慢氧化（化学变化）。",
  0.45)
Q("kp_chem9_phys_chem_change", "fill", "fill_blank",
  "化学变化和物理变化的本质区别是：______（填是否生成新物质）。",
  None,
  "是否生成新物质",
  "化学变化有新物质生成；物理变化没有新物质生成。",
  0.32)

# kp_chem9_quality_conservation
Q("kp_chem9_quality_conservation", "choice", "mcq_single",
  "质量守恒定律的微观本质是（　　）",
  ["反应前后分子总数不变","反应前后原子种类、数目和质量都不变","反应前后元素种类不变","反应前后物质种类不变"],
  "B",
  "质量守恒的微观本质：反应前后原子的种类、数目、质量都不变。",
  0.45)
Q("kp_chem9_quality_conservation", "choice", "mcq_single",
  "根据质量守恒定律，反应 2H2 + O2 =点燃= 2H2O 中，若消耗 4 g 氢气和 32 g 氧气，则生成水的质量为（　　）",
  ["32 g","34 g","36 g","38 g"],
  "C",
  "根据质量守恒，生成水的质量 = 4 g + 32 g = 36 g。",
  0.4)
Q("kp_chem9_quality_conservation", "fill", "fill_blank",
  "质量守恒定律：参加化学反应的各物质的______（填总质量或总体积）等于反应后生成的各物质的总质量。",
  None,
  "总质量",
  "质量守恒定律适用于所有化学反应。",
  0.32)

# kp_chem9_conservation_experiments
Q("kp_chem9_conservation_experiments", "choice", "mcq_single",
  "下列实验中，能直接验证质量守恒定律的是（　　）",
  ["白磷在密闭容器中燃烧","碳酸钠与盐酸在敞口烧杯中反应","铁与硫酸铜溶液在敞口烧杯中反应","氯化钡与硫酸钠在敞口烧杯中反应"],
  "A",
  "白磷燃烧放热但产物 P2O5 是固体，且在密闭容器中物质总质量不变。其他在敞口装置中有气体生成或参与反应，会造成测量误差。",
  0.55)
Q("kp_chem9_conservation_experiments", "choice", "mcq_single",
  "碳酸钠与盐酸反应在敞口烧杯中反应后，烧杯内物质总质量减小，主要原因是（　　）",
  ["Na2CO3 分解","反应生成 CO2 气体逸出","NaCl 升华","空气参与反应"],
  "B",
  "Na2CO3 + 2HCl → 2NaCl + H2O + CO2↑，CO2 逸出使总质量减小。",
  0.45)
Q("kp_chem9_conservation_experiments", "fill", "fill_blank",
  "验证质量守恒定律时，有气体参加或生成的反应必须在______（填敞口或密闭）容器中进行。",
  None,
  "密闭",
  "有气体参加或生成时，密闭容器可保证物质不逸出或进入。",
  0.4)

# kp_chem9_conservation_apps
Q("kp_chem9_conservation_apps", "choice", "mcq_single",
  "下列现象中，可以用质量守恒定律解释的是（　　）",
  ["水结冰后体积变大","高锰酸钾加热后剩余固体质量变小","酒精与水混合后总体积变小","氢气球升空"],
  "B",
  "高锰酸钾加热分解生成 K2MnO4、MnO2、O2，O2 逸出使剩余固体质量减小，符合质量守恒。",
  0.5)
Q("kp_chem9_conservation_apps", "choice", "mcq_single",
  "下列说法符合质量守恒定律的是（　　）",
  ["10 g 氢气和 10 g 氧气反应一定生成 20 g 水","10 g 氢气和 80 g 氧气反应一定生成 90 g 水","8 g 氢气和 32 g 氧气反应一定生成 40 g 水","A、B、C 都不对"],
  "B",
  "化学方程式中 H2 与 O2 质量比 1:8。10 g 氢气恰好完全反应需要 80 g 氧气，生成 90 g 水。",
  0.55)
Q("kp_chem9_conservation_apps", "fill", "fill_blank",
  "化学反应前后，元素的______（填种类或质量）不变。",
  None,
  "种类和质量",
  "质量守恒定律：元素种类和质量、原子种类和质量都不变。",
  0.4)

# kp_chem9_equation_meaning
Q("kp_chem9_equation_meaning", "choice", "mcq_single",
  "化学方程式 2H2 + O2 =点燃= 2H2O 表示的含义中，错误的是（　　）",
  ["氢气和氧气在点燃条件下反应生成水","参加反应的氢气、氧气与生成的水的分子数之比为 2:1:2","参加反应的氢气和氧气的质量之比为 1:8","参加反应的氢气、氧气和生成的水的质量之比为 1:8:9"],
  "D",
  "由方程式，H2、O2、H2O 质量比 = (2×2):(1×32):(2×18) = 4:32:36 = 1:8:9，D 正确。等等，让我重新计算：H2 分子量 2，O2 分子量 32，H2O 分子量 18。系数 × 分子量：H2 = 2×2 = 4；O2 = 1×32 = 32；H2O = 2×18 = 36。比 4:32:36 = 1:8:9。D 对。错误选项是哪一个？C 说 1:8 是 H2:O2 质量比，正确；D 说 1:8:9 也正确。重新审视：A、B、C、D 都正确？",
  0.55)
# Recreate kp_chem9_equation_meaning choice #2 with clearer distractor
Q("kp_chem9_equation_meaning", "choice", "mcq_single",
  "化学方程式 2H2 + O2 =点燃= 2H2O 表示的含义中，不正确的是（　　）",
  ["氢气和氧气在点燃条件下生成水","参加反应的 H2、O2 与生成 H2O 的分子个数比为 2:1:2","参加反应的 H2 和 O2 的质量比为 1:8","参加反应的 H2、O2 与生成 H2O 的质量比为 1:8:9，且水分子中含有 1 个 H2 分子"],
  "D",
  "D 错：水分子由 H 原子和 O 原子构成，不含 H2 分子。A、B、C 都正确：质量比 = (2×2):32:(2×18)=4:32:36=1:8:9。",
  0.6)
Q("kp_chem9_equation_meaning", "fill", "fill_blank",
  "化学方程式 2H2 + O2 =点燃= 2H2O 中的=点燃=表示反应条件是______。",
  None,
  "点燃",
  "化学方程式中等号上方的文字表示反应条件。",
  0.35)

# kp_chem9_equation_writing
Q("kp_chem9_equation_writing", "choice", "mcq_single",
  "下列化学方程式书写正确的是（　　）",
  ["Mg + O2 =点燃= MgO2","Mg + O2 =点燃= 2MgO","2Mg + O2 =点燃= 2MgO","2Mg + O2 = 2MgO"],
  "C",
  "A 产物错误（应为 MgO）；B 未配平；D 缺反应条件点燃。",
  0.5)
Q("kp_chem9_equation_writing", "choice", "mcq_single",
  "下列化学方程式书写错误的是（　　）",
  ["Fe + 2HCl = FeCl2 + H2↑","2H2O =通电= 2H2↑ + O2↑","CaCO3 + 2HCl = CaCl2 + H2O + CO2↑","Cu + 2AgCl = CuCl2 + 2Ag"],
  "D",
  "D 错：AgCl 难溶于水，不能与铜反应置换出 Ag。",
  0.55)
Q("kp_chem9_equation_writing", "fill", "fill_blank",
  "配平化学方程式 2H2O =通电= 2H2↑ + O2↑ 中，反应物的系数和为______。",
  None,
  "2",
  "反应物 H2O 系数为 2。",
  0.32)

# kp_chem9_typical_equations
Q("kp_chem9_typical_equations", "choice", "mcq_single",
  "下列化学方程式正确的是（　　）",
  ["2H2O2 =MnO2= 2H2O + O2↑","H2O2 =MnO2= H2O + O2","H2O2 =MnO2= H2O + O2↑","2H2O2 =MnO2= 2H2O + O2"],
  "A",
  "A 正确：配平、催化剂 MnO2 写在等号上、生成 O2 标↑。B 未配平；C↑标在 H2O 后错误；D 未标↑。",
  0.5)
Q("kp_chem9_typical_equations", "choice", "mcq_single",
  "铁与硫酸铜溶液反应的化学方程式为（　　）",
  ["Fe + CuSO4 = FeSO4 + Cu","2Fe + 3CuSO4 = Fe2(SO4)3 + 3Cu","Fe + CuSO4 = FeSO4 + Cu↓","Fe + CuSO4 = FeCu + SO4"],
  "A",
  "A 正确：Fe + CuSO4 → FeSO4 + Cu。Cu 是固体不标↓；Fe 显 +2 价生成 FeSO4。",
  0.45)
Q("kp_chem9_typical_equations", "fill", "fill_blank",
  "实验室制取氧气的反应之一：高锰酸钾受热分解的化学方程式为 2KMnO4 =△= K2MnO4 + MnO2 + ______。",
  None,
  "O2↑",
  "高锰酸钾受热分解生成锰酸钾、二氧化锰和氧气。",
  0.4)

# kp_chem9_combination_decomposition
Q("kp_chem9_combination_decomposition", "choice", "mcq_single",
  "下列反应中属于化合反应的是（　　）",
  ["CaCO3 =高温= CaO + CO2↑","2H2 + O2 =点燃= 2H2O","Zn + 2HCl = ZnCl2 + H2↑","2H2O =通电= 2H2↑ + O2↑"],
  "B",
  "化合反应：多变一。A 是分解反应；C 是置换反应；D 是分解反应。",
  0.4)
Q("kp_chem9_combination_decomposition", "choice", "mcq_single",
  "下列反应中属于分解反应的是（　　）",
  ["S + O2 =点燃= SO2","H2CO3 = H2O + CO2↑","Fe + CuSO4 = FeSO4 + Cu","NaOH + HCl = NaCl + H2O"],
  "B",
  "分解反应：一变多。A 是化合；C 是置换；D 是复分解。",
  0.4)
Q("kp_chem9_combination_decomposition", "fill", "fill_blank",
  "由两种或两种以上的物质生成______（填一种或多种）新物质的反应叫做化合反应。",
  None,
  "一种",
  "化合反应多变一。",
  0.32)

# kp_chem9_replacement_reaction
Q("kp_chem9_replacement_reaction", "choice", "mcq_single",
  "下列反应中属于置换反应的是（　　）",
  ["2H2 + O2 =点燃= 2H2O","Zn + 2HCl = ZnCl2 + H2↑","CaCO3 =高温= CaO + CO2↑","NaOH + HCl = NaCl + H2O"],
  "B",
  "置换反应：单质 + 化合物 → 新单质 + 新化合物。A 是化合；C 是分解；D 是复分解。",
  0.4)
Q("kp_chem9_replacement_reaction", "choice", "mcq_single",
  "下列反应不能发生的是（　　）",
  ["Zn + 2HCl = ZnCl2 + H2↑","Cu + 2AgNO3 = Cu(NO3)2 + 2Ag","Fe + CuSO4 = FeSO4 + Cu","Cu + FeSO4 = CuSO4 + Fe"],
  "D",
  "Cu 在金属活动性顺序中位于 Fe 之后，不能置换 Fe。",
  0.45)
Q("kp_chem9_replacement_reaction", "fill", "fill_blank",
  "置换反应中，反应物是一种单质和一种______（填单质或化合物），生成物是另一种单质和另一种化合物。",
  None,
  "化合物",
  "置换反应：单质 + 化合物 → 新单质 + 新化合物。",
  0.35)

# kp_chem9_double_decomposition
Q("kp_chem9_double_decomposition", "choice", "mcq_single",
  "下列反应中属于复分解反应的是（　　）",
  ["Fe + 2HCl = FeCl2 + H2↑","Na2CO3 + 2HCl = 2NaCl + H2O + CO2↑","2H2O =通电= 2H2↑ + O2↑","C + 2CuO =高温= 2Cu + CO2↑"],
  "B",
  "复分解反应：两种化合物互相交换成分生成两种新化合物（这里有 H2O 生成）。A 是置换；C 是分解；D 是置换。",
  0.45)
Q("kp_chem9_double_decomposition", "choice", "mcq_single",
  "下列各组物质在水溶液中能发生复分解反应的是（　　）",
  ["NaCl 和 KNO3","NaOH 和 H2SO4","Na2SO4 和 KCl","HCl 和 Cu"],
  "B",
  "NaOH + H2SO4 → Na2SO4 + H2O，是中和反应（属复分解）。A、C 无沉淀气体水生成；D Cu 在金属活动性顺序 H 之后不与盐酸反应。",
  0.5)
Q("kp_chem9_double_decomposition", "fill", "fill_blank",
  "复分解反应是两种化合物互相交换成分生成两种新______（填单质或化合物）的反应。",
  None,
  "化合物",
  "复分解反应的特点：两化合物互换成分，生成两新化合物。",
  0.35)

# kp_chem9_combustion_conditions
Q("kp_chem9_combustion_conditions", "choice", "mcq_single",
  "可燃物燃烧需要同时具备的条件是（　　）",
  ["可燃物、氧气","可燃物、温度达到可燃物的着火点","氧气、温度达到可燃物的着火点","可燃物、氧气（空气）、温度达到可燃物的着火点"],
  "D",
  "燃烧三条件：可燃物、氧气（空气）、温度达到着火点。三者同时具备，缺一不可。",
  0.4)
Q("kp_chem9_combustion_conditions", "choice", "mcq_single",
  "下列做法中，利用了隔绝氧气灭火原理的是（　　）",
  ["用水浇灭燃着的木材","用锅盖盖灭油锅火","用沙土盖灭燃着的化学品","降低可燃物温度到着火点以下"],
  "B",
  "锅盖盖灭油锅火是隔绝氧气（空气）。A、C 既降温又隔绝空气；D 是降温灭火。",
  0.5)
Q("kp_chem9_combustion_conditions", "fill", "fill_blank",
  "可燃物的温度必须达到______（填燃点或着火点）才能燃烧。",
  None,
  "着火点",
  "着火点：可燃物燃烧所需的最低温度。",
  0.32)

# kp_chem9_combustion_inquiry
Q("kp_chem9_combustion_inquiry", "choice", "mcq_single",
  "探究燃烧条件实验中，白磷和红磷对比实验的设计目的是验证（　　）",
  ["温度对燃烧的影响","氧气对燃烧的影响","可燃物（白磷 vs 红磷）对燃烧的影响","A 和 B 共同影响"],
  "C",
  "白磷和红磷是可燃物不同种类对比，且温度相同（约 80℃），控制变量：探究可燃物自身性质（着火点不同）对燃烧的影响。",
  0.55)
Q("kp_chem9_combustion_inquiry", "choice", "mcq_single",
  "下列关于燃烧条件实验的描述中，错误的是（　　）",
  ["铜片上的白磷燃烧而红磷不燃烧，说明温度需达到可燃物的着火点","水下白磷不通入氧气时不燃烧，说明燃烧需要氧气","白磷燃烧时产生大量白烟","白磷燃烧生成 CO2 和 H2O"],
  "D",
  "D 错：白磷燃烧只生成 P2O5（白色固体小颗粒形成白烟），不生成 CO2 和 H2O（白磷是单质，不含 C、H 元素）。",
  0.5)
Q("kp_chem9_combustion_inquiry", "fill", "fill_blank",
  "探究燃烧条件实验中，烧杯中热水的作用是提供______（填温度）和隔绝氧气（用于水下白磷）。",
  None,
  "温度",
  "热水提供温度（≥白磷着火点 40℃）和水下隔绝氧气环境。",
  0.4)

# kp_chem9_explosion_safety
Q("kp_chem9_explosion_safety", "choice", "mcq_single",
  "下列物质与空气混合后遇明火可能发生爆炸的是（　　）",
  ["氧气","氮气","面粉粉尘","二氧化碳"],
  "C",
  "可燃性粉尘（面粉、煤粉等）与空气混合遇明火可能发生爆炸。",
  0.4)
Q("kp_chem9_explosion_safety", "choice", "mcq_single",
  "下列场所中必须严禁烟火的是（　　）",
  ["面粉加工厂","公园草坪","教室","图书馆阅览室"],
  "A",
  "面粉加工厂空气中有可燃性粉尘，遇明火可能爆炸。",
  0.4)
Q("kp_chem9_explosion_safety", "fill", "fill_blank",
  "可燃性气体或______（填粉尘或蒸汽）与空气混合遇明火可能发生爆炸。",
  None,
  "可燃性粉尘",
  "可燃性气体、蒸气、粉尘与空气混合达到爆炸极限遇明火爆炸。",
  0.4)

# kp_chem9_fire_fighting
Q("kp_chem9_fire_fighting", "choice", "mcq_single",
  "下列灭火原理中不正确的是（　　）",
  ["清除可燃物","隔绝氧气（空气）","降低温度到可燃物的着火点以下","增加可燃物与氧气接触面积"],
  "D",
  "灭火原理是破坏燃烧条件之一（清除可燃物、隔绝氧气、降温到着火点以下）。增加接触面积是促进燃烧。",
  0.4)
Q("kp_chem9_fire_fighting", "choice", "mcq_single",
  "森林着火时，砍掉大火前方一定宽度的树木，目的是（　　）",
  ["降低温度到着火点以下","隔绝氧气","清除可燃物","降低可燃物的着火点"],
  "C",
  "砍树清除了可燃物，使火无法继续蔓延。",
  0.35)
Q("kp_chem9_fire_fighting", "fill", "fill_blank",
  "灭火的原理是：清除______、隔绝空气（氧气）、降低温度到可燃物的______以下。",
  None,
  "可燃物；着火点",
  "灭火原理：破坏燃烧条件之一即可灭火。",
  0.35)

# kp_chem9_fire_extinguisher
Q("kp_chem9_fire_extinguisher", "choice", "mcq_single",
  "下列灭火器中，主要用于扑灭图书档案、贵重设备火灾的是（　　）",
  ["泡沫灭火器","干粉灭火器","二氧化碳灭火器","水基灭火器"],
  "C",
  "CO2 灭火器灭火后不留痕迹，适用于扑灭图书、档案、贵重设备火灾。",
  0.45)
Q("kp_chem9_fire_extinguisher", "choice", "mcq_single",
  "CO2 灭火器灭火的主要原理是（　　）",
  ["降低着火点","隔绝氧气（空气）并降温","清除可燃物","生成水降温"],
  "B",
  "CO2 不可燃也不支持燃烧，喷出时温度降低，液态 CO2 气化吸热并隔绝空气。",
  0.4)
Q("kp_chem9_fire_extinguisher", "fill", "fill_blank",
  "CO2 灭火器是利用 CO2______（填能或不能）燃烧也不支持燃烧的性质。",
  None,
  "不能",
  "CO2 不能燃烧也不支持燃烧，可用于灭火。",
  0.32)

# kp_chem9_combustion_complete
Q("kp_chem9_combustion_complete", "choice", "mcq_single",
  "下列做法中，能使燃料充分燃烧的是（　　）",
  ["将煤块粉碎后燃烧","燃烧时减少氧气供应","保持较低温度燃烧","减少空气流通"],
  "A",
  "煤粉碎后增大与氧气的接触面积，使燃烧更充分。",
  0.4)
Q("kp_chem9_combustion_complete", "choice", "mcq_single",
  "使燃料充分燃烧的两种方法是（　　）",
  ["①增大氧气浓度；②增大可燃物与氧气的接触面积","①降低温度；②减少氧气","①增加可燃物；②减少氧气","①隔绝空气；②降低温度"],
  "A",
  "促进燃料充分燃烧的方法：①足量氧气（或空气）；②增大可燃物与氧气的接触面积。",
  0.4)
Q("kp_chem9_combustion_complete", "fill", "fill_blank",
  "使燃料充分燃烧通常考虑两点：①提供足够的______；②增大可燃物与氧气的接触面积。",
  None,
  "氧气（或空气）",
  "充分燃烧条件：足量氧气、充分接触。",
  0.4)

# kp_chem9_burn_products
Q("kp_chem9_burn_products", "choice", "mcq_single",
  "检验某气体燃烧产物中有水生成，可采用的方法是（　　）",
  ["将气体通入澄清石灰水","用干燥的冷烧杯罩在火焰上方，观察是否有水珠","将气体通过浓硫酸","闻气味"],
  "B",
  "用干燥冷烧杯罩在火焰上，若烧杯内壁有水珠，说明燃烧产物中有水。",
  0.4)
Q("kp_chem9_burn_products", "choice", "mcq_single",
  "检验某气体燃烧产物中有 CO2 生成，可采用的方法是（　　）",
  ["将气体通入澄清石灰水观察是否变浑浊","用干燥冷烧杯罩在火焰上","观察火焰颜色","闻气味"],
  "A",
  "CO2 通入澄清石灰水：CO2 + Ca(OH)2 → CaCO3↓ + H2O，石灰水变浑浊。",
  0.4)
Q("kp_chem9_burn_products", "fill", "fill_blank",
  "甲烷（CH4）燃烧生成 CO2 和 H2O，反应方程式为：CH4 + 2O2 =点燃= CO2 + ______。",
  None,
  "2H2O",
  "甲烷燃烧生成 CO2 和 H2O，方程式：CH4 + 2O2 =点燃= CO2 + 2H2O。",
  0.4)

# kp_chem9_candle_inquiry
Q("kp_chem9_candle_inquiry", "choice", "mcq_single",
  "蜡烛燃烧时，下列说法正确的是（　　）",
  ["只发生物理变化","只发生化学变化","既发生物理变化又发生化学变化","蜡烛不燃烧时也有化学变化"],
  "C",
  "蜡烛先熔化（物理变化），再燃烧生成 CO2 和 H2O（化学变化）。",
  0.4)
Q("kp_chem9_candle_inquiry", "choice", "mcq_single",
  "蜡烛燃烧过程中，下列描述错误的是（　　）",
  ["火焰分外焰、内焰、焰心三层","外焰温度最高","蜡烛燃烧只生成 CO2 和 H2O","熄灭时产生白烟"],
  "C",
  "C 错：蜡烛燃烧产物除 CO2 和 H2O 外，还有炭黑（不完全燃烧）等。",
  0.5)
Q("kp_chem9_candle_inquiry", "fill", "fill_blank",
  "蜡烛火焰温度最高的是______层（填外焰、内焰或焰心）。",
  None,
  "外焰",
  "外焰与空气接触最充分，燃烧最完全，温度最高。",
  0.32)

# kp_chem9_quantitative_calc
Q("kp_chem9_quantitative_calc", "choice", "mcq_single",
  "工业上高温煅烧石灰石（CaCO3）制取生石灰（CaO）和二氧化碳。煅烧 100 t 含 CaCO3 80% 的石灰石，理论上可生产生石灰的质量是（　　）",
  ["44.8 t","56 t","64 t","44.8 t"],
  "A",
  "CaCO3 =高温= CaO + CO2↑。100 t × 80% = 80 t CaCO3。设 CaO 质量 x：100/56 = 80/x，x = 80 × 56 / 100 = 44.8 t。",
  0.55)
Q("kp_chem9_quantitative_calc", "choice", "mcq_single",
  "电解 18 g 水，能产生氢气的质量为（　　）",
  ["1 g","2 g","4 g","8 g"],
  "B",
  "2H2O =通电= 2H2↑ + O2↑。36 g 水产生 4 g H2，则 18 g 水产生 2 g H2。",
  0.45)
Q("kp_chem9_quantitative_calc", "fill", "fill_blank",
  "利用化学方程式计算的依据是______定律。",
  None,
  "质量守恒",
  "化学方程式计算的理论依据是质量守恒定律。",
  0.32)

# kp_chem9_calc_excess_purity
Q("kp_chem9_calc_excess_purity", "choice", "mcq_single",
  "煅烧 200 t 含 80% CaCO3 的石灰石，理论上可生成 CO2 的质量是（杂质不反应）（　　）",
  ["35.2 t","44 t","70.4 t","88 t"],
  "C",
  "CaCO3 质量 = 200 × 80% = 160 t。CaCO3 ~ CO2 质量比 = 100 : 44。CO2 质量 = 160 × 44 / 100 = 70.4 t。",
  0.55)
Q("kp_chem9_calc_excess_purity", "choice", "mcq_single",
  "将 10 g 含杂质（不参与反应）的锌粒与足量稀盐酸反应，生成 0.2 g 氢气，则锌粒中锌的质量分数约为（　　）",
  ["65%","50%","35%","80%"],
  "A",
  "Zn + 2HCl → ZnCl2 + H2↑。设 Zn 质量 x：65/2 = x/0.2，x = 6.5 g。质量分数 = 6.5/10 = 65%。",
  0.55)
Q("kp_chem9_calc_excess_purity", "fill", "fill_blank",
  "含杂质问题的化学方程式计算中，必须将______（填杂质或不纯物质）质量换算成纯净的参加反应的物质质量。",
  None,
  "不纯",
  "化学方程式计算的是纯净物质的质量，含杂质时要先换算。",
  0.4)

# kp_chem9_solution_reaction_calc
Q("kp_chem9_solution_reaction_calc", "choice", "mcq_single",
  "100 g 质量分数为 14.6% 的稀盐酸与足量石灰石反应，生成 CO2 的质量为（　　）",
  ["4.4 g","8.8 g","2.2 g","6.6 g"],
  "B",
  "HCl 质量 = 100 × 14.6% = 14.6 g。CaCO3 + 2HCl → CaCl2 + H2O + CO2↑。HCl:CO2 质量比 = 73:44。CO2 = 14.6 × 44 / 73 = 8.8 g。",
  0.6)
Q("kp_chem9_solution_reaction_calc", "choice", "mcq_single",
  "足量铁与 200 g 9.8% 的稀硫酸完全反应，生成硫酸亚铁（FeSO4）的质量为（　　）",
  ["15.2 g","7.6 g","30.4 g","20 g"],
  "A",
  "H2SO4 质量 = 200 × 9.8% = 19.6 g。Fe + H2SO4 → FeSO4 + H2↑。H2SO4:FeSO4 = 98:152。FeSO4 = 19.6 × 152 / 98 = 30.4 g。",
  0.6)
Q("kp_chem9_solution_reaction_calc", "fill", "fill_blank",
  "溶液中反应的综合计算时，应先将溶液中______（填溶质或溶剂）的质量算出来再代入方程式。",
  None,
  "溶质",
  "化学方程式计算的是参加反应的溶质（反应物）质量。",
  0.4)

# kp_chem9_reduction
Q("kp_chem9_reduction", "choice", "mcq_single",
  "在反应 CuO + H2 =△= Cu + H2O 中，氧化剂是（　　）",
  ["CuO","H2","Cu","H2O"],
  "A",
  "CuO 中的 O 被夺走，CuO 是氧化剂；H2 夺得 O 是还原剂。",
  0.45)
Q("kp_chem9_reduction", "choice", "mcq_single",
  "在反应 2CuO + C =高温= 2Cu + CO2↑ 中，下列说法正确的是（　　）",
  ["C 是氧化剂","CuO 是还原剂","C 失去氧，被氧化，是还原剂","CuO 得到氧，被氧化，是还原剂"],
  "C",
  "C 夺得 O（被氧化），是还原剂；CuO 失去 O（被还原），是氧化剂。",
  0.5)
Q("kp_chem9_reduction", "fill", "fill_blank",
  "在反应中，物质得到氧的反应叫做______反应；物质失去氧的反应叫做______反应。",
  None,
  "氧化；还原",
  "氧化反应：得氧；还原反应：失氧。",
  0.4)

# kp_chem9_cuox_reduction
Q("kp_chem9_cuox_reduction", "choice", "mcq_single",
  "下列实验中，能说明 H2 具有还原性的是（　　）",
  ["H2 在空气中燃烧","H2 还原氧化铜生成 Cu 和 H2O","H2 通入水中","H2 与 CuO 混合不反应"],
  "B",
  "H2 还原 CuO 生成 Cu 和 H2O，H2 是还原剂，具有还原性。",
  0.4)
Q("kp_chem9_cuox_reduction", "choice", "mcq_single",
  "H2 还原氧化铜实验操作中，下列顺序正确的是（　　）",
  ["先加热后通 H2","先通 H2 一段时间后加热，反应后先停止加热继续通 H2 至冷却","边加热边通 H2","直接加热"],
  "B",
  "先通 H2 排尽装置内空气（防 H2 受热爆炸）；反应后继续通 H2 直至冷却（防生成的 Cu 被空气重新氧化）。",
  0.55)
Q("kp_chem9_cuox_reduction", "fill", "fill_blank",
  "H2 还原氧化铜的化学方程式为：H2 + CuO =△= Cu +______。",
  None,
  "H2O",
  "H2 还原 CuO：H2 + CuO → Cu + H2O。",
  0.32)

# kp_chem9_carbon_chem_properties
Q("kp_chem9_carbon_chem_properties", "choice", "mcq_single",
  "下列关于碳单质化学性质的叙述，正确的是（　　）",
  ["常温下碳的化学性质活泼","碳在氧气中充分燃烧生成 CO","碳在氧气中不充分燃烧生成 CO2","碳的还原性可用于工业冶炼金属"],
  "D",
  "A 错（常温稳定）；B 错（充分燃烧生成 CO2）；C 错（不充分燃烧生成 CO）；D 对。",
  0.45)
Q("kp_chem9_carbon_chem_properties", "choice", "mcq_single",
  "碳还原氧化铜的化学方程式为（　　）",
  ["C + 2CuO =高温= 2Cu + CO2↑","2C + CuO =高温= Cu + CO2↑","C + CuO = Cu + CO↑","C + CuO =△= Cu + CO"],
  "A",
  "C + 2CuO =高温= 2Cu + CO2↑ 是标准方程式。注意温度为高温。",
  0.5)
Q("kp_chem9_carbon_chem_properties", "fill", "fill_blank",
  "木炭（主要成分是 C）还原氧化铜实验中，黑色粉末变成红色，同时生成的气体能使澄清石灰水______，证明生成 CO2。",
  None,
  "变浑浊",
  "CO2 + Ca(OH)2 → CaCO3↓ + H2O，石灰水变浑浊证明含 CO2。",
  0.4)

# kp_chem9_hydrogen_properties
Q("kp_chem9_hydrogen_properties", "choice", "mcq_single",
  "下列关于氢气性质的叙述，错误的是（　　）",
  ["氢气是无色、无味、密度最小的气体","氢气难溶于水","氢气具有可燃性","氢气具有助燃性"],
  "D",
  "D 错：H2 不助燃，本身可燃。",
  0.35)
Q("kp_chem9_hydrogen_properties", "choice", "mcq_single",
  "检验氢气纯度的正确方法是（　　）",
  ["用拇指堵住试管口靠近火焰后移开拇指听声音","直接用燃着的木条伸入试管","点燃后观察火焰颜色","闻气味"],
  "A",
  "检验 H2 纯度：拇指堵口靠近火焰后移开，听到尖锐爆鸣声则不纯，较小声则纯。",
  0.4)
Q("kp_chem9_hydrogen_properties", "fill", "fill_blank",
  "点燃 H2 前必须______，防止不纯的 H2 发生爆炸。",
  None,
  "检验纯度",
  "点燃 H2 前必须检验纯度。",
  0.32)

# kp_chem9_energy_changes
Q("kp_chem9_energy_changes", "choice", "mcq_single",
  "下列变化中属于化学变化且放出热量的是（　　）",
  ["冰雪融化","生石灰与水反应","酒精挥发","干冰升华"],
  "B",
  "生石灰与水反应：CaO + H2O → Ca(OH)2，放出大量热，是化学变化。",
  0.4)
Q("kp_chem9_energy_changes", "choice", "mcq_single",
  "下列能量变化过程中，化学能转化为热能的是（　　）",
  ["植物光合作用","燃料燃烧","电灯发光","水力发电"],
  "B",
  "燃料燃烧：化学能 → 热能（和光能）。",
  0.4)
Q("kp_chem9_energy_changes", "fill", "fill_blank",
  "化学反应在生成新物质的同时，还伴随着______（填热量或能量）的变化。",
  None,
  "能量",
  "化学反应都伴随能量变化（吸热或放热）。",
  0.35)

# kp_chem9_neutral_heat
Q("kp_chem9_neutral_heat", "choice", "mcq_single",
  "中和反应一般是（　　）",
  ["放热反应","吸热反应","既不吸热也不放热","无法判断"],
  "A",
  "中和反应都是放热反应。",
  0.3)
Q("kp_chem9_neutral_heat", "choice", "mcq_single",
  "稀盐酸与 NaOH 溶液反应时，下列测量温度变化的仪器是（　　）",
  ["量筒","温度计","托盘天平","pH 试纸"],
  "B",
  "中和反应放热，用温度计测量温度变化。",
  0.3)
Q("kp_chem9_neutral_heat", "fill", "fill_blank",
  "中和反应是______（填放热或吸热）反应，反应过程中溶液温度升高。",
  None,
  "放热",
  "中和反应放热，溶液温度升高。",
  0.32)

# kp_chem9_reaction_rate_factors
Q("kp_chem9_reaction_rate_factors", "choice", "mcq_single",
  "下列因素中，能影响化学反应速率的是（　　）",
  ["反应物的性质","温度","反应物的浓度","以上都是"],
  "D",
  "化学反应速率与反应物性质、温度、浓度、催化剂、接触面积等有关。",
  0.4)
Q("kp_chem9_reaction_rate_factors", "choice", "mcq_single",
  "实验室用过氧化氢溶液制取氧气时，加入 MnO2 后产生氧气明显加快，说明 MnO2 在反应中起的作用是（　　）",
  ["氧化剂","催化剂","还原剂","反应物"],
  "B",
  "MnO2 加快反应速率，但本身质量和化学性质不变，是催化剂。",
  0.35)
Q("kp_chem9_reaction_rate_factors", "fill", "fill_blank",
  "在化学反应中，活化能较高的反应通常需要______（填加热或加压）才能较快进行。",
  None,
  "加热（或加催化剂）",
  "升高温度可以加快化学反应速率。",
  0.4)

# kp_chem9_reaction_regulation
Q("kp_chem9_reaction_regulation", "choice", "mcq_single",
  "下列事例中，主要通过加快反应速率来提高生产效率的是（　　）",
  ["煤的燃烧","食品真空包装防腐","铁制品放在潮湿处加速生锈","粮食密封储存"],
  "A",
  "煤粉碎、鼓入空气可加快燃烧，提高效率。其他都是减缓反应。",
  0.45)
Q("kp_chem9_reaction_regulation", "choice", "mcq_single",
  "下列事例中，主要通过减慢反应速率来防止损失的是（　　）",
  ["煤粉碎燃烧","食品冷藏","氢气点燃","钢铁冶炼"],
  "B",
  "食品冷藏降低温度减慢食品变质的反应速率。",
  0.4)
Q("kp_chem9_reaction_regulation", "fill", "fill_blank",
  "化学反应的应用价值常体现在：①利用反应放出的______；②利用反应速率的调控；③利用生成的新物质等。",
  None,
  "能量（或热量）",
  "化学反应的重要应用是释放能量（取暖、发电、动力等）。",
  0.4)

# kp_chem9_transform_network
Q("kp_chem9_transform_network", "choice", "mcq_single",
  "下列物质之间的转化，不能一步实现的是（　　）",
  ["CaCO3 → CO2","CO2 → CaCO3","C → CO2","CO2 → CO"],
  "D",
  "D 不能一步实现（CO2 → C 一步不能；CO2 → CO 需 C + CO2 →高温→ 2CO 是 CO2 转化但多步）。",
  0.5)
Q("kp_chem9_transform_network", "choice", "mcq_single",
  "下列各组物质间能相互转化，且都能由一步反应实现的是（　　）",
  ["CO2 ↔ CaCO3","CO2 ↔ O2","Cu ↔ Cu(OH)2","H2O ↔ H2O2"],
  "A",
  "CO2 + Ca(OH)2 → CaCO3↓ + H2O；CaCO3 + 2HCl → CaCl2 + H2O + CO2↑。",
  0.55)
Q("kp_chem9_transform_network", "fill", "fill_blank",
  "常见物质转化关系网络中，碳、CO、CO2 之间可以相互转化。写出 CO 转化为 CO2 的化学方程式：2CO + O2 =点燃= ______。",
  None,
  "2CO2",
  "2CO + O2 =点燃= 2CO2 是 CO 转化为 CO2 的燃烧反应。",
  0.45)

# kp_chem9_conservation_calc
Q("kp_chem9_conservation_calc", "choice", "mcq_single",
  "在反应 A + B → C + D 中，若 A 与 B 恰好完全反应时消耗 8 g A 和 4 g B，生成 9 g C，则生成 D 的质量为（　　）",
  ["3 g","4 g","5 g","6 g"],
  "A",
  "由质量守恒：8 + 4 = 9 + m(D)，m(D) = 3 g。",
  0.4)
Q("kp_chem9_conservation_calc", "choice", "mcq_single",
  "镁带在空气中燃烧后质量增加，下列解释正确的是（　　）",
  ["不遵守质量守恒定律","生成物的质量等于参加反应的镁和氧气的质量之和","反应前后元素种类改变","空气不参与反应"],
  "B",
  "镁燃烧生成 MgO，质量增加是因为结合了空气中 O2 的质量，符合质量守恒。",
  0.5)
Q("kp_chem9_conservation_calc", "fill", "fill_blank",
  "化学反应中，参加反应的各物质质量之和等于反应后生成的各物质______（填质量或体积）之和。",
  None,
  "质量",
  "质量守恒：反应前后物质总质量不变。",
  0.32)

# ===== Cluster 5: 化学与社会·跨学科实践 (14 KPs) =====

# kp_chem9_fossil_fuels
Q("kp_chem9_fossil_fuels", "choice", "mcq_single",
  "下列物质中不属于化石燃料的是（　　）",
  ["煤","石油","天然气","酒精"],
  "D",
  "化石燃料：煤、石油、天然气（不可再生能源）。酒精是可再生能源。",
  0.35)
Q("kp_chem9_fossil_fuels", "choice", "mcq_single",
  "下列叙述错误的是（　　）",
  ["化石燃料是不可再生能源","煤主要含碳元素","天然气主要成分是甲烷","化石燃料燃烧不会污染空气"],
  "D",
  "D 错：化石燃料燃烧产生 SO2、NO2、烟尘等，污染空气。",
  0.4)
Q("kp_chem9_fossil_fuels", "fill", "fill_blank",
  "化石燃料主要包括______、石油和天然气。",
  None,
  "煤",
  "三大化石燃料：煤、石油、天然气。",
  0.3)

# kp_chem9_methane
Q("kp_chem9_methane", "choice", "mcq_single",
  "天然气的主要成分是（　　）",
  ["CO","H2","CH4","C2H5OH"],
  "C",
  "天然气主要成分是甲烷（CH4），是可燃性气体。",
  0.32)
Q("kp_chem9_methane", "choice", "mcq_single",
  "下列叙述中，属于甲烷性质的是（　　）",
  ["无色、无味、难溶于水","密度比空气大","不支持燃烧","是红棕色气体"],
  "A",
  "甲烷无色无味，难溶于水，密度比空气小，能燃烧。",
  0.4)
Q("kp_chem9_methane", "fill", "fill_blank",
  "甲烷（CH4）燃烧的化学方程式为：CH4 + 2O2 =点燃= CO2 + ______。",
  None,
  "2H2O",
  "甲烷燃烧生成 CO2 和 H2O：CH4 + 2O2 =点燃= CO2 + 2H2O。",
  0.32)

# kp_chem9_new_energy
Q("kp_chem9_new_energy", "choice", "mcq_single",
  "下列能源中属于新能源（清洁能源）的是（　　）",
  ["煤","石油","太阳能","天然气"],
  "C",
  "新能源包括太阳能、风能、地热能、氢能、核能、生物质能等。",
  0.3)
Q("kp_chem9_new_energy", "choice", "mcq_single",
  "下列说法错误的是（　　）",
  ["氢气是清洁能源","太阳能是清洁能源","核能不会产生放射性污染","风能是清洁能源"],
  "C",
  "C 错：核能利用过程中会产生放射性废料，存在环境污染风险。",
  0.4)
Q("kp_chem9_new_energy", "fill", "fill_blank",
  "氢气被认为是理想能源，主要原因是其燃烧产物是______，不污染空气。",
  None,
  "水（H2O）",
  "2H2 + O2 =点燃= 2H2O，产物只有水，清洁无污染。",
  0.35)

# kp_chem9_sustainable_dev
Q("kp_chem9_sustainable_dev", "choice", "mcq_single",
  "下列做法符合绿色化学理念的是（　　）",
  ["任意排放工业废水","焚烧废旧塑料处理垃圾","化工生产中提高原子利用率","大量使用一次性塑料制品"],
  "C",
  "A、B、D 都不符合绿色化学。绿色化学核心：原子经济性、无污染。",
  0.4)
Q("kp_chem9_sustainable_dev", "choice", "mcq_single",
  "下列叙述中不属于绿色化学思想的是（　　）",
  ["采用无毒无害的原料","提高原子利用率","生产可降解塑料","任意排放废水废气"],
  "D",
  "D 错误。绿色化学：从源头减少污染，原料无害、产物无毒、副产物少、原子利用率高。",
  0.4)
Q("kp_chem9_sustainable_dev", "fill", "fill_blank",
  "______化学要求从源头上减少和消除工业生产对环境的污染。",
  None,
  "绿色",
  "绿色化学的核心是利用化学原理从源头消除污染。",
  0.35)

# kp_chem9_salt_project
Q("kp_chem9_salt_project", "choice", "mcq_single",
  "海水中含量最多的盐是（　　）",
  ["氯化钠","氯化镁","硫酸钠","氯化钙"],
  "A",
  "海水中盐类以 NaCl 含量最多（约 3.5%）。",
  0.35)
Q("kp_chem9_salt_project", "choice", "mcq_single",
  "海水晒盐是利用了氯化钠的什么性质（　　）",
  ["溶解度受温度影响较小","易溶于水","不溶于水","密度大"],
  "A",
  "NaCl 溶解度受温度影响较小，故采用蒸发结晶法晒盐。",
  0.45)
Q("kp_chem9_salt_project", "fill", "fill_blank",
  "海水晒盐的原理是______（填蒸发结晶或冷却结晶），利用氯化钠溶解度受温度影响较小的特点。",
  None,
  "蒸发结晶",
  "海水晒盐用蒸发结晶法。",
  0.4)

# kp_chem9_materials
Q("kp_chem9_materials", "choice", "mcq_single",
  "下列材料中属于合成材料的是（　　）",
  ["棉花","塑料","木材","蚕丝"],
  "B",
  "三大合成材料：塑料、合成纤维、合成橡胶。棉花、木材、蚕丝是天然材料。",
  0.35)
Q("kp_chem9_materials", "choice", "mcq_single",
  "下列材料中属于无机非金属材料的是（　　）",
  ["塑料","玻璃","钢铁","棉麻"],
  "B",
  "玻璃是无机非金属材料。塑料是有机合成材料；钢铁是金属材料；棉麻是天然纤维。",
  0.4)
Q("kp_chem9_materials", "fill", "fill_blank",
  "三大合成材料是塑料、______和合成橡胶。",
  None,
  "合成纤维",
  "三大合成材料：塑料、合成纤维、合成橡胶。",
  0.3)

# kp_chem9_health_chem
Q("kp_chem9_health_chem", "choice", "mcq_single",
  "下列营养素中能为人体提供能量的是（　　）",
  ["维生素","无机盐","糖类","水"],
  "C",
  "六大营养素中提供能量的有糖类、油脂、蛋白质。",
  0.3)
Q("kp_chem9_health_chem", "choice", "mcq_single",
  "下列食物中富含蛋白质的是（　　）",
  ["米饭","鸡蛋","蔬菜","植物油"],
  "B",
  "鸡蛋富含蛋白质；米饭主要含糖类；蔬菜富含维生素；植物油富含油脂。",
  0.35)
Q("kp_chem9_health_chem", "fill", "fill_blank",
  "人体必需的六大营养素包括糖类、油脂、蛋白质、维生素、无机盐和______。",
  None,
  "水",
  "六大营养素：糖类、油脂、蛋白质、维生素、无机盐、水。",
  0.3)

# kp_chem9_environment
Q("kp_chem9_environment", "choice", "mcq_single",
  "下列做法中，有利于保护环境的是（　　）",
  ["生活垃圾分类处理","焚烧秸秆","工厂直接排放废水","使用一次性塑料袋"],
  "A",
  "B、C、D 都污染环境。A 垃圾分类回收再利用有利于环境保护。",
  0.35)
Q("kp_chem9_environment", "choice", "mcq_single",
  "下列环境问题与 SO2 排放直接相关的是（　　）",
  ["温室效应","酸雨","臭氧层破坏","白色污染"],
  "B",
  "SO2 排放到空气中形成酸雨。温室效应主要由 CO2 引起；臭氧层破坏与氟氯烃有关；白色污染是塑料垃圾。",
  0.4)
Q("kp_chem9_environment", "fill", "fill_blank",
  "三大化石燃料燃烧产生的 SO2、NO2 等气体排放到空气中会形成______，破坏环境。",
  None,
  "酸雨",
  "SO2、NO2 溶于雨水形成酸雨。",
  0.35)

# kp_chem9_air_quality_project
Q("kp_chem9_air_quality_project", "choice", "mcq_single",
  "空气质量报告中的 AQI 数值越大，说明空气质量（　　）",
  ["越好","越差","不变","无法判断"],
  "B",
  "AQI 数值越大，空气质量越差；数值越小，空气质量越好。",
  0.3)
Q("kp_chem9_air_quality_project", "choice", "mcq_single",
  "下列做法中，不利于改善空气质量的是（　　）",
  ["骑自行车或步行代替开车","使用新能源替代化石燃料","工厂废气处理达标后排放","大量燃烧秸秆"],
  "D",
  "A、B、C 有利；D 大量燃烧秸秆产生大量烟尘和气体，污染空气。",
  0.35)
Q("kp_chem9_air_quality_project", "fill", "fill_blank",
  "空气质量监测的主要污染物有 PM2.5、PM10、SO2、NO2、O3 和______等。",
  None,
  "CO（一氧化碳）",
  "六大主要污染物：PM2.5、PM10、SO2、NO2、O3、CO。",
  0.4)

# kp_chem9_oxygen_supplier_project
Q("kp_chem9_oxygen_supplier_project", "choice", "mcq_single",
  "下列反应能产生氧气且适合在简易供氧器中使用的是（　　）",
  ["石灰石与盐酸反应","过氧化氢溶液与二氧化锰","大理石与稀硫酸","碳酸钠与稀盐酸"],
  "B",
  "过氧化氢在 MnO2 催化下分解产生 O2，速率可控、安全，适合供氧。",
  0.5)
Q("kp_chem9_oxygen_supplier_project", "choice", "mcq_single",
  "过氧化氢分解的化学方程式为（　　）",
  ["H2O2 = H2O + O","2H2O2 =MnO2= 2H2O + O2↑","H2O2 =MnO2= H2O + O2↑","H2O2 =MnO2= H2O + O"],
  "B",
  "B 正确：2H2O2 =MnO2= 2H2O + O2↑，配平、催化剂、↑齐全。",
  0.4)
Q("kp_chem9_oxygen_supplier_project", "fill", "fill_blank",
  "简易供氧器中常使用过氧化氢溶液和二氧化锰，反应方程式为 2H2O2 =MnO2= 2H2O + O2↑，其中 MnO2 起______作用。",
  None,
  "催化",
  "MnO2 在过氧化氢分解反应中是催化剂。",
  0.35)

# kp_chem9_water_purify_project
Q("kp_chem9_water_purify_project", "choice", "mcq_single",
  "自制简易净水器中常使用的吸附剂是（　　）",
  ["活性炭","石英砂","小卵石","蓬松棉"],
  "A",
  "活性炭具有吸附性，常用作净水器的吸附层。",
  0.35)
Q("kp_chem9_water_purify_project", "choice", "mcq_single",
  "简易净水器中各层材料的作用中，下列说法错误的是（　　）",
  ["小卵石、石英砂起过滤作用","活性炭吸附色素和异味","蓬松棉防止上层颗粒进入下层","小卵石层应该放在最上层"],
  "D",
  "D 错：自制净水器一般由上到下：蓬松棉→小卵石→石英砂→活性炭（顺序为先粗过滤再吸附）。",
  0.5)
Q("kp_chem9_water_purify_project", "fill", "fill_blank",
  "活性炭净水器主要利用其______性，除去水中的色素和异味。",
  None,
  "吸附",
  "活性炭具有疏松多孔结构，有强吸附性。",
  0.35)

# kp_chem9_carbon_neutral_project
Q("kp_chem9_carbon_neutral_project", "choice", "mcq_single",
  "实现碳中和的途径不包括（　　）",
  ["减少化石燃料燃烧","植树造林增加碳吸收","开发新能源","增加煤炭使用量"],
  "D",
  "增加煤炭使用量会增加 CO2 排放，不符合碳中和理念。",
  0.35)
Q("kp_chem9_carbon_neutral_project", "choice", "mcq_single",
  "下列行为符合低碳生活理念的是（　　）",
  ["随手关灯节约用电","出门打车代替步行","频繁使用一次性筷子","长时间开空调"],
  "A",
  "随手关灯符合低碳生活。其他都增加能源消耗。",
  0.3)
Q("kp_chem9_carbon_neutral_project", "fill", "fill_blank",
  "碳中和是指通过植树造林、节能减排等方式抵消自身产生的______排放，实现二氧化碳净零排放。",
  None,
  "二氧化碳（CO2）",
  "碳中和：CO2 排放量与吸收量平衡，实现净零排放。",
  0.4)

# kp_chem9_garbage_project
Q("kp_chem9_garbage_project", "choice", "mcq_single",
  "下列垃圾中属于可回收垃圾的是（　　）",
  ["果皮","废电池","易拉罐","剩饭剩菜"],
  "C",
  "易拉罐（金属）是可回收垃圾。果皮、剩饭剩菜是厨余垃圾；废电池是有害垃圾。",
  0.4)
Q("kp_chem9_garbage_project", "choice", "mcq_single",
  "废电池属于有害垃圾，原因是其中含有（　　）",
  ["汞、镉、铅等重金属","糖类","大量水分","油污"],
  "A",
  "废电池含汞、镉、铅等重金属，随意丢弃会污染土壤和水源。",
  0.4)
Q("kp_chem9_garbage_project", "fill", "fill_blank",
  "生活垃圾一般分为可回收垃圾、有害垃圾、厨余垃圾和______垃圾四类。",
  None,
  "其他",
  "生活垃圾分类：可回收、有害、厨余、其他。",
  0.3)

# kp_chem9_cross_practice_misc
Q("kp_chem9_cross_practice_misc", "choice", "mcq_single",
  "下列跨学科实践活动中，与化学关系最密切的是（　　）",
  ["组装微型空气质量检测站","校园运动会的接力比赛","班级合唱","朗诵比赛"],
  "A",
  "组装空气质量检测站需要测量 SO2、NO2、PM2.5 等，与化学关系最密切。",
  0.35)
Q("kp_chem9_cross_practice_misc", "choice", "mcq_single",
  "探究土壤酸碱性对植物生长影响的实验中，测定土壤 pH 常用的方法是（　　）",
  ["闻气味","用 pH 试纸测定浸出液","目测土壤颜色","用手摸"],
  "B",
  "用 pH 试纸测定土壤浸出液的酸碱性。",
  0.35)
Q("kp_chem9_cross_practice_misc", "fill", "fill_blank",
  "调查家用燃料的变迁与合理使用活动中，常见家用燃料有煤、______、液化石油气和天然气等。",
  None,
  "煤气",
  "我国家用燃料历经木柴→煤→煤气→液化石油气/天然气的变迁。",
  0.4)
