"""实验指标辅助函数在当前 MySQL 数据范围下的回归检查。"""

from __future__ import annotations

from text2query.data.catalog import load_catalog
from text2query.experiments.sqlite50 import _set_metrics, expected_targets
from text2query.retrieval.sql_parser import SourceResolver


def test_set_metrics_reports_missing_extra_recall_precision():
    result = _set_metrics({"transportation.vehicle", "transportation.driver"}, {"transportation.vehicle"})
    assert result["exact"] is False
    assert result["recall"] == 0.5
    assert result["precision"] == 1.0
    assert result["missing"] == ["transportation.driver"]
    assert result["extra"] == []


def test_expected_targets_from_mysql_reference():
    resolver = SourceResolver(load_catalog().by_id())
    row = {
        "question_id": 1,
        "question": "q",
        "db": "MYSQL",
        "query": "SELECT * FROM transportation.vehicle v JOIN transportation.driver d ON v.driver_id = d.driver_id",
    }
    targets = expected_targets(row, resolver)
    assert targets["engines"] == ["MYSQL"]
    assert targets["databases"] == ["transportation"]
    assert set(targets["tables"]) == {"transportation.vehicle", "transportation.driver"}
