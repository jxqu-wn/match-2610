# 2487：查询所有超大规模且优秀护理的医院的名称。

归类：**输入证据缺失主导**；原语义审查状态：`different`。

超大规模1709被误关联到MYSQL规模字典，ES流程取不到。优秀护理1710虽也未召回，但案例2473已给完整护理条件且模型正确使用；真正决定本题错误的是超大规模证据缺失。

[实际请求和完整提示词](request.json) · [实际响应](response.json) · [结构化证据](diagnosis.json)

## 参考与预测

参考：

```json
{
  "question_id": 2487,
  "question": "查询所有超大规模且优秀护理的医院的名称。",
  "db": "Elasticsearch",
  "query": "{\"_source\":[\"name\"],\"query\":{\"bool\":{\"must\":[{\"range\":{\"bed_count\":{\"gte\":2000}}},{\"range\":{\"annual_outpatient\":{\"gte\":6000000}}},{\"range\":{\"nurse_count\":{\"gte\":2000}}},{\"script\":{\"script\":{\"source\":\"doc['bed_count'].value / doc['nurse_count'].value <= 1.2\"}}}]}}}"
}
```

预测：

```json
{
  "question_id": 2487,
  "db": "Elasticsearch",
  "query": "{\"_source\":[\"name\"],\"query\":{\"bool\":{\"must\":[{\"range\":{\"bed_count\":{\"gte\":1500}}},{\"range\":{\"doctor_count\":{\"gte\":1500}}},{\"range\":{\"nurse_count\":{\"gte\":2000}}},{\"script\":{\"script\":{\"source\":\"doc['bed_count'].value / doc['nurse_count'].value <= 1.2\"}}}]}}}"
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
    1712,
    1703,
    1704,
    1711,
    1708
  ],
  "prompt_example_ids": [
    2454,
    2457,
    2473,
    2447
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
      "question_id": 2473,
      "question": "查询所有优秀护理医院的名称和护士数。",
      "steps": [
        {
          "engine": "Elasticsearch",
          "query": "{\"_source\":[\"name\",\"nurse_count\"],\"query\":{\"bool\":{\"must\":[{\"range\":{\"nurse_count\":{\"gte\":2000}}},{\"script\":{\"script\":{\"source\":\"doc['bed_count'].value / doc['nurse_count'].value <= 1.2\"}}}]}}}",
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
      "knowledge_id": 1709,
      "knowledge_text": "超大规模医院的定义：床位数达到2000张及以上，且年门诊量达到600万人次及以上。",
      "frozen_index_engines": [
        "MYSQL"
      ],
      "frozen_index_table_ids": [
        "MYSQL:common.dict_size_category"
      ],
      "scope": "Offline diagnosis only; not added to generation or production association"
    },
    {
      "knowledge_id": 1710,
      "knowledge_text": "优秀护理医院的判断标准：护士数达到2000人及以上，且床位数与护士数的比值不超过1.2。",
      "frozen_index_engines": [],
      "frozen_index_table_ids": [],
      "scope": "Offline diagnosis only; not added to generation or production association"
    }
  ]
}
```

后续核验：补正确超大规模关联；不能把所有未召回知识都算成本题有效缺口。

这是现有请求的静态证据归因，没有运行改提示词或换模型的控制变量实验。
