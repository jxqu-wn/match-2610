"""Exercise model-aware resume and ordered BIRD/Flash merge without network calls."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from text2query.config import settings
from text2query.io import read_json, write_json
from text2query.submission import hybrid_flash
from text2query.submission.generate import _resume
from text2query.submission.validate import resolver_for


@pytest.fixture(scope="session", autouse=True)
def prepared_catalog():
    """These isolated flow tests do not need the repository's raw-data catalog build."""
    yield


def test_flash_generation_merges_bird_in_original_order(tmp_path: Path, monkeypatch):
    parent = tmp_path / "frozen"
    for name in ("hybrid-0.6b/preprocessed/knowledge.json", "hybrid-0.6b/index/manifest.json",
                 "hybrid-0.6b/index/documents.jsonl", "hybrid-0.6b/index/vectors.npz",
                 "shared/retrieval_train.json", "shared/router.joblib"):
        target = parent / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("[]")
    write_json(parent / "hybrid-0.6b/preprocessed/schema_catalog.json", {"tables": []})
    rows = [{"question_id": 9, "question": "first"}, {"question_id": 3, "question": "BIRD"},
            {"question_id": 1, "question": "last"}]
    bird = {"question_id": 3, "db": "SQLite", "query": "SELECT 2"}
    write_json(tmp_path / "questions.json", rows)
    write_json(tmp_path / "bird.json", [bird])
    (tmp_path / "rules.txt").write_text("只输出所需列。")
    directory = tmp_path / "run"
    for row in (rows[0], rows[2]):
        write_json(directory / f"prepared_{row['question_id']}.json", {"context": {"candidate_tables": []}})
    args = argparse.Namespace(parent=parent, directory=directory, questions=tmp_path / "questions.json",
                              rules=tmp_path / "rules.txt", bird_answers=tmp_path / "bird.json",
                              result=tmp_path / "result.json", workers=2)
    requests = []

    class FakeClient:
        def __init__(self, **kwargs):
            assert kwargs["model"] == "deepseek-flash"
            assert kwargs["default_headers"] == {"Accept-Encoding": "identity"}
            self.client = SimpleNamespace(models=SimpleNamespace(
                list=lambda: SimpleNamespace(data=[SimpleNamespace(id="deepseek-flash")])) )

    def generate_one(row, directory, **kwargs):
        assert kwargs["model"] == "deepseek-flash"
        assert "只输出所需列。" in kwargs["system"]
        requests.append(row["question_id"])
        return {"question": row, "answer": {"question_id": row["question_id"], "db": "MYSQL", "query": "SELECT 1"}}

    monkeypatch.setenv("DEEPSEEK_API_KEY", "unit-test-placeholder")
    monkeypatch.setattr(hybrid_flash, "ChatClient", FakeClient)
    monkeypatch.setattr(hybrid_flash, "InputEstimator", lambda: None)
    monkeypatch.setattr(hybrid_flash, "generate_one", generate_one)
    # Restore global settings after testing the isolated artifact directory.
    monkeypatch.setattr(settings, "preprocessed_dir", settings.preprocessed_dir)
    monkeypatch.setattr(settings, "embedding_model", settings.embedding_model)
    hybrid_flash.generate(args)
    result = read_json(args.result)
    assert [row["question_id"] for row in result] == [9, 3, 1]
    assert result[1] == bird
    assert sorted(requests) == [1, 9]
    assert "unit-test-placeholder" not in json.dumps(read_json(directory / "run_config.json"))
    write_json(args.questions, rows[::-1])
    with pytest.raises(ValueError, match="Run inputs changed"):
        hybrid_flash.inputs(args)


def test_resume_does_not_reuse_a_different_models_answer(tmp_path: Path):
    row = {"question_id": 1, "question": "q"}
    record = {"model": "deepseek-flash", "question": row,
              "answer": {"question_id": 1, "db": "MYSQL", "query": "SELECT 1"}}
    write_json(tmp_path / "question_1.json", record)
    resolver = resolver_for({})
    assert _resume(tmp_path, row, resolver, "deepseek-flash") == record
    assert _resume(tmp_path, row, resolver, "deepseek-v4-pro") is None
