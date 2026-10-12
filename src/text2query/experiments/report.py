"""把 SQLite-50 实验结果渲染为 Markdown 报告。"""

from __future__ import annotations

from typing import Any

from .sqlite50 import run  # noqa: F401  (便于 `from text2query.experiments.report import ...` 时同包可用)


def render_report(
    report: dict[str, Any],
    *,
    title: str,
    setup_lines: list[str],
    equivalent: set[int],
    partial: set[int],
    reasons: dict[int, str],
    findings: list[str],
    reproduce: str,
) -> str:
    metrics = report["metrics"]
    per_question = {item["question_id"]: item for item in report["per_question"]}
    total = metrics["count"]

    def verdict(qid: int) -> str:
        if qid in equivalent:
            return "一致"
        if qid in partial:
            return "部分一致"
        return "不一致"

    counts = {"一致": 0, "部分一致": 0, "不一致": 0}
    for qid in per_question:
        counts[verdict(qid)] += 1

    def pct(value: float | None) -> str:
        return f"{value * 100:.1f}%" if value is not None else "—"

    lines: list[str] = [f"# {title}\n"]
    lines.extend(setup_lines)
    lines.append("")
    lines.append("## 一、总体指标\n")
    lines.append("| 指标 | 数值 |")
    lines.append("| --- | ---: |")
    lines.append(f"| 数据库类型正确率 | {pct(metrics['engine_accuracy'])}（{round((metrics['engine_accuracy'] or 0) * total)}/{total}） |")
    lines.append(
        f"| 提示词完整业务库覆盖率 | {pct(metrics['prompt_complete_db_coverage_rate'])}"
        f"（{round((metrics['prompt_complete_db_coverage_rate'] or 0) * total)}/{total}） |"
    )
    lines.append(
        f"| 提示词完整业务表覆盖率 | {pct(metrics['prompt_complete_table_coverage_rate'])}"
        f"（{round((metrics['prompt_complete_table_coverage_rate'] or 0) * total)}/{total}） |"
    )
    lines.append(f"| 提示词业务库召回率 | {pct(metrics['prompt_db_recall'])} |")
    lines.append(f"| 提示词业务表召回率 | {pct(metrics['prompt_table_recall'])} |")
    lines.append(f"| 生成 SQL 可解析率 | {pct(metrics['generated_parse_rate'])} |")
    lines.append(f"| 生成 SQL 业务库完全正确率 | {pct(metrics['generated_db_exact_rate'])} |")
    lines.append(f"| 生成 SQL 业务库 召回/精确 | {pct(metrics['generated_db_recall'])} / {pct(metrics['generated_db_precision'])} |")
    lines.append(f"| 生成 SQL 业务表完全正确率 | {pct(metrics['generated_table_exact_rate'])} |")
    lines.append(
        f"| 生成 SQL 业务表 召回/精确 | {pct(metrics['generated_table_recall'])} / {pct(metrics['generated_table_precision'])} |"
    )
    lines.append("")
    lines.append("说明：业务库/业务表“完全正确率”要求集合完全相等；召回率=参考集合被覆盖比例，精确率=生成集合中属于参考的比例。")
    lines.append("")

    lines.append("## 二、SQL 与验证集答案一致性（人工复核）\n")
    lines.append(
        "判定口径：**一致**=结果集等价（允许别名/大小写/等价改写）；**部分一致**=核心表与条件正确但存在多余连接、"
        "DISTINCT、字面量大小写等可能影响结果或重复行的差异；**不一致**=缺表/多错表、条件或字段错误、逻辑偏离、无法解析。\n"
    )
    lines.append("| 结论 | 题数 | 占比 |")
    lines.append("| --- | ---: | ---: |")
    for key in ("一致", "部分一致", "不一致"):
        lines.append(f"| {key} | {counts[key]} | {counts[key] / total * 100:.0f}% |")
    lines.append("")
    lines.append("| 题号 | 库表标签 | 一致性 | 说明 |")
    lines.append("| ---: | --- | --- | --- |")
    for qid in sorted(per_question):
        match = per_question[qid]["generated_table_match"]
        tag = "EXACT" if match["exact"] else ("MISS" if match["missing"] else "EXTRA")
        lines.append(f"| {qid} | {tag} | {verdict(qid)} | {reasons.get(qid, '')} |")
    lines.append("")

    lines.append("## 三、关键发现\n")
    for index, finding in enumerate(findings, 1):
        lines.append(f"{index}. {finding}")
    lines.append("")

    lines.append("## 四、复现\n")
    lines.append("```bash")
    lines.append(reproduce)
    lines.append("```")
    return "\n".join(lines) + "\n"
