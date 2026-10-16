"""Regression checks for benchmark scoring and label-free query construction."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

PATH = Path(__file__).resolve().parents[1] / "evaluation/table_knowledge/evaluate_hybrid_recall.py"
SPEC = importlib.util.spec_from_file_location("hybrid_evaluation", PATH)
evaluation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(evaluation)


def test_unjudged_text_is_not_a_false_positive():
    rows = [{"table_id": "A", "rankings": {method: [99, 1, 2] for method in evaluation.METHODS}}]
    scores = evaluation.score_rankings(rows, {"A": {1}}, {1, 2})
    score = scores["rrf_rerank"]["3"]
    assert (score["tp"], score["fp"], score["fn"], score["unjudged"]) == (1, 1, 0, 1)
    assert score["precision_on_judged"] == 0.5
    assert score["recall"] == 1.0
    assert score["judged_fraction"] == pytest.approx(2 / 3)
    assert score["mrr_nonempty"] == 0.5
    assert scores["rrf_rerank"]["1"]["precision_on_judged"] is None


def test_empty_tables_remain_in_precision_and_noise_counts():
    rows = [
        {"table_id": "A", "rankings": {method: [1, 2] for method in evaluation.METHODS}},
        {"table_id": "B", "rankings": {method: [2, 1] for method in evaluation.METHODS}},
    ]
    score = evaluation.score_rankings(rows, {"A": {1}, "B": set()}, {1, 2})["bm25"]["1"]
    assert (score["tp"], score["fp"], score["fn"]) == (1, 1, 0)
    assert score["precision_on_judged"] == 0.5
    assert score["empty_tables_with_judged_predictions"] == 1
    assert score["macro_recall_nonempty"] == 1.0


def test_schema_queries_have_no_knowledge_associations():
    context = evaluation.read_json(evaluation.ROOT / "evaluation/table_knowledge/input_context.json")["context"]
    queries = evaluation.raw_queries(context)
    assert len(queries) == 72
    vessel = next(row for row in queries if row["table_id"] == "MYSQL:transportation.vessel")
    assert "max_load" in vessel["query"]
    assert all(set(row) == {"table_id", "query"} for row in queries)
    docs = evaluation.documents(context["knowledge_context"])
    assert len(docs) == 247
    assert all(row["table_ids"] == [] for row in docs)
