"""Versioned evidence views; retain source facts and keep candidates unconfirmed."""

from __future__ import annotations

import re
from collections import deque
from typing import Any

from ..models import Table

VERSION = "grounded-evidence-v1"


def knowledge_scope(text: str, tables: dict[str, Table]) -> dict[str, Any]:
    """Reject an explicit foreign database scope, without knowledge-ID rules.

    Missing scope is not proof of irrelevance. Generic unscoped facts remain
    retrievable, and a mixed-scope source remains visible with its warning.
    """
    known = {table.namespace.lower() for table in tables.values() if table.namespace}
    declared = set(re.findall(r"(?:数据库|\bdatabase\s+)\s*[`\"']?([a-zA-Z_][a-zA-Z_0-9]*)", text, re.I))
    qualified = set(re.findall(r"(?<![a-zA-Z_0-9])([a-zA-Z_][a-zA-Z_0-9]*)\.[a-zA-Z_][a-zA-Z_0-9]*", text))
    # Qualified names may also be table.column. Only an explicit database
    # declaration can exclude evidence; qualifiers are diagnostic only.
    declared = {name.lower() for name in declared}
    return {"eligible": not declared or bool(declared & known),
            "declared_namespaces": sorted(declared), "unknown_namespaces": sorted(declared - known),
            "qualified_prefixes": sorted(qualified), "policy": VERSION}


def compact_table(table: Table, *, values: bool = True) -> dict[str, Any]:
    result: dict[str, Any] = {
        "table_id": table.table_id, "engine": table.engine, "description": table.description,
        "column_layout": ["name", "type", "nullable", "description"],
        "columns": [[c.name, c.data_type, c.nullable, c.description] for c in table.columns],
        "primary_key": table.primary_key,
        "foreign_keys": [fk.model_dump(by_alias=True) for fk in table.foreign_keys],
        "constraints": table.constraints,
    }
    if values and (table.model_extra or {}).get("source_values"):
        # These are raw source rows, not guessed enums. Never relabel or rewrite.
        result["source_values"] = table.model_extra["source_values"]
    return result


def fk_candidates(seeds: list[str], tables: dict[str, Table], limit: int = 12) -> list[dict[str, Any]]:
    """Declared outgoing FK closure, candidate-only, deterministic breadth-first."""
    queue = deque(key for key in seeds if key in tables)
    seen = set(queue)
    result = []
    while queue and len(result) < limit:
        key = queue.popleft()
        for fk in tables[key].foreign_keys:
            target = fk.references.table_id
            if target not in tables or target in seen:
                continue
            seen.add(target)
            result.append({"table_id": target, "candidate_reason": "declared_fk_parent",
                           "source_table": key, "columns": fk.columns,
                           "target_columns": fk.references.columns,
                           "association_confirmed": False})
            queue.append(target)
            if len(result) >= limit:
                break
    return result


def schema_directory(tables: dict[str, Table]) -> list[dict[str, Any]]:
    return [{"table_id": table.table_id, "description": table.description}
            for table in tables.values()]
