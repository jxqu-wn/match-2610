"""Offline table-to-knowledge retrieval benchmark; reviewed labels are scoring-only.

This measures knowledge ranking from raw table schemas, not question-to-SQL quality
or production preprocessing associations. No reviewed links scope the candidates.
"""

# ruff: noqa: E402 -- standalone evaluation entry point
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import platform
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np

from text2query.config import settings
from text2query.data.catalog import document_text, parse_es, parse_sql, resolve_implicit_foreign_keys
from text2query.io import file_sha256, read_json, write_json
from text2query.models import Catalog
from text2query.retrieval.embedding import retrieval_encoder
from text2query.retrieval.index import RetrievalIndex
from text2query.retrieval.ranking import RecallConfig, RerankerService

ENGINES = ["MYSQL", "POSTGRESQL", "Elasticsearch"]
METHODS = ("bm25", "embedding", "rrf", "rrf_rerank")
CUTOFFS = (1, 3, 5, 8, 12, 20, 50)


def fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def raw_queries(context: dict[str, Any]) -> list[dict[str, str]]:
    tables = []
    for source in context["schema_sources"]:
        path = ROOT / source["source_file"]
        if file_sha256(path) != source["sha256"]:
            raise ValueError("Schema differs from frozen inputs: " + str(path))
        name = Path(source["source_file"]).name
        tables.extend(parse_sql(source["text"], name, source["encoding"]))
        tables.extend(parse_es(source["text"], name, source["encoding"]))
    catalog = Catalog(format_version=1, sources=[], tables=tables)
    resolve_implicit_foreign_keys(catalog)
    expected = [table["table_id"] for table in context["table_catalog"]]
    by_id = catalog.by_id()
    if len(tables) != len(expected) or set(by_id) != set(expected):
        raise ValueError("Raw schema coverage differs from frozen table catalog")
    return [{"table_id": table_id, "query": document_text(by_id[table_id])} for table_id in expected]


def documents(knowledge: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # All knowledge competes globally. No human or programmatic table links are
    # supplied, and the same candidate scope is used for all four methods.
    return [
        {
            "source_id": f"knowledge:{item['knowledge_id']}",
            "kind": "knowledge",
            "engines": ENGINES,
            "table_ids": [],
            "text": item["knowledge_text"],
            "data": item,
        }
        for item in knowledge
    ]


class CachedReranker:
    """Reuse identical schema/text scores between the old and new corpus runs."""

    def __init__(self, service: RerankerService, path: Path):
        self.service, self.path = service, path
        self.signature = service.signature
        self.prefix = fingerprint(self.signature)
        self.cache: dict[str, float] = {}
        self.hits = 0
        self.computed = 0

    def score(self, query: str, texts: list[str]) -> list[float]:
        keys = [fingerprint([self.prefix, query, text]) for text in texts]
        missing = dict((key, text) for key, text in zip(keys, texts, strict=True) if key not in self.cache)
        self.hits += len(keys) - len(missing)
        if missing:
            scores = self.service.score(query, list(missing.values()))
            self.cache.update(zip(missing, scores, strict=True))
            self.computed += len(scores)
            with self.path.open("a", encoding="utf-8") as stream:
                for key, score in zip(missing, scores, strict=True):
                    stream.write(json.dumps({"key": key, "score": score}) + "\n")
        return [self.cache[key] for key in keys]


def ranked_ids(index: RetrievalIndex, hits: list[dict[str, Any]]) -> list[int]:
    return [index.by_id[hit["source_id"]]["data"]["knowledge_id"] for hit in hits]


def run_rankings(
    name: str,
    corpus: list[dict[str, Any]],
    queries: list[dict[str, str]],
    encoder: Any,
    reranker: CachedReranker,
    output: Path,
    vectors: np.ndarray,
) -> dict[str, Any]:
    started = time.perf_counter()
    docs = documents(corpus)
    config = RecallConfig()
    keyword = RetrievalIndex(docs, recall_config=RecallConfig(rerank_enabled=False))
    hybrid = RetrievalIndex(docs, encoder, vectors, recall_config=config, reranker=reranker)
    rows = []
    for number, entry in enumerate(queries, 1):
        query = entry["query"]
        bm25 = keyword.search(query, "knowledge", ENGINES, limit=50, rerank=False)
        semantic_scores = hybrid._semantic_scores(encoder.encode([query])[0], list(range(len(docs))))
        semantic = sorted(range(len(docs)), key=lambda i: (-semantic_scores[i], docs[i]["source_id"]))[:50]
        rrf = hybrid.search(query, "knowledge", ENGINES, limit=50, rerank=False)
        reranked = hybrid.rank_hits(query, rrf, limit=50)
        rows.append(
            {
                "table_id": entry["table_id"],
                "rankings": {
                    "bm25": ranked_ids(keyword, bm25),
                    "embedding": [docs[i]["data"]["knowledge_id"] for i in semantic],
                    "rrf": ranked_ids(hybrid, rrf),
                    "rrf_rerank": ranked_ids(hybrid, reranked),
                },
                "reranked_hits": [
                    {"knowledge_id": hybrid.by_id[hit["source_id"]]["data"]["knowledge_id"], **hit}
                    for hit in reranked
                ],
            }
        )
        with (output / f"{name}.rankings.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(rows[-1], ensure_ascii=False) + "\n")
        print(f"{name}: {number}/{len(queries)} {entry['table_id']}", flush=True)
    return {"rows": rows, "seconds": time.perf_counter() - started, "index_stats": hybrid.stats}


def score_rankings(
    rows: list[dict[str, Any]], target: dict[str, set[int]], judged_ids: set[int]
) -> dict[str, Any]:
    """Unjudged new/changed text never becomes a false positive by implication."""
    result: dict[str, Any] = {}
    nonempty = sum(bool(ids) for ids in target.values())
    for method in METHODS:
        cutoffs = {}
        for cutoff in CUTOFFS:
            counts = Counter()
            reciprocal, ndcg, macro_recall = [], [], []
            per_table = []
            for row in rows:
                table_id = row["table_id"]
                wanted = target[table_id]
                ranking = row["rankings"][method][:cutoff]
                predicted = set(ranking) & judged_ids
                matched = predicted & wanted
                extra = predicted - wanted
                missing = wanted - predicted
                unjudged = set(ranking) - judged_ids
                counts.update(tp=len(matched), fp=len(extra), fn=len(missing), unjudged=len(unjudged), returned=len(ranking))
                if not wanted:
                    counts["empty_tables_with_judged_predictions"] += bool(predicted)
                else:
                    macro_recall.append(len(matched) / len(wanted))
                    reciprocal.append(next((1 / rank for rank, kid in enumerate(ranking, 1) if kid in wanted), 0.0))
                    dcg = sum(1 / math.log2(rank + 1) for rank, kid in enumerate(ranking, 1) if kid in wanted)
                    ideal = sum(1 / math.log2(rank + 1) for rank in range(1, min(cutoff, len(wanted)) + 1))
                    ndcg.append(dcg / ideal)
                if cutoff == 12:
                    per_table.append(
                        {"table_id": table_id, "matched": sorted(matched), "extra_judged": sorted(extra),
                         "missing": sorted(missing), "unjudged": sorted(unjudged), "ranking": ranking}
                    )
            tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]
            cutoffs[str(cutoff)] = {
                **dict(counts),
                "precision_on_judged": tp / (tp + fp) if tp + fp else None,
                "recall": tp / (tp + fn) if tp + fn else None,
                "f1_on_judged": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None,
                "judged_fraction": (tp + fp) / counts["returned"] if counts["returned"] else None,
                "macro_recall_nonempty": float(np.mean(macro_recall)) if nonempty else None,
                "mrr_nonempty": float(np.mean(reciprocal)) if nonempty else None,
                "known_positive_ndcg_nonempty": float(np.mean(ndcg)) if nonempty else None,
                **({"per_table": per_table} if cutoff == 12 else {}),
            }
        result[method] = cutoffs
    return result


def pct(value: float | None) -> str:
    return f"{value:.2%}" if value is not None else "—"


def write_readme(report: dict[str, Any], output: Path) -> None:
    lines = [
        "# 混合召回评估", "",
        f"Embedding：{Path(report['embedding_signature']['model_path']).name}；"
        f"Reranker：{Path(report['reranker_signature']['model_path']).name}。", "",
        "以原始表结构为查询检索知识；比较 BM25、Embedding、RRF、RRF＋重排。",
        "本实验评估表→知识候选排序，不等同于逐题召回、预处理确认关联或最终 SQL 正确率。",
        "候选不按审核关联过滤，生产预处理不读取标注；标注仅在全部排序完成后用于离线评分。", "",
        "参数：两路各取50，RRF k=60，重排前50；向量截断512 tokens，重排截断2048 tokens。",
        "参数未依据本轮分数调优；仍属于已有审核集上的开发评估，未验证未见数据泛化。", "",
    ]
    for name, run in report["corpora"].items():
        lines += [
            f"## {name}", "",
            f"知识 {run['knowledge_count']} 条；可评分原文 {run['judged_knowledge_count']} 条；"
            f"目标关联 {run['target_pairs']} 对；耗时 {run['ranking_seconds']:.1f} 秒。", "",
            "| 方法 | P@12（已标注原文） | Recall@12 | F1@12（已标注原文） | MRR@12（非空表） | 未标注返回数@12 |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
        for method in METHODS:
            score = run["metrics"][method]["12"]
            lines.append(
                f"| {method} | {pct(score['precision_on_judged'])} | {pct(score['recall'])} | "
                f"{pct(score['f1_on_judged'])} | {score['mrr_nonempty']:.4f} | {score.get('unjudged', 0)} |"
            )
        lines += ["", "| 方法 | Recall@1 | Recall@3 | Recall@5 | Recall@8 | Recall@12 | Recall@20 | Recall@50 |",
                  "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
        for method in METHODS:
            lines.append("| " + method + " | " + " | ".join(pct(run["metrics"][method][str(k)]["recall"]) for k in CUTOFFS) + " |")
        lines += [""]
    lines += [
        "新版知识库：只对旧版与新版 knowledge_id、原文同时相同的知识评分。新增、改写知识为未标注，",
        "其返回数量单列，不计为多关联；新版 precision/F1 仅针对已标注子集，不能与旧版整体精度直接比较。",
        "两种排序算法的差异才是本次消融比较；固定 Top-K 结果不自动成为生产确认关联。", "",
        f"GPU 显存峰值（PyTorch allocated）：{report['hardware']['peak_allocated_gib']:.2f} GiB；"
        f"reserved：{report['hardware']['peak_reserved_gib']:.2f} GiB。", "",
        "完整逐表差异、排序分数、输入及代码哈希见 report.json 和各 *.rankings.jsonl。", "",
    ]
    (output / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--dtype", choices=("float16", "bfloat16"), default="bfloat16")
    parser.add_argument("--embedding-batch-size", type=int, default=4)
    parser.add_argument("--reranker-batch-size", type=int, default=2)
    parser.add_argument("--release-embedding", action="store_true")
    args = parser.parse_args()
    if args.output_dir.exists():
        raise ValueError("Output exists; choose a new run directory")
    args.output_dir.mkdir(parents=True)
    output = args.output_dir
    context_path = ROOT / "evaluation/table_knowledge/input_context.json"
    context = read_json(context_path)["context"]
    queries = raw_queries(context)
    old = context["knowledge_context"]
    new = read_json(settings.knowledge)
    old_texts = {item["knowledge_id"]: item["knowledge_text"] for item in old}
    new_texts = {item["knowledge_id"]: item["knowledge_text"] for item in new}
    stable = {kid for kid, text in old_texts.items() if new_texts.get(kid) == text}
    if len(old_texts) != len(old) or len(new_texts) != len(new):
        raise ValueError("Duplicate knowledge IDs")
    write_json(output / "queries.json", queries)
    import torch

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for this GPU benchmark")
    torch.cuda.set_device(torch.device(args.device))
    torch.cuda.reset_peak_memory_stats(args.device)
    encoder = retrieval_encoder(device=args.device, dtype=args.dtype, batch_size=args.embedding_batch_size,
                                max_length=512, cache_dir=output / "embedding_cache")
    service = RerankerService(device=args.device, dtype=args.dtype, batch_size=args.reranker_batch_size, max_length=2048)
    reranker = CachedReranker(service, output / "reranker_cache.jsonl")
    started = time.perf_counter()
    try:
        vectors = {}
        for name, corpus in (("frozen_247", old), ("current_1833", new)):
            print(f"Embedding {name}: {len(corpus)} documents", flush=True)
            vectors[name] = encoder.encode_documents([item["knowledge_text"] for item in corpus])
            np.testing.assert_allclose(np.linalg.norm(vectors[name], axis=1), 1, atol=1e-4)
        encoder.encode([row["query"] for row in queries])
        embedding_seconds = time.perf_counter() - started
        if args.release_embedding:
            encoder.unload()
        ranked = {
            name: run_rankings(name, corpus, queries, encoder, reranker, output, vectors[name])
            for name, corpus in (("frozen_247", old), ("current_1833", new))
        }
        hardware = {
            "gpu": torch.cuda.get_device_name(args.device),
            "total_gib": torch.cuda.get_device_properties(args.device).total_memory / 1024**3,
            "peak_allocated_gib": torch.cuda.max_memory_allocated(args.device) / 1024**3,
            "peak_reserved_gib": torch.cuda.max_memory_reserved(args.device) / 1024**3,
            "embedding_kept_loaded": not args.release_embedding,
        }
    finally:
        encoder.unload()
        service.unload()

    # Reviewed targets are first loaded after both corpus rankings are complete.
    reference = ROOT / "evaluation/table_knowledge/runs/reference-v1"
    manifest = read_json(reference / "manifest.json")
    if file_sha256(context_path) != manifest["input_files"]["input_context.json"]:
        raise ValueError("Frozen input hash mismatch")
    for name, expected in manifest["files"].items():
        if file_sha256(reference / name) != expected:
            raise ValueError("Reference hash mismatch: " + name)
    target_rows = read_json(reference / "tables.json")["tables"]
    target = {}
    for row in target_rows:
        for item in row["knowledge"]:
            if old_texts.get(item["knowledge_id"]) != item["knowledge_text"]:
                raise ValueError("Reference text differs from frozen knowledge")
        ids = [item["knowledge_id"] for item in row["knowledge"]]
        if len(ids) != len(set(ids)) or row["table_id"] in target:
            raise ValueError("Duplicate reference table or pair")
        target[row["table_id"]] = set(ids)
    if set(target) != {row["table_id"] for row in queries}:
        raise ValueError("Reference/query table coverage differs")
    report = {
        "benchmark": "raw_schema_to_knowledge_retrieval_v1",
        "hardware": hardware,
        "environment": {name: importlib.metadata.version(name) for name in
                        ("torch", "transformers", "sentence-transformers", "numpy", "faiss-cpu", "rank-bm25")},
        "python": platform.python_version(),
        "parameters": {**vars(args), "output_dir": str(output)},
        "embedding_signature": encoder.signature,
        "reranker_signature": service.signature,
        "recall_parameters": RecallConfig().as_dict(),
        "input_sha256": {"context": file_sha256(context_path), "new_knowledge": file_sha256(settings.knowledge),
                         "reference": file_sha256(reference / "tables.json")},
        "code_sha256": {str(path.relative_to(ROOT)): file_sha256(path) for path in
                        [Path(__file__), *sorted((ROOT / "src/text2query").rglob("*.py"))]},
        "embedding_seconds": embedding_seconds,
        "reranker_computed_pairs": reranker.computed,
        "reranker_cached_pairs": reranker.hits,
        "corpora": {},
        "limitations": [
            "Table-to-knowledge proxy benchmark, not question retrieval or SQL generation accuracy.",
            "Fixed Top-K hypotheses are not confirmed preprocessing associations.",
            "Development evaluation on an existing reviewed set, not held-out generalization.",
            "For the new corpus only identical ID AND text is judged; changed/new text is unjudged.",
            "New-corpus precision/F1 uses judged predictions only; inspect judged_fraction and unjudged counts.",
            "Schema embedding is truncated at 512 tokens; reranking pairs are truncated at 2048 tokens.",
        ],
    }
    for name, corpus, judged in (("frozen_247", old, set(old_texts)), ("current_1833", new, stable)):
        wanted = {table_id: ids & judged for table_id, ids in target.items()}
        report["corpora"][name] = {
            "knowledge_count": len(corpus), "judged_knowledge_count": len(judged),
            "judged_knowledge_ids": sorted(judged), "target_pairs": sum(map(len, wanted.values())),
            "table_count": len(wanted), "nonempty_tables": sum(bool(ids) for ids in wanted.values()),
            "ranking_seconds": ranked[name]["seconds"], "index_stats": ranked[name]["index_stats"],
            "metrics": score_rankings(ranked[name]["rows"], wanted, judged),
        }
    write_json(output / "report.json", report)
    write_readme(report, output)
    print(json.dumps({"output": str(output), "hardware": hardware,
                      "embedding_seconds": embedding_seconds,
                      "ranking_seconds": {name: row["seconds"] for name, row in ranked.items()}}, indent=2), flush=True)


if __name__ == "__main__":
    main()
