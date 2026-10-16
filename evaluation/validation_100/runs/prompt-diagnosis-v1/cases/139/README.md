# 139：查询四川省所有危化品车辆的公司分布

归类：**输入与模型处理混合**；原语义审查状态：`different`。

缺少车辆类型字典DDL，但案例130已给出正确危化车辆连接。模型没有请求补表，同时把四川车辆的条件放到公司所在地，存在输入缺口及需求绑定错误。

[实际请求和完整提示词](request.json) · [实际响应](response.json) · [结构化证据](diagnosis.json)

## 参考与预测

参考：

```json
{
  "question_id": 139,
  "question": "查询四川省所有危化品车辆的公司分布",
  "db": "MYSQL",
  "query": "SELECT c.company_name, COUNT(v.vehicle_id) AS hazmat_count FROM transportation.vehicle_company c JOIN transportation.vehicle v ON c.company_id = v.company_id JOIN common.vehicle_type_dict t ON v.vehicle_type_code = t.type_code WHERE v.area_id LIKE '51%' AND t.type_name = '危化品车' GROUP BY c.company_id;"
}
```

预测：

```json
{
  "question_id": 139,
  "db": "MYSQL",
  "query": "SELECT vc.company_name, COUNT(DISTINCT v.vehicle_id) AS hazmat_vehicle_count FROM transportation.vehicle_company vc JOIN transportation.vehicle v ON vc.company_id = v.company_id JOIN common.vehicle_type_dict vtd ON v.vehicle_type_code = vtd.type_code JOIN common.administrative_division ad ON vc.area_id = ad.id WHERE ad.province_name = '四川省' AND vtd.type_name = '危化品车' GROUP BY vc.company_id, vc.company_name ORDER BY hazmat_vehicle_count DESC;"
}
```

## 输入证据

```json
{
  "prompt_table_ids": [
    "MYSQL:common.administrative_division",
    "MYSQL:common.license_type_dict",
    "MYSQL:transportation.driver",
    "MYSQL:transportation.shipping_company",
    "MYSQL:transportation.vehicle",
    "MYSQL:transportation.vehicle_company"
  ],
  "reference_tables_not_in_prompt": [
    "MYSQL:common.vehicle_type_dict"
  ],
  "predicted_tables_not_in_prompt": [
    "MYSQL:common.vehicle_type_dict"
  ],
  "prompt_knowledge_ids": [
    1791,
    1818,
    1787,
    1761,
    1765,
    561,
    1770,
    1659,
    1820,
    1771,
    1348,
    1789
  ],
  "prompt_example_ids": [
    130,
    84,
    237,
    117
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
      "question_id": 130,
      "question": "统计各公司危化品运输车的数量，只显示数量大于0的公司",
      "steps": [
        {
          "engine": "MYSQL",
          "query": "SELECT c.company_name, COUNT(v.vehicle_id) AS hazmat_count FROM transportation.vehicle_company c JOIN transportation.vehicle v ON c.company_id = v.company_id JOIN common.vehicle_type_dict t ON v.vehicle_type_code = t.type_code WHERE t.type_name = '危化品车' GROUP BY c.company_id HAVING COUNT(v.vehicle_id) > 0;",
          "step": "query",
          "table_ids": [
            "MYSQL:common.vehicle_type_dict",
            "MYSQL:transportation.vehicle",
            "MYSQL:transportation.vehicle_company"
          ],
          "joins": [
            {
              "left_table": "MYSQL:transportation.vehicle_company",
              "left_columns": [
                "company_id"
              ],
              "right_table": "MYSQL:transportation.vehicle",
              "right_columns": [
                "company_id"
              ]
            },
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
      "question_id": 117,
      "question": "查询所有车辆公司中，注册地区划代码为'110101'的公司",
      "steps": [
        {
          "engine": "MYSQL",
          "query": "SELECT company_name FROM transportation.vehicle_company WHERE area_id = '110101';",
          "step": "query",
          "table_ids": [
            "MYSQL:transportation.vehicle_company"
          ],
          "joins": [],
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

后续核验：补全类型字典结构，显式核验车辆所在地与公司所在地，不从参考SQL补规则。

这是现有请求的静态证据归因，没有运行改提示词或换模型的控制变量实验。
