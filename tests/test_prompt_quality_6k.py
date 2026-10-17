"""6k applies to all input messages, including schema expansion and repair."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from text2query.io import write_json
from text2query.models import Catalog
from text2query.retrieval.context import Budget
from text2query.submission.generate import generate_one

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("quality_6k", ROOT / "evaluation/prompt_quality/iteration_6k.py")
small = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = small
spec.loader.exec_module(small)


@pytest.fixture(scope="session", autouse=True)
def prepared_catalog():
    yield


def test_grid_and_budget_allow_no_examples_and_never_exceed_6k():
    rows = small.grid()
    assert len(rows) == len({p.name for p in rows}) == 38
    assert max(p.input_budget for p in rows) == 6000
    assert {p.examples for p in rows} >= {0, 1, 2}
    assert Budget(examples=0).examples == 0
    with pytest.raises(ValueError):
        Budget(examples=-1)
    with pytest.raises(ValueError):
        small.Parameters("bad", input_budget=6001)


def test_terse_schema_keeps_every_column_fact():
    context = {"_schema_format": "terse", "candidate_tables": [{
        "column_layout": ["name", "type", "nullable", "comment", "origin", "review"],
        "columns": [["id", "INT", False, "原始字段说明", "schema", None]],
        "primary_key": ["id"], "foreign_keys": [], "source": {"file": "original.txt"},
    }], "knowledge": [], "examples": []}
    result = small.compact(context)
    assert result["candidate_tables"][0]["columns"] == [["id", "INT", False, "原始字段说明"]]
    assert result["candidate_tables"][0]["primary_key"] == ["id"]
    assert result["candidate_tables"][0]["source"] == {"file": "original.txt"}
    assert len(context["candidate_tables"][0]["columns"][0]) == 6


def test_one_example_can_be_removed_before_schema_in_small_budget():
    b = small.Builder.__new__(small.Builder)
    b.p = small.Parameters("test", examples=1)
    c = {"initial_databases": ["MYSQL"], "candidate_tables": [
        {"table_id": "MYSQL:a", "engine": "MYSQL", "source_id": "schema:a"}],
        "examples": [{"source_id": "example:1"}], "knowledge": [], "omitted_evidence": []}
    assert b._prune_once(c, {"MYSQL:a"}) == "example:1"
    assert len(c["candidate_tables"]) == 1
    assert c["examples"] == []


def test_generate_rejects_total_input_over_explicit_limit_before_api_call(tmp_path):
    row = {"question_id": 1, "question": "test"}
    write_json(tmp_path / "prepared_1.json", {"context": {"candidate_tables": [], "searched_databases": ["MYSQL"]}})
    client = SimpleNamespace(calls=[])
    client.complete = lambda *args, **kwargs: pytest.fail("oversized request must not be sent")
    result = generate_one(row, tmp_path, catalog=Catalog(), client=client, estimator=lambda messages: 6100,
                          keyword=SimpleNamespace(), model="deepseek-flash", system="system", max_input_tokens=6000)
    assert "answer" not in result
    assert "输入估算超过上限" in result["error"]
    assert result["calls"] == []
