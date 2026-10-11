# 微调模型推理生成 result.json

本目录脚本面向「用 `tmp/train.json` 训练得到的微调模型」的推理流程。它做三件事：

1. 按 `tmp/train.json` 的 `instruction` / `input` 格式，为每个测试问题程序化构造提示；
2. 通过 OpenAI 兼容 HTTP 接口连接微调模型；
3. 将模型输出规范化为竞赛要求的 `result.json`。

## 输入与产物

- 测试问题：`data/赛题8/QA_test.json`（400 题）。
- Schema 目录：`data/preprocessed/schema_catalog.json`。
- 路由与检索复用：
  - 引擎集合分类器：`outputs/qa_test_deepseek_v4_pro_full_train/routing_full_train/`
  - 全量训练集检索索引：`outputs/qa_test_deepseek_v4_pro_full_train/index_full_train/`
- 每题的 `prepared_{id}.json` 与 `question_{id}.json` 写入 `--output-dir`，可断点续跑。
- 最终写入 `--result-path`（默认项目根目录 `result.json`）。

## 运行

微调模型需以 OpenAI 兼容方式部署（vLLM / SGLang 等），例如：

```bash
# 假设 vLLM 在 8000 端口提供 /v1/chat/completions
.venv/bin/python scripts/finetuned_inference/generate_submission.py \
  --endpoint http://127.0.0.1:8000/v1/chat/completions \
  --model your-finetuned-model \
  --output-dir outputs/finetuned_inference
```

先只构造提示（不调用模型），用于检查 instruction/input：

```bash
.venv/bin/python scripts/finetuned_inference/generate_submission.py \
  --prepare-only --limit 10
```

只跑前 5 题、避免覆盖已有提交文件：

```bash
.venv/bin/python scripts/finetuned_inference/generate_submission.py \
  --limit 5 --result-path outputs/finetuned_inference/result.json
```

## 主要参数

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `--endpoint` | `http://127.0.0.1:8000/v1/chat/completions` | OpenAI 兼容 chat 接口 |
| `--model` | `finetuned-model` | 服务端模型名 |
| `--api-key` | 空 | 可选，Bearer 鉴权（或 `FINETUNED_API_KEY`） |
| `--prompt-style` | `chat` | `chat` 用 system=instruction + user=input；`alpaca` 用 `### Instruction/Input/Response` 模板 |
| `--recall` | `examples` | 表召回策略，见下 |
| `--max-tables` | `6` | 单题最多注入的表数量 |
| `--example-k` | `3` | `--recall examples` 时参考的最近训练样例数 |
| `--workers` | `8` | 并发请求数 |
| `--device` / `--dtype` | `cuda` / `float16` | 复用检索与路由编码器的推理设备 |
| `--prepare-only` | 否 | 只构造提示不调用模型 |
| `--limit` | `0`（全部） | 只处理前 N 题，便于冒烟测试 |

## instruction/input 构造说明

`tmp/train.json` 每条为 `{instruction, input, output}`。其中：

- `input` 即问题文本；
- `instruction` 由「固定导语 + 输出指令 + 涉及数据源/数据库 + 官方表结构 DDL」组成；
- DDL 取自 `schema_catalog.json` 的 `raw_definition`，去掉 `ENGINE=...` / `COMMENT='...'` 尾部后以 `);` 结尾；
- Elasticsearch 表使用 `medical_institutions mapping: {...}` 紧凑映射行；
- 跨数据源（`MYSQL|POSTGRESQL`）使用两步 JSON 输出指令，`db1/db2` 顺序由最近训练样例的查询顺序决定；
- 表块顺序按外键依赖排列（事实表在前、被引用字典表在后），与训练提示一致。

## 表召回策略

- `--recall examples`（默认）：取最近 `--example-k` 个训练样例，以最近样例所属数据库集合为准合并其真实表集合。该策略最贴近微调提示分布，对单库问题更稳。
- `--recall schema`：复用 `scripts/information_retrieval` 的有界 schema/关键词检索与一跳外键补充，对跨库、跨域问题召回更全，但会带更多无关候选表。

两种策略都不读测试集答案；召回质量可在 `validation.json` 上进一步评估。

## 注意事项

- 本脚本默认覆盖项目根目录 `result.json`；调试时请用 `--result-path` 指定其他路径。
- 复用索引与分类器要求 `--device` / `--dtype` 与建索引时一致（当前为 `cuda` / `float16`）。若在纯 CPU 环境运行，需先重建对应缓存，或改用 `route_question.py` 等纯标准库路由。
- 微调模型不在本仓库内，脚本只负责连接部署好的服务。
