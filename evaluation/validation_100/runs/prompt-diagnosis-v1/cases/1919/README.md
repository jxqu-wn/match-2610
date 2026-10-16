# 1919：比较2024与2025学期表中结束日期键最大的记录数量，按结束日期键排序取前1学期代码后，再统计该前1对应的行数，返回两年数量。

归类：**题目、参考或数据口径尚不能裁定**；原语义审查状态：`different`。

题面明确先取前1学期代码再计数，预测正按semester_code实现；参考按最大end_date_key并列计数且改变结果布局。该题先要裁定参考与题意，而不是按生成算法不同推断模型能力。

[实际请求和完整提示词](request.json) · [实际响应](response.json) · [结构化证据](diagnosis.json)

## 参考与预测

参考：

```json
{
  "question_id": 1919,
  "question": "比较2024与2025学期表中结束日期键最大的记录数量，按结束日期键排序取前1学期代码后，再统计该前1对应的行数，返回两年数量。",
  "db": "MYSQL",
  "query": "WITH t2024 AS (SELECT end_date_key, COUNT(*) AS cnt FROM education_2024.semester WHERE end_date_key IS NOT NULL GROUP BY end_date_key ORDER BY end_date_key DESC LIMIT 1), t2025 AS (SELECT end_date_key, COUNT(*) AS cnt FROM education_2025.semester WHERE end_date_key IS NOT NULL GROUP BY end_date_key ORDER BY end_date_key DESC LIMIT 1) SELECT t2025.cnt AS top_end_date_key_row_cnt_2025, t2024.cnt AS top_end_date_key_row_cnt_2024 FROM t2024 CROSS JOIN t2025;"
}
```

预测：

```json
{
  "question_id": 1919,
  "db": "MYSQL",
  "query": "SELECT '2024' AS year, COUNT(*) AS cnt FROM education_2024.semester WHERE semester_code = (SELECT semester_code FROM education_2024.semester ORDER BY end_date_key DESC LIMIT 1) UNION ALL SELECT '2025' AS year, COUNT(*) AS cnt FROM education_2025.semester WHERE semester_code = (SELECT semester_code FROM education_2025.semester ORDER BY end_date_key DESC LIMIT 1);"
}
```

## 输入证据

```json
{
  "prompt_table_ids": [
    "MYSQL:education_2024.enrollment",
    "MYSQL:education_2024.semester",
    "MYSQL:education_2025.course",
    "MYSQL:education_2025.enrollment",
    "MYSQL:education_2025.semester",
    "MYSQL:education_2025.student"
  ],
  "reference_tables_not_in_prompt": [],
  "predicted_tables_not_in_prompt": [],
  "prompt_knowledge_ids": [
    1385,
    1513,
    1576,
    1509,
    878,
    1575,
    1294,
    1323,
    1210,
    1230,
    888,
    1400
  ],
  "prompt_example_ids": [
    2052,
    1940,
    1913,
    1932
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
      "question_id": 2052,
      "question": "比较2024与2025学期表中结束日期键为空的记录数，返回两年数量。",
      "steps": [
        {
          "engine": "MYSQL",
          "query": "SELECT '2024' AS year, COUNT(*) AS end_date_key_is_null_cnt FROM education_2024.semester WHERE end_date_key IS NULL UNION ALL SELECT '2025' AS year, COUNT(*) AS end_date_key_is_null_cnt FROM education_2025.semester WHERE end_date_key IS NULL;",
          "step": "query",
          "table_ids": [
            "MYSQL:education_2024.semester",
            "MYSQL:education_2025.semester"
          ],
          "joins": [],
          "parse_status": "parsed",
          "unresolved_tables": []
        }
      ]
    },
    {
      "question_id": 1940,
      "question": "比较2024与2025学期表中学期代码包含2025的数量，返回两年数量。",
      "steps": [
        {
          "engine": "MYSQL",
          "query": "SELECT '2024' AS year, COUNT(*) AS semester_code_like_2025_cnt FROM education_2024.semester WHERE semester_code LIKE '%2025%' UNION ALL SELECT '2025' AS year, COUNT(*) AS semester_code_like_2025_cnt FROM education_2025.semester WHERE semester_code LIKE '%2025%';",
          "step": "query",
          "table_ids": [
            "MYSQL:education_2024.semester",
            "MYSQL:education_2025.semester"
          ],
          "joins": [],
          "parse_status": "parsed",
          "unresolved_tables": []
        }
      ]
    },
    {
      "question_id": 1932,
      "question": "比较2024与2025学期表中结束日期键为空或0的学期数量，返回两年数量。",
      "steps": [
        {
          "engine": "MYSQL",
          "query": "SELECT '2024' AS year, COUNT(*) AS semester_end_date_empty_or_zero_cnt FROM education_2024.semester WHERE end_date_key IS NULL OR end_date_key=0 UNION ALL SELECT '2025' AS year, COUNT(*) AS semester_end_date_empty_or_zero_cnt FROM education_2025.semester WHERE end_date_key IS NULL OR end_date_key=0;",
          "step": "query",
          "table_ids": [
            "MYSQL:education_2024.semester",
            "MYSQL:education_2025.semester"
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

后续核验：明确最大日期并列记录与前1学期代码的区别及两年输出布局。

这是现有请求的静态证据归因，没有运行改提示词或换模型的控制变量实验。
