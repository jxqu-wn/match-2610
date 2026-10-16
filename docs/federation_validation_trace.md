# 多库验证集流程诊断

使用已冻结的 0.6B 混合检索与重排结果，对验证集全部 9 道跨系统题重新调用 DeepSeek Flash，保存路由、检索证据、上下文裁剪、实际请求、响应及修复记录。另对其中 4 道初始单系统路由题做补充 Schema 对照。实验未修改原 `result.json`，未修改生产路由、检索或生成策略。

[完整报告与逐题入口](../outputs/experiments/federation-validation-trace-v1/README.md) · [划分清单](../outputs/experiments/federation-validation-trace-v1/split_manifest.json) · [逐题指标 CSV](../outputs/experiments/federation-validation-trace-v1/evaluation/overview.csv) · [对照汇总 JSON](../outputs/experiments/federation-validation-trace-v1/comparison.json)

## 数据与参考答案隔离

有标注数据为 `data/赛题8/QA_train.json`，共 2839 题。沿用此前 seed=42 的 90/10 分层划分，训练 2555 题、验证 284 题；剔除训练侧与验证题同文本的 13 条记录后，路由和训练案例检索仅使用 2542 题。这是开发验证集，并非新的独立测试集。

抽取验证集中全部 MySQL↔PostgreSQL 题：2942、2949、2950、2968、2970、2972、2980、2984、3012。选择只使用系统标签，未按生成结果筛选。生成入口不读取验证参考 SQL；参考仅由生成结束后的独立评价入口读取。对照补表根据问题文本在目录中做关键词排名，未使用参考表或参考 SQL。

## 结果

| 指标 | 原流程全部 9 题 | 其中遗漏 MySQL 的 4 题 | 同 4 题补 Schema 对照 |
| --- | ---: | ---: | ---: |
| 初始完整库表覆盖 | 5/9 | 0/4 | 4/4 |
| 最终完整库表覆盖 | 5/9 | 0/4 | 4/4 |
| 最终静态校验通过 | 9/9 | 4/4 | 4/4 |
| 实际生成请求数 | 9 | 4 | 9（包含 5 次修复） |

完整库表覆盖表示生成查询包含参考所需的系统和表，不代表结果集正确。没有连接 MySQL 或 PostgreSQL 执行，无法报告执行正确率，也不能据此推算 680 题的新分数。

## 问题原因

1. **路由提前排除了另一系统。** 2942、2970、2972、2980 仅路由到 PG；历史已评分候选中仅有 1 张 PG 表。相关 MySQL Schema 没有进入候选，无法靠 RRF 或重排恢复。9 题均未发生初始上下文裁剪，因此这次缺表不是 token 裁剪造成的。
2. **模型省略或替换需求后仍被接受。** 2942 删除公司条件，2970 删除船长条件；2972、2980 把自持力分别错误映射为吃水 `draught>45`、`draught>90`。四题均返回 `complete`，静态校验通过，没有触发补充召回。
3. **补全 Schema 后，分步规划仍不可靠。** 对照保持初始知识、训练案例、relations、系统提示词和模型配置不变，仅补充最多 4 张其他系统的 Schema 并更新检索系统元信息。四题首轮都把 MySQL 表写进 PG 查询，经表归属校验反馈及后续补表修复后，才恢复两系统分步协议和库表覆盖。
4. **累计 Schema 预算未落实。** 上下文声明总计最多 12 表；生成器实际按每次最多追加 12 表处理。2942 对照输入累计从 5 表增至 17 表、29 表。
5. **静态通过仍有语义问题。** 2950 缺少参考中的 MMSI 分组；3012 输出公司名，与参考的船舶记录投影不同。对照中还出现轨迹过早空间过滤、`result` 被当成表、MySQL 字符串函数参数误用等问题，详见逐题报告。

建议依次改进：允许跨系统候选扩展；生成前检查“需求→字段→系统→步骤”；禁止带未满足需求完成；统一累计表数与 token 预算；核验中间结果协议、统计粒度、输出对象、单位和函数语义。本次只实现诊断与对照工具，尚未将这些改进应用到生产流程。

## 跟踪文件与复现

每个 `cases/<question_id>/` 保存 `01_routing.json`、`02_selected_retrieval_evidence.json`、裁剪前后上下文、初始消息、`06_generation/` 实际请求与响应、`07_offline_evaluation.json`、`08_request_lineage.json` 和逐题说明。对照位于同目录下的 `schema_expansion_control/`。

检索重放已冻结的 0.6B 证据，保留原 BM25、向量、RRF 与重排分数；未重新运行 embedding/reranker。历史缓存可恢复已重排文档的并集，无法恢复未保存的每次原始 Top50 边界。新生成及修复为本次真实调用，共 18 次请求。

[实验入口](../src/text2query/experiments/federation_trace.py)提供 `prepare`、`generate`、`score`、`prepare-control` 四个命令。以下命令在 V6 目录、配置好项目依赖和本地 tokenizer 的环境下运行；新实验使用新目录，避免覆盖冻结产物。`generate` 会调用 API，并从环境变量或隐藏输入读取密钥；验证参考不会进入请求。

```bash
python -m text2query.experiments.federation_trace prepare --output outputs/experiments/federation-validation-trace-v2
python -m text2query.experiments.federation_trace generate --output outputs/experiments/federation-validation-trace-v2 --workers 8
python -m text2query.experiments.federation_trace score --output outputs/experiments/federation-validation-trace-v2
python -m text2query.experiments.federation_trace prepare-control --output outputs/experiments/federation-validation-trace-v2
python -m text2query.experiments.federation_trace generate --output outputs/experiments/federation-validation-trace-v2/schema_expansion_control --workers 4
python -m text2query.experiments.federation_trace score --output outputs/experiments/federation-validation-trace-v2/schema_expansion_control
```

冻结 v1 报告可离线重新生成：

```bash
python evaluation/federation_trace/build_report.py --input outputs/experiments/federation-validation-trace-v1
```

逐题人工诊断与两份答案的 SHA256 绑定；新调用结果改变后，必须重新核对并建立新的诊断版本，不能直接套用 v1 结论。[3 项离线测试](../tests/test_federation_trace.py)覆盖参考隔离、凭证不落盘和未限定字段校验盲点，均已通过。
