"""Offline regression for scope repair, label isolation and selection."""

from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("quality_sweep", ROOT / "evaluation/prompt_quality/parameter_sweep.py")
sweep = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = sweep
spec.loader.exec_module(sweep)


@pytest.fixture(scope="session", autouse=True)
def prepared_catalog():
    yield


def knowledge(kid, engines, tables):
    return {
        "source_id": f"knowledge:{kid}",
        "kind": "knowledge",
        "engines": engines,
        "table_ids": tables,
        "text": "天府广场的坐标为30.66，104.063",
        "data": {"knowledge_id": kid, "knowledge_text": "原文"},
    }


def test_global_scope_rescues_unscoped_and_wrong_engine_without_mutating_original():
    docs = [knowledge(1, [], []), knowledge(2, ["MYSQL"], ["MYSQL:wrong"])]
    # Avoid the degenerate all-identical two-document BM25 corpus (negative IDF).
    for kid, text in [(3, "法院审理案件"), (4, "课程成绩记录"), (5, "股票财务报表")]:
        docs.append({**knowledge(kid, [], []), "text": text})
    before = copy.deepcopy(docs)
    view = sweep.global_documents(docs)
    assert docs == before
    original = sweep.RetrievalIndex(docs, recall_config=sweep.RecallConfig(rerank_enabled=False))
    global_index = sweep.RetrievalIndex(view, recall_config=sweep.RecallConfig(rerank_enabled=False))
    assert original.search("天府广场", "knowledge", ["Elasticsearch"], 10) == []
    hits = global_index.search("天府广场", "knowledge", sweep.ENGINES, 10)
    assert {h["source_id"] for h in hits} == {"knowledge:1", "knowledge:2"}
    assert all(d["kind"] == "knowledge" for d in view)


def test_partition_is_disjoint_deterministic_and_contains_each_multidatabase_group():
    rows = [{"question_id": i, "question": f"问题{i}"} for i in range(80)]
    groups = {r["question_id"]: sweep.GROUPS[r["question_id"] % 4] for r in rows}
    split = sweep.partitions(rows, groups)
    assert split == sweep.partitions(list(reversed(rows)), groups)
    assert len(split["generation_ids"]) == 20
    assert not set(split["generation_ids"]) & set(split["tuning_ids"])
    assert set(split["generation_ids"]) | set(split["tuning_ids"]) == set(groups)
    assert sum(groups[i] == "cross_system" for i in split["generation_ids"]) == 4
    assert sum(groups[i] == "same_system_cross_business" for i in split["generation_ids"]) == 6


def test_grid_has_scope_control_and_single_factor_variants():
    grid = sweep.initial_grid()
    assert len(grid) == len({p.name for p in grid}) == 16
    baseline = next(p for p in grid if p.name == "associated_control")
    global_default = next(p for p in grid if p.name == "global_default")
    a, b = sweep.asdict(baseline), sweep.asdict(global_default)
    assert {key for key in a if a[key] != b[key]} == {"name", "scope"}
    with pytest.raises(ValueError):
        sweep.Parameters("../bad")
    with pytest.raises(ValueError):
        sweep.Parameters("bad", knowledge=0)


def test_selection_uses_tuning_only_and_rejects_hidden_cross_system_regression():
    m = {
        "complete_db": 10,
        "complete_table": 9,
        "positive_knowledge_hits": 2,
        "tokens_p95": 14000,
        "knowledge_fidelity_errors": 0,
    }
    baseline = {"parameters": {"scope": "frozen"}, "tuning": m, "tuning_groups": {g: dict(m) for g in sweep.GROUPS}}
    candidate = copy.deepcopy(baseline)
    candidate["parameters"]["scope"] = "global"
    candidate["generation_holdback"] = {"complete_table": 0}
    assert sweep.eligible_candidate(candidate, baseline)
    oldkey = sweep.selection_key(candidate)
    candidate["generation_holdback"] = {"complete_table": 999999}
    assert sweep.selection_key(candidate) == oldkey
    candidate["tuning_groups"]["cross_system"]["complete_table"] -= 1
    assert not sweep.eligible_candidate(candidate, baseline)


def test_unavailable_semantic_metrics_are_null_not_simulated_scores():
    result = sweep.summarize([])
    assert result["necessary_fact_coverage"] is None
    assert result["answerable_prompt_rate"] is None
    assert result["semantic_noise_rate"] is None
    assert result["partial_positive_knowledge_recall"] is None


def test_silver_anchor_labels_are_exact_and_not_claimed_as_fact_gold():
    labels = sweep.literal_anchor_labels(
        [{"question_id": 1, "question": "查询成都天府广场附近医院"}],
        [
            {"knowledge_id": 10, "knowledge_text": "成都天府广场的经纬度坐标为 (30.66,104.063)"},
            {"knowledge_id": 11, "knowledge_text": "成都人民公园的经纬度坐标为 (30.6,104.0)"},
        ],
    )
    assert [(x["question_id"], x["knowledge_id"]) for x in labels] == [(1, 10)]
    assert labels[0]["label_type"] == "literal_anchor_silver"


def test_global_view_preserves_nonknowledge_and_identical_bm25_corpus():
    docs = [
        knowledge(1, [], []),
        {
            "source_id": "example:10",
            "kind": "example",
            "engines": ["MYSQL"],
            "table_ids": [],
            "text": "天府广场附近医院",
            "data": {"question_id": 10},
        },
    ]
    view = sweep.global_documents(docs)
    assert view[1] == docs[1]
    original = sweep.RetrievalIndex(docs, recall_config=sweep.RecallConfig(rerank_enabled=False))
    global_index = sweep.RetrievalIndex(view, recall_config=sweep.RecallConfig(rerank_enabled=False))
    assert original._tokenized == global_index._tokenized
    assert original._bm25.idf == global_index._bm25.idf


sql_spec = importlib.util.spec_from_file_location("quality_sql", ROOT / "evaluation/prompt_quality/sql_experiment.py")
quality_sql = importlib.util.module_from_spec(sql_spec)
sys.modules[sql_spec.name] = quality_sql
sql_spec.loader.exec_module(quality_sql)


def test_sql_collect_rejects_reference_access_before_generation_complete(tmp_path):
    from types import SimpleNamespace

    with pytest.raises(ValueError, match="Generation not complete"):
        quality_sql.collect(SimpleNamespace(output=tmp_path))


def test_format_normalization_does_not_claim_alias_changes_are_semantically_equal():
    a = {"question_id": 1, "db": "MYSQL", "query": "select count(*) as n from db.t"}
    b = {"question_id": 1, "db": "MYSQL", "query": "SELECT COUNT(*) AS n FROM db.t"}
    c = {"question_id": 1, "db": "MYSQL", "query": "SELECT COUNT(*) AS other_name FROM db.t"}
    assert quality_sql.normalized(a) == quality_sql.normalized(b)
    assert quality_sql.normalized(a) != quality_sql.normalized(c)


def test_generation_refuses_changed_prompts_before_any_network_request(tmp_path):
    from types import SimpleNamespace

    public = tmp_path / "public"
    out = tmp_path / "inference"
    public.mkdir()
    out.mkdir()
    (public / "system.txt").write_text("system")
    sweep.write_json(public / "partition.json", {"generation_ids": [1]})
    sweep.write_json(public / "questions.json", [{"question_id": 1, "question": "问题"}])
    sweep.write_json(out / "selection.json", {"configurations": ["control"], "generation_question_ids": [1]})
    prompt = out / "runs/control/prompts.jsonl"
    sweep.write_jsonl(prompt, [{"question_id": 1, "messages": [{"role": "user", "content": "问题"}]}])
    args = SimpleNamespace(output=out, public=public, diagnostic_ids="", model="deepseek-flash")
    quality_sql.prepare(args)
    prompt.write_text(prompt.read_text() + "\n")
    with pytest.raises(ValueError, match="Prompt changed"):
        quality_sql.generate(args)


def test_two_unparseable_queries_never_count_as_matching():
    a = {"question_id": 1, "db": "MYSQL", "query": "SELECT FROM ("}
    assert quality_sql.normalized(a) is None
    assert quality_sql.format_matches(a, a) is False


def test_diverse_selection_keeps_one_fixed_one_joint_and_ignores_heldback_results():
    m = {
        "complete_db": 10,
        "complete_table": 9,
        "positive_knowledge_hits": 2,
        "tokens_p95": 14000,
        "knowledge_fidelity_errors": 0,
    }
    base = {
        "parameters": {"scope": "frozen", "table_mode": "frozen"},
        "tuning": dict(m),
        "tuning_groups": {g: dict(m) for g in sweep.GROUPS},
    }
    fixed = copy.deepcopy(base)
    fixed["parameters"]["scope"] = "global"
    joint = copy.deepcopy(fixed)
    joint["parameters"]["table_mode"] = "retrieved"
    weak = copy.deepcopy(joint)
    weak["tuning"]["positive_knowledge_hits"] = 0
    weak["generation_holdback"] = {"complete_table": 999999}
    report = {"frozen_original": base, "best_fixed": fixed, "best_joint": joint, "weak_joint": weak}
    assert quality_sql.choose_diverse_configs(report) == ["frozen_original", "best_fixed", "best_joint"]
