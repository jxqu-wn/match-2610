# 2358：找到最靠近北京天安门广场且为三级甲等的5个医疗机构。

归类：**题目、参考或数据口径尚不能裁定**；原语义审查状态：`different`。

题面只要求医疗机构，没有说只返回name；最相近案例2338恰好省略_source。预测沿用该返回格式，不能根据参考多了_source就认定模型未遵守明确输出要求。

[实际请求和完整提示词](request.json) · [实际响应](response.json) · [结构化证据](diagnosis.json)

## 参考与预测

参考：

```json
{
  "question_id": 2358,
  "question": "找到最靠近北京天安门广场且为三级甲等的5个医疗机构。",
  "db": "Elasticsearch",
  "query": "{\"size\":5,\"_source\":[\"name\"],\"query\":{\"bool\":{\"filter\":{\"term\":{\"level\":\"三甲\"}}}},\"sort\":[{\"_geo_distance\":{\"location\":{\"lat\":39.9087,\"lon\":116.3975},\"order\":\"asc\",\"unit\":\"km\"}}]}"
}
```

预测：

```json
{
  "question_id": 2358,
  "db": "Elasticsearch",
  "query": "{\"size\":5,\"query\":{\"bool\":{\"must\":{\"term\":{\"level\":\"三甲\"}}}},\"sort\":[{\"_geo_distance\":{\"location\":{\"lat\":39.9087,\"lon\":116.3975},\"order\":\"asc\",\"unit\":\"km\"}}]}"
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
    1708,
    1712,
    1703,
    1711
  ],
  "prompt_example_ids": [
    2338,
    2311,
    2133,
    2319
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
      "question_id": 2338,
      "question": "找到最靠近北京天安门广场的5个医疗机构。",
      "steps": [
        {
          "engine": "Elasticsearch",
          "query": "{\"size\":5,\"sort\":[{\"_geo_distance\":{\"location\":{\"lat\":39.9087,\"lon\":116.3975},\"order\":\"asc\",\"unit\":\"km\"}}]}",
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
  "raw_knowledge_not_in_actual_prompt": []
}
```

后续核验：明确机构类ES查询默认_source；执行评分若仅比较ID，这种投影差异可能无影响。

这是现有请求的静态证据归因，没有运行改提示词或换模型的控制变量实验。
