"""Experimental namespace quotas using only explicit year/name matches in schema."""
# ruff: noqa: E402
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("six_for_namespace", Path(__file__).with_name("iteration_6k.py"))
six = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = six
spec.loader.exec_module(six)

from text2query.retrieval.context import ContextBuilder, round_robin


def mentioned_namespaces(question, candidates, tables):
    """A single registration year must not introduce an unrelated annual database."""
    years = set(re.findall(r"(?<!\d)(?:19|20)\d{2}(?!\d)", question))
    if len(years) < 2:
        return []
    parsed = {}
    for table in tables.values():
        ns = table.namespace
        match = re.fullmatch(r"(.+?)[_-]((?:19|20)\d{2})", ns or "")
        if match and match[2] in years:
            parsed[ns] = match[1]
    selected = {tables[c["table_id"]].namespace for c in candidates}
    stems = {parsed[ns] for ns in selected if ns in parsed}
    result = [ns for ns, stem in parsed.items() if stem in stems]
    return sorted(result) if len(result) > 1 else []


@dataclass(frozen=True)
class Parameters(six.Parameters):
    namespace_quota: int = 1

    def __post_init__(self):
        super().__post_init__()
        if self.namespace_quota not in (1, 2, 3):
            raise ValueError("namespace_quota must be 1/2/3")


class Builder(six.SixKBuilder):
    def assemble(self, question, engines, question_id=None, previous=None, requests=None):
        result = super().assemble(question, engines, question_id, previous, requests)
        namespaces = mentioned_namespaces(question, result["candidate_tables"], self.index.tables)
        if previous or requests or not namespaces:
            return result
        count = min(self.p.namespace_quota, self.p.tables // len(namespaces))
        groups = []
        for ns in namespaces:
            source_ids = ["schema:" + t.table_id for t in self.index.tables.values() if t.namespace == ns]
            hits = self.index.search(question, "schema", engines, count, source_ids=source_ids)
            groups.append([self.table(h["table_ids"][0], {**h, "selection_reason": "explicit_year_namespace_candidate"}) for h in hits])
        chosen = round_robin(groups, count * len(namespaces))
        ids = {t["table_id"] for t in chosen}
        chosen += [t for t in result["candidate_tables"] if t["table_id"] not in ids]
        chosen = chosen[:self.p.tables]
        result["candidate_tables"] = chosen
        keys = [t["table_id"] for t in chosen]
        result["relations"] = self.relations(keys, [e["source_id"] for e in result["examples"]])
        return result

    def _prune_once(self, context, preferred):
        namespaces = mentioned_namespaces(context["question"], context["candidate_tables"], self.index.tables)
        if not namespaces:
            return super()._prune_once(context, preferred)
        if self.p.pruning == "examples_first" and context["examples"]:
            removed = context["examples"].pop()
            context["omitted_evidence"].append(removed["source_id"])
            return removed["source_id"]
        protected = set()
        for namespace in namespaces:
            first = next((t["table_id"] for t in context["candidate_tables"]
                          if self.index.tables[t["table_id"]].namespace == namespace), None)
            if first:
                protected.add(first)
        for engine in context["initial_databases"]:
            first = next((t["table_id"] for t in context["candidate_tables"] if t["engine"] == engine), None)
            if first:
                protected.add(first)
        return ContextBuilder._prune_once(self, context, protected)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--public", type=Path, required=True)
    parser.add_argument("--grid", type=Path, required=True)
    parser.add_argument("--embedding-model", type=Path, required=True)
    parser.add_argument("--reranker-model", type=Path, required=True)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--dtype", default="bfloat16")
    args = parser.parse_args()
    if any(p.get("pruning") != "examples_first" for p in json.loads(args.grid.read_text())):
        raise ValueError("Namespace probes use an examples-first matched seed")
    six.v2.run(args, parameters_class=Parameters, builder_class=Builder, transform=six.compact,
               additional_sources=(Path(__file__), Path(six.__file__)), version="prompt-quality-6k-namespace-probe-v1")
