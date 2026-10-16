# 100题生成结果与错题提示词归因

使用语义向量多标签路由、0.6B混合检索/重排及更新后的统一规则，调用DeepSeek Flash完成100题生成。
路由与检索复用冻结开发验证上下文，生成与响应为真实新请求；参考SQL不用于生成补证据。

[40题提示词与归因报告](../evaluation/validation_100/runs/prompt-diagnosis-v1/README.md) · [完整提示词JSONL](../evaluation/validation_100/runs/prompt-diagnosis-v1/wrong_prompts.jsonl) · [逐题归因CSV](../evaluation/validation_100/runs/prompt-diagnosis-v1/diagnosis.csv) · [100题预测](../evaluation/validation_100/runs/prompt-diagnosis-v1/predictions_100.json)

## 原始语义审查

100题全部首轮通过已有静态校验。逐题静态语义审查为60题与参考一致、1题仅新增规则导致的精度差异、36题有差异、3题暂不能确认。
跨系统联查为2/9；同系统跨业务库为14/20。没有连接数据库执行，也没有独立人工或第二个评审模型，因此不是执行准确率。
字典维度表示、具名列排列等归一化边界见[原审查汇总](../evaluation/validation_100/runs/prompt-diagnosis-v1/source_semantic_summary.json)。

验证集没有官方逐题type字段，按题意和参考进行近似分层，使用seed42无重复抽100题：知识39、简单23、计算21、空间8、跨系统9。
跨系统只有9题，未达到按测试比例应取的17题；用户确认全部纳入9题、其他类别按权重回填。原284题开发验证集不含SQLite。
[抽样清单](../evaluation/validation_100/runs/prompt-diagnosis-v1/sampling.csv)和[抽样说明](../evaluation/validation_100/runs/prompt-diagnosis-v1/sampling_manifest.json)保留完整口径，不能将本次成绩外推到680题外部评分。

## 来自提示词还是模型

40道非确认一致题的互斥归类如下。分类基于实际可见证据，不是已完成控制变量实验的因果结论。

| 主要归类 | 题数 | 含义 |
| --- | ---: | --- |
| 输入证据缺失 | 4 | 提示词中没有专用概念定义、地标坐标或区域几何，已有Schema不足以推得答案 |
| 规则或案例冲突 | 3 | 系统规则与参考/案例有冲突，或同批案例使用不同业务口径 |
| 混合 | 10 | 同时有输入缺口，以及模型误用已有信息、未补证据或删除明确要求 |
| 模型未利用已有证据 | 4 | 所需信息已明确提供，仍被改写或丢失，或产生无输入依据的错误运算顺序 |
| 尚不能裁定 | 19 | 题面、参考或实际数据缺少唯一口径，不能直接认定模型错误 |

需要细化上一轮的解释：

- **245**：案例155明确给出新能源车用`brand LIKE '%电动%'`，模型改为`'%新能源%'`；属于没有正确利用已有案例。
- **2907**：案例2932已给出正确的朝连岛禁航区多边形，模型仍声称缺边界并改坐标。2908则确实没召回日照警戒区定义，两题原因不同。
- **441**：专门BPS知识未召回，但案例433、439已有正确BPS公式；还有EPS近似公式干扰，因此归为混合，不能只怪漏知识。
- **1588**：新规则明确比率ROUND2并优先于案例；预测遵循它，与旧参考ROUND4不同，不能归为模型能力问题。
- **1723/1728**：两个年份的DDL都在，题面没有年份，不能归为路由漏库。

优先统一题目、参考与规则口径，再修复专用知识和必要Schema的召回。对输入已经充分的题，固定同一提示词比较模型或重复生成，才有依据估计模型差异。
本轮没有重新调用LLM，也未修改生产检索、提示词、标签或训练SQL。

## 复核

在原冻结输出仍存在的本地环境，可重新导出并验证请求与证据：

```bash
python evaluation/validation_100/diagnose_prompts.py
```

归因注释与原始review pack的SHA256绑定；输入改变会拒绝回放。程序只读离线参考，生产代码不导入此模块。
每题保留实际`request.json`、`response.json`、`diagnosis.json`及可读说明；这些文件不包含凭证或认证请求头。
远程仓库同步紧凑的审计材料；模型权重、完整本地运行缓存及原提交仍按现有忽略规则保留在本地。

同步前完整离线测试：101项通过、1项显式模型测试跳过；[测试摘要](../evaluation/validation_100/runs/prompt-diagnosis-v1/verification/test_summary.json)。
