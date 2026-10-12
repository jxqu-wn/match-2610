# 历史实验结果

本目录保留旧手写实现（原 `scripts/`）产出的实验记录与设计结论，作为可追溯的历史资料。
当前实现已迁移到 [`src/text2query`](../../src/text2query) 并改用社区框架，命令与文件路径
已在根目录 [README](../../README.md) 中更新。

- `database_routing/`：字符线性分类器与 Qwen embedding 路由实验结果。
- `information_retrieval/`：库表召回设计、20/50/200 题真实模型测试、优化与回退对照。
- `data_preprocessing/`：schema 描述校验与人工抽查结论。
- `finetuned_inference/`：微调模型推理流程说明。

这些记录中的准确率、token 消耗与结论由旧实现产生，未在框架化重写后重新运行；
重写版本在结构与证据处理上保持一致，但数值不作为新实现的复现结果。
