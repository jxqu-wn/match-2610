import pytest

from text2query.models import Catalog
from text2query.submission.training_bindings import TrainingBindings


@pytest.fixture(scope="session", autouse=True)
def prepared_catalog():
    yield


def test_name_binding_comes_from_original_question_and_resolved_column():
    catalog = Catalog.model_validate({"tables": [{"table_id": "MYSQL:demo.stocks", "engine": "MYSQL", "database": "demo",
        "name": "stocks", "columns": [{"name": "stock_name", "data_type": "TEXT"}]}]})
    docs = {"example:1": {"kind": "example", "source_id": "example:1", "data": {
        "question": "查询某某公司数据", "steps": [{"engine": "MYSQL", "query": "SELECT stock_name FROM demo.stocks s WHERE s.stock_name='某某公司'"}]}},
        "example:2": {"kind": "example", "source_id": "example:2", "data": {
            "question": "查询其他企业", "steps": [{"engine": "MYSQL", "query": "SELECT stock_name FROM demo.stocks WHERE stock_name='未提及公司'"}]}}}
    index = TrainingBindings(docs, catalog)
    found = index.match("请计算某某公司年度指标")
    assert len(found) == 1
    assert found[0]["table_id"] == "MYSQL:demo.stocks"
    assert found[0]["column"] == "stock_name"
    assert found[0]["examples"][0]["source_id"] == "example:1"
    assert "unverified" in found[0]["status"]
    assert index.match("未提及公司") == []
