"""One frozen full run, after development/gate review; never submits to a website.

Preserve the independently strong historical ES baseline and previously authorized
BIRD answers. Generate the remaining business queries without diagnostic AI SQL.
"""

from __future__ import annotations

import argparse
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from pathlib import Path

from text2query.config import settings
from text2query.io import canonical_json, file_sha256, read_json, read_jsonl, sha256_text, write_json
from text2query.models import Catalog
from text2query.submission.generate import InputEstimator
from text2query.submission.grounded import Profile, generate
from text2query.submission.integrity import validate_integrity
from text2query.submission.source_rows import SourceRows
from text2query.submission.training_bindings import TrainingBindings
from text2query.submission.validate import resolver_for, step_pairs

from .compile import compile_query
from .experiment import key


def checked_ready(root: Path) -> dict:
    ready = read_json(root / "readiness.json")
    if ready.get("approved_for_full_generation") is not True or ready.get("selection_frozen_before_gate") is not True:
        raise ValueError("Development and gate review have not approved a frozen full run")
    amendment_path = root / "readiness-amendment.json"
    amendment = read_json(amendment_path) if amendment_path.exists() else None
    if amendment is not None:
        if amendment.get("original_readiness_sha256") != file_sha256(root / "readiness.json") or amendment.get("packing_fix_only") is not True:
            raise ValueError("Invalid packing resume amendment")
    for filename, expected in ready["evidence_sha256"].items():
        if file_sha256(Path(filename)) == expected:
            continue
        archived = (amendment or {}).get("original_evidence_replacements", {}).get(filename)
        # Amendments can preserve old CODE in an immutable snapshot. Public
        # questions, schemas, raw facts and scored evidence cannot be replaced.
        if (Path(filename).suffix != ".py" or not archived
                or filename not in amendment.get("new_evidence_sha256", {})
                or file_sha256(Path(archived)) != expected):
            raise ValueError("Readiness evidence changed: " + filename)
    if amendment is not None:
        for filename, expected in amendment["new_evidence_sha256"].items():
            if file_sha256(Path(filename)) != expected:
                raise ValueError("Amended code/evidence changed: " + filename)
        ready = {**ready, "resume_amendment": amendment, "resume_amendment_sha256": file_sha256(amendment_path)}
    return ready


def prepare(args, *, retrieval_only=False):
    ready = {} if retrieval_only else checked_ready(args.root)
    initial = read_json(args.root / "initial_manifest.json")["sources"]
    if file_sha256(args.questions) != initial["test_questions"]["sha256"]:
        raise ValueError("Official questions changed since the historical baseline was frozen")
    if file_sha256(args.root / "old_v6.original.json") != initial["old_v6"]["sha256"]:
        raise ValueError("Historical baseline changed")
    rows = read_json(args.questions)
    if len(rows) != 680 or len({row["question_id"] for row in rows}) != 680 or any(set(row) != {"question_id", "question"} for row in rows):
        raise ValueError("Expected 680 unique public questions, without SQL labels")
    directory = args.root / "full"
    public = directory / "public"
    public.mkdir(parents=True, exist_ok=True)
    records = read_json(args.bird_sources)["records"]
    by_text = {record["question"].strip(): record for record in records}
    old = {row["question_id"]: row for row in read_json(args.root / "old_v6.original.json")}
    reused, questions = [], []
    for row in rows:
        qid = row["question_id"]
        if row["question"].strip() in by_text:
            record = by_text[row["question"].strip()]
            answer = {"question_id": qid, "db": "SQLite", "query": record["submission_query"]}
            reused.append({"answer": answer, "source": "previously_authorized_BIRD_original_SQL",
                           "source_file": record["bird"]["source"], "source_row": record["bird"]["row_index"]})
        elif old[qid].get("db") == "Elasticsearch":
            reused.append({"answer": old[qid], "source": "frozen_historical_ES_model_predictions",
                           "historical_submission_sha256": file_sha256(args.root / "old_v6.original.json"),
                           "historical_official_score": "113.25/114; 49/50 exact, as supplied by user"})
        else:
            questions.append(row)
    if len(reused) != 128 or len(questions) != 552:
        raise ValueError("Domain cache/source partition changed; review the inputs")
    manifest = {"official_questions_sha256": file_sha256(args.questions),
                "readiness_sha256": None if retrieval_only else file_sha256(args.root / "readiness.json"),
                "bird_sources_sha256": file_sha256(args.bird_sources), "profile": ready.get("profile"),
                "stage": "candidate_evidence_only" if retrieval_only else "frozen_generation",
                "source_sha256": {name: file_sha256(args.root / "public" / name)
                                  for name in ("catalog.json", "documents.jsonl", "knowledge.json", "rules.txt")},
                "business_llm_questions": len(questions), "reused": len(reused), "website_submissions": 0}
    target = directory / ("retrieval_manifest.json" if retrieval_only else "manifest.json")
    if target.exists() and read_json(target) != manifest:
        raise ValueError("Frozen full-run inputs changed; no second full run is permitted")
    write_json(target, manifest)
    write_json(public / "questions.json", questions)
    write_json(directory / "reused_answers.json", reused)
    for filename in ("catalog.json", "documents.jsonl", "knowledge.json", "rules.txt"):
        shutil.copyfile(args.root / "public" / filename, public / filename)
    source_rows_file = ready.get("source_rows_file") or getattr(args, "source_rows_file", None)
    if source_rows_file:
        shutil.copyfile(Path(source_rows_file), public / "source_rows.sql")
    print({"prepared_business_questions": len(questions), "BIRD": 78, "frozen_ES": 50, "LLM_requests_sent": 0})


def run(args):
    ready = checked_ready(args.root)
    directory = args.root / "full"
    manifest = read_json(directory / "manifest.json")
    if manifest["readiness_sha256"] != file_sha256(args.root / "readiness.json"):
        raise ValueError("Readiness changed after full-run preparation")
    state_path = args.root / "working_state.json"
    state = read_json(state_path)
    run_signature = sha256_text(canonical_json(manifest))
    if state.get("full_generation_runs", 0) and state.get("full_run_signature") != run_signature:
        raise ValueError("The single full-generation opportunity has already been used by a different frozen run")
    profile = Profile(**ready["profile"])
    public = directory / "public"
    catalog = Catalog.model_validate(read_json(public / "catalog.json"))
    documents = {row["source_id"]: row for row in read_jsonl(public / "documents.jsonl")}
    rules = (public / "rules.txt").read_text()
    source_rows = SourceRows(public / "source_rows.sql", catalog) if (public / "source_rows.sql").exists() else None
    training_usage = TrainingBindings(documents, catalog) if ready.get("training_usage") else None
    settings.embedding_model = settings.project_root.parent / "models/Qwen3-Embedding-0.6B"
    estimator = InputEstimator()
    rows = read_json(public / "questions.json")
    missing = [row["question_id"] for row in rows if not (directory / "pools" / f"{row['question_id']}.json").exists()]
    if missing:
        raise ValueError(f"Complete GPU evidence pools required before generation; missing {len(missing)}")
    runtime = read_json(directory / "runtime.json")
    for name in ("questions", "documents"):
        suffix = "jsonl" if name == "documents" else "json"
        if runtime[name + "_sha256"] != file_sha256(public / f"{name}.{suffix}"):
            raise ValueError("GPU evidence does not match frozen " + name)
    if runtime.get("gpu_required") is not True or runtime.get("question_set") != "official":
        raise ValueError("Official GPU retrieval provenance is required")
    for row in rows:
        if read_json(directory / "pools" / f"{row['question_id']}.json")["row"] != row:
            raise ValueError("GPU pool question changed: " + str(row["question_id"]))
    if state.get("full_generation_runs", 0) == 0:
        state.update(full_generation_runs=1, full_run_signature=run_signature)
        write_json(state_path, state)
    amendment = ready.get("resume_amendment", {})
    if amendment:
        digest = ready["resume_amendment_sha256"]
        if state.get("packing_resume_amendment_sha256", digest) != digest:
            raise ValueError("The full run already resumed with a different amendment")
        state.update(packing_resume_amendment_sha256=digest,
                     partial_resume_invocations=state.get("partial_resume_invocations", 0) + 1)
        write_json(state_path, state)

    def extra_validator(answer):
        errors = []
        for db, query in step_pairs(answer):
            if answer[db] == "MYSQL":
                result = compile_query(answer[query], args.mysql_socket)
                if not result["ok"]:
                    errors.append("MySQL编译失败：" + result["error"])
        return errors

    completed, pending = [], []
    for row in rows:
        path = directory / "inference" / f"{row['question_id']}.json"
        qid = str(row["question_id"])
        reuse_digest = amendment.get("reuse_existing_sha256", {}).get(qid)
        if reuse_digest:
            if file_sha256(path) != reuse_digest:
                raise ValueError("Preserved successful answer changed: " + qid)
            old = read_json(path)
            if old["row"] != row or old["profile"] != asdict(profile) or validate_integrity(old.get("answer"), row, resolver_for(catalog.by_id())):
                raise ValueError("Invalid preserved successful answer: " + qid)
            completed.append(old)
            continue
        prior_digest = amendment.get("repair_original_sha256", {}).get(qid)
        if path.exists() and prior_digest and file_sha256(path) == prior_digest:
            archived = directory / "pre-packing-fix/inference" / path.name
            archived.parent.mkdir(parents=True, exist_ok=True)
            if archived.exists() and file_sha256(archived) != prior_digest:
                raise ValueError("Original repair trace changed: " + qid)
            shutil.copyfile(path, archived)
            path.unlink()
        pending.append(row)
    print({"reused_successful": len(completed), "pending_or_affected": len(pending),
           "full_generation_runs": state["full_generation_runs"]}, flush=True)
    progress = {"finished": len(completed), "total": len(rows), "success": sum("answer" in row for row in completed),
                "failed_ids": [row["row"]["question_id"] for row in completed if "answer" not in row]}
    write_json(directory / "progress.json", progress)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(generate, row, read_json(directory / "pools" / f"{row['question_id']}.json"),
                               documents, catalog, rules, profile, directory / "inference", key(), estimator, extra_validator, source_rows, training_usage)
                   for row in pending]
        for future in as_completed(futures):
            completed.append(future.result())
            progress = {"finished": len(completed), "total": len(rows), "success": sum("answer" in row for row in completed),
                        "failed_ids": [row["row"]["question_id"] for row in completed if "answer" not in row]}
            write_json(directory / "progress.json", progress)
            print(progress, flush=True)
    write_json(directory / "generation_complete.json", progress)


def export(args):
    checked_ready(args.root)
    directory = args.root / "full"
    answers = {row["answer"]["question_id"]: row["answer"] for row in read_json(directory / "reused_answers.json")}
    provenance = {row["answer"]["question_id"]: row for row in read_json(directory / "reused_answers.json")}
    catalog = Catalog.model_validate(read_json(directory / "public/catalog.json"))
    resolver = resolver_for(catalog.by_id())
    for row in read_json(directory / "public/questions.json"):
        generated = read_json(directory / "inference" / f"{row['question_id']}.json")
        if "answer" not in generated:
            raise ValueError("Unfinished answer: " + str(row["question_id"]))
        errors = validate_integrity(generated["answer"], row, resolver)
        if errors:
            raise ValueError(str(errors))
        answers[row["question_id"]] = generated["answer"]
        provenance[row["question_id"]] = {"source": "new_grounded_deepseek_flash", "profile": generated["profile"],
                                         "generation_version": generated.get("generation_version", read_json(args.root / "readiness.json")["revision"]),
                                         "trace_path": str(directory / "inference" / f"{row['question_id']}.json")}
    rows = read_json(args.questions)
    if set(answers) != {row["question_id"] for row in rows}:
        raise ValueError("Missing or extra official question IDs")
    result = [answers[row["question_id"]] for row in rows]
    state_path = args.root / "working_state.json"
    state = read_json(state_path)
    initial_hash = file_sha256(args.root / "old_v6.original.json")
    expected_current = state.get("final_result_exported_sha256", initial_hash)
    if args.result.exists() and file_sha256(args.result) != expected_current:
        raise ValueError("result.json was changed externally; do not overwrite it")
    write_json(args.result, result)
    state["final_result_exported_sha256"] = file_sha256(args.result)
    write_json(state_path, state)
    write_json(directory / "result_provenance.json", provenance)
    write_json(directory / "export.json", {"result": str(args.result), "sha256": file_sha256(args.result),
               "questions": len(result), "generation_profile": asdict(Profile(**read_json(args.root / "readiness.json")["profile"])),
               "website_submissions": 0, "official_score": None,
               "packing_resume_amendment_sha256": state.get("packing_resume_amendment_sha256"),
               "full_generation_runs": state["full_generation_runs"]})
    print({"questions": len(result), "sha256": file_sha256(args.result), "website_submissions": 0})


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("command", choices=["prepare-retrieval", "prepare", "generate", "export"])
    parser.add_argument("--root", type=Path, default=Path("outputs/experiments/single-submit-v1"))
    parser.add_argument("--questions", type=Path, default=Path("../data/QA_test.json"))
    parser.add_argument("--bird-sources", type=Path, default=Path("outputs/qa_test_680_hybrid06b_deepseek_flash_v1/bird_match_sources.json"))
    parser.add_argument("--result", type=Path, default=Path("result.json"))
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--mysql-socket", type=Path, default=Path("/tmp/match-v6-single-submit-mariadb/socket"))
    parser.add_argument("--source-rows-file", type=Path)
    args = parser.parse_args()
    if args.command == "prepare-retrieval":
        prepare(args, retrieval_only=True)
    else:
        {"prepare": prepare, "generate": run, "export": export}[args.command](args)


if __name__ == "__main__":
    main()
