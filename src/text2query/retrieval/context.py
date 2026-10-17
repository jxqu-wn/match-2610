"""证据组装：配额、一轮外键扩展、预算裁剪。

程序负责可重复的事实整理与边界控制；不做业务正确性判断。
裁剪时整条移除低优先级证据，绝不静默截断单表结构。
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

from ..io import get_logger

logger = get_logger(__name__)


@dataclass
class Budget:
    initial_tables: int = 8
    extra_tables: int = 4
    total_tables: int = 12
    knowledge: int = 12
    examples: int = 4
    expansion_rounds: int = 1
    context_tokens: int = 24000
    output_tokens: int = 3000
    repair_reserve: int = 4000
    judgment_calls: int = 2
    repair_calls: int = 1
    transport_retries: int = 2

    def __post_init__(self) -> None:
        if min(
            self.initial_tables,
            self.extra_tables,
            self.total_tables,
            self.knowledge,
            self.context_tokens,
            self.output_tokens,
            self.judgment_calls,
        ) < 1:
            raise ValueError("检索/上下文/调用上限必须为正")
        if self.examples < 0:
            raise ValueError("案例数量必须非负")
        if not 0 <= self.expansion_rounds <= 1 or self.judgment_calls > 2 or self.repair_calls > 1:
            raise ValueError("首版最多一轮扩展、两次判断、一次修复")
        if self.repair_reserve < 0 or self.repair_calls < 0 or self.transport_retries < 0:
            raise ValueError("调用上限非法")
        if self.initial_tables > self.total_tables:
            raise ValueError("首轮候选不能超过累计候选上限")
        if self.output_tokens >= self.context_tokens:
            raise ValueError("输出预留必须小于上下文预算")


def token_upper_bound(messages: list[dict[str, str]]) -> int:
    """保守的 UTF-8 字节上界；没有精确 tokenizer 时使用。"""
    return sum(len(m["content"].encode("utf-8")) + 64 for m in messages) + 64


def round_robin(groups: list[list[dict[str, Any]]], limit: int) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    groups = [list(group) for group in groups]
    while len(selected) < limit and any(groups):
        for group in groups:
            chosen = {item["source_id"] for item in selected}
            while group and group[0]["source_id"] in chosen:
                group.pop(0)
            if group and len(selected) < limit:
                selected.append(group.pop(0))
    return selected


class ContextBuilder:
    def __init__(self, index: Any, budget: Budget | None = None) -> None:
        self.index = index
        self.budget = budget or Budget()
        self.tokenizer = None
        if index.encoder is not None:
            try:
                from transformers import AutoTokenizer

                self.tokenizer = AutoTokenizer.from_pretrained(
                    index.encoder.model_path, local_files_only=True
                )
            except Exception:  # noqa: BLE001 - 无 tokenizer 时退回字节估算
                self.tokenizer = None

    # -- token 估算 -------------------------------------------------------- #
    def estimate(self, messages: list[dict[str, str]]) -> int:
        if self.tokenizer is not None:
            return int(
                sum(len(self.tokenizer.encode(m["content"])) + 8 for m in messages) * 1.2
            ) + 256
        return token_upper_bound(messages)

    # -- 单表上下文 -------------------------------------------------------- #
    def table(self, key: str, retrieval: dict[str, Any] | None = None) -> dict[str, Any]:
        original = self.index.tables[key]
        columns = []
        for column in original.columns:
            review = column.secondary_review or {}
            fallback = column.description_review or {}
            columns.append(
                [
                    column.name,
                    column.data_type,
                    column.nullable,
                    column.description,
                    column.description_origin,
                    review.get("status", fallback.get("status")),
                ]
            )
        return {
            "source_id": "schema:" + key,
            "table_id": key,
            "engine": original.engine,
            "database": original.database,
            "schema_name": original.schema_,
            "name": original.name,
            "description": original.description,
            "column_layout": ["name", "data_type", "nullable", "description", "description_origin", "review_status"],
            "columns": columns,
            "primary_key": original.primary_key,
            "foreign_keys": [fk.model_dump(by_alias=True) for fk in original.foreign_keys],
            "constraints": original.constraints,
            "source": original.source.model_dump() if original.source else None,
            "retrieval_evidence": retrieval or {"reason": "one_hop_declared_relation"},
            "review_notes": original.secondary_issues,
        }

    def relations(self, keys: list[str], example_ids: list[str]) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        selected = set(keys)
        for key in keys:
            for position, foreign_key in enumerate(self.index.tables[key].foreign_keys):
                target = foreign_key.references.table_id
                if target in selected:
                    result.append(
                        {
                            "source_id": f"relation:declared:{key}:{position}",
                            "kind": "declared_foreign_key",
                            "left_table": key,
                            "left_columns": foreign_key.columns,
                            "right_table": target,
                            "right_columns": foreign_key.references.columns,
                            "evidence": ["schema:" + key],
                        }
                    )
        for source_id in example_ids:
            example = self.index.by_id[source_id]
            for step in example["data"]["steps"]:
                for position, join in enumerate(step["joins"]):
                    if {join["left_table"], join["right_table"]} <= selected:
                        result.append(
                            {
                                "source_id": f"relation:example:{example['data']['question_id']}:{step['step']}:{position}",
                                "kind": "training_case_join_unverified",
                                **join,
                                "evidence": [source_id],
                            }
                        )
            result.extend(self._cross_engine_binding(example, selected))
        return result

    def _cross_engine_binding(self, example: dict[str, Any], selected: set[str]) -> list[dict[str, Any]]:
        import re

        steps = example["data"]["steps"]
        if len(steps) < 2 or not all(len(step["table_ids"]) == 1 for step in steps[:2]):
            return []
        first, second = steps[:2]
        left, right = first["table_ids"][0], second["table_ids"][0]
        if not {left, right} <= selected or first["engine"] == second["engine"]:
            return []
        match = re.search(r"([\w.]+)\s+IN\s*\(\s*result\s*\)", second["query"], re.I)
        output = re.search(r"^\s*SELECT\s+(?:DISTINCT\s+)?([\w.]+)\s+FROM\b", first["query"], re.I)
        if not match or not output:
            return []
        left_column, right_column = output.group(1).split(".")[-1], match.group(1).split(".")[-1]
        if left_column not in {c.name for c in self.index.tables[left].columns} or right_column not in {
            c.name for c in self.index.tables[right].columns
        }:
            return []
        return [
            {
                "source_id": f"relation:example:{example['data']['question_id']}:result_binding",
                "kind": "training_case_result_binding_unverified",
                "left_table": left,
                "left_columns": [left_column],
                "right_table": right,
                "right_columns": [right_column],
                "evidence": [example["source_id"]],
            }
        ]

    # -- 候选召回 ---------------------------------------------------------- #
    def retrieve(
        self, question: str, engines: list[str], limit: int | None = None, exclude: tuple[str, ...] = ()
    ) -> list[dict[str, Any]]:
        limit = limit or self.budget.initial_tables
        groups = [
            self.index.search_tables(
                question, [engine], limit, exclude=exclude, knowledge_limit=self.budget.knowledge
            )
            for engine in engines
        ]
        ranking = round_robin(groups, limit)
        primary = ranking[: max(len(engines), limit - 2)]
        keys = [item["table_ids"][0] for item in primary]
        neighbors = []
        for key in keys:
            for other_key, table in self.index.tables.items():
                if table.engine not in engines or other_key in keys:
                    continue
                connected = any(
                    fk.references.table_id == other_key for fk in self.index.tables[key].foreign_keys
                ) or any(fk.references.table_id == key for fk in table.foreign_keys)
                if connected and "schema:" + other_key not in exclude and other_key not in neighbors:
                    neighbors.append(other_key)
        for key in neighbors[: min(2, limit - len(primary))]:
            primary.append(
                {"source_id": "schema:" + key, "table_ids": [key], "reason": "one_hop_declared_relation"}
            )
        for item in ranking:
            if len(primary) >= limit:
                break
            if item["source_id"] not in {x["source_id"] for x in primary}:
                primary.append(item)
        return primary

    # -- 上下文组装 -------------------------------------------------------- #
    def assemble(
        self,
        question: str,
        engines: list[str],
        question_id: int | None = None,
        previous: dict[str, Any] | None = None,
        requests: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        previous = previous or {}
        old_tables = previous.get("candidate_tables", [])
        old_ids = {"schema:" + t["table_id"] for t in old_tables}
        old_evidence = {
            d["source_id"] for name in ("knowledge", "examples") for d in previous.get(name, [])
        }
        selected = list(engines)
        if requests:
            if any(gap.get("allow_engine_expansion") for gap in requests):
                selected = sorted({table.engine for table in self.index.tables.values()})
            limit = min(self.budget.extra_tables, self.budget.total_tables - len(old_tables))
            rankings: list[dict[str, Any]] = []
            for gap in requests:
                if gap["kind"] == "unknown_values":
                    continue
                rankings.extend(self.retrieve(gap["search_query"], selected, max(1, limit), tuple(old_ids)))
            ranking = round_robin([rankings], max(0, limit))
            query = " ".join(gap["search_query"] for gap in requests)
        else:
            ranking = self.retrieve(question, selected)
            query = question

        candidates = old_tables + [self.table(item["table_ids"][0], item) for item in ranking]
        keys = [item["table_id"] for item in candidates]
        found_knowledge = self.index.search(
            query, "knowledge", selected, self.budget.knowledge, table_ids=keys, exclude=old_evidence
        )
        support = {
            hit["source_id"]: hit
            for table in candidates
            for hit in table["retrieval_evidence"].get("knowledge_support", [])
            if hit["source_id"] not in old_evidence
        }
        support_hits = sorted(support.values(), key=lambda hit: (hit["knowledge_rank"], hit["source_id"]))
        # 合并表召回携带的知识与直接召回结果后再精排，避免轮取覆盖相关性顺序。
        found_knowledge = self.index.rank_hits(query, support_hits + found_knowledge, self.budget.knowledge)
        knowledge = previous.get("knowledge", []) + [
            {
                "source_id": hit["source_id"],
                **self.index.by_id[hit["source_id"]]["data"],
                "retrieval_evidence": hit,
            }
            for hit in found_knowledge
        ]

        exact = self.index.search(
            query,
            "example",
            selected,
            self.budget.examples,
            table_ids=keys,
            exclude=old_evidence,
            exact_engines=True,
        )
        if len(engines) == 1 and not requests:
            groups = [exact]
        else:
            groups = [exact[:2]] + [
                self.index.search(
                    query, "example", [engine], 2, table_ids=keys, exclude=old_evidence, exact_engines=True
                )
                for engine in selected
            ]
        examples = previous.get("examples", []) + [
            {
                "source_id": hit["source_id"],
                **self.index.by_id[hit["source_id"]]["data"],
                "retrieval_evidence": hit,
            }
            for hit in round_robin(groups, self.budget.examples)
        ]
        knowledge = (knowledge[-self.budget.knowledge :] if requests else knowledge[: self.budget.knowledge])
        examples = (examples[-self.budget.examples :] if requests else examples[: self.budget.examples])

        # 已启用精排时不再用首个案例强行替换精排选出的表。
        if examples and not requests and not self.index.recall_metadata["rerank_enabled"]:
            preferred_keys = [
                key
                for step in examples[0]["steps"]
                for key in step["table_ids"]
                if self.index.tables[key].engine in selected
            ]
            for key in dict.fromkeys(preferred_keys):
                if key in keys:
                    continue
                if len(candidates) >= self.budget.initial_tables:
                    removable = next(
                        (
                            n
                            for n in range(len(candidates) - 1, len(selected) - 1, -1)
                            if candidates[n]["table_id"] not in preferred_keys
                        ),
                        None,
                    )
                    if removable is None:
                        continue
                    candidates.pop(removable)
                candidates.append(
                    self.table(
                        key,
                        {"reason": "first_relevant_training_case", "source_id": examples[0]["source_id"]},
                    )
                )
                keys = [item["table_id"] for item in candidates]

        comparisons = previous.get("source_comparisons", [])
        if requests and any(
            gap["kind"] in ("description_conflict", "unclear_relation") for gap in requests
        ):
            comparisons = self._load_comparisons(requests, comparisons)

        return {
            "question_id": question_id,
            "question": question,
            "initial_databases": previous.get("initial_databases", engines),
            "searched_databases": selected,
            "candidate_tables": candidates,
            "knowledge": knowledge,
            "examples": examples,
            "source_comparisons": comparisons,
            "relations": self.relations(keys, [e["source_id"] for e in examples]),
            "retrieval_budget": {
                **asdict(self.budget),
                "remaining_expansion_rounds": 0 if previous else self.budget.expansion_rounds,
            },
            "omitted_evidence": [],
            "token_estimation": "local_tokenizer_times_1.2_plus_256"
            if self.tokenizer
            else "conservative_utf8_bytes_plus_envelope",
        }

    def _load_comparisons(
        self, requests: list[dict[str, Any]], comparisons: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        from ..config import settings
        from ..io import read_json

        extracted = read_json(settings.schema_extracted)
        secondary = read_json(settings.secondary_review) if settings.secondary_review.exists() else {}
        manual = read_json(settings.manual_review) if settings.manual_review.exists() else {}
        requested_keys = {key for gap in requests for key in gap["checked_tables"]}
        existing = {item["source_id"] for item in comparisons}
        for table in extracted["tables"]:
            key = table["table_id"]
            if key not in requested_keys or "review:" + key in existing:
                continue
            comparisons.append(
                {
                    "source_id": "review:" + key,
                    "table_id": key,
                    "source": table["source"],
                    "raw_definition": table["raw_definition"],
                    "original_descriptions": {c["name"]: c["description"] for c in table["columns"]},
                    "manual_corrections": [r for r in manual.get("corrections", []) if r.get("table_id") == key],
                    "secondary_field_reviews": [r for r in secondary.get("field_reviews", []) if r.get("table_id") == key],
                    "special_cases": [r for r in secondary.get("special_cases", []) if r.get("table_id") == key],
                }
            )
        return comparisons

    # -- 预算裁剪 ---------------------------------------------------------- #
    def fit(
        self,
        context: dict[str, Any],
        system: str,
        extra_messages: tuple[dict[str, str], ...] = (),
        *,
        allow_pruning: bool = True,
    ) -> tuple[dict[str, Any], list[dict[str, str]]]:
        context = json.loads(json.dumps(context))
        max_input = self.budget.context_tokens - self.budget.output_tokens - (
            self.budget.repair_reserve if allow_pruning and self.budget.repair_calls else 0
        )
        preferred: set[str] = set()
        if context["examples"]:
            preferred.update(key for step in context["examples"][0]["steps"] for key in step["table_ids"])
        for engine in context["initial_databases"]:
            first = next((t["table_id"] for t in context["candidate_tables"] if t["engine"] == engine), None)
            if first:
                preferred.add(first)

        while True:
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(context, ensure_ascii=False, separators=(",", ":"))},
                *extra_messages,
            ]
            estimate = self.estimate(messages)
            if estimate <= max_input:
                context["estimated_input_tokens"] = estimate + 128
                if estimate + 128 <= max_input:
                    messages[1]["content"] = json.dumps(context, ensure_ascii=False, separators=(",", ":"))
                    return context, messages
                context.pop("estimated_input_tokens")
            if not allow_pruning:
                raise ValueError("修复轮在冻结证据下超出预算；不移除 schema")

            removed = self._prune_once(context, preferred)
            if removed is None:
                raise ValueError("问题与指令本身超出上下文预算")
            self._drop_orphans(context)

    def _prune_once(self, context: dict[str, Any], preferred: set[str]) -> str | None:
        """移除一条最低优先级证据，返回其 source_id。"""
        expendable = [
            i for i, table in enumerate(context["candidate_tables"]) if table["table_id"] not in preferred
        ]
        pools: list[tuple[str, int]] = []
        if expendable:
            pools.append(("candidate_tables", expendable[-1]))
        if len(context["knowledge"]) > 2:
            pools.append(("knowledge", len(context["knowledge"]) - 1))
        if context["examples"]:
            pools.append(("examples", len(context["examples"]) - 1))
        if context["knowledge"]:
            pools.append(("knowledge", len(context["knowledge"]) - 1))
        if context.get("source_comparisons"):
            pools.append(("source_comparisons", len(context["source_comparisons"]) - 1))
        if context["candidate_tables"]:
            pools.append(("candidate_tables", len(context["candidate_tables"]) - 1))
        if not pools:
            return None
        name, index = pools[0]
        removed = context[name].pop(index)
        context["omitted_evidence"].append(removed["source_id"])
        return removed["source_id"]

    def _drop_orphans(self, context: dict[str, Any]) -> None:
        keys = {t["table_id"] for t in context["candidate_tables"]}
        for name in ("knowledge", "examples"):
            kept = []
            for item in context[name]:
                independent_candidate = name == "knowledge" and item.get("retrieval_scope") == "global"
                if independent_candidate or set(self.index.by_id[item["source_id"]]["table_ids"]) & keys:
                    kept.append(item)
                else:
                    context["omitted_evidence"].append(item["source_id"])
            context[name] = kept
        context["relations"] = self.relations(
            [t["table_id"] for t in context["candidate_tables"]],
            [e["source_id"] for e in context["examples"]],
        )
