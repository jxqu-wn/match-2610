# 476：请计算顺丰控股2025年度所得税额占营业收入的比例

归类：**规则或案例冲突**；原语义审查状态：`different`。

同一提示词的案例499固定乘25%，案例453/545使用分档税率，知识1653支持20%优惠。问题未指定税率和比例/百分数单位；ROUND2的高优先级规则不能解决这些冲突。

[实际请求和完整提示词](request.json) · [实际响应](response.json) · [结构化证据](diagnosis.json)

## 参考与预测

参考：

```json
{
  "question_id": 476,
  "question": "请计算顺丰控股2025年度所得税额占营业收入的比例",
  "db": "MYSQL",
  "query": "SELECT ((r.revenue - r.non_taxable_income - r.deductions - r.prior_year_losses) * 0.25 / r.revenue) * 100 AS tax_burden FROM finance_tax.corporate_income_tax_returns r JOIN finance_tax.stocks s ON r.company_id = s.company_id WHERE s.stock_name = '顺丰控股' AND r.tax_year = 2025;"
}
```

预测：

```json
{
  "question_id": 476,
  "db": "MYSQL",
  "query": "SELECT ROUND(((r.revenue - r.non_taxable_income - r.deductions - r.prior_year_losses) * CASE WHEN c.is_key_high_tech THEN 0.15 WHEN (r.revenue - r.non_taxable_income - r.deductions - r.prior_year_losses) <= 100 AND r.employee_count <= 300 AND r.total_assets <= 5000 AND r.is_restricted_industry = FALSE THEN 0.20 ELSE 0.25 END) / r.revenue, 2) AS tax_to_revenue_ratio FROM finance_tax.corporate_income_tax_returns r JOIN finance_tax.stocks s ON r.company_id = s.company_id JOIN finance_tax.companies c ON r.company_id = c.company_id WHERE s.stock_name = '顺丰控股' AND r.tax_year = 2025;"
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
    1610,
    1611,
    1608,
    1615,
    1653,
    1621,
    1612,
    1659,
    1661,
    1635,
    1609
  ],
  "prompt_example_ids": [
    499,
    545,
    492,
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
      "knowledge_id": 1653,
      "knowledge_text": "小型微利企业判定基于年度申报数据，满足条件则适用20%优惠税率。"
    }
  ],
  "raw_knowledge_not_in_actual_prompt": []
}
```

后续核验：在生成前给出适用税率证据和输出单位；不得把调换示例顺序当作业务裁定。

这是现有请求的静态证据归因，没有运行改提示词或换模型的控制变量实验。
