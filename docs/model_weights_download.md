# 本地 8B 模型下载记录

2026-10-15：两个原始模型的权重已在本地和GPU服务器完成下载，全部 Git LFS 文件的大小和 SHA256 与克隆版本记录一致。真实模型测试与标注对比结果见 [GPU评估报告](gpu_evaluation.md)。

| 模型 | V6 默认引用路径 | LFS 文件数 | 下载大小（GB） | 校验 |
| --- | --- | ---: | ---: | --- |
| Qwen/Qwen3-Embedding-8B | `../models/Qwen3-Embedding-8B` | 5 | 15.146 | SHA256 一致 |
| Qwen/Qwen3-Reranker-8B | `../models/Qwen3-Reranker-8B` | 6 | 16.389 | SHA256 一致 |

合计 11 个 LFS 文件（9 个权重分片和 2 个 tokenizer.json），共 31,534,622,441 字节，约 31.535 GB。没有替换为小模型或量化版本。

模型修订、预期大小和 SHA256 见 [model_weights_manifest.json](model_weights_manifest.json)。逐文件实际校验记录保存在共享目录 `../models/download-verification.json`。校验工具 `scripts/verify_model_weights.py` 只读取和核对文件，不加载模型。

V6 的 Settings 和 .env.example 已引用上述共享目录。`tests/test_local_models.py` 为真实模型集成测试入口，默认跳过，只有进程环境显式设置 T2Q_RUN_MODEL_TESTS=1 才执行；测试分阶段加载 embedding 和 reranker，释放前一个模型后再进入下一阶段。GPU集成测试已通过，独立排序评估同时保留两个模型。

本地 V6/.venv 用于下载；真实推理在用户提供的48GB GPU服务器上运行，使用独立测试环境和BF16精度。服务器端校验记录见评估结果目录的 `execution/weights-verification.json`。

人工＋LLM reference-v1 对应旧版247条知识、72张表和270个接受配对；当前知识为1833条。已分别评估旧版完整基准和新版原文未变的173条知识、155个接受配对；改写与新增知识保持未标注，不能将旧基准直接作为新版全量真值。
