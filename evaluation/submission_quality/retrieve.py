"""GPU-only candidate pools. Inputs contain questions/schema/knowledge/train only."""

from __future__ import annotations

import argparse
import copy
from pathlib import Path

import numpy as np

from text2query.experiments.multilabel_prompt_coverage import ResumableScores
from text2query.io import file_sha256, read_json, read_jsonl, write_json
from text2query.retrieval.embedding import retrieval_encoder
from text2query.retrieval.index import RetrievalIndex
from text2query.retrieval.ranking import RecallConfig, RerankerService
from text2query.submission.evidence import fk_candidates, knowledge_scope


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--public", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--models", required=True, type=Path)
    parser.add_argument("--vectors", required=True, type=Path)
    parser.add_argument("--question-set", choices=["validation", "official"], default="validation")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    documents = read_jsonl(args.public / "documents.jsonl")
    questions = read_json(args.public / "questions.json")
    if any(set(row) != {"question_id", "question"} for row in questions):
        raise ValueError("Only public questions accepted")
    validation_ids = {row["question_id"] for row in questions}
    training_ids = {doc["data"]["question_id"] for doc in documents if doc["kind"] == "example"}
    if args.question_set == "validation" and validation_ids & training_ids:
        raise ValueError("Validation leakage in training documents")
    encoder = retrieval_encoder(model_path=args.models / "Qwen3-Embedding-0.6B", device="cuda:0", dtype="bfloat16",
                                batch_size=32, max_length=512, cache_dir=args.output / "embedding_cache")
    service = RerankerService(args.models / "Qwen3-Reranker-0.6B", device="cuda:0", dtype="bfloat16",
                              batch_size=8, max_length=2048)
    vector_manifest = read_json(args.vectors.parent / "runtime_manifest.json")
    if vector_manifest["embedding"] != encoder.signature:
        raise ValueError("Frozen document vectors use a different embedding model/protocol")
    scores = ResumableScores(service, args.output / "reranker_cache")
    with np.load(args.vectors, allow_pickle=False) as saved:
        if saved["source_ids"].tolist() != [doc["source_id"] for doc in documents]:
            raise ValueError("Vector/document alignment changed")
        vectors = saved["vectors"]
    encoder.encode([row["question"] for row in questions])
    encoder.unload()
    config = RecallConfig(50, 50, 60, 50, True)
    base = RetrievalIndex(documents, encoder, vectors, recall_config=config, reranker=scores)
    eligible = []
    for document in documents:
        if document["kind"] == "knowledge":
            policy = knowledge_scope(document["text"], base.tables)
            eligible.append({"source_id": document["source_id"], **policy})
    global_docs = copy.deepcopy(documents)
    eligibility = {row["source_id"]: row for row in eligible}
    for item in global_docs:
        if item["kind"] == "knowledge":
            item["engines"] = ["MYSQL", "POSTGRESQL", "Elasticsearch"] if eligibility[item["source_id"]]["eligible"] else []
            item["table_ids"] = []
    global_index = RetrievalIndex(global_docs, encoder, vectors, recall_config=config, reranker=scores)
    write_json(args.output / "knowledge_scope_audit.json", eligible)
    write_json(args.output / "runtime.json", {"embedding": encoder.signature, "reranker": service.signature,
               "questions_sha256": file_sha256(args.public / "questions.json"),
               "documents_sha256": file_sha256(args.public / "documents.jsonl"),
               "vectors_sha256": file_sha256(args.vectors), "gpu_required": True,
               "train_examples": len(training_ids), "question_set": args.question_set,
               "validation_ids_excluded": args.question_set == "validation"})
    engines = ["MYSQL", "POSTGRESQL", "Elasticsearch"]
    for i, row in enumerate(questions, 1):
        path = args.output / "pools" / f"{row['question_id']}.json"
        if path.exists():
            if read_json(path)["row"] != row:
                raise ValueError("Question ID reused with different text; use an isolated output directory")
            continue
        query = row["question"]
        tables = base.search(query, "schema", engines, 24)
        knowledge = global_index.search(query, "knowledge", engines, 48)
        examples = base.search(query, "example", engines, 4)
        positions = [position for position, document in enumerate(documents) if document["kind"] == "example"]
        lexical = base._lexical_scores(query, positions)
        lexical_examples = [{"source_id": documents[position]["source_id"], "score": lexical[position],
                             "ranking_method": "bm25_auxiliary_training_example"}
                            for position in sorted(lexical, key=lambda index: (-lexical[index], documents[index]["source_id"]))[:6]]
        write_json(path, {"row": row, "tables": tables, "knowledge": knowledge, "examples": examples,
                         "lexical_examples": lexical_examples,
                         "fk_candidates": fk_candidates([hit["table_ids"][0] for hit in tables[:8]], base.tables)})
        if i % 10 == 0 or i == len(questions):
            print({"completed": i, "total": len(questions), "new_rerank_pairs": scores.computed}, flush=True)
    encoder.unload()
    service.unload()
    write_json(args.output / "complete.json", {"questions": len(questions), "new_rerank_pairs": scores.computed,
                                              "cache_hits": scores.hits})


if __name__ == "__main__":
    main()
