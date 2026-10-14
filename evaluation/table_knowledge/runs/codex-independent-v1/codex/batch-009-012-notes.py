"""Independent manual decisions for batches 009--012.

Semantic decisions below were made after reading the full 72-table catalog,
both decoded schema texts and all 247 knowledge entries in input_context.json.
This script only copies original text, extracts verbatim schema evidence and
serializes the decisions. It performs no keyword, field or semantic matching.
"""
import json
import re
from pathlib import Path

ROOT = Path('/home/jxqu/Share/Match/V5')
CONTEXT = json.loads((ROOT / 'evaluation/table_knowledge/input_context.json').read_text())['context']
KS = {k['knowledge_id']: k['knowledge_text'] for k in CONTEXT['knowledge_context']}
CAT = {t['table_id']: t for t in CONTEXT['table_catalog']}
SOURCES = {s['source_file']: s['text'] for s in CONTEXT['schema_sources']}
CORE = 'data/赛题8/Schema/core_schema.txt'
COMMON = 'data/赛题8/Schema/commom_schema.txt'
BATCHES = [b for b in json.loads((ROOT / 'evaluation/table_knowledge/batches.json').read_text())['batches']
           if b['batch_id'] in ('batch-009', 'batch-010', 'batch-011', 'batch-012')]
DECISIONS = {t: {'accepted': [], 'candidates': [], 'content_issues': []}
             for b in BATCHES for t in b['target_table_ids']}


def ke(kid, quote=None):
    text = KS[kid] if quote is None else quote
    assert text in KS[kid], (kid, text)
    return {'knowledge_id': kid, 'quote': text}


def schema_quote(tid):
    """Mechanical extraction by the catalog's authoritative source line."""
    table = CAT[tid]
    source = SOURCES[table['source_file']]
    lines = source.splitlines(keepends=True)
    start = sum(len(x) for x in lines[:table['source_start_line'] - 1])
    if table['engine'] == 'Elasticsearch':
        end = source.index('\r\n\r\n-- =====================================================', start)
    else:
        end = source.index(';', start) + 1
    quote = source[start:end]
    assert quote in source
    evidence = [{'source_file': table['source_file'], 'quote': quote}]
    if table['database'] and table['database'] != 'common':
        scope = 'USE ' + table['database'] + ';'
        assert scope in source
        evidence.insert(0, {'source_file': table['source_file'], 'quote': scope})
    if tid == 'POSTGRESQL:public.vessel_ais_data':
        comments_start = source.index('COMMENT ON TABLE public.vessel_ais_data IS')
        evidence.append({'source_file': table['source_file'], 'quote': source[comments_start:]})
    elif tid == 'Elasticsearch:medical_institutions':
        evidence.insert(0, {'source_file': table['source_file'], 'quote': '-- 医院库（ES）'})
    return evidence


def accepted(tid, kid, basis, fields, reason, quote=None, qualifiers=(), extra_schema=()):
    assert set(fields) <= set(CAT[tid]['columns']), (tid, fields)
    assert all(q in KS[kid] for q in qualifiers)
    DECISIONS[tid]['accepted'].append({
        'knowledge_id': kid, 'basis': basis, 'fields': fields,
        'knowledge_evidence': [ke(kid, quote)],
        'schema_evidence': schema_quote(tid) + list(extra_schema),
        'qualifiers': list(qualifiers), 'reason': reason,
    })


def candidate(tid, kid, reason, quote=None):
    DECISIONS[tid]['candidates'].append({
        'knowledge_id': kid, 'knowledge_evidence': [ke(kid, quote)], 'reason': reason,
    })


def issue(tid, kid, kind, reason, evidence=None, related=()):
    DECISIONS[tid]['content_issues'].append({
        'knowledge_id': kid, 'kind': kind,
        'knowledge_evidence': evidence or [ke(kid)],
        'related_knowledge_ids': list(related), 'reason': reason,
    })


# Education: each of the sixteen tables was checked against all 247 entries.
# Semester, department, teacher and class contain no directly explained
# attribute or explicit unambiguous physical-table reference in these entries.
# Generic median/window-function/geographic rules are not table associations.
for db in ('education_2024', 'education_2025'):
    student = f'MYSQL:{db}.student'
    course = f'MYSQL:{db}.course'
    enroll = f'MYSQL:{db}.enrollment'
    score = f'MYSQL:{db}.exam_score'

    candidate(student, 1579,
              '条目涉及同一学生的跨课程总评，但学生表没有总评或成绩属性；不能仅沿选课、成绩关系把计算规则归入学生表。')
    candidate(course, 1579,
              '条目涉及多门课程的总评求和，但课程表没有总评属性；尚缺该规则直接解释课程表字段或操作的证据。')

    accepted(enroll, 1575, 'schema_supported', ['is_withdraw'],
             '原始选课表结构包含退课标记，直接对应条目的退课记录及排除规则；短表名在两个教育库重复，未按唯一显式引用处理。',
             qualifiers=['（示例）'])
    accepted(enroll, 1576, 'schema_supported', ['student_id', 'is_withdraw'],
             '选课记录同时含学生标识与退课标记，直接支持退课去重学生和选课去重学生这一计算口径。')
    candidate(enroll, 1579,
              '选课表提供学生与课程的粒度线索，但没有总评；本条未说明总评来源，也未显式引用其他总评计算知识。')
    issue(enroll, 1575, 'ambiguous_reference',
          'enrollment.is_withdraw 未注明数据库，完整目录中 education_2024、education_2025 均有该表字段；关联按各自结构支持记录，不能声称短引用唯一指定了当前库。',
          evidence=[ke(1575, 'enrollment.is_withdraw=1 的记录视为已退课，不计入成绩统计与排名。')])

    accepted(score, 1572, 'schema_supported', ['exam_item', 'score'],
             '教育成绩表以考试项目和分数保存成绩明细，直接对应条目按平时、期中、期末分数折算总评的示例计算。',
             qualifiers=['（教育教务常用口径示例）'])
    candidate(score, 1573,
              '条目针对总评成绩判定挂科，而原始表保存 exam_item、score 明细，未注明 score 为总评；本条未明确引用总评折算规则。')
    candidate(score, 1574,
              '条目把总评映射为绩点，成绩表未存储总评或绩点，也未说明哪一考试项目代表总评；不能自行补入折算步骤。')
    candidate(score, 1579,
              '成绩明细具有分数及选课关联，但本条未定义总评来源和跨课程聚合的直接口径；不能从未显式引用的其他知识补齐。')


# Ecommerce: literal SQL object references were checked as physical tables,
# with aliases and subqueries separated from physical objects.
CUSTOMER = 'MYSQL:ecommerce.customer'
PRODUCT = 'MYSQL:ecommerce.product'
INVENTORY = 'MYSQL:ecommerce.inventory'
ORDERS = 'MYSQL:ecommerce.orders'
ITEM = 'MYSQL:ecommerce.order_item'
PAYMENT = 'MYSQL:ecommerce.payment'

accepted(CUSTOMER, 1564, 'explicit', ['customer_id', 'customer_name'],
         '示例 SQL 明确读取 ecommerce.customer 作为用户标识和姓名来源；累计应付金额与排序来自示例中的订单表。',
         quote='FROM ecommerce.customer c JOIN ecommerce.orders o ON c.customer_id = o.customer_id',
         qualifiers=['通常按用户累计应付金额或累计支付金额排序。'])

accepted(PRODUCT, 1563, 'explicit', ['product_id', 'product_name'],
         '示例 SQL 明确 JOIN ecommerce.product 提取商品标识与名称，销量计算来自订单明细。',
         quote='JOIN ecommerce.product p ON oi.product_id = p.product_id',
         qualifiers=['通常按销量从高到低排序；若问题强调销售额，则按 item_amount 汇总排序。'])
accepted(PRODUCT, 1565, 'explicit', ['product_id', 'product_name'],
         '库存告警的示例 SQL 明确 JOIN ecommerce.product 取得商品名称，库存比较条件属于示例中的库存表。',
         quote='FROM ecommerce.inventory i JOIN ecommerce.product p ON i.product_id = p.product_id')
accepted(PRODUCT, 1571, 'explicit', ['product_id', 'product_name', 'category_id'],
         '类目销售排序示例明确 JOIN ecommerce.product，使用商品名称及分类标识；金额汇总来自订单明细。',
         quote='JOIN ecommerce.product p ON oi.product_id = p.product_id JOIN common.product_category pc ON p.category_id = pc.category_id',
         qualifiers=['MySQL 5.7 可通过自连接或变量实现；若训练 SQL 允许 MySQL 8，可使用窗口函数。'])

accepted(INVENTORY, 1565, 'explicit', ['product_id', 'warehouse_name', 'stock_quantity', 'safety_stock'],
         '条目明示库存表的当前库存、安全库存比较，示例直接读取该物理表。',
         quote='ecommerce.inventory.stock_quantity <= ecommerce.inventory.safety_stock')

accepted(ORDERS, 1554, 'explicit', ['total_amount', 'payable_amount'],
         '知识明示订单表商品总额汇总并给出读取 ecommerce.orders 的示例；实付要求保留原文限定。',
         quote='SQL逻辑：SUM(ecommerce.orders.total_amount)。',
         qualifiers=['通常按订单表 total_amount 汇总，不扣除优惠、退款或支付失败',
                     '若题目强调实付金额，应使用 payable_amount 或 payment_amount。',
                     '如果问题明确要求成交或实付，优先使用 payable_amount。'])
accepted(ORDERS, 1555, 'explicit', ['payable_amount', 'order_id'],
         '知识明示 ecommerce.orders 的订单应付金额和去重订单数用于客单价。',
         quote='SUM(ecommerce.orders.payable_amount) / COUNT(DISTINCT ecommerce.orders.order_id)')
accepted(ORDERS, 1556, 'explicit', ['order_id', 'payable_amount'],
         '知识明示订单应付金额汇总，支付事实要求由示例 JOIN 的支付表承担。',
         quote='FROM ecommerce.orders o JOIN ecommerce.payment p ON o.order_id = p.order_id',
         qualifiers=['若需要以支付事实为准，应关联 payment 并筛选 SUCCESS。',
                     '若题目出现支付成功，必须关联 payment 并筛选 payment_status_code = \'SUCCESS\'。'])
accepted(ORDERS, 1558, 'explicit', ['order_id'],
         '退款率示例明确读取订单表作为订单总数分母，退款判断来自订单明细。',
         quote='FROM ecommerce.orders o LEFT JOIN ecommerce.order_item oi ON o.order_id = oi.order_id',
         qualifiers=['可按退款订单数占订单数计算。', '订单明细存在 refund_amount 大于 0 时，可认为发生退款。'])
accepted(ORDERS, 1559, 'explicit', ['customer_id', 'order_id'],
         '复购率示例的内层查询明确按订单表用户分组统计订单数，外层 t 是子查询别名。',
         quote='FROM (SELECT customer_id, COUNT(DISTINCT order_id) AS order_count FROM ecommerce.orders GROUP BY customer_id) t')
accepted(ORDERS, 1564, 'explicit', ['customer_id', 'payable_amount'],
         '高价值用户知识明示按订单应付金额排序，示例直接 JOIN 订单表进行用户累计。',
         quote='ORDER BY SUM(ecommerce.orders.payable_amount) DESC',
         qualifiers=['通常按用户累计应付金额或累计支付金额排序。'])
accepted(ORDERS, 1566, 'explicit', ['order_time', 'payable_amount'],
         '知识明示用订单表下单时间的年月维度汇总应付金额。',
         quote="GROUP BY DATE_FORMAT(ecommerce.orders.order_time, '%Y-%m')")
accepted(ORDERS, 1567, 'explicit', ['customer_id'],
         '知识明示对 ecommerce.orders.customer_id 去重统计下单用户。',
         quote='COUNT(DISTINCT ecommerce.orders.customer_id)')
accepted(ORDERS, 1568, 'explicit', ['order_status_code'],
         '知识明示订单表完成状态的条件及完成率计算。',
         quote="ecommerce.orders.order_status_code = 'COMPLETED'")
accepted(ORDERS, 1569, 'explicit', ['customer_id', 'order_time'],
         '最近订单示例在外层和聚合子查询中均读取真实订单表，t 是子查询别名。',
         quote='FROM ecommerce.orders o JOIN (SELECT customer_id, MAX(order_time) AS max_order_time FROM ecommerce.orders GROUP BY customer_id) t',
         qualifiers=['可使用窗口函数或 MySQL 5.7 兼容的子查询。',
                     'MySQL 5.7 不支持 ROW_NUMBER，可用聚合子查询实现。'])
accepted(ORDERS, 1570, 'explicit', ['customer_id', 'payable_amount', 'order_id'],
         '用户客单价与全局客单价的示例子查询均明确读取订单表。',
         quote='FROM (SELECT customer_id, SUM(payable_amount) / COUNT(DISTINCT order_id) AS user_aov FROM ecommerce.orders GROUP BY customer_id) t')

accepted(ITEM, 1558, 'explicit', ['order_id', 'refund_amount'],
         '知识明示订单明细退款金额条件，示例将退款订单与订单总数分别统计。',
         quote='CASE WHEN ecommerce.order_item.refund_amount > 0 THEN ecommerce.order_item.order_id END',
         qualifiers=['可按退款订单数占订单数计算。', '订单明细存在 refund_amount 大于 0 时，可认为发生退款。'])
accepted(ITEM, 1560, 'explicit', ['item_amount', 'item_cost_amount'],
         '知识明示订单明细应付金额减成本金额的毛利汇总。',
         quote='SUM(ecommerce.order_item.item_amount - ecommerce.order_item.item_cost_amount)')
accepted(ITEM, 1561, 'explicit', ['item_amount', 'item_cost_amount'],
         '毛利率示例明确读取 ecommerce.order_item，使用该表金额和成本计算。',
         quote='FROM ecommerce.order_item')
accepted(ITEM, 1562, 'explicit', ['quantity', 'product_id'],
         '知识明示订单明细购买数量汇总，示例按商品标识分组。',
         quote='SUM(ecommerce.order_item.quantity)',
         qualifiers=['一般使用 order_item.quantity。'])
accepted(ITEM, 1563, 'explicit', ['product_id', 'quantity', 'item_amount'],
         '热销商品知识明示按订单明细数量排序，并保留强调销售额时改按金额的条件。',
         quote='ORDER BY SUM(ecommerce.order_item.quantity) DESC',
         qualifiers=['通常按销量从高到低排序；若问题强调销售额，则按 item_amount 汇总排序。'])
accepted(ITEM, 1571, 'explicit', ['product_id', 'item_amount', 'quantity'],
         '类目内排名示例明确从订单明细汇总商品销售额；原文也列出按购买数量排序的口径。',
         quote='FROM ecommerce.order_item oi JOIN ecommerce.product p ON oi.product_id = p.product_id',
         qualifiers=['MySQL 5.7 可通过自连接或变量实现；若训练 SQL 允许 MySQL 8，可使用窗口函数。'])

accepted(PAYMENT, 1554, 'schema_supported', ['payment_amount'],
         '条目在强调实付时明示 payment_amount；支付表原始字段注释直接标识为支付金额，按该限定记录关联。',
         quote='若题目强调实付金额，应使用 payable_amount 或 payment_amount。',
         qualifiers=['若题目强调实付金额，应使用 payable_amount 或 payment_amount。'])
accepted(PAYMENT, 1556, 'explicit', ['order_id', 'payment_status_code'],
         '知识的支付事实示例明确 JOIN ecommerce.payment 并筛选支付成功状态。',
         quote="JOIN ecommerce.payment p ON o.order_id = p.order_id WHERE p.payment_status_code = 'SUCCESS'",
         qualifiers=['若需要以支付事实为准，应关联 payment 并筛选 SUCCESS。',
                     '若题目出现支付成功，必须关联 payment 并筛选 payment_status_code = \'SUCCESS\'。'])
accepted(PAYMENT, 1557, 'explicit', ['payment_status_code'],
         '知识明示支付表成功状态占全部支付记录的比例。',
         quote="ecommerce.payment.payment_status_code = 'SUCCESS'")


# AIS: accept rules that directly constrain vessel position, course, speed,
# draught or navigation state. Geographic boundaries alone, communication,
# piloting, signals or overtaking without an observable rule remain candidates.
AIS = 'POSTGRESQL:public.vessel_ais_data'
POS = ['longitude', 'latitude', 'geom']

accepted(AIS, 1719, 'schema_supported', POS,
         '禁航规则明确约束所有船舶驶入所列水域，船舶AIS表的位置字段直接支持该空间操作约束；保留临时禁航限定。',
         quote='该区域为军事演习或武器试验临时禁航区，禁止所有船舶驶入。',
         qualifiers=['该区域为军事演习或武器试验临时禁航区', '禁航时段通常由海事部门通过航行警告提前发布'])
accepted(AIS, 1720, 'schema_supported', POS + ['cog'],
         '知识明确给出该水域进出港船舶的真航向与逆向禁令，直接对应AIS位置与航向属性。',
         quote='进港主交通流向282°（真航向），出港主交通流向103°。')
accepted(AIS, 1721, 'schema_supported', POS + ['sog', 'nav_status'],
         '航道内船舶限速和禁止锚泊直接解释AIS航速、航行状态在给定水域的条件。',
         quote='航道内限速12节，禁止追越和锚泊。')
accepted(AIS, 1724, 'schema_supported', POS + ['nav_status'],
         '知识明确禁止船舶在所列航道内锚泊，AIS位置与航行状态直接对应这一约束；不补写状态代码。',
         quote='船舶应沿浮筒标示的航槽行驶，禁止在航道内锚泊或捕捞。')
accepted(AIS, 1726, 'schema_supported', POS + ['sog'],
         '所列航道的船舶限速直接对应AIS位置和航速；VTS通信和引航信息不扩充为本表字段。',
         quote='航道内限速10节，大型船舶需申请引航。')
accepted(AIS, 1727, 'schema_supported', POS + ['nav_status'],
         '警戒区内禁止船舶抛锚的规则直接对应位置与航行状态；不自行指定锚泊状态数值。',
         quote='禁止在警戒区内抛锚或进行捕鱼作业。')
accepted(AIS, 1728, 'schema_supported', POS + ['cog'],
         '知识对进出港船舶方向和使用分道作出空间航向约束，直接对应船舶位置与航向属性。',
         quote='西行船舶（进港）走北侧分道，东行船舶（出港）走南侧分道。')
accepted(AIS, 1730, 'schema_supported', POS,
         '知识明确禁止船舶在军事训练禁航期间进入给定多边形水域，直接约束船舶AIS位置。',
         quote='该区域为军事训练禁航区，定期发布航行警告禁止船舶进入。',
         qualifiers=['该区域为军事训练禁航区，定期发布航行警告禁止船舶进入。'])
accepted(AIS, 1731, 'schema_supported', POS + ['cog', 'nav_status'],
         '分道方向与海峡内禁止锚泊直接对应AIS位置、航向和航行状态；不新增分道边界或状态代码。',
         quote='进港船舶（向北）使用东侧分道，出港船舶（向南）使用西侧分道。')
accepted(AIS, 1732, 'schema_supported', POS,
         '禁航期间任何船舶不得驶入所列四点水域，直接约束AIS船舶空间位置。',
         quote='禁航期间任何船舶不得驶入，否则将面临军事处罚。',
         qualifiers=['禁航期间任何船舶不得驶入'])
accepted(AIS, 1733, 'schema_supported', POS + ['sog', 'draught'],
         '航道限速与吃水条件直接涉及AIS航速、吃水及位置属性；高潮通过仍作为原文条件保留。',
         quote='航道内限速8节，禁止追越。',
         qualifiers=['吃水超过9米的船舶应乘高潮通过。'])
accepted(AIS, 1734, 'schema_supported', POS + ['nav_status'],
         '航道内禁止船舶锚泊直接对应位置和航行状态；引航、报告等内容不推定为本表可记录事实。',
         quote='航道内禁止锚泊，大型船舶需引航。')
accepted(AIS, 1735, 'schema_supported', POS + ['cog'],
         '进出港船舶按南北方向使用东西分道的规则直接约束AIS航向与位置属性。',
         quote='进港船舶（向北）使用东侧分道，出港船舶（向南）使用西侧分道，分隔带为虚拟线段。')
accepted(AIS, 1736, 'schema_supported', POS + ['sog'],
         '给定航道内的船舶限速直接对应AIS航速和空间位置。',
         quote='航道内限速10节，禁止在航道内追越。')
accepted(AIS, 1737, 'schema_supported', POS,
         '知识明确民用船舶应避开给定圆形禁航区并保持距离，直接约束AIS船舶位置。',
         quote='民用船舶应保持与禁航区边界至少2海里的安全距离，不得进入。',
         qualifiers=['为某部海军训练区，全年禁航。', '民用船舶应保持与禁航区边界至少2海里的安全距离，不得进入。'])
accepted(AIS, 1738, 'schema_supported', POS + ['sog'],
         '所列航道船舶限速直接对应AIS位置与航速；锚地安全间距仍保留为原文一般要求。',
         quote='航道内限速8节，锚地内船舶应保持安全间距，避免锚泊碰撞。')
accepted(AIS, 1739, 'schema_supported', ['nav_status', 'sog'],
         '知识定义异常航行记录并明示航行状态、航速字段，原始AIS字段注释直接对应；规则残缺与状态解释冲突另行记录。')
accepted(AIS, 1740, 'schema_supported', ['nav_status'],
         '知识解释停泊所含航行状态取值，直接对应原始AIS航行状态字段；不裁定与另一条的代码解释冲突。')
accepted(AIS, 1741, 'schema_supported', POS,
         '军事禁航期间任何船舶不得进入所列多边形水域，直接约束AIS船舶位置。',
         quote='禁航期间任何船舶不得驶入，过往船舶应绕行外海，保持VHF16频道守听。',
         qualifiers=['禁航期间任何船舶不得驶入'])
accepted(AIS, 1742, 'schema_supported', POS + ['sog'],
         '所列航道内的船舶限速直接对应AIS位置和航速。',
         quote='航道内限速10节，大型船舶需引航。')
accepted(AIS, 1744, 'schema_supported', POS + ['nav_status'],
         '知识明确禁止船舶在所列航道内锚泊，直接对应AIS位置与航行状态。',
         quote='禁止在航道内锚泊。')
accepted(AIS, 1746, 'schema_supported', POS + ['sog'],
         '港内船舶限速直接对应AIS位置与航速属性；不补入追越判定算法。',
         quote='港内限速8节，禁止追越。')
accepted(AIS, 1748, 'schema_supported', POS + ['draught'],
         '知识明确按船舶吃水条件限制通航，AIS表包含船舶吃水和位置属性；乘高潮仍保留为条件。',
         quote='吃水超过7米的船舶应乘高潮通过。',
         qualifiers=['吃水超过7米的船舶应乘高潮通过。'])
accepted(AIS, 1749, 'schema_supported', POS + ['sog'],
         '航道内船舶限速直接对应AIS位置与航速。',
         quote='航道内限速10节。')
accepted(AIS, 1751, 'schema_supported', POS + ['nav_status'],
         '所列航道内禁止船舶锚泊直接对应AIS位置和航行状态，未从潮汐叙述补写通航时点。',
         quote='船舶应选择高平潮时段进出港，禁止在航道内锚泊。')
accepted(AIS, 1753, 'schema_supported', POS + ['sog'],
         '航道内船舶限速直接对应AIS位置与航速。',
         quote='航道内限速8节。')
accepted(AIS, 1758, 'schema_supported', POS + ['sog'],
         '航道内船舶限速直接对应AIS位置与航速。',
         quote='航道内限速8节。')
accepted(AIS, 1760, 'schema_supported', POS + ['nav_status'],
         '知识明确航道内禁止船舶锚泊，直接对应AIS位置和航行状态；不自行补写状态代码。',
         quote='航道内实行分道通航，禁止锚泊。')
accepted(AIS, 1777, 'schema_supported', ['sog'],
         '船舶航速单位说明和通常高速阈值直接解释原始AIS航速属性；保留通常限定。',
         qualifiers=['高速船舶通常指航速≥25节。'])
accepted(AIS, 1790, 'schema_supported', ['mmsi'],
         '知识解释船舶MMSI前三位国家码，原始AIS字段注释明确为船舶MMSI码。')

# Full primary excerpts preserve the zone boundary and the actual vessel rule
# together, so no geographic coordinates are merely inferred from an isolated
# sentence. This is original-text copying after the decisions above.
for entry in DECISIONS[AIS]['accepted']:
    if entry['knowledge_id'] in [1719, 1720, 1721, 1724, 1726, 1727, 1728, 1730,
                                1731, 1732, 1733, 1734, 1735, 1736, 1737, 1738,
                                1741, 1742, 1744, 1746, 1748, 1749, 1751, 1753,
                                1758, 1760]:
        entry['knowledge_evidence'] = [ke(entry['knowledge_id'])]

for kid, reason in [
    (1713, '条目仅定义禁航水域多边形，未明确船舶记录或本表查询条件；AIS表保存船舶点位置，不保存禁航区对象。'),
    (1714, '条目仅定义禁捕管理区域，缺少该区域与AIS船舶记录查询或操作约束的直接说明，不能仅凭空间字段确认。'),
    (1715, '条目仅描述管制区起止水域，未给出直接针对AIS记录属性的条件或明确表对象。'),
    (1716, '条目提供监管区地理边界，未说明船舶记录的具体条件；不能只因AIS含经纬度而确认关联。'),
    (1717, '条目提供某次实弹训练禁航区边界，未说明船舶记录的具体适用时段或直接查询条件。'),
    (1718, '条目提供天津港及禁航、管制水域位置，未明确本表对象或对船舶记录属性的直接条件。'),
    (1722, '条目主要定义航道并要求守听、按潮汐通航和引航；Schema没有通信、潮汐或引航属性，不能从区域坐标推定关联。'),
    (1723, '条目定义锚地并要求锚泊信号、守听及排污约束；AIS结构没有这些属性，也没有载重字段支持十万吨级条件。'),
    (1725, '条目提供航道、锚地坐标并要求遵守外部制度，未给出可直接对应AIS字段的船舶条件。'),
    (1729, '条目给出航道、锚地和载重适用范围及外部规定；AIS没有最大载重字段，地理边界本身不足以确认。'),
    (1743, '航道内禁止追越有潜在线索，但原文未给出由AIS记录判定追越的规则；不能自行补充轨迹或相对运动算法。'),
    (1745, '条目定义航道、锚地并要求遵守外部制度和报告，Schema未记录这些制度或报告属性。'),
    (1747, '安全航速、靠离泊作业区等要求有船舶线索，但安全阈值、沿岸边界和作业区均未提供，不能补成AIS条件。'),
    (1750, '条目描述航道及分道制、守听和法规要求，未给出分道方向或位置条件；Schema不记录通信和法规遵守情况。'),
    (1752, '条目主要给出航道警戒区与VTS、引航要求；AIS没有引航属性，且大型船舶条件未定义。'),
    (1754, '条目提出安全航速和加强瞭望的一般要求，未定义安全阈值，Schema也没有瞭望属性，具体AIS条件无法确认。'),
    (1755, '条目给出航道、报告和大型船舶引航要求，AIS没有报告或引航属性，大型条件也未定义。'),
    (1756, '条目禁止航道内追越，但未提供从AIS字段判断追越的口径；其余主要是区域坐标和报告要求。'),
    (1757, '条目主要定义航道并要求遵守定线制与VTS报告，没有给出直接对应AIS字段的方向、速度或状态条件。'),
    (1759, '条目提供区域边界并要求大型船舶引航，AIS不含引航属性，且大型条件未定义，不能仅据空间字段确认。'),
]:
    candidate(AIS, kid, reason)

issue(AIS, 1739, 'incomplete_rule',
      'sog15、sog0.5 缺失比较符，状态条件与航速条件的连接范围也未完整写出；不补写阈值方向。',
      evidence=[ke(1739, 'nav_status=1（航行中）sog15或sog0.5')])
issue(AIS, 1739, 'conflicting_content',
      '同一 nav_status=1 在1739被标为航行中，在1740被标为锚泊；不选定其中一方。',
      evidence=[ke(1739, 'nav_status=1（航行中）'), ke(1740, 'nav_status=1锚泊')], related=[1740])
issue(AIS, 1740, 'conflicting_content',
      '同一 nav_status=1 在1740被标为锚泊，在1739被标为航行中；不选定其中一方。',
      evidence=[ke(1740, 'nav_status=1锚泊'), ke(1739, 'nav_status=1（航行中）')], related=[1739])


# Medical index: named hospitals have the same object/name/location attributes;
# other landmark coordinates and regional lists are not propagated here.
MED = 'Elasticsearch:medical_institutions'
for kid in [1696, 1697, 1698, 1699, 1700, 1701, 1702]:
    accepted(MED, kid, 'schema_supported', ['name', 'location'],
             '知识给出具名医院及其经纬度，原始医院索引中的名称与geo_point位置直接支持同一对象的位置属性。')

for kid, fields, reason in [
    (1703, ['bed_count', 'doctor_count'], '大型医院的床位数和医生数条件直接对应原始医院索引的两个数量属性。'),
    (1704, ['has_icu', 'ambulance_count', 'rating'], '知识明确的ICU、救护车和评分条件直接对应医院索引属性；未自行添加其他筛选条件。'),
    (1705, ['doctor_count', 'annual_outpatient'], '医生数或年门诊量的条件直接对应医院索引的医生数量和年门诊量属性。'),
    (1706, ['annual_outpatient'], '高负荷医院按年门诊量定义，原始医院索引直接保存该属性。'),
    (1707, ['emergency_24h', 'ambulance_count'], '24小时急诊与救护车数量的条件直接对应原始医院索引属性。'),
    (1708, ['is_teaching_hospital'], '教学医院定义直接解释原始医院索引中是否教学医院的布尔属性。'),
    (1709, ['bed_count', 'annual_outpatient'], '超大规模医院的床位数和年门诊量条件直接对应医院索引属性。'),
    (1710, ['nurse_count', 'bed_count'], '护士数量及床位数与护士数比值所需属性均由原始医院索引直接提供。'),
    (1711, ['has_icu', 'department_count'], 'ICU与科室数量的现代化医院定义直接对应原始医院索引属性。'),
    (1712, ['founded_year', 'rating'], '成立年份和评分的老牌知名医院标准直接对应原始医院索引属性。'),
]:
    accepted(MED, kid, 'schema_supported', fields, reason)


def validate_and_write():
    for batch in BATCHES:
        main = []
        audits = []
        for tid in batch['target_table_ids']:
            d = DECISIONS[tid]
            for name in ('accepted', 'candidates'):
                d[name].sort(key=lambda x: x['knowledge_id'])
                ids = [x['knowledge_id'] for x in d[name]]
                assert len(ids) == len(set(ids)), (tid, name)
            assert not ({x['knowledge_id'] for x in d['accepted']} & {x['knowledge_id'] for x in d['candidates']})
            d['content_issues'].sort(key=lambda x: x['knowledge_id'])
            associated = {x['knowledge_id'] for x in d['accepted'] + d['candidates']}
            for group in ('accepted', 'candidates', 'content_issues'):
                for a in d[group]:
                    assert a['knowledge_id'] in KS
                    assert any(e['knowledge_id'] == a['knowledge_id'] for e in a['knowledge_evidence'])
                    for e in a['knowledge_evidence']:
                        assert e['quote'] in KS[e['knowledge_id']], (tid, group, e)
                    if group != 'content_issues':
                        assert all(e['knowledge_id'] == a['knowledge_id'] for e in a['knowledge_evidence'])
                    else:
                        assert a['knowledge_id'] in associated
                        assert a['kind'] in ('incomplete_rule', 'conflicting_content', 'missing_reference', 'ambiguous_reference')
                    if group == 'accepted':
                        assert len(a['fields']) == len(set(a['fields']))
                        assert set(a['fields']) <= set(CAT[tid]['columns'])
                        for e in a['schema_evidence']:
                            assert e['quote'] in SOURCES[e['source_file']], (tid, e)
                        assert all(q in KS[a['knowledge_id']] for q in a['qualifiers'])
            main.append({'table_id': tid, 'knowledge': [
                {'knowledge_id': a['knowledge_id'], 'knowledge_text': KS[a['knowledge_id']]}
                for a in d['accepted']]})
            audits.append({'table_id': tid, **d,
                           'needs_human_review': bool(d['candidates'] or d['content_issues'])})
        result = {'tables': main, 'audit': {
            'rubric_version': 'table-knowledge-reference-v2', 'batch_id': batch['batch_id'],
            'status': 'complete', 'input_issues': [],
            'reviewed_knowledge_ids': [k['knowledge_id'] for k in CONTEXT['knowledge_context']],
            'table_audit': audits,
        }}
        assert len(result['audit']['reviewed_knowledge_ids']) == 247
        assert [t['table_id'] for t in main] == batch['target_table_ids']
        assert [t['table_id'] for t in audits] == batch['target_table_ids']
        for t, a in zip(main, audits):
            assert [k['knowledge_id'] for k in t['knowledge']] == [x['knowledge_id'] for x in a['accepted']]
        dest = ROOT / 'evaluation/table_knowledge/runs/codex-independent-v1/codex' / (batch['batch_id'] + '.json')
        dest.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
        print(batch['batch_id'], 'tables', len(main), 'accepted', sum(len(a['accepted']) for a in audits),
              'candidates', sum(len(a['candidates']) for a in audits),
              'content_issues', sum(len(a['content_issues']) for a in audits))


if __name__ == '__main__':
    validate_and_write()
