# 758：统计武汉市电力企业中学历为大专的员工数量

归类：**输入与模型处理混合**；原语义审查状态：`different`。

行政区划表DDL未展示，模型仍按全码连接后用ad.name=武汉市，无法覆盖区县。知识1761提示城市前4位；输入缺结构，模型也没有正确处理层级。

[实际请求和完整提示词](request.json) · [实际响应](response.json) · [结构化证据](diagnosis.json)

## 参考与预测

参考：

```json
{
  "question_id": 758,
  "question": "统计武汉市电力企业中学历为大专的员工数量",
  "db": "MYSQL",
  "query": "SELECT COUNT(*) AS diploma_count FROM energy.employee e JOIN energy.energy_company ec ON e.company_id = ec.company_id WHERE ec.area_id LIKE '4201%' AND e.education = '大专';"
}
```

预测：

```json
{
  "question_id": 758,
  "db": "MYSQL",
  "query": "SELECT COUNT(*) AS count FROM energy.employee e JOIN energy.energy_company ec ON e.company_id = ec.company_id JOIN common.administrative_division ad ON ec.area_id = ad.id WHERE ad.name = '武汉市' AND e.education = '大专';"
}
```

## 输入证据

```json
{
  "prompt_table_ids": [
    "MYSQL:common.dict_academic_level",
    "MYSQL:common.energy_position_dict",
    "MYSQL:education_2025.class",
    "MYSQL:energy.employee",
    "MYSQL:energy.energy_company",
    "MYSQL:energy.energy_station"
  ],
  "reference_tables_not_in_prompt": [],
  "predicted_tables_not_in_prompt": [
    "MYSQL:common.administrative_division"
  ],
  "prompt_knowledge_ids": [
    1580,
    1589,
    1761,
    529,
    1149,
    530,
    533,
    1137,
    537,
    1147,
    534,
    1026
  ],
  "prompt_example_ids": [
    600,
    692,
    1009,
    597
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
      "question_id": 692,
      "question": "统计电力企业各学历员工的数量分布",
      "steps": [
        {
          "engine": "MYSQL",
          "query": "SELECT education, COUNT(*) AS count FROM energy.employee GROUP BY education ORDER BY count DESC;",
          "step": "query",
          "table_ids": [
            "MYSQL:energy.employee"
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

后续核验：保证区划表可见，区分name与city_name、全码与前缀关联。

这是现有请求的静态证据归因，没有运行改提示词或换模型的控制变量实验。
