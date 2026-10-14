"""Optional training-question/SQL evidence; no files, services or answer labels.

SQLGlot supplies parsing and scopes. This adapter binds scope columns to the
project's catalog, labels their syntactic use, and scores question evidence.
Training annotations are weak evidence, never schema descriptions or facts.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import sqlglot
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize
from sqlglot import exp
from sqlglot.optimizer.scope import Scope, traverse_scope

from ..models import Catalog, Sample
from ..retrieval.sql_parser import DIALECTS, SourceResolver
from .association_support import SupportResult, SupportSignal
from .lexical import text_features as _features

# Syntactic roles only; no task IDs, table names or business vocabulary.
DEFAULT_ROLE_WEIGHTS = {
    "calculation": 1.0,
    "filter": 0.9,
    "having": 0.9,
    "output": 0.65,
    "group": 0.4,
    "order": 0.5,
    "join": 0.0,
}


@dataclass
class TrainingSQLSupport:
    catalog: Catalog
    rows: list[dict[str, Any]]
    role_weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_ROLE_WEIGHTS))
    weight: float = 0.75

    def __post_init__(self):
        if not 0 <= self.weight <= 1 or any(not 0 <= v <= 1 for v in self.role_weights.values()):
            raise ValueError("training weights must be in [0, 1]")
        self.tables = self.catalog.by_id()
        self.resolver = SourceResolver(self.tables)
        self.records: list[dict[str, Any]] = []
        self.issues: list[dict[str, Any]] = []
        self.examples: dict[str, list[dict[str, Any]]] = defaultdict(list)
        ids = [r["question_id"] for r in self.rows]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate training question_id")
        for row in self.rows:
            sample = Sample.model_validate(row)
            for step, engine, query in sample.steps():
                name = "query" if step == 0 else f"query{step}"
                try:
                    self._unresolved = set()
                    usage = self._dsl(query) if engine == "Elasticsearch" else self._sql(query, engine)
                except (sqlglot.errors.SqlglotError, ValueError, KeyError) as error:
                    self.issues.append(
                        {
                            "question_id": row["question_id"],
                            "step": name,
                            "reason": type(error).__name__,
                            "detail": str(error)[:200],
                        }
                    )
                    continue
                if self._unresolved:
                    self.issues.append(
                        {
                            "question_id": row["question_id"],
                            "step": name,
                            "reason": "unresolved_columns",
                            "columns": sorted(self._unresolved),
                        }
                    )
                for tid, fields in sorted(usage.items()):
                    record = {
                        "question_id": row["question_id"],
                        "question": row["question"],
                        "query": query,
                        "step": name,
                        "table_id": tid,
                        "fields": {k: sorted(v) for k, v in sorted(fields.items())},
                    }
                    record["role_weight"] = max(
                        (self.role_weights.get(role, 0.0) for roles in fields.values() for role in roles), default=0.0
                    )
                    self.records.append(record)
                    self.examples[tid].append({k: record[k] for k in ("question_id", "question", "query", "step")})

    def _column_sources(self, scope, column, engine, seen=frozenset()):
        marker = (id(scope), column.table.casefold(), column.name.casefold())
        if marker in seen:
            return set()
        seen = seen | {marker}
        sources = {k.casefold(): v for k, v in scope.sources.items()}
        if column.table:
            source = sources.get(column.table.casefold())
            if source is None:
                return self._column_sources(scope.parent, column, engine, seen) if scope.parent else set()
            candidates = [source]
        else:
            candidates = list(sources.values())
        matches = set()
        for source in candidates:
            if isinstance(source, exp.Table):
                tid = self.resolver.resolve(engine, source)
                if tid:
                    names = {c.name.casefold(): c.name for c in self.tables[tid].columns}
                    if column.name.casefold() in names:
                        matches.add((tid, names[column.name.casefold()]))
            elif isinstance(source, Scope):
                selections = [
                    v for v in source.expression.selects if v.alias_or_name.casefold() == column.name.casefold()
                ]
                for selection in selections:
                    for child in selection.find_all(exp.Column):
                        if child.find_ancestor(exp.Select) is source.expression:
                            matches.update(self._column_sources(source, child, engine, seen))
                if not selections and any(v.is_star for v in source.expression.selects):
                    matches.update(self._column_sources(source, exp.column(column.name), engine, seen))
        # An unqualified column with multiple origins is ambiguous. Derived
        # expressions on a qualified CTE column may legitimately use many fields.
        return matches if column.table or len(matches) <= 1 else set()

    @staticmethod
    def _role(column, expression):
        node = column.parent
        computed = False
        while node is not None and node is not expression:
            if isinstance(node, exp.Join):
                return "join"
            if isinstance(node, exp.Where):
                return "filter"
            if isinstance(node, exp.Having):
                return "having"
            if isinstance(node, exp.Group):
                return "group"
            if isinstance(node, exp.Order):
                return "order"
            if isinstance(node, (exp.Func, exp.Binary)):
                computed = True
            node = node.parent
        return "calculation" if computed else "output"

    def _sql(self, query, engine):
        tree = sqlglot.parse_one(query, read=DIALECTS[engine])
        usage = defaultdict(lambda: defaultdict(set))
        for scope in traverse_scope(tree):
            for source in scope.sources.values():
                if isinstance(source, exp.Table):
                    tid = self.resolver.resolve(engine, source)
                    if tid:
                        usage[tid]  # retain join-only/row-only cases in audit
            for column in scope.columns:
                role = self._role(column, scope.expression)
                sources = self._column_sources(scope, column, engine)
                if not sources:
                    self._unresolved.add(column.sql())
                equality = column.find_ancestor(exp.EQ)
                if (
                    role == "filter"
                    and equality is not None
                    and isinstance(equality.left, exp.Column)
                    and isinstance(equality.right, exp.Column)
                ):
                    left = self._column_sources(scope, equality.left, engine)
                    right = self._column_sources(scope, equality.right, engine)
                    if left and right and {tid for tid, _ in left}.isdisjoint(tid for tid, _ in right):
                        role = "join"
                for tid, name in sources:
                    usage[tid][name].add(role)
            # COUNT(*) has no named column. Only a unique physical source can
            # supply row-count evidence without inventing a join-side meaning.
            if any(
                isinstance(node.this, exp.Star) and node.find_ancestor(exp.Select) is scope.expression
                for node in scope.expression.find_all(exp.Count)
            ):
                direct = {
                    self.resolver.resolve(engine, v) for v in scope.sources.values() if isinstance(v, exp.Table)
                } - {None}
                if len(direct) == 1 and len(scope.sources) == 1:
                    usage[next(iter(direct))]["*"].add("calculation")
        return usage

    def _dsl(self, query):
        value = json.loads(query)
        tids = [tid for tid, t in self.tables.items() if t.engine == "Elasticsearch"]
        if len(tids) != 1:
            raise ValueError("DSL index not uniquely identified by the catalog")
        tid = tids[0]
        names = set(self.tables[tid].column_names)
        usage = defaultdict(lambda: defaultdict(set))
        usage[tid]

        def add(name, role):
            if name in names:
                usage[tid][name].add(role)

        def visit(node, role="filter"):
            if isinstance(node, list):
                for child in node:
                    visit(child, role)
            elif isinstance(node, dict):
                for key, child in node.items():
                    if key == "_source":
                        for name in child if isinstance(child, list) else [child]:
                            if isinstance(name, str):
                                add(name, "output")
                    elif key == "sort":
                        if isinstance(child, str):
                            add(child, "order")
                        else:
                            visit(child, "order")
                    elif key == "field" and isinstance(child, str):
                        add(child, role)
                    else:
                        add(key, role)
                        visit(child, "calculation" if key in ("aggs", "aggregations") else role)

        visit(value)
        return usage

    def prepare(self, knowledge, *, method="tfidf", bm25_k1=1.5, bm25_b=0.75):
        # Imported only when this optional provider is used, never by the base matcher.
        from .bm25 import bm25_similarities

        active = [r for r in self.records if r["role_weight"] > 0]
        audit = {
            "provider": "training-sql-v1",
            "training_rows": len(self.rows),
            "role_weights": self.role_weights,
            "weight": self.weight,
            "record_count": len(self.records),
            "issues": self.issues,
            "field_profiles": {},
            "active_records": len(active),
            "method": method,
            "limitations": [
                "Training annotations are unverified weak evidence.",
                "Unresolved/ambiguous columns provide no field evidence.",
            ],
        }
        result = SupportResult(audit=audit)
        if not active or not knowledge:
            return result
        questions = list(dict.fromkeys(r["question"] for r in active))
        query_lookup = {question: i for i, question in enumerate(questions)}
        query_ids = np.array([query_lookup[r["question"]] for r in active])
        record_weights = np.array([r["role_weight"] for r in active])
        record_groups = defaultdict(list)
        for i, record in enumerate(active):
            record_groups[record["table_id"]].append(i)
        segments = []
        owners = []

        for item in knowledge:
            for segment in [item["knowledge_text"], *re.split(r"[。；;\n]", item["knowledge_text"])]:
                if _features(segment):
                    segments.append(segment)
                    owners.append(item["knowledge_id"])
        if not segments:
            return result
        profiles = {}
        if method == "bm25":
            similarities = bm25_similarities(questions, segments, _features, k1=bm25_k1, b=bm25_b)
        else:
            vectorizer = TfidfVectorizer(analyzer=_features, sublinear_tf=True, norm="l2")
            matrix = vectorizer.fit_transform(questions + segments)
            qvectors = matrix[: len(questions)]
            kvectors = matrix[len(questions) :]
            similarities = (qvectors @ kvectors.T).toarray()
            # Learn field-level question profiles from repeated observed uses.
            uses = defaultdict(list)
            for index, record in enumerate(active):
                for name, roles in record["fields"].items():
                    if max((self.role_weights.get(role, 0) for role in roles), default=0) > 0:
                        uses[(record["table_id"], name)].append(index)
            for pair, indices in uses.items():
                if (
                    len({active[i]["question_id"] for i in indices}) >= 2
                    and len({active[i]["question"] for i in indices}) >= 2
                ):
                    vector = normalize(np.asarray(qvectors[query_ids[indices]].mean(axis=0)))
                    profiles[pair] = (np.asarray(vector @ kvectors.T).ravel(), indices)
                    audit["field_profiles"][pair[0] + "/" + pair[1]] = {
                        "question_ids": sorted({active[i]["question_id"] for i in indices})
                    }
        segment_groups = defaultdict(list)
        for i, kid in enumerate(owners):
            segment_groups[kid].append(i)
        for kid, indices in segment_groups.items():
            query_scores = similarities[:, indices].max(axis=1)
            weighted_scores = query_scores[query_ids] * record_weights * self.weight
            for tid, record_indices in record_groups.items():
                index = max(record_indices, key=lambda i: weighted_scores[i])
                record = active[index]
                score = float(weighted_scores[index])
                if score > 0:
                    result.signals[(tid, kid)] = SupportSignal(
                        score,
                        (
                            {
                                "kind": "training_question_fields",
                                "similarity": float(query_scores[query_ids[index]]),
                                **{
                                    k: record[k]
                                    for k in ("question_id", "question", "query", "step", "fields", "role_weight")
                                },
                            },
                        ),
                    )
            for (tid, name), (scores, indices_used) in profiles.items():
                similarity = float(scores[indices].max())
                weight = max(self.role_weights.get(role, 0) for i in indices_used for role in active[i]["fields"][name])
                score = similarity * weight * self.weight
                pair = (tid, kid)
                if score > result.signals.get(pair, SupportSignal()).score:
                    result.signals[pair] = SupportSignal(
                        score,
                        (
                            {
                                "kind": "training_field_profile",
                                "field": name,
                                "profile_id": tid + "/" + name,
                                "question_count": len({active[i]["question_id"] for i in indices_used}),
                                "similarity": similarity,
                                "role_weight": weight,
                            },
                        ),
                    )
        return result
