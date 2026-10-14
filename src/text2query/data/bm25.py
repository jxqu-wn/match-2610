"""rank-bm25 adapter with positive IDF and an explicit score bound.

Documents are raw knowledge segments; queries are raw Schema/training facets.
The normalized score divides BM25 by sum(IDF(query term) * (k1 + 1)).
Query terms are deduplicated. Out-of-vocabulary terms contribute to the bound,
so a query with a single shared word is not treated as a complete match.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
from rank_bm25 import BM25Okapi


class _PositiveIDFBM25(BM25Okapi):
    """Keep the existing positive-IDF convention; rank-bm25 owns core scoring."""

    def _calc_idf(self, document_frequency):
        self.idf = {
            term: float(np.log1p((self.corpus_size - count + 0.5) / (count + 0.5)))
            for term, count in document_frequency.items()
        }


def bm25_similarities(
    queries: list[str],
    documents: list[str],
    tokenizer: Callable[[str], list[str]],
    *,
    k1: float = 1.5,
    b: float = 0.75,
) -> np.ndarray:
    if k1 <= 0 or not 0 <= b <= 1:
        raise ValueError("BM25 requires k1 > 0 and b in [0, 1]")
    if not queries or not documents:
        return np.zeros((len(queries), len(documents)))
    corpus = [tokenizer(document) for document in documents]
    if not any(corpus):
        return np.zeros((len(queries), len(documents)))
    model = _PositiveIDFBM25(corpus, k1=k1, b=b)
    unseen_idf = float(np.log1p((model.corpus_size + 0.5) / 0.5))
    scores = np.zeros((len(queries), len(documents)))
    for index, text in enumerate(queries):
        terms = sorted(set(tokenizer(text)))
        upper = sum(model.idf.get(term, unseen_idf) for term in terms) * (k1 + 1)
        # rank-bm25 has a 0/0 for empty documents at b=1; they have no matches.
        with np.errstate(invalid="ignore", divide="ignore"):
            scores[index] = np.nan_to_num(model.get_scores(terms), nan=0.0) / max(upper, 1e-12)
    return scores
