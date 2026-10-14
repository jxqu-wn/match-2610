# Codex 独立参考标注 v1

状态：初次全量标注已完成并冻结，等待用户独立运行的 Deepseek Flash 结果；尚未比对或人类裁定。
本次由三个 subagents 分工完成，每人24张表，每张检查完整247条知识；未读取 Flash 输出。
输入、提示词和12批目标与 input_lock.json 的启动校验值一致。

主结果：`frozen/tables.json`，采用 `tables[].knowledge[]`；知识只含 knowledge_id 和完整原文 knowledge_text。
独立审计：`frozen/audit.json`；原始12批响应：`frozen/batches/`；完整性报告：`frozen/validation.json`。
各冻结文件的 SHA-256 及输入版本保存在 `frozen/manifest.json`。`codex/` 为工作副本，后续比较以冻结版本为准。

- 完整覆盖72张表/索引、247条知识；12批完整性与原文校验通过，无错误。
- 261条参考关联：58条 explicit，203条 schema_supported。
- 182条知识至少有一条参考关联，65条未输出肯定关联；44张表有肯定关联，28张为空。
- 59个未决配对涉及42条知识；11份内容问题报告涉及9条知识。
- 单方待审清单：`review_pending.md` / `review_pending.json`。分歧清单将在 Flash 结果完成后另行生成。

已记录的内容问题涉及：1572, 1575, 1596, 1653, 1739, 1740, 1773, 1783, 1785。
例如：示例成绩权重与 Schema 默认值不同、重复教育表名的归属、引用知识108缺失、驾驶规则边界、区划示例冲突及1739/1740状态码冲突。
不补写缺失规则，不将候选并入主结果；单方接受、一致或双方未关联都需要后续复核。

校验与比较工具见 ../../README.md，16项结构完整性测试已通过。
标注及工具均位于 evaluation，不进入正式数据预处理。
