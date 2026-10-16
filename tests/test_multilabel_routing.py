"""Multilabel routes, leakage boundaries and join-specific routing metrics."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest
from sklearn.preprocessing import normalize
from typer.testing import CliRunner

from text2query import cli
from text2query.experiments.multilabel_routing import (
    evaluation_subsets,
    grouped_folds,
    selection_quality,
    selection_rank,
)
from text2query.io import read_json
from text2query.models import Column, Table
from text2query.retrieval.sql_parser import SourceResolver
from text2query.routing.multilabel import SemanticMultiLabelRouter, decode_probabilities, routing_metrics


@pytest.fixture(scope="session", autouse=True)
def prepared_catalog():
    """These routing tests use explicit tiny fixtures, with no raw catalog rebuild."""
    yield


def test_independent_labels_and_empty_route_fallback():
    scores = np.array([[0.8, 0.7, 0.1], [0.2, 0.4, 0.1], [0.7, 0.1, 0.2]])
    np.testing.assert_array_equal(decode_probabilities(scores, 0.5), [[1, 1, 0], [0, 1, 0], [1, 0, 0]])
    np.testing.assert_array_equal(decode_probabilities(scores[:1], np.array([0.9, 0.6, 0.5])), [[0, 1, 0]])
    with pytest.raises(ValueError, match="threshold"):
        decode_probabilities(scores, np.array([0.5, 0.5]))
    with pytest.raises(ValueError, match="finite"):
        decode_probabilities(np.array([[np.nan, 0.5]]), 0.5)


def test_real_model_can_select_an_unseen_system_combination_and_reload(tmp_path):
    vectors = np.repeat(np.eye(3), 12, axis=0)
    labels = [[name] for name in ("A", "B", "C") for _ in range(12)]
    embedder = SimpleNamespace(signature={"model": "unit-vectors", "instruction": "test"})
    router = SemanticMultiLabelRouter(embedder, C=100).fit_vectors(vectors, labels)
    questions = normalize(np.array([[1.0, 1.0, 0.0], [0.0, 0.0, 1.0]]))
    assert router.predict_vectors(questions) == ["A|B", "C"]
    router.save(tmp_path)
    restored = SemanticMultiLabelRouter.load(tmp_path, embedder)
    np.testing.assert_array_equal(restored.predict_proba_vectors(questions), router.predict_proba_vectors(questions))
    assert restored.predict_vectors(questions) == ["A|B", "C"]
    with pytest.raises(ValueError, match="Encoder settings"):
        SemanticMultiLabelRouter.load(tmp_path, SimpleNamespace(signature={"model": "different"}))


def test_grouped_training_folds_never_split_identical_questions():
    rows = [
        {
            "question_id": len(group) * 100 + i * 2 + duplicate,
            "question": f"{group}-{i}",
            **({"db": "MYSQL"} if group == "single" else {"db1": "MYSQL", "db2": "POSTGRESQL"}),
        }
        for group in ("single", "cross")
        for i in range(12)
        for duplicate in range(2)
    ]
    folds = grouped_folds(rows, 3)
    all_dev = []
    for fit, dev in folds:
        assert not {rows[i]["question"] for i in fit} & {rows[i]["question"] for i in dev}
        all_dev.extend(dev.tolist())
    assert sorted(all_dev) == list(range(len(rows)))


def test_selection_balances_single_and_cross_systems_using_training_only():
    actual = [["MYSQL"]] * 100 + [["MYSQL", "POSTGRESQL"]] * 4
    majority = [["MYSQL"]] * 104
    recover_cross = [["MYSQL", "POSTGRESQL"]] * 5 + [["MYSQL"]] * 95 + [["MYSQL", "POSTGRESQL"]] * 4
    a, b = selection_quality(actual, majority), selection_quality(actual, recover_cross)
    assert a["overall"]["exact_match_accuracy"] > b["overall"]["exact_match_accuracy"]
    assert selection_rank({"training_oof": b}) > selection_rank({"training_oof": a})
    assert a["cross"]["missing_system_cases"] == 4


def test_join_metrics_distinguish_full_coverage_from_exact_routes_and_false_expansion():
    actual = [["MYSQL", "POSTGRESQL"], ["MYSQL", "POSTGRESQL"], ["MYSQL"]]
    predicted = [["MYSQL"], ["MYSQL", "POSTGRESQL", "Elasticsearch"], ["MYSQL", "POSTGRESQL"]]
    result = routing_metrics(actual, predicted)
    assert result["cross_system"]["count"] == 2
    assert result["cross_system"]["full_system_coverage_correct"] == 1
    assert result["cross_system"]["exact_match_correct"] == 0
    assert result["cross_system"]["missing_system_cases"] == 1
    assert result["multi_query_detection"]["false_positive"] == 1
    assert result["multi_query_detection"]["false_negative"] == 1


def test_same_system_cross_database_is_separate_from_cross_system_routing():
    tables = [
        Table(
            table_id=f"MYSQL:{database}.{name}",
            engine="MYSQL",
            database=database,
            name=name,
            columns=[Column(name="id", data_type="INT")],
        )
        for database, name in (("sales", "orders"), ("users", "accounts"))
    ]
    rows = [
        {
            "question_id": 1,
            "question": "join",
            "db": "MYSQL",
            "query": "SELECT o.id FROM sales.orders o JOIN users.accounts a ON o.id=a.id",
        },
        {
            "question_id": 2,
            "question": "cross",
            "db1": "MYSQL",
            "query1": "SELECT id FROM sales.orders",
            "db2": "POSTGRESQL",
            "query2": "SELECT id FROM missing WHERE id IN (result)",
        },
    ]
    subsets, targets = evaluation_subsets(rows, SourceResolver({t.table_id: t for t in tables}))
    assert subsets["same_system_multi_database"] == [0]
    assert subsets["same_system_multi_table"] == [0]
    assert subsets["cross_system"] == [1]
    assert targets[0]["evaluable"]
    assert not targets[1]["evaluable"]


def test_prediction_cli_saves_a_route_that_recall_can_consume(tmp_path, monkeypatch):
    unloaded = []
    embedder = SimpleNamespace(
        signature={
            "model_path": "fixture",
            "instruction": "test",
            "device": "cpu",
            "dtype": "float32",
            "max_length": 256,
        },
        encode=lambda questions: normalize(np.array([[1.0, 1.0, 0.0]])),
        unload=lambda: unloaded.append(True),
    )
    labels = [[name] for name in ("MYSQL", "POSTGRESQL", "Elasticsearch") for _ in range(12)]
    router = SemanticMultiLabelRouter(embedder, C=100).fit_vectors(np.repeat(np.eye(3), 12, axis=0), labels)
    router.save(tmp_path / "model")
    monkeypatch.setattr("text2query.routing.embedding.EmbeddingService", lambda **kwargs: embedder)
    saved = tmp_path / "route.json"
    result = CliRunner().invoke(
        cli.app,
        [
            "route-multilabel-predict",
            "--question",
            "a multi-system question",
            "--output",
            str(tmp_path / "model"),
            "--save",
            str(saved),
        ],
    )
    assert result.exit_code == 0, result.output
    assert read_json(saved)["databases"] == ["MYSQL", "POSTGRESQL"]
    assert cli._resolve_engines(None, saved) == ["MYSQL", "POSTGRESQL"]
    assert unloaded == [True]
