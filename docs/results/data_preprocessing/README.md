# Schema 数据预处理

脚本仅依赖 Python 标准库，输出默认保存在 `data/preprocessed`。源文件保持不变。

## 运行

```bash
python scripts/data_preprocessing/build_catalog.py
# 在终端安全输入 API key，不会进入 shell 历史或代码文件。
read -rs -p 'DeepSeek API key: ' DEEPSEEK_API_KEY
export DEEPSEEK_API_KEY
python scripts/data_preprocessing/enrich_descriptions.py --workers 4
unset DEEPSEEK_API_KEY
# 本次抽查记录已提供；模型生成结束后应用修订。
python scripts/data_preprocessing/apply_review.py
python -m unittest discover -s scripts/data_preprocessing -p 'test_*.py'
```

模型使用 `deepseek-flash`，非思考模式，JSON 输出。每张表一次请求，支持重试和按内容哈希缓存；成功结果缓存于被 Git 忽略的 `outputs/data_preprocessing/api_cache`，失败后重跑无需重复处理已成功表。`--limit` 用于试运行，生成的 catalog 会标记 partial，不能作为全量结果使用。

已有完整缓存时可用 `python scripts/data_preprocessing/enrich_descriptions.py --offline` 重建模型结果，无需 API key，也不会发送请求。随后运行 apply_review.py 恢复抽查修订。复用旧审查记录时会检查修订前描述；新数据或模型输出不匹配时停止，避免套用过期修订。

## 输出

| 文件 | 内容 |
|---|---|
| schema_extracted.json | DDL 结构、已有注释、知识描述、知识原文、最多四条相关训练案例及来源 |
| schema_catalog.json | 完整结构及模型校验/补充的描述，保留 extracted_description 和审查记录 |
| schema_documents.jsonl | 按表/索引组织的检索文本，支持先按 engine 过滤 |
| enrichment_report.json | 完成数、失败列表、调用 usage 和缓存复用记录 |
| manual_review.json | 完成后人工抽查的结论及修订记录 |
| secondary_review.json | 剩余未知字段及特殊情况的二次复核记录，区分 confirmed/inferred/unresolved |

数据源：`bird_schemas.txt`、`commom_schema.txt` 使用 UTF-8；`core_schema.txt` 使用 GB18030。按数据库分段提取 SQLite/MySQL，PostgreSQL 的 public 单独保存为 schema，实际业务数据库名未知时为 null。Elasticsearch 索引保留 mapping 和 keyword 子字段。

外键、主键和完整约束原文均保存；不会根据名字猜测主键。字段知识按业务库、表和字段名关联；只从 `splits/train.json` 关联案例，不读取 validation/test。源文件 SHA256 和行号用于追溯。字典 INSERT 数据和行政区划数据不在本模块解析范围；完整类型/方言信息以 raw_definition 为准。

发送给外部 API 的内容仅限表/索引标识、字段名、类型、已提取描述和知识编号；不发送数据记录、DDL 原文、完整知识或训练案例。模型校验准确描述时原文保留，缺失描述生成，错误描述修正，无法确定则 null。程序检查字段覆盖、状态和来源编号，但不能证明语义正确，模型结果默认 human_reviewed=false，需要人工抽查。

人工抽查后修订最终 catalog 和检索文档，原始提取及 API 缓存保持原样。抽查只能代表已检查样本，不等于全部描述均已人工核验。调用 usage 可从报告查看，实际费用以 API 平台账单为准。

## 本次处理结果

2026-10-11 完成 265 张表/索引、1694 个字段：SQLite 193、MYSQL 70、POSTGRESQL 1、Elasticsearch 1。恢复 GB18030 中文注释并提取非标准知识句式后，1511 个字段已有来源描述；模型校验和补充后最终有描述的字段为1654，40个不确定字段保留 null。

本会话 Codex 主代理亲自对照资料抽查16张表的全部135个字段（8张定向、8张固定种子随机），额外检查全部38个模型标记 corrected 的字段，记录15项描述修订/增强。重要修订包括 Yelp 投票的发出/收到方向和级别语义、方法参数名称与类型、船舶静态/动态表的检索摘要。此处“人工抽查”指代理逐项检查，不代表用户或外部人员核验；模型记录 human_reviewed 仍为 false。

二次复核全部40个剩余未知字段、143个模型补充字段和38个模型修正字段，并检查类型冲突及模型警告。40个未知字段中4个有直接证据确认，33个提供保守推断说明并明确未确定的编码/值域，3个仍无法可靠确定：professional_basketball.players 的 useFirst、nameGiven、fullGivenName。最终1691个字段有描述，3个保留 null。推断说明不等于数据值验证；原始数据库记录未提供。

二次结果另记录17项特殊情况，包括4处知识类型与DDL冲突、Genes.GeneID主键知识冲突、MethodId未声明关联、Checkins小时后缀/星期混淆、无签到与闭店的逻辑差异，以及教育库日期键编码未声明。修正两个教育库 exam_score.enrollment_id 的含义为选课记录，并依据完整训练案例确认 home_region_id 是家庭地区编号。apply_review.py 自动依次应用初次和二次记录，支持重复执行；schema_documents.jsonl 同步包含特殊情况注意事项及 inferred_fields/unresolved_fields。
