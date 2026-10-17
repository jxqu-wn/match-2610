"""Exercise schema repair and independent review without models/network."""

import json
from types import SimpleNamespace

import pytest

from text2query.models import Catalog
from text2query.submission import grounded


@pytest.fixture(scope="session", autouse=True)
def prepared_catalog():
    yield


def fixtures():
    row = {"question_id": 7, "question": "读取真实标识"}
    catalog = Catalog.model_validate({"tables": [
        {"table_id": f"MYSQL:demo.{name}", "engine": "MYSQL", "database": "demo", "name": name,
         "columns": [{"name": "id", "data_type": "INT", "description": "原文标识"}]}
        for name in ("a", "b")
    ]})
    pool = {"tables": [{"table_ids": ["MYSQL:demo.a"]}], "knowledge": [], "fk_candidates": []}
    return row, catalog, pool


def client_factory(responses, messages_seen):
    class FakeClient:
        def __init__(self, **kwargs):
            assert kwargs["model"] == "deepseek-flash"
            self.calls, self.cache = [], None

        def complete(self, messages, max_tokens, purpose):
            messages_seen.append(messages)
            raw, finish = responses.pop(0)
            self.calls.append(SimpleNamespace(finish_reason=finish, as_dict=lambda: {"finish_reason": finish}))
            return raw if isinstance(raw, str) else json.dumps(raw)
    return FakeClient


def test_unseen_real_schema_is_supplied_before_acceptance_and_review_is_fresh(tmp_path, monkeypatch):
    row, catalog, pool = fixtures()
    answer = {"question_id": 7, "db": "MYSQL", "query": "SELECT id FROM demo.b"}
    responses = [({"table_ids": ["MYSQL:demo.a"]}, "stop"),
                 ({"status": "complete", "answer": answer}, "stop"),
                 ({"status": "complete", "answer": answer}, "stop"),
                 ({"status": "complete", "verdict": "keep", "answer": answer}, "stop")]
    seen = []
    monkeypatch.setattr(grounded, "ChatClient", client_factory(responses, seen))
    result = grounded.generate(row, pool, {}, catalog, "原始规则", grounded.Profile("test", planned=True, review=True),
                               tmp_path, "fake-test-key", lambda _: 100)
    assert result["answer"] == answer
    assert result["trace"][1]["validation_errors"]
    assert all(len(messages) == 2 for messages in seen)
    repaired = json.loads(seen[2][1]["content"])
    assert {table["table_id"] for table in repaired["schema"]} == {"MYSQL:demo.a", "MYSQL:demo.b"}
    assert "draft_plan_may_be_corrected" not in json.loads(seen[3][1]["content"])
    assert "fake-test-key" not in json.dumps(result)


def test_truncated_answer_is_not_silently_accepted(tmp_path, monkeypatch):
    row, catalog, pool = fixtures()
    answer = {"question_id": 7, "db": "MYSQL", "query": "SELECT id FROM demo.a"}
    monkeypatch.setattr(grounded, "ChatClient", client_factory([({"answer": answer}, "length")], []))
    result = grounded.generate(row, pool, {}, catalog, "规则", grounded.Profile("test"), tmp_path, "fake", lambda _: 100)
    assert "answer" not in result
    assert "truncated" in result["error"]


def test_malformed_json_is_repaired_without_accepting_the_first_object(tmp_path, monkeypatch):
    row, catalog, pool = fixtures()
    answer = {"question_id": 7, "db": "MYSQL", "query": "SELECT id FROM demo.a"}
    seen = []
    responses = [(json.dumps({"answer": answer}) + ',"extra":[]}', "stop"), ({"answer": answer}, "stop")]
    monkeypatch.setattr(grounded, "ChatClient", client_factory(responses, seen))
    result = grounded.generate(row, pool, {}, catalog, "规则", grounded.Profile("test"), tmp_path, "fake", lambda _: 100)
    assert result["answer"] == answer
    assert len(result["trace"]) == 2
    assert result["trace"][0]["validation_errors"]
    assert "repair_attempt" in json.loads(seen[1][1]["content"])


def test_literal_intent_precedes_examples_and_review_does_not_see_full_cases(tmp_path, monkeypatch):
    row, catalog, pool = fixtures()
    pool["examples"] = [{"source_id": "example:1"}]
    docs = {"example:1": {"kind": "example", "table_ids": ["MYSQL:demo.a"], "data": {
        "question": "另一个训练问题", "steps": [{"engine": "MYSQL", "query": "SELECT id FROM demo.a"}]}}}
    answer = {"question_id": 7, "db": "MYSQL", "query": "SELECT id FROM demo.a"}
    responses = [({"quoted_requirements": [{"quote": "读取真实标识", "role": "output", "meaning": "业务标识"}]}, "stop"),
                 ({"table_ids": ["MYSQL:demo.a"]}, "stop"), ({"answer": answer}, "stop"),
                 ({"answer": answer, "verdict": "keep"}, "stop")]
    seen = []
    monkeypatch.setattr(grounded, "ChatClient", client_factory(responses, seen))
    result = grounded.generate(row, pool, docs, catalog, "规则", grounded.Profile("test", planned=True, review=True, intent_first=True),
                               tmp_path, "fake", lambda _: 100)
    assert result["answer"] == answer
    assert "另一个训练问题" not in seen[0][1]["content"]
    assert "另一个训练问题" in seen[1][1]["content"]
    assert "weak_training_examples" not in json.loads(seen[-1][1]["content"])
    assert "literal_requirement_contract" in json.loads(seen[-1][1]["content"])
    contract = json.loads(seen[-1][1]["content"])["literal_requirement_contract"]
    assert "meaning" not in contract["quoted_requirements"][0]


def test_budget_discards_directory_metadata_before_required_schema(tmp_path, monkeypatch):
    row, catalog, pool = fixtures()
    answer = {"question_id": 7, "db": "MYSQL", "query": "SELECT id FROM demo.a"}
    monkeypatch.setattr(grounded, "ChatClient", client_factory([({"answer": answer}, "stop")], []))
    def estimator(messages):
        return 9000 if "schema_directory" in json.loads(messages[1]["content"]) else 4000
    result = grounded.generate(row, pool, {}, catalog, "规则", grounded.Profile("test"), tmp_path, "fake", estimator)
    assert result["answer"] == answer
    assert "schema_directory_metadata" in result["trace"][0]["omitted_whole_evidence"]
    sent = json.loads(result["trace"][0]["messages"][1]["content"])
    assert sent["schema"][0]["columns"] == [["id", "INT", None, "原文标识"]]


def test_review_keeps_original_knowledge_and_its_narrow_applicability():
    _, catalog, pool = fixtures()
    row = {"question_id": 7, "question": "统计资质过期的企业"}
    original = "许可分类分为甲乙。资质过期指到期日早于当前日期。"
    quote = "资质过期指到期日早于当前日期。"
    docs = {"knowledge:1": {"data": {"knowledge_id": 1, "knowledge_text": original}}}
    pool["knowledge"] = [{"source_id": "knowledge:1"}]
    plan = {"knowledge_applicability": [{"knowledge_id": 1, "question_trigger": "资质过期",
                                        "source_quote": quote, "use": "unsupported generated interpretation"}]}
    messages = grounded.draft_messages(row, pool, docs, catalog, "规则", grounded.Profile("test"),
                                        ["MYSQL:demo.a"], plan=plan, review=True)
    body = json.loads(messages[1]["content"])
    assert body["knowledge"][0]["knowledge_text"] == original
    assert body["knowledge"][0]["applicability"]["source_quote"] == quote
    assert "unsupported generated interpretation" not in messages[1]["content"]
    assert docs["knowledge:1"]["data"]["knowledge_text"] == original


def test_bad_knowledge_reference_repairs_plan_instead_of_losing_definition(tmp_path, monkeypatch):
    row, catalog, pool = fixtures()
    pool["knowledge"] = [{"source_id": "knowledge:1"}]
    docs = {"knowledge:1": {"data": {"knowledge_id": 1, "knowledge_text": "本库真实标识指id。"}}}
    plan = {"table_ids": ["MYSQL:demo.a"], "knowledge_applicability": [
        {"knowledge_id": 1, "question_trigger": "真实标识", "fragment_ids": ["s1"]}]}
    bad = {**plan, "knowledge_applicability": [{**plan["knowledge_applicability"][0], "fragment_ids": ["s99"]}]}
    answer = {"question_id": 7, "db": "MYSQL", "query": "SELECT id FROM demo.a"}
    seen = []
    monkeypatch.setattr(grounded, "ChatClient", client_factory([(bad, "stop"), (plan, "stop"), ({"answer": answer}, "stop")], seen))
    result = grounded.generate(row, pool, docs, catalog, "规则", grounded.Profile("test", planned=True), tmp_path, "fake", lambda _: 100)
    assert result["answer"] == answer
    assert "planning_repair" in json.loads(seen[1][1]["content"])
    body = json.loads(seen[-1][1]["content"])
    assert body["knowledge"][0]["applicability"]["source_quotes"] == ["本库真实标识指id。"]
    assert all(trace["input_limit"] == 6000 for trace in result["trace"])


def test_existing_table_evidence_request_can_recover_missing_metric_knowledge(tmp_path, monkeypatch):
    row, catalog, pool = fixtures()
    pool["knowledge"] = [{"source_id": "knowledge:1"}]
    docs = {"knowledge:1": {"data": {"knowledge_id": 1, "knowledge_text": "本库真实标识指id。"}}}
    plan = {"table_ids": ["MYSQL:demo.a"], "knowledge_applicability": []}
    expanded = {**plan, "knowledge_applicability": [{"knowledge_id": 1, "question_trigger": "真实标识", "fragment_ids": ["s1"]}]}
    answer = {"question_id": 7, "db": "MYSQL", "query": "SELECT id FROM demo.a"}
    responses = [(plan, "stop"), ({"status": "need_more_evidence", "table_ids": ["MYSQL:demo.a"], "reason": "缺少标识定义"}, "stop"),
                 (expanded, "stop"), ({"answer": answer}, "stop")]
    seen = []
    monkeypatch.setattr(grounded, "ChatClient", client_factory(responses, seen))
    result = grounded.generate(row, pool, docs, catalog, "规则", grounded.Profile("test", planned=True), tmp_path, "fake", lambda _: 100)
    assert result["answer"] == answer
    assert "evidence_request" in json.loads(seen[2][1]["content"])
    assert json.loads(seen[-1][1]["content"])["knowledge"][0]["knowledge_id"] == 1


def test_review_can_request_actual_schema_by_exact_id_in_reason(tmp_path, monkeypatch):
    row, catalog, pool = fixtures()
    answer = {"question_id": 7, "db": "MYSQL", "query": "SELECT id FROM demo.a"}
    responses = [({"answer": answer}, "stop"),
                 ({"status": "need_more_evidence", "reason": "需要 MYSQL:demo.b 的原始字典"}, "stop"),
                 ({"answer": answer, "verdict": "keep"}, "stop")]
    seen = []
    monkeypatch.setattr(grounded, "ChatClient", client_factory(responses, seen))
    result = grounded.generate(row, pool, {}, catalog, "规则", grounded.Profile("test", review=True), tmp_path, "fake", lambda _: 100)
    assert result["answer"] == answer
    assert {table["table_id"] for table in json.loads(seen[-1][1]["content"])["schema"]} == {"MYSQL:demo.a", "MYSQL:demo.b"}


def test_failed_run_resumes_with_fresh_request_and_preserves_failure_trace(tmp_path, monkeypatch):
    row, catalog, pool = fixtures()
    profile = grounded.Profile("test")
    monkeypatch.setattr(grounded, "ChatClient", client_factory([("", "length")], []))
    failed = grounded.generate(row, pool, {}, catalog, "规则", profile, tmp_path, "fake", lambda _: 100)
    assert "answer" not in failed
    seen = []
    answer = {"question_id": 7, "db": "MYSQL", "query": "SELECT id FROM demo.a"}
    monkeypatch.setattr(grounded, "ChatClient", client_factory([({"answer": answer}, "stop")], seen))
    resumed = grounded.generate(row, pool, {}, catalog, "规则", profile, tmp_path, "fake", lambda _: 100)
    assert resumed["answer"] == answer
    assert resumed["signature"] == failed["signature"]
    assert resumed["run_attempt"] == 2
    assert json.loads(seen[0][1]["content"])["retry_run_attempt"] == 2
    assert (tmp_path / "attempt_history/7.1.json").exists()


def test_lower_ranked_compatible_case_is_not_hidden_by_first_two_lexical_hits():
    _, _, pool = fixtures()
    pool["lexical_examples"] = [{"source_id": f"example:{i}"} for i in range(4)]
    docs = {f"example:{i}": {"table_ids": ["MYSQL:demo.b" if i < 2 else "MYSQL:demo.a"],
                             "data": {"question": str(i), "steps": []}} for i in range(4)}
    examples = grounded.weak_examples(pool, docs, ["MYSQL:demo.a"], 2)
    assert [item["source_id"] for item in examples] == ["example:2", "example:3"]


def test_missing_source_values_are_explicitly_flagged_instead_of_claiming_review_pass(tmp_path, monkeypatch):
    row, catalog, pool = fixtures()
    plan = {"table_ids": ["MYSQL:demo.a"], "knowledge_applicability": []}
    answer = {"question_id": 7, "db": "MYSQL", "query": "SELECT id FROM demo.a"}
    request = {"status": "need_more_evidence", "table_ids": ["MYSQL:demo.a"], "reason": "缺少真实值样本"}
    responses = [(plan, "stop"), ({"answer": answer}, "stop"), (request, "stop"), (plan, "stop"), (request, "stop")]
    monkeypatch.setattr(grounded, "ChatClient", client_factory(responses, []))
    result = grounded.generate(row, pool, {}, catalog, "规则", grounded.Profile("test", planned=True, review=True), tmp_path, "fake", lambda _: 100)
    assert result["answer"] == answer
    assert result["review_status"] == "unresolved_source_evidence"
    assert result["analysis"]["status"] == "source_limited"
    assert "verdict" not in result["analysis"]


def test_irrelevant_cross_engine_candidate_cannot_expand_simple_question_planning_budget(tmp_path, monkeypatch):
    row, catalog, pool = fixtures()
    catalog.tables.append(Catalog.model_validate({"tables": [{"table_id": "POSTGRESQL:public.decoy", "engine": "POSTGRESQL",
        "schema": "public", "name": "decoy", "columns": [{"name": "id", "data_type": "INT"}]}]}).tables[0])
    pool["tables"].append({"table_ids": ["POSTGRESQL:public.decoy"]})
    answer = {"question_id": 7, "db": "MYSQL", "query": "SELECT id FROM demo.a"}
    responses = [({"table_ids": ["MYSQL:demo.a"]}, "stop"), ({"answer": answer}, "stop")]
    monkeypatch.setattr(grounded, "ChatClient", client_factory(responses, []))
    result = grounded.generate(row, pool, {}, catalog, "规则", grounded.Profile("test", planned=True), tmp_path, "fake", lambda _: 100)
    assert result["answer"] == answer
    assert all(trace["input_limit"] == 6000 for trace in result["trace"])
