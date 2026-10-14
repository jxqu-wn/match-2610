"""Schema 目录构建：用 sqlglot 解析 DDL，用 json 解析 Elasticsearch mapping。

替换原先手写的括号平衡与列切分逻辑。解析只做结构提取，不猜测主键、
知识关联由纯程序字符、正则及本地TF-IDF完成，不读取审核标签或调用模型。
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
from ..models import Catalog, Column, ForeignKey, ForeignKeyReference, Table, TrainingExampleRef
from .association import associate

ENCODINGS = ("utf-8-sig", "gb18030")
SQL_DIALECTS = {"MYSQL": "mysql", "POSTGRESQL": "postgres", "SQLite": "sqlite"}
_HEADER_DB = re.compile(r"数据库[:：]\s*(\w+)")
_HEADER_USE = re.compile(r"USE\s+(\w+)\s*;")
_ES_BLOCK = re.compile(r"PUT\s+/(\w+)\s*\n\s*\{")


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
    for match, _, end, _, _ in _es_blocks(text):
        for position in range(match.start(), end):
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
                declared_not_null or (is_primary and (engine != "SQLite" or data_type.upper() == "INTEGER"))
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


def _preceding_table_comment(text: str, start: int, table: Table) -> dict[str, Any] | None:
    """Use the closest standalone comment, crossing only this table's DROP statement."""
    lines = text[:start].splitlines()
    drop = re.compile(
        r"DROP\s+TABLE\s+(?:IF\s+EXISTS\s+)?(?:`?\w+`?\.)?`?" + re.escape(table.name) + r"`?\s*;\s*$",
        re.I,
    )
    for index in range(len(lines) - 1, -1, -1):
        line = lines[index].strip()
        if not line or drop.fullmatch(line):
            continue
        if line.startswith("--"):
            value = line[2:].strip()
            if value and not re.fullmatch(r"[=*_\-\s]+", value):
                return {"text": value, "line": index + 1, "quote": lines[index]}
        break
    return None


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
    for table in tables:
        if table.description:
            continue
        start = sum(len(line) for line in text.splitlines(keepends=True)[: table.source.start_line - 1])
        comment = _preceding_table_comment(text, start, table)
        if comment:
            table.description = comment["text"]
            table.description_origin = "schema_comment"
            table.description_source = {
                "kind": "sql_line_comment",
                "file": filename,
                "line": comment["line"],
                "quote": comment["quote"],
            }
    # Schema-provided dictionary rows are raw evidence, not hand-written synonyms.
    for match in re.finditer(r"INSERT\s+INTO\s+([`\w.]+)\s*(?:\([^;]*?\))?\s*VALUES\s*[^;]+;", masked, re.I):
        target = match.group(1).replace("`", "")
        prefix = masked[: match.start()]
        scopes = list(re.finditer(r"(?:数据库[:：]\s*|USE\s+)(\w+)", prefix, re.I))
        namespace = scopes[-1].group(1) if scopes else None
        parts = target.split(".")
        candidates = [
            t
            for t in tables
            if t.name.casefold() == parts[-1].casefold()
            and (t.namespace or "").casefold() == (parts[-2] if len(parts) > 1 else namespace or "").casefold()
        ]
        if len(candidates) != 1:
            continue
        try:
            insert = sqlglot.parse_one(match.group(), read=dialect)
        except sqlglot.errors.SqlglotError:
            continue
        values = insert.expression
        if not isinstance(values, exp.Values):
            continue
        table = candidates[0]
        table.source_values = list((table.model_extra or {}).get("source_values", []))
        for row in values.expressions:
            row_values = [str(v.this) for v in row.expressions if isinstance(v, exp.Literal) and v.is_string]
            if row_values:
                table.source_values.append(" ".join(row_values))
    return tables


def _apply_postgres_comments(text: str, tables: list[Table]) -> None:
    """应用 PostgreSQL 的 ``COMMENT ON TABLE/COLUMN`` 语句。"""
    by_id = {table.table_id: table for table in tables}
    for match in re.finditer(r"COMMENT\s+ON\s+(TABLE|COLUMN)\s+([^\s]+)\s+IS\s+'((?:''|[^'])*)'", text, re.I):
        kind, target, value = match.group(1).upper(), match.group(2).strip('"'), match.group(3).replace("''", "'")
        parts = [p.strip('"') for p in target.split(".")]
        if len(parts) < 2:
            continue
        schema_name, rest = parts[0], parts[1:]
        table_name = rest[0]
        table = next(
            (
                t
                for t in by_id.values()
                if t.engine == "POSTGRESQL" and t.name == table_name and t.schema_ == schema_name
            ),
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


def _json_line_comments(raw: str) -> tuple[str, list[tuple[int, str]]]:
    """Mask // comments while preserving offsets and // inside JSON strings."""
    chars = list(raw)
    comments = []
    quoted = escaped = False
    index = 0
    while index < len(raw):
        char = raw[index]
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif raw.startswith("//", index):
            end = raw.find("\n", index)
            if end < 0:
                end = len(raw)
            comments.append((index, raw[index:end].removesuffix("\r")))
            chars[index:end] = " " * (end - index)
            index = end
            continue
        index += 1
    return "".join(chars), comments


def _es_blocks(text: str):
    """Let the standard JSON decoder find object boundaries, including quoted braces."""
    decoder = json.JSONDecoder()
    for match in _ES_BLOCK.finditer(text):
        start = match.end() - 1
        cleaned, comments = _json_line_comments(text[start:])
        mapping, length = decoder.raw_decode(cleaned)
        yield match, start, start + length, mapping, [(offset, quote) for offset, quote in comments if offset < length]


def parse_es(text: str, filename: str, encoding: str) -> list[Table]:
    tables: list[Table] = []
    for match, start, end, mapping, comments in _es_blocks(text):
        raw = text[start:end]
        columns: list[Column] = []

        def visit(properties: dict[str, Any], prefix: str = "") -> None:
            for name, definition in properties.items():
                full = prefix + name
                columns.append(  # noqa: B023 -- visit finishes before the next index
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
        for offset, quote in comments:
            line_start = raw.rfind("\n", 0, offset) + 1
            # Only attach complete one-line property definitions. Ambiguous or
            # multi-line comments remain in raw_definition instead of guessing.
            prop = re.fullmatch(r'\s*("(?:[^"\\]|\\.)*")\s*:\s*(\{.*\})\s*,?\s*', raw[line_start:offset])
            if not prop or not quote[2:].strip():
                continue
            name, definition = json.loads(prop[1]), json.loads(prop[2])
            targets = [c for c in columns if c.name.rsplit(".", 1)[-1] == name and c.mapping == definition]
            if len(targets) != 1 or targets[0].description:
                continue
            column = targets[0]
            column.description = quote[2:].strip()
            column.description_origin = "schema_comment"
            column.description_source = {
                "kind": "es_line_comment",
                "file": filename,
                "line": text.count("\n", 0, start + offset) + 1,
                "quote": quote,
            }
        tables.append(
            Table(
                table_id=f"Elasticsearch:{match.group(1)}",
                engine="Elasticsearch",
                database=None,
                schema=None,
                object_type="index",
                name=match.group(1),
                columns=columns,
                raw_definition=text[match.start() : end],
                source={"file": filename, "encoding": encoding, "start_line": text.count("\n", 0, match.start()) + 1},
            )
        )
    return tables


# --------------------------------------------------------------------------- #
# 知识 / 训练案例关联
# --------------------------------------------------------------------------- #


def link_knowledge(
    catalog: Catalog,
    knowledge: list[dict[str, Any]],
    train_rows: list[dict[str, Any]] | None = None,
    *,
    association_method: str = "tfidf",
    association_threshold: float = 0.3,
    bm25_k1: float = 1.5,
    bm25_b: float = 0.75,
) -> None:
    provider = None
    if train_rows:
        from .training_support import TrainingSQLSupport

        provider = TrainingSQLSupport(catalog, train_rows)
    for table in catalog.tables:
        examples = provider.examples.get(table.table_id, []) if provider is not None else []
        table.training_examples = [TrainingExampleRef(**r) for r in examples[:4]]
    catalog.association_audit = associate(
        catalog,
        knowledge,
        support=provider,
        method=association_method,
        threshold=association_threshold,
        bm25_k1=bm25_k1,
        bm25_b=bm25_b,
    )


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
    lines += [f"外键：{','.join(fk.columns)} → {fk.references.table_id}" for fk in table.foreign_keys]
    lines += [f"二次复核注意：{issue['resolution']}" for issue in table.secondary_issues]
    return "\n".join(lines)


def schema_documents(catalog: Catalog) -> list[dict[str, Any]]:
    return [
        {
            "table_id": table.table_id,
            "engine": table.engine,
            "database": table.database,
            "inferred_fields": [c.name for c in table.columns if c.review_status == "inferred"],
            "unresolved_fields": [c.name for c in table.columns if c.description is None],
            "text": document_text(table),
        }
        for table in catalog.tables
    ]


# --------------------------------------------------------------------------- #
# 顶层构建
# --------------------------------------------------------------------------- #


def build_catalog(
    data_dir: Path | None = None,
    *,
    persist: bool = False,
    association_method: str = "tfidf",
    association_threshold: float = 0.3,
    bm25_k1: float = 1.5,
    bm25_b: float = 0.75,
    training_support: str = "auto",
    training_source: Path | None = None,
) -> Catalog:
    if training_support not in ("auto", "none", "sql"):
        raise ValueError("training_support must be auto, none or sql")
    use_default_data = data_dir is None
    data_dir = data_dir or settings.path("data")
    competition = data_dir / "赛题8"
    tables: list[Table] = []
    sources: list[dict[str, Any]] = []
    for filename in settings.schema_sources:
        path = competition / "Schema" / filename
        text, encoding = read_source(path)
        tables.extend(parse_sql(text, filename, encoding))
        tables.extend(parse_es(text, filename, encoding))
        sources.append(
            {"file": str(path.relative_to(data_dir.parent)), "encoding": encoding, "sha256": file_sha256(path)}
        )

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
    train_rows = None
    train_path = training_source or (settings.train_split if use_default_data else competition / "splits/train.json")
    if training_support != "none":
        if train_path.is_file():
            train_rows = read_json(train_path)
        elif training_support == "sql":
            raise FileNotFoundError(f"training-support sql requires a training file: {train_path}")
    link_knowledge(
        catalog,
        knowledge,
        train_rows,
        association_method=association_method,
        association_threshold=association_threshold,
        bm25_k1=bm25_k1,
        bm25_b=bm25_b,
    )
    catalog.association_audit["training_input"] = {
        "mode": training_support,
        "used": train_rows is not None and bool(train_rows),
        "source": str(train_path) if train_rows is not None else None,
        "sha256": file_sha256(train_path) if train_rows is not None else None,
    }
    catalog.summary = {
        "tables": len(tables),
        "by_engine": dict(Counter(t.engine for t in tables)),
        "columns": sum(len(t.columns) for t in tables),
        "described_columns": sum(bool(c.description) for t in tables for c in t.columns),
        "knowledge_association_version": catalog.association_audit["version"],
        "knowledge_pairs": sum(len(t.knowledge) for t in tables),
        "training_support_provider": catalog.association_audit["support"]["provider"],
    }
    if persist:
        output = settings.path(settings.preprocessed_dir)
        write_json(output / "schema_extracted.json", catalog.model_dump(by_alias=True))
        write_json(output / "schema_catalog.json", catalog.model_dump(by_alias=True))
        write_json(output / "knowledge_association_audit.json", catalog.association_audit)
        write_json(output / "training_support_audit.json", catalog.association_audit["support"])
        write_documents(catalog, output / "schema_documents.jsonl")
    return catalog


def load_catalog(path: Path | None = None) -> Catalog:
    return Catalog.model_validate(read_json(path or settings.schema_catalog))


def write_documents(catalog: Catalog, path: Path | None = None) -> Path:
    target = path or (settings.path(settings.preprocessed_dir) / "schema_documents.jsonl")
    write_jsonl(target, schema_documents(catalog))
    return target
