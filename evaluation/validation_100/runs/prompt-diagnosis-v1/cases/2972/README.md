# 2972：查询自持力超过45天的船舶，在最近24小时内位于(122.0, 30.0)至(122.2, 30.2)矩形内且速度小于3节的MMSI。

归类：**题目、参考或数据口径尚不能裁定**；原语义审查状态：`different`。

业务条件和两步result完整，差异仍在矩形边界是否纳入。题面没有给出边界约定，属于与参考严格不等价但无法唯一判定题意错误。

[实际请求和完整提示词](request.json) · [实际响应](response.json) · [结构化证据](diagnosis.json)

## 参考与预测

参考：

```json
{
  "question_id": 2972,
  "question": "查询自持力超过45天的船舶，在最近24小时内位于(122.0, 30.0)至(122.2, 30.2)矩形内且速度小于3节的MMSI。",
  "db1": "MYSQL",
  "query1": "SELECT mmsi FROM transportation.vessel WHERE endurance > 45",
  "db2": "POSTGRESQL",
  "query2": "SELECT DISTINCT mmsi FROM vessel_ais_data WHERE mmsi IN (result) AND timestamp >= NOW() - INTERVAL '24 hours' AND sog < 3 AND ST_Within(geom, ST_MakeEnvelope(122.0, 30.0, 122.2, 30.2, 4326))"
}
```

预测：

```json
{
  "question_id": 2972,
  "db1": "MYSQL",
  "query1": "SELECT mmsi FROM transportation.vessel WHERE endurance > 45",
  "db2": "POSTGRESQL",
  "query2": "SELECT DISTINCT mmsi FROM public.vessel_ais_data WHERE mmsi IN (result) AND timestamp >= NOW() - INTERVAL '24 hours' AND longitude BETWEEN 122.0 AND 122.2 AND latitude BETWEEN 30.0 AND 30.2 AND sog < 3"
}
```

## 输入证据

```json
{
  "prompt_table_ids": [
    "MYSQL:common.administrative_division",
    "MYSQL:common.vessel_type_dict",
    "MYSQL:transportation.shipping_company",
    "MYSQL:transportation.vehicle",
    "MYSQL:transportation.vessel",
    "POSTGRESQL:public.vessel_ais_data"
  ],
  "reference_tables_not_in_prompt": [],
  "predicted_tables_not_in_prompt": [],
  "prompt_knowledge_ids": [
    1786,
    1803,
    1777,
    1790,
    426,
    231,
    1739,
    1806,
    881,
    477,
    476,
    638
  ],
  "prompt_example_ids": [
    2975,
    118,
    2860,
    2969
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
      "question_id": 2975,
      "question": "查询最近24小时内位于(118.7, 20.1)半径5公里内且航行状态不为0的船舶，再找出其中自持力大于30天且最大荷载量超过40000吨的MMSI。",
      "steps": [
        {
          "engine": "POSTGRESQL",
          "query": "SELECT DISTINCT mmsi FROM vessel_ais_data WHERE timestamp >= NOW() - INTERVAL '24 hours' AND nav_status <> 0 AND ST_DWithin(geom::geography, ST_SetSRID(ST_MakePoint(118.7, 20.1), 4326)::geography, 5000)",
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
          "query": "SELECT mmsi FROM transportation.vessel WHERE mmsi IN (result) AND endurance > 30 AND max_load > 40000",
          "step": "query2",
          "table_ids": [
            "MYSQL:transportation.vessel"
          ],
          "joins": [],
          "parse_status": "parsed",
          "unresolved_tables": []
        }
      ]
    },
    {
      "question_id": 2860,
      "question": "查询以(123.0, 31.5)为圆心、半径18公里圆形区域内，所有速度小于3节的船舶记录，返回MMSI、记录时间和航行状态",
      "steps": [
        {
          "engine": "POSTGRESQL",
          "query": "SELECT mmsi, timestamp, nav_status FROM vessel_ais_data WHERE ST_DWithin(geom::geography, ST_SetSRID(ST_MakePoint(123.0, 31.5), 4326)::geography, 18000) AND sog < 3",
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
  "knowledge_in_actual_prompt": [
    {
      "knowledge_id": 1786,
      "knowledge_text": "船舶自持力 endurance 表示船舶在不补充燃料、淡水、食物的情况下能够连续航行的天数或海里数。"
    }
  ],
  "raw_knowledge_not_in_actual_prompt": []
}
```

后续核验：明确ST_Within或覆盖边界语义，而不是将两步结构完整与参考一致混为一谈。

这是现有请求的静态证据归因，没有运行改提示词或换模型的控制变量实验。
