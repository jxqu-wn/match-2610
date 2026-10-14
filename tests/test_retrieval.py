"""召回：分词、知识显式引用、SQL 解析与混合检索。"""

from __future__ import annotations

from text2query.config import settings
from text2query.io import read_json
from text2query.models import Sample
from text2query.retrieval.context import Budget, ContextBuilder, round_robin
from text2query.retrieval.index import literal_references, terms, tokenize
from text2query.retrieval.sql_parser import SourceResolver, engine_set


def test_terms_mixes_identifiers_and_chinese_ngrams():
    result = terms("统计 vehicle_type 数量")
    assert "vehicle_type" in result
    assert "统计" in result
    assert tokenize("统计") == ["统", "计", "统计"]


def test_literal_references_only_explicit(catalog):
    tables = catalog.by_id()
    text = "数据库transportation的表vehicle中，load_capacity表示载重量。"
    links = literal_references(text, tables)
    assert "MYSQL:transportation.vehicle" in links
    # 单独出现的字段名不建立表关联。
    assert literal_references("load_capacity 是最多的", tables) == {}


def test_source_resolver_extracts_tables_and_joins(catalog):
    resolver = SourceResolver(catalog.by_id())
    query = (
        "SELECT c.company_name, COUNT(*) FROM transportation.vehicle_company c "
        "JOIN transportation.driver d ON c.company_id = d.company_id GROUP BY c.company_id;"
    )
    parsed = resolver.parse(query, "MYSQL")
    assert parsed["parse_status"] == "parsed"
    assert set(parsed["table_ids"]) == {
        "MYSQL:transportation.vehicle_company",
        "MYSQL:transportation.driver",
    }
    assert parsed["joins"]


def test_engine_set_from_row():
    row = read_json(settings.qa_train)[0]
    assert engine_set(row) == ["MYSQL"]


def test_keyword_index_finds_vehicle_table(keyword_index):
    question = "统计 transportation.vehicle 中各车型的总载重量 load_capacity"
    hits = keyword_index.search(question, "schema", ["MYSQL"], 12)
    ids = [hit["table_ids"][0] for hit in hits]
    assert "MYSQL:transportation.vehicle" in ids


def test_context_assembly_marks_sources_and_budget(keyword_index):
    question = "统计各公司驾驶员中女性驾驶员的比例"
    builder = ContextBuilder(keyword_index, Budget(initial_tables=8))
    context = builder.assemble(question, ["MYSQL"], 1)
    assert context["initial_databases"] == ["MYSQL"]
    assert context["candidate_tables"]
    assert context["retrieval_budget"]["remaining_expansion_rounds"] == 1
    for table in context["candidate_tables"]:
        assert table["columns"]
    fitted, messages = builder.fit(context, "system")
    assert fitted["estimated_input_tokens"] > 0
    assert messages[0]["role"] == "system"


def test_round_robin_preserves_per_group_quota():
    groups = [
        [{"source_id": "a1"}, {"source_id": "a2"}],
        [{"source_id": "b1"}, {"source_id": "b2"}],
    ]
    assert [item["source_id"] for item in round_robin(groups, 3)] == ["a1", "b1", "a2"]


def test_budget_validation_rejects_impossible_limits():
    import pytest

    with pytest.raises(ValueError):
        Budget(initial_tables=20, total_tables=12)
    with pytest.raises(ValueError):
        Budget(context_tokens=1000, output_tokens=2000)


def test_sample_steps_supports_cross_source():
    sample = Sample.model_validate(
        {"question_id": 1, "question": "q", "db1": "MYSQL", "query1": "a", "db2": "POSTGRESQL", "query2": "b"}
    )
    assert [step[0] for step in sample.steps()] == [1, 2]


def test_index_contains_only_training_examples_and_current_engines(keyword_index):
    expected_ids = {row["question_id"] for row in read_json(settings.train_split)}
    validation_ids = {row["question_id"] for row in read_json(settings.validation_split)}
    examples = [doc for doc in keyword_index.documents if doc["kind"] == "example"]
    actual_ids = {doc["data"]["question_id"] for doc in examples}
    assert actual_ids == expected_ids
    assert not actual_ids.intersection(validation_ids)
    assert len(examples) == 2555
    assert all(set(doc["engines"]) <= {"MYSQL", "POSTGRESQL", "Elasticsearch"} for doc in keyword_index.documents)


def test_source_comparison_works_without_historical_reviews(keyword_index):
    builder = ContextBuilder(keyword_index)
    table_id = "MYSQL:transportation.vehicle"
    comparisons = builder._load_comparisons([{"checked_tables": [table_id]}], [])
    assert len(comparisons) == 1
    assert comparisons[0]["table_id"] == table_id
    assert comparisons[0]["raw_definition"]
    assert comparisons[0]["manual_corrections"] == []
    assert comparisons[0]["secondary_field_reviews"] == []
    assert comparisons[0]["special_cases"] == []
