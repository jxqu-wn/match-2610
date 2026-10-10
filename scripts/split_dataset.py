#!/usr/bin/env python3
"""按数据源及跨源查询方向分层划分赛题 8 数据，仅依赖 Python 标准库。"""

import argparse
import hashlib
import json
import random
from collections import defaultdict
from fractions import Fraction
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def stratum_for(sample):
    if sample.get("db"):
        return sample["db"]
    if sample.get("db1") and sample.get("db2"):
        return f'{sample["db1"]} -> {sample["db2"]}'
    raise ValueError(f'样本 {sample.get("question_id")} 缺少数据源信息')


def write_json(path, value):
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input", type=Path, default=PROJECT_ROOT / "data/赛题8/QA_train.json"
    )
    parser.add_argument(
        "--output-dir", type=Path, default=PROJECT_ROOT / "data/赛题8/splits"
    )
    parser.add_argument("--validation-ratio", type=Fraction, default=Fraction(1, 10))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if not 0 < args.validation_ratio < 1:
        parser.error("--validation-ratio 必须在 0 与 1 之间")

    source_bytes = args.input.read_bytes()
    samples = json.loads(source_bytes.decode("utf-8"))
    if not isinstance(samples, list) or len(samples) < 2:
        parser.error("输入必须是包含至少两个样本的 JSON 数组")
    ids = [sample["question_id"] for sample in samples]
    if len(set(ids)) != len(ids):
        parser.error("原始数据的 question_id 必须唯一")

    groups = defaultdict(list)
    for index, sample in enumerate(samples):
        groups[stratum_for(sample)].append(index)

    total = len(samples)
    validation_size = round(total * args.validation_ratio)
    if not 0 < validation_size < total:
        parser.error("该比例无法生成非空的训练集和验证集")

    # 最大余数法：先向下取整，再按余数分配，保证总样本数精确。
    quotas = {
        label: Fraction(len(indices) * validation_size, total)
        for label, indices in groups.items()
    }
    allocations = {
        label: quota.numerator // quota.denominator for label, quota in quotas.items()
    }
    remainder_order = sorted(
        groups, key=lambda label: (-(quotas[label] - allocations[label]), label)
    )
    for label in remainder_order[: validation_size - sum(allocations.values())]:
        allocations[label] += 1

    rng = random.Random(args.seed)
    validation_indices = set()
    for label in sorted(groups):
        candidates = list(groups[label])
        rng.shuffle(candidates)
        validation_indices.update(candidates[: allocations[label]])

    # 随机选择成员，输出仍按原始数据的顺序排列；完整保留样本字段。
    train = [sample for i, sample in enumerate(samples) if i not in validation_indices]
    validation = [sample for i, sample in enumerate(samples) if i in validation_indices]
    train_ids = {sample["question_id"] for sample in train}
    validation_ids = {sample["question_id"] for sample in validation}
    assert len(validation) == validation_size
    assert len(train) + len(validation) == total
    assert not train_ids & validation_ids
    assert train_ids | validation_ids == set(ids)

    stats = [
        {
            "stratum": label,
            "total": len(groups[label]),
            "train": len(groups[label]) - allocations[label],
            "validation": allocations[label],
        }
        for label in sorted(groups)
    ]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    train_path = args.output_dir / "train.json"
    validation_path = args.output_dir / "validation.json"
    write_json(train_path, train)
    write_json(validation_path, validation)
    manifest = {
        "source_file": args.input.name,
        "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "seed": args.seed,
        "validation_ratio": float(args.validation_ratio),
        "stratification": "db; cross-source queries use ordered db1 -> db2",
        "allocation_method": "largest_remainder",
        "split_unit": "sample",
        "output_order": "original_source_order",
        "total_samples": total,
        "train_samples": len(train),
        "validation_samples": len(validation),
        "strata": stats,
        "output_sha256": {
            "train.json": hashlib.sha256(train_path.read_bytes()).hexdigest(),
            "validation.json": hashlib.sha256(validation_path.read_bytes()).hexdigest(),
        },
    }
    write_json(args.output_dir / "split_manifest.json", manifest)
    print(f"原始 {total} 条；训练 {len(train)} 条；验证 {len(validation)} 条；seed={args.seed}")
    for item in stats:
        print(f'{item["stratum"]}: 总计 {item["total"]}, 训练 {item["train"]}, 验证 {item["validation"]}')
    print(f"输出目录：{args.output_dir}")


if __name__ == "__main__":
    main()
