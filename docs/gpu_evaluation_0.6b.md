# Qwen3 0.6B 权重与检索实验

两个0.6B模型的原始权重已下载到共享 `models/`，并在此前的48GB GPU服务器上完成真实模型测试和检索评估。
结果见 [0.6B运行报告](../evaluation/table_knowledge/runs/hybrid-qwen3-0.6b-gpu-v1/README.md) 与
[0.6B／8B对照](../evaluation/table_knowledge/runs/comparison-0.6b-vs-8b-v1/README.md)。

## 模型与校验

| 模型 | 路径 | 仓库修订 |
| --- | --- | --- |
| Qwen3-Embedding-0.6B | `../models/Qwen3-Embedding-0.6B` | `97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3` |
| Qwen3-Reranker-0.6B | `../models/Qwen3-Reranker-0.6B` | `e61197ed45024b0ed8a2d74b80b4d909f1255473` |

两个权重约2.383GB，加上两个tokenizer.json，LFS文件合计2.406GB。
本地及服务器均已核对这4个LFS文件和4个分词器辅助文件的SHA256。
预期大小与校验值见 [model_weights_manifest_0.6b.json](model_weights_manifest_0.6b.json)。
本地实际校验记录位于 `../models/download-verification-0.6b.json`，服务器记录随运行结果保存在 `execution/`。

## 实验条件

沿用8B实验的同一GPU、依赖版本、原始输入、任务指令和参数：BF16、Embedding batch=4、Reranker batch=2、
向量截断512 tokens、重排截断2048 tokens、两路各取50、RRF k=60、重排前50。
所有Top-K、候选范围与原文未变知识的计分口径相同。
对照程序已确认生产检索代码哈希相同、数据和标签哈希相同，且BM25完整排序相同。
评估入口只将报告标题改为显示实际模型名，未修改检索或评分算法。

旧版使用247条知识与270个标注配对。新版以1833条知识竞争，仅对ID与原文均未变的173条知识、155个标注配对评分；
改写和新增知识保持未标注。参数未依据本轮标签调优，结果仍属于已有审核集的开发评估。

## RRF＋重排结果

| 指标 | 8B＋8B | 0.6B＋0.6B |
| --- | ---: | ---: |
| 旧版命中@12 | 194/270 | 200/270 |
| 旧版 Recall@12 | 71.85% | **74.07%** |
| 旧版 precision@12 | 22.45% | 23.15% |
| 旧版 F1@12 | 34.22% | 35.27% |
| 新版可比子集命中@12 | 84/155 | 77/155 |
| 新版可比子集 Recall@12 | **54.19%** | 49.68% |
| 新版已标注返回 precision@12 | 40.00% | 46.95% |
| 新版已标注返回 F1@12 | 46.03% | 48.28% |

0.6B组合在旧版Recall@12上提高2.22个百分点，在新版可比子集上降低4.52个百分点。
新版precision和F1只覆盖已标注返回，不能解释为1833条知识的全量精度。
0.6B新版前12有700个未标注返回，8B为654个，需结合标注覆盖范围解读。

0.6B的新版RRF前50覆盖82个已知正例，重排将其中77个放入前12；8B分别为88和84。
当前0.6B候选池的已知正例上限为82/155（52.90%），单独增加最终输出数量无法补回候选池外的正例。
Top-K均为候选，未写回预处理确认关联；逐表噪声与200%要求检查见各运行目录的 `noise_summary.json`。

## 资源与测试

| 项目 | 8B＋8B | 0.6B＋0.6B |
| --- | ---: | ---: |
| GPU allocated峰值 | 29.66 GiB | **2.40 GiB** |
| GPU reserved峰值 | 30.15 GiB | 2.49 GiB |
| 批量向量编码 | 26.75秒 | 13.75秒 |
| 两套语料排序合计 | 256.11秒 | **75.07秒** |

两个模型同时保留在GPU。0.6B实际计算重排6960对，缓存命中240对；8B为6891对、309对。
耗时是包含缓存复用的离线批处理结果，不能直接作为在线单请求延迟或纯模型吞吐。
4项测试通过，包括真实GPU集成测试和3项评估计分／输入检查；记录见 `execution/model-tests.log`。
GPU任务完成后模型显存已释放。

本实验同时替换Embedding与Reranker，反映组合方案的差异，尚未做两个组件交叉替换的独立归因。
评估查询为原始表结构；结果不等同于逐题问题召回率或最终查询正确率。

## 复现

```bash
export T2Q_EMBEDDING_MODEL=../models/Qwen3-Embedding-0.6B
export T2Q_RERANKER_MODEL=../models/Qwen3-Reranker-0.6B

python scripts/verify_model_weights.py --manifest docs/model_weights_manifest_0.6b.json

T2Q_RUN_MODEL_TESTS=1 T2Q_MODEL_TEST_DEVICE=cuda:0 T2Q_MODEL_TEST_DTYPE=bfloat16 \
  python -m pytest tests/test_local_models.py tests/test_hybrid_evaluation.py

python evaluation/table_knowledge/evaluate_hybrid_recall.py \
  --output-dir evaluation/table_knowledge/runs/hybrid-qwen3-0.6b-gpu-v2 \
  --device cuda:0 --dtype bfloat16 --embedding-batch-size 4 --reranker-batch-size 2

python evaluation/table_knowledge/summarize_hybrid_recall.py \
  --run-dir evaluation/table_knowledge/runs/hybrid-qwen3-0.6b-gpu-v2

python evaluation/table_knowledge/compare_model_runs.py \
  --baseline evaluation/table_knowledge/runs/hybrid-qwen3-8b-gpu-v2 \
  --candidate evaluation/table_knowledge/runs/hybrid-qwen3-0.6b-gpu-v2 \
  --output-dir evaluation/table_knowledge/runs/comparison-0.6b-vs-8b-v2
```

选择尚不存在的输出目录，保留既有实验产物。
