"""Schema-grounded checks for the values-only federation submission protocol.

These checks prove structural properties, never business correctness. Qualification
uses a copy of the SQL tree: the submitted SQL and source catalog are not changed.
"""

from __future__ import annotations

import json
import re
from typing import Any

import sqlglot
from sqlglot import exp
from sqlglot.optimizer.qualify import qualify
from sqlglot.optimizer.scope import traverse_scope
from sqlglot.schema import MappingSchema

from ..retrieval.sql_parser import DIALECTS, SourceResolver
from .validate import step_pairs, validate_answer


def _result_value(node: exp.Expression) -> bool:
    return isinstance(node, exp.Column) and not node.table and node.name.lower() == "result"


def result_slots(tree: exp.Expression) -> list[exp.Column]:
    """Only a sole unqualified IN(result) expression is a transferable value list."""
    return [
        node.expressions[0]
        for node in tree.find_all(exp.In)
        if not node.args.get("query") and len(node.expressions) == 1 and _result_value(node.expressions[0])
    ]


def _aggregate_errors(tree: exp.Expression) -> list[str]:
    errors: list[str] = []
    for aggregate in tree.find_all(exp.AggFunc):
        # Aggregation inside a scalar subquery is a separate query block.
        for node in aggregate.walk(prune=lambda n, outer=aggregate: n is not outer and isinstance(n, exp.Query)):
            if node is aggregate:
                continue
            if isinstance(node, exp.Window):
                errors.append("聚合函数不能直接包含同一查询层的窗口函数：" + aggregate.sql())
                break
            if isinstance(node, exp.AggFunc) and not isinstance(aggregate.parent, exp.Window):
                errors.append("同一查询层禁止嵌套聚合，请使用子查询/CTE分层：" + aggregate.sql())
                break
    return errors


def _postgis_errors(tree: exp.Expression) -> list[str]:
    """A narrow proven signature check, not a replacement for PostGIS EXPLAIN.

    Official signature: https://postgis.net/docs/ST_Within.html
    ST_Intersects/ST_DWithin DO support geography and must remain allowed.
    """
    errors = []
    for function in tree.find_all(exp.Anonymous):
        if function.name.lower() != "st_within":
            continue
        for argument in function.expressions:
            while isinstance(argument, exp.Paren):
                argument = argument.this
            if isinstance(argument, exp.Cast) and argument.to.this == exp.DataType.Type.GEOGRAPHY:
                errors.append("ST_Within仅支持geometry参数，不存在ST_Within(geography, geography)签名")
                break
    return errors


def _qualify(tree: exp.Expression, engine: str, resolver: SourceResolver) -> None:
    dialect = DIALECTS[engine]
    schema: dict[str, dict[str, dict[str, str]]] = {}
    for table in resolver.tables.values():
        if table.engine == engine:
            schema.setdefault(table.namespace or "__unqualified__", {})[table.name] = {
                column.name: "UNKNOWN" for column in table.columns
            }
    copied = tree.copy()
    # Resolve physical tables first, so unqualified table names work even when
    # unrelated namespaces contain tables with the same name.
    for scope in traverse_scope(copied):
        for source in scope.sources.values():
            if isinstance(source, exp.Table):
                key = resolver.resolve(engine, source)
                if key:
                    source.set("db", exp.to_identifier(resolver.tables[key].namespace or "__unqualified__"))
    for node in result_slots(copied):
        node.replace(exp.Null())
    qualify(
        copied, dialect=dialect, schema=MappingSchema(schema, dialect=dialect),
        allow_partial_qualification=False, validate_qualify_columns=True,
    )


def _es_errors(query: str, resolver: SourceResolver) -> list[str]:
    tables = [table for table in resolver.tables.values() if table.engine == "Elasticsearch"]
    if len(tables) != 1:
        return []  # The legacy protocol carries no index name; do not guess one.
    fields = {column.name for column in tables[0].columns}
    used: set[str] = set()
    field_queries = {"term", "terms", "range", "match", "match_phrase", "prefix", "wildcard", "regexp", "geo_distance", "geo_bounding_box"}

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if key == "field" and isinstance(item, str):
                    used.add(item)
                if key in field_queries and isinstance(item, dict):
                    used.update(name for name in item if name not in {"distance", "distance_type", "validation_method", "ignore_unmapped"})
                if key in {"sort", "_source"}:
                    for entry in item if isinstance(item, list) else [item]:
                        if isinstance(entry, str) and entry not in {"_score", "_doc"}:
                            used.add(entry)
                        elif isinstance(entry, dict):
                            used.update(name for name in entry if not name.startswith("_"))
                if key == "source" and isinstance(item, str):
                    used.update(re.findall(r"doc\[['\"]([^'\"]+)['\"]\]", item))
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(json.loads(query))
    return ["Elasticsearch mapping中不存在字段：" + name for name in sorted(used - fields) if "*" not in name]


def validate_integrity(answer: Any, row: dict[str, Any], resolver: SourceResolver) -> list[str]:
    errors = validate_answer(answer, row, resolver)
    if not isinstance(answer, dict):
        return errors
    pairs = step_pairs(answer)
    multi = len(pairs) > 1
    if multi:
        if len(pairs) != 2:
            errors.append("跨系统提交协议限定两步值列表传递")
        if len({answer.get(db) for db, _ in pairs}) != len(pairs):
            errors.append("同一系统跨业务库必须在一条SQL内完成连接")
        if any(answer.get(db) not in {"MYSQL", "POSTGRESQL", "SQLite"} for db, _ in pairs):
            errors.append("跨系统值列表协议仅支持SQL系统")
    for index, (db_key, query_key) in enumerate(pairs):
        engine, query = answer.get(db_key), answer.get(query_key)
        if not isinstance(query, str):
            continue
        try:
            if engine == "Elasticsearch":
                errors.extend(_es_errors(query, resolver))
                continue
            if engine not in DIALECTS:
                continue
            tree = sqlglot.parse_one(query, read=DIALECTS[engine])
            for scope in traverse_scope(tree):
                for source in scope.sources.values():
                    if not isinstance(source, exp.Table) or resolver.resolve(engine, source):
                        continue
                    owners = {table.engine for table in resolver.tables.values()
                              if table.name.lower() == source.name.lower()
                              and (not source.db or (table.namespace or "").lower() == source.db.lower())}
                    if owners and engine not in owners:
                        errors.append(f"{query_key}: 跨系统表误用：{source.sql()}实际属于{','.join(sorted(owners))}，不能放入{engine}语句。必须使用db1/query1、db2/query2两步IN (result)传递")
            slots = result_slots(tree)
            physical_result = any(table.name.lower() == "result" for table in tree.find_all(exp.Table))
            if physical_result:
                errors.append(f"{query_key}: result是值列表占位符，不能FROM/JOIN result")
            if index == 0 and slots:
                errors.append(f"{query_key}: 首步不能引用result")
            if multi and index > 0 and not slots:
                errors.append(f"{query_key}: 后步必须使用IN (result)，注释/字符串不算引用")
            if multi and index == 0 and (len(tree.selects) != 1 or any(p.is_star for p in tree.selects)):
                errors.append(f"{query_key}: 首步必须只输出一个用于后步过滤的键字段")
            errors.extend(f"{query_key}: {message}" for message in _aggregate_errors(tree))
            if engine == "POSTGRESQL":
                errors.extend(f"{query_key}: {message}" for message in _postgis_errors(tree))
            if not physical_result:
                try:
                    _qualify(tree, engine, resolver)
                except sqlglot.errors.SqlglotError as error:
                    errors.append(f"{query_key}: 字段/作用域校验失败：{str(error)[:280]}")
        except (ValueError, TypeError, sqlglot.errors.SqlglotError):
            # The compatibility validator already records malformed SQL/JSON.
            continue
    return list(dict.fromkeys(errors))
