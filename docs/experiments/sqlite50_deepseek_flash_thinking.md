# SQLite 50 题实验报告：deepseek-flash（thinking）

模型：`deepseek-flash` @ `https://api.deepseek.com/v1`，**thinking 已开启**  
外部知识：仅 `data/赛题8/splits/train.json`（5247 条）+ knowledge 构建检索索引  
测试数据：`data/赛题8/splits/validation.json` 中 SQLite 单源题抽样 50 道（seed=42）  
路由：字符 TF-IDF + 逻辑回归（离线）；提示词最多 6 张表；`max_tokens=16384`  
指标在保存输出上重算：未限定表名按“引擎内唯一 → 提示词优先 → 限定列覆盖 → 列覆盖最大”做无答案泄露消歧。

## 一、总体指标

| 指标 | 数值 |
| --- | ---: |
| 数据库类型正确率 | 100.0%（50/50） |
| 提示词完整业务库覆盖率 | 98.0%（49/50） |
| 提示词完整业务表覆盖率 | 84.0%（42/50） |
| 提示词业务库召回率 | 98.0% |
| 提示词业务表召回率 | 89.3% |
| 生成 SQL 可解析率 | 92.0% |
| 生成 SQL 业务库完全正确率 | 94.0% |
| 生成 SQL 业务库 召回/精确 | 94.0% / 97.9% |
| 生成 SQL 业务表完全正确率 | 76.0% |
| 生成 SQL 业务表 召回/精确 | 86.3% / 91.8% |

说明：业务库/业务表“完全正确率”要求集合完全相等；召回率=参考集合被覆盖比例，精确率=生成集合中属于参考的比例。

## 二、SQL 与验证集答案一致性（人工复核）

判定口径：**一致**=结果集等价（允许别名/大小写/等价改写）；**部分一致**=核心表与条件正确但存在多余连接、DISTINCT、字面量大小写等可能影响结果或重复行的差异；**不一致**=缺表/多错表、条件或字段错误、逻辑偏离、无法解析。

| 结论 | 题数 | 占比 |
| --- | ---: | ---: |
| 一致 | 22 | 44% |
| 部分一致 | 11 | 22% |
| 不一致 | 17 | 34% |

| 题号 | 库表标签 | 一致性 | 说明 |
| ---: | --- | --- | --- |
| 3071 | EXACT | 不一致 | 生成 lname（贴合‘姓氏’），参考 fname；表集合正确 |
| 3189 | EXACT | 不一致 | 编译条件取反：WasCompiled=1 vs 参考 0 |
| 3193 | EXACT | 一致 | ORDER BY Forks DESC LIMIT 1 等价于 MAX(Forks) |
| 3203 | EXACT | 不一致 | 应查 Method.Name 派生任务，生成改查 FullComment |
| 3210 | MISS | 不一致 | 缺 Solution；COUNT(Method) vs COUNT(SolutionId) |
| 3296 | EXACT | 部分一致 | COUNT(DISTINCT Over_Id) vs 参考 COUNT(Over_Id) |
| 3297 | EXACT | 一致 | 与参考等价（仅未限定库名） |
| 3435 | EXACT | 一致 | CASE 逻辑与参考子查询等价 |
| 3508 | EXACT | 一致 | 自连接与参考子查询等价 |
| 3521 | MISS | 不一致 | thinking 耗尽预算，无输出 |
| 3540 | MISS | 不一致 | 使用 awards 表（列 award），非 awards_players |
| 3549 | EXACT | 部分一致 | 表正确；fullGivenName/teamID 与参考字段口径不同 |
| 3583 | EXACT | 一致 | 连接键含 draftYear，与参考一致 |
| 3584 | EXACT | 一致 | 奖项、年份、国家条件与参考一致 |
| 3606 | MISS | 不一致 | 缺 players_teams，改用 season_id 过滤 |
| 3680 | EXACT | 一致 | 三表连接与 COUNT DISTINCT 等价 |
| 3741 | EXACT | 一致 | DISTINCT 改写，等价 |
| 3841 | EXACT | 一致 | 三表连接等价 |
| 3854 | EXACT | 一致 | MIN(release_year) 等价 |
| 3989 | EXACT | 一致 | 论文/作者连接与 DISTINCT 等价 |
| 4027 | EXACT | 一致 | 过滤 Title 等价 |
| 4149 | EXACT | 不一致 | 用 review_count<10 替代参考的 Phoenix/Low 口径 |
| 4162 | EXACT | 一致 | 与参考完全一致 |
| 4175 | EXACT | 部分一致 | 时间差表达式不同（strftime），结果可能不同 |
| 4191 | EXTRA | 部分一致 | 多连 Business；过滤条件一致 |
| 4218 | EXACT | 不一致 | user_fans>100 替代参考的 'High' 口径 |
| 4275 | EXACT | 一致 | DISTINCT + 大小写无关，等价 |
| 4387 | EXACT | 部分一致 | 连接链一致但缺 DISTINCT，可能重复 |
| 4516 | MISS | 不一致 | thinking 耗尽预算，无输出 |
| 4554 | EXTRA | 部分一致 | 多连 Award/Episode 并加 season=20 |
| 4565 | MISS | 不一致 | 缺 Vote，SUM(e.votes) 引用不存在的列 |
| 4644 | EXACT | 一致 |  |
| 4683 | EXACT | 不一致 | 漏 'Maybe'，改用问题文本过滤 |
| 4895 | EXACT | 部分一致 | COUNT(DISTINCT games_id) vs 参考 COUNT(games_id) |
| 4907 | EXACT | 一致 | 多 DISTINCT，等价 |
| 4918 | EXACT | 一致 | 等值匹配等价于参考 LIKE |
| 4973 | EXACT | 一致 | 日期区间等价于 STRFTIME 月份 |
| 4981 | EXACT | 部分一致 | COUNT(DISTINCT BrandID)，Twitter 空串并入 NULL |
| 5077 | MISS | 不一致 | 改用 location.State，缺 rootbeerbrand |
| 5088 | MISS | 不一致 | 误答 public_review_platform，缺 beer_factory |
| 5287 | EXACT | 部分一致 | 参考按订单数计占比，生成按价格加权 |
| 5320 | MISS | 不一致 | 误连 customer/cust_order/order_line，缺 author |
| 5472 | EXACT | 不一致 | 用 Y 列排序，参考用 H 列 |
| 5549 | EXACT | 部分一致 | 表与条件一致，连接键用 year+tmID 而非 lgID |
| 5802 | EXACT | 不一致 | 书名改 'chicken pita sandwiches'，输出 max_qty |
| 6052 | MISS | 部分一致 | 缺 address；其余与参考等价 |
| 6118 | EXACT | 一致 | ORDER BY length DESC LIMIT 1 等价于 MAX(length) |
| 6139 | EXACT | 一致 | 三表连接等价 |
| 6166 | EXACT | 一致 | 大小写无关的等价条件 |
| 6223 | EXACT | 一致 | MAX(amount) 等价于 ORDER BY amount DESC LIMIT 1 |

## 三、关键发现

1. **综合表现最好**：业务库完全正确率 94%、业务表完全正确率 76%，均高于两个微调模型（82%/26%）。
2. **几乎不产生幻觉连接**：业务表精确率 91.8%，而微调模型仅 55.6%/62.1%；失败主要来自字段口径而非多余表。
3. **可解析率 92%**：8 条未通过解析，其中重算后仍有 2 条 thinking 耗尽 16384 token 导致空输出（3521、4516），2 条未限定且二义的表名（3540、6052）。
4. **输出普遍使用未限定表名**：SQLite 题面要求 `库.表` 限定，DeepSeek 大量输出裸表名；已在评测中做无答案泄露的唯一化映射。
5. **剩余错误集中在口径**：阈值/字面量（4218 粉丝 High、4149 评论 Low、5802 书名）、字段选择（3203、5472）、聚合对象（3210、4895）。
6. **thinking 成本高**：单题 completion 常在 1000–16000 token，2 题跑满预算未收敛；相比微调模型（≤768 token）延迟与成本显著上升。
7. **提示词召回仍是上限**：8 题提示词缺参考表，与两个微调实验同一批。

## 四、复现

```bash
DEEPSEEK_API_KEY=... PYTHONPATH=src .venv/bin/python -m text2query.cli experiment-sqlite50 \
  --endpoint https://api.deepseek.com/v1 --model deepseek-flash --thinking \
  --sample-size 50 --seed 42 --max-tables 6 --max-output-tokens 16384 --workers 6 \
  --output-dir outputs/experiments/sqlite50_deepseek_flash_thinking
```

## 五、数据泄露检查

结论：**未发现训练集注入或答案泄露**。三个模型使用完全相同的样本、检索索引与提示词，检查结果一致。

| 检查项 | 结果 |
| --- | --- |
| 检索索引训练来源 | `data/赛题8/splits/train.json`，SHA256 `5b2a23…`（与完整 `QA_train.json` 的 `2e7403…` 不同） |
| 索引训练案例数 | 5247（= 划分后训练集），非 5830 |
| 索引中与验证集文本重叠的案例 | 10（id 不重叠）；**抽样 50 题中为 0** |
| 抽样 50 题与训练集完全/规范化同文本 | 0 / 0 |
| 提示词中出现 `SELECT` | 0 / 50 |
| 提示词中出现训练集问题文本 | 0 |
| 提示词中出现训练集 SQL | 0 |
| 提示词中出现本题参考答案 SQL | 0 |
| 知识库文档中出现验证集参考 SQL | 0 |
| 提示词内容 | 仅表 DDL（`CREATE TABLE` / ES mapping）+ 数据源与召回业务库名 |

说明：

1. 外部注入只使用**划分后训练集**构建检索索引；训练集只影响“召回哪些表”，其问题与 SQL **从不进入提示词**。
2. 抽样前按 `question not in train_texts` 排除与训练集同文本的题；SQLite 验证题中此类重复为 0。
3. 整个验证集（583 题）中有 10 题与训练集存在同文本不同 id 的重复（属数据集自身问题，非本实验引入），这 10 题均为非 SQLite，未进入本次抽样。
4. 提示词中的“涉及的数据库”来自召回表的 schema 归属，属既定提示格式，不读取参考答案。
