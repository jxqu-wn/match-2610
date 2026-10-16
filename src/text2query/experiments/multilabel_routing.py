"""Frozen-split evaluation of semantic multilabel database-system routing.

Encoding uses public question text only. Model and threshold selection use
grouped out-of-fold predictions on training rows, never validation labels.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import platform
import time
from collections import Counter
from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedGroupKFold

from ..config import settings
from ..io import file_sha256, read_json, write_json, write_jsonl
from ..models import Catalog, Sample
from ..retrieval.sql_parser import SourceResolver
from ..routing.embedding import EmbeddingService
from ..routing.multilabel import SemanticMultiLabelRouter, decode_probabilities, routing_metrics, subset_metrics
from .prompt_coverage import reference_targets

DEFAULT_PARENT = Path("outputs/experiments/preprocessing-prompt-coverage-v1")
DEFAULT_OUTPUT = Path("outputs/experiments/semantic-multilabel-routing-v1")
CS = (0.1, 1.0, 10.0, 100.0)
WEIGHTS = (None, "balanced")
THRESHOLDS = (0.5, 0.4, 0.6, 0.3, 0.7)


def frozen_rows(parent: Path) -> tuple[list[dict], list[dict]]:
    hashes = read_json(parent / "artifact_sha256.json")
    names = ("shared/retrieval_train.json", "shared/splits/validation.json")
    for name in names:
        if file_sha256(parent / name) != hashes[name]:
            raise ValueError("Frozen split changed: " + name)
    train, validation = [read_json(parent / name) for name in names]
    if {r["question_id"] for r in train} & {r["question_id"] for r in validation}:
        raise ValueError("Training and validation IDs overlap")
    if {r["question"] for r in train} & {r["question"] for r in validation}:
        raise ValueError("Training and validation question texts overlap")
    return train, validation


def encode(args: argparse.Namespace) -> None:
    train, validation = frozen_rows(args.parent)
    rows = [{key: row[key] for key in ("question_id", "question")} for row in train + validation]
    args.output.mkdir(parents=True, exist_ok=True)
    encoder = EmbeddingService(
        model_path=args.model_path,
        instruction=settings.routing_instruction,
        device=args.device,
        dtype=args.dtype,
        batch_size=args.batch_size,
        max_length=args.max_length,
        cache_dir=args.output / "embedding_cache",
    )
    config = {
        "parent": str(args.parent.resolve()),
        "training_rows": len(train),
        "validation_rows": len(validation),
        "encoder": encoder.signature,
        "rows": rows,
        "frozen_sha256": {
            name: file_sha256(args.parent / name)
            for name in ("shared/retrieval_train.json", "shared/splits/validation.json", "shared/router.joblib")
        },
    }
    manifest = args.output / "encoding_manifest.json"
    if manifest.exists() and read_json(manifest) != config:
        raise ValueError("Encoding inputs changed; choose a new output directory")
    write_json(manifest, config)
    write_json(args.output / "public_questions.json", rows)
    started = time.perf_counter()
    try:
        vectors = []
        for start in range(0, len(rows), 64):
            block = rows[start : start + 64]
            vectors.append(encoder.encode([row["question"] for row in block]))
            progress = {
                "encoded": min(start + 64, len(rows)),
                "total": len(rows),
                "elapsed_seconds": time.perf_counter() - started,
            }
            write_json(args.output / "encoding_progress.json", progress)
            print(progress, flush=True)
        matrix = np.concatenate(vectors)
        np.savez_compressed(
            args.output / "vectors.npz", question_ids=np.array([r["question_id"] for r in rows]), vectors=matrix
        )
        write_json(
            args.output / "encoding_complete.json",
            {
                **progress,
                "shape": list(matrix.shape),
                "vectors_sha256": file_sha256(args.output / "vectors.npz"),
                "cached_texts": len(encoder._cache),
            },
        )
    finally:
        encoder.unload()


def grouped_folds(rows: list[dict], n_splits: int = 5) -> list[tuple[np.ndarray, np.ndarray]]:
    labels = ["|".join(Sample.model_validate(row).engines()) for row in rows]
    groups = [row["question"] for row in rows]
    splitter = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=2026)
    folds = list(splitter.split(np.zeros(len(rows)), labels, groups))
    for fit, dev in folds:
        if {groups[i] for i in fit} & {groups[i] for i in dev}:
            raise ValueError("Duplicate question text crosses an inner fold")
    return folds


def selection_quality(actual: list[list[str]], predicted: list[list[str]]) -> dict:
    groups = {}
    for name, multi in (("single", False), ("cross", True)):
        ids = [i for i, row in enumerate(actual) if (len(row) > 1) == multi]
        groups[name] = subset_metrics([actual[i] for i in ids], [predicted[i] for i in ids])
    if not groups["single"]["count"] or not groups["cross"]["count"]:
        raise ValueError("Selection requires both single-system and cross-system training examples")
    return {
        "balanced_single_cross_exact_accuracy": (
            groups["single"]["exact_match_accuracy"] + groups["cross"]["exact_match_accuracy"]
        )
        / 2,
        "overall": subset_metrics(actual, predicted),
        **groups,
    }


def selection_rank(row: dict) -> tuple[float, float, int]:
    scores = row["training_oof"]
    return (
        scores["balanced_single_cross_exact_accuracy"],
        scores["overall"]["exact_match_accuracy"],
        -scores["overall"]["extra_system_cases"],
    )


def select_models(
    vectors: np.ndarray, rows: list[dict], embedder: EmbeddingService, folds: list[tuple[np.ndarray, np.ndarray]]
) -> tuple[dict, dict]:
    """Only training features/labels enter search; validation is not an argument."""
    labels = [Sample.model_validate(row).engines() for row in rows]
    composite = np.array(["|".join(values) for values in labels])
    classes = sorted({engine for values in labels for engine in values})
    candidates, oof = {"semantic_multiclass": [], "semantic_multilabel": []}, {}
    for C in CS:
        for weight in WEIGHTS:
            scores = np.zeros((len(rows), len(classes)))
            predicted = np.empty(len(rows), dtype=object)
            for fit, dev in folds:
                router = SemanticMultiLabelRouter(embedder, C=C, class_weight=weight)
                router.fit_vectors(vectors[fit], [labels[i] for i in fit])
                if router.classes != classes:
                    raise ValueError("An inner training fold is missing a system")
                scores[dev] = router.predict_proba_vectors(vectors[dev])
                estimator = LogisticRegression(C=C, class_weight=weight, max_iter=2000, random_state=42)
                estimator.fit(vectors[fit], composite[fit])
                predicted[dev] = estimator.predict(vectors[dev])
            key = f"C={C};weight={weight}"
            oof[key] = {"probabilities": scores, "multiclass": predicted.tolist()}
            candidates["semantic_multiclass"].append(
                {
                    "C": C,
                    "class_weight": weight,
                    "cache_key": key,
                    "training_oof": selection_quality(labels, [r.split("|") for r in predicted]),
                }
            )
            for threshold in THRESHOLDS:
                indicators = decode_probabilities(scores, threshold)
                routes = [[engine for engine, keep in zip(classes, row, strict=True) if keep] for row in indicators]
                candidates["semantic_multilabel"].append(
                    {
                        "C": C,
                        "class_weight": weight,
                        "threshold": threshold,
                        "cache_key": key,
                        "training_oof": selection_quality(labels, routes),
                    }
                )
            print(
                json.dumps(
                    {
                        "selection_candidate": key,
                        "best_multilabel_training_oof": max(
                            selection_rank(row)[0] for row in candidates["semantic_multilabel"]
                        ),
                    }
                ),
                flush=True,
            )
    selection = {
        "objective": "0.5 * single-system exact accuracy + 0.5 * cross-system exact accuracy",
        "ties": "overall exact accuracy, fewer extra-system cases, then first candidate in declared grid",
        "validation_used": False,
        "folds": len(folds),
        "grouping": "exact question text",
        "seed": 2026,
        "classes": classes,
        "grid": {"C": CS, "class_weight": WEIGHTS, "threshold": THRESHOLDS},
        "candidates": candidates,
        "selected": {name: max(values, key=selection_rank) for name, values in candidates.items()},
    }
    return selection, oof


def evaluation_subsets(rows: list[dict], resolver: SourceResolver) -> tuple[dict[str, list[int]], list[dict]]:
    """Reference SQL is used only to label offline business-database subgroups."""
    targets = [reference_targets(row, resolver) for row in rows]
    subsets = {"cross_system": [], "same_system_multi_database": [], "same_system_multi_table": []}
    for i, (row, target) in enumerate(zip(rows, targets, strict=True)):
        engines = Sample.model_validate(row).engines()
        if len(engines) > 1:
            subsets["cross_system"].append(i)
            direction = " -> ".join(engine for _, engine, _ in Sample.model_validate(row).steps())
            subsets.setdefault("direction:" + direction, []).append(i)
        elif target["evaluable"]:
            if len(target["databases"]) > 1:
                subsets["same_system_multi_database"].append(i)
            if len(target["table_ids"]) > 1:
                subsets["same_system_multi_table"].append(i)
    return subsets, targets


def render_report(output: Path, summary: dict, details: list[dict]) -> None:
    lines = [
        "# 语义向量＋多标签系统路由评估",
        "",
        f"沿用冻结开发划分：有效训练{summary['training_rows']}题、验证{summary['validation_rows']}题；"
        "5折按问题文本分组，参数与阈值只在训练集OOF预测上选择。",
        f"使用本地{Path(summary['encoder']['model_path']).name}、路由专用指令、"
        f"{summary['encoder']['device']} {summary['encoder']['dtype']}向量。旧路由与原有结果未被覆盖。",
        "",
        "## 整体与跨系统表现",
        "",
        "| 方法 | 整体系统集合完全正确 | 跨系统集合完全正确 | 跨系统无漏库 | 单系统误扩为多系统 |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for name, result in summary["methods"].items():
        cross = result["cross_system"]
        lines.append(
            f"| {name} | {result['exact_match_correct']}/{result['count']} | "
            f"{cross['exact_match_correct']}/{cross['count']} | "
            f"{cross['full_system_coverage_correct']}/{cross['count']} | "
            f"{result['multi_query_detection']['false_positive']} |"
        )
    lines += [
        "",
        "## 跨系统逐题结果",
        "",
        "| ID | 参考系统 | 旧字符路由 | 语义多类 | 语义多标签 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in details:
        if len(row["expected_engines"]) > 1:
            values = [" + ".join(row["predictions"][name]["engines"]) for name in summary["methods"]]
            lines.append(
                f"| {row['question_id']} | {' + '.join(row['expected_engines'])} | " + " | ".join(values) + " |"
            )
    lines += [
        "",
        "## 多库联查口径",
        "",
        f"跨系统：参考涉及至少两个数据库系统，{summary['subgroups']['cross_system']['count']}题；"
        "同时报告完全正确与无漏库，额外选择系统不算完全正确。",
        f"同系统跨业务库：参考SQL可解析且使用多个业务库，共{summary['subgroups']['same_system_multi_database']['count']}题。"
        "这些题系统标签仍只有一个；系统路由正确不能证明具体业务库、表已召回或联查SQL正确。",
        f"同系统多表查询共{summary['subgroups']['same_system_multi_table']['count']}题，与跨业务库子集可重叠。",
        "分方向、分业务库子集和每个系统的precision/recall/F1均见summary.json。",
        "",
        "| 子集 | 旧字符路由 | 语义多类 | 语义多标签 |",
        "| --- | ---: | ---: | ---: |",
    ]
    for name, subset in summary["subgroups"].items():
        values = [
            f"{subset['methods'][method]['exact_match_correct']}/{subset['count']}" for method in summary["methods"]
        ]
        lines.append(f"| {name} | " + " | ".join(values) + " |")
    lines += [
        "",
        "方向是按参考SQL步骤分组，只评价该组的系统集合，路由模型本身不预测执行顺序。",
        "",
        "## 训练内OOF开发分数",
        "",
        "| 方法 | 训练OOF整体完全正确 | 训练OOF跨系统完全正确 |",
        "| --- | ---: | ---: |",
    ]
    for name, selected in summary["selection"]["selected"].items():
        scores = selected["training_oof"]
        lines.append(
            f"| {name} | {scores['overall']['exact_match_correct']}/{scores['overall']['count']} | "
            f"{scores['cross']['exact_match_correct']}/{scores['cross']['count']} |"
        )
    lines += [
        "",
        "这些OOF结果用于参数选择，不是额外的独立测试成绩。多标签在本次284题验证上全对，但训练内跨系统分数低于语义多类，"
        "不能据此断言多标签普遍优于语义多类；本次结果支持语义特征改善了原字符路由。",
        "",
        "## 训练内选择与边界",
        "",
        "```json",
        json.dumps(
            {
                name: {key: value for key, value in selected.items() if key not in ("training_oof", "cache_key")}
                for name, selected in summary["selection"]["selected"].items()
            },
            ensure_ascii=False,
            indent=2,
        ),
        "```",
        "",
        "选择目标为单系统与跨系统完全匹配率各占50%；C、class_weight及阈值预设网格见selection.json。"
        "阈值为各系统独立判定的共享阈值；没有系统超过阈值时仅回退到分数最高的一个。概率未做校准。",
        "验证集仅在选参冻结、全训练集拟合并保存模型后评分；这是此前使用过的开发验证集，跨系统样本较少，不能据此推算113题或680题成绩。",
        "本次仅评估系统路由，未运行LLM生成、库表重召回或数据库执行。",
        "",
        "[汇总](summary.json) · [逐题预测](validation_predictions.jsonl) · [跨系统明细](cross_system_cases.json) · "
        "[训练内选择](selection.json) · [内部分组划分](inner_folds.json) · [模型](semantic_multilabel/classifier.joblib)",
        "",
    ]
    (output / "README.md").write_text("\n".join(lines), encoding="utf-8")


def evaluate(args: argparse.Namespace) -> dict:
    output = args.output
    if (output / "selection.json").exists():
        raise FileExistsError("Selection already frozen; choose a new experiment directory")
    train, validation = frozen_rows(args.parent)
    manifest = read_json(output / "encoding_manifest.json")
    for name, digest in manifest["frozen_sha256"].items():
        if file_sha256(args.parent / name) != digest:
            raise ValueError("Frozen input changed: " + name)
    complete = read_json(output / "encoding_complete.json")
    if file_sha256(output / "vectors.npz") != complete["vectors_sha256"]:
        raise ValueError("Encoded vectors changed")
    with np.load(output / "vectors.npz", allow_pickle=False) as stored:
        vectors = stored["vectors"]
        if stored["question_ids"].tolist() != [row["question_id"] for row in train + validation]:
            raise ValueError("Encoded row order differs from the frozen split")
    if not np.isfinite(vectors).all() or not np.allclose(np.linalg.norm(vectors, axis=1), 1, atol=1e-5):
        raise ValueError("Routing vectors must be finite unit vectors")
    signature = manifest["encoder"]
    embedder = EmbeddingService(
        model_path=args.model_path,
        instruction=settings.routing_instruction,
        device=args.device,
        dtype=args.dtype,
        max_length=args.max_length,
        cache_dir=output / "embedding_cache",
    )
    if embedder.signature != signature:
        raise ValueError("Encoder files/settings differ from the encoded features")
    train_x, validation_x = vectors[: len(train)], vectors[len(train) :]
    write_json(
        output / "evaluation_plan.json",
        {
            "C": CS,
            "class_weight": WEIGHTS,
            "thresholds": THRESHOLDS,
            "folds": 5,
            "grouping": "exact question text",
            "seed": 2026,
            "objective": "0.5 * single-system exact accuracy + 0.5 * cross-system exact accuracy",
            "validation_used_for_selection": False,
            "groups_to_report": ["cross_system", "same_system_multi_database", "same_system_multi_table", "direction"],
            "code_sha256": file_sha256(Path(__file__)),
        },
    )
    folds = grouped_folds(train)
    write_json(
        output / "inner_folds.json",
        [
            {
                "fold": n + 1,
                "fit_ids": [train[i]["question_id"] for i in fit],
                "development_ids": [train[i]["question_id"] for i in dev],
            }
            for n, (fit, dev) in enumerate(folds)
        ],
    )
    started = time.perf_counter()
    selection, oof = select_models(train_x, train, embedder, folds)
    write_json(output / "selection.json", selection)
    selected = selection["selected"]
    actual_train = [Sample.model_validate(row).engines() for row in train]
    config = selected["semantic_multilabel"]
    router = SemanticMultiLabelRouter(
        embedder, C=config["C"], class_weight=config["class_weight"], threshold=config["threshold"]
    )
    router.fit_vectors(train_x, actual_train)
    router.save(output / "semantic_multilabel")
    config_multi = selected["semantic_multiclass"]
    multiclass = LogisticRegression(
        C=config_multi["C"], class_weight=config_multi["class_weight"], max_iter=2000, random_state=42
    )
    multiclass.fit(train_x, ["|".join(values) for values in actual_train])
    joblib.dump(multiclass, output / "semantic_multiclass.joblib")
    write_json(
        output / "training_oof_predictions.json",
        {
            name: {
                "training_ids": [r["question_id"] for r in train],
                "probabilities" if name == "semantic_multilabel" else "labels": oof[item["cache_key"]][
                    "probabilities"
                ].tolist()
                if name == "semantic_multilabel"
                else oof[item["cache_key"]]["multiclass"],
            }
            for name, item in selected.items()
        },
    )
    # Validation labels and reference SQL enter only after both selected models are saved.
    baseline = joblib.load(args.parent / "shared/router.joblib")
    questions = [row["question"] for row in validation]
    predictions = {
        "character_multiclass": baseline.predict(questions).tolist(),
        "semantic_multiclass": multiclass.predict(validation_x).tolist(),
        "semantic_multilabel": router.predict_vectors(validation_x),
    }
    frozen = {
        row["question_id"]: "|".join(row["predicted_engines"]) for row in read_json(args.parent / "shared/routing.json")
    }
    if predictions["character_multiclass"] != [frozen[row["question_id"]] for row in validation]:
        raise ValueError("Baseline no longer reproduces frozen routing")
    actual = [Sample.model_validate(row).engines() for row in validation]
    metrics = {
        name: routing_metrics(actual, [value.split("|") for value in values]) for name, values in predictions.items()
    }
    catalog = Catalog.model_validate(read_json(args.parent / "hybrid-0.6b/preprocessed/schema_catalog.json"))
    subsets, targets = evaluation_subsets(validation, SourceResolver(catalog.by_id()))
    subgroup_metrics = {
        name: {
            "count": len(indices),
            "question_ids": [validation[i]["question_id"] for i in indices],
            "methods": {
                method: subset_metrics([actual[i] for i in indices], [values[i].split("|") for i in indices])
                for method, values in predictions.items()
            },
        }
        for name, indices in subsets.items()
    }
    scores = router.predict_proba_vectors(validation_x)
    details = [
        {
            "question_id": row["question_id"],
            "question": row["question"],
            "expected_engines": actual[i],
            "reference_target_scope": targets[i],
            "semantic_multilabel_probabilities": dict(zip(router.classes, scores[i].tolist(), strict=True)),
            "semantic_multilabel_fallback": bool((scores[i] < router.threshold).all()),
            "predictions": {
                name: {
                    "engines": values[i].split("|"),
                    "exact": set(actual[i]) == set(values[i].split("|")),
                    "missing": sorted(set(actual[i]) - set(values[i].split("|"))),
                    "extra": sorted(set(values[i].split("|")) - set(actual[i])),
                }
                for name, values in predictions.items()
            },
        }
        for i, row in enumerate(validation)
    ]
    write_jsonl(output / "validation_predictions.jsonl", details)
    write_json(output / "cross_system_cases.json", [details[i] for i in subsets["cross_system"]])
    write_json(
        output / "errors.json", [row for row in details if not row["predictions"]["semantic_multilabel"]["exact"]]
    )
    summary = {
        "training_rows": len(train),
        "validation_rows": len(validation),
        "training_system_combinations": dict(Counter("|".join(values) for values in actual_train)),
        "encoder": signature,
        "selection": {key: value for key, value in selection.items() if key != "candidates"},
        "methods": metrics,
        "subgroups": subgroup_metrics,
        "reference_parse_failures": [
            row["question_id"] for row, target in zip(validation, targets, strict=True) if not target["evaluable"]
        ],
        "fitting_and_evaluation_seconds": time.perf_counter() - started,
        "environment": {
            name: importlib.metadata.version(name)
            for name in ("numpy", "scikit-learn", "torch", "sentence-transformers", "transformers")
        },
        "python": platform.python_version(),
        "embedding_seconds": complete["elapsed_seconds"],
        "baseline_unchanged": True,
        "execution_accuracy": None,
        "validation_limit": "previously used development validation, not a new independent holdout",
    }
    write_json(output / "summary.json", summary)
    render_report(output, summary, details)
    print(
        json.dumps(
            {
                name: {"exact": value["exact_match_accuracy"], "cross_system": value["cross_system"]}
                for name, value in metrics.items()
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("encode", "evaluate"))
    parser.add_argument("--parent", type=Path, default=DEFAULT_PARENT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--model-path", type=Path, default=Path("../models/Qwen3-Embedding-0.6B"))
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--dtype", default="float32")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--max-length", type=int, default=256)
    args = parser.parse_args()
    {"encode": encode, "evaluate": evaluate}[args.command](args)


if __name__ == "__main__":
    main()
