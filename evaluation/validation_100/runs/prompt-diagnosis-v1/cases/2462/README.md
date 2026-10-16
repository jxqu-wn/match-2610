# 2462：统计所有高负荷医院的床位数的统计值（总和、平均值、最大值、最小值）。

归类：**输入证据缺失主导**；原语义审查状态：`different`。

高负荷原始定义1706没有表/引擎关联，被候选过滤排除。实际提示词只有大型医院定义及其他概念，案例也未给高负荷阈值。不能要求模型可靠恢复未提供的专用定义。

[实际请求和完整提示词](request.json) · [实际响应](response.json) · [结构化证据](diagnosis.json)

## 参考与预测

参考：

```json
{
  "question_id": 2462,
  "question": "统计所有高负荷医院的床位数的统计值（总和、平均值、最大值、最小值）。",
  "db": "Elasticsearch",
  "query": "{\"size\":0,\"query\":{\"range\":{\"annual_outpatient\":{\"gte\":5000000}}},\"aggs\":{\"beds_stats\":{\"stats\":{\"field\":\"bed_count\"}}}}"
}
```

预测：

```json
{
  "question_id": 2462,
  "db": "Elasticsearch",
  "query": "{\"size\":0,\"query\":{\"bool\":{\"must\":[{\"range\":{\"bed_count\":{\"gte\":1500}}},{\"range\":{\"doctor_count\":{\"gte\":1500}}}]}},\"aggs\":{\"beds_stats\":{\"stats\":{\"field\":\"bed_count\"}}}}"
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
    1703,
    1704,
    1711,
    1712,
    1708
  ],
  "prompt_example_ids": [
    2220,
    2455,
    2411,
    2225
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
      "question_id": 2411,
      "question": "统计所有医院的床位数统计值。",
      "steps": [
        {
          "engine": "Elasticsearch",
          "query": "{\"size\":0,\"aggs\":{\"beds_stats\":{\"stats\":{\"field\":\"bed_count\"}}}}",
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
      "question_id": 2455,
      "question": "计算所有顶尖三甲医院的平均床位数。",
      "steps": [
        {
          "engine": "Elasticsearch",
          "query": "{\"size\":0,\"query\":{\"bool\":{\"must\":[{\"term\":{\"has_icu\":true}},{\"range\":{\"ambulance_count\":{\"gte\":20}}},{\"range\":{\"rating\":{\"gte\":4.8}}}]}},\"aggs\":{\"avg_beds\":{\"avg\":{\"field\":\"bed_count\"}}}}",
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
  "knowledge_in_actual_prompt": [
    {
      "knowledge_id": 1703,
      "knowledge_text": "大型医院的定义：床位数达到1500张及以上，且医生数达到1500人及以上。"
    }
  ],
  "raw_knowledge_not_in_actual_prompt": [
    {
      "knowledge_id": 1706,
      "knowledge_text": "高负荷医院的定义：年门诊量达到500万人次及以上。",
      "frozen_index_engines": [],
      "frozen_index_table_ids": [],
      "scope": "Offline diagnosis only; not added to generation or production association"
    }
  ]
}
```

后续核验：修复知识可召回性，区分高负荷和大型，保持该修复不依赖错题ID白名单。

这是现有请求的静态证据归因，没有运行改提示词或换模型的控制变量实验。
