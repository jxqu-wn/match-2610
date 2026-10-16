"""Export exact initial Flash messages for review, without making API requests."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    directory = args.directory
    if not (directory / "prepared_complete.json").exists():
        raise SystemExit("Context preparation is not complete")
    rows = read(directory / "questions_input.json")
    bird = read(directory / "bird_answers.json")
    bird_ids = {row["question_id"] for row in bird}
    assert len(bird_ids) == len(bird)
    system = (directory / "system_prompt.txt").read_text(encoding="utf-8")
    prompts, table_counts, routes, examples = [], [], Counter(), {}
    for row in rows:
        if row["question_id"] in bird_ids:
            continue
        item = read(directory / f"prepared_{row['question_id']}.json")
        assert item["row"] == row
        context = item["context"]
        assert context["question"] == row["question"] and context["question_id"] == row["question_id"]
        table_ids = [table["table_id"] for table in context["candidate_tables"]]
        assert table_ids and len(table_ids) == len(set(table_ids))
        messages = [{"role": "system", "content": system},
                    {"role": "user", "content": json.dumps(context, ensure_ascii=False)}]
        prompt = {"question_id": row["question_id"], "predicted_engines": item["predicted_engines"],
                  "prompt_table_ids": table_ids, "messages": messages}
        prompts.append(prompt)
        table_counts.append(len(table_ids))
        route = "|".join(item["predicted_engines"])
        routes[route] += 1
        examples.setdefault(route, prompt)
    assert len(prompts) + len(bird) == len(rows)
    target = directory / "prompts.jsonl"
    target.write_text("".join(json.dumps(prompt, ensure_ascii=False) + "\n" for prompt in prompts), encoding="utf-8")
    review = ["# DeepSeek Flash 初始提示词预览", "",
              "完整初始请求见同目录 prompts.jsonl；此文件每种预测路由展示一题。此步骤不发送 API 请求。", ""]
    for route, prompt in examples.items():
        review.extend([f"## 题目 {prompt['question_id']} · {route}", ""])
        for message in prompt["messages"]:
            review.extend([f"### {message['role']}", "", "```json" if message["role"] == "user" else "```text",
                           message["content"], "```", ""])
    (directory / "prompts_review.md").write_text("\n".join(review), encoding="utf-8")
    generation = [read(path) for pattern in ("question_[0-9]*.json", "failed_[0-9]*.json")
                  for path in directory.glob(pattern)]
    summary = {
        "questions": len(rows), "llm_initial_prompts": len(prompts), "BIRD_answers": len(bird),
        "predicted_route_counts": dict(routes), "min_tables": min(table_counts), "max_tables": max(table_counts),
        "contexts_with_pruning": sum(bool(read(directory / f"prepared_{p['question_id']}.json")
                                           ["context"]["omitted_evidence"]) for p in prompts),
        "prompts_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "model": "deepseek-flash", "endpoint": "https://api.deepseek.com",
        "API_responses_in_saved_traces": sum(len(item.get("trace", [])) for item in generation),
        "approval_status": "authorized_by_user" if (directory / "external_transfer_authorization.json").exists()
                           else "required_by_automatic_approval_review",
        "data_sent_if_approved": ["question", "retrieved schemas", "retrieved knowledge", "training examples",
                                  "declared relations", "query interpretation rules"],
        "repair_policy": "Up to four generation/repair/evidence expansion calls per pass using the same catalog",
    }
    (directory / "prompt_review_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
                                                           encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
