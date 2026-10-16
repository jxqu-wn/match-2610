# 2907：查询今天出现在青岛朝连岛附近水域禁航区的船舶MMSI和平均航速。

归类：**已有证据未被模型正确利用**；原语义审查状态：`different`。

案例2932已给出朝连岛同名禁航区的精确多边形，坐标与参考完全一致。模型却声称没有精确边界，并将经度整体移到另一侧，属于实际输入已有正确值却未正确利用。

[实际请求和完整提示词](request.json) · [实际响应](response.json) · [结构化证据](diagnosis.json)

## 参考与预测

参考：

```json
{
  "question_id": 2907,
  "question": "查询今天出现在青岛朝连岛附近水域禁航区的船舶MMSI和平均航速。",
  "db": "POSTGRESQL",
  "query": "SELECT mmsi, AVG(sog) AS avg_sog FROM vessel_ais_data WHERE timestamp::date = CURRENT_DATE AND ST_Within(geom, ST_GeomFromText('POLYGON((121.1667 35.8333, 121.50 35.8333, 121.50 35.5833, 121.1667 35.5833, 121.1667 35.8333))', 4326)) GROUP BY mmsi"
}
```

预测：

```json
{
  "question_id": 2907,
  "db": "POSTGRESQL",
  "query": "SELECT mmsi, ROUND(AVG(sog), 2) AS avg_sog FROM public.vessel_ais_data WHERE timestamp::date = CURRENT_DATE AND ST_Within(geom, ST_GeomFromText('POLYGON((120.9167 35.8333, 121.1667 35.8333, 121.1667 35.5833, 120.9167 35.5833, 120.9167 35.8333))', 4326)) GROUP BY mmsi"
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
    881,
    1739,
    638,
    476,
    425,
    653
  ],
  "prompt_example_ids": [
    2661,
    2514,
    2932,
    2666
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
      "question_id": 2932,
      "question": "找出最近24小时内进入宁波舟山港穿山港区警戒区的船舶，且这些船舶曾经在青岛朝连岛禁航区内出现过，返回船舶MMSI。",
      "steps": [
        {
          "engine": "POSTGRESQL",
          "query": "WITH zone1 AS (SELECT ST_SetSRID(ST_MakePoint(122.1667, 29.8667), 4326)::geography AS center), zone2 AS (SELECT ST_GeomFromText('POLYGON((121.1667 35.8333, 121.50 35.8333, 121.50 35.5833, 121.1667 35.5833, 121.1667 35.8333))', 4326) AS polygon) SELECT DISTINCT v1.mmsi FROM vessel_ais_data v1, zone1 z WHERE v1.timestamp >= NOW() - INTERVAL '24 hours' AND ST_DWithin(v1.geom::geography, z.center, 926) AND v1.mmsi IN (SELECT v2.mmsi FROM vessel_ais_data v2 WHERE ST_Within(v2.geom, (SELECT polygon FROM zone2)))",
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

后续核验：核验assumptions中的缺证据声明，优先测试模型对长案例中嵌套空间常量的提取能力。

这是现有请求的静态证据归因，没有运行改提示词或换模型的控制变量实验。
