# Codex × Deepseek Flash 比对 v1

状态：`compared_not_adjudicated`。双方冻结版本使用同一输入与提示词版本，报告未经人类裁定。

- 双方一致关联：230 对。
- 仅 Codex：31 对；仅 Flash：35 对；依据分类分歧：0 对。
- 双方均为空表：28 张。
- 待人类裁定事项：156 项（关联分歧 66、候选 71、内容问题 19）。

## 文件

- `comparison.json`：逐表列出 `left_only`/`right_only`/`basis_disagreements`/`accepted_by_both`。
- `human_review.json`：完整待审队列（含知识原文与双方审计证据）。
- `human_review.md`：待审清单索引。
- `agreement_audit.json`：双方一致关联、双方均空表、双方均未关联的 38 条知识。

一致项与双方互相遗漏都需复核；一致不等于人工确认，遗漏不等于已确认负例。
疑难项由人类裁定后再形成金标准。
