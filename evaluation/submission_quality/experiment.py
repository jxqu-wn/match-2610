"""Frozen development/gate experiment; SQL references used by judge only.

No command in this module generates the official 680-question submission.
"""

from __future__ import annotations

import argparse
import collections
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from pathlib import Path

from dotenv import dotenv_values

from text2query.config import settings
from text2query.io import canonical_json, file_sha256, read_json, read_jsonl, sha256_text, write_json
from text2query.llm.client import ChatClient
from text2query.models import Catalog
from text2query.retrieval.sql_parser import SourceResolver
from text2query.submission.evidence import compact_table
from text2query.submission.generate import InputEstimator
from text2query.submission.grounded import Profile, generate, knowledge_items, planning_messages
from text2query.submission.source_rows import SourceRows
from text2query.submission.training_bindings import TrainingBindings
from text2query.submission.validate import step_pairs

PROFILES = [
    Profile("direct_plain", output_limit=4000),
    Profile("direct_thinking", thinking=True),
    Profile("planned_thinking", planned=True, thinking=True),
    Profile("planned_review", planned=True, thinking=True, review=True),
    Profile("intent_review", planned=True, thinking=True, review=True, intent_first=True),
    Profile("intent_review_high", planned=True, thinking=True, review=True, intent_first=True,
            reasoning_effort="high", output_limit=20000),
]

JUDGE = """你是严格的Text-to-SQL语义评审。比较匿名候选查询与原始问题，并参考原始训练SQL、真实Schema、原始知识和口径。输出JSON。
原始训练参考可能含错误，不能将不一致自动判为候选错。先判参考是否符合问题，再判候选是否符合问题，最后判二者能否在所有符合Schema约束的数据上等价。不要把当前数据偶然相同当语义等价。没有实际业务数据，不能声称执行准确率。
核对输出列数、统计对象/粒度、过滤/时间/边界、空值、去重、连接倍增、分母、排序和跨系统值传递。允许别名变化、逻辑等价的JOIN/EXISTS和合法方言改写。对问题确实未规定的解释或资料冲突标记uncertain，给出具体理由。SQL语法/字段合法不等于语义正确。
判断术语阈值时必须查看给出的原始知识，不能因题目没写具体阈值就标记来源不明。知识自身的限定条件必须被题目激活；不能把某类统计专用条件变成所有查询的默认条件，也不能凭常识给原本已代表所问实体的数据表额外添加资质/状态限制。
只有能指明题目、Schema或原始知识的明确冲突，才将reference_status标为question_conflict；不能因设想另一种业务解释就否定参考。业务称谓可能已由实体表及原始训练语境表示，缺少更细分类定义不意味着应该猜一个字符串LIKE条件。候选额外增加过滤时，必须有原文绑定依据；否则不能判faithful。对整数脚本除法应检查语言类型语义，不能因表达式长得相似就忽略截断误差。
源资料中某类证书、部门、项目等的分类，不能逆推为其所属主体的必要分类条件或等价定义；需检查新增约束的蕴含方向。训练表用法证据只帮助判断数据集中的称谓与字段使用，不保证训练SQL业务逻辑全对。
比例不必然是乘100后的百分数，须依据题目及适用原始公式的单位判断，不可用通常经验追加要求。题目未指定年份且存在平行年度库时，参考只使用某一年不能单独证明题意已限定该年；应报告原题歧义及二者不等价。原始知识明确标为本库特殊定义时，按本库定义核对，不能用现实业务常识否定它。
返回{"reference_status":"supported或question_conflict或invalid或ambiguous","candidate_status":"faithful或incorrect或uncertain","equivalent":true或false或null,"reason":"具体语义依据","defects":["候选实质问题"],"source_issues":["参考或资料的问题"]}。"""


def inputs(root):
    public = root / "public"
    manifest = read_json(public / "input_manifest.json")
    for name, digest in manifest["files"].items():
        if file_sha256(public / name) != digest:
            raise ValueError("Public input changed: " + name)
    rows = read_json(public / "questions.json")
    if any(set(row) != {"question_id", "question"} for row in rows):
        raise ValueError("Private label in generation questions")
    return rows, Catalog.model_validate(read_json(public / "catalog.json")), {
        doc["source_id"]: doc for doc in read_jsonl(public / "documents.jsonl")}, (public / "rules.txt").read_text()


def key():
    values = dotenv_values(settings.project_root.parent / ".env")
    return values.get("API_KEY") or values.get("DEEPSEEK_API_KEY") or settings.api_key


def profile_named(name):
    return next(profile for profile in PROFILES if profile.name == name)


def phase_ids(args):
    partition = read_json(args.root / "public/partition.json")
    if args.phase == "pilot":
        return read_json(args.root / "pilot.json")["ids"]
    return partition[args.phase + "_ids"]


def prepare(args):
    rows, catalog, docs, rules = inputs(args.root)
    targets = read_json(args.root / "private_evaluation/targets.json")
    partition = read_json(args.root / "public/partition.json")
    groups = collections.defaultdict(list)
    for qid in partition["development_ids"]:
        groups[targets[str(qid)]["topology"]].append(qid)
    # Known diagnostic cases belong to development only; IDs affect experiment
    # sampling, never retrieval, prompt facts or production generation rules.
    known = {1208, 1853, 1919, 1996, 2487, 2942, 2980, 3012, 183, 1587}
    pilot = []
    for _group, ids in sorted(groups.items()):
        ids.sort(key=lambda qid: (qid not in known, sha256_text(str(qid))))
        pilot += ids[:3]
    write_json(args.root / "pilot.json", {"ids": sorted(pilot), "development_only": True})
    write_json(args.root / "experiment_protocol.json", {
        "profiles": [asdict(profile) for profile in PROFILES], "pilot_ids": sorted(pilot),
        "development": 60, "gate": 48, "gate_used_for_tuning": False,
        "website_submissions": 0, "full_680_generation": False,
        "references_in_generation": False, "judge_model": "deepseek-flash, separate reference-visible scoring only if authorized",
        "limitations": "Validation set previously studied; LLM semantic review is not independent human review or actual business execution.",
    })
    row = rows[0]
    pool = read_json(args.root / "pools" / f"{row['question_id']}.json")
    write_json(args.root / "planning_prompt_preview.json", planning_messages(row, pool, docs, catalog, rules))
    refs = {row["question_id"]: row for row in read_json(args.references)}
    write_json(args.root / "private_evaluation/scoring_prompt_preview.json", {
        "system": JUDGE, "question": row,
        "reference": refs[row["question_id"]], "candidate": "Injected only after the generation answer is frozen",
        "warning": "Contains reference SQL: only allowed in separate judge request, never generation/server retrieval",
    })
    print({"pilot": pilot, "profiles": [profile.name for profile in PROFILES]})


def run(args):
    rows, catalog, docs, rules = inputs(args.root)
    selected = set(phase_ids(args))
    rows = [row for row in rows if row["question_id"] in selected]
    profile = profile_named(args.profile)
    directory = args.root / "inference" / args.revision / args.phase / profile.name
    directory.mkdir(parents=True, exist_ok=True)
    settings.embedding_model = settings.project_root.parent / "models/Qwen3-Embedding-0.6B"
    estimator = InputEstimator()
    source_rows = SourceRows(args.source_rows_file, catalog) if args.source_rows_file else None
    training_usage = TrainingBindings(docs, catalog) if args.training_usage else None
    complete = []
    api_key = key()
    if not api_key:
        raise ValueError("No API key in .env")
    extra_validator = None
    if args.mysql_socket:
        from .compile import compile_query

        def extra_validator(answer):
            errors = []
            for db, query in step_pairs(answer):
                if answer[db] == "MYSQL":
                    result = compile_query(answer[query], args.mysql_socket)
                    if not result["ok"]:
                        errors.append("MySQL编译失败：" + result["error"])
            return errors
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(generate, row, read_json((args.pools or args.root / "pools") / f"{row['question_id']}.json"),
                               docs, catalog, rules, profile, directory, api_key, estimator, extra_validator, source_rows, training_usage) for row in rows]
        for future in as_completed(futures):
            output = future.result()
            complete.append(output)
            progress = {"profile": profile.name, "phase": args.phase, "finished": len(complete), "total": len(rows),
                        "success": sum("answer" in row for row in complete),
                        "failed_ids": [row["row"]["question_id"] for row in complete if "answer" not in row]}
            write_json(directory / "progress.json", progress)
            print(json.dumps(progress), flush=True)
    write_json(directory / "complete.json", progress)


def judge_one(row, output, reference, catalog, rules, source_knowledge, auxiliary_evidence, directory, api_key):
    path = directory / f"{row['question_id']}.json"
    if "answer" not in output:
        result = {"question_id": row["question_id"], "candidate_status": "generation_failed", "error": output.get("error")}
        write_json(path, result)
        return result
    tables = catalog.by_id()
    resolver = SourceResolver(tables)
    selected = set()
    for answer in (output["answer"], reference):
        for db, query in step_pairs(answer):
            selected.update(resolver.parse(answer[query], answer[db]).get("table_ids", []))
    payload = {"question": row, "candidate": output["answer"], "training_reference": reference,
               "schema": [compact_table(tables[key]) for key in sorted(selected)], "knowledge": source_knowledge, "rules": rules}
    payload.update(auxiliary_evidence)
    messages = [{"role": "system", "content": JUDGE},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False, separators=(",", ":"))}]
    signature = sha256_text(canonical_json({"messages": messages, "model": "deepseek-flash",
                                          "thinking": "low", "limits": [12000, 18000, 24000]}))
    if path.exists():
        old = read_json(path)
        if old.get("signature") == signature and old.get("candidate_status") in {"faithful", "incorrect", "uncertain"}:
            return old
    client = ChatClient(model="deepseek-flash", api_key=api_key, thinking=True, reasoning_effort="low", timeout=300,
                        cache_dir=directory.parent / "judge_cache", default_headers={"Accept-Encoding": "identity"})
    trace = []
    value = None
    try:
        for attempt, limit in enumerate((12000, 18000, 24000)):
            raw = client.complete(messages, limit, "blinded_reference_visible_semantic_judge")
            trace.append({"raw": raw, "output_limit": limit, "call": client.calls[-1].as_dict()})
            if client.calls[-1].finish_reason not in {"stop", "cached"}:
                continue
            try:
                value = json.loads(raw)
                if not isinstance(value, dict) or value.get("candidate_status") not in {"faithful", "incorrect", "uncertain"}:
                    raise ValueError("Missing valid semantic verdict")
                break
            except ValueError as error:
                trace[-1]["json_error"] = str(error)[:160]
                value = None
                messages[1]["content"] = json.dumps({**payload, "response_repair": "只输出一个合法JSON对象并包含candidate_status、reference_status、equivalent和reason", "repair_attempt": attempt + 1}, ensure_ascii=False, separators=(",", ":"))
    except Exception as error:  # noqa: BLE001 - preserve other completed judgments
        trace.append({"error_type": type(error).__name__})
    result = {"question_id": row["question_id"], "signature": signature,
              **(value or {"candidate_status": "judge_failed", "reason": "No valid complete verdict after bounded retries"}),
              "calls": [call.as_dict() for call in client.calls], "messages": messages, "trace": trace}
    write_json(path, result)
    if client.cache is not None:
        client.cache.close()
    return result


def judge(args):
    rows, catalog, docs, rules = inputs(args.root)
    selected = set(phase_ids(args))
    rows = [row for row in rows if row["question_id"] in selected]
    if args.completed_only:
        if args.phase == "gate":
            raise ValueError("Gate scoring requires the entire frozen set")
        rows = [row for row in rows if (args.root / "inference" / args.revision / args.phase / args.profile / f"{row['question_id']}.json").exists()]
    references = {row["question_id"]: row for row in read_json(args.references)}
    source_rows = SourceRows(args.source_rows_file, catalog) if args.source_rows_file else None
    usage = TrainingBindings(docs, catalog) if args.training_usage else None
    directory = args.root / "judgments" / args.judge_revision / args.revision / args.phase / args.profile
    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(judge_one, row, read_json(args.root / "inference" / args.revision / args.phase / args.profile / f"{row['question_id']}.json"),
                               references[row["question_id"]], catalog, rules,
                               knowledge_items(read_json(args.root / "pools" / f"{row['question_id']}.json"), docs, catalog.by_id(), 48),
                               {"source_row_evidence": source_rows.match(row["question"]) if source_rows is not None else [],
                                "training_literal_usage_unverified": usage.match(row["question"]) if usage is not None else [],
                                "training_case_scope_unverified": usage.scope_examples(read_json((args.pools or args.root / "pools") / f"{row['question_id']}.json").get("examples", [])) if usage is not None else []},
                               directory, key()) for row in rows]
        for future in as_completed(futures):
            results.append(future.result())
            print({"judged": len(results), "total": len(rows), "profile": args.profile}, flush=True)
    targets = read_json(args.root / "private_evaluation/targets.json")
    report = {"overall": dict(collections.Counter(row["candidate_status"] for row in results)), "by_topology": {},
              "judge_revision": args.judge_revision,
              "expected_count": len(selected), "completed_count": len(rows),
              "reference_status": dict(collections.Counter(row.get("reference_status", "not_scored") for row in results)),
              "raw_reference_equivalence": dict(collections.Counter(str(row.get("equivalent")) for row in results)),
              "metric": "Flash semantic judgment, no business-data execution accuracy claimed"}
    mysql = [row for row in results if targets[str(row["question_id"])]["engines"] == ["MYSQL"]]
    report["mysql_only"] = {"count": len(mysql),
                            "faithfulness": dict(collections.Counter(row["candidate_status"] for row in mysql)),
                            "raw_reference_equivalence": dict(collections.Counter(str(row.get("equivalent")) for row in mysql)),
                            "supported_reference_equivalence": dict(collections.Counter(str(row.get("equivalent")) for row in mysql if row.get("reference_status") == "supported"))}
    for topology in {row["topology"] for row in targets.values()}:
        report["by_topology"][topology] = dict(collections.Counter(row["candidate_status"] for row in results
                                      if targets[str(row["question_id"])]["topology"] == topology))
    write_json(directory / ("partial_summary.json" if len(rows) != len(selected) else "summary.json"), report)
    print(json.dumps(report, ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("command", choices=["prepare", "generate", "judge"])
    parser.add_argument("--root", type=Path, default=Path("outputs/experiments/single-submit-v1"))
    parser.add_argument("--references", type=Path, default=Path("outputs/experiments/prompt-quality-6k-v1/private_evaluation/references.json"))
    parser.add_argument("--phase", choices=["pilot", "development", "gate"], default="pilot")
    parser.add_argument("--profile", choices=[profile.name for profile in PROFILES], default="direct_plain")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--revision", default="v2")
    parser.add_argument("--judge-revision", default="source-grounded-v7")
    parser.add_argument("--completed-only", action="store_true")
    parser.add_argument("--mysql-socket", type=Path)
    parser.add_argument("--source-rows-file", type=Path)
    parser.add_argument("--training-usage", action="store_true")
    parser.add_argument("--pools", type=Path)
    args = parser.parse_args()
    {"prepare": prepare, "generate": run, "judge": judge}[args.command](args)


if __name__ == "__main__":
    main()
