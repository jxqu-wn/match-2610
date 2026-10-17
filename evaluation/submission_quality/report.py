"""Render measured validation/export evidence without claiming website accuracy."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from text2query.io import read_json, write_json

LABELS = {"single_table": "单表", "same_business_multitable": "同业务库多表",
          "same_system_cross_business": "同系统跨业务库", "cross_system": "跨系统联查"}


def render(root: Path, revision: str, profile: str, judge_revision: str, target: Path):
    phases = {}
    for phase in ("development", "gate"):
        generation = root / "inference" / revision / phase / profile
        judging = root / "judgments" / judge_revision / revision / phase / profile
        phases[phase] = {"context": read_json(generation / "context_metrics.json"),
                         "judgment": read_json(judging / "summary.json")}
    summary = {"generation_revision": revision, "profile": profile, "judge_revision": judge_revision,
               "phases": phases, "official_website_score": None, "website_submissions": 0}
    if (root / "readiness-amendment.json").exists():
        summary["packing_resume"] = read_json(root / "readiness-amendment.json")
        summary["initial_v11_gate"] = read_json(root / f"judgments/{judge_revision}/v11/gate/{profile}/summary.json")
    if (root / "full/export.json").exists():
        summary["export"] = read_json(root / "full/export.json")
    write_json(root / "measured_results.json", summary)
    lines = ["# 单次正式验证前的实测结果", "", f"分支：`improve/v6-single-submit-20261017`；生成版本 `{revision}`，配置 `{profile}`。", "",
             "使用指定 GPU 的 0.6B embedding/reranking 候选与 deepseek-flash；验证参考 SQL 仅用于独立评分。原始 Schema、knowledge、字典值未改写。", "",
             "| 集合 | 生成成功 | 最终提示词完整表覆盖 | 完整业务库覆盖 | LLM 判符合题意 | 错误 | 歧义 | 生成/评分失败 | 保留候选的来源不足回退 |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for phase, values in phases.items():
        context, judge = values["context"], values["judgment"]
        c, j = context["overall"], judge["overall"]
        lines.append(f"| {phase} | {c['generated']}/{context['expected']} | {c['complete_table']}/{c['count']} | {c['complete_database']}/{c['count']} | {j.get('faithful', 0)} | {j.get('incorrect', 0)} | {j.get('uncertain', 0)} | {j.get('generation_failed', 0) + j.get('judge_failed', 0)} | {c.get('unresolved_source_evidence', 0)} |")
    lines += ["", "## 联查单独评估", "", "| 集合 | 拓扑 | 完整表覆盖 | LLM 判符合题意 | 错误 | 歧义 |", "|---|---|---:|---:|---:|---:|"]
    for phase, values in phases.items():
        for topology, label in LABELS.items():
            c = values["context"]["by_topology"].get(topology, {})
            j = values["judgment"]["by_topology"].get(topology, {})
            lines.append(f"| {phase} | {label} | {c.get('complete_table', 0)}/{c.get('count', 0)} | {j.get('faithful', 0)} | {j.get('incorrect', 0)} | {j.get('uncertain', 0)} |")
    lines += ["", "## 结果等价与边界", "", "LLM 判符合题意与参考结果严格等价分别报告，均不等于实际业务库执行准确率。", ""]
    for phase, values in phases.items():
        j = values["judgment"]
        lines += [f"- {phase}：参考严格等价统计 `{json.dumps(j['raw_reference_equivalence'], ensure_ascii=False)}`；MySQL 子集 `{json.dumps(j['mysql_only'], ensure_ascii=False)}`。"]
    lines += ["", "MySQL 使用隔离 MariaDB 空 Schema 编译检查，未取得正式业务数据；PostgreSQL/PostGIS 仅做结构、字段及已知函数签名检查。当前口径和部分训练参考的精度、输出形状或年份存在冲突，不能以更换评分口径隐藏差异。", "",
              "60 道开发题与 48 道验收题生成前冻结；v11 配置在查看该轮验收输出前冻结。整个 284 题验证池此前已有研究，因此不是从未见过的新数据。v12 是发现装包缺陷后的同集回归，不能作为新的独立验收成绩。", "",
              "正式 680 题由 552 道新业务 SQL、78 道此前授权复用的 BIRD 来源 SQL，以及 50 道冻结的旧 ES 模型预测组成。旧 ES 网站得分 113.25/114、旧 SQLite 得分 218/239 是历史成绩，不能当作本轮重测成绩。", "",
              "网站验证次数为 0。大参数 AI 的 89.07% 是用户提供的历史网站得分；没有网站本轮分数，不能声称已经达到该水平。"]
    if "packing_resume" in summary:
        packing = summary["packing_resume"]
        initial = summary["initial_v11_gate"]["overall"]
        lines += ["", "## 装包修复与正式任务恢复", "",
                  f"v11 初次验收 48 题的语义复核为 {initial.get('faithful', 0)} 符合、{initial.get('incorrect', 0)} 错误、{initial.get('uncertain', 0)} 歧义；其原始记录保留。上表为 v12 同集回归，评分请求的措辞和随机性也可能影响标签。", "",
                  "正式任务中发现，简单题的行政区划样本同时包含原始 INSERT 和解析值，冗余样本挤掉了靠前的业务定义。修复只调整装包优先级：先精简重复样本，保留原始匹配及原始不一致示例，再裁剪知识；没有修改原始事实、模型或配置。", "",
                  f"暂停时已保存 {packing['old_completed']} 题；原样保留 {packing['keep_completed']} 题，归档并补做 {packing['repair_completed']} 道受影响或失败题，另完成 {packing['missing']} 道未完成题。恢复仍属于同一正式任务，完整任务计数 1，网站次数 0。每题版本与来源见 full/result_provenance.json。"]
    if "export" in summary:
        export = summary["export"]
        lines += ["", f"正式结果：`{export['result']}`，{export['questions']} 题；SHA-256：`{export['sha256']}`。"]
    if (root / "full/final_audit.json").exists():
        audit = read_json(root / "full/final_audit.json")
        summary["final_audit"] = audit
        write_json(root / "measured_results.json", summary)
        lines += ["", "## 正式文件离线检查", "",
                  f"完整格式及字段校验 {audit['integrity_valid']}/{audit['questions']}；MySQL 步骤空库编译 {audit['mysql_compile_valid']}/{audit['mysql_steps']}；跨系统双步骤 {audit['two_step_questions']} 题。", "",
                  f"保留来源与历史预测 {audit['reused_exact']}/128，业务生成 {audit['business_questions']} 题；所有请求预算检查通过，来源不足回退 {len(audit['unresolved_source_evidence_ids'])} 题。空库编译和协议通过不等于业务执行结果正确。"]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines) + "\n")
    print({"report": str(target), "phases": {phase: values["judgment"]["overall"] for phase, values in phases.items()}})


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--root", type=Path, default=Path("outputs/experiments/single-submit-v1"))
    parser.add_argument("--revision", default="v12")
    parser.add_argument("--profile", default="intent_review")
    parser.add_argument("--judge-revision", default="source-grounded-v7")
    parser.add_argument("--output", type=Path, default=Path("docs/single_submit_results.md"))
    args = parser.parse_args()
    render(args.root, args.revision, args.profile, args.judge_revision, args.output)


if __name__ == "__main__":
    main()
