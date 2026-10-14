"""Export the reviewed target; this module is not a preprocessing matcher."""

import argparse
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory

from manage import PACKAGE, compare, digest, frozen, read, write


def build(output):
    runs = PACKAGE / "runs"
    left = runs / "codex-independent-v1/frozen"
    right = runs / "flash-independent-v1/frozen"
    review = runs / "comparison-v1"
    output = Path(output)
    if output.exists():
        raise ValueError("reference output exists; use a new version")
    lm, lt, la = frozen(left)
    rm, rt, ra = frozen(right)
    # Reproduce comparison, including source hashes and coverage validation.
    with TemporaryDirectory() as tmp:
        fresh = Path(tmp) / "comparison"
        compare(left, right, fresh)
        for name in ("comparison.json", "human_review.json", "agreement_audit.json"):
            if read(fresh / name) != read(review / name):
                raise ValueError(f"stale comparison: {name}")

    decisions = read(review / "decisions.json")
    reports = read(review / "human_review.json")["items"]
    report_pairs = {(r["table_id"], r["knowledge_id"]) for r in reports}
    texts = {k["knowledge_id"]: k["knowledge_text"] for k in
             read(PACKAGE / "input_context.json")["context"]["knowledge_context"]}
    links = {}
    for tables, audits, side in ((lt, la, "codex"), (rt, ra, "flash")):
        for table, audit in zip(tables, audits, strict=True):
            tid = table["table_id"]
            for annotation in audit["accepted"]:
                pair = (tid, annotation["knowledge_id"])
                links.setdefault(pair, {"initial_acceptance": {}, "decision": None})[
                    "initial_acceptance"][side] = annotation

    seen, indices, review_ids = set(), [], set()
    for decision in decisions["items"]:
        pair = (decision["table_id"], decision["knowledge_id"])
        if pair in seen or pair not in report_pairs or decision["review_id"] in review_ids:
            raise ValueError("duplicate or unknown review unit")
        seen.add(pair)
        review_ids.add(decision["review_id"])
        if decision["decision"] != "resolved" or not decision.get("reason"):
            raise ValueError("unresolved decision")
        action = decision["association_decision"]
        if action not in (None, "accept", "reject"):
            raise ValueError("invalid association decision")
        if action == "accept" and decision["accepted_basis"] not in ("explicit", "schema_supported"):
            raise ValueError("accepted association lacks basis")
        if action != "accept" and decision["accepted_basis"] is not None:
            raise ValueError("non-accepted association has basis")
        for number in decision["source_report_numbers"]:
            if type(number) is not int or not 1 <= number <= len(reports):
                raise ValueError("invalid report number")
            report = reports[number - 1]
            if (report["table_id"], report["knowledge_id"]) != pair:
                raise ValueError("report pair mismatch")
            if report["kind"] in ("association_disagreement", "basis_disagreement", "candidates") and action is None:
                raise ValueError("association report has no association decision")
            indices.append(number)
        if action == "reject":
            links.pop(pair, None)
        elif action == "accept":
            links.setdefault(pair, {"initial_acceptance": {}})["decision"] = decision
        elif pair in links:
            links[pair]["decision"] = decision
    if seen != report_pairs or sorted(indices) != list(range(1, len(reports) + 1)):
        raise ValueError("review coverage mismatch")

    tables, associations = [], []
    for table in lt:
        tid = table["table_id"]
        ids = sorted(kid for table_id, kid in links if table_id == tid)
        tables.append({"table_id": tid, "knowledge": [
            {"knowledge_id": kid, "knowledge_text": texts[kid]} for kid in ids]})
        for kid in ids:
            source = links[(tid, kid)]
            decision = source["decision"]
            basis = (decision["accepted_basis"] if decision and decision["association_decision"] == "accept"
                     else next(iter(source["initial_acceptance"].values()))["basis"])
            associations.append({"table_id": tid, "knowledge_id": kid, "basis": basis,
                                 "provenance": decision["decision_source"] if decision else "both_annotators",
                                 **source})
    statistics = {"table_count": len(tables), "knowledge_count": len(texts),
                  "accepted_pairs": len(associations),
                  "nonempty_tables": sum(bool(t["knowledge"]) for t in tables),
                  "basis_counts": dict(Counter(a["basis"] for a in associations)),
                  "review_units": len(seen), "pending_units": 0}
    write(output / "tables.json", {"tables": tables})
    write(output / "audit.json", {"associations": associations, "decisions": decisions,
                                   "limitations": ["Agreement carried forward is not individual human review.",
                                                   "Association acceptance does not resolve every content issue."]})
    sources = [left / "manifest.json", right / "manifest.json", review / "decisions.json",
               review / "comparison.json", review / "human_review.json", PACKAGE / "input_context.json"]
    write(output / "manifest.json", {"reference_version": output.name,
          "status": "llm_and_user_reviewed_target", "statistics": statistics,
          "input_files": lm["input_files"],
          "source_files": {str(p.relative_to(PACKAGE)): digest(p) for p in sources},
          "files": {name: digest(output / name) for name in ("tables.json", "audit.json")},
          "builder_sha256": digest(Path(__file__))})
    return statistics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(build(args.output_dir))
