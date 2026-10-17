"""Stable references into original knowledge; never synthesize source quotes."""

from __future__ import annotations

import re


def fragments(text: str) -> list[dict]:
    # Chinese sentence boundaries, never decimal points or SQL identifiers.
    return [{"fragment_id": f"s{index}", "start": match.start(), "end": match.end(),
             "text": match.group()}
            for index, match in enumerate(re.finditer(r"[^。；\n]+[。；\n]*|[。；\n]+", text), 1)]


def planning_item(item: dict) -> dict:
    return {key: value for key, value in item.items() if key != "knowledge_text"} | {
        "source_fragments": fragments(item["knowledge_text"])}


def resolve_annotations(annotations: list, items: list[dict], question: str) -> list[dict]:
    by_id = {item["knowledge_id"]: item for item in items}
    selected = {}
    for annotation in annotations:
        if not isinstance(annotation, dict):
            raise ValueError("Knowledge applicability must contain objects")
        item = by_id.get(annotation.get("knowledge_id"))
        trigger = annotation.get("question_trigger")
        if item is None or not isinstance(trigger, str) or not trigger or trigger not in question:
            raise ValueError("Knowledge ID/trigger must refer to supplied evidence and exact question text")
        spans = {part["fragment_id"]: part for part in fragments(item["knowledge_text"])}
        ids = annotation.get("fragment_ids")
        if ids is not None:
            if not isinstance(ids, list) or not ids or any(not isinstance(key, str) or key not in spans for key in ids):
                raise ValueError("Unknown knowledge fragment IDs; select supplied sN IDs")
            quotes = [spans[key]["text"] for key in dict.fromkeys(ids)]
        else:
            # Accept old callers only when their entire quote really is original.
            quote = annotation.get("source_quote")
            if not isinstance(quote, str) or not quote or quote not in item["knowledge_text"]:
                raise ValueError("Knowledge quote is not a continuous original span")
            quotes = [quote]
        entry = selected.setdefault(item["knowledge_id"], {**item, "applicability": {
            "question_triggers": [], "source_quotes": [],
            "status": "LLM_scope_hint; source_spans_verified_only; other_text_is_not_automatically_applicable"}})
        scope = entry["applicability"]
        scope["question_triggers"] = list(dict.fromkeys(scope["question_triggers"] + [trigger]))
        scope["source_quotes"] = list(dict.fromkeys(scope["source_quotes"] + quotes))
        if len(scope["source_quotes"]) == 1:
            scope["source_quote"] = scope["source_quotes"][0]
        else:
            scope.pop("source_quote", None)
    return list(selected.values())
