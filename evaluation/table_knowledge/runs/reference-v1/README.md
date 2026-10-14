# LLM＋人工审核关联理想基准 v1

当前版本含72张表、247条知识范围、270对关联：58 explicit、212 schema_supported；44张表非空，28张表为空。108个裁定单元已处理，无待裁定关联。

- `tables.json`：与预处理一致的 `tables[].knowledge[]`，保留完整知识原文。
- `audit.json`：每条接受关联的初始证据、裁定来源及完整108项裁定（含拒绝和内容处理）。
- `manifest.json`：来源校验值、导出程序校验值、产物哈希及统计。

基准由Codex与Flash冻结结果的并集应用全部裁定得到。reject优先于初始接受；仅内容裁定不自动删除表级关联。双方一致沿用不等于用户逐条亲审，关联接受不等于全部内容可直接执行。生成阶段应同时读取内容处理意见。

这是当前预处理的理想目标，不是独立算法的实测成绩。参见[新预处理规范](../../../../docs/preprocessing_rules.md)。原始两方冻结文件不修改。

从项目根目录复现到新目录：

```bash
python -B evaluation/table_knowledge/build_reference.py --output-dir /tmp/table-knowledge-reference-rebuilt
```
