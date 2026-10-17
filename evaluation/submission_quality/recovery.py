"""Audit and freeze a source-preserving packing fix within the existing full run."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from text2query.io import file_sha256, read_json, write_json
from text2query.submission.packing import affected_by_row_crowding


def needs_repacking(output: dict) -> bool:
    if affected_by_row_crowding(output):
        return True
    for trace in output.get("trace", []):
        removed = trace.get("omitted_whole_evidence", [])
        if any(value.startswith("source_row:") for value in removed):
            return True
        if any(value.startswith("definition_dependency:") for value in removed):
            body = json.loads(trace["messages"][1]["content"])
            if len(body.get("source_row_evidence", [])) > 2:
                return True
    return False


def prepare(root: Path):
    ready = read_json(root / "readiness.json")
    state = read_json(root / "working_state.json")
    if state["full_generation_runs"] != 1 or state["official_submissions_used"] != 0:
        raise ValueError("Expected one ongoing local full task and no website submission")
    replacements = {}
    for filename, expected in ready["evidence_sha256"].items():
        if file_sha256(Path(filename)) == expected:
            continue
        if Path(filename).name == "grounded.py":
            archived = root / "code-v11/submission/grounded.py"
        elif Path(filename).name == "final_run.py":
            archived = root / "code-v11/final_run.py"
        else:
            raise ValueError("Unexpected changed frozen evidence: " + filename)
        if file_sha256(archived) != expected:
            raise ValueError("Original code snapshot does not match frozen run")
        replacements[filename] = str(archived.resolve())
    keep, repair, reasons = {}, {}, {}
    for path in (root / "full/inference").glob("*.json"):
        if not path.stem.isdigit():
            continue
        output = read_json(path)
        affected = needs_repacking(output)
        if "answer" not in output or affected:
            repair[path.stem] = file_sha256(path)
            reasons[path.stem] = "generation_failed" if "answer" not in output else "sample_crowding_changes_packed_evidence"
        else:
            keep[path.stem] = file_sha256(path)
    value = {"original_readiness_sha256": file_sha256(root / "readiness.json"), "packing_fix_only": True,
             "created_at": datetime.now(timezone.utc).isoformat(),
             "reason": "Redundant original administrative samples displaced necessary recalled definitions; preserve two faithful samples before dropping knowledge",
             "original_evidence_replacements": replacements, "reuse_existing_sha256": keep,
             "repair_original_sha256": repair, "repair_reasons": reasons,
             "original_generation_version": "grounded-flash-v11", "resumed_generation_version": "grounded-flash-v12",
             "profile_changed": False, "raw_inputs_changed": False, "models_changed": False,
             "old_completed": len(keep) + len(repair), "keep_completed": len(keep), "repair_completed": len(repair),
             "missing": 552 - len(keep) - len(repair), "new_full_generation_run": False,
             "validation_revision": "v12", "validation_is_regression_after_fix": True}
    write_json(root / "packing_resume_plan.json", value)
    print({key: value[key] for key in ("old_completed", "keep_completed", "repair_completed", "missing")})


def freeze(root: Path):
    value = read_json(root / "packing_resume_plan.json")
    evidence = {filename: file_sha256(Path(filename)) for filename in value["original_evidence_replacements"]}
    for path in (Path("src/text2query/submission/packing.py"), Path(__file__), root / "verification_v12.log",
                 root / "verification_recovery_audit.log", root / "full/packing_fix_preview89.json"):
        evidence[str(path.resolve())] = file_sha256(path)
    for phase, count in (("development", 60), ("gate", 48)):
        context_path = root / f"inference/v12/{phase}/intent_review/context_metrics.json"
        judge_path = root / f"judgments/source-grounded-v7/v12/{phase}/intent_review/summary.json"
        context, judge = read_json(context_path), read_json(judge_path)
        if context["overall"]["generated"] != count or judge["completed_count"] != count:
            raise ValueError("Complete packing-fix regression evidence required")
        if any(judge["overall"].get(key) for key in ("judge_failed", "generation_failed")):
            raise ValueError("Unfinished regression verdicts")
        for path in (context_path, judge_path):
            evidence[str(path.resolve())] = file_sha256(path)
    probe = read_json(root / "full/repair-probe/89.json")
    if "answer" not in probe:
        raise ValueError("Observed production packing failure has not recovered")
    value["new_evidence_sha256"] = evidence
    path = root / "readiness-amendment.json"
    if path.exists():
        raise ValueError("Resume amendment is already frozen")
    write_json(path, value)
    print({"amendment_sha256": file_sha256(path), "full_generation_runs": 1, "website_submissions": 0})


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("command", choices=("prepare", "freeze"))
    parser.add_argument("--root", type=Path, default=Path("outputs/experiments/single-submit-v1"))
    args = parser.parse_args()
    {"prepare": prepare, "freeze": freeze}[args.command](args.root)


if __name__ == "__main__":
    main()
