# 245：查询济南市注册的所有新能源车数量

归类：**已有证据未被模型正确利用**；原语义审查状态：`different`。

实际案例155明确使用v.brand LIKE '%电动%'表示新能源车，模型仍改成'%新能源%'，并在assumptions中宣称缺少标识字段。所需编码已经在输入中，属于已有证据未被正确利用。

[实际请求和完整提示词](request.json) · [实际响应](response.json) · [结构化证据](diagnosis.json)

## 参考与预测

参考：

```json
{
  "question_id": 245,
  "question": "查询济南市注册的所有新能源车数量",
  "db": "MYSQL",
  "query": "SELECT COUNT(*) FROM transportation.vehicle WHERE area_id LIKE '3701%' AND brand LIKE '%电动%';"
}
```

预测：

```json
{
  "question_id": 245,
  "db": "MYSQL",
  "query": "SELECT COUNT(*) FROM transportation.vehicle v JOIN common.administrative_division ad ON v.area_id = ad.id WHERE ad.city_name = '济南市' AND v.brand LIKE '%新能源%';"
}
```

## 输入证据

```json
{
  "prompt_table_ids": [
    "MYSQL:common.administrative_division",
    "MYSQL:common.vehicle_type_dict",
    "MYSQL:ecommerce.customer",
    "MYSQL:energy.energy_company",
    "MYSQL:transportation.vehicle",
    "MYSQL:transportation.vehicle_company"
  ],
  "reference_tables_not_in_prompt": [],
  "predicted_tables_not_in_prompt": [],
  "prompt_knowledge_ids": [
    1580,
    1770,
    1761,
    1593,
    1789,
    1820,
    604,
    1659,
    1351,
    432,
    1348,
    600
  ],
  "prompt_example_ids": [
    155,
    9,
    10,
    59
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
      "question_id": 155,
      "question": "统计各类车辆中品牌中新能源车的数量",
      "steps": [
        {
          "engine": "MYSQL",
          "query": "SELECT t.type_name, COUNT(v.vehicle_id) AS new_energy_count FROM transportation.vehicle v JOIN common.vehicle_type_dict t ON v.vehicle_type_code = t.type_code WHERE v.brand LIKE '%电动%' GROUP BY t.type_name;",
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
  "knowledge_in_actual_prompt": [
    {
      "knowledge_id": 1761,
      "knowledge_text": "行政区划代码（area_id）为6位数字编码。前2位代表省级行政区，前4位代表地市级行政区，6位全码代表区县级行政区。统计省份时使用 LEFT(area_id,2) 分组，统计城市时使用 LEFT(area_id,4) 分组，统计区县时使用 area_id 全码分组。省份名称可通过 administrative_division 表中 level=1 的记录获取，城市名称可通过 level=2 的记录获取。"
    }
  ],
  "raw_knowledge_not_in_actual_prompt": []
}
```

后续核验：优先检查案例语义迁移与假设核验；同一提示词换模型/重复运行才可比较模型差异。

这是现有请求的静态证据归因，没有运行改提示词或换模型的控制变量实验。
