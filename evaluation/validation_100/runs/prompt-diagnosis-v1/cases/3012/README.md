# 3012：查询最近24小时内出现在点(118.7,20.1)8公里范围内且出现次数超过3次的船舶，按公司名称升序排列。

归类：**已有证据未被模型正确利用**；原语义审查状态：`different`。

题面要求船舶，按公司名只是排序，Schema和案例2947同时给出了船舶MMSI及公司关联。模型最终只输出公司名称，需求清单也遗漏返回船舶对象，属于输出对象绑定错误。

[实际请求和完整提示词](request.json) · [实际响应](response.json) · [结构化证据](diagnosis.json)

## 参考与预测

参考：

```json
{
  "question_id": 3012,
  "question": "查询最近24小时内出现在点(118.7,20.1)8公里范围内且出现次数超过3次的船舶，按公司名称升序排列。",
  "db1": "POSTGRESQL",
  "query1": "SELECT mmsi FROM vessel_ais_data WHERE timestamp >= NOW() - INTERVAL '24 hours' AND ST_DWithin(geom::geography, ST_SetSRID(ST_MakePoint(118.7, 20.1), 4326)::geography, 8000) GROUP BY mmsi HAVING COUNT(*) > 3",
  "db2": "MYSQL",
  "query2": "SELECT * FROM transportation.vessel WHERE mmsi IN (result) ORDER BY (SELECT company_name FROM transportation.shipping_company WHERE company_id = vessel.company_id) ASC"
}
```

预测：

```json
{
  "question_id": 3012,
  "db1": "POSTGRESQL",
  "query1": "SELECT mmsi FROM public.vessel_ais_data WHERE timestamp >= NOW() - INTERVAL '24 hours' AND ST_DWithin(geom::geography, ST_SetSRID(ST_MakePoint(118.7, 20.1), 4326)::geography, 8000) GROUP BY mmsi HAVING COUNT(*) > 3",
  "db2": "MYSQL",
  "query2": "SELECT sc.company_name FROM transportation.vessel v JOIN transportation.shipping_company sc ON v.company_id = sc.company_id WHERE v.mmsi IN (result) ORDER BY sc.company_name ASC"
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
    231,
    1790,
    426,
    881,
    638,
    477,
    476,
    1803,
    1786,
    1770,
    425,
    1761
  ],
  "prompt_example_ids": [
    2947,
    176,
    2895,
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
      "question_id": 2947,
      "question": "找出过去24小时内轨迹包含多边形(121.3,31.0)-(121.5,31.0)-(121.4,31.2)内任意点的船舶，获取这些船舶的所属公司以及船长姓名。",
      "steps": [
        {
          "engine": "POSTGRESQL",
          "query": "SELECT mmsi FROM vessel_ais_data WHERE timestamp >= NOW() - INTERVAL '24 hours' GROUP BY mmsi HAVING ST_Intersects(ST_MakeLine(geom ORDER BY timestamp), ST_GeomFromText('POLYGON((121.3 31.0, 121.5 31.0, 121.4 31.2, 121.3 31.0))', 4326))",
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
          "query": "SELECT v.mmsi, sc.company_name AS company, v.captain_name FROM transportation.vessel v JOIN transportation.shipping_company sc ON v.company_id = sc.company_id WHERE v.mmsi IN (result)",
          "step": "query2",
          "table_ids": [
            "MYSQL:transportation.shipping_company",
            "MYSQL:transportation.vessel"
          ],
          "joins": [
            {
              "left_table": "MYSQL:transportation.vessel",
              "left_columns": [
                "company_id"
              ],
              "right_table": "MYSQL:transportation.shipping_company",
              "right_columns": [
                "company_id"
              ]
            }
          ],
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

后续核验：核验返回实体与ORDER BY维度分离；不能因按公司排序就只返回公司。

这是现有请求的静态证据归因，没有运行改提示词或换模型的控制变量实验。
