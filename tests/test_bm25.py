"""Check BM25 numerics independently of the reviewed reference."""

import numpy as np
import pytest

from text2query.data.association import associate
from text2query.data.bm25 import bm25_similarities
from text2query.models import Catalog, Column, Table


def test_bm25_matches_hand_calculation_and_query_deduplication():
    scores = bm25_similarities(
        ["token", "unknown", "token unknown", "token token"], ["token token", "other"], str.split
    )
    # N=2, df(token)=1, avgdl=1.5, dl=2, tf=2, k1=1.5, b=.75.
    # Raw BM25 / (IDF(token)*(k1+1)) = 2/(2+1.5*(.25+.75*2/1.5)).
    expected = 2 / (2 + 1.5 * (0.25 + 0.75 * 2 / 1.5))
    assert scores[0, 0] == pytest.approx(expected)
    assert scores[0, 1] == 0
    assert not scores[1].any()
    assert 0 < scores[2, 0] < scores[0, 0]
    np.testing.assert_array_equal(scores[0], scores[3])
    assert np.isfinite(scores).all() and (scores >= 0).all() and (scores <= 1).all()


def test_saturation_length_normalization_and_empty_input():
    docs = ["token", "token token", "token token token token"]
    scores = bm25_similarities(["token"], docs, str.split, b=0)[0]
    np.testing.assert_allclose(scores, [1 / 2.5, 2 / 3.5, 4 / 5.5])
    assert scores[1] - scores[0] > (scores[2] - scores[1]) / 2
    assert bm25_similarities([""], [""], str.split).shape == (1, 1)
    assert not bm25_similarities([""], [""], str.split).any()
    assert bm25_similarities([], docs, str.split).shape == (0, 3)
    assert bm25_similarities(["token"], [], str.split).shape == (1, 0)
    for k1, b in [(0, 0.75), (1.5, -0.1), (1.5, 1.1)]:
        with pytest.raises(ValueError):
            bm25_similarities(["token"], docs, str.split, k1=k1, b=b)


def test_bm25_associations_preserve_explicit_links_raw_text_and_idempotence():
    c = Catalog(
        tables=[
            Table(
                table_id="MYSQL:demo.records",
                engine="MYSQL",
                database="demo",
                name="records",
                columns=[Column(name="amount_value", data_type="INT", description="计量数值")],
            )
        ]
    )
    knowledge = [{"knowledge_id": 82281, "knowledge_text": "demo.records.amount_value 定义。"}]
    audit = associate(c, knowledge, method="bm25")
    assert audit["version"] == "bm25-v1"
    assert c.tables[0].knowledge[0].model_dump() == knowledge[0]
    assert audit["pairs"][0]["score"] == 1
    assert associate(c, knowledge, method="bm25") == audit


def test_cli_passes_bm25_options_to_catalog(monkeypatch):
    from types import SimpleNamespace

    from typer.testing import CliRunner

    from text2query.cli import app
    from text2query.data import catalog

    received = {}

    def fake_build(**kwargs):
        received.update(kwargs)
        return SimpleNamespace(summary={"knowledge_pairs": 2})

    monkeypatch.setattr(catalog, "build_catalog", fake_build)
    result = CliRunner().invoke(
        app,
        [
            "build-catalog",
            "--association-method",
            "bm25",
            "--association-threshold",
            "0.2",
            "--bm25-k1",
            "1.2",
            "--bm25-b",
            "0.5",
        ],
    )
    assert result.exit_code == 0, result.output
    assert received == {
        "persist": True,
        "association_method": "bm25",
        "association_threshold": 0.2,
        "bm25_k1": 1.2,
        "bm25_b": 0.5,
        "training_support": "auto",
        "training_source": None,
    }


def test_empty_documents_at_full_length_normalization_remain_zero():
    scores = bm25_similarities(["token", "missing"], ["", "token"], str.split, b=1)
    assert np.isfinite(scores).all()
    assert not scores[:, 0].any()
    assert scores[0, 1] > 0 and scores[1, 1] == 0
