"""Three isolated preprocessing/prompt runs; validation answers are scoring-only.

Run ``prepare``, ``run --method ...`` for all three methods, then ``score``.
Model-produced table/knowledge links are explicitly experimental candidates.
The default production catalog and its association rules are never overwritten.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import platform
import time
from pathlib import Path
from typing import Any

from ..config import settings
from ..data.catalog import build_catalog, document_text, schema_documents
from ..data.split import build_split
from ..io import canonical_json, file_sha256, read_json, read_jsonl, write_json, write_jsonl
from ..models import Catalog, KnowledgeRef, Sample, Table
from ..retrieval.context import Budget, ContextBuilder
from ..retrieval.embedding import retrieval_encoder
from ..retrieval.index import RetrievalIndex
from ..retrieval.ranking import RecallConfig, RerankerService
from ..retrieval.sql_parser import SourceResolver, engine_set
from ..routing.classifier import CharacterTfidfBaseline, label
from ..submission.finetuned import (
    EXCLUDED_TABLE_IDS,
    build_instruction,
    database_label,
    es_mapping_block,
    normalize_ddl,
)

METHODS = ("programmatic", "hybrid-8b", "hybrid-0.6b")
MODEL_SIZES = {"hybrid-8b": "8B", "hybrid-0.6b": "0.6B"}
ENGINES = ["MYSQL", "POSTGRESQL", "Elasticsearch"]


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def code_hashes() -> dict[str, str]:
    root = settings.project_root
    return {str(p.relative_to(root)): file_sha256(p) for p in sorted((root / "src/text2query").rglob("*.py"))}


def persist_catalog(catalog: Catalog, knowledge: list[dict], directory: Path) -> Catalog:
    """Keep full score evidence separately, without duplicating it in both catalogs."""
    audit = (catalog.model_extra or {}).get("association_audit", {})
    write_json(directory / "knowledge_association_audit.json", audit)
    data = catalog.model_dump(by_alias=True)
    data["association_audit"] = {
        k: v for k, v in audit.items() if k not in {"pairs", "support", "rankings"}
    }
    data["association_audit"]["detail_file"] = "knowledge_association_audit.json"
    write_json(directory / "schema_extracted.json", data)
    write_json(directory / "schema_catalog.json", data)
    write_json(directory / "knowledge.json", knowledge)
    write_json(directory / "training_support_audit.json", audit.get("support", {}))
    write_jsonl(directory / "schema_documents.jsonl", schema_documents(catalog))
    return Catalog.model_validate(data)


def prepare(directory: Path, *, seed: int = 42, max_tables: int = 6, max_chars: int = 16000) -> None:
    if directory.exists():
        raise FileExistsError("Choose a new experiment directory")
    if max_tables < 1 or max_chars < 1:
        raise ValueError("Prompt limits must be positive")
    directory.mkdir(parents=True)
    shared = directory / "shared"
    split = build_split(output_dir=shared / "splits", seed=seed)
    train = read_json(shared / "splits/train.json")
    validation = read_json(shared / "splits/validation.json")
    texts = {r["question"] for r in validation}
    # Preserve every validation question; remove identical texts from training.
    excluded = [r["question_id"] for r in train if r["question"] in texts]
    train = [r for r in train if r["question"] not in texts]
    write_json(shared / "retrieval_train.json", train)
    public = [{k: r[k] for k in ("question_id", "question")} for r in validation]
    write_json(shared / "questions.json", public)
    catalog = build_catalog(training_source=shared / "retrieval_train.json", training_support="sql")
    persist_catalog(catalog, read_json(settings.knowledge), directory / "programmatic/preprocessed")
    router = CharacterTfidfBaseline().fit(
        [r["question"] for r in train], [label(Sample.model_validate(r)) for r in train]
    )
    predicted = router.predict([r["question"] for r in public])
    write_json(shared / "routing.json", [
        {"question_id": row["question_id"], "predicted_engines": value.split("|")}
        for row, value in zip(public, predicted, strict=True)
    ])
    import joblib

    joblib.dump(router.pipeline, shared / "router.joblib")
    sources = {"qa_train": file_sha256(settings.qa_train), "knowledge": file_sha256(settings.knowledge)}
    sources.update({name: file_sha256(path) for name, path in settings.schema_sources.items()})
    manifest = {
        "experiment": "three_preprocessing_prompt_coverage_v1", "methods": list(METHODS),
        "seed": seed, "split": split, "training_rows": len(train),
        "validation_rows": len(public), "excluded_training_ids_with_validation_text": excluded,
        "router": "shared CharacterTfidfBaseline trained only on retrieval_train.json",
        "max_tables": max_tables, "max_instruction_chars": max_chars,
        "model_association_top_k": 12, "recall_parameters": RecallConfig().as_dict(),
        "source_sha256": sources, "code_sha256": code_hashes(),
        "shared_sha256": {name: file_sha256(shared / name) for name in
                          ("retrieval_train.json", "questions.json", "routing.json", "router.joblib",
                           "splits/validation.json", "splits/train.json")},
        "baseline_catalog_sha256": file_sha256(directory / "programmatic/preprocessed/schema_catalog.json"),
        "prompt_flow": "ContextBuilder.assemble -> finetuned.build_instruction -> whole-table character pruning",
        "model_links": "experimental candidate ownership; not reviewed/confirmed business associations",
        "validation_answers": "query fields are not used during generation; parsed by score after all prompts complete",
    }
    write_json(directory / "manifest.json", manifest)
    print(json.dumps({"prepared": str(directory), "training": len(train), "validation": len(public),
                      "excluded_training_duplicates": len(excluded)}, ensure_ascii=False), flush=True)


def verify_inputs(directory: Path) -> dict:
    manifest = read_json(directory / "manifest.json")
    if manifest["code_sha256"] != code_hashes():
        raise ValueError("Experiment code changed; create a new experiment")
    for name, expected in manifest["shared_sha256"].items():
        if file_sha256(directory / "shared" / name) != expected:
            raise ValueError("Shared input changed: " + name)
    if file_sha256(settings.knowledge) != manifest["source_sha256"]["knowledge"]:
        raise ValueError("Knowledge changed")
    for name, path in settings.schema_sources.items():
        if file_sha256(path) != manifest["source_sha256"][name]:
            raise ValueError("Schema changed: " + name)
    baseline = directory / "programmatic/preprocessed/schema_catalog.json"
    if file_sha256(baseline) != manifest["baseline_catalog_sha256"]:
        raise ValueError("Baseline catalog changed")
    return manifest


class CachedScores:
    """Reuse exact model/query/text scores within this run; no ranking shortcuts."""

    def __init__(self, service: RerankerService, path: Path):
        self.service, self.path = service, path
        self.signature = service.signature
        self.prefix = digest(self.signature)
        self.cache: dict[str, float] = {}
        self.computed = self.hits = 0

    def score(self, query: str, documents: list[str]) -> list[float]:
        keys = [digest([self.prefix, query, text]) for text in documents]
        missing = {key: text for key, text in zip(keys, documents, strict=True) if key not in self.cache}
        self.hits += len(keys) - len(missing)
        if missing:
            values = self.service.score(query, list(missing.values()))
            self.cache.update(zip(missing, values, strict=True))
            self.computed += len(values)
            with self.path.open("a", encoding="utf-8") as stream:
                for key, value in zip(missing, values, strict=True):
                    stream.write(json.dumps({"key": key, "score": value}) + "\n")
        return [self.cache[key] for key in keys]


def model_catalog(catalog: Catalog, knowledge: list[dict], encoder: Any,
                  reranker: CachedScores, method: str, top_k: int, output: Path) -> Catalog:
    documents = [{"source_id": f"knowledge:{k['knowledge_id']}", "kind": "knowledge",
                  "engines": ENGINES, "table_ids": [], "text": k["knowledge_text"], "data": k}
                 for k in knowledge]
    vectors = encoder.encode_documents([d["text"] for d in documents])
    index = RetrievalIndex(documents, encoder, vectors, recall_config=RecallConfig(), reranker=reranker)
    queries = [document_text(t) for t in catalog.tables]
    encoder.encode(queries)
    rows = []
    for number, (table, query) in enumerate(zip(catalog.tables, queries, strict=True), 1):
        hits = index.search(query, "knowledge", ENGINES, limit=50)
        table.knowledge = sorted(
            [KnowledgeRef(**index.by_id[h["source_id"]]["data"]) for h in hits[:top_k]],
            key=lambda k: k.knowledge_id,
        )
        rows.append({"table_id": table.table_id, "query": query, "rankings": hits,
                     "candidate_knowledge_ids": [index.by_id[h["source_id"]]["data"]["knowledge_id"]
                                                 for h in hits[:top_k]]})
        if number % 12 == 0:
            print(f"{method}: table/knowledge candidates {number}/{len(catalog.tables)}", flush=True)
    catalog.summary["knowledge_pairs"] = sum(len(t.knowledge) for t in catalog.tables)
    version = "experimental-" + method + "-rrf-rerank-top12-v1"
    catalog.summary["knowledge_association_version"] = version
    catalog.association_audit = {
        "version": version, "semantics": "experimental_candidates_not_confirmed",
        "method": method, "top_k": top_k, "threshold": None,
        "candidate_scope": "all raw knowledge; no reference labels or baseline link filtering",
        "embedding_signature": encoder.signature, "reranker_signature": reranker.signature,
        "recall_parameters": RecallConfig().as_dict(), "rankings": rows,
        "sources": {"knowledge_sha256": file_sha256(settings.knowledge)},
    }
    write_jsonl(output / "association_rankings.jsonl", rows)
    return catalog


def make_prompt(question: str, table_ids: list[str], tables: dict[str, Table], max_chars: int) -> dict:
    """Count exactly the DDL blocks actually kept by the existing prompt builder."""
    kept = list(dict.fromkeys(t for t in table_ids if t in tables and t not in EXCLUDED_TABLE_IDS))
    before = list(kept)
    instruction = build_instruction(kept, tables) if kept else ""
    chars_before = len(instruction)
    while kept and len(instruction) > max_chars:
        kept.pop()
        instruction = build_instruction(kept, tables) if kept else ""
    if not kept:
        instruction = "未召回能放入当前预算的官方表结构，证据不足，无法生成查询。"
    if len(instruction) > max_chars:
        raise ValueError("Even the empty-evidence instruction exceeds the budget")
    for key in kept:
        table = tables[key]
        block = es_mapping_block(table) if table.engine == "Elasticsearch" else normalize_ddl(table.raw_definition or "")
        if block not in instruction:
            raise AssertionError("Counted table is absent from the actual prompt: " + key)
    return {
        "prompt_table_ids": kept, "tables_before_char_pruning": before,
        "excluded_table_ids": [t for t in table_ids if t in EXCLUDED_TABLE_IDS],
        "removed_by_char_budget": [t for t in before if t not in kept],
        "instruction_chars_before": chars_before, "instruction_chars": len(instruction),
        "status": "prepared" if kept else "no_usable_tables",
        "messages": [{"role": "system", "content": instruction}, {"role": "user", "content": question}],
    }


def run_method(directory: Path, method: str, *, device: str, dtype: str) -> None:
    manifest = verify_inputs(directory)
    output = directory / method
    output.mkdir(exist_ok=True)
    if (output / "run.json").exists() or (output / "prompts.jsonl").exists():
        raise FileExistsError("Method already started; preserve it and choose a new experiment")
    catalog = Catalog.model_validate(read_json(directory / "programmatic/preprocessed/schema_catalog.json"))
    knowledge = read_json(settings.knowledge)
    train = read_json(directory / "shared/retrieval_train.json")
    questions = read_json(directory / "shared/questions.json")
    routes = read_json(directory / "shared/routing.json")
    assert [r["question_id"] for r in routes] == [r["question_id"] for r in questions]
    started = time.perf_counter()
    encoder = service = reranker = None
    hardware: dict[str, Any] = {}
    try:
        if method != "programmatic":
            import torch

            if not torch.cuda.is_available():
                raise RuntimeError("This experiment requires the authorized CUDA server")
            torch.cuda.set_device(torch.device(device))
            torch.cuda.reset_peak_memory_stats(device)
            size = MODEL_SIZES[method]
            encoder = retrieval_encoder(model_path=Path(f"../models/Qwen3-Embedding-{size}"),
                                        device=device, dtype=dtype, batch_size=4, max_length=512,
                                        cache_dir=output / "embedding_cache")
            service = RerankerService(Path(f"../models/Qwen3-Reranker-{size}"), device=device,
                                      dtype=dtype, batch_size=2, max_length=2048)
            reranker = CachedScores(service, output / "reranker_scores.jsonl")
            catalog = model_catalog(catalog, knowledge, encoder, reranker, method,
                                    manifest["model_association_top_k"], output)
            catalog = persist_catalog(catalog, knowledge, output / "preprocessed")
        association_seconds = time.perf_counter() - started
        settings.preprocessed_dir = output / "preprocessed"
        index = RetrievalIndex.build(output / "index", encoder, catalog=catalog, knowledge=knowledge,
                                     train_rows=train, training_source=directory / "shared/retrieval_train.json",
                                     recall_config=RecallConfig(rerank_enabled=method != "programmatic"),
                                     reranker=reranker)
        if encoder:
            encoder.encode([r["question"] for r in questions])
        builder = ContextBuilder(index, Budget(initial_tables=manifest["max_tables"],
                                               total_tables=max(12, manifest["max_tables"])))
        index_seconds = time.perf_counter() - started - association_seconds
        tables = catalog.by_id()
        for number, (row, route) in enumerate(zip(questions, routes, strict=True), 1):
            # Public question and predicted engines only: no validation SQL here.
            context = builder.assemble(row["question"], route["predicted_engines"], row["question_id"])
            keys = [t["table_id"] for t in context["candidate_tables"]]
            item = {**row, **route, "retrieved_table_ids": keys,
                    **make_prompt(row["question"], keys, tables, manifest["max_instruction_chars"])}
            with (output / "prompts.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(item, ensure_ascii=False) + "\n")
            with (output / "contexts.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(context, ensure_ascii=False) + "\n")
            if number % 10 == 0 or number == len(questions):
                progress = {"method": method, "prepared": number, "total": len(questions),
                            "elapsed_seconds": time.perf_counter() - started,
                            "reranker_computed_pairs": reranker.computed if reranker else 0}
                write_json(output / "progress.json", progress)
                print(json.dumps(progress), flush=True)
        if encoder:
            hardware = {"gpu": torch.cuda.get_device_name(device),
                        "peak_allocated_gib": torch.cuda.max_memory_allocated(device) / 1024**3,
                        "peak_reserved_gib": torch.cuda.max_memory_reserved(device) / 1024**3}
        write_json(output / "run.json", {
            "method": method, "prepared": len(questions), "elapsed_seconds": time.perf_counter() - started,
            "association_seconds": association_seconds, "index_and_query_encoding_seconds": index_seconds,
            "recall": index.recall_metadata, "stats": index.stats, "hardware": hardware,
            "encoder": encoder.signature if encoder else None,
            "reranker_computed_pairs": reranker.computed if reranker else 0,
            "reranker_cache_hits": reranker.hits if reranker else 0,
            "prompts_sha256": file_sha256(output / "prompts.jsonl"),
            "manifest_sha256": file_sha256(directory / "manifest.json"),
            "catalog_sha256": file_sha256(output / "preprocessed/schema_catalog.json"),
            "environment": {name: importlib.metadata.version(name) for name in
                            ("numpy", "scikit-learn", "sqlglot", "torch", "transformers",
                             "sentence-transformers", "rank-bm25", "faiss-cpu")},
            "python": platform.python_version(),
        })
    finally:
        if encoder:
            encoder.unload()
        if service:
            service.unload()


def database_key(table: Table) -> str:
    return table.engine + ":" + (table.namespace or database_label(table))


def reference_targets(row: dict, resolver: SourceResolver) -> dict:
    """All SQL steps plus the actual ES index; unresolved answers cannot pass."""
    ids: set[str] = set()
    issues = []
    for position, engine, query in Sample.model_validate(row).steps():
        try:
            parsed = resolver.parse(query, engine)
        except (ValueError, KeyError) as error:
            parsed = {"table_ids": [], "parse_status": "parse_error", "error": str(error)}
        unresolved = parsed.get("unresolved_tables", [])
        # Cross-source result is a protocol value, not an additional physical table.
        unresolved = [u for u in unresolved if not (position > 1 and u.strip('`"').lower() == "result")]
        valid_status = parsed.get("parse_status") in {"parsed", "unresolved_tables", "single_index_by_catalog"}
        if not valid_status or unresolved or not parsed.get("table_ids"):
            issues.append({"step": position, "engine": engine, **parsed, "remaining_unresolved": unresolved})
        ids.update(parsed.get("table_ids", []))
    return {"engines": engine_set(row), "table_ids": sorted(ids),
            "databases": sorted({database_key(resolver.tables[t]) for t in ids}),
            "evaluable": bool(ids) and not issues, "parse_issues": issues}


def coverage(expected: set[str], actual: set[str], evaluable: bool) -> dict:
    return {"complete": evaluable and bool(expected) and expected <= actual,
            "recall": len(expected & actual) / len(expected) if evaluable and expected else None,
            "missing": sorted(expected - actual), "extra": sorted(actual - expected)}


def aggregate(rows: list[dict]) -> dict:
    total = len(rows)
    result = {"count": total, "evaluable": sum(r["expected"]["evaluable"] for r in rows),
              "routing_correct": sum(r["routing_correct"] for r in rows),
              "empty_prompts": sum(r["prompt_status"] != "prepared" for r in rows)}
    for stage in ("retrieved", "prompt"):
        for kind in ("db", "table"):
            name = stage + "_" + kind + "_coverage"
            hits = sum(r[name]["complete"] for r in rows)
            result[stage + "_complete_" + kind + "_count"] = hits
            result[stage + "_complete_" + kind + "_coverage_rate"] = hits / total if total else None
            recalls = [r[name]["recall"] for r in rows if r[name]["recall"] is not None]
            result[stage + "_" + kind + "_recall_evaluable"] = sum(recalls) / len(recalls) if recalls else None
    return result


def score(directory: Path) -> None:
    manifest = verify_inputs(directory)
    # All three completed prompt artifacts must exist before parsing answer SQL.
    prepared = {}
    runs = {}
    for method in METHODS:
        runs[method] = read_json(directory / method / "run.json")
        path = directory / method / "prompts.jsonl"
        if file_sha256(path) != runs[method]["prompts_sha256"]:
            raise ValueError("Prompt file changed: " + method)
        prepared[method] = read_jsonl(path)
    answers = read_json(directory / "shared/splits/validation.json")
    tables = Catalog.model_validate(read_json(directory / "programmatic/preprocessed/schema_catalog.json")).by_id()
    resolver = SourceResolver(tables)
    expected = {r["question_id"]: reference_targets(r, resolver) for r in answers}
    write_json(directory / "reference_targets.json", [{"question_id": qid, **value} for qid, value in expected.items()])
    summary, details = {}, []
    ids = [r["question_id"] for r in answers]
    for method in METHODS:
        if [r["question_id"] for r in prepared[method]] != ids:
            raise ValueError("Question coverage differs: " + method)
        group = []
        for item in prepared[method]:
            target = expected[item["question_id"]]
            final = set(item["prompt_table_ids"])
            retrieved = set(item["retrieved_table_ids"])
            valid = target["evaluable"]
            detail = {"method": method, "question_id": item["question_id"], "question": item["question"],
                      "expected": target, "category": "|".join(target["engines"]),
                      "predicted_engines": item["predicted_engines"],
                      "routing_correct": set(item["predicted_engines"]) == set(target["engines"]),
                      "prompt_status": item["status"], "prompt_table_ids": sorted(final),
                      "retrieved_table_ids": sorted(retrieved), "removed_by_char_budget": item["removed_by_char_budget"],
                      "excluded_table_ids": item["excluded_table_ids"],
                      "instruction_chars": item["instruction_chars"],
                      "retrieved_db_coverage": coverage(set(target["databases"]), {database_key(tables[t]) for t in retrieved}, valid),
                      "retrieved_table_coverage": coverage(set(target["table_ids"]), retrieved, valid),
                      "prompt_db_coverage": coverage(set(target["databases"]), {database_key(tables[t]) for t in final}, valid),
                      "prompt_table_coverage": coverage(set(target["table_ids"]), final, valid)}
            group.append(detail)
        summary[method] = {"overall": aggregate(group), "by_category": {
            category: aggregate([r for r in group if r["category"] == category])
            for category in sorted({r["category"] for r in group})},
            "run": runs[method]}
        details.extend(group)
        write_json(directory / method / "coverage.json", summary[method])
        write_jsonl(directory / method / "coverage_details.jsonl", group)
    write_json(directory / "comparison.json", {"manifest": manifest, "methods": summary})
    wide = []
    lookup = {(d["method"], d["question_id"]): d for d in details}
    for row in answers:
        entry = {"question_id": row["question_id"], "question": row["question"],
                 "category": "|".join(expected[row["question_id"]]["engines"]),
                 "reference_evaluable": expected[row["question_id"]]["evaluable"]}
        for method in METHODS:
            detail = lookup[method, row["question_id"]]
            for kind in ("db", "table"):
                entry[method + "_complete_" + kind] = detail["prompt_" + kind + "_coverage"]["complete"]
                entry[method + "_missing_" + kind] = ";".join(detail["prompt_" + kind + "_coverage"]["missing"])
        wide.append(entry)
    with (directory / "per_question_comparison.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(wide[0]))
        writer.writeheader()
        writer.writerows(wide)
    lines = ["# 三种预处理与最终提示词覆盖率", "",
             f"同一分层划分：训练 {manifest['training_rows']} 题，验证 {len(answers)} 题；seed={manifest['seed']}。",
             "三组共用纯CPU字符TF-IDF路由，防止路由差异混入预处理/检索差异。",
             f"候选表上限 {manifest['max_tables']}，官方DDL提示词上限 {manifest['max_instruction_chars']} 字符，整表裁剪。",
             "完整覆盖要求参考查询所需集合全部出现在最终提示词；允许额外库表，区别于集合完全相等。", "",
             "| 方法 | 完整业务库覆盖率 | 完整业务表覆盖率 | 裁剪前完整表覆盖率 |",
             "| --- | ---: | ---: | ---: |"]
    for method in METHODS:
        m = summary[method]["overall"]
        lines.append(f"| {method} | {m['prompt_complete_db_coverage_rate']:.2%} ({m['prompt_complete_db_count']}/{len(answers)}) | "
                     f"{m['prompt_complete_table_coverage_rate']:.2%} ({m['prompt_complete_table_count']}/{len(answers)}) | "
                     f"{m['retrieved_complete_table_coverage_rate']:.2%} |")
    lines += ["", "## 按数据源分组", "", "| 数据源 | 题数 | 方法 | 完整库覆盖 | 完整表覆盖 |", "| --- | ---: | --- | ---: | ---: |"]
    for category in summary[METHODS[0]]["by_category"]:
        display_category = category.replace("|", r"\|")
        for method in METHODS:
            m = summary[method]["by_category"][category]
            lines.append(f"| {display_category} | {m['count']} | {method} | {m['prompt_complete_db_coverage_rate']:.2%} | {m['prompt_complete_table_coverage_rate']:.2%} |")
    issues = [qid for qid, value in expected.items() if not value["evaluable"]]
    lines += ["", "## 口径与产物", "",
              "- programmatic：原有TF-IDF/字符/字段规则关联、训练SQL弱证据及BM25检索。",
              "- hybrid两组：全1833条知识竞争，各表RRF＋重排Top12作为实验候选归属；逐题也使用对应模型混合检索与重排。",
              "- 模型候选归属只用于本轮独立实验，不等于人工确认关联，不覆盖默认生产预处理。",
              "- 每组preprocessed/含原文目录、知识、文档和关联审计；index/含实际索引、文档和模型向量；prompts.jsonl为最终消息。",
              "- 复用现有DDL提示词流程，knowledge/examples参与召回，最终提示词不直接附加其全文。",
              "- coverage_details.jsonl及per_question_comparison.csv保存逐题缺失、预算裁剪和路由；contexts.jsonl保存召回证据。",
              "- 业务库按engine:namespace标识；Elasticsearch以唯一原始索引确定归属，未跳过ES题。",
              f"- 参考查询无法完整解析的题数：{len(issues)}；全量分母保留，保守计为未完整覆盖，不将空目标计为成功。",
              "- 验证SQL仅在三组提示词完成后解析评分；其内容未参与预处理、路由拟合、索引、检索或提示词。",
              f"- 删除与验证问题同文本的训练记录：{len(manifest['excluded_training_ids_with_validation_text'])}；划分ID仍保持冻结。",
              "- 同时改变知识候选归属和逐题检索，结果比较的是完整方案，不是单独某个组件的因果归因。",
              "- 仅衡量提示词证据覆盖，不调用SQL生成模型，不代表SQL正确率或执行正确率。", ""]
    (directory / "README.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({method: value["overall"] for method, value in summary.items()}, ensure_ascii=False, indent=2), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--max-tables", type=int, default=6)
    p.add_argument("--max-instruction-chars", type=int, default=16000)
    p = sub.add_parser("run")
    p.add_argument("--experiment-dir", type=Path, required=True)
    p.add_argument("--method", choices=METHODS, required=True)
    p.add_argument("--device", default="cuda:0")
    p.add_argument("--dtype", default="bfloat16", choices=("bfloat16", "float16"))
    p = sub.add_parser("score")
    p.add_argument("--experiment-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.output_dir.resolve(), seed=args.seed, max_tables=args.max_tables, max_chars=args.max_instruction_chars)
    elif args.command == "run":
        run_method(args.experiment_dir.resolve(), args.method, device=args.device, dtype=args.dtype)
    else:
        score(args.experiment_dir.resolve())


if __name__ == "__main__":
    main()
