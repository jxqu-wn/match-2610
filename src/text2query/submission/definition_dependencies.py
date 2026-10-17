"""Literal definition dependencies within the frozen candidate pool, unconfirmed."""

from __future__ import annotations

import re


def definition_heads(text: str) -> list[str]:
    first = re.split(r"[。\n]", text, maxsplit=1)[0]
    match = re.match(r"(.{3,65}?)(?:判定条件|判定基于|计算公式|规则[：:]|近似指|指|表示)", first)
    if not match:
        return []
    head = match.group(1).strip()
    # Parenthetic aliases are original strings, never inferred synonyms.
    values = re.split(r"[（()）/、]", head)
    return list(dict.fromkeys(value.strip() for value in values if len(value.strip()) >= 3))


def dependency_candidates(selected: list[dict], candidates: list[dict], limit: int = 8) -> list[dict]:
    chosen = {item["knowledge_id"] for item in selected}
    output = []
    for item in candidates:
        if item["knowledge_id"] in chosen:
            continue
        heads = definition_heads(item["knowledge_text"])
        matches = [{"concept_original_text": head, "mentioned_by_knowledge_id": parent["knowledge_id"]}
                   for head in heads for parent in selected if head in parent["knowledge_text"]]
        if matches:
            output.append({**item, "dependency_mentions": matches,
                           "status": "literal_definition_dependency_candidate; confirm_applicability_and_full_source_scope"})
        if len(output) >= limit:
            break
    return output
