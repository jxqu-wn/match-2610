"""Sample held-out questions and rebuild LLM messages from frozen retrieval hits.

No routing/embedding/reranking/LLM call is repeated. Targets are parsed only after
all exported messages are complete, and never enter the LLM payloads.
"""

# ruff: noqa: E402 -- standalone evaluation entry point
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from text2query.data.split import split_samples, stratum_for
from text2query.experiments.prompt_coverage import (
    METHODS,
    aggregate,
    coverage,
    database_key,
    make_prompt,
    reference_targets,
)
from text2query.io import file_sha256, read_json, read_jsonl, write_json, write_jsonl
from text2query.models import Catalog, Sample
from text2query.retrieval.sql_parser import SourceResolver

SCOPES = ("corresponding_retrieval", "fixed_bm25")
NAMES = {"programmatic": "纯程序", "hybrid-8b": "8B", "hybrid-0.6b": "0.6B"}


def checked(parent: Path, relative: str, hashes: dict) -> Path:
    path = parent / relative
    if file_sha256(path) != hashes[relative]:
        raise ValueError("Parent artifact changed: " + relative)
    return path


def render_prompt(question_id: int, messages: list[dict]) -> str:
    sections = [f"# Question {question_id}", ""]
    for message in messages:
        sections += ["## " + message["role"], "", message["content"], ""]
    return "\n".join(sections)


def run(parent: Path, output: Path, size: int, seed: int) -> None:
    if output.exists():
        raise FileExistsError("Choose a new output directory")
    hashes = read_json(parent / "artifact_sha256.json")
    manifest = read_json(checked(parent, "manifest.json", hashes))
    public = read_json(checked(parent, "shared/questions.json", hashes))
    public_by_id = {row["question_id"]: row for row in public}
    validation_path = checked(parent, "shared/splits/validation.json", hashes)
    # Use only question fields and source strata for sampling, never query content.
    source_rows = read_json(validation_path)
    samples = [Sample.model_validate({k: v for k, v in row.items()
                                     if k in {"question_id", "question", "db", "db1", "db2", "db3"}})
               for row in source_rows]
    del source_rows
    if not 0 < size < len(samples):
        raise ValueError("Sample size must be between zero and the validation size")
    _, selected, positions = split_samples(samples, validation_ratio=size / len(samples), seed=seed)
    if len(selected) != size:
        raise ValueError("Requested sample size differs from stratified sample size")
    ids = [sample.question_id for sample in selected]
    selected_set = set(ids)
    questions = [public_by_id[qid] for qid in ids]
    output.mkdir(parents=True)
    write_json(output / "questions.json", questions)
    sample_manifest = {
        "parent": str(parent), "parent_manifest_sha256": file_sha256(parent / "manifest.json"),
        "parent_artifact_manifest_sha256": file_sha256(parent / "artifact_sha256.json"),
        "sample_size": size, "validation_size": len(samples), "seed": seed,
        "sampling": "existing stratified split_samples; original order; no outcome-based selection",
        "strata": dict(sorted(Counter(stratum_for(s) for s in selected).items())),
        "validation_positions": positions, "question_ids": ids,
        "max_tables": manifest["max_tables"], "max_instruction_chars": manifest["max_instruction_chars"],
        "source_artifacts": {},
        "generation": "rebuild DDL messages from each catalog and frozen retrieval hits; no model inference repeated",
        "scopes": {"corresponding_retrieval": "original corresponding full pipeline",
                   "fixed_bm25": "all three preprocessed datasets with identical BM25 question retrieval"},
        "llm_calls": 0,
    }
    routes = {r["question_id"]: r["predicted_engines"] for r in
              read_json(checked(parent, "shared/routing.json", hashes))}
    catalogs = {}
    metadata = {}
    exported = {}
    for method in METHODS:
        catalog_rel = f"{method}/preprocessed/schema_catalog.json"
        catalogs[method] = Catalog.model_validate(read_json(checked(parent, catalog_rel, hashes)))
        sample_manifest["source_artifacts"][catalog_rel] = hashes[catalog_rel]
    for scope in SCOPES:
        for method in METHODS:
            source = method if scope == "corresponding_retrieval" or method == "programmatic" else "controlled_bm25/" + method
            prompt_rel = source + "/prompts.jsonl"
            context_rel = source + "/contexts.jsonl"
            source_prompts = {r["question_id"]: r for r in read_jsonl(checked(parent, prompt_rel, hashes))
                              if r["question_id"] in selected_set}
            source_contexts = {r["question_id"]: r for r in read_jsonl(checked(parent, context_rel, hashes))
                               if r["question_id"] in selected_set}
            sample_manifest["source_artifacts"].update({p: hashes[p] for p in (prompt_rel, context_rel)})
            if set(source_prompts) != selected_set or set(source_contexts) != selected_set:
                raise ValueError("Missing selected questions in parent")
            folder = output / scope / method
            tables = catalogs[method].by_id()
            rows, evidence, markdown = [], [], []
            for question in questions:
                qid = question["question_id"]
                source_prompt, context = source_prompts[qid], source_contexts[qid]
                if source_prompt["question"] != question["question"] or source_prompt["predicted_engines"] != routes[qid]:
                    raise ValueError("Question or routing changed")
                keys = [table["table_id"] for table in context["candidate_tables"]]
                if keys != source_prompt["retrieved_table_ids"]:
                    raise ValueError("Frozen retrieval context differs from its prompt")
                prepared = make_prompt(question["question"], keys, tables, manifest["max_instruction_chars"])
                if prepared["messages"] != source_prompt["messages"] or prepared["prompt_table_ids"] != source_prompt["prompt_table_ids"]:
                    raise ValueError("Rebuilt LLM messages differ from parent: " + str(qid))
                item = {"question_id": qid, "messages": prepared["messages"]}
                rows.append(item)
                evidence.append({**question, "predicted_engines": routes[qid], "retrieved_table_ids": keys,
                                 **{k: v for k, v in prepared.items() if k != "messages"}})
                text = render_prompt(qid, item["messages"])
                path = folder / "prompts" / f"question_{qid}.md"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")
                markdown.append(text)
            write_jsonl(folder / "prompts.jsonl", rows)
            write_jsonl(folder / "retrieval_metadata.jsonl", evidence)
            (folder / "prompts.md").write_text("\n---\n\n".join(markdown), encoding="utf-8")
            exported[scope, method] = rows
            metadata[scope, method] = evidence
    # All 50-question payloads exist before inspecting any reference query.
    answers = {r["question_id"]: r for r in read_json(validation_path) if r["question_id"] in selected_set}
    targets = {qid: reference_targets(answers[qid], SourceResolver(catalogs["programmatic"].by_id())) for qid in ids}
    write_json(output / "evaluation/reference_targets.json", [{"question_id": qid, **targets[qid]} for qid in ids])
    results, details, wide = {}, {}, []
    for scope in SCOPES:
        results[scope] = {}
        for method in METHODS:
            group = []
            tables = catalogs[method].by_id()
            for evidence in metadata[scope, method]:
                qid = evidence["question_id"]
                target = targets[qid]
                detail = {"method": method, "question_id": qid, "question": evidence["question"],
                          "expected": target, "category": "|".join(target["engines"]),
                          "routing_correct": set(evidence["predicted_engines"]) == set(target["engines"]),
                          "predicted_engines": evidence["predicted_engines"], "prompt_status": evidence["status"],
                          "prompt_table_ids": evidence["prompt_table_ids"],
                          "instruction_chars": evidence["instruction_chars"],
                          "removed_by_char_budget": evidence["removed_by_char_budget"]}
                for stage, field in (("retrieved", "retrieved_table_ids"), ("prompt", "prompt_table_ids")):
                    actual = set(evidence[field])
                    detail[stage + "_table_coverage"] = coverage(set(target["table_ids"]), actual, target["evaluable"])
                    detail[stage + "_db_coverage"] = coverage(set(target["databases"]), {database_key(tables[k]) for k in actual}, target["evaluable"])
                group.append(detail)
                details[scope, method, qid] = detail
            results[scope][method] = {"overall": aggregate(group), "by_category": {
                category: aggregate([r for r in group if r["category"] == category])
                for category in sorted({r["category"] for r in group})}}
            write_jsonl(output / "evaluation" / scope / f"{method}.coverage_details.jsonl", group)
    for scope in SCOPES:
        for question in questions:
            qid = question["question_id"]
            row = {"scope": scope, **question, "expected_databases": ";".join(targets[qid]["databases"]),
                   "expected_tables": ";".join(targets[qid]["table_ids"])}
            for method in METHODS:
                for kind in ("db", "table"):
                    value = details[scope, method, qid]["prompt_" + kind + "_coverage"]
                    row[method + "_complete_" + kind] = value["complete"]
                    row[method + "_missing_" + kind] = ";".join(value["missing"])
            wide.append(row)
    with (output / "evaluation/per_question_comparison.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(wide[0]))
        writer.writeheader()
        writer.writerows(wide)
    write_json(output / "comparison.json", results)
    write_json(output / "sample_manifest.json", sample_manifest)
    validation = {
        "same_50_questions_for_every_method": all([r["question_id"] for r in rows] == ids for rows in exported.values()),
        "rebuilt_messages_equal_frozen_messages": True,
        "llm_payloads_contain_only_question_id_and_messages": all(set(r) == {"question_id", "messages"} for rows in exported.values() for r in rows),
        "reference_evaluable_count": sum(t["evaluable"] for t in targets.values()),
        "message_pairs": sum(len(rows) for rows in exported.values()),
        "no_empty_prompts": all(r["status"] == "prepared" for rows in metadata.values() for r in rows),
        "llm_calls": 0,
    }
    assert all(validation[k] for k in ("same_50_questions_for_every_method", "rebuilt_messages_equal_frozen_messages",
                                       "llm_payloads_contain_only_question_id_and_messages", "no_empty_prompts"))
    write_json(output / "verification.json", validation)
    lines = [f"# 验证集{size}题LLM提示词与覆盖率", "",
             f"从已冻结的{len(samples)}道验证题中按数据库系统与跨源方向分层抽取{size}题，seed={seed}，三组使用同一题单。",
             "抽样未根据覆盖结果筛题；原数据划分、训练侧去重、路由、表数上限及提示词预算保持一致。",
             "复用已完成的逐题检索排序，从三组预处理目录重新生成官方DDL system消息及原问题user消息，已逐条核对与冻结消息一致。",
             "此次没有重复运行Embedding/Reranker，也没有调用LLM生成答案。", "",
             "分层数量：" + "；".join(f"{key}: {value}" for key, value in sample_manifest["strata"].items()) + "。", ""]
    for scope, title in (("corresponding_retrieval", "沿用各组对应检索方案"), ("fixed_bm25", "统一BM25召回，仅比较预处理数据")):
        lines += ["## " + title, "", "| 预处理数据 | 完整业务库覆盖 | 完整业务表覆盖 | 提示词 |",
                  "| --- | ---: | ---: | --- |"]
        for method in METHODS:
            scores = results[scope][method]["overall"]
            lines.append(f"| {NAMES[method]} | {scores['prompt_complete_db_coverage_rate']:.2%} ({scores['prompt_complete_db_count']}/{size}) | "
                         f"{scores['prompt_complete_table_coverage_rate']:.2%} ({scores['prompt_complete_table_count']}/{size}) | "
                         f"[JSONL]({scope}/{method}/prompts.jsonl) · [Markdown]({scope}/{method}/prompts.md) |")
    lines += ["", "## 指标与使用", "",
              "完整覆盖要求参考查询所需的全部业务库／表都在最终提示词中，允许多召回；不等同于库表集合完全相等。",
              f"全部{validation['reference_evaluable_count']}/{size}道参考查询可完整解析；ES索引和跨源查询均参与评分。",
              "问题抽样与消息生成不使用参考查询内容；全部消息完成后才解析参考查询评分。",
              "prompts.jsonl每行仅包含question_id与messages；取messages作为LLM输入。prompts.md和prompts/question_<id>.md提供可阅读版本。",
              "参考目标和缺失明细仅保存在evaluation/，没有写入LLM消息。",
              "沿用已有微调DDL提示词格式：knowledge/examples影响召回，最终消息不直接附加知识和案例全文。",
              "此结果复用同一验证集已计算的检索证据，作为50题可检查样本，不是新增独立测试集。", "",
              "[抽样清单](sample_manifest.json) · [问题原文](questions.json) · [逐题覆盖差异](evaluation/per_question_comparison.csv) · [核对记录](verification.json)", ""]
    (output / "README.md").write_text("\n".join(lines), encoding="utf-8")
    source_target = output / "execution/sample_prompts.py"
    source_target.parent.mkdir(parents=True)
    source_target.write_bytes(Path(__file__).read_bytes())
    write_json(output / "artifact_sha256.json", {
        str(p.relative_to(output)): file_sha256(p) for p in sorted(output.rglob("*"))
        if p.is_file() and p.name != "artifact_sha256.json"
    })
    print(json.dumps({"sample": sample_manifest["strata"], "results": results, "verification": validation}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--size", type=int, default=50)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    run(args.parent_dir.resolve(), args.output_dir.resolve(), args.size, args.seed)
