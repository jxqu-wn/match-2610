# 489：请计算顺丰速运2025年度所得税费用占净利润的比例

归类：**输入与模型处理混合**；原语义审查状态：`different`。

税率案例互相冲突；同时模型把参考年末报表放宽为年内全部报表。前者来自输入口径，后者是时间范围和连接基数推理偏差，不能用一次运行二选一归因。

[实际请求和完整提示词](request.json) · [实际响应](response.json) · [结构化证据](diagnosis.json)

## 参考与预测

参考：

```json
{
  "question_id": 489,
  "question": "请计算顺丰速运2025年度所得税费用占净利润的比例",
  "db": "MYSQL",
  "query": "SELECT ((r.revenue - r.non_taxable_income - r.deductions - r.prior_year_losses) * 0.25) / (f.total_assets - f.total_liabilities) * 100 AS ratio FROM finance_tax.corporate_income_tax_returns r JOIN finance_tax.company_financials f ON r.company_id = f.company_id AND r.tax_year = 2025 JOIN finance_tax.stocks s ON r.company_id = s.company_id WHERE s.stock_name = '顺丰速运' AND f.report_date = '2025-12-31';"
}
```

预测：

```json
{
  "question_id": 489,
  "db": "MYSQL",
  "query": "SELECT ROUND(((r.revenue - r.non_taxable_income - r.deductions - r.prior_year_losses) * CASE WHEN c.is_key_high_tech THEN 0.15 WHEN (r.revenue - r.non_taxable_income - r.deductions - r.prior_year_losses) <= 100 AND r.employee_count <= 300 AND r.total_assets <= 5000 AND r.is_restricted_industry = FALSE THEN 0.20 ELSE 0.25 END) / (f.total_assets - f.total_liabilities) * 100, 2) AS tax_to_net_profit_ratio FROM finance_tax.corporate_income_tax_returns r JOIN finance_tax.companies c ON r.company_id = c.company_id JOIN finance_tax.stocks s ON r.company_id = s.company_id JOIN finance_tax.company_financials f ON r.company_id = f.company_id AND YEAR(f.report_date) = r.tax_year WHERE s.stock_name = '顺丰速运' AND r.tax_year = 2025;"
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
    1628,
    1635,
    1611,
    1637,
    1610,
    1626,
    1608,
    1615,
    1632,
    1653,
    1612,
    1661
  ],
  "prompt_example_ids": [
    499,
    492,
    545,
    453
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
      "question_id": 499,
      "question": "请计算顺丰控股2025年所得税费用相对于行业平均所得税费用的比值",
      "steps": [
        {
          "engine": "MYSQL",
          "query": "SELECT ((r.revenue - r.non_taxable_income - r.deductions - r.prior_year_losses) * 0.25) / 1800 AS ratio FROM finance_tax.corporate_income_tax_returns r JOIN finance_tax.stocks s ON r.company_id = s.company_id WHERE s.stock_name = '顺丰控股' AND r.tax_year = 2025;",
          "step": "query",
          "table_ids": [
            "MYSQL:finance_tax.corporate_income_tax_returns",
            "MYSQL:finance_tax.stocks"
          ],
          "joins": [
            {
              "left_table": "MYSQL:finance_tax.corporate_income_tax_returns",
              "left_columns": [
                "company_id"
              ],
              "right_table": "MYSQL:finance_tax.stocks",
              "right_columns": [
                "company_id"
              ]
            }
          ],
          "parse_status": "parsed",
          "unresolved_tables": []
        }
      ]
    },
    {
      "question_id": 492,
      "question": "请计算顺丰速运2025年度实际缴税额与按普通税率25%计算的差额",
      "steps": [
        {
          "engine": "MYSQL",
          "query": "SELECT (r.revenue - r.non_taxable_income - r.deductions - r.prior_year_losses) * 0.00 AS tax_diff FROM finance_tax.corporate_income_tax_returns r JOIN finance_tax.stocks s ON r.company_id = s.company_id WHERE s.stock_name = '顺丰速运' AND r.tax_year = 2025;",
          "step": "query",
          "table_ids": [
            "MYSQL:finance_tax.corporate_income_tax_returns",
            "MYSQL:finance_tax.stocks"
          ],
          "joins": [
            {
              "left_table": "MYSQL:finance_tax.corporate_income_tax_returns",
              "left_columns": [
                "company_id"
              ],
              "right_table": "MYSQL:finance_tax.stocks",
              "right_columns": [
                "company_id"
              ]
            }
          ],
          "parse_status": "parsed",
          "unresolved_tables": []
        }
      ]
    },
    {
      "question_id": 545,
      "question": "计算各企业2025年度的所得税贡献率",
      "steps": [
        {
          "engine": "MYSQL",
          "query": "SELECT c.company_name, ((r.revenue - r.non_taxable_income - r.deductions - r.prior_year_losses) * CASE WHEN c.is_key_high_tech THEN 0.15 WHEN (r.revenue - r.non_taxable_income - r.deductions - r.prior_year_losses) <= 100 AND r.employee_count <= 300 AND r.total_assets <= 5000 AND r.is_restricted_industry = FALSE THEN 0.20 ELSE 0.25 END / r.total_assets) * 100 AS contribution FROM finance_tax.corporate_income_tax_returns r JOIN finance_tax.companies c ON r.company_id = c.company_id WHERE r.tax_year = 2025 ORDER BY contribution DESC LIMIT 10;",
          "step": "query",
          "table_ids": [
            "MYSQL:finance_tax.companies",
            "MYSQL:finance_tax.corporate_income_tax_returns"
          ],
          "joins": [
            {
              "left_table": "MYSQL:finance_tax.corporate_income_tax_returns",
              "left_columns": [
                "company_id"
              ],
              "right_table": "MYSQL:finance_tax.companies",
              "right_columns": [
                "company_id"
              ]
            }
          ],
          "parse_status": "parsed",
          "unresolved_tables": []
        }
      ]
    },
    {
      "question_id": 453,
      "question": "计算各企业2025年度的实际税负率，列出实际税负率低于15%的企业",
      "steps": [
        {
          "engine": "MYSQL",
          "query": "SELECT c.company_name, ((r.revenue - r.non_taxable_income - r.deductions - r.prior_year_losses) * CASE WHEN c.is_key_high_tech THEN 0.15 WHEN (r.revenue - r.non_taxable_income - r.deductions - r.prior_year_losses) <= 100 AND r.employee_count <= 300 AND r.total_assets <= 5000 AND r.is_restricted_industry = FALSE THEN 0.20 ELSE 0.25 END / r.revenue) * 100 AS effective_rate FROM finance_tax.corporate_income_tax_returns r JOIN finance_tax.companies c ON r.company_id = c.company_id WHERE r.tax_year = 2025 HAVING effective_rate < 15;",
          "step": "query",
          "table_ids": [
            "MYSQL:finance_tax.companies",
            "MYSQL:finance_tax.corporate_income_tax_returns"
          ],
          "joins": [
            {
              "left_table": "MYSQL:finance_tax.corporate_income_tax_returns",
              "left_columns": [
                "company_id"
              ],
              "right_table": "MYSQL:finance_tax.companies",
              "right_columns": [
                "company_id"
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
      "knowledge_id": 1626,
      "knowledge_text": "净利润近似指总资产减去总负债（本库特殊定义，实际净利润不等于资产减负债）。计算公式：total_assets - total_liabilities。"
    },
    {
      "knowledge_id": 1653,
      "knowledge_text": "小型微利企业判定基于年度申报数据，满足条件则适用20%优惠税率。"
    }
  ],
  "raw_knowledge_not_in_actual_prompt": []
}
```

后续核验：先统一税率/报告期，再检查是否仍产生多报告期行。

这是现有请求的静态证据归因，没有运行改提示词或换模型的控制变量实验。
