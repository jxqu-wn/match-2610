# 2125：成都天府广场周围8公里内，找出24小时急诊且救护车数大于10的医院。

归类：**输入证据缺失主导**；原语义审查状态：`different`。

实际提示词没有天府广场坐标；知识1689原文有准确坐标，但没有被召回，四个案例也不给该地标坐标。模型使用另一组常识坐标，主缺口是输入地理证据。

[实际请求和完整提示词](request.json) · [实际响应](response.json) · [结构化证据](diagnosis.json)

## 参考与预测

参考：

```json
{
  "question_id": 2125,
  "question": "成都天府广场周围8公里内，找出24小时急诊且救护车数大于10的医院。",
  "db": "Elasticsearch",
  "query": "{\"query\":{\"bool\":{\"must\":[{\"term\":{\"emergency_24h\":true}},{\"range\":{\"ambulance_count\":{\"gt\":10}}}],\"filter\":{\"geo_distance\":{\"distance\":\"8km\",\"location\":{\"lat\":30.6600,\"lon\":104.0630}}}}},\"_source\":[\"name\"]}"
}
```

预测：

```json
{
  "question_id": 2125,
  "db": "Elasticsearch",
  "query": "{\"query\":{\"bool\":{\"must\":[{\"term\":{\"emergency_24h\":true}},{\"range\":{\"ambulance_count\":{\"gt\":10}}}],\"filter\":{\"geo_distance\":{\"distance\":\"8km\",\"location\":{\"lat\":30.657,\"lon\":104.065}}}}},\"_source\":[\"name\"]}"
}
```

## 输入证据

```json
{
  "prompt_table_ids": [
    "Elasticsearch:medical_institutions"
  ],
  "reference_tables_not_in_prompt": [],
  "predicted_tables_not_in_prompt": [],
  "prompt_knowledge_ids": [
    1704,
    1711,
    1703,
    1708,
    1712
  ],
  "prompt_example_ids": [
    2433,
    2281,
    2464,
    2230
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
      "question_id": 2433,
      "question": "查询所有24小时急诊的医院名称和救护车数。",
      "steps": [
        {
          "engine": "Elasticsearch",
          "query": "{\"_source\":[\"name\",\"ambulance_count\"],\"query\":{\"term\":{\"emergency_24h\":true}}}",
          "step": "query",
          "table_ids": [
            "Elasticsearch:medical_institutions"
          ],
          "joins": [],
          "parse_status": "single_index_by_catalog"
        }
      ]
    },
    {
      "question_id": 2281,
      "question": "在多边形区域（顶点：31.24,121.45；31.23,121.47；31.22,121.46；31.23,121.44）内，找出拥有24小时急诊的医院名称和救护车数。",
      "steps": [
        {
          "engine": "Elasticsearch",
          "query": "{\"query\":{\"bool\":{\"must\":{\"term\":{\"emergency_24h\":true}},\"filter\":{\"geo_polygon\":{\"location\":{\"points\":[{\"lat\":31.24,\"lon\":121.45},{\"lat\":31.23,\"lon\":121.47},{\"lat\":31.22,\"lon\":121.46},{\"lat\":31.23,\"lon\":121.44}]}}}}},\"_source\":[\"name\",\"ambulance_count\"]}",
          "step": "query",
          "table_ids": [
            "Elasticsearch:medical_institutions"
          ],
          "joins": [],
          "parse_status": "single_index_by_catalog"
        }
      ]
    }
  ],
  "knowledge_in_actual_prompt": [],
  "raw_knowledge_not_in_actual_prompt": [
    {
      "knowledge_id": 1689,
      "knowledge_text": "成都天府广场的经纬度坐标为 (lat: 30.6600, lon: 104.0630)",
      "frozen_index_engines": [],
      "frozen_index_table_ids": [],
      "scope": "Offline diagnosis only; not added to generation or production association"
    }
  ]
}
```

后续核验：先让地标坐标原文进入提示词，禁止以未验证常识坐标静默替代业务坐标。

这是现有请求的静态证据归因，没有运行改提示词或换模型的控制变量实验。
