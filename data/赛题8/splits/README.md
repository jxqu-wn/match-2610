# 训练集与验证集划分

原始数据：`../QA_train.json`，移除 SQLite 后共 2,839 条。

- `train.json`：重新生成后 2,555 条。
- `validation.json`：重新生成后 284 条。
- `split_manifest.json`：生成时记录随机种子、原始文件 SHA-256、各层样本数及输出文件 SHA-256。

旧划分文件已清空，以上三个文件不提交版本库；运行划分命令后生成。

## 分层方式

按样本的数据源分层：单源查询使用 `db`，跨源查询使用有顺序的 `db1 -> db2`。因此两种跨源查询方向分别抽样。

| 分层 | 原始样本 | 训练集 | 验证集 |
| --- | ---: | ---: | ---: |
| Elasticsearch | 370 | 333 | 37 |
| MYSQL | 1969 | 1772 | 197 |
| MYSQL -> POSTGRESQL | 50 | 45 | 5 |
| POSTGRESQL | 410 | 369 | 41 |
| POSTGRESQL -> MYSQL | 40 | 36 | 4 |
| 合计 | 2839 | 2555 | 284 |

使用 scikit-learn 的分层划分分配各层配额，验证集总数为 284；随机种子为 `42`。
原始问题 ID 及各字段完整保留，输出按原始数据的顺序排列。

训练集与验证集的 `question_id` 不重叠，二者合并后覆盖原始训练集全部样本。划分单位为单条样本。

## 复现

在项目根目录运行：

```bash
text2query split-dataset
```

划分使用 scikit-learn 的 `train_test_split`（分层、近似最大余数法），同一输入及随机种子生成相同文件。脚本支持 `--input`、`--output-dir`、`--validation-ratio` 和 `--seed` 调整参数。

为防止运行中途意外改变实验基准，默认拒绝覆盖已存在的划分文件；需要重新划分时显式使用 `--overwrite`。

示例：

```bash
text2query split-dataset --validation-ratio 0.1 --seed 42 --overwrite
```
