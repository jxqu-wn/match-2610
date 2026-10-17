import pytest

from text2query.models import Catalog
from text2query.submission.evidence import compact_table, fk_candidates, knowledge_scope


@pytest.fixture(scope="session", autouse=True)
def prepared_catalog():
    yield


def tables():
    return Catalog.model_validate({"tables": [
        {"table_id": "MYSQL:business.child", "engine": "MYSQL", "database": "business", "name": "child",
         "foreign_keys": [{"columns": ["pid"], "references": {"table_id": "MYSQL:business.parent", "columns": ["id"]}}],
         "source_values": ["CANCELLED 注销"], "columns": [{"name": "pid", "data_type": "INT", "description": "原文"}]},
        {"table_id": "MYSQL:business.parent", "engine": "MYSQL", "database": "business", "name": "parent", "columns": []},
    ]}).by_id()


def test_scope_exclusion_depends_on_declared_namespace_not_ids():
    t = tables()
    assert not knowledge_scope("在数据库foreign_db的表orders中，金额指sales。", t)["eligible"]
    assert knowledge_scope("在数据库business的表child中。", t)["eligible"]
    assert knowledge_scope("退款率为退款订单数除以全部订单数。", t)["eligible"]
    assert knowledge_scope("使用child.pid连接parent.id。", t)["eligible"]


def test_fk_closure_stays_candidate_and_source_values_are_exact():
    t = tables()
    rows = fk_candidates(["MYSQL:business.child"], t)
    assert rows[0]["table_id"] == "MYSQL:business.parent"
    assert rows[0]["association_confirmed"] is False
    before = t["MYSQL:business.child"].model_dump()
    view = compact_table(t["MYSQL:business.child"])
    assert view["source_values"] == ["CANCELLED 注销"]
    assert view["columns"][0][3] == "原文"
    assert t["MYSQL:business.child"].model_dump() == before
