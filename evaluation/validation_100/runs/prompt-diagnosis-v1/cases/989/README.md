# 989：统计山东省拥有风力发电场的电力企业数量

归类：**题目、参考或数据口径尚不能裁定**；原语义审查状态：`different`。

题面说山东省拥有风场的企业，模型按企业注册地，参考按场站所在地。两者业务意义不同，但题面没有清楚说明采用哪一处位置。

[实际请求和完整提示词](request.json) · [实际响应](response.json) · [结构化证据](diagnosis.json)

## 参考与预测

参考：

```json
{
  "question_id": 989,
  "question": "统计山东省拥有风力发电场的电力企业数量",
  "db": "MYSQL",
  "query": "SELECT COUNT(DISTINCT company_id) AS company_count FROM energy.energy_station WHERE area_id LIKE '37%' AND station_type_code = 'WP';"
}
```

预测：

```json
{
  "question_id": 989,
  "db": "MYSQL",
  "query": "SELECT COUNT(DISTINCT ec.company_id) AS company_count FROM energy.energy_company ec JOIN energy.energy_station es ON ec.company_id = es.company_id WHERE ec.area_id LIKE '37%' AND es.station_type_code = 'WP';"
}
```

## 输入证据

```json
{
  "prompt_table_ids": [
    "MYSQL:common.administrative_division",
    "MYSQL:energy.company_certification",
    "MYSQL:energy.employee",
    "MYSQL:energy.energy_company",
    "MYSQL:energy.energy_station",
    "MYSQL:energy.supply_area"
  ],
  "reference_tables_not_in_prompt": [],
  "predicted_tables_not_in_prompt": [],
  "prompt_knowledge_ids": [
    1593,
    1835,
    1580,
    1761,
    1603,
    1829,
    1348,
    1582,
    1341,
    1659,
    1356,
    1370
  ],
  "prompt_example_ids": [
    675,
    639,
    1014,
    1031
  ],
  "pruned_evidence": [],
  "rule_priority_excerpts": [
    "本次问题的统一口径如下，优先于训练案例及不明确的知识描述：",
    "1.比率、比例、百分比、平均值，用 ROUND(..., 2)。",
    "2.公式算出来的比率类、平均值类结果，以及每股类指标，包括资产负债率、总资产收益率、市盈率、每股现金分红 DPS 等，用 ROUND(..., 2)。",
    "3.其他情况一律不使用 ROUND。"
  ],
  "examples_in_actual_prompt": [],
  "knowledge_in_actual_prompt": [],
  "raw_knowledge_not_in_actual_prompt": []
}
```

后续核验：先确定区域修饰对象并统一同模板标注。

这是现有请求的静态证据归因，没有运行改提示词或换模型的控制变量实验。
