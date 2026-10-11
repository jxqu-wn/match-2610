# 库表信息召回

输入问题与已有数据库系统分类，按照 **系统类型 → 系统内跨业务库检索候选表 → LLM选择表/字段** 执行；不执行业务 SQL。已回退业务库前置选择方案，保留补检索控制修复及token统计。

## 环境与使用

在项目根目录执行：

```bash
uv pip install --python .venv/bin/python -r scripts/information_retrieval/requirements.txt

# 使用已有本地 Qwen3-Embedding-0.6B；首次构建完整索引
.venv/bin/python scripts/information_retrieval/run.py build-index --device cuda --dtype float16

# 直接检索候选表，不调用外部模型
.venv/bin/python scripts/information_retrieval/run.py retrieve \
  --device cuda --dtype float16 --engines SQLite \
  --question '哪个国家培养的冰球运动员最多？请标明哪一年出生的冰球运动员最多。' \
  --question-id 5635 --output outputs/information_retrieval/context.json

# 候选表及相关知识、训练案例发送至DeepSeek；密钥从DEEPSEEK_API_KEY读取
.venv/bin/python scripts/information_retrieval/run.py plan \
  --device cuda --dtype float16 --engines SQLite \
  --question '哪个国家培养的冰球运动员最多？请标明哪一年出生的冰球运动员最多。' \
  --output outputs/information_retrieval/plan.json

# 验证集评估：答案仅用于评估标签，不进入索引/LLM
.venv/bin/python scripts/information_retrieval/run.py evaluate \
  --device cuda --dtype float16 --output outputs/information_retrieval/evaluation.json

.venv/bin/python -m unittest discover -s scripts/information_retrieval -p 'test_*.py'
```

CPU 使用 `--device cpu`。索引绑定模型、精度、设备及输入长度，构建和加载必须使用匹配设置。关键词基线可以使用 `--keyword-only --index outputs/information_retrieval/keyword` 单独构建和加载。

`--classification-json` 可替代 `--engines`，接受已有路由输出的 `databases` 数组，也接受 `engines` 或 `db/db1/db2/db3`。未知分类/空集合不会默认扩大到所有系统。多系统示例：`--engines MYSQL POSTGRESQL`。

`retrieve`直接输出候选表上下文；`plan`直接进行表和字段判断。业务库由召回表的归属体现，不再独立调用LLM选择或作为硬性过滤范围。

`--budget-json` 接受 Budget 字段的 JSON 配置，默认输入与输出合计24000、输出预留3000；首轮另外为格式修复预留4000；其余默认与设计一致。`evaluate --limit 30` 可做小样本检查。默认模型为 `deepseek-flash`，密钥不会写入脚本或产物。

## 实现

- `index.py`：265张完整表、1800条知识、5247条训练案例的稳定来源索引，关键词与embedding RRF；文件SHA256及模型签名校验。只读取训练子集。SQL使用SQLGlot解析别名/CTE/多步骤，ES单索引归属明确标记为catalog推断，案例始终标记未验证。
- `explicit_knowledge.py`：仅解析知识原文中的明确库表引用和唯一可解析的表.字段；不按单独字段名或业务语义推断表。
- `context.py`：按系统轮流召回候选表、最多一层已声明外键扩展、完整字段数组与复核状态。知识和训练案例根据候选表关联召回，允许同系统内跨业务库证据。
- `planner.py`：最多两次表判断、一次补检索和一次结构修复。存在可执行的检索缺口时，即使模型返回insufficient_evidence也继续补检索；歧义和未知值域不会触发补检索。格式修复冻结已有证据，每次调用仍受24000总预算/3000输出预留限制。
- `run.py`：命令行入口；`evaluate.py`：独立检索评估；`test_retrieval.py`：异常路径与预算等测试。

计划状态为 ready、ready_with_assumptions、needs_clarification、insufficient_evidence、error；need_more_evidence仅为中间状态。输出包含初始/最终系统集合、系统变更原因、所选表字段、关系证据、假设、未决缺口，以及调用、token使用量、延迟、缓存命中和省略资料日志。模型调用失败不会伪装成确定业务结论。

`test_live.py`保留固定题号重测、训练集隔离审计、裁剪前后token统计及输出版本检查。`--prepare-only`只生成候选表上下文，不调用API。业务库匹配指标由最终所选表的归属计算，输出字段为`selected_table_business_databases`，不表示独立业务库路由结果。回退版本标识为`system-table-v2`；当前明确知识关联优化版本为`system-table-explicit-knowledge-v5`，重测需使用新的输出目录，避免混用历史结果。

业务库前置方案的历史50题报告见[STAGED50_RESULTS.md](STAGED50_RESULTS.md)，实验代码快照保存在`experiments/business_routing_v1/`，不参与当前运行与测试。`business_routing.py`和`review_staged.py`仅保留用于历史实验复核。回退未新增真实模型调用；历史准确率不视为回退后的新测结果。

程序不根据同名字段创造外键。已声明关系、未经验证的案例关系与明确标记的推断关系分别处理。案例关系和推断关系须保留假设；模型仍需判断业务意图与证据充分性。

## 当前限制

1. 未安装DeepSeek的精确tokenizer。有embedding模型时使用本地Qwen tokenizer计数×1.2＋256余量；关键词模式没有tokenizer时回退到UTF-8字节数估算。这是经验估算，不是目标模型的精确计数。日志明确标记估算方式。修复请求也受同一总预算限制，冻结已有schema和证据；无法容纳时明确error，不移除必要schema。
2. 超限时整条移除低优先级资料，绝不静默截断表字段。优先保留每个初始系统的首位表和首个相关案例所涉及的候选表；首个相关案例涉及但未召回的表可在配额内替换低排名候选。这是排序依据，不是业务正确性判定。过大的单表也可能被整表省略，记录于omitted_evidence。
3. Embedding输入受max-length限制，audit.json记录受截断影响的来源。完整文本仍进入关键词索引，完整schema仍可提供给模型；后续应评估分块向量索引。
4. 196条知识缺少可靠库表归属，保留在索引并记入unscoped_knowledge_ids，首版不召回这些条目。需要后续独立标注，不能猜测所属系统。
5. SQL解析结果只是弱标签；显式JOIN可记录案例证据，复杂表达式、CTE输出字段追踪及更多跨库结果映射没有完整关系推导。实际模型已获再次审批并完成20题测试，结果见LIVE20_RESULTS.md；此前离线评估不包含真实模型判断。
6. 当前评估使用正确系统集合，衡量检索本身；不是数据库分类加检索的端到端指标。相同训练问题命中只作流程展示，不能证明泛化能力。

评估数据和检查结论见 [RESULTS.md](RESULTS.md)。

## 20题真实模型与token试验

`test_live.py --prepare-only` 只准备本地资料，不调用API。按系统组合轮流选取20个验证问题，排除训练集中完全相同的问题，使用正确系统分类隔离召回与模型选择能力。

获得明确资料发送授权后执行 `test_live.py`，密钥从DEEPSEEK_API_KEY读取；每题结果落盘，重复执行读取已有结果，不再次发送已完成的问题。保持默认两次语义判断、一次格式修复的限额。验证答案仅用于本地评分。

产物位于 `outputs/information_retrieval/live20/`：selection.json、prepared_*.json、prepared_profiles.json、question_*.json、progress.json和report.json。真实调用记录保留API usage中的输入、输出、缓存token，以及finish_reason；token_report.py汇总均值、P50/P90/P95、最大值和输出长度终止次数。

裁剪前后均记录表、字段、知识、案例数量，以及本地Qwen tokenizer的估计。用实际输入token校准裁剪前估计，帮助判断预算与估算方法的影响；未裁剪上下文的token数量属于校准估计，不是API实测。20题分层样本适合初步预算诊断，不足以确定生产尾部预算。此次再次申请已获批准，20题测试完成；详见 [LIVE20_RESULTS.md](LIVE20_RESULTS.md)。


优化版同20题对比见 [OPTIMIZATION_RESULTS.md](OPTIMIZATION_RESULTS.md)。用 `test_live.py --output-directory outputs/information_retrieval/live20_v2` 独立保存重测结果；旧版产物不覆盖。字符串数组形式的requested_evidence可等价转为字符串；含假设的ready自动降为ready_with_assumptions。不存在的表、字段和证据仍然拒绝。


全新50题端到端测试见 [LIVE50_RESULTS.md](LIVE50_RESULTS.md)。`test_live.py --sample-size 50 --random-seed 20261011 --exclude-selection outputs/information_retrieval/live20/selection.json --predicted-routing --output-directory outputs/information_retrieval/live50` 支持训练案例审计、排除前次样本、规范化重复排除、固定随机抽样及训练集分类器预测。`review_live.py`只在本地整理生成结果与参考对照，不调用API；语义分数来自逐题审核，不能用表集合相同自动代替。


50题问题定位、补检索控制缺陷和改进顺序见 [LIVE50_ANALYSIS.md](LIVE50_ANALYSIS.md)。本分析未新增模型调用、未修改评测答案或检索知识。

回退流程同50题真实重测及库表比例见 [ROLLBACK50_RESULTS.md](ROLLBACK50_RESULTS.md)。`review_coverage.py`在本地分别统计首轮上下文、补检索后上下文和最终选择，不调用模型，不将参考答案加入推理。

`review_coverage.py`同时提供原问题RRF相关性排名：表在预测系统合并范围内排序，业务库按库内最高表分数归并排序。无排名参考对象单列，均值不计为零；该诊断排名与上下文位置分开。全新200题真实测试见 [LIVE200_RESULTS.md](LIVE200_RESULTS.md)。

当前新增的知识定位链路使用原始知识句子，不改写schema：仅对原文命中问题低频token且有明确表引用的知识进行投影，前12条知识按表归并，最高命中分数形成排名，以0.25权重加入schema RRF。低频token长度至少2、非纯数字、出现在不超过10%的明确关联知识文档中。该过滤只证明文本匹配，不证明业务适用性。原知识/表/案例配额和LLM提示不改；原句在知识配额内提供，schema中记录关联来源。1800条知识中1519条有可解析明确表引用，281条不用于新增定位。

同200题真实对照及初版失败实验的消耗记录见 [EXPLICIT_KNOWLEDGE200_RESULTS.md](EXPLICIT_KNOWLEDGE200_RESULTS.md)。旧版产物保留，新版重测目录为`outputs/information_retrieval/live200_explicit_knowledge_v5/`。测试覆盖明确引用、多库范围、歧义引用、仅字段名、关键词模式、系统过滤与来源排除。

## 完整测试集查询生成

`generate_submission.py` 使用 `deepseek-v4-pro`，读取全部 `data/赛题8/QA_test.json` 问题，使用完整5830条 `QA_train.json` 重训分类器并建立独立 v5 检索索引，直接生成最终 SQL/DSL；不执行数据库查询，也不读取独立验证文件或任何测试答案；正式测试的完整训练集包含原分割验证子集，这是官方测试推理允许使用的训练数据。模型输出需求与字段对应关系，并可请求补充 schema。补充仅使用已有 catalog，不进行人工业务判断。

```bash
.venv/bin/python scripts/information_retrieval/generate_submission.py --prepare-only
# DEEPSEEK_API_KEY 由环境注入，不能写入源文件
.venv/bin/python scripts/information_retrieval/generate_submission.py --workers 8
```

默认中间结果保存在 `outputs/qa_test_deepseek_v4_pro_full_train/`，全部成功后按测试集原始顺序写入项目根目录 `result.json`。成功题断点复用，失败题单独保存，重新运行只重试失败题。每题最多4次生成/修复/补充调用，传输重试沿用客户端限制。使用非思考模式、temperature=0、每次输出最多3000 token，保留真实 API usage。请求补充时按缺口文本在真实 schema 中检索，最多补充12张表，逐张检查上下文估算预算；输入最多21000、输出最多3000，总预算24000。初版补充整套 schema 的3道题已重新生成，历史消耗保留在 retry_history 中。估算沿用本地Qwen tokenizer×1.2＋256余量，并非DeepSeek精确tokenizer。

静态检查包含提交键与题号、数据库类型、单条只读SQL、库表引用、可解析的带别名字段、DSL JSON对象及跨系统 result 占位符。检查不等于业务或数据库执行正确性，未验证所有未限定字段、函数兼容性及数据取值。无全量有效结果时不输出虚构占位答案。
