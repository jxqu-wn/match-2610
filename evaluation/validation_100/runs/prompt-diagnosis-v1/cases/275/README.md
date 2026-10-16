# 275：查询广州市注册的所有车辆

归类：**题目、参考或数据口径尚不能裁定**；原语义审查状态：`different`。

题面未列输出字段，参考SELECT *，模型返回车牌；召回案例236、263都使用车牌标识车辆。输入案例对精简投影有支持，不能直接归为模型漏需求。

[实际请求和完整提示词](request.json) · [实际响应](response.json) · [结构化证据](diagnosis.json)

## 参考与预测

参考：

```json
{
  "question_id": 275,
  "question": "查询广州市注册的所有车辆",
  "db": "MYSQL",
  "query": "SELECT * FROM transportation.vehicle WHERE area_id LIKE '4401%';"
}
```

预测：

```json
{
  "question_id": 275,
  "db": "MYSQL",
  "query": "SELECT v.plate_number FROM transportation.vehicle v JOIN common.administrative_division a ON v.area_id = a.id WHERE a.city_name = '广州市'"
}
```

## 输入证据

```json
{
  "prompt_table_ids": [
    "MYSQL:common.administrative_division",
    "MYSQL:common.vehicle_type_dict",
    "MYSQL:transportation.driver",
    "MYSQL:transportation.vehicle",
    "MYSQL:transportation.vehicle_company",
    "MYSQL:transportation.vessel"
  ],
  "reference_tables_not_in_prompt": [],
  "predicted_tables_not_in_prompt": [],
  "prompt_knowledge_ids": [
    1789,
    1770,
    1820,
    1761,
    1818,
    1768,
    247,
    1769,
    1787,
    1805,
    1348,
    1351
  ],
  "prompt_example_ids": [
    236,
    263,
    63,
    237
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
      "question_id": 236,
      "question": "查询广州市天河区注册的所有货车",
      "steps": [
        {
          "engine": "MYSQL",
          "query": "SELECT plate_number FROM transportation.vehicle v JOIN common.vehicle_type_dict t ON v.vehicle_type_code = t.type_code WHERE v.area_id LIKE '440106%' AND t.type_name='货车';",
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
    },
    {
      "question_id": 263,
      "question": "查询广州市注册的新能源品牌车辆",
      "steps": [
        {
          "engine": "MYSQL",
          "query": "SELECT plate_number, brand FROM transportation.vehicle WHERE area_id LIKE '4401%' AND brand LIKE '%电动%';",
          "step": "query",
          "table_ids": [
            "MYSQL:transportation.vehicle"
          ],
          "joins": [],
          "parse_status": "parsed",
          "unresolved_tables": []
        }
      ]
    },
    {
      "question_id": 237,
      "question": "查询所有车辆及其所属公司名称",
      "steps": [
        {
          "engine": "MYSQL",
          "query": "SELECT v.plate_number, c.company_name FROM transportation.vehicle v LEFT JOIN transportation.vehicle_company c ON v.company_id = c.company_id;",
          "step": "query",
          "table_ids": [
            "MYSQL:transportation.vehicle",
            "MYSQL:transportation.vehicle_company"
          ],
          "joins": [
            {
              "left_table": "MYSQL:transportation.vehicle",
              "left_columns": [
                "company_id"
              ],
              "right_table": "MYSQL:transportation.vehicle_company",
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
      "knowledge_id": 1820,
      "knowledge_text": "车辆注册地是车辆登记时所属的行政区划，反映车辆归属地。船舶注册地是船舶登记时所属的行政区划，反映船舶归属地。注册地影响车辆的保险、年检和监管归属。"
    }
  ],
  "raw_knowledge_not_in_actual_prompt": []
}
```

后续核验：确定查询所有车辆是否必须返回全部车辆属性。

这是现有请求的静态证据归因，没有运行改提示词或换模型的控制变量实验。
