import pytest

from text2query.submission.knowledge_spans import fragments, planning_item, resolve_annotations


def test_fragment_references_preserve_formula_and_multiple_disjoint_original_sentences():
    text = "指标采用本库特殊定义。公式：assets - liabilities。其他条件仅适用另一指标。"
    item = {"knowledge_id": 7, "knowledge_text": text}
    view = planning_item(item)
    assert "knowledge_text" not in view
    assert "".join(span["text"] for span in fragments(text)) == text
    for span in view["source_fragments"]:
        assert span["text"] == text[span["start"]:span["end"]]
    result = resolve_annotations([{"knowledge_id": 7, "question_trigger": "指标", "fragment_ids": ["s1", "s2"]}], [item], "计算指标")
    assert result[0]["knowledge_text"] == text
    assert result[0]["applicability"]["source_quotes"] == ["指标采用本库特殊定义。", "公式：assets - liabilities。"]
    assert item == {"knowledge_id": 7, "knowledge_text": text}


@pytest.mark.parametrize("annotation", [
    {"knowledge_id": 7, "question_trigger": "不存在", "fragment_ids": ["s1"]},
    {"knowledge_id": 7, "question_trigger": "指标", "fragment_ids": ["s99"]},
    {"knowledge_id": 7, "question_trigger": "指标", "source_quote": "原文……不同"},
])
def test_invalid_scope_is_rejected_instead_of_silently_dropping_recalled_knowledge(annotation):
    with pytest.raises(ValueError):
        resolve_annotations([annotation], [{"knowledge_id": 7, "knowledge_text": "指标原文。"}], "计算指标")
