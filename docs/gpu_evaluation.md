# Qwen3 8B 召回模型 GPU 评估

两个本地模型已完成真实 GPU 集成测试及表结构→知识排序评估。
结果保存于 [hybrid-qwen3-8b-gpu-v2](../evaluation/table_knowledge/runs/hybrid-qwen3-8b-gpu-v2/README.md)，
逐表解读见 [COMPARISON.md](../evaluation/table_knowledge/runs/hybrid-qwen3-8b-gpu-v2/COMPARISON.md)。

## 环境与参数

- 服务器检测到 RTX 4090、49140 MiB 显存；容器配额为20 vCPU、96 GiB内存。
- PyTorch 2.8.0+cu128、sentence-transformers 5.7.0、transformers 5.19.0。
- 两个原始8B模型使用BF16，同时保留在GPU；模型和分词器的11个LFS文件全部通过SHA256校验。
- Embedding batch=4、截断512 tokens；Reranker batch=2、截断2048 tokens。
- BM25与Embedding各取50，RRF k=60，精排前50，观察不同Top-K。
- PyTorch allocated峰值29.66 GiB，reserved峰值30.15 GiB。48GB显存足以完成此次配置。

完整依赖、硬件和校验记录见结果目录的 `execution/`。
显存结论适用于此次两个模型的召回评估。

## 与人工＋LLM标注比较

旧版完整基准为72张表、247条知识、270个接受配对。
新版以全部1833条知识竞争候选，仅对ID与原文同时未变的173条知识、155个接受配对评分；
新增和改写知识单列为未标注，不作负例。

| 方法 | 旧版 Recall@12 | 新版可比子集 Recall@12 |
| --- | ---: | ---: |
| BM25 | 40.37% | 43.23% |
| Embedding | 58.15% | 40.65% |
| RRF | 57.78% | 43.23% |
| RRF＋重排 | **71.85%** | **54.19%** |

相对RRF，重排在旧版多命中38个配对，提升14.07个百分点；新版可比子集多命中17个配对，提升10.97个百分点。
新版已标注子集的precision从55.37%降至40.00%，F1从48.55%降至46.03%。
重排改变了已标注与未标注结果的占比，不能仅凭召回提升宣称所有指标改善。

新版155个已知正例仅有88个进入RRF前50；重排把其中84个放入前12。
候选覆盖仍是下一步需要评估的重点。

本实验使用原始表结构作为查询，所有知识全局竞争，未用审核关联过滤候选。
它衡量表→知识候选排序，不代表逐题问题召回率或最终查询正确率。
Top-K不写回预处理确认关联；若将旧版Top12直接作为确认关系，多关联/命中为345.36%，未满足200%要求。
逐表precision、recall、F1、噪声及零命中项保存在 `per_table_metrics.csv` 和 `noise_summary.json`。

## 修复与验证

真实BF16推理暴露了模型内部归一化后的舍入误差，单位向量长度最多偏离1约0.15%。
向量服务现以float32再次L2归一化后写缓存；缓存签名增加 `normalization_dtype`，旧向量缓存自动失配。
新版1833条知识的来源、数量和哈希另存 `knowledge_manifest.json`，历史清理清单保留。

22项数据、向量缓存、评估计分和检索回归测试通过；真实GPU集成测试通过。
本地已核对报告记录的37个代码哈希，并验证576条逐表指标与汇总计数一致。
冻结标注仅读于独立评价入口，生产预处理未接入审核答案。

向量批量编码耗时26.75秒；旧版排序137.55秒，新版排序118.56秒。
两套语料共享相同文本的重排分数，实际计算6891对、缓存命中309对；这些是离线批处理耗时。

## 复现

模型目录默认位于V6旁的 `../models/`。真实模型测试需显式启用：

```bash
T2Q_RUN_MODEL_TESTS=1 T2Q_MODEL_TEST_DEVICE=cuda:0 T2Q_MODEL_TEST_DTYPE=bfloat16 \
  python -m pytest tests/test_embedding.py tests/test_local_models.py

python evaluation/table_knowledge/evaluate_hybrid_recall.py \
  --output-dir evaluation/table_knowledge/runs/hybrid-qwen3-8b-gpu-v3 \
  --device cuda:0 --dtype bfloat16 \
  --embedding-batch-size 4 --reranker-batch-size 2

python evaluation/table_knowledge/summarize_hybrid_recall.py \
  --run-dir evaluation/table_knowledge/runs/hybrid-qwen3-8b-gpu-v3
```

输出目录必须不存在。分阶段加载可加 `--release-embedding`。
