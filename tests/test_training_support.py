"""Optional training evidence remains detachable and respects SQL field lineage."""

import builtins
from copy import deepcopy

import pytest

from text2query.config import settings
from text2query.data.association import associate
from text2query.data.catalog import build_catalog, link_knowledge
from text2query.data.training_support import TrainingSQLSupport
from text2query.models import Catalog, Column, Table


def sample_catalog():
    return Catalog(
        tables=[
            Table(
                table_id=f"MYSQL:demo.{name}",
                engine="MYSQL",
                database="demo",
                name=name,
                columns=[Column(name=c, data_type="INT") for c in columns],
            )
            for name, columns in [("fact", ["id", "metric", "flag"]), ("names", ["id", "title"])]
        ]
    )


def row(sql, number=1, question="计量指标汇总"):
    return {"question_id": number, "question": question, "db": "MYSQL", "query": sql}


def test_roles_distinguish_measure_filter_group_and_join_only_table():
    c = sample_catalog()
    sql = "SELECT SUM(f.metric) FROM demo.fact f JOIN demo.names n ON f.id=n.id WHERE f.flag>0 GROUP BY f.flag HAVING SUM(f.metric)>1 ORDER BY SUM(f.metric)"
    support = TrainingSQLSupport(c, [row(sql)])
    records = {r["table_id"]: r for r in support.records}
    assert records["MYSQL:demo.names"]["fields"] == {"id": ["join"]}
    assert records["MYSQL:demo.names"]["role_weight"] == 0
    fields = records["MYSQL:demo.fact"]["fields"]
    assert set(fields["metric"]) == {"calculation", "having", "order"}
    assert set(fields["flag"]) == {"filter", "group"}


def test_cte_alias_resolves_back_to_original_fields():
    sql = "WITH d AS (SELECT metric AS amount, flag FROM demo.fact) SELECT SUM(d.amount) FROM d WHERE d.flag>0"
    support = TrainingSQLSupport(sample_catalog(), [row(sql)])
    fact = next(r for r in support.records if r["table_id"] == "MYSQL:demo.fact")
    assert "calculation" in fact["fields"]["metric"]
    assert "filter" in fact["fields"]["flag"]
    assert "amount" not in fact["fields"]


def test_correlated_and_implicit_equality_joins_do_not_become_filter_evidence():
    sql = "SELECT SUM(f.metric) FROM demo.fact f WHERE EXISTS(SELECT 1 FROM demo.names n WHERE n.id=f.id)"
    support = TrainingSQLSupport(sample_catalog(), [row(sql)])
    names = next(r for r in support.records if r["table_id"] == "MYSQL:demo.names")
    assert names["fields"] == {"id": ["join"]}
    assert names["role_weight"] == 0


def test_unknown_or_ambiguous_fields_do_not_get_assigned_arbitrarily():
    support = TrainingSQLSupport(
        sample_catalog(), [row("SELECT id, missing FROM demo.fact f JOIN demo.names n ON f.id=n.id")]
    )
    assert all(r["role_weight"] == 0 for r in support.records)
    assert any(i["reason"] == "unresolved_columns" for i in support.issues)
    broken = TrainingSQLSupport(sample_catalog(), [row("SELECT (")])
    assert broken.issues and not broken.records


def test_single_table_count_and_dsl_field_roles():
    support = TrainingSQLSupport(sample_catalog(), [row("SELECT COUNT(*) FROM demo.fact")])
    assert support.records[0]["fields"] == {"*": ["calculation"]}
    c = Catalog(
        tables=[
            Table(
                table_id="Elasticsearch:demo",
                engine="Elasticsearch",
                name="demo",
                columns=[Column(name="metric", data_type="integer")],
            )
        ]
    )
    support = TrainingSQLSupport(
        c,
        [
            {
                "question_id": 1,
                "question": "计量值",
                "db": "Elasticsearch",
                "query": '{"query":{"range":{"metric":{"gt":1}}},"aggs":{"total":{"sum":{"field":"metric"}}}}',
            }
        ],
    )
    assert set(support.records[0]["fields"]["metric"]) == {"calculation", "filter"}


@pytest.mark.parametrize("method", ["tfidf", "bm25"])
def test_plugin_only_affects_support_channel_and_can_be_removed(method):
    c = sample_catalog()
    rows = [row("SELECT SUM(f.metric) FROM demo.fact f JOIN demo.names n ON f.id=n.id", i) for i in [1, 2]]
    data = [{"knowledge_id": 93121, "knowledge_text": "计量指标汇总"}]
    before = deepcopy(c.model_dump())
    plain = associate(c, data, method=method)
    base = {(r["table_id"], r["knowledge_id"]): r["components"]["base"] for r in plain["pairs"]}
    with_support = associate(c, data, support=TrainingSQLSupport(c, rows), method=method)
    assert with_support["support"]["provider"] == "training-sql-v1"
    assert c.tables[1].knowledge == []
    for r in with_support["pairs"]:
        assert r["components"]["base"] == base.get((r["table_id"], r["knowledge_id"]), 0)
    if method == "tfidf":
        assert c.tables[0].knowledge
    restored = associate(c, data, method=method)
    assert restored == plain
    assert c.model_dump() == before
    link_knowledge(c, data, rows)
    assert c.tables[0].training_examples
    link_knowledge(c, data, None)
    assert all(not t.training_examples for t in c.tables)
    assert c.association_audit["support"] == {"provider": "none"}


def test_disabled_and_missing_training_do_not_import_provider_or_read_training(monkeypatch, tmp_path):
    original_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        assert not name.endswith("training_support"), "disabled provider imported"
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    from text2query.data import catalog as module

    original_read = module.read_json

    def guarded_read(path):
        assert path != settings.train_split, "training file read while disabled"
        return original_read(path)

    monkeypatch.setattr(module, "read_json", guarded_read)
    monkeypatch.setattr(settings, "preprocessed_dir", tmp_path / "output")
    disabled = build_catalog(training_support="none", persist=True)
    import json

    assert json.loads((settings.preprocessed_dir / "training_support_audit.json").read_text()) == {"provider": "none"}
    absent = build_catalog(training_support="auto", training_source=tmp_path / "absent.json")
    assert disabled.tables == absent.tables
    assert disabled.association_audit["support"] == {"provider": "none"}
    assert not absent.association_audit["training_input"]["used"]
    with pytest.raises(FileNotFoundError, match="requires a training file"):
        build_catalog(training_support="sql", training_source=tmp_path / "absent.json")


def test_profiles_require_distinct_questions_and_do_not_learn_join_fields():
    c = sample_catalog()
    support = TrainingSQLSupport(
        c,
        [
            row("SELECT SUM(f.metric) FROM demo.fact f JOIN demo.names n ON f.id=n.id", 1, "计量指标按日期汇总"),
            row("SELECT AVG(f.metric) FROM demo.fact f JOIN demo.names n ON f.id=n.id", 2, "计量指标平均值"),
        ],
    )
    result = support.prepare(
        [{"knowledge_id": 92345, "knowledge_text": "计量指标统计"}], method="tfidf", bm25_k1=1.5, bm25_b=0.75
    )
    assert result.audit["field_profiles"]["MYSQL:demo.fact/metric"]["question_ids"] == [1, 2]
    assert not any("/id" in key for key in result.audit["field_profiles"])


def test_custom_data_directory_does_not_pick_up_another_datasets_training(tmp_path):
    data = tmp_path / "data"
    competition = data / "赛题8"
    schemas = competition / "Schema"
    schemas.mkdir(parents=True)
    (schemas / "commom_schema.txt").write_text("数据库：demo\nCREATE TABLE isolated(id INT);")
    (schemas / "core_schema.txt").write_text("")
    (competition / "knowledge.json").write_text('[{"knowledge_id":92134,"knowledge_text":"demo.isolated"}]')
    c = build_catalog(data_dir=data, training_support="auto")
    assert not c.association_audit["training_input"]["used"]
    assert c.association_audit["support"] == {"provider": "none"}
    assert [k.knowledge_id for k in c.tables[0].knowledge] == [92134]


@pytest.mark.parametrize("method", ["tfidf", "bm25"])
def test_training_provider_does_not_read_files_or_call_services(monkeypatch, method):
    import socket
    from pathlib import Path

    def forbidden(*args, **kwargs):
        raise AssertionError("unexpected I/O")

    monkeypatch.setattr(Path, "open", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    support = TrainingSQLSupport(sample_catalog(), [row("SELECT SUM(metric) FROM demo.fact")])
    result = support.prepare(
        [{"knowledge_id": 97123, "knowledge_text": "计量指标汇总"}], method=method, bm25_k1=1.5, bm25_b=0.75
    )
    assert result.signals
