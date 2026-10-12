"""提交文件静态校验：SQL / DSL / 跨源两步协议。

用 sqlglot 校验表与字段是否存在、语句是否只读、跨系统是否用 result 占位。
校验不等于业务或数据库执行正确性。
"""

from __future__ import annotations

import json
import re
from typing import Any

import sqlglot
from sqlglot import exp
from sqlglot.optimizer.scope import traverse_scope

from ..models import Table
from ..retrieval.sql_parser import DIALECTS, SourceResolver

ENGINES = {"MYSQL", "POSTGRESQL", "SQLite", "Elasticsearch"}
NON_READ = (exp.Insert, exp.Update, exp.Delete, exp.Create, exp.Drop, exp.Alter, exp.Into)


def step_pairs(answer: dict[str, Any]) -> list[tuple[str, str]]:
    if "db" in answer:
        return [("db", "query")]
    pairs = [(f"db{i}", f"query{i}") for i in range(1, 4) if f"db{i}" in answer]
    return pairs


def validate_answer(answer: Any, row: dict[str, Any], resolver: SourceResolver) -> list[str]:
    errors: list[str] = []
    if not isinstance(answer, dict) or answer.get("question_id") != row["question_id"]:
        return ["answer/question_id 非法"]
    pairs = step_pairs(answer)
    if "db" not in answer:
        if len(pairs) < 2 or pairs != [(f"db{i}", f"query{i}") for i in range(1, len(pairs) + 1)]:
            errors.append("多步查询必须连续且至少两步")
    allowed = {"question_id"} | {key for pair in pairs for key in pair}
    if set(answer) != allowed:
        errors.append("提交键多余或缺失")
    for db_key, query_key in pairs:
        engine, query = answer.get(db_key), answer.get(query_key)
        if engine not in ENGINES or not isinstance(query, str) or not query.strip():
            errors.append(f"{db_key}/{query_key} 非法")
            continue
        try:
            if engine == "Elasticsearch":
                if not isinstance(json.loads(query), dict):
                    errors.append("DSL 必须是对象")
            else:
                trees = sqlglot.parse(query, read=DIALECTS[engine])
                if len(trees) != 1 or not isinstance(trees[0], exp.Query):
                    errors.append("必须是单条只读查询")
                    continue
                if any(isinstance(node, NON_READ) for node in trees[0].walk()):
                    errors.append("禁止非只读 SQL")
                parsed = resolver.parse(query, engine)
                # result 是官方跨系统结果占位符。
                unknown = [x for x in parsed.get("unresolved_tables", []) if x.lower() != "result"]
                if parsed["parse_status"] == "parse_error" or unknown:
                    errors.append("SQL 未解析：" + str(unknown or parsed.get("parse_error")))
                for scope in traverse_scope(trees[0]):
                    aliases: dict[str, set[str]] = {}
                    for alias, table in scope.sources.items():
                        if isinstance(table, exp.Table):
                            key = resolver.resolve(engine, table)
                            if key:
                                aliases[alias.lower()] = {c.name.lower() for c in resolver.tables[key].columns}
                    for column in scope.columns:
                        if (
                            column.table.lower() in aliases
                            and column.name != "*"
                            and column.name.lower() not in aliases[column.table.lower()]
                        ):
                            errors.append("未知限定字段：" + column.sql())
        except Exception as error:  # noqa: BLE001 - 校验失败需可诊断
            errors.append(f"{query_key}: {type(error).__name__}: {str(error)[:200]}")
    if len(pairs) > 1 and any(not re.search(r"\bresult\b", answer.get(q, ""), re.I) for _, q in pairs[1:]):
        errors.append("后续步骤必须使用 result")
    return errors


def resolver_for(tables: dict[str, Table]) -> SourceResolver:
    return SourceResolver(tables)
