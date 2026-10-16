# 三种预处理与最终提示词覆盖率

比较三套完整方案：纯程序关联＋BM25、Qwen3 8B 混合检索＋重排、Qwen3 0.6B 混合检索＋重排。
入口为 `text2query.experiments.prompt_coverage`。三套产物分别保存，不覆盖默认 `data/preprocessed/`。

本轮目录为 [`preprocessing-prompt-coverage-v1`](../outputs/experiments/preprocessing-prompt-coverage-v1/)。
三组均保留72张表、1833条知识，索引各含4447条文档（72条Schema、1833条知识、2542条训练案例）。

| 预处理方法 | 表与知识配对数 | 至少关联一张表的知识数 |
| --- | ---: | ---: |
| 纯程序 | 766 | 391 |
| 8B模型 | 864 | 357 |
| 0.6B模型 | 864 | 387 |

程序组按原有0.30阈值筛选，两个模型组各表保留12个实验候选；配对数量不作为关联正确性指标。

## 本轮结果

三组使用各自完整检索方案，最终提示词覆盖率如下。全部284道参考查询均成功解析；完整覆盖允许额外库表。

| 方案 | 完整业务库覆盖 | 完整业务表覆盖 |
| --- | ---: | ---: |
| 纯程序预处理＋BM25 | 85.56%（243/284） | 84.86%（241/284） |
| 8B预处理＋8B混合检索／重排 | **98.24%（279/284）** | **93.66%（266/284）** |
| 0.6B预处理＋0.6B混合检索／重排 | 97.89%（278/284） | 93.31%（265/284） |

8B的完整表覆盖率比程序组高8.80个百分点，0.6B高8.45个百分点；8B比0.6B多覆盖1题，差0.35个百分点。
相对程序组，8B新增完整覆盖31题、损失6题；0.6B新增31题、损失7题。
两模型直接比较，8B独有完整覆盖7题，0.6B独有6题，不能把总体差1题理解为逐题结果相同。

在下游统一使用BM25、只改变预处理数据时：

| 预处理数据 | 完整业务库覆盖 | 完整业务表覆盖 |
| --- | ---: | ---: |
| 纯程序 | 85.56%（243/284） | 84.86%（241/284） |
| 8B | 88.03%（250/284） | 84.86%（241/284） |
| 0.6B | 87.68%（249/284） | 84.86%（241/284） |

单独更换预处理数据未提高本轮完整表覆盖的总题数，主要净增益与查询阶段的混合检索、重排及相应案例选择流程有关。
统一BM25时8B有2题增益／2题损失，0.6B有5题增益／5题损失，预处理仍会改变逐题结果。

| 数据源 | 题数 | 程序组完整表覆盖 | 8B完整表覆盖 | 0.6B完整表覆盖 |
| --- | ---: | ---: | ---: | ---: |
| MySQL | 197 | 80.71%（159） | 93.91%（185） | 92.89%（183） |
| PostgreSQL | 41 | 97.56%（40） | 97.56%（40） | 97.56%（40） |
| Elasticsearch | 37 | 100%（37） | 100%（37） | 100%（37） |
| MySQL＋PostgreSQL | 9 | 55.56%（5） | 44.44%（4） | 55.56%（5） |

总体提升集中在MySQL；跨源样本只有9题，8B本轮比另两组少完整覆盖1题。
共享路由正确279/284题，5题漏掉所需数据库系统；三组均未触发16000字符预算裁剪，均无空提示词。
现有提示词构造器排除`common.administrative_division`，本轮参考目标没有要求该表。
8B运行显存allocated峰值29.66GiB，0.6B为2.40GiB。

主流程共852份提示词；补充BM25对照再生成568份，程序组复用原结果。
7项评分／提示词边界测试通过，实际文档、向量对齐、原文保真、输入隔离和独立覆盖计数核对通过。
执行时源码与运行脚本归档在`execution/source/`及`execution/`，完成后的代码仅修正报告表格转义和评分边界的文字说明。
输入、运行源码和产物哈希分别见`manifest.json`、`execution/source/`与`artifact_sha256.json`。

- [完整方案报告](../outputs/experiments/preprocessing-prompt-coverage-v1/README.md)
- [统一BM25对照](../outputs/experiments/preprocessing-prompt-coverage-v1/controlled_bm25/README.md)
- [逐题三方对照CSV](../outputs/experiments/preprocessing-prompt-coverage-v1/per_question_comparison.csv)
- [产物独立核对](../outputs/experiments/preprocessing-prompt-coverage-v1/artifact_verification.json)

## 输入与流程

对当前 `QA_train.json` 按已有分层方法划分，seed=42，保留全部284道验证题。
删除训练划分中与验证问题同文本的记录，供三套关联、路由和检索共同使用；原始划分及排除ID均保存在清单中。
路由使用同一个字符TF-IDF分类器，避免路由模型差异影响比较。

程序基线沿用默认TF-IDF、字符／字段规则和训练SQL弱证据。
两个模型组从原始表结构生成查询，让全部1833条知识参与BM25与Embedding检索，经RRF和重排后，
每张表取Top12作为本次实验的候选归属。候选归属明确标为实验数据，不是人工确认关系。
关联原文、完整排序与分数单独审计；Schema和knowledge原文保留。

各组分别构建包含Schema、全部知识与划分后训练案例的索引，再用对应方法执行逐题召回。
复用 `ContextBuilder.assemble` 和 `submission.finetuned.build_instruction`，候选表上限6，
DDL指令上限16000字符；超限时按召回顺序从末尾整张移除。
沿用已有DDL提示词格式：知识和案例影响召回，最终消息不直接拼入其全文。
现有提示词构造器排除的表不会计入最终覆盖。

准备阶段从验证样本中提取question_id和question，并冻结划分；不使用验证SQL的内容。
生成阶段仅加载公共问题文件和共享路由预测，参考SQL在三组提示词全部完成后才解析用于独立评分。
不调用SQL生成端点；此实验衡量提示词证据覆盖，不能解释为SQL正确率。

## 覆盖率口径

完整业务库覆盖：参考查询所需的全部业务库均出现在最终提示词中的表结构中。
完整业务表覆盖：参考查询所需的全部业务表均出现在最终提示词中。
允许额外召回；这与要求集合完全相等的精确匹配指标不同。

库和表均按数据库系统区分，PostgreSQL按业务Schema命名空间、Elasticsearch按原始唯一索引解析。
跨源查询合并所有步骤的目标。
参考SQL有未解析表或解析错误时，不把剩余部分或空目标当作完整目标；在全量分母中保守计为未完整覆盖并单列。
同时报告路由正确性、裁剪前覆盖、裁剪后覆盖、预算移除和逐题缺失，便于定位损失来源。

## 运行

在具备模型权重及CUDA的V6目录执行，使用尚不存在的新目录：

```bash
export PYTHONPATH=src
export OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false
EXP=outputs/experiments/preprocessing-prompt-coverage-v2

python -m text2query.experiments.prompt_coverage prepare --output-dir "$EXP"
python -m text2query.experiments.prompt_coverage run --experiment-dir "$EXP" --method programmatic
python -m text2query.experiments.prompt_coverage run --experiment-dir "$EXP" --method hybrid-8b
python -m text2query.experiments.prompt_coverage run --experiment-dir "$EXP" --method hybrid-0.6b
python -m text2query.experiments.prompt_coverage score --experiment-dir "$EXP"
```

默认BF16、Embedding batch=4、Reranker batch=2，输入截断512／2048 tokens，召回深度50，RRF k=60。
每组均输出 `preprocessed/`、`index/`、`contexts.jsonl`、`prompts.jsonl`、运行记录和覆盖率明细。
总目录保存输入／代码哈希、固定划分、共享路由预测、逐题CSV和三方对照报告。
模型候选归属与问题检索同时变化，实验结果比较完整方案，不单独归因于Embedding或重排组件。
历史运行的执行源码已保留在`execution/source/`；重评分历史产物需使用该快照，以满足严格代码哈希核验。

## 固定下游召回的补充对照

为单独观察三份预处理数据的影响，另用同一BM25配置、路由预测、案例回退、表数上限和字符预算生成提示词。
程序组复用原有提示词，两个模型组只使用各自已完成的预处理目录，不再运行模型或改变候选关联。
结果单独保存在实验目录的 `controlled_bm25/`，不与各自使用模型召回的主实验混报。

在主实验完成后执行：

```bash
python evaluation/prompt_coverage/controlled_retrieval.py --experiment-dir "$EXP" --method hybrid-8b
python evaluation/prompt_coverage/controlled_retrieval.py --experiment-dir "$EXP" --method hybrid-0.6b
python evaluation/prompt_coverage/controlled_retrieval.py --experiment-dir "$EXP"
```
