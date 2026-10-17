# 提示词参数迭代与小样本SQL实验

入口为`evaluation/prompt_quality/parameter_sweep.py`与`sql_experiment.py`。向量和重排在独立GPU目录运行，评分与DeepSeek生成在本地进行，认证信息只从环境或交互认证获取，不写入代码、数据包或日志。

## 数据与隔离

复用已有284题开发验证、允许的训练案例索引、语义多标签路由和0.6B预处理目录。不是新的独立测试集。

- `prepare`验证题号和题面均未进入训练案例池，导出只有题号/题目的公共题目文件。
- `public/`包含推理资料，`private_evaluation/`包含参考、表目标及离线诊断标签；上传时只传public、代码与统一规则。
- 从四个拓扑分组按固定哈希预留20题：单表6、同业务库多表4、同系统跨库6、跨系统4；其余264题选参。抽取不看生成结果。
- 所有方案使用相同预留题，选择程序仅读取264题指标。由于既有验证集已反复用于开发，预留隔离只适用于本轮迭代。

## 首轮16组配置

保留冻结知识/结构控制、重新排序的关联范围控制、全局范围默认配置；逐项改变BM25 TopK（25/100）、embedding TopK（25/100）、RRF k（20/100）、重排池（25/100）、最终knowledge上限（6/18），另有无重排消融和两组宽候选组合。

第一轮路由、候选表与案例冻结。关联范围与全局范围控制使用相同文档文本、BM25语料/IDF、向量和新GPU重排分数，仅改变知识的范围限制。原始冻结控制保留历史知识选择，不将其冒称为新推理的逐字复现。

文本模型固定为Qwen3-Embedding-0.6B与Qwen3-Reranker-0.6B；查询/文档编码协议独立，embedding最大512 tokens，重排最大2048 tokens。计算签名包括模型文件指纹、精度、指令、脚本及输入哈希。分数缓存只复用同一签名的相同问题/文本对，不混历史CPU/GPU logits。

可以在第一轮选出配置后导出第二轮网格：为两个种子分别重新检索6/8/12张表，测试上下文预算与跨库覆盖。该轮允许表变化，必须与知识范围单变量实验分开解释。

## 当前能计算的评价与边界

自动计算参考完整库/表覆盖、按拓扑分组的覆盖、部分正例知识召回、知识原文保真、精确重复及输入长度。

知识正例由两类诊断组成：从原始知识标题/地标名称与题面严格字面匹配的银标，以及此前已核查的8个question×knowledge缺口。只报告部分正例覆盖，不称全量必要知识召回。银标不证明所列内容全部必需；缺知识块也可能由案例提供事实。

完整必要事实覆盖、可回答提示词率、语义噪声率没有完整事实金标，输出null。所有配置使用统一Qwen tokenizer的保守输入估算，不称DeepSeek精确计费tokens。

选参先要求整体及每个拓扑分组的参考库/表覆盖不低于冻结控制，原文无改写；然后按部分正例命中数与P95长度排序，并去除选参题上证据集合完全相同的配置。候选优劣是开发代理指标排序，需要后续SQL评价确认。

配置耗时受共享缓存影响，不是每组独立冷启动性能。报告新重排文档对数、缓存使用及总运行环境，不用后跑配置耗时较短直接宣称推理更快。

## 命令示例

设RUN为新建实验目录。所有命令从V6根目录执行。

```bash
python evaluation/prompt_quality/parameter_sweep.py prepare --output outputs/experiments/prompt-quality-sweep-v1
```

仅将public目录、src、测试入口和统一规则复制至GPU机器的独立V6目录，再在服务器执行：

```bash
python evaluation/prompt_quality/parameter_sweep.py run \
  --public outputs/experiments/prompt-quality-sweep-v1/public \
  --output outputs/experiments/prompt-quality-sweep-v1/inference \
  --embedding-model /path/to/Qwen3-Embedding-0.6B \
  --reranker-model /path/to/Qwen3-Reranker-0.6B \
  --device cuda:0 --dtype bfloat16
```

同步inference运行产物回本地后，独立评分和选择：

```bash
python evaluation/prompt_quality/parameter_sweep.py score \
  --output outputs/experiments/prompt-quality-sweep-v1/inference \
  --public outputs/experiments/prompt-quality-sweep-v1/public \
  --private outputs/experiments/prompt-quality-sweep-v1/private_evaluation
python evaluation/prompt_quality/parameter_sweep.py select \
  --output outputs/experiments/prompt-quality-sweep-v1/inference \
  --public outputs/experiments/prompt-quality-sweep-v1/public \
  --top 2 --expansion-grid outputs/experiments/prompt-quality-sweep-v1/expansion_grid.json
```

第二轮使用同一GPU入口的`--grid expansion_grid.json`。保持同一个推理快照和缓存签名；若代码或模型签名变化，另建版本。已有cases可恢复，已完成配置不重算。

## 小规模DeepSeek生成

保留基线，加上最佳固定表知识配置和最佳重新检索表配置，对相同20题生成。三个方案均只按264题选参指标确定，不用20题成绩重新挑选。通过`--diagnostic-ids`追加7道已知缺口题，明确属于开发诊断，不混入20题预留成绩；本轮共27题×3方案=81个生成任务。

```bash
python evaluation/prompt_quality/sql_experiment.py prepare \
  --output outputs/experiments/prompt-quality-sweep-v1/inference \
  --public outputs/experiments/prompt-quality-sweep-v1/public \
  --diverse-table-modes \
  --diagnostic-ids 441,935,1050,2125,2462,2487,2908
python evaluation/prompt_quality/sql_experiment.py generate \
  --output outputs/experiments/prompt-quality-sweep-v1/inference \
  --public outputs/experiments/prompt-quality-sweep-v1/public \
  --embedding-model ../models/Qwen3-Embedding-0.6B \
  --model deepseek-flash --workers 6
```

生成仅读取选中方案的公共题目、准备好的上下文及Schema，不读取参考查询。API密钥由DEEPSEEK_API_KEY提供。复用现有生成/静态校验/补Schema与修复流程，保存每次真实请求、响应、用量及失败记录。配置和提示词哈希冻结，变化时拒绝复用旧生成结果。

生成完成后运行`sql_experiment.py collect`，显式传入`--private`目录，汇总静态通过、保守的格式规范化查询匹配及逐题review pack。格式匹配不等于完整语义比较，不把不同SQL自动判错。`finalize --reviews ...`检查逐题注释完整性及review pack哈希，按组输出静态业务审查结果。

语义审查要求、源资料疑点先冻结，再查看预测。没有数据库连接时明确为代理静态语义复核，不宣称执行准确率或独立人工标注；不以查询非空代替正确。
