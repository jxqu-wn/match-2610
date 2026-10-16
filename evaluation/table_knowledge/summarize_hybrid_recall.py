"""Expand a finished retrieval report into per-table metrics without inference."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


def summarize(directory: Path) -> None:
    raw = (directory / "report.json").read_bytes()
    report = json.loads(raw)
    rows = []
    summary = {}
    for corpus, run in report["corpora"].items():
        summary[corpus] = {}
        for method, scores in run["metrics"].items():
            totals = {"tp": 0, "fp": 0, "fn": 0, "unjudged": 0}
            violating = zero_with_noise = 0
            for table in scores["12"]["per_table"]:
                tp, fp, fn = (len(table[key]) for key in ("matched", "extra_judged", "missing"))
                passed = fp <= 2 * tp
                violating += not passed
                zero_with_noise += tp == 0 and fp > 0
                for key, value in (("tp", tp), ("fp", fp), ("fn", fn)):
                    totals[key] += value
                totals["unjudged"] += len(table["unjudged"])
                rows.append(
                    {
                        "corpus": corpus, "method": method, "table_id": table["table_id"],
                        "tp": tp, "fp": fp, "fn": fn, "unjudged_count": len(table["unjudged"]),
                        "precision_on_judged": tp / (tp + fp) if tp + fp else None,
                        "recall": tp / (tp + fn) if tp + fn else None,
                        "f1_on_judged": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None,
                        "unrelated_per_effective": fp / tp if tp else None,
                        "passes_200_percent_noise_target_on_judged": passed,
                        "zero_effective_with_judged_noise": tp == 0 and fp > 0,
                        **{key: ";".join(map(str, table[key])) for key in
                           ("matched", "extra_judged", "missing", "unjudged", "ranking")},
                    }
                )
            if any(totals[key] != scores["12"][key] for key in totals):
                raise ValueError("Per-table counts differ from aggregate scores")
            score = scores["12"]
            summary[corpus][method] = {
                "unrelated_per_effective": score["fp"] / score["tp"] if score["tp"] else None,
                "passes_200_percent_noise_target_on_judged": score["fp"] <= 2 * score["tp"],
                "violating_tables_on_judged": violating,
                "zero_effective_with_judged_noise_tables": zero_with_noise,
            }
    with (directory / "per_table_metrics.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    result = {
        "source_report_sha256": hashlib.sha256(raw).hexdigest(),
        "summarizer_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "cutoff": 12,
        "scope": "candidate_ranking_projection_only_not_confirmed_associations",
        "unjudged_is_excluded_from_noise_counts": True,
        "summary": summary,
    }
    (directory / "noise_summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# 结果解读与逐表比较", "",
        "比较重排前后的已有正例召回、精度和未标注比例；数值仅对应当前报告中的模型组合。", "",
        "| 语料 | 目标关联 | RRF 命中@12 | 重排命中@12 | Recall 提升 | RRF 前50候选覆盖 |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for corpus, run in report["corpora"].items():
        before = run["metrics"]["rrf"]["12"]
        after = run["metrics"]["rrf_rerank"]["12"]
        ceiling = run["metrics"]["rrf"]["50"]
        lines.append(
            f"| {corpus} | {run['target_pairs']} | {before['tp']} | {after['tp']} | "
            f"{(after['recall'] - before['recall']) * 100:.2f} 个百分点 | "
            f"{ceiling['tp']}/{run['target_pairs']}（{ceiling['recall']:.2%}） |"
        )
    current = report["corpora"]["current_1833"]
    before = current["metrics"]["rrf"]["12"]
    after = current["metrics"]["rrf_rerank"]["12"]
    ceiling = current["metrics"]["rrf"]["50"]
    lines += [
        "", f"新版{current['target_pairs']}个已知正例中，{ceiling['tp']}个进入RRF前50；重排将其中{after['tp']}个放入前12。",
        "新版的候选覆盖仍有明显提升空间；新增与改写知识需补充独立标注。",
        f"新版已标注预测的 precision 为 {before['precision_on_judged']:.2%} → {after['precision_on_judged']:.2%}，"
        f"F1为 {before['f1_on_judged']:.2%} → {after['f1_on_judged']:.2%}；",
        f"未标注返回为 {before.get('unjudged', 0)} → {after.get('unjudged', 0)}。其余返回尚无可靠真值，不作为负例。", "",
        "## 候选与确认关联的区别", "",
        "本实验对所有72张表固定返回前12，包含参考中零关联的表。Top-K是供后续筛选的候选，",
        "不能直接作为预处理的确认关联。若按确认关联验收，旧版重排结果的多关联/命中为",
        f"{summary['frozen_247']['rrf_rerank']['unrelated_per_effective']:.2%}，超过200%要求；",
        "逐表不达标项和零命中但存在多关联的表见 noise_summary.json 与 per_table_metrics.csv。",
        f"新版噪声指标只覆盖{current['judged_knowledge_count']}条原文未变知识，不能据此宣布新版全量通过验收。", "",
        "## 运行边界", "",
        "输入是原始表结构，候选知识全局竞争，没有使用人工表关联过滤。",
        "本实验不提供逐题问题召回或最终查询正确率结论。",
        "所有问题向量先批量编码；两套语料共享相同文本的重排分数缓存。",
        f"实际计算重排 {report['reranker_computed_pairs']} 对，缓存命中 {report['reranker_cached_pairs']} 对；",
        "报告中的耗时是离线批处理时间，不能直接当作在线单请求延迟。", "",
        "测试及环境执行记录见 execution/。",
        "BF16向量在写缓存前以float32再次归一化，修复真实模型测试暴露的单位向量误差。", "",
        "复现派生表：`python evaluation/table_knowledge/summarize_hybrid_recall.py --run-dir <结果目录>`。", "",
    ]
    (directory / "COMPARISON.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    summarize(parser.parse_args().run_dir)
