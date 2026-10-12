"""Schema 目录解析与复核回放。"""

from __future__ import annotations

from text2query.config import settings
from text2query.data.catalog import build_catalog, load_catalog
from text2query.data.review import apply_reviews
from text2query.io import read_json
from text2query.models import Catalog


def test_catalog_summary_matches_original_extraction():
    built = build_catalog()
    extracted = Catalog.model_validate(read_json(settings.schema_extracted))
    assert built.summary == extracted.summary
    assert built.summary["tables"] == 265
    assert built.summary["by_engine"] == {"SQLite": 193, "MYSQL": 70, "POSTGRESQL": 1, "Elasticsearch": 1}


def test_primary_foreign_keys_and_descriptions_match():
    built = build_catalog().by_id()
    extracted = Catalog.model_validate(read_json(settings.schema_extracted)).by_id()
    assert set(built) == set(extracted)
    for table_id, table in built.items():
        other = extracted[table_id]
        assert table.primary_key == other.primary_key, table_id
        assert [(fk.columns, fk.references.table_id, fk.references.columns) for fk in table.foreign_keys] == [
            (fk.columns, fk.references.table_id, fk.references.columns) for fk in other.foreign_keys
        ], table_id
        assert [(c.name, c.description, c.description_origin) for c in table.columns] == [
            (c.name, c.description, c.description_origin) for c in other.columns
        ], table_id


def test_review_replay_is_idempotent():
    catalog = load_catalog()
    expected = read_json(settings.schema_catalog)["description_summary"]
    replayed = apply_reviews(catalog.model_copy(deep=True), persist=False)
    assert replayed.description_summary == expected
