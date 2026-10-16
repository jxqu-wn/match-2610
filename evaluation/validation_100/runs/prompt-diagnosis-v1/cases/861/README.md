# 861：统计东莞市发电场站中运营超过15年的场站数量

归类：**题目、参考或数据口径尚不能裁定**；原语义审查状态：`different`。

预测按场站category=发电过滤，题面也写发电场站；参考未做该过滤。知识1582和案例615支持发电/非发电区分，预测的额外条件可能符合题意。

[实际请求和完整提示词](request.json) · [实际响应](response.json) · [结构化证据](diagnosis.json)

## 参考与预测

参考：

```json
{
  "question_id": 861,
  "question": "统计东莞市发电场站中运营超过15年的场站数量",
  "db": "MYSQL",
  "query": "SELECT COUNT(*) AS old_station_count FROM energy.energy_station WHERE area_id LIKE '4419%' AND TIMESTAMPDIFF(YEAR, grid_connect_date, CURDATE()) > 15;"
}
```

预测：

```json
{
  "question_id": 861,
  "db": "MYSQL",
  "query": "SELECT COUNT(*) AS station_count FROM energy.energy_station es JOIN common.station_type_dict std ON es.station_type_code = std.type_code JOIN common.administrative_division ad ON es.area_id = ad.id WHERE ad.city_name = '东莞市' AND std.category = '发电' AND TIMESTAMPDIFF(YEAR, es.grid_connect_date, CURDATE()) > 15;"
}
```

## 输入证据

```json
{
  "prompt_table_ids": [
    "MYSQL:common.administrative_division",
    "MYSQL:common.energy_type_dict",
    "MYSQL:common.station_type_dict",
    "MYSQL:energy.employee",
    "MYSQL:energy.energy_company",
    "MYSQL:energy.energy_station"
  ],
  "reference_tables_not_in_prompt": [],
  "predicted_tables_not_in_prompt": [],
  "prompt_knowledge_ids": [
    1580,
    1582,
    1592,
    1804,
    1591,
    1831,
    1833,
    1593,
    1594,
    1603,
    1761,
    1830
  ],
  "prompt_example_ids": [
    1045,
    921,
    615,
    1043
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
      "question_id": 1045,
      "question": "统计珠三角各城市发电场站中运营超过20年的老旧场站数量",
      "steps": [
        {
          "engine": "MYSQL",
          "query": "SELECT LEFT(area_id,4) AS city_code, COUNT(*) AS old_station_count FROM energy.energy_station WHERE LEFT(area_id,4) IN ('4401','4403','4404','4406','4413','4419','4420','4407','4412') AND TIMESTAMPDIFF(YEAR, grid_connect_date, CURDATE()) > 20 GROUP BY LEFT(area_id,4);",
          "step": "query",
          "table_ids": [
            "MYSQL:energy.energy_station"
          ],
          "joins": [],
          "parse_status": "parsed",
          "unresolved_tables": []
        }
      ]
    },
    {
      "question_id": 615,
      "question": "统计各电力企业中发电类场站和非发电类场站的数量",
      "steps": [
        {
          "engine": "MYSQL",
          "query": "SELECT ec.company_name, SUM(CASE WHEN st.category='发电' THEN 1 ELSE 0 END) AS generation_count, SUM(CASE WHEN st.category!='发电' THEN 1 ELSE 0 END) AS other_count FROM energy.energy_company ec JOIN energy.energy_station es ON ec.company_id = es.company_id JOIN common.station_type_dict st ON es.station_type_code = st.type_code GROUP BY ec.company_id, ec.company_name;",
          "step": "query",
          "table_ids": [
            "MYSQL:common.station_type_dict",
            "MYSQL:energy.energy_company",
            "MYSQL:energy.energy_station"
          ],
          "joins": [
            {
              "left_table": "MYSQL:energy.energy_company",
              "left_columns": [
                "company_id"
              ],
              "right_table": "MYSQL:energy.energy_station",
              "right_columns": [
                "company_id"
              ]
            },
            {
              "left_table": "MYSQL:energy.energy_station",
              "left_columns": [
                "station_type_code"
              ],
              "right_table": "MYSQL:common.station_type_dict",
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
      "knowledge_id": 1582,
      "knowledge_text": "场站类型代码映射：PP=发电厂，SUB=变电站，TL=输电线路，DS=配电站，WP=风电场，SP=光伏电站，HP=水电站，NP=核电站，ES=储能站，CC=集控中心。发电类场站包括PP、WP、SP、HP、NP。"
    }
  ],
  "raw_knowledge_not_in_actual_prompt": []
}
```

后续核验：先确认参考是否有意将所有能源场站都称为发电场站。

这是现有请求的静态证据归因，没有运行改提示词或换模型的控制变量实验。
