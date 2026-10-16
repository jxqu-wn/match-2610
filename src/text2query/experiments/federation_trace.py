"""Trace labeled cross-system validation cases without leaking reference SQL.

Reuse the frozen 90/10 split and exact historical 0.6B retrieval evidence. New
Flash generations preserve every request/response. Reference SQL is consumed by
the separate score command only. This is diagnostic replay, not a new holdout.
"""

from __future__ import annotations

import argparse
import csv
import getpass
import importlib.metadata
import json
import os
import shutil
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import joblib
import sqlglot
from sqlglot import exp
from sqlglot.optimizer.scope import traverse_scope

from ..config import settings
from ..io import canonical_json, file_sha256, read_json, read_jsonl, sha256_text, write_json, write_jsonl
from ..llm.client import ChatClient
from ..models import Catalog, Sample
from ..retrieval.context import Budget, ContextBuilder
from ..retrieval.index import RetrievalIndex
from ..retrieval.ranking import RecallConfig
from ..retrieval.sql_parser import DIALECTS, SourceResolver, engine_set
from ..submission.generate import BASE_SYSTEM, InputEstimator, SchemaKeywordSearch, generate_one, schema_fallback
from ..submission.prompts import with_query_rules
from ..submission.validate import validate_answer
from .prompt_coverage import coverage, reference_targets

MODEL = "deepseek-flash"


def checked(parent: Path, name: str, hashes: dict) -> Path:
    path = parent / name
    if file_sha256(path) != hashes[name]:
        raise ValueError("Frozen artifact changed: " + name)
    return path


def selected_evidence(context: dict) -> list[dict]:
    rows = []
    for field, kind in (("candidate_tables", "schema"), ("knowledge", "knowledge"), ("examples", "example")):
        for item in context[field]:
            hit = item.get("retrieval_evidence", {})
            rows.append({"kind": kind, "source_id": item["source_id"],
                         "table_id": item.get("table_id"), **hit})
    return rows


def prepare(args: argparse.Namespace) -> None:
    output, parent = args.output, args.parent
    if output.exists():
        raise FileExistsError("Choose a new diagnostic output directory")
    hashes = read_json(parent / "artifact_sha256.json")
    manifest = read_json(checked(parent, "manifest.json", hashes))
    source = read_json(settings.qa_train)
    if file_sha256(settings.qa_train) != manifest["source_sha256"]["qa_train"]:
        raise ValueError("Labeled source dataset changed")
    train = read_json(checked(parent, "shared/splits/train.json", hashes))
    validation = read_json(checked(parent, "shared/splits/validation.json", hashes))
    retrieval_train = read_json(checked(parent, "shared/retrieval_train.json", hashes))
    train_ids = {row["question_id"] for row in train}
    val_ids = {row["question_id"] for row in validation}
    assert not train_ids & val_ids
    assert train_ids | val_ids == {row["question_id"] for row in source}
    assert not {row["question"] for row in retrieval_train} & {row["question"] for row in validation}
    # Selection uses engine labels only; no reference query is parsed here.
    cases = [{"question_id": row["question_id"], "question": row["question"]}
             for row in validation if len(engine_set(row)) > 1]
    ids = {row["question_id"] for row in cases}
    if not ids:
        raise ValueError("No cross-system validation cases")
    contexts = {row["question_id"]: row for row in read_jsonl(
        checked(parent, "hybrid-0.6b/contexts.jsonl", hashes)) if row["question_id"] in ids}
    frozen_routes = {row["question_id"]: row["predicted_engines"] for row in read_json(
        checked(parent, "shared/routing.json", hashes))}
    router = joblib.load(checked(parent, "shared/router.joblib", hashes))
    predicted = router.predict([row["question"] for row in cases])
    probabilities = router.predict_proba([row["question"] for row in cases])
    catalog_path = checked(parent, "hybrid-0.6b/preprocessed/schema_catalog.json", hashes)
    catalog = Catalog.model_validate(read_json(catalog_path))
    documents = read_jsonl(checked(parent, "hybrid-0.6b/index/documents.jsonl", hashes))
    index_manifest = read_json(checked(parent, "hybrid-0.6b/index/manifest.json", hashes))
    scores = {r["key"]: r["score"] for r in read_jsonl(
        checked(parent, "hybrid-0.6b/reranker_scores.jsonl", hashes))}
    score_prefix = sha256_text(canonical_json(index_manifest["recall_defaults"]["reranker"]))
    # This index supplies fact lookups for fit only; retrieval is frozen replay.
    index = RetrievalIndex(documents, recall_config=RecallConfig(rerank_enabled=False))
    settings.embedding_model = settings.path("../models/Qwen3-Embedding-0.6B")
    estimator = InputEstimator()
    builder = ContextBuilder(index, Budget(initial_tables=6, total_tables=12))
    builder.tokenizer = estimator.tokenizer
    if estimator.tokenizer is None:
        raise ValueError("Local tokenizer required to reproduce the prompt budget")
    system = with_query_rules(BASE_SYSTEM, args.rules)
    output.mkdir(parents=True)
    for name in ("train.json", "validation.json", "split_manifest.json"):
        shutil.copy2(checked(parent, "shared/splits/" + name, hashes), output / name)
    shutil.copy2(parent / "shared/retrieval_train.json", output / "retrieval_train.json")
    write_json(output / "questions.json", cases)
    write_json(output / "schema_fallback.json", schema_fallback(catalog))
    (output / "system_prompt.txt").write_text(system, encoding="utf-8")
    (output / "query_rules.txt").write_text(args.rules.read_text(), encoding="utf-8")
    trace_paths = []
    for row, label, distribution in zip(cases, predicted, probabilities, strict=True):
        qid = row["question_id"]
        folder = output / "cases" / str(qid)
        context = contexts[qid]
        assert context["question"] == row["question"]
        assert label.split("|") == frozen_routes[qid] == context["initial_databases"]
        example_ids = [item["question_id"] for item in context["examples"]]
        assert set(example_ids) <= {item["question_id"] for item in retrieval_train}
        assert not set(example_ids) & val_ids
        route = {"question_id": qid, "predicted_engines": label.split("|"),
                 "class_probabilities": dict(zip(router.classes_.tolist(), distribution.tolist(), strict=True))}
        write_json(folder / "01_routing.json", route)
        write_json(folder / "02_selected_retrieval_evidence.json", selected_evidence(context))
        cached = []
        for document in documents:
            key = sha256_text(canonical_json([score_prefix, row["question"], document["text"]]))
            if key in scores:
                cached.append({"source_id": document["source_id"], "kind": document["kind"],
                               "engines": document["engines"], "table_ids": document["table_ids"],
                               "rerank_score": scores[key]})
        write_json(folder / "02_cached_reranked_candidates.json", cached)
        write_json(folder / "03_context_before_budget.json", context)
        fitted, _ = builder.fit(context, system)
        messages = [{"role": "system", "content": system},
                    {"role": "user", "content": json.dumps(fitted, ensure_ascii=False)}]
        assert estimator(messages) <= 21000
        write_json(folder / "04_context_after_budget.json", fitted)
        write_json(folder / "05_initial_messages.json", messages)
        write_json(output / f"prepared_{qid}.json", {"row": row, "context": fitted, "messages": messages})
        trace_paths.append({**row, "predicted_engines": route["predicted_engines"],
                            "candidate_tables": [item["table_id"] for item in context["candidate_tables"]],
                            "prompt_tables": [item["table_id"] for item in fitted["candidate_tables"]],
                            "example_ids": example_ids, "cached_scored_candidates": len(cached),
                            "initial_token_estimate": estimator(messages),
                            "remaining_budget_omissions": fitted["omitted_evidence"]})
    write_json(output / "case_manifest.json", trace_paths)
    write_json(output / "manifest.json", {
        "parent": str(parent.resolve()), "split_reused": True, "seed": 42,
        "labeled_source": str(settings.qa_train), "source_sha256": file_sha256(settings.qa_train),
        "train_rows": len(train), "validation_rows": len(validation), "effective_training_rows": len(retrieval_train),
        "excluded_train_text_duplicates": len(train) - len(retrieval_train), "cases": len(cases),
        "case_ids": [row["question_id"] for row in cases], "selection": "all cross-system cases in validation; no outcome filtering",
        "model": MODEL, "system_prompt_sha256": file_sha256(output / "system_prompt.txt"),
        "retrieval": "exact frozen 0.6B evidence replay; no new embedding or reranker inference",
        "ranking_trace_limit": "selected evidence retains original BM25/embedding/RRF/rerank values; cached scored candidate union has rerank scores only, not original per-call top-50 boundaries",
        "reference_isolation": "generation reads questions, prepared evidence, catalog and training examples only; score reads reference SQL after generation",
        "validation_limit": "previously used development validation split, not a fresh independent test",
        "schema_tables": len(catalog.tables), "knowledge_rows": len(read_json(settings.knowledge)),
        "frozen_inputs": {name: hashes[name] for name in (
            "shared/splits/train.json", "shared/splits/validation.json", "shared/retrieval_train.json", "shared/router.joblib",
            "hybrid-0.6b/preprocessed/schema_catalog.json", "hybrid-0.6b/index/documents.jsonl",
            "hybrid-0.6b/index/manifest.json", "hybrid-0.6b/contexts.jsonl", "hybrid-0.6b/reranker_scores.jsonl")},
        "environment": {name: importlib.metadata.version(name) for name in
                        ("numpy", "scikit-learn", "joblib", "sqlglot", "openai", "transformers")},
    })
    print(json.dumps({"prepared_cases": len(cases), "validation": len(validation),
                      "effective_train": len(retrieval_train), "case_ids": [row["question_id"] for row in cases]}))


class TracedClient(ChatClient):
    """Save the actual conversation for every generation/repair request."""

    def __init__(self, *, folder: Path, **kwargs):
        super().__init__(**kwargs)
        self.folder = folder
        self.number = max((int(p.stem.split("_")[-1]) for p in folder.glob("request_*.json")), default=0)

    def complete(self, messages, max_tokens, purpose, *, temperature=0.0):
        self.number += 1
        path = self.folder / f"request_{self.number:02d}.json"
        record = {"model": self.model, "purpose": purpose, "messages": messages,
                  "max_tokens": max_tokens, "temperature": temperature, "thinking": False}
        write_json(path, record)
        try:
            raw = super().complete(messages, max_tokens, purpose, temperature=temperature)
        except Exception as error:
            write_json(self.folder / f"response_{self.number:02d}.json", {"error_type": type(error).__name__})
            raise
        write_json(self.folder / f"response_{self.number:02d}.json", {"raw": raw, "calls": [c.as_dict() for c in self.calls]})
        return raw


def generate(args: argparse.Namespace) -> None:
    output = args.output
    rows = read_json(output / "questions.json")
    manifest = read_json(output / "manifest.json")
    settings.embedding_model = settings.path("../models/Qwen3-Embedding-0.6B")
    catalog = Catalog.model_validate(read_json(args.parent / "hybrid-0.6b/preprocessed/schema_catalog.json"))
    assert file_sha256(args.parent / "hybrid-0.6b/preprocessed/schema_catalog.json") == manifest["frozen_inputs"]["hybrid-0.6b/preprocessed/schema_catalog.json"]
    system = (output / "system_prompt.txt").read_text()
    assert file_sha256(output / "system_prompt.txt") == manifest["system_prompt_sha256"]
    key = os.environ.get("DEEPSEEK_API_KEY") or getpass.getpass("DeepSeek API key: ")
    estimator, keyword = InputEstimator(), SchemaKeywordSearch(schema_fallback(catalog))

    def one(row):
        client = TracedClient(folder=output / "cases" / str(row["question_id"]) / "06_generation",
                              model=MODEL, api_key=key, timeout=180, default_headers={"Accept-Encoding": "identity"})
        try:
            return generate_one(row, output, catalog=catalog, client=client, estimator=estimator,
                                keyword=keyword, model=MODEL, system=system)
        finally:
            client.client.close()

    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(one, row) for row in rows]
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            print(json.dumps({"finished": len(results), "total": len(rows),
                              "question_id": result["question"]["question_id"], "static_success": "answer" in result}), flush=True)
    by_id = {r["question"]["question_id"]: r for r in results}
    write_json(output / "generation_complete.json", {"processed": len(results), "cases": len(rows),
               "static_success": sum("answer" in r for r in results),
               "failed_ids": [r["question"]["question_id"] for r in results if "answer" not in r]})
    write_json(output / "generated_answers.json", [by_id[r["question_id"]].get("answer") for r in rows])


def prepare_control(args: argparse.Namespace) -> None:
    """Question-only schema augmentation; no reference SQL or target tables read."""
    base = args.output
    output = base / "schema_expansion_control"
    if output.exists():
        raise FileExistsError("Schema expansion control already prepared")
    manifest = read_json(base / "manifest.json")
    cases = [row for row in read_json(base / "case_manifest.json") if len(row["predicted_engines"]) == 1]
    catalog = Catalog.model_validate(read_json(checked(
        args.parent, "hybrid-0.6b/preprocessed/schema_catalog.json", manifest["frozen_inputs"])))
    documents = read_jsonl(checked(args.parent, "hybrid-0.6b/index/documents.jsonl", manifest["frozen_inputs"]))
    index = RetrievalIndex(documents, recall_config=RecallConfig(rerank_enabled=False))
    settings.embedding_model = settings.path("../models/Qwen3-Embedding-0.6B")
    estimator = InputEstimator()
    builder = ContextBuilder(index, Budget(initial_tables=6, total_tables=12))
    builder.tokenizer = estimator.tokenizer
    keyword = SchemaKeywordSearch(schema_fallback(catalog))
    system = (base / "system_prompt.txt").read_text()
    output.mkdir(parents=True)
    stages, public = [], []
    for source in cases:
        row = {key: source[key] for key in ("question_id", "question")}
        qid = row["question_id"]
        folder = output / "cases" / str(qid)
        original = read_json(base / "cases" / str(qid) / "03_context_before_budget.json")
        context = json.loads(json.dumps(original))
        prior_engines = {t["engine"] for t in context["candidate_tables"]}
        supplied = {t["table_id"] for t in context["candidate_tables"]}
        added = []
        for rank, item in enumerate(keyword.rank(row["question"]), 1):
            if item["engine"] in prior_engines or item["table_id"] in supplied:
                continue
            context["candidate_tables"].append(builder.table(item["table_id"], {
                "source_id": "schema:" + item["table_id"], "table_ids": [item["table_id"]],
                "reason": "question_only_keyword_schema_expansion_control", "keyword_control_rank": rank}))
            added.append(item["table_id"])
            if len(added) == 4:
                break
        context["searched_databases"] = sorted({t["engine"] for t in context["candidate_tables"]})
        for key in ("question", "knowledge", "examples", "relations", "initial_databases"):
            assert context[key] == original[key]
        fitted, _ = builder.fit(context, system)
        if fitted["omitted_evidence"]:
            raise ValueError("Control would prune evidence and confound schema-only comparison")
        messages = [{"role": "system", "content": system},
                    {"role": "user", "content": json.dumps(fitted, ensure_ascii=False)}]
        assert estimator(messages) <= 21000
        write_json(folder / "00_baseline_context.json", original)
        write_json(folder / "01_routing.json", read_json(base / "cases" / str(qid) / "01_routing.json"))
        write_json(folder / "02_schema_expansion.json", {"source": "question-only keyword rank over catalog",
                   "added_table_ids": added, "reference_SQL_used": False, "system_prompt_unchanged": True,
                   "knowledge_examples_relations_unchanged": True})
        write_json(folder / "03_context_before_budget.json", context)
        write_json(folder / "04_context_after_budget.json", fitted)
        write_json(folder / "05_initial_messages.json", messages)
        write_json(output / f"prepared_{qid}.json", {"row": row, "context": fitted, "messages": messages})
        stages.append({**source, "candidate_tables": [t["table_id"] for t in context["candidate_tables"]],
                       "prompt_tables": [t["table_id"] for t in fitted["candidate_tables"]],
                       "control_added_tables": added, "initial_token_estimate": estimator(messages),
                       "remaining_budget_omissions": []})
        public.append(row)
    write_json(output / "questions.json", public)
    write_json(output / "case_manifest.json", stages)
    for name in ("system_prompt.txt", "query_rules.txt", "validation.json"):
        shutil.copy2(base / name, output / name)
    authorization = base / "external_transfer_authorization.json"
    if authorization.exists():
        shutil.copy2(authorization, output / authorization.name)
    write_json(output / "manifest.json", {**manifest, "cases": len(cases), "case_ids": [r["question_id"] for r in public],
               "selection": "all initial single-system routes in the fixed cross-system validation cases",
               "retrieval": "schema-only keyword augmentation control; frozen knowledge/examples/relations unchanged",
               "control_baseline": str(base.resolve()), "maximum_added_schema_tables": 4})
    print(json.dumps({"prepared_control_cases": len(cases), "case_ids": [r["question_id"] for r in public]}))


def unqualified_unknowns(answer: dict, resolver: SourceResolver) -> list[str]:
    """Conservative diagnostic for physical-only SELECT scopes, not a new validator."""
    issues = []
    for _, engine, query in Sample.model_validate({"question": "diagnostic", **answer}).steps():
        if engine not in DIALECTS:
            continue
        tree = sqlglot.parse_one(query, read=DIALECTS[engine])
        for scope in traverse_scope(tree):
            if not scope.sources or any(not isinstance(s, exp.Table) for s in scope.sources.values()):
                continue
            keys = [resolver.resolve(engine, source) for source in scope.sources.values()]
            if not all(keys):
                continue
            names = {c.name.casefold() for key in keys for c in resolver.tables[key].columns}
            aliases = {s.alias.casefold() for s in scope.expression.selects if s.alias}
            for column in scope.columns:
                if not column.table and column.name.casefold() not in names | aliases | {"result", "*"}:
                    issues.append(column.sql())
    return sorted(set(issues))


def score(args: argparse.Namespace) -> None:
    output = args.output
    complete = read_json(output / "generation_complete.json")
    if complete["processed"] != complete["cases"]:
        raise ValueError("Score only after every selected question was processed")
    rows = read_json(output / "questions.json")
    references = {r["question_id"]: r for r in read_json(output / "validation.json")}
    stages = {r["question_id"]: r for r in read_json(output / "case_manifest.json")}
    catalog = Catalog.model_validate(read_json(args.parent / "hybrid-0.6b/preprocessed/schema_catalog.json"))
    resolver = SourceResolver(catalog.by_id())
    details, all_references = [], []
    for row in rows:
        qid = row["question_id"]
        stage = stages[qid]
        reference = references[qid]
        expected = reference_targets(reference, resolver)
        all_references.append(reference)
        path = output / f"question_{qid}.json"
        if not path.exists():
            path = output / f"failed_{qid}.json"
        record = read_json(path)
        answer = record.get("answer")
        actual = reference_targets({**row, **answer}, resolver) if answer else {"engines": [], "table_ids": [], "evaluable": False}
        original = read_json(output / "cases" / str(qid) / "03_context_before_budget.json")
        fitted = read_json(output / "cases" / str(qid) / "04_context_after_budget.json")
        errors = validate_answer(answer, row, resolver) if answer else [record.get("error", "no answer")]
        detail = {**row, "expected": expected, "predicted_engines": stage["predicted_engines"],
                  "routing_correct": set(expected["engines"]) == set(stage["predicted_engines"]),
                  "retrieved_table_coverage": coverage(set(expected["table_ids"]), set(stage["candidate_tables"]), expected["evaluable"]),
                  "prompt_table_coverage": coverage(set(expected["table_ids"]), set(stage["prompt_tables"]), expected["evaluable"]),
                  "final_engine_coverage": coverage(set(expected["engines"]), set(actual["engines"]), expected["evaluable"]),
                  "final_table_coverage": coverage(set(expected["table_ids"]), set(actual["table_ids"]), expected["evaluable"]),
                  "static_validation_passed": not errors, "static_errors": errors,
                  "unqualified_unknowns_diagnostic": unqualified_unknowns(answer, resolver) if answer else [],
                  "generation_calls": len(record["trace"]), "generated": answer is not None,
                  "assumptions": record.get("analysis", {}).get("assumptions", []),
                  "requirements": record.get("analysis", {}).get("requirements", []),
                  "initial_candidate_count": len(original["candidate_tables"]), "prompt_candidate_count": len(fitted["candidate_tables"]),
                  "pruned_evidence": fitted["omitted_evidence"], "cross_source_binding_evidence": [r for r in original["relations"] if "result_binding" in r["kind"]],
                  "actual": actual, "answer": answer,
                  "reference_query_comparison": "table/engine coverage only; not executed and not result-set equivalence"}
        requests = [read_json(p) for p in sorted((output / "cases" / str(qid) / "06_generation").glob("request_*.json"))]
        detail["evidence_expansion_used"] = any(any("additional_schemas" in m["content"] for m in r["messages"]) for r in requests)
        write_json(output / "cases" / str(qid) / "07_offline_evaluation.json", detail)
        details.append(detail)
    write_json(output / "evaluation/reference_answers.json", all_references)
    write_jsonl(output / "evaluation/details.jsonl", details)
    summary = {"cases": len(rows), "routing_correct": sum(d["routing_correct"] for d in details),
               "initial_full_table_coverage": sum(d["retrieved_table_coverage"]["complete"] for d in details),
               "prompt_full_table_coverage": sum(d["prompt_table_coverage"]["complete"] for d in details),
               "static_validation_passed": sum(d["static_validation_passed"] for d in details),
               "final_full_engine_coverage": sum(d["final_engine_coverage"]["complete"] for d in details),
               "final_full_table_coverage": sum(d["final_table_coverage"]["complete"] for d in details),
               "diagnostic_unqualified_unknowns_cases": sum(bool(d["unqualified_unknowns_diagnostic"]) for d in details),
               "evidence_expansion_cases": sum(d["evidence_expansion_used"] for d in details),
               "cases_with_pruning": sum(bool(d["pruned_evidence"]) for d in details),
               "generation_calls": sum(d["generation_calls"] for d in details), "execution_accuracy": None,
               "reference_parsed": sum(d["expected"]["evaluable"] for d in details),
               "initial_routes": dict(Counter("|".join(d["predicted_engines"]) for d in details))}
    write_json(output / "summary.json", summary)
    with (output / "evaluation/overview.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        fields = ["question_id", "routing_correct", "prompt_full_tables", "static_pass", "final_full_engines", "final_full_tables", "generation_calls", "expansion", "assumptions"]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for d in details:
            writer.writerow(dict(zip(fields, [d["question_id"], d["routing_correct"], d["prompt_table_coverage"]["complete"],
                d["static_validation_passed"], d["final_engine_coverage"]["complete"], d["final_table_coverage"]["complete"],
                d["generation_calls"], d["evidence_expansion_used"], json.dumps(d["assumptions"], ensure_ascii=False)], strict=True)))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "generate", "score", "prepare-control"))
    parser.add_argument("--parent", type=Path, default=Path("outputs/experiments/preprocessing-prompt-coverage-v1"))
    parser.add_argument("--output", type=Path, default=Path("outputs/experiments/federation-validation-trace-v1"))
    parser.add_argument("--rules", type=Path, default=Path("../data/问题描述与查询指令口径规则.txt"))
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("workers must be positive")
    {"prepare": prepare, "generate": generate, "score": score, "prepare-control": prepare_control}[args.command](args)


if __name__ == "__main__":
    main()
