# 680 题：0.6B 检索 + DeepSeek Flash + BIRD 补齐

本次输入为项目目录外的 `../data/QA_test.json`（680 题），不是 V6 内的旧 200 题文件。用户确认“0.8B”指此前的 0.6B 方案，随后指定 SQLite 使用 BIRD 数据集答案。

已完成全部 **680 题**，正式文件为 [result.json](../result.json)，保留输入的全部 ID 和原始顺序。用户已明确授权本次提示词发送到 `https://api.deepseek.com`。602 题使用 0.6B 混合检索与 DeepSeek Flash 查询生成，78 题使用 BIRD 标准 SQL。

首轮 585 题通过；对失败题扩大到目录全部数据源召回后，另有 15 题通过；最后 2 题与本次其他成功题文本完全一致，复用相同查询且只替换 question_id（454 ← 464，522 ← 479）。没有手写补充业务 SQL。所有答案均通过格式与现有静态校验；未进行真实数据库执行评分。

## 数据与方法

- 工作目录：`outputs/qa_test_680_hybrid06b_deepseek_flash_v1/`。
- 0.6B 目录：`outputs/experiments/preprocessing-prompt-coverage-v1/hybrid-0.6b/`。使用冻结目录、索引与原有字符 TF-IDF 路由，不重新关联知识，不覆盖默认生产预处理数据。
- 检索：BM25 / embedding 各 Top 50，RRF k=60，候选池 Top 50 使用 Qwen3-Reranker-0.6B 精排。首轮 6 表，累计最多 12 表，知识 12 条，训练案例 4 条；模型参数与原实验一致。
- 提示词：`ContextBuilder.assemble -> fit -> submission.generate_one`，包含真实 Schema、原始知识、训练案例及 `../data/问题描述与查询指令口径规则.txt`。与上一轮只导出 DDL 的提示词评估不同，本次采用已有通用查询生成流程，不能把上一轮覆盖率当作本次查询正确率。
- 生成端点：`https://api.deepseek.com`，模型 `deepseek-flash`，JSON 输出、非思考模式，温度 0。密钥仅从环境或无回显终端读取。
- 生成每轮最多 4 次生成/修复/Schema 补充，静态校验不通过则保留失败记录，支持断点续跑；全部完成后才写完整提交文件。

## SQLite 来源

78 题（ID 603–680）对应本地 BIRD 原始记录。58 题由旧版中文题目与标准 SQL 匹配定位，20 题逐条对照中英文题意定位。`bird_match_sources.json` 保留原始英文问题、SQL、数据库、文件、数组位置和中文匹配方式；`input_and_BIRD_verification.json` 核对这些内容与原始数据文件一致。

仅在物理表上添加 `数据库.表` 限定；移除这些限定后，SQL AST 与 BIRD 原答案一致，不根据本次统一口径修写 BIRD 标准 SQL。78 条均通过原始数据库只读 `EXPLAIN QUERY PLAN` 检查。该检查证明语法、表字段可解析，不代表原始 BIRD 标注语义正确或本次执行正确率。

`result_bird_only.json` 是明确标记的 78 题部分结果；完整文件必须包括所有 680 个原始 ID，并保持输入顺序。不会以部分文件冒充完整结果。

## 复现

在安装项目依赖且具有 CUDA 的环境下，在 V6 根目录运行：

```bash
RUN=outputs/qa_test_680_hybrid06b_deepseek_flash_v1
PYTHONPATH=src python -m text2query.submission.hybrid_flash prepare \
  --directory "$RUN" --questions "$RUN/questions_input.json" \
  --rules "$RUN/query_rules.txt" --bird-answers "$RUN/bird_answers.json"
```

外部发送获得授权后，以相同参数将 `prepare` 改为 `generate`，设置 `--result result.json --workers 8`；通过 `DEEPSEEK_API_KEY` 或无回显终端输入凭证，不把凭证写入配置与日志。

官方接口参考：[首次调用](https://api-docs.deepseek.com/)、[JSON 输出](https://api-docs.deepseek.com/guides/json_mode)、[思考模式开关](https://api-docs.deepseek.com/guides/thinking_mode)。

## 执行记录

- 初始上下文准备：846.0 秒；17 题扩展召回：45.6 秒。使用冻结的相同目录与索引，首轮 602 份上下文均未发生预算裁剪。
- DeepSeek 使用 8 路并发：首轮 150.3 秒，扩展证据重试 15.9 秒。累计 686 次成功的生成/修复请求。客户端使用 `Accept-Encoding: identity` 避开服务器现有 Brotli/httpx2 解压兼容问题。
- 对扩展重试轮，每次最多补充 4 张表，并为后续修复预留 2500 token；所有表与字段仍必须来自冻结目录。该策略不改变知识关联或检索阈值。
- Token 用量：输入 7,828,423，输出 144,514，合计 7,972,937（含失败尝试与修复；未折算费用）。
- 提交文件：MySQL 单系统 464 条、PostgreSQL 单系统 59 条、Elasticsearch 50 条、SQLite 78 条、跨系统 29 条。
- 全部 ID、顺序、键集合、非空查询及 Elasticsearch JSON DSL 已在本机独立复核；文件 SHA256 与服务器一致。
- SHA256：`dc613ba14f85952b20f6dc3e38b56406aae774cadf1d204e99cfc3aa261b1c5c`。

完整提示词为运行目录中的 `prompts.jsonl`，扩展重试提示词在 `expanded_engine_retry/`。`final_sources.json` 逐题标明最终使用的来源文件；失败尝试保留供审计，不代表最终仍有失败。

离线检查：两项聚焦流程测试通过；本次 Python 文件 Ruff 通过；78 条 BIRD SQL 通过原始只读数据库的 `EXPLAIN QUERY PLAN`；全部 602 个初始请求的 token 预算检查通过，最大保守估算 18,465，小于 21,000 上限。

合并与复核入口：

```bash
PYTHONPATH=src python scripts/finalize_flash_submission.py \
  outputs/qa_test_680_hybrid06b_deepseek_flash_v1 --result result.json
```
