"""Bounded input packing; redundant source samples must not displace definitions."""

from __future__ import annotations

import json


def pack(messages, purpose, input_limit, estimator):
    messages = [dict(message) for message in messages]
    body = json.loads(messages[1]["content"])
    omitted = []
    while estimator(messages) > input_limit:
        if purpose != "evidence_planning" and "schema_directory" in body:
            body.pop("schema_directory")
            omitted.append("schema_directory_metadata")
        elif body.get("weak_training_examples"):
            omitted.append(body["weak_training_examples"].pop()["source_id"])
        elif len(body.get("training_case_scope_unverified", [])) > 3:
            omitted.append("training_case_scope:" + body["training_case_scope_unverified"].pop()["source_id"])
        elif "declared_fk_candidates_only" in body:
            body.pop("declared_fk_candidates_only")
            omitted.append("fk_candidate_metadata; original_schema_foreign_keys_preserved")
        elif purpose == "evidence_planning" and "retrieved_column_names" in body:
            body.pop("retrieved_column_names")
            omitted.append("planning_column_name_metadata; full_selected_schema_supplied_at_generation")
        elif "draft_plan_may_be_corrected" in body:
            body.pop("draft_plan_may_be_corrected")
            omitted.append("draft_plan_metadata")
        elif len(body.get("source_row_evidence", [])) > 2:
            rows = body["source_row_evidence"]
            # Retain the highest-ranked original match and an original
            # inconsistency example where present, without rewriting either.
            index = next((i for i in range(len(rows) - 1, 0, -1)
                          if rows[i].get("evidence_role") != "original_source_city_name_inconsistency"), len(rows) - 1)
            item = rows.pop(index)
            omitted.append(f"source_row:{item['source_sha256']}:{item['source_line']}")
        elif len(body.get("definition_dependency_candidates", [])) > 1:
            omitted.append("definition_dependency:" + body["definition_dependency_candidates"].pop()["source_id"])
        elif len(body.get("knowledge_candidates", body.get("knowledge", []))) > 1:
            name = "knowledge_candidates" if "knowledge_candidates" in body else "knowledge"
            omitted.append(body[name].pop()["source_id"])
        elif len(body.get("source_row_evidence", [])) > 1:
            item = body["source_row_evidence"].pop()
            omitted.append(f"source_row:{item['source_sha256']}:{item['source_line']}")
        else:
            raise ValueError(f"Required schema exceeds input budget {input_limit}; no partial-table truncation")
        messages[1]["content"] = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
    return messages, omitted


def affected_by_row_crowding(output: dict) -> bool:
    """Detect only the observed packing defect; never read SQL reference labels."""
    for trace in output.get("trace", []):
        if not any(item.startswith("knowledge:") for item in trace.get("omitted_whole_evidence", [])):
            continue
        body = json.loads(trace["messages"][1]["content"])
        if len(body.get("source_row_evidence", [])) > 2:
            return True
    return False
