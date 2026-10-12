"""pydantic 数据模型：schema 目录、检索证据与规划协议。

目录模型容忍额外字段（``extra="allow"``），因为预处理产物保留了复核、
模型来源等审计信息，重写时不应丢弃。
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Engine = Literal["SQLite", "MYSQL", "POSTGRESQL", "Elasticsearch"]

PlanStatus = Literal[
    "ready",
    "ready_with_assumptions",
    "needs_clarification",
    "insufficient_evidence",
    "need_more_evidence",
    "error",
]

FINAL_STATUSES = {"ready", "ready_with_assumptions", "needs_clarification", "insufficient_evidence", "error"}

GAP_KINDS = {"missing_attribute", "unclear_relation", "description_conflict", "intent_ambiguity", "unknown_values"}

_TOLERANT = ConfigDict(extra="allow", populate_by_name=True)


class KnowledgeRef(BaseModel):
    model_config = _TOLERANT
    knowledge_id: int
    knowledge_text: str | None = None


class TrainingExampleRef(BaseModel):
    model_config = _TOLERANT
    question_id: int
    question: str | None = None
    query: str | None = None
    step: str | None = None


class ForeignKeyReference(BaseModel):
    model_config = _TOLERANT
    table_id: str
    columns: list[str] = Field(default_factory=list)


class ForeignKey(BaseModel):
    model_config = _TOLERANT
    columns: list[str] = Field(default_factory=list)
    references: ForeignKeyReference
    raw_definition: str | None = None
    implicit_primary_key: bool = False


class Column(BaseModel):
    model_config = _TOLERANT
    name: str
    data_type: str
    nullable: bool | None = None
    description: str | None = None
    description_origin: str | None = None
    knowledge_ids: list[int] = Field(default_factory=list)
    raw_definition: str | None = None
    mapping: dict[str, Any] | None = None
    description_review: dict[str, Any] | None = None
    secondary_review: dict[str, Any] | None = None

    @property
    def review_status(self) -> str | None:
        if self.secondary_review:
            return self.secondary_review.get("status")
        if self.description_review:
            return self.description_review.get("status")
        return None


class SourceRef(BaseModel):
    model_config = _TOLERANT
    file: str | None = None
    encoding: str | None = None
    start_line: int | None = None


class Table(BaseModel):
    model_config = _TOLERANT
    table_id: str
    engine: Engine
    database: str | None = None
    schema_: str | None = Field(default=None, alias="schema")
    object_type: str = "table"
    name: str
    description: str | None = None
    description_origin: str | None = None
    columns: list[Column] = Field(default_factory=list)
    primary_key: list[str] = Field(default_factory=list)
    foreign_keys: list[ForeignKey] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    knowledge: list[KnowledgeRef] = Field(default_factory=list)
    training_examples: list[TrainingExampleRef] = Field(default_factory=list)
    source: SourceRef | None = None
    raw_definition: str | None = None
    secondary_issues: list[dict[str, Any]] = Field(default_factory=list)

    @property
    def namespace(self) -> str | None:
        """业务库名：MySQL/SQLite 用 database，PostgreSQL 用 schema。"""
        return self.database or self.schema_

    @property
    def column_names(self) -> list[str]:
        return [c.name for c in self.columns]


class Catalog(BaseModel):
    model_config = _TOLERANT
    format_version: int = 1
    sources: list[dict[str, Any]] = Field(default_factory=list)
    tables: list[Table] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)
    enrichment: dict[str, Any] = Field(default_factory=dict)

    def by_id(self) -> dict[str, Table]:
        return {t.table_id: t for t in self.tables}


class Sample(BaseModel):
    """训练/测试问答对，兼容跨数据源的多步字段。"""

    model_config = _TOLERANT
    question_id: int
    question: str

    def steps(self) -> list[tuple[int, Engine, str]]:
        """返回 ``[(step_index, engine, query)]``；单源 step_index=0。"""
        extra = self.model_extra or {}
        result: list[tuple[int, Engine, str]] = []
        if extra.get("db"):
            result.append((0, extra["db"], extra.get("query", "")))
        index = 1
        while f"db{index}" in extra:
            result.append((index, extra[f"db{index}"], extra.get(f"query{index}", "")))
            index += 1
        return result

    def engines(self) -> list[Engine]:
        return sorted({engine for _, engine, _ in self.steps()})


class KnowledgeItem(BaseModel):
    knowledge_id: int
    knowledge_text: str


# --------------------------------------------------------------------------- #
# 规划协议
# --------------------------------------------------------------------------- #


class SelectedTable(BaseModel):
    model_config = _TOLERANT
    table_id: str
    required_columns: list[str]
    evidence: list[str] = Field(default_factory=list)


class JoinPlan(BaseModel):
    model_config = _TOLERANT
    relation_id: str | None = None
    kind: Literal["inferred"] | None = None
    left_table: str | None = None
    left_columns: list[str] = Field(default_factory=list)
    right_table: str | None = None
    right_columns: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    reason: str | None = None


class Gap(BaseModel):
    model_config = _TOLERANT
    kind: str
    requirement: str
    requested_evidence: str
    search_query: str
    checked_tables: list[str] = Field(default_factory=list)
    allow_engine_expansion: bool = False


class PlanResult(BaseModel):
    model_config = _TOLERANT
    status: PlanStatus
    selected_tables: list[SelectedTable] = Field(default_factory=list)
    join_plan: list[JoinPlan] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    unresolved_gaps: list[Any] = Field(default_factory=list)
    gaps: list[Gap] = Field(default_factory=list)
    database_change_reason: str | None = None
    question_id: int | None = None
    initial_databases: list[str] = Field(default_factory=list)
    final_databases: list[str] = Field(default_factory=list)
    retrieval_class: str | None = None
    stop_reason: str | None = None
