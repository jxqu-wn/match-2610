"""Audit saved prompts against raw input facts; never used by inference."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def read(path):
    return json.loads(path.read_text())


def audit(root):
    public, out = root / "public", root / "inference"
    catalog = {t["table_id"]: t for t in read(public / "catalog.json")["tables"]}
    docs = {d["source_id"]: d for d in (json.loads(line) for line in (public / "documents.jsonl").open())}
    expected_ids = {q["question_id"] for q in read(public / "questions.json")}
    result = {}
    for folder in sorted((out / "runs").iterdir()):
        if not (folder / "complete.json").exists():
            continue
        errors = []
        seen = set()
        counts = {"tables": 0, "knowledge": 0, "examples": 0, "pruned_tables": 0, "pruned_knowledge": 0,
                  "unassociated_knowledge_preserved": 0, "value_sample_tables": 0}
        for line in (folder / "prompts.jsonl").open():
            row = json.loads(line)
            qid = row["question_id"]
            if qid in seen:
                errors.append([qid, "duplicate question"])
            seen.add(qid)
            c = row["context"]
            if json.loads(row["messages"][1]["content"]) != c:
                errors.append([qid, "actual message/context differs"])
            if row["estimated_tokens"] > row["parameters"]["input_budget"]:
                errors.append([qid, "input budget exceeded"])
            for t in c["candidate_tables"]:
                raw = catalog[t["table_id"]]
                wanted = [[col["name"], col["data_type"], col.get("nullable"), col.get("description")] for col in raw["columns"]]
                if [col[:4] for col in t["columns"]] != wanted:
                    errors.append([qid, "schema column facts changed", t["table_id"]])
                if t["primary_key"] != raw["primary_key"] or t["foreign_keys"] != raw["foreign_keys"]:
                    errors.append([qid, "schema key facts changed", t["table_id"]])
                if "source_values" in t:
                    counts["value_sample_tables"] += 1
                    if t["source_values"] != raw.get("source_values", [])[:row["parameters"]["value_samples"]]:
                        errors.append([qid, "value samples changed", t["table_id"]])
            for k in c["knowledge"]:
                raw = docs[k["source_id"]]
                if k["knowledge_id"] != raw["data"]["knowledge_id"] or k["knowledge_text"] != raw["data"]["knowledge_text"]:
                    errors.append([qid, "knowledge facts changed", k["source_id"]])
                if not raw["table_ids"]:
                    counts["unassociated_knowledge_preserved"] += 1
            for e in c["examples"]:
                raw = docs[e["source_id"]]["data"]
                if e["question"] != raw["question"] or e["steps"] != raw["steps"]:
                    errors.append([qid, "training example changed", e["source_id"]])
            counts["tables"] += len(c["candidate_tables"])
            counts["knowledge"] += len(c["knowledge"])
            counts["examples"] += len(c["examples"])
            counts["pruned_tables"] += len(set(row["before_budget_table_ids"]) - {t["table_id"] for t in c["candidate_tables"]})
            counts["pruned_knowledge"] += len(set(row["before_budget_knowledge_ids"]) - {k["knowledge_id"] for k in c["knowledge"]})
        if seen != expected_ids:
            errors.append([None, "question IDs differ from public inputs"])
        result[folder.name] = {"cases": len(seen), "fact_fidelity_errors": len(errors), "errors": errors, "totals": counts,
                               "average_counts": {key: counts[key] / len(seen) for key in ("tables", "knowledge", "examples")}}
    path = out / "fact_fidelity_audit.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"configurations": len(result), "cases": sum(r["cases"] for r in result.values()),
                      "fact_fidelity_errors": sum(r["fact_fidelity_errors"] for r in result.values()),
                      "audit_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}, ensure_ascii=False))
    if any(r["fact_fidelity_errors"] for r in result.values()):
        raise SystemExit("Fact fidelity audit failed; inspect error records")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    audit(parser.parse_args().root)
