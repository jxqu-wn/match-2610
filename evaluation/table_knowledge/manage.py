"""Validate, freeze and compare independent references; never import preprocessing.

Uses the Python standard library. Evidence checks establish source fidelity,
not whether a model's semantic decision is correct.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parents[1]
RUBRIC_VERSION = "table-knowledge-reference-v2"
INPUT_FILES = ("input_context.json", "batches.json", "system_prompt.md", "user_prompt.template.md")


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def input_hashes(package=None):
    package = Path(package or PACKAGE)
    return {name: digest(package / name) for name in INPUT_FILES}


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class Validator:
    def __init__(self, package=None, root=None):
        self.package, self.root = Path(package or PACKAGE), Path(root or ROOT)
        self.input_files = input_hashes(self.package)
        self.context = read(self.package / "input_context.json")["context"]
        self.manifest = read(self.package / "batches.json")
        self.knowledge = {x["knowledge_id"]: x["knowledge_text"] for x in self.context["knowledge_context"]}
        self.tables = {x["table_id"]: x for x in self.context["table_catalog"]}
        self.sources = {x["source_file"]: x["text"] for x in self.context["schema_sources"]}
        self.errors = []

    def error(self, at, message):
        self.errors.append({"at": at, "message": message})

    def keys(self, value, required, at):
        if not isinstance(value, dict):
            self.error(at, "expected object")
            return False
        if set(value) != set(required.split()):
            self.error(at, "expected exactly these keys: " + required)
        return True

    def array(self, obj, key, at):
        value = obj.get(key)
        if not isinstance(value, list):
            self.error(at + "." + key, "expected array")
            return []
        return value

    def source_checks(self):
        expected = self.manifest["input_context_sha256"]
        if digest(self.package / "input_context.json") != expected:
            self.error("input_context", "snapshot hash differs from batches.json")
        source_manifest = self.context["source_manifest"]
        for at, manifest in (("batches", self.manifest), ("source_manifest", source_manifest)):
            if manifest.get("rubric_version") != RUBRIC_VERSION:
                self.error(at, "unsupported or inconsistent rubric version")
            for key, actual in (("table_count", len(self.context["table_catalog"])), ("knowledge_count", len(self.context["knowledge_context"]))):
                if manifest.get(key) != actual:
                    self.error(at + "." + key, "declared count differs from actual input")
        if len(self.tables) != len(self.context["table_catalog"]) or len(self.knowledge) != len(self.context["knowledge_context"]):
            self.error("context", "duplicate table or knowledge IDs")
        if self.manifest.get("batch_count") != len(self.manifest["batches"]):
            self.error("batches.batch_count", "declared count differs from actual batches")
        batch_ids = [b["batch_id"] for b in self.manifest["batches"]]
        if len(batch_ids) != len(set(batch_ids)):
            self.error("batches", "duplicate batch IDs")
        size = self.manifest.get("tables_per_batch")
        if type(size) is not int or size <= 0 or any(not 0 < len(b["target_table_ids"]) <= size for b in self.manifest["batches"]):
            self.error("batches", "invalid batch size")
        actual_sources = [{key: record[key] for key in ("source_file", "encoding", "sha256")} for record in self.context["schema_sources"]]
        if source_manifest["schema_sources"] != actual_sources or len(self.sources) != len(actual_sources):
            self.error("schema_sources", "source lists differ or contain duplicate paths")
        records = [{"source_file": source_manifest["knowledge_file"], "sha256": source_manifest["knowledge_sha256"]}]
        records += source_manifest["schema_sources"]
        for record in records:
            path = self.root / record["source_file"]
            if not path.is_file() or digest(path) != record["sha256"]:
                self.error(str(path), "raw source missing or hash differs from snapshot")
        for record in self.context["schema_sources"]:
            path = self.root / record["source_file"]
            if path.is_file() and path.read_bytes().decode(record["encoding"]) != record["text"]:
                self.error(record["source_file"], "decoded source differs from snapshot")
        raw_path = self.root / source_manifest["knowledge_file"]
        if raw_path.is_file() and read(raw_path) != self.context["knowledge_context"]:
            self.error("knowledge_context", "original knowledge entries differ from snapshot")
        targets = [t for b in self.manifest["batches"] for t in b["target_table_ids"]]
        if targets != list(self.tables) or len(targets) != len(set(targets)):
            self.error("batches", "batch targets must cover the catalogue exactly once, in order")
        if input_hashes(self.package) != self.input_files:
            self.error("inputs", "inputs changed during validation")

    def evidence(self, item, at, allow_conflict=False):
        own = item.get("knowledge_id")
        text = self.knowledge.get(own)
        if text is None:
            self.error(at, "unknown knowledge_id")
            return
        evidence = self.array(item, "knowledge_evidence", at)
        if not any(isinstance(e, dict) and e.get("knowledge_id") == own for e in evidence):
            self.error(at, "must quote the item's own knowledge")
        for i, e in enumerate(evidence):
            where = f"{at}.knowledge_evidence[{i}]"
            if not self.keys(e, "knowledge_id quote", where):
                continue
            source = self.knowledge.get(e.get("knowledge_id"))
            quote = e.get("quote")
            if source is None or not isinstance(quote, str) or not quote or quote not in source:
                self.error(where, "quote must be a nonempty exact substring of the identified knowledge")
            other = e.get("knowledge_id")
            if other != own and not allow_conflict and not re.search(rf"(?<!\d){re.escape(str(other))}(?!\d)", text):
                self.error(where, "supplementary knowledge ID is not mentioned by the primary knowledge")
        if not isinstance(item.get("reason"), str) or not item["reason"].strip():
            self.error(at, "nonempty reason required")

    def ordered_ids(self, items, at):
        ids = [x.get("knowledge_id") if isinstance(x, dict) else None for x in items]
        if any(type(x) is not int for x in ids) or len(ids) != len(set(ids)):
            self.error(at, "knowledge IDs must be unique integers")
        elif ids != sorted(ids):
            self.error(at, "knowledge IDs must be sorted")
        return ids

    def batch(self, value, batch):
        label = batch["batch_id"]
        if not self.keys(value, "tables audit", label):
            return
        tables = self.array(value, "tables", label)
        targets = batch["target_table_ids"]
        if [x.get("table_id") if isinstance(x, dict) else None for x in tables] != targets:
            self.error(label, "main table IDs/order differ from batch targets")
        audit = value.get("audit")
        if not self.keys(audit, "rubric_version batch_id status input_issues reviewed_knowledge_ids table_audit", label + ".audit"):
            return
        for key, expected in (("rubric_version", self.manifest["rubric_version"]), ("batch_id", label), ("status", "complete"), ("input_issues", []), ("reviewed_knowledge_ids", list(self.knowledge))):
            if audit.get(key) != expected:
                self.error(label + ".audit." + key, "does not match the complete input/batch contract")
        audits = self.array(audit, "table_audit", label + ".audit")
        if [x.get("table_id") if isinstance(x, dict) else None for x in audits] != targets:
            self.error(label, "audit table IDs/order differ from batch targets")
        for table in tables:
            at = label + ".tables"
            if not self.keys(table, "table_id knowledge", at):
                continue
            tid = table.get("table_id")
            if tid not in self.tables:
                continue
            at = label + "." + tid
            entries = self.array(table, "knowledge", at)
            ids = self.ordered_ids(entries, at)
            for entry in entries:
                if self.keys(entry, "knowledge_id knowledge_text", at):
                    kid = entry.get("knowledge_id")
                    if kid not in self.knowledge or entry.get("knowledge_text") != self.knowledge[kid]:
                        self.error(at + "." + str(kid), "knowledge_text must equal the full unchanged original")
            matches = [x for x in audits if isinstance(x, dict) and x.get("table_id") == tid]
            if len(matches) != 1:
                continue
            row = matches[0]
            self.keys(row, "table_id accepted candidates content_issues needs_human_review", at + ".audit")
            accepted = self.array(row, "accepted", at)
            candidates = self.array(row, "candidates", at)
            issues = self.array(row, "content_issues", at)
            accepted_ids = self.ordered_ids(accepted, at + ".accepted")
            candidate_ids = self.ordered_ids(candidates, at + ".candidates")
            if ids != accepted_ids:
                self.error(at, "main knowledge IDs and audit accepted IDs must match")
            if set(accepted_ids) & set(candidate_ids):
                self.error(at, "a pair cannot be both accepted and unresolved")
            if type(row.get("needs_human_review")) is not bool or row.get("needs_human_review") != bool(candidates or issues):
                self.error(at, "needs_human_review must equal bool(candidates or content_issues)")
            for item in accepted:
                if not self.keys(item, "knowledge_id basis fields knowledge_evidence schema_evidence qualifiers reason", at + ".accepted"):
                    continue
                where = at + ".accepted." + str(item.get("knowledge_id"))
                self.evidence(item, where)
                if item.get("basis") not in ("explicit", "schema_supported"):
                    self.error(where, "invalid basis")
                fields = self.array(item, "fields", where)
                if any(f not in self.tables[tid]["columns"] for f in fields) or len(fields) != len(set(fields)):
                    self.error(where, "fields must be unique actual fields of this table")
                schema = self.array(item, "schema_evidence", where)
                if item.get("basis") == "schema_supported" and not schema:
                    self.error(where, "schema_supported requires original Schema evidence")
                for e in schema:
                    if self.keys(e, "source_file quote", where + ".schema_evidence"):
                        source = self.sources.get(e.get("source_file"), "")
                        quote = e.get("quote")
                        if not isinstance(quote, str) or not quote or quote not in source:
                            self.error(where, "Schema quote is not an exact source substring")
                primary = self.knowledge.get(item.get("knowledge_id"), "")
                for quote in self.array(item, "qualifiers", where):
                    if not isinstance(quote, str) or not quote or quote not in primary:
                        self.error(where, "qualifier must be an exact quote of the primary knowledge")
            for item in candidates:
                if self.keys(item, "knowledge_id knowledge_evidence reason", at + ".candidates"):
                    self.evidence(item, at + ".candidates." + str(item.get("knowledge_id")))
            for item in issues:
                if not self.keys(item, "knowledge_id kind knowledge_evidence related_knowledge_ids reason", at + ".content_issues"):
                    continue
                where = at + ".content_issues." + str(item.get("knowledge_id"))
                self.evidence(item, where, allow_conflict=True)
                if item.get("knowledge_id") not in accepted_ids + candidate_ids:
                    self.error(where, "content issue must concern an accepted or candidate pair")
                if item.get("kind") not in ("incomplete_rule", "conflicting_content", "missing_reference", "ambiguous_reference"):
                    self.error(where, "invalid content issue kind")
                if any(type(k) is not int for k in self.array(item, "related_knowledge_ids", where)):
                    self.error(where, "related knowledge IDs must be integers")

    def directory(self, directory):
        self.source_checks()
        responses = []
        directory = Path(directory)
        for batch in self.manifest["batches"]:
            path = directory / (batch["batch_id"] + ".json")
            try:
                raw = path.read_bytes()
                value = json.loads(raw.decode("utf-8"))
            except (OSError, ValueError) as exc:
                self.error(str(path), str(exc))
                continue
            self.batch(value, batch)
            responses.append((path, value, raw))
        return responses


def statistics(tables, audits, all_ids):
    linked = {k["knowledge_id"] for t in tables for k in t["knowledge"]}
    return {
        "table_count": len(tables),
        "knowledge_count": len(all_ids),
        "nonempty_tables": sum(bool(t["knowledge"]) for t in tables),
        "accepted_pairs": sum(len(t["knowledge"]) for t in tables),
        "basis_counts": dict(Counter(k["basis"] for t in audits for k in t["accepted"])),
        "linked_knowledge_count": len(linked),
        "unlinked_knowledge_ids": [k for k in all_ids if k not in linked],
        "candidate_pairs": sum(len(t["candidates"]) for t in audits),
        "content_issue_reports": sum(len(t["content_issues"]) for t in audits),
    }


def validate_directory(directory):
    validator = Validator()
    responses = validator.directory(directory)
    report = {"valid": not validator.errors, "validated_batches": len(responses), "errors": validator.errors,
              "limitations": ["Checks source fidelity and structural coverage, not semantic correctness or actual reading of all pairs."]}
    if not validator.errors:
        tables = [t for _, value, _ in responses for t in value["tables"]]
        audits = [t for _, value, _ in responses for t in value["audit"]["table_audit"]]
        report["statistics"] = statistics(tables, audits, list(validator.knowledge))
    return validator, responses, report


def freeze(directory, output, annotator):
    validator, responses, report = validate_directory(directory)
    if not report["valid"]:
        return report
    output = Path(output)
    if output.exists():
        raise ValueError("freeze output already exists; use a new version rather than overwriting")
    tables = [t for _, value, _ in responses for t in value["tables"]]
    audits = [t for _, value, _ in responses for t in value["audit"]["table_audit"]]
    write(output / "tables.json", {"tables": tables})
    write(output / "audit.json", {"rubric_version": validator.manifest["rubric_version"], "status": "complete",
                                  "batch_ids": [v["audit"]["batch_id"] for _, v, _ in responses],
                                  "reviewed_knowledge_ids": list(validator.knowledge), "table_audit": audits})
    write(output / "validation.json", report)
    for path, _, raw in responses:
        destination = output / "batches" / path.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)
    # Bind this freeze to the exact input version used by the validator.
    if input_hashes(validator.package) != validator.input_files:
        raise ValueError("inputs changed during freeze; partial output has no completed manifest")
    files = sorted(p for p in output.rglob("*") if p.is_file())
    write(output / "manifest.json", {
        "annotator": annotator,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "rubric_version": validator.manifest["rubric_version"],
        "input_files": validator.input_files,
        "files": {str(path.relative_to(output)): digest(path) for path in files},
        "statistics": report["statistics"],
        "status": "independent_reference_frozen_not_human_adjudicated",
    })
    return report


def frozen(path):
    path = Path(path)
    manifest = read(path / "manifest.json")
    if manifest.get("input_files") != input_hashes() or manifest.get("rubric_version") != RUBRIC_VERSION:
        raise ValueError(f"{path}: frozen input/prompt version differs from the current package")
    expected_files = {"tables.json", "audit.json", "validation.json"}
    expected_files.update("batches/" + b["batch_id"] + ".json" for b in read(PACKAGE / "batches.json")["batches"])
    if set(manifest["files"]) != expected_files:
        raise ValueError(f"{path}: incomplete frozen file manifest")
    for name, expected in manifest["files"].items():
        if digest(path / name) != expected:
            raise ValueError(f"{path / name}: frozen hash changed")
    _, responses, report = validate_directory(path / "batches")
    if not report["valid"]:
        raise ValueError(f"{path}: frozen batches failed current source validation: {report['errors']}")
    tables, audit = read(path / "tables.json")["tables"], read(path / "audit.json")
    if tables != [t for _, value, _ in responses for t in value["tables"]] or audit["table_audit"] != [t for _, value, _ in responses for t in value["audit"]["table_audit"]]:
        raise ValueError(f"{path}: merged files differ from frozen batches")
    return manifest, tables, audit["table_audit"]


def compare(left, right, output):
    lm, lt, la = frozen(left)
    rm, rt, ra = frozen(right)
    if lm["input_files"] != rm["input_files"] or lm["rubric_version"] != rm["rubric_version"]:
        raise ValueError("the two references used different source/prompt versions")
    output = Path(output)
    if output.exists():
        raise ValueError("comparison output exists; use a new version")
    result, queue, agreements, empty = [], [], [], []
    for ltab, rtab, laudit, raudit in zip(lt, rt, la, ra, strict=True):
        tid = ltab["table_id"]
        if rtab["table_id"] != tid or laudit["table_id"] != tid or raudit["table_id"] != tid:
            raise ValueError("table order mismatch")
        ls = {x["knowledge_id"]: x for x in laudit["accepted"]}
        rs = {x["knowledge_id"]: x for x in raudit["accepted"]}
        basis = [k for k in sorted(ls.keys() & rs.keys()) if ls[k]["basis"] != rs[k]["basis"]]
        lonly, ronly = sorted(ls.keys() - rs.keys()), sorted(rs.keys() - ls.keys())
        result.append({"table_id": tid, "left_only": lonly, "right_only": ronly, "basis_disagreements": basis,
                       "accepted_by_both": sorted(ls.keys() & rs.keys())})
        for k in sorted(ls.keys() & rs.keys()):
            agreements.append({"table_id": tid, "knowledge_id": k, "left": ls[k], "right": rs[k]})
        if not ls and not rs:
            empty.append(tid)
        for k in sorted(set(lonly + ronly + basis)):
            queue.append({"table_id": tid, "knowledge_id": k, "kind": "association_disagreement" if k not in basis else "basis_disagreement",
                          "left": ls.get(k), "right": rs.get(k), "human_decision": None})
        for side, a in (("left", laudit), ("right", raudit)):
            for category in ("candidates", "content_issues"):
                for item in a[category]:
                    queue.append({"table_id": tid, "knowledge_id": item["knowledge_id"], "kind": category,
                                  "reported_by": side, "annotation": item, "human_decision": None})
    all_ids = [k["knowledge_id"] for k in read(PACKAGE / "input_context.json")["context"]["knowledge_context"]]
    linked = {k["knowledge_id"] for t in lt + rt for k in t["knowledge"]}
    report = {"left_annotator": lm["annotator"], "right_annotator": rm["annotator"], "tables": result,
              "summary": {"table_count": len(result), "left_only_pairs": sum(len(t["left_only"]) for t in result),
                          "right_only_pairs": sum(len(t["right_only"]) for t in result), "basis_disagreements": sum(len(t["basis_disagreements"]) for t in result),
                          "accepted_by_both_pairs": len(agreements), "both_empty_table_count": len(empty), "human_review_reports": len(queue)},
              "status": "compared_not_adjudicated"}
    write(output / "comparison.json", report)
    texts = {k["knowledge_id"]: k["knowledge_text"] for k in read(PACKAGE / "input_context.json")["context"]["knowledge_context"]}
    for item in queue:
        item["knowledge_text"] = texts[item["knowledge_id"]]
    write(output / "human_review.json", {"items": queue})
    write(output / "agreement_audit.json", {"accepted_by_both": agreements, "both_empty_tables": empty,
          "knowledge_unlinked_by_both": [{"knowledge_id": k, "knowledge_text": texts[k]} for k in all_ids if k not in linked],
          "instruction": "Agreement and mutual omission require review; agreement is not human adjudication."})
    lines = ["# 待人审项目", "", "此文件只汇总独立标注的分歧、候选及内容问题，尚未裁定。完整证据见 human_review.json。", ""]
    for item in queue:
        lines.extend([f"- `{item['table_id']}` / {item['knowledge_id']} / {item['kind']}", ""])
    if not queue:
        lines.append("没有主动报告的争议。仍需审核 agreement_audit.json 中的一致项与双方遗漏。")
    (output / "human_review.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report["summary"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate")
    validate.add_argument("directory", type=Path)
    validate.add_argument("--report", type=Path)
    freeze_parser = commands.add_parser("freeze")
    freeze_parser.add_argument("directory", type=Path)
    freeze_parser.add_argument("--output-dir", type=Path, required=True)
    freeze_parser.add_argument("--annotator", required=True)
    comparison = commands.add_parser("compare")
    comparison.add_argument("left", type=Path)
    comparison.add_argument("right", type=Path)
    comparison.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "compare":
            result = compare(args.left, args.right, args.output_dir)
        elif args.command == "freeze":
            result = freeze(args.directory, args.output_dir, args.annotator)
        else:
            _, _, result = validate_directory(args.directory)
            if args.report:
                write(args.report, result)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(2, str(exc) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("valid", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
