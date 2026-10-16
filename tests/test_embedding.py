"""Lower precision model outputs must be unit vectors before indexing/caching."""

from __future__ import annotations

import numpy as np

from text2query.routing.embedding import EmbeddingService


def test_float32_normalization_is_persisted_and_reused(tmp_path):
    class LowerPrecisionModel:
        def encode(self, texts, **kwargs):
            # Representative BF16 rounding error observed in the real 8B run.
            return np.tile(np.array([[0.70703125, 0.70703125]], dtype=np.float32), (len(texts), 1))

    encoder = EmbeddingService(cache_dir=tmp_path, dtype="bfloat16", document_prompt="")
    encoder._model = LowerPrecisionModel()
    vectors = encoder.encode_documents(["document"])
    query = encoder.encode(["query"])
    assert vectors.dtype == query.dtype == np.float32
    np.testing.assert_allclose(np.linalg.norm(vectors, axis=1), 1, atol=1e-6)
    np.testing.assert_allclose(np.linalg.norm(query, axis=1), 1, atol=1e-6)
    assert encoder.signature["normalization_dtype"] == "float32"
    restored = EmbeddingService(cache_dir=tmp_path, dtype="bfloat16", document_prompt="")
    np.testing.assert_array_equal(restored.encode_documents(["document"]), vectors)
    np.testing.assert_array_equal(restored.encode(["query"]), query)
    assert restored._model is None
