"""Explore a <=6000 estimated input-token budget, including system instructions."""
# ruff: noqa: E402
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sys
from dataclasses import asdict, dataclass, replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("quality_v2_for_6k", Path(__file__).with_name("iteration_v2.py"))
v2 = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = v2
spec.loader.exec_module(v2)

from text2query.io import file_sha256, read_json, read_jsonl, write_json
from text2query.retrieval.context import ContextBuilder
from text2query.submission.generate import InputEstimator

VERSION = "prompt-quality-6k-v1"


@dataclass(frozen=True)
class Parameters(v2.Parameters):
    input_budget: int = 6000
    tables: int = 6
    knowledge: int = 8
    examples: int = 1
    schema_format: str = "terse"
    protect_examples: bool = False
    pruning: str = "examples_first"
    schema_share: float = 0.65

    def __post_init__(self):
        v2.v1.Parameters.__post_init__(self)
        if not 3000 <= self.input_budget <= 6000 or not 0 <= self.examples <= 4:
            raise ValueError("6k input budget or example count invalid")
        if self.pruning not in {"tables_first", "examples_first", "balanced"}:
            raise ValueError("Unknown pruning policy")
        if self.schema_format not in {"full", "terse"} or self.metadata_mode not in {"full", "compact"}:
            raise ValueError("Unknown serialization")
        if not 0.4 <= self.schema_share <= 0.8 or not 0 <= self.value_samples <= 8:
            raise ValueError("Invalid context allocation")
        if self.routing not in {"frozen", "all_engines", "schema_expand"}:
            raise ValueError("Unknown routing")
        self.config("schema")
        self.config("example")


def grid():
    p = Parameters("seed")
    result = [
        replace(p, name="frozen_original", scope="frozen", table_mode="frozen", knowledge=12, examples=4,
                metadata_mode="full", schema_format="full", protect_examples=True, pruning="tables_first", preserve_global=False),
        replace(p, name="control_legacy", metadata_mode="full", schema_format="full", protect_examples=True,
                pruning="tables_first", preserve_global=False),
        replace(p, name="control_fixed_fixed", metadata_mode="full", schema_format="full", protect_examples=True,
                pruning="tables_first"),
        replace(p, name="compact_full_schema", schema_format="full"),
    ]
    result += [replace(p, name=f"quota_t{t}_k{k}_e{e}", tables=t, knowledge=k, examples=e)
               for t in (4, 6, 8) for k in (4, 8, 12, 18) for e in (0, 1)]
    result += [replace(p, name="two_examples", examples=2)]
    result += [replace(p, name="tables_first", pruning="tables_first")]
    result += [replace(p, name=f"balanced_{int(share*100)}", pruning="balanced", schema_share=share) for share in (0.6, 0.75)]
    result += [replace(p, name=f"values_t{t}", tables=t, value_samples=8) for t in (4, 6)]
    result += [replace(p, name=f"budget_{budget}", input_budget=budget) for budget in (4000, 5000)]
    result += [replace(p, name=f"tables_{t}", tables=t, examples=0) for t in (10, 12)]
    return result


class Builder(v2.Builder):
    def estimate(self, messages):
        return InputEstimator.__call__(self, messages)

    def _prune_once(self, context, preferred):
        p = self.p
        if p.protect_examples:
            return super()._prune_once(context, preferred)
        protected = set()
        for engine in context["initial_databases"]:
            first = next((t["table_id"] for t in context["candidate_tables"] if t["engine"] == engine), None)
            if first:
                protected.add(first)
        if p.pruning == "examples_first" and context["examples"]:
            removed = context["examples"].pop()
            context["omitted_evidence"].append(removed["source_id"])
            return removed["source_id"]
        if p.pruning == "balanced":
            table_positions = [i for i, t in enumerate(context["candidate_tables"]) if t["table_id"] not in protected]
            removable = {}
            if table_positions:
                removable["candidate_tables"] = table_positions[-1]
            if len(context["knowledge"]) > 1:
                removable["knowledge"] = len(context["knowledge"]) - 1
            if context["examples"]:
                removable["examples"] = len(context["examples"]) - 1
            shares = {"candidate_tables": p.schema_share, "examples": 0.15 if p.examples else 0.0}
            shares["knowledge"] = 1 - shares["candidate_tables"] - shares["examples"]
            if removable:
                def load(name):
                    text = json.dumps(context[name], ensure_ascii=False)
                    tokens = len(self.tokenizer.encode(text)) if self.tokenizer else len(text.encode())
                    return tokens / max(shares[name], 0.01)
                name = max(removable, key=load)
                removed = context[name].pop(removable[name])
                context["omitted_evidence"].append(removed["source_id"])
                return removed["source_id"]
        return ContextBuilder._prune_once(self, context, protected)


def compact(context):
    result = v2.compact(context)
    if context.get("_schema_format") == "terse":
        for table in result["candidate_tables"]:
            table["column_layout"] = table["column_layout"][:4]
            table["columns"] = [column[:4] for column in table["columns"]]
    result.pop("_schema_format", None)
    return result


class SixKBuilder(Builder):
    def assemble(self, *args, **kwargs):
        result = super().assemble(*args, **kwargs)
        result["_schema_format"] = self.p.schema_format
        return result


def prepare(args):
    if args.output.exists():
        raise FileExistsError("Choose a new output version")
    v2.v1.check_public(args.source / "public")
    shutil.copytree(args.source / "public", args.output / "public")
    shutil.copytree(args.source / "private_evaluation", args.output / "private_evaluation")
    public = args.output / "public"
    write_json(public / "grid.json", [asdict(p) for p in grid()])
    manifest = read_json(public / "input_manifest.json")
    manifest.update(version=VERSION, parent_manifest_sha256=file_sha256(args.source / "public/input_manifest.json"))
    manifest["files"] = {p.name: file_sha256(p) for p in public.iterdir() if p.is_file() and p.name != "input_manifest.json"}
    write_json(public / "input_manifest.json", manifest)
    protocol = read_json(args.source / "private_evaluation/sql_review_protocol_v2.json")
    protocol["source_unresolved_ids"] = sorted(set(protocol["source_unresolved_ids"]) | set(protocol["iteration_source_unresolved_ids"]))
    write_json(args.output / "private_evaluation/sql_review_protocol.json", protocol)
    write_json(args.output / "protocol.json", {
        "version": VERSION, "frozen_before_runs": True, "input_limit_including_system_and_user": 6000,
        "token_measure": "local Qwen tokenizer with 1.2 envelope and 256 overhead; verify actual DeepSeek prompt_tokens separately",
        "stage_a_configurations": len(grid()), "stage_b_configurations": 31,
        "selection": "tuning-only, per-topology DB/table nonregression; maximize reviewed-gap retention, keep within one of best partial-positive hits; then table coverage and P95; offer lower-token near-best alternative",
        "column_policy": "keep every column name/type/nullability/comment and all keys; only omit repeated origin/review metadata in terse mode; preserve full pre-budget audit",
        "split": read_json(public / "partition.json"), "sql_subsets": "new 12 + known gap 7 + old regression [171,395,1038,3012]",
        "reference_queries_read_by_inference": False,
    })
    print(json.dumps({"configurations": len(grid()), "input_limit": 6000}, ensure_ascii=False))


def score(args):
    v2.score(args)
    report = read_json(args.output / "comparison.json")
    known = read_json(args.private / "known_gap_labels.json")
    tuning = set(read_json(args.public / "partition.json")["tuning_ids"])
    for name, row in report.items():
        by = {r["question_id"]: set(r["knowledge_ids"]) for r in read_jsonl(args.output / "runs" / name / "metrics_details.jsonl")}
        row["reviewed_gap_hits"] = sum(k["knowledge_id"] in by[k["question_id"]] for k in known if k["question_id"] in tuning)
        row["reviewed_gap_total"] = sum(k["question_id"] in tuning for k in known)
        write_json(args.output / "runs" / name / "metrics.json", row)
    write_json(args.output / "comparison.json", report)


def select(args):
    report = read_json(args.output / "comparison.json")
    candidates = [(name, row) for name, row in report.items() if v2.v1.eligible_candidate(row, report["frozen_original"])]
    best_gap = max(row["reviewed_gap_hits"] for _, row in candidates)
    candidates = [(n, r) for n, r in candidates if r["reviewed_gap_hits"] == best_gap]
    best_positive = max(row["tuning"]["positive_knowledge_hits"] for _, row in candidates)
    candidates = [(n, r) for n, r in candidates if r["tuning"]["positive_knowledge_hits"] >= best_positive - 1]
    high, row = max(candidates, key=lambda x: (v2.v1.selection_key(x[1]), x[0]))
    close = [(n, r) for n, r in candidates if r["tuning"]["complete_table"] >= row["tuning"]["complete_table"] - 1]
    lean, _ = min(close, key=lambda x: (x[1]["tuning"]["tokens_p95"], x[0]))
    write_json(args.output / "selection_6k.json", {"high_coverage": high, "low_tokens": lean,
                                                 "heldback_used_for_selection": False, "selection_partition": "tuning_only"})
    if args.expansion_grid:
        seed = Parameters(**row["parameters"])
        write_json(args.expansion_grid, [asdict(p) for p in v2.second_grid(seed)])
    print(json.dumps({"high_coverage": high, "low_tokens": lean}, ensure_ascii=False))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=["prepare", "run", "score", "select"])
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--source", type=Path, default=ROOT / "outputs/experiments/prompt-quality-sweep-v2")
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
    if a.command == "run":
        v2.run(a, parameters_class=Parameters, builder_class=SixKBuilder, transform=compact,
               additional_sources=(Path(__file__),), version=VERSION)
    else:
        {"prepare": prepare, "score": score, "select": select}[a.command](a)


if __name__ == "__main__":
    main()
