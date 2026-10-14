"""测试集提交生成（test-submission）辅助函数。"""

from __future__ import annotations

from text2query.data.catalog import load_catalog
from text2query.experiments.test_submission import _expected_engines, _prompt_engines


def test_expected_engines_splits_multi_label():
    assert _expected_engines("MYSQL|POSTGRESQL") == ["MYSQL", "POSTGRESQL"]
    assert _expected_engines("Elasticsearch") == ["Elasticsearch"]
    assert _expected_engines("") == []


def test_prompt_engines_derives_from_catalog():
    tables = load_catalog().by_id()
    engines = _prompt_engines(
        ["POSTGRESQL:public.vessel_ais_data", "MYSQL:transportation.vehicle"], tables
    )
    assert engines == ["MYSQL", "POSTGRESQL"]
    assert _prompt_engines(["UNKNOWN:table"], tables) == []
