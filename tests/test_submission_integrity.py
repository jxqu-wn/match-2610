"""Regression tests for real false negatives in submission validation."""

import pytest

from text2query.models import Catalog
from text2query.submission.integrity import validate_integrity
from text2query.submission.validate import resolver_for


@pytest.fixture(scope="session", autouse=True)
def prepared_catalog():
    yield


@pytest.fixture
def resolver():
    catalog = Catalog.model_validate({"tables": [
        {"table_id": "MYSQL:demo.a", "engine": "MYSQL", "database": "demo", "name": "a", "columns": [
            {"name": "id", "data_type": "INT"}, {"name": "value", "data_type": "INT"}]},
        {"table_id": "MYSQL:demo.b", "engine": "MYSQL", "database": "demo", "name": "b", "columns": [
            {"name": "id", "data_type": "INT"}]},
        {"table_id": "POSTGRESQL:public.p", "engine": "POSTGRESQL", "schema": "public", "name": "p", "columns": [
            {"name": "id", "data_type": "INT"}, {"name": "value", "data_type": "INT"}]},
    ]})
    return resolver_for(catalog.by_id())


def check(query, resolver):
    return validate_integrity({"question_id": 1, "db": "MYSQL", "query": query}, {"question_id": 1}, resolver)


@pytest.mark.parametrize("query", [
    "SELECT ghost FROM demo.a",
    "SELECT id FROM demo.a a JOIN demo.b b ON a.id=b.id",
    "WITH x AS (SELECT id FROM demo.a) SELECT value FROM x",
    "SELECT SUM(MAX(value)) FROM demo.a",
    "SELECT SUM(LAG(value) OVER (ORDER BY id)) FROM demo.a",
])
def test_reject_missing_ambiguous_derived_and_invalid_aggregate(query, resolver):
    assert check(query, resolver)


@pytest.mark.parametrize("query", [
    "SELECT id FROM demo.a",
    "WITH x AS (SELECT id FROM demo.a) SELECT id FROM x",
    "SELECT SUM((SELECT MAX(value) FROM demo.a)) FROM demo.a",
    "SELECT id, SUM(SUM(value)) OVER () FROM demo.a GROUP BY id",
    "SELECT a.id FROM demo.a a WHERE EXISTS(SELECT 1 FROM demo.b b WHERE b.id=a.id)",
])
def test_accept_valid_scopes_and_window_after_aggregation(query, resolver):
    assert check(query, resolver) == []


def test_values_protocol_requires_one_key_and_actual_in_slot(resolver):
    answer = {"question_id": 1, "db1": "MYSQL", "query1": "SELECT id FROM demo.a",
              "db2": "POSTGRESQL", "query2": "SELECT id FROM public.p WHERE id IN (result)"}
    assert validate_integrity(answer, {"question_id": 1}, resolver) == []
    for replacement in ("SELECT id FROM public.p -- result", "SELECT id FROM result", "SELECT id FROM public.p WHERE 'result'='result'"):
        assert validate_integrity({**answer, "query2": replacement}, {"question_id": 1}, resolver)
    assert validate_integrity({**answer, "query1": "SELECT id,value FROM demo.a"}, {"question_id": 1}, resolver)


def test_postgis_geometry_only_predicate_does_not_reject_geography_supported_ones(resolver):
    def query(predicate):
        return {"question_id": 1, "db": "POSTGRESQL",
                "query": f"SELECT id FROM public.p WHERE {predicate}('POINT(1 2)'::geography,'POINT(1 2)'::geography)"}
    assert any("ST_Within" in message for message in validate_integrity(query("ST_Within"), {"question_id": 1}, resolver))
    assert validate_integrity(query("ST_Intersects"), {"question_id": 1}, resolver) == []
