# 316：查询2025年度没有不征税收入的企业名称

归类：**题目、参考或数据口径尚不能裁定**；原语义审查状态：`different`。

non_taxable_income在Schema中可空，但没有业务规则说明没有收入是否包含NULL。预测接受0或NULL，参考只接受0；这是数据缺失和零值的未定义口径。

[实际请求和完整提示词](request.json) · [实际响应](response.json) · [结构化证据](diagnosis.json)

## 参考与预测

参考：

```json
{
  "question_id": 316,
  "question": "查询2025年度没有不征税收入的企业名称",
  "db": "MYSQL",
  "query": "SELECT c.company_name FROM finance_tax.corporate_income_tax_returns r JOIN finance_tax.companies c ON r.company_id = c.company_id WHERE r.tax_year = 2025 AND r.non_taxable_income = 0;"
}
```

预测：

```json
{
  "question_id": 316,
  "db": "MYSQL",
  "query": "SELECT c.company_name FROM finance_tax.corporate_income_tax_returns r JOIN finance_tax.companies c ON r.company_id = c.company_id WHERE r.tax_year = 2025 AND (r.non_taxable_income IS NULL OR r.non_taxable_income = 0);"
}
```

## 输入证据

```json
{
  "prompt_table_ids": [
    "MYSQL:education_2025.class",
    "MYSQL:education_2025.department",
    "MYSQL:education_2025.teacher",
    "MYSQL:finance_tax.companies",
    "MYSQL:finance_tax.company_financials",
    "MYSQL:finance_tax.corporate_income_tax_returns"
  ],
  "reference_tables_not_in_prompt": [],
  "predicted_tables_not_in_prompt": [],
  "prompt_knowledge_ids": [
    1611,
    1621,
    1661,
    1653,
    1628,
    1629,
    1610,
    1655,
    1617,
    1385,
    1616,
    1652
  ],
  "prompt_example_ids": [
    333,
    307,
    509,
    331
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
      "question_id": 333,
      "question": "查询2025年度扣除金额为0的企业名称",
      "steps": [
        {
          "engine": "MYSQL",
          "query": "SELECT c.company_name FROM finance_tax.corporate_income_tax_returns r JOIN finance_tax.companies c ON r.company_id = c.company_id WHERE r.tax_year = 2025 AND r.deductions = 0;",
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
      "knowledge_id": 1611,
      "knowledge_text": "corporate_income_tax_returns.non_taxable_income 表示不征税收入与免税收入合计，单位：万元。"
    }
  ],
  "raw_knowledge_not_in_actual_prompt": []
}
```

后续核验：先明确NULL是否代表未知、未填报还是0，避免用普通自然语言替代业务定义。

这是现有请求的静态证据归因，没有运行改提示词或换模型的控制变量实验。
