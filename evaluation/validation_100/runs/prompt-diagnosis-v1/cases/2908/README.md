# 2908：统计最近48小时内进入日照港石臼港区警戒区的船舶数量，按航行状态分组。

归类：**输入证据缺失主导**；原语义审查状态：`different`。

原始知识1742含日照警戒区中心及0.5海里半径，实际提示词没有它，案例也没有该区位置。模型自行编造矩形；这与2907已提供同名区域的情形不同。

[实际请求和完整提示词](request.json) · [实际响应](response.json) · [结构化证据](diagnosis.json)

## 参考与预测

参考：

```json
{
  "question_id": 2908,
  "question": "统计最近48小时内进入日照港石臼港区警戒区的船舶数量，按航行状态分组。",
  "db": "POSTGRESQL",
  "query": "SELECT nav_status, COUNT(DISTINCT mmsi) AS cnt FROM vessel_ais_data WHERE timestamp >= NOW() - INTERVAL '48 hours' AND ST_DWithin(geom::geography, ST_SetSRID(ST_MakePoint(119.5833, 35.3333), 4326)::geography, 926) GROUP BY nav_status"
}
```

预测：

```json
{
  "question_id": 2908,
  "db": "POSTGRESQL",
  "query": "SELECT nav_status, COUNT(DISTINCT mmsi) AS vessel_count FROM public.vessel_ais_data WHERE timestamp >= NOW() - INTERVAL '48 hours' AND ST_Within(geom, ST_GeomFromText('POLYGON((119.45 35.30, 119.65 35.30, 119.65 35.45, 119.45 35.45, 119.45 35.30))', 4326)) GROUP BY nav_status"
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
    638,
    881,
    653,
    425,
    476
  ],
  "prompt_example_ids": [
    2596,
    2586,
    2614,
    2595
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
      "question_id": 2596,
      "question": "按航行状态分组，统计每种航行状态下的船舶记录数量。",
      "steps": [
        {
          "engine": "POSTGRESQL",
          "query": "SELECT nav_status, COUNT(*) AS cnt FROM vessel_ais_data GROUP BY nav_status",
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
      "question_id": 2586,
      "question": "按航行状态分组，统计每种航行状态的船舶记录数量。",
      "steps": [
        {
          "engine": "POSTGRESQL",
          "query": "SELECT nav_status, COUNT(*) AS cnt FROM vessel_ais_data GROUP BY nav_status",
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
  "raw_knowledge_not_in_actual_prompt": [
    {
      "knowledge_id": 1742,
      "knowledge_text": "日照港石臼港区航道及警戒区。石臼港区航道自航道入口（35°20.0′N,119°35.0′E）至煤炭码头前沿（35°18.5′N,119°32.0′E），全长约6海里，航道宽度250米，水深-18米。航道入口处设警戒区，以点(35°20.0′N,119°35.0′E)为中心、半径0.5海里的圆形水域。船舶进入警戒区前应向日照VTS中心报告（VHF14频道），航道内限速10节，大型船舶需引航。",
      "frozen_index_engines": [],
      "frozen_index_table_ids": [],
      "scope": "Offline diagnosis only; not added to generation or production association"
    }
  ]
}
```

后续核验：补警戒区原始定义、单位和几何对象，检索缺失时阻止编造边界。

这是现有请求的静态证据归因，没有运行改提示词或换模型的控制变量实验。
