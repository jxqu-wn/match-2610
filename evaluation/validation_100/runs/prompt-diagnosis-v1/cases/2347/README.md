# 2347：找到最靠近上海静安寺的3个医院，返回名称和日均门诊量。

归类：**输入与模型处理混合**；原语义审查状态：`different`。

Schema无daily_outpatient，但案例两次使用该字段，参考也使用它，输入证据自相矛盾。模型知道要日均，却只输出年量并把计算推给不存在的后续步骤，是额外的需求未完成。

[实际请求和完整提示词](request.json) · [实际响应](response.json) · [结构化证据](diagnosis.json)

## 参考与预测

参考：

```json
{
  "question_id": 2347,
  "question": "找到最靠近上海静安寺的3个医院，返回名称和日均门诊量。",
  "db": "Elasticsearch",
  "query": "{\"_source\":[\"name\",\"daily_outpatient\"],\"size\":3,\"query\":{\"match_all\":{}},\"sort\":[{\"_geo_distance\":{\"location\":{\"lat\":31.2235,\"lon\":121.4447},\"order\":\"asc\",\"unit\":\"km\"}}]}"
}
```

预测：

```json
{
  "question_id": 2347,
  "db": "Elasticsearch",
  "query": "{\"size\":3,\"query\":{\"match_all\":{}},\"sort\":[{\"_geo_distance\":{\"location\":{\"lat\":31.2235,\"lon\":121.4447},\"order\":\"asc\",\"unit\":\"km\"}}],\"_source\":[\"name\",\"annual_outpatient\"]}"
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
    1708,
    1712,
    1704,
    1703,
    1711
  ],
  "prompt_example_ids": [
    2070,
    2130,
    2367,
    2079
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
      "question_id": 2367,
      "question": "找到最靠近上海静安寺且拥有ICU的3个医院，返回名称和日均门诊量。",
      "steps": [
        {
          "engine": "Elasticsearch",
          "query": "{\"_source\":[\"name\",\"daily_outpatient\"],\"size\":3,\"query\":{\"bool\":{\"filter\":{\"term\":{\"has_icu\":true}}}},\"sort\":[{\"_geo_distance\":{\"location\":{\"lat\":31.2235,\"lon\":121.4447},\"order\":\"asc\",\"unit\":\"km\"}}]}",
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
      "question_id": 2079,
      "question": "查询上海东方明珠塔周围3公里内的所有医院，返回名称和日均门诊量。",
      "steps": [
        {
          "engine": "Elasticsearch",
          "query": "{\"query\":{\"geo_distance\":{\"distance\":\"3km\",\"location\":{\"lat\":31.2395,\"lon\":121.4990}}},\"_source\":[\"name\",\"daily_outpatient\"]}",
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

后续核验：先澄清真实字段/派生规则；确认生成结果自身完成日均计算。

这是现有请求的静态证据归因，没有运行改提示词或换模型的控制变量实验。
