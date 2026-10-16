# 多标签路由后的提示词完整覆盖率

将已冻结的“Qwen3-Embedding-0.6B＋多标签分类”系统路由接入原 0.6B 混合检索与 DDL 提示词流程，评价全部 284 道验证题。

[完整报告](../outputs/experiments/semantic-multilabel-prompt-coverage-v1/README.md) · [实际 LLM 消息](../outputs/experiments/semantic-multilabel-prompt-coverage-v1/llm_messages.jsonl) · [逐题 CSV](../outputs/experiments/semantic-multilabel-prompt-coverage-v1/evaluation/overview.csv) · [剩余缺表明细](../outputs/experiments/semantic-multilabel-prompt-coverage-v1/evaluation/missing_tables.json)

## 结果

| 系统路由 | 完整业务库覆盖率 | 完整业务表覆盖率 |
| --- | ---: | ---: |
| 原字符 TF-IDF＋多类分类 | 97.89%（278/284） | 93.31%（265/284） |
| **语义向量＋多标签分类** | **99.65%（283/284）** | **95.07%（270/284）** |

两项均新增完整覆盖 5 题，提升 1.76 个百分点。系统路由准确率为 284/284，但仍有具体业务库、表没有进入最终提示词，不能将系统路由成绩替代提示词覆盖率。

| 联查子集 | 题数 | 原路由完整业务库／表 | 多标签路由完整业务库／表 |
| --- | ---: | --- | --- |
| 跨系统 MySQL＋PG | 9 | 5/9、5/9 | **9/9、9/9** |
| 参考方向 MySQL→PG | 5 | 2/5、2/5 | 5/5、5/5 |
| 参考方向 PG→MySQL | 4 | 3/4、3/4 | 4/4、4/4 |
| 同系统内跨业务库 | 48 | 47/48、36/48 | **47/48、36/48** |
| 同系统内多表 | 98 | 97/98、84/98 | 97/98、84/98 |

同系统跨业务库的完整库覆盖率为 97.92%，完整表覆盖率为 75%。该子集与同系统多表子集有重叠；参考方向分组不表示路由模型预测了执行顺序。

剩余 14 道不完整覆盖均为 MySQL 多表题，涉及字典表、财税表及跨年度教育表。1996 题还缺少整个 `education_2025` 业务库。它们的系统路由均正确，具体库表召回缺口仍然存在；新旧路由下提示词相同，没有进一步扩大候选表预算。

## 生成和评价口径

- 沿用此前有效训练 2542 题、验证 284 题的冻结划分，使用既有 0.6B 预处理、4447 条检索文档及对应文档向量。没有重新训练或调节多标签参数。
- 使用 `ContextBuilder.assemble` → `make_prompt`／`finetuned.build_instruction`，初始最多 6 张表，官方 DDL 系统提示词最多 16000 字符，超限整表裁剪。本轮没有字符预算裁剪或空提示词。
- 知识和训练案例参与检索排序；该 DDL 提示词格式不直接附加知识和案例全文，与此前覆盖率实验口径一致。它与 DeepSeek 完整 JSON 上下文提示词是不同格式，本报告不混报后者。
- 完整业务库覆盖要求参考所需的所有 `系统:业务命名空间` 均在实际提示词的表结构中；完整表覆盖要求全部参考表均出现。允许额外召回，不要求集合完全相等。
- 全部 284 道参考 SQL/DSL 均成功解析，跨系统查询合并所有步骤的目标。仅在全部提示词准备完毕后解析参考，生成阶段不使用验证参考 SQL。
- 这仍是此前使用过的开发验证集，跨系统只有 9 题；覆盖率不代表 SQL 正确率或外部判题成绩。本次没有调用 LLM 或执行数据库。

## 复用、重算与环境差异

新旧路由仅 2574、2942、2970、2972、2980 五题不同。其余 279 题复用冻结检索结果，并重新核对 DDL 消息逐字一致。

五题在本机 CPU FP32 下重新执行 BM25＋embedding→RRF→0.6B 重排。文档向量保留原 GPU BF16 推理后归一化的 FP32 版本；新查询与重排使用 CPU FP32，没有将历史 GPU logits 混入新的评分池。原预处理关联、候选深度 50、RRF k=60、表数及字符预算保持原配置。

同时为五题重新运行旧路由作为对照：五份旧路由提示词全部逐字复现历史消息。新路由补齐了 PG AIS、MySQL 船舶及公司等结构，五题均从不完整变为完整覆盖。

本机重新计算 1297 个问题/文档重排分数，复用本轮缓存 380 次，生成阶段约 1149 秒。未重新计算全部文档向量，未启动 GPU 服务器。执行环境和源码快照见实验目录 `execution/`。

10 项针对性与路由回归测试通过；评分前全量提示词检查、缓存精度隔离、完整业务库与表计数差异均有测试覆盖。

## 复现

在 V6 目录、配置好项目依赖与本地模型的环境中，使用新的输出目录：

```bash
python -m text2query.experiments.multilabel_prompt_coverage generate \
  --output outputs/experiments/semantic-multilabel-prompt-coverage-v2
python -m text2query.experiments.multilabel_prompt_coverage score \
  --output outputs/experiments/semantic-multilabel-prompt-coverage-v2
```

`generate` 可从同配置的部分完成案例和本轮本地分数缓存恢复；完成后禁止覆盖冻结结果。`score` 校验生成时的输入哈希及题目全量性，输出完整覆盖、分组、逐题缺失和变化明细。
