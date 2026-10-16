# 1728：查询院系编号为2的班级列表，返回班级编号与名称，并按班级编号升序取前30条。

归类：**题目、参考或数据口径尚不能裁定**；原语义审查状态：`different`。

两个年份class表都已召回，题面不含年份且结构相同，参考2025与预测2024的差异没有题面裁决依据。

[实际请求和完整提示词](request.json) · [实际响应](response.json) · [结构化证据](diagnosis.json)

## 参考与预测

参考：

```json
{
  "question_id": 1728,
  "question": "查询院系编号为2的班级列表，返回班级编号与名称，并按班级编号升序取前30条。",
  "db": "MYSQL",
  "query": "SELECT cl.class_id, cl.class_name FROM education_2025.class cl WHERE cl.department_id=2 ORDER BY cl.class_id ASC LIMIT 30;"
}
```

预测：

```json
{
  "question_id": 1728,
  "db": "MYSQL",
  "query": "SELECT cl.class_id, cl.class_name FROM education_2024.class cl WHERE cl.department_id = 2 ORDER BY cl.class_id ASC LIMIT 30;"
}
```

## 输入证据

```json
{
  "prompt_table_ids": [
    "MYSQL:education_2024.class",
    "MYSQL:education_2024.department",
    "MYSQL:education_2024.student",
    "MYSQL:education_2025.class",
    "MYSQL:education_2025.course",
    "MYSQL:education_2025.department"
  ],
  "reference_tables_not_in_prompt": [],
  "predicted_tables_not_in_prompt": [],
  "prompt_knowledge_ids": [
    1042,
    1026,
    1027,
    720,
    1351,
    1230,
    1044,
    1575,
    1043,
    1250,
    1045,
    347
  ],
  "prompt_example_ids": [
    1651,
    1772,
    1629,
    1666
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

后续核验：修复题目/标签歧义后再评价路由或生成模型。

这是现有请求的静态证据归因，没有运行改提示词或换模型的控制变量实验。
