"""Plain-English treaty summary (B7): one opt-in LLM call producing a
short executive summary (parties, layer, key dates, notable clauses).

Unlike every other domain task's own module (burn_cost_check_node,
exclusion_completeness_checklist_node, key_date_renewal_calendar_
extraction_node), this one is NOT wired into build_workflow_graph()'s
node/fan-out mechanism at all -- src/domain_tasks.py registers it with
workflow_node=None even though it's implemented. It's triggered by its
own standalone button in src/app.py, independent of the "Domain tasks
to run" checklist and the shared Extractor/Verifier pipeline's per-task
fan-out. This is deliberate: this task's own acceptance criteria
requires it never run just because other domain tasks are selected and
"Analyze" is clicked -- the only way to guarantee that is to keep it
entirely outside the graph/checklist mechanism those other tasks share.
"""

import logging
import time

from src.llm_client import call_with_retry, get_client
from src.models import TreatyTerms
from src.parser import PageSection

logger = logging.getLogger(__name__)

_LLM_MODEL = "claude-haiku-4-5-20251001"
_LLM_TIMEOUT_SECONDS = 30.0


def _format_sections_for_llm(sections: list[PageSection]) -> str:
    return "\n\n".join(f"--- Page {s.page_number} ---\n{s.text}" for s in sections)


def _build_prompt(treaty: TreatyTerms, sections: list[PageSection]) -> str:
    exclusions_text = ", ".join(treaty.exclusions) if treaty.exclusions else "none extracted"
    return (
        "Write a short, plain-English executive summary of this reinsurance "
        "treaty for a non-technical stakeholder. Cover the parties, the "
        "layer (attachment point and limit), the premium, and any notable "
        "exclusions. Keep it to 3-5 sentences, no bullet points.\n\n"
        "Extracted terms:\n"
        f"Cedent: {treaty.cedent_name}\n"
        f"Attachment point: {treaty.attachment_point:,.0f}\n"
        f"Limit: {treaty.limit:,.0f}\n"
        f"Reinsurance premium: {treaty.reinsurance_premium:,.0f}\n"
        f"Exclusions: {exclusions_text}\n\n"
        f"Full treaty text for additional context:\n\n{_format_sections_for_llm(sections)}"
    )


def generate_plain_english_treaty_summary(treaty: TreatyTerms, sections: list[PageSection]) -> str:
    """Produce a short plain-English executive summary of the treaty via a
    single LLM call.

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
            messages=[{"role": "user", "content": _build_prompt(treaty, sections)}],
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
    return summary_text
