"""Schema 目录构建：用 sqlglot 解析 DDL，用 json 解析 Elasticsearch mapping。

替换原先手写的括号平衡与列切分逻辑。解析只做结构提取，不猜测主键、
不根据字段同名建立关联；知识关联只使用原文中可解析的明确引用。
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import sqlglot
from sqlglot import exp
from sqlglot.tokens import TokenType

from ..config import settings
from ..io import file_sha256, read_json, write_json, write_jsonl
from ..models import Column, Catalog, ForeignKey, ForeignKeyReference, KnowledgeRef, Table, TrainingExampleRef

ENCODINGS = ("utf-8-sig", "gb18030")
SQL_DIALECTS = {"MYSQL": "mysql", "POSTGRESQL": "postgres", "SQLite": "sqlite"}
_HEADER_DB = re.compile(r"数据库[:：]\s*(\w+)")
_HEADER_USE = re.compile(r"USE\s+(\w+)\s*;")
_ES_BLOCK = re.compile(r"PUT\s+/(\w+)\s*\n\s*\{")
_KNOWLEDGE_TABLE = re.compile(r"数据库([A-Za-z0-9_]+)的表([A-Za-z0-9_]+)")
_FIELD_TEMPLATE = re.compile(r"字段{field}，.*?表示(.+?)(?:，取值为|。|$)")
_FIELD_INLINE = re.compile(r"(?<![A-Za-z0-9_]){field}(?:字段)?表示([^，；。：]+)")
_QUALIFIED_IDENTIFIER = re.compile(r"[A-Za-z][A-Za-z0-9]*_[A-Za-z0-9_]+")


def read_source(path: Path) -> tuple[str, str]:
    raw = Path(path).read_bytes()
    for encoding in ENCODINGS:
        try:
            return raw.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    raise ValueError(f"未知编码：{path}")


# --------------------------------------------------------------------------- #
# DDL -> statement spans（用 sqlglot tokenizer 找语句边界，兼容 SQLite 无分号）
# --------------------------------------------------------------------------- #


def _strip_es_blocks(text: str) -> str:
    """把 Elasticsearch 的 ``PUT /index {json}`` 块替换为等长空白，保持偏移不变。"""
    chars = list(text)
    for match in _ES_BLOCK.finditer(text):
        start = match.end() - 1
        depth, index = 0, start
        while index < len(chars):
            if chars[index] == "{":
                depth += 1
            elif chars[index] == "}":
                depth -= 1
                if depth == 0:
                    break
            index += 1
        for position in range(match.start(), min(index + 1, len(chars))):
            if chars[position] != "\n":
                chars[position] = " "
    return "".join(chars)


_CREATE_MODIFIERS = {
    getattr(TokenType, name)
    for name in ("OR", "REPLACE", "TEMPORARY", "GLOBAL", "LOCAL", "UNLOGGED", "IF", "NOT", "EXISTS")
    if hasattr(TokenType, name)
}


def table_statement_spans(text: str, dialect: str) -> list[tuple[int, int]]:
    """返回每个 ``CREATE TABLE`` 语句的 ``[start, end]`` 字符区间（含结尾分号）。"""
    spans: list[tuple[int, int]] = []
    masked = _strip_es_blocks(text)
    tokens = sqlglot.Dialect.get_or_raise(dialect).tokenize(masked)
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token.token_type != TokenType.CREATE:
            index += 1
            continue
        look = index + 1
        while look < len(tokens) and tokens[look].token_type in _CREATE_MODIFIERS:
            look += 1
        if look >= len(tokens) or tokens[look].token_type != TokenType.TABLE:
            index += 1
            continue
        # 找到定义体左括号
        depth, cursor = 0, look + 1
        while cursor < len(tokens) and tokens[cursor].token_type != TokenType.L_PAREN:
            if tokens[cursor].token_type in (TokenType.SEMICOLON,):
                break
            cursor += 1
        if cursor >= len(tokens) or tokens[cursor].token_type != TokenType.L_PAREN:
            index += 1
            continue
        depth = 0
        while cursor < len(tokens):
            if tokens[cursor].token_type == TokenType.L_PAREN:
                depth += 1
            elif tokens[cursor].token_type == TokenType.R_PAREN:
                depth -= 1
                if depth == 0:
                    break
            cursor += 1
        end = tokens[cursor].end
        # 吸收 MySQL 的 ENGINE=/COMMENT= 等尾部选项，直到分号
        tail = cursor + 1
        while tail < len(tokens) and tokens[tail].token_type != TokenType.SEMICOLON:
            if tokens[tail].token_type == TokenType.CREATE:
                break
            tail += 1
        if tail < len(tokens) and tokens[tail].token_type == TokenType.SEMICOLON:
            end = tokens[tail].end
        spans.append((token.start, end + 1))
        index = tail if (tail < len(tokens) and tokens[tail].token_type == TokenType.CREATE) else tail + 1
    return spans


# --------------------------------------------------------------------------- #
# AST -> 目录条目
# --------------------------------------------------------------------------- #


def _literal(node: Any) -> str | None:
    if isinstance(node, exp.Literal):
        return str(node.this)
    return None


def _table_comment(create: exp.Create) -> str | None:
    properties = create.args.get("properties")
    if not properties:
        return None
    for prop in properties.expressions:
        if isinstance(prop, exp.SchemaCommentProperty):
            return _literal(prop.this)
    return None


def _column_comment(column: exp.ColumnDef) -> str | None:
    for constraint in column.constraints:
        if isinstance(constraint.kind, exp.CommentColumnConstraint):
            return _literal(constraint.kind.this)
    return None


def _reference_target(reference: exp.Reference, namespace: str | None, engine: str) -> ForeignKeyReference:
    target = reference.this
    if isinstance(target, exp.Schema):
        table = target.this
        columns = [identifier.name for identifier in target.expressions]
    else:
        table = target
        columns = [identifier.name for identifier in (reference.expressions or [])]
    if isinstance(table, exp.Table):
        target_namespace = table.db or table.catalog or namespace
        name = table.name
    else:
        target_namespace, name = namespace, str(table.name if hasattr(table, "name") else target.sql())
    qualified = f"{target_namespace}.{name}" if target_namespace else name
    return ForeignKeyReference(table_id=f"{engine}:{qualified}", columns=columns)


def _parse_create_table(
    statement: str, *, dialect: str, filename: str, encoding: str, namespace: str | None, start_line: int
) -> Table:
    create = sqlglot.parse_one(statement, read=dialect)
    if not isinstance(create, exp.Create) or create.args.get("kind") != "TABLE":
        raise ValueError(f"不是 CREATE TABLE：{statement[:80]!r}")
    schema = create.this
    raw_table = schema.this if isinstance(schema, exp.Schema) else schema
    name = raw_table.name
    object_schema = raw_table.db or raw_table.catalog or None

    engine = "SQLite"
    if filename.endswith("bird_schemas.txt"):
        engine = "SQLite"
    elif (object_schema or "").lower() == "public" or "without time zone" in statement.lower():
        engine = "POSTGRESQL"
    else:
        engine = "MYSQL"

    if engine == "POSTGRESQL":
        database, schema_name = None, "public"
    else:
        database, schema_name = (namespace if engine == "MYSQL" else object_schema), None
        if engine == "SQLite":
            database = namespace
            schema_name = None

    table_id = f"{engine}:{database or schema_name}.{name}"
    columns: list[Column] = []
    primary_key: list[str] = []
    foreign_keys: list[ForeignKey] = []
    constraints: list[str] = []

    for item in schema.expressions:
        if isinstance(item, exp.ColumnDef):
            data_type = item.kind.sql(dialect=dialect) if item.kind else "UNKNOWN"
            declared_not_null = any(isinstance(c.kind, exp.NotNullColumnConstraint) for c in item.constraints)
            is_primary = any(isinstance(c.kind, exp.PrimaryKeyColumnConstraint) for c in item.constraints)
            comment = _column_comment(item)
            nullable = not (
                declared_not_null
                or (is_primary and (engine != "SQLite" or data_type.upper() == "INTEGER"))
            )
            columns.append(
                Column(
                    name=item.name,
                    data_type=data_type,
                    nullable=nullable,
                    description=comment,
                    description_origin="schema_comment" if comment else None,
                    raw_definition=item.sql(dialect=dialect),
                )
            )
            if is_primary:
                primary_key.append(item.name)
            for constraint in item.constraints:
                if isinstance(constraint.kind, exp.Reference):
                    foreign_keys.append(
                        ForeignKey(
                            columns=[item.name],
                            references=_reference_target(constraint.kind, database or schema_name, engine),
                            raw_definition=item.sql(dialect=dialect),
                        )
                    )
        else:
            # 表级约束：可能是 PRIMARY KEY / FOREIGN KEY，也可能包在 CONSTRAINT 里。
            for node in [item, *getattr(item, "expressions", [])] if isinstance(item, exp.Constraint) else [item]:
                if isinstance(node, exp.PrimaryKey):
                    primary_key = [expression.name for expression in node.expressions]
                elif isinstance(node, exp.ForeignKey):
                    reference = node.args.get("reference")
                    foreign_keys.append(
                        ForeignKey(
                            columns=[identifier.name for identifier in node.expressions],
                            references=_reference_target(reference, database or schema_name, engine),
                            raw_definition=node.sql(dialect=dialect),
                        )
                    )
            if not isinstance(item, exp.PrimaryKey):
                constraints.append(item.sql(dialect=dialect))

    comment = _table_comment(create)
    return Table(
        table_id=table_id,
        engine=engine,
        database=database,
        schema=schema_name,
        object_type="table",
        name=name,
        description=comment,
        description_origin="schema_comment" if comment else None,
        columns=columns,
        primary_key=primary_key,
        foreign_keys=foreign_keys,
        constraints=constraints,
        raw_definition=statement.strip(),
        source={"file": filename, "encoding": encoding, "start_line": start_line},
    )


def parse_sql(text: str, filename: str, encoding: str) -> list[Table]:
    masked = _strip_es_blocks(text)
    dialect = "sqlite" if filename.endswith("bird_schemas.txt") else "mysql"
    tables: list[Table] = []
    for start, end in table_statement_spans(text, dialect):
        prefix = masked[:start]
        namespaces = _HEADER_DB.findall(prefix) + _HEADER_USE.findall(prefix)
        namespace = namespaces[-1] if namespaces else None
        statement = text[start:end]
        statement_dialect = dialect
        if re.search(r"public\.|timestamp without time zone|::", statement):
            statement_dialect = "postgres"
        start_line = text.count("\n", 0, start) + 1
        tables.append(
            _parse_create_table(
                statement,
                dialect=statement_dialect,
                filename=filename,
                encoding=encoding,
                namespace=namespace,
                start_line=start_line,
            )
        )
    _apply_postgres_comments(text, tables)
    return tables


def _apply_postgres_comments(text: str, tables: list[Table]) -> None:
    """应用 PostgreSQL 的 ``COMMENT ON TABLE/COLUMN`` 语句。"""
    by_id = {table.table_id: table for table in tables}
    for match in re.finditer(
        r"COMMENT\s+ON\s+(TABLE|COLUMN)\s+([^\s]+)\s+IS\s+'((?:''|[^'])*)'", text, re.I
    ):
        kind, target, value = match.group(1).upper(), match.group(2).strip('"'), match.group(3).replace("''", "'")
        parts = [p.strip('"') for p in target.split(".")]
        if len(parts) < 2:
            continue
        schema_name, rest = parts[0], parts[1:]
        table_name = rest[0]
        table = next(
            (t for t in by_id.values() if t.engine == "POSTGRESQL" and t.name == table_name and t.schema_ == schema_name),
            None,
        )
        if table is None:
            continue
        if kind == "TABLE":
            table.description = value
            table.description_origin = "schema_comment"
        elif len(rest) >= 2:
            for column in table.columns:
                if column.name == rest[-1]:
                    column.description = value
                    column.description_origin = "schema_comment"


def parse_es(text: str, filename: str, encoding: str) -> list[Table]:
    tables: list[Table] = []
    for match in _ES_BLOCK.finditer(text):
        start = match.end() - 1
        depth, index = 0, start
        while index < len(text):
            if text[index] == "{":
                depth += 1
            elif text[index] == "}":
                depth -= 1
                if depth == 0:
                    break
            index += 1
        raw = text[start : index + 1]
        mapping = json.loads(re.sub(r"//[^\n]*", "", raw))
        columns: list[Column] = []

        def visit(properties: dict[str, Any], prefix: str = "") -> None:
            for name, definition in properties.items():
                full = prefix + name
                columns.append(
                    Column(
                        name=full,
                        data_type=definition.get("type", "object"),
                        nullable=None,
                        mapping=definition,
                    )
                )
                visit(definition.get("properties", {}), full + ".")
                visit(definition.get("fields", {}), full + ".")

        visit(mapping["mappings"]["properties"])
        tables.append(
            Table(
                table_id=f"Elasticsearch:{match.group(1)}",
                engine="Elasticsearch",
                database=None,
                schema=None,
                object_type="index",
                name=match.group(1),
                columns=columns,
                raw_definition=text[match.start() : index + 1],
                source={"file": filename, "encoding": encoding, "start_line": text.count("\n", 0, match.start()) + 1},
            )
        )
    return tables


# --------------------------------------------------------------------------- #
# 知识 / 训练案例关联
# --------------------------------------------------------------------------- #


def link_knowledge(catalog: Catalog, knowledge: list[dict[str, Any]], train_rows: list[dict[str, Any]]) -> None:
    index = {(t.database, t.name): t for t in catalog.tables if t.database}
    for item in knowledge:
        match = _KNOWLEDGE_TABLE.search(item["knowledge_text"])
        table = index.get((match.group(1), match.group(2))) if match else None
        if table is None:
            continue
        table.knowledge.append(KnowledgeRef(knowledge_id=item["knowledge_id"], knowledge_text=item["knowledge_text"]))
        for column in table.columns:
            field = re.search(
                _FIELD_TEMPLATE.pattern.format(field=re.escape(column.name)), item["knowledge_text"]
            )
            if field:
                column.knowledge_ids.append(item["knowledge_id"])
                if not column.description:
                    column.description = field.group(1)
                    column.description_origin = "knowledge"

    for table in catalog.tables:
        # 一条知识可能同时描述多个字段，使用较宽松的“字段…表示…”句式。
        for column in table.columns:
            if column.description:
                continue
            for item in table.knowledge:
                match = re.search(
                    _FIELD_INLINE.pattern.format(field=re.escape(column.name)), item.knowledge_text or ""
                )
                if match:
                    column.description = re.split(r"[（(]", match.group(1), maxsplit=1)[0].strip()
                    column.description_origin = "knowledge"
                    column.knowledge_ids.append(item.knowledge_id)
                    break

        qualified = (
            table.name
            if table.engine == "POSTGRESQL"
            else (f"{table.namespace}.{table.name}" if table.namespace else table.name)
        )
        pattern = re.compile(r"(?<!\w)" + re.escape(qualified) + r"(?!\w)", re.I)
        for row in train_rows:
            for db_key, query_key in [("db", "query")] + [(f"db{i}", f"query{i}") for i in range(1, 4)]:
                if row.get(db_key) != table.engine or not row.get(query_key):
                    continue
                if pattern.search(row[query_key]):
                    table.training_examples.append(
                        TrainingExampleRef(
                            question_id=row["question_id"],
                            question=row["question"],
                            query=row[query_key],
                            step=query_key,
                        )
                    )
        table.training_examples = table.training_examples[:4]


def resolve_implicit_foreign_keys(catalog: Catalog) -> None:
    """为未显式给出目标列的引用补上目标表主键。"""
    by_id = catalog.by_id()
    for table in catalog.tables:
        for column in table.columns:
            if column.name in table.primary_key and table.engine != "SQLite":
                column.nullable = False
        for fk in table.foreign_keys:
            if fk.references.columns:
                continue
            target = by_id.get(fk.references.table_id)
            if target is None or not target.primary_key:
                raise ValueError(f"无法解析隐式引用主键：{fk}")
            fk.references.columns = list(target.primary_key)
            fk.implicit_primary_key = True


def document_text(table: Table) -> str:
    lines = [
        f"系统：{table.engine}",
        f"业务库：{table.namespace or '未提供'}",
        f"表/索引：{table.name}",
        f"描述：{table.description or '未确认'}",
    ]
    lines += [f"字段：{c.name} ({c.data_type})：{c.description or '未确认'}" for c in table.columns]
    lines += [
        f"外键：{','.join(fk.columns)} → {fk.references.table_id}" for fk in table.foreign_keys
    ]
    lines += [f"二次复核注意：{issue['resolution']}" for issue in table.secondary_issues]
    return "\n".join(lines)


def schema_documents(catalog: Catalog) -> list[dict[str, Any]]:
    return [
        {
            "table_id": table.table_id,
            "engine": table.engine,
            "database": table.database,
            "inferred_fields": [
                c.name for c in table.columns if c.review_status == "inferred"
            ],
            "unresolved_fields": [c.name for c in table.columns if c.description is None],
            "text": document_text(table),
        }
        for table in catalog.tables
    ]


# --------------------------------------------------------------------------- #
# 顶层构建
# --------------------------------------------------------------------------- #


def build_catalog(data_dir: Path | None = None, *, persist: bool = False) -> Catalog:
    data_dir = data_dir or settings.path("data")
    competition = data_dir / "赛题8"
    tables: list[Table] = []
    sources: list[dict[str, Any]] = []
    for filename in settings.schema_sources:
        path = competition / "Schema" / filename
        text, encoding = read_source(path)
        tables.extend(parse_sql(text, filename, encoding))
        tables.extend(parse_es(text, filename, encoding))
        sources.append({"file": str(path.relative_to(data_dir.parent)), "encoding": encoding, "sha256": file_sha256(path)})

    ids = [t.table_id for t in tables]
    if len(ids) != len(set(ids)):
        raise ValueError("表标识重复")
    for table in tables:
        names = table.column_names
        if len(names) != len(set(names)):
            raise ValueError(f"字段名重复：{table.table_id}")

    catalog = Catalog(format_version=1, sources=sources, tables=tables)
    resolve_implicit_foreign_keys(catalog)
    knowledge = read_json(competition / "knowledge.json")
    train_rows = read_json(settings.train_split)
    link_knowledge(catalog, knowledge, train_rows)
    catalog.summary = {
        "tables": len(tables),
        "by_engine": dict(Counter(t.engine for t in tables)),
        "columns": sum(len(t.columns) for t in tables),
        "described_columns": sum(bool(c.description) for t in tables for c in t.columns),
    }
    if persist:
        output = settings.path(settings.preprocessed_dir)
        write_json(output / "schema_extracted.json", catalog.model_dump(by_alias=True))
        write_json(output / "schema_catalog.json", catalog.model_dump(by_alias=True))
        write_documents(catalog, output / "schema_documents.jsonl")
    return catalog


def load_catalog(path: Path | None = None) -> Catalog:
    return Catalog.model_validate(read_json(path or settings.schema_catalog))


def write_documents(catalog: Catalog, path: Path | None = None) -> Path:
    target = path or (settings.path(settings.preprocessed_dir) / "schema_documents.jsonl")
    write_jsonl(target, schema_documents(catalog))
    return target
