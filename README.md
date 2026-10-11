# 2026 全国大数据与计算智能挑战赛 · 赛题 8

赛题：面向多源异构数据源的统一查询指令生成。

## 资料

- [网页资料索引](docs/赛题8/网页资料/README.md)
- [赛题网页合集](docs/赛题8/网页资料/赛题网页合集.md)
- [训练集与验证集划分说明](data/赛题8/splits/README.md)

## 数据划分

原始训练集为 `data/赛题8/QA_train.json`。按验证集 10%、训练集 90%划分，使用固定随机种子 `42`，按单数据源类型及跨数据源查询方向分层抽样。

在项目根目录运行：

```bash
python scripts/split_dataset.py
```

脚本仅依赖 Python 标准库，生成训练集 `data/赛题8/splits/train.json`、验证集 `data/赛题8/splits/validation.json` 和划分清单 `data/赛题8/splits/split_manifest.json`。

模型训练和训练样例检索使用划分后的 `train.json`；`validation.json` 用于本地验证。官方 `QA_test.json` 用于竞赛预测。

## 数据库路由基线

```bash
python scripts/database_routing/route_question.py '哪个国家培养的冰球运动员最多？请标明哪一年出生的冰球运动员最多。' --question-id 5635
python -m unittest discover -s scripts/database_routing -p 'test_route_question.py'
```

脚本只依赖标准库，解析三个 schema 文件构建表与数据库系统目录，使用字符二元组 TF-IDF 检索 `splits/train.json` 中的相似问题，再从 `knowledge.json` 提取候选表的知识证据。数据库系统映射依据 `data/数据库说明及行政区划表数据/数据库说明.txt`：BIRD 为 SQLite，通用及其他业务库为 MYSQL，船舶为 POSTGRESQL，医疗为 Elasticsearch。

输出包含 `query_type`（single/multi/unknown）、`databases`、候选表和字段、知识证据及相似训练问题。检索分数低于 0.45 或未匹配到 schema 表时，返回 unknown；该阈值是初始经验值，分数不是正确率或概率。多类标签按涉及的数据库系统去重计算，同系统多个业务库仍为单类。

这是可运行的检索基线，数据库选择主要来自最相似训练样例，尚未实现模型驱动的需求拆解、字段覆盖验证、跨库执行计划或 SQL 生成。候选表也是从相似样例查询提取，可能包含当前问题不需要的表。不会读取验证集和测试集标签；示例原题本身在训练子集中，原题命中不能证明泛化能力。后续应在 validation.json 上评估路由准确率和多类召回率，再接入查询计划模块。

## Embedding 分类器

分类代码已统一整理至 [scripts/database_routing](scripts/database_routing/README.md)，包含原检索基线、字符线性分类器和基于本地 Qwen3-Embedding-0.6B 的分类器。

```bash
.venv/bin/python scripts/database_routing/embedding_classifier.py evaluate --int8
.venv/bin/python scripts/database_routing/embedding_classifier.py predict --int8 --question '哪个国家培养的冰球运动员最多？请标明哪一年出生的冰球运动员最多。'
.venv/bin/python -m unittest discover -s scripts/database_routing -p 'test_*.py'
```

Embedding 分类器在训练集内部选择近邻或逻辑回归，独立验证时排除训练集中的同文本问题。向量缓存、模型系数、逐题结果和评估指标保存至 `outputs/database_routing/embedding`。详细安装方法及评估边界见分类目录说明。

## Git

Schema 结构提取、DeepSeek 描述校验和补充见 [数据预处理脚本](scripts/data_preprocessing/README.md)。产物位于 `data/preprocessed`，人工抽查结论随产物保存。

远程仓库：<https://github.com/jxqu-wn/match-2610.git>

## 库表信息召回

数据库分类之后的混合召回和有界库表规划见 [scripts/information_retrieval/README.md](scripts/information_retrieval/README.md)。支持完整 schema、知识与训练案例索引、按系统过滤、GPU embedding、一次补检索、结构校验及预算控制。实测指标与待改进项见 [RESULTS.md](scripts/information_retrieval/RESULTS.md)；DeepSeek 已完成20题真实测试，token消耗与预算建议见 [LIVE20_RESULTS.md](scripts/information_retrieval/LIVE20_RESULTS.md)。

召回优化后的同20题对比、schema保护和token成本说明见 [OPTIMIZATION_RESULTS.md](scripts/information_retrieval/OPTIMIZATION_RESULTS.md)。

全新50题的完全一致率、语义一致率及验证隔离审计见 [LIVE50_RESULTS.md](scripts/information_retrieval/LIVE50_RESULTS.md)。
