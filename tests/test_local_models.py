"""显式启用的真实本地模型集成测试；默认不加载权重或进行推理。"""

from __future__ import annotations

import os

import numpy as np
import pytest

from text2query.config import settings
from text2query.data.catalog import document_text
from text2query.retrieval.embedding import retrieval_encoder
from text2query.retrieval.index import RetrievalIndex
from text2query.retrieval.ranking import RecallConfig, RerankerService

pytestmark = [
    pytest.mark.model,
    pytest.mark.skipif(
        os.environ.get("T2Q_RUN_MODEL_TESTS") != "1",
        reason="真实模型测试需显式设置 T2Q_RUN_MODEL_TESTS=1",
    ),
]


def test_local_embedding_rrf_and_reranking(catalog, tmp_path):
    """检验本地权重、向量归一化、两路分数和精排的完整衔接。"""
    device = os.environ.get("T2Q_MODEL_TEST_DEVICE", "cpu")
    dtype = os.environ.get("T2Q_MODEL_TEST_DTYPE", "bfloat16")
    encoder = retrieval_encoder(device=device, dtype=dtype, batch_size=1, cache_dir=tmp_path)
    reranker = RerankerService(device=device, dtype=dtype, batch_size=1)
    assert encoder.model_path == settings.path(settings.embedding_model).resolve()
    assert reranker.model_path == settings.path(settings.reranker_model).resolve()
    selected = [
        catalog.by_id()["MYSQL:transportation.vessel"],
        catalog.by_id()["MYSQL:ecommerce.orders"],
    ]
    documents = [
        {
            "source_id": "schema:" + table.table_id,
            "kind": "schema",
            "engines": [table.engine],
            "table_ids": [table.table_id],
            "text": document_text(table),
            "data": table.model_dump(by_alias=True),
        }
        for table in selected
    ]
    question = "查询船舶最大载重 max_load 超过10000吨的船舶数量"
    try:
        vectors = encoder.encode_documents([document["text"] for document in documents])
        query_vector = encoder.encode([question])
        assert vectors.shape[0] == 2 and vectors.shape[1] == query_vector.shape[1]
        assert np.isfinite(vectors).all() and np.isfinite(query_vector).all()
        np.testing.assert_allclose(np.linalg.norm(vectors, axis=1), 1.0, atol=1e-5)
        # 查询向量已缓存；先释放 embedding，避免两个 8B 模型同时驻留。
        encoder.unload()
        index = RetrievalIndex(
            documents, encoder, vectors,
            recall_config=RecallConfig(bm25_top_k=2, embedding_top_k=2, rerank_top_k=2),
            reranker=reranker,
        )
        hits = index.search(question, "schema", ["MYSQL"], limit=2)
        assert len(hits) == 2
        assert hits[0]["table_ids"] == ["MYSQL:transportation.vessel"]
        assert all(hit["rerank_score"] is not None and hit["rrf_score"] > 0 for hit in hits)
        assert hits[0]["rerank_score"] >= hits[1]["rerank_score"]
        assert index.stats["embedding_cache_hits"] == 1
        assert index.stats["rerank_calls"] == 1
    finally:
        encoder.unload()
        reranker.unload()
