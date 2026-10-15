"""库表/知识/案例混合召回索引。

- 关键词：``rank_bm25``（中文按 1~3 字 n-gram，英文按下划线标识符切分）；
- 语义：``faiss`` 内积索引（不可用时退回 numpy 精确计算）；
- 融合：倒数排名融合（RRF）。
- 精排：本地 CrossEncoder，对 RRF 候选联合编码问题与文档。

索引版本与来源文件 SHA256、编码器签名绑定；资料变化必须重建，避免旧向量
搭配新结构。
"""

from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import numpy as np
from rank_bm25 import BM25Okapi

from ..config import settings
from ..data.association import ASSOCIATION_VERSION, literal_references
from ..io import file_sha256, get_logger, read_json, write_json, write_jsonl
from ..models import Catalog, Sample, Table
from .ranking import RecallConfig, RerankerService
from .sql_parser import SourceResolver, engine_set

logger = get_logger(__name__)

INDEX_VERSION = 4


# --------------------------------------------------------------------------- #
# 文本处理
# --------------------------------------------------------------------------- #


def terms(text: str) -> Counter[str]:
    """英文标识符 + 中文 1~3 字 n-gram，与旧实现保持一致。"""
    text = text.lower()
    result: list[str] = re.findall(r"[a-z_][a-z_0-9]*|[0-9]+", text)
    for segment in re.findall(r"[\u3400-\u9fff]+", text):
        result.extend(segment[i : i + n] for n in (1, 2, 3) for i in range(len(segment) - n + 1))
    return Counter(result)


def tokenize(text: str) -> list[str]:
    return list(terms(text).elements())


# --------------------------------------------------------------------------- #
# 文档构建
# --------------------------------------------------------------------------- #


def build_documents(
    catalog: Catalog, knowledge: list[dict[str, Any]], train_rows: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    from ..data.catalog import document_text

    tables = catalog.by_id()
    resolver = SourceResolver(tables)
    documents: list[dict[str, Any]] = []

    for table in catalog.tables:
        documents.append(
            {
                "source_id": "schema:" + table.table_id,
                "kind": "schema",
                "engines": [table.engine],
                "table_ids": [table.table_id],
                "text": document_text(table),
                "data": table.model_dump(by_alias=True),
            }
        )

    unmatched_knowledge: list[int] = []
    for item in knowledge:
        text = item["knowledge_text"]
        related = {
            table.table_id
            for table in catalog.tables
            if any(k.knowledge_id == item["knowledge_id"] for k in table.knowledge)
        }
        if not related:
            unmatched_knowledge.append(item["knowledge_id"])
        documents.append(
            {
                "source_id": f"knowledge:{item['knowledge_id']}",
                "kind": "knowledge",
                "engines": sorted({tables[key].engine for key in related}),
                "table_ids": sorted(related),
                "text": text,
                "data": item,
                "association": (catalog.model_extra or {})
                .get("association_audit", {})
                .get("version", ASSOCIATION_VERSION)
                if related
                else "unscoped",
            }
        )

    parse_issues: list[dict[str, Any]] = []
    for row in train_rows:
        sample = Sample.model_validate(row)
        steps: list[dict[str, Any]] = []
        for index, engine, query in sample.steps():
            try:
                parsed = resolver.parse(query, engine)
            except (ValueError, KeyError) as error:
                parsed = {"table_ids": [], "joins": [], "parse_status": "parse_error", "parse_error": str(error)[:200]}
            step_name = "query" if index == 0 else f"query{index}"
            steps.append({"engine": engine, "query": query, "step": step_name, **parsed})
            if parsed["parse_status"] not in ("parsed", "single_index_by_catalog"):
                parse_issues.append({"question_id": row["question_id"], "step": step_name, **parsed})
        related = sorted({key for step in steps for key in step["table_ids"]})
        documents.append(
            {
                "source_id": f"example:{row['question_id']}",
                "kind": "example",
                "engines": engine_set(row),
                "table_ids": related,
                "text": row["question"],
                "data": {
                    "question_id": row["question_id"],
                    "question": row["question"],
                    "steps": steps,
                    "label_quality": "training_annotation_unverified",
                },
            }
        )

    ids = [d["source_id"] for d in documents]
    if len(ids) != len(set(ids)):
        raise ValueError("source_id 不唯一")
    audit = {
        "document_counts": dict(Counter(d["kind"] for d in documents)),
        "example_parse_issues": parse_issues,
        "unscoped_knowledge_ids": unmatched_knowledge,
    }
    return documents, audit


# --------------------------------------------------------------------------- #
# 索引
# --------------------------------------------------------------------------- #


class RetrievalIndex:
    def __init__(
        self,
        documents: list[dict[str, Any]],
        encoder: Any = None,
        vectors: np.ndarray | None = None,
        *,
        recall_config: RecallConfig | None = None,
        reranker: Any = None,
    ) -> None:
        self.documents = documents
        self.by_id = {d["source_id"]: d for d in documents}
        self.tables: dict[str, Table] = {
            d["table_ids"][0]: Table.model_validate(d["data"]) for d in documents if d["kind"] == "schema"
        }
        self.encoder = encoder
        self.vectors = vectors
        if encoder is not None and vectors is None:
            raise ValueError("混合检索缺少文档向量，请先用 embedding 模型构建索引")
        self.recall_config = recall_config or RecallConfig.from_settings()
        self.reranker = reranker
        if self.reranker is None and encoder is not None and self.recall_config.rerank_enabled:
            self.reranker = RerankerService()
        self.positions = {d["source_id"]: i for i, d in enumerate(documents)}
        self.stats = {
            "semantic_queries": 0, "embedding_cache_hits": 0, "lexical_searches": 0,
            "rerank_calls": 0, "reranked_documents": 0,
        }
        tokenized = [tokenize(d["text"]) for d in documents]
        self._tokenized = tokenized
        self._bm25 = BM25Okapi(tokenized) if any(tokenized) else None
        self._faiss = self._build_faiss(vectors) if vectors is not None else None
        # The catalog is the sole authority for associations. Literal evidence is
        # descriptive only and never adds a second set of links here.
        self.knowledge_links = {
            d["source_id"]: {
                key: [{"kind": "catalog_association", "version": d.get("association")}] for key in d["table_ids"]
            }
            for d in documents
            if d["kind"] == "knowledge"
        }
        self.explicit_knowledge_links = {
            d["source_id"]: {
                key: evidence
                for key, evidence in literal_references(d["text"], self.tables).items()
                if key in d["table_ids"]
            }
            for d in documents
            if d["kind"] == "knowledge"
        }

    @property
    def recall_metadata(self) -> dict[str, Any]:
        return {
            "strategy": "bm25_embedding_rrf" if self.encoder is not None else "bm25",
            **self.recall_config.as_dict(),
            "rerank_enabled": self.reranker is not None and self.recall_config.rerank_enabled,
            "reranker": self.reranker.signature if self.reranker is not None else None,
        }

    # -- FAISS ------------------------------------------------------------ #
    @staticmethod
    def _build_faiss(vectors: np.ndarray) -> Any:
        try:
            import faiss
        except ImportError:  # pragma: no cover - faiss 为推荐依赖
            logger.warning("未安装 faiss，语义检索退回 numpy 精确计算")
            return None
        index = faiss.IndexFlatIP(vectors.shape[1])
        index.add(np.ascontiguousarray(vectors, dtype=np.float32))
        return index

    def _semantic_scores(self, query_vector: np.ndarray, candidates: list[int]) -> dict[int, float]:
        """在候选集合内计算余弦相似度（向量已归一化，内积即余弦）。"""
        if self.vectors is None:
            return {}
        if self._faiss is not None:
            try:
                import faiss

                selector = faiss.IDSelectorBatch(np.asarray(candidates, dtype="int64"))
                params = faiss.SearchParameters()
                params.sel = selector
                scores, ids = self._faiss.search(
                    np.ascontiguousarray(query_vector[None, :], dtype=np.float32), len(candidates), params=params
                )
                return {int(i): float(s) for i, s in zip(ids[0], scores[0], strict=True) if i >= 0}
            except Exception:  # noqa: BLE001 - 退回精确计算
                pass
        subset = self.vectors[candidates]
        return {index: float(value) for index, value in zip(candidates, subset @ query_vector, strict=True)}

    # -- 构建/加载 -------------------------------------------------------- #
    @staticmethod
    def _fingerprints(training_source: Path) -> dict[str, str]:
        return {
            "catalog": file_sha256(settings.schema_catalog),
            "knowledge": file_sha256(settings.knowledge),
            "training": file_sha256(training_source),
        }

    @classmethod
    def build(
        cls,
        path: Path | None = None,
        encoder: Any = None,
        *,
        training_source: Path | None = None,
        catalog: Catalog | None = None,
        knowledge: list[dict[str, Any]] | None = None,
        train_rows: list[dict[str, Any]] | None = None,
        recall_config: RecallConfig | None = None,
        reranker: Any = None,
    ) -> RetrievalIndex:
        from ..data.catalog import load_catalog

        path = path or settings.path("outputs/information_retrieval/index")
        training_source = training_source or settings.train_split
        catalog = catalog or load_catalog()
        knowledge = knowledge if knowledge is not None else read_json(settings.knowledge)
        train_rows = train_rows if train_rows is not None else read_json(training_source)
        documents, audit = build_documents(catalog, knowledge, train_rows)

        path.mkdir(parents=True, exist_ok=True)
        write_jsonl(path / "documents.jsonl", documents)
        vectors = encoder.encode_documents([d["text"] for d in documents]) if encoder else None
        built = cls(documents, encoder, vectors, recall_config=recall_config, reranker=reranker)
        artifacts = ["documents.jsonl"]
        if vectors is not None:
            np.savez_compressed(
                path / "vectors.npz",
                source_ids=np.array([d["source_id"] for d in documents]),
                vectors=vectors,
            )
            artifacts.append("vectors.npz")
            audit["semantic_truncation"] = {
                "max_length": encoder.max_length,
                "note": "向量输入按 max_length 截断；完整文本仍在关键词索引与上下文中。",
            }
        write_json(path / "audit.json", audit)
        write_json(
            path / "manifest.json",
            {
                "version": INDEX_VERSION,
                "sources": cls._fingerprints(training_source),
                "encoder": encoder.signature if encoder else None,
                "recall_defaults": built.recall_metadata,
                "documents": len(documents),
                "audit": audit["document_counts"],
                "artifacts": {name: file_sha256(path / name) for name in artifacts},
            },
        )
        return built

    @classmethod
    def load(
        cls,
        path: Path | None = None,
        encoder: Any = None,
        *,
        training_source: Path | None = None,
        recall_config: RecallConfig | None = None,
        reranker: Any = None,
    ) -> RetrievalIndex:
        path = path or settings.path("outputs/information_retrieval/index")
        training_source = training_source or settings.train_split
        manifest = read_json(path / "manifest.json")
        if manifest["version"] != INDEX_VERSION:
            raise ValueError("索引版本不匹配，请重新 build-index")
        if manifest["sources"] != cls._fingerprints(training_source):
            raise ValueError("索引来源已变化，请重新 build-index")
        if manifest["encoder"] != (encoder.signature if encoder else None):
            raise ValueError("索引编码器设置已变化，请使用匹配设置或重建")
        for name, digest in manifest.get("artifacts", {}).items():
            if file_sha256(path / name) != digest:
                raise ValueError("索引文件完整性校验失败：" + name)
        documents = [
            json.loads(line) for line in (path / "documents.jsonl").read_text(encoding="utf-8").splitlines() if line
        ]
        if len(documents) != manifest["documents"]:
            raise ValueError("索引文档数不匹配")
        vectors = None
        if encoder:
            with np.load(path / "vectors.npz", allow_pickle=False) as stored:
                if stored["source_ids"].tolist() != [d["source_id"] for d in documents]:
                    raise ValueError("向量与来源未对齐")
                vectors = stored["vectors"]
        return cls(documents, encoder, vectors, recall_config=recall_config, reranker=reranker)

    # -- 检索 ------------------------------------------------------------- #
    def search(
        self,
        query: str,
        kind: str,
        engines: Iterable[str],
        limit: int = 8,
        *,
        table_ids: Iterable[str] | None = None,
        exclude: Iterable[str] = (),
        exact_engines: bool = False,
        scope_table_ids: Iterable[str] | None = None,
        explicit_only: bool = False,
        associated_only: bool = False,
        source_ids: Iterable[str] | None = None,
        rerank: bool = True,
    ) -> list[dict[str, Any]]:
        if limit <= 0:
            return []
        self.stats["lexical_searches"] += 1
        selected = set(engines)
        scope = set(scope_table_ids) if scope_table_ids is not None else None
        excluded = set(exclude)
        table_filter = set(table_ids) if table_ids is not None else None
        source_filter = set(source_ids) if source_ids is not None else None

        def associated(document: dict[str, Any]) -> list[str]:
            if associated_only:
                return list(self.knowledge_links.get(document["source_id"], {}))
            if explicit_only:
                return list(self.explicit_knowledge_links.get(document["source_id"], {}))
            return document["table_ids"]

        def doc_engines(document: dict[str, Any]) -> set[str]:
            if explicit_only or associated_only:
                return {self.tables[key].engine for key in associated(document)}
            return set(document["engines"])

        candidates = [
            i
            for i, document in enumerate(self.documents)
            if document["kind"] == kind
            and (doc_engines(document) == selected if exact_engines else doc_engines(document) <= selected)
            and bool(doc_engines(document))
            and document["source_id"] not in excluded
            and (source_filter is None or document["source_id"] in source_filter)
            and (table_filter is None or bool(set(associated(document)) & table_filter))
            and (scope is None or (bool(associated(document)) and set(associated(document)) <= scope))
        ]
        if not candidates:
            return []

        lexical = self._lexical_scores(query, candidates)
        lexical_order = sorted(
            (i for i in candidates if lexical.get(i, 0) > 0),
            key=lambda i: (-lexical[i], self.documents[i]["source_id"]),
        )[: self.recall_config.bm25_top_k]
        keyword_rank = {index: rank + 1 for rank, index in enumerate(lexical_order)}

        semantic: dict[int, float] = {}
        semantic_rank: dict[int, int] = {}
        if self.encoder is not None:
            self.stats["semantic_queries"] += 1
            self.stats["embedding_cache_hits"] += int(query in self.encoder._cache)
            vector = self.encoder.encode([query])[0]
            semantic = self._semantic_scores(vector, candidates)
            semantic_rank = {
                index: rank + 1
                for rank, index in enumerate(
                    sorted(candidates, key=lambda i: (-semantic.get(i, 0.0), self.documents[i]["source_id"]))[
                        : self.recall_config.embedding_top_k
                    ]
                )
            }

        fused = {
            i: sum(1 / (self.recall_config.rrf_k + ranks[i]) for ranks in (keyword_rank, semantic_rank) if i in ranks)
            for i in keyword_rank.keys() | semantic_rank.keys()
        }
        ordered = sorted(
            fused, key=lambda i: (-fused[i], self.documents[i]["source_id"])
        )
        query_terms = set(terms(query))
        hits = [
            {
                "source_id": self.documents[i]["source_id"],
                "table_ids": self.documents[i]["table_ids"],
                "score": fused[i],
                "rrf_score": fused[i],
                "rrf_rank": rank,
                "candidate_score": fused[i],
                "rerank_score": None,
                "ranking_method": "rrf" if self.encoder is not None else "bm25",
                "semantic_rank": semantic_rank.get(i),
                "semantic_similarity": semantic.get(i),
                "keyword_rank": keyword_rank.get(i),
                "keyword_score": lexical.get(i, 0.0),
                "keyword_hits": sorted(query_terms & set(self._tokenized[i]), key=lambda t: (-len(t), t))[:12],
            }
            for rank, i in enumerate(ordered, 1)
        ]
        return self.rank_hits(query, hits, limit) if rerank else hits[:limit]

    def rank_hits(self, query: str, hits: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
        """合并候选后统一精排；原始检索分数独立保存，不与模型 logits 相加。"""
        if limit <= 0:
            return []
        unique: dict[str, dict[str, Any]] = {}
        for hit in hits:
            source_id = hit["source_id"]
            if source_id not in self.by_id:
                raise ValueError("精排候选不在当前索引中：" + source_id)
            previous = unique.get(source_id)
            if previous is None or hit.get("candidate_score", hit.get("score", 0)) > previous.get(
                "candidate_score", previous.get("score", 0)
            ):
                unique[source_id] = dict(hit)
        ordered = sorted(
            unique.values(),
            key=lambda hit: (-hit.get("candidate_score", hit.get("score", 0)), hit["source_id"]),
        )
        if self.reranker is None or not self.recall_config.rerank_enabled:
            return ordered[:limit]
        pool = ordered[: max(limit, self.recall_config.rerank_top_k)]
        if not pool:
            return []
        scores = self.reranker.score(query, [self.by_id[hit["source_id"]]["text"] for hit in pool])
        if len(scores) != len(pool) or not np.isfinite(scores).all():
            raise ValueError("重排模型分数数量或数值非法")
        self.stats["rerank_calls"] += 1
        self.stats["reranked_documents"] += len(pool)
        for candidate_rank, (hit, score) in enumerate(zip(pool, scores, strict=True), 1):
            hit.update(
                candidate_rank=candidate_rank,
                rerank_score=float(score),
                score=float(score),
                ranking_method="rrf_cross_encoder",
            )
        pool.sort(key=lambda hit: (-hit["rerank_score"], -hit.get("candidate_score", 0), hit["source_id"]))
        for rank, hit in enumerate(pool, 1):
            hit["rerank_rank"] = rank
        return pool[:limit]

    def _lexical_scores(self, query: str, candidates: list[int]) -> dict[int, float]:
        if self._bm25 is None:
            return {}
        scores = self._bm25.get_scores(tokenize(query))
        return {i: float(scores[i]) for i in candidates if scores[i] > 0}

    def search_tables(
        self,
        query: str,
        engines: Iterable[str],
        limit: int = 8,
        *,
        exclude: Iterable[str] = (),
        knowledge_limit: int = 12,
    ) -> list[dict[str, Any]]:
        engines = list(engines)
        if limit <= 0:
            return []
        pool_size = max(limit, self.recall_config.rerank_top_k)
        base = self.search(query, "schema", engines, pool_size, exclude=exclude, rerank=False)

        # 使用目录已确定的关联；不在检索阶段重建或补齐关联。
        explicit_docs = [
            d for d in self.documents if d["kind"] == "knowledge" and self.knowledge_links.get(d["source_id"])
        ]
        query_terms = {t for t in terms(query) if len(t) >= 2 and not t.isdigit()}
        counts = Counter(t for d in explicit_docs for t in set(terms(d["text"])))
        anchors = {t for t in query_terms if counts[t] <= max(1, len(explicit_docs) / 10)}
        eligible = {d["source_id"]: sorted(anchors & set(terms(d["text"]))) for d in explicit_docs}
        knowledge = self.search(
            query, "knowledge", engines, knowledge_limit, associated_only=True,
            source_ids=[source_id for source_id, matched in eligible.items() if matched],
        )

        supported: dict[str, list[dict[str, Any]]] = {}
        for rank, hit in enumerate(knowledge, 1):
            for key, links in self.knowledge_links[hit["source_id"]].items():
                if self.tables[key].engine not in engines or "schema:" + key in set(exclude):
                    continue
                supported.setdefault(key, []).append(
                    {
                        **hit,
                        "source_id": hit["source_id"],
                        "knowledge_rank": rank,
                        "knowledge_score": hit["score"],
                        "matched_query_tokens": eligible[hit["source_id"]][:8],
                        "association_links": links,
                    }
                )
        order = sorted(supported, key=lambda key: (min(h["knowledge_rank"] for h in supported[key]), key))
        ranks = {key: rank for rank, key in enumerate(order, 1)}
        existing = {hit["table_ids"][0] for hit in base}
        for key in supported:
            if key not in existing:
                base.append(
                    {
                        "source_id": "schema:" + key,
                        "table_ids": [key],
                        "score": 0.0,
                        "rrf_score": 0.0,
                        "candidate_score": 0.0,
                        "semantic_rank": None,
                        "semantic_similarity": None,
                        "keyword_rank": None,
                        "keyword_score": 0.0,
                        "keyword_hits": [],
                    }
                )
        results = []
        for hit in base:
            key = hit["table_ids"][0]
            rank = ranks.get(key)
            support_score = 0.25 / (self.recall_config.rrf_k + rank) if rank else 0.0
            candidate_score = hit["rrf_score"] + support_score
            results.append(
                {
                    **hit,
                    "schema_score": hit["score"],
                    "knowledge_table_rank": rank,
                    "score": candidate_score,
                    "candidate_score": candidate_score,
                    "knowledge_support_score": support_score,
                    "knowledge_support": supported.get(key, [])[:2],
                }
            )
        return self.rank_hits(query, results, limit)
