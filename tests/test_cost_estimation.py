"""Tests for src.cost_estimation: per-task cost estimation and actual cost tracking."""

from src.cost_estimation import (
    HAIKU_INPUT_PRICE_PER_TOKEN,
    HAIKU_OUTPUT_PRICE_PER_TOKEN,
    actual_task_cost,
    estimate_task_cost,
)
from src.domain_tasks import DomainTask


def _task(shape: str) -> DomainTask:
    return DomainTask(
        id="x",
        title="X",
        candidate_id="B0",
        implementation_status="not_implemented",
        shape=shape,
        workflow_node=None,
    )


def test_estimate_task_cost_is_zero_for_deterministic_tasks():
    assert estimate_task_cost(_task("deterministic"), page_count=10) == 0.0


def test_estimate_task_cost_is_zero_for_deterministic_regardless_of_page_count():
    assert estimate_task_cost(_task("deterministic"), page_count=1000) == 0.0


def test_estimate_task_cost_scales_with_page_count_for_llm_tasks():
    small = estimate_task_cost(_task("llm"), page_count=2)
    large = estimate_task_cost(_task("llm"), page_count=20)

    assert small > 0
    assert large > small


def test_estimate_task_cost_is_nonzero_for_hybrid_tasks():
    assert estimate_task_cost(_task("hybrid"), page_count=5) > 0


def test_actual_task_cost_uses_published_per_token_prices():
    cost = actual_task_cost(input_tokens=1_000_000, output_tokens=1_000_000)

    assert cost == HAIKU_INPUT_PRICE_PER_TOKEN * 1_000_000 + HAIKU_OUTPUT_PRICE_PER_TOKEN * 1_000_000


def test_actual_task_cost_matches_known_dollar_figures():
    # $1.00/1M input, $5.00/1M output -- 500 input + 60 output tokens
    # (a real logged example from tests/test_app.py's mock LLM client).
    cost = actual_task_cost(input_tokens=500, output_tokens=60)

    assert cost == (500 / 1_000_000) * 1.00 + (60 / 1_000_000) * 5.00


def test_actual_task_cost_zero_tokens_is_zero():
    assert actual_task_cost(input_tokens=0, output_tokens=0) == 0.0
