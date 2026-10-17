"""Stage-specific retrieval and context experiments; evaluation targets stay local."""

# ruff: noqa: E402
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import shutil
import sys
import time
from dataclasses import asdict, dataclass, replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
spec = importlib.util.spec_from_file_location("quality_v1", Path(__file__).with_name("parameter_sweep.py"))
v1 = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = v1
spec.loader.exec_module(v1)

import numpy as np

from text2query.io import file_sha256, read_json, read_jsonl, write_json, write_jsonl
from text2query.retrieval.context import Budget, ContextBuilder
from text2query.retrieval.index import RetrievalIndex
from text2query.retrieval.ranking import RecallConfig

VERSION = "prompt-quality-sweep-v2"
SOURCE = ROOT / "outputs/experiments/prompt-quality-sweep-v1"


@dataclass(frozen=True)
class Parameters(v1.Parameters):
    table_mode: str = "retrieved"
    tables: int = 8
    knowledge: int = 18
    examples: int = 4
    input_budget: int = 21000
    metadata_mode: str = "compact"
    preserve_global: bool = True
    pruning: str = "tables_first"
    value_samples: int = 0
    routing: str = "frozen"
    schema_bm25_top_k: int = 50
    schema_embedding_top_k: int = 50
    schema_rrf_k: int = 60
    schema_rerank_top_k: int = 50
    schema_rerank_enabled: bool = True
    example_bm25_top_k: int = 50
    example_embedding_top_k: int = 50
    example_rrf_k: int = 60
    example_rerank_top_k: int = 50
    example_rerank_enabled: bool = True
    knowledge_support_weight: float = 0.25

    def __post_init__(self):
        super().__post_init__()
        if self.metadata_mode not in {"compact", "full"} or self.pruning not in {"tables_first", "examples_first"}:
            raise ValueError("Unknown context policy")
        if self.routing not in {"frozen", "all_engines", "schema_expand"}:
            raise ValueError("Unknown routing policy")
        if not 1 <= self.examples <= 8 or not 10000 <= self.input_budget <= 21000 or not 0 <= self.value_samples <= 20:
            raise ValueError("Invalid budget")
        self.config("schema")
        self.config("example")

    def config(self, kind):
        if kind == "knowledge":
            return self.recall()
        prefix = "schema" if kind == "schema" else "example"
        return RecallConfig(
            **{field: getattr(self, prefix + "_" + field) for field in
               ("bm25_top_k", "embedding_top_k", "rrf_k", "rerank_top_k", "rerank_enabled")},
            knowledge_support_weight=self.knowledge_support_weight,
        )


def initial_grid():
    base = Parameters("quota_t8_k18_e4")
    result = [
        replace(base, name="frozen_original", scope="frozen", table_mode="frozen", tables=6, knowledge=12,
                metadata_mode="full", preserve_global=False),
        replace(base, name="control_legacy_fixed", table_mode="frozen", tables=6, metadata_mode="full", preserve_global=False),
        replace(base, name="control_fixed_fixed", table_mode="frozen", tables=6, metadata_mode="full"),
        replace(base, name="control_legacy_t12", tables=12, metadata_mode="full", preserve_global=False),
        replace(base, name="control_fixed_t12", tables=12, metadata_mode="full"),
    ]
    for t in (6, 8, 10, 12):
        for k in (6, 12, 18):
            for e in (2, 4):
                result.append(replace(base, name=f"quota_t{t}_k{k}_e{e}", tables=t, knowledge=k, examples=e))
    for t in (6, 8, 10):
        result.append(replace(base, name=f"full_t{t}", tables=t, metadata_mode="full"))
    result += [replace(base, name="examples_first", tables=12, pruning="examples_first")]
    result += [replace(base, name=f"input_{n}", tables=12, input_budget=n) for n in (15000, 18000)]
    result += [replace(base, name=f"samples_t{t}", tables=t, value_samples=8) for t in (8, 12)]
    return result


def second_grid(seed):
    result = []
    for kind, prefix in (("schema", "schema_"), ("knowledge", ""), ("example", "example_")):
        for field, values in (("bm25_top_k", (25, 100)), ("embedding_top_k", (25, 100)),
                              ("rrf_k", (20, 100)), ("rerank_top_k", (25, 100)), ("rerank_enabled", (False,))):
            for value in values:
                result.append(replace(seed, name=f"stage_{kind}_{field}_{value}", **{prefix + field: value}))
    result += [replace(seed, name="support_" + str(w).replace(".", "_"), knowledge_support_weight=w) for w in (0.0, 1.0)]
    result += [replace(seed, name=f"routing_{r}", routing=r) for r in ("all_engines", "schema_expand")]
    return result


def prepare(args):
    if args.output.exists():
        raise FileExistsError("Use a new output version")
    src = args.source
    v1.check_public(src / "public")
    shutil.copytree(src / "public", args.output / "public")
    shutil.copytree(src / "private_evaluation", args.output / "private_evaluation")
    public = args.output / "public"
    targets = read_json(args.output / "private_evaluation/targets.json")
    old = read_json(src / "inference/sql_experiment_config.json")["selection"]
    regression = set(old["heldback_generation_question_ids"])
    diagnostic = set(old["diagnostic_generation_question_ids"])
    questions = read_json(public / "questions.json")
    held = []
    quotas = dict(zip(v1.GROUPS, (4, 3, 3, 2), strict=True))
    for group, n in quotas.items():
        available = [q for q in questions if q["question_id"] not in regression | diagnostic
                     and targets[str(q["question_id"])]["topology"] == group]
        held += sorted(available, key=lambda q: v1.digest([VERSION, 20261016, group, q["question_id"]]))[:n]
    ids = {q["question_id"] for q in held}
    if len(ids) != 12:
        raise ValueError("Insufficient heldback cases")
    write_json(public / "partition.json", {
        "generation_ids": sorted(ids), "tuning_ids": sorted(q["question_id"] for q in questions if q["question_id"] not in ids | regression),
        "regression_ids": sorted(regression), "diagnostic_ids": sorted(diagnostic), "quotas": quotas,
        "limit": "iteration-only isolation from previously used development validation; not independent test data",
    })
    write_json(public / "grid.json", [asdict(p) for p in initial_grid()])
    m = read_json(public / "input_manifest.json")
    m.update(version=VERSION, parent_manifest_sha256=file_sha256(src / "public/input_manifest.json"))
    m["files"] = {p.name: file_sha256(p) for p in public.iterdir() if p.is_file() and p.name != "input_manifest.json"}
    write_json(public / "input_manifest.json", m)
    write_json(args.output / "protocol.json", {
        "frozen_before_parameter_runs": True, "phase_a_configurations": len(initial_grid()),
        "phase_b": "single-factor changes to schema, knowledge and example retrieval plus support/routing",
        "reference_queries_read_by_inference": False,
        "selection": "per-topology DB/table nonregression against frozen baseline; knowledge positives nonregression against fixed global control; table coverage then lower P95; report Pareto frontier",
        "sql_subsets": "12 iteration-heldback, 7 known-gap diagnostic, 4 old regression cases; report separately",
        "facts_and_source_examples": "raw schema/knowledge/example SQL unchanged; value samples only from original schema source_values",
        "unavailable_gold_metrics": ["necessary_fact_coverage", "semantic_noise_rate", "execution_accuracy"],
    })
    print(json.dumps({"prepared": len(questions), "phase_a": len(initial_grid()), "iteration_holdback": sorted(ids)}, ensure_ascii=False))


class StageIndex(RetrievalIndex):
    """Reuse the existing retrieval algorithms with kind-specific configs and memoization."""

    def configure(self, p):
        self.p = p
        self.recall_config = p.config("schema")
        if not hasattr(self, "search_memo"):
            self.search_memo = {}
            self.tables_memo = {}

    def search(self, query, kind, engines, limit=8, **kwargs):
        config = self.p.config(kind)
        engines = list(engines)
        key = memo_key([query, kind, engines, limit, kwargs, config.as_dict()])
        if key not in self.search_memo:
            previous = self.recall_config
            self.recall_config = config
            try:
                self.search_memo[key] = super().search(query, kind, engines, limit, **kwargs)
            finally:
                self.recall_config = previous
        return copy.deepcopy(self.search_memo[key])

    def search_tables(self, query, engines, limit=8, **kwargs):
        engines = list(engines)
        key = memo_key([query, engines, limit, kwargs, self.p.config("schema").as_dict(), self.p.config("knowledge").as_dict()])
        if key not in self.tables_memo:
            self.tables_memo[key] = super().search_tables(query, engines, limit, **kwargs)
        return copy.deepcopy(self.tables_memo[key])


def memo_key(value):
    def normalized(item):
        if isinstance(item, dict):
            return {key: normalized(val) for key, val in item.items()}
        if isinstance(item, (set, frozenset)):
            return sorted(normalized(val) for val in item)
        if isinstance(item, (tuple, list)):
            return [normalized(val) for val in item]
        return item
    return v1.digest(normalized(value))


class Builder(ContextBuilder):
    def __init__(self, index, p):
        super().__init__(index, Budget(initial_tables=p.tables, total_tables=12, knowledge=p.knowledge,
                                      examples=p.examples, context_tokens=p.input_budget + 3000,
                                      repair_calls=0, repair_reserve=0))
        self.p = p

    def _prune_once(self, context, preferred):
        if self.p.pruning == "examples_first" and len(context["examples"]) > 1:
            removed = context["examples"].pop()
            context["omitted_evidence"].append(removed["source_id"])
            return removed["source_id"]
        return super()._prune_once(context, preferred)


def compact(context):
    """Remove ranking/debug metadata; preserve business facts and source identifiers."""
    result = copy.deepcopy(context)
    for name in ("candidate_tables", "knowledge", "examples"):
        for item in result[name]:
            item.pop("retrieval_evidence", None)
    for key in ("retrieval_budget", "token_estimation"):
        result.pop(key, None)
    return result


def build_context(row, frozen, p, base, global_index, builder):
    route = list(frozen["initial_databases"])
    if p.routing == "all_engines":
        route = list(v1.ENGINES)
    elif p.routing == "schema_expand":
        hits = base.search(row["question"], "schema", v1.ENGINES, 6)
        extra = [base.tables[h["table_ids"][0]].engine for h in hits[:2]]
        route = sorted(set(route + extra))
    if p.table_mode == "retrieved":
        c = builder.assemble(row["question"], route, row["question_id"])
    else:
        c = copy.deepcopy(frozen)
    if p.scope != "frozen":
        index = global_index if p.scope == "global" else base
        keys = [t["table_id"] for t in c["candidate_tables"]]
        hits = index.search(row["question"], "knowledge", v1.ENGINES if p.scope == "global" else route,
                            max(p.knowledge, p.rerank_top_k), table_ids=None if p.scope == "global" else keys)
        c["knowledge"] = [{"source_id": h["source_id"], **base.by_id[h["source_id"]]["data"],
                           "retrieval_evidence": h,
                           **({"retrieval_scope": "global"} if p.scope == "global" and p.preserve_global else {})}
                          for h in hits[:p.knowledge]]
    c["examples"] = c["examples"][:p.examples]
    if p.value_samples:
        for t in c["candidate_tables"]:
            values = base.tables[t["table_id"]].model_extra.get("source_values", []) if base.tables[t["table_id"]].model_extra else []
            if values:
                t["source_values"] = values[:p.value_samples]
    c["retrieval_budget"]["knowledge"] = p.knowledge
    return c


def run(args, *, parameters_class=Parameters, builder_class=Builder, transform=compact, additional_sources=(), version=VERSION):
    public, out = args.public, args.output
    m = v1.check_public(public)
    grid = [parameters_class(**p) for p in read_json(args.grid or public / "grid.json")]
    out.mkdir(parents=True, exist_ok=True)
    docs = read_jsonl(public / "documents.jsonl")
    questions = read_json(public / "questions.json")
    frozen = {c["question_id"]: c for c in read_jsonl(public / "frozen_contexts.jsonl")}
    encoder = v1.retrieval_encoder(model_path=args.embedding_model, device=args.device, dtype=args.dtype,
                                  batch_size=32, max_length=512, cache_dir=out / "embedding_cache")
    service = v1.RerankerService(args.reranker_model, device=args.device, dtype=args.dtype, batch_size=8, max_length=2048)
    cache = out / "reranker_cache"
    scores = v1.ResumableScores(service, cache)
    signatures = {str(p.relative_to(ROOT)): file_sha256(p) for p in [Path(__file__), Path(v1.__file__),
                  ROOT / "src/text2query/retrieval/context.py", ROOT / "src/text2query/retrieval/index.py",
                  ROOT / "src/text2query/retrieval/ranking.py", *additional_sources]}
    signature = {"version": version, "inputs": v1.digest(m), "code": signatures,
                 "embedding": encoder.signature, "reranker": service.signature}
    if (out / "runtime_manifest.json").exists() and read_json(out / "runtime_manifest.json") != signature:
        raise ValueError("Runtime changed; use a new output version")
    write_json(out / "runtime_manifest.json", signature)
    started = time.perf_counter()
    try:
        path = out / "vectors.npz"
        if path.exists():
            with np.load(path, allow_pickle=False) as values:
                if values["source_ids"].tolist() != [d["source_id"] for d in docs]:
                    raise ValueError("Misaligned vectors")
                vectors = values["vectors"]
        else:
            vectors = encoder.encode_documents([d["text"] for d in docs])
            np.savez_compressed(path, vectors=vectors, source_ids=np.array([d["source_id"] for d in docs]))
        encoder.encode([q["question"] for q in questions])
        encoder.unload()
        base = StageIndex(docs, encoder, vectors, recall_config=RecallConfig(), reranker=scores)
        global_index = StageIndex(v1.global_documents(docs), encoder, vectors, recall_config=RecallConfig(), reranker=scores)
        tokenizer = None
        for p in grid:
            folder = out / "runs" / p.name
            done = folder / "complete.json"
            if done.exists():
                if read_json(done)["parameters"] != asdict(p):
                    raise ValueError("Configuration changed")
                continue
            base.configure(p)
            global_index.configure(p)
            builder = builder_class(base, p)
            if tokenizer is None:
                tokenizer = builder.tokenizer
            builder.tokenizer = tokenizer
            begin = time.perf_counter()
            initial_pairs = scores.computed
            rows = []
            for i, row in enumerate(questions, 1):
                c = build_context(row, frozen[row["question_id"]], p, base, global_index, builder)
                before = copy.deepcopy(c)
                if p.metadata_mode == "compact":
                    c = transform(c)
                fitted, messages = v1.fit_actual(builder, c, (public / "system.txt").read_text())
                rows.append({"question_id": row["question_id"], "row": row, "parameters": asdict(p), "context": fitted,
                             "messages": messages, "estimated_tokens": builder.estimate(messages),
                             "before_budget_table_ids": [t["table_id"] for t in before["candidate_tables"]],
                             "before_budget_knowledge_ids": [k["knowledge_id"] for k in before["knowledge"]],
                             "audit_context_before_budget": before})
                if i % 50 == 0 or i == len(questions):
                    progress = {"configuration": p.name, "finished": i, "total": len(questions),
                                "new_reranker_pairs": scores.computed, "elapsed_seconds": time.perf_counter() - started}
                    write_json(out / "progress.json", progress)
                    print(json.dumps(progress), flush=True)
            write_jsonl(folder / "prompts.jsonl", rows)
            write_json(done, {"parameters": asdict(p), "cases": len(rows), "prompts_sha256": file_sha256(folder / "prompts.jsonl"),
                              "seconds": time.perf_counter() - begin, "new_reranker_pairs": scores.computed - initial_pairs})
        write_json(out / "complete.json", {"configurations": [p.name for p in grid], "cases": len(questions),
                                          "seconds": time.perf_counter() - started, "new_reranker_pairs": scores.computed,
                                          "cache_hits": scores.hits, "model_inference_device": args.device})
    finally:
        encoder.unload()
        service.unload()


def eligible(row, report):
    if not v1.eligible_candidate(row, report["frozen_original"]):
        return False
    control = report["control_fixed_fixed"]["tuning"]
    return row["tuning"]["positive_knowledge_hits"] >= control["positive_knowledge_hits"]


def score(args):
    v1.score(args)
    report = read_json(args.output / "comparison.json")
    split = read_json(args.public / "partition.json")
    for name, row in report.items():
        details = read_jsonl(args.output / "runs" / name / "metrics_details.jsonl")
        for label, key in (("old_regression", "regression_ids"), ("known_gap_diagnostic", "diagnostic_ids")):
            subset = [d for d in details if d["question_id"] in split[key]]
            row[label] = v1.summarize(subset)
        row["eligible"] = eligible(row, report)
        write_json(args.output / "runs" / name / "metrics.json", row)
    write_json(args.output / "comparison.json", report)


def select(args):
    report = read_json(args.output / "comparison.json")
    candidates = [(n, row) for n, row in report.items() if eligible(row, report)]
    if not candidates:
        raise ValueError("No nonregressing eligible configuration")
    best_name, best = max(candidates, key=lambda x: (v1.selection_key(x[1]), x[0]))
    near = [(n, r) for n, r in candidates if r["tuning"]["complete_table"] >= best["tuning"]["complete_table"] - 1]
    lean_name, _ = min(near, key=lambda x: (x[1]["tuning"]["tokens_p95"], -x[1]["tuning"]["complete_table"], x[0]))
    frontier = []
    for name, row in candidates:
        m = row["tuning"]
        point = (m["complete_table"], m["positive_knowledge_hits"], -m["tokens_p95"])
        if not any(all(a >= b for a, b in zip((r["tuning"]["complete_table"], r["tuning"]["positive_knowledge_hits"], -r["tuning"]["tokens_p95"]), point, strict=True))
                   and (r["tuning"]["complete_table"], r["tuning"]["positive_knowledge_hits"], -r["tuning"]["tokens_p95"]) != point for _, r in candidates):
            frontier.append(name)
    write_json(args.output / "selection_v2.json", {"high_coverage": best_name, "low_tokens": lean_name, "pareto_frontier": frontier,
                                                 "selection_partition": "tuning_only", "heldback_used_for_selection": False})
    if args.expansion_grid:
        write_json(args.expansion_grid, [asdict(p) for p in second_grid(Parameters(**best["parameters"]))])
    print(json.dumps({"high_coverage": best_name, "low_tokens": lean_name, "frontier": frontier}, ensure_ascii=False))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=["prepare", "run", "score", "select"])
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--source", type=Path, default=SOURCE)
    p.add_argument("--public", type=Path)
    p.add_argument("--private", type=Path)
    p.add_argument("--grid", type=Path)
    p.add_argument("--expansion-grid", type=Path)
    p.add_argument("--embedding-model", type=Path, default=ROOT.parent / "models/Qwen3-Embedding-0.6B")
    p.add_argument("--reranker-model", type=Path, default=ROOT.parent / "models/Qwen3-Reranker-0.6B")
    p.add_argument("--device", default="cuda:0")
    p.add_argument("--dtype", default="bfloat16")
    a = p.parse_args()
    a.output = a.output.resolve()
    a.public = a.public or a.output / "public"
    a.private = a.private or a.output / "private_evaluation"
    {"prepare": prepare, "run": run, "score": score, "select": select}[a.command](a)


if __name__ == "__main__":
    main()
