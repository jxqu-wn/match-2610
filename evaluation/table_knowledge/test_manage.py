"""Structural integrity tests with synthetic labels, never production labels."""

import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import manage


class IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.validator = manage.Validator()
        self.batch = self.validator.manifest["batches"][0]
        self.response = self.empty_response(self.batch)

    def empty_response(self, batch):
        return {
            "tables": [{"table_id": tid, "knowledge": []} for tid in batch["target_table_ids"]],
            "audit": {
                "rubric_version": self.validator.manifest["rubric_version"],
                "batch_id": batch["batch_id"], "status": "complete", "input_issues": [],
                "reviewed_knowledge_ids": list(self.validator.knowledge),
                "table_audit": [{"table_id": tid, "accepted": [], "candidates": [], "content_issues": [], "needs_human_review": False}
                                for tid in batch["target_table_ids"]],
            },
        }

    def add_structural_fixture(self, response, basis="explicit"):
        """This pair is arbitrary: the validator deliberately cannot prove meaning."""
        kid = next(iter(self.validator.knowledge))
        text = self.validator.knowledge[kid]
        item = {"knowledge_id": kid, "basis": basis, "fields": [],
                "knowledge_evidence": [{"knowledge_id": kid, "quote": text[:12]}],
                "schema_evidence": [], "qualifiers": [], "reason": "Synthetic structural test fixture only."}
        if basis == "schema_supported":
            source = next(iter(self.validator.sources))
            item["schema_evidence"] = [{"source_file": source, "quote": self.validator.sources[source].splitlines()[0]}]
        response["tables"][0]["knowledge"] = [{"knowledge_id": kid, "knowledge_text": text}]
        response["audit"]["table_audit"][0]["accepted"] = [item]
        return item

    def check(self, response):
        validator = manage.Validator()
        validator.batch(response, self.batch)
        return validator.errors

    def test_current_original_sources_match_snapshot(self):
        self.validator.source_checks()
        self.assertEqual([], self.validator.errors)

    def test_empty_tables_are_valid(self):
        self.assertEqual([], self.check(self.response))

    def test_missing_table_rejected(self):
        self.response["tables"].pop()
        self.assertTrue(self.check(self.response))

    def test_coverage_declaration_must_include_all_knowledge(self):
        self.response["audit"]["reviewed_knowledge_ids"].pop()
        self.assertTrue(self.check(self.response))

    def test_altered_or_truncated_original_rejected(self):
        self.add_structural_fixture(self.response)
        self.response["tables"][0]["knowledge"][0]["knowledge_text"] += " altered"
        self.assertTrue(self.check(self.response))

    def test_fabricated_evidence_rejected(self):
        item = self.add_structural_fixture(self.response)
        item["knowledge_evidence"][0]["quote"] = "THIS IS NOT A SOURCE QUOTE"
        self.assertTrue(self.check(self.response))

    def test_field_of_another_table_rejected(self):
        item = self.add_structural_fixture(self.response)
        item["fields"] = ["nonexistent_column"]
        self.assertTrue(self.check(self.response))

    def test_schema_supported_requires_schema_evidence(self):
        self.add_structural_fixture(self.response)["basis"] = "schema_supported"
        self.assertTrue(self.check(self.response))

    def test_unreferenced_supplementary_knowledge_rejected(self):
        item = self.add_structural_fixture(self.response)
        other = next(k for k in self.validator.knowledge if k != item["knowledge_id"])
        item["knowledge_evidence"].append({"knowledge_id": other, "quote": self.validator.knowledge[other][:10]})
        self.assertTrue(self.check(self.response))

    def test_unresolved_pair_cannot_be_accepted_and_must_raise_review_flag(self):
        item = self.add_structural_fixture(self.response)
        row = self.response["audit"]["table_audit"][0]
        row["candidates"] = [{k: copy.deepcopy(item[k]) for k in ("knowledge_id", "knowledge_evidence", "reason")}]
        self.assertTrue(self.check(self.response))

    def test_freeze_compare_and_tamper_detection(self):
        with tempfile.TemporaryDirectory(prefix="table-knowledge-integrity-") as tmp:
            tmp = Path(tmp)
            source = tmp / "batches"
            values = [self.empty_response(b) for b in self.validator.manifest["batches"]]
            for batch, value in zip(self.validator.manifest["batches"], values, strict=True):
                manage.write(source / (batch["batch_id"] + ".json"), value)
            left, right = tmp / "left", tmp / "right"
            self.assertTrue(manage.freeze(source, left, "synthetic-left")["valid"])
            self.add_structural_fixture(values[0])
            manage.write(source / (self.batch["batch_id"] + ".json"), values[0])
            self.assertTrue(manage.freeze(source, right, "synthetic-right")["valid"])
            summary = manage.compare(left, right, tmp / "comparison")
            self.assertEqual(1, summary["right_only_pairs"])
            self.assertEqual(71, summary["both_empty_table_count"])
            queue = manage.read(tmp / "comparison" / "human_review.json")["items"]
            self.assertEqual("association_disagreement", queue[0]["kind"])
            self.assertEqual(values[0]["tables"][0]["knowledge"][0]["knowledge_text"], queue[0]["knowledge_text"])
            with self.assertRaises(ValueError):
                manage.freeze(source, right, "synthetic-right")
            path = right / "tables.json"
            path.write_text(path.read_text() + " ", encoding="utf-8")
            with self.assertRaises(ValueError):
                manage.frozen(right)

    def test_agreed_association_with_different_basis_is_queued(self):
        with tempfile.TemporaryDirectory(prefix="table-knowledge-basis-") as tmp:
            tmp = Path(tmp)
            source = tmp / "batches"
            values = [self.empty_response(b) for b in self.validator.manifest["batches"]]
            self.add_structural_fixture(values[0])
            for batch, value in zip(self.validator.manifest["batches"], values, strict=True):
                manage.write(source / (batch["batch_id"] + ".json"), value)
            manage.freeze(source, tmp / "left", "synthetic-left")
            self.add_structural_fixture(values[0], "schema_supported")
            manage.write(source / (self.batch["batch_id"] + ".json"), values[0])
            manage.freeze(source, tmp / "right", "synthetic-right")
            summary = manage.compare(tmp / "left", tmp / "right", tmp / "comparison")
            self.assertEqual(1, summary["basis_disagreements"])
            self.assertEqual(1, summary["accepted_by_both_pairs"])

    def clone_input(self, root):
        package = root / "evaluation" / "table_knowledge"
        package.mkdir(parents=True)
        for name in manage.INPUT_FILES:
            shutil.copyfile(manage.PACKAGE / name, package / name)
        manifest = self.validator.context["source_manifest"]
        paths = [manifest["knowledge_file"]] + [s["source_file"] for s in manifest["schema_sources"]]
        for name in paths:
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(manage.ROOT / name, target)
        return package

    def replace_context(self, package, context):
        manage.write(package / "input_context.json", {"context": context})
        batches = manage.read(package / "batches.json")
        batches["input_context_sha256"] = manage.digest(package / "input_context.json")
        manage.write(package / "batches.json", batches)

    def test_metadata_cannot_claim_72_tables_after_one_was_removed(self):
        with tempfile.TemporaryDirectory(prefix="table-knowledge-count-") as tmp:
            root = Path(tmp)
            package = self.clone_input(root)
            context = manage.read(package / "input_context.json")["context"]
            context["table_catalog"].pop()
            self.replace_context(package, context)
            batches = manage.read(package / "batches.json")
            batches["batches"][-1]["target_table_ids"].pop()
            manage.write(package / "batches.json", batches)
            validator = manage.Validator(package, root)
            validator.source_checks()
            self.assertTrue(any(e["at"].endswith("table_count") for e in validator.errors))

    def test_manifest_rubric_must_match_supported_source_rubric(self):
        with tempfile.TemporaryDirectory(prefix="table-knowledge-rubric-") as tmp:
            root = Path(tmp)
            package = self.clone_input(root)
            batches = manage.read(package / "batches.json")
            batches["rubric_version"] = "different-rubric"
            manage.write(package / "batches.json", batches)
            validator = manage.Validator(package, root)
            validator.source_checks()
            self.assertTrue(any("rubric" in e["message"] for e in validator.errors))

    def test_frozen_comparison_rejects_updated_input_with_the_same_ids(self):
        with tempfile.TemporaryDirectory(prefix="table-knowledge-version-") as tmp:
            root = Path(tmp)
            package = self.clone_input(root)
            with mock.patch.object(manage, "PACKAGE", package), mock.patch.object(manage, "ROOT", root):
                source = root / "responses"
                for batch in self.validator.manifest["batches"]:
                    manage.write(source / (batch["batch_id"] + ".json"), self.empty_response(batch))
                manage.freeze(source, root / "left", "synthetic-left")
                manage.freeze(source, root / "right", "synthetic-right")
                context = manage.read(package / "input_context.json")["context"]
                context["knowledge_context"][-1]["knowledge_text"] += " changed in v2"
                raw = root / context["source_manifest"]["knowledge_file"]
                manage.write(raw, context["knowledge_context"])
                context["source_manifest"]["knowledge_sha256"] = manage.digest(raw)
                self.replace_context(package, context)
                validator = manage.Validator()
                validator.source_checks()
                self.assertEqual([], validator.errors)
                with self.assertRaisesRegex(ValueError, "version differs"):
                    manage.compare(root / "left", root / "right", root / "comparison")

    def test_freeze_copies_validated_bytes_even_if_response_is_later_rewritten(self):
        with tempfile.TemporaryDirectory(prefix="table-knowledge-race-") as tmp:
            tmp = Path(tmp)
            source = tmp / "responses"
            for batch in self.validator.manifest["batches"]:
                manage.write(source / (batch["batch_id"] + ".json"), self.empty_response(batch))
            validated = manage.validate_directory(source)
            first = source / (self.batch["batch_id"] + ".json")
            manage.write(first, {"tables": [], "audit": {}})
            with mock.patch.object(manage, "validate_directory", return_value=validated):
                self.assertTrue(manage.freeze(source, tmp / "frozen", "synthetic")["valid"])
            manage.frozen(tmp / "frozen")
            self.assertEqual(6, len(manage.read(tmp / "frozen" / "batches" / first.name)["tables"]))


if __name__ == "__main__":
    unittest.main()
