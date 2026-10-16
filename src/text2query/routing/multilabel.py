"""Semantic multilabel routing; one independent classifier per database system.

The caller supplies only training vectors and system labels to fit. Thresholds
are explicit deployment parameters; no reference SQL or evaluation is read here.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import precision_recall_fscore_support
from sklearn.multiclass import OneVsRestClassifier
from sklearn.preprocessing import MultiLabelBinarizer

from ..io import read_json, write_json
from .embedding import EmbeddingService


def decode_probabilities(probabilities: np.ndarray, thresholds: float | np.ndarray) -> np.ndarray:
    """Independent thresholds, with top-one fallback only for an empty route."""
    probabilities = np.asarray(probabilities, dtype=float)
    thresholds = np.asarray(thresholds, dtype=float)
    if probabilities.ndim != 2 or probabilities.shape[1] == 0:
        raise ValueError("Expected a samples-by-systems probability matrix")
    if not np.isfinite(probabilities).all() or np.any((probabilities < 0) | (probabilities > 1)):
        raise ValueError("Probabilities must be finite and within [0, 1]")
    if thresholds.ndim > 1 or (thresholds.ndim == 1 and thresholds.shape[0] != probabilities.shape[1]):
        raise ValueError("Provide one threshold or one threshold per system")
    if not np.isfinite(thresholds).all() or np.any((thresholds <= 0) | (thresholds >= 1)):
        raise ValueError("Thresholds must be finite and strictly between 0 and 1")
    result = (probabilities >= thresholds).astype(np.int64)
    empty = np.flatnonzero(result.sum(axis=1) == 0)
    result[empty, probabilities[empty].argmax(axis=1)] = 1
    return result


class SemanticMultiLabelRouter:
    """Normalized embeddings -> binary relevance logistic heads -> engine sets."""

    def __init__(
        self, embedder: EmbeddingService, *, C: float = 10.0, class_weight: str | None = None, threshold: float = 0.5
    ) -> None:
        if C <= 0 or not 0 < threshold < 1:
            raise ValueError("C must be positive and threshold must be in (0, 1)")
        self.embedder = embedder
        self.C, self.class_weight, self.threshold = C, class_weight, threshold
        self.estimator = OneVsRestClassifier(
            LogisticRegression(C=C, class_weight=class_weight, max_iter=2000, random_state=42), n_jobs=1
        )
        self.binarizer = MultiLabelBinarizer()

    def fit_vectors(self, vectors: np.ndarray, labels: list[list[str]]) -> SemanticMultiLabelRouter:
        if len(vectors) != len(labels) or not labels or any(not item for item in labels):
            raise ValueError("Provide matching nonempty training vectors and label sets")
        indicators = self.binarizer.fit_transform(labels)
        if indicators.shape[1] < 2:
            raise ValueError("Multilabel routing requires at least two observed systems")
        self.estimator.fit(vectors, indicators)
        return self

    @property
    def classes(self) -> list[str]:
        return self.binarizer.classes_.tolist()

    def predict_proba_vectors(self, vectors: np.ndarray) -> np.ndarray:
        return np.asarray(self.estimator.predict_proba(vectors))

    def predict_vectors(self, vectors: np.ndarray) -> list[str]:
        indicators = decode_probabilities(self.predict_proba_vectors(vectors), self.threshold)
        return ["|".join(values) for values in self.binarizer.inverse_transform(indicators)]

    def predict(self, questions: list[str]) -> list[str]:
        """Compatible with existing routing callers that consume pipe labels."""
        return self.predict_vectors(self.embedder.encode(questions))

    def route(self, question: str) -> dict[str, Any]:
        scores = self.predict_proba_vectors(self.embedder.encode([question]))
        chosen = decode_probabilities(scores, self.threshold)
        engines = list(self.binarizer.inverse_transform(chosen)[0])
        return {
            "question": question,
            "databases": engines,
            "query_type": "multi" if len(engines) > 1 else "single",
            "probabilities": dict(zip(self.classes, scores[0].tolist(), strict=True)),
            "threshold": self.threshold,
            "fallback_used": bool((scores[0] < self.threshold).all()),
            "method": "semantic_multilabel_logistic",
            "probability_calibration": "not calibrated",
        }

    def save(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "format_version": 1,
                "estimator": self.estimator,
                "binarizer": self.binarizer,
                "C": self.C,
                "class_weight": self.class_weight,
                "threshold": self.threshold,
            },
            directory / "classifier.joblib",
        )
        write_json(directory / "encoder_settings.json", self.embedder.signature)

    @classmethod
    def load(cls, directory: Path, embedder: EmbeddingService) -> SemanticMultiLabelRouter:
        if read_json(directory / "encoder_settings.json") != embedder.signature:
            raise ValueError("Encoder settings differ from the trained router")
        payload = joblib.load(directory / "classifier.joblib")
        if payload["format_version"] != 1:
            raise ValueError("Unsupported multilabel router format")
        router = cls(embedder, C=payload["C"], class_weight=payload["class_weight"], threshold=payload["threshold"])
        router.estimator, router.binarizer = payload["estimator"], payload["binarizer"]
        return router


def subset_metrics(actual: list[list[str]], predicted: list[list[str]]) -> dict[str, Any]:
    if len(actual) != len(predicted):
        raise ValueError("Actual and predicted routes must have equal lengths")
    pairs = [(set(a), set(p)) for a, p in zip(actual, predicted, strict=True)]
    count = len(pairs)
    exact = sum(a == p for a, p in pairs)
    covered = sum(a <= p for a, p in pairs)
    return {
        "count": count,
        "exact_match_correct": exact,
        "exact_match_accuracy": exact / count if count else None,
        "full_system_coverage_correct": covered,
        "full_system_coverage_rate": covered / count if count else None,
        "missing_system_cases": sum(bool(a - p) for a, p in pairs),
        "extra_system_cases": sum(bool(p - a) for a, p in pairs),
        "mean_predicted_systems": sum(len(p) for _, p in pairs) / count if count else None,
    }


def routing_metrics(actual: list[list[str]], predicted: list[list[str]]) -> dict[str, Any]:
    """Separate exact sets, safe coverage, multi-query detection and extra engines."""
    summary = subset_metrics(actual, predicted)
    classes = sorted({label for rows in (actual, predicted) for row in rows for label in row})
    binarizer = MultiLabelBinarizer(classes=classes)
    gold = binarizer.fit_transform(actual)
    guessed = binarizer.transform(predicted)
    precision, recall, f1, support = precision_recall_fscore_support(gold, guessed, average=None, zero_division=0)
    summary["per_system"] = {
        name: {"precision": float(p), "recall": float(r), "f1": float(f), "support": int(n)}
        for name, p, r, f, n in zip(classes, precision, recall, f1, support, strict=True)
    }
    for average in ("micro", "macro"):
        p, r, f, _ = precision_recall_fscore_support(gold, guessed, average=average, zero_division=0)
        summary[average] = {"precision": float(p), "recall": float(r), "f1": float(f)}
    for name, multi in (("cross_system", True), ("single_system", False)):
        ids = [i for i, row in enumerate(actual) if (len(set(row)) > 1) == multi]
        summary[name] = subset_metrics([actual[i] for i in ids], [predicted[i] for i in ids])
    multi_true = np.array([len(set(row)) > 1 for row in actual])
    multi_pred = np.array([len(set(row)) > 1 for row in predicted])
    p, r, f, _ = precision_recall_fscore_support(multi_true, multi_pred, average="binary", zero_division=0)
    summary["multi_query_detection"] = {
        "precision": float(p),
        "recall": float(r),
        "f1": float(f),
        "true_positive": int((multi_true & multi_pred).sum()),
        "false_positive": int((~multi_true & multi_pred).sum()),
        "false_negative": int((multi_true & ~multi_pred).sum()),
    }
    summary["by_system_combination"] = {
        key: subset_metrics(
            [actual[i] for i in range(len(actual)) if "|".join(sorted(actual[i])) == key],
            [predicted[i] for i in range(len(actual)) if "|".join(sorted(actual[i])) == key],
        )
        for key in sorted({"|".join(sorted(row)) for row in actual})
    }
    return summary
