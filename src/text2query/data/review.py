"""应用人工抽查与二次复核记录；不调用任何 API。

复核记录随产物保存，脚本只把已记录的修订回放到 catalog，并在回放前检查
修订前描述是否与当前一致，避免套用过期结论。
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from ..config import settings
from ..io import get_logger, read_json, write_json
from ..models import Catalog, Table
from .catalog import schema_documents, write_documents

logger = get_logger(__name__)


def _target(table: Table, field: str | None) -> Any:
    if field is None:
        return table
    return next(column for column in table.columns if column.name == field)


def apply_manual_review(catalog: Catalog, review: dict[str, Any]) -> Catalog:
    by_id = catalog.by_id()
    for item in review["checks"]:
        by_id[item["table_id"]].agent_review = {
            "reviewer": review["reviewer"],
            "scope": item["scope"],
            "notes": item["notes"],
        }
    for correction in review["corrections"]:
        table = by_id[correction["table_id"]]
        target = _target(table, correction["field"])
        if target.description not in (correction["before"], correction["after"]):
            raise ValueError(f'复核记录已过期：{correction["table_id"]}.{correction["field"]}')
        target.description = correction["after"]
        target.description_origin = "agent_review"
        target.agent_review = {
            "reviewer": review["reviewer"],
            "reason": correction["reason"],
            "evidence": correction["evidence"],
        }
    return catalog


def restore_secondary(catalog: Catalog) -> None:
    """回滚上一次二次复核，支持脚本重复执行。"""
    for table in catalog.tables:
        for target in [table, *table.columns]:
            previous = getattr(target, "secondary_review", None)
            if previous:
                target.description = previous["before"]
                target.description_origin = previous["before_origin"]
            if hasattr(target, "secondary_review"):
                target.secondary_review = None
        table.secondary_issues = []


def apply_secondary_review(catalog: Catalog, report: dict[str, Any]) -> Catalog:
    by_id = catalog.by_id()
    for entry in report["field_reviews"]:
        table = by_id[entry["table_id"]]
        target = _target(table, entry["field"])
        if target.description != entry["before"]:
            raise ValueError(f'二次复核已过期：{entry["table_id"]}.{entry["field"]}')
        target.secondary_review = {
            **entry,
            "before_origin": target.description_origin,
            "reviewer": report["reviewer"],
        }
        if entry["after"] != entry["before"]:
            target.description = entry["after"]
            target.description_origin = "agent_secondary_review"
    for issue in report["special_cases"]:
        by_id[issue["table_id"]].secondary_issues.append(issue)
    return catalog


def describe_summary(catalog: Catalog, review: dict[str, Any] | None, report: dict[str, Any] | None) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "tables_with_description": sum(bool(t.description) for t in catalog.tables),
        "columns_with_description": sum(bool(c.description) for t in catalog.tables for c in t.columns),
        "columns_unknown": sum(c.description is None for t in catalog.tables for c in t.columns),
        "model_field_statuses": dict(
            Counter(
                c.description_review["status"]
                for t in catalog.tables
                for c in t.columns
                if c.description_review
            )
        ),
    }
    if review is not None:
        summary["agent_corrections"] = len(review["corrections"])
    if report is not None:
        summary.update(
            secondary_review_statuses=dict(Counter(e["status"] for e in report["field_reviews"])),
            previous_unknown_outcomes=dict(
                Counter(e["status"] for e in report["field_reviews"] if e["before"] is None)
            ),
            secondary_description_changes=sum(e["before"] != e["after"] for e in report["field_reviews"]),
            secondary_special_cases=len(report["special_cases"]),
        )
    return summary


def apply_reviews(catalog: Catalog | None = None, *, persist: bool = True) -> Catalog:
    catalog = catalog or Catalog.model_validate(read_json(settings.schema_catalog))
    review = read_json(settings.manual_review)
    secondary_path = settings.secondary_review
    report = read_json(secondary_path) if secondary_path.exists() else None

    if report is not None:
        restore_secondary(catalog)
    apply_manual_review(catalog, review)
    if report is not None:
        apply_secondary_review(catalog, report)
    catalog.description_summary = describe_summary(catalog, review, report)

    if persist:
        output = settings.path(settings.preprocessed_dir)
        write_json(output / "schema_catalog.json", catalog.model_dump(by_alias=True))
        write_documents(catalog, output / "schema_documents.jsonl")
    logger.info("描述汇总：%s", catalog.description_summary)
    return catalog
