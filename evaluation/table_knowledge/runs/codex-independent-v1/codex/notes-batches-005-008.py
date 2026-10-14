"""Independent manual semantic decisions for batches 005–008.
The program only copies original text, extracts declared schema excerpts, formats
manual decisions, and validates strings. It does not select semantic labels.
"""
import json
from pathlib import Path

ROOT=Path('/home/jxqu/Share/Match/V5')
C=json.loads((ROOT/'evaluation/table_knowledge/input_context.json').read_text())['context']
K={x['knowledge_id']: x['knowledge_text'] for x in C['knowledge_context']}
T={x['table_id']:x for x in C['table_catalog']}
S={x['source_file']:x['text'] for x in C['schema_sources']}
B=json.loads((ROOT/'evaluation/table_knowledge/batches.json').read_text())['batches']
OUT=ROOT/'evaluation/table_knowledge/runs/codex-independent-v1/codex'
D={}

def tid(name):
    if ':' in name:return name
    return 'MYSQL:'+name

def table_quote(name):
    t=T[tid(name)]
    text=S[t['source_file']]
    lines=text.splitlines(keepends=True)
    start=t['source_start_line']-1
    quote=''
    for line in lines[start:]:
        quote+=line
        if line.rstrip().endswith(';'):break
    assert quote in text
    return {'source_file': t['source_file'], 'quote':quote.rstrip('\r\n')}

def literal_schema(quote, source='data/赛题8/Schema/commom_schema.txt'):
    assert quote in S[source],quote
    return {'source_file':source,'quote':quote}

def init(name):
    name=tid(name)
    D[name]={'accepted':[],'candidates':[],'content_issues':[]}
    return name

def accept(name,k,fields,reason,basis='schema_supported',quotes=None,qualifiers=None,extra_schema=None):
    name=tid(name)
    if name not in D:init(name)
    assert set(fields)<=set(T[name]['columns'])
    if quotes is None:quotes=[K[k]]
    for q in quotes:assert q in K[k],(k,q)
    for q in qualifiers or []:assert q in K[k],(k,q)
    D[name]['accepted'].append({'knowledge_id':k,'basis':basis,'fields':fields,
        'knowledge_evidence':[{'knowledge_id':k,'quote':q} for q in quotes],
        'schema_evidence':[table_quote(name)]+(extra_schema or []),
        'qualifiers':qualifiers or [],'reason':reason})

def candidate(name,k,reason,quotes=None):
    name=tid(name)
    if name not in D:init(name)
    if quotes is None:quotes=[K[k]]
    for q in quotes:assert q in K[k]
    D[name]['candidates'].append({'knowledge_id':k,'knowledge_evidence':[{'knowledge_id':k,'quote':q} for q in quotes], 'reason':reason})

def issue(name,k,kind,reason,related=None):
    name=tid(name)
    ev=[{'knowledge_id':k,'quote':K[k]}]
    for r in related or []:
        if r in K:ev.append({'knowledge_id':r,'quote':K[r]})
    D[name]['content_issues'].append({'knowledge_id':k,'kind':kind,'knowledge_evidence':ev,
        'related_knowledge_ids':related or [],'reason':reason})

# All 247 entries have been individually considered against each of these tables.
for batch in B[4:8]:
    for name in batch['target_table_ids']:init(name)

# Education dictionaries. None of the unrelated employee-status, generic-time,
# regional-definition, or business-domain entries is assigned by name similarity.
exam_rows=literal_schema("INSERT INTO dict_exam_item (item_code, item_name, default_weight) VALUES\r\n('平时', '平时成绩', 0.35),\r\n('期中', '期中考试', 0.45),\r\n('期末', '期末考试', 0.75);")
accept('common.dict_exam_item',1572,['item_code','item_name','default_weight'],
       '本条示例直接规定平时、期中、期末项目的成绩权重；本表以相同考试项目记录默认权重，按示例限定关联。',
       qualifiers=['教育教务常用口径示例'],extra_schema=[exam_rows])
issue('common.dict_exam_item',1572,'conflicting_content',
      '知识示例权重为平时0.30、期中0.30、期末0.40；原始Schema的本表初始化默认权重分别为0.35、0.45、0.75，不能混为同一默认口径。')
grade_rows=literal_schema("INSERT INTO dict_grade_level (grade_level, min_score, max_score, grade_point) VALUES\r\n('A', 90, 100, 4.0),\r\n('B', 80, 89, 3.0),\r\n('C', 70, 79, 2.0),\r\n('D', 60, 69, 1.0),\r\n('F', 0, 59, 0.0);")
accept('common.dict_grade_level',1574,['min_score','max_score','grade_point'],
       '本条总评分段与绩点映射对应本表分数上下限和绩点，Schema初始化值提供直接对应。',
       qualifiers=['示例映射'],extra_schema=[grade_rows])
candidate('common.dict_grade_level',1573,
          '本表有分数段、等级与绩点，但原始Schema未明示哪个等级代表不合格或挂科，且没有总评字段；仅凭F或低绩点不能确认此挂科规则适用于本表。')

# Administrative-code rules explicitly operate on area_id. Schema excerpts
# establish the administrative-code meaning, rather than matching a bare name.
area_tables=['transportation.vehicle_company','transportation.driver','transportation.vehicle',
             'transportation.shipping_company','transportation.vessel','energy.energy_company',
             'energy.energy_station','energy.supply_area']
for name in area_tables:
    accept(name,1761,['area_id'],
           '本条直接解释行政区划字段area_id的编码和分组；本表area_id注释为区划代码，类型为CHAR(6)且引用统一行政区划表。',
           extra_schema=[table_quote('common.administrative_division')])
    for k in [1793,1799,1800]:
        accept(name,k,['area_id'],
               '本条明确给出行政区划area_id的省级过滤表达式；本表以area_id记录行政区划并引用统一行政区划表，支持该查询条件。',
               extra_schema=[table_quote('common.administrative_division')])
    candidate(name,1596,
              '条目描述县级市、地级市及省直管县的代码特征，但未明示使用本表area_id；Schema仅说明区划代码，没有县级市或地级市判别属性，保留代码口径适用范围待核。')

# The enterprise side of the cancellation/retirement distinction applies to
# each schema-declared enterprise status; no employee status is substituted.
for name in ['transportation.vehicle_company','transportation.shipping_company','energy.energy_company']:
    accept(name,1592,['status'],
           '本条对企业status=注销的解释直接对应本表企业经营状态中的注销；关联限于企业状态部分。',
           quotes=["企业 status='注销' 表示企业主体消亡"])

accept('transportation.vehicle_company',1787,['business_type'],
       '本条明确涉及驾驶员所属公司business_type；Schema将驾驶员定义为车辆公司员工，车辆公司经营类型包含客运、货运、危化品运输。',
       extra_schema=[table_quote('transportation.driver')])
accept('transportation.vehicle_company',1791,['business_type'],
       '本条显式指定唯一的vehicle_company表及其business_type筛选。',basis='explicit',qualifiers=['通常'])

license_rows=literal_schema("INSERT INTO common.license_type_dict (license_code, license_name) VALUES\r\n('A1', '大型客车'),\r\n('A2', '牵引车'),\r\n('A3', '城市公交车'),\r\n('B1', '中型客车'),\r\n('B2', '大型货车'),\r\n('C1', '小型汽车'),\r\n('C2', '小型自动挡汽车'),\r\n('C3', '低速载货汽车'),\r\n('C4', '三轮汽车');")
accept('transportation.driver',1768,['license_type'],
       '驾驶员表的驾照类型代码引用驾照字典；本条明确解释该类驾照代码及准驾车型，字典值核对了代码对象。',
       extra_schema=[license_rows])
accept('transportation.driver',1769,['status'],
       '本条驾驶员驾照状态的四个取值与Schema驾照状态枚举逐项对应。')
accept('transportation.driver',1773,['issue_date','valid_years'],
       '本条驾驶证有效期规则直接使用发证日期和有效年数，与驾驶员表两字段注释直接对应。')
issue('transportation.driver',1773,'incomplete_rule',
      '本条提到第三次换证为长期，并称可用issue_date和valid_years计算到期日，但没有说明长期有效在valid_years中的表示及其到期处理。')
accept('transportation.driver',1783,['birth_date'],
       '本条明确按驾驶员年龄分组，Schema在驾驶员对象上提供出生日期，直接支持该年龄条件。')
issue('transportation.driver',1783,'incomplete_rule',
      '中年写作30-45岁，老年写作45岁以上；45岁处的区间边界未明确是否重叠，不能自行选择比较符。')
accept('transportation.driver',1787,['license_type','company_id'],
       '本条描述驾驶员资格类型与license_type及所属公司经营类型的对应；Schema直接记录驾照类型及所属车辆公司。',
       extra_schema=[table_quote('transportation.vehicle_company')])
accept('transportation.driver',1792,['issue_date'],
       '本条明确用驾驶员issue_date计算领证年限分段，Schema该字段即发证日期。')
accept('transportation.driver',1798,['birth_date'],
       '本条直接定义低龄驾驶员年龄条件，驾驶员表出生日期提供同一对象的年龄依据。',qualifiers=['一般'])

vehicle_rows=literal_schema("INSERT INTO common.vehicle_type_dict (type_code, type_name, category) VALUES\r\n('BUS', '客车', '客运'),\r\n('TRUCK', '货车', '货运'),\r\n('HAZMAT', '危化品车', '特种'),\r\n('VAN', '面包车', '货运'),\r\n('MINIBUS', '小型客车', '客运'),\r\n('DUMP', '自卸车', '货运'),\r\n('TANKER', '罐式车', '特种'),\r\n('REFRIGERATED', '冷藏车', '特种');")
accept('transportation.vehicle',1762,['load_capacity'],
       '本条按车辆载重分段；本表载重字段以吨为单位，直接对应分段对象及属性。')
accept('transportation.vehicle',1765,['vehicle_type_code','seat_count'],
       '本条解释货车、危化品车和客车称呼，并以座位数限制小客车；本表记录车辆类型代码和客车座位数，字典明确这些类型对象。',
       qualifiers=['仅当运输危化品时','座位数≥9'],extra_schema=[vehicle_rows])
accept('transportation.vehicle',1770,['register_date'],
       '本条车辆注册年份表达式直接使用本表注释为注册日期的register_date。',qualifiers=['例如'])
accept('transportation.vehicle',1772,['insurance_expire'],
       '本条车辆保险过期条件直接解释本表保险到期日字段及过期后的上路约束。')
accept('transportation.vehicle',1775,['vehicle_type_code','load_capacity'],
       '本条以货车和载重阈值定义黄蓝牌车辆；本表记录车辆类型和吨载重，支持该条件。',extra_schema=[vehicle_rows])
accept('transportation.vehicle',1781,['brand'],
       '本条直接提供车辆品牌含电动关键词的新能源筛选条件；本表brand注释为车辆品牌。')
accept('transportation.vehicle',1782,['vehicle_type_code','manufacture_year'],
       '本条货车报废条件直接使用生产年份manufacture_year，车辆表具有该属性及车辆类型。',extra_schema=[vehicle_rows])
accept('transportation.vehicle',1785,['vehicle_type_code','load_capacity'],
       '本条明确把重型货车条件写为load_capacity阈值；本表该字段为吨载重并有车辆类型。',qualifiers=['通常'],extra_schema=[vehicle_rows])
issue('transportation.vehicle',1785,'conflicting_content',
      '知识1762把重型车阈值写为载重>15吨，本条通常把重型货车写为load_capacity≥12吨；货车在12至15吨区间的重型口径不同，需保留两条限定交由人审。',related=[1762])
accept('transportation.vehicle',1788,['vehicle_type_code','seat_count'],
       '本条免费对象限定为7座及以下小型客车；车辆表具有类型和客车座位数，关联依据为该适用对象部分。',
       quotes=['免费对象为7座及以下小型客车。'],extra_schema=[vehicle_rows])
accept('transportation.vehicle',1789,['register_date'],
       '本条直接以车辆register_date定义老旧车辆，Schema字段即注册日期。',qualifiers=['以当前日期计算'])
candidate('transportation.vehicle',1771,
          '车辆类型可涉及危化品车，但Schema没有押运员或从业资格证属性，无法核实本条要求的配备和持证约束。')
candidate('transportation.vehicle',1784,
          '本表能表达危险品车辆类型，但无罐体检测、合格标志或备注字段；本条若有的存储说明不能确认对应本表。')

accept('transportation.employee',1586,['status'],
       '本条关于在职、离职、退休的员工状态解释对应船舶公司员工status枚举；关联依据限于这三项。',
       quotes=['员工状态“在职”表示当前在岗，“离职”表示已离开企业，“退休”表示已办理退休手续'])
accept('transportation.vessel',1776,['max_load'],
       '本条船舶万吨轮阈值直接使用max_load，Schema为最大荷载量且单位吨。')
accept('transportation.vessel',1777,['max_speed'],
       '本条节与海里/小时的单位解释直接对应船舶最大航速字段中的节；依据为单位解释部分。',
       quotes=['船舶航速单位“节”等于海里/小时，1节≈1.852公里/小时。'])
accept('transportation.vessel',1786,['endurance'],
       '本条直接解释船舶endurance自持力，与Schema自持力天/海里字段对应。')
accept('transportation.vessel',1790,['mmsi'],
       '本条解释船舶MMSI的国家码部分，本表mmsi明确为船舶9位唯一标识。')

# Finance and tax: explicit table.field references are kept separate from
# direct schema-supported metric components; no foreign-key propagation.
for k,field in [(1616,'is_key_high_tech'),(1618,'is_tech_advanced_service'),(1619,'established_year'),(1620,'registered_capital'),(1621,'is_private')]:
    accept('finance_tax.companies',k,[field],
           '本条显式引用companies的真实字段，目录唯一定位公司主表。',basis='explicit')
accept('finance_tax.companies',1630,['is_key_high_tech'],
       '本条高新技术企业的税率条件对应公司表的重点扶持高新技术企业标志；仅据该企业属性部分建立关联。')
accept('finance_tax.companies',1652,['is_key_high_tech'],
       '本条明确引用companies.is_key_high_tech解释认定标志与税率。',basis='explicit',qualifiers=['若为TRUE'])
accept('finance_tax.companies',1656,['is_tech_advanced_service'],
       '本条定义技术先进型服务企业优惠，公司表具有明确的同一企业资格标志。')
for k,fields in [(1659,['industry_code']),(1660,['size_category_code']),(1661,['established_year']),(1663,['registration_type_code'])]:
    accept('finance_tax.companies',k,fields,
           '本条显式指定companies的真实属性及其用途。',basis='explicit')
accept('finance_tax.companies',1662,['is_key_high_tech'],
       '本条直接解释高新技术企业标志应优先于行业推断；Schema该字段明确记录同一资格。')
accept('finance_tax.companies',1664,['company_id','industry_code'],
       '本条按企业所属行业计算集中度，公司主表直接记录企业标识及所属行业；依据限于行业分组对象。')

for k,field in [(1604,'total_shares'),(1605,'current_price')]:
    accept('finance_tax.stocks',k,[field],
           '本条显式引用stocks真实字段并解释其含义及单位。',basis='explicit',qualifiers=['通常'] if k==1605 else [])
accept('finance_tax.stocks',1624,['total_shares'],
       '每股净资产公式明确使用总股本total_shares；股票表该字段为发行股数，直接对应分母。')
accept('finance_tax.stocks',1625,['current_price'],
       '市净率公式明确以股价为分子；股票表current_price为最新股票价格，直接提供该价格属性。',
       quotes=['市净率(P/B)计算公式：股价 / 每股净资产'])
accept('finance_tax.stocks',1627,['current_price'],
       '本条股息率公式明确使用股票价格；股票表最新股票价格与该股价属性对应。')
accept('finance_tax.stocks',1632,['current_price','total_shares'],
       '市盈率公式明确使用current_price和total_shares，股票表同时记录最新价格与总股本。')
accept('finance_tax.stocks',1633,['total_shares'],
       '换手率公式明确以total_shares作分母，股票表股本字段与这一股票属性对应。')
accept('finance_tax.stocks',1635,['total_shares'],
       '每股收益公式明确使用total_shares总股本，股票表该字段为股数。')
accept('finance_tax.stocks',1644,['current_price','total_shares'],
       '本条股票总市值公式直接使用股票表中的最新价格及总股本，并与Schema单位对应。')
accept('finance_tax.stocks',1646,['total_shares'],
       '本条每股现金分红公式以total_shares总股本为分母，股票表直接记录该股数。')
for k,field in [(1648,'share_right_type'),(1649,'register_type'),(1650,'par_value_type'),(1651,'market_class')]:
    accept('finance_tax.stocks',k,[field],
           '本条显式引用stocks真实字段，并解释该字段分类取值。',basis='explicit')
candidate('finance_tax.stocks',1638,
          '本条提及以每股收益/每股净资产替代ROE，但股票表没有这两个指标；本条未给出从股票表股本、价格推导二者的规则，不能借用相邻知识补全。')

accept('finance_tax.stock_daily_trades',1622,['volume','close_price'],
       '日成交总价值近似公式直接使用成交量与收盘价，本表同一日成交对象具有这两个属性。',qualifiers=['近似'])
accept('finance_tax.stock_daily_trades',1623,['volume','close_price'],
       '本条描述日成交均价并允许近似使用收盘价；本表日成交量和收盘价与这两个属性直接对应。',qualifiers=['可近似使用收盘价代替'])
accept('finance_tax.stock_daily_trades',1633,['volume'],
       '本条换手率公式使用股票成交量volume，Schema本表明确为每日成交量股数。')
accept('finance_tax.stock_daily_trades',1636,['open_price','close_price'],
       '日涨跌幅公式直接使用开盘价和收盘价，本表为股票日成交汇总并有两个真实价格字段。')
accept('finance_tax.stock_daily_trades',1640,['trade_date','open_price','close_price'],
       '年化波动率规则明确以日开收盘价计算涨跌幅，本表记录交易日期及日开收盘价。',qualifiers=['250为年交易日数近似值'])
accept('finance_tax.stock_daily_trades',1643,['trade_date','high_price','low_price','close_price'],
       '本条年度股价波幅使用最高、最低及收盘价均值；日成交表记录交易日期和相应股票价格，支持按年汇总。',qualifiers=['年内均价可用收盘价均值近似'])

for k,field in [(1606,'dividend_cash'),(1607,'dividend_stock'),(1608,'total_assets'),(1609,'total_liabilities')]:
    accept('finance_tax.company_financials',k,[field],
           '本条显式引用company_financials真实字段并解释含义及单位。',basis='explicit')
accept('finance_tax.company_financials',1624,['total_assets'],
       '本条每股净资产公式将总资产从万元转元；本表为公司财务摘要，total_assets注释为总资产万元，直接支持该财务分子。')
accept('finance_tax.company_financials',1626,['total_assets','total_liabilities'],
       '本库特殊净利润定义直接使用财务总资产和总负债，Schema同时明确这两个财务属性。',qualifiers=['本库特殊定义，实际净利润≠资产-负债'])
accept('finance_tax.company_financials',1627,['dividend_stock'],
       '股息率公式直接使用dividend_stock并由分/股转元/股，Schema本表该字段注释为每股股息分/股。')
accept('finance_tax.company_financials',1632,['total_assets','total_liabilities'],
       '市盈率近似公式中的资产减负债部分直接对应本表总资产、总负债，二者单位同为万元。',qualifiers=['近似计算公式'])
accept('finance_tax.company_financials',1634,['total_liabilities','total_assets'],
       '资产负债率公式直接使用财务总负债和总资产，Schema同时给出同单位的对应字段。')
accept('finance_tax.company_financials',1635,['total_assets','total_liabilities'],
       '每股收益近似公式直接以总资产减总负债作分子，本表财务字段及万元单位对应。',qualifiers=['近似计算公式'])
accept('finance_tax.company_financials',1637,['dividend_cash','total_assets','total_liabilities'],
       '红利支付率公式直接使用现金分红、总资产与总负债，Schema本表三项含义及万元单位直接对应。')
accept('finance_tax.company_financials',1638,['total_assets','total_liabilities'],
       '本条明确用total_assets-total_liabilities表示净利润，并令净资产=total_assets；财务表具备对应资产负债属性，保留本库定义。',qualifiers=['本库中以每股收益/每股净资产替代计算'])
accept('finance_tax.company_financials',1645,['total_assets','total_liabilities'],
       '本条ROA使用总资产及本库定义的资产减负债净利润，直接对应公司财务表两个字段。',qualifiers=['本库中净利润 = total_assets - total_liabilities'])
accept('finance_tax.company_financials',1646,['dividend_cash'],
       '每股现金分红公式直接使用dividend_cash并由万元转元，Schema现金分红总额字段及单位对应。')
candidate('finance_tax.company_financials',1625,
          '本条市净率需要每股净资产，但本表只有总资产且没有每股净资产或总股本；本条未给出换算规则，不能使用未被显式引用的知识1624补全。')
candidate('finance_tax.company_financials',1642,
          '本表有财务总资产，但没有收入总额；条目也未指定资产来源。另有年度申报表同时记录收入与季度平均资产，不能仅凭总资产词语把本表作为已确认来源。')

for k,field in [(1610,'revenue'),(1611,'non_taxable_income'),(1612,'deductions'),(1613,'prior_year_losses'),(1614,'employee_count'),(1615,'total_assets'),(1617,'is_restricted_industry')]:
    accept('finance_tax.corporate_income_tax_returns',k,[field],
           '本条显式引用corporate_income_tax_returns真实字段，其语义及单位与Schema对应。',basis='explicit')
accept('finance_tax.corporate_income_tax_returns',1628,['revenue','non_taxable_income','deductions','prior_year_losses'],
       '本条应纳税所得额公式直接使用本表四项申报属性，Schema对含义及万元单位作了对应说明。')
accept('finance_tax.corporate_income_tax_returns',1629,['employee_count','total_assets','is_restricted_industry'],
       '小型微利判定直接规定从业人数、资产总额及限制行业条件，Schema申报表记录相同对象及属性；依据为这三项条件。')
accept('finance_tax.corporate_income_tax_returns',1639,['revenue'],
       '本条实际税负率明确以收入总额作分母，申报表revenue注释为收入总额，直接支持该分母属性。')
accept('finance_tax.corporate_income_tax_returns',1641,['total_assets'],
       '本条明确指定申报表中的全年季度平均资产总额，本表total_assets的对象、季度平均口径及单位直接对应。')
accept('finance_tax.corporate_income_tax_returns',1642,['revenue','total_assets'],
       '本条周转率直接使用企业收入总额及资产总额，Schema本表同时记录这两项申报属性。')
accept('finance_tax.corporate_income_tax_returns',1647,['revenue','deductions'],
       '本条扣除后利润率公式直接使用revenue与deductions，Schema本表分别为收入总额和扣除金额。')
accept('finance_tax.corporate_income_tax_returns',1653,[],
       '本条明确把小型微利企业判定对象指定为年度申报数据，Schema本表为企业所得税年度申报信息；判定内容的缺失引用单列审计。')
issue('finance_tax.corporate_income_tax_returns',1653,'missing_reference',
      '本条指向知识108，但完整247条输入没有该ID，无法核对其所称判定条件；不能用内容相似的其他知识替换。',related=[108])
accept('finance_tax.corporate_income_tax_returns',1655,['is_restricted_industry'],
       '本条明确引用本表is_restricted_industry并解释其值与优惠限制。',basis='explicit',qualifiers=['若corporate_income_tax_returns.is_restricted_industry为TRUE'])
accept('finance_tax.corporate_income_tax_returns',1658,['deductions'],
       '本条明确说明本库研发加计扣除包含在deductions字段，Schema企业所得税申报表以该字段记录扣除金额。',qualifiers=['本库中加计扣除包含在deductions字段内'])
accept('finance_tax.corporate_income_tax_returns',1664,['company_id','revenue'],
       '本条企业行业集中度以企业收入排序及汇总，申报表直接记录公司标识与收入总额；关联依据为企业收入部分。')
candidate('finance_tax.corporate_income_tax_returns',1624,
          '本表也有万元资产总额，但其口径为全年季度平均；每股净资产条目没有指定资产来源，另有财务总资产表，不能仅凭total_assets同名确认使用申报平均资产。')
candidate('finance_tax.corporate_income_tax_returns',1630,
          '条目给出高新技术、小型微利和其他企业的税率；本表没有这些企业类别或税率字段，本条也未提供由本表现有字段判定小型微利的条件，需补充明确适用依据。')
candidate('finance_tax.corporate_income_tax_returns',1631,
          '条目公式的应纳税所得额与适用税率都不是本表字段，本条未解释如何由申报属性取得二者；不能借用邻近但未显式引用的知识补全。')
candidate('finance_tax.corporate_income_tax_returns',1652,
          '本条明确引用companies.is_key_high_tech解释资格和税率，但本表没有该资格或税率属性；仅可通过公司外键连接不足以确认归属。')
candidate('finance_tax.corporate_income_tax_returns',1654,
          '条目仅给出一般企业税率，没有指定申报表或可核对的税率字段；Schema也没有一般企业判定属性，保留其对本表计算适用性待核。')
candidate('finance_tax.corporate_income_tax_returns',1656,
          '本条优惠税率依赖技术先进型服务企业资格，本表没有该资格或税率属性，不能仅沿公司外键传播。')
candidate('finance_tax.corporate_income_tax_returns',1657,
          '条目描述小型微利企业应纳税所得额与税率，但未指明本表、未提供由本表字段判定资格或计算应纳税所得额的规则；本表无这些直接属性。')

# Energy objects and direct field semantics.
accept('energy.energy_company',1580,['staff_count','area_id'],
       '本条明确按能源企业注册地统计员工，Schema能源企业表同时记录员工总数和注册地区划代码。')
accept('energy.energy_company',1593,['business_type'],
       '本条直接以能源企业business_type=新能源定义企业类别，Schema能源企业表具有经营类型字段。')
accept('energy.energy_company',1595,['staff_count'],
       '本条以staff_count划分企业员工规模，Schema能源企业表该字段明确为员工总数。')
candidate('energy.energy_company',1587,
          '本条列出发电集团和电网企业名称及EC代码，但未明确表或字段；原始Schema没有这些企业实例、代码约定或集团归属属性，不能仅以能源行业推定对应记录。')
accept('energy.company_certification',1584,['cert_type','expire_date','issue_authority'],
       '本条直接解释企业资质类型、发证机关及过期条件，Schema企业资质表具有这三个对应属性。')
accept('energy.company_certification',1588,['expire_date'],
       '本条资质已过期及半年内到期条件直接使用expire_date，Schema企业资质表该字段即到期日期。')
energy_rows=literal_schema("INSERT INTO energy_type_dict (type_code, type_name, category, is_renewable) VALUES\r\n('THERMAL', '火电', '传统能源', 0),\r\n('HYDRO', '水电', '清洁能源', 1),\r\n('WIND', '风电', '新能源', 1),\r\n('SOLAR', '光伏', '新能源', 1),\r\n('NUCLEAR', '核电', '清洁能源', 0),\r\n('BIOMASS', '生物质发电', '新能源', 1),\r\n('GAS', '天然气发电', '清洁能源', 0),\r\n('PUMPED', '抽水蓄能', '清洁能源', 1),\r\n('GEOTHERMAL', '地热发电', '新能源', 1),\r\n('HYDROGEN', '氢能', '新能源', 1);")
station_rows=literal_schema("INSERT INTO station_type_dict (type_code, type_name, category) VALUES\r\n('PP', '发电厂', '发电'),\r\n('SUB', '变电站', '变电'),\r\n('TL', '输电线路', '输电'),\r\n('DS', '配电站', '配电'),\r\n('WP', '风电场', '发电'),\r\n('SP', '光伏电站', '发电'),\r\n('HP', '水电站', '发电'),\r\n('NP', '核电站', '发电'),\r\n('ES', '储能站', '配电'),\r\n('CC', '集控中心', '变电');")
accept('energy.energy_station',1581,['energy_type_code'],
       '本条能源类型代码与分类直接解释场站的能源类型属性；Schema该字段明确引用能源类型字典，字典原始值核对同一代码对象。',extra_schema=[energy_rows])
accept('energy.energy_station',1582,['station_type_code'],
       '本条场站类型代码解释对应场站表的类型属性，Schema该字段引用场站类型字典，原始字典值核对代码对象。',extra_schema=[station_rows])
accept('energy.energy_station',1583,['installed_capacity','annual_generation','energy_type_code'],
       '本条直接解释场站装机容量与年发电量单位，并按能源类型给出容量条件；Schema具备相应属性且单位一致。',extra_schema=[energy_rows])
accept('energy.energy_station',1591,['status'],
       '本条场站运行状态四个取值及含义，与Schema能源场站status枚举直接对应。')
accept('energy.energy_station',1592,['status'],
       '本条场站status=退役的解释直接对应能源场站运行状态；依据为场站状态部分。',
       quotes=["场站 status='退役' 表示该设施永久关停但所属企业可能仍在运营。"])
accept('energy.energy_station',1593,['energy_type_code','company_id'],
       '本条直接描述新能源企业所属场站的能源类型代码；场站表记录所属企业及能源类型，Schema字典核对给定能源代码。',qualifiers=['通常'],extra_schema=[energy_rows])
accept('energy.energy_station',1594,['energy_type_code','annual_generation'],
       '本条抽水蓄能场站发电量及统计排除条件直接对应能源类型代码和年发电量属性。',extra_schema=[energy_rows])
accept('energy.energy_station',1597,['energy_type_code','installed_capacity'],
       '本条清洁能源装机占比使用清洁类型装机及总装机；场站表记录装机容量，能源类型字典原文明确清洁类别。',
       quotes=['清洁能源装机占比 = 清洁能源装机容量 / 总装机容量 × 100%。'],extra_schema=[energy_rows])
accept('energy.energy_station',1600,['energy_type_code','annual_generation','installed_capacity'],
       '本条火电场站效率条件直接涉及年发电量、装机容量与火电类型，Schema能源场站具有对应对象属性。',qualifiers=['约为4500小时'],extra_schema=[energy_rows])
accept('energy.energy_station',1601,['annual_generation','installed_capacity'],
       '本条年利用小时公式明确给出万kWh与MW的换算，场站表年发电量和装机容量字段的单位逐项对应。')
accept('energy.energy_station',1603,['installed_capacity','station_type_code'],
       '本条直接以发电场站装机容量定义小型场站；Schema提供装机容量MW及场站类型，原始类型字典标明发电类。',extra_schema=[station_rows])
candidate('energy.energy_station',1602,
          '本条以年利用小时数判定高效，但Schema没有该指标字段；本条未给出由年发电量和装机容量取得年利用小时数的公式，不能使用未显式引用的相邻条目补全。')
accept('energy.supply_area',1585,['supply_level','area_id'],
       '本条划分供电区域等级，Schema本表直接记录供电等级和供电区域代码，属于同一供电区域对象。')
accept('energy.supply_area',1599,['household_count'],
       '本条按供电户数划分区域规模，本表household_count注释为供电户数，直接对应阈值属性。')
accept('energy.employee',1580,['employee_id','company_id'],
       '本条明确统计能源企业员工数量并按所属企业注册地归集；Schema本表为能源企业员工并记录员工标识、所属企业，关联限于员工及企业归属部分。',
       extra_schema=[table_quote('energy.energy_company')])
accept('energy.employee',1586,['status'],
       '本条在职、离职、退休、外派的员工状态解释，与Schema能源企业员工status四个枚举逐项对应。')
accept('energy.employee',1589,['education','position_code'],
       '本条直接描述员工学历与岗位代码的通常对应，Schema能源企业员工具有学历、岗位代码并引用能源岗位字典。',qualifiers=['通常'],
       extra_schema=[table_quote('common.energy_position_dict')])

# Mechanical validation and formatting. Every decision above was manually made.
for batch in B[4:8]:
    names=batch['target_table_ids']
    result={'tables':[],'audit':{'rubric_version':'table-knowledge-reference-v2',
            'batch_id':batch['batch_id'],'status':'complete','input_issues':[],
            'reviewed_knowledge_ids':[x['knowledge_id'] for x in C['knowledge_context']],
            'table_audit':[]}}
    for name in names:
        audit=D[name]
        for key in ['accepted','candidates','content_issues']:
            audit[key].sort(key=lambda x:x['knowledge_id'])
        accepted_ids=[x['knowledge_id'] for x in audit['accepted']]
        candidate_ids=[x['knowledge_id'] for x in audit['candidates']]
        assert len(accepted_ids)==len(set(accepted_ids))
        assert len(candidate_ids)==len(set(candidate_ids))
        assert not set(accepted_ids)&set(candidate_ids)
        for a in audit['accepted']:
            assert set(a['fields'])<=set(T[name]['columns'])
            assert len(a['fields'])==len(set(a['fields']))
            assert a['basis'] in ['explicit','schema_supported']
            for e in a['schema_evidence']:assert e['quote'] in S[e['source_file']]
            for q in a['qualifiers']:assert q in K[a['knowledge_id']]
        for key in ['accepted','candidates','content_issues']:
            for a in audit[key]:
                assert any(e['knowledge_id']==a['knowledge_id'] for e in a['knowledge_evidence'])
                for e in a['knowledge_evidence']:assert e['quote'] in K[e['knowledge_id']]
        result['tables'].append({'table_id':name,'knowledge':[{'knowledge_id':k,'knowledge_text':K[k]} for k in accepted_ids]})
        result['audit']['table_audit'].append({'table_id':name,**audit,
                    'needs_human_review':bool(audit['candidates'] or audit['content_issues'])})
    dest=OUT/(batch['batch_id']+'.json')
    dest.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(batch['batch_id'],'tables',len(names),'accepted',sum(len(D[n]['accepted']) for n in names),
          'candidates',sum(len(D[n]['candidates']) for n in names),
          'issues',sum(len(D[n]['content_issues']) for n in names))
