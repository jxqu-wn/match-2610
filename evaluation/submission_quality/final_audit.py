"""Offline audit of the exported file; never calls an LLM or grading website."""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from text2query.io import file_sha256, read_json, write_json
from text2query.models import Catalog
from text2query.submission.integrity import validate_integrity
from text2query.submission.validate import resolver_for, step_pairs

from .audit import db_paths, sqlite_tables
from .compile import compile_query
from .final_run import checked_ready


def audit(args):
    checked_ready(args.root)
    directory = args.root / "full"
    manifest = read_json(directory / "manifest.json")
    if file_sha256(args.questions) != manifest["official_questions_sha256"]:
        raise ValueError("Official questions changed")
    questions = read_json(args.questions)
    result = read_json(args.result)
    if ([row["question_id"] for row in result] != [row["question_id"] for row in questions]
            or len(result) != 680 or len({row["question_id"] for row in result}) != 680
            or any(type(row["question_id"]) is not int for row in result)):
        raise ValueError("Expected all 680 unique integer question IDs in original order")
    export = read_json(directory / "export.json")
    if export["sha256"] != file_sha256(args.result):
        raise ValueError("Export checksum changed")
    answers = {row["question_id"]: row for row in result}
    reused = read_json(directory / "reused_answers.json")
    if len(reused) != 128 or any(answers[row["answer"]["question_id"]] != row["answer"] for row in reused):
        raise ValueError("Reused answers changed")
    old = {row["question_id"]: row for row in read_json(args.root / "old_v6.original.json")}
    for row in reused:
        if row["source"] == "frozen_historical_ES_model_predictions" and row["answer"] != old[row["answer"]["question_id"]]:
            raise ValueError("Historical ES baseline changed")
    records = read_json(args.bird_sources)["records"]
    bird = {row["question"].strip(): row for row in records}
    question_by_id = {row["question_id"]: row for row in questions}
    for row in reused:
        if row["source"] == "previously_authorized_BIRD_original_SQL":
            qid = row["answer"]["question_id"]
            if row["answer"]["query"] != bird[question_by_id[qid]["question"].strip()]["submission_query"]:
                raise ValueError("Authorized BIRD source answer changed")
    catalog = Catalog.model_validate(read_json(directory / "public/catalog.json"))
    paths = db_paths(args.bird_root)
    catalog.tables.extend(sqlite_tables(paths, {row["bird"]["db_id"] for row in records}))
    resolver = resolver_for(catalog.by_id())
    errors, compilation = [], []
    engine_counts = Counter()
    for row in result:
        failures = validate_integrity(row, question_by_id[row["question_id"]], resolver)
        if failures:
            errors.append({"question_id": row["question_id"], "errors": failures})
        engine_counts["→".join(row[db] for db, _ in step_pairs(row))] += 1
        for db, query in step_pairs(row):
            if row[db] == "MYSQL":
                compilation.append((row["question_id"], query, row[query]))
    with ThreadPoolExecutor(max_workers=8) as pool:
        compiled = list(pool.map(lambda item: {"question_id": item[0], "step": item[1],
                                               **compile_query(item[2], args.mysql_socket)}, compilation))
    rules = (directory / "public/rules.txt").read_text()
    budget_errors, provenance_errors, fallback_ids, uncertainty_ids = [], [], [], []
    versions = Counter()
    stages, actual_peak, estimated_peak = 0, 0, 0
    business = read_json(directory / "public/questions.json")
    for row in business:
        qid = row["question_id"]
        generated = read_json(directory / "inference" / f"{qid}.json")
        if generated.get("row") != row or generated.get("answer") != answers[qid]:
            provenance_errors.append(qid)
        versions[generated.get("generation_version", "v11")] += 1
        if generated.get("review_status") == "unresolved_source_evidence":
            fallback_ids.append(qid)
        if generated.get("analysis", {}).get("uncertainties"):
            uncertainty_ids.append(qid)
        for trace in generated.get("trace", []):
            stages += 1
            estimated = trace.get("estimated_tokens", 0)
            actual = trace.get("call", {}).get("usage", {}).get("prompt_tokens", 0)
            estimated_peak, actual_peak = max(estimated_peak, estimated), max(actual_peak, actual)
            if max(estimated, actual) > trace["input_limit"]:
                budget_errors.append({"question_id": qid, "stage": trace["purpose"],
                                      "estimated": estimated, "actual": actual, "limit": trace["input_limit"]})
            if trace["purpose"] != "literal_intent" and rules not in trace["messages"][0]["content"]:
                provenance_errors.append({"question_id": qid, "missing_original_rules": trace["purpose"]})
    state = read_json(args.root / "working_state.json")
    failures = [row for row in compiled if not row["ok"]]
    report = {"result": str(args.result.resolve()), "sha256": file_sha256(args.result), "questions": len(result),
              "integrity_valid": len(result) - len(errors), "integrity_errors": errors,
              "mysql_steps": len(compiled), "mysql_compile_valid": len(compiled) - len(failures),
              "mysql_compile_errors": failures, "engines": dict(engine_counts),
              "two_step_questions": sum(len(step_pairs(row)) == 2 for row in result),
              "reused_exact": len(reused), "business_questions": len(business), "generation_versions": dict(versions),
              "checked_stages": stages, "estimated_input_peak": estimated_peak, "actual_prompt_peak": actual_peak,
              "budget_errors": budget_errors, "provenance_errors": provenance_errors,
              "unresolved_source_evidence_ids": sorted(fallback_ids), "reported_uncertainty_ids": sorted(uncertainty_ids),
              "full_generation_runs": state["full_generation_runs"], "website_submissions": state["official_submissions_used"],
              "official_score": None, "business_execution_accuracy": None,
              "limitations": "Static validation and empty MariaDB compilation only; PostgreSQL/PostGIS not executed; source reuse is not hidden-answer validation."}
    write_json(directory / "final_audit.json", report)
    if errors or failures or budget_errors or provenance_errors:
        raise ValueError("Offline audit failed; see full/final_audit.json")
    print({key: report[key] for key in ("questions", "integrity_valid", "mysql_compile_valid", "two_step_questions", "generation_versions", "website_submissions", "sha256")})


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--root", type=Path, default=Path("outputs/experiments/single-submit-v1"))
    parser.add_argument("--questions", type=Path, default=Path("../data/QA_test.json"))
    parser.add_argument("--result", type=Path, default=Path("result.json"))
    parser.add_argument("--bird-root", type=Path, default=Path("../bird"))
    parser.add_argument("--bird-sources", type=Path, default=Path("outputs/qa_test_680_hybrid06b_deepseek_flash_v1/bird_match_sources.json"))
    parser.add_argument("--mysql-socket", type=Path, default=Path("/tmp/match-v6-single-submit-mariadb/socket"))
    audit(parser.parse_args())


if __name__ == "__main__":
    main()
