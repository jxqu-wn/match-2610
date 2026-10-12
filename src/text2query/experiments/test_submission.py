"""用微调模型跑完整官方测试集（QA_test.json，400 题）并生成提交文件。

与 SQLite-50 实验同构：字符 TF-IDF 路由 + 训练集检索索引 + 与微调训练一致的
instruction 提示词 + OpenAI 兼容端点。支持断点续跑，最终按 QA_test 原始顺序
写出提交 JSON。
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from ..config import settings
from ..io import get_logger, read_json, write_json
from ..models import Catalog, Sample, Table
from ..retrieval.context import Budget, ContextBuilder
from ..retrieval.index import RetrievalIndex
from ..retrieval.sql_parser import SourceResolver
from ..routing.classifier import CharacterTfidfBaseline, label
from ..submission.finetuned import build_instruction, normalize_output, strip_fences

logger = get_logger(__name__)

DEFAULT_ENDPOINT = "http://192.168.15.119:8000/v1"
DEFAULT_MODEL = "qwen-track8-sqlite"


def _expected_engines(engine_label: str) -> list[str]:
    return [engine for engine in engine_label.split("|") if engine]


def _prompt_engines(prompt_table_ids: list[str], tables: dict[str, Table]) -> list[str]:
    return sorted({tables[key].engine for key in prompt_table_ids if key in tables})


def run(
    *,
    endpoint: str = DEFAULT_ENDPOINT,
    model: str = DEFAULT_MODEL,
    api_key: str | None = None,
    thinking: bool | None = None,
    training_source: Path | str | None = None,
    max_tables: int = 6,
    max_instruction_chars: int = 16000,
    max_output_tokens: int = 1024,
    workers: int = 8,
    output_dir: Path | str | None = None,
    result_path: Path | str | None = None,
    limit: int = 0,
    seed: int = 42,
) -> dict[str, Any]:
    import openai

    output_dir = Path(output_dir or settings.path("outputs/experiments/test400"))
    output_dir.mkdir(parents=True, exist_ok=True)
    result_path = Path(result_path or settings.path("output/qwen-track8-sqlite-result-1012.json"))
    training_source = Path(training_source or settings.qa_train)

    rows = read_json(settings.qa_test)
    if limit:
        rows = rows[:limit]
    if len({row["question_id"] for row in rows}) != len(rows):
        raise ValueError("测试集 question_id 必须唯一")

    catalog = Catalog.model_validate(read_json(settings.schema_catalog))
    tables = catalog.by_id()
    train_rows = read_json(training_source)
    router = CharacterTfidfBaseline().fit(
        [row["question"] for row in train_rows], [label(Sample.model_validate(row)) for row in train_rows]
    )
    predicted = router.predict([row["question"] for row in rows])

    index_dir = output_dir / "index"
    if (index_dir / "manifest.json").exists():
        index = RetrievalIndex.load(index_dir, encoder=None, training_source=training_source)
    else:
        index = RetrievalIndex.build(
            index_dir,
            encoder=None,
            training_source=training_source,
            catalog=catalog,
            knowledge=read_json(settings.knowledge),
            train_rows=train_rows,
        )
    builder = ContextBuilder(index, Budget(initial_tables=max_tables))

    write_json(
        output_dir / "run_config.json",
        {
            "endpoint": endpoint,
            "model": model,
            "thinking": thinking,
            "training_source": str(training_source),
            "training_rows": len(train_rows),
            "max_tables": max_tables,
            "max_output_tokens": max_output_tokens,
            "questions": len(rows),
            "seed": seed,
        },
    )

    prepared: list[dict[str, Any]] = []
    for row, engine_label in zip(rows, predicted):
        target = output_dir / f"prepared_{row['question_id']}.json"
        if target.exists():
            prepared.append(read_json(target))
            continue
        engines = _expected_engines(engine_label)
        context = builder.assemble(row["question"], engines, row["question_id"])
        prompt_tables = [item["table_id"] for item in context["candidate_tables"]]
        instruction = build_instruction(prompt_tables, tables)
        kept = list(prompt_tables)
        while len(instruction) > max_instruction_chars and kept:
            kept.pop()
            instruction = build_instruction(kept, tables)
        item = {
            "row": row,
            "predicted_engines": engines,
            "prompt_table_ids": kept,
            "instruction": instruction,
        }
        write_json(target, item)
        prepared.append(item)
        if len(prepared) % 50 == 0:
            logger.info("已准备 %d/%d", len(prepared), len(rows))

    client = openai.OpenAI(api_key=api_key or settings.api_key or "not-needed", base_url=endpoint)
    extra_body = None if thinking is None else {"thinking": {"type": "enabled" if thinking else "disabled"}}

    def call(messages: list[dict[str, str]]) -> tuple[str, str, dict[str, Any]]:
        request: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": 0,
            "max_tokens": max_output_tokens,
        }
        if extra_body is not None:
            request["extra_body"] = extra_body
        response = client.chat.completions.create(**request)
        choice = response.choices[0]
        usage = response.usage.model_dump() if response.usage else {}
        return choice.message.content or "", choice.finish_reason, usage

    def generate(item: dict[str, Any]) -> dict[str, Any]:
        question_id = item["row"]["question_id"]
        target = output_dir / f"question_{question_id}.json"
        if target.exists():
            cached = read_json(target)
            if (
                cached.get("model") == model
                and cached.get("question") == item["row"]
                and cached.get("answer") is not None
            ):
                return cached
        engines = _prompt_engines(item["prompt_table_ids"], tables) or item["predicted_engines"]
        messages = [
            {"role": "system", "content": item["instruction"]},
            {"role": "user", "content": item["row"]["question"]},
        ]
        try:
            raw, finish, usage = call(messages)
        except Exception as error:  # noqa: BLE001 - 逐题记录失败
            raw, finish, usage = "", "error", {"error": f"{type(error).__name__}: {error}"}
        answer: dict[str, Any] | None = None
        error_text: str | None = None
        try:
            answer = normalize_output(raw, engines, question_id)
        except Exception as error:  # noqa: BLE001 - 输出不合法，尝试一次修复
            error_text = f"{type(error).__name__}: {error}"
            try:
                repair = [
                    {
                        "role": "user",
                        "content": (
                            "下面的提交内容不是合法的 JSON/DSL。错误信息："
                            + error_text
                            + "。请只输出修正后的完整内容，保持原有查询结构，不要解释、不要 Markdown：\n"
                            + raw
                        ),
                    }
                ]
                repaired_raw, repair_finish, repair_usage = call(repair)
                answer = normalize_output(repaired_raw, engines, question_id)
                raw, finish, error_text = repaired_raw, repair_finish, None
                usage = {"initial": usage, "repair": repair_usage}
            except Exception as repair_error:  # noqa: BLE001 - 修复失败保留原因
                error_text = f"{error_text}; repair: {type(repair_error).__name__}: {repair_error}"
        output = {
            "model": model,
            "question": item["row"],
            "engines": engines,
            "prompt_table_ids": item["prompt_table_ids"],
            "raw_output": raw,
            "finish_reason": finish,
            "usage": usage,
            "answer": answer,
            "error": error_text,
        }
        write_json(target, output)
        return output

    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(generate, item) for item in prepared]
        for future in as_completed(futures):
            results.append(future.result())
            done = len(results)
            if done % 25 == 0 or done == len(prepared):
                logger.info("生成 %d/%d", done, len(prepared))
    by_id = {item["question"]["question_id"]: item for item in results}
    ordered = [by_id[row["question_id"]] for row in rows]

    complete = [item for item in ordered if item["answer"] is not None]
    submission = [item["answer"] for item in complete]
    write_json(result_path, submission)
    report = {
        "model": model,
        "endpoint": endpoint,
        "thinking": thinking,
        "training_source": str(training_source),
        "questions": len(rows),
        "generated": len(complete),
        "failed": [item["question"]["question_id"] for item in ordered if item["answer"] is None],
        "engine_distribution": _counter(item["answer"]["db"] for item in complete if "db" in item["answer"]),
        "multi_step": sum(1 for item in complete if "db1" in item["answer"]),
        "result_path": str(result_path),
    }
    write_json(output_dir / "report.json", report)
    logger.info("提交文件：%s（%d/%d）", result_path, len(complete), len(rows))
    return report


def _counter(values: Any) -> dict[str, int]:
    from collections import Counter

    return dict(Counter(values))
