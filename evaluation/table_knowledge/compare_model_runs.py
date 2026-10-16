"""Compare finished model runs with identical inputs and retrieval parameters."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def compare(baseline: Path, candidate: Path, output: Path) -> None:
    if output.exists():
        raise ValueError("Choose a new comparison directory")
    base, trial = (read(path / "report.json") for path in (baseline, candidate))
    for key in ("benchmark", "input_sha256", "recall_parameters", "environment", "python"):
        if base[key] != trial[key]:
            raise ValueError("Runs differ in " + key)
    base_parameters = {k: v for k, v in base["parameters"].items() if k != "output_dir"}
    trial_parameters = {k: v for k, v in trial["parameters"].items() if k != "output_dir"}
    if base_parameters != trial_parameters:
        raise ValueError("Inference parameters differ")
    base_code = {k: v for k, v in base["code_sha256"].items() if k.startswith("src/")}
    trial_code = {k: v for k, v in trial["code_sha256"].items() if k.startswith("src/")}
    if base_code != trial_code:
        raise ValueError("Production retrieval implementations differ")
    for signature, fields in (
        ("embedding_signature", ("instruction", "max_length", "device", "dtype", "normalize", "normalization_dtype", "document_prompt", "encoding_protocol")),
        ("reranker_signature", ("instruction", "max_length", "device", "dtype", "batch_size", "score_type")),
    ):
        for field in fields:
            if base[signature].get(field) != trial[signature].get(field):
                raise ValueError(f"Runs differ in {signature}.{field}")
    rows = []
    for corpus, run in base["corpora"].items():
        other = trial["corpora"][corpus]
        for key in ("knowledge_count", "judged_knowledge_ids", "target_pairs", "table_count", "nonempty_tables"):
            if run[key] != other[key]:
                raise ValueError(f"Runs differ in {corpus}.{key}")
        ranking_files = [path / f"{corpus}.rankings.jsonl" for path in (baseline, candidate)]
        rankings = [[json.loads(line) for line in path.read_text().splitlines()] for path in ranking_files]
        if [(r["table_id"], r["rankings"]["bm25"]) for r in rankings[0]] != [
            (r["table_id"], r["rankings"]["bm25"]) for r in rankings[1]
        ]:
            raise ValueError("BM25 control rankings differ")
        for method, scores in run["metrics"].items():
            for cutoff in ("1", "3", "5", "8", "12", "20", "50"):
                left, right = scores[cutoff], other["metrics"][method][cutoff]
                row = {"corpus": corpus, "method": method, "cutoff": int(cutoff)}
                for metric in ("tp", "fp", "fn", "unjudged", "precision_on_judged", "recall", "f1_on_judged", "mrr_nonempty", "known_positive_ndcg_nonempty", "judged_fraction"):
                    row["baseline_" + metric] = left.get(metric)
                    row["candidate_" + metric] = right.get(metric)
                row["recall_delta_percentage_points"] = (right["recall"] - left["recall"]) * 100
                rows.append(row)
    output.mkdir(parents=True)
    with (output / "metrics.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    result = {
        "baseline": str(baseline), "candidate": str(candidate),
        "source_sha256": {label: hashlib.sha256((path / "report.json").read_bytes()).hexdigest()
                          for label, path in (("baseline", baseline), ("candidate", candidate))},
        "production_code_equal": True, "identical_bm25_control": True,
        "baseline_hardware": base["hardware"], "candidate_hardware": trial["hardware"],
        "baseline_embedding_seconds": base["embedding_seconds"],
        "candidate_embedding_seconds": trial["embedding_seconds"],
        "baseline_ranking_seconds": sum(r["ranking_seconds"] for r in base["corpora"].values()),
        "candidate_ranking_seconds": sum(r["ranking_seconds"] for r in trial["corpora"].values()),
        "rows": rows,
    }
    (output / "comparison.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    names = [" + ".join(Path(report[key]["model_path"]).name for key in ("embedding_signature", "reranker_signature"))
             for report in (base, trial)]
    lines = ["# 模型规模对照", "", f"基线：{names[0]}。", f"实验：{names[1]}。", "",
             "原始数据、标签、任务指令、精度、batch、截断长度、召回深度和生产代码均一致；BM25完整排序一致。",
             "本实验为表结构→知识候选排序，新增或改写知识保持未标注。", "",
             "| 语料 | 方法 | 基线 Recall@12 | 实验 Recall@12 | 差值（百分点） | 基线 P@12* | 实验 P@12* |",
             "| --- | --- | ---: | ---: | ---: | ---: | ---: |"]
    for row in rows:
        if row["cutoff"] == 12:
            lines.append(
                f"| {row['corpus']} | {row['method']} | {row['baseline_recall']:.2%} | {row['candidate_recall']:.2%} | "
                f"{row['recall_delta_percentage_points']:+.2f} | {row['baseline_precision_on_judged']:.2%} | {row['candidate_precision_on_judged']:.2%} |"
            )
    lines += ["", "*新版precision/F1仅对已标注返回计算，不能作为新版全量精度。", "",
              "| 资源 | 基线 | 实验 |", "| --- | ---: | ---: |",
              f"| GPU allocated峰值（GiB） | {base['hardware']['peak_allocated_gib']:.2f} | {trial['hardware']['peak_allocated_gib']:.2f} |",
              f"| GPU reserved峰值（GiB） | {base['hardware']['peak_reserved_gib']:.2f} | {trial['hardware']['peak_reserved_gib']:.2f} |",
              f"| 批量向量编码（秒） | {base['embedding_seconds']:.2f} | {trial['embedding_seconds']:.2f} |",
              f"| 两套语料排序合计（秒） | {result['baseline_ranking_seconds']:.2f} | {result['candidate_ranking_seconds']:.2f} |", "",
              "耗时包含离线批处理和同文本重排缓存复用，不能直接等同在线单请求延迟或纯模型吞吐。",
              "本次同时替换embedding与reranker，差异反映组合方案；尚未做组件交叉替换的独立归因。",
              "不同Top-K的precision、recall、F1、MRR、nDCG及来源哈希见 metrics.csv、comparison.json；逐表明细见各自运行目录。", ""]
    (output / "README.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    compare(args.baseline, args.candidate, args.output_dir)
