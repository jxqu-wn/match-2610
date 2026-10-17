"""Actual sent-context coverage and costs. Reference table IDs are score-only."""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

import numpy as np

from text2query.io import read_json, write_json


def summarize(root: Path, revision: str, phase: str, profile: str) -> dict:
    targets = read_json(root / "private_evaluation/targets.json")
    ids = read_json(root / "pilot.json")["ids"] if phase == "pilot" else read_json(root / "public/partition.json")[phase + "_ids"]
    directory = root / "inference" / revision / phase / profile
    details, groups = [], defaultdict(list)
    for qid in ids:
        path = directory / f"{qid}.json"
        if not path.exists():
            continue
        output = read_json(path)
        traces = output.get("trace", [])
        actual = [trace for trace in traces if trace.get("raw") and trace.get("purpose") not in {"literal_intent", "evidence_planning"}]
        body = read_body(actual[-1]) if actual else {}
        supplied = {table["table_id"] for table in body.get("schema", [])}
        required = set(targets[str(qid)]["table_ids"])
        required_dbs = {table.rsplit(".", 1)[0] for table in required}
        supplied_dbs = {table.rsplit(".", 1)[0] for table in supplied}
        calls = output.get("calls", [])
        row = {"question_id": qid, "topology": targets[str(qid)]["topology"], "generated": "answer" in output,
               "unresolved_source_evidence": output.get("review_status") == "unresolved_source_evidence",
               "complete_table": required <= supplied, "complete_database": required_dbs <= supplied_dbs,
               "missing_tables": sorted(required - supplied), "provided_table_count": len(supplied),
               "knowledge_count": len(body.get("knowledge", [])),
               "definition_dependency_candidate_count": len(body.get("definition_dependency_candidates", [])),
               "fragment_annotated_knowledge": sum("applicability" in item for item in body.get("knowledge", [])),
               "estimated_input_peak": max((trace.get("estimated_tokens", 0) for trace in traces), default=0),
               "actual_prompt_peak": max((call.get("usage", {}).get("prompt_tokens", 0) for call in calls), default=0),
               "uncached_calls": sum(call.get("finish_reason") != "cached" for call in calls),
               "uncached_prompt_tokens": sum(call.get("usage", {}).get("prompt_tokens", 0) for call in calls if call.get("finish_reason") != "cached"),
               "uncached_completion_tokens": sum(call.get("usage", {}).get("completion_tokens", 0) for call in calls if call.get("finish_reason") != "cached")}
        details.append(row)
        groups[row["topology"]].append(row)
    def aggregate(rows):
        return {"count": len(rows), "generated": sum(row["generated"] for row in rows),
                "unresolved_source_evidence": sum(row["unresolved_source_evidence"] for row in rows),
                "complete_table": sum(row["complete_table"] for row in rows),
                "complete_database": sum(row["complete_database"] for row in rows),
                "estimated_input_p95": float(np.percentile([row["estimated_input_peak"] for row in rows], 95)) if rows else None,
                "actual_prompt_max": max((row["actual_prompt_peak"] for row in rows), default=0)}
    result = {"expected": len(ids), "overall": aggregate(details), "by_topology": {group: aggregate(rows) for group, rows in groups.items()},
              "knowledge_metric": "available and applicability-annotated evidence, not proof the model used it correctly",
              "details": details}
    write_json(directory / "context_metrics.json", result)
    return result


def read_body(trace):
    import json
    return json.loads(trace["messages"][1]["content"])


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--root", type=Path, default=Path("outputs/experiments/single-submit-v1"))
    parser.add_argument("--revision", required=True)
    parser.add_argument("--phase", choices=["pilot", "development", "gate"], required=True)
    parser.add_argument("--profile", required=True)
    args = parser.parse_args()
    report = summarize(args.root, args.revision, args.phase, args.profile)
    print({"overall": report["overall"], "by_topology": report["by_topology"]})


if __name__ == "__main__":
    main()
