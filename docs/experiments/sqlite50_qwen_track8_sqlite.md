# SQLite 50 题实验报告：qwen-track8-sqlite

模型：`qwen-track8-sqlite` @ `http://192.168.15.119:8000/v1`（vLLM，max_model_len 16384）  
外部知识：仅 `data/赛题8/splits/train.json`（5247 条）+ knowledge 构建检索索引  
测试数据：`data/赛题8/splits/validation.json` 中 SQLite 单源题抽样 50 道（seed=42）  
路由：字符 TF-IDF + 逻辑回归（离线）；提示词最多 6 张表  
采样与提示词与 text2sql 实验完全一致，仅更换模型。

## 一、总体指标

| 指标 | 数值 |
| --- | ---: |
| 数据库类型正确率 | 100.0%（50/50） |
| 提示词完整业务库覆盖率 | 98.0%（49/50） |
| 提示词完整业务表覆盖率 | 84.0%（42/50） |
| 提示词业务库召回率 | 98.0% |
| 提示词业务表召回率 | 89.3% |
| 生成 SQL 可解析率 | 100.0% |
| 生成 SQL 业务库完全正确率 | 82.0% |
| 生成 SQL 业务库 召回/精确 | 96.0% / 88.7% |
| 生成 SQL 业务表完全正确率 | 26.0% |
| 生成 SQL 业务表 召回/精确 | 87.7% / 55.6% |

说明：业务库/业务表“完全正确率”要求集合完全相等；召回率=参考集合被覆盖比例，精确率=生成集合中属于参考的比例。

## 二、SQL 与验证集答案一致性（人工复核）

判定口径：**一致**=结果集等价（允许别名/大小写/等价改写）；**部分一致**=核心表与条件正确但存在多余连接、DISTINCT、字面量大小写等可能影响结果或重复行的差异；**不一致**=缺表/多错表、条件或字段错误、逻辑偏离、无法解析。

| 结论 | 题数 | 占比 |
| --- | ---: | ---: |
| 一致 | 7 | 14% |
| 部分一致 | 16 | 32% |
| 不一致 | 27 | 54% |

| 题号 | 库表标签 | 一致性 | 说明 |
| ---: | --- | --- | --- |
| 3071 | EXACT | 不一致 | 生成用 lname（贴合‘姓氏’），参考用 fname；表集合正确 |
| 3189 | EXACT | 不一致 | 编译条件取反：WasCompiled=1 vs 参考 0；分母 COUNT(WasCompiled) |
| 3193 | EXTRA | 不一致 | 改为按 Solution 数排序取第一条，非 MAX(Forks) |
| 3203 | EXTRA | 不一致 | 应查 Method.Name 派生任务，生成改查 FullComment+MethodParameter |
| 3210 | EXTRA | 部分一致 | 多连 MethodParameter；COUNT(Method.Id) vs COUNT(SolutionId) |
| 3296 | EXTRA | 不一致 | 多连 Match/Batsman_Scored/Extra_Runs/Wicket_Taken/Out_Type |
| 3297 | EXTRA | 部分一致 | 多连 5 张表，按 Match_Id 连接；选择/排序一致，结果大概率相同 |
| 3435 | EXACT | 不一致 | 只覆盖 Team_2 获胜分支，缺另一分支 |
| 3508 | EXTRA | 不一致 | 误连 coaches 并 SUM(won) |
| 3521 | EXTRA | 不一致 | 过滤值 HOU 与 round='F' 不同，并多连 coaches/hockey 表 |
| 3540 | MISS | 不一致 | 误用 hockey.AwardsPlayers+Master 替代 awards_players |
| 3549 | MISS | 不一致 | 误连 soccer_2016/olympics 库 |
| 3583 | EXACT | 部分一致 | 缺 year=draftYear 连接键，可能多出球队 |
| 3584 | EXTRA | 部分一致 | 核心条件正确，多连 draft 表 |
| 3606 | MISS | 不一致 | 缺 players_teams，改用 season_id 过滤 |
| 3680 | EXTRA | 不一致 | characters 连接键错误（characters.id=works.id） |
| 3741 | EXACT | 一致 | DISTINCT 改写，等价 |
| 3841 | EXTRA | 部分一致 | 起点改为 game_platform 并多连 region_sales/platform |
| 3854 | EXTRA | 部分一致 | 改为 ORDER BY release_year LIMIT 1（等价 MIN），多连 5 表 |
| 3989 | EXTRA | 不一致 | 误连 citeseer 表 |
| 4027 | EXTRA | 部分一致 | 多连 PaperAuthor/Conference；过滤正确 |
| 4149 | EXTRA | 不一致 | 统计对象与条件整体偏离参考 |
| 4162 | MISS | 不一致 | 缺 Attributes 表，改按 Categories 过滤 |
| 4175 | EXTRA | 部分一致 | 多连 2 张表，选择/过滤一致 |
| 4191 | EXTRA | 部分一致 | 多连 Business；过滤条件与参考一致，可能重复 business_id |
| 4218 | EXTRA | 不一致 | 多连 5 张表，语义偏离 |
| 4275 | EXACT | 一致 | DISTINCT 改写，大小写无关，等价 |
| 4387 | EXTRA | 部分一致 | 经 Business 中转并 DISTINCT，语义等价 |
| 4516 | MISS | 不一致 | 缺 Person，改用 Episode.year 计算年龄 |
| 4554 | EXTRA | 部分一致 | 多连 Award/Episode 并加 season=20 |
| 4565 | EXTRA | 部分一致 | 多连 Episode 并改 SUM(votes) 聚合 |
| 4644 | EXACT | 一致 | 字段与过滤一致，等价 |
| 4683 | EXTRA | 不一致 | 漏 'Maybe'，问题文本过滤不同 |
| 4895 | EXTRA | 部分一致 | 多连 games/competitor_event/event |
| 4907 | EXACT | 一致 | 连接链一致，等价 |
| 4918 | EXTRA | 部分一致 | 多连 competitor_event/games_competitor/games/medal |
| 4973 | EXACT | 一致 | 月份用 LIKE 匹配，等价 |
| 4981 | EXTRA | 部分一致 | 多连 location/geolocation；Twitter IS NULL 变成 ='FALSE' |
| 5077 | EXTRA | 不一致 | 改为 location 州聚合，与参考按品牌州计数不同 |
| 5088 | MISS | 不一致 | 误答 public_review_platform，缺 beer_factory |
| 5287 | EXACT | 部分一致 | 参考按订单数计占比，生成按价格加权 |
| 5320 | MISS | 不一致 | 误连 order_line/cust_order/customer，缺 author/book_author |
| 5472 | EXTRA | 不一致 | 多连 4 表并加 lowest 过滤，无 ORDER/LIMIT |
| 5549 | EXTRA | 不一致 | 多连 professional_basketball.teams 并改聚合 |
| 5802 | EXACT | 不一致 | 输出 max_qty 而非计数；书名用复数 |
| 6052 | MISS | 不一致 | 误答 books 库 |
| 6118 | EXTRA | 不一致 | 多连 film_actor/film_category/inventory/disney |
| 6139 | EXACT | 一致 | 连接链一致，等价 |
| 6166 | EXACT | 一致 | 大小写无关的等价条件 |
| 6223 | MISS | 不一致 | 误答 payment+rental+inventory+category+music_platform_2，缺 customer |

## 三、关键发现

1. **数据库类型无错误**：50 题全部正确路由到 SQLite。
2. **生成可解析率 100%**：全部 50 条输出均为可解析的单条只读 SQL，无退化或截断（优于 text2sql 的 98%）。
3. **过度连接更严重**：50 题中 28 题出现多余表，业务表精确率降至 55.6%，为三套设置中最低。
4. **同系统内跨业务库混淆**：多题误连 hockey、soccer_2016、olympics、citeseer、books、public_review_platform、professional_basketball.teams。
5. **提示词召回仍是上限**：8 题在提示词阶段缺参考表（与 text2sql 同一批）。
6. **与 text2sql 相比**：可解析率与业务库召回略升（1.00 / 0.96），但业务表完全正确率与精确率下降（0.26 / 0.556）。

## 四、复现

```bash
PYTHONPATH=src .venv/bin/python -m text2query.cli experiment-sqlite50 \
  --endpoint http://192.168.15.119:8000/v1 --model qwen-track8-sqlite \
  --sample-size 50 --seed 42 --max-tables 6 --workers 4 \
  --output-dir outputs/experiments/sqlite50_qwen_track8_sqlite
```
