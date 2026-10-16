# 935：统计衡阳市发电场站中火电场的装机容量

归类：**输入与模型处理混合**；原语义审查状态：`different`。

正确能源代码THERMAL知识1581未召回；但场站类型知识1582和案例603已显示能源类型与场站类型是两套字段。模型在station_type_dict中猜火电名称，兼有知识缺口与字典维度混淆。

[实际请求和完整提示词](request.json) · [实际响应](response.json) · [结构化证据](diagnosis.json)

## 参考与预测

参考：

```json
{
  "question_id": 935,
  "question": "统计衡阳市发电场站中火电场的装机容量",
  "db": "MYSQL",
  "query": "SELECT SUM(installed_capacity) AS thermal_capacity FROM energy.energy_station WHERE area_id LIKE '4304%' AND energy_type_code = 'THERMAL';"
}
```

预测：

```json
{
  "question_id": 935,
  "db": "MYSQL",
  "query": "SELECT SUM(es.installed_capacity) AS total_installed_capacity FROM energy.energy_station es JOIN common.administrative_division ad ON es.area_id = ad.id JOIN common.station_type_dict std ON es.station_type_code = std.type_code WHERE ad.city_name = '衡阳市' AND std.type_name = '火电';"
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
    1603,
    1830,
    1583,
    1601,
    1582,
    1580,
    1761,
    1593,
    1594,
    1835,
    815,
    474
  ],
  "prompt_example_ids": [
    1006,
    603,
    577,
    664
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
      "question_id": 603,
      "question": "查询各发电场站中装机容量超过同类型平均装机容量的场站名称",
      "steps": [
        {
          "engine": "MYSQL",
          "query": "SELECT es.station_name, es.installed_capacity, et.type_name FROM energy.energy_station es JOIN common.energy_type_dict et ON es.energy_type_code = et.type_code WHERE es.installed_capacity > (SELECT AVG(es2.installed_capacity) FROM energy.energy_station es2 WHERE es2.energy_type_code = es.energy_type_code);",
          "step": "query",
          "table_ids": [
            "MYSQL:common.energy_type_dict",
            "MYSQL:energy.energy_station"
          ],
          "joins": [
            {
              "left_table": "MYSQL:energy.energy_station",
              "left_columns": [
                "energy_type_code"
              ],
              "right_table": "MYSQL:common.energy_type_dict",
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
      "question_id": 664,
      "question": "统计各发电场站类型的平均装机容量",
      "steps": [
        {
          "engine": "MYSQL",
          "query": "SELECT st.type_name, AVG(es.installed_capacity) AS avg_capacity FROM energy.energy_station es JOIN common.station_type_dict st ON es.station_type_code = st.type_code GROUP BY st.type_name;",
          "step": "query",
          "table_ids": [
            "MYSQL:common.station_type_dict",
            "MYSQL:energy.energy_station"
          ],
          "joins": [
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
  "raw_knowledge_not_in_actual_prompt": [
    {
      "knowledge_id": 1581,
      "knowledge_text": "能源类型分类：火电(THERMAL)、水电(HYDRO)、风电(WIND)、光伏(SOLAR)、核电(NUCLEAR)、生物质发电(BIOMASS)、天然气发电(GAS)、抽水蓄能(PUMPED)、地热发电(GEOTHERMAL)、氢能(HYDROGEN)。清洁能源包括水电、核电、天然气发电、抽水蓄能，新能源包括风电、光伏、生物质发电、地热发电、氢能。可再生能源包括水电、风电、光伏、生物质发电、地热发电。",
      "frozen_index_engines": [
        "MYSQL"
      ],
      "frozen_index_table_ids": [
        "MYSQL:common.energy_type_dict"
      ],
      "scope": "Offline diagnosis only; not added to generation or production association"
    }
  ]
}
```

后续核验：补能源类型映射，同时检查模型是否仍把能源类型放到场站类型字典。

这是现有请求的静态证据归因，没有运行改提示词或换模型的控制变量实验。
