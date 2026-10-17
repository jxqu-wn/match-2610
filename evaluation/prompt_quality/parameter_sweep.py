"""Isolated retrieval-parameter experiments; reference labels are score-only.

prepare writes public inference inputs and separate private evaluation labels.
run uses GPU embedding/reranking and saves prompts without reading references.
score/select run locally; generate sends only selected public prompts to DeepSeek.
"""

# ruff: noqa: E402
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import os
import re
import shutil
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np

from text2query.config import settings
from text2query.experiments.federation_trace import TracedClient
from text2query.experiments.multilabel_prompt_coverage import ResumableScores
from text2query.experiments.prompt_coverage import database_key, reference_targets
from text2query.io import canonical_json, file_sha256, read_json, read_jsonl, write_json, write_jsonl
from text2query.models import Catalog
from text2query.retrieval.context import Budget, ContextBuilder
from text2query.retrieval.embedding import retrieval_encoder
from text2query.retrieval.index import RetrievalIndex
from text2query.retrieval.ranking import RecallConfig, RerankerService
from text2query.retrieval.sql_parser import SourceResolver
from text2query.submission.generate import (
    SYSTEM,
    InputEstimator,
    SchemaKeywordSearch,
    generate_one,
    schema_fallback,
)

VERSION = "prompt-quality-sweep-v1"
ENGINES = ["MYSQL", "POSTGRESQL", "Elasticsearch"]
PARENT = ROOT / "outputs/experiments/preprocessing-prompt-coverage-v1"
FROZEN = ROOT / "outputs/experiments/semantic-multilabel-prompt-coverage-v1"
GROUPS = ("single_table", "same_business_multitable", "same_system_cross_business", "cross_system")


@dataclass(frozen=True)
class Parameters:
    name: str
    scope: str = "global"
    bm25_top_k: int = 50
    embedding_top_k: int = 50
    rrf_k: int = 60
    rerank_top_k: int = 50
    knowledge: int = 12
    rerank_enabled: bool = True
    table_mode: str = "frozen"
    tables: int = 6

    def __post_init__(self):
        if self.scope not in {"frozen", "associated", "global"}:
            raise ValueError("Unknown scope")
        if self.table_mode not in {"frozen", "retrieved"}:
            raise ValueError("Unknown table mode")
        if not re.fullmatch(r"[a-zA-Z0-9_-]+", self.name):
            raise ValueError("Unsafe experiment name")
        if min(self.bm25_top_k, self.embedding_top_k, self.rrf_k, self.rerank_top_k, self.knowledge, self.tables) < 1:
            raise ValueError("Positive parameter required")
        if self.tables > 12:
            raise ValueError("At most 12 tables")

    def recall(self):
        return RecallConfig(self.bm25_top_k, self.embedding_top_k, self.rrf_k, self.rerank_top_k, self.rerank_enabled)


def initial_grid():
    base = Parameters("global_default")
    rows = [
        replace(base, name="frozen_original", scope="frozen"),
        replace(base, name="associated_control", scope="associated"),
        base,
    ]
    for field, values in (
        ("bm25_top_k", (25, 100)),
        ("embedding_top_k", (25, 100)),
        ("rrf_k", (20, 100)),
        ("rerank_top_k", (25, 100)),
        ("knowledge", (6, 18)),
    ):
        rows += [replace(base, **{field: value, "name": f"global_{field}_{value}"}) for value in values]
    rows += [
        replace(base, name="global_no_rerank", rerank_enabled=False),
        replace(base, name="global_wide_12", bm25_top_k=100, embedding_top_k=100, rerank_top_k=100),
        replace(base, name="global_wide_18", bm25_top_k=100, embedding_top_k=100, rerank_top_k=100, knowledge=18),
    ]
    return rows


def digest(value):
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def topology(target):
    if len(target["engines"]) > 1:
        return "cross_system"
    if len(target["databases"]) > 1:
        return "same_system_cross_business"
    return "same_business_multitable" if len(target["table_ids"]) > 1 else "single_table"


def partitions(rows, groups, seed=20261016):
    """Outcome-independent split: 20 generation cases, 264 tuning cases."""
    quotas = dict(zip(GROUPS, (6, 4, 6, 4), strict=True))
    selected = []
    for group, quota in quotas.items():
        candidates = [r for r in rows if groups[r["question_id"]] == group]
        if len(candidates) < quota:
            raise ValueError(f"Not enough cases for {group}")
        selected += sorted(candidates, key=lambda r: digest([VERSION, seed, group, r["question_id"]]))[:quota]
    ids = {r["question_id"] for r in selected}
    return {
        "generation_ids": sorted(ids),
        "tuning_ids": sorted(r["question_id"] for r in rows if r["question_id"] not in ids),
        "quotas": quotas,
        "seed": seed,
        "limit": "iteration-isolated subset of previously used development validation; not a new independent test",
    }


def literal_anchor_labels(questions, knowledge):
    """Conservative silver diagnostic, NOT a necessary-fact or relevance gold."""
    labels = []
    for item in knowledge:
        text = item["knowledge_text"]
        match = re.match(r"(.{3,32}?)(?:的经纬度坐标为|的定义[：:]|的判断标准[：:]|的标准[：:])", text)
        if not match:
            continue
        anchor = match[1].strip('‘’“”" ')
        for row in questions:
            if anchor in row["question"]:
                labels.append(
                    {
                        "question_id": row["question_id"],
                        "knowledge_id": item["knowledge_id"],
                        "anchor": anchor,
                        "label_type": "literal_anchor_silver",
                    }
                )
    return labels


def prepare(args):
    out = args.output
    if out.exists():
        raise FileExistsError("Choose a new output version")
    catalog_path = args.parent / "hybrid-0.6b/preprocessed/schema_catalog.json"
    catalog = Catalog.model_validate(read_json(catalog_path))
    validation = read_json(args.parent / "shared/splits/validation.json")
    questions = [{k: r[k] for k in ("question_id", "question")} for r in validation]
    contexts = read_jsonl(args.frozen / "contexts.jsonl")
    docs = read_jsonl(args.parent / "hybrid-0.6b/index/documents.jsonl")
    train = read_json(args.parent / "shared/retrieval_train.json")
    qids, texts = {r["question_id"] for r in questions}, {r["question"] for r in questions}
    if qids & {r["question_id"] for r in train} or texts & {r["question"] for r in train}:
        raise ValueError("Validation contamination")
    if {r["question_id"] for r in contexts} != qids:
        raise ValueError("Frozen context IDs differ")
    for c in contexts:
        if any(e["question_id"] not in {r["question_id"] for r in train} for e in c["examples"]):
            raise ValueError("Frozen example outside allowed training split")
    for d in docs:
        if d["kind"] == "example" and (d["data"]["question_id"] in qids or d["data"]["question"] in texts):
            raise ValueError("Index contains validation example")
    resolver = SourceResolver(catalog.by_id())
    targets = {r["question_id"]: reference_targets(r, resolver) for r in validation}
    groups = {qid: topology(t) for qid, t in targets.items()}
    split = partitions(questions, groups)
    public = out / "public"
    public.mkdir(parents=True)
    write_json(public / "questions.json", questions)
    write_jsonl(public / "frozen_contexts.jsonl", contexts)
    write_jsonl(public / "documents.jsonl", docs)
    shutil.copy2(catalog_path, public / "catalog.json")
    knowledge = read_json(args.parent / "hybrid-0.6b/preprocessed/knowledge.json")
    write_json(public / "knowledge.json", knowledge)
    (public / "system.txt").write_text(SYSTEM, encoding="utf-8")
    # No answer labels are uploaded in this public inference bundle.
    write_json(public / "grid.json", [asdict(p) for p in initial_grid()])
    write_json(public / "partition.json", split)
    private = out / "private_evaluation"
    write_json(private / "references.json", validation)
    write_json(private / "targets.json", {str(qid): {**t, "topology": groups[qid]} for qid, t in targets.items()})
    write_json(private / "literal_anchor_labels.json", literal_anchor_labels(questions, knowledge))
    # Previously reviewed gaps are an explicitly partial, development-only diagnostic.
    diagnosis = ROOT / "evaluation/validation_100/runs/prompt-diagnosis-v1/diagnosis.json"
    known = []
    for row in read_json(diagnosis):
        for k in row["evidence"]["raw_knowledge_not_in_actual_prompt"]:
            known.append(
                {
                    "question_id": row["question_id"],
                    "knowledge_id": k["knowledge_id"],
                    "label_type": "previously_reviewed_partial_gap",
                }
            )
    write_json(private / "known_gap_labels.json", known)
    hashes = {p.name: file_sha256(p) for p in sorted(public.iterdir()) if p.is_file()}
    write_json(
        public / "input_manifest.json",
        {
            "version": VERSION,
            "files": hashes,
            "reference_isolation": "public input bundle contains no validation reference query fields",
            "cases": len(questions),
            "train_cases": len(train),
            "source_files": {
                "catalog": file_sha256(catalog_path),
                "contexts": file_sha256(args.frozen / "contexts.jsonl"),
            },
            "script_sha256": file_sha256(Path(__file__)),
        },
    )
    print(
        json.dumps(
            {
                "prepared": len(questions),
                "configurations": len(initial_grid()),
                "split": split["quotas"],
                "groups": dict(Counter(groups.values())),
                "silver_labels": len(read_json(private / "literal_anchor_labels.json")),
                "partial_gap_labels": len(known),
            },
            ensure_ascii=False,
        )
    )


def check_public(public):
    m = read_json(public / "input_manifest.json")
    for name, expected in m["files"].items():
        if file_sha256(public / name) != expected:
            raise ValueError("Input changed: " + name)
    rows = read_json(public / "questions.json")
    if any(set(r) != {"question_id", "question"} for r in rows):
        raise ValueError("Public questions contain answer fields")
    return m


def global_documents(documents):
    """Same corpus/IDF; only knowledge eligibility metadata is changed."""
    return [
        {**copy.deepcopy(d), "engines": ENGINES, "table_ids": []} if d["kind"] == "knowledge" else copy.deepcopy(d)
        for d in documents
    ]


def select_knowledge(index, question, route, keys, p):
    config = p.recall()
    index.recall_config = config
    return index.search(
        question,
        "knowledge",
        ENGINES if p.scope == "global" else route,
        p.knowledge,
        table_ids=None if p.scope == "global" else keys,
    )


def fit_actual(builder, context, system):
    """Fit the exact spaced JSON serialization used by existing generate_one."""
    original = builder.budget.context_tokens
    try:
        for reserve in (0, 512, 1024, 2048, 4096, 6144):
            builder.budget.context_tokens = original - reserve
            fitted, _ = builder.fit(context, system)
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(fitted, ensure_ascii=False)},
            ]
            if builder.estimate(messages) <= original - builder.budget.output_tokens:
                return fitted, messages
        raise ValueError("Cannot fit actual serialized messages")
    finally:
        builder.budget.context_tokens = original


def run(args):
    public, output = args.public, args.output
    manifest = check_public(public)
    output.mkdir(parents=True, exist_ok=True)
    grid = [Parameters(**p) for p in read_json(args.grid or public / "grid.json")]
    questions = read_json(public / "questions.json")
    frozen = {r["question_id"]: r for r in read_jsonl(public / "frozen_contexts.jsonl")}
    docs = read_jsonl(public / "documents.jsonl")
    encoder = retrieval_encoder(
        model_path=args.embedding_model,
        device=args.device,
        dtype=args.dtype,
        batch_size=args.embedding_batch_size,
        max_length=512,
        cache_dir=output / "embedding_cache",
    )
    service = RerankerService(
        args.reranker_model, device=args.device, dtype=args.dtype, batch_size=args.reranker_batch_size, max_length=2048
    )
    scores = ResumableScores(service, output / "reranker_cache")
    signature = {
        "version": VERSION,
        "input_manifest": digest(manifest),
        "embedding": encoder.signature,
        "reranker": service.signature,
        "script_sha256": file_sha256(Path(__file__)),
    }
    sigpath = output / "runtime_manifest.json"
    if sigpath.exists() and read_json(sigpath) != signature:
        raise ValueError("Runtime inputs changed; use a new output version")
    write_json(sigpath, signature)
    started = time.perf_counter()
    try:
        vectors_path = output / "vectors.npz"
        if vectors_path.exists():
            with np.load(vectors_path, allow_pickle=False) as data:
                if data["source_ids"].tolist() != [d["source_id"] for d in docs]:
                    raise ValueError("Document vectors misaligned")
                vectors = data["vectors"]
        else:
            vectors = encoder.encode_documents([d["text"] for d in docs])
            np.savez_compressed(vectors_path, source_ids=[d["source_id"] for d in docs], vectors=vectors)
        encoder.encode([r["question"] for r in questions])
        encoder.unload()
        base = RetrievalIndex(docs, encoder, vectors, recall_config=RecallConfig(), reranker=scores)
        global_index = RetrievalIndex(
            global_documents(docs), encoder, vectors, recall_config=RecallConfig(), reranker=scores
        )
        base_builder = ContextBuilder(base, Budget(initial_tables=6, total_tables=12, repair_calls=0, repair_reserve=0))
        for p in grid:
            directory = output / "runs" / p.name
            done = directory / "complete.json"
            if done.exists():
                if read_json(done)["parameters"] != asdict(p):
                    raise ValueError("Config changed")
                continue
            directory.mkdir(parents=True, exist_ok=True)
            write_json(directory / "parameters.json", asdict(p))
            builder = ContextBuilder(
                base,
                Budget(
                    initial_tables=p.tables, total_tables=12, knowledge=p.knowledge, repair_calls=0, repair_reserve=0
                ),
            )
            builder.tokenizer = base_builder.tokenizer
            config_started = time.perf_counter()
            initial_pairs = scores.computed
            rows = []
            for number, row in enumerate(questions, 1):
                qid = row["question_id"]
                case = directory / "cases" / f"{qid}.json"
                if case.exists():
                    saved = read_json(case)
                    if saved["row"] != row:
                        raise ValueError("Question changed")
                    rows.append(saved)
                    continue
                c = copy.deepcopy(frozen[qid])
                route = c["initial_databases"]
                if p.table_mode == "retrieved":
                    base.recall_config = RecallConfig()
                    c = builder.assemble(row["question"], route, qid)
                keys = [t["table_id"] for t in c["candidate_tables"]]
                hits = []
                if p.scope != "frozen":
                    idx = global_index if p.scope == "global" else base
                    # Store the entire rerank pool for diagnostics, not only final K.
                    idx.recall_config = p.recall()
                    hits = idx.search(
                        row["question"],
                        "knowledge",
                        ENGINES if p.scope == "global" else route,
                        max(p.knowledge, p.rerank_top_k),
                        table_ids=None if p.scope == "global" else keys,
                    )
                    chosen = hits[: p.knowledge]
                    c["knowledge"] = [
                        {"source_id": h["source_id"], **base.by_id[h["source_id"]]["data"], "retrieval_evidence": h}
                        for h in chosen
                    ]
                c["retrieval_budget"]["knowledge"] = p.knowledge
                fitted, messages = fit_actual(builder, c, (public / "system.txt").read_text())
                payload = {
                    "row": row,
                    "context": fitted,
                    "messages": messages,
                    "question_id": qid,
                    "parameters": asdict(p),
                    "before_budget_table_ids": keys,
                    "before_budget_knowledge_ids": [k["knowledge_id"] for k in c["knowledge"]],
                    "ranking": hits,
                    "estimated_tokens": builder.estimate(messages),
                }
                write_json(case, payload)
                rows.append(payload)
                if number % 25 == 0 or number == len(questions):
                    write_json(
                        output / "progress.json",
                        {
                            "config": p.name,
                            "finished": number,
                            "total": len(questions),
                            "new_reranker_pairs": scores.computed,
                            "elapsed_seconds": time.perf_counter() - started,
                        },
                    )
                    print(json.dumps({"config": p.name, "finished": number, "new_pairs": scores.computed}), flush=True)
            write_jsonl(directory / "prompts.jsonl", rows)
            write_json(
                done,
                {
                    "parameters": asdict(p),
                    "cases": len(rows),
                    "prompts_sha256": file_sha256(directory / "prompts.jsonl"),
                    "seconds": time.perf_counter() - config_started,
                    "new_reranker_pairs": scores.computed - initial_pairs,
                },
            )
        write_json(
            output / "complete.json",
            {
                "configurations": [p.name for p in grid],
                "cases": len(questions),
                "new_reranker_pairs": scores.computed,
                "cache_hits": scores.hits,
                "seconds": time.perf_counter() - started,
                "model_inference_device": args.device,
                "execution_accuracy": None,
            },
        )
    finally:
        encoder.unload()
        service.unload()


def summarize(rows):
    n = len(rows)

    def count(key):
        return sum(bool(r[key]) for r in rows)

    ktotal = sum(r["positive_total"] for r in rows)
    khits = sum(r["positive_hits"] for r in rows)
    return {
        "count": n,
        "complete_db": count("complete_db"),
        "complete_table": count("complete_table"),
        "complete_db_rate": count("complete_db") / n if n else None,
        "complete_table_rate": count("complete_table") / n if n else None,
        "positive_knowledge_hits": khits,
        "positive_knowledge_total": ktotal,
        "partial_positive_knowledge_recall": khits / ktotal if ktotal else None,
        "tokens_p50": float(np.median([r["tokens"] for r in rows])) if n else None,
        "tokens_p95": float(np.percentile([r["tokens"] for r in rows], 95)) if n else None,
        "duplicate_knowledge_items": sum(r["duplicate_knowledge_items"] for r in rows),
        "knowledge_fidelity_errors": sum(r["knowledge_fidelity_errors"] for r in rows),
        "necessary_fact_coverage": None,
        "answerable_prompt_rate": None,
        "semantic_noise_rate": None,
    }


def score(args):
    public, out = args.public, args.output
    check_public(public)
    targets = read_json(args.private / "targets.json")
    labels = read_json(args.private / "literal_anchor_labels.json") + read_json(args.private / "known_gap_labels.json")
    positives = defaultdict(set)
    for item in labels:
        positives[item["question_id"]].add(item["knowledge_id"])
    catalog = Catalog.model_validate(read_json(public / "catalog.json")).by_id()
    raw = {k["knowledge_id"]: k["knowledge_text"] for k in read_json(public / "knowledge.json")}
    split = read_json(public / "partition.json")
    tuning = set(split["tuning_ids"])
    held = set(split["generation_ids"])
    report = {}
    for directory in sorted((out / "runs").iterdir()):
        if not (directory / "complete.json").exists():
            continue
        done = read_json(directory / "complete.json")
        if file_sha256(directory / "prompts.jsonl") != done["prompts_sha256"]:
            raise ValueError("Prompt artifacts changed")
        details = []
        for item in read_jsonl(directory / "prompts.jsonl"):
            qid = item["question_id"]
            t = targets[str(qid)]
            c = item["context"]
            tables = {x["table_id"] for x in c["candidate_tables"]}
            dbs = {database_key(catalog[x]) for x in tables}
            kids = {x["knowledge_id"] for x in c["knowledge"]}
            details.append(
                {
                    "question_id": qid,
                    "topology": t["topology"],
                    "partition": "tuning" if qid in tuning else "generation",
                    "complete_db": t["evaluable"] and set(t["databases"]) <= dbs,
                    "complete_table": t["evaluable"] and set(t["table_ids"]) <= tables,
                    "missing_tables": sorted(set(t["table_ids"]) - tables),
                    "tokens": item["estimated_tokens"],
                    "knowledge_ids": sorted(kids),
                    "positive_hits": len(kids & positives[qid]),
                    "positive_total": len(positives[qid]),
                    "duplicate_knowledge_items": len(c["knowledge"])
                    - len({k["knowledge_text"] for k in c["knowledge"]}),
                    "knowledge_fidelity_errors": sum(
                        k["knowledge_text"] != raw[k["knowledge_id"]] for k in c["knowledge"]
                    ),
                    "pruned_evidence": c["omitted_evidence"],
                }
            )
        tuning_rows = [r for r in details if r["question_id"] in tuning]
        summary = {
            "parameters": done["parameters"],
            "tuning": summarize(tuning_rows),
            "generation_holdback": summarize([r for r in details if r["question_id"] in held]),
            "overall": summarize(details),
            "tuning_groups": {g: summarize([r for r in tuning_rows if r["topology"] == g]) for g in GROUPS},
            "overall_groups": {g: summarize([r for r in details if r["topology"] == g]) for g in GROUPS},
            "limits": "reference schema coverage and partial/silver knowledge positives only; full semantic quality is not labeled",
            "runtime": done,
        }
        write_json(directory / "metrics.json", summary)
        write_jsonl(directory / "metrics_details.jsonl", details)
        report[directory.name] = summary
    write_json(out / "comparison.json", report)
    fields = [
        "configuration",
        "tuning_count",
        "complete_db",
        "complete_table",
        "positive_hits",
        "positive_total",
        "partial_positive_recall",
        "tokens_p95",
    ]
    with (out / "comparison.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for name, x in report.items():
            m = x["tuning"]
            writer.writerow(
                dict(
                    zip(
                        fields,
                        [
                            name,
                            m["count"],
                            m["complete_db"],
                            m["complete_table"],
                            m["positive_knowledge_hits"],
                            m["positive_knowledge_total"],
                            m["partial_positive_knowledge_recall"],
                            m["tokens_p95"],
                        ],
                        strict=True,
                    )
                )
            )
    print(json.dumps({n: r["tuning"] for n, r in report.items()}, ensure_ascii=False, indent=2))


def selection_key(row):
    m = row["tuning"]
    return (m["complete_table"], m["complete_db"], m["positive_knowledge_hits"], -m["tokens_p95"])


def eligible_candidate(row, baseline):
    if row["parameters"]["scope"] != "global" or row["tuning"]["knowledge_fidelity_errors"]:
        return False
    for scope in ["overall", *GROUPS]:
        current = row["tuning"] if scope == "overall" else row["tuning_groups"][scope]
        control = baseline["tuning"] if scope == "overall" else baseline["tuning_groups"][scope]
        if any(current[key] < control[key] for key in ("complete_table", "complete_db")):
            return False
    return True


def select(args):
    report = read_json(args.output / "comparison.json")
    baseline = report["frozen_original"]
    candidates = [(n, r) for n, r in report.items() if eligible_candidate(r, baseline)]
    candidates.sort(key=lambda x: (selection_key(x[1]), x[0]), reverse=True)
    if not candidates:
        raise ValueError("No nonregressing candidate")
    # Distinct prompt artifacts; identical variants do not waste API calls.
    selected = []
    seen = set()
    tuning_ids = set(read_json(args.public / "partition.json")["tuning_ids"])
    for name, _row in candidates:
        evidence = [
            {
                "qid": x["question_id"],
                "tables": [t["table_id"] for t in x["context"]["candidate_tables"]],
                "knowledge": [k["knowledge_id"] for k in x["context"]["knowledge"]],
            }
            for x in read_jsonl(args.output / "runs" / name / "prompts.jsonl")
            if x["question_id"] in tuning_ids
        ]
        key = digest(evidence)
        if key in seen:
            continue
        seen.add(key)
        selected.append(name)
        if len(selected) == args.top:
            break
    chosen = ["frozen_original", *selected]
    write_json(
        args.output / "selection.json",
        {
            "configurations": chosen,
            "selection_partition": "tuning_only",
            "rule": "reference table/db nonregression, then partial/silver positive hits, then lower P95 tokens; no full prompt-quality score",
            "generation_question_ids": read_json(args.public / "partition.json")["generation_ids"],
            "heldback_labels_used_for_selection": False,
        },
    )
    if args.expansion_grid:
        grid = []
        for name in selected:
            p = Parameters(**report[name]["parameters"])
            for limit in (6, 8, 12):
                grid.append(replace(p, name=f"{name}_tables_{limit}", table_mode="retrieved", tables=limit))
        write_json(args.expansion_grid, [asdict(p) for p in grid])
    print(json.dumps({"selected": chosen}, ensure_ascii=False))


def generate(args):
    """Only selected public prompts are read; no reference queries are loaded."""
    selection = read_json(args.output / "selection.json")
    ids = set(selection["generation_question_ids"])
    catalog = Catalog.model_validate(read_json(args.public / "catalog.json"))
    settings.embedding_model = args.embedding_model
    estimator = InputEstimator()
    keyword = SchemaKeywordSearch(schema_fallback(catalog))
    if estimator.tokenizer is None:
        raise ValueError("Local tokenizer required for generation budget")
    key = settings.api_key or os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        raise ValueError("DEEPSEEK_API_KEY is not available")
    system = (args.public / "system.txt").read_text()
    jobs = []
    for name in selection["configurations"]:
        folder = args.output / "generation" / name
        folder.mkdir(parents=True, exist_ok=True)
        for p in read_jsonl(args.output / "runs" / name / "prompts.jsonl"):
            if p["question_id"] not in ids:
                continue
            write_json(
                folder / f"prepared_{p['question_id']}.json",
                {"row": p["row"], "context": p["context"], "messages": p["messages"]},
            )
            jobs.append((name, folder, p["row"]))

    def one(job):
        name, folder, row = job
        client = TracedClient(
            folder=folder / "cases" / str(row["question_id"]) / "requests",
            model=args.model,
            api_key=key,
            timeout=180,
            default_headers={"Accept-Encoding": "identity"},
        )
        try:
            result = generate_one(
                row,
                folder,
                catalog=catalog,
                client=client,
                estimator=estimator,
                keyword=keyword,
                model=args.model,
                system=system,
                max_added_tables=4,
            )
            return {"configuration": name, "question_id": row["question_id"], "static_success": "answer" in result}
        finally:
            client.client.close()

    progress = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for future in as_completed([pool.submit(one, j) for j in jobs]):
            progress.append(future.result())
            write_json(args.output / "generation_progress.json", progress)
            print(json.dumps({"finished": len(progress), "total": len(jobs), **progress[-1]}), flush=True)
    write_json(
        args.output / "generation_complete.json",
        {
            "model": args.model,
            "jobs": len(jobs),
            "results": progress,
            "static_success": sum(p["static_success"] for p in progress),
            "execution_accuracy": None,
        },
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "run", "score", "select", "generate"])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--public", type=Path)
    parser.add_argument("--private", type=Path)
    parser.add_argument("--parent", type=Path, default=PARENT)
    parser.add_argument("--frozen", type=Path, default=FROZEN)
    parser.add_argument("--grid", type=Path)
    parser.add_argument("--expansion-grid", type=Path)
    parser.add_argument("--embedding-model", type=Path, default=ROOT.parent / "models/Qwen3-Embedding-0.6B")
    parser.add_argument("--reranker-model", type=Path, default=ROOT.parent / "models/Qwen3-Reranker-0.6B")
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--dtype", default="bfloat16")
    parser.add_argument("--embedding-batch-size", type=int, default=32)
    parser.add_argument("--reranker-batch-size", type=int, default=8)
    parser.add_argument("--model", default="deepseek-flash")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--top", type=int, default=2)
    args = parser.parse_args()
    args.output = args.output.resolve()
    args.public = (args.public or args.output / "public").resolve()
    args.private = (args.private or args.output / "private_evaluation").resolve()
    {"prepare": prepare, "run": run, "score": score, "select": select, "generate": generate}[args.command](args)


if __name__ == "__main__":
    main()
