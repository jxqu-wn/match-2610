请严格按照系统提示词 table-knowledge-reference-v2，独立完成本批标注。

batch_id: {{BATCH_ID}}
target_table_ids: {{TARGET_TABLE_IDS_JSON}}

完整上下文如下。每张目标表都必须检查 context.knowledge_context 中的全部247条知识。
使用完整的72张表/索引目录消除引用歧义，主结果仅输出上述目标表，顺序与列表相同。
主结果必须保持 tables[].knowledge[]，每条 knowledge 只含 knowledge_id 和完整原文 knowledge_text。
知识排序、去重、空表、未决项及独立 audit 信息均遵守系统提示词。
不使用其他标注员的结果或程序当前的匹配结果。

<REFERENCE_INPUT_JSON>
{{INPUT_CONTEXT_JSON}}
</REFERENCE_INPUT_JSON>

END_OF_REFERENCE_INPUT_TABLE_KNOWLEDGE_V2
