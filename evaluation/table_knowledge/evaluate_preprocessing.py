"""Evaluate program output against a read-only reviewed reference.

Only this evaluation entry point reads the reference. The matcher never does.
"""

# ruff: noqa: E402 -- standalone script adds the local src tree before imports
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from manage import Validator, digest, read, write

from text2query.config import settings
from text2query.data.catalog import build_catalog
from text2query.data.split import build_split


def metrics(predicted, target):
    tp, fp, fn = len(predicted & target), len(predicted - target), len(target - predicted)
    precision = tp / len(predicted) if predicted else None
    recall = tp / len(target) if target else None
    return {
        "predicted": len(predicted),
        "reference": len(target),
        "true_positive": tp,
        "false_positive": fp,
        "false_negative": fn,
        "precision": precision,
        "recall": recall,
        "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None,
        "unrelated_per_effective": fp / tp if tp else None,
        "passes_200_percent_noise_target": fp <= 2 * tp,
        "zero_effective_with_noise": tp == 0 and fp > 0,
    }


def coverage(predicted, target, table_ids):
    nonempty = {tid for tid, _ in target}
    missing_tables = {tid for tid, _ in target - predicted}
    covered = set(table_ids) - missing_tables
    return {
        "all_tables": len(table_ids),
        "fully_covered_tables": len(covered),
        "all_table_full_coverage_rate": len(covered) / len(table_ids) if table_ids else None,
        "nonempty_answer_tables": len(nonempty),
        "fully_covered_nonempty_tables": len(nonempty - missing_tables),
        "nonempty_table_full_coverage_rate": len(nonempty - missing_tables) / len(nonempty) if nonempty else None,
    }


def evaluate(
    output: Path, reference: Path, *, method="tfidf", threshold=0.3, bm25_k1=1.5, bm25_b=0.75, training_support="auto"
):
    if output.exists():
        raise ValueError("output exists; choose a new run directory")
    manifest = read(reference / "manifest.json")
    for name, expected in manifest["files"].items():
        if digest(reference / name) != expected:
            raise ValueError("reference file hash mismatch: " + name)
    validator = Validator()
    validator.source_checks()
    if validator.errors:
        raise ValueError(str(validator.errors))
    if digest(validator.package / "input_context.json") != manifest["input_files"]["input_context.json"]:
        raise ValueError("reference input version mismatch")
    # Disabled mode does not load QA_train or create any training split.
    previous = settings.splits_dir
    training, training_sha, split = [], None, {}
    try:
        with TemporaryDirectory() as tmp:
            settings.splits_dir = Path(tmp) / "splits"
            if training_support != "none":
                split = build_split()
                training = read(settings.train_split)
                training_sha = digest(settings.train_split)
            catalog = build_catalog(
                persist=False,
                association_method=method,
                association_threshold=threshold,
                bm25_k1=bm25_k1,
                bm25_b=bm25_b,
                training_support=training_support,
            )
    finally:
        settings.splits_dir = previous
    # Reference is opened only after the production algorithm has finished.
    target_tables = read(reference / "tables.json")["tables"]
    if [t["table_id"] for t in target_tables] != [t.table_id for t in catalog.tables]:
        raise ValueError("reference and prediction table coverage differ")
    texts = {k["knowledge_id"]: k["knowledge_text"] for k in read(settings.knowledge)}
    target = set()
    for t in target_tables:
        for k in t["knowledge"]:
            if texts.get(k["knowledge_id"]) != k["knowledge_text"]:
                raise ValueError("reference text differs from raw knowledge")
            pair = (t["table_id"], k["knowledge_id"])
            if pair in target:
                raise ValueError("duplicate reference pair")
            target.add(pair)
    predicted = {(t.table_id, k.knowledge_id) for t in catalog.tables for k in t.knowledge}
    legacy = set()
    lookup = {(t.database, t.name): t.table_id for t in catalog.tables if t.database}
    for kid, text in texts.items():
        m = re.search(r"数据库([A-Za-z0-9_]+)的表([A-Za-z0-9_]+)", text)
        if m and (m[1], m[2]) in lookup:
            legacy.add((lookup[(m[1], m[2])], kid))
    per_table = []
    for t in catalog.tables:
        got = {k for tid, k in predicted if tid == t.table_id}
        wanted = {k for tid, k in target if tid == t.table_id}
        per_table.append(
            {
                "table_id": t.table_id,
                **metrics(got, wanted),
                "matched": sorted(got & wanted),
                "missing": sorted(wanted - got),
                "extra": sorted(got - wanted),
            }
        )
    scores = catalog.association_audit["pairs"]
    report = {
        "algorithm": catalog.association_audit["version"],
        "similarity_method": method,
        "bm25_parameters": catalog.association_audit.get("bm25_parameters"),
        "threshold": catalog.association_audit["threshold"],
        "summary": metrics(predicted, target),
        "coverage": coverage(predicted, target, [t.table_id for t in catalog.tables]),
        "legacy_primary_catalog": metrics(legacy, target),
        "per_table": per_table,
        "threshold_sweep": [
            {
                "threshold": th,
                **metrics({(r["table_id"], r["knowledge_id"]) for r in scores if r["score"] >= th}, target),
                **coverage(
                    {(r["table_id"], r["knowledge_id"]) for r in scores if r["score"] >= th},
                    target,
                    [t.table_id for t in catalog.tables],
                ),
            }
            for th in (
                0.05,
                0.075,
                0.1,
                0.125,
                0.15,
                0.175,
                0.2,
                0.225,
                0.25,
                0.275,
                0.3,
                0.325,
                0.35,
                0.4,
                0.5,
                0.6,
                0.7,
                0.8,
            )
        ],
        "training_support": training_support,
        "support_summary": {
            k: v for k, v in catalog.association_audit["support"].items() if k not in ("field_profiles", "issues")
        },
        "noise_violating_table_count": sum(not t["passes_200_percent_noise_target"] for t in per_table),
        "training_rows": len(training),
        "validation_ratio": split.get("validation_ratio", 0.1) if training_support != "none" else None,
        "training_sha256": training_sha,
        "reference_sha256": digest(reference / "tables.json"),
        "knowledge_sha256": digest(settings.knowledge),
        "schema_sources": catalog.sources,
        "algorithm_sha256": digest(ROOT / "src/text2query/data/association.py"),
        "support_implementation_sha256": digest(ROOT / "src/text2query/data/training_support.py"),
        "lexical_features_sha256": digest(ROOT / "src/text2query/data/lexical.py"),
        "bm25_implementation_sha256": digest(ROOT / "src/text2query/data/bm25.py"),
        "limitations": [
            "Thresholds were selected on this reviewed set; these are development scores, not held-out generalization.",
            "No reference labels, human decisions or LLM calls are used by the production matcher.",
            "Lexical links are program hypotheses, not a proof of content correctness.",
        ],
    }
    write(
        output / "tables.json",
        {
            "tables": [
                {"table_id": t.table_id, "knowledge": [k.model_dump() for k in t.knowledge]} for t in catalog.tables
            ]
        },
    )
    write(output / "association_audit.json", catalog.association_audit)
    write(output / "report.json", report)
    lines = [
        "# 纯程序关联评估：" + method,
        "",
        f"以LLM＋人工审核的270对关联为目标；算法只读原始Schema、知识及可选训练划分（本轮{len(training)}条）。训练增强模式：{training_support}。",
        "",
        "当前结果为同集开发评估，阈值选择参考了该基准；不代表未见数据上的成绩。",
        "",
        "| 算法 | 命中 | 多关联 | 漏关联 | Precision | Recall | F1 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]

    def fmt(value):
        return f"{value:.2%}" if value is not None else "未定义"

    for name, m in [("旧主目录规则", report["legacy_primary_catalog"]), ("纯程序新规则", report["summary"])]:
        lines.append(
            f"| {name} | {m['true_positive']} | {m['false_positive']} | {m['false_negative']} | {fmt(m['precision'])} | {fmt(m['recall'])} | {fmt(m['f1'])} |"
        )
    lines += [
        "",
        f"答案非空表完全覆盖：{report['coverage']['fully_covered_nonempty_tables']}/{report['coverage']['nonempty_answer_tables']}；全部表完全覆盖：{report['coverage']['fully_covered_tables']}/{report['coverage']['all_tables']}。",
        "",
        "## 逐表差异",
        "",
        "| 表 | 命中 | 多关联ID | 漏关联ID |",
        "| --- | --- | --- | --- |",
    ]
    for row in per_table:
        lines.append(
            f"| {row['table_id']} | {row['true_positive']} | {', '.join(map(str, row['extra'])) or '—'} | {', '.join(map(str, row['missing'])) or '—'} |"
        )
    (output / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {**report["summary"], **report["coverage"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--reference", type=Path, default=Path(__file__).resolve().parent / "runs/reference-v1")
    parser.add_argument("--method", choices=("tfidf", "bm25"), default="tfidf")
    parser.add_argument("--threshold", type=float, default=0.3)
    parser.add_argument("--bm25-k1", type=float, default=1.5)
    parser.add_argument("--bm25-b", type=float, default=0.75)
    parser.add_argument("--training-support", choices=("auto", "none", "sql"), default="auto")
    args = parser.parse_args()
    print(
        json.dumps(
            evaluate(
                args.output_dir,
                args.reference,
                method=args.method,
                threshold=args.threshold,
                bm25_k1=args.bm25_k1,
                bm25_b=args.bm25_b,
                training_support=args.training_support,
            ),
            ensure_ascii=False,
            indent=2,
        )
    )
