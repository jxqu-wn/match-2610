"""Render the frozen validation trace and schema-expansion control for review."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def episodes(root, qid):
    record = read(root / f"question_{qid}.json")
    rows = []
    folder = root / "cases" / str(qid) / "06_generation"
    for index, path in enumerate(sorted(folder.glob("request_*.json"))):
        request = read(path)
        context = json.loads(request["messages"][1]["content"])
        schemas = {t["table_id"] for t in context["candidate_tables"]}
        for message in request["messages"][2:]:
            if message["role"] != "user":
                continue
            try:
                value = json.loads(message["content"])
            except ValueError:
                continue
            schemas.update(t["table_id"] for t in value.get("additional_schemas", []))
        response = read(folder / path.name.replace("request_", "response_"))
        output = json.loads(response["raw"])
        answer = output.get("answer", {})
        rows.append({"request": path.name, "available_schema_count": len(schemas),
                     "declared_total_tables_budget": context["retrieval_budget"]["total_tables"],
                     "estimated_input_tokens": record["trace"][index]["estimated_input_tokens"],
                     "status": output.get("status"),
                     "engines": [answer[key] for key in ("db", "db1", "db2", "db3") if key in answer],
                     "validation_errors": record["trace"][index].get("validation_errors", [])})
    return rows


def case_report(root, qid, note):
    folder = root / "cases" / str(qid)
    evaluation = read(folder / "07_offline_evaluation.json")
    route = read(folder / "01_routing.json")
    context = read(folder / "03_context_before_budget.json")
    calls = episodes(root, qid)
    dump(folder / "08_request_lineage.json", calls)
    lines = [f"# 验证案例 {qid}", "", evaluation["question"], "",
             "## 路由与初始证据", "", "预测系统：" + "、".join(route["predicted_engines"]), "",
             "| 分类标签 | 概率 |", "| --- | ---: |"]
    lines.extend(f"| {label} | {prob:.4f} |" for label, prob in route["class_probabilities"].items())
    lines += ["", "| Schema | BM25排名 | 向量排名 | RRF | 重排分 |", "| --- | ---: | ---: | ---: | ---: |"]
    for table in context["candidate_tables"]:
        hit = table["retrieval_evidence"]
        lines.append(f"| {table['table_id']} | {hit.get('keyword_rank', '—')} | {hit.get('semantic_rank', '—')} | "
                     f"{hit.get('rrf_score', '—')} | {hit.get('rerank_score', '—')} |")
    lines += ["", f"知识 {len(context['knowledge'])} 条，训练案例 {len(context['examples'])} 条。",
              "未显示的原候选池边界不能由历史文件完整还原；可核对选中证据的原始分数，以及曾被重排的候选文档并集。", "",
              "## 实际生成及修复", "", "| 请求 | 累计Schema数 | 输入token估算 | 输出系统 | 静态错误 |",
              "| --- | ---: | ---: | --- | --- |"]
    for call in calls:
        lines.append(f"| [{call['request']}](06_generation/{call['request']}) | {call['available_schema_count']} | "
                     f"{call['estimated_input_tokens']} | {' → '.join(call['engines'])} | "
                     f"{'; '.join(call['validation_errors']) or '通过'} |")
    lines += ["", "## 结果与参考对照", "",
              "参考所需表：" + "、".join(evaluation["expected"]["table_ids"]), "",
              f"提示词完整表覆盖：{evaluation['prompt_table_coverage']['complete']}；"
              f"最终完整表覆盖：{evaluation['final_table_coverage']['complete']}；"
              f"静态通过：{evaluation['static_validation_passed']}。", "",
              "```json", json.dumps(evaluation["answer"], ensure_ascii=False, indent=2), "```", "",
              "模型 assumptions：", "", "```json", json.dumps(evaluation["assumptions"], ensure_ascii=False, indent=2), "```", "",
              "## 人工离线诊断", "", note, "",
              "上述覆盖与静态检查不等同于结果集等价；未执行真实数据库。", "",
              "[路由](01_routing.json) · [裁剪前](03_context_before_budget.json) · [裁剪后](04_context_after_budget.json) · "
              "[初始完整消息](05_initial_messages.json) · [评价明细](07_offline_evaluation.json) · [请求轨迹](08_request_lineage.json)", ""]
    (folder / "README.md").write_text("\n".join(lines), encoding="utf-8")
    return calls


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--notes", type=Path, default=Path("evaluation/federation_trace/case_notes_v1.json"))
    args = parser.parse_args()
    root = args.input
    control = root / "schema_expansion_control"
    notes = read(args.notes)
    assert sha(root / "generated_answers.json") == notes["binding"]["baseline_answers_sha256"]
    assert sha(control / "generated_answers.json") == notes["binding"]["control_answers_sha256"]
    manifest = read(root / "manifest.json")
    baseline_summary, control_summary = read(root / "summary.json"), read(control / "summary.json")
    baseline_details = [json.loads(line) for line in (root / "evaluation/details.jsonl").read_text().splitlines()]
    control_ids = {r["question_id"] for r in read(control / "questions.json")}
    all_episodes, first_control_errors = [], 0
    for row in baseline_details:
        qid = row["question_id"]
        all_episodes.extend(case_report(root, qid, notes["notes"][str(qid)]["baseline"]))
        if qid in control_ids:
            calls = case_report(control, qid, notes["notes"][str(qid)]["control"])
            all_episodes.extend(calls)
            first_control_errors += bool(calls[0]["validation_errors"])
    request_checks = []
    train_ids = {r["question_id"] for r in read(root / "retrieval_train.json")}
    val_ids = {r["question_id"] for r in read(root / "validation.json")}
    for base in (root, control):
        for question in read(base / "questions.json"):
            qid = question["question_id"]
            initial = read(base / "cases" / str(qid) / "05_initial_messages.json")
            actual = read(base / "cases" / str(qid) / "06_generation/request_01.json")["messages"]
            assert initial == actual
            for path in (base / "cases" / str(qid) / "06_generation").glob("request_*.json"):
                messages = read(path)["messages"]
                context = json.loads(messages[1]["content"])
                examples = {item["question_id"] for item in context["examples"]}
                assert examples <= train_ids and not examples & val_ids
                request_checks.append(str(path.relative_to(root)))
    usage, calls = {}, []
    for base in (root, control):
        for path in base.glob("question_[0-9]*.json"):
            calls.extend(read(path)["calls"])
    for call in calls:
        for name, value in call.get("usage", {}).items():
            if isinstance(value, int):
                usage[name] = usage.get(name, 0) + value
    comparison = {"baseline": baseline_summary, "schema_expansion_control": control_summary,
                  "control_first_response_static_failure_cases": first_control_errors,
                  "maximum_supplied_schema_tables": max(call["available_schema_count"] for call in all_episodes),
                  "declared_schema_budget": 12, "request_snapshots": len(request_checks),
                  "model_request_attempts": len(calls), "successful_model_requests": sum(c["success"] for c in calls),
                  "usage": usage, "initial_payloads_equal_actual_requests": True,
                  "all_retrieved_examples_are_training_only": True, "execution_accuracy": None}
    dump(root / "comparison.json", comparison)
    text = ["# 跨系统验证案例全流程跟踪", "",
            "主要瓶颈已复现：初始路由遗漏MySQL后，相关Schema在重排前被排除；模型省略或替换需求仍被静态校验接受。补充Schema后可恢复库表覆盖，但跨系统规划、需求验收和SQL语义仍需分别处理。", "",
            "## 数据划分与样本", "",
            f"使用有标注的QA_train.json共2839题，沿用seed=42的冻结90/10划分：训练{manifest['train_rows']}题、验证{manifest['validation_rows']}题。"
            f"训练侧移除{manifest['excluded_train_text_duplicates']}条与验证题同文本的记录，路由和检索仅使用{manifest['effective_training_rows']}题。",
            "抽取验证集中全部9道MySQL↔PostgreSQL案例，未按模型成败筛选。该验证集已用于此前开发评估，不是新独立测试集。",
            "参考SQL仅在生成结束后的独立评价阶段解析，不进入模型请求。原680题result.json保持不变。", "",
            "## 实验结果", "", "| 指标 | 原流程9题 | 原流程中4道遗漏MySQL的题 | 补Schema后的4题 |",
            "| --- | ---: | ---: | ---: |", "| 初始完整库表覆盖 | 5/9 | 0/4 | 4/4 |",
            "| 最终完整库表覆盖 | 5/9 | 0/4 | 4/4 |", "| 最终静态校验通过 | 9/9 | 4/4 | 4/4 |",
            "| 实际生成请求 | 9 | 4 | 9（含5次修复） |", "",
            "这里的完整覆盖只比较参考所需系统和表是否出现，不代表SQL业务正确或执行成功。", "",
            "```mermaid", "flowchart TD", '  A[验证集284题] --> B[全部跨系统案例9题]',
            '  B --> C[路由两系统5题]', '  B --> D[路由仅PG 4题]',
            '  C --> E[两侧Schema完整]', '  D --> F[MySQL Schema未进入召回]',
            '  F --> G[省略公司或船长条件 / 自持力误换吃水]',
            '  E --> H[静态校验通过]', '  G --> H', '  H --> I[9题都结束生成 但仅5题表覆盖完整]', "```", "",
            "## 逐题入口", "", "| ID | 初始路由 | 初始表覆盖 | 最终表覆盖 | 主要观察 |",
            "| --- | --- | --- | --- | --- |"]
    for row in baseline_details:
        qid = row["question_id"]
        text.append(f"| [{qid}](cases/{qid}/README.md) | {'+'.join(row['predicted_engines'])} | "
                    f"{row['prompt_table_coverage']['complete']} | {row['final_table_coverage']['complete']} | {notes['notes'][str(qid)]['baseline']} |")
    text += ["", "## Schema扩展对照", "",
             "选择全部初始单系统路由案例2942、2970、2972、2980，不读取参考SQL挑选表。"
             "按原问题文本对全目录做关键词排名，最多补4张其他系统Schema，并更新searched_databases元信息。"
             "初始system提示词、模型、问题、知识、训练案例和relations保持一致，未给模型参考答案。",
             "后续仍执行同一生成/校验/修复策略。4题首轮都把MySQL表写进PG查询，静态校验拒绝后才逐步修正为分步协议。"
             "因此此对照说明Schema入口和既有修复策略共同恢复了结构覆盖，不能表述为补表后首次生成即全部正确。", "",
             "| 案例 | 对照轨迹 | 最终结构覆盖 |", "| --- | --- | --- |"]
    for qid in sorted(control_ids):
        calls_for_case = episodes(control, qid)
        counts = " → ".join(str(row["available_schema_count"]) for row in calls_for_case)
        text.append(f"| [{qid}](schema_expansion_control/cases/{qid}/README.md) | {len(calls_for_case)}次请求；Schema累计{counts} | 完整 |")
    text += ["", "## 已定位的问题", "",
             "1. **路由硬过滤**：4个错误路由案例的历史重排池均只有1张PG表；MySQL表并非重排分数低，而是没有参与本次候选评分。",
             "2. **需求不完整仍被接受**：2942省略公司条件，2970省略船长条件，2972/2980把自持力换为吃水；这4题首轮都返回complete，且静态无错，所以未触发补充召回。",
             "3. **跨系统计划不可靠**：即使补全两侧Schema，4题首轮仍混写两个系统的表；修复依赖表归属校验反馈。生成前需要明确系统分工和中间结果协议。",
             "4. **累计预算未统一执行**：上下文声明最多12表，生成器却按每次最多12表补充；2942在对照修复时累计达到29表，增加噪声和预算风险。",
             "5. **表覆盖和语法不能代替语义验收**：2950缺少参考中的按MMSI分组，3012仅输出公司名而非参考船舶记录。", "",
             "对照仍有语义问题：2942在构造轨迹前删除区域外的点，可能漏掉穿过区域但采样端点在区域外的线段；"
             "控制查询还将result当成临时表，外部协议兼容性未知。2980对MySQL使用`SUBSTRING(endurance FROM '^[0-9]+')`，"
             "其FROM后是位置参数，不能实现模型声称的正则提取。"
             "参见[MySQL SUBSTRING](https://dev.mysql.com/doc/refman/8.0/en/string-functions.html)与"
             "[REGEXP_SUBSTR](https://dev.mysql.com/doc/refman/8.0/en/regexp.html)。", "",
             "## 跟踪边界与检查", "",
             "检索阶段重放已冻结0.6B结果，未重新运行embedding/reranker。选中证据保留原BM25、向量、RRF、重排值；"
             "历史缓存可还原已重排文档并集，但未保存的每次原始Top50边界不能补造。API生成与修复为本次真实调用。",
             "18次实际请求均保存完整消息与响应；初始请求与预备消息逐字一致，全部检索案例ID属于训练集且与验证ID无交集。"
             "3项离线测试覆盖参考隔离、凭证不落盘及字段校验盲点。",
             "未连接MySQL/PG执行，无真实结果集、执行正确率或外部分数；9题样本和表覆盖不能推算680题新成绩。", "",
             "建议优先：将路由改为可扩展的候选优先级；生成前形成需求→字段→系统→步骤计划；"
             "把需求缺失和语义替换作为拒绝完成条件；统一全流程表数与token预算；进一步检查结果传递、输出粒度、单位与函数语义。", "",
             "[划分清单](split_manifest.json) · [实验清单](manifest.json) · [汇总](comparison.json) · "
             "[逐题CSV](evaluation/overview.csv) · [输入案例](questions.json) · [离线参考SQL](evaluation/reference_answers.json)", ""]
    (root / "README.md").write_text("\n".join(text), encoding="utf-8")
    print(json.dumps({"report": str(root / "README.md"), "requests": len(request_checks),
                      "maximum_schema_tables": comparison["maximum_supplied_schema_tables"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
