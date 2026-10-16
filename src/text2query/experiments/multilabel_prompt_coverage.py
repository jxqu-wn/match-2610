"""Evaluate actual DDL prompts after substituting the frozen multilabel router.

Unchanged routes reuse exact frozen retrieval. Changed routes and their old-route
controls run local FP32 retrieval/reranking against the frozen document index.
Reference SQL is consumed by the separate score command after all prompts exist.
"""

from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path

import numpy as np

from ..config import settings
from ..io import canonical_json, file_sha256, read_json, read_jsonl, sha256_text, write_json, write_jsonl
from ..models import Catalog
from ..retrieval.context import Budget, ContextBuilder
from ..retrieval.embedding import retrieval_encoder
from ..retrieval.index import RetrievalIndex
from ..retrieval.ranking import RecallConfig, RerankerService
from ..retrieval.sql_parser import SourceResolver
from ..routing.embedding import EmbeddingService
from ..routing.multilabel import SemanticMultiLabelRouter
from .multilabel_routing import evaluation_subsets
from .prompt_coverage import aggregate, coverage, database_key, make_prompt, reference_targets

DEFAULT_OUTPUT = Path("outputs/experiments/semantic-multilabel-prompt-coverage-v1")


class ResumableScores:
    """Local inference cache; historical GPU logits are never mixed into a pool."""

    def __init__(self, service, directory: Path):
        self.service, self.signature = service, service.signature
        self.prefix = sha256_text(canonical_json(self.signature))
        directory.mkdir(parents=True, exist_ok=True)
        meta = directory / "signature.json"
        if meta.exists() and read_json(meta) != self.signature:
            raise ValueError("Reranker signature changed; choose a new output directory")
        write_json(meta, self.signature)
        self.path = directory / "scores.jsonl"
        self.cache = {r["key"]: r["score"] for r in read_jsonl(self.path)} if self.path.exists() else {}
        self.computed = self.hits = 0

    def score(self, query: str, documents: list[str]) -> list[float]:
        keys = [sha256_text(canonical_json([self.prefix, query, document])) for document in documents]
        missing = {key: document for key, document in zip(keys, documents, strict=True) if key not in self.cache}
        self.hits += len(keys) - len(missing)
        if missing:
            scores = self.service.score(query, list(missing.values()))
            if len(scores) != len(missing) or not np.isfinite(scores).all():
                raise ValueError("Invalid local reranker scores")
            with self.path.open("a", encoding="utf-8") as stream:
                for key, value in zip(missing, scores, strict=True):
                    self.cache[key] = float(value)
                    stream.write(json.dumps({"key": key, "score": float(value)}) + "\n")
            self.computed += len(scores)
            print(json.dumps({"local_reranker_pairs": self.computed, "cache_hits": self.hits}), flush=True)
        return [self.cache[key] for key in keys]


def checked_inputs(args: argparse.Namespace) -> dict:
    hashes = read_json(args.parent / "artifact_sha256.json")
    names = (
        "shared/questions.json",
        "shared/routing.json",
        "shared/retrieval_train.json",
        "shared/splits/validation.json",
        "hybrid-0.6b/prompts.jsonl",
        "hybrid-0.6b/contexts.jsonl",
        "hybrid-0.6b/preprocessed/schema_catalog.json",
        "hybrid-0.6b/index/documents.jsonl",
        "hybrid-0.6b/index/vectors.npz",
        "hybrid-0.6b/index/manifest.json",
    )
    result = {}
    for name in names:
        value = file_sha256(args.parent / name)
        if value != hashes[name]:
            raise ValueError("Frozen input changed: " + name)
        result["parent/" + name] = value
    router_hashes = read_json(args.router_run / "artifact_sha256.json")
    for name in ("semantic_multilabel/classifier.joblib", "semantic_multilabel/encoder_settings.json", "vectors.npz"):
        value = file_sha256(args.router_run / name)
        if value != router_hashes[name]:
            raise ValueError("Frozen router input changed: " + name)
        result["router/" + name] = value
    return result


def public_routes(args: argparse.Namespace) -> tuple[list[dict], dict[int, list[str]], dict[int, list[str]]]:
    questions = read_json(args.parent / "shared/questions.json")
    if any(set(row) != {"question_id", "question"} for row in questions):
        raise ValueError("Generation accepts public question fields only")
    old = {r["question_id"]: r["predicted_engines"] for r in read_json(args.parent / "shared/routing.json")}
    signature = read_json(args.router_run / "semantic_multilabel/encoder_settings.json")
    embedder = EmbeddingService(
        model_path=signature["model_path"],
        instruction=signature["instruction"],
        device=signature["device"],
        dtype=signature["dtype"],
        max_length=signature["max_length"],
        cache_dir=args.output / "routing_cache",
    )
    router = SemanticMultiLabelRouter.load(args.router_run / "semantic_multilabel", embedder)
    with np.load(args.router_run / "vectors.npz", allow_pickle=False) as saved:
        positions = {int(qid): i for i, qid in enumerate(saved["question_ids"])}
        vectors = saved["vectors"][[positions[r["question_id"]] for r in questions]]
    predicted = router.predict_vectors(vectors)
    return questions, old, {r["question_id"]: value.split("|") for r, value in zip(questions, predicted, strict=True)}


def generate(args: argparse.Namespace) -> None:
    hashes = checked_inputs(args)
    output = args.output
    if (output / "run.json").exists():
        raise FileExistsError("Prompts already frozen; choose a new directory")
    questions, old, new = public_routes(args)
    changed = [r for r in questions if set(old[r["question_id"]]) != set(new[r["question_id"]])]
    settings.embedding_model = settings.path("../models/Qwen3-Embedding-0.6B")
    encoder = retrieval_encoder(
        model_path=settings.embedding_model,
        device="cpu",
        dtype="float32",
        batch_size=4,
        max_length=512,
        cache_dir=output / "retrieval_query_cache",
    )
    service = RerankerService(
        settings.path("../models/Qwen3-Reranker-0.6B"), device="cpu", dtype="float32", batch_size=2, max_length=2048
    )
    manifest = {
        "parent": str(args.parent.resolve()),
        "router_run": str(args.router_run.resolve()),
        "input_sha256": hashes,
        "cases": len(questions),
        "changed_ids": [r["question_id"] for r in changed],
        "reuse_count": len(questions) - len(changed),
        "max_tables": 6,
        "max_instruction_chars": 16000,
        "recall": RecallConfig().as_dict(),
        "query_encoder": encoder.signature,
        "reranker": service.signature,
        "document_vectors": "frozen GPU BF16-produced, normalized FP32 document vectors",
        "changed_retrieval": "new CPU FP32 queries and fresh CPU FP32 logits, including old-route paired controls",
        "reference_isolation": "only question text, saved router, training index and frozen retrieval; SQL read by score only",
    }
    path = output / "manifest.json"
    if path.exists() and read_json(path) != manifest:
        raise ValueError("Run inputs changed; choose a new directory")
    write_json(path, manifest)
    write_json(output / "questions.json", questions)
    write_json(
        output / "routes.json", [{**r, "old": old[r["question_id"]], "new": new[r["question_id"]]} for r in questions]
    )
    catalog = Catalog.model_validate(read_json(args.parent / "hybrid-0.6b/preprocessed/schema_catalog.json"))
    documents = read_jsonl(args.parent / "hybrid-0.6b/index/documents.jsonl")
    with np.load(args.parent / "hybrid-0.6b/index/vectors.npz", allow_pickle=False) as stored:
        if stored["source_ids"].tolist() != [d["source_id"] for d in documents]:
            raise ValueError("Document vectors are not aligned")
        document_vectors = stored["vectors"]
    frozen_prompts = {r["question_id"]: r for r in read_jsonl(args.parent / "hybrid-0.6b/prompts.jsonl")}
    frozen_contexts = {r["question_id"]: r for r in read_jsonl(args.parent / "hybrid-0.6b/contexts.jsonl")}
    scores = ResumableScores(service, output / "local_reranker")
    started = time.perf_counter()
    try:
        if changed:
            encoder.encode([r["question"] for r in changed])
            encoder.unload()
        index = RetrievalIndex(documents, encoder, document_vectors, recall_config=RecallConfig(), reranker=scores)
        builder = ContextBuilder(index, Budget(initial_tables=6, total_tables=12))
        for row in changed:
            qid = row["question_id"]
            folder = output / "cases" / str(qid)
            for label, route in (("old_control", old[qid]), ("new", new[qid])):
                if (folder / f"{label}_prompt.json").exists() and (folder / f"{label}_context.json").exists():
                    continue
                print(json.dumps({"question_id": qid, "phase": label, "engines": route}), flush=True)
                context = builder.assemble(row["question"], route, qid)
                keys = [table["table_id"] for table in context["candidate_tables"]]
                prompt = {
                    **row,
                    "predicted_engines": route,
                    "retrieved_table_ids": keys,
                    **make_prompt(row["question"], keys, catalog.by_id(), 16000),
                }
                write_json(folder / f"{label}_context.json", context)
                write_json(folder / f"{label}_prompt.json", prompt)
            control = read_json(folder / "old_control_prompt.json")
            original = frozen_prompts[qid]
            write_json(
                folder / "control_reproduction.json",
                {
                    "same_prompt_table_set": set(control["prompt_table_ids"]) == set(original["prompt_table_ids"]),
                    "same_prompt_table_order": control["prompt_table_ids"] == original["prompt_table_ids"],
                    "same_messages": control["messages"] == original["messages"],
                    "same_retrieved_table_set": set(control["retrieved_table_ids"])
                    == set(original["retrieved_table_ids"]),
                    "original_prompt_table_ids": original["prompt_table_ids"],
                    "local_prompt_table_ids": control["prompt_table_ids"],
                },
            )
        prompts, contexts = [], []
        for row in questions:
            qid = row["question_id"]
            if set(old[qid]) == set(new[qid]):
                prompt, context = frozen_prompts[qid], frozen_contexts[qid]
                rebuilt = make_prompt(row["question"], prompt["retrieved_table_ids"], catalog.by_id(), 16000)
                if rebuilt["messages"] != prompt["messages"]:
                    raise ValueError("Unchanged prompt no longer reproduces frozen DDL")
            else:
                prompt = read_json(output / "cases" / str(qid) / "new_prompt.json")
                context = read_json(output / "cases" / str(qid) / "new_context.json")
            prompts.append(prompt)
            contexts.append(context)
        write_jsonl(output / "prompts.jsonl", prompts)
        write_jsonl(output / "contexts.jsonl", contexts)
        write_jsonl(
            output / "llm_messages.jsonl",
            [{"question_id": p["question_id"], "messages": p["messages"]} for p in prompts],
        )
        write_json(
            output / "run.json",
            {
                "prepared": len(prompts),
                "changed_retrieved": len(changed),
                "exact_frozen_reuse": len(questions) - len(changed),
                "elapsed_seconds": time.perf_counter() - started,
                "reranker_new_pairs": scores.computed,
                "reranker_cache_hits": scores.hits,
                "prompts_sha256": file_sha256(output / "prompts.jsonl"),
                "stats": index.stats,
            },
        )
    finally:
        encoder.unload()
        service.unload()
    print(json.dumps(read_json(output / "run.json")), flush=True)


def score_rows(prompts: list[dict], targets: dict, tables: dict) -> list[dict]:
    details = []
    for item in prompts:
        target = targets[item["question_id"]]
        retrieved, final = set(item["retrieved_table_ids"]), set(item["prompt_table_ids"])
        row = {
            "question_id": item["question_id"],
            "question": item["question"],
            "expected": target,
            "category": "|".join(target["engines"]),
            "predicted_engines": item["predicted_engines"],
            "routing_correct": set(item["predicted_engines"]) == set(target["engines"]),
            "prompt_status": item["status"],
            "prompt_table_ids": sorted(final),
            "retrieved_table_ids": sorted(retrieved),
            "removed_by_char_budget": item["removed_by_char_budget"],
            "instruction_chars": item["instruction_chars"],
        }
        for stage, keys in (("retrieved", retrieved), ("prompt", final)):
            row[stage + "_db_coverage"] = coverage(
                set(target["databases"]), {database_key(tables[t]) for t in keys}, target["evaluable"]
            )
            row[stage + "_table_coverage"] = coverage(set(target["table_ids"]), keys, target["evaluable"])
        details.append(row)
    return details


def score(args: argparse.Namespace) -> None:
    output = args.output
    run = read_json(output / "run.json")
    if file_sha256(output / "prompts.jsonl") != run["prompts_sha256"]:
        raise ValueError("Generated prompt artifact changed")
    questions = read_json(output / "questions.json")
    prepared = read_jsonl(output / "prompts.jsonl")
    if run["prepared"] != len(questions) or [r["question_id"] for r in prepared] != [
        r["question_id"] for r in questions
    ]:
        raise ValueError("Score only after all public questions have prompts")
    if checked_inputs(args) != read_json(output / "manifest.json")["input_sha256"]:
        raise ValueError("Scoring inputs differ from the generated prompts")
    references = read_json(args.parent / "shared/splits/validation.json")
    tables = Catalog.model_validate(read_json(args.parent / "hybrid-0.6b/preprocessed/schema_catalog.json")).by_id()
    resolver = SourceResolver(tables)
    targets = {r["question_id"]: reference_targets(r, resolver) for r in references}
    baseline = score_rows(read_jsonl(args.parent / "hybrid-0.6b/prompts.jsonl"), targets, tables)
    current = score_rows(prepared, targets, tables)
    groups, _ = evaluation_subsets(references, resolver)
    summary = {
        "old_router": aggregate(baseline),
        "semantic_multilabel": aggregate(current),
        "by_category": {
            category: {
                "old_router": aggregate([r for r in baseline if r["category"] == category]),
                "semantic_multilabel": aggregate([r for r in current if r["category"] == category]),
            }
            for category in sorted({r["category"] for r in current})
        },
        "subgroups": {
            name: {
                "old_router": aggregate([baseline[i] for i in ids]),
                "semantic_multilabel": aggregate([current[i] for i in ids]),
            }
            for name, ids in groups.items()
        },
        "changed_ids": read_json(output / "manifest.json")["changed_ids"],
        "controls": {
            str(qid): read_json(output / "cases" / str(qid) / "control_reproduction.json")
            for qid in read_json(output / "manifest.json")["changed_ids"]
        },
        "unresolved_references": [qid for qid, t in targets.items() if not t["evaluable"]],
        "execution_accuracy": None,
    }
    write_json(output / "summary.json", summary)
    write_jsonl(output / "evaluation/details.jsonl", current)
    write_json(
        output / "evaluation/missing_tables.json", [r for r in current if not r["prompt_table_coverage"]["complete"]]
    )
    write_json(output / "evaluation/reference_targets.json", targets)
    changed = []
    for old, new in zip(baseline, current, strict=True):
        if new["question_id"] in summary["changed_ids"]:
            changed.append({"question_id": new["question_id"], "old": old, "new": new})
    write_json(output / "evaluation/changed_cases.json", changed)
    with (output / "evaluation/overview.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        fields = (
            "question_id",
            "category",
            "old_db_complete",
            "new_db_complete",
            "old_table_complete",
            "new_table_complete",
            "missing_tables",
        )
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for old, new in zip(baseline, current, strict=True):
            writer.writerow(
                dict(
                    zip(
                        fields,
                        (
                            new["question_id"],
                            new["category"],
                            old["prompt_db_coverage"]["complete"],
                            new["prompt_db_coverage"]["complete"],
                            old["prompt_table_coverage"]["complete"],
                            new["prompt_table_coverage"]["complete"],
                            ";".join(new["prompt_table_coverage"]["missing"]),
                        ),
                        strict=True,
                    )
                )
            )
    lines = [
        "# 多标签路由后的实际提示词覆盖率",
        "",
        "相同冻结验证集、0.6B预处理与索引；上限6表、16000字符官方DDL提示词。",
        "",
        "| 方法 | 完整业务库覆盖 | 完整业务表覆盖 |",
        "| --- | ---: | ---: |",
    ]
    for name in ("old_router", "semantic_multilabel"):
        m = summary[name]
        lines.append(
            f"| {name} | {m['prompt_complete_db_count']}/{m['count']}（{m['prompt_complete_db_coverage_rate']:.2%}） | "
            f"{m['prompt_complete_table_count']}/{m['count']}（{m['prompt_complete_table_coverage_rate']:.2%}） |"
        )
    lines += [
        "",
        "## 联查子集",
        "",
        "| 子集 | 方法 | 题数 | 完整业务库 | 完整业务表 |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for group, values in summary["subgroups"].items():
        for name, m in values.items():
            lines.append(
                f"| {group} | {name} | {m['count']} | {m['prompt_complete_db_count']} | {m['prompt_complete_table_count']} |"
            )
    lines += [
        "",
        "## 口径",
        "",
        "完整覆盖要求参考所需集合全部出现在实际消息中的DDL，允许额外库表；这是提示词证据覆盖，不是SQL执行正确率。",
        "279题路由未变，逐字复用冻结消息；5题按公共问题和新路由重新执行BM25＋向量→RRF→0.6B重排。"
        "这5题的旧路由同时重跑，控制结果见summary.json；CPU FP32查询/重排与原GPU BF16存在数值环境差异，"
        "文档向量保留冻结版本，没有把历史GPU logits混入新评分池。",
        "参考SQL仅在全部284份提示词准备完毕后解析；未发送LLM，也未执行数据库。该验证集为已使用过的开发集。",
        "",
        "[实际LLM消息](llm_messages.jsonl) · [完整元数据](prompts.jsonl) · [汇总](summary.json) · "
        "[逐题CSV](evaluation/overview.csv) · [剩余缺表](evaluation/missing_tables.json) · [5题变化](evaluation/changed_cases.json)",
        "",
    ]
    (output / "README.md").write_text("\n".join(lines), encoding="utf-8")
    print(
        json.dumps(
            {name: summary[name] for name in ("old_router", "semantic_multilabel")}, ensure_ascii=False, indent=2
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("generate", "score"))
    parser.add_argument("--parent", type=Path, default=Path("outputs/experiments/preprocessing-prompt-coverage-v1"))
    parser.add_argument("--router-run", type=Path, default=Path("outputs/experiments/semantic-multilabel-routing-v1"))
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    {"generate": generate, "score": score}[args.command](args)


if __name__ == "__main__":
    main()
