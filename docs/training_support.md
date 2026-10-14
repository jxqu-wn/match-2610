# 可插拔训练数据增强

训练问题与SQL的增强逻辑独立位于 `src/text2query/data/training_support.py`。基础关联器不导入该模块、不读取训练文件，仅读原始Schema和知识；模块输出可审计弱证据，通过 `AssociationSupport` 接口接入。

## 流程开关

从项目根目录执行：

```bash
# 显式启用；训练文件不存在时明确报错
PYTHONPATH=src .venv/bin/python -B -m text2query.cli build-catalog --training-support sql

# 完全禁用；不读取训练数据，也不导入训练增强模块
T2Q_PREPROCESSED_DIR=data/preprocessed/schema-only PYTHONPATH=src .venv/bin/python -B -m text2query.cli build-catalog --training-support none

# 默认auto：训练文件存在则启用，缺失时仅使用Schema和知识
PYTHONPATH=src .venv/bin/python -B -m text2query.cli build-catalog --training-support auto

# 使用其他格式兼容的原始训练文件
PYTHONPATH=src .venv/bin/python -B -m text2query.cli build-catalog --training-support sql --training-source data/赛题8/splits/train.json
```

默认训练来源为已生成的训练划分，不会自动回退到完整QA_train或验证文件。传入自定义data_dir时，默认训练路径跟随该数据目录，避免读取另一任务的训练集。auto适合日常使用，正式实验建议显式指定sql或none。

关闭模块后不保留上次增强的knowledge关联或training_examples；需要重新运行构建，使旧产物被基础模式结果替换。模式、训练文件哈希、字段用途、分数及证据记录在 `knowledge_association_audit.json`；模块审计另存 `training_support_audit.json`，禁用时明确保存provider=none，避免旧记录混用。

开关控制预处理中的训练增强和训练案例附挂。现有路由训练、检索案例索引等其他阶段原有的训练数据依赖不随此开关自动取消；未来无训练集任务可独立使用基础预处理。

## 独立调用与移除

```python
from text2query.data.association import associate
from text2query.data.training_support import TrainingSQLSupport

# catalog、knowledge、train_rows由调用方提供，不在模块内部读取文件。
provider = TrainingSQLSupport(catalog, train_rows)
associate(catalog, knowledge, support=provider)

# 剔除增强，重新生成基础结果；没有训练增强对基础词频统计的残留。
associate(catalog, knowledge, support=None)
```

独立模块没有文件、网络、LLM或答案读取。也可实现 `association_support.py` 中的协议，将其他训练数据格式的适配器接入；无需更改基础匹配算法。

## 提取和评分

- SQLGlot解析SQL和作用域，SourceResolver将真实表绑定到catalog。
- 解析具名字段在输出、计算、过滤、HAVING、分组、排序及JOIN中的用途；可定位的CTE、别名和相关子查询追溯到原始字段。
- JOIN ON及WHERE中的跨表字段等值连接仅作为连接证据，默认不用于增强业务关联。
- COUNT(*)仅在当前作用域有唯一物理表时提供行数证据；不猜多表JOIN后的统计对象。
- ES DSL在索引唯一时，按原始字段键提取过滤、排序、输出及聚合用途；多索引无法唯一确定时记录问题。
- 原始问题和知识文本使用共享字符2–4gram、英文标识符；支持本地TF-IDF或BM25。按字段用途降低只承担输出、分组、排序的辅助表权重。
- TF-IDF模式还从至少两个不同问题的实际字段使用中构建字段问题向量，保存样本ID；BM25模式使用直接问题证据，不混入TF-IDF字段向量。
- 当前通用角色权重：计算1.0，过滤/HAVING 0.9，输出0.65，排序0.5，分组0.4，JOIN 0。增强总权重0.75，可通过provider配置修改；没有按业务、表ID或知识ID的白名单。

基础语料的IDF和基础分数不受训练模块启停影响。增强分数单独计算，与基础分组合；有明确其他表引用时沿用现有降权规则。不会改写Schema、字段描述或知识原文。接入不代表知识已被人工或程序证明正确。

## 验证与效果

合成测试覆盖JOIN辅助表、CTE、相关/隐式JOIN、歧义字段、非法SQL、COUNT(*)、DSL、禁用后移除、缺训练文件、跨任务数据隔离、文件/网络隔离及两种评分后端。

使用相同修复后Schema、知识和答案，固定阈值0.30，逐表核对所有候选的基础分数完全一致：

| 指标 | 不启用训练增强 | 启用训练SQL增强 |
| --- | ---: | ---: |
| 程序关联数 | 209 | 241 |
| 命中 / 多关联 / 漏关联 | 177 / 32 / 93 | 195 / 46 / 75 |
| Precision | 84.69% | 80.91% |
| Recall | 65.56% | 72.22% |
| F1 | 73.90% | 76.32% |
| 非空答案表完全覆盖 | 22/44（50%） | 22/44（50%） |
| 整体无关/有效 | 18.08% | 23.59% |
| 超过200%噪声目标的表数 | 5 | 3 |

训练增强提高了关联级召回和F1，但精度下降，完全覆盖表数没有提升；仍有3张表未达到逐表噪声目标。结果是当前答案集开发评估，不保证泛化。当前训练记录有230份解析/字段定位问题报告，均保留在审计中，不为无法定位的字段编造证据。

结果分别位于 `evaluation/table_knowledge/runs/training-support-none-v1/` 与 `training-support-sql-v1/`。重新评估使用新目录，不覆盖历史结果：

```bash
.venv/bin/python -B evaluation/table_knowledge/evaluate_preprocessing.py --training-support none --output-dir /tmp/table-knowledge-no-training-new
.venv/bin/python -B evaluation/table_knowledge/evaluate_preprocessing.py --training-support sql --output-dir /tmp/table-knowledge-training-new
```

none评估入口也不读取QA_train或创建划分；sql评估入口仅在临时目录生成固定训练划分，答案仅在程序产物生成后用于评价。禁止凭反复调整阈值或添加业务例外追求答案拟合。
