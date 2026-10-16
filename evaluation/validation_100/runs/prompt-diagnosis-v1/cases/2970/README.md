# 2970：查询船长姓名为‘张海’的船舶，在2024年6月1日08:00至12:00期间位于(121.5, 31.2)至(121.8, 31.4)矩形区域内且航行状态为系泊的MMSI。

归类：**题目、参考或数据口径尚不能裁定**；原语义审查状态：`different`。

两系统、公司/船长条件都保留，主要差异是BETWEEN闭边界与参考ST_Within开边界。题面矩形区域内未定义边界集合，不能据此断言路由或跨系统规划仍失败。

[实际请求和完整提示词](request.json) · [实际响应](response.json) · [结构化证据](diagnosis.json)

## 参考与预测

参考：

```json
{
  "question_id": 2970,
  "question": "查询船长姓名为‘张海’的船舶，在2024年6月1日08:00至12:00期间位于(121.5, 31.2)至(121.8, 31.4)矩形区域内且航行状态为系泊的MMSI。",
  "db1": "MYSQL",
  "query1": "SELECT v.mmsi FROM transportation.vessel v WHERE v.captain_name = '张海'",
  "db2": "POSTGRESQL",
  "query2": "SELECT DISTINCT mmsi FROM vessel_ais_data WHERE mmsi IN (result) AND timestamp BETWEEN '2024-06-01 08:00:00' AND '2024-06-01 12:00:00' AND nav_status = 5 AND ST_Within(geom, ST_MakeEnvelope(121.5, 31.2, 121.8, 31.4, 4326))"
}
```

预测：

```json
{
  "question_id": 2970,
  "db1": "POSTGRESQL",
  "query1": "SELECT DISTINCT mmsi FROM public.vessel_ais_data WHERE timestamp >= '2024-06-01 08:00:00' AND timestamp <= '2024-06-01 12:00:00' AND nav_status = 5 AND longitude >= 121.5 AND longitude <= 121.8 AND latitude >= 31.2 AND latitude <= 31.4",
  "db2": "MYSQL",
  "query2": "SELECT mmsi FROM transportation.vessel WHERE captain_name = '张海' AND mmsi IN (result)"
}
```

## 输入证据

```json
{
  "prompt_table_ids": [
    "MYSQL:common.administrative_division",
    "MYSQL:common.employee_type_dict",
    "MYSQL:common.vessel_type_dict",
    "MYSQL:transportation.employee",
    "MYSQL:transportation.vessel",
    "POSTGRESQL:public.vessel_ais_data"
  ],
  "reference_tables_not_in_prompt": [],
  "predicted_tables_not_in_prompt": [],
  "prompt_knowledge_ids": [
    1790,
    477,
    1821,
    426,
    231,
    1739,
    476,
    425,
    881,
    532,
    1806,
    530
  ],
  "prompt_example_ids": [
    2995,
    108,
    2497,
    3023
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
      "question_id": 2995,
      "question": "查询2024年6月1日上午8点到12点之间位于矩形区域(121.2,30.9,121.6,31.3)内的船舶，按船长姓名升序排列。",
      "steps": [
        {
          "engine": "POSTGRESQL",
          "query": "SELECT DISTINCT mmsi FROM vessel_ais_data WHERE timestamp BETWEEN '2024-06-01 08:00:00' AND '2024-06-01 12:00:00' AND ST_Within(geom, ST_MakeEnvelope(121.2, 30.9, 121.6, 31.3, 4326))",
          "step": "query1",
          "table_ids": [
            "POSTGRESQL:public.vessel_ais_data"
          ],
          "joins": [],
          "parse_status": "parsed",
          "unresolved_tables": []
        },
        {
          "engine": "MYSQL",
          "query": "SELECT * FROM transportation.vessel WHERE mmsi IN (result) ORDER BY captain_name ASC",
          "step": "query2",
          "table_ids": [
            "MYSQL:transportation.vessel"
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

后续核验：统一空间谓词的边界约定，并通过边界反例或实际数据评估影响。

这是现有请求的静态证据归因，没有运行改提示词或换模型的控制变量实验。
