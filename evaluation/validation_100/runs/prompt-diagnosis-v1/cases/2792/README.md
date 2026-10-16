# 2792：查询船首向（heading）在0到90度之间且对地航向（cog）也在0到90度之间的船舶

归类：**题目、参考或数据口径尚不能裁定**；原语义审查状态：`different`。

案例中既有船舶AIS记录SELECT *，也有按MMSI去重；题面没有写每船一行或返回三列。参考和预测的行粒度有差异，但当前输入缺少统一船舶查询默认粒度。

[实际请求和完整提示词](request.json) · [实际响应](response.json) · [结构化证据](diagnosis.json)

## 参考与预测

参考：

```json
{
  "question_id": 2792,
  "question": "查询船首向（heading）在0到90度之间且对地航向（cog）也在0到90度之间的船舶",
  "db": "POSTGRESQL",
  "query": "SELECT DISTINCT ON (mmsi) mmsi, heading, cog FROM vessel_ais_data WHERE heading BETWEEN 0 AND 90 AND cog BETWEEN 0 AND 90 ORDER BY mmsi"
}
```

预测：

```json
{
  "question_id": 2792,
  "db": "POSTGRESQL",
  "query": "SELECT * FROM public.vessel_ais_data WHERE heading BETWEEN 0 AND 90 AND cog BETWEEN 0 AND 90"
}
```

## 输入证据

```json
{
  "prompt_table_ids": [
    "POSTGRESQL:public.vessel_ais_data"
  ],
  "reference_tables_not_in_prompt": [],
  "predicted_tables_not_in_prompt": [],
  "prompt_knowledge_ids": [
    1739,
    881,
    476,
    638,
    425,
    653
  ],
  "prompt_example_ids": [
    2543,
    2643,
    2836,
    2871
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
      "question_id": 2543,
      "question": "查询在2024年6月1日09:00:00至11:00:00期间，航向在0到90度之间的货船的记录，按航向升序、速度降序排列。",
      "steps": [
        {
          "engine": "POSTGRESQL",
          "query": "SELECT * FROM vessel_ais_data WHERE timestamp BETWEEN '2024-06-01 09:00:00' AND '2024-06-01 11:00:00' AND vessel_type = 70 AND cog BETWEEN 0 AND 90 ORDER BY cog ASC, sog DESC",
          "step": "query",
          "table_ids": [
            "POSTGRESQL:public.vessel_ais_data"
          ],
          "joins": [],
          "parse_status": "parsed",
          "unresolved_tables": []
        }
      ]
    },
    {
      "question_id": 2836,
      "question": "查询所有船首向（heading）与对地航向（cog）完全相同（差值=0）的船舶",
      "steps": [
        {
          "engine": "POSTGRESQL",
          "query": "SELECT DISTINCT ON (mmsi) mmsi, heading, cog FROM vessel_ais_data WHERE heading IS NOT NULL AND heading = cog ORDER BY mmsi, timestamp DESC",
          "step": "query",
          "table_ids": [
            "POSTGRESQL:public.vessel_ais_data"
          ],
          "joins": [],
          "parse_status": "parsed",
          "unresolved_tables": []
        }
      ]
    },
    {
      "question_id": 2871,
      "question": "查询矩形(121.0, 31.5)至(122.0, 32.0)内，对地航向在0到45度之间的船舶，按时间戳升序取20条",
      "steps": [
        {
          "engine": "POSTGRESQL",
          "query": "SELECT * FROM vessel_ais_data WHERE longitude BETWEEN 121.0 AND 122.0 AND latitude BETWEEN 31.5 AND 32.0 AND cog BETWEEN 0 AND 45 ORDER BY timestamp ASC LIMIT 20",
          "step": "query",
          "table_ids": [
            "POSTGRESQL:public.vessel_ais_data"
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

后续核验：明确查询船舶与查询AIS记录的输出粒度及最新/任一记录规则。

这是现有请求的静态证据归因，没有运行改提示词或换模型的控制变量实验。
