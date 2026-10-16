# 2942：查询所属公司为长航集团的船舶，在2024年6月1日经过(121.0,31.0)至(121.5,31.5)矩形区域的轨迹，并返回船舶MMSI和在区域内的部分轨迹长度

归类：**已有证据未被模型正确利用**；原语义审查状态：`different`。

公司、两系统Schema、日期和题面矩形都已给出，案例3005也采用先按船生成轨迹再做空间关系。模型仍先过滤点再连线，未求整轨迹交集，并写出SUM包ST_MakeLine的同层聚合。未见输入强制它这样做。

[实际请求和完整提示词](request.json) · [实际响应](response.json) · [结构化证据](diagnosis.json)

## 参考与预测

参考：

```json
{
  "question_id": 2942,
  "question": "查询所属公司为长航集团的船舶，在2024年6月1日经过(121.0,31.0)至(121.5,31.5)矩形区域的轨迹，并返回船舶MMSI和在区域内的部分轨迹长度",
  "db1": "MYSQL",
  "query1": "SELECT v.mmsi FROM transportation.vessel v JOIN transportation.shipping_company sc ON v.company_id = sc.company_id WHERE sc.company_name = '长航集团'",
  "db2": "POSTGRESQL",
  "query2": "WITH tracks AS (SELECT mmsi, ST_MakeLine(geom ORDER BY timestamp) AS track FROM vessel_ais_data WHERE mmsi IN (result) AND timestamp::date = '2024-06-01' GROUP BY mmsi) SELECT mmsi, ST_Length(ST_Intersection(track, ST_MakeEnvelope(121.0, 31.0, 121.5, 31.5, 4326))::geography) AS length_in_area FROM tracks WHERE ST_Intersects(track, ST_MakeEnvelope(121.0, 31.0, 121.5, 31.5, 4326))"
}
```

预测：

```json
{
  "question_id": 2942,
  "db1": "MYSQL",
  "query1": "SELECT v.mmsi FROM transportation.vessel v JOIN transportation.shipping_company sc ON v.company_id = sc.company_id WHERE sc.company_name = '长航集团'",
  "db2": "POSTGRESQL",
  "query2": "SELECT mmsi, ROUND(SUM(ST_Length(ST_Transform(ST_MakeLine(geom ORDER BY timestamp), 3857)))::numeric, 2) AS track_length_meters FROM vessel_ais_data WHERE mmsi IN (result) AND timestamp >= '2024-06-01 00:00:00' AND timestamp < '2024-06-02 00:00:00' AND geom && ST_MakeEnvelope(121.0, 31.0, 121.5, 31.5, 4326) GROUP BY mmsi"
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
    1790,
    1739,
    1786,
    1777,
    1770,
    1803,
    1659,
    477,
    231,
    426,
    881,
    1806
  ],
  "prompt_example_ids": [
    3005,
    239,
    2692,
    2947
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
      "question_id": 3005,
      "question": "查询今天航行轨迹线穿越矩形区域(121.0,31.0,121.5,31.5)的船舶，按自持力降序排列。",
      "steps": [
        {
          "engine": "POSTGRESQL",
          "query": "SELECT mmsi FROM vessel_ais_data WHERE timestamp::date = CURRENT_DATE GROUP BY mmsi HAVING ST_Intersects(ST_MakeLine(geom ORDER BY timestamp), ST_MakeEnvelope(121.0, 31.0, 121.5, 31.5, 4326))",
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
          "query": "SELECT * FROM transportation.vessel WHERE mmsi IN (result) ORDER BY endurance DESC",
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

后续核验：检查空间运算顺序和数据库聚合约束；增加可执行语义校验才能拦截此类静态通过。

这是现有请求的静态证据归因，没有运行改提示词或换模型的控制变量实验。
