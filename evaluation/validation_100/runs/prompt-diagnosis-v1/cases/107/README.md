# 107：查询所有车辆中颜色为'黑'且品牌为'奔驰'的车辆

归类：**题目、参考或数据口径尚不能裁定**；原语义审查状态：`different`。

题目只说查询车辆，没有限定车牌一列。参考只输出plate_number，预测SELECT *；案例229支持车牌投影，但不能消除题目本身的输出口径缺失。

[实际请求和完整提示词](request.json) · [实际响应](response.json) · [结构化证据](diagnosis.json)

## 参考与预测

参考：

```json
{
  "question_id": 107,
  "question": "查询所有车辆中颜色为'黑'且品牌为'奔驰'的车辆",
  "db": "MYSQL",
  "query": "SELECT plate_number FROM transportation.vehicle WHERE color = '黑' AND brand = '奔驰';"
}
```

预测：

```json
{
  "question_id": 107,
  "db": "MYSQL",
  "query": "SELECT * FROM transportation.vehicle WHERE color = '黑' AND brand = '奔驰';"
}
```

## 输入证据

```json
{
  "prompt_table_ids": [
    "MYSQL:common.administrative_division",
    "MYSQL:common.vehicle_type_dict",
    "MYSQL:common.vessel_type_dict",
    "MYSQL:transportation.driver",
    "MYSQL:transportation.vehicle",
    "MYSQL:transportation.vehicle_company"
  ],
  "reference_tables_not_in_prompt": [],
  "predicted_tables_not_in_prompt": [],
  "prompt_knowledge_ids": [
    247,
    1770,
    1765,
    815,
    1348,
    1351,
    1659,
    656,
    1772,
    1768,
    1818,
    1789
  ],
  "prompt_example_ids": [
    229,
    18,
    251,
    77
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
      "question_id": 229,
      "question": "查询所有黑色且为货车的车辆",
      "steps": [
        {
          "engine": "MYSQL",
          "query": "SELECT plate_number FROM transportation.vehicle v JOIN common.vehicle_type_dict t ON v.vehicle_type_code = t.type_code WHERE v.color = '黑' AND t.type_name = '货车';",
          "step": "query",
          "table_ids": [
            "MYSQL:common.vehicle_type_dict",
            "MYSQL:transportation.vehicle"
          ],
          "joins": [
            {
              "left_table": "MYSQL:transportation.vehicle",
              "left_columns": [
                "vehicle_type_code"
              ],
              "right_table": "MYSQL:common.vehicle_type_dict",
              "right_columns": [
                "type_code"
              ]
            }
          ],
          "parse_status": "parsed",
          "unresolved_tables": []
        }
      ]
    }
  ],
  "knowledge_in_actual_prompt": [],
  "raw_knowledge_not_in_actual_prompt": []
}
```

后续核验：先统一车辆类查询的默认输出对象/字段，再评价模型是否遵循。

这是现有请求的静态证据归因，没有运行改提示词或换模型的控制变量实验。
