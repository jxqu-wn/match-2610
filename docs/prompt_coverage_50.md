# 验证集50题的LLM提示词与覆盖率

从上轮冻结的284道验证题中按数据库系统和跨源方向分层抽取50题，固定seed=42。
三组使用同一题单：MySQL 35题、PostgreSQL 7题、Elasticsearch 6题、两个跨源方向各1题。
抽样未按成功或失败结果筛选；原始训练集、预处理数据、路由、候选表上限6和指令预算16000字符保持一致。

复用已完成的逐题检索排序，从对应预处理目录重新组装官方DDL `system` 消息和原问题 `user` 消息。
所有重建消息均与上轮冻结消息完全一致，没有重复进行模型推理。
三组主比较各生成50份LLM输入；另导出三组统一BM25对照，程序组消息在两种口径下相同。

## 沿用各组对应检索方案

| 方案 | 完整业务库覆盖 | 完整业务表覆盖 |
| --- | ---: | ---: |
| 纯程序预处理＋BM25 | 82%（41/50） | 82%（41/50） |
| 8B预处理＋8B混合检索／重排 | 98%（49/50） | 94%（47/50） |
| 0.6B预处理＋0.6B混合检索／重排 | 98%（49/50） | 96%（48/50） |

0.6B在本轮50题样本中比8B多完整覆盖1题；这不是全量284题的排名结论。
三组共享路由，数据库系统预测正确49/50题。全部50道参考查询可完整解析，均无空提示词。

## 统一BM25，只比较预处理数据

| 预处理数据 | 完整业务库覆盖 | 完整业务表覆盖 |
| --- | ---: | ---: |
| 纯程序 | 82%（41/50） | 82%（41/50） |
| 8B | 82%（41/50） | 82%（41/50） |
| 0.6B | 84%（42/50） | 82%（41/50） |

完整覆盖要求参考查询所需的全部业务库／表都在最终提示词中，允许额外召回。
这是提示词证据覆盖率，不是库表集合完全相等或SQL生成正确率。
样本来自已经评估过的同一验证集，用于逐题检查，不是新增独立测试集。

## 提示词与报告

JSONL每行仅含 `question_id` 和 `messages`，取 `messages` 作为LLM输入。
参考目标与缺失明细单独保存在 `evaluation/`，没有加入消息。
沿用现有微调DDL格式：知识和训练案例影响召回，消息不直接附加其全文。

| 方案 | LLM消息JSONL | 可阅读Markdown |
| --- | --- | --- |
| 纯程序 | [prompts.jsonl](../outputs/experiments/prompt-coverage-50-v1/corresponding_retrieval/programmatic/prompts.jsonl) | [prompts.md](../outputs/experiments/prompt-coverage-50-v1/corresponding_retrieval/programmatic/prompts.md) |
| 8B | [prompts.jsonl](../outputs/experiments/prompt-coverage-50-v1/corresponding_retrieval/hybrid-8b/prompts.jsonl) | [prompts.md](../outputs/experiments/prompt-coverage-50-v1/corresponding_retrieval/hybrid-8b/prompts.md) |
| 0.6B | [prompts.jsonl](../outputs/experiments/prompt-coverage-50-v1/corresponding_retrieval/hybrid-0.6b/prompts.jsonl) | [prompts.md](../outputs/experiments/prompt-coverage-50-v1/corresponding_retrieval/hybrid-0.6b/prompts.md) |

各目录的 `prompts/question_<id>.md` 保存每题独立提示词；`fixed_bm25/` 保存统一召回配置的对照消息。

- [完整报告与统一BM25提示词链接](../outputs/experiments/prompt-coverage-50-v1/README.md)
- [50题抽样清单与来源哈希](../outputs/experiments/prompt-coverage-50-v1/sample_manifest.json)
- [问题原文](../outputs/experiments/prompt-coverage-50-v1/questions.json)
- [逐题覆盖差异CSV](../outputs/experiments/prompt-coverage-50-v1/evaluation/per_question_comparison.csv)
- [消息一致性核对](../outputs/experiments/prompt-coverage-50-v1/verification.json)

## 复现

使用尚不存在的新输出目录，已完成的284题父实验保持不变：

```bash
PYTHONPATH=src python evaluation/prompt_coverage/sample_prompts.py \
  --parent-dir outputs/experiments/preprocessing-prompt-coverage-v1 \
  --output-dir outputs/experiments/prompt-coverage-50-v2 \
  --size 50 --seed 42
```

脚本在消息全部生成后才解析参考查询评分，校验父产物哈希，并保存本轮源码及产物校验清单。
此次没有调用LLM生成答案。
