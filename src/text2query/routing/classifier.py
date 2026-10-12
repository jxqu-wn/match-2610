"""数据库系统路由：Qwen 语义向量 + scikit-learn 分类器。

- 近邻：``KNeighborsClassifier``，余弦距离，权重 ``max(1-distance, 0)**3``；
- 逻辑回归：``LogisticRegression``；超参在训练集内部开发集上选择；
- 字符 TF-IDF + 逻辑回归作为可复现的纯 CPU 对照基线。
验证标签只用于报告，不参与拟合或选参。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import StratifiedShuffleSplit
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline

from ..config import settings
from ..io import get_logger, read_json, write_json
from ..models import Sample
from .embedding import EmbeddingService

logger = get_logger(__name__)


def label(sample: Sample) -> str:
    """多类标签：涉及的数据库系统集合，按名称排序去重。"""
    return "|".join(sample.engines())


def load_split(name: str) -> list[Sample]:
    path = settings.path(settings.splits_dir) / f"{name}.json"
    return [Sample.model_validate(row) for row in read_json(path)]


def _neighbor_weight(distances: np.ndarray) -> np.ndarray:
    # 余弦距离 -> 相似度；保持与原实现一致的相似度三次方加权。
    return np.maximum(1.0 - distances, 0.0) ** 3


def build_estimator(method: str) -> Any:
    if method.startswith("knn"):
        return KNeighborsClassifier(n_neighbors=int(method[3:]), metric="cosine", weights=_neighbor_weight)
    if method.startswith("logistic_C"):
        return LogisticRegression(C=float(method.split("_C")[1]), max_iter=2000, random_state=42)
    raise ValueError(f"未知方法：{method}")


class CharacterTfidfBaseline:
    """字符 1~3 元组 TF-IDF + 逻辑回归，纯 CPU 对照。"""

    def __init__(self) -> None:
        self.pipeline = Pipeline(
            [
                ("tfidf", TfidfVectorizer(analyzer="char", ngram_range=(1, 3), min_df=1)),
                ("clf", LogisticRegression(max_iter=2000, random_state=42)),
            ]
        )

    def fit(self, questions: list[str], labels: list[str]) -> "CharacterTfidfBaseline":
        self.pipeline.fit(questions, labels)
        return self

    def predict(self, questions: list[str]) -> list[str]:
        return list(self.pipeline.predict(questions))


def internal_split(rows: list[Sample], *, test_size: float = 0.1, seed: int = 2026) -> tuple[list[int], list[int]]:
    """按标签分层，在训练集内部切出开发集，用于选择近邻/逻辑回归。"""
    labels = [label(row) for row in rows]
    splitter = StratifiedShuffleSplit(n_splits=1, test_size=test_size, random_state=seed)
    fit_idx, dev_idx = next(splitter.split(np.zeros(len(rows)), labels))
    dev_texts = {rows[i].question for i in dev_idx}
    fit_idx = [i for i in fit_idx if rows[i].question not in dev_texts]
    return sorted(fit_idx), sorted(dev_idx)


def metrics(rows: list[Sample], predictions: list[str]) -> dict[str, Any]:
    actual = np.array([label(r) for r in rows])
    predicted = np.array(predictions)
    by_database = {
        category: {
            "count": int((actual == category).sum()),
            "accuracy": float((predicted[actual == category] == category).mean()),
        }
        for category in sorted(set(actual))
    }
    return {
        "count": len(rows),
        "correct": int((actual == predicted).sum()),
        "database_set_accuracy": float(accuracy_score(actual, predicted)),
        "single_multi_accuracy": float(np.mean([("|" in a) == ("|" in p) for a, p in zip(actual, predicted)])),
        "by_database": by_database,
    }


class RoutingClassifier:
    def __init__(self, embedder: EmbeddingService, estimator: Any, method: str) -> None:
        self.embedder = embedder
        self.estimator = estimator
        self.method = method

    def predict_vectors(self, vectors: np.ndarray) -> list[str]:
        return [str(value) for value in self.estimator.predict(vectors)]

    def predict(self, questions: list[str]) -> list[str]:
        return self.predict_vectors(self.embedder.encode(questions))

    def save(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {"estimator": self.estimator, "method": self.method},
            directory / "classifier.joblib",
        )
        write_json(directory / "encoder_settings.json", self.embedder.signature)

    @classmethod
    def load(cls, directory: Path, embedder: EmbeddingService) -> "RoutingClassifier":
        payload = joblib.load(directory / "classifier.joblib")
        return cls(embedder, payload["estimator"], payload["method"])


def _select_method(
    fit_x: np.ndarray, fit_y: list[str], dev_x: np.ndarray, dev_y: list[str]
) -> tuple[str, dict[str, float]]:
    candidates: dict[str, float] = {}
    for name in ("knn1", "knn3", "knn5", "logistic_C0.1", "logistic_C1.0", "logistic_C10.0", "logistic_C100.0"):
        estimator = build_estimator(name)
        estimator.fit(fit_x, fit_y)
        candidates[name] = float(accuracy_score(dev_y, estimator.predict(dev_x)))
    selected = max(candidates, key=lambda key: candidates[key])
    return selected, candidates


def evaluate(*, output: Path | None = None, limit: int | None = None, **embedding_kwargs: Any) -> dict[str, Any]:
    output = output or settings.path("outputs/database_routing/embedding")
    output.mkdir(parents=True, exist_ok=True)
    train, validation = load_split("train"), load_split("validation")
    validation_texts = {row.question for row in validation}
    train = [row for row in train if row.question not in validation_texts]

    embedder = EmbeddingService(instruction=settings.routing_instruction, **embedding_kwargs)
    fit_idx, dev_idx = internal_split(train)
    all_rows = train + validation
    vectors = embedder.encode([row.question for row in all_rows])
    train_x, validation_x = vectors[: len(train)], vectors[len(train) :]
    train_y = [label(row) for row in train]

    selected, candidates = _select_method(
        train_x[fit_idx], [train_y[i] for i in fit_idx], train_x[dev_idx], [train_y[i] for i in dev_idx]
    )
    estimator = build_estimator(selected)
    estimator.fit(train_x, train_y)
    classifier = RoutingClassifier(embedder, estimator, selected)
    classifier.save(output)

    prediction = classifier.predict_vectors(validation_x)
    baseline = CharacterTfidfBaseline().fit([r.question for r in train], train_y)
    baseline_prediction = baseline.predict([row.question for row in validation])

    details = [
        {
            "question_id": row.question_id,
            "question": row.question,
            "expected": label(row),
            "predicted": predicted,
            "character_predicted": character,
            "correct": predicted == label(row),
        }
        for row, predicted, character in zip(validation, prediction, baseline_prediction)
    ]
    summary = {
        "model": str(embedder.model_path),
        "encoder_settings": embedder.signature,
        "training_size": len(train),
        "internal_fit_size": len(fit_idx),
        "internal_dev_size": len(dev_idx),
        "dev_candidates": candidates,
        "selected_method": selected,
        "embedding": metrics(validation, prediction),
        "character_tfidf_logistic": metrics(validation, baseline_prediction),
        "scope": "仅数据库系统集合；训练集排除与验证集完全同文本的问题。",
    }
    write_json(output / "summary.json", summary)
    write_json(output / "predictions.json", details)
    write_json(output / "errors.json", [row for row in details if not row["correct"]])
    write_json(
        output / "split_ids.json",
        {"fit": [train[i].question_id for i in fit_idx], "dev": [train[i].question_id for i in dev_idx]},
    )
    return summary


def predict(question: str, *, output: Path | None = None, **embedding_kwargs: Any) -> dict[str, Any]:
    output = output or settings.path("outputs/database_routing/embedding")
    embedder = EmbeddingService(instruction=settings.routing_instruction, **embedding_kwargs)
    if not (output / "summary.json").exists():
        raise FileNotFoundError("请先运行 evaluate 生成分类器")
    summary = read_json(output / "summary.json")
    if summary["encoder_settings"] != embedder.signature:
        raise ValueError("模型设置与评估时不同，请使用相同参数或重新评估")
    classifier = RoutingClassifier.load(output, embedder)
    prediction = classifier.predict([question])[0]
    return {
        "question": question,
        "databases": prediction.split("|"),
        "query_type": "multi" if "|" in prediction else "single",
        "method": classifier.method,
    }


def cross_validate(*, output: Path | None = None, folds: int = 5, **embedding_kwargs: Any) -> dict[str, Any]:
    """字符 TF-IDF + 逻辑回归的五折交叉验证（排除同文本以降低模板泄漏）。"""
    from sklearn.model_selection import StratifiedKFold

    output = output or settings.path("outputs/database_routing/linear")
    output.mkdir(parents=True, exist_ok=True)
    train = load_split("train")
    labels = [label(row) for row in train]
    questions = np.array([row.question for row in train])
    splitter = StratifiedKFold(n_splits=folds, shuffle=True, random_state=42)
    details: list[dict[str, Any]] = []
    for fold, (fit_idx, test_idx) in enumerate(splitter.split(questions, labels)):
        dev_texts = set(questions[test_idx])
        keep = [i for i in fit_idx if questions[i] not in dev_texts]
        model = CharacterTfidfBaseline().fit([train[i].question for i in keep], [labels[i] for i in keep])
        predicted = model.predict([train[i].question for i in test_idx])
        for index, value in zip(test_idx, predicted):
            details.append(
                {
                    "question_id": train[index].question_id,
                    "expected": labels[index],
                    "predicted": value,
                    "correct": value == labels[index],
                    "fold": fold,
                }
            )
    report = {
        "count": len(details),
        "correct": sum(row["correct"] for row in details),
        "accuracy": float(np.mean([row["correct"] for row in details])),
        "folds": folds,
        "scope": "字符 TF-IDF + 逻辑回归；每折排除与测试文本相同的训练问题。",
    }
    write_json(output / "cross_validation_summary.json", report)
    write_json(output / "cross_validation_predictions.json", details)
    return report
