"""数据划分：与已提交划分的规模、分层一致。"""

from __future__ import annotations

from text2query.config import settings
from text2query.data.split import build_split, split_samples, stratum_for
from text2query.io import read_json
from text2query.models import Sample


def test_split_sizes_and_strata_match_manifest(tmp_path):
    manifest = build_split(
        input_path=settings.qa_train,
        output_dir=tmp_path,
        validation_ratio=0.1,
        seed=42,
    )
    committed = read_json(settings.path(settings.splits_dir) / "split_manifest.json")
    assert manifest["total_samples"] == committed["total_samples"] == 5830
    assert manifest["train_samples"] == committed["train_samples"] == 5247
    assert manifest["validation_samples"] == committed["validation_samples"] == 583
    assert manifest["strata"] == committed["strata"]


def test_split_is_disjoint_and_order_preserving():
    samples = [Sample.model_validate(row) for row in read_json(settings.qa_train)]
    train, validation, _ = split_samples(samples, validation_ratio=0.1, seed=42)
    assert len(train) + len(validation) == len(samples)
    assert not {s.question_id for s in train} & {s.question_id for s in validation}
    assert [s.question_id for s in validation] == sorted(s.question_id for s in validation)


def test_stratum_uses_ordered_cross_source():
    assert stratum_for(Sample.model_validate({"question_id": 1, "question": "q", "db": "MYSQL"})) == "MYSQL"
    cross = Sample.model_validate(
        {"question_id": 2, "question": "q", "db1": "MYSQL", "query1": "a", "db2": "POSTGRESQL", "query2": "b"}
    )
    assert stratum_for(cross) == "MYSQL -> POSTGRESQL"
    assert cross.engines() == ["MYSQL", "POSTGRESQL"]
