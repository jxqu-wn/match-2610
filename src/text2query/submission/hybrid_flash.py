"""Frozen 0.6B hybrid recall + DeepSeek Flash; BIRD answers are a separate input.

Preparation uses only public questions and the frozen training/index artifacts.
Generation reuses the existing static validation and evidence expansion flow.
Credentials come from the environment or an interactive prompt, never artifacts.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from ..config import settings
from ..experiments.prompt_coverage import CachedScores
from ..io import file_sha256, read_json, write_json
from ..llm.client import ChatClient
from ..models import Catalog
from ..retrieval.context import Budget, ContextBuilder
from ..retrieval.embedding import retrieval_encoder
from ..retrieval.index import RetrievalIndex
from ..retrieval.ranking import RerankerService
from .generate import BASE_SYSTEM, InputEstimator, SchemaKeywordSearch, generate_one, schema_fallback
from .prompts import with_query_rules
from .validate import resolver_for, validate_answer

MODEL = "deepseek-flash"
# The server's installed Brotli decoder is incompatible with httpx2. Identity
# encoding avoids that optional transport codec without changing API content.
HTTP_HEADERS = {"Accept-Encoding": "identity"}


def inputs(args: argparse.Namespace) -> tuple[list[dict], dict[int, dict], str]:
    rows = read_json(args.questions)
    if any(set(row) != {"question_id", "question"} for row in rows):
        raise ValueError("Only public question_id/question fields are allowed")
    if len({row["question_id"] for row in rows}) != len(rows):
        raise ValueError("Duplicate question_id")
    bird = {row["question_id"]: row for row in read_json(args.bird_answers)}
    if not set(bird) <= {row["question_id"] for row in rows}:
        raise ValueError("BIRD answer IDs outside the requested test set")
    if any(row.get("db") != "SQLite" or set(row) != {"question_id", "db", "query"} for row in bird.values()):
        raise ValueError("BIRD supplement must contain SQLite submission objects only")
    system = with_query_rules(BASE_SYSTEM, args.rules)
    expanded = getattr(args, "expand_engines", False)
    if expanded:
        system += (
            "\n本轮检索已扩展到目录中的全部数据源。请逐表核对 table_id 的系统前缀；"
            "不同系统的表不得放入同一条SQL，必须用db1/query1、db2/query2与result分步查询。"
            "字段必须属于当前查询所用系统中的真实表，不能把跨系统字段转写为同系统字段。"
        )
    config = {
        "model": MODEL, "thinking": False, "preprocessing": "hybrid-0.6b",
        "questions_sha256": file_sha256(args.questions), "rules_sha256": file_sha256(args.rules),
        "bird_answers_sha256": file_sha256(args.bird_answers), "questions": len(rows),
        "bird_questions": len(bird), "llm_questions": len(rows) - len(bird),
        "frozen_inputs": {name: file_sha256(args.parent / name) for name in (
            "hybrid-0.6b/preprocessed/schema_catalog.json", "hybrid-0.6b/preprocessed/knowledge.json",
            "hybrid-0.6b/index/manifest.json", "hybrid-0.6b/index/documents.jsonl",
            "hybrid-0.6b/index/vectors.npz", "shared/retrieval_train.json", "shared/router.joblib")},
        "initial_tables": 6, "total_tables": 12, "knowledge": 12, "examples": 4,
        "prompt_flow": "ContextBuilder.assemble -> fit -> submission.generate_one",
        "max_attempts_per_pass": 4, "output_tokens": 3000,
        "execution_accuracy": None,
    }
    if expanded:
        config["retry_routing"] = "expand all catalog engines; no answer labels used"
    target = args.directory / "run_config.json"
    if target.exists() and read_json(target) != config:
        raise ValueError("Run inputs changed; choose a new directory")
    write_json(target, config)
    write_json(args.directory / "questions.json", rows)
    (args.directory / "system_prompt.txt").write_text(system, encoding="utf-8")
    settings.preprocessed_dir = args.parent / "hybrid-0.6b/preprocessed"
    settings.embedding_model = settings.path("../models/Qwen3-Embedding-0.6B")
    return rows, bird, system


def prepare(args: argparse.Namespace) -> None:
    import joblib

    rows, bird, system = inputs(args)
    pending = [row for row in rows if row["question_id"] not in bird]
    if getattr(args, "expand_engines", False):
        engines = sorted({table["engine"] for table in read_json(settings.schema_catalog)["tables"]})
        predicted = ["|".join(engines)] * len(pending)
    else:
        router = joblib.load(args.parent / "shared/router.joblib")
        predicted = router.predict([row["question"] for row in pending])
    encoder = retrieval_encoder(model_path=settings.embedding_model, device="cuda:0", dtype="bfloat16",
                                batch_size=4, max_length=512,
                                cache_dir=args.directory / "embedding_cache")
    service = RerankerService(settings.path("../models/Qwen3-Reranker-0.6B"), device="cuda:0",
                              dtype="bfloat16", batch_size=2, max_length=2048)
    reranker = CachedScores(service, args.directory / "reranker_scores.jsonl")
    started = time.monotonic()
    try:
        index = RetrievalIndex.load(args.parent / "hybrid-0.6b/index", encoder,
                                    training_source=args.parent / "shared/retrieval_train.json", reranker=reranker)
        builder = ContextBuilder(index, Budget(initial_tables=6, total_tables=12))
        catalog = Catalog.model_validate(read_json(settings.schema_catalog))
        write_json(args.directory / "schema_fallback.json", schema_fallback(catalog))
        encoder.encode([row["question"] for row in pending])
        for number, (row, route) in enumerate(zip(pending, predicted, strict=True), 1):
            path = args.directory / f"prepared_{row['question_id']}.json"
            if not path.exists():
                context = builder.assemble(row["question"], route.split("|"), row["question_id"])
                context, _ = builder.fit(context, system)
                # Preserve the exact initial request used by generate_one.
                messages = [{"role": "system", "content": system},
                            {"role": "user", "content": json.dumps(context, ensure_ascii=False)}]
                write_json(path, {"row": row, "predicted_engines": route.split("|"),
                                  "context": context, "messages": messages})
            elif read_json(path)["row"] != row:
                raise ValueError("Prepared question changed")
            progress = {"prepared": number, "total": len(pending),
                        "elapsed_seconds": time.monotonic() - started,
                        "reranked_pairs": reranker.computed, "recall": index.recall_metadata}
            write_json(args.directory / "prepare_progress.json", progress)
            if number % 10 == 0 or number == len(pending):
                print(json.dumps({k: v for k, v in progress.items() if k != "recall"}), flush=True)
        write_json(args.directory / "prepared_complete.json", progress)
    finally:
        encoder.unload()
        service.unload()


def generate(args: argparse.Namespace) -> None:
    rows, bird, system = inputs(args)
    key = os.environ.get("DEEPSEEK_API_KEY") or getpass.getpass("DeepSeek API key: ")
    client = ChatClient(model=MODEL, api_key=key, default_headers=HTTP_HEADERS)
    models = [item.id for item in client.client.models.list().data]
    if MODEL not in models:
        raise ValueError(f"Requested model unavailable; available model IDs: {models}")
    print(json.dumps({"authenticated": True, "model": MODEL}), flush=True)
    catalog = Catalog.model_validate(read_json(settings.schema_catalog))
    resolver = resolver_for(catalog.by_id())
    estimator = InputEstimator()
    keyword = SchemaKeywordSearch(schema_fallback(catalog))
    repair_options = ({"max_added_tables": 4, "expansion_token_reserve": 2500, "expand_all_engines": True}
                      if getattr(args, "expand_engines", False) else {})

    def one(row: dict) -> dict:
        deadline = time.monotonic() + 3600
        while not (args.directory / f"prepared_{row['question_id']}.json").exists():
            if (args.directory / "prepare_failed.json").exists() or time.monotonic() > deadline:
                raise RuntimeError("Preparation failed or timed out; no request was sent for this question")
            time.sleep(2)
        return generate_one(row, args.directory, catalog=catalog,
                            client=ChatClient(model=MODEL, api_key=key, timeout=180, default_headers=HTTP_HEADERS),
                            estimator=estimator, keyword=keyword, model=MODEL, system=system,
                            **repair_options)

    pending = [row for row in rows if row["question_id"] not in bird]
    results = []
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(one, row) for row in pending]
        for future in as_completed(futures):
            results.append(future.result())
            progress = {"finished": len(results), "total": len(pending),
                        "completed": sum("answer" in item for item in results),
                        "failed": [item["question"]["question_id"] for item in results if "answer" not in item],
                        "elapsed_seconds": time.monotonic() - started}
            write_json(args.directory / "generate_progress.json", progress)
            if len(results) % 10 == 0 or len(results) == len(pending):
                print(json.dumps(progress), flush=True)
    by_id = {item["question"]["question_id"]: item["answer"] for item in results if "answer" in item}
    for row in pending:
        if row["question_id"] in by_id:
            errors = validate_answer(by_id[row["question_id"]], row, resolver)
            if errors:
                raise ValueError(f"Final static validation failed for {row['question_id']}: {errors}")
    by_id.update(bird)
    report = {**progress, "model": MODEL, "bird_answers": len(bird), "total_questions": len(rows),
              "submission_answers": len(by_id), "execution_accuracy": None,
              "result_sha256": None}
    if len(by_id) == len(rows):
        write_json(args.result, [by_id[row["question_id"]] for row in rows])
        report["result_sha256"] = file_sha256(args.result)
    write_json(args.directory / "report.json", report)
    if len(by_id) != len(rows):
        raise SystemExit("Some questions failed; successful results are resumable")
    print(json.dumps(report), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "generate"))
    parser.add_argument("--parent", type=Path, default=Path("outputs/experiments/preprocessing-prompt-coverage-v1"))
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--rules", type=Path, required=True)
    parser.add_argument("--bird-answers", type=Path, required=True)
    parser.add_argument("--result", type=Path, default=Path("result.json"))
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--expand-engines", action="store_true", help="Retry with all catalog engines in recall scope")
    args = parser.parse_args()
    args.parent = args.parent.resolve()
    args.directory = args.directory.resolve()
    if args.workers < 1:
        parser.error("--workers must be positive")
    if args.command == "prepare":
        try:
            prepare(args)
        except Exception as error:
            write_json(args.directory / "prepare_failed.json", {"error_type": type(error).__name__,
                                                               "error": str(error)})
            raise
    else:
        generate(args)


if __name__ == "__main__":
    main()
