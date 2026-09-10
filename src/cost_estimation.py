"""Per-task cost estimation (pre-run) and actual cost tracking (post-run).

The first real $-cost logic in this app. `estimate_task_cost()` gives a
rough pre-run figure from a domain task's shape and the document's page
count -- near-zero for deterministic tasks (no LLM call involved), a
document-length-scaled estimate for llm/hybrid-shaped ones.
`actual_task_cost()` converts a completed LLM call's real token counts
(e.g. `llm_extraction_fallback`'s already-logged usage) into an actual $
figure, using the same published per-token price.

Only Claude Haiku 4.5 (`src/workflow.py`'s `_LLM_MODEL`) is priced here,
since it's the only model any task in this app calls today.
"""

from src.domain_tasks import DomainTask

# Claude Haiku 4.5 published pricing (per token, not per million) --
# $1.00 / 1M input tokens, $5.00 / 1M output tokens.
HAIKU_INPUT_PRICE_PER_TOKEN = 1.00 / 1_000_000
HAIKU_OUTPUT_PRICE_PER_TOKEN = 5.00 / 1_000_000

# Rough per-page/per-call token counts used only for the pre-run estimate,
# before any node has actually run -- not measured averages. A real
# treaty page is a few hundred words of prose; a single structured
# tool-use extraction response is short.
_ESTIMATED_INPUT_TOKENS_PER_PAGE = 500
_ESTIMATED_OUTPUT_TOKENS_PER_LLM_CALL = 200


def estimate_task_cost(task: DomainTask, page_count: int) -> float:
    """Rough pre-run $ estimate for running task against a page_count-page treaty.

    Always 0.0 for a deterministic-shaped task (regex/arithmetic, no LLM
    call). For llm/hybrid-shaped tasks, scales with page_count, since a
    longer document means more input tokens sent to the model.
    """
    if task.shape == "deterministic":
        return 0.0
    estimated_input_tokens = page_count * _ESTIMATED_INPUT_TOKENS_PER_PAGE
    return (
        estimated_input_tokens * HAIKU_INPUT_PRICE_PER_TOKEN
        + _ESTIMATED_OUTPUT_TOKENS_PER_LLM_CALL * HAIKU_OUTPUT_PRICE_PER_TOKEN
    )


def actual_task_cost(input_tokens: int, output_tokens: int) -> float:
    """Convert a completed LLM call's real token counts into an actual $ figure."""
    return input_tokens * HAIKU_INPUT_PRICE_PER_TOKEN + output_tokens * HAIKU_OUTPUT_PRICE_PER_TOKEN
