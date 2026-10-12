# 2026 全国大数据与计算智能挑战赛 · 赛题 8

**面向多源异构数据源的统一查询指令生成**（Text-to-Query）。

本仓库基于社区成熟框架重构了赛题解决方案：数据库路由、库表召回、有界 LLM 规划与
查询指令生成。原始手写实现已由 `src/text2query` 下的框架化实现替换，
历史实验记录保留在 [`docs/results`](docs/results)。

## 赛题要点

- **输入**：用户自然语言问题，不指定数据源或数据库。
- **输出**：MySQL / SQLite 的 SQL、PostgreSQL 的时空查询、Elasticsearch 的查询 DSL，
  以及跨数据源联邦查询计划（第二步以 `result` 代替第一步结果）。
- **评测**：查询语句加权执行准确率；ES 查询按 `0.5 × id_match + 0.5 × order_match` 计分。
- 模型限制：国产开源基座、总参数量不超过 30B、权重总大小不超过 40GB。

资料索引见 [`docs/赛题8/网页资料/README.md`](docs/赛题8/网页资料/README.md)，
库表召回设计见 [`docs/赛题8/库表信息召回设计说明.md`](docs/赛题8/库表信息召回设计说明.md)。

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
tests/                 pytest 测试
docs/results/          历史实验结果（旧实现产出）
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
# 0) 数据划分（划分文件已冻结，重新划分需显式 --overwrite）
text2query split-dataset

# 1) schema 目录与描述
text2query build-catalog
text2query enrich-descriptions --workers 4        # 需要 DEEPSEEK_API_KEY
text2query apply-review

# 2) 数据库路由
text2query route-evaluate --device cuda --dtype float16
text2query route-predict --question '统计船舶总数' --device cuda

# 3) 库表召回（关键词模式无需模型）
text2query build-index --device cuda --dtype float16
text2query retrieve --engines SQLite --question '哪个国家培养的冰球运动员最多？'
text2query evaluate-retrieval --device cuda

# 4) 有界规划
text2query plan --engines MYSQL --question '统计各公司驾驶员中女性驾驶员的比例'

# 5) 生成提交
text2query generate-submission --workers 8
text2query finetuned-submission --endpoint http://127.0.0.1:8000/v1/chat/completions
```

未安装包时可用 `PYTHONPATH=src python -m text2query.cli <command>`。

## 数据与划分

原始训练集 `data/赛题8/QA_train.json`（5830 条）按数据源分层划分为训练集 5247 条、
验证集 583 条（种子 42）。跨源查询按有序 `db1 -> db2` 分层，两个方向分别抽样。
分层规模与已冻结的 [`split_manifest.json`](data/赛题8/splits/split_manifest.json) 完全一致。

`split-dataset` 使用 scikit-learn 重新划分时会生成**同规模、同分层但成员不同**的划分，
因此默认拒绝覆盖已冻结文件；确认要更换基准时使用 `--overwrite`。

Schema 预处理产物位于 `data/preprocessed`。`build-catalog` 用 sqlglot 重新解析
`bird_schemas.txt` / `commom_schema.txt` / `core_schema.txt`，产出的表、字段、主外键
与描述与已提交的 `schema_extracted.json` 逐项一致。

## 约束与边界

- 程序负责可重复的结构化工作与执行边界；LLM 负责业务判断，两者证据分离。
- 相似度、外键存在、训练案例命中都不构成业务正确性证明。
- 不根据字段同名建立关联；推断关系必须显式标记为假设。
- 上下文超限时整条移除低优先级证据，绝不静默截断单表结构。
- 静态校验只检查语法、库表字段与跨源协议，不代表执行结果正确。
