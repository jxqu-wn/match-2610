"""OpenAI 兼容 LLM 客户端：重试、用量记录、可选内容哈希缓存。

DeepSeek 通过 OpenAI 协议访问；非思考模式与 JSON 输出通过 ``extra_body`` /
``response_format`` 指定。密钥只从环境读取。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import diskcache
import openai
from tenacity import Retrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from ..config import settings
from ..io import canonical_json, get_logger, sha256_text

logger = get_logger(__name__)

RETRYABLE = (
    openai.APIConnectionError,
    openai.APITimeoutError,
    openai.RateLimitError,
    openai.InternalServerError,
)


@dataclass
class CallRecord:
    purpose: str
    attempt: int
    latency_seconds: float = 0.0
    usage: dict[str, Any] = field(default_factory=dict)
    success: bool = False
    response_model: str | None = None
    finish_reason: str | None = None
    output_token_limit: int | None = None
    input_token_upper_bound: int | None = None
    error_type: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {key: value for key, value in self.__dict__.items() if value not in (None, {})}


class ChatClient:
    def __init__(
        self,
        *,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        retries: int = 2,
        timeout: float | None = None,
        cache_dir: Any = None,
        json_mode: bool = True,
        thinking: bool = False,
    ) -> None:
        key = api_key or settings.api_key
        if not key:
            raise ValueError("需要 DEEPSEEK_API_KEY 环境变量")
        if retries < 0:
            raise ValueError("retries 必须非负")
        self.model = model or settings.judge_model
        self.json_mode = json_mode
        self.thinking = thinking
        self.retries = retries
        self.client = openai.OpenAI(
            api_key=key,
            base_url=base_url or settings.base_url,
            timeout=timeout or settings.llm_timeout,
            max_retries=0,
        )
        self.cache = diskcache.Cache(str(cache_dir)) if cache_dir else None
        self.calls: list[CallRecord] = []

    def _cache_key(self, payload: dict[str, Any]) -> str:
        return sha256_text(canonical_json(payload))

    def complete(
        self,
        messages: list[dict[str, str]],
        max_tokens: int,
        purpose: str,
        *,
        temperature: float = 0.0,
    ) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if self.json_mode:
            payload["response_format"] = {"type": "json_object"}
        if not self.thinking:
            payload["extra_body"] = {"thinking": {"type": "disabled"}}

        if self.cache is not None:
            cached = self.cache.get(self._cache_key(payload))
            if cached is not None:
                record = CallRecord(purpose=purpose, attempt=1, success=True, usage=cached.get("usage", {}))
                record.response_model = cached.get("model")
                record.finish_reason = "cached"
                self.calls.append(record)
                return cached["content"]

        retrying = Retrying(
            stop=stop_after_attempt(self.retries + 1),
            wait=wait_exponential(multiplier=1, max=4),
            retry=retry_if_exception_type(RETRYABLE),
            sleep=time.sleep,
            reraise=True,
        )
        try:
            for attempt in retrying:
                with attempt:
                    record = CallRecord(purpose=purpose, attempt=attempt.retry_state.attempt_number)
                    self.calls.append(record)
                    started = time.monotonic()
                    try:
                        response = self._request(payload)
                    except RETRYABLE as error:
                        record.latency_seconds = time.monotonic() - started
                        record.error_type = type(error).__name__
                        raise
                    record.latency_seconds = time.monotonic() - started
                    record.success = True
                    record.usage = response.pop("usage", {})
                    record.response_model = response.get("model")
                    record.finish_reason = response.get("finish_reason")
                    record.output_token_limit = max_tokens
                    content = response["content"]
                    if self.cache is not None:
                        self.cache.set(self._cache_key(payload), {"content": content, **response})
                    return content
        except RETRYABLE as error:
            raise RuntimeError(f"API 传输失败：{type(error).__name__}") from error
        raise RuntimeError("API 重试耗尽")

    def _request(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = self.client.chat.completions.create(**payload)
        choice = response.choices[0]
        return {
            "content": choice.message.content or "",
            "model": response.model,
            "finish_reason": choice.finish_reason,
            "usage": response.usage.model_dump() if response.usage else {},
        }
