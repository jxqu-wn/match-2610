"""Offline checks for diagnostic field auditing and private request traces."""

from __future__ import annotations

import argparse
from types import SimpleNamespace

import pytest

from text2query.experiments import federation_trace
from text2query.experiments.federation_trace import TracedClient, unqualified_unknowns
from text2query.io import file_sha256, read_json, write_json
from text2query.llm.client import ChatClient
from text2query.models import Column, Table
from text2query.retrieval.sql_parser import SourceResolver
from text2query.submission.validate import validate_answer


@pytest.fixture(scope="session", autouse=True)
def prepared_catalog():
    """The diagnostic unit tests use a tiny explicit schema, not raw-data rebuilds."""
    yield


def test_diagnostic_exposes_unqualified_column_gap_without_changing_baseline():
    table = Table(table_id="MYSQL:demo.vessel", engine="MYSQL", database="demo", name="vessel",
                  columns=[Column(name="mmsi", data_type="TEXT"), Column(name="max_speed", data_type="REAL")])
    resolver = SourceResolver({table.table_id: table})
    row = {"question_id": 1, "question": "q"}
    answer = {"question_id": 1, "db": "MYSQL", "query": "SELECT name FROM demo.vessel"}
    assert validate_answer(answer, row, resolver) == []
    assert unqualified_unknowns(answer, resolver) == ["name"]
    answer["query"] = "SELECT mmsi, MAX(max_speed) AS maximum FROM demo.vessel WHERE mmsi IN (result) GROUP BY mmsi ORDER BY maximum"
    assert unqualified_unknowns(answer, resolver) == []


def test_trace_records_messages_and_resumes_without_recording_credentials(tmp_path, monkeypatch):
    monkeypatch.setattr("text2query.llm.client.openai.OpenAI", lambda **kwargs: SimpleNamespace(close=lambda: None))
    monkeypatch.setattr(ChatClient, "complete", lambda *args, **kwargs: '{"status":"complete"}')
    messages = [{"role": "user", "content": "a public question"}]
    key = "local-unit-test-credential-sentinel"
    for number in (1, 2):
        client = TracedClient(folder=tmp_path, api_key=key, model="test-model")
        assert client.complete(messages, 100, "diagnosis") == '{"status":"complete"}'
        assert read_json(tmp_path / f"request_{number:02d}.json")["messages"] == messages
    assert len(list(tmp_path.glob("request_*.json"))) == 2
    assert all(key not in path.read_text() for path in tmp_path.glob("*.json"))


def test_generation_never_reads_the_validation_reference_file(tmp_path, monkeypatch):
    output, parent = tmp_path / "run", tmp_path / "frozen"
    schema = parent / "hybrid-0.6b/preprocessed/schema_catalog.json"
    write_json(schema, {"tables": []})
    write_json(output / "questions.json", [{"question_id": 1, "question": "public question"}])
    (output / "system_prompt.txt").write_text("public instructions")
    # Any read_json of this private file would fail immediately.
    (output / "validation.json").write_text("PRIVATE REFERENCE, NOT VALID JSON")
    write_json(output / "manifest.json", {
        "frozen_inputs": {"hybrid-0.6b/preprocessed/schema_catalog.json": file_sha256(schema)},
        "system_prompt_sha256": file_sha256(output / "system_prompt.txt"),
    })
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-placeholder")
    monkeypatch.setattr(federation_trace, "InputEstimator", lambda: None)
    monkeypatch.setattr(federation_trace, "TracedClient", lambda **kwargs: SimpleNamespace(
        client=SimpleNamespace(close=lambda: None)))

    def generate(row, directory, **kwargs):
        assert row == {"question_id": 1, "question": "public question"}
        assert kwargs["system"] == "public instructions"
        return {"question": row, "answer": {"question_id": 1, "db": "MYSQL", "query": "SELECT 1"}}

    monkeypatch.setattr(federation_trace, "generate_one", generate)
    federation_trace.generate(argparse.Namespace(output=output, parent=parent, workers=1))
    assert read_json(output / "generation_complete.json")["static_success"] == 1
