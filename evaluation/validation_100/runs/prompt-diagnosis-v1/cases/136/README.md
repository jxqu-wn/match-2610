# 136：统计湖北省各公司拥有的危化品车辆数

归类：**题目、参考或数据口径尚不能裁定**；原语义审查状态：`different`。

题面湖北省各公司可以理解为公司注册地，参考却按车辆注册地筛选。两个area_id都在Schema中；未规定地域修饰对象，不能仅凭与参考不同认定模型能力不足。

[实际请求和完整提示词](request.json) · [实际响应](response.json) · [结构化证据](diagnosis.json)

## 参考与预测

参考：

```json
{
  "question_id": 136,
  "question": "统计湖北省各公司拥有的危化品车辆数",
  "db": "MYSQL",
  "query": "SELECT c.company_name, COUNT(v.vehicle_id) FROM transportation.vehicle_company c JOIN transportation.vehicle v ON c.company_id = v.company_id JOIN common.vehicle_type_dict t ON v.vehicle_type_code = t.type_code WHERE v.area_id LIKE '42%' AND t.type_name = '危化品车' GROUP BY c.company_id;"
}
```

预测：

```json
{
  "question_id": 136,
  "db": "MYSQL",
  "query": "SELECT c.company_name, COUNT(v.vehicle_id) AS hazmat_vehicle_count FROM transportation.vehicle_company c JOIN transportation.vehicle v ON c.company_id = v.company_id JOIN common.vehicle_type_dict t ON v.vehicle_type_code = t.type_code JOIN common.administrative_division a ON c.area_id = a.id WHERE t.type_name = '危化品车' AND a.province_name = '湖北省' GROUP BY c.company_id, c.company_name;"
}
```

## 输入证据

```json
{
  "prompt_table_ids": [
    "MYSQL:common.administrative_division",
    "MYSQL:common.license_type_dict",
    "MYSQL:common.vehicle_type_dict",
    "MYSQL:transportation.driver",
    "MYSQL:transportation.vehicle",
    "MYSQL:transportation.vehicle_company"
  ],
  "reference_tables_not_in_prompt": [],
  "predicted_tables_not_in_prompt": [],
  "prompt_knowledge_ids": [
    1818,
    1791,
    1761,
    1765,
    561,
    1770,
    1787,
    1804,
    1348,
    1351,
    1820,
    444
  ],
  "prompt_example_ids": [
    130,
    125,
    133,
    23
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
    }
  ],
  "knowledge_in_actual_prompt": [
    {
      "knowledge_id": 1761,
      "knowledge_text": "行政区划代码（area_id）为6位数字编码。前2位代表省级行政区，前4位代表地市级行政区，6位全码代表区县级行政区。统计省份时使用 LEFT(area_id,2) 分组，统计城市时使用 LEFT(area_id,4) 分组，统计区县时使用 area_id 全码分组。省份名称可通过 administrative_division 表中 level=1 的记录获取，城市名称可通过 level=2 的记录获取。"
    },
    {
      "knowledge_id": 1820,
      "knowledge_text": "车辆注册地是车辆登记时所属的行政区划，反映车辆归属地。船舶注册地是船舶登记时所属的行政区划，反映船舶归属地。注册地影响车辆的保险、年检和监管归属。"
    }
  ],
  "raw_knowledge_not_in_actual_prompt": []
}
```

后续核验：明确地域约束作用于车辆还是公司，并检查同模板标签。

这是现有请求的静态证据归因，没有运行改提示词或换模型的控制变量实验。
