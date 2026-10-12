"""规划协议与提交校验。"""

from __future__ import annotations

from text2query.config import settings
from text2query.data.catalog import load_catalog
from text2query.llm.planner import normalize_result, validate
from text2query.retrieval.sql_parser import SourceResolver
from text2query.submission.validate import validate_answer


def _minimal_context(table_id: str = "MYSQL:transportation.vehicle_company", column: str = "company_name"):
    return {
        "initial_databases": ["MYSQL"],
        "candidate_tables": [
            {
                "source_id": "schema:" + table_id,
                "table_id": table_id,
                "engine": "MYSQL",
                "columns": [[column, "VARCHAR(100)", None, "名称", "model_accepted", "accepted"]],
            }
        ],
        "knowledge": [],
        "examples": [],
        "relations": [],
        "source_comparisons": [],
    }


def test_normalize_result_adds_assumption_status():
    result = normalize_result({"status": "ready", "assumptions": ["口径假设"]})
    assert result["status"] == "ready_with_assumptions"


def test_normalize_result_joins_string_evidence_list():
    result = normalize_result(
        {"status": "need_more_evidence", "gaps": [{"requested_evidence": ["a", "b"]}]}
    )
    assert result["gaps"][0]["requested_evidence"] == "a; b"


def test_validate_accepts_supported_ready_plan():
    context = _minimal_context()
    result = {
        "status": "ready",
        "selected_tables": [
            {
                "table_id": "MYSQL:transportation.vehicle_company",
                "required_columns": ["company_name"],
                "evidence": ["schema:MYSQL:transportation.vehicle_company"],
            }
        ],
        "join_plan": [],
        "assumptions": [],
        "unresolved_gaps": [],
        "gaps": [],
    }
    assert validate(result, context) == []


def test_validate_rejects_unknown_table_and_evidence():
    context = _minimal_context()
    result = {
        "status": "ready",
        "selected_tables": [
            {"table_id": "MYSQL:nope.missing", "required_columns": ["x"], "evidence": ["schema:ghost"]}
        ],
    }
    errors = validate(result, context)
    assert any("未知表" in error for error in errors)


def test_validate_ready_requires_no_gaps():
    context = _minimal_context()
    result = {
        "status": "ready_with_assumptions",
        "selected_tables": [
            {
                "table_id": "MYSQL:transportation.vehicle_company",
                "required_columns": ["company_name"],
                "evidence": ["schema:MYSQL:transportation.vehicle_company"],
            }
        ],
        "assumptions": [],
        "unresolved_gaps": [{"kind": "x"}],
        "gaps": [],
    }
    errors = validate(result, context)
    assert errors


def _resolver() -> SourceResolver:
    return SourceResolver(load_catalog().by_id())


def test_validate_answer_accepts_single_read_query():
    row = {"question_id": 1, "question": "q"}
    answer = {
        "question_id": 1,
        "db": "MYSQL",
        "query": (
            "SELECT c.company_name FROM transportation.vehicle_company c "
            "JOIN transportation.driver d ON c.company_id = d.company_id;"
        ),
    }
    assert validate_answer(answer, row, _resolver()) == []


def test_validate_answer_accepts_cross_source_with_result():
    row = {"question_id": 2, "question": "q"}
    answer = {
        "question_id": 2,
        "db1": "POSTGRESQL",
        "query1": "SELECT mmsi FROM public.vessel_ais_data;",
        "db2": "MYSQL",
        "query2": "SELECT company_name FROM transportation.vehicle WHERE mmsi IN (result);",
    }
    assert validate_answer(answer, row, _resolver()) == []


def test_validate_answer_rejects_unknown_qualified_column():
    row = {"question_id": 3, "question": "q"}
    answer = {"question_id": 3, "db": "MYSQL", "query": "SELECT v.ghost FROM transportation.vehicle v;"}
    assert any("未知限定字段" in error for error in validate_answer(answer, row, _resolver()))


def test_validate_answer_rejects_non_read_and_missing_result():
    row = {"question_id": 4, "question": "q"}
    delete = {"question_id": 4, "db": "MYSQL", "query": "DELETE FROM transportation.vehicle;"}
    assert validate_answer(delete, row, _resolver())
    no_result = {
        "question_id": 4,
        "db1": "MYSQL",
        "query1": "SELECT company_id FROM transportation.vehicle_company;",
        "db2": "POSTGRESQL",
        "query2": "SELECT mmsi FROM public.vessel_ais_data;",
    }
    assert any("result" in error for error in validate_answer(no_result, row, _resolver()))
