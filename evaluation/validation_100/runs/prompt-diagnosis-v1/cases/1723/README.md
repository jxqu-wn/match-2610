# 1723：统计学期表共有多少条记录，并返回数量。

归类：**题目、参考或数据口径尚不能裁定**；原语义审查状态：`different`。

两个年份semester表都在提示词中，问题未指明年份。参考选2025、预测选2024，输入无法提供唯一正确年份，不是系统路由漏库。

[实际请求和完整提示词](request.json) · [实际响应](response.json) · [结构化证据](diagnosis.json)

## 参考与预测

参考：

```json
{
  "question_id": 1723,
  "question": "统计学期表共有多少条记录，并返回数量。",
  "db": "MYSQL",
  "query": "SELECT COUNT(*) AS semester_cnt FROM education_2025.semester sem;"
}
```

预测：

```json
{
  "question_id": 1723,
  "db": "MYSQL",
  "query": "SELECT COUNT(*) AS semester_cnt FROM education_2024.semester;"
}
```

## 输入证据

```json
{
  "prompt_table_ids": [
    "MYSQL:common.dict_semester_type",
    "MYSQL:education_2024.enrollment",
    "MYSQL:education_2024.semester",
    "MYSQL:education_2025.enrollment",
    "MYSQL:education_2025.semester",
    "MYSQL:education_2025.student"
  ],
  "reference_tables_not_in_prompt": [],
  "predicted_tables_not_in_prompt": [],
  "prompt_knowledge_ids": [
    1509,
    1230,
    848,
    1576,
    1400,
    1513,
    1294,
    1575,
    1385,
    878,
    940,
    888
  ],
  "prompt_example_ids": [
    1652,
    1771,
    1780,
    1775
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

后续核验：补问题年份或建立公开、统一、与标签一致的默认年份规则。

这是现有请求的静态证据归因，没有运行改提示词或换模型的控制变量实验。
