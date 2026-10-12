# 本地分类测试结果

## GPU 环境与测试（2026-10-11）

项目 .venv 已由 CPU 版替换为 torch 2.14.1+cu130（CUDA runtime 13.0），Python 3.14.7，其余直接依赖版本保持不变。GPU 为 RTX 4060 8 GB，驱动 615.71.09，驱动报告 CUDA 13.3；CUDA 可用，支持 BF16。`uv pip check` 通过，11 项单元测试通过。本环境沙箱屏蔽 GPU 访问，真实 GPU 测试在沙箱外执行。

使用 `--device cuda:0 --dtype float16 --batch-size 16`，独立输出目录 `outputs/database_routing/embedding_gpu`。5761 条去重问题编码约 27.9 秒（包含周期缓存保存，不含模型加载及分类器训练）。训练数据仍为 5235 题，验证 583 题；内部开发集选择逻辑回归 C=10。

| 指标 | GPU FP16 Embedding + 逻辑回归 |
|---|---:|
| 数据库集合完全匹配 | 582/583，99.83% |
| 单类/多类分类 | 583/583，100% |
| MYSQL + POSTGRESQL | 9/9 |

唯一错误为 question_id=220：“查询所有货船（vessel_type=70）的MMSI和最大载重”，标注 MYSQL，预测 POSTGRESQL。原字符分类器在相同数据上仍为 583/583。GPU FP16 与原 CPU int8 的精度、开发集选定 C 均不同，不能把指标差异单独归因于 GPU。

真实 GPU BF16 测试覆盖 auto 选卡、不同长度的两条问题、模型位于 cuda:0、有限且 L2 归一化的 float32 输出（2×1024）、缓存重载后无需加载模型。冰球原题通过 GPU 分类器预测为 single / SQLite；该原题在训练集中，仅用于检查预测入口。

结果：[完整指标](../../outputs/database_routing/embedding_gpu/summary.json)、[错误题](../../outputs/database_routing/embedding_gpu/errors.json)、[日志](../../outputs/database_routing/embedding_gpu/evaluation.log)、[环境版本](../../outputs/database_routing/embedding_gpu/environment.txt)。以下保留原 CPU 实验记录。

测试日期：2026-10-11。使用 CPU、动态 int8 的 Qwen3-Embedding-0.6B。模型冻结，1024 维、最后有效 token 池化、L2 归一化。最大输入长度 256；数据检查最长 149，没有截断。

## 数据隔离

使用已有 train/validation 划分。排除训练中与验证问题完全同文本的记录后，训练 5235 题，验证 583 题。内部开发集 523 题，拟合 4703 题，额外排除内部开发集同文本训练记录。只用内部开发集选择近邻 k 或逻辑回归 C；验证标签仅用于计算指标。

开发集最优方案为逻辑回归 C=100，准确率 99.04%。随后在全部 5235 条有效训练记录上拟合最终分类器。近邻、其他 C 值的开发集结果保存在 summary.json。

## 独立验证

| 指标 | Embedding + 逻辑回归 | 原字符线性分类器 |
|---|---:|---:|
| 数据库集合完全匹配 | 577/583，98.97% | 583/583，100% |
| 单类/多类分类 | 579/583，99.31% | 583/583，100% |
| Elasticsearch | 37/37 | 37/37 |
| MYSQL | 195/197 | 197/197 |
| POSTGRESQL | 40/41 | 41/41 |
| SQLite | 299/299 | 299/299 |
| MYSQL + POSTGRESQL | 6/9 | 9/9 |

本次 embedding 方案未超过字符方案，不能认为语义向量必然提高路由准确率。跨库问题容易被 AIS 语义主导，漏掉公司、最大荷载量等对应的 MYSQL 需求；另有静态/动态船舶混淆，以及公司领域混淆。量化可能影响结果，但未进行全精度对照，不能把错误归因于量化。

两种方法均只是问题到数据库集合的闭集分类，未验证全部数据需求的覆盖、具体表或 SQL。随机划分中的相近模板也限制了指标对新问题的代表性。

## 程序检查

9 项单元测试全部通过，覆盖原路由功能、内部划分去重、多库标签、指标区别、向量缓存复用及参数变更后的缓存失效。真实模型加载和编码通过；缓存向量均为 1024 维且数值有限，归一化误差约 1.8e-7。冰球示例通过独立预测入口输出 single / SQLite。

## 本地结果文件

- [完整指标](../../outputs/database_routing/embedding/summary.json)
- [逐题预测](../../outputs/database_routing/embedding/predictions.json)
- [6 道错误题](../../outputs/database_routing/embedding/errors.json)
- [执行日志](../../outputs/database_routing/embedding/evaluation.log)
- [依赖版本](../../outputs/database_routing/embedding/environment.txt)
- [输入长度检查](../../outputs/database_routing/embedding/token_length_audit.json)

输出目录在 .gitignore 中，不随代码提交；执行 README 中的 evaluate 命令可重新生成。已有向量缓存会复用，不必再次进行完整编码。
