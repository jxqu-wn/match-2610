# 498：计算海康威视2025年总市值是行业平均市值的多少倍

归类：**题目、参考或数据口径尚不能裁定**；原语义审查状态：`uncertain`。

参考将行业均值硬编码183000000000，输入没有这个常量及其数据来源；预测用行业AVG有题意依据。缺少真实数据，不能判定常量和动态平均是否相等。

[实际请求和完整提示词](request.json) · [实际响应](response.json) · [结构化证据](diagnosis.json)

## 参考与预测

参考：

```json
{
  "question_id": 498,
  "question": "计算海康威视2025年总市值是行业平均市值的多少倍",
  "db": "MYSQL",
  "query": "SELECT (s.current_price * s.total_shares) / 183000000000 AS ratio FROM finance_tax.stocks s WHERE s.stock_name = '海康威视';"
}
```

预测：

```json
{
  "question_id": 498,
  "db": "MYSQL",
  "query": "SELECT ROUND(hk.total_mv / avg_ind.avg_mv, 2) AS ratio FROM (SELECT s.current_price * s.total_shares AS total_mv FROM finance_tax.stocks s JOIN finance_tax.companies c ON s.company_id = c.company_id WHERE c.company_name = '海康威视' LIMIT 1) hk CROSS JOIN (SELECT AVG(s2.current_price * s2.total_shares) AS avg_mv FROM finance_tax.stocks s2 JOIN finance_tax.companies c2 ON s2.company_id = c2.company_id WHERE c2.industry_code = (SELECT c3.industry_code FROM finance_tax.companies c3 WHERE c3.company_name = '海康威视' LIMIT 1)) avg_ind;"
}
```

## 输入证据

```json
{
  "prompt_table_ids": [
    "MYSQL:common.dict_registration_type",
    "MYSQL:finance_tax.companies",
    "MYSQL:finance_tax.company_financials",
    "MYSQL:finance_tax.corporate_income_tax_returns",
    "MYSQL:finance_tax.stock_daily_trades",
    "MYSQL:finance_tax.stocks"
  ],
  "reference_tables_not_in_prompt": [],
  "predicted_tables_not_in_prompt": [],
  "prompt_knowledge_ids": [
    1632,
    1608,
    1644,
    1604,
    1635,
    1605,
    1659,
    1622,
    1623,
    1634,
    571,
    1615
  ],
  "prompt_example_ids": [
    439,
    430,
    436,
    435
  ],
  "pruned_evidence": [],
  "rule_priority_excerpts": [
    "本次问题的统一口径如下，优先于训练案例及不明确的知识描述：",
    "1.比率、比例、百分比、平均值，用 ROUND(..., 2)。",
    "2.公式算出来的比率类、平均值类结果，以及每股类指标，包括资产负债率、总资产收益率、市盈率、每股现金分红 DPS 等，用 ROUND(..., 2)。",
    "3.其他情况一律不使用 ROUND。"
  ],
  "examples_in_actual_prompt": [
    {
      "question_id": 439,
      "question": "计算各行业2025年平均每股净资产",
      "steps": [
        {
          "engine": "MYSQL",
          "query": "SELECT i.industry_name, AVG((f.total_assets * 10000) / s.total_shares) FROM finance_tax.stocks s JOIN finance_tax.companies c ON s.company_id = c.company_id JOIN finance_tax.company_financials f ON s.company_id = f.company_id JOIN common.dict_industry i ON c.industry_code = i.industry_code WHERE f.report_date = '2025-12-31' GROUP BY i.industry_name;",
          "step": "query",
          "table_ids": [
            "MYSQL:common.dict_industry",
            "MYSQL:finance_tax.companies",
            "MYSQL:finance_tax.company_financials",
            "MYSQL:finance_tax.stocks"
          ],
          "joins": [
            {
              "left_table": "MYSQL:finance_tax.stocks",
              "left_columns": [
                "company_id"
              ],
              "right_table": "MYSQL:finance_tax.companies",
              "right_columns": [
                "company_id"
              ]
            },
            {
              "left_table": "MYSQL:finance_tax.stocks",
              "left_columns": [
                "company_id"
              ],
              "right_table": "MYSQL:finance_tax.company_financials",
              "right_columns": [
                "company_id"
              ]
            },
            {
              "left_table": "MYSQL:finance_tax.companies",
              "left_columns": [
                "industry_code"
              ],
              "right_table": "MYSQL:common.dict_industry",
              "right_columns": [
                "industry_code"
              ]
            }
          ],
          "parse_status": "parsed",
          "unresolved_tables": []
        }
      ]
    },
    {
      "question_id": 430,
      "question": "计算所有A股在2025年12月31日的平均市盈率",
      "steps": [
        {
          "engine": "MYSQL",
          "query": "SELECT AVG(t.close_price / (((f.total_assets - f.total_liabilities) * 10000) / s.total_shares)) AS avg_pe FROM finance_tax.stocks s JOIN finance_tax.company_financials f ON s.company_id = f.company_id JOIN finance_tax.stock_daily_trades t ON s.stock_id = t.stock_id WHERE s.market_class = 'A' AND f.report_date = '2025-12-31' AND t.trade_date = '2025-12-31';",
          "step": "query",
          "table_ids": [
            "MYSQL:finance_tax.company_financials",
            "MYSQL:finance_tax.stock_daily_trades",
            "MYSQL:finance_tax.stocks"
          ],
          "joins": [
            {
              "left_table": "MYSQL:finance_tax.stocks",
              "left_columns": [
                "company_id"
              ],
              "right_table": "MYSQL:finance_tax.company_financials",
              "right_columns": [
                "company_id"
              ]
            },
            {
              "left_table": "MYSQL:finance_tax.stocks",
              "left_columns": [
                "stock_id"
              ],
              "right_table": "MYSQL:finance_tax.stock_daily_trades",
              "right_columns": [
                "stock_id"
              ]
            }
          ],
          "parse_status": "parsed",
          "unresolved_tables": []
        }
      ]
    }
  ],
  "knowledge_in_actual_prompt": [
    {
      "knowledge_id": 1644,
      "knowledge_text": "股票总市值指最新股价乘以总股本，单位：元，其中最新股价单位为元，总股本单位为股。计算公式：current_price * total_shares。"
    },
    {
      "knowledge_id": 1659,
      "knowledge_text": "上市公司所属行业分类存储在companies.industry_code，对应的行业名称在common.dict_industry表中。"
    }
  ],
  "raw_knowledge_not_in_actual_prompt": []
}
```

后续核验：核验参考常量来源、行业口径及公司名称映射后再做模型评价。

这是现有请求的静态证据归因，没有运行改提示词或换模型的控制变量实验。
