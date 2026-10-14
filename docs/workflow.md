# V5 流程与测试清单

本轮先清理数据和旧产物。接下来按顺序确认每个阶段的输入、输出、实现与测试，
每一步通过后再运行下一步。已有算法和模型策略仍需逐项梳理。

后续修改遵守根目录 `AGENTS.md` 与[新预处理规范](preprocessing_rules.md)：table–knowledge 关联以当前 LLM＋人工审核结果为理想基准，允许已审核的 Schema 支持关系与部分适用片段。原始结构和知识原文保留，冲突采用 Schema；缺失内容不凭常识补齐。
table–knowledge 当前实现及待修复问题见[关联审计](knowledge_association_audit.md)。

## 当前起点

- 原始输入只保留 MySQL、PostgreSQL、Elasticsearch：2,839 条训练问答、200 条无标签测试问题、247 条知识、72 张表/索引。
- SQLite 样本、BIRD Schema 和明确引用 BIRD 数据库的知识已移除；原始 ID、保留记录内容和顺序不变。
- 旧划分、Schema 提取、模型描述、人工复核、索引、缓存、实验结果、提交文件及历史实验报告已清空。
- 测试所需的派生数据在临时目录重新生成，V5 工作目录不预先保留运行产物。
- 清理来源及删除 ID 见 `data/赛题8/dataset_manifest.json`；原始完整文件可在其记录的 Git 提交中查看。

## 梳理顺序

| 顺序 | 环节与主要代码 | 输入 → 输出 | 测试与待确认项 |
| --- | --- | --- | --- |
| 1 | 数据加载与划分：`models.Sample`、`data/split.py` | `QA_train.json` → 2,555 条训练 / 284 条验证及划分清单 | ID 唯一、字段保真、分层规模、跨源方向、成员互斥、固定种子、覆盖保护 |
| 2 | Schema 提取：`data/catalog.py` | 两份 Schema + 知识 + 训练划分 → 基础目录与文档 | 72 张表/索引、主外键、字段描述来源、无 SQLite、干净目录可重建 |
| 3 | 原始描述来源与关联审计 | 原始注释、知识原文及引用 → 可追溯目录 | 原文与结构保真；用 `evaluation/table_knowledge/runs/reference-v1/` 验收关联，算法仅读原始输入、基准只用于离线评价；不回放无关旧描述与复核 |
| 4 | 数据库路由：`routing/classifier.py`、`routing/embedding.py` | 训练划分 → 路由模型；问题 → 数据源集合 | 待梳理训练与选参边界、跨源分类、向量缓存失效、验证标签隔离 |
| 5 | 索引与召回：`retrieval/index.py`、`sql_parser.py` | 目录 + 知识 + 训练划分 → 索引 → 候选证据 | 已检查训练案例集合与验证 ID 隔离；后续补齐召回质量、缓存失效、知识归属测试 |
| 6 | 上下文与规划：`retrieval/context.py`、`llm/planner.py` | 候选证据 → 有界规划 | 已有来源、预算与协议检查；后续梳理补检索、停止条件、无新增证据、模型异常 |
| 7 | 查询生成与提交：`submission/` | 问题 + 规划 → SQL/DSL/跨源计划 → 提交 | 已有静态校验回归；后续补齐生成失败、续跑与缓存一致性、完整覆盖、执行验证 |

现有 `experiments/` 源代码保留供梳理时参考，其中 SQLite 专用实验不适用于当前数据范围。
本轮没有调用远程模型，没有运行训练或生成新提交；单元测试通过不能证明实际查询执行正确。

## 从头运行的前两步

在 V5 项目根目录、安装项目依赖后执行：

```bash
text2query split-dataset
text2query build-catalog
```

第一步生成 `data/赛题8/splits/` 下的划分 JSON；第二步生成 `data/preprocessed/` 下的基础目录。
`build-catalog` 会重置基础目录。构建命令使用纯程序关联算法；审核基准仅用于独立评估，不进入生产匹配。预处理同时生成 knowledge_association_audit.json。旧模型描述补充和人工复核回放不属于此流程。
路由、索引、规划和提交在逐步确认后再运行。

## 测试入口

```bash
# 原始输入与数据划分
python -m pytest tests/test_dataset.py tests/test_split.py -q -p no:cacheprovider

# 全部离线回归
python -m pytest -q -p no:cacheprovider
```

测试夹具先把派生数据目录改为临时目录，再重新划分、解析和构建索引。
测试不读取旧实验文件，不调用模型服务，也不向 V5 写入这些中间文件。
