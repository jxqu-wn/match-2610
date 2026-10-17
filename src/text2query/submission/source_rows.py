"""Question-matched original INSERT rows, with exact SQL/line provenance.

This reader supplies evidence, never edits the catalog or repairs source values.
Names and hierarchy disagreements remain visible to the SQL generation model.
"""

from __future__ import annotations

from pathlib import Path

import sqlglot
from sqlglot import exp

from ..io import file_sha256
from ..models import Catalog
from ..retrieval.sql_parser import SourceResolver


class SourceRows:
    def __init__(self, path: Path, catalog: Catalog):
        self.path, self.digest = path, file_sha256(path)
        resolver = SourceResolver(catalog.by_id())
        self.rows = []
        for line_number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
            if not line.strip():
                continue
            statement = sqlglot.parse_one(line, read="mysql")
            if not isinstance(statement, exp.Insert) or not isinstance(statement.this, exp.Schema) or not isinstance(statement.expression, exp.Values):
                raise ValueError(f"Expected one literal INSERT per line: {path}:{line_number}")
            table = statement.this.this
            key = resolver.resolve("MYSQL", table)
            if not key:
                raise ValueError(f"Source row has no unambiguous schema table: {table.sql()}")
            columns = [column.name for column in statement.this.expressions]
            if not set(columns) <= set(resolver.tables[key].column_names):
                raise ValueError("Source row declares a field absent from Schema")
            for row in statement.expression.expressions:
                values = []
                for value in row.expressions:
                    if isinstance(value, exp.Null):
                        values.append(None)
                    elif isinstance(value, exp.Literal):
                        values.append(value.this if value.is_string else int(value.this) if value.is_int else float(value.this))
                    else:
                        raise ValueError("Only literal source values are accepted")
                if len(values) != len(columns):
                    raise ValueError("Source row width mismatch")
                self.rows.append({"table_id": key, "values": dict(zip(columns, values, strict=True)),
                                  "source_file": str(path), "source_sha256": self.digest,
                                  "source_line": line_number, "raw_sql": line})

    def match(self, question: str, knowledge: list[dict] = (), limit: int = 12) -> list[dict]:
        texts = [(question, 100)] + [(item["knowledge_text"], max(1, 20 - i)) for i, item in enumerate(knowledge)]
        matches = []
        for row in self.rows:
            name = row["values"].get("name")
            if not isinstance(name, str) or len(name) < 2:
                continue
            aliases = [name]
            # Prefixes are candidate search aliases only. Raw names/IDs/levels
            # remain unchanged and the matched alias is separately identified.
            if name.endswith(("省", "市", "县", "区", "州")):
                aliases += [name[:n] for n in range(2, min(6, len(name)))]
            found = [(priority * 100 + len(alias), alias) for text, priority in texts for alias in aliases if alias in text]
            if found:
                score, alias = max(found)
                matches.append((score, row["source_line"], {**row, "matched_question_or_knowledge_alias": alias,
                                                          "search_match_is_not_a_confirmed_scope": True}))
        selected = [row for _, _, row in sorted(matches, key=lambda item: (-item[0], item[1]))[:limit]]
        existing = {row["source_line"] for row in selected}
        anomalies = []
        for region in selected:
            if len(anomalies) >= 2:
                break
            values = region["values"]
            if values.get("level") != 1 or not values.get("name", "").endswith("市"):
                continue
            for row in self.rows:
                data = row["values"]
                if (data.get("province_name") == values["name"]
                        and data.get("city_name") not in {None, "", values["name"]}
                        and row["source_line"] not in existing):
                    anomalies.append({**row, "evidence_role": "original_source_city_name_inconsistency"})
                    existing.add(row["source_line"])
                    if len(anomalies) >= 2:
                        break
        return selected[:max(0, limit - len(anomalies))] + anomalies[:limit]
