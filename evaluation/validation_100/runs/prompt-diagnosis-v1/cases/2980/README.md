# 2980：查询过去24小时内航向在270至360度之间且速度大于8节的船舶，再从中找出自持力超过90天的MMSI。

归类：**题目、参考或数据口径尚不能裁定**；原语义审查状态：`uncertain`。

自持力只有VARCHAR类型和天数或海里的业务描述，未声明天数/海里字符串格式。参考隐式转数值、预测截斜杠并CAST，是否一致依赖实际取值，当前无法归因。

[实际请求和完整提示词](request.json) · [实际响应](response.json) · [结构化证据](diagnosis.json)

## 参考与预测

参考：

```json
{
  "question_id": 2980,
  "question": "查询过去24小时内航向在270至360度之间且速度大于8节的船舶，再从中找出自持力超过90天的MMSI。",
  "db1": "POSTGRESQL",
  "query1": "SELECT DISTINCT mmsi FROM vessel_ais_data WHERE timestamp >= NOW() - INTERVAL '24 hours' AND cog BETWEEN 270 AND 360 AND sog > 8",
  "db2": "MYSQL",
  "query2": "SELECT mmsi FROM transportation.vessel WHERE mmsi IN (result) AND endurance > 90"
}
```

预测：

```json
{
  "question_id": 2980,
  "db1": "POSTGRESQL",
  "query1": "SELECT DISTINCT mmsi FROM public.vessel_ais_data WHERE timestamp >= NOW() - INTERVAL '24 hours' AND cog >= 270 AND cog <= 360 AND sog > 8",
  "db2": "MYSQL",
  "query2": "SELECT mmsi FROM transportation.vessel WHERE mmsi IN (result) AND CAST(SUBSTRING_INDEX(endurance, '/', 1) AS UNSIGNED) > 90"
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
    1786,
    1803,
    1790,
    1777,
    1739,
    1806,
    1770,
    881,
    1789,
    638,
    477,
    1772
  ],
  "prompt_example_ids": [
    2965,
    83,
    2770,
    2975
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
      "question_id": 2965,
      "question": "查询自持力大于60天的船舶，找出其中在过去24小时内轨迹穿过(120.8, 30.5)至(121.0, 30.7)矩形区域且航行状态为航行中的船舶mmsi。",
      "steps": [
        {
          "engine": "MYSQL",
          "query": "SELECT mmsi FROM transportation.vessel WHERE endurance > 60",
          "step": "query1",
          "table_ids": [
            "MYSQL:transportation.vessel"
          ],
          "joins": [],
          "parse_status": "parsed",
          "unresolved_tables": []
        },
        {
          "engine": "POSTGRESQL",
          "query": "SELECT DISTINCT mmsi FROM vessel_ais_data WHERE mmsi IN (result) AND timestamp >= NOW() - INTERVAL '24 hours' AND nav_status = 0 AND ST_Intersects(geom, ST_MakeEnvelope(120.8, 30.5, 121.0, 30.7, 4326))",
          "step": "query2",
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
      "question_id": 2975,
      "question": "查询最近24小时内位于(118.7, 20.1)半径5公里内且航行状态不为0的船舶，再找出其中自持力大于30天且最大荷载量超过40000吨的MMSI。",
      "steps": [
        {
          "engine": "POSTGRESQL",
          "query": "SELECT DISTINCT mmsi FROM vessel_ais_data WHERE timestamp >= NOW() - INTERVAL '24 hours' AND nav_status <> 0 AND ST_DWithin(geom::geography, ST_SetSRID(ST_MakePoint(118.7, 20.1), 4326)::geography, 5000)",
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
          "query": "SELECT mmsi FROM transportation.vessel WHERE mmsi IN (result) AND endurance > 30 AND max_load > 40000",
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
  "knowledge_in_actual_prompt": [
    {
      "knowledge_id": 1786,
      "knowledge_text": "船舶自持力 endurance 表示船舶在不补充燃料、淡水、食物的情况下能够连续航行的天数或海里数。"
    }
  ],
  "raw_knowledge_not_in_actual_prompt": []
}
```

后续核验：补自持力字段格式、单位和样本取值定义，再决定解析方法。

这是现有请求的静态证据归因，没有运行改提示词或换模型的控制变量实验。
