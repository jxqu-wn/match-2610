# 2026 全国大数据与计算智能挑战赛 · 赛题 8

**面向多源异构数据源的统一查询指令生成**（Text-to-Query）。

V5 基于 `rewrite/framework-based`，当前工作分支为 `rewrite/v5`。
保留社区框架实现，准备逐步梳理数据库路由、库表召回、LLM 规划与查询生成。
旧实验中间文件、结果及报告已清空，后续按[流程与测试清单](docs/workflow.md)重新运行。
预处理禁止添加人工或大模型提供的额外业务理解，具体约束见 [AGENTS.md](AGENTS.md)。

## 赛题要点

- **输入**：用户自然语言问题，不指定数据源或数据库。
- **当前数据范围**：MySQL、PostgreSQL、Elasticsearch；已移除 SQLite 样本、Schema 和相关知识。
- **输出**：MySQL 的 SQL、PostgreSQL 的时空查询、Elasticsearch 的查询 DSL，
  以及跨数据源联邦查询计划（第二步以 `result` 代替第一步结果）。
- **评测**：查询语句加权执行准确率；ES 查询按 `0.5 × id_match + 0.5 × order_match` 计分。
- 模型限制：国产开源基座、总参数量不超过 30B、权重总大小不超过 40GB。

资料索引见 [`docs/赛题8/网页资料/README.md`](docs/赛题8/网页资料/README.md)，
库表召回设计见 [`docs/赛题8/库表信息召回设计说明.md`](docs/赛题8/库表信息召回设计说明.md)。
官方资料描述原始完整赛题，当前子集的范围以本文和数据清单为准。

## 目录结构

```
src/text2query/
  config.py            集中配置（pydantic-settings）
  models.py            schema/规划协议的数据模型（pydantic）
  data/
    split.py           分层数据划分（scikit-learn）
    catalog.py         schema 目录解析（sqlglot）+ 知识/案例关联
    enrich.py          LLM 描述校验与补充（openai + tenacity + diskcache）
    review.py          人工抽查 / 二次复核回放
  routing/
    embedding.py       sentence-transformers 语义向量 + 向量缓存
    classifier.py      路由分类器（scikit-learn）+ 字符 TF-IDF 对照
  retrieval/
    sql_parser.py      SQL / DSL 解析（sqlglot）
    index.py           BM25 + FAISS + RRF 混合召回
    context.py         配额、一跳外键扩展、预算裁剪
    evaluate.py        表级召回评估
  llm/
    client.py          OpenAI 兼容客户端（重试 / 用量 / 可选缓存）
    planner.py         有界规划协议与结构校验
  submission/
    validate.py        SQL / DSL / 跨源协议静态校验（sqlglot）
    generate.py        DeepSeek 端到端生成 result.json
    finetuned.py       微调模型（OpenAI 兼容服务）推理
  cli.py               typer 命令行入口
tests/                 pytest 测试（从原始输入在临时目录构建所需产物）
docs/workflow.md       从头梳理流程的顺序、输入输出与测试边界
```

## 安装

```bash
uv venv .venv --python 3.14
uv pip install -e '.[dev]'
```

语义向量依赖本地 Qwen3-Embedding-0.6B（默认 `models/Qwen3-Embedding-0.6B`）。
LLM 通过环境变量 `DEEPSEEK_API_KEY` 提供，密钥不写入代码或产物。

## 框架选型

| 环节 | 框架 | 替代的原手写实现 |
| --- | --- | --- |
| 数据划分 | scikit-learn `train_test_split` | 手写最大余数法 + `random.shuffle` |
| DDL 解析 | sqlglot tokenizer + AST | 手写括号平衡 / 列切分 / 正则 |
| 语义向量 | sentence-transformers | 手写 transformers 池化与缓存 |
| 向量检索 | faiss `IndexFlatIP` | numpy 全量点积 |
| 关键词检索 | rank-bm25 `BM25Okapi` | 手写 BM25 |
| 分类器 | scikit-learn KNN / LogisticRegression | 手写感知机与 NB |
| 模型持久化 | joblib | 手写 `npz` 系数 |
| 数据模型 | pydantic v2 | 裸 dict 校验 |
| LLM 调用 | openai SDK + tenacity + diskcache | 手写 urllib 重试与缓存 |
| 配置 | pydantic-settings | argparse + 常量 |
| 命令行 | typer + rich | argparse |
| 测试 | pytest | unittest |

## 使用

```bash
# 0) 从过滤后的原始训练集重新划分
text2query split-dataset

# 1) 解析原始 Schema，生成基础目录和检索文档
text2query build-catalog

# 预处理仅保留原始资料与可验证引用，不运行模型补写或复核回放

# 2) 数据库路由
text2query route-evaluate --device cuda --dtype float16
text2query route-predict --question '统计船舶总数' --device cuda

# 3) 库表召回（关键词模式无需模型）
text2query build-index --device cuda --dtype float16
text2query retrieve --engines MYSQL --question '统计各公司驾驶员中女性驾驶员的比例'
text2query evaluate-retrieval --device cuda

# 4) 有界规划
text2query plan --engines MYSQL --question '统计各公司驾驶员中女性驾驶员的比例'

# 5) 生成提交
text2query generate-submission --workers 8
text2query finetuned-submission --endpoint http://127.0.0.1:8000/v1/chat/completions
```

未安装包时可用 `PYTHONPATH=src python -m text2query.cli <command>`。

## 数据与划分

| 输入 | 当前规模 | 本轮移除 |
| --- | ---: | ---: |
| `data/赛题8/QA_train.json` | 2,839 | 2,991 条 SQLite 样本 |
| `data/赛题8/QA_test.json` | 200 | 200 条 SQLite 问题 |
| `data/赛题8/knowledge.json` | 247 | 1,553 条引用 BIRD 数据库的知识 |
| 原始 Schema | 72 张表/索引 | 23 个 BIRD 数据库的 193 张表 |

保留记录的 ID、顺序、问题、查询及其余字段不变。清理依据、删除 ID 和文件 SHA-256
记录在 [`dataset_manifest.json`](data/赛题8/dataset_manifest.json)。
测试集本身无数据源标签：按原始编号区间 3040–6230 识别 SQLite 题，并与已有 SQLite 子集交叉核对。
该规则仅用于本次固定数据清理，不作为模型推理或未来数据分类规则。

旧 `splits/*.json` 已删除。重新运行 `split-dataset` 将使用种子 42、按数据源分层，
生成训练集 2,555 条和验证集 284 条；跨源查询按有序 `db1 -> db2` 分层。
新划分由 scikit-learn 生成，成员与旧划分可能不同；已有文件默认拒绝覆盖，需显式 `--overwrite`。

`build-catalog` 解析 `commom_schema.txt` 和 `core_schema.txt`，从本轮训练划分关联案例，
在 `data/preprocessed/` 生成 `schema_extracted.json`、`schema_catalog.json` 和 `schema_documents.jsonl`。
这些基础描述仅来自原始 Schema 和知识，后续不得用人工或模型生成的业务解释替换。
当前 table–knowledge 关联的覆盖与误关联风险见[关联审计](docs/knowledge_association_audit.md)。
划分、预处理、索引、缓存和提交结果均为本地生成文件，已加入 `.gitignore`。

## 测试

```bash
python -m pytest -q -p no:cacheprovider
```

测试自动在临时目录重建划分、Schema 目录和关键词索引，不依赖旧产物，
不调用模型服务。当前覆盖输入范围与哈希、数据划分、Schema 提取、检索隔离、
上下文预算、规划协议和提交静态校验；后续流程梳理中逐步补充测试。

## 约束与边界

- 程序负责可重复的结构化工作与执行边界；LLM 负责业务判断，两者证据分离。
- 相似度、外键存在、训练案例命中都不构成业务正确性证明。
- 不根据字段同名建立关联；推断关系必须显式标记为假设。
- 上下文超限时整条移除低优先级证据，绝不静默截断单表结构。
- 静态校验只检查语法、库表字段与跨源协议，不代表执行结果正确。
