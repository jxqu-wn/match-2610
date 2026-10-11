# QA_test 完整生成报告

- 模型：DeepSeek v4 pro，API响应模型标识全部为 deepseek-v4-pro。
- 数据：全部400道 QA_test.json；检索索引和分类器使用完整5830条 QA_train.json。正式测试不使用分割后的训练子集，原验证实验索引不变。
- 索引：265张schema、1800条知识、5830条训练案例。首轮上下文实际使用1320个不同训练案例，其中106个来自此前分割的验证子集；对正式测试而言它们属于合法完整训练集。
- 文件：项目根目录 result.json，UTF-8 JSON数组；388道单系统、12道多系统，题号唯一、完整、顺序与测试集一致。
- 静态检查：400/400通过；SQL语法、真实库表及可解析的限定字段、只读语句、DSL JSON、跨系统result占位符。35项单元测试通过。
- 执行准确率：未知，没有评测数据库，未执行SQL或DSL、未提交平台。静态检查通过不代表语义或执行正确。

## 预算及消耗

最终采用的400题结果对应405次调用，均满足实际输入token加3000输出预留不超过24000；最大单次实际输入13430。最终每题含修复平均7349.15 token，P95=10536.15，最大24426，后者是多次调用之和。

完整训练集批次连同失败、修复及已替换的超预算尝试，共420次调用，输入3562825、输出87496、合计3650321 token。初版补充整个系统schema超预算，2990、3684、5028已按预算重跑，原调用完整保留并计费；最终流程按缺口文本检索完整表schema，最多补充12张，逐表检查预算，不截断字段。

用户更正训练数据范围前的分割训练集批次共434次调用、3152638 token，其全部结果不进入最终文件。本任务两个批次累计854次调用、6802959 token。

## 复现与产物

密钥通过DEEPSEEK_API_KEY注入，不写入源码或产物。生成使用非思考模式、temperature=0、输出最多3000 token；分步查询和歧义说明由DeepSeek生成，无人工答案标注。字段缺口匹配仅按真实catalog中的字段名称、库表及系统归属，不加入人工业务判断。

```bash
.venv/bin/python scripts/information_retrieval/generate_submission.py --prepare-only
.venv/bin/python scripts/information_retrieval/generate_submission.py --workers 8
.venv/bin/python scripts/information_retrieval/audit_submission.py
```

中间结果位于 outputs/qa_test_deepseek_v4_pro_full_train/，包括独立完整训练索引、分类器、prepared上下文、question逐题响应、retry_history历史调用、report token汇总、billing_summary两个批次消耗、submission_audit提交检查及代码指纹。

结果SHA256：4fd58479a1078e7904d9b3c79e7d6a8d76fc5ead76310e9748c32046db7072ef。
