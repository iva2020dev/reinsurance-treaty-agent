"""Harness for calling Anthropic's API reliably.

Owns the mechanics of talking to the LLM -- client construction and
retry/backoff on transient failures -- decoupled from any particular
node's business logic (what to ask for, how to parse the response, how
to degrade on failure). Business logic stays in workflow.py; this
module only knows how to make one attempt reliable and retryable.
"""

import logging
import time
from typing import Callable, TypeVar

import anthropic

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Transient failures worth retrying (network hiccups, rate limits, momentary
# server overload). Everything else (auth errors, malformed responses,
# application-level validation errors) is not retried by this harness --
# call_with_retry() lets it propagate on the first attempt.
RETRYABLE_EXCEPTIONS = (
    anthropic.APITimeoutError,
    anthropic.APIConnectionError,
    anthropic.RateLimitError,
    anthropic.InternalServerError,
    anthropic.OverloadedError,
    anthropic.ServiceUnavailableError,
)

DEFAULT_MAX_RETRIES = 2
DEFAULT_RETRY_BASE_DELAY_SECONDS = 1.0


def get_client(*, timeout: float) -> anthropic.Anthropic:
    """An Anthropic client with the SDK's own silent retries disabled.

    Callers should use call_with_retry() for retry/backoff instead, so
    every attempt is visible in this app's logs (and the two mechanisms
    don't stack, silently multiplying the worst-case delay).
    """
    return anthropic.Anthropic(timeout=timeout, max_retries=0)


def call_with_retry(
    fn: Callable[[], T],
    *,
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay_seconds: float = DEFAULT_RETRY_BASE_DELAY_SECONDS,
    description: str = "LLM call",
) -> T:
    """Call fn(), retrying transient Anthropic failures with exponential backoff.

    Retries exceptions in RETRYABLE_EXCEPTIONS up to max_retries times,
    logging each attempt (attempt number, exception, backoff delay). Any
    other exception propagates immediately, unretried. If every retry is
    exhausted, the last exception propagates to the caller to handle
    (e.g. graceful degradation) rather than being swallowed here.
    """
    attempt = 0
    while True:
        try:
            return fn()
        except RETRYABLE_EXCEPTIONS as exc:
            if attempt >= max_retries:
                logger.info(
                    "%s: failed after %d retries (%s: %s)",
                    description,
                    attempt,
                    type(exc).__name__,
                    exc,
                )
                raise
            delay = base_delay_seconds * (2**attempt)
            logger.info(
                "%s: transient failure on attempt %d/%d (%s: %s), retrying in %.1fs",
                description,
                attempt + 1,
                max_retries + 1,
                type(exc).__name__,
                exc,
                delay,
            )
            time.sleep(delay)
            attempt += 1
