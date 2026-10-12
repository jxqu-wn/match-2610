"""数据划分：按数据源分层，使用 scikit-learn 的 ``train_test_split``。

`stratum` 规则：单源用 ``db``，跨源用有序的 ``db1 -> db2``，因此两个跨源方向
分别抽样。验证集规模与每层配额由 sklearn 的近似最大余数法分配。
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from sklearn.model_selection import train_test_split

from ..config import settings
from ..io import file_sha256, read_json, write_json
from ..models import Sample

STRATIFICATION = "db; cross-source queries use ordered db1 -> db2"


def stratum_for(sample: Sample) -> str:
    extra = sample.model_extra or {}
    if extra.get("db"):
        return str(extra["db"])
    if extra.get("db1") and extra.get("db2"):
        return f"{extra['db1']} -> {extra['db2']}"
    raise ValueError(f"样本 {sample.question_id} 缺少数据源信息")


def split_samples(
    samples: list[Sample], *, validation_ratio: float = 0.1, seed: int = 42
) -> tuple[list[Sample], list[Sample], list[int]]:
    """返回 ``(train, validation, validation_indices)``，两者均保持原始顺序。"""
    if not 0 < validation_ratio < 1:
        raise ValueError("validation_ratio 必须在 0 与 1 之间")
    ids = [s.question_id for s in samples]
    if len(set(ids)) != len(ids):
        raise ValueError("原始数据的 question_id 必须唯一")

    strata = [stratum_for(s) for s in samples]
    indices = list(range(len(samples)))
    train_idx, validation_idx = train_test_split(
        indices,
        test_size=validation_ratio,
        random_state=seed,
        shuffle=True,
        stratify=strata,
    )
    train_idx, validation_idx = sorted(train_idx), sorted(validation_idx)
    train = [samples[i] for i in train_idx]
    validation = [samples[i] for i in validation_idx]
    return train, validation, validation_idx


def _strata_stats(samples: list[Sample], validation_idx: list[int]) -> list[dict[str, object]]:
    selected = set(validation_idx)
    totals = Counter(stratum_for(s) for s in samples)
    chosen = Counter(stratum_for(samples[i]) for i in validation_idx)
    return [
        {
            "stratum": label,
            "total": totals[label],
            "train": totals[label] - chosen[label],
            "validation": chosen[label],
        }
        for label in sorted(totals)
    ]


def build_split(
    *,
    input_path: Path | None = None,
    output_dir: Path | None = None,
    validation_ratio: float = 0.1,
    seed: int = 42,
    overwrite: bool = False,
) -> dict[str, object]:
    input_path = input_path or settings.qa_train
    output_dir = output_dir or settings.path(settings.splits_dir)
    train_path = output_dir / "train.json"
    validation_path = output_dir / "validation.json"
    # 划分是竞赛基准数据；sklearn 会生成同规模同分层但不同成员的划分，
    # 因此默认拒绝覆盖已存在的冻结划分，必须显式 --overwrite。
    if not overwrite and (train_path.exists() or validation_path.exists()):
        raise FileExistsError(
            "划分文件已存在。重新划分会改变成员并影响历史实验；如确认请使用 --overwrite。"
        )
    raw = read_json(input_path)
    samples = [Sample.model_validate(row) for row in raw]
    if len(samples) < 2:
        raise ValueError("输入必须是包含至少两个样本的 JSON 数组")

    train, validation, validation_idx = split_samples(samples, validation_ratio=validation_ratio, seed=seed)
    if not train or not validation:
        raise ValueError("该比例无法生成非空的训练集和验证集")

    write_json(train_path, [s.model_dump(by_alias=True) for s in train])
    write_json(validation_path, [s.model_dump(by_alias=True) for s in validation])

    manifest = {
        "source_file": input_path.name,
        "source_sha256": file_sha256(input_path),
        "seed": seed,
        "validation_ratio": validation_ratio,
        "stratification": STRATIFICATION,
        "allocation_method": "sklearn.model_selection.train_test_split (stratified, approximate largest remainder)",
        "split_unit": "sample",
        "output_order": "original_source_order",
        "total_samples": len(samples),
        "train_samples": len(train),
        "validation_samples": len(validation),
        "strata": _strata_stats(samples, validation_idx),
        "output_sha256": {
            "train.json": file_sha256(train_path),
            "validation.json": file_sha256(validation_path),
        },
    }
    write_json(output_dir / "split_manifest.json", manifest)
    return manifest
