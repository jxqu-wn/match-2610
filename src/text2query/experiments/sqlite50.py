"""SQLite 50 题微调模型实验。

流程：
1. 从划分后的验证集抽取 50 道 SQLite 单源题（固定种子，排除与训练集同文本的题）；
2. 路由：字符 TF-IDF + 逻辑回归分类器预测数据库系统；
3. 外部知识注入：仅使用划分后训练集构建的检索索引，召回候选库表并生成
   与微调训练一致的 instruction（官方 DDL 提示）；
4. 调用 OpenAI 兼容的微调模型生成 SQL；
5. 统计：数据库类型正确率、提示词完整业务库/业务表覆盖率、
   生成 SQL 的业务库/业务表正确率，并保存逐题对照供一致性复核。

验证答案只用于评分，不进入索引或提示词。
"""

from __future__ import annotations

import json
import random
import re
from pathlib import Path
from typing import Any

from ..config import settings
from ..io import get_logger, read_json, write_json, write_jsonl
from ..models import Catalog, Sample, Table
from ..retrieval.context import Budget, ContextBuilder
from ..retrieval.index import RetrievalIndex
from ..retrieval.sql_parser import SourceResolver
from ..routing.classifier import CharacterTfidfBaseline, label
from ..submission.finetuned import build_instruction, strip_fences

logger = get_logger(__name__)

DEFAULT_ENDPOINT = "http://192.168.15.119:8000/v1"
DEFAULT_MODEL = "qwen-track8-text2sql"


def _step_queries(row: dict[str, Any]) -> list[tuple[str, str]]:
    pairs = []
    if row.get("db"):
        pairs.append((row["db"], row["query"]))
    for index in range(1, 4):
        if row.get(f"db{index}"):
            pairs.append((row[f"db{index}"], row.get(f"query{index}", "")))
    return pairs


def expected_targets(row: dict[str, Any], resolver: SourceResolver) -> dict[str, Any]:
    """参考 SQL 解析出的系统、业务库与业务表。"""
    engines: set[str] = set()
    table_ids: set[str] = set()
    for engine, query in _step_queries(row):
        engines.add(engine)
        if engine == "Elasticsearch":
            continue
        parsed = resolver.parse(query, engine)
        table_ids.update(parsed["table_ids"])
    tables = resolver.tables
    databases = {tables[key].namespace for key in table_ids if tables[key].namespace}
    qualified = {_qualified(tables[key]) for key in table_ids}
    return {
        "engines": sorted(engines),
        "databases": sorted(databases),
        "tables": sorted(qualified),
        "table_ids": sorted(table_ids),
    }


def _qualified(table: Table) -> str:
    return f"{table.namespace}.{table.name}" if table.namespace else table.name


def _parse_generated(
    sql: str, engine: str, resolver: SourceResolver, tables: dict[str, Table], prompt_table_ids: list[str] = ()
) -> dict[str, Any]:
    try:
        parsed = resolver.parse(sql, engine)
    except Exception as error:  # noqa: BLE001 - 生成结果可能不是合法 SQL
        return {"parse_status": "error", "error": f"{type(error).__name__}: {error}", "table_ids": []}

    ids = set(parsed.get("table_ids", []))
    unresolved = list(parsed.get("unresolved_tables", []))
    if unresolved:
        # SQLite/MySQL 允许未限定表名；在引擎内唯一时按该表计，冲突时优先提示词中的表。
        by_name: dict[str, list[str]] = {}
        for table_id, table in tables.items():
            if table.engine == engine:
                by_name.setdefault(table.name.lower(), []).append(table_id)
        prompt = set(prompt_table_ids)
        remaining = []
        for token in unresolved:
            base = re.split(r"\s+as\s+", token, flags=re.I)[0].strip()
            name = base.strip('`"').split(".")[-1].lower()
            candidates = by_name.get(name, [])
            if len(candidates) == 1:
                ids.add(candidates[0])
                continue
            preferred = [candidate for candidate in candidates if candidate in prompt]
            if len(preferred) == 1:
                ids.add(preferred[0])
                continue
            remaining.append(token)
        unresolved = remaining
    status = parsed.get("parse_status")
    if status == "unresolved_tables" and not unresolved:
        status = "parsed_unqualified_resolved"
    return {
        **parsed,
        "parse_status": status,
        "table_ids": sorted(ids),
        "unresolved_tables": unresolved,
        "databases": sorted({tables[key].namespace for key in ids if tables[key].namespace}),
        "tables": sorted({_qualified(tables[key]) for key in ids}),
    }


def _set_metrics(expected: set[str], produced: set[str]) -> dict[str, Any]:
    intersection = expected & produced
    return {
        "exact": expected == produced,
        "recall": len(intersection) / len(expected) if expected else None,
        "precision": len(intersection) / len(produced) if produced else None,
        "missing": sorted(expected - produced),
        "extra": sorted(produced - expected),
    }


def sample_validation_rows(
    *, sample_size: int, seed: int, exclude_train_texts: bool = True
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    validation = read_json(settings.validation_split)
    train_texts = {row["question"] for row in read_json(settings.train_split)} if exclude_train_texts else set()
    sqlite_rows = [
        row for row in validation if _step_queries(row) and all(engine == "SQLite" for engine, _ in _step_queries(row))
    ]
    eligible = [row for row in sqlite_rows if row["question"] not in train_texts]
    rng = random.Random(seed)
    sample = rng.sample(eligible, min(sample_size, len(eligible)))
    sample.sort(key=lambda row: row["question_id"])
    audit = {
        "validation_sqlite_total": len(sqlite_rows),
        "eligible_after_train_text_exclusion": len(eligible),
        "excluded_train_duplicates": len(sqlite_rows) - len(eligible),
        "sample_size": len(sample),
        "seed": seed,
    }
    return sample, audit


def run(
    *,
    endpoint: str = DEFAULT_ENDPOINT,
    model: str = DEFAULT_MODEL,
    api_key: str | None = None,
    thinking: bool | None = None,
    sample_size: int = 50,
    seed: int = 42,
    max_tables: int = 6,
    max_instruction_chars: int = 16000,
    max_output_tokens: int = 768,
    workers: int = 4,
    output_dir: Path | None = None,
    recall: str = "retrieval",
) -> dict[str, Any]:
    import openai
    from concurrent.futures import ThreadPoolExecutor, as_completed

    output_dir = Path(output_dir) if output_dir else settings.path(f"outputs/experiments/sqlite{sample_size}")
    output_dir.mkdir(parents=True, exist_ok=True)

    catalog = Catalog.model_validate(read_json(settings.schema_catalog))
    tables = catalog.by_id()
    resolver = SourceResolver(tables)
    train_rows = read_json(settings.train_split)
    rows, sample_audit = sample_validation_rows(sample_size=sample_size, seed=seed)

    # 路由：离线字符 TF-IDF 逻辑回归（本地无 embedding 模型）。
    router = CharacterTfidfBaseline().fit(
        [row["question"] for row in train_rows], [label(Sample.model_validate(row)) for row in train_rows]
    )
    predicted_engines = router.predict([row["question"] for row in rows])

    # 外部知识注入：仅用划分后训练集构建检索索引。
    index_path = output_dir / "index_train_split"
    index = RetrievalIndex.build(
        index_path,
        encoder=None,
        training_source=settings.train_split,
        catalog=catalog,
        knowledge=read_json(settings.knowledge),
        train_rows=train_rows,
    )
    builder = ContextBuilder(index, Budget(initial_tables=max_tables))

    prepared: list[dict[str, Any]] = []
    for row, engine_label in zip(rows, predicted_engines):
        engines = engine_label.split("|")
        context = builder.assemble(row["question"], engines, row["question_id"])
        prompt_tables = [t["table_id"] for t in context["candidate_tables"]]
        # 遵守 8192 上下文：按召回顺序保留能装下的表。
        instruction = build_instruction(prompt_tables, tables)
        kept = list(prompt_tables)
        while len(instruction) > max_instruction_chars and kept:
            kept.pop()
            instruction = build_instruction(kept, tables)
        expected = expected_targets(row, resolver)
        prepared.append(
            {
                "row": row,
                "predicted_engines": engines,
                "prompt_table_ids": kept,
                "instruction": instruction,
                "expected": expected,
            }
        )
    logger.info("已准备 %d 题，开始调用 %s", len(prepared), model)

    client = openai.OpenAI(api_key=api_key or settings.api_key or "not-needed", base_url=endpoint)
    extra_body = None if thinking is None else {"thinking": {"type": "enabled" if thinking else "disabled"}}

    def generate(item: dict[str, Any]) -> dict[str, Any]:
        try:
            request: dict[str, Any] = {
                "model": model,
                "messages": [
                    {"role": "system", "content": item["instruction"]},
                    {"role": "user", "content": item["row"]["question"]},
                ],
                "temperature": 0,
                "max_tokens": max_output_tokens,
            }
            if extra_body is not None:
                request["extra_body"] = extra_body
            response = client.chat.completions.create(**request)
            choice = response.choices[0]
            content = choice.message.content or ""
            reasoning = getattr(choice.message, "reasoning_content", None)
            finish = choice.finish_reason
            usage = response.usage.model_dump() if response.usage else {}
        except Exception as error:  # noqa: BLE001 - 逐题记录失败
            content, reasoning, finish, usage = "", None, "error", {"error": f"{type(error).__name__}: {error}"}
        sql = strip_fences(content)
        engine = item["predicted_engines"][0] if len(item["predicted_engines"]) == 1 else "SQLite"
        generated = _parse_generated(sql, engine, resolver, tables, item["prompt_table_ids"])
        return {
            **item,
            "generated_sql": sql,
            "raw_output": content,
            "reasoning_content": reasoning,
            "finish_reason": finish,
            "usage": usage,
            "generated": generated,
        }

    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(generate, item) for item in prepared]
        for future in as_completed(futures):
            results.append(future.result())
            logger.info("完成 %d/%d", len(results), len(prepared))
    results.sort(key=lambda item: item["row"]["question_id"])

    details = []
    for item in results:
        expected = item["expected"]
        prompt_table_ids = item["prompt_table_ids"]
        prompt_dbs = {tables[key].namespace for key in prompt_table_ids if tables[key].namespace}
        prompt_tables = {_qualified(tables[key]) for key in prompt_table_ids}
        generated = item["generated"]
        details.append(
            {
                "question_id": item["row"]["question_id"],
                "question": item["row"]["question"],
                "reference_sql": item["row"].get("query", ""),
                "reference_engines": expected["engines"],                "predicted_engines": item["predicted_engines"],
                "engine_correct": expected["engines"] == item["predicted_engines"],
                "expected_databases": expected["databases"],
                "expected_tables": expected["tables"],
                "prompt_table_ids": prompt_table_ids,
                "prompt_databases": sorted(prompt_dbs),
                "prompt_tables": sorted(prompt_tables),
                "prompt_db_coverage": _set_metrics(set(expected["databases"]), prompt_dbs),
                "prompt_table_coverage": _set_metrics(set(expected["tables"]), prompt_tables),
                "generated_sql": item["generated_sql"],
                "raw_output": item.get("raw_output"),
                "generated_parse_status": generated.get("parse_status"),
                "generated_databases": generated.get("databases", []),
                "generated_tables": generated.get("tables", []),
                "generated_db_match": _set_metrics(set(expected["databases"]), set(generated.get("databases", []))),
                "generated_table_match": _set_metrics(set(expected["tables"]), set(generated.get("tables", []))),
                "finish_reason": item["finish_reason"],
                "usage": item["usage"],
                "reasoning_content": item.get("reasoning_content"),
            }
        )

    report = _aggregate(details, sample_audit, model, endpoint, max_tables)
    write_json(output_dir / "config.json", {"endpoint": endpoint, "model": model, "thinking": thinking, "seed": seed, "max_tables": max_tables, "recall": recall})
    write_json(output_dir / "sample.json", [row["question_id"] for row in rows])
    write_jsonl(output_dir / "results.jsonl", details)
    write_json(output_dir / "report.json", report)
    logger.info("报告：%s", json.dumps(report["metrics"], ensure_ascii=False))
    return report


def _mean(values: list[float | None]) -> float | None:
    present = [v for v in values if v is not None]
    return sum(present) / len(present) if present else None


def _aggregate(details: list[dict[str, Any]], sample_audit: dict[str, Any], model: str, endpoint: str, max_tables: int) -> dict[str, Any]:
    total = len(details)
    parseable = [
        d for d in details if d["generated_parse_status"] in ("parsed", "single_index_by_catalog", "parsed_unqualified_resolved")
    ]
    metrics = {
        "count": total,
        "engine_accuracy": _mean([1.0 if d["engine_correct"] else 0.0 for d in details]),
        "prompt_complete_db_coverage_rate": _mean([1.0 if not d["prompt_db_coverage"]["missing"] else 0.0 for d in details]),
        "prompt_complete_table_coverage_rate": _mean([1.0 if not d["prompt_table_coverage"]["missing"] else 0.0 for d in details]),
        "prompt_db_recall": _mean([d["prompt_db_coverage"]["recall"] for d in details]),
        "prompt_table_recall": _mean([d["prompt_table_coverage"]["recall"] for d in details]),
        "generated_parse_rate": len(parseable) / total if total else None,
        "generated_db_exact_rate": _mean([1.0 if d["generated_db_match"]["exact"] else 0.0 for d in details]),
        "generated_db_recall": _mean([d["generated_db_match"]["recall"] for d in details]),
        "generated_db_precision": _mean([d["generated_db_match"]["precision"] for d in details]),
        "generated_table_exact_rate": _mean([1.0 if d["generated_table_match"]["exact"] else 0.0 for d in details]),
        "generated_table_recall": _mean([d["generated_table_match"]["recall"] for d in details]),
        "generated_table_precision": _mean([d["generated_table_match"]["precision"] for d in details]),
    }
    return {
        "model": model,
        "endpoint": endpoint,
        "max_tables": max_tables,
        "sample_audit": sample_audit,
        "metrics": metrics,
        "per_question": details,
    }
