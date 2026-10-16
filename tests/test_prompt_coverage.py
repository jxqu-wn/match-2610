"""Coverage is measured on actual prompt blocks, with complete reference targets."""

from text2query.experiments.prompt_coverage import (
    aggregate,
    coverage,
    make_prompt,
    reference_targets,
)
from text2query.models import Table
from text2query.retrieval.sql_parser import SourceResolver


def table(key, name, *, engine="MYSQL", namespace="business"):
    return Table(table_id=key, engine=engine, database=namespace, name=name,
                 raw_definition=f"CREATE TABLE {namespace}.{name} (id INT);")


def test_complete_coverage_requires_all_tables_and_allows_extras():
    assert not coverage({"a", "b"}, {"a", "c"}, True)["complete"]
    assert coverage({"a", "b"}, {"a", "b", "c"}, True)["complete"]
    assert not coverage(set(), {"a"}, True)["complete"]
    assert not coverage({"a"}, {"a"}, False)["complete"]


def test_actual_prompt_excludes_hidden_table_and_whole_table_pruning():
    a, b = "MYSQL:business.a", "MYSQL:business.b"
    excluded = "MYSQL:common.administrative_division"
    tables = {a: table(a, "a"), b: table(b, "b"), excluded: table(excluded, "administrative_division", namespace="common")}
    one = make_prompt("question", [a], tables, 16000)
    result = make_prompt("question", [a, b, excluded], tables, one["instruction_chars"])
    assert result["prompt_table_ids"] == [a]
    assert result["removed_by_char_budget"] == [b]
    assert result["excluded_table_ids"] == [excluded]
    assert tables[a].raw_definition in result["messages"][0]["content"]
    assert tables[b].raw_definition not in result["messages"][0]["content"]


def test_empty_prompt_is_recorded_without_claiming_table_coverage():
    result = make_prompt("q", [], {}, 16000)
    assert result["prompt_table_ids"] == []
    assert result["status"] == "no_usable_tables"
    assert result["messages"][1]["content"] == "q"


def test_es_index_is_a_nonempty_reference_target():
    key = "Elasticsearch:medical_institutions"
    tables = {key: Table(table_id=key, engine="Elasticsearch", name="medical_institutions")}
    result = reference_targets({"question_id": 1, "question": "q", "db": "Elasticsearch", "query": '{"query":{"match_all":{}}}'}, SourceResolver(tables))
    assert result["evaluable"]
    assert result["table_ids"] == [key]
    assert result["databases"] == [key]


def test_partial_reference_parse_does_not_count_as_full_coverage():
    key = "MYSQL:business.a"
    result = reference_targets({"question_id": 1, "question": "q", "db": "MYSQL", "query": "SELECT * FROM business.a JOIN missing.b ON a.id=b.id"}, SourceResolver({key: table(key, "a")}))
    assert result["table_ids"] == [key]
    assert not result["evaluable"]
    assert result["parse_issues"]


def test_cross_source_reference_keeps_both_steps_and_missing_second_table():
    first, second = "MYSQL:business.a", "POSTGRESQL:public.b"
    tables = {first: table(first, "a"), second: table(second, "b", engine="POSTGRESQL", namespace="public")}
    row = {"question_id": 1, "question": "q", "db1": "MYSQL", "query1": "SELECT id FROM business.a", "db2": "POSTGRESQL", "query2": "SELECT id FROM public.b WHERE id IN (result)"}
    result = reference_targets(row, SourceResolver(tables))
    assert result["evaluable"]
    assert result["table_ids"] == sorted(tables)
    assert not coverage(set(result["table_ids"]), {first}, result["evaluable"])["complete"]


def test_aggregate_counts_unresolved_questions_in_full_denominator():
    rows = []
    for valid in (True, False):
        row = {"expected": {"evaluable": valid}, "routing_correct": True, "prompt_status": "prepared"}
        for stage in ("retrieved", "prompt"):
            for kind in ("db", "table"):
                row[f"{stage}_{kind}_coverage"] = coverage({"a"}, {"a"}, valid)
        rows.append(row)
    result = aggregate(rows)
    assert result["count"] == 2
    assert result["evaluable"] == 1
    assert result["prompt_complete_table_coverage_rate"] == 0.5
