"""Deterministic table–knowledge matching from raw text only.

No reference labels, generated descriptions, model weights or remote calls are used.
TF-IDF is fitted on the current raw corpus; scores are lexical similarity evidence,
not a claim that a business rule is correct.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from ..models import Catalog, KnowledgeRef, Table
from .association_support import AssociationSupport, SupportResult, SupportSignal
from .bm25 import bm25_similarities
from .lexical import text_features as _features

ASSOCIATION_VERSION = "lexical-v1"
IDENTIFIER = r"[A-Za-z_][A-Za-z0-9_]*"


def literal_references(text: str, tables: dict[str, Table]) -> dict[str, list[dict[str, str]]]:
    """Resolve qualified names, scoped lists and unambiguous table.field mentions."""
    links: dict[str, list[dict[str, str]]] = {}
    counts = Counter(((t.namespace or "").casefold(), t.name.casefold()) for t in tables.values())

    def add(key, kind, mention):
        item = {"kind": kind, "mention": mention}
        if item not in links.setdefault(key, []):
            links[key].append(item)

    normalized = re.sub(r'[`"](' + IDENTIFIER + r')[`"]', r"\1", text)
    for key, t in tables.items():
        if t.namespace and counts[(t.namespace.casefold(), t.name.casefold())] == 1:
            pattern = (
                r"(?<![A-Za-z0-9_.])" + re.escape(t.namespace) + r"\s*\.\s*" + re.escape(t.name) + r"(?![A-Za-z0-9_])"
            )
            for m in re.finditer(pattern, normalized, re.I):
                add(key, "qualified_table", m.group())
    scopes = list(re.finditer(r"数据库\s*(" + IDENTIFIER + ")", normalized))
    for i, m in enumerate(scopes):
        region = normalized[m.end() : scopes[i + 1].start() if i + 1 < len(scopes) else len(normalized)]
        for key, t in tables.items():
            if not t.namespace or t.namespace.casefold() != m[1].casefold():
                continue
            if counts[(t.namespace.casefold(), t.name.casefold())] != 1:
                continue
            lists = re.findall(r"表\s*(" + IDENTIFIER + r"(?:\s*[和及与、,]\s*" + IDENTIFIER + ")*)", region)
            names = [v.casefold() for group in lists for v in re.findall(IDENTIFIER, group)]
            if t.name.casefold() in names or re.search(
                r"(?<![A-Za-z0-9_.])" + re.escape(t.name) + r"\s*表", region, re.I
            ):
                add(key, "database_scoped_table_name", m.group() + " … " + t.name)
    for m in re.finditer(
        r"(?<![A-Za-z0-9_.])(" + IDENTIFIER + r")\s*\.\s*(" + IDENTIFIER + r")(?![A-Za-z0-9_.])", normalized
    ):
        candidates = [
            key
            for key, t in tables.items()
            if t.name.casefold() == m[1].casefold() and m[2].casefold() in {c.name.casefold() for c in t.columns}
        ]
        if len(candidates) == 1:
            add(candidates[0], "unique_table_field", m.group())
    for key, t in tables.items():
        candidates = [v for v in tables.values() if v.name.casefold() == t.name.casefold()]
        if len(candidates) == 1:
            for m in re.finditer(r"(?<![A-Za-z0-9_.])" + re.escape(t.name) + r"\s*表", normalized, re.I):
                add(key, "unique_table_name", m.group())
    return links


def _contains(text, token):
    if re.fullmatch(IDENTIFIER, token):
        return bool(re.search(r"(?<![a-z0-9_])" + re.escape(token) + r"(?![a-z0-9_])", text, re.I))
    return token in text


def associate(
    catalog: Catalog,
    knowledge: list[dict[str, Any]],
    support: AssociationSupport | None = None,
    *,
    threshold: float = 0.3,
    method: str = "tfidf",
    bm25_k1: float = 1.5,
    bm25_b: float = 0.75,
) -> dict[str, Any]:
    """Replace associations, preserving raw descriptions; return auditable pair scores."""
    if method not in ("tfidf", "bm25"):
        raise ValueError("method must be tfidf or bm25")
    version = ASSOCIATION_VERSION if method == "tfidf" else "bm25-v1"
    if not 0 < threshold <= 1:
        raise ValueError("threshold must be in (0, 1]")
    tables = catalog.tables
    if len({t.table_id for t in tables}) != len(tables):
        raise ValueError("duplicate table_id")
    items = sorted(knowledge, key=lambda k: k["knowledge_id"])
    if len({k["knowledge_id"] for k in items}) != len(items):
        raise ValueError("duplicate knowledge_id")
    for t in tables:
        t.knowledge = []
    if not tables or not items:
        return {
            "version": version,
            "threshold": threshold,
            "pairs": [],
            "unlinked_knowledge_ids": [k["knowledge_id"] for k in items],
        }
    extension = (
        support.prepare(items, method=method, bm25_k1=bm25_k1, bm25_b=bm25_b)
        if support is not None
        else SupportResult()
    )
    facets, owners, kinds = [], [], []
    for i, t in enumerate(tables):
        values = [("schema", t.description or "")]
        values += [("schema", c.description or "") for c in t.columns]
        values += [("schema", str(v)) for v in (t.model_extra or {}).get("source_values", [])]
        for kind, text in values:
            if _features(text):
                facets.append(text)
                owners.append(i)
                kinds.append(kind)
    # Include only raw text; refitting is deterministic and has no label supervision.
    segments, segment_ids = [], []
    for item in items:
        start = len(segments)
        text = item["knowledge_text"]
        segments.extend([text, *[v for v in re.split(r"[。；;\n]", text) if len(_features(v)) >= 2]])
        segment_ids.append(list(range(start, len(segments))))
    matrix, bm25_scores = None, None
    if method == "bm25":
        bm25_scores = bm25_similarities(facets, segments, _features, k1=bm25_k1, b=bm25_b)
    else:
        corpus = facets + segments
        vectorizer = TfidfVectorizer(analyzer=_features, sublinear_tf=True, norm="l2")
        try:
            matrix = vectorizer.fit_transform(corpus)
        except ValueError as error:
            if "empty vocabulary" not in str(error):
                raise
    field_frequency = Counter(c.name.casefold() for t in tables for c in t.columns)
    schema_docs = [
        " ".join(
            [
                t.description or "",
                *[c.description or "" for c in t.columns],
                *map(str, (t.model_extra or {}).get("source_values", [])),
            ]
        )
        for t in tables
    ]
    vocab_frequency = Counter(v for text in schema_docs for v in set(_features(text)))
    # Enumerated values come exclusively from INSERT statements in the Schema.
    enums = {}
    for t in tables:
        values = set()
        for row in (t.model_extra or {}).get("source_values", []):
            values.update(v for v in row.split() if len(v) >= 2 and not v.isdigit())
        enums[t.table_id] = values
    enum_frequency = Counter(v for values in enums.values() for v in values)
    pairs, linked = [], set()
    facet_groups = {
        (i, kind): [n for n, (o, k) in enumerate(zip(owners, kinds, strict=True)) if o == i and k == kind]
        for i in range(len(tables))
        for kind in ("schema",)
    }
    by_id = catalog.by_id()
    for ki, item in enumerate(items):
        text = item["knowledge_text"]
        lower = text.casefold()
        explicit = literal_references(text, by_id)
        clauses = [(v, literal_references(v, by_id)) for v in re.split(r"[。；;\n]", text) if v]
        identifiers = {v for v in re.findall(IDENTIFIER, lower) if len(v) >= 3}
        matched_fields = identifiers & set(field_frequency)
        knowledge_features = set(_features(lower))
        if method == "bm25":
            similarities = bm25_scores[:, segment_ids[ki]].max(axis=1)
        else:
            similarities = (
                (matrix[: len(facets)] @ matrix[[len(facets) + n for n in segment_ids[ki]]].T).toarray().max(axis=1)
                if matrix is not None
                else np.zeros(len(facets))
            )
        for ti, t in enumerate(tables):
            fields = sorted(v for v in matched_fields if v in {c.name.casefold() for c in t.columns})
            # Widely shared identifiers cannot act as strong anchors on their own.
            weights = {v: math.log1p(len(tables) / field_frequency[v]) for v in matched_fields}
            field_coverage = sum(weights[v] for v in fields) / sum(weights.values()) if weights else 0.0
            specificity = max((1 / math.sqrt(field_frequency[v]) for v in fields), default=0)
            field_score = 0.9 * field_coverage * specificity
            unscoped = any(
                _contains(clause, field) and (not refs or t.table_id in refs)
                for field in fields
                for clause, refs in clauses
            )
            if explicit and t.table_id not in explicit and not unscoped:
                field_score *= 0.25
            best = {}
            for kind in ("schema",):
                ids = facet_groups[(ti, kind)]
                pos = max(ids, key=lambda n: similarities[n], default=None)
                best[kind] = (float(similarities[pos]), facets[pos]) if pos is not None else (0.0, "")
            # A raw uncommon phrase anchors cosine scores; generic suffix overlap is weak.
            shared = {
                v
                for v in knowledge_features
                if len(v) >= 2
                and vocab_frequency[v] > 0
                and vocab_frequency[v] <= max(2, len(tables) // 8)
                and _contains(schema_docs[ti].casefold(), v)
            }
            lexical = best["schema"][0] * (1.0 if shared else 0.4)
            signal = extension.signals.get((t.table_id, item["knowledge_id"]), SupportSignal())
            if not math.isfinite(signal.score) or not 0 <= signal.score <= 1:
                raise ValueError("support score must be finite and in [0, 1]")
            support_score = signal.score
            # Once a table is explicit, do not distribute incidental fields to other tables.
            if explicit and t.table_id not in explicit:
                support_score *= 0.6
                lexical *= 0.6
            enum_matches = sorted(
                v for v in enums[t.table_id] if _contains(lower, v.casefold()) and enum_frequency[v] <= 2
            )
            enum_score = min(0.75, 0.17 * len(enum_matches))
            # Dictionary evidence can support a declared referring field, not an
            # arbitrary foreign-key walk. Only raw exact values are propagated.
            fk_matches = []
            for fk in t.foreign_keys:
                values = enums.get(fk.references.table_id, set())
                hits = [v for v in values if _contains(lower, v.casefold()) and enum_frequency[v] <= 2]
                if len(hits) >= 2:
                    fk_matches.extend(hits)
            fk_score = min(0.6, 0.13 * len(set(fk_matches)))
            base_score = max(field_score, lexical, enum_score, fk_score)
            score = max(base_score, support_score)
            evidence = list(signal.evidence) if support_score > 0 else []
            if t.table_id in explicit:
                score = 1.0
                evidence += explicit[t.table_id]
            if enum_matches:
                evidence.append({"kind": "schema_values", "matches": enum_matches, "score": round(enum_score, 6)})
            if fk_matches:
                evidence.append(
                    {"kind": "foreign_key_values", "matches": sorted(set(fk_matches)), "score": round(fk_score, 6)}
                )
            if fields:
                evidence.append(
                    {
                        "kind": "field_tokens",
                        "fields": fields,
                        "coverage": round(field_coverage, 6),
                        "score": round(field_score, 6),
                    }
                )
            for kind in ("schema",):
                if best[kind][0] > 0:
                    evidence.append(
                        {
                            "kind": kind + "_" + method,
                            "similarity": round(best[kind][0], 6),
                            "source_text": best[kind][1],
                        }
                    )
            accepted = score >= threshold
            if accepted:
                t.knowledge.append(KnowledgeRef(**item))
                linked.add(item["knowledge_id"])
            if score > 0:
                pairs.append(
                    {
                        "table_id": t.table_id,
                        "knowledge_id": item["knowledge_id"],
                        "score": round(score, 6),
                        "accepted": accepted,
                        "components": {
                            "base": round(1.0 if t.table_id in explicit else base_score, 6),
                            "field": round(field_score, 6),
                            "schema": round(lexical, 6),
                            "support": round(support_score, 6),
                            "enum": round(enum_score, 6),
                            "foreign_key_enum": round(fk_score, 6),
                        },
                        "basis": "explicit" if t.table_id in explicit else "lexical_similarity",
                        "evidence": evidence,
                    }
                )
    return {
        "version": version,
        "threshold": threshold,
        "support": extension.audit or {"provider": "none"},
        "similarity_method": method,
        "bm25_parameters": {"k1": bm25_k1, "b": bm25_b, "normalization": "query_idf_upper_bound"}
        if method == "bm25"
        else None,
        "pairs": pairs,
        "unlinked_knowledge_ids": [k["knowledge_id"] for k in items if k["knowledge_id"] not in linked],
    }
