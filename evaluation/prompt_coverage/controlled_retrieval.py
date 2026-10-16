"""Hold question retrieval fixed to BM25 to isolate preprocessing differences."""

# ruff: noqa: E402 -- standalone evaluation entry point
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from text2query.config import settings
from text2query.experiments.prompt_coverage import (
    METHODS,
    aggregate,
    coverage,
    database_key,
    make_prompt,
    verify_inputs,
)
from text2query.io import file_sha256, read_json, read_jsonl, write_json, write_jsonl
from text2query.models import Catalog
from text2query.retrieval.context import Budget, ContextBuilder
from text2query.retrieval.index import RetrievalIndex
from text2query.retrieval.ranking import RecallConfig


def run(directory: Path, method: str) -> None:
    manifest = verify_inputs(directory)
    output = directory / "controlled_bm25" / method
    if output.exists():
        raise FileExistsError("Control already exists")
    output.mkdir(parents=True)
    catalog_path = directory / method / "preprocessed/schema_catalog.json"
    catalog = Catalog.model_validate(read_json(catalog_path))
    settings.preprocessed_dir = catalog_path.parent
    started = time.perf_counter()
    index = RetrievalIndex.build(
        output / "index", encoder=None, catalog=catalog,
        knowledge=read_json(settings.knowledge),
        train_rows=read_json(directory / "shared/retrieval_train.json"),
        training_source=directory / "shared/retrieval_train.json",
        recall_config=RecallConfig(rerank_enabled=False),
    )
    builder = ContextBuilder(index, Budget(initial_tables=manifest["max_tables"],
                                           total_tables=max(12, manifest["max_tables"])))
    questions = read_json(directory / "shared/questions.json")
    routes = read_json(directory / "shared/routing.json")
    prompts = []
    contexts = []
    tables = catalog.by_id()
    for number, (row, route) in enumerate(zip(questions, routes, strict=True), 1):
        assert row["question_id"] == route["question_id"]
        context = builder.assemble(row["question"], route["predicted_engines"], row["question_id"])
        keys = [t["table_id"] for t in context["candidate_tables"]]
        prompts.append({**row, **route, "retrieved_table_ids": keys,
                        **make_prompt(row["question"], keys, tables, manifest["max_instruction_chars"])})
        contexts.append(context)
        if number % 50 == 0:
            print(json.dumps({"method": method, "prepared": number, "total": len(questions)}), flush=True)
    write_jsonl(output / "prompts.jsonl", prompts)
    write_jsonl(output / "contexts.jsonl", contexts)
    write_json(output / "run.json", {
        "method": method, "controlled_retrieval": "identical BM25 only, including identical case fallback",
        "prepared": len(prompts), "elapsed_seconds": time.perf_counter() - started,
        "catalog_sha256": file_sha256(catalog_path),
        "prompts_sha256": file_sha256(output / "prompts.jsonl"),
        "recall": index.recall_metadata, "stats": index.stats,
        "script_sha256": file_sha256(Path(__file__)),
    })


def score(directory: Path) -> None:
    verify_inputs(directory)
    # Reuse answer targets only after all primary prompts have been scored.
    targets = {r["question_id"]: r for r in read_json(directory / "reference_targets.json")}
    public = read_json(directory / "shared/questions.json")
    tables = Catalog.model_validate(read_json(directory / "programmatic/preprocessed/schema_catalog.json")).by_id()
    summaries = {}
    control = directory / "controlled_bm25"
    paths = {m: (directory / m if m == "programmatic" else control / m) for m in METHODS}
    lines = ["# 固定BM25召回的预处理对照", "",
             "三份预处理数据不变，三组逐题召回统一使用同一BM25配置、路由、案例回退、候选上限与DDL提示词预算。",
             "该对照用于区分预处理候选归属和下游检索模型变化；与主实验的完整方案比较分开报告。", "",
             "| 预处理方法 | 完整业务库覆盖 | 完整业务表覆盖 |", "| --- | ---: | ---: | ---: |"]
    for method in METHODS:
        prompts = read_jsonl(paths[method] / "prompts.jsonl")
        run = read_json(paths[method] / "run.json")
        assert file_sha256(paths[method] / "prompts.jsonl") == run["prompts_sha256"]
        assert [p["question_id"] for p in prompts] == [q["question_id"] for q in public]
        rows = []
        for p in prompts:
            target = targets[p["question_id"]]
            row = {"method": method, "question_id": p["question_id"], "expected": target,
                   "routing_correct": set(p["predicted_engines"]) == set(target["engines"]),
                   "prompt_status": p["status"], "prompt_table_ids": p["prompt_table_ids"],
                   "category": "|".join(target["engines"])}
            for stage, field in (("retrieved", "retrieved_table_ids"), ("prompt", "prompt_table_ids")):
                ids = set(p[field])
                row[stage + "_table_coverage"] = coverage(set(target["table_ids"]), ids, target["evaluable"])
                row[stage + "_db_coverage"] = coverage(set(target["databases"]), {database_key(tables[t]) for t in ids}, target["evaluable"])
            rows.append(row)
        overall = aggregate(rows)
        summaries[method] = {"overall": overall, "by_category": {
            category: aggregate([r for r in rows if r["category"] == category])
            for category in sorted({r["category"] for r in rows})}}
        write_jsonl(control / f"{method}.coverage_details.jsonl", rows)
        lines.append(f"| {method} | {overall['prompt_complete_db_coverage_rate']:.2%} ({overall['prompt_complete_db_count']}/{len(prompts)}) | "
                     f"{overall['prompt_complete_table_coverage_rate']:.2%} ({overall['prompt_complete_table_count']}/{len(prompts)}) |")
    write_json(control / "comparison.json", summaries)
    lines += ["", "程序组复用主实验相同BM25提示词，不重复生成；模型组额外保存统一BM25召回的提示词、上下文和索引。",
              "完整覆盖的分母、ES索引处理、未解析参考答案和标注隔离均沿用主实验口径。", ""]
    (control / "README.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(summaries, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment-dir", type=Path, required=True)
    parser.add_argument("--method", choices=("hybrid-8b", "hybrid-0.6b"))
    args = parser.parse_args()
    if args.method:
        run(args.experiment_dir.resolve(), args.method)
    else:
        score(args.experiment_dir.resolve())
