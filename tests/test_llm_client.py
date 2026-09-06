"""Tests for src.llm_client: the LLM-calling harness, in isolation from any caller.

These test get_client()/call_with_retry() directly against a fake
zero-arg callable -- not through src.workflow.llm_extraction_fallback
or any other caller -- so the harness's own retry/backoff mechanics
(attempt counts, backoff delays, which exceptions retry) are verified
independent of any feature that happens to use it. See
tests/test_workflow.py for how a caller's business logic (extraction
succeeding/degrading) is verified instead.
"""

from unittest.mock import MagicMock

import anthropic
import pytest

from src.llm_client import call_with_retry, get_client

_TIMEOUT = anthropic.APITimeoutError(request=MagicMock())
_CONNECTION_ERROR = anthropic.APIConnectionError(message="connection failed", request=MagicMock())


def _rate_limit_error() -> anthropic.RateLimitError:
    return anthropic.RateLimitError(
        message="rate limited", response=MagicMock(headers={}), body=None
    )


def _auth_error() -> anthropic.AuthenticationError:
    return anthropic.AuthenticationError(
        message="invalid x-api-key", response=MagicMock(headers={}), body=None
    )


def test_get_client_disables_the_sdks_own_silent_retries(monkeypatch):
    captured_kwargs = {}

    def _fake_anthropic(**kwargs):
        captured_kwargs.update(kwargs)
        return "the-client"

    monkeypatch.setattr("src.llm_client.anthropic.Anthropic", _fake_anthropic)

    client = get_client(timeout=12.5)

    assert client == "the-client"
    assert captured_kwargs == {"timeout": 12.5, "max_retries": 0}


def test_call_with_retry_returns_result_on_first_success(monkeypatch):
    monkeypatch.setattr("src.llm_client.time.sleep", MagicMock())
    fn = MagicMock(return_value="ok")

    result = call_with_retry(fn)

    assert result == "ok"
    fn.assert_called_once()


def test_call_with_retry_retries_transient_failure_then_succeeds(monkeypatch):
    sleeps: list[float] = []
    monkeypatch.setattr("src.llm_client.time.sleep", sleeps.append)
    fn = MagicMock(side_effect=[_TIMEOUT, "ok"])

    result = call_with_retry(fn)

    assert result == "ok"
    assert fn.call_count == 2
    assert sleeps == [1.0]


def test_call_with_retry_uses_exponential_backoff_across_multiple_retries(monkeypatch):
    sleeps: list[float] = []
    monkeypatch.setattr("src.llm_client.time.sleep", sleeps.append)
    fn = MagicMock(side_effect=[_TIMEOUT, _CONNECTION_ERROR, "ok"])

    result = call_with_retry(fn, max_retries=2)

    assert result == "ok"
    assert fn.call_count == 3
    assert sleeps == [1.0, 2.0]  # doubles each retry


def test_call_with_retry_respects_custom_max_retries_and_base_delay(monkeypatch):
    sleeps: list[float] = []
    monkeypatch.setattr("src.llm_client.time.sleep", sleeps.append)
    fn = MagicMock(side_effect=[_TIMEOUT, "ok"])

    result = call_with_retry(fn, max_retries=1, base_delay_seconds=0.25)

    assert result == "ok"
    assert sleeps == [0.25]


def test_call_with_retry_raises_last_exception_after_exhausting_retries(monkeypatch):
    sleeps: list[float] = []
    monkeypatch.setattr("src.llm_client.time.sleep", sleeps.append)
    fn = MagicMock(side_effect=[_TIMEOUT, _TIMEOUT, _CONNECTION_ERROR])

    with pytest.raises(anthropic.APIConnectionError):
        call_with_retry(fn, max_retries=2)

    # 1 initial attempt + 2 retries = 3 total calls; 2 backoff sleeps in between.
    assert fn.call_count == 3
    assert sleeps == [1.0, 2.0]


def test_call_with_retry_does_not_retry_a_non_retryable_exception(monkeypatch):
    sleeps: list[float] = []
    monkeypatch.setattr("src.llm_client.time.sleep", sleeps.append)
    fn = MagicMock(side_effect=_auth_error())

    with pytest.raises(anthropic.AuthenticationError):
        call_with_retry(fn)

    fn.assert_called_once()
    assert sleeps == []


def test_call_with_retry_treats_a_plain_exception_as_non_retryable(monkeypatch):
    """Non-anthropic exceptions (e.g. a parsing/validation error in the
    caller's own code) are not in RETRYABLE_EXCEPTIONS, so they propagate
    immediately -- this harness only retries transient Anthropic failures."""
    sleeps: list[float] = []
    monkeypatch.setattr("src.llm_client.time.sleep", sleeps.append)
    fn = MagicMock(side_effect=ValueError("not an Anthropic failure at all"))

    with pytest.raises(ValueError, match="not an Anthropic failure"):
        call_with_retry(fn)

    fn.assert_called_once()
    assert sleeps == []


def test_call_with_retry_retries_all_documented_retryable_exception_types(monkeypatch):
    """Every exception type in RETRYABLE_EXCEPTIONS should actually trigger a retry,
    not just the ones exercised by the other tests above."""
    monkeypatch.setattr("src.llm_client.time.sleep", MagicMock())
    retryable_instances = [
        anthropic.APITimeoutError(request=MagicMock()),
        anthropic.APIConnectionError(message="boom", request=MagicMock()),
        anthropic.RateLimitError(message="boom", response=MagicMock(headers={}), body=None),
        anthropic.InternalServerError(message="boom", response=MagicMock(headers={}), body=None),
        anthropic.OverloadedError(message="boom", response=MagicMock(headers={}), body=None),
        anthropic.ServiceUnavailableError(
            message="boom", response=MagicMock(headers={}), body=None
        ),
    ]

    for exc in retryable_instances:
        fn = MagicMock(side_effect=[exc, "ok"])

        result = call_with_retry(fn)

        assert result == "ok"
        assert fn.call_count == 2


def test_call_with_retry_logs_each_attempt_with_the_given_description(monkeypatch, caplog):
    monkeypatch.setattr("src.llm_client.time.sleep", MagicMock())
    fn = MagicMock(side_effect=[_TIMEOUT, "ok"])

    with caplog.at_level("INFO", logger="src.llm_client"):
        call_with_retry(fn, description="My Feature's LLM Call")

    messages = [record.message for record in caplog.records]
    assert any("My Feature's LLM Call" in m and "attempt 1/3" in m for m in messages)
