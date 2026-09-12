"""Plain-English treaty summary (B7): one opt-in LLM call producing a
short executive summary (parties, layer, key dates, notable clauses).

Unlike every other domain task's own module (burn_cost_check_node,
exclusion_completeness_checklist_node, key_date_renewal_calendar_
extraction_node), this one is NOT wired into build_workflow_graph()'s
node/fan-out mechanism at all -- src/domain_tasks.py registers it with
workflow_node=None even though it's implemented. It's triggered by its
own standalone button in src/app.py, placed right where a treaty is
picked (alongside "Review treaty"), independent of the "Domain tasks to
run" checklist and the shared Extractor/Verifier pipeline's per-task
fan-out -- and independent of "Analyze" too, since it only depends on
which treaty was picked, not on that treaty's extracted terms. This is
deliberate: this task's own acceptance criteria requires it never run
just because other domain tasks are selected and "Analyze" is clicked,
and it should be available as soon as a treaty is selected -- the only
way to guarantee both is to keep it entirely outside the graph/
checklist/extraction mechanism those other tasks share, working
directly off the treaty's raw parsed text instead of its (not yet
extracted) TreatyTerms.
"""

import logging
import time
from dataclasses import dataclass

from src.llm_client import call_with_retry, get_client
from src.parser import PageSection

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PlainEnglishSummaryResult:
    """The generated summary text plus the LLM call's real token usage.

    Usage is returned as its own field (not appended into `text`) so a
    caller can surface it separately -- e.g. as an on-screen info line --
    without it ever being written into the saved/downloaded summary
    document itself.
    """

    text: str
    input_tokens: int
    output_tokens: int

_LLM_MODEL = "claude-haiku-4-5-20251001"
_LLM_TIMEOUT_SECONDS = 30.0


def _format_sections_for_llm(sections: list[PageSection]) -> str:
    return "\n\n".join(f"--- Page {s.page_number} ---\n{s.text}" for s in sections)


def _build_prompt(sections: list[PageSection]) -> str:
    return (
        "Write a short, plain-English executive summary of this reinsurance "
        "treaty for a non-technical stakeholder. Cover the parties, the "
        "layer (attachment point and limit), the premium, and any notable "
        "exclusions. Identify these directly from the treaty text below. "
        "Keep it to 3-5 sentences, no bullet points.\n\n"
        f"Treaty text:\n\n{_format_sections_for_llm(sections)}"
    )


def generate_plain_english_treaty_summary(sections: list[PageSection]) -> PlainEnglishSummaryResult:
    """Produce a short plain-English executive summary of the treaty via a
    single LLM call, working directly off its raw parsed page text --
    doesn't need (and doesn't wait for) the treaty's extracted TreatyTerms,
    so it's available as soon as a treaty is picked, before "Analyze".

    Raises whatever exception the underlying call raises once
    call_with_retry's retries are exhausted -- there's no graph state to
    gracefully degrade into here, so the caller (src/app.py's button
    handler) is responsible for catching and displaying the failure.
    """
    started_at = time.perf_counter()

    def _create_completion():
        client = get_client(timeout=_LLM_TIMEOUT_SECONDS)
        return client.messages.create(
            model=_LLM_MODEL,
            max_tokens=512,
            messages=[{"role": "user", "content": _build_prompt(sections)}],
        )

    response = call_with_retry(_create_completion, description="Plain-English Treaty Summary")

    duration = time.perf_counter() - started_at
    summary_text = "".join(block.text for block in response.content if block.type == "text").strip()
    usage = response.usage
    logger.info(
        "[plain_english_treaty_summary] Plain-English Treaty Summary: generated in %.2fs "
        "(model=%s, input_tokens=%d, output_tokens=%d)",
        duration,
        _LLM_MODEL,
        usage.input_tokens,
        usage.output_tokens,
    )
    return PlainEnglishSummaryResult(
        text=summary_text, input_tokens=usage.input_tokens, output_tokens=usage.output_tokens
    )
