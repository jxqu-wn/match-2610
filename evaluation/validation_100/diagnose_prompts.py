"""Export exact failed-case requests and evidence-based offline attribution.

No generation, external services, model loading, or production-rule updates.
The notes are tied to the frozen review-pack hash; changed answers require a
new review version. Reference queries are used only in this evaluation module.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LABELS = {
    "prompt_evidence_gap": "输入证据缺失主导",
    "prompt_conflict": "规则或案例冲突",
    "mixed": "输入与模型处理混合",
    "model_following": "已有证据未被模型正确利用",
    "underdetermined": "题目、参考或数据口径尚不能裁定",
}


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def block(value) -> str:
    return "```json\n" + json.dumps(value, ensure_ascii=False, indent=2) + "\n```"


def run(args: argparse.Namespace) -> None:
    source, output = args.source.resolve(), args.output.resolve()
    if source == output or source in output.parents:
        raise ValueError("Choose an output outside the frozen source experiment")
    notes = read(args.notes)
    if sha(source / "evaluation/review_pack.json") != notes["source_review_pack_sha256"]:
        raise ValueError("Queries changed: old diagnostic notes cannot be replayed")
    frozen_hashes = read(source / "artifact_sha256.json")
    if any(sha(source / name) != digest for name, digest in frozen_hashes.items()):
        raise ValueError("Frozen experiment artifact changed")
    source_details = read(source / "evaluation/non_equivalent_cases.json")
    native = {
        d["question_id"]: d
        for d in map(json.loads, (source / "evaluation/details.jsonl").read_text().splitlines())
    }
    by_id = {d["question_id"]: d for d in source_details}
    assert len(by_id) == len(notes["cases"]) == 40
    assert set(by_id) == {n["question_id"] for n in notes["cases"]}
    knowledge = {k["knowledge_id"]: k for k in read(REPO / "data/赛题8/knowledge.json")}
    documents = {
        d["source_id"]: d
        for d in map(
            json.loads,
            (REPO / "outputs/experiments/preprocessing-prompt-coverage-v1/hybrid-0.6b/index/documents.jsonl")
            .read_text()
            .splitlines(),
        )
    }
    fingerprint = {
        "notes_sha256": sha(args.notes),
        "source_artifacts_sha256": sha(source / "artifact_sha256.json"),
        "source_review_pack_sha256": sha(source / "evaluation/review_pack.json"),
        "knowledge_source_sha256": sha(REPO / "data/赛题8/knowledge.json"),
    }
    prior = output / "manifest.json"
    if prior.exists() and read(prior)["input_fingerprint"] != fingerprint:
        raise ValueError("Diagnostic inputs changed; choose a new output version")
    output.mkdir(parents=True, exist_ok=True)
    rows, prompts = [], []
    for note in notes["cases"]:
        qid = note["question_id"]
        original = source / "cases" / str(qid)
        folder = output / "cases" / str(qid)
        folder.mkdir(parents=True, exist_ok=True)
        request_path = original / "06_generation/request_01.json"
        response_path = original / "06_generation/response_01.json"
        request = read(request_path)
        prepared = read(original / "05_initial_messages.json")
        assert request["messages"] == prepared
        context = json.loads(request["messages"][1]["content"])
        assert context == read(original / "04_context_after_budget.json")
        examples = {e["question_id"]: e for e in context["examples"]}
        supplied_knowledge = {k["knowledge_id"]: k for k in context["knowledge"]}
        assert set(note["examples"]) <= examples.keys()
        assert set(note["knowledge"]) <= supplied_knowledge.keys()
        assert not set(note["missing_knowledge"]) & supplied_knowledge.keys()
        assert note["primary"] in LABELS
        assert all(supplied_knowledge[kid]["knowledge_text"] == knowledge[kid]["knowledge_text"] for kid in note["knowledge"])
        witnesses = {
            "examples_in_actual_prompt": [
                {key: examples[eid][key] for key in ("question_id", "question", "steps")}
                for eid in note["examples"]
            ],
            "knowledge_in_actual_prompt": [knowledge[kid] for kid in note["knowledge"]],
            "raw_knowledge_not_in_actual_prompt": [
                {
                    **knowledge[kid],
                    "frozen_index_engines": documents[f"knowledge:{kid}"]["engines"],
                    "frozen_index_table_ids": documents[f"knowledge:{kid}"]["table_ids"],
                    "scope": "Offline diagnosis only; not added to generation or production association",
                }
                for kid in note["missing_knowledge"]
            ],
        }
        table_ids = {t["table_id"] for t in context["candidate_tables"]}
        detail = by_id[qid]
        evidence = {
            "prompt_table_ids": sorted(table_ids),
            "reference_tables_not_in_prompt": sorted(set(native[qid]["expected"]["table_ids"]) - table_ids),
            "predicted_tables_not_in_prompt": sorted(set(native[qid]["actual"]["table_ids"]) - table_ids),
            "prompt_knowledge_ids": list(supplied_knowledge),
            "prompt_example_ids": list(examples),
            "pruned_evidence": context["omitted_evidence"],
            "rule_priority_excerpts": [
                line
                for line in request["messages"][0]["content"].splitlines()
                if any(word in line for word in ("优先于", "1列", "ROUND"))
            ],
            **witnesses,
        }
        row = {
            "question_id": qid,
            "question": detail["question"],
            "semantic_status": detail["semantic_status"],
            "primary": note["primary"],
            "primary_label": LABELS[note["primary"]],
            "finding": note["finding"],
            "next_validation": note["action"],
            "reference": detail["reference"],
            "predicted": detail["predicted"],
            "source_semantic_review": detail["review_note"],
            "evidence": evidence,
            "actual_request_sha256": sha(request_path),
            "actual_response_sha256": sha(response_path),
            "causal_experiment_performed": False,
        }
        rows.append(row)
        prompts.append({"question_id": qid, "messages": request["messages"]})
        shutil.copy2(request_path, folder / "request.json")
        shutil.copy2(response_path, folder / "response.json")
        write(folder / "diagnosis.json", row)
        (folder / "README.md").write_text(
            f"# {qid}：{detail['question']}\n\n"
            f"归类：**{LABELS[note['primary']]}**；原语义审查状态：`{detail['semantic_status']}`。\n\n"
            f"{note['finding']}\n\n"
            f"[实际请求和完整提示词](request.json) · [实际响应](response.json) · [结构化证据](diagnosis.json)\n\n"
            f"## 参考与预测\n\n参考：\n\n{block(detail['reference'])}\n\n"
            f"预测：\n\n{block(detail['predicted'])}\n\n"
            f"## 输入证据\n\n{block(evidence)}\n\n"
            f"后续核验：{note['action']}\n\n"
            "这是现有请求的静态证据归因，没有运行改提示词或换模型的控制变量实验。\n",
            encoding="utf-8",
        )
    write(output / "diagnosis.json", rows)
    with (output / "diagnosis.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=["question_id", "question", "semantic_status", "primary_label", "finding", "next_validation"],
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)
    (output / "wrong_prompts.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in prompts), encoding="utf-8"
    )
    for name, destination in [
        ("evaluation/semantic_summary.json", "source_semantic_summary.json"),
        ("evaluation/semantic_details.json", "source_semantic_details.json"),
        ("sampling_manifest.json", "sampling_manifest.json"),
        ("sampling.csv", "sampling.csv"),
        ("result.json", "predictions_100.json"),
        ("system_prompt.txt", "system_prompt.txt"),
        ("query_rules.txt", "query_rules.txt"),
        ("evaluation/semantic_protocol.json", "source_semantic_protocol.json"),
    ]:
        shutil.copy2(source / name, output / destination)
    counts = Counter(row["primary"] for row in rows)
    summary = {
        "reviewed_cases": len(rows),
        "source_status_counts": dict(Counter(r["semantic_status"] for r in rows)),
        "primary_counts": {key: counts[key] for key in LABELS},
        "primary_ids": {key: [r["question_id"] for r in rows if r["primary"] == key] for key in LABELS},
        "prompt_issue_observed_including_mixed": counts["prompt_evidence_gap"] + counts["prompt_conflict"] + counts["mixed"],
        "model_following_issue_observed_including_mixed": counts["model_following"] + counts["mixed"],
        "causal_experiment_performed": False,
        "new_LLM_calls": 0,
        "original_100_semantic_scores_changed": False,
        "all_actual_requests_match_prepared_messages": True,
        "all_selected_evidence_exists_in_actual_prompt": True,
        "all_missing_knowledge_verified_absent": True,
        "input_fingerprint": fingerprint,
    }
    assert sum(summary["primary_counts"].values()) == 40
    write(output / "summary.json", summary)
    write(output / "manifest.json", {"input_fingerprint": fingerprint, "source_run": str(source), "script_sha256": sha(Path(__file__))})
    table = "\n".join(
        f"| {LABELS[k]} | {counts[k]} | {', '.join(map(str, summary['primary_ids'][k]))} |" for k in LABELS
    )
    index = "\n".join(
        f"| [{r['question_id']}](cases/{r['question_id']}/README.md) | {r['semantic_status']} | {r['primary_label']} | {r['finding']} |"
        for r in rows
    )
    (output / "README.md").write_text(
        "# 100题验证实验：40道非一致题的真实提示词与归因\n\n"
        "已导出全部40题的实际请求、模型响应、参考与预测、逐题证据。范围为36道有差异、1道纯精度差异、3道待确认；"
        "不能把40题统称为已证明的业务错题。此前60/100静态语义一致率不改写，本次进一步区分差异来源。\n\n"
        "结论是输入和模型处理均有问题，另有大量题目/参考口径尚不能裁定。**这是逐题静态证据归因，不是控制变量因果实验，也不是模型能力排行榜。**\n\n"
        "[40题完整提示词JSONL](wrong_prompts.jsonl) · [归因CSV](diagnosis.csv) · [完整证据JSON](diagnosis.json) · "
        "[100题原始比较](source_semantic_details.json) · [100题预测](predictions_100.json) · [分类依据](../../case_notes_v1.json)\n\n"
        "| 主要归类（互斥） | 题数 | ID |\n| --- | ---: | --- |\n" + table + "\n\n"
        "含混合问题，17题观察到输入缺口或冲突，14题观察到模型处理偏差；这两项重叠10题，不能相加。"
        "19题的题面、参考或实际数据口径缺少唯一裁决依据，需先明确口径。\n\n"
        "## 关键证据与对上一轮结论的细化\n\n"
        "- **245：正确新能源条件已在输入。** 案例155给出了`brand LIKE '%电动%'`，预测改成`'%新能源%'`。"
        "这是可见案例未被正确利用，不能归为完全没有知识。\n"
        "- **2907：正确禁航区已在输入。** 案例2932嵌套SQL包含与参考一致的朝连岛多边形；模型仍说无精确边界并改了经度。"
        "2908则确实没有召回日照警戒区定义1742，二者需分别归因。\n"
        "- **441：不能仅归为BPS知识缺失。** 知识1624未召回，但案例433、439已有正确BPS公式；同时EPS近似知识1635带来干扰。"
        "本题归为混合：改善关联有帮助，但原提示词并非完全不含正确公式。\n"
        "- **2487：缺知识不等于每个概念都缺证据。** 超大规模1709未进入ES提示词；护理1710虽也缺失，案例2473已经补上护理条件且模型用对。"
        "决定性输入缺口是超大规模定义。\n"
        "- **1588：模型遵循新规则。** 系统要求比率ROUND2并优先于案例，案例/参考ROUND4，不能将这条差异归为模型生成错误。\n"
        "- **2950：单列计数规则作用域过宽。** 规则与参考每船分组不兼容，但尚未做去规则对照；不能声称该规则已被证明是漏分组的唯一原因。\n"
        "- **1723/1728：两个年份DDL都在。** 题面不含年份，2024或2025没有唯一选择依据，不能说模型路由漏库。\n\n"
        "## 如何回答提示词还是模型\n\n"
        "将提示词分为三层：召回的事实证据、系统口径/输出契约、案例。上游缺证据不等于改写一句system就能修复；"
        "有正确案例仍答错说明本次模型没有正确利用输入，但不证明该模型在所有重试、表达方式或更短上下文中都无法解决。\n\n"
        "建议先统一年份、输出对象、地域修饰对象、NULL/空串、空间边界和参考标签，再修复专用知识及必要表的可召回性；"
        "最后对证据充分的案例固定同一提示词，对比模型或做重复运行。若做提示词消融，只变动单一字段/规则，"
        "不把验证参考SQL或由答案推导的字段白名单传给生成器。本轮没有更改生产策略、参考标签或重新外发数据。\n\n"
        "## 逐题入口\n\n| 题目 | 原语义状态 | 主要归类 | 依据 |\n| --- | --- | --- | --- |\n"
        + index + "\n\n"
        "每题`request.json`是实际API请求文件的逐字拷贝，含完整system/user消息；`response.json`是实际响应记录。"
        "`diagnosis.json`保存选中的原始证据和缺失项。原始消息未为展示而改写，没有API key或请求认证头。"
        "归因程序校验源实验所有哈希、请求与准备消息一致、选中案例/知识确实在请求、缺失知识确实不在请求。"
        "所有归因属于离线评价材料，生产代码不导入该文件。\n",
        encoding="utf-8",
    )
    write(output / "artifact_sha256.json", {
        str(p.relative_to(output)): sha(p)
        for p in sorted(output.rglob("*"))
        if p.is_file() and p.name != "artifact_sha256.json"
    })
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=REPO / "outputs/experiments/validation-100-semantic-v1")
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "runs/prompt-diagnosis-v1")
    parser.add_argument("--notes", type=Path, default=Path(__file__).with_name("case_notes_v1.json"))
    run(parser.parse_args())


if __name__ == "__main__":
    main()
