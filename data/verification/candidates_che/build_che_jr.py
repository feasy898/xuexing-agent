# -*- coding: utf-8 -*-
"""build_che_jr.py —— 读取 che_jr_questions.py，应用类型多样化变换，输出三个 JSON。
变换策略：
- 把 ~20 道选择题改成 mcq_multiple（subset，5-6 个选项，2 个正确）
- 把 ~40 道题改成 solve（experiment/calculation/comprehension/process_flow/equation_writing 等 form）
- 编号：che_che_jr_0001 到 che_che_jr_0411
"""
import sys, os, json, importlib, importlib.util
from collections import Counter, defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import che_jr_questions as Q

# ---- 1. 重新组织成 (kp -> [(index_in_QUESTIONS, q)]) ----
by_kp = defaultdict(list)
for i, q in enumerate(Q.QUESTIONS):
    by_kp[q[0]].append((i, q))

# ---- 2. 类型多样化变换 ----
# (kp_id, position) -> (new_type, new_form, new_stem, new_options, new_answer, new_solution, answer_mode)
# position: 0/1/2 表示该 KP 下的第几题
# For mcq_multiple, new_options 应为 5 或 6 项，new_answer 为 "A,C" 形式

TRANSFORMATIONS = {}

# === Cluster 1: 科学探究与化学实验 — 5 mcq_multi, 5 solve ===
TRANSFORMATIONS[("kp_chem9_chem_dev_history", 0)] = (
    "choice", "mcq_multiple",
    "下列我国古代化学成就中，利用了化学变化的有（　　）（多选）",
    ["火药的发明","瓷器的烧制","指南针的制造","钢铁的冶炼","活字印刷"],
    "A,B,D",
    "火药燃烧、瓷器烧制、钢铁冶炼都是化学变化；指南针和活字印刷是物理变化。",
    "subset"
)
TRANSFORMATIONS[("kp_chem9_sci_inquiry", 1)] = (
    "choice", "mcq_multiple",
    "下列属于科学探究环节的有（　　）（多选）",
    ["提出问题","猜想与假设","设计实验方案","收集证据","得出结论"],
    "A,B,C,D,E",
    "科学探究包括提出问题→猜想与假设→设计实验方案→收集证据→得出结论→反思评价→表达交流。",
    "subset"
)
TRANSFORMATIONS[("kp_chem9_safety_lab", 1)] = (
    "choice", "mcq_multiple",
    "下列化学实验事故处理方法中，正确的有（　　）（多选）",
    ["浓硫酸沾到皮肤上立即用大量水冲洗，再涂 3%~5% NaHCO3 溶液","酒精灯失火用湿抹布盖灭","浓碱液沾到皮肤上立即用大量水冲洗，再涂硼酸溶液","实验台起火立即用水浇灭"],
    "A,B,C",
    "前三种正确；D 错：化学实验台起火应根据药品性质选择灭火方式，不一定都用水。",
    "subset"
)
TRANSFORMATIONS[("kp_chem9_reagent_handling", 1)] = (
    "choice", "mcq_multiple",
    "下列操作符合化学实验室安全规则的有（　　）（多选）",
    ["用药匙取用粉末状药品","用镊子取用块状药品","用镊子夹取砝码","直接用手接触 NaOH 固体"],
    "A,B,C",
    "A、B、C 符合三不一要原则；D 直接用手接触 NaOH 会腐蚀皮肤。",
    "subset"
)
TRANSFORMATIONS[("kp_chem9_heating_ops", 1)] = (
    "choice", "mcq_multiple",
    "使用酒精灯给物质加热时的正确操作有（　　）（多选）",
    ["用酒精灯外焰加热","用嘴吹灭酒精灯","给试管内液体加热时，试管与桌面成 45°角","加热完毕用灯帽盖灭酒精灯"],
    "A,C,D",
    "用嘴吹灭酒精灯可能引燃灯内酒精蒸气，造成危险。",
    "subset"
)

# Solve 类型的转换（cluster 1）
TRANSFORMATIONS[("kp_chem9_o2_lab_prep", 2)] = (
    "solve", "experiment",
    "某化学兴趣小组拟用过氧化氢溶液和二氧化锰在实验室制取氧气。请回答：（1）写出反应的化学方程式；（2）选择发生装置需要考虑的因素；（3）如何检验所收集的气体是氧气？",
    None,
    "（1）2H2O2 =MnO2= 2H2O + O2↑；（2）反应物状态（液体）和反应条件（不需加热），选择固液常温型发生装置；（3）将带火星的木条伸入集气瓶中，若木条复燃，证明气体是氧气。",
    "实验室用过氧化氢溶液制氧气的标准操作与检验方法。",
    None
)
TRANSFORMATIONS[("kp_chem9_co2_lab_prep", 2)] = (
    "solve", "experiment",
    "实验室用大理石与稀盐酸反应制取二氧化碳。（1）写出化学方程式；（2）能否用稀硫酸代替稀盐酸？为什么？（3）如何证明所收集的气体是 CO2？",
    None,
    "（1）CaCO3 + 2HCl = CaCl2 + H2O + CO2↑；（2）不能用稀硫酸代替，因为 CaSO4 微溶，会附着在大理石表面阻止反应继续；（3）将气体通入澄清石灰水，若石灰水变浑浊，证明是 CO2。",
    "实验室制 CO2 的关键细节与验证方法。",
    None
)
TRANSFORMATIONS[("kp_chem9_separation_ops", 2)] = (
    "solve", "experiment",
    "回答过滤操作中一贴二低三靠的具体含义，并说明若操作不当（如液面高于滤纸边缘）会造成什么后果。",
    None,
    "一贴：滤纸紧贴漏斗内壁；二低：滤纸边缘低于漏斗边缘，液面低于滤纸边缘；三靠：倾倒时烧杯口紧靠玻璃棒，玻璃棒紧靠三层滤纸，漏斗下端紧靠烧杯内壁。若液面高于滤纸边缘，液体从滤纸与漏斗之间流下，未经滤纸过滤，滤液浑浊。",
    "过滤操作核心规范与错误后果分析。",
    None
)
TRANSFORMATIONS[("kp_chem9_control_variable", 2)] = (
    "solve", "experiment",
    "小明探究温度对化学反应速率的影响，他用等量 5% 的过氧化氢溶液，一份在 20℃下加入 MnO2，另一份在 50℃下加入等量 MnO2，比较产生氧气的速率。请指出该实验设计的错误并改正。",
    None,
    "错误：探究温度影响时，应控制其他变量（如催化剂、浓度）相同，仅改变温度。小明的设计加入了等量 MnO2 但没有指明浓度和体积完全相同，且应避免同时引入催化剂变量。改正：取等浓度、等体积的过氧化氢溶液两份，均加入等量 MnO2，但分别在 20℃和 50℃下进行反应，观察产生气泡的快慢。",
    "控制变量法要点：单一变量。",
    None
)
TRANSFORMATIONS[("kp_chem9_salt_purification", 2)] = (
    "solve", "experiment",
    "粗盐提纯实验中，各步骤玻璃棒的作用是什么？蒸发操作中何时停止加热？为什么？",
    None,
    "玻璃棒作用：溶解时搅拌加速溶解；过滤时引流；蒸发时搅拌防止液滴飞溅并使受热均匀。蒸发时，当蒸发皿中出现较多固体时停止加热，利用蒸发皿余热将剩余水分蒸干，防止温度过高造成固体溅出。",
    "粗盐提纯关键操作细节。",
    None
)

# === Cluster 2: 物质的性质与应用 — 8 mcq_multi, 10 solve ===
TRANSFORMATIONS[("kp_chem9_chem_use_safety", 1)] = (
    "choice", "mcq_multiple",
    "下列符合化学品安全使用要求的有（　　）（多选）",
    ["稀释浓硫酸时将浓硫酸沿器壁慢慢注入水中","家用洁厕灵与 84 消毒液混合使用","实验室品尝药品的味道","用完酒精灯后用灯帽盖灭"],
    "A,D",
    "B 错：洁厕灵+84 消毒液会产生有毒氯气；C 错：化学药品严禁品尝。",
    "subset"
)
TRANSFORMATIONS[("kp_chem9_substance_id", 1)] = (
    "choice", "mcq_multiple",
    "下列除杂方案（括号内为杂质）中，能达到目的的有（　　）（多选）",
    ["CO（CO2）——通过足量 NaOH 溶液","NaCl（Na2CO3）——加适量稀盐酸后蒸发","Cu（CuO）——加足量稀盐酸后过滤","Fe（Fe2O3）——加足量稀盐酸后过滤"],
    "A,B",
    "A 对：CO2 + 2NaOH → Na2CO3 + H2O；B 对：Na2CO3 + 2HCl → 2NaCl + H2O + CO2↑；C 错：稀盐酸会与 Cu 反应；D 错：稀盐酸会与 Fe 反应。",
    "subset"
)
TRANSFORMATIONS[("kp_chem9_double_decomp_cond", 1)] = (
    "choice", "mcq_multiple",
    "下列各组物质在水溶液中不能大量共存的有（　　）（多选）",
    ["NaCl 和 KNO3","NaOH 和 H2SO4","Na2CO3 和 HCl","BaCl2 和 Na2SO4"],
    "B,C,D",
    "B 中和反应（NaOH + H2SO4 → Na2SO4 + H2O）；C 生成 CO2（Na2CO3 + 2HCl → 2NaCl + H2O + CO2↑）；D 生成 BaSO4 沉淀。仅 A 无反应能共存。",
    "subset"
)
TRANSFORMATIONS[("kp_chem9_ion_identity", 1)] = (
    "choice", "mcq_multiple",
    "下列离子检验方案中，正确的有（　　）（多选）",
    ["检验 SO4 2-：加 BaCl2 溶液和稀盐酸","检验 Cl-：加 AgNO3 溶液和稀硝酸","检验 CO3 2-：加稀盐酸，将气体通入澄清石灰水","检验 NH4+：加 NaOH 溶液共热，用湿润红色石蕊试纸检验"],
    "A,B,C,D",
    "四种离子检验方案均正确。A 中 BaSO4 白色沉淀不溶于稀盐酸；B 中 AgCl 白色沉淀不溶于稀硝酸；C 中 CO2 使石灰水变浑浊；D 中 NH3 使湿润红色石蕊试纸变蓝。",
    "subset"
)
TRANSFORMATIONS[("kp_chem9_metal_activity", 1)] = (
    "choice", "mcq_multiple",
    "下列各组金属活动性顺序判断正确的有（　　）（多选）",
    ["Fe > Cu","Zn > Fe","Cu > Ag","Mg > Al"],
    "A,B,C,D",
    "金属活动性顺序：K Ca Na Mg Al Zn Fe Sn Pb (H) Cu Hg Ag Pt Au。Fe > Cu、Zn > Fe、Cu > Ag、Mg > Al 均正确。",
    "subset"
)
TRANSFORMATIONS[("kp_chem9_fertilizer", 1)] = (
    "choice", "mcq_multiple",
    "下列化肥中属于氮肥的有（　　）（多选）",
    ["尿素 CO(NH2)2","氯化铵 NH4Cl","硝酸钾 KNO3","碳酸钾 K2CO3"],
    "A,B",
    "A、B 含 N 元素属氮肥；C 含 N 和 K，是复合肥；D 含 K 属钾肥。",
    "subset"
)
TRANSFORMATIONS[("kp_chem9_indicators", 1)] = (
    "choice", "mcq_multiple",
    "下列溶液能使无色酚酞变红的有（　　）（多选）",
    ["石灰水","NaOH 溶液","稀盐酸","Na2CO3 溶液"],
    "A,B,D",
    "A、B、D 都显碱性，能使酚酞变红；稀盐酸显酸性，不能使酚酞变色。",
    "subset"
)
TRANSFORMATIONS[("kp_chem9_acid_properties", 1)] = (
    "choice", "mcq_multiple",
    "下列物质能与稀盐酸反应的有（　　）（多选）",
    ["铁锈（Fe2O3·xH2O）","大理石（CaCO3）","氧化铜（CuO）","铜（Cu）"],
    "A,B,C",
    "A、B、C 都能与盐酸反应；Cu 在金属活动性顺序 H 之后，不与盐酸反应。",
    "subset"
)

TRANSFORMATIONS[("kp_chem9_base_properties", 1)] = (
    "choice", "mcq_multiple",
    "下列物质能与 NaOH 溶液反应的有（　　）（多选）",
    ["CO2","稀盐酸","CuSO4 溶液","NaCl 溶液"],
    "A,B,C",
    "A：2NaOH + CO2 → Na2CO3 + H2O；B：NaOH + HCl → NaCl + H2O；C：2NaOH + CuSO4 → Cu(OH)2↓ + Na2SO4；D 不反应。",
    "subset"
)

TRANSFORMATIONS[("kp_chem9_iron_smelting", 2)] = (
    "solve", "process_flow",
    "工业炼铁的主要反应原理是用 CO 还原铁矿石中的氧化铁。写出主要反应的化学方程式，并简述炼铁高炉中焦炭和石灰石的作用。",
    None,
    "化学方程式：3CO + Fe2O3 =高温= 2Fe + 3CO2。焦炭的作用：燃烧放出大量热提供高温，并与 CO2 反应生成 CO（CO 是主要还原剂）：C + O2 =点燃= CO2、CO2 + C =高温= 2CO。石灰石的作用：高温分解生成 CaO，CaO 与脉石（SiO2）反应生成 CaSiO3 炉渣，便于分离：CaCO3 =高温= CaO + CO2↑；CaO + SiO2 =高温= CaSiO3。",
    "工业炼铁原理和原料作用。",
    None
)
TRANSFORMATIONS[("kp_chem9_quantitative_calc", 2)] = (
    "solve", "calculation",
    "工业上高温煅烧 200 t 含 80% CaCO3 的石灰石，理论上可生产多少吨生石灰（CaO）？同时产生多少吨 CO2？（杂质不反应，CaCO3、CaO、CO2 的相对分子质量分别为 100、56、44）",
    None,
    "纯 CaCO3 质量 = 200 t × 80% = 160 t。CaCO3 =高温= CaO + CO2↑。设 CaO 质量为 x：100/56 = 160/x，x = 160 × 56 / 100 = 89.6 t。设 CO2 质量为 y：100/44 = 160/y，y = 160 × 44 / 100 = 70.4 t。答：理论上可生产生石灰 89.6 t，CO2 70.4 t。",
    "化学方程式计算 + 含杂质问题。",
    None
)
TRANSFORMATIONS[("kp_chem9_calc_excess_purity", 2)] = (
    "solve", "calculation",
    "将 13 g 含杂质的锌粒与足量稀硫酸反应，生成 0.4 g H2，求锌粒中锌的质量分数。（Zn + H2SO4 → ZnSO4 + H2↑，Zn 相对原子质量 65）",
    None,
    "设 Zn 质量为 x。Zn ~ H2 质量比 = 65 : 2。65/2 = x/0.4，x = 65 × 0.4 / 2 = 13 g。质量分数 = 13/13 × 100% = 100%。答：锌粒中锌的质量分数为 100%（即纯锌）。",
    "化学方程式计算 + 杂质含量推断。",
    None
)
TRANSFORMATIONS[("kp_chem9_solution_reaction_calc", 2)] = (
    "solve", "calculation",
    "向 200 g 质量分数为 9.8% 的稀硫酸中加入足量的铁，完全反应后能生成多少克硫酸亚铁（FeSO4）？（Fe + H2SO4 → FeSO4 + H2↑，H2SO4、FeSO4 相对分子质量分别为 98、152）",
    None,
    "纯 H2SO4 质量 = 200 × 9.8% = 19.6 g。设 FeSO4 质量为 x：98/152 = 19.6/x，x = 19.6 × 152 / 98 = 30.4 g。答：生成 FeSO4 30.4 g。",
    "溶液中化学反应的方程式计算。",
    None
)
TRANSFORMATIONS[("kp_chem9_mass_fraction", 2)] = (
    "solve", "calculation",
    "将 20 g NaOH 固体溶于 180 g 水中，所得 NaOH 溶液中溶质的质量分数是多少？若要将其稀释为 5% 的 NaOH 溶液，需要加水多少克？",
    None,
    "NaOH 质量分数 = 20 / (20+180) × 100% = 10%。设稀释后总质量为 m：20/m × 100% = 5%，m = 400 g。需加水 = 400 - 200 = 200 g。答：所得溶液质量分数为 10%；稀释为 5% 需加水 200 g。",
    "溶质质量分数计算与稀释问题。",
    None
)
TRANSFORMATIONS[("kp_chem9_solution_calc", 2)] = (
    "solve", "calculation",
    "把 100 g 20% 的 NaCl 溶液与 200 g 10% 的 NaCl 溶液混合，求混合后溶液中 NaCl 的质量分数。",
    None,
    "NaCl 总质量 = 100 × 20% + 200 × 10% = 20 + 20 = 40 g。混合溶液总质量 = 100 + 200 = 300 g。质量分数 = 40/300 × 100% ≈ 13.3%。答：混合后 NaCl 质量分数约为 13.3%。",
    "溶液混合计算。",
    None
)
TRANSFORMATIONS[("kp_chem9_equation_writing", 2)] = (
    "solve", "equation_writing",
    "完成下列化学方程式并配平：（1）Al + O2 →；（2）Fe + CuSO4 →；（3）H2O2 → H2O + O2↑；（4）CaCO3 + HCl →。",
    None,
    "（1）4Al + 3O2 =点燃= 2Al2O3；（2）Fe + CuSO4 = FeSO4 + Cu；（3）2H2O2 =MnO2= 2H2O + O2↑；（4）CaCO3 + 2HCl = CaCl2 + H2O + CO2↑。",
    "化学方程式的书写与配平基本功。",
    None
)
TRANSFORMATIONS[("kp_chem9_formula_writing", 2)] = (
    "solve", "equation_writing",
    "根据要求书写化学式：（1）氧化铁（铁显 +3 价）；（2）氯化锌；（3）硝酸铵；（4）氢氧化钙；（5）硫酸铝（铝显 +3 价）。",
    None,
    "（1）Fe2O3；（2）ZnCl2；（3）NH4NO3；（4）Ca(OH)2；（5）Al2(SO4)3。",
    "化学式书写规则：正负价代数和为零。",
    None
)
TRANSFORMATIONS[("kp_chem9_naoh_deterioration", 2)] = (
    "solve", "experiment",
    "实验室有一瓶长期暴露在空气中的 NaOH 固体，如何检验它是否变质？若部分变质，如何检验？",
    None,
    "（1）是否变质：取少量样品溶于水，滴加足量稀盐酸，若产生气泡，则 NaOH 已变质（生成 Na2CO3：Na2CO3 + 2HCl → 2NaCl + H2O + CO2↑）。（2）部分变质：取少量样品溶于水配成溶液，先加入足量 CaCl2 溶液（或 BaCl2 溶液）产生白色沉淀（除去 Na2CO3），过滤后向滤液中滴加几滴酚酞试液，若变红则含 NaOH（未完全变质）；若不变红则完全变质。",
    "NaOH 变质程度探究的关键是排除 Na2CO3 的干扰。",
    None
)
TRANSFORMATIONS[("kp_chem9_substance_id", 2)] = (
    "solve", "experiment",
    "有三瓶无色溶液，标签脱落，只知道分别是稀盐酸、稀硫酸和石灰水。请设计实验加以鉴别。",
    None,
    "分别取三种溶液少量于三支试管中，各加入少量 Na2CO3 溶液。产生气泡且能使澄清石灰水变浑浊的是稀盐酸或稀硫酸（不能区分）；产生白色沉淀的是石灰水。再向产生气泡的两种溶液中各加入少量 BaCl2 溶液，产生白色沉淀的是稀硫酸，无明显现象的是稀盐酸。答：先加 Na2CO3 区分石灰水，再加 BaCl2 区分稀盐酸和稀硫酸。",
    "开放性鉴别题，需考虑试剂选择和顺序。",
    None
)

# === Cluster 3: 物质的组成与结构 — 4 mcq_multi, 7 solve ===
TRANSFORMATIONS[("kp_chem9_periodic_table_apps", 1)] = (
    "choice", "mcq_multiple",
    "下列关于元素周期表的说法，正确的有（　　）（多选）",
    ["元素周期表共有 7 个横行（周期）","元素周期表共有 18 个纵行（族）","同一周期元素的原子电子层数相同","同一主族元素的最外层电子数相同"],
    "A,B,C,D",
    "周期表 7 行 18 列；同周期电子层数相同；同主族最外层电子数相同。",
    "subset"
)
TRANSFORMATIONS[("kp_chem9_atom_model_history", 1)] = (
    "choice", "mcq_multiple",
    "下列关于原子结构模型演变历程的说法，正确的有（　　）（多选）",
    ["道尔顿提出近代原子学说","汤姆森发现电子并提出枣糕模型","卢瑟福通过 α 粒子散射实验提出核式结构模型","玻尔提出电子在固定轨道上运动"],
    "A,B,C,D",
    "以上四种说法均正确，均为原子结构模型发展史上的重要节点。",
    "subset"
)
TRANSFORMATIONS[("kp_chem9_chem_dev_history", 1)] = (
    "choice", "mcq_multiple",
    "下列属于化学发展史上的重要里程碑有（　　）（多选）",
    ["火的利用和陶瓷烧制","原子分子学说的创立","门捷列夫发现元素周期律","侯德榜发明侯氏制碱法"],
    "A,B,C,D",
    "四项均为化学发展史上的重要事件，分别代表了人类利用化学、理论化学、系统化和工业化四个阶段。",
    "subset"
)
TRANSFORMATIONS[("kp_chem9_relative_molecular_mass", 1)] = (
    "choice", "mcq_multiple",
    "下列化合物的相对分子质量计算正确的有（　　）（多选）",
    ["H2O 的相对分子质量 = 18","CO2 的相对分子质量 = 44","NaCl 的相对分子质量 = 58.5","H2SO4 的相对分子质量 = 98"],
    "A,B,C,D",
    "A: 1×2+16=18；B: 12+16×2=44；C: 23+35.5=58.5；D: 1×2+32+16×4=98。",
    "subset"
)
TRANSFORMATIONS[("kp_chem9_atom_model_history", 2)] = (
    "solve", "comprehension",
    "简述原子结构模型的演变过程，并说明每个模型的核心观点。",
    None,
    "（1）道尔顿原子学说（1803）：原子是化学变化中的最小粒子，不可再分；同种原子质量相同。（2）汤姆森枣糕模型（1904）：原子是带正电的球，电子镶嵌在其中。（3）卢瑟福核式结构模型（1911）：原子由原子核和核外电子构成，原子核带正电且集中了原子的大部分质量，电子在核外空间绕核运动。（4）玻尔模型：电子在固定轨道上运动，轨道能量量子化。",
    "原子结构模型的演变是逐步接近真相的过程。",
    None
)
TRANSFORMATIONS[("kp_chem9_composition_description", 2)] = (
    "solve", "comprehension",
    "用宏观和微观两个角度描述水的组成和构成。",
    None,
    "宏观：水是由氢元素和氧元素组成的纯净物。微观：水是由大量水分子构成的；每个水分子由 2 个氢原子和 1 个氧原子构成。注意：元素只讲种类不讲个数；原子、分子既讲种类也讲个数。",
    "宏观讲元素组成，微观讲微粒构成。",
    None
)
TRANSFORMATIONS[("kp_chem9_relative_molecular_mass", 2)] = (
    "solve", "calculation",
    "求硝酸铵 NH4NO3 中氮元素的质量分数。（相对原子质量：N=14，H=1，O=16）",
    None,
    "NH4NO3 相对分子质量 = 14 + 1×4 + 14 + 16×3 = 14×2 + 4 + 48 = 80。氮元素总质量 = 14×2 = 28。氮元素质量分数 = 28/80 × 100% = 35%。答：硝酸铵中氮元素的质量分数为 35%。",
    "化学式中元素质量分数的计算。",
    None
)
TRANSFORMATIONS[("kp_chem9_valence", 2)] = (
    "solve", "comprehension",
    "标出 KMnO4 中各元素的化合价，并解释为什么化合物中各元素化合价代数和为零。",
    None,
    "KMnO4 中：K 为 +1，O 为 -2，Mn 为 +7。代数和：(+1) + (+7) + (-2)×4 = +8 - 8 = 0。原因：化合物整体不带电，正负化合价的总数必须相等；这是电荷守恒在化合价上的体现。",
    "化合价规则：化合物中正负化合价代数和为零。",
    None
)
TRANSFORMATIONS[("kp_chem9_electrolysis_calc", 2)] = (
    "solve", "calculation",
    "电解 54 g 水能产生多少克氢气和多少克氧气？产生的氢气和氧气在相同条件下的体积比是多少？",
    None,
    "电解水反应：2H2O =通电= 2H2↑ + O2↑。设 H2 质量为 x：36/4 = 54/x，x = 6 g。O2 质量 = 54 - 6 = 48 g（同温同压下体积比 = 2:1）。答：产生 6 g 氢气，48 g 氧气；体积比 = 2:1。",
    "电解水的定量关系。",
    None
)
TRANSFORMATIONS[("kp_chem9_particle_models", 2)] = (
    "solve", "comprehension",
    "已知某反应的微观示意图：反应前为 2 个 H2 分子和 1 个 O2 分子，反应后为 2 个 H2O 分子。请用分子、原子的观点解释该反应，并判断是否符合质量守恒定律。",
    None,
    "反应微观过程：反应前共有 4 个 H 原子和 2 个 O 原子，反应后 2 个 H2O 分子中含 4 个 H 原子和 2 个 O 原子。原子的种类和数目没有改变，符合质量守恒定律。化学变化实质是原子的重新组合。",
    "微观示意图与质量守恒定律。",
    None
)

# === Cluster 4: 物质的化学变化 — 6 mcq_multi, 10 solve ===
TRANSFORMATIONS[("kp_chem9_combustion_conditions", 1)] = (
    "choice", "mcq_multiple",
    "下列事实中，与温度达到可燃物着火点有关的有（　　）（多选）",
    ["白磷保存在水中","木炭加热到一定温度才能在氧气中燃烧","用火柴点燃柴草","液化石油气泄漏遇明火爆炸"],
    "B,C",
    "B 和 C 都体现温度需达到着火点才能燃烧；A 是隔绝氧气；D 是爆炸极限问题，与着火点无直接关系。",
    "subset"
)
TRANSFORMATIONS[("kp_chem9_fire_fighting", 1)] = (
    "choice", "mcq_multiple",
    "下列灭火方法对应的原理正确的有（　　）（多选）",
    ["用水浇灭木材火灾——降低温度到可燃物的着火点以下","用锅盖盖灭油锅火——隔绝氧气","森林火灾砍伐树木形成隔离带——清除可燃物","吹灭蜡烛——降低可燃物的着火点"],
    "A,B,C",
    "A、B、C 灭火原理正确；D 错：吹灭蜡烛是带走热量使温度降到着火点以下，不是降低着火点（着火点是物质的固有属性）。",
    "subset"
)
TRANSFORMATIONS[("kp_chem9_explosion_safety", 1)] = (
    "choice", "mcq_multiple",
    "下列可燃物与空气混合后遇明火可能发生爆炸的有（　　）（多选）",
    ["氢气","甲烷","面粉粉尘","液化石油气"],
    "A,B,C,D",
    "可燃性气体（H2、CH4、C4H10 等）和可燃性粉尘（面粉、煤粉等）与空气混合遇明火都可能发生爆炸。",
    "subset"
)
TRANSFORMATIONS[("kp_chem9_combustion_complete", 1)] = (
    "choice", "mcq_multiple",
    "下列做法中，能使燃料更充分燃烧的有（　　）（多选）",
    ["将煤粉碎后燃烧","鼓入充足的空气","提高炉温","减少空气的供应"],
    "A,B,C",
    "A、B、C 都是使燃料充分燃烧的方法；D 错：减少空气供应使燃烧不充分。",
    "subset"
)
TRANSFORMATIONS[("kp_chem9_environment", 1)] = (
    "choice", "mcq_multiple",
    "下列行为符合低碳生活理念的有（　　）（多选）",
    ["骑自行车上学","随手关灯","使用一次性筷子","纸张双面打印"],
    "A,B,D",
    "A、B、D 减少能源消耗或资源消耗；C 浪费木材，不符合低碳生活。",
    "subset"
)
TRANSFORMATIONS[("kp_chem9_sustainable_dev", 1)] = (
    "choice", "mcq_multiple",
    "下列做法符合绿色化学理念的有（　　）（多选）",
    ["工业废水处理达标后排放","化工生产中提高原子利用率","研发可降解塑料","任意排放废气"],
    "A,B,C",
    "A、B、C 符合绿色化学；D 错，任意排放废气污染环境。",
    "subset"
)
TRANSFORMATIONS[("kp_chem9_garbage_project", 1)] = (
    "choice", "mcq_multiple",
    "下列属于可回收垃圾的有（　　）（多选）",
    ["废纸","易拉罐","塑料瓶","果皮"],
    "A,B,C",
    "A、B、C 可回收再利用；D 是厨余垃圾。",
    "subset"
)

TRANSFORMATIONS[("kp_chem9_equation_meaning", 2)] = (
    "solve", "comprehension",
    "化学方程式 2H2 + O2 =点燃= 2H2O 表示哪些含义？分别从宏观和微观角度说明。",
    None,
    "宏观含义：氢气和氧气在点燃条件下反应生成水。微观含义：每 2 个氢分子与 1 个氧分子反应生成 2 个水分子。质量含义：每 4 份质量的氢气与 32 份质量的氧气反应生成 36 份质量的水，质量比 1:8:9。各物质分子数比 = 2:1:2。",
    "化学方程式含义三角度：宏观、微观、质量。",
    None
)
TRANSFORMATIONS[("kp_chem9_transform_network", 2)] = (
    "solve", "comprehension",
    "写出 C、CO、CO2 三种物质之间相互转化的化学方程式（至少 4 个）。",
    None,
    "（1）C + O2 =点燃= CO2；（2）2C + O2 =点燃= 2CO；（3）CO2 + C =高温= 2CO；（4）2CO + O2 =点燃= 2CO2；（5）CaCO3 =高温= CaO + CO2↑；（6）CO2 + H2O = H2CO3。",
    "物质间转化网络的构建。",
    None
)
TRANSFORMATIONS[("kp_chem9_replacement_reaction", 2)] = (
    "solve", "comprehension",
    "判断下列反应是否为置换反应：（1）Fe + CuSO4 = FeSO4 + Cu；（2）2H2O =通电= 2H2↑ + O2↑；（3）C + 2CuO =高温= 2Cu + CO2↑；（4）CO + CuO =△= Cu + CO2。",
    None,
    "置换反应要求反应物为单质+化合物，生成物为新单质+新化合物。（1）是置换反应；（2）分解反应；（3）是置换反应（单质 C 和化合物 CuO → 单质 Cu 和化合物 CO2）；（4）不是置换反应（CO 是化合物，反应物两种都是化合物）。",
    "置换反应的特征：单换化换单。",
    None
)
TRANSFORMATIONS[("kp_chem9_combustion_inquiry", 2)] = (
    "solve", "experiment",
    "某兴趣小组为探究燃烧条件，设计如下实验：在 500 mL 烧杯中加 400 mL 热水，在铜片上放一小块白磷和一小块红磷，烧杯水中放一小块白磷。观察现象并回答：（1）铜片上白磷燃烧而红磷不燃烧，说明什么？（2）水下白磷不燃烧但通入氧气后燃烧，说明什么？（3）由此得出燃烧需要哪些条件？",
    None,
    "（1）说明燃烧需要温度达到可燃物的着火点（白磷着火点 40℃ 低于热水温度，红磷着火点 240℃ 高于热水温度）。（2）说明燃烧需要氧气（空气）。（3）燃烧需要同时具备三个条件：①可燃物；②氧气（空气）；③温度达到可燃物的着火点。",
    "燃烧条件的控制变量法探究。",
    None
)
TRANSFORMATIONS[("kp_chem9_evidence_conclusion", 2)] = (
    "solve", "comprehension",
    "小明通过实验发现：将一根燃着的蜡烛用烧杯罩住，过一会儿蜡烛熄灭。将烧杯倒转后注入少量澄清石灰水，振荡，石灰水变浑浊。请根据实验现象得出结论，并用化学方程式表示相关反应。",
    None,
    "结论：蜡烛燃烧生成了 CO2（石灰水变浑浊）和 H2O（烧杯内壁有水雾）。化学方程式：C25H52 + 33O2 =点燃= 25CO2 + 26H2O（蜡烛主要成分为石蜡，主要元素为 C 和 H）。CO2 检验反应：CO2 + Ca(OH)2 = CaCO3↓ + H2O。",
    "证据推理：现象→结论。",
    None
)
TRANSFORMATIONS[("kp_chem9_hypothesis_design", 2)] = (
    "solve", "experiment",
    "为探究铁生锈的条件，请提出你的假设并设计实验方案进行验证。",
    None,
    "假设：铁生锈可能与水有关；可能与氧气（空气）有关；可能与水和氧气共同作用有关。实验方案：取四根相同的铁钉（编号 ①、②、③、④），①铁钉浸没在煮沸过的蒸馏水中（隔绝氧气），②铁钉部分浸入水中（接触水和空气），③铁钉放在干燥的空气中（接触氧气无水），④铁钉完全浸没在植物油中（隔绝水和氧气）。观察四根铁钉是否生锈。结果：只有 ② 生锈，说明铁生锈是铁与水和氧气共同作用的结果。",
    "控制变量法设计探究铁生锈条件。",
    None
)
TRANSFORMATIONS[("kp_chem9_candle_inquiry", 2)] = (
    "solve", "experiment",
    "探究蜡烛燃烧的产物：将干燥的冷烧杯罩在火焰上方，观察到烧杯内壁有水雾；将内壁附有澄清石灰水的烧杯罩在火焰上方，石灰水变浑浊。请写出实验结论。",
    None,
    "实验结论：蜡烛燃烧生成了水（烧杯内壁有水雾）和二氧化碳（石灰水变浑浊）。化学反应方程式：C25H52 + 33O2 =点燃= 25CO2 + 26H2O；CO2 + Ca(OH)2 = CaCO3↓ + H2O。",
    "蜡烛燃烧产物的探究。",
    None
)
TRANSFORMATIONS[("kp_chem9_quantitative_calc", 2)] = (
    "solve", "calculation",
    "实验室用含 CaCO3 90% 的石灰石 100 g 与足量稀盐酸反应，理论上可制得 CO2 多少克？同时生成 CaCl2 多少克？（相对分子质量：CaCO3=100、CO2=44、CaCl2=111）",
    None,
    "纯 CaCO3 质量 = 100 × 90% = 90 g。CaCO3 + 2HCl = CaCl2 + H2O + CO2↑。设 CO2 质量为 x：100/44 = 90/x，x = 90 × 44 / 100 = 39.6 g。设 CaCl2 质量为 y：100/111 = 90/y，y = 90 × 111 / 100 = 99.9 g。答：生成 CO2 39.6 g，CaCl2 99.9 g。",
    "含杂质问题的方程式计算。",
    None
)
TRANSFORMATIONS[("kp_chem9_solution_reaction_calc", 2)] = (
    "solve", "calculation",
    "足量铁与 100 g 9.8% 的稀硫酸完全反应，求生成硫酸亚铁（FeSO4）的质量。（H2SO4、FeSO4 相对分子质量：98、152）",
    None,
    "纯 H2SO4 质量 = 100 × 9.8% = 9.8 g。Fe + H2SO4 = FeSO4 + H2↑。设 FeSO4 质量为 x：98/152 = 9.8/x，x = 9.8 × 152 / 98 = 15.2 g。答：生成 FeSO4 15.2 g。",
    "溶液中反应的方程式计算。",
    None
)
TRANSFORMATIONS[("kp_chem9_conservation_calc", 2)] = (
    "solve", "calculation",
    "在反应 A + B → C + D 中，已知 6 g A 与 4 g B 恰好完全反应生成 8 g C，求同时生成 D 的质量。",
    None,
    "由质量守恒定律，参加反应的各物质质量总和等于生成物质量总和。6 + 4 = 8 + m(D)，m(D) = 2 g。答：同时生成 D 2 g。",
    "质量守恒定律的应用。",
    None
)
TRANSFORMATIONS[("kp_chem9_calc_excess_purity", 2)] = (
    "solve", "calculation",
    "煅烧含 90% CaCO3 的石灰石 200 t，理论上可得到生石灰（CaO）多少吨？同时产生 CO2 多少吨？",
    None,
    "纯 CaCO3 质量 = 200 × 90% = 180 t。CaCO3 =高温= CaO + CO2↑。设 CaO 质量为 x：100/56 = 180/x，x = 180 × 56 / 100 = 100.8 t。设 CO2 质量为 y：100/44 = 180/y，y = 180 × 44 / 100 = 79.2 t。答：生成 CaO 100.8 t，CO2 79.2 t。",
    "含杂质石灰石煅烧的定量计算。",
    None
)

# === Cluster 5: 化学与社会 — 1 mcq_multi, 5 solve ===
TRANSFORMATIONS[("kp_chem9_health_chem", 2)] = (
    "solve", "comprehension",
    "简述六大营养素的主要功能，并指出哪些营养素能为人体提供能量。",
    None,
    "六大营养素：糖类（主要供能）、油脂（备用能源）、蛋白质（构成和修复人体组织，必要时供能）、维生素（调节新陈代谢）、无机盐（构成体组织）、水（溶剂，参与代谢）。能为人体提供能量的有糖类、油脂、蛋白质三大类。",
    "营养与健康：合理膳食。",
    None
)
TRANSFORMATIONS[("kp_chem9_sustainable_dev", 2)] = (
    "solve", "essay",
    "请从化学角度谈谈如何践行绿色化学和可持续发展理念。",
    None,
    "（1）原料选择上：尽量采用无毒无害、可再生的原料，减少使用有毒有害原料。（2）反应过程：提高原子利用率，减少副产物；优化反应条件，降低能耗。（3）产品设计：研发可降解材料，减少白色污染。（4）能源选择：开发太阳能、风能等新能源，减少化石燃料燃烧。（5）末端处理：废水、废气、废渣处理达标后再排放。",
    "绿色化学从源头消除污染。",
    None
)
TRANSFORMATIONS[("kp_chem9_water_purify_project", 2)] = (
    "solve", "open_design",
    "请设计一个简易净水器，说明所用材料、各层材料的作用及原理。",
    None,
    "材料：塑料瓶（剪去底部）、蓬松棉、小卵石、石英砂、活性炭、棉花等。装置由上至下顺序：棉花 → 小卵石 → 石英砂 → 活性炭 → 棉花。原理：小卵石和石英砂起过滤作用，除去较大不溶性杂质；活性炭吸附色素和异味；蓬松棉和棉花起支撑和防止颗粒下移的作用。该净水器只能除去不溶性杂质和部分色素异味，不能除去可溶性杂质。",
    "简易净水器设计与原理。",
    None
)
TRANSFORMATIONS[("kp_chem9_air_quality_project", 2)] = (
    "solve", "comprehension",
    "什么是 AQI？列出 6 种主要的空气污染物，并说明如何从我做起改善空气质量。",
    None,
    "AQI（空气质量指数）是定量描述空气质量状况的无量纲指数。6 种主要污染物：PM2.5、PM10、SO2、NO2、O3、CO。个人行动：①绿色出行，多步行、骑车或乘公交；②节约用电，减少燃煤发电；③不焚烧秸秆、垃圾；④积极参与植树造林；⑤举报工厂违规排放等。",
    "空气质量与个人行动。",
    None
)
TRANSFORMATIONS[("kp_chem9_carbon_neutral_project", 2)] = (
    "solve", "comprehension",
    "什么是碳中和？请列举 3 种实现碳中和的具体措施。",
    None,
    "碳中和是指通过植树造林、节能减排等方式抵消人类活动产生的 CO2 排放，实现 CO2 净零排放。措施举例：①植树造林，增强光合作用吸收 CO2；②优化能源结构，开发太阳能、风能、水能等清洁能源替代化石燃料；③发展低碳技术，提高能源利用率；④倡导低碳生活（节约用电、绿色出行等）。",
    "碳中和：CO2 排放与吸收平衡。",
    None
)
TRANSFORMATIONS[("kp_chem9_methane", 2)] = (
    "solve", "comprehension",
    "天然气（主要成分 CH4）是一种清洁能源。请回答：（1）写出 CH4 完全燃烧的化学方程式；（2）说明天然气被誉为清洁能源的原因；（3）使用天然气时应注意什么？",
    None,
    "（1）CH4 + 2O2 =点燃= CO2 + 2H2O。（2）天然气燃烧产物主要是 CO2 和 H2O，相比煤和石油产生的 SO2、NO2、烟尘等污染物少，故是较清洁的能源。（3）使用注意：①保持通风，防止可燃气体聚集；②使用前检验气密性；③发现泄漏立即关闭阀门并开窗通风；④点燃前检验纯度（虽不一定爆炸但要安全）。",
    "天然气是重要的清洁能源。",
    None
)

# ---- 3. 应用变换 ----
applied_count = {"mcq_multi": 0, "solve": 0}
for (kp_id, pos), (new_type, new_form, new_stem, new_opts, new_ans, new_sol, new_mode) in TRANSFORMATIONS.items():
    # find target index
    target_idx = None
    seen_count = 0
    for i, q in enumerate(Q.QUESTIONS):
        if q[0] == kp_id:
            if seen_count == pos:
                target_idx = i
                break
            seen_count += 1
    if target_idx is None:
        print(f"WARN: kp {kp_id} pos {pos} not found")
        continue
    # 修改
    old_q = Q.QUESTIONS[target_idx]
    new_q = (old_q[0], new_type, new_form, new_stem, new_opts, new_ans, new_sol, old_q[7], new_mode)
    Q.QUESTIONS[target_idx] = new_q
    if new_type == "choice" and new_form == "mcq_multiple":
        applied_count["mcq_multi"] += 1
    elif new_type == "solve":
        applied_count["solve"] += 1

print(f"Applied: mcq_multi={applied_count['mcq_multi']}, solve={applied_count['solve']}")

# ---- 4. 排序并编号 ----
# 按 KP 在 KP 文件中的顺序
import json as _json
KNOW = os.path.join(BASE, "..", "..", "knowledge", "chemistry_grade9.json")
kp_data = _json.load(open(KNOW, encoding="utf-8"))
kp_order = [k["id"] for k in kp_data["knowledge_points"]]
print(f"KP order length: {len(kp_order)}")

# 对 QUESTIONS 按 (kp_order index, original index) 排序
kp_to_order = {kid: i for i, kid in enumerate(kp_order)}
Q.QUESTIONS.sort(key=lambda q: (kp_to_order[q[0]], q[3][:30]))

# ---- 5. 生成 3 个 JSON ----
PUBLIC = []
FULL = []
ANSWERS = {}

counter = [0]
def next_id():
    counter[0] += 1
    return f"che_che_jr_{counter[0]:04d}"

LETTERS = "ABCDEF"

for q in Q.QUESTIONS:
    qid = next_id()
    kp, t, form, stem, opts, ans, sol, diff, am = q
    base = {
        "id": qid,
        "item_type": t,
        "form": form,
        "stem": stem,
        "kps": [kp],
        "difficulty": round(diff, 2),
        "source": "llm_generated",
    }
    if t == "choice":
        if form == "mcq_single" or form == "mcq_multiple":
            # 选项是 list[str]，加上 A./B. 前缀
            full_opts = [f"{LETTERS[i]}. {o}" for i, o in enumerate(opts)]
            base["options"] = full_opts
            if form == "mcq_multiple":
                base["answer_mode"] = "subset"
    PUBLIC.append(base)
    full = dict(base)
    full["answer"] = ans
    full["solution"] = sol
    FULL.append(full)
    ANSWERS[qid] = ans

print(f"Generated {len(PUBLIC)} public items, {len(FULL)} full items, {len(ANSWERS)} answers")

# 写出 3 个文件
PUB_PATH = os.path.join(BASE, "che_jr_public.json")
FUL_PATH = os.path.join(BASE, "che_jr_full.json")
LED_PATH = os.path.join(BASE, "che_jr_ledger_gen.json")

with open(PUB_PATH, "w", encoding="utf-8") as f:
    _json.dump(PUBLIC, f, ensure_ascii=False, indent=2)
with open(FUL_PATH, "w", encoding="utf-8") as f:
    _json.dump(FULL, f, ensure_ascii=False, indent=2)

ledger = {
    "agent_id": "che-gen-w1-20261003",
    "solver": "MiniMax-M3",
    "method": "generator self-answer",
    "answers": ANSWERS,
}
with open(LED_PATH, "w", encoding="utf-8") as f:
    _json.dump(ledger, f, ensure_ascii=False, indent=2)

print("Written:")
print(" ", PUB_PATH)
print(" ", FUL_PATH)
print(" ", LED_PATH)

# 验证摘要
from collections import Counter
print("\n=== Validation Summary ===")
print("item_type:", dict(Counter(it["item_type"] for it in PUBLIC)))
print("form:", dict(Counter(it["form"] for it in PUBLIC)))
print("source:", dict(Counter(it["source"] for it in PUBLIC)))
diffs = [it["difficulty"] for it in PUBLIC]
print(f"difficulty: min={min(diffs)} max={max(diffs)} mean={sum(diffs)/len(diffs):.2f}")
cnt = Counter(it["kps"][0] for it in PUBLIC)
print(f"KP coverage: {len(cnt)}/{len(kp_order)}")
extras = [(k, v) for k, v in cnt.items() if v != 3]
print(f"KP count anomalies: {extras}")
mcq_multi_count = sum(1 for it in PUBLIC if it.get("answer_mode") == "subset")
print(f"mcq_multi (subset): {mcq_multi_count}")
choice_count = sum(1 for it in PUBLIC if it["item_type"] == "choice")
solve_count = sum(1 for it in PUBLIC if it["item_type"] == "solve")
fill_count = sum(1 for it in PUBLIC if it["item_type"] == "fill")
print(f"choice={choice_count}, fill={fill_count}, solve={solve_count}")
