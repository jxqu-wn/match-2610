# 第二轮检索与提示词参数迭代

入口：`evaluation/prompt_quality/iteration_v2.py`。保留v1的输入、评分与SQL生成产物，新建`outputs/experiments/prompt-quality-sweep-v2`。

## 修复与对照

`ContextBuilder._drop_orphans`保留明确标记`retrieval_scope=global`的knowledge候选，即使原目录没有table–knowledge关联。只保留候选身份，不修改关联器、知识原文或已确认关系；未标记的旧候选仍按原逻辑清理。

保留冻结基线，以及固定表/重新检索12表的修复前后对照。旧逻辑对照不设置global标记，重现原关联清理行为。

## 阶段A：37组

- 5组控制。
- 候选表6/8/10/12 × knowledge6/12/18 × 案例2/4，共24组。
- 原完整检索元数据3组，与压缩元数据方案对照；12表完整元数据已包含在控制中。
- 先裁案例1组；输入预算15000/18000两组，与21000比较。
- 使用原Schema的`source_values`前8条样例两组，分别配8/12表；不猜值域或增加人工字典。

压缩只去掉实际LLM上下文中冗长的检索分数、命中词、候选排序元数据，以及预算调试描述。完整列信息、主外键、原始knowledge、案例查询和来源标识保留。预算前的完整上下文另存`audit_context_before_budget`，不丢诊断记录。

## 阶段B：31组

仅根据阶段A选参子集选择种子，再分别对Schema、knowledge、案例三个检索分支改变BM25 TopK25/100、embedding TopK25/100、RRF k20/100、重排池25/100与关闭重排，共27组；另测知识支持表排名权重0/1与路由扩展两组。

路由扩展为全引擎搜索，或用全局Schema排名前两条涉及的引擎扩充原路由。没有重新训练分类器或调整其概率阈值。知识支持默认权重仍为0.25，生产默认排序保持原值。

分支检索复用现有`RetrievalIndex`、rank-bm25、embedding和CrossEncoder；只做参数编排与同签名缓存。Schema关闭重排时，现有组装器会启用首案例补表行为，因此该组是现有完整流程的消融，不是冻结表集合的纯打分对照。

## 数据隔离与选参

原284题中，上一轮20题只作回归。按固定哈希再取12题作本轮开发验收：单表4、同库多表3、同系统跨业务库3、跨系统2；其余252题选参。7道已知知识缺口题不进入新验收题，但仍属于开发选参资料。由于所有题此前曾用于项目开发，新验收只具有本轮隔离意义。

推理仅使用`public/`。原参考、表目标和局部知识标签留在本地`private_evaluation/`。选参要求每个拓扑分组及整体库表覆盖不退于冻结控制，局部知识正例命中不退于修复后的固定表全局知识控制；再比较完整表覆盖和P95，另提供接近最高覆盖但输入较短的方案与Pareto前沿。该筛选仍是开发代理指标，不是全量提示词质量金标。

完整必要事实覆盖、语义噪声率与执行准确率无金标或数据库环境，仍输出null。表覆盖不能抵消关键知识丢失；静态校验通过不等于业务正确。

## 运行

```bash
python evaluation/prompt_quality/iteration_v2.py prepare --output outputs/experiments/prompt-quality-sweep-v2
python evaluation/prompt_quality/iteration_v2.py run \
  --public outputs/experiments/prompt-quality-sweep-v2/public \
  --output outputs/experiments/prompt-quality-sweep-v2/inference \
  --embedding-model /path/to/Qwen3-Embedding-0.6B \
  --reranker-model /path/to/Qwen3-Reranker-0.6B --device cuda:0 --dtype bfloat16
python evaluation/prompt_quality/iteration_v2.py score \
  --public outputs/experiments/prompt-quality-sweep-v2/public \
  --private outputs/experiments/prompt-quality-sweep-v2/private_evaluation \
  --output outputs/experiments/prompt-quality-sweep-v2/inference
python evaluation/prompt_quality/iteration_v2.py select \
  --public outputs/experiments/prompt-quality-sweep-v2/public \
  --output outputs/experiments/prompt-quality-sweep-v2/inference \
  --expansion-grid outputs/experiments/prompt-quality-sweep-v2/stage_b_grid.json
```

第二阶段使用相同run命令加`--grid stage_b_grid.json`，在同一代码/输入/模型签名下继续。源码与权重签名发生变化时必须另建输出版本。分数/向量缓存只在模型、精度、指令与原始文档一致时复用；独立复制旧缓存并保留核验清单，不修改旧实验缓存。

选定少量配置后复用`sql_experiment.py`冻结真实提示词，调用DeepSeek并保存请求响应。新12题、已知缺口7题与原回归抽样分别报告；参考查询不发送给生成模型。没有真实数据库执行时仅作Codex静态业务核心复核，精度/投影规则问题单列。
