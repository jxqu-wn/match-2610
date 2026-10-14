# Deepseek Flash table–knowledge 标注提示词包

本包保存独立评测参考标注的输入、结果及校验工具，不向正式预处理写入标注。
当前口径版本为 `table-knowledge-reference-v2`；主结果与程序的 `tables[].knowledge[]` 直接配套。
统一口径由 `system_prompt.md` 定义；Deepseek Flash 与 Codex/指定 subagents 均应使用同一口径、同一输入快照独立标注。

## 文件

- `system_prompt.md`：作为 system 消息，包含判定边界、两类关联依据、证据要求和 JSON 输出格式。
- `user_prompt.template.md`：后续批次的 user 消息模板。
- `input_context.json`：完整的原始输入快照，含247条知识、72张表/索引目录和两份原始 Schema 的解码全文。
- `batches.json`：按表划分为12批，每批6张表，每张表检查全部247条知识。
- `first_batch_user_prompt.md`：已填入完整输入的第一批 user 消息，可直接复制使用。
- `format_example.json`：以 orders 表的1554、1555两条知识展示主结果格式，不代表该表的全量标注。

## 与预处理结果配套

主结果采用现有预处理产物中的相同字段与层级：

```json
{
  "tables": [
    {
      "table_id": "<table_id>",
      "knowledge": [
        {"knowledge_id": 0, "knowledge_text": "<完整原文>"}
      ]
    }
  ]
}
```

这保留了比对所需字段，不要求模型重复生成列定义等无关 Schema 字段。
对两份结果按相同的 table_id 比较 knowledge_id 集合，并核对 knowledge_text 原文即可，不需要转换关联方向。
同一张表内去重并按知识ID排序；没有关联的表仍输出 knowledge=[]。
模型响应的独立顶层 audit 保存依据、证据、候选、人审项和覆盖声明，主结果 knowledge 内不添加这些字段。
落盘时可以直接保存完整响应；若单独保存主结果和审计文件，也只需分别保留 tables 与 audit，不需要倒置层级。

## 使用

第一批将 `system_prompt.md` 作为 system 消息，`first_batch_user_prompt.md` 作为 user 消息。
它包含完整的247条知识与72张表资料，本次返回第一批6张表各自的 knowledge。

后续每批沿用同一个 system 消息，从 `batches.json` 取出 batch_id 和 target_table_ids，
将它们及 `input_context.json` 的完整内容代入 user 模板。每批都使用完整原始上下文，
不要只提供待测程序挑选的候选知识。批次划分只控制输出长度，不改变“两个标注方各完成全部247条”的要求。
保留各批原始响应；12批合并后 tables 直接拼接为72项，顺序与预处理目录相同。
只有全部72张表完成对247条知识的检查、表ID完整且无重复，才算一份全量标注完成。

具体模型上下文及输出上限在执行前核对；本包没有假设某个 API 的 token 上限。
若执行环境容纳不了完整输入，须先调整输入组织与覆盖检查，不能静默截断 Schema 或知识。

## 判定口径

- `explicit`：原文明示表引用，包括可唯一定位的表字段引用或真实 SQL 表引用。
- `schema_supported`：知识与原始 Schema 共同支持的直接适用关系，无需额外业务假设。
- 两类关系分别记录、分别比较和评分。同一配对 explicit 优先，不能重复输出。
- 证据不足的可能关联进入 audit.table_audit[].candidates；独立通用知识可以没有 table。
- 表归属与内容残缺/冲突分别处理。不得补写缺失知识、比较符、单位或业务规则。

这些是独立参考标注，不是程序已确认事实。模型声明 complete 也不能代替后续完整性与证据校验。
未列出的配对表示本轮没有输出肯定依据，不应直接解释为已经过人类裁定的负例。

## 输入来源与独立性

table_catalog 只机械提取稳定表标识、原始列名和源位置，用于查阅和统一命名。
Schema 全文从 `data/赛题8/Schema/` 的两份原始文件解码得到；知识直接来自 `knowledge.json`。
不含训练/验证/测试问答、旧目录的模型描述、人工复核、当前关联算法输出或其他标注方的结果。
所有原始文件校验值记录在 input_context.json 的 source_manifest 中。输入变化时应重新生成并统一两边版本。

后续自动校验至少检查目标表覆盖、原文完整性、知识ID与字段合法性、引文、去重、主结果与审计对应关系及人审标志。
reviewed_knowledge_ids 是模型的覆盖声明，不是对其实际逐条审阅行为的客观证明。
证据可找到只证明引用真实，不能自动证明理由成立；仍需双份标注比对、疑难项人审及一致项抽检。

## 本次执行与校验

Deepseek Flash 通过 pi coding agent 逐批独立运行（每批独立提示词调用，无工具、无会话残留）；
本目录的校验工具本身不发起模型调用。Codex 侧由三个 subagents 分别完成001–004、005–008、009–012批，
每人负责24张表，每张表检查全部247条知识。两方初次标注只使用上述输入，互不查看对方结果。
输入及提示词的校验值保存在 `runs/codex-independent-v1/input_lock.json`。

每方保留12批响应，分别命名为 `batch-001.json` 至 `batch-012.json`。
`manage.py` 只使用 Python 标准库，校验原始文件与快照的校验值、完整表和知识覆盖声明、
原文、引文、字段、排序、主结果与审计对应关系和人审标志；不会据此自动裁定语义。

从 V5 目录执行 Codex 结果校验及冻结：

```bash
python -B evaluation/table_knowledge/manage.py validate evaluation/table_knowledge/runs/codex-independent-v1/codex
python -B evaluation/table_knowledge/manage.py freeze evaluation/table_knowledge/runs/codex-independent-v1/codex --annotator Codex --output-dir evaluation/table_knowledge/runs/codex-independent-v1/frozen
```

冻结目录保存主结果 `tables.json`、独立审计 `audit.json`、12批原始响应、校验报告和带校验值的清单。
已存在的冻结目录不能覆盖，修订必须使用新版本。正式预处理不会读取这些文件。

Flash 的12批响应已放入 `runs/flash-independent-v1/responses/`，并使用同一工具校验和冻结；
随后比较两个冻结目录。两方统计与比对结果见 `runs/flash-independent-v1/README.md` 和 `runs/comparison-v1/comparison.json`：
完备冻结（Codex 261 对 / Flash 265 对，依据分类分歧 0 对，双方一致 230 对，双方均为空 28 张表，
待人类裁定 156 项）。以下命令可复现该流程：

```bash
python -B evaluation/table_knowledge/manage.py freeze evaluation/table_knowledge/runs/flash-independent-v1/responses --annotator 'Deepseek Flash via pi coding agent' --output-dir evaluation/table_knowledge/runs/flash-independent-v1/frozen
python -B evaluation/table_knowledge/manage.py compare evaluation/table_knowledge/runs/codex-independent-v1/frozen evaluation/table_knowledge/runs/flash-independent-v1/frozen --output-dir evaluation/table_knowledge/runs/comparison-v1
```

比较工具拒绝提示词或输入版本不同、冻结文件被修改或完整性校验失败的结果。
`comparison.json` 逐表列出双方独有的关联与依据分类分歧；`human_review.json` 和 `.md` 汇总未裁定事项；
`agreement_audit.json` 保留双方一致的关联、双方均空的表和双方均未关联的知识，供后续复核。
相同结果不自动成为金标准，互相遗漏也不自动成为已确认负例。

工具的结构完整性测试使用临时合成标签，不写入参考标注：

```bash
python -B -m unittest discover -s evaluation/table_knowledge -p 'test_*.py' -v
```

## 当前审核基准与新预处理规则

108个裁定单元已全部处理；最终关联目标见 `runs/reference-v1/tables.json`，完整裁定与内容处理见同目录 `audit.json`。该版本为72张表、270对关联（58 explicit、212 schema_supported），44张表非空。当前预处理关联规则见[新规范](../../docs/preprocessing_rules.md)。以上各独立标注README和comparison-v1原始报告记录的是初次比对状态，不代表当前仍有未决项。

基准由双方冻结关联并集应用全部裁定形成；reject覆盖初始接受，accept加入，内容裁定单独保存。双方一致沿用与用户逐项裁定不混同。它是预处理的理想目标；生产算法不读取标签，也不提供加载审核结果的预处理模式。

```bash
python -B evaluation/table_knowledge/build_reference.py --output-dir evaluation/table_knowledge/runs/reference-v2
```

导出前重新验证冻结文件和比对结果，检查裁定覆盖与优先级；输出目录必须不存在。输入或裁定变化后保留旧版本，创建新版本。

## 纯程序预处理评估

最新结果见 `runs/programmatic-v2/`：256对程序关联，命中200对、多关联56对、漏关联70对，precision 78.125%、recall 74.074%、F1 76.046%。`programmatic-v1/`保留上一代码快照的同规模开发结果。

生产算法仅读原始Schema、知识及训练划分，不读取参考标注、不调用LLM或嵌入模型。审核参考仅由以下独立评价入口读取：

```bash
.venv/bin/python -B evaluation/table_knowledge/evaluate_preprocessing.py --output-dir /tmp/table-knowledge-programmatic-eval
```

该入口在临时目录生成固定训练划分，运行生产关联器后再进行集合比对；输出逐表知识列表、得分证据、原始输入哈希、阈值扫描和差异报告。全局阈值在当前审核集上选择，成绩属于同集开发评估。

## BM25预处理对照

`runs/bm25-v1-default/COMPARISON.md` 保存相同原始输入、训练划分、分词和非文本规则下的BM25/TF-IDF对照及阈值扫描。BM25默认参数k1=1.5、b=0.75、阈值0.30，非空答案表完全覆盖率56.82%，F1=64.70%。默认算法仍为TF-IDF。

```bash
.venv/bin/python -B evaluation/table_knowledge/evaluate_preprocessing.py --method bm25 --output-dir /tmp/table-knowledge-bm25-eval
```

## 可插拔训练增强对照

同一修复后Schema、阈值0.30下，none模式命中177对、F1 73.90%；sql模式命中195对、F1 76.32%，非空表完全覆盖均为22/44。逐表噪声目标未达标表从5张降为3张，仍未全面达标。两组结果保存于 `runs/training-support-none-v1/` 与 `runs/training-support-sql-v1/`。独立模块与开关见[模块说明](../../docs/training_support.md)。
