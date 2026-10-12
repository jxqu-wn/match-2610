"""库表/知识/案例混合召回索引。

- 关键词：``rank_bm25``（中文按 1~3 字 n-gram，英文按下划线标识符切分）；
- 语义：``faiss`` 内积索引（不可用时退回 numpy 精确计算）；
- 融合：倒数排名融合（RRF）。

索引版本与来源文件 SHA256、编码器签名绑定；资料变化必须重建，避免旧向量
搭配新结构。
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from rank_bm25 import BM25Okapi

from ..config import settings
from ..io import file_sha256, get_logger, read_json, write_json, write_jsonl
from ..models import Catalog, Sample, Table
from .sql_parser import SourceResolver, engine_set

logger = get_logger(__name__)

INDEX_VERSION = 2
IDENTIFIER = r"[A-Za-z_][A-Za-z0-9_]*"
_RRF_K = 60
_KNOWLEDGE_TABLE_MENTION = re.compile(r"数据库([A-Za-z0-9_]+)(?:的表|中，)([^，。]+)")
_IDENTIFIER_LIKE = re.compile(r"[A-Za-z][A-Za-z0-9]*_[A-Za-z0-9_]+")


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


def literal_references(text: str, tables: dict[str, Table]) -> dict[str, list[dict[str, str]]]:
    """知识原文中可解析的明确库表引用；不使用单独字段名或业务语义推断表。"""
    links: dict[str, list[dict[str, str]]] = {}
    counts = Counter(((t.namespace or "").casefold(), t.name.casefold()) for t in tables.values())

    def add(key: str, kind: str, mention: str) -> None:
        item = {"kind": kind, "mention": mention}
        if item not in links.setdefault(key, []):
            links[key].append(item)

    for key, table in tables.items():
        namespace = table.namespace
        if not namespace or counts[(namespace.casefold(), table.name.casefold())] != 1:
            continue
        pattern = r"(?<![A-Za-z0-9_])" + re.escape(namespace + "." + table.name) + r"(?![A-Za-z0-9_])"
        for match in re.finditer(pattern, text, re.I):
            add(key, "qualified_table", match.group())

    scopes = list(re.finditer(r"数据库(" + IDENTIFIER + r")", text))
    for index, match in enumerate(scopes):
        end = scopes[index + 1].start() if index + 1 < len(scopes) else len(text)
        region = text[match.end() : end]
        for key, table in tables.items():
            namespace = table.namespace
            if not namespace or namespace.casefold() != match.group(1).casefold():
                continue
            if counts[(namespace.casefold(), table.name.casefold())] != 1:
                continue
            name = re.escape(table.name)
            lists = re.findall(r"表\s*([A-Za-z_][A-Za-z0-9_-]*(?:\s*[和及与、,]\s*[A-Za-z_][A-Za-z0-9_-]*)*)", region)
            listed = any(re.search(name, value, re.I) for value in lists)
            suffix = re.search(r"(?<![A-Za-z0-9_.])" + name + r"\s*表", region, re.I)
            reference = re.search(r"(?:关联到?|映射到)\s*" + name + r"(?![A-Za-z0-9_])", region, re.I)
            fields = re.findall(r"(?<![A-Za-z0-9_.])" + name + r"\.(" + IDENTIFIER + r")(?![A-Za-z0-9_])", region, re.I)
            field_reference = any(
                field.casefold() in {c.name.casefold() for c in table.columns} for field in fields
            )
            if listed or suffix or reference or field_reference:
                add(key, "database_scoped_table_name", match.group() + " … " + table.name)

    for match in re.finditer(r"(?<![A-Za-z0-9_])(" + IDENTIFIER + r")\.(" + IDENTIFIER + r")(?![A-Za-z0-9_])", text):
        candidates = [
            key
            for key, table in tables.items()
            if table.name.casefold() == match.group(1).casefold()
            and any(c.name.casefold() == match.group(2).casefold() for c in table.columns)
        ]
        if len(candidates) == 1:
            add(candidates[0], "unique_table_field", match.group())
    return links


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
        # 形如“表Checkins和Days”的句子需要把提到的表全部关联。
        for match in _KNOWLEDGE_TABLE_MENTION.finditer(text):
            database, sentence = match.groups()
            for key, table in tables.items():
                if table.database == database and re.search(
                    r"(?<![A-Za-z0-9_])" + re.escape(table.name) + r"(?![A-Za-z0-9_])", sentence
                ):
                    related.add(key)
        if not related:
            identifiers = set(_IDENTIFIER_LIKE.findall(text))
            related = {
                key for key, table in tables.items() if identifiers & {c.name for c in table.columns}
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
                "association": "source_or_field_reference" if related else "unscoped",
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
        self, documents: list[dict[str, Any]], encoder: Any = None, vectors: np.ndarray | None = None
    ) -> None:
        self.documents = documents
        self.by_id = {d["source_id"]: d for d in documents}
        self.tables: dict[str, Table] = {
            d["table_ids"][0]: Table.model_validate(d["data"]) for d in documents if d["kind"] == "schema"
        }
        self.encoder = encoder
        self.vectors = vectors
        self.positions = {d["source_id"]: i for i, d in enumerate(documents)}
        self.stats = {"semantic_queries": 0, "embedding_cache_hits": 0, "lexical_searches": 0}
        tokenized = [tokenize(d["text"]) for d in documents]
        self._tokenized = tokenized
        self._bm25 = BM25Okapi(tokenized) if any(tokenized) else None
        self._faiss = self._build_faiss(vectors) if vectors is not None else None
        self.explicit_knowledge_links = {
            d["source_id"]: literal_references(d["text"], self.tables)
            for d in documents
            if d["kind"] == "knowledge"
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
                return {int(i): float(s) for i, s in zip(ids[0], scores[0]) if i >= 0}
            except Exception:  # noqa: BLE001 - 退回精确计算
                pass
        subset = self.vectors[candidates]
        return {index: float(value) for index, value in zip(candidates, subset @ query_vector)}

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
    ) -> "RetrievalIndex":
        from ..data.catalog import load_catalog

        path = path or settings.path("outputs/information_retrieval/index")
        training_source = training_source or settings.train_split
        catalog = catalog or load_catalog()
        knowledge = knowledge if knowledge is not None else read_json(settings.knowledge)
        train_rows = train_rows if train_rows is not None else read_json(training_source)
        documents, audit = build_documents(catalog, knowledge, train_rows)

        path.mkdir(parents=True, exist_ok=True)
        write_jsonl(path / "documents.jsonl", documents)
        vectors = encoder.encode([d["text"] for d in documents]) if encoder else None
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
                "documents": len(documents),
                "audit": audit["document_counts"],
                "artifacts": {name: file_sha256(path / name) for name in artifacts},
            },
        )
        return cls(documents, encoder, vectors)

    @classmethod
    def load(
        cls,
        path: Path | None = None,
        encoder: Any = None,
        *,
        training_source: Path | None = None,
    ) -> "RetrievalIndex":
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
        return cls(documents, encoder, vectors)

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
    ) -> list[dict[str, Any]]:
        self.stats["lexical_searches"] += 1
        selected = set(engines)
        scope = set(scope_table_ids) if scope_table_ids is not None else None
        excluded = set(exclude)
        table_filter = set(table_ids) if table_ids is not None else None

        def associated(document: dict[str, Any]) -> list[str]:
            if explicit_only:
                return list(self.explicit_knowledge_links.get(document["source_id"], {}))
            return document["table_ids"]

        def doc_engines(document: dict[str, Any]) -> set[str]:
            if explicit_only:
                return {self.tables[key].engine for key in associated(document)}
            return set(document["engines"])

        candidates = [
            i
            for i, document in enumerate(self.documents)
            if document["kind"] == kind
            and (doc_engines(document) == selected if exact_engines else doc_engines(document) <= selected)
            and bool(doc_engines(document))
            and document["source_id"] not in excluded
            and (table_filter is None or bool(set(associated(document)) & table_filter))
            and (scope is None or (bool(associated(document)) and set(associated(document)) <= scope))
        ]
        if not candidates:
            return []

        lexical = self._lexical_scores(query, candidates)
        lexical_order = sorted(
            (i for i in candidates if lexical.get(i, 0) > 0),
            key=lambda i: (-lexical[i], self.documents[i]["source_id"]),
        )
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
                    sorted(candidates, key=lambda i: (-semantic.get(i, 0.0), self.documents[i]["source_id"]))
                )
            }

        fused = {
            i: sum(1 / (_RRF_K + ranks[i]) for ranks in (keyword_rank, semantic_rank) if i in ranks)
            for i in candidates
        }
        ordered = sorted(
            (i for i in candidates if fused[i] > 0), key=lambda i: (-fused[i], self.documents[i]["source_id"])
        )[:limit]
        query_terms = set(terms(query))
        return [
            {
                "source_id": self.documents[i]["source_id"],
                "table_ids": self.documents[i]["table_ids"],
                "score": fused[i],
                "semantic_rank": semantic_rank.get(i),
                "semantic_similarity": semantic.get(i),
                "keyword_rank": keyword_rank.get(i),
                "keyword_score": lexical.get(i, 0.0),
                "keyword_hits": sorted(
                    query_terms & set(self._tokenized[i]), key=lambda t: (-len(t), t)
                )[:12],
            }
            for i in ordered
        ]

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
        base = self.search(query, "schema", engines, len(self.tables), exclude=exclude)

        # 仅保留原文命中问题中低频 token 的知识，且该知识有明确表引用。
        explicit_docs = [
            d
            for d in self.documents
            if d["kind"] == "knowledge" and self.explicit_knowledge_links.get(d["source_id"])
        ]
        query_terms = {t for t in terms(query) if len(t) >= 2 and not t.isdigit()}
        counts = Counter(t for d in explicit_docs for t in set(terms(d["text"])))
        anchors = {t for t in query_terms if counts[t] <= max(1, len(explicit_docs) / 10)}
        eligible = {d["source_id"]: sorted(anchors & set(terms(d["text"]))) for d in explicit_docs}
        knowledge = [
            hit
            for hit in self.search(query, "knowledge", engines, len(explicit_docs), explicit_only=True)
            if eligible[hit["source_id"]]
        ][:knowledge_limit]

        supported: dict[str, list[dict[str, Any]]] = {}
        for rank, hit in enumerate(knowledge, 1):
            for key, links in self.explicit_knowledge_links[hit["source_id"]].items():
                if self.tables[key].engine not in engines or "schema:" + key in set(exclude):
                    continue
                supported.setdefault(key, []).append(
                    {
                        "source_id": hit["source_id"],
                        "knowledge_rank": rank,
                        "knowledge_score": hit["score"],
                        "matched_query_tokens": eligible[hit["source_id"]][:8],
                        "literal_links": links,
                    }
                )
        order = sorted(supported, key=lambda key: (-max(h["knowledge_score"] for h in supported[key]), key))
        ranks = {key: rank for rank, key in enumerate(order, 1)}
        existing = {hit["table_ids"][0] for hit in base}
        for key in supported:
            if key not in existing:
                base.append(
                    {
                        "source_id": "schema:" + key,
                        "table_ids": [key],
                        "score": 0.0,
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
            results.append(
                {
                    **hit,
                    "schema_score": hit["score"],
                    "knowledge_table_rank": rank,
                    "score": hit["score"] + (0.25 / (_RRF_K + rank) if rank else 0),
                    "knowledge_support": supported.get(key, [])[:2],
                }
            )
        return sorted(results, key=lambda h: (-h["score"], h["source_id"]))[:limit]
