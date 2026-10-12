"""用微调模型（OpenAI 兼容服务）生成 result.json。

按训练时的 ``instruction`` / ``input`` 结构构造提示，连接 vLLM/SGLang 等
OpenAI 兼容端点，并把输出规范化为竞赛提交格式。微调模型不在仓库内。
"""

from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from ..config import settings
from ..io import get_logger, read_json, write_json
from ..models import Catalog, Table
from ..retrieval.context import ContextBuilder, Budget
from ..retrieval.index import RetrievalIndex
from ..routing.embedding import EmbeddingService

logger = get_logger(__name__)

PG_DATABASE = "ais"
ES_DATABASE = "medical_institutions"
EXCLUDED_TABLE_IDS = {"MYSQL:common.administrative_division"}


def normalize_ddl(raw_definition: str) -> str:
    text = (raw_definition or "").rstrip()
    if text.endswith(";"):
        text = text[:-1].rstrip()
    index = text.rfind(")")
    if index == -1:
        return text + ";"
    return text[: index + 1].rstrip() + ";"


def es_mapping_block(table: Table) -> str:
    properties = {
        c.name: c.mapping for c in table.columns if "." not in c.name and c.mapping
    }
    mapping = {"mappings": {"properties": properties}}
    return f"{table.name} mapping: {json.dumps(mapping, ensure_ascii=False, separators=(',', ':'))}"


def database_label(table: Table) -> str:
    if table.engine == "POSTGRESQL":
        return PG_DATABASE
    if table.engine == "Elasticsearch":
        return ES_DATABASE
    return table.namespace or table.name


def order_tables_by_fk(table_ids: list[str], tables: dict[str, Table]) -> list[str]:
    """被引用表排在引用表之后，与训练提示的 FROM/JOIN 顺序一致。"""
    ordered = list(table_ids)
    for left in ordered:
        for fk in tables[left].foreign_keys:
            target = fk.references.table_id
            if target in ordered and target != left:
                left_index, target_index = ordered.index(left), ordered.index(target)
                if left_index > target_index:
                    ordered.pop(target_index)
                    ordered.insert(left_index, target)
    return ordered


def build_instruction(table_ids: list[str], tables: dict[str, Table]) -> str:
    ordered = order_tables_by_fk([tid for tid in table_ids if tid in tables and tid not in EXCLUDED_TABLE_IDS], tables)
    grouped: list[dict[str, Any]] = []
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for table_id in ordered:
        table = tables[table_id]
        key = (table.engine, database_label(table))
        if key not in by_key:
            by_key[key] = {"engine": table.engine, "database": key[1], "blocks": []}
            grouped.append(by_key[key])
        block = es_mapping_block(table) if table.engine == "Elasticsearch" else normalize_ddl(table.raw_definition or "")
        by_key[key]["blocks"].append(block)

    engines = list(dict.fromkeys(group["engine"] for group in grouped))
    databases = [group["database"] for group in grouped]
    if len(engines) > 1:
        output_instruction = (
            "这是跨数据源的两步查询。只输出一个 JSON 对象，字段依次为 db1、query1、db2、query2；"
            "第二步按原赛题协议使用第一步结果 result。不要解释。"
        )
    elif engines[0] == "Elasticsearch":
        output_instruction = "只输出 Elasticsearch JSON DSL 字符串，不要解释、Markdown 或 HTTP 路径。"
    else:
        output_instruction = "只输出一条只读 SQL 查询，不要解释、Markdown 或附加字段。"

    header = "\n".join(
        [
            "根据下列官方数据库结构，将问题转换为查询。",
            output_instruction,
            "涉及的数据源：" + "、".join(engines),
            "涉及的数据库：" + "、".join(databases),
            "官方表结构：",
        ]
    )
    body = []
    for group in grouped:
        body.append(f"[{group['engine']} / {group['database']}]")
        body.append("\n".join(group["blocks"]))
    return header + "\n" + "\n".join(body)


def strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z]*\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)
    return text.strip()


def normalize_output(raw: str, engines: list[str], question_id: int) -> dict[str, Any]:
    text = strip_fences(raw)
    if len(engines) > 1:
        value = json.loads(text)
        if not isinstance(value, dict):
            raise ValueError(f"跨数据源输出不是合法 JSON：{text[:200]}")
        answer = {"question_id": question_id}
        for step in (1, 2, 3):
            if f"db{step}" in value:
                answer[f"db{step}"] = value[f"db{step}"]
                answer[f"query{step}"] = value[f"query{step}"]
        return answer
    engine = engines[0]
    if engine == "Elasticsearch":
        return {"question_id": question_id, "db": engine, "query": json.dumps(json.loads(text), ensure_ascii=False, separators=(",", ":"))}
    return {"question_id": question_id, "db": engine, "query": text}


class FinetunedPipeline:
    def __init__(
        self,
        *,
        endpoint: str = "http://127.0.0.1:8000/v1/chat/completions",
        model: str = "finetuned-model",
        api_key: str = "not-needed",
        prompt_style: str = "chat",
        recall: str = "examples",
        max_tables: int = 6,
        example_k: int = 3,
        routing_dir: Path | None = None,
        **embedding_kwargs: Any,
    ) -> None:
        import openai

        self.model = model
        self.prompt_style = prompt_style
        self.recall = recall
        self.max_tables = max_tables
        self.example_k = example_k
        base_url = endpoint.rsplit("/chat/completions", 1)[0]
        self.client = openai.OpenAI(api_key=api_key, base_url=base_url)
        self.catalog = Catalog.model_validate(read_json(settings.schema_catalog))
        self.tables = self.catalog.by_id()
        self.index = RetrievalIndex.load(
            settings.path("outputs/information_retrieval/index_full_train"),
            EmbeddingService(instruction=settings.retrieval_instruction, **embedding_kwargs),
            training_source=settings.qa_train,
        )
        self.router = self._load_router(routing_dir, **embedding_kwargs)

    def _load_router(self, routing_dir: Path | None, **embedding_kwargs: Any) -> Any:
        import joblib

        directory = Path(routing_dir or settings.path("outputs/database_routing/embedding"))
        payload = joblib.load(directory / "classifier.joblib")
        embedder = EmbeddingService(instruction=settings.routing_instruction, **embedding_kwargs)

        def predict(questions: list[str]) -> list[str]:
            return [str(value) for value in payload["estimator"].predict(embedder.encode(questions))]

        return predict

    def _recall_tables(self, question: str, row: dict[str, Any]) -> tuple[list[str], list[str]]:
        engines = self.router([question])[0].split("|")
        if self.recall == "schema":
            builder = ContextBuilder(self.index, Budget(initial_tables=self.max_tables))
            context = builder.assemble(question, engines, row.get("question_id"))
            return engines, [t["table_id"] for t in context["candidate_tables"]]

        import numpy as np

        positions = [
            self.index.positions[document["source_id"]]
            for document in self.index.documents
            if document["kind"] == "example" and set(document["engines"]) == set(engines)
        ]
        if not positions:
            return engines, []
        query = self.index.encoder.encode([question])[0]
        similarities = np.asarray(self.index.vectors)[positions] @ query
        order = np.argsort(-similarities)[: self.example_k]
        keys: list[str] = []
        for index in order:
            keys.extend(self.index.documents[positions[int(index)]]["table_ids"])
        return engines, list(dict.fromkeys(keys))[: self.max_tables]

    def _messages(self, question: str, instruction: str) -> list[dict[str, str]]:
        if self.prompt_style == "alpaca":
            content = f"### Instruction\n{instruction}\n\n### Input\n{question}\n\n### Response\n"
            return [{"role": "user", "content": content}]
        return [{"role": "system", "content": instruction}, {"role": "user", "content": question}]

    def generate(self, row: dict[str, Any], *, prepare_only: bool = False) -> dict[str, Any]:
        engines, keys = self._recall_tables(row["question"], row)
        instruction = build_instruction(keys, self.tables)
        messages = self._messages(row["question"], instruction)
        if prepare_only:
            return {"question_id": row["question_id"], "engines": engines, "table_ids": keys, "messages": messages}
        response = self.client.chat.completions.create(
            model=self.model, messages=messages, temperature=0, max_tokens=2048
        )
        raw = response.choices[0].message.content or ""
        return {"question_id": row["question_id"], "engines": engines, "answer": normalize_output(raw, engines, row["question_id"])}


def run(
    *,
    output_dir: Path | None = None,
    result_path: Path | None = None,
    workers: int = 8,
    prepare_only: bool = False,
    limit: int = 0,
    **kwargs: Any,
) -> dict[str, Any]:
    output_dir = output_dir or settings.path("outputs/finetuned_inference")
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = read_json(settings.qa_test)
    if limit:
        rows = rows[:limit]
    pipeline = FinetunedPipeline(**kwargs)
    results = []
    if prepare_only:
        for row in rows:
            results.append(pipeline.generate(row, prepare_only=True))
            write_json(output_dir / f"prepared_{row['question_id']}.json", results[-1])
        return {"prepared": len(results), "directory": str(output_dir)}

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(pipeline.generate, row): row for row in rows}
        for future in as_completed(futures):
            output = future.result()
            results.append(output)
            write_json(output_dir / f"question_{output['question_id']}.json", output)
            logger.info("finished %d/%d", len(results), len(rows))
    by_id = {item["question_id"]: item["answer"] for item in results}
    submission = [by_id[row["question_id"]] for row in rows]
    write_json(result_path or settings.project_root / "result.json", submission)
    return {"result": str(result_path or settings.project_root / "result.json"), "questions": len(submission)}
