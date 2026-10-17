"""Regression for global knowledge retention and stage-specific experiments."""
from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from text2query.models import Table
from text2query.retrieval.context import ContextBuilder
from text2query.retrieval.ranking import RecallConfig

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("quality_v2", ROOT / "evaluation/prompt_quality/iteration_v2.py")
v2 = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = v2
spec.loader.exec_module(v2)


@pytest.fixture(scope="session", autouse=True)
def prepared_catalog():
    yield


def test_independent_global_candidate_survives_cleanup_without_creating_association():
    docs = {
        "knowledge:1": {"table_ids": []},
        "knowledge:2": {"table_ids": ["MYSQL:gone"]},
        "knowledge:3": {"table_ids": ["MYSQL:kept"]},
        "knowledge:4": {"table_ids": []},
    }
    table = Table(table_id="MYSQL:kept", engine="MYSQL", name="kept")
    b = ContextBuilder.__new__(ContextBuilder)
    b.index = SimpleNamespace(by_id=docs, tables={table.table_id: table})
    c = {"candidate_tables": [{"table_id": table.table_id}], "examples": [], "knowledge": [
        {"source_id": "knowledge:1", "knowledge_text": "原文", "retrieval_scope": "global"},
        {"source_id": "knowledge:2"}, {"source_id": "knowledge:3"}, {"source_id": "knowledge:4"},
    ], "omitted_evidence": []}
    before = copy.deepcopy(docs)
    b._drop_orphans(c)
    assert [k["source_id"] for k in c["knowledge"]] == ["knowledge:1", "knowledge:3"]
    assert c["knowledge"][0]["knowledge_text"] == "原文"
    assert docs == before
    assert c["omitted_evidence"] == ["knowledge:2", "knowledge:4"]


def test_compaction_preserves_fact_payload_and_scope_but_removes_only_debug_metadata():
    original = {"candidate_tables": [{"table_id": "MYSQL:t", "columns": [["a", "INT"]], "source": "raw",
                                      "retrieval_evidence": {"score": 0.5}}],
                "knowledge": [{"knowledge_id": 1, "knowledge_text": "完整原文", "retrieval_scope": "global",
                               "retrieval_evidence": {"rank": 2}}], "examples": [{"steps": [{"query": "SELECT a FROM t"}]}],
                "retrieval_budget": {"tables": 8}, "token_estimation": "debug"}
    result = v2.compact(original)
    assert result["candidate_tables"][0]["columns"] == [["a", "INT"]]
    assert result["knowledge"][0]["knowledge_text"] == "完整原文"
    assert result["knowledge"][0]["retrieval_scope"] == "global"
    assert result["examples"] == original["examples"]
    assert "retrieval_evidence" not in result["candidate_tables"][0]
    assert "retrieval_evidence" in original["candidate_tables"][0]


def test_stage_configs_are_independent_and_cache_key_handles_unordered_exclusions():
    p = v2.Parameters("test", schema_rrf_k=20, example_bm25_top_k=100, knowledge_support_weight=0.0)
    assert p.config("schema").rrf_k == 20
    assert p.config("knowledge").rrf_k == 60
    assert p.config("example").bm25_top_k == 100
    assert p.config("schema").knowledge_support_weight == 0.0
    assert v2.memo_key({"exclude": {"a", "b"}}) == v2.memo_key({"exclude": {"b", "a"}})
    with pytest.raises(ValueError):
        RecallConfig(knowledge_support_weight=float("nan"))


def test_stage_search_restores_outer_schema_config_and_returns_independent_copies(monkeypatch):
    index = v2.StageIndex.__new__(v2.StageIndex)
    p = v2.Parameters("test", schema_rrf_k=20, rrf_k=100)
    index.configure(p)
    calls = []
    def search(self, query, kind, engines, limit, **kwargs):
        calls.append(self.recall_config.rrf_k)
        return [{"source_id": "knowledge:1"}]
    monkeypatch.setattr(v2.RetrievalIndex, "search", search)
    first = index.search("q", "knowledge", ["MYSQL"], 2, exclude=set())
    first[0]["source_id"] = "changed"
    second = index.search("q", "knowledge", ["MYSQL"], 2, exclude=set())
    assert calls == [100]
    assert second[0]["source_id"] == "knowledge:1"
    assert index.recall_config.rrf_k == 20


def test_grid_covers_quotas_and_changes_each_retrieval_stage_separately():
    grid = v2.initial_grid()
    quotas = [p for p in grid if p.name.startswith("quota_")]
    assert len(quotas) == 24
    assert {(p.tables, p.knowledge, p.examples) for p in quotas} == {
        (t,k,e) for t in (6,8,10,12) for k in (6,12,18) for e in (2,4)}
    stage = v2.second_grid(quotas[0])
    assert len(stage) == len({p.name for p in stage}) == 31
    for p in stage:
        changed = {key for key in v2.asdict(p) if v2.asdict(p)[key] != v2.asdict(quotas[0])[key]}
        assert len(changed - {"name"}) == 1


def test_small_inference_pipeline_uses_public_inputs_and_preserves_global_candidate(tmp_path, monkeypatch):
    import numpy as np
    public = tmp_path / "public"
    public.mkdir()
    table = Table(table_id="MYSQL:db.t", engine="MYSQL", database="db", name="t")
    docs = [
        {"source_id": "schema:MYSQL:db.t", "kind": "schema", "text": "测试业务表", "engines": ["MYSQL"],
         "table_ids": [table.table_id], "data": table.model_dump(by_alias=True)},
        {"source_id": "knowledge:1", "kind": "knowledge", "text": "业务定义和条件", "engines": [],
         "table_ids": [], "data": {"knowledge_id": 1, "knowledge_text": "业务定义和条件"}},
    ]
    v2.write_json(public / "questions.json", [{"question_id": 1, "question": "查询业务条件"}])
    v2.write_jsonl(public / "documents.jsonl", docs)
    v2.write_jsonl(public / "frozen_contexts.jsonl", [{"question_id": 1, "initial_databases": ["MYSQL"]}])
    v2.write_json(public / "grid.json", [v2.asdict(v2.Parameters("smoke", tables=6))])
    (public / "system.txt").write_text("只生成查询")
    v2.write_json(public / "input_manifest.json", {"files": {p.name: v2.file_sha256(p) for p in public.iterdir()}})
    class Encoder:
        signature = {"fake": True}
        model_path = tmp_path / "no_model"
        _cache = {}
        def encode(self, texts):
            return np.ones((len(texts), 2), dtype=np.float32)
        encode_documents = encode
        def unload(self):
            pass
    class Reranker:
        signature = {"fake": True}
        def score(self, query, documents):
            return [1.0] * len(documents)
        def unload(self):
            pass
    monkeypatch.setattr(v2.v1, "retrieval_encoder", lambda **kwargs: Encoder())
    monkeypatch.setattr(v2.v1, "RerankerService", lambda *args, **kwargs: Reranker())
    out = tmp_path / "inference"
    v2.run(SimpleNamespace(public=public, output=out, grid=None, embedding_model=tmp_path, reranker_model=tmp_path,
                           device="cpu", dtype="float32"))
    row = v2.read_jsonl(out / "runs/smoke/prompts.jsonl")[0]
    assert row["context"]["knowledge"][0]["knowledge_text"] == "业务定义和条件"
    assert row["context"]["knowledge"][0]["retrieval_scope"] == "global"
    assert row["estimated_tokens"] <= 21000
    assert row["messages"][1]["content"] == v2.json.dumps(row["context"], ensure_ascii=False)
