"""命令行入口：``text2query <command>``。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console

from .config import settings
from .io import read_json, setup_logging, write_json

app = typer.Typer(add_completion=False, help="统一查询指令生成：路由、召回、生成")
console = Console()

ENGINE = ["MYSQL", "POSTGRESQL", "Elasticsearch"]


def _echo(value: object) -> None:
    console.print_json(json.dumps(value, ensure_ascii=False, default=str))


def _resolve_engines(engines: Optional[list[str]], classification_json: Optional[Path]) -> list[str]:
    if classification_json:
        row = read_json(classification_json)
        found = row.get("databases", row.get("engines"))
        if found is None:
            found = sorted({row[key] for key in ("db", "db1", "db2", "db3") if row.get(key)})
        return sorted(set(found))
    return sorted(set(engines or []))


# --------------------------------------------------------------------------- #
# 数据准备
# --------------------------------------------------------------------------- #


@app.command("split-dataset")
def split_dataset(
    input: Optional[Path] = typer.Option(None, help="原始训练集，默认 QA_train.json"),
    output_dir: Optional[Path] = typer.Option(None, help="输出目录，默认 data/赛题8/splits"),
    validation_ratio: float = typer.Option(0.1, help="验证集比例"),
    seed: int = typer.Option(42, help="随机种子"),
    overwrite: bool = typer.Option(False, help="允许覆盖已冻结的划分文件"),
) -> None:
    """按数据源分层划分训练/验证集（scikit-learn）。"""
    from .data.split import build_split

    manifest = build_split(
        input_path=input or settings.qa_train,
        output_dir=output_dir or settings.path(settings.splits_dir),
        validation_ratio=validation_ratio,
        seed=seed,
        overwrite=overwrite,
    )
    _echo({key: manifest[key] for key in ("total_samples", "train_samples", "validation_samples")})


@app.command("build-catalog")
def build_catalog(
    association_method: Annotated[str, typer.Option(help="知识关联文本评分：tfidf 或 bm25")] = "tfidf",
    association_threshold: Annotated[float, typer.Option(help="关联得分阈值")] = 0.3,
    bm25_k1: Annotated[float, typer.Option()] = 1.5,
    bm25_b: Annotated[float, typer.Option()] = 0.75,
    training_support: Annotated[
        str, typer.Option(help="训练增强：auto（有文件时启用）、sql（必须有文件）、none（禁用）")
    ] = "auto",
    training_source: Annotated[Path | None, typer.Option(help="可选训练文件，默认训练划分")] = None,
) -> None:
    """解析当前范围的 Schema，生成基础目录与检索文档。"""
    from .data.catalog import build_catalog as build

    catalog = build(
        persist=True,
        association_method=association_method,
        association_threshold=association_threshold,
        bm25_k1=bm25_k1,
        bm25_b=bm25_b,
        training_support=training_support,
        training_source=training_source,
    )
    _echo(catalog.summary)


@app.command("enrich-descriptions")
def enrich_descriptions(
    workers: int = typer.Option(4, help="并发请求数"),
    limit: Optional[int] = typer.Option(None, help="仅处理前 N 张表（试运行）"),
    offline: bool = typer.Option(False, help="只用缓存，不调用 API"),
) -> None:
    """用 LLM 校验/补充字段描述（OpenAI 兼容接口 + 缓存）。"""
    from .data.enrich import main as enrich_main

    enrich_main(offline=offline, workers=workers, limit=limit)


@app.command("apply-review")
def apply_review() -> None:
    """回放人工抽查与二次复核记录。"""
    from .data.review import apply_reviews

    catalog = apply_reviews()
    _echo(catalog.description_summary)


# --------------------------------------------------------------------------- #
# 路由
# --------------------------------------------------------------------------- #


@app.command("route-evaluate")
def route_evaluate(
    output: Optional[Path] = typer.Option(None),
    limit: Optional[int] = typer.Option(None),
    device: str = typer.Option("cpu"),
    dtype: str = typer.Option("auto"),
    batch_size: int = typer.Option(8),
) -> None:
    """评估数据库系统路由分类器。"""
    from .routing.classifier import evaluate

    _echo(evaluate(output=output, limit=limit, device=device, dtype=dtype, batch_size=batch_size))


@app.command("route-predict")
def route_predict(
    question: str = typer.Option(..., "--question"),
    output: Optional[Path] = typer.Option(None),
    device: str = typer.Option("cpu"),
    dtype: str = typer.Option("auto"),
) -> None:
    """对单个问题预测数据库系统集合。"""
    from .routing.classifier import predict

    _echo(predict(question, output=output, device=device, dtype=dtype))


@app.command("route-cross-validate")
def route_cross_validate(output: Optional[Path] = typer.Option(None), folds: int = typer.Option(5)) -> None:
    """字符 TF-IDF + 逻辑回归交叉验证对照。"""
    from .routing.classifier import cross_validate

    _echo(cross_validate(output=output, folds=folds))


# --------------------------------------------------------------------------- #
# 召回
# --------------------------------------------------------------------------- #


def _encoder(keyword_only: bool, device: str, dtype: str, batch_size: int, max_length: int):
    if keyword_only:
        return None
    from .retrieval.embedding import retrieval_encoder

    return retrieval_encoder(
        instruction=settings.retrieval_instruction,
        device=device,
        dtype=dtype,
        batch_size=batch_size,
        max_length=max_length,
    )


@app.command("build-index")
def build_index(
    index: Optional[Path] = typer.Option(None),
    keyword_only: bool = typer.Option(False),
    device: str = typer.Option("cpu"),
    dtype: str = typer.Option("auto"),
    batch_size: int = typer.Option(8),
    max_length: int = typer.Option(512),
    training_source: Optional[Path] = typer.Option(None),
) -> None:
    """构建库表/知识/训练案例混合索引。"""
    from .retrieval.index import RetrievalIndex

    encoder = _encoder(keyword_only, device, dtype, batch_size, max_length)
    built = RetrievalIndex.build(index, encoder, training_source=training_source)
    _echo(
        {"index": str(index or settings.path("outputs/information_retrieval/index")), "documents": len(built.documents)}
    )


@app.command("recall")
@app.command("retrieve")
def retrieve(
    question: str = typer.Option(..., "--question"),
    engines: Optional[list[str]] = typer.Option(None, "--engines"),
    classification_json: Optional[Path] = typer.Option(None),
    question_id: Optional[int] = typer.Option(None),
    index: Optional[Path] = typer.Option(None),
    output: Optional[Path] = typer.Option(None),
    keyword_only: bool = typer.Option(False),
    device: str = typer.Option("cpu"),
    dtype: str = typer.Option("auto"),
    max_length: int = typer.Option(512),
) -> None:
    """BM25 + embedding → RRF → 本地重排；与 recall 命令等价。"""
    from .llm.planner import SYSTEM
    from .retrieval.context import ContextBuilder
    from .retrieval.index import RetrievalIndex

    encoder = _encoder(keyword_only, device, dtype, 8, max_length)
    loaded = RetrievalIndex.load(index, encoder)
    selected = _resolve_engines(engines, classification_json)
    if not selected:
        raise typer.BadParameter("需要 --engines 或 --classification-json")
    builder = ContextBuilder(loaded)
    context, _ = builder.fit(builder.assemble(question, selected, question_id), SYSTEM)
    if output:
        write_json(output, context)
    _echo(context)


@app.command("evaluate-retrieval")
def evaluate_retrieval(
    validation: Optional[Path] = typer.Option(None),
    limit: int = typer.Option(0),
    index: Optional[Path] = typer.Option(None),
    output: Optional[Path] = typer.Option(None),
    keyword_only: bool = typer.Option(False),
    device: str = typer.Option("cpu"),
    dtype: str = typer.Option("auto"),
    max_length: int = typer.Option(512),
) -> None:
    """在验证集上评估表级召回（验证答案只作标签）。"""
    from .retrieval.evaluate import evaluate
    from .retrieval.index import RetrievalIndex

    encoder = _encoder(keyword_only, device, dtype, 8, max_length)
    loaded = RetrievalIndex.load(index, encoder)
    report = evaluate(loaded, validation, limit)
    if output:
        write_json(output, report)
    _echo(report["metrics"])


# --------------------------------------------------------------------------- #
# 生成
# --------------------------------------------------------------------------- #


@app.command("plan")
def plan(
    question: str = typer.Option(..., "--question"),
    engines: Optional[list[str]] = typer.Option(None, "--engines"),
    classification_json: Optional[Path] = typer.Option(None),
    question_id: Optional[int] = typer.Option(None),
    index: Optional[Path] = typer.Option(None),
    output: Optional[Path] = typer.Option(None),
    model: str = typer.Option("deepseek-flash"),
    keyword_only: bool = typer.Option(False),
    device: str = typer.Option("cpu"),
    dtype: str = typer.Option("auto"),
    max_length: int = typer.Option(512),
) -> None:
    """调用 LLM 做有界库表规划。"""
    from .llm.client import ChatClient
    from .llm.planner import Planner
    from .retrieval.index import RetrievalIndex

    encoder = _encoder(keyword_only, device, dtype, 8, max_length)
    loaded = RetrievalIndex.load(index, encoder)
    selected = _resolve_engines(engines, classification_json)
    if not selected:
        raise typer.BadParameter("需要 --engines 或 --classification-json")
    run = Planner(loaded, ChatClient(model=model)).run(question, selected, question_id)
    if output:
        write_json(output, run)
    _echo(run["result"])


@app.command("generate-submission")
def generate_submission(
    directory: Optional[Path] = typer.Option(None),
    workers: int = typer.Option(8),
    prepare_only: bool = typer.Option(False),
    device: str = typer.Option("cuda"),
    dtype: str = typer.Option("auto"),
) -> None:
    """端到端生成 result.json（DeepSeek）。"""
    from .submission.generate import run

    _echo(run(directory=directory, workers=workers, prepare_only=prepare_only, device=device, dtype=dtype))


@app.command("finetuned-submission")
def finetuned_submission(
    endpoint: str = typer.Option("http://127.0.0.1:8000/v1/chat/completions"),
    model: str = typer.Option("finetuned-model"),
    output_dir: Optional[Path] = typer.Option(None),
    result_path: Optional[Path] = typer.Option(None),
    prompt_style: str = typer.Option("chat"),
    recall: str = typer.Option("hybrid", help="召回模式：hybrid、schema 或 examples；均使用统一检索评分"),
    max_tables: int = typer.Option(6),
    example_k: int = typer.Option(3),
    workers: int = typer.Option(8),
    prepare_only: bool = typer.Option(False),
    limit: int = typer.Option(0),
) -> None:
    """用微调模型（OpenAI 兼容服务）生成 result.json。"""
    from .submission.finetuned import run

    _echo(
        run(
            output_dir=output_dir,
            result_path=result_path,
            workers=workers,
            prepare_only=prepare_only,
            limit=limit,
            endpoint=endpoint,
            model=model,
            prompt_style=prompt_style,
            recall=recall,
            max_tables=max_tables,
            example_k=example_k,
        )
    )


@app.command("experiment-sqlite50")
def experiment_sqlite50(
    endpoint: str = typer.Option("http://192.168.15.119:8000/v1", help="OpenAI 兼容端点"),
    model: str = typer.Option("qwen-track8-text2sql", help="微调模型名"),
    api_key: Optional[str] = typer.Option(None, "--api-key", help="API key；默认读 DEEPSEEK_API_KEY"),
    thinking: Optional[bool] = typer.Option(
        None, "--thinking/--no-thinking", help="是否开启 thinking；不传则不发送该字段"
    ),
    sample_size: int = typer.Option(50, help="验证集 SQLite 题抽样数"),
    seed: int = typer.Option(42, help="抽样随机种子"),
    max_tables: int = typer.Option(6, help="提示词最多注入的表数"),
    max_output_tokens: int = typer.Option(768),
    workers: int = typer.Option(4),
    output_dir: Optional[Path] = typer.Option(None),
) -> None:
    """SQLite 50 题微调模型实验：覆盖率与 SQL 目标正确率。"""
    from .experiments.sqlite50 import run

    report = run(
        endpoint=endpoint,
        model=model,
        api_key=api_key,
        thinking=thinking,
        sample_size=sample_size,
        seed=seed,
        max_tables=max_tables,
        max_output_tokens=max_output_tokens,
        workers=workers,
        output_dir=output_dir,
    )
    _echo(report["metrics"])


@app.command("test-submission")
def test_submission(
    endpoint: str = typer.Option("http://192.168.15.119:8000/v1", help="OpenAI 兼容端点"),
    model: str = typer.Option("qwen-track8-sqlite", help="微调模型名"),
    api_key: Optional[str] = typer.Option(None, "--api-key"),
    thinking: Optional[bool] = typer.Option(None, "--thinking/--no-thinking"),
    training_source: Optional[Path] = typer.Option(None, help="检索索引使用的训练集，默认完整 QA_train.json"),
    max_tables: int = typer.Option(6),
    max_output_tokens: int = typer.Option(1024),
    workers: int = typer.Option(8),
    output_dir: Optional[Path] = typer.Option(None),
    result_path: Optional[Path] = typer.Option(None),
    limit: int = typer.Option(0),
) -> None:
    """用微调模型跑完整官方测试集并生成提交文件。"""
    from .experiments.test_submission import run

    _echo(
        run(
            endpoint=endpoint,
            model=model,
            api_key=api_key,
            thinking=thinking,
            training_source=training_source,
            max_tables=max_tables,
            max_output_tokens=max_output_tokens,
            workers=workers,
            output_dir=output_dir,
            result_path=result_path,
            limit=limit,
        )
    )


def main() -> None:
    setup_logging()
    app()


if __name__ == "__main__":
    main()
