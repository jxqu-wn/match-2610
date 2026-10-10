# 训练集与验证集划分

原始数据：`../QA_train.json`，共 5830 条。

- 训练集：[train.json](train.json)，5247 条，占 90%。
- 验证集：[validation.json](validation.json)，583 条，占 10%。
- 划分清单：[split_manifest.json](split_manifest.json)，记录随机种子、原始文件 SHA-256、各层样本数及输出文件 SHA-256。

## 分层方式

按样本的数据源分层：单源查询使用 `db`，跨源查询使用有顺序的 `db1 -> db2`。因此两种跨源查询方向分别抽样。

| 分层 | 原始样本 | 训练集 | 验证集 |
| --- | ---: | ---: | ---: |
| Elasticsearch | 370 | 333 | 37 |
| MYSQL | 1969 | 1772 | 197 |
| MYSQL -> POSTGRESQL | 50 | 45 | 5 |
| POSTGRESQL | 410 | 369 | 41 |
| POSTGRESQL -> MYSQL | 40 | 36 | 4 |
| SQLite | 2991 | 2692 | 299 |
| 合计 | 5830 | 5247 | 583 |

采用最大余数法分配各层验证样本数，保证验证集总数为 583；各层使用固定随机种子 `42` 随机选取样本。原始数据、问题 ID 及各字段完整保留，输出按原始数据的顺序排列。

训练集与验证集的 `question_id` 不重叠，二者合并后覆盖原始训练集全部样本。划分单位为单条样本。

## 复现

在项目根目录运行：

```bash
python scripts/split_dataset.py
```

同一输入及随机种子生成相同文件。脚本支持通过 `--input`、`--output-dir`、`--validation-ratio` 和 `--seed` 调整参数。

示例：

```bash
python scripts/split_dataset.py --validation-ratio 0.1 --seed 42
```
