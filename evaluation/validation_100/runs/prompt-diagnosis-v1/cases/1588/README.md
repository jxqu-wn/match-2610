# 1588：请统计整体退款率，输出结果。

归类：**规则或案例冲突**；原语义审查状态：`rules_only_difference`。

系统新规则明确比率ROUND2且优先于案例，参考与召回退款率案例为ROUND4。预测遵循新规则，不能将精度差异归为模型生成错误。

[实际请求和完整提示词](request.json) · [实际响应](response.json) · [结构化证据](diagnosis.json)

## 参考与预测

参考：

```json
{
  "question_id": 1588,
  "question": "请统计整体退款率，输出结果。",
  "db": "MYSQL",
  "query": "SELECT ROUND(COUNT(DISTINCT CASE WHEN oi.refund_amount > 0 THEN o.order_id END) / NULLIF(COUNT(DISTINCT o.order_id), 0), 4) AS refund_rate FROM ecommerce.orders o LEFT JOIN ecommerce.order_item oi ON o.order_id = oi.order_id;"
}
```

预测：

```json
{
  "question_id": 1588,
  "db": "MYSQL",
  "query": "SELECT ROUND(COUNT(DISTINCT CASE WHEN oi.refund_amount > 0 THEN o.order_id END) / NULLIF(COUNT(DISTINCT o.order_id), 0), 2) AS refund_rate FROM ecommerce.orders o LEFT JOIN ecommerce.order_item oi ON o.order_id = oi.order_id;"
}
```

## 输入证据

```json
{
  "prompt_table_ids": [
    "MYSQL:ecommerce.customer",
    "MYSQL:ecommerce.order_item",
    "MYSQL:ecommerce.orders",
    "MYSQL:ecommerce.payment",
    "MYSQL:ecommerce.product",
    "MYSQL:finance_tax.corporate_income_tax_returns"
  ],
  "reference_tables_not_in_prompt": [],
  "predicted_tables_not_in_prompt": [],
  "prompt_knowledge_ids": [
    1558,
    1557,
    353,
    1554,
    1568,
    1610,
    708,
    1556,
    1561,
    226,
    1135,
    1140
  ],
  "prompt_example_ids": [
    1196,
    1584,
    1356,
    1070
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
      "question_id": 1584,
      "question": "请帮我统计整体退款率，输出结果。",
      "steps": [
        {
          "engine": "MYSQL",
          "query": "SELECT ROUND(COUNT(DISTINCT CASE WHEN oi.refund_amount > 0 THEN o.order_id END) / NULLIF(COUNT(DISTINCT o.order_id), 0), 4) AS refund_rate FROM ecommerce.orders o LEFT JOIN ecommerce.order_item oi ON o.order_id = oi.order_id;",
          "step": "query",
          "table_ids": [
            "MYSQL:ecommerce.order_item",
            "MYSQL:ecommerce.orders"
          ],
          "joins": [
            {
              "left_table": "MYSQL:ecommerce.orders",
              "left_columns": [
                "order_id"
              ],
              "right_table": "MYSQL:ecommerce.order_item",
              "right_columns": [
                "order_id"
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
      "knowledge_id": 1558,
      "knowledge_text": "退款率（订单退款率/售后退款率）可按退款订单数占订单数计算。订单明细中退款金额超过0时，可认为发生退款。计算公式：COUNT(DISTINCT CASE WHEN refund_amount > 0 THEN order_id END) / COUNT(DISTINCT order_id)。"
    }
  ],
  "raw_knowledge_not_in_actual_prompt": []
}
```

后续核验：先统一规则与监督标签，或明确本任务评估允许的精度。

这是现有请求的静态证据归因，没有运行改提示词或换模型的控制变量实验。
