"""Program-only association boundaries; synthetic fixtures contain no reference IDs."""

from copy import deepcopy

import pytest

from text2query.data.association import associate, literal_references
from text2query.data.catalog import link_knowledge, parse_sql
from text2query.models import Catalog, Column, Table
from text2query.retrieval.index import RetrievalIndex, build_documents


def table(name, namespace="demo", engine="MYSQL", **kwargs):
    return Table(table_id=f"{engine}:{namespace}.{name}", name=name, engine=engine, database=namespace, **kwargs)


def test_explicit_multitable_unknown_and_identifier_boundaries():
    tables = [table("entry"), table("entry_log"), table("other")]
    by_id = {t.table_id: t for t in tables}
    links = literal_references("数据库missing的表unknown。数据库demo的表entry_log和other。", by_id)
    assert set(links) == {"MYSQL:demo.entry_log", "MYSQL:demo.other"}
    assert set(literal_references("使用 `demo`.`entry` 与 demo.other。", by_id)) == {
        "MYSQL:demo.entry",
        "MYSQL:demo.other",
    }
    assert literal_references("demo.entry_log_extra", by_id) == {}
    assert set(literal_references("使用demo.entry字段。", by_id)) == {"MYSQL:demo.entry"}


def test_same_namespace_cross_engine_is_not_silently_resolved():
    tables = [table("entry"), table("entry", engine="POSTGRESQL")]
    assert literal_references("demo.entry", {t.table_id: t for t in tables}) == {}


def test_raw_fidelity_id_independence_and_idempotence():
    c = Catalog(
        tables=[
            table("entry", columns=[Column(name="metric_value", data_type="INT", description="原始注释")]),
            table("empty"),
        ]
    )
    data = [{"knowledge_id": 92701, "knowledge_text": "定义：demo.entry.metric_value。"}]
    associate(c, data)
    assert c.tables[0].knowledge[0].knowledge_text == data[0]["knowledge_text"]
    once = c.model_dump()
    associate(c, data)
    assert c.model_dump() == once
    renumbered = deepcopy(data)
    renumbered[0]["knowledge_id"] = 81337
    associate(c, renumbered)
    assert c.tables[0].knowledge[0].knowledge_id == 81337
    assert not c.tables[1].knowledge
    assert c.tables[0].columns[0].description == "原始注释"
    with pytest.raises(ValueError, match="duplicate knowledge"):
        associate(c, data + data)


@pytest.mark.parametrize("method", ["tfidf", "bm25"])
def test_no_model_or_reference_access(monkeypatch, method):
    import builtins
    import socket
    from pathlib import Path

    original = builtins.open

    def guarded(file, *args, **kwargs):
        assert not any(
            word in str(file) for word in ("evaluation/", "decisions.json", "manual_review", "secondary_review")
        )
        return original(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", guarded)

    def no_io(*args, **kwargs):
        raise AssertionError("matcher attempted file/network access")

    monkeypatch.setattr(Path, "open", no_io)
    monkeypatch.setattr(socket.socket, "connect", no_io)
    c = Catalog(tables=[table("entry")])
    link_knowledge(c, [{"knowledge_id": 85021, "knowledge_text": "demo.entry"}], [], association_method=method)
    assert len(c.tables[0].knowledge) == 1
    assert not c.enrichment


def test_dictionary_values_come_from_raw_schema():
    text = "数据库：demo\nCREATE TABLE kinds(code VARCHAR(20), name VARCHAR(20));\nINSERT INTO kinds VALUES ('X','甲类别'),('Y','乙类别');"
    parsed = parse_sql(text, "test_schema.txt", "utf-8")
    assert parsed[0].source_values == ["X 甲类别", "Y 乙类别"]
    c = Catalog(tables=parsed)
    associate(c, [{"knowledge_id": 82100, "knowledge_text": "包含甲类别与乙类别。"}])
    assert c.tables[0].knowledge


def test_documents_and_retrieval_do_not_add_associations():
    c = Catalog(tables=[table("entry", columns=[Column(name="metric_value", data_type="INT")])])
    data = [{"knowledge_id": 83000, "knowledge_text": "demo.entry 的 metric_value 定义。"}]
    docs, _ = build_documents(c, data, [])
    kdoc = next(d for d in docs if d["kind"] == "knowledge")
    assert kdoc["table_ids"] == []
    index = RetrievalIndex(docs)
    assert index.knowledge_links[kdoc["source_id"]] == {}
    assert index.explicit_knowledge_links[kdoc["source_id"]] == {}
