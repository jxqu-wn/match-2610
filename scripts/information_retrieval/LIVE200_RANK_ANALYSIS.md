# 200题参考表低排名原因分析

分析对象：原问题RRF排名大于8的参考表，共34次出现，涉及28题；另有220题的2张参考表因系统分类错误无排名，不与低排名混算。仅做本地冻结结果复核，没有新增外部模型调用或修改召回流程。

## 覆盖事实

34次低排名参考表中，29次首轮已提供：18次由第一训练案例补表，11次由一跳外键补表；另3次经补检索提供，最终上下文合计覆盖32/34。模型最终选择27/34。排名低不等于缺少上下文，未选中也不必然由排名低导致。

仍未提供的低排名表为3432的soccer_2016.Team（32）和1696的education_2024.course（16）。其他未覆盖上下文参考表分别是1643的student（原排名未超过8）及220题系统范围外的两张表。

## 原因及证据

1. 题面实体值与schema结构语言之间缺少映射。3455询问板球守门员，Rolee只写角色/角色描述，没有Keeper，排名92；3293问两支英文球队，Team文档没有具体队名，排名54；3680和3708问中文作品名，works没有这些标题或中英文对应，分别排名83和61。此类名称和值域表承担定位条件，但词面很弱。

2. 已有知识未用于表的第一阶段检索。5420的OBJ_CLASSES排名46，schema只写对象类别，但knowledge:247明确列出broccoli/tomato；5405的PRED_CLASSES排名51，schema笼统写预测类别，knowledge:249明确列出parked on；4204的Attributes排名40，schema只写属性信息，knowledge:146明确包含Good for Kids/适合儿童；3455的knowledge:24已有Keeper含义。schema文档没有这些知识文本，表召回后才依候选表检索知识。局部离线重放不限候选表的知识检索，knowledge:146/249/247分别排名1/2/6，knowledge:24排名17，显示利用知识有机会改善前三例，但不能保证全部案例。未执行新方案或准确率对比。

3. 关联桥表和派生指标需要拆解。4869的competitor_event排名24，承担运动员与项目关联，题面没有表名；3452的Player_Match排名22，承担球员参赛关联；1356的orders排名28，退款条件主要在order_item，orders承担全部订单分母。整题相似度偏向主实体和条件表，不能完整表示每张必要表的独立职责。考试总评分题的exam_score排名9–13，也需要把课程/学期/去重学生/总评等需求拆解，识别成绩来源；schema的通用考试成绩描述没有充分体现业务计算。

4. RRF对弱关键词通道存在实际排名惩罚。34次中25次关键词排名比语义排名差（或无关键词命中），13次语义排名已经在前10；19次只有单个汉字命中或完全无词命中。1356.orders语义第5、关键词第69，融合后第28；5405.PRED_CLASSES语义16、关键词177，融合后51；3680.works语义33且无关键词命中，融合后83。RRF固定叠加1/(60+rank)，只获一条通道分数的候选可输给两条通道均靠后的候选。中文1/2/3元字符索引仍保留“的”等泛词，泛词能够产生第二条通道的弱匹配。这是排序机制事实，不代表尚未做的调权重方案必然更好。

5. 跨业务库同类表竞争放大全局排名。34次中27次在本业务库内排序不超过8；仅用于分析的库内重排不改变当前运行。movie_3.actor被disney电影/配音表竞争；education_2024/2025.course、enrollment、exam_score互相竞争；板球守门员问题前列却包含hockey门将表。部分表确实属于库内弱匹配：Rolee在本库仍第18、3293.Team仍第14，说明业务库正确并不能自动解决。

## 排除因素与判断边界

34次低排名出现中只有1次schema embedding输入受到512长度截断（3589.players_teams，语义仍第3）；其余33次未截断。不能把本批低排名主要归因于embedding长度。200题均无上下文预算裁剪；裁剪也不是原始相关性排名下降原因。

当前结果支持优先改进表的业务语义索引、知识→表的联合召回以及条件/输出/关联/分母等需求拆解，再评估融合排序对弱词面候选的影响。单独扩大候选数量会引入更多非参考信息；已有外键及训练案例补表已经挽回多数低排名表。以上为诊断意见，本次未实现新流程。

## 逐表证据

库内排名是原排序限制到同一业务库后的相对位置，仅用于定位跨库竞争。语义和关键词排名均为预测系统范围内全量表排名；“-”代表未命中。

| 题号 | 参考表 | RRF排名 | 语义排名 | 关键词排名 | 库内排名 | 首轮提供 | 最终上下文提供 | 最终选择 |
|---|---|---:|---:|---:|---:|---|---|---|
| 5420 | SQLite:image_and_language.OBJ_CLASSES | 46 | 18 | 123 | 5 | 是 | 是 | 是 |
| 4204 | SQLite:public_review_platform.Attributes | 40 | 36 | 63 | 13 | 是 | 是 | 否 |
| 1998 | MYSQL:education_2024.exam_score | 11 | 10 | 12 | 5 | 是 | 是 | 是 |
| 1998 | MYSQL:education_2025.exam_score | 13 | 14 | 13 | 5 | 是 | 是 | 是 |
| 3293 | SQLite:soccer_2016.Team | 54 | 59 | 66 | 14 | 是 | 是 | 是 |
| 6166 | SQLite:movie_3.actor | 9 | 9 | 16 | 5 | 是 | 是 | 是 |
| 4869 | SQLite:olympics.competitor_event | 24 | 15 | 55 | 9 | 是 | 是 | 是 |
| 6203 | SQLite:movie_3.actor | 11 | 16 | 16 | 5 | 否 | 是 | 是 |
| 4916 | SQLite:olympics.person | 20 | 10 | 44 | 6 | 是 | 是 | 否 |
| 3404 | SQLite:soccer_2016.City | 14 | 48 | 5 | 8 | 是 | 是 | 否 |
| 3404 | SQLite:soccer_2016.Country | 24 | 59 | 11 | 9 | 否 | 是 | 否 |
| 3432 | SQLite:soccer_2016.Team | 32 | 34 | 31 | 8 | 否 | 否 | 否 |
| 3366 | SQLite:soccer_2016.Team | 42 | 38 | 52 | 15 | 否 | 是 | 是 |
| 4844 | SQLite:olympics.person | 15 | 8 | 28 | 7 | 是 | 是 | 是 |
| 3089 | SQLite:book_publishing_company.titles | 9 | 13 | 15 | 4 | 是 | 是 | 是 |
| 3452 | SQLite:soccer_2016.Match | 10 | 17 | 11 | 5 | 是 | 是 | 是 |
| 3452 | SQLite:soccer_2016.Player_Match | 22 | 41 | 8 | 7 | 是 | 是 | 是 |
| 6116 | SQLite:movie_3.film_category | 14 | 9 | 69 | 3 | 是 | 是 | 是 |
| 3435 | SQLite:soccer_2016.Team | 23 | 22 | 25 | 8 | 是 | 是 | 是 |
| 3589 | SQLite:professional_basketball.players_teams | 9 | 3 | 23 | 5 | 是 | 是 | 是 |
| 5702 | SQLite:hockey.Master | 13 | 5 | 30 | 10 | 是 | 是 | 是 |
| 4871 | SQLite:olympics.noc_region | 14 | 25 | 24 | 8 | 是 | 是 | 是 |
| 1356 | MYSQL:ecommerce.orders | 28 | 5 | 69 | 3 | 是 | 是 | 是 |
| 3680 | SQLite:shakespeare.chapters | 9 | 13 | 11 | 3 | 是 | 是 | 是 |
| 3680 | SQLite:shakespeare.works | 83 | 33 | - | 4 | 是 | 是 | 是 |
| 1852 | MYSQL:education_2024.exam_score | 9 | 8 | 9 | 4 | 是 | 是 | 是 |
| 1852 | MYSQL:education_2025.exam_score | 10 | 9 | 16 | 4 | 是 | 是 | 是 |
| 5405 | SQLite:image_and_language.PRED_CLASSES | 51 | 16 | 177 | 6 | 是 | 是 | 是 |
| 2034 | MYSQL:education_2025.exam_score | 9 | 8 | 13 | 4 | 是 | 是 | 是 |
| 3455 | SQLite:soccer_2016.Player_Match | 25 | 23 | 25 | 7 | 是 | 是 | 是 |
| 3455 | SQLite:soccer_2016.Rolee | 92 | 55 | 188 | 18 | 是 | 是 | 是 |
| 1696 | MYSQL:education_2024.course | 16 | 9 | 34 | 6 | 否 | 否 | 否 |
| 3708 | SQLite:shakespeare.works | 61 | 40 | - | 4 | 是 | 是 | 是 |
| 1914 | MYSQL:education_2025.exam_score | 10 | 10 | 14 | 4 | 是 | 是 | 否 |

明细数据：outputs/information_retrieval/live200_rollback_v2/tail_rank_audit.json，保留schema描述、字段、命中词、竞争表和补表来源。
