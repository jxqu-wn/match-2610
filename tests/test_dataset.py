"""当前数据范围、新生成划分与输入完整性契约。"""

from __future__ import annotations

from collections import Counter

import pytest

from text2query.config import settings
from text2query.io import file_sha256, read_json
from text2query.retrieval.sql_parser import engine_set


@pytest.mark.parametrize("relative, expected", [
    ("QA_train.json", 2839),
    ("QA_test.json", 200),
    ("knowledge.json", 247),
])
def test_dataset_counts_and_hashes(relative, expected):
    root = settings.path(settings.competition_dir)
    manifest = read_json(root / "dataset_manifest.json")
    entry = manifest["datasets"][relative]
    rows = read_json(root / relative)
    key = "knowledge_id" if relative == "knowledge.json" else "question_id"
    assert len(rows) == expected == entry["after"]
    assert entry["before"] - entry["removed"] == expected
    assert len(entry["removed_ids"]) == entry["removed"]
    assert file_sha256(root / relative) == entry["sha256"]
    ids = [row[key] for row in rows]
    assert len(ids) == len(set(ids))
    assert ids == sorted(ids)
    assert not set(ids).intersection(entry["removed_ids"])


def test_generated_training_and_validation_cover_filtered_source():
    source = read_json(settings.qa_train)
    train = read_json(settings.train_split)
    validation = read_json(settings.validation_split)
    assert not {r["question_id"] for r in train}.intersection(r["question_id"] for r in validation)
    assert sorted(train + validation, key=lambda row: row["question_id"]) == source
    expected = {
        ("MYSQL",): 1969,
        ("POSTGRESQL",): 410,
        ("Elasticsearch",): 370,
        ("MYSQL", "POSTGRESQL"): 90,
    }
    assert Counter(tuple(engine_set(row)) for row in source) == expected
    for row in source:
        assert set(engine_set(row)) <= {"MYSQL", "POSTGRESQL", "Elasticsearch"}
        assert row["question_id"] < 3040


def test_generated_split_manifest_matches_files():
    root = settings.path(settings.splits_dir)
    manifest = read_json(root / "split_manifest.json")
    assert manifest["source_sha256"] == file_sha256(settings.qa_train)
    for filename in ("train.json", "validation.json"):
        assert manifest["output_sha256"][filename] == file_sha256(root / filename)
    assert sum(s["total"] for s in manifest["strata"]) == manifest["total_samples"] == 2839
    assert sum(s["train"] for s in manifest["strata"]) == manifest["train_samples"] == 2555
    assert sum(s["validation"] for s in manifest["strata"]) == manifest["validation_samples"] == 284
    assert "sklearn.model_selection.train_test_split" in manifest["allocation_method"]
    assert all("SQLite" not in s["stratum"] for s in manifest["strata"])


def test_unlabelled_test_set_retains_non_sqlite_boundary_cases():
    rows = read_json(settings.qa_test)
    ids = {row["question_id"] for row in rows}
    assert {2598, 2604, 3039}.issubset(ids)
    assert all(question_id < 3040 for question_id in ids)
    assert not ids.intersection(row["question_id"] for row in read_json(settings.qa_train))
    # 测试集依旧只有问题；编号规则只用于一次性清理，不添加模型预测标签。
    assert all(set(row) == {"question_id", "question"} for row in rows)


def test_knowledge_and_schema_exclude_bird_databases(catalog):
    root = settings.path(settings.competition_dir)
    manifest = read_json(root / "dataset_manifest.json")
    removed_names = set(manifest["sqlite_databases_removed"])
    knowledge = read_json(settings.knowledge)
    assert [row["knowledge_id"] for row in knowledge] == list(range(1554, 1801))
    assert not (root / "Schema/bird_schemas.txt").exists()
    assert not removed_names.intersection(table.namespace for table in catalog.tables)
    for row in knowledge:
        assert not any("数据库" + name in row["knowledge_text"] for name in removed_names)
