"""Literal/column usage evidence derived only from original training examples.

An observed equality is a weak usage example, never a verified entity mapping.
No reference labels or question-specific production exceptions are accepted.
"""

from __future__ import annotations

from collections import defaultdict

import sqlglot
from sqlglot import exp
from sqlglot.optimizer.scope import traverse_scope

from ..models import Catalog
from ..retrieval.sql_parser import DIALECTS, SourceResolver
from .projection_usage import projection_usage


class TrainingBindings:
    def __init__(self, documents: dict, catalog: Catalog):
        resolver = SourceResolver(catalog.by_id())
        evidence = defaultdict(list)
        self.case_scopes = {}
        for document in documents.values():
            if document["kind"] != "example":
                continue
            data = document["data"]
            filter_fields = set()
            case_tables = set()
            for step in data["steps"]:
                engine = step["engine"]
                if engine not in DIALECTS:
                    continue
                try:
                    tree = sqlglot.parse_one(step["query"], read=DIALECTS[engine])
                except sqlglot.errors.SqlglotError:
                    continue
                for scope in traverse_scope(tree):
                    aliases = {alias.lower(): resolver.resolve(engine, source)
                               for alias, source in scope.sources.items() if isinstance(source, exp.Table)}
                    case_tables.update(key for key in aliases.values() if key)
                    where = scope.expression.args.get("where")
                    if where is not None:
                        for column in where.find_all(exp.Column):
                            if column.find_ancestor(exp.Select) is not scope.expression:
                                continue
                            owner = aliases.get(column.table.lower())
                            if not column.table:
                                owners = {key for key in aliases.values() if key and column.name.lower() in {
                                    field.name.lower() for field in resolver.tables[key].columns}}
                                owner = next(iter(owners)) if len(owners) == 1 else None
                            if owner and column.name.lower() in {field.name.lower() for field in resolver.tables[owner].columns}:
                                filter_fields.add(owner + "." + column.name)
                    for equality in scope.expression.find_all(exp.EQ):
                        if equality.find_ancestor(exp.Select) is not scope.expression:
                            continue
                        column, literal = equality.left, equality.right
                        if isinstance(column, exp.Literal):
                            column, literal = literal, column
                        if not isinstance(column, exp.Column) or not isinstance(literal, exp.Literal) or not literal.is_string:
                            continue
                        value = literal.this
                        if len(value) < 3 or value not in data["question"]:
                            continue
                        if column.table:
                            key = aliases.get(column.table.lower())
                        else:
                            owners = {key for key in aliases.values() if key and column.name.lower() in {
                                field.name.lower() for field in resolver.tables[key].columns}}
                            key = next(iter(owners)) if len(owners) == 1 else None
                        if not key or column.name.lower() not in {field.name.lower() for field in resolver.tables[key].columns}:
                            continue
                        evidence[value, key, column.name].append({
                            "source_id": document["source_id"], "question": data["question"],
                            "sql_fragment": equality.sql(dialect=DIALECTS[engine]),
                        })
            self.case_scopes[document["source_id"]] = {
                "source_id": document["source_id"], "original_question": data["question"],
                "table_ids": sorted(case_tables), "where_fields_observed": sorted(filter_fields),
                "output_convention_observed": projection_usage(data["steps"]),
                "status": "training_scope_usage_unverified; not an instruction to copy its filters or aggregation",
            }
        self.bindings = []
        for (value, key, column), examples in sorted(evidence.items()):
            unique = {example["source_id"]: example for example in examples}
            self.bindings.append({"surface": value, "table_id": key, "column": column, "literal": value,
                                  "operator": "=", "support_count": len(unique),
                                  "examples": list(unique.values())[:3],
                                  "status": "original_training_usage_unverified; not a confirmed mapping"})

    def match(self, question: str, limit: int = 10) -> list[dict]:
        matched = [row for row in self.bindings if row["surface"] in question]
        return sorted(matched, key=lambda row: (-len(row["surface"]), -row["support_count"], row["table_id"], row["column"]))[:limit]

    def scope_examples(self, examples: list[dict], limit: int = 2) -> list[dict]:
        return [self.case_scopes[example["source_id"]] for example in examples
                if example["source_id"] in self.case_scopes][:limit]
