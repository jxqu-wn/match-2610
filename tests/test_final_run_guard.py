"""Protect the sole full-run opportunity and the existing submission file."""

from argparse import Namespace

import pytest

from evaluation.submission_quality import final_run
from text2query.io import file_sha256, read_json, write_json


@pytest.fixture(scope="session", autouse=True)
def prepared_catalog():
    yield


def prepared(tmp_path):
    root = tmp_path / "run"
    root.mkdir()
    questions = [{"question_id": i, "question": f"question {i}"} for i in range(1, 681)]
    old = [{"question_id": i, "db": "Elasticsearch" if i <= 50 else "MYSQL",
            "query": "{}" if i <= 50 else "SELECT 1"} for i in range(1, 681)]
    write_json(tmp_path / "questions.json", questions)
    write_json(root / "old_v6.original.json", old)
    write_json(tmp_path / "result.json", old)
    write_json(root / "initial_manifest.json", {"sources": {
        "test_questions": {"sha256": file_sha256(tmp_path / "questions.json")},
        "old_v6": {"sha256": file_sha256(root / "old_v6.original.json")}}})
    write_json(tmp_path / "bird.json", {"records": [{"question": f"question {i}", "submission_query": "SELECT 1",
        "bird": {"source": "original/train.json", "row_index": i}} for i in range(51, 129)]})
    write_json(root / "readiness.json", {"approved_for_full_generation": True, "selection_frozen_before_gate": True,
        "evidence_sha256": {str(tmp_path / "questions.json"): file_sha256(tmp_path / "questions.json")},
        "profile": {"name": "test"}})
    write_json(root / "working_state.json", {"full_generation_runs": 0})
    for name, value in (("catalog.json", {"tables": []}), ("knowledge.json", [])):
        write_json(root / "public" / name, value)
    (root / "public/documents.jsonl").write_text("")
    (root / "public/rules.txt").write_text("rules")
    args = Namespace(root=root, questions=tmp_path / "questions.json", bird_sources=tmp_path / "bird.json",
                     result=tmp_path / "result.json", workers=1, mysql_socket=tmp_path / "socket")
    final_run.prepare(args)
    return args


def test_readiness_required_before_any_full_run(tmp_path):
    write_json(tmp_path / "readiness.json", {"approved_for_full_generation": False})
    with pytest.raises(ValueError, match="have not approved"):
        final_run.checked_ready(tmp_path)


def test_missing_gpu_pools_does_not_spend_full_run_opportunity(tmp_path, monkeypatch):
    args = prepared(tmp_path)
    monkeypatch.setattr(final_run, "InputEstimator", lambda: None)
    monkeypatch.setattr(final_run.settings, "embedding_model", final_run.settings.embedding_model)
    with pytest.raises(ValueError, match="GPU evidence pools"):
        final_run.run(args)
    assert read_json(args.root / "working_state.json")["full_generation_runs"] == 0


def test_incomplete_generation_cannot_overwrite_existing_result(tmp_path):
    args = prepared(tmp_path)
    before = file_sha256(args.result)
    with pytest.raises(FileNotFoundError):
        final_run.export(args)
    assert file_sha256(args.result) == before


def test_packing_resume_requires_original_code_snapshot_and_pins_new_code(tmp_path):
    code = tmp_path / "module.py"
    code.write_text("original")
    archived = tmp_path / "original.py"
    archived.write_text(code.read_text())
    write_json(tmp_path / "readiness.json", {"approved_for_full_generation": True, "selection_frozen_before_gate": True,
        "evidence_sha256": {str(code): file_sha256(code)}})
    original_ready = file_sha256(tmp_path / "readiness.json")
    code.write_text("packing fix")
    with pytest.raises(ValueError, match="evidence changed"):
        final_run.checked_ready(tmp_path)
    write_json(tmp_path / "readiness-amendment.json", {"original_readiness_sha256": original_ready, "packing_fix_only": True,
        "original_evidence_replacements": {str(code): str(archived)}, "new_evidence_sha256": {str(code): file_sha256(code)}})
    assert final_run.checked_ready(tmp_path)["resume_amendment"]
    code.write_text("unfrozen second modification")
    with pytest.raises(ValueError, match="Amended code"):
        final_run.checked_ready(tmp_path)


def test_resume_amendment_cannot_replace_public_input_facts(tmp_path):
    source = tmp_path / "catalog.json"
    write_json(source, {"original": True})
    archived = tmp_path / "original.json"
    archived.write_bytes(source.read_bytes())
    write_json(tmp_path / "readiness.json", {"approved_for_full_generation": True, "selection_frozen_before_gate": True,
        "evidence_sha256": {str(source): file_sha256(source)}})
    original_ready = file_sha256(tmp_path / "readiness.json")
    write_json(source, {"fabricated": True})
    write_json(tmp_path / "readiness-amendment.json", {"original_readiness_sha256": original_ready, "packing_fix_only": True,
        "original_evidence_replacements": {str(source): str(archived)}, "new_evidence_sha256": {str(source): file_sha256(source)}})
    with pytest.raises(ValueError, match="evidence changed"):
        final_run.checked_ready(tmp_path)
