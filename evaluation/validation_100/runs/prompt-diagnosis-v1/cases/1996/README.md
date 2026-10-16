# 1996：比较2024与2025学期一中每门课程的平均学分，取课程表学分，返回两年平均学分，对课程求平均。

归类：**输入与模型处理混合**；原语义审查状态：`different`。

整个2025业务库未进入初始Schema；模型未请求补证据，还把学期一解释为学年，忽略已可见的2024选课/学期结构。案例1839本身题面>=5而SQL>=3，存在不可靠示例干扰。

[实际请求和完整提示词](request.json) · [实际响应](response.json) · [结构化证据](diagnosis.json)

## 参考与预测

参考：

```json
{
  "question_id": 1996,
  "question": "比较2024与2025学期一中每门课程的平均学分，取课程表学分，返回两年平均学分，对课程求平均。",
  "db": "MYSQL",
  "query": "WITH p2024 AS (SELECT DISTINCT e.course_id, c.credit FROM education_2024.enrollment e JOIN education_2024.course c ON c.course_id=e.course_id WHERE e.semester_id=1 AND e.is_withdraw=0), p2025 AS (SELECT DISTINCT e.course_id, c.credit FROM education_2025.enrollment e JOIN education_2025.course c ON c.course_id=e.course_id WHERE e.semester_id=1 AND e.is_withdraw=0) SELECT (SELECT ROUND(AVG(credit),2) FROM p2024) AS avg_credit_for_distinct_courses_2024, (SELECT ROUND(AVG(credit),2) FROM p2025) AS avg_credit_for_distinct_courses_2025;"
}
```

预测：

```json
{
  "question_id": 1996,
  "db": "MYSQL",
  "query": "SELECT '2024' AS year, ROUND(AVG(credit),2) AS avg_credit FROM education_2024.course UNION ALL SELECT '2025' AS year, ROUND(AVG(credit),2) AS avg_credit FROM education_2025.course;"
}
```

## 输入证据

```json
{
  "prompt_table_ids": [
    "MYSQL:education_2024.course",
    "MYSQL:education_2024.department",
    "MYSQL:education_2024.enrollment",
    "MYSQL:education_2024.exam_score",
    "MYSQL:education_2024.semester",
    "MYSQL:education_2024.teacher"
  ],
  "reference_tables_not_in_prompt": [
    "MYSQL:education_2025.course",
    "MYSQL:education_2025.enrollment"
  ],
  "predicted_tables_not_in_prompt": [
    "MYSQL:education_2025.course"
  ],
  "prompt_knowledge_ids": [
    1385,
    1513,
    878,
    847,
    885,
    1026,
    1294,
    1323,
    888,
    1027,
    855,
    283
  ],
  "prompt_example_ids": [
    1964,
    1839,
    1951,
    1999
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
      "question_id": 1964,
      "question": "比较2024与2025课程表中院系编号为2的课程平均学分，返回两年平均值，保留两位小数，及差值，即2025减2024。",
      "steps": [
        {
          "engine": "MYSQL",
          "query": "WITH a AS (SELECT ROUND(AVG(credit),2) AS avg_credit_2024 FROM education_2024.course WHERE department_id=2), b AS (SELECT ROUND(AVG(credit),2) AS avg_credit_2025 FROM education_2025.course WHERE department_id=2) SELECT (b.avg_credit_2025-a.avg_credit_2024) AS diff_avg_credit_2025_minus_2024, a.avg_credit_2024, b.avg_credit_2025 FROM a CROSS JOIN b;",
          "step": "query",
          "table_ids": [
            "MYSQL:education_2024.course",
            "MYSQL:education_2025.course"
          ],
          "joins": [],
          "parse_status": "parsed",
          "unresolved_tables": []
        }
      ]
    },
    {
      "question_id": 1839,
      "question": "比较2024与2025课程学分不低于5的课程平均学分，并返回两年结果。",
      "steps": [
        {
          "engine": "MYSQL",
          "query": "SELECT '2024' AS year, ROUND(AVG(credit),2) AS avg_credit_ge_5 FROM education_2024.course WHERE credit>=3 UNION ALL SELECT '2025' AS year, ROUND(AVG(credit),2) AS avg_credit_ge_5 FROM education_2025.course WHERE credit>=3;",
          "step": "query",
          "table_ids": [
            "MYSQL:education_2024.course",
            "MYSQL:education_2025.course"
          ],
          "joins": [],
          "parse_status": "parsed",
          "unresolved_tables": []
        }
      ]
    }
  ],
  "knowledge_in_actual_prompt": [],
  "raw_knowledge_not_in_actual_prompt": []
}
```

后续核验：补跨年度选课/课程结构，逐项检查学期、退课和课程粒度，避免用假设删除需求。

这是现有请求的静态证据归因，没有运行改提示词或换模型的控制变量实验。
