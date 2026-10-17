"""Namespace selection must use schema names, never question-ID exceptions."""
import importlib.util
import sys
from pathlib import Path

import pytest

from text2query.models import Table

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("namespace_probe_test", ROOT / "evaluation/prompt_quality/namespace_probe.py")
probe = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = probe
spec.loader.exec_module(probe)


@pytest.fixture(scope="session", autouse=True)
def prepared_catalog():
    yield


def table(db):
    return Table(table_id=f"MYSQL:{db}.t", name="t", database=db, engine="MYSQL")


def test_explicit_two_years_expand_only_matching_existing_namespace_family():
    rows = [table(db) for db in ["school_2024", "school_2025", "other_2025", "transportation"]]
    catalog = {t.table_id: t for t in rows}
    selected = [{"table_id": rows[0].table_id}]
    assert probe.mentioned_namespaces("比较2024与2025的数据", selected, catalog) == ["school_2024", "school_2025"]


def test_single_year_or_unrelated_domain_does_not_introduce_annual_database():
    rows = [table(db) for db in ["school_2024", "school_2025", "transportation"]]
    catalog = {t.table_id: t for t in rows}
    assert probe.mentioned_namespaces("查询2024年车辆", [{"table_id": rows[2].table_id}], catalog) == []
    assert probe.mentioned_namespaces("比较2024和2025车辆", [{"table_id": rows[2].table_id}], catalog) == []
    assert probe.mentioned_namespaces("查询2024年学生", [{"table_id": rows[0].table_id}], catalog) == []
