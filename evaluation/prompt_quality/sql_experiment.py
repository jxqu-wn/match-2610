"""Freeze selected SQL experiments and collect score-only review artifacts.

No reference query is read by the prepare or generate commands. The collect
command can read references only after generation_complete.json exists.
"""

# ruff: noqa: E402
from __future__ import annotations

import argparse
import functools
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
import sqlglot

from text2query.io import file_sha256, read_json, read_jsonl, write_json
from text2query.models import Catalog, Sample
from text2query.retrieval.sql_parser import DIALECTS, SourceResolver
from text2query.submission.validate import validate_answer


def load_runner():
    spec = importlib.util.spec_from_file_location(
        "prompt_quality_sweep_runner", Path(__file__).with_name("parameter_sweep.py")
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def choose_diverse_configs(report):
    runner = load_runner()
    chosen = ["frozen_original"]
    for mode in ("frozen", "retrieved"):
        candidates = [
            (name, row)
            for name, row in report.items()
            if row["parameters"]["table_mode"] == mode and runner.eligible_candidate(row, report["frozen_original"])
        ]
        if not candidates:
            raise ValueError("No eligible candidate for table mode: " + mode)
        chosen.append(max(candidates, key=lambda item: (runner.selection_key(item[1]), item[0]))[0])
    return chosen


def prepare(args):
    selection = read_json(args.output / "selection.json")
    if getattr(args, "diverse_table_modes", False):
        selection["configurations"] = choose_diverse_configs(read_json(args.output / "comparison.json"))
        selection["diversity_policy"] = (
            "one best fixed-table knowledge configuration and one best re-retrieved-table configuration; tuning metrics only"
        )
    original_ids = set(read_json(args.public / "partition.json")["generation_ids"])
    extra = {int(q) for q in args.diagnostic_ids.split(",") if q.strip()} - original_ids
    public_ids = {q["question_id"] for q in read_json(args.public / "questions.json")}
    if not extra <= public_ids:
        raise ValueError("Diagnostic ID outside public validation")
    selection["heldback_generation_question_ids"] = sorted(original_ids)
    regression_ids = set(selection.get("regression_generation_question_ids", []))
    if not regression_ids <= extra:
        raise ValueError("Regression cases must be explicitly requested diagnostic IDs")
    selection["diagnostic_generation_question_ids"] = sorted(extra - regression_ids)
    selection["generation_question_ids"] = sorted(original_ids | extra)
    paths = {name: file_sha256(args.output / "runs" / name / "prompts.jsonl") for name in selection["configurations"]}
    config = {
        "selection": selection,
        "prompts_sha256": paths,
        "system_sha256": file_sha256(args.public / "system.txt"),
        "model": args.model,
        "generation_reads_reference_queries": False,
        "diagnostic_limit": "diagnostic IDs are previously reviewed tuning cases, reported separately from heldback and regression cases",
    }
    if getattr(args, "input_limit", None) is not None:
        config["input_limit"] = args.input_limit
    frozen = args.output / "sql_experiment_config.json"
    if frozen.exists() and read_json(frozen) != config:
        raise ValueError("Generation inputs changed; choose new output")
    write_json(frozen, config)
    write_json(args.output / "selection.json", selection)
    first = selection["configurations"][-1]
    prompts = read_jsonl(args.output / "runs" / first / "prompts.jsonl")
    example = next(p for p in prompts if p["question_id"] in original_ids)
    write_json(args.output / "sql_prompt_preview.json", example["messages"])
    print(
        json.dumps(
            {
                "configurations": selection["configurations"],
                "heldback": len(original_ids),
                "diagnostic": len(extra),
                "planned_jobs": len(selection["configurations"]) * len(original_ids | extra),
            },
            ensure_ascii=False,
        )
    )


def generate(args):
    config = read_json(args.output / "sql_experiment_config.json")
    if config["model"] != args.model:
        raise ValueError("Model changed")
    if config.get("input_limit") != getattr(args, "input_limit", None):
        raise ValueError("Input limit changed")
    if config["system_sha256"] != file_sha256(args.public / "system.txt"):
        raise ValueError("System changed")
    if config["selection"] != read_json(args.output / "selection.json"):
        raise ValueError("Selection changed")
    for name, sha in config["prompts_sha256"].items():
        if file_sha256(args.output / "runs" / name / "prompts.jsonl") != sha:
            raise ValueError("Prompt changed")
    runner = load_runner()
    if config.get("input_limit") is not None:
        runner.generate_one = functools.partial(runner.generate_one, max_input_tokens=config["input_limit"])
    runner.generate(args)


def normalized(answer):
    if not answer:
        return None
    result = []
    try:
        for _, engine, query in Sample.model_validate({"question": "", **answer}).steps():
            if engine == "Elasticsearch":
                text = json.dumps(json.loads(query), ensure_ascii=False, sort_keys=True)
            else:
                text = sqlglot.parse_one(query, read=DIALECTS[engine]).sql(dialect=DIALECTS[engine])
            result.append([engine, text])
    except (ValueError, TypeError, sqlglot.errors.ParseError):
        return None
    return result


def format_matches(answer, reference):
    left, right = normalized(answer), normalized(reference)
    return left is not None and right is not None and left == right


def collect(args):
    if not (args.output / "generation_complete.json").exists():
        raise ValueError("Generation not complete")
    config = read_json(args.output / "sql_experiment_config.json")
    selection = config["selection"]
    references = {r["question_id"]: r for r in read_json(args.private / "references.json")}
    targets = read_json(args.private / "targets.json")
    catalog = Catalog.model_validate(read_json(args.public / "catalog.json"))
    resolver = SourceResolver(catalog.by_id())
    pack = []
    binding = {}
    for qid in selection["generation_question_ids"]:
        item = {
            "question_id": qid,
            "question": references[qid]["question"],
            "partition": (
                "generation_holdback" if qid in selection["heldback_generation_question_ids"]
                else "regression" if qid in selection.get("regression_generation_question_ids", [])
                else "development_diagnostic"
            ),
            "topology": targets[str(qid)]["topology"],
            "reference": references[qid],
            "predictions": {},
        }
        for name in selection["configurations"]:
            folder = args.output / "generation" / name
            path = folder / f"question_{qid}.json"
            if not path.exists():
                path = folder / f"failed_{qid}.json"
            value = read_json(path)
            answer = value.get("answer")
            binding[f"{name}/{qid}"] = file_sha256(path)
            static_errors = (
                validate_answer(answer, {"question_id": qid}, resolver) if answer else ["generation_failure"]
            )
            item["predictions"][name] = {
                "answer": answer,
                "assumptions": value.get("analysis", {}).get("assumptions", []),
                "static_pass": not static_errors,
                "static_errors": static_errors,
                "format_normalized_query_match": format_matches(answer, references[qid]),
                "generation_calls": len(value.get("trace", [])),
                "usage": {
                    key: sum(call.get("usage", {}).get(key, 0) for call in value.get("calls", []))
                    for key in ["prompt_tokens", "completion_tokens", "total_tokens"]
                },
            }
        pack.append(item)
    dest = args.output / "sql_evaluation"
    write_json(dest / "review_pack.json", pack)
    protocol_path = args.private / "sql_review_protocol.json"
    source_protocol = read_json(protocol_path) if protocol_path.exists() else {}
    write_json(
        dest / "review_binding.json",
        {
            "config": config,
            "response_hashes": binding,
            "references_sha256": file_sha256(args.private / "references.json"),
            "review_pack_sha256": file_sha256(dest / "review_pack.json"),
            "source_protocol": source_protocol,
            "source_protocol_sha256": file_sha256(protocol_path) if protocol_path.exists() else None,
            "method": "automatic static checks and conservative formatting-normalized query equality; semantic review pending",
            "execution_accuracy": None,
        },
    )
    summaries = {}
    partitions = ["generation_holdback", "development_diagnostic"]
    if selection.get("regression_generation_question_ids"):
        partitions.append("regression")
    for partition in partitions:
        subset = [q for q in pack if q["partition"] == partition]
        summaries[partition] = {}
        for name in selection["configurations"]:
            rows = [q["predictions"][name] for q in subset]
            summaries[partition][name] = {
                "questions": len(rows),
                "static_pass": sum(r["static_pass"] for r in rows),
                "format_normalized_query_match": sum(r["format_normalized_query_match"] for r in rows),
                "calls": sum(r["generation_calls"] for r in rows),
                "total_tokens": sum(r["usage"]["total_tokens"] for r in rows),
                "semantic_consistency": None,
                "execution_accuracy": None,
            }
    write_json(dest / "automatic_summary.json", summaries)
    print(json.dumps(summaries, ensure_ascii=False, indent=2))


def finalize(args):
    dest = args.output / "sql_evaluation"
    pack = read_json(dest / "review_pack.json")
    binding = read_json(dest / "review_binding.json")
    reviews = read_json(args.reviews)
    if reviews["review_pack_sha256"] != file_sha256(dest / "review_pack.json"):
        raise ValueError("Stale reviews")
    annotations = {(r["configuration"], r["question_id"]): r for r in reviews["cases"]}
    expected = {(name, q["question_id"]) for q in pack for name in q["predictions"]}
    if set(annotations) != expected or len(annotations) != len(reviews["cases"]):
        raise ValueError("Incomplete/duplicate review cases")
    allowed = {
        "satisfies_requirements",
        "rules_only_difference",
        "violates_requirement",
        "unresolved",
        "generation_failure",
    }
    if any(a["status"] not in allowed or not a.get("reason") for a in annotations.values()):
        raise ValueError("Invalid review")
    if file_sha256(dest / "review_pack.json") != binding["review_pack_sha256"]:
        raise ValueError("Pack changed")
    if read_json(args.output / "sql_experiment_config.json") != binding["config"]:
        raise ValueError("Generation config changed after collection")
    for key, expected_sha in binding["response_hashes"].items():
        name, qid = key.split("/")
        path = args.output / "generation" / name / f"question_{qid}.json"
        if not path.exists():
            path = path.with_name(f"failed_{qid}.json")
        if file_sha256(path) != expected_sha:
            raise ValueError("Generation response changed: " + key)
    summary = {}
    unresolved_source = set(binding.get("source_protocol", {}).get("source_unresolved_ids", []))
    for partition in dict.fromkeys(q["partition"] for q in pack):
        summary[partition] = {}
        subset = [q for q in pack if q["partition"] == partition]
        for name in pack[0]["predictions"]:

            def stats(rows, configuration=name):
                c = Counter(annotations[configuration, q["question_id"]]["status"] for q in rows)
                n = len(rows)
                ok = c["satisfies_requirements"] + c["rules_only_difference"]
                resolved = n - c["unresolved"]
                return {
                    "questions": n,
                    "counts": dict(c),
                    "confirmed_satisfies": ok,
                    "all_question_confirmed_rate": ok / n if n else None,
                    "resolved_rate": ok / resolved if resolved else None,
                    "unresolved": c["unresolved"],
                    "rule_issue_cases": sum(bool(annotations[configuration, q["question_id"]].get("rule_issues")) for q in rows),
                    "full_prompt_contract_pass_rate": None,
                    "execution_accuracy": None,
                }

            summary[partition][name] = {
                "overall": stats(subset),
                "fixed_source_resolved_subset": stats([q for q in subset if q["question_id"] not in unresolved_source]),
                "groups": {g: stats([q for q in subset if q["topology"] == g]) for g in load_runner().GROUPS},
            }
    write_json(
        dest / "semantic_summary.json",
        {
            "reviewer": reviews["reviewer"],
            "method": "agent static semantic review; no database execution; not independent human or external LLM judging",
            "success_scope": "business core only; rules_only_difference includes precision/projection deviations in either direction relative to current rules or references; inspect rule_issues separately; not full prompt-contract accuracy",
            "development_limit": "iteration-heldback cases isolated from this parameter selection, but drawn from previously used development validation; regression and diagnostic cases reported separately",
            "results": summary,
        },
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=["prepare", "generate", "collect", "finalize"])
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--public", type=Path, required=True)
    p.add_argument("--private", type=Path)
    p.add_argument("--reviews", type=Path)
    p.add_argument("--diagnostic-ids", default="")
    p.add_argument("--diverse-table-modes", action="store_true")
    p.add_argument("--model", default="deepseek-flash")
    p.add_argument("--workers", type=int, default=6)
    p.add_argument("--input-limit", type=int)
    p.add_argument("--embedding-model", type=Path, default=ROOT.parent / "models/Qwen3-Embedding-0.6B")
    a = p.parse_args()
    {"prepare": prepare, "generate": generate, "collect": collect, "finalize": finalize}[a.command](a)


if __name__ == "__main__":
    main()
