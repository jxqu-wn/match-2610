"""SQL / DSL 解析：用 sqlglot 从训练查询中提取表引用与连接关系。

解析结果只作为弱标签使用；显式 JOIN 记为案例证据，不据此确认业务关联。
"""

from __future__ import annotations

import json
from typing import Any

import sqlglot
from sqlglot import exp
from sqlglot.optimizer.scope import traverse_scope

from ..models import Engine, Table

DIALECTS: dict[str, str] = {"MYSQL": "mysql", "SQLite": "sqlite", "POSTGRESQL": "postgres"}


def engine_set(row: dict[str, Any]) -> list[str]:
    return sorted({row[key] for key in ("db", "db1", "db2", "db3") if key in row and row[key]})


class SourceResolver:
    """把查询中的表名解析为 ``engine:namespace.table`` 标识。"""

    def __init__(self, tables: dict[str, Table]) -> None:
        self.tables = tables
        self.lookup: dict[tuple[str, str | None, str], list[str]] = {}
        for key, table in tables.items():
            for namespace in {table.database, table.schema_, None}:
                self.lookup.setdefault(
                    (table.engine, namespace.lower() if namespace else None, table.name.lower()), []
                ).append(key)

    def resolve(self, engine: str, table: exp.Table) -> str | None:
        namespace = (table.db or table.catalog or "").lower() or None
        values = self.lookup.get((engine, namespace, table.name.lower()), [])
        unique = list(dict.fromkeys(values))
        return unique[0] if len(unique) == 1 else None

    def parse(self, query: str, engine: Engine) -> dict[str, Any]:
        if engine == "Elasticsearch":
            json.loads(query)
            indices = [key for key, table in self.tables.items() if table.engine == engine]
            return {
                "table_ids": indices if len(indices) == 1 else [],
                "joins": [],
                "parse_status": "single_index_by_catalog" if len(indices) == 1 else "unresolved_index",
            }
        try:
            tree = sqlglot.parse_one(query, read=DIALECTS[engine])
        except (sqlglot.errors.SqlglotError, ValueError) as error:
            return {"table_ids": [], "joins": [], "parse_status": "parse_error", "parse_error": str(error)[:200]}

        table_ids: set[str] = set()
        joins: list[dict[str, Any]] = []
        unresolved: set[str] = set()
        for scope in traverse_scope(tree):
            aliases: dict[str, str] = {}
            for alias, source in scope.sources.items():
                if isinstance(source, exp.Table):
                    key = self.resolve(engine, source)
                    if key:
                        table_ids.add(key)
                        aliases[alias.lower()] = key
                    else:
                        unresolved.add(source.sql())
            for equality in scope.expression.find_all(exp.EQ):
                if equality.find_ancestor(exp.Select) is not scope.expression:
                    continue
                left, right = equality.left, equality.right
                if not isinstance(left, exp.Column) or not isinstance(right, exp.Column):
                    continue
                left_id, right_id = aliases.get(left.table.lower()), aliases.get(right.table.lower())
                if not left_id or not right_id or left_id == right_id:
                    continue
                left_fields = {c.name.lower(): c.name for c in self.tables[left_id].columns}
                right_fields = {c.name.lower(): c.name for c in self.tables[right_id].columns}
                if left.name.lower() in left_fields and right.name.lower() in right_fields:
                    joins.append(
                        {
                            "left_table": left_id,
                            "left_columns": [left_fields[left.name.lower()]],
                            "right_table": right_id,
                            "right_columns": [right_fields[right.name.lower()]],
                        }
                    )
        return {
            "table_ids": sorted(table_ids),
            "joins": joins,
            "parse_status": "unresolved_tables" if unresolved else "parsed",
            "unresolved_tables": sorted(unresolved),
        }
