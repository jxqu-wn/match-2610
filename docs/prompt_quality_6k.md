# 6k输入上下文参数实验

入口为`evaluation/prompt_quality/iteration_6k.py`，产物使用独立目录`outputs/experiments/prompt-quality-6k-v1`。6k指system与所有user/assistant历史消息的输入合计，不含模型输出。原37组大预算实验已经完成并保留，用作背景对照。

本地计数复用现有Qwen tokenizer ×1.2并加256开销的保守估算，固定system约1310；实际DeepSeek计数需要逐次检查`usage.prompt_tokens`，不能把不同模型tokenizer的估算当成完全相同的计费数。

所有列名、类型、可空性、字段注释、主外键及知识原文均保留。紧凑Schema去掉逐列重复的来源/审核元数据；完整来源和预算前对象保存在audit记录中。允许案例数为0；全局知识候选继续保留独立检索身份，不被旧关联清理误删。

首轮38组：4组控制，表4/6/8 × knowledge4/8/12/18 × 案例0/1共24组，另有2案例、裁剪顺序、按类别token占比分配、原始值域样例、4000/5000预算及10/12候选表。之后只按252题选参，再分别调整Schema、knowledge、案例检索分支的BM25、embedding、RRF、重排，以及表排名知识支持权重和路由扩展。

固定12题作本轮开发验收，原20题只作回归，7道已知缺口单列。所有题此前曾用于开发，验收不属于新的独立测试集；无SQLite案例。

参考库表覆盖与knowledge ID命中只做代理指标。knowledge不在提示词中时，训练案例或Schema字典样例仍可能提供所需事实。因此后续SQL对比除高知识命中、较短上下文方案外，也评估值域样例方案，并分别记录事实缺失、源冲突、模型条件/投影错误。

LLM生成入口可传`--input-limit 6000`：预算约束覆盖首轮、补Schema和修复调用。超过输入估算上限时保留失败记录，不向API发出超限请求；实际返回用量另外审计。完整语义等价与数据库执行准确率没有执行环境，不虚构成绩。

本轮实际完成94组：首轮38、高knowledge分支31、匹配案例控制1、低knowledge分支18、通用跨年命名空间配额6。参数分支使用独立缓存快照并行执行；逐组运行完成文件和提示词校验值保留，不能把耗时作为独立冷启动对比。

最终SQL候选选取与报告入口为`summarize_6k.py`和`report_6k.py`。`selection_6k.json`用于中途实验种子选择；`inference/selection.json`是最终冻结SQL任务，`recommended_parameters.json`按候选用途保存配置，`selected_grid.json`可直接供6k实验入口复跑。完整库表及知识命中相同、P95差异不超过64 tokens时视为持平，优先保留匹配种子的参数；避免依据几个token改变生产配置。

最终程序指标优先候选为`quota_t8_k4_e0`：Schema候选8、全局knowledge4、案例0；BM25/embedding候选各50，RRF60，重排50；compact/terse，最大输入6000。252题完整库252/252、完整表248/252；已审知识缺口7/8。knowledge18方案补到8/8，但完整表降到243/252。该建议须与SQL生成质量分开解释。

收到本轮明确授权后，23题×4方案的92个DeepSeek任务已执行，共93次调用，服务端输入最大5010 tokens，零超限、零用量缺失。三个新方案各23/23生成通过静态校验的答案；旧基线21/23，两题因追加对话后本地估算超预算停止。

Codex逐题静态业务复核：固定8题子集四方案均仅确认3题满足，已知7题从基线0题提升至知识18/知识4/原值域方案4/4/5题，旧4题回归为2/1/2/1题。新主验收同系统跨业务库为0/3，跨系统为0/2（其中自持力格式1题未决）。因此尚未证明当前覆盖率优先方案能提高SQL总体质量；不将表覆盖率当执行准确率。具体依据见产物目录的`sql_quality_report.md`和`inference/sql_evaluation/semantic_reviews.json`；没有业务库执行或独立人工/外部LLM裁判。

实际提示词全部保存在`inference/sql_prompt_previews/`，`audit_6k_generation.py`用于生成结束后逐次验证服务端`usage.prompt_tokens`和本地初次/修复估算。程序覆盖率不能替代最终语义准确率。

```bash
python evaluation/prompt_quality/iteration_6k.py prepare --output outputs/experiments/prompt-quality-6k-v1
python evaluation/prompt_quality/iteration_6k.py run \
  --public outputs/experiments/prompt-quality-6k-v1/public \
  --output outputs/experiments/prompt-quality-6k-v1/inference \
  --embedding-model /path/to/Qwen3-Embedding-0.6B \
  --reranker-model /path/to/Qwen3-Reranker-0.6B --device cuda:0 --dtype bfloat16
python evaluation/prompt_quality/iteration_6k.py score \
  --public outputs/experiments/prompt-quality-6k-v1/public \
  --private outputs/experiments/prompt-quality-6k-v1/private_evaluation \
  --output outputs/experiments/prompt-quality-6k-v1/inference
python evaluation/prompt_quality/iteration_6k.py select \
  --public outputs/experiments/prompt-quality-6k-v1/public \
  --output outputs/experiments/prompt-quality-6k-v1/inference \
  --expansion-grid outputs/experiments/prompt-quality-6k-v1/stage_b_grid.json
python evaluation/prompt_quality/sql_experiment.py prepare \
  --public outputs/experiments/prompt-quality-6k-v1/public \
  --output outputs/experiments/prompt-quality-6k-v1/inference \
  --diagnostic-ids 171,395,441,935,1038,1050,2125,2462,2487,2908,3012 \
  --input-limit 6000
```
