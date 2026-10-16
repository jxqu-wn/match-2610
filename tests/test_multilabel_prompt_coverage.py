"""Actual prompt coverage and local-score replay boundaries."""

from __future__ import annotations

import argparse
from types import SimpleNamespace

import pytest

from text2query.experiments import multilabel_prompt_coverage
from text2query.experiments.multilabel_prompt_coverage import ResumableScores, score_rows
from text2query.io import file_sha256, write_json, write_jsonl
from text2query.models import Table


@pytest.fixture(scope="session", autouse=True)
def prepared_catalog():
    yield


def test_local_scores_resume_without_mixing_other_precision_signatures(tmp_path):
    calls = []

    def infer(query, documents):
        calls.append((query, documents))
        return [float(len(text)) for text in documents]

    service = SimpleNamespace(signature={"model": "fixture", "dtype": "float32"}, score=infer)
    cache = ResumableScores(service, tmp_path)
    assert cache.score("q", ["a", "bb", "a"]) == [1.0, 2.0, 1.0]
    assert calls == [("q", ["a", "bb"])]
    restored = ResumableScores(service, tmp_path)
    assert restored.score("q", ["bb", "a"]) == [2.0, 1.0]
    assert restored.computed == 0
    assert len(calls) == 1
    with pytest.raises(ValueError, match="signature changed"):
        ResumableScores(SimpleNamespace(signature={"model": "fixture", "dtype": "bfloat16"}), tmp_path)


def test_business_databases_can_be_complete_while_a_required_table_is_missing():
    tables = {
        f"MYSQL:{db}.{name}": Table(table_id=f"MYSQL:{db}.{name}", engine="MYSQL", database=db, name=name)
        for db, name in (("business", "a"), ("business", "b"), ("other", "c"))
    }
    target = {
        "engines": ["MYSQL"],
        "databases": ["MYSQL:business", "MYSQL:other"],
        "table_ids": list(tables),
        "evaluable": True,
    }
    prompt = {
        "question_id": 1,
        "question": "q",
        "predicted_engines": ["MYSQL"],
        "status": "prepared",
        "retrieved_table_ids": list(tables),
        "prompt_table_ids": ["MYSQL:business.a", "MYSQL:other.c"],
        "removed_by_char_budget": ["MYSQL:business.b"],
        "instruction_chars": 100,
    }
    result = score_rows([prompt], {1: target}, tables)[0]
    assert result["retrieved_table_coverage"]["complete"]
    assert result["prompt_db_coverage"]["complete"]
    assert not result["prompt_table_coverage"]["complete"]
    assert result["prompt_table_coverage"]["missing"] == ["MYSQL:business.b"]


def test_scoring_waits_for_every_prompt_before_reference_access(tmp_path, monkeypatch):
    write_jsonl(tmp_path / "prompts.jsonl", [{"question_id": 1}])
    write_json(tmp_path / "questions.json", [{"question_id": 1}, {"question_id": 2}])
    write_json(tmp_path / "run.json", {"prepared": 1, "prompts_sha256": file_sha256(tmp_path / "prompts.jsonl")})
    monkeypatch.setattr(
        multilabel_prompt_coverage, "checked_inputs", lambda args: pytest.fail("Reference stage entered early")
    )
    with pytest.raises(ValueError, match="all public questions"):
        multilabel_prompt_coverage.score(argparse.Namespace(output=tmp_path))
