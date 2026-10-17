"""Compile MySQL SELECTs against an isolated, empty MariaDB schema fixture.

This catches engine errors; it is NOT execution accuracy on the business data.
The fixture uses no TCP listener and contains no fabricated business rows.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import sqlglot
from sqlglot import exp

from text2query.io import read_json, write_json
from text2query.models import Catalog
from text2query.submission.integrity import result_slots
from text2query.submission.validate import NON_READ, step_pairs


def sql_request(sql: str, socket: Path) -> dict:
    try:
        result = subprocess.run(["mariadb", "--no-defaults", "--socket=" + str(socket), "--user=root",
                                 "--batch", "--skip-column-names"], input=sql, text=True,
                                capture_output=True, timeout=5)
        return {"ok": result.returncode == 0, "error": result.stderr.strip()[:500] or None}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "compile timeout"}


def fixture(catalog: Catalog, socket: Path) -> None:
    statements = []
    namespaces = set()
    def quoted(value):
        return "`" + value.replace("`", "``") + "`"
    for table in catalog.tables:
        if table.engine != "MYSQL":
            continue
        namespace = table.namespace
        if namespace not in namespaces:
            statements.append("CREATE DATABASE IF NOT EXISTS " + quoted(namespace))
            namespaces.add(namespace)
        columns = [quoted(column.name) + " " + column.data_type for column in table.columns]
        statements.append("CREATE TABLE IF NOT EXISTS " + quoted(namespace) + "." + quoted(table.name) + "(" + ",".join(columns) + ")")
    result = sql_request(";\n".join(statements) + ";", socket)
    if not result["ok"]:
        raise RuntimeError("Schema fixture creation failed: " + str(result["error"]))


def compile_query(query: str, socket: Path) -> dict:
    try:
        trees = sqlglot.parse(query, read="mysql")
        if len(trees) != 1 or not isinstance(trees[0], exp.Query) or any(isinstance(n, NON_READ) for n in trees[0].walk()):
            return {"ok": False, "error": "Not one read-only SELECT"}
        tree = trees[0]
        for node in result_slots(tree):
            node.replace(exp.Null())
        return sql_request("EXPLAIN " + tree.sql(dialect="mysql") + ";", socket)
    except (ValueError, sqlglot.errors.SqlglotError) as error:
        return {"ok": False, "error": str(error)[:500]}


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--socket", type=Path, default=Path("/tmp/match-v6-single-submit-mariadb/socket"))
    args = parser.parse_args()
    catalog = Catalog.model_validate(read_json(args.directory / "public/catalog.json"))
    fixture(catalog, args.socket)
    report = {"engine": "MariaDB 13.0 empty structural fixture; differs from website MySQL",
              "real_business_rows": 0, "result_equivalence_claimed": False, "submissions": {}}
    for label in ("large_ai", "current_1016", "old_v6"):
        details = []
        for answer in read_json(args.directory / f"{label}.original.json"):
            for db, query in step_pairs(answer):
                if answer[db] == "MYSQL":
                    details.append({"question_id": answer["question_id"], "step": query,
                                    **compile_query(answer[query], args.socket)})
        report["submissions"][label] = {"steps": len(details), "passed": sum(row["ok"] for row in details),
                                       "failures": [row for row in details if not row["ok"]]}
        print({label: report["submissions"][label]}, flush=True)
    write_json(args.directory / "mysql_compilation_audit.json", report)


if __name__ == "__main__":
    main()
