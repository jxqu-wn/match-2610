# Codex 单方待审事项

此清单来自已冻结的 Codex 初次标注，尚未与 Flash 比对，不是人类裁定。原文证据保存在 review_pending.json 和 frozen/audit.json。

| 表 | 知识ID | 类型 | 待判定问题 |
|---|---:|---|---|
| MYSQL:common.administrative_division | 1596 | conflicting_content | 知识称地级市代码前4位以00结尾，原始Schema却列苏州市320500和南京市320100为level=2；两例前4位分别为3205、3201，与该断言冲突，未修改任何代码规则。 |
| MYSQL:common.vessel_type_dict | 1777 | candidate | 字典有高速客船名称，但本条定义的是高速船舶的一般航速阈值，未说明是否界定字典中的高速客船类型，字典也没有航速属性，不能确认直接适用范围。 |
| MYSQL:common.license_type_dict | 1787 | candidate | 本条提及license_type并列出从业资格类型，但未给出这些资格与字典驾照代码的对应关系，无法确认它是否直接解释本字典取值。 |
| MYSQL:common.energy_type_dict | 1597 | candidate | 清洁能源、新能源与字典大类名称相符，但本条核心为双碳目标和装机占比，字典不含装机容量，也未明确指定字典作为分类来源，无法确认该计算对字典的直接适用范围。 |
| MYSQL:common.customer_level_dict | 1564 | candidate | 字典说明中有高价值用户和核心高价值用户，但字典等级依据最低成长值，本条依据累计应付或支付金额排序，未说明排序结果与会员等级的映射，不能确认同一口径。 |
| MYSQL:common.dict_exam_item | 1572 | conflicting_content | 知识示例权重为平时0.30、期中0.30、期末0.40；原始Schema的本表初始化默认权重分别为0.35、0.45、0.75，不能混为同一默认口径。 |
| MYSQL:common.dict_grade_level | 1573 | candidate | 本表有分数段、等级与绩点，但原始Schema未明示哪个等级代表不合格或挂科，且没有总评字段；仅凭F或低绩点不能确认此挂科规则适用于本表。 |
| MYSQL:transportation.vehicle_company | 1596 | candidate | 条目描述县级市、地级市及省直管县的代码特征，但未明示使用本表area_id；Schema仅说明区划代码，没有县级市或地级市判别属性，保留代码口径适用范围待核。 |
| MYSQL:transportation.driver | 1596 | candidate | 条目描述县级市、地级市及省直管县的代码特征，但未明示使用本表area_id；Schema仅说明区划代码，没有县级市或地级市判别属性，保留代码口径适用范围待核。 |
| MYSQL:transportation.driver | 1773 | incomplete_rule | 本条提到第三次换证为长期，并称可用issue_date和valid_years计算到期日，但没有说明长期有效在valid_years中的表示及其到期处理。 |
| MYSQL:transportation.driver | 1783 | incomplete_rule | 中年写作30-45岁，老年写作45岁以上；45岁处的区间边界未明确是否重叠，不能自行选择比较符。 |
| MYSQL:transportation.vehicle | 1596 | candidate | 条目描述县级市、地级市及省直管县的代码特征，但未明示使用本表area_id；Schema仅说明区划代码，没有县级市或地级市判别属性，保留代码口径适用范围待核。 |
| MYSQL:transportation.vehicle | 1771 | candidate | 车辆类型可涉及危化品车，但Schema没有押运员或从业资格证属性，无法核实本条要求的配备和持证约束。 |
| MYSQL:transportation.vehicle | 1784 | candidate | 本表能表达危险品车辆类型，但无罐体检测、合格标志或备注字段；本条若有的存储说明不能确认对应本表。 |
| MYSQL:transportation.vehicle | 1785 | conflicting_content | 知识1762把重型车阈值写为载重>15吨，本条通常把重型货车写为load_capacity≥12吨；货车在12至15吨区间的重型口径不同，需保留两条限定交由人审。 |
| MYSQL:transportation.shipping_company | 1596 | candidate | 条目描述县级市、地级市及省直管县的代码特征，但未明示使用本表area_id；Schema仅说明区划代码，没有县级市或地级市判别属性，保留代码口径适用范围待核。 |
| MYSQL:transportation.vessel | 1596 | candidate | 条目描述县级市、地级市及省直管县的代码特征，但未明示使用本表area_id；Schema仅说明区划代码，没有县级市或地级市判别属性，保留代码口径适用范围待核。 |
| MYSQL:finance_tax.stocks | 1638 | candidate | 本条提及以每股收益/每股净资产替代ROE，但股票表没有这两个指标；本条未给出从股票表股本、价格推导二者的规则，不能借用相邻知识补全。 |
| MYSQL:finance_tax.company_financials | 1625 | candidate | 本条市净率需要每股净资产，但本表只有总资产且没有每股净资产或总股本；本条未给出换算规则，不能使用未被显式引用的知识1624补全。 |
| MYSQL:finance_tax.company_financials | 1642 | candidate | 本表有财务总资产，但没有收入总额；条目也未指定资产来源。另有年度申报表同时记录收入与季度平均资产，不能仅凭总资产词语把本表作为已确认来源。 |
| MYSQL:finance_tax.corporate_income_tax_returns | 1624 | candidate | 本表也有万元资产总额，但其口径为全年季度平均；每股净资产条目没有指定资产来源，另有财务总资产表，不能仅凭total_assets同名确认使用申报平均资产。 |
| MYSQL:finance_tax.corporate_income_tax_returns | 1630 | candidate | 条目给出高新技术、小型微利和其他企业的税率；本表没有这些企业类别或税率字段，本条也未提供由本表现有字段判定小型微利的条件，需补充明确适用依据。 |
| MYSQL:finance_tax.corporate_income_tax_returns | 1631 | candidate | 条目公式的应纳税所得额与适用税率都不是本表字段，本条未解释如何由申报属性取得二者；不能借用邻近但未显式引用的知识补全。 |
| MYSQL:finance_tax.corporate_income_tax_returns | 1652 | candidate | 本条明确引用companies.is_key_high_tech解释资格和税率，但本表没有该资格或税率属性；仅可通过公司外键连接不足以确认归属。 |
| MYSQL:finance_tax.corporate_income_tax_returns | 1654 | candidate | 条目仅给出一般企业税率，没有指定申报表或可核对的税率字段；Schema也没有一般企业判定属性，保留其对本表计算适用性待核。 |
| MYSQL:finance_tax.corporate_income_tax_returns | 1656 | candidate | 本条优惠税率依赖技术先进型服务企业资格，本表没有该资格或税率属性，不能仅沿公司外键传播。 |
| MYSQL:finance_tax.corporate_income_tax_returns | 1657 | candidate | 条目描述小型微利企业应纳税所得额与税率，但未指明本表、未提供由本表字段判定资格或计算应纳税所得额的规则；本表无这些直接属性。 |
| MYSQL:finance_tax.corporate_income_tax_returns | 1653 | missing_reference | 本条指向知识108，但完整247条输入没有该ID，无法核对其所称判定条件；不能用内容相似的其他知识替换。 |
| MYSQL:energy.energy_company | 1587 | candidate | 本条列出发电集团和电网企业名称及EC代码，但未明确表或字段；原始Schema没有这些企业实例、代码约定或集团归属属性，不能仅以能源行业推定对应记录。 |
| MYSQL:energy.energy_company | 1596 | candidate | 条目描述县级市、地级市及省直管县的代码特征，但未明示使用本表area_id；Schema仅说明区划代码，没有县级市或地级市判别属性，保留代码口径适用范围待核。 |
| MYSQL:energy.energy_station | 1596 | candidate | 条目描述县级市、地级市及省直管县的代码特征，但未明示使用本表area_id；Schema仅说明区划代码，没有县级市或地级市判别属性，保留代码口径适用范围待核。 |
| MYSQL:energy.energy_station | 1602 | candidate | 本条以年利用小时数判定高效，但Schema没有该指标字段；本条未给出由年发电量和装机容量取得年利用小时数的公式，不能使用未显式引用的相邻条目补全。 |
| MYSQL:energy.supply_area | 1596 | candidate | 条目描述县级市、地级市及省直管县的代码特征，但未明示使用本表area_id；Schema仅说明区划代码，没有县级市或地级市判别属性，保留代码口径适用范围待核。 |
| MYSQL:education_2024.student | 1579 | candidate | 条目涉及同一学生的跨课程总评，但学生表没有总评或成绩属性；不能仅沿选课、成绩关系把计算规则归入学生表。 |
| MYSQL:education_2024.course | 1579 | candidate | 条目涉及多门课程的总评求和，但课程表没有总评属性；尚缺该规则直接解释课程表字段或操作的证据。 |
| MYSQL:education_2024.enrollment | 1579 | candidate | 选课表提供学生与课程的粒度线索，但没有总评；本条未说明总评来源，也未显式引用其他总评计算知识。 |
| MYSQL:education_2024.enrollment | 1575 | ambiguous_reference | enrollment.is_withdraw 未注明数据库，完整目录中 education_2024、education_2025 均有该表字段；关联按各自结构支持记录，不能声称短引用唯一指定了当前库。 |
| MYSQL:education_2024.exam_score | 1573 | candidate | 条目针对总评成绩判定挂科，而原始表保存 exam_item、score 明细，未注明 score 为总评；本条未明确引用总评折算规则。 |
| MYSQL:education_2024.exam_score | 1574 | candidate | 条目把总评映射为绩点，成绩表未存储总评或绩点，也未说明哪一考试项目代表总评；不能自行补入折算步骤。 |
| MYSQL:education_2024.exam_score | 1579 | candidate | 成绩明细具有分数及选课关联，但本条未定义总评来源和跨课程聚合的直接口径；不能从未显式引用的其他知识补齐。 |
| MYSQL:education_2025.student | 1579 | candidate | 条目涉及同一学生的跨课程总评，但学生表没有总评或成绩属性；不能仅沿选课、成绩关系把计算规则归入学生表。 |
| MYSQL:education_2025.course | 1579 | candidate | 条目涉及多门课程的总评求和，但课程表没有总评属性；尚缺该规则直接解释课程表字段或操作的证据。 |
| MYSQL:education_2025.enrollment | 1579 | candidate | 选课表提供学生与课程的粒度线索，但没有总评；本条未说明总评来源，也未显式引用其他总评计算知识。 |
| MYSQL:education_2025.enrollment | 1575 | ambiguous_reference | enrollment.is_withdraw 未注明数据库，完整目录中 education_2024、education_2025 均有该表字段；关联按各自结构支持记录，不能声称短引用唯一指定了当前库。 |
| MYSQL:education_2025.exam_score | 1573 | candidate | 条目针对总评成绩判定挂科，而原始表保存 exam_item、score 明细，未注明 score 为总评；本条未明确引用总评折算规则。 |
| MYSQL:education_2025.exam_score | 1574 | candidate | 条目把总评映射为绩点，成绩表未存储总评或绩点，也未说明哪一考试项目代表总评；不能自行补入折算步骤。 |
| MYSQL:education_2025.exam_score | 1579 | candidate | 成绩明细具有分数及选课关联，但本条未定义总评来源和跨课程聚合的直接口径；不能从未显式引用的其他知识补齐。 |
| POSTGRESQL:public.vessel_ais_data | 1713 | candidate | 条目仅定义禁航水域多边形，未明确船舶记录或本表查询条件；AIS表保存船舶点位置，不保存禁航区对象。 |
| POSTGRESQL:public.vessel_ais_data | 1714 | candidate | 条目仅定义禁捕管理区域，缺少该区域与AIS船舶记录查询或操作约束的直接说明，不能仅凭空间字段确认。 |
| POSTGRESQL:public.vessel_ais_data | 1715 | candidate | 条目仅描述管制区起止水域，未给出直接针对AIS记录属性的条件或明确表对象。 |
| POSTGRESQL:public.vessel_ais_data | 1716 | candidate | 条目提供监管区地理边界，未说明船舶记录的具体条件；不能只因AIS含经纬度而确认关联。 |
| POSTGRESQL:public.vessel_ais_data | 1717 | candidate | 条目提供某次实弹训练禁航区边界，未说明船舶记录的具体适用时段或直接查询条件。 |
| POSTGRESQL:public.vessel_ais_data | 1718 | candidate | 条目提供天津港及禁航、管制水域位置，未明确本表对象或对船舶记录属性的直接条件。 |
| POSTGRESQL:public.vessel_ais_data | 1722 | candidate | 条目主要定义航道并要求守听、按潮汐通航和引航；Schema没有通信、潮汐或引航属性，不能从区域坐标推定关联。 |
| POSTGRESQL:public.vessel_ais_data | 1723 | candidate | 条目定义锚地并要求锚泊信号、守听及排污约束；AIS结构没有这些属性，也没有载重字段支持十万吨级条件。 |
| POSTGRESQL:public.vessel_ais_data | 1725 | candidate | 条目提供航道、锚地坐标并要求遵守外部制度，未给出可直接对应AIS字段的船舶条件。 |
| POSTGRESQL:public.vessel_ais_data | 1729 | candidate | 条目给出航道、锚地和载重适用范围及外部规定；AIS没有最大载重字段，地理边界本身不足以确认。 |
| POSTGRESQL:public.vessel_ais_data | 1743 | candidate | 航道内禁止追越有潜在线索，但原文未给出由AIS记录判定追越的规则；不能自行补充轨迹或相对运动算法。 |
| POSTGRESQL:public.vessel_ais_data | 1745 | candidate | 条目定义航道、锚地并要求遵守外部制度和报告，Schema未记录这些制度或报告属性。 |
| POSTGRESQL:public.vessel_ais_data | 1747 | candidate | 安全航速、靠离泊作业区等要求有船舶线索，但安全阈值、沿岸边界和作业区均未提供，不能补成AIS条件。 |
| POSTGRESQL:public.vessel_ais_data | 1750 | candidate | 条目描述航道及分道制、守听和法规要求，未给出分道方向或位置条件；Schema不记录通信和法规遵守情况。 |
| POSTGRESQL:public.vessel_ais_data | 1752 | candidate | 条目主要给出航道警戒区与VTS、引航要求；AIS没有引航属性，且大型船舶条件未定义。 |
| POSTGRESQL:public.vessel_ais_data | 1754 | candidate | 条目提出安全航速和加强瞭望的一般要求，未定义安全阈值，Schema也没有瞭望属性，具体AIS条件无法确认。 |
| POSTGRESQL:public.vessel_ais_data | 1755 | candidate | 条目给出航道、报告和大型船舶引航要求，AIS没有报告或引航属性，大型条件也未定义。 |
| POSTGRESQL:public.vessel_ais_data | 1756 | candidate | 条目禁止航道内追越，但未提供从AIS字段判断追越的口径；其余主要是区域坐标和报告要求。 |
| POSTGRESQL:public.vessel_ais_data | 1757 | candidate | 条目主要定义航道并要求遵守定线制与VTS报告，没有给出直接对应AIS字段的方向、速度或状态条件。 |
| POSTGRESQL:public.vessel_ais_data | 1759 | candidate | 条目提供区域边界并要求大型船舶引航，AIS不含引航属性，且大型条件未定义，不能仅据空间字段确认。 |
| POSTGRESQL:public.vessel_ais_data | 1739 | incomplete_rule | sog15、sog0.5 缺失比较符，状态条件与航速条件的连接范围也未完整写出；不补写阈值方向。 |
| POSTGRESQL:public.vessel_ais_data | 1739 | conflicting_content | 同一 nav_status=1 在1739被标为航行中，在1740被标为锚泊；不选定其中一方。 |
| POSTGRESQL:public.vessel_ais_data | 1740 | conflicting_content | 同一 nav_status=1 在1740被标为锚泊，在1739被标为航行中；不选定其中一方。 |
