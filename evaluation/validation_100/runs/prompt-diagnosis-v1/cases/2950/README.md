# 2950：找到最大航速大于20节的船舶，统计其在最近24小时内以(121.5,31.2)为中心、半径15公里范围内的出现次数。

归类：**规则或案例冲突**；原语义审查状态：`different`。

输入的高优先级数量只输出1列与参考每MMSI返回维度+次数不兼容。题面其是否指每船也需澄清。模型输出单列总数符合过宽规则；没有去规则对照，不能证明唯一因果。

[实际请求和完整提示词](request.json) · [实际响应](response.json) · [结构化证据](diagnosis.json)

## 参考与预测

参考：

```json
{
  "question_id": 2950,
  "question": "找到最大航速大于20节的船舶，统计其在最近24小时内以(121.5,31.2)为中心、半径15公里范围内的出现次数。",
  "db1": "MYSQL",
  "query1": "SELECT mmsi FROM transportation.vessel WHERE max_speed > 20",
  "db2": "POSTGRESQL",
  "query2": "SELECT mmsi, COUNT(*) AS appearances FROM vessel_ais_data WHERE mmsi IN (result) AND timestamp >= NOW() - INTERVAL '24 hours' AND ST_DWithin(geom::geography, ST_SetSRID(ST_MakePoint(121.5, 31.2), 4326)::geography, 15000) GROUP BY mmsi"
}
```

预测：

```json
{
  "question_id": 2950,
  "db1": "MYSQL",
  "query1": "SELECT mmsi FROM transportation.vessel WHERE max_speed > 20",
  "db2": "POSTGRESQL",
  "query2": "SELECT COUNT(*) FROM public.vessel_ais_data WHERE mmsi IN (result) AND timestamp >= NOW() - INTERVAL '24 hours' AND ST_DWithin(geom::geography, ST_SetSRID(ST_MakePoint(121.5, 31.2), 4326)::geography, 15000)"
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
    1777,
    231,
    881,
    426,
    1803,
    477,
    1786,
    425,
    1790,
    476,
    638,
    1806
  ],
  "prompt_example_ids": [
    2947,
    79,
    2773,
    2974
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
      "question_id": 79,
      "question": "查询所有船舶中最大航速大于20节的船舶",
      "steps": [
        {
          "engine": "MYSQL",
          "query": "SELECT mmsi, max_speed FROM transportation.vessel WHERE max_speed > 20;",
          "step": "query",
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
      "question_id": 2974,
      "question": "查询今天在(121.0, 31.0)周围20公里内且航向在0至90度之间的船舶，从中筛选出最大航速超过20节的MMSI。",
      "steps": [
        {
          "engine": "POSTGRESQL",
          "query": "SELECT DISTINCT mmsi FROM vessel_ais_data WHERE timestamp::date = CURRENT_DATE AND cog BETWEEN 0 AND 90 AND ST_DWithin(geom::geography, ST_SetSRID(ST_MakePoint(121.0, 31.0), 4326)::geography, 20000)",
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
          "query": "SELECT mmsi FROM transportation.vessel WHERE mmsi IN (result) AND max_speed > 20",
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

后续核验：将单列数量规则限定为无分组/无逐对象要求，先明确本题每船计数口径。

这是现有请求的静态证据归因，没有运行改提示词或换模型的控制变量实验。
