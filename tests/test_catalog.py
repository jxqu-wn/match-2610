"""从当前原始 Schema 构建目录，独立于旧模型和复核产物。"""

from __future__ import annotations

from text2query.config import settings
from text2query.data.catalog import build_catalog, load_catalog
from text2query.data.review import apply_manual_review, apply_reviews
from text2query.io import read_json


def test_catalog_contains_only_current_sources(catalog):
    assert catalog.summary["tables"] == 72
    assert catalog.summary["by_engine"] == {"MYSQL": 70, "POSTGRESQL": 1, "Elasticsearch": 1}
    assert {table.engine for table in catalog.tables} == {"MYSQL", "POSTGRESQL", "Elasticsearch"}
    assert {source["file"].rsplit("/", 1)[-1] for source in catalog.sources} == {
        "commom_schema.txt", "core_schema.txt"
    }


def test_primary_foreign_keys_and_source_descriptions(catalog):
    tables = catalog.by_id()
    company = tables["MYSQL:transportation.vehicle_company"]
    driver = tables["MYSQL:transportation.driver"]
    assert company.primary_key == ["company_id"]
    assert next(c for c in company.columns if c.name == "company_id").nullable is False
    assert next(c for c in company.columns if c.name == "company_name").description
    assert any(
        fk.columns == ["company_id"]
        and fk.references.table_id == company.table_id
        and fk.references.columns == ["company_id"]
        for fk in driver.foreign_keys
    )
    for table in catalog.tables:
        assert table.raw_definition
        assert table.source.file in settings.schema_sources
        assert table.source.start_line > 0
        assert all(column.description_origin in (None, "schema_comment", "knowledge") for column in table.columns)


def test_catalog_persistence_bootstraps_clean_workspace(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "preprocessed_dir", tmp_path)
    built = build_catalog(persist=True)
    assert load_catalog().model_dump() == built.model_dump()
    assert read_json(settings.schema_extracted)["tables"] == read_json(settings.schema_catalog)["tables"]
    lines = settings.schema_documents.read_text(encoding="utf-8").splitlines()
    assert len(lines) == len(built.tables)
    assert not settings.manual_review.exists()
    assert not settings.secondary_review.exists()


def test_review_without_old_artifacts_preserves_descriptions(catalog):
    replayed = apply_reviews(catalog.model_copy(deep=True), persist=False)
    assert replayed.tables == catalog.tables
    assert "agent_corrections" not in replayed.description_summary
    assert "secondary_description_changes" not in replayed.description_summary


def test_manual_review_replay_is_idempotent(catalog):
    current = catalog.model_copy(deep=True)
    table = current.by_id()["MYSQL:transportation.vehicle_company"]
    column = next(c for c in table.columns if c.name == "company_name")
    review = {
        "reviewer": "test",
        "checks": [],
        "corrections": [{
            "table_id": table.table_id,
            "field": column.name,
            "before": column.description,
            "after": "测试用公司名称描述",
            "reason": "测试复核回放",
            "evidence": ["schema"],
        }],
    }
    apply_manual_review(current, review)
    once = current.model_dump()
    apply_manual_review(current, review)
    assert current.model_dump() == once
