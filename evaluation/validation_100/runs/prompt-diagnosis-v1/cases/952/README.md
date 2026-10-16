# 952：统计伊犁州发电场站中风电场的总装机容量

归类：**题目、参考或数据口径尚不能裁定**；原语义审查状态：`uncertain`。

伊犁州full_name前缀是否为伊犁需要实际字典值，Schema仅声明行政区划全称。当前输入与离线资料均不足以验证名称前缀和6540编码等价。

[实际请求和完整提示词](request.json) · [实际响应](response.json) · [结构化证据](diagnosis.json)

## 参考与预测

参考：

```json
{
  "question_id": 952,
  "question": "统计伊犁州发电场站中风电场的总装机容量",
  "db": "MYSQL",
  "query": "SELECT SUM(installed_capacity) AS wind_capacity FROM energy.energy_station WHERE area_id LIKE '6540%' AND station_type_code = 'WP';"
}
```

预测：

```json
{
  "question_id": 952,
  "db": "MYSQL",
  "query": "SELECT SUM(es.installed_capacity) AS total_capacity FROM energy.energy_station es JOIN common.administrative_division ad ON es.area_id = ad.id WHERE ad.full_name LIKE '伊犁%' AND es.station_type_code = 'WP';"
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
    1582,
    1830,
    1583,
    1603,
    1593,
    1601,
    1580,
    1835,
    1581,
    1761,
    1594,
    432
  ],
  "prompt_example_ids": [
    577,
    949,
    664,
    656
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
      "question_id": 949,
      "question": "统计大理州发电场站中风电场的总装机容量",
      "steps": [
        {
          "engine": "MYSQL",
          "query": "SELECT SUM(installed_capacity) AS wind_capacity FROM energy.energy_station WHERE area_id LIKE '5329%' AND station_type_code = 'WP';",
          "step": "query",
          "table_ids": [
            "MYSQL:energy.energy_station"
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
      "knowledge_id": 1761,
      "knowledge_text": "行政区划代码（area_id）为6位数字编码。前2位代表省级行政区，前4位代表地市级行政区，6位全码代表区县级行政区。统计省份时使用 LEFT(area_id,2) 分组，统计城市时使用 LEFT(area_id,4) 分组，统计区县时使用 area_id 全码分组。省份名称可通过 administrative_division 表中 level=1 的记录获取，城市名称可通过 level=2 的记录获取。"
    }
  ],
  "raw_knowledge_not_in_actual_prompt": []
}
```

后续核验：提供可验证的行政区划值映射，而非凭全称字段名推断字符串格式。

这是现有请求的静态证据归因，没有运行改提示词或换模型的控制变量实验。
