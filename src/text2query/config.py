"""集中配置：路径、模型、预算与外部服务。

所有路径默认相对仓库根目录；可通过 ``T2Q_`` 前缀的环境变量或 ``.env`` 覆盖。
密钥只从环境读取，绝不写入代码或产物。
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def repo_root() -> Path:
    """仓库根目录（``<root>/src/text2query/config.py`` 向上三级）。"""
    return Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="T2Q_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    project_root: Path = Field(default_factory=repo_root)

    # ---- 数据 ----
    competition_dir: Path = Path("data/赛题8")
    preprocessed_dir: Path = Path("data/preprocessed")
    splits_dir: Path = Path("data/赛题8/splits")
    output_dir: Path = Path("outputs")

    # ---- 模型 ----
    embedding_model: Path = Path("models/Qwen3-Embedding-0.6B")
    routing_instruction: str = (
        "Identify the business entities and data requirements of this database query for database routing."
    )
    retrieval_instruction: str = (
        "Retrieve database schemas, field definitions and query examples needed to answer the database question."
    )

    # ---- Recall：两路召回 → RRF → 本地重排 ----
    recall_bm25_top_k: int = Field(default=50, gt=0)
    recall_embedding_top_k: int = Field(default=50, gt=0)
    recall_rrf_k: int = Field(default=60, gt=0)
    recall_rerank_top_k: int = Field(default=50, gt=0)
    recall_rerank_enabled: bool = True
    reranker_model: Path = Path("models/Qwen3-Reranker-0.6B")
    reranker_device: str = "cpu"
    reranker_dtype: str = "auto"
    reranker_batch_size: int = Field(default=8, gt=0)
    reranker_max_length: int = Field(default=2048, gt=0)
    reranker_instruction: str = (
        "Given a database question, judge whether the document provides evidence needed to answer it. "
        "Consider the business domain, requested entities, attributes, filters, grouping and aggregation. "
        "Shared identifiers alone do not establish relevance."
    )

    # ---- LLM（DeepSeek 兼容 OpenAI 协议）----
    # 密钥只从环境变量读取，不参与 T2Q_ 前缀。
    api_key: str | None = Field(default=None, validation_alias="DEEPSEEK_API_KEY")
    base_url: str = "https://api.deepseek.com"
    judge_model: str = "deepseek-flash"
    generate_model: str = "deepseek-v4-pro"
    llm_timeout: float = 120.0
    llm_retries: int = 2

    def path(self, relative: Path | str) -> Path:
        """把相对路径解析到仓库根目录下。"""
        path = Path(relative)
        return path if path.is_absolute() else self.project_root / path

    # 常用产物路径
    @property
    def schema_catalog(self) -> Path:
        return self.path(self.preprocessed_dir) / "schema_catalog.json"

    @property
    def schema_extracted(self) -> Path:
        return self.path(self.preprocessed_dir) / "schema_extracted.json"

    @property
    def schema_documents(self) -> Path:
        return self.path(self.preprocessed_dir) / "schema_documents.jsonl"

    @property
    def manual_review(self) -> Path:
        return self.path(self.preprocessed_dir) / "manual_review.json"

    @property
    def secondary_review(self) -> Path:
        return self.path(self.preprocessed_dir) / "secondary_review.json"

    @property
    def enrichment_report(self) -> Path:
        return self.path(self.preprocessed_dir) / "enrichment_report.json"

    @property
    def knowledge(self) -> Path:
        return self.path(self.competition_dir) / "knowledge.json"

    @property
    def qa_train(self) -> Path:
        return self.path(self.competition_dir) / "QA_train.json"

    @property
    def qa_test(self) -> Path:
        return self.path(self.competition_dir) / "QA_test.json"

    @property
    def train_split(self) -> Path:
        return self.path(self.splits_dir) / "train.json"

    @property
    def validation_split(self) -> Path:
        return self.path(self.splits_dir) / "validation.json"

    @property
    def schema_sources(self) -> dict[str, Path]:
        return {
            "commom_schema.txt": self.path(self.competition_dir) / "Schema/commom_schema.txt",
            "core_schema.txt": self.path(self.competition_dir) / "Schema/core_schema.txt",
        }


settings = Settings()
