"""端到端生成 result.json：训练集重训分类器 + 全量检索索引 + LLM 生成。

- 路由：全量 ``QA_train.json`` 训练逻辑回归；
- 召回：全量训练集独立索引（含原分割验证子集，这是官方测试推理允许的训练数据）；
- 生成：逐题最多 4 次生成/修复/补充调用，静态校验后落盘，支持断点续跑。

不执行数据库查询，不读取任何测试答案。补充 schema 只来自已有 catalog。
"""

from __future__ import annotations

import json
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from rank_bm25 import BM25Okapi
from sklearn.linear_model import LogisticRegression

from ..config import settings
from ..io import file_sha256, get_logger, read_json, sha256_text, write_json
from ..llm.client import ChatClient
from ..models import Catalog
from ..retrieval.context import ContextBuilder
from ..retrieval.embedding import retrieval_encoder
from ..retrieval.index import RetrievalIndex, tokenize
from ..routing.classifier import label
from ..routing.embedding import EmbeddingService
from .prompts import with_query_rules
from .validate import validate_answer

logger = get_logger(__name__)

MODEL = "deepseek-v4-pro"
TRAINING_SOURCE = "data/赛题8/QA_train.json"
BASE_SYSTEM = """根据提供的问题、schema、原始知识和训练案例生成最终可执行查询。仅返回JSON对象：
{"status":"complete","answer":{"question_id":原ID,"db":"数据库系统","query":"查询字符串"},"requirements":[{"requirement":"题目的一项要求","tables":["table_id"],"columns":["字段"]}],"assumptions":[]}。
跨系统查询answer使用db1/query1、db2/query2，必要时db3/query3；后续查询以result代替前一步执行结果。单系统跨业务库仍使用db/query。
跨系统完整answer格式示例：{"question_id":原ID,"db1":"MYSQL","query1":"真实的第一步SELECT语句","db2":"POSTGRESQL","query2":"真实的第二步SELECT语句，其中引用result"}。禁止MYSQL/POSTGRESQL之类组合db值，禁止以db1/query1等占位文字代替真实查询。
SQL数据库系统名仅MYSQL、POSTGRESQL、SQLite；Elasticsearch的query为JSON DSL字符串。SQL使用schema中的真实库表与字段，按对应方言引用特殊标识符；仅生成读取查询，不执行查询。SQLite表使用业务库.表名限定，MySQL同理；PostgreSQL使用schema.表名。
逐项覆盖输出、过滤、日期、分组、统计对象、去重及引用方向，检查统计粒度、必要连接、分母和排序。每张最终表必须承担需求或必要关联任务，不能因存在外键就添加连接。不要遗漏仅用于条件的字段。训练案例不是保证正确的答案，先检查问题差异；不得编造schema字段。优先采用已有明确知识，冲突或问题歧义在assumptions中如实记录，仍给出最有依据的查询，不把明确未满足的要求当成假设。
如果缺少必要schema，不猜表字段，返回{"status":"need_more_evidence","search_queries":["具体检索词"],"engines":["系统名"],"reason":"缺少的需求"}。分类和候选排序不是业务正确性证明。不得输出Markdown。"""
SYSTEM = with_query_rules(BASE_SYSTEM)

MAX_INPUT_TOKENS = 21000
MAX_OUTPUT_TOKENS = 3000
MAX_ATTEMPTS = 4
MAX_ADDED_TABLES = 12


def _tokenizer():
    try:
        from transformers import AutoTokenizer

        return AutoTokenizer.from_pretrained(settings.embedding_model, local_files_only=True)
    except Exception:  # noqa: BLE001 - 退回字节估算
        return None


class InputEstimator:
    def __init__(self) -> None:
        self.tokenizer = _tokenizer()

    def __call__(self, messages: list[dict[str, str]]) -> int:
        if self.tokenizer is not None:
            return math.ceil(1.2 * sum(len(self.tokenizer.encode(m["content"])) + 8 for m in messages)) + 256
        return sum(len(m["content"].encode("utf-8")) + 64 for m in messages) + 64


def schema_fallback(catalog: Catalog) -> list[dict[str, Any]]:
    """紧凑 schema，仅结构，不含验证/测试答案。"""
    return [
        {
            "table_id": table.table_id,
            "engine": table.engine,
            "description": table.description,
            "columns": [[c.name, c.data_type, c.description] for c in table.columns],
            "primary_key": table.primary_key,
            "foreign_keys": [fk.model_dump() for fk in table.foreign_keys],
        }
        for table in catalog.tables
    ]


class SchemaKeywordSearch:
    def __init__(self, fallback: list[dict[str, Any]]) -> None:
        self.fallback = fallback
        corpus = [tokenize(json.dumps(item, ensure_ascii=False)) for item in fallback]
        self.bm25 = BM25Okapi(corpus) if any(corpus) else None

    def rank(self, query: str) -> list[dict[str, Any]]:
        if self.bm25 is None:
            return list(self.fallback)
        scores = self.bm25.get_scores(tokenize(query))
        order = sorted(range(len(self.fallback)), key=lambda i: (-scores[i], self.fallback[i]["table_id"]))
        return [self.fallback[i] for i in order]


def train_router(rows: list[dict[str, Any]], directory: Path, **embedding_kwargs: Any) -> tuple[Any, EmbeddingService]:
    directory.mkdir(parents=True, exist_ok=True)
    embedder = EmbeddingService(instruction=settings.routing_instruction, **embedding_kwargs)
    vectors = embedder.encode([row["question"] for row in rows])
    classifier = LogisticRegression(C=10.0, max_iter=2000, random_state=42)
    classifier.fit(vectors, [label(_sample(row)) for row in rows])
    import joblib

    joblib.dump({"estimator": classifier, "method": "logistic_C10.0; refit on full QA_train"}, directory / "classifier.joblib")
    write_json(
        directory / "summary.json",
        {
            "training_source": TRAINING_SOURCE,
            "training_size": len(rows),
            "encoder_settings": embedder.signature,
            "method": "logistic_C10.0; refit on full QA_train",
        },
    )
    return classifier, embedder


def _sample(row: dict[str, Any]) -> Any:
    from ..models import Sample

    return Sample.model_validate(row)


def prepare(
    rows: list[dict[str, Any]], directory: Path, *, index_path: Path | None = None, **embedding_kwargs: Any
) -> None:
    catalog = Catalog.model_validate(read_json(settings.schema_catalog))
    train_rows = read_json(settings.qa_train)
    train = {row["question_id"]: row for row in train_rows}
    route_path = directory / "routing_full_train"
    index_path = index_path or directory / "index_full_train"

    classifier, embedder = train_router(train_rows, route_path, **embedding_kwargs)
    test_vectors = embedder.encode([row["question"] for row in rows])
    labels = classifier.predict(test_vectors)

    encoder = retrieval_encoder(instruction=settings.retrieval_instruction, **embedding_kwargs)
    if (index_path / "manifest.json").exists():
        index = RetrievalIndex.load(index_path, encoder, training_source=settings.qa_train)
    else:
        index = RetrievalIndex.build(
            index_path,
            encoder,
            training_source=settings.qa_train,
            catalog=catalog,
            knowledge=read_json(settings.knowledge),
            train_rows=train_rows,
        )
    builder = ContextBuilder(index)
    index.encoder.encode([row["question"] for row in rows])
    for row, prediction in zip(rows, labels, strict=True):
        target = directory / f"prepared_{row['question_id']}.json"
        if target.exists():
            continue
        context = builder.assemble(row["question"], str(prediction).split("|"), row["question_id"])
        context, _ = builder.fit(context, SYSTEM)
        write_json(target, {"question": row, "context": context})
        logger.info("prepared %s", row["question_id"])

    indexed = {d["data"]["question_id"] for d in index.documents if d["kind"] == "example"}
    if indexed != set(train):
        raise ValueError("索引案例与训练集不一致")
    write_json(
        directory / "leakage_audit.json",
        {
            "training_source": TRAINING_SOURCE,
            "index_examples_full_training_only": True,
            "train_examples": len(train),
            "indexed_examples": len(indexed),
            "test_answers_available": False,
            "test_questions": len(rows),
        },
    )
    write_json(directory / "schema_fallback.json", schema_fallback(catalog))


def _resume(directory: Path, row: dict[str, Any], resolver: Any, model: str = MODEL) -> dict[str, Any] | None:
    target = directory / f"question_{row['question_id']}.json"
    if not target.exists():
        return None
    old = read_json(target)
    if old.get("model") == model and old.get("question") == row and not validate_answer(old.get("answer"), row, resolver):
        return old
    return None


def _failure_witnesses(directory: Path, errors: list[str], tables: dict[str, Any]) -> list[dict[str, Any]]:
    names = {
        e.rsplit(".", 1)[-1]
        for e in errors
        if e.startswith("未知限定字段") or e.startswith("Unknown qualified column")
    }
    history = directory / "retry_history"
    for path in sorted(history.glob("*.json")) if history.exists() else []:
        try:
            prior = read_json(path)
        except ValueError:
            continue
        for item in prior.get("trace", []):
            try:
                value = json.loads(item["raw"])
            except (ValueError, TypeError, KeyError):
                continue
            names.update(
                c.rsplit(".", 1)[-1]
                for requirement in value.get("requirements", [])
                for c in requirement.get("columns", [])
                if isinstance(c, str)
            )
    return [
        {"table_id": key, "columns": [c.name for c in table.columns]}
        for key, table in tables.items()
        if sum(c.name in names for c in table.columns) >= (2 if len(names) > 1 else 1)
    ]


def generate_one(
    row: dict[str, Any],
    directory: Path,
    *,
    catalog: Catalog,
    client: ChatClient,
    estimator: InputEstimator,
    keyword: SchemaKeywordSearch,
    model: str = MODEL,
    system: str = SYSTEM,
    max_added_tables: int = MAX_ADDED_TABLES,
    expansion_token_reserve: int = 0,
    expand_all_engines: bool = False,
    max_input_tokens: int = MAX_INPUT_TOKENS,
) -> dict[str, Any]:
    tables = catalog.by_id()
    from ..submission.validate import resolver_for

    resolver = resolver_for(tables)
    resumed = _resume(directory, row, resolver, model)
    if resumed is not None:
        return resumed

    prepared = read_json(directory / f"prepared_{row['question_id']}.json")
    context = prepared["context"]
    messages: list[dict[str, str]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
    ]
    supplied = {t["table_id"] for t in context["candidate_tables"]}

    def add_schemas(query: str, engines: list[str] | None = None) -> None:
        allowed = set(engines) if engines else None
        chosen: list[dict[str, Any]] = []
        instruction = "以下是按缺口文本检索的真实schema。严格使用其中字段；跨系统使用db1/query1、db2/query2和result。请生成最终answer。"
        ranked = keyword.rank(query)
        if expand_all_engines and allowed is not None and not any(
            item["table_id"] not in supplied and item["engine"] in allowed for item in ranked
        ):
            allowed = None
        for candidate in ranked:
            if candidate["table_id"] in supplied:
                continue
            if allowed is not None and candidate["engine"] not in allowed:
                continue
            trial = {
                "role": "user",
                "content": json.dumps(
                    {"additional_schemas": chosen + [candidate], "instruction": instruction}, ensure_ascii=False
                ),
            }
            if estimator(messages + [trial]) <= max_input_tokens - expansion_token_reserve:
                chosen.append(candidate)
            if len(chosen) >= max_added_tables:
                break
        messages.append(
            {"role": "user", "content": json.dumps({"additional_schemas": chosen, "instruction": instruction}, ensure_ascii=False)}
        )
        supplied.update(item["table_id"] for item in chosen)

    failed = directory / f"failed_{row['question_id']}.json"
    if failed.exists():
        previous = read_json(failed)
        (directory / "retry_history").mkdir(parents=True, exist_ok=True)
        write_json(directory / "retry_history" / f"question_{row['question_id']}_{sha256_text(str(previous))[:8]}.json", previous)
        errors = [e for item in previous.get("trace", []) for e in item.get("validation_errors", [])]
        messages.append(
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "previous_validation_errors": sorted(set(errors)),
                        "exact_column_matches_in_catalog": _failure_witnesses(directory, errors, tables),
                        "instruction": "此前尝试因真实schema校验失败，不能复用无效语句。字段不存在不是可接受的假设。table_id前缀是该表的真实数据库系统，不能迁移表到另一系统。需求字段分属不同系统时，必须使用db1/query1、db2/query2和result分步查询。请按实际schema重新选择库表；如需完整描述返回need_more_evidence。",
                    },
                    ensure_ascii=False,
                ),
            }
        )

    trace: list[dict[str, Any]] = []
    try:
        for attempt in range(MAX_ATTEMPTS):
            estimate = estimator(messages)
            if estimate > max_input_tokens:
                raise ValueError("输入估算超过上限；保留 schema 并失败，不静默截断")
            raw = client.complete(messages, MAX_OUTPUT_TOKENS, "generation" if attempt == 0 else "repair_or_expansion")
            trace.append({"attempt": attempt + 1, "raw": raw, "estimated_input_tokens": estimate})
            try:
                value = json.loads(raw)
                if value.get("status") == "need_more_evidence":
                    engines = value.get("engines") or context["searched_databases"]
                    if not isinstance(engines, list) or not set(engines) <= {"MYSQL", "POSTGRESQL", "SQLite", "Elasticsearch"}:
                        engines = context["searched_databases"]
                    messages.append({"role": "assistant", "content": raw})
                    add_schemas(row["question"] + " " + json.dumps(value, ensure_ascii=False), engines)
                    continue
                answer = value.get("answer")
                if isinstance(answer, dict):
                    for db_key, query_key in [("db", "query")] + [(f"db{i}", f"query{i}") for i in range(1, 4)]:
                        if answer.get(db_key) == "Elasticsearch" and isinstance(answer.get(query_key), dict):
                            answer[query_key] = json.dumps(answer[query_key], ensure_ascii=False, separators=(",", ":"))
                errors = validate_answer(answer, row, resolver)
            except Exception as error:  # noqa: BLE001 - 记录后重试
                errors = [f"输出非法：{type(error).__name__}: {str(error)[:200]}"]
            if not errors:
                output = {
                    "model": model,
                    "question": row,
                    "answer": answer,
                    "analysis": value,
                    "trace": trace,
                    "calls": [call.as_dict() for call in client.calls],
                }
                write_json(directory / f"question_{row['question_id']}.json", output)
                if failed.exists():
                    failed.unlink()
                return output
            trace[-1]["validation_errors"] = errors
            if any("未解析" in e or "非法" in e or "未知限定字段" in e for e in errors):
                add_schemas(row["question"] + " " + json.dumps(errors, ensure_ascii=False))
            messages.extend(
                [
                    {"role": "assistant", "content": raw},
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "validation_errors": errors,
                                "instruction": "修正错误并返回完整最终对象。若Elasticsearch query字符串内JSON不合法，请将query改为JSON对象而非转义字符串，程序会自动序列化成提交字符串。不要重复之前无效的query。",
                            },
                            ensure_ascii=False,
                        ),
                    },
                ]
            )
        raise ValueError("四次调用后仍未得到合法提交答案")
    except Exception as error:  # noqa: BLE001 - 失败题目单独保存
        output = {
            "model": model,
            "question": row,
            "error": str(error),
            "trace": trace,
            "calls": [call.as_dict() for call in client.calls],
        }
        write_json(directory / f"failed_{row['question_id']}.json", output)
        return output


def run(
    *,
    directory: Path | None = None,
    workers: int = 8,
    prepare_only: bool = False,
    device: str = "cuda",
    dtype: str = "auto",
    **embedding_kwargs: Any,
) -> dict[str, Any]:
    directory = directory or settings.path("outputs/qa_test_deepseek_v4_pro_full_train")
    directory.mkdir(parents=True, exist_ok=True)
    rows = read_json(settings.qa_test)
    if len({row["question_id"] for row in rows}) != len(rows):
        raise ValueError("测试集 question_id 必须唯一")
    write_json(
        directory / "run_config.json",
        {
            "model": MODEL,
            "training_source": TRAINING_SOURCE,
            "training_sha256": file_sha256(settings.qa_train),
            "input_sha256": file_sha256(settings.qa_test),
            "questions": len(rows),
            "workers": workers,
        },
    )
    if not all((directory / f"prepared_{row['question_id']}.json").exists() for row in rows):
        prepare(rows, directory, device=device, dtype=dtype, **embedding_kwargs)
    if prepare_only:
        return {"prepared": len(rows), "directory": str(directory)}

    catalog = Catalog.model_validate(read_json(settings.schema_catalog))
    keyword = SchemaKeywordSearch(read_json(directory / "schema_fallback.json"))
    estimator = InputEstimator()
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(
                generate_one,
                row,
                directory,
                catalog=catalog,
                client=ChatClient(model=MODEL, retries=2),
                estimator=estimator,
                keyword=keyword,
            ): row["question_id"]
            for row in rows
        }
        for future in as_completed(futures):
            output = future.result()
            results.append(output)
            success = sum("answer" in item for item in results)
            logger.info("finished %d/%d，成功 %d", len(results), len(rows), success)
            write_json(
                directory / "progress.json",
                {
                    "finished": len(results),
                    "success": success,
                    "failed": [item["question"]["question_id"] for item in results if "answer" not in item],
                },
            )

    report = {
        "model": MODEL,
        "training_source": TRAINING_SOURCE,
        "questions": len(rows),
        "completed": sum("answer" in item for item in results),
        "execution_accuracy": None,
    }
    write_json(directory / "report.json", report)
    if any("answer" not in item for item in results):
        raise SystemExit("未全部完成；成功答案已保存，可重跑重试失败题。")
    by_id = {item["question"]["question_id"]: item["answer"] for item in results}
    submission = [by_id[row["question_id"]] for row in rows]
    write_json(settings.project_root / "result.json", submission)
    return {"result": str(settings.project_root / "result.json"), "questions": len(submission)}
