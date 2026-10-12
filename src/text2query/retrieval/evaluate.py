"""离线表级召回评估：验证集 SQL 只作标签，不进入索引或 LLM。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..config import settings
from ..io import read_json
from .context import ContextBuilder
from .index import RetrievalIndex
from .sql_parser import SourceResolver, engine_set


def evaluate(index: RetrievalIndex, path: Path | None = None, limit: int = 0) -> dict[str, Any]:
    from ..llm.planner import SYSTEM

    path = path or settings.validation_split
    rows = read_json(path)
    if limit:
        rows = rows[:limit]
    if index.encoder is not None and rows:
        index.encoder.encode([row["question"] for row in rows])

    resolver = SourceResolver(index.tables)
    builder = ContextBuilder(index)
    training_questions = {d["text"] for d in index.documents if d["kind"] == "example"}
    results: list[dict[str, Any]] = []
    skipped: list[int] = []
    for row in rows:
        expected: set[str] = set()
        valid = True
        for db_key, query_key in [("db", "query")] + [(f"db{i}", f"query{i}") for i in range(1, 4)]:
            if db_key in row:
                try:
                    parsed = resolver.parse(row[query_key], row[db_key])
                    expected.update(parsed["table_ids"])
                    valid &= parsed["parse_status"] in ("parsed", "single_index_by_catalog")
                except ValueError:
                    valid = False
        if not valid or not expected:
            skipped.append(row["question_id"])
            continue
        engines = engine_set(row)
        ranking = index.search(row["question"], "schema", engines, 12)
        raw = [hit["table_ids"][0] for hit in ranking]
        context, _ = builder.fit(builder.assemble(row["question"], engines, row["question_id"]), SYSTEM)
        selected = {t["table_id"] for t in context["candidate_tables"]}
        result = {
            "question_id": row["question_id"],
            "expected": sorted(expected),
            "provided": sorted(selected),
            "complete_context_recall": expected <= selected,
            "irrelevant_tables": len(selected - expected),
            "train_question_duplicate": row["question"] in training_questions,
            "context_recall": len(expected & selected) / len(expected),
        }
        for k in (1, 4, 8, 12):
            result[f"recall@{k}"] = len(expected & set(raw[:k])) / len(expected)
        results.append(result)

    n = len(results)
    keys = ("recall@1", "recall@4", "recall@8", "recall@12", "context_recall", "complete_context_recall", "irrelevant_tables")
    metrics = {key: sum(r[key] for r in results) / max(n, 1) for key in keys}
    return {
        "scope": "仅表级召回；使用真实系统集合隔离召回，验证答案不进入索引/LLM",
        "evaluated": n,
        "skipped_unresolved_labels": skipped,
        "train_question_duplicates": sum(r["train_question_duplicate"] for r in results),
        "metrics": metrics,
        "cases": results,
    }
