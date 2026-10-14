# Deepseek Flash 独立参考标注 v1

状态：初次全量标注已完成并冻结，且已与 Codex 参考结果比对；尚未人类裁定。
本目录的响应由 Deepseek Flash 通过 pi coding agent 逐批独立生成：每批独立的 system/user 提示词、
同一份 `input_context.json` 快照、无工具调用、无会话残留，未读取 Codex 输出或程序匹配结果。

- 完整覆盖72张表/索引、247条知识；12批结构完整性与原文校验通过，无错误。
- 265条参考关联：58条 explicit，207条 schema_supported。
- 197条知识至少有一条参考关联，50条未输出肯定关联；44张表有肯定关联，28张为空。
- 12个未决候选；8份内容问题报告。
- 主结果：`frozen/tables.json`，采用 `tables[].knowledge[]`，每条知识只含 `knowledge_id` 与完整原文 `knowledge_text`。
- 独立审计：`frozen/audit.json`；原始12批响应：`frozen/batches/`；完整性报告：`frozen/validation.json`。
- 各冻结文件 SHA-256 及输入版本保存在 `frozen/manifest.json`。

## 复现

`make_prompts.py` 从冻结的提示词包生成 `prompts/batch-001.md` 至 `batch-012.md`；
`run_batch.sh` 以同一 system 提示词与对应 user 提示词调用 Deepseek Flash：

```bash
python3 evaluation/table_knowledge/runs/flash-independent-v1/make_prompts.py
bash evaluation/table_knowledge/runs/flash-independent-v1/run_batch.sh batch-001
python -B evaluation/table_knowledge/manage.py validate \
  evaluation/table_knowledge/runs/flash-independent-v1/responses
```

`responses/` 保存原始响应，`logs/` 保存每次运行的退出码、耗时与字符数，均不进入正式预处理。

## 与 Codex 的比对

`runs/comparison-v1/` 保存比对结果：双方一致230对、Codex独有31对、Flash独有35对、
依据分类分歧0对、双方均为空28张表；共156条待审项（关联分歧66、候选71、内容问题19）。
`human_review.json`/`.md` 为待人类裁定清单，`agreement_audit.json` 保留一致项与双方均未关联的知识。
同侧结果不自动成为金标准，互相遗漏也不自动成为已确认负例。
