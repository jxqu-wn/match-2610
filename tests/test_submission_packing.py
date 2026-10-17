import json

from text2query.submission.packing import affected_by_row_crowding, pack


def test_redundant_samples_cannot_displace_high_ranked_original_definitions():
    body = {"schema": [{"table_id": "MYSQL:demo.a", "columns": [["id", "INT"]]}],
            "knowledge_candidates": [{"source_id": "knowledge:1", "original_fact": "分类定义"},
                                     {"source_id": "knowledge:2", "original_fact": "问题需要的地区范围"}],
            "source_row_evidence": [{"source_sha256": "raw", "source_line": i, "values": {"id": i},
                                     **({"evidence_role": "original_source_city_name_inconsistency"} if i >= 3 else {})}
                                    for i in range(5)]}
    messages = [{"role": "system", "content": "规则"}, {"role": "user", "content": json.dumps(body)}]
    def estimate(messages):
        value = json.loads(messages[1]["content"])
        return 3000 + 1000 * len(value["source_row_evidence"]) + 500 * len(value["knowledge_candidates"])
    packed, omitted = pack(messages, "evidence_planning", 6000, estimate)
    after = json.loads(packed[1]["content"])
    assert after["knowledge_candidates"] == body["knowledge_candidates"]
    assert after["schema"] == body["schema"]
    assert after["source_row_evidence"][0] == body["source_row_evidence"][0]
    assert any(row.get("evidence_role") == "original_source_city_name_inconsistency" for row in after["source_row_evidence"])
    assert all(row in body["source_row_evidence"] for row in after["source_row_evidence"])
    assert estimate(packed) <= 6000
    assert not any(item.startswith("knowledge:") for item in omitted)
    assert len(json.loads(messages[1]["content"])["source_row_evidence"]) == 5


def test_affected_detection_uses_only_actual_packing_records():
    trace = {"omitted_whole_evidence": ["knowledge:2"], "messages": [{}, {"content": json.dumps({"source_row_evidence": [{}, {}, {}]})}]}
    assert affected_by_row_crowding({"trace": [trace]})
    trace["omitted_whole_evidence"] = ["training_case_scope:example:3"]
    assert not affected_by_row_crowding({"trace": [trace]})
