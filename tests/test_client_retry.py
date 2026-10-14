"""Offline retry behavior: no network requests and no actual waits."""

import openai
import pytest

from text2query.llm.client import ChatClient


@pytest.fixture
def fake_transport(monkeypatch):
    constructor_args = {}
    waits = []

    def factory(**kwargs):
        constructor_args.update(kwargs)
        return object()

    monkeypatch.setattr("text2query.llm.client.openai.OpenAI", factory)
    monkeypatch.setattr("text2query.llm.client.time.sleep", waits.append)
    return constructor_args, waits


def connection_error():
    return openai.APIConnectionError(request=object())


def test_retry_success_records_attempts_and_cache_hit(fake_transport, monkeypatch, tmp_path):
    args, waits = fake_transport
    client = ChatClient(api_key="test-only", retries=2, cache_dir=tmp_path / "cache")
    attempts = []

    def request(payload):
        attempts.append(payload)
        if len(attempts) < 3:
            raise connection_error()
        return {"content": "ok", "usage": {"total_tokens": 7}, "model": "test", "finish_reason": "stop"}

    monkeypatch.setattr(client, "_request", request)
    messages = [{"role": "user", "content": "test"}]
    assert client.complete(messages, 100, "test") == "ok"
    assert args["max_retries"] == 0
    assert waits == [1, 2]
    assert [call.attempt for call in client.calls] == [1, 2, 3]
    assert [call.success for call in client.calls] == [False, False, True]
    assert client.calls[-1].usage == {"total_tokens": 7}
    assert client.complete(messages, 100, "test") == "ok"
    assert len(attempts) == 3 and client.calls[-1].finish_reason == "cached"
    client.cache.close()


def test_retry_exhaustion_is_bounded_and_preserves_cause(fake_transport, monkeypatch):
    _, waits = fake_transport
    client = ChatClient(api_key="test-only", retries=5)

    def request(payload):
        raise connection_error()

    monkeypatch.setattr(client, "_request", request)
    with pytest.raises(RuntimeError, match="API 传输失败") as error:
        client.complete([], 100, "test")
    assert isinstance(error.value.__cause__, openai.APIConnectionError)
    assert len(client.calls) == 6 and all(not call.success for call in client.calls)
    assert waits == [1, 2, 4, 4, 4]


def test_non_retryable_failure_is_not_retried(fake_transport, monkeypatch):
    _, waits = fake_transport
    client = ChatClient(api_key="test-only", retries=2)

    def request(payload):
        raise ValueError("invalid response")

    monkeypatch.setattr(client, "_request", request)
    with pytest.raises(ValueError, match="invalid response"):
        client.complete([], 100, "test")
    assert len(client.calls) == 1 and waits == []
