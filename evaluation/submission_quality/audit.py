"""Compare immutable submissions, with genuine local BIRD result execution.

python -m evaluation.submission_quality.audit --directory ... --bird-root ../bird
"""

from __future__ import annotations

import argparse
import collections
import json
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import sqlglot

from text2query.io import file_sha256, read_json, write_json
from text2query.models import Catalog, Column, Table
from text2query.submission.integrity import validate_integrity
from text2query.submission.validate import resolver_for, step_pairs, validate_answer


def db_paths(root: Path) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for path in sorted(root.rglob("*.sqlite")):
        if path.stem in paths and file_sha256(paths[path.stem]) != file_sha256(path):
            raise ValueError(f"Different SQLite files for {path.stem}; select an explicit root")
        paths[path.stem] = path
    return paths


def readonly(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    connection.execute("PRAGMA query_only=ON")
    return connection


def sqlite_tables(paths: dict[str, Path], names: set[str]) -> list[Table]:
    tables = []
    for name in sorted(names):
        if name not in paths:
            continue
        with readonly(paths[name]) as connection:
            for (table_name,) in connection.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view')"):
                quoted = '"' + table_name.replace('"', '""') + '"'
                columns = [Column(name=row[1], data_type=row[2] or "UNKNOWN")
                           for row in connection.execute(f"PRAGMA table_info({quoted})")]
                tables.append(Table(table_id=f"SQLite:{name}.{table_name}", engine="SQLite", database=name,
                                    name=table_name, columns=columns))
    return tables


def execute(query: str, path: Path, alias: str, timeout: float = 8.0, row_limit: int = 100000) -> dict:
    started = time.monotonic()
    try:
        tree = sqlglot.parse_one(query, read="sqlite")
        from sqlglot import exp
        if not isinstance(tree, exp.Query) or len(sqlglot.parse(query, read="sqlite")) != 1:
            raise ValueError("Only one read-only query is accepted")
        with readonly(path) as connection:
            quoted = '"' + alias.replace('"', '""') + '"'
            connection.execute(f"ATTACH DATABASE ? AS {quoted}", (path.resolve().as_uri() + "?mode=ro",))
            connection.set_progress_handler(lambda: int(time.monotonic() - started > timeout), 20000)
            cursor = connection.execute(query)
            rows = cursor.fetchmany(row_limit + 1)
            if len(rows) > row_limit:
                return {"status": "row_limit", "elapsed": time.monotonic() - started}
            def cell(value):
                if isinstance(value, float):
                    return round(value, 8)
                return value
            return {"status": "ok", "rows": [tuple(cell(v) for v in row) for row in rows],
                    "columns": len(cursor.description or []), "elapsed": time.monotonic() - started}
    except (sqlite3.Error, ValueError, sqlglot.errors.SqlglotError) as error:
        return {"status": "error", "error": f"{type(error).__name__}: {str(error)[:250]}",
                "elapsed": time.monotonic() - started}


def sqlite_case(record: dict, predictions: dict[str, dict], paths: dict[str, Path]) -> dict:
    qid, bird = record["question_id"], record["bird"]
    name = bird["db_id"]
    if name not in paths:
        return {"question_id": qid, "status": "missing_database"}
    gold = execute(bird["SQL"], paths[name], name)
    ordered = bool(sqlglot.parse_one(bird["SQL"], read="sqlite").args.get("order"))
    output = {"question_id": qid, "database": name, "source": bird["source"], "source_row": bird["row_index"],
              "gold_status": gold["status"], "gold_error": gold.get("error"), "order_checked": ordered, "predictions": {}}
    for label, answers in predictions.items():
        answer = answers[qid]
        if answer.get("db") != "SQLite":
            output["predictions"][label] = {"status": "wrong_engine", "equivalent": False}
            continue
        candidate = execute(answer["query"], paths[name], name)
        equivalent = None
        if gold["status"] == "ok" and candidate["status"] == "error":
            equivalent = False
        if gold["status"] == candidate["status"] == "ok":
            equivalent = gold["columns"] == candidate["columns"] and (
                gold["rows"] == candidate["rows"] if ordered else
                collections.Counter(gold["rows"]) == collections.Counter(candidate["rows"]))
        output["predictions"][label] = {
            "status": candidate["status"], "equivalent": equivalent, "error": candidate.get("error"),
            "gold_rows": len(gold.get("rows", [])), "predicted_rows": len(candidate.get("rows", [])),
            "elapsed": round(candidate["elapsed"], 3),
        }
    return output


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--bird-root", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, default=Path("outputs/experiments/prompt-quality-6k-v1/public/catalog.json"))
    parser.add_argument("--questions", type=Path, default=Path("../data/QA_test.json"))
    parser.add_argument("--bird-sources", type=Path, default=Path("outputs/qa_test_680_hybrid06b_deepseek_flash_v1/bird_match_sources.json"))
    args = parser.parse_args()
    questions = {row["question_id"]: row for row in read_json(args.questions)}
    source_records = read_json(args.bird_sources)["records"]
    paths = db_paths(args.bird_root)
    catalog = Catalog.model_validate(read_json(args.catalog))
    catalog.tables.extend(sqlite_tables(paths, {row["bird"]["db_id"] for row in source_records}))
    resolver = resolver_for(catalog.by_id())
    predictions = {}
    structural = {}
    for label, filename in (("large_ai", "large_ai.original.json"), ("current_1016", "current_1016.original.json"), ("old_v6", "old_v6.original.json")):
        rows = read_json(args.directory / filename)
        answers = {row["question_id"]: row for row in rows}
        if set(answers) != set(questions) or len(answers) != len(rows):
            raise ValueError("Incomplete/duplicate submission: " + label)
        predictions[label] = answers
        details = []
        for row in rows:
            qid = row["question_id"]
            errors = validate_integrity(row, questions[qid], resolver)
            details.append({"question_id": qid, "question": questions[qid]["question"], "errors": errors,
                            "legacy_errors": validate_answer(row, questions[qid], resolver)})
        structural[label] = {
            "questions": len(rows), "legacy_valid": sum(not row["legacy_errors"] for row in details),
            "integrity_valid": sum(not row["errors"] for row in details),
            "engines": dict(collections.Counter("→".join(row[db] for db, _ in step_pairs(row)) for row in rows)),
            "failures": [row for row in details if row["errors"]],
        }
        print(json.dumps({"structural": label, "valid": structural[label]["integrity_valid"]}), flush=True)
    write_json(args.directory / "structural_audit.json", structural)
    cases = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(sqlite_case, record, predictions, paths) for record in source_records]
        for future in as_completed(futures):
            cases.append(future.result())
            if len(cases) % 10 == 0:
                print(json.dumps({"sqlite_completed": len(cases)}), flush=True)
    summary = {label: dict(collections.Counter(str(case.get("predictions", {}).get(label, {}).get("equivalent")) for case in cases)) for label in predictions}
    write_json(args.directory / "sqlite_execution_audit.json", {
        "comparison_target": "original BIRD source SQL, not website hidden references",
        "limitations": "No business DBs or per-question website verdicts; local BIRD equivalence is a proxy. Duplicate multiplicity and gold top-level ordering checked; floats rounded to 8 decimals.",
        "summary": summary, "cases": sorted(cases, key=lambda row: row["question_id"]),
    })
    print(json.dumps({"sqlite_summary": summary}), flush=True)


if __name__ == "__main__":
    main()
