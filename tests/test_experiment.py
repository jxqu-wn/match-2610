"""SQLite 50 题实验的解析与指标辅助函数。"""

from __future__ import annotations

from text2query.data.catalog import load_catalog
from text2query.experiments.sqlite50 import _set_metrics, expected_targets
from text2query.retrieval.sql_parser import SourceResolver


def test_set_metrics_reports_missing_extra_recall_precision():
    result = _set_metrics({"hockey.Master", "hockey.AwardsPlayers"}, {"hockey.Master"})
    assert result["exact"] is False
    assert result["recall"] == 0.5
    assert result["precision"] == 1.0
    assert result["missing"] == ["hockey.AwardsPlayers"]
    assert result["extra"] == []


def test_expected_targets_from_sqlite_reference():
    resolver = SourceResolver(load_catalog().by_id())
    row = {
        "question_id": 1,
        "question": "q",
        "db": "SQLite",
        "query": "SELECT * FROM hockey.Master m JOIN hockey.AwardsPlayers a ON m.playerID = a.playerID",
    }
    targets = expected_targets(row, resolver)
    assert targets["engines"] == ["SQLite"]
    assert targets["databases"] == ["hockey"]
    assert set(targets["tables"]) == {"hockey.Master", "hockey.AwardsPlayers"}
