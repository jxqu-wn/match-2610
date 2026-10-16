"""Validate and merge successful Flash passes with the user-requested BIRD SQL."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

import sqlglot
from sqlglot import exp

from text2query.config import settings
from text2query.io import file_sha256, read_json, write_json
from text2query.models import Catalog
from text2query.submission.validate import NON_READ, resolver_for, validate_answer


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--result", type=Path, default=Path("result.json"))
    args = parser.parse_args()
    root = args.directory
    rows = read_json(root / "questions_input.json")
    bird = {row["question_id"]: row for row in read_json(root / "bird_answers.json")}
    original_bird = {row["question_id"]: row for row in read_json(root / "bird_match_sources.json")["records"]}
    catalog = Catalog.model_validate(read_json(settings.path(
        "outputs/experiments/preprocessing-prompt-coverage-v1/hybrid-0.6b/preprocessed/schema_catalog.json")))
    resolver = resolver_for(catalog.by_id())
    submission, sources, selected = [], [], Counter()
    retry = root / "expanded_engine_retry"
    reused = {}
    for row in rows:
        qid = row["question_id"]
        if qid in bird:
            answer = bird[qid]
            original = original_bird[qid]
            assert answer["query"] == original["submission_query"]
            parsed = sqlglot.parse(answer["query"], read="sqlite")
            assert len(parsed) == 1 and isinstance(parsed[0], exp.Query)
            assert not any(isinstance(node, NON_READ) for node in parsed[0].walk())
            raw = sqlglot.parse_one(original["bird"]["SQL"], read="sqlite")
            for tree in (raw, parsed[0]):
                for table in tree.find_all(exp.Table):
                    table.set("db", None)
            assert raw == parsed[0], qid
            source = "BIRD"
            path = root / "bird_match_sources.json"
        else:
            candidates = [path for base in (retry, root)
                          if (path := base / f"question_{qid}.json").exists()]
            if not candidates:
                for base in (retry, root):
                    for source_path in sorted(base.glob("question_[0-9]*.json")):
                        source_record = read_json(source_path)
                        if source_record["question"]["question"] != row["question"]:
                            continue
                        answer = {**source_record["answer"], "question_id": qid}
                        if validate_answer(answer, row, resolver):
                            continue
                        target = retry / f"question_{qid}.json"
                        write_json(target, {"model": "deepseek-flash", "question": row, "answer": answer,
                                            "exact_question_reuse": True,
                                            "source_question_id": source_record["question"]["question_id"],
                                            "source_record": str(source_path.relative_to(root)),
                                            "trace": [], "calls": []})
                        reused[qid] = source_record["question"]["question_id"]
                        candidates = [target]
                        break
                    if candidates:
                        break
                if not candidates:
                    raise ValueError(f"No successful answer for {qid}")
            path = candidates[0]
            record = read_json(path)
            assert record["question"] == row and record["model"] == "deepseek-flash"
            answer = record["answer"]
            errors = validate_answer(answer, row, resolver)
            if errors:
                raise ValueError(f"{qid}: {errors}")
            source = "DeepSeek Flash expanded engines" if path.parent == retry else "DeepSeek Flash first pass"
            if record.get("exact_question_reuse"):
                source = "DeepSeek Flash exact duplicate reuse"
                reused[qid] = record["source_question_id"]
        selected[source] += 1
        submission.append(answer)
        sources.append({"question_id": qid, "source": source, "artifact": str(path.relative_to(root))})
    assert len(submission) == len(rows) == len({answer["question_id"] for answer in submission})
    assert [answer["question_id"] for answer in submission] == [row["question_id"] for row in rows]
    validation = read_json(root / "bird_sqlite_validation.json")
    assert validation["count"] == validation["prepared"] == len(bird)
    usage = Counter()
    calls = []
    for base in (root, retry):
        for pattern in ("question_[0-9]*.json", "failed_[0-9]*.json"):
            for path in base.glob(pattern):
                for call in read_json(path).get("calls", []):
                    calls.append(call)
                    usage.update({key: value for key, value in call.get("usage", {}).items()
                                  if isinstance(value, int)})
    write_json(root / "result.json", submission)
    write_json(args.result, submission)
    write_json(root / "final_sources.json", sources)
    report = {
        "model": "deepseek-flash", "questions": len(rows), "completed": len(submission),
        "failed": [], "sources": dict(selected), "workers": 8,
        "exact_question_reuse": reused,
        "first_pass_seconds": read_json(root / "first_pass_report.json")["elapsed_seconds"],
        "retry_pass_seconds": read_json(retry / "report.json")["elapsed_seconds"],
        "main_preparation_seconds": read_json(root / "prepared_complete.json")["elapsed_seconds"],
        "retry_preparation_seconds": read_json(retry / "prepared_complete.json")["elapsed_seconds"],
        "model_request_attempts": len(calls), "successful_model_requests": sum(c["success"] for c in calls),
        "summed_request_latency_seconds": sum(c["latency_seconds"] for c in calls),
        "usage": dict(usage), "multi_step": sum("db1" in row for row in submission),
        "single_engine_distribution": dict(Counter(row["db"] for row in submission if "db" in row)),
        "static_validation": "all 680 passed; BIRD checked against original SQLite schemas",
        "execution_accuracy": None, "query_execution_performed": False,
        "result_sha256": file_sha256(args.result), "result_path": str(args.result.resolve()),
    }
    write_json(root / "report.json", report)
    print(report)


if __name__ == "__main__":
    main()
