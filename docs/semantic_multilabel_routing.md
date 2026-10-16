# 语义向量＋多标签路由

新增可独立使用的系统路由方法：本地 Qwen3-Embedding-0.6B 编码问题，scikit-learn `OneVsRestClassifier(LogisticRegression)` 分别判断每个系统是否参与。保留原字符路由及默认生成流程；未修改原 680 题提交结果。

[完整实验报告](../outputs/experiments/semantic-multilabel-routing-v1/README.md) · [汇总 JSON](../outputs/experiments/semantic-multilabel-routing-v1/summary.json) · [逐题预测](../outputs/experiments/semantic-multilabel-routing-v1/validation_predictions.jsonl) · [跨系统案例](../outputs/experiments/semantic-multilabel-routing-v1/cross_system_cases.json)

路由接入既有召回后，实际 DDL 提示词的完整业务库／表覆盖率分别为 99.65% 和 95.07%，跨系统 9 题均完整覆盖。详见[提示词覆盖率实验](semantic_multilabel_prompt_coverage.md)；该指标与下表的系统路由准确率不同。

## 冻结验证结果

沿用此前开发划分：原训练 2555 题，删除与验证问题同文本的 13 条记录后，有效训练 2542 题；验证 284 题。有效训练集中跨系统 81 题，验证集中跨系统 9 题。模型仅使用问题文本作为特征。

| 方法 | 整体系统集合完全正确 | 跨系统系统集合完全正确 | 跨系统漏库 | 单系统误扩为多系统 |
| --- | ---: | ---: | ---: | ---: |
| 原字符 TF-IDF＋多类逻辑回归 | 279/284（98.24%） | 5/9（55.56%） | 4 | 0 |
| 语义向量＋多类逻辑回归 | 283/284（99.65%） | 9/9（100%） | 0 | 1 |
| **语义向量＋多标签逻辑回归** | **284/284（100%）** | **9/9（100%）** | **0** | **0** |

9 道跨系统案例全部保留，没有按成败筛选。旧路由遗漏 MySQL 的 2942、2970、2972、2980 均恢复为两系统集合。多类语义对照唯一错误为 2669：将仅需 PG 的查询额外扩成 MySQL＋PG；多标签模型正确保留 PG。

## 单独评价多库联查

| 子集 | 题数 | 原字符路由正确 | 语义多类正确 | 语义多标签正确 |
| --- | ---: | ---: | ---: | ---: |
| MySQL＋PG 跨系统 | 9 | 5 | 9 | 9 |
| 参考方向 MySQL→PG | 5 | 2 | 5 | 5 |
| 参考方向 PG→MySQL | 4 | 3 | 4 | 4 |
| 同系统内跨业务库 | 48 | 48 | 48 | 48 |
| 同系统内多表查询 | 98 | 98 | 98 | 98 |

方向按参考 SQL 的步骤分组，以上只评价各组是否选对系统集合，模型不预测执行顺序。同系统跨业务库、同系统多表子集有重叠，不能相加。全部 284 题的参考 SQL/DSL 均成功解析；业务库和表集合只用于模型保存后的离线分组，不作为模型特征。

“同系统跨业务库路由正确”仅表示选对 MySQL 等系统，不表示已经选对所有业务库/表，也不代表 JOIN 或最终结果正确。本次未运行 LLM 生成、库表重召回或数据库执行。

## 训练与阈值

编码使用路由专用指令，CPU FP32、最大长度 256、batch size 8，1024 维 L2 单位向量。2826 条训练/验证输入的最大长度为 149 token，没有截断；相同文本复用编码缓存。模型没有微调。

选参使用训练集内部 5 折 `StratifiedGroupKFold`，按问题文本分组，避免相同问题出现在同一折的拟合侧和开发侧。参数网格：

- `C`：0.1、1、10、100。
- `class_weight`：默认、balanced。
- 多标签共享阈值：0.3、0.4、0.5、0.6、0.7。

选择目标是“单系统完全匹配率”和“跨系统完全匹配率”各占 50%；并列时依次比较整体完全匹配率、额外系统数量和预声明网格顺序。验证标签不参与参数选择。选择完成后冻结参数，在全部有效训练数据上重新拟合、保存模型，再评价验证集。

最终多标签参数为 `C=100`、默认类别权重、阈值 `0.3`。每个系统分别过阈值，可以同时选择多个系统；没有系统过阈值时，仅回退到分数最高的一个系统。概率未做校准。

| 选参方法 | 训练内 OOF 整体完全正确 | 训练内 OOF 跨系统完全正确 |
| --- | ---: | ---: |
| 语义多类，C=10、balanced | 2526/2542 | 81/81 |
| 语义多标签，C=100、阈值0.3 | 2520/2542 | 79/81 |

这些 OOF 分数用于选参，不是额外独立测试。多标签在 284 题开发验证上全对，但训练内跨系统分数低于语义多类，因此尚不能断言多标签普遍优于语义多类。本次结果支持语义特征改善了旧字符路由，仍应使用更多独立跨系统问题检验稳定性。

## 使用

[路由实现](../src/text2query/routing/multilabel.py)提供 `fit_vectors`、`predict_vectors`、兼容旧调用格式的 `predict`，以及 `save/load`。保存时绑定编码器设置与权重文件指纹，避免推理时混用其他模型、精度或指令。

在 V6 目录、已安装项目依赖的环境中运行。新评估使用新目录，避免覆盖冻结 v1：

```bash
python -m text2query.cli route-multilabel-evaluate \
  --model-path ../models/Qwen3-Embedding-0.6B \
  --device cpu --dtype float32 \
  --output outputs/experiments/semantic-multilabel-routing-v2
```

加载本次已经训练完成的模型进行预测：

```bash
python -m text2query.cli route-multilabel-predict \
  --question '查询自持力超过45天的船舶，在最近24小时内位于(122.0, 30.0)至(122.2, 30.2)矩形内且速度小于3节的MMSI。' \
  --save outputs/route_example.json
```

输出包含 `databases`、各系统分数、阈值及是否发生回退，可供现有 `recall --classification-json` 读取。此次 CLI 实测返回 `MYSQL`、`POSTGRESQL`。预测默认沿用保存模型的编码配置，未自动切换原生成流程。

## 检查与边界

7 项新增测试覆盖多标签选择、空集合回退、未见过的系统组合、模型保存加载及编码设置隔离、训练分组、选参目标、联查指标和 CLI→recall 兼容；连同 3 项既有跟踪回归，共 10 项通过。新增模块通过 Ruff 检查；CLI 既有 `B008/UP045` 项未扩大整改。

本次向量计算在本机 CPU 完成，用时约 539 秒；分类器选参、拟合及评价约 4.44 秒。没有外部 API 调用、GPU 使用或模型权重下载。完整环境版本、逐题分数、内部分组和参数候选均保存在实验目录。

这是此前已使用过的开发验证集，跨系统仅 9 题；100% 是该集合的系统路由成绩，不能推算外部 113 道联邦题或 680 题的 SQL 执行成绩。下游硬过滤及需求验收等问题仍需独立处理。

接口依据：[scikit-learn 多标签分类](https://scikit-learn.org/stable/modules/multiclass.html#multilabel-classification)、[分层分组交叉验证](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.StratifiedGroupKFold.html)。
