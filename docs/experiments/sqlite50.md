# SQLite 50 题微调模型实验报告

日期：2026-10-12  
模型：`qwen-track8-text2sql` @ `http://192.168.15.119:8000/v1`（vLLM，max_model_len 8192）  
外部知识：仅 `data/赛题8/splits/train.json`（5247 条）+ knowledge 构建检索索引  
测试数据：`data/赛题8/splits/validation.json` 中 SQLite 单源题抽样 50 道（seed=42）  
抽样：SQLite 验证题 299 道，排除与训练集同文本后全部可抽样，取 50 道  
路由：字符 TF-IDF + 逻辑回归（离线，无本地 embedding 模型）；提示词最多 6 张表

## 一、总体指标

| 指标 | 数值 |
| --- | ---: |
| 数据库类型正确率 | 100.0%（50/50） |
| 提示词完整业务库覆盖率 | 98.0%（49/50） |
| 提示词完整业务表覆盖率 | 84.0%（42/50） |
| 提示词业务库召回率 | 98.0% |
| 提示词业务表召回率 | 89.3% |
| 生成 SQL 可解析率 | 98.0%（49/50） |
| 生成 SQL 业务库完全正确率 | 82.0%（41/50） |
| 生成 SQL 业务库召回率 / 精确率 | 94.0% / 89.5% |
| 生成 SQL 业务表完全正确率 | 32.0%（16/50） |
| 生成 SQL 业务表召回率 / 精确率 | 86.7% / 62.1% |

说明：业务库/业务表“完全正确率”要求集合完全相等；召回率=参考集合被覆盖比例，精确率=生成集合中属于参考的比例。
生成库表普遍偏多（幻觉连接）导致精确率低，是主要失分来源。

## 二、SQL 与验证集答案一致性（人工复核）

判定口径：**一致**=结果集等价（允许别名/大小写/等价改写）；**部分一致**=核心表与条件正确但存在多余连接、DISTINCT、字面量大小写等可能影响结果或重复行的差异；**不一致**=缺表/多错表、条件或字段错误、逻辑偏离、无法解析。

| 结论 | 题数 | 占比 |
| --- | ---: | ---: |
| 一致 | 7 | 14% |
| 部分一致 | 16 | 32% |
| 不一致 | 27 | 54% |

| 题号 | 库表标签 | 一致性 | 说明 |
| ---: | --- | --- | --- |
| 3071 | EXTRA | 不一致 | 生成用 lname（贴合‘姓氏’），参考用 fname；多连 publishers |
| 3189 | EXACT | 不一致 | 编译条件取反：WasCompiled=1 vs 参考 0 |
| 3193 | EXTRA | 部分一致 | 多连 Solution 并取 RepoId；最大 forks 逻辑近似 |
| 3203 | EXTRA | 不一致 | 应查 Method.Name 派生任务，生成改查 MethodParameter.Summary |
| 3210 | EXTRA | 部分一致 | 多连 MethodParameter；COUNT(DISTINCT Method.Id) 计数对象不同 |
| 3296 | EXACT | 部分一致 | 参考 COUNT(Over_Id)，生成 COUNT(DISTINCT Over_Id) |
| 3297 | EXTRA | 部分一致 | 多余 5 张表连接，选择/过滤/排序一致，结果大概率相同 |
| 3435 | EXACT | 不一致 | 只覆盖 Team_2 获胜分支，缺另一分支 |
| 3508 | EXACT | 一致 | 自连接 vs 相关子查询，等价 |
| 3521 | EXACT | 不一致 | 过滤值 HOU/HSM 与排序方向不同，且缺 round 条件 |
| 3540 | MISS | 不一致 | 误用 hockey.AwardsPlayers 替代 professional_basketball.awards_players |
| 3549 | MISS | 不一致 | 误连 soccer_2016/olympics 库 |
| 3583 | EXACT | 部分一致 | 缺 year=draftYear 连接键，可能多出球队 |
| 3584 | EXACT | 不一致 | 奖项由 Most Improved Player 变成 Rookie of the Year |
| 3606 | MISS | 不一致 | 缺 players_teams，改用 season_id 过滤 |
| 3680 | EXTRA | 部分一致 | 多连 characters；COUNT(DISTINCT character_id) 大概率同结果 |
| 3741 | EXACT | 一致 | 字段与连接一致，等价 |
| 3841 | EXTRA | 部分一致 | 多连 game_platform，可能造成行重复 |
| 3854 | EXTRA | 不一致 | 改为按销量取第一条，非 MIN(release_year) |
| 3989 | EXTRA | 不一致 | 误连 citeseer 且去掉 DISTINCT |
| 4027 | EXTRA | 不一致 | 把论文标题当作作者名过滤 |
| 4149 | EXTRA | 不一致 | 统计对象与条件整体偏离参考 |
| 4162 | MISS | 不一致 | 缺 Attributes 表，改按 Categories 过滤 |
| 4175 | EXTRA | 部分一致 | 多连 4 张表，选择/过滤一致 |
| 4191 | EXTRA | 不一致 | 缺 attribute_value LIKE 'TRUE' 条件 |
| 4218 | EXTRA | 不一致 | 改为 compliments/Elite 过滤，语义偏离 |
| 4275 | EXACT | 一致 | 大小写无关的等价条件 |
| 4387 | EXTRA | 部分一致 | 多连 Business 且缺 DISTINCT |
| 4516 | MISS | 不一致 | 误连 hockey.AwardsPlayers 与 Episode/Character_Award |
| 4554 | EXTRA | 部分一致 | 多连 Award/Episode 并加 season=20 |
| 4565 | EXACT | 部分一致 | 聚合方式不同：SUM(votes)+GROUP BY |
| 4644 | EXACT | 一致 | 字段与过滤一致，等价 |
| 4683 | EXTRA | 不一致 | 漏 'Maybe'，分母计数对象不同 |
| 4895 | EXTRA | 部分一致 | 多连 games/competitor_event/event，COUNT DISTINCT |
| 4907 | EXACT | 一致 | 连接链一致，等价 |
| 4918 | EXTRA | 部分一致 | 多连 games/games_competitor/competitor_event |
| 4973 | EXTRA | 部分一致 | 多连 location，月份用 LIKE 匹配 |
| 4981 | EXTRA | 部分一致 | 多连 location/geolocation，Twitter IS NULL 变成 ='No' |
| 5077 | EXTRA | 不一致 | 改为按 location 州聚合，与参考按品牌州计数不同 |
| 5088 | MISS | 不一致 | 误答 public_review_platform/professional_basketball，缺 beer_factory |
| 5287 | EXACT | 部分一致 | 参考按订单数计占比，生成按价格加权 |
| 5320 | MISS | 不一致 | 误连 cust_order/customer/order_line，缺 author/book_author |
| 5472 | EXTRA | 不一致 | 多连 4 表并加 lowest/bounding box 过滤 |
| 5549 | EXTRA | 不一致 | 多连 professional_basketball.teams，字段口径不同 |
| 5802 | EXACT | 不一致 | 书名复数、缺 unit 过滤、输出 max_qty |
| 6052 | MISS | 不一致 | 误答 books 库 |
| 6118 | EXTRA | 不一致 | 多连 film_actor/film_category/inventory/disney |
| 6139 | EXACT | 一致 | 连接链一致，等价 |
| 6166 | EXACT | 一致 | 大小写无关的等价条件 |
| 6223 | MISS | 不一致 | 输出退化为重复子查询，解析失败 |

## 三、关键发现

1. **数据库类型无错误**：50 题全部正确路由到 SQLite（字符 TF-IDF 路由在该分层上稳定）。
2. **提示词召回是上限瓶颈**：完整业务表覆盖仅 84%，8 道题在提示词阶段就缺少参考表；这些题最终生成几乎必然不一致（如 5088 整库缺失）。
3. **模型倾向过度连接**：34/50 题生成表集合与参考不等，其中 26 道是‘多表’（EXTRA）。模型把训练集中常见的关联表模式外推到不相关问题，导致业务表精确率仅 62.1%。
4. **同库内跨库混淆**：多道题把参考表误连到其他业务库（hockey、citeseer、books、olympics、soccer_2016、public_review_platform、professional_basketball.teams），说明仅靠同系统检索会丢失业务库边界。
5. **一处输出退化**：6223 生成重复嵌套子查询直到输出上限，无法解析；需要输出长度/重复检测与重试。
6. **参考答案本身存在可疑项**：3071 参考取 `fname` 但问题问‘姓氏’，5287 参考按订单数计占比但问题说‘总价格’，这类题不宜作为模型能力的唯一判据。

## 四、复现

```bash
PYTHONPATH=src .venv/bin/python -m text2query.cli experiment-sqlite50 \
  --endpoint http://192.168.15.119:8000/v1 --model qwen-track8-text2sql \
  --sample-size 50 --seed 42 --max-tables 6 --workers 4
```

产物：`outputs/experiments/sqlite50/`（config.json、sample.json、results.jsonl、report.json、review.md）。
注意：路由使用离线字符 TF-IDF 分类器；若提供本地 Qwen3-Embedding-0.6B，可切换为语义路由与语义召回。