# 纯程序关联评估：tfidf

以LLM＋人工审核的270对关联为目标；算法只读原始Schema、知识及可选训练划分（本轮2555条）。训练增强模式：sql。

当前结果为同集开发评估，阈值选择参考了该基准；不代表未见数据上的成绩。

| 算法 | 命中 | 多关联 | 漏关联 | Precision | Recall | F1 |
| --- | --- | --- | --- | --- | --- | --- |
| 旧主目录规则 | 0 | 0 | 270 | 未定义 | 0.00% | 0.00% |
| 纯程序新规则 | 195 | 46 | 75 | 80.91% | 72.22% | 76.32% |

答案非空表完全覆盖：22/44；全部表完全覆盖：50/72。

## 逐表差异

| 表 | 命中 | 多关联ID | 漏关联ID |
| --- | --- | --- | --- |
| MYSQL:common.administrative_division | 4 | — | 1590, 1596, 1598, 1763, 1779, 1780, 1793, 1794, 1795, 1796, 1797, 1800 |
| MYSQL:common.vehicle_type_dict | 2 | 1787, 1788 | — |
| MYSQL:common.vessel_type_dict | 0 | 1728, 1737, 1787 | — |
| MYSQL:common.employee_type_dict | 0 | — | — |
| MYSQL:common.license_type_dict | 1 | 1765 | — |
| MYSQL:common.dict_registration_type | 1 | — | — |
| MYSQL:common.dict_size_category | 2 | 1599, 1762, 1768 | — |
| MYSQL:common.dict_stock_type | 4 | — | — |
| MYSQL:common.dict_industry | 1 | — | — |
| MYSQL:common.energy_type_dict | 4 | 1582, 1583, 1598 | — |
| MYSQL:common.voltage_level_dict | 0 | — | — |
| MYSQL:common.energy_position_dict | 1 | — | — |
| MYSQL:common.station_type_dict | 1 | 1583 | — |
| MYSQL:common.cert_type_dict | 1 | 1773 | — |
| MYSQL:common.product_category | 1 | — | — |
| MYSQL:common.customer_level_dict | 0 | — | — |
| MYSQL:common.customer_status_dict | 0 | — | — |
| MYSQL:common.product_status_dict | 0 | — | — |
| MYSQL:common.order_status_dict | 1 | — | — |
| MYSQL:common.payment_method_dict | 0 | — | — |
| MYSQL:common.payment_status_dict | 2 | — | — |
| MYSQL:common.refund_reason_dict | 0 | — | — |
| MYSQL:common.order_channel_dict | 0 | — | — |
| MYSQL:common.platform_dict | 0 | — | — |
| MYSQL:common.dict_gender | 0 | — | — |
| MYSQL:common.dict_academic_level | 0 | 1589 | — |
| MYSQL:common.dict_student_status | 0 | — | — |
| MYSQL:common.dict_course_type | 0 | — | — |
| MYSQL:common.dict_exam_item | 1 | — | — |
| MYSQL:common.dict_take_mode | 0 | — | — |
| MYSQL:common.dict_semester_type | 0 | — | — |
| MYSQL:common.dict_grade_level | 1 | — | 1573 |
| MYSQL:transportation.vehicle_company | 5 | — | 1761, 1787 |
| MYSQL:transportation.driver | 8 | 1592 | 1769, 1783, 1798 |
| MYSQL:transportation.vehicle | 8 | 1762, 1785, 1797 | 1761, 1775, 1781, 1788 |
| MYSQL:transportation.shipping_company | 5 | — | — |
| MYSQL:transportation.employee | 0 | 1592 | 1586 |
| MYSQL:transportation.vessel | 6 | 1737 | 1761, 1777 |
| MYSQL:finance_tax.companies | 13 | 1595, 1599, 1641, 1712 | 1664 |
| MYSQL:finance_tax.stocks | 12 | 1638 | 1625, 1627 |
| MYSQL:finance_tax.stock_daily_trades | 4 | — | 1623, 1643 |
| MYSQL:finance_tax.company_financials | 13 | — | 1624 |
| MYSQL:finance_tax.corporate_income_tax_returns | 15 | — | 1664 |
| MYSQL:energy.energy_company | 5 | — | 1580, 1587, 1593, 1761 |
| MYSQL:energy.company_certification | 2 | 1773, 1792 | — |
| MYSQL:energy.energy_station | 13 | — | 1591, 1602, 1761 |
| MYSQL:energy.supply_area | 5 | — | 1761 |
| MYSQL:energy.employee | 1 | 1592 | 1580, 1586 |
| MYSQL:education_2024.semester | 0 | — | — |
| MYSQL:education_2024.department | 0 | — | — |
| MYSQL:education_2024.teacher | 0 | — | — |
| MYSQL:education_2024.class | 0 | — | — |
| MYSQL:education_2024.student | 0 | — | — |
| MYSQL:education_2024.course | 0 | — | — |
| MYSQL:education_2024.enrollment | 1 | 1575 | 1579 |
| MYSQL:education_2024.exam_score | 0 | — | 1572, 1573, 1574, 1575, 1577, 1579 |
| MYSQL:education_2025.semester | 0 | — | — |
| MYSQL:education_2025.department | 0 | — | — |
| MYSQL:education_2025.teacher | 0 | — | — |
| MYSQL:education_2025.class | 0 | — | — |
| MYSQL:education_2025.student | 0 | — | — |
| MYSQL:education_2025.course | 0 | — | — |
| MYSQL:education_2025.enrollment | 1 | 1575 | 1579 |
| MYSQL:education_2025.exam_score | 0 | — | 1572, 1573, 1574, 1577, 1579 |
| MYSQL:ecommerce.customer | 1 | — | — |
| MYSQL:ecommerce.product | 3 | 1781 | — |
| MYSQL:ecommerce.inventory | 1 | — | — |
| MYSQL:ecommerce.orders | 11 | — | — |
| MYSQL:ecommerce.order_item | 6 | — | — |
| MYSQL:ecommerce.payment | 3 | 1558 | — |
| POSTGRESQL:public.vessel_ais_data | 12 | 1722, 1723, 1725, 1729, 1739, 1740, 1747, 1750, 1752, 1754, 1755, 1759 | 1721, 1730, 1732, 1733, 1734, 1735, 1736, 1737, 1738, 1741, 1742, 1746, 1753, 1758, 1760, 1777 |
| Elasticsearch:medical_institutions | 13 | 1672 | 1697, 1698, 1699, 1701 |
