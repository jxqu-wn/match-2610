from text2query.submission.definition_dependencies import dependency_candidates


def test_definition_dependency_preserves_original_conditions_without_id_rules():
    selected = [{"knowledge_id": 901, "knowledge_text": "优惠费用按适用分类计算，小额企业取优惠档。"}]
    raw = "小额企业判定条件：收入不超过80且人数不超过20。"
    candidates = selected + [{"knowledge_id": 27, "knowledge_text": raw},
                             {"knowledge_id": 500, "knowledge_text": "其他对象指不相关实体。"}]
    result = dependency_candidates(selected, candidates)
    assert len(result) == 1
    assert result[0]["knowledge_id"] == 27
    assert result[0]["knowledge_text"] == raw
    assert result[0]["dependency_mentions"] == [{"concept_original_text": "小额企业", "mentioned_by_knowledge_id": 901}]
    assert "candidate" in result[0]["status"]
    assert "applicability" not in result[0]
    assert candidates[1] == {"knowledge_id": 27, "knowledge_text": raw}
