"""有界规划协议：库表选择与缺口判断，不生成或执行业务查询。"""

from __future__ import annotations

import json
import time
from typing import Any

from ..retrieval.context import Budget, ContextBuilder, token_upper_bound
from .client import ChatClient

PIPELINE_VERSION = "framework-v1"

SYSTEM = """你负责选择库表，不生成或执行业务SQL。仅返回JSON对象：
{"status":"ready|ready_with_assumptions|needs_clarification|insufficient_evidence|need_more_evidence","selected_tables":[{"table_id":"已提供ID","required_columns":["真实字段"],"evidence":["已提供source_id"]}],"join_plan":[{"relation_id":"已提供关系source_id","evidence":["已提供source_id"]}],"assumptions":[],"unresolved_gaps":[],"gaps":[],"database_change_reason":""}。
补检索gaps每项格式：{"kind":"missing_attribute","requirement":"缺少什么，字符串","checked_tables":["已提供table_id"],"requested_evidence":"需要的资料，必须是非空字符串而非数组或对象","search_query":"检索词，字符串","allow_engine_expansion":false}。kind也可为unclear_relation/description_conflict/intent_ambiguity/unknown_values。
推断关系可用kind=inferred、left_table/left_columns、right_table/right_columns、evidence和reason，但须明确假设，不声称已验证。使用column_layout解释columns数组。相似排名不证明业务正确；训练标注未经验证；inferred描述不是事实。同名字段不是关联依据；名称推断的必要关联无法确认时返回insufficient_evidence。培养国家与出生国家、国家总数与国家年份联合分组必须区分，遵循案例口径时列明假设。歧义不能靠增加表解决；没有值域工具，不编造取值。按公司、车型等业务实体分组时检查名称/编码口径，优先利用有证据的公司表或字典表提供业务名称；仅用编码时明确假设。逐项覆盖输出、分组、条件、统计和实体名称，对照相关案例检查遗漏关联表；不要机械复制案例。实体名称缺表时提出具体补检索，不能仅因主表有ID就ready。ready必须有表和字段且没有未决缺口；有假设用ready_with_assumptions。数据库改变必须说明依据。remaining_expansion_rounds为0时不得返回need_more_evidence。证据只引用本轮提供的source_id。"""

STATUSES = {"ready", "ready_with_assumptions", "needs_clarification", "insufficient_evidence", "need_more_evidence"}
GAPS = {"missing_attribute", "unclear_relation", "description_conflict", "intent_ambiguity", "unknown_values"}


def sources(context: dict[str, Any]) -> set[str]:
    return {
        item["source_id"]
        for name in ("candidate_tables", "knowledge", "examples", "relations", "source_comparisons")
        for item in context.get(name, [])
    }


def normalize_result(result: Any) -> Any:
    """只规范化等价容器，不凭空补造缺失证据。"""
    if not isinstance(result, dict):
        return result
    if result.get("status") == "ready" and isinstance(result.get("assumptions"), list) and result["assumptions"]:
        result["status"] = "ready_with_assumptions"
    gaps = result.get("gaps", [])
    for gap in gaps if isinstance(gaps, list) else []:
        if isinstance(gap, dict):
            value = gap.get("requested_evidence")
            if isinstance(value, list) and value and all(isinstance(v, str) and v.strip() for v in value):
                gap["requested_evidence"] = "; ".join(value)
    return result


def validate(result: Any, context: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(result, dict):
        return ["输出必须是对象"]
    status = result.get("status")
    if status not in STATUSES:
        errors.append("status 非法")
    tables = {t["table_id"]: t for t in context["candidate_tables"]}
    evidence = sources(context)
    selected = result.get("selected_tables", [])
    if not isinstance(selected, list):
        return errors + ["selected_tables 必须是数组"]
    ids: list[str] = []
    for table in selected:
        if not isinstance(table, dict):
            errors.append("selected_tables 元素必须是对象")
            continue
        key = table.get("table_id")
        ids.append(key)
        if key not in tables:
            errors.append(f"未知表：{key}")
            continue
        fields = {c[0] for c in tables[key]["columns"]}
        columns = table.get("required_columns")
        if not isinstance(columns, list) or not columns or any(c not in fields for c in columns):
            errors.append(f"required_columns 非法：{key}")
        refs = table.get("evidence")
        if not isinstance(refs, list) or not refs or any(r not in evidence for r in refs):
            errors.append(f"证据引用非法：{key}")
    if len(ids) != len(set(ids)):
        errors.append("selected_tables 重复")
    for name in ("join_plan", "assumptions", "unresolved_gaps", "gaps"):
        if not isinstance(result.get(name, []), list):
            errors.append(f"{name} 必须是数组")
    if errors:
        return errors

    relations = {r["source_id"]: r for r in context["relations"]}
    for join in result.get("join_plan", []):
        if not isinstance(join, dict):
            errors.append("join 必须是对象")
            continue
        if join.get("relation_id") in relations:
            relation = relations[join["relation_id"]]
        elif join.get("kind") == "inferred":
            relation = join
            if not result.get("assumptions") or not join.get("reason"):
                errors.append("推断关系需要 reason 与 assumption")
            for side in ("left", "right"):
                key = join.get(side + "_table")
                fields = {c[0] for c in tables.get(key, {}).get("columns", [])}
                columns = join.get(side + "_columns")
                if not isinstance(columns, list) or not columns or any(c not in fields for c in columns):
                    errors.append("推断关系字段非法")
            if (
                not join.get("left_columns")
                or not join.get("right_columns")
                or len(join["left_columns"]) != len(join["right_columns"])
            ):
                errors.append("join 字段数不匹配")
            if "left_table" not in join or "right_table" not in join:
                errors.append("缺少 join 端点")
                continue
        else:
            errors.append("未知关系")
            continue
        if relation["left_table"] not in ids or relation["right_table"] not in ids:
            errors.append("关系端点必须被选中")
        refs = join.get("evidence", [])
        if not refs or any(r not in evidence for r in refs):
            errors.append("join 证据非法")
        if "unverified" in relation["kind"] and not result.get("assumptions"):
            errors.append("未验证案例关系需要显式假设")

    for gap in result.get("gaps", []):
        if not isinstance(gap, dict):
            errors.append("gap 必须是对象")
            continue
        if gap.get("kind") not in GAPS:
            errors.append("gap kind 非法")
        for field in ("requirement", "requested_evidence", "search_query"):
            if not isinstance(gap.get(field), str) or not gap[field].strip():
                errors.append(f"gap 缺少 {field}")
        checked = gap.get("checked_tables")
        if not isinstance(checked, list) or any(t not in tables for t in checked):
            errors.append("checked_tables 非法")
        if not isinstance(gap.get("allow_engine_expansion"), bool):
            errors.append("allow_engine_expansion 必须是布尔")

    if status in ("ready", "ready_with_assumptions") and (
        not selected or result.get("unresolved_gaps") or result.get("gaps")
    ):
        errors.append("ready 需要有选中表且没有未决缺口")
    if status == "ready" and result.get("assumptions"):
        errors.append("有假设请使用 ready_with_assumptions")
    if status == "ready_with_assumptions" and not result.get("assumptions"):
        errors.append("ready_with_assumptions 需要假设")
    if status == "need_more_evidence" and not result.get("gaps"):
        errors.append("need_more_evidence 需要具体 gaps")
    engines = sorted({tables[k]["engine"] for k in ids if k in tables})
    if engines != sorted(context["initial_databases"]) and selected and not result.get("database_change_reason"):
        errors.append("数据库改变需要说明依据")
    return errors


class Planner:
    def __init__(self, index: Any, client: ChatClient, budget: Budget | None = None) -> None:
        self.builder = ContextBuilder(index, budget)
        self.client = client

    def run(
        self, question: str, engines: list[str], question_id: int | None = None
    ) -> dict[str, Any]:
        start = time.monotonic()
        budget = self.builder.budget
        encoder = self.builder.index.encoder
        stats_initial = dict(self.builder.index.stats)
        cache_initial = len(encoder._cache) if encoder else 0
        log: dict[str, Any] = {"judgment_calls": 0, "repair_calls": 0, "expansion_rounds": 0, "rounds": []}
        call_start = len(self.client.calls)
        context: dict[str, Any] = {"question": question, "question_id": question_id, "candidate_tables": []}
        result: dict[str, Any]
        try:
            context = self.builder.assemble(question, engines, question_id)
            for round_number in range(budget.judgment_calls):
                raw_context = context
                context, messages = self.builder.fit(context, SYSTEM)
                log["rounds"].append(
                    {
                        "source_ids": sorted(sources(context)),
                        "omitted_evidence": context["omitted_evidence"],
                        "input_token_upper_bound": token_upper_bound(messages),
                        "estimated_input_tokens": self.builder.estimate(messages),
                    }
                )
                log["judgment_calls"] += 1
                raw = self.client.complete(messages, budget.output_tokens, "judgment")
                log.setdefault("model_outputs", []).append({"purpose": "judgment", "raw": raw})
                try:
                    result = normalize_result(json.loads(raw))
                    errors = validate(result, context)
                except (ValueError, TypeError):
                    errors, result = ["JSON 非法"], None
                if errors and log["repair_calls"] < budget.repair_calls:
                    repair_messages = (
                        {"role": "assistant", "content": raw},
                        {
                            "role": "user",
                            "content": json.dumps(
                                {"repair_errors": errors, "instruction": "修复JSON结构，不扩大资料范围。"},
                                ensure_ascii=False,
                            ),
                        },
                    )
                    context, repair_input = self.builder.fit(context, SYSTEM, repair_messages, allow_pruning=False)
                    log.setdefault("repairs", []).append(
                        {
                            "input_token_upper_bound": token_upper_bound(repair_input),
                            "errors": errors,
                            "source_ids": sorted(sources(context)),
                            "estimated_input_tokens": self.builder.estimate(repair_input),
                        }
                    )
                    log["repair_calls"] += 1
                    raw = self.client.complete(repair_input, budget.output_tokens, "repair")
                    log.setdefault("model_outputs", []).append({"purpose": "repair", "raw": raw})
                    try:
                        result = normalize_result(json.loads(raw))
                        errors = validate(result, context)
                    except (ValueError, TypeError):
                        errors = ["修复后 JSON 仍非法"]
                if errors:
                    raise ValueError("; ".join(errors))

                if result["status"] in ("ready", "ready_with_assumptions"):
                    break
                gaps = result.get("gaps", [])
                actionable = [g for g in gaps if g["kind"] not in ("intent_ambiguity", "unknown_values")]
                if (
                    not actionable
                    or log["expansion_rounds"] >= budget.expansion_rounds
                    or round_number + 1 >= budget.judgment_calls
                ):
                    result["status"] = (
                        "needs_clarification"
                        if result["status"] == "needs_clarification"
                        or any(g["kind"] == "intent_ambiguity" for g in gaps)
                        else "insufficient_evidence"
                    )
                    result["unresolved_gaps"] = result.get("unresolved_gaps", []) + [
                        g for g in gaps if g not in result.get("unresolved_gaps", [])
                    ]
                    result["stop_reason"] = "no_actionable_gaps" if not actionable else "budget_exhausted"
                    break
                before = sources(context)
                expanded = self.builder.assemble(question, engines, question_id, context, actionable)
                expanded["previous_judgment"] = result
                expanded, _ = self.builder.fit(expanded, SYSTEM)
                log["expansion_rounds"] += 1
                if not sources(expanded) - before:
                    result.update(status="insufficient_evidence", unresolved_gaps=gaps, stop_reason="no_new_evidence")
                    break
                context = expanded

            if result["status"] == "need_more_evidence":
                result.update(
                    status="insufficient_evidence",
                    unresolved_gaps=result.get("gaps", []),
                    stop_reason="budget_exhausted",
                )
            tables = {t["table_id"]: t for t in context["candidate_tables"]}
            selected_engines = sorted({tables[t["table_id"]]["engine"] for t in result.get("selected_tables", [])})
            result.update(
                question_id=question_id,
                initial_databases=engines,
                final_databases=selected_engines,
                retrieval_class=("single" if len(selected_engines) == 1 else "multi") if selected_engines else None,
            )
        except Exception as error:  # noqa: BLE001 - 失败必须可诊断，不冒充业务结论
            result = {
                "question_id": question_id,
                "status": "error",
                "initial_databases": engines,
                "error": f"{type(error).__name__}: {error}",
            }
        stats = {key: value - stats_initial[key] for key, value in self.builder.index.stats.items()}
        stats["embedding_cache_hit_rate"] = (
            stats["embedding_cache_hits"] / stats["semantic_queries"] if stats["semantic_queries"] else None
        )
        log["retrieval_stats"] = stats
        log["embedding_cache"] = {
            "entries_before": cache_initial,
            "entries_after": len(encoder._cache) if encoder else 0,
        }
        log["latency_seconds"] = time.monotonic() - start
        log["transport_calls"] = [call.as_dict() for call in self.client.calls[call_start:]]
        return {"pipeline_version": PIPELINE_VERSION, "result": result, "execution": log, "context": context}
