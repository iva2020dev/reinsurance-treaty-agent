"""LangGraph state machine & agent logic."""

import logging
import re
import time
from pathlib import Path
from typing import Literal, TypedDict

from dotenv import load_dotenv
from langgraph.graph import END, StateGraph
from pydantic import ValidationError

from src.domain_tasks import DOMAIN_TASKS
from src.llm_client import call_with_retry, get_client
from src.models import AnomalyFinding, AnomalyReport, ClaimsData, Severity, TreatyTerms
from src.parser import PageSection, extract_treaty_sections
from src.tools import calculate_loss_ratio, check_treaty_grounding, query_historical_claims

load_dotenv()  # no-op in production, where ANTHROPIC_API_KEY comes from a real env var/secret

logger = logging.getLogger(__name__)

_REQUIRED_FIELDS = ("cedent_name", "attachment_point", "limit", "reinsurance_premium")

_LLM_MODEL = "claude-haiku-4-5-20251001"
_LLM_TIMEOUT_SECONDS = 30.0

_TREATY_EXTRACTION_TOOL = {
    "name": "extract_treaty_terms",
    "description": (
        "Extract reinsurance treaty terms from the given page text. "
        "'limit' is the width of the reinsurance layer above the attachment "
        "point, not the absolute top of the layer -- e.g. an attachment "
        "point of 2,500,000 with a limit of 5,000,000 means coverage runs "
        "from 2,500,000 up to 7,500,000 of loss."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "cedent_name": {
                "type": "string",
                "description": "The ceding insurer party to this treaty",
            },
            "attachment_point": {
                "type": "number",
                "description": "Loss level at which reinsurance coverage begins",
            },
            "limit": {
                "type": "number",
                "description": "Width of reinsurance coverage above the attachment point",
            },
            "reinsurance_premium": {
                "type": "number",
                "description": "Premium ceded to the reinsurer",
            },
            "exclusions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Exclusion clauses",
            },
            "page_citations": {
                "type": "object",
                "description": "Maps each extracted field name to the 1-indexed page it was found on",
                "properties": {
                    "cedent_name": {"type": "integer"},
                    "attachment_point": {"type": "integer"},
                    "limit": {"type": "integer"},
                    "reinsurance_premium": {"type": "integer"},
                    "exclusions": {"type": "integer"},
                },
            },
        },
        "required": ["cedent_name", "attachment_point", "limit", "reinsurance_premium", "page_citations"],
    },
}

_FIELD_PATTERNS = {
    "cedent_name": re.compile(r"Cedent:\s*(.+)"),
    "attachment_point": re.compile(r"Attachment Point:\s*([\d,]+(?:\.\d+)?)"),
    "limit": re.compile(r"Limit:\s*([\d,]+(?:\.\d+)?)"),
    "reinsurance_premium": re.compile(r"Reinsurance Premium:\s*([\d,]+(?:\.\d+)?)"),
}

_EXCLUSIONS_SECTION_PATTERN = re.compile(r"EXCLUSIONS\s*\n(.*)", re.DOTALL | re.IGNORECASE)
_LEADING_NUMBERING_PATTERN = re.compile(r"^\d+\.\s*")

LOSS_RATIO_MEDIUM_THRESHOLD = 0.5
LOSS_RATIO_HIGH_THRESHOLD = 1.0


class WorkflowState(TypedDict, total=False):
    """State passed between workflow nodes."""

    sections: list[PageSection]
    treaty: TreatyTerms | None
    missing_fields: list[str]
    extraction_method: Literal["regex", "llm", "none"]
    llm_error: str | None
    ungrounded_fields: list[str]
    claims: list[ClaimsData]
    complete: bool
    report: AnomalyReport | None


def _extract_exclusions(sections: list[PageSection]) -> tuple[list[str], int | None]:
    """Find the EXCLUSIONS section and return its list items, plus the page it was found on."""
    for section in sections:
        match = _EXCLUSIONS_SECTION_PATTERN.search(section.text)
        if not match:
            continue
        lines = [line.strip() for line in match.group(1).splitlines() if line.strip()]
        items = [
            _LEADING_NUMBERING_PATTERN.sub("", line) for line in lines if not line.endswith(":")
        ]
        return items, section.page_number
    return [], None


def extract_treaty_terms(sections: list[PageSection]) -> tuple[TreatyTerms | None, list[str]]:
    """Deterministically extract TreatyTerms from parsed treaty sections.

    Matches the "Label: value" convention used by the treaty fixtures. For
    a multi-layer treaty, each field's first match (in page order) wins,
    i.e. Layer 1's values, since TreatyTerms models a single layer.

    Returns (TreatyTerms, []) on success, or (None, missing_field_names)
    if required fields could not be found or the extracted values failed
    schema validation.
    """
    raw_values: dict[str, str] = {}
    page_citations: dict[str, int] = {}
    for field, pattern in _FIELD_PATTERNS.items():
        for section in sections:
            match = pattern.search(section.text)
            if match:
                raw_values[field] = match.group(1).strip()
                page_citations[field] = section.page_number
                break

    missing = [field for field in _REQUIRED_FIELDS if field not in raw_values]
    if missing:
        return None, missing

    exclusions, exclusions_page = _extract_exclusions(sections)
    if exclusions_page is not None:
        page_citations["exclusions"] = exclusions_page

    try:
        treaty = TreatyTerms(
            cedent_name=raw_values["cedent_name"],
            attachment_point=float(raw_values["attachment_point"].replace(",", "")),
            limit=float(raw_values["limit"].replace(",", "")),
            reinsurance_premium=float(raw_values["reinsurance_premium"].replace(",", "")),
            exclusions=exclusions,
            page_citations=page_citations,
        )
    except ValidationError as exc:
        return None, [str(exc)]

    return treaty, []


def extractor_node(state: WorkflowState) -> dict:
    """Extract TreatyTerms from the parsed treaty sections."""
    treaty, missing_fields = extract_treaty_terms(state["sections"])
    if treaty is None:
        logger.info("Extractor (Regex): missing required fields %s", missing_fields)
        return {"treaty": treaty, "missing_fields": missing_fields}
    logger.info("Extractor (Regex): extracted treaty terms for cedent %r", treaty.cedent_name)
    return {"treaty": treaty, "missing_fields": missing_fields, "extraction_method": "regex"}


def _format_sections_for_llm(sections: list[PageSection]) -> str:
    return "\n\n".join(f"--- Page {s.page_number} ---\n{s.text}" for s in sections)


def llm_extraction_fallback(state: WorkflowState) -> dict:
    """Fall back to an LLM to extract TreatyTerms when regex found no required fields.

    Only called when the Extractor Node's missing_fields is non-empty (see
    _route_after_extractor). Transient failures (timeout, connection error,
    rate limit, momentary server overload) are retried with exponential
    backoff by src.llm_client.call_with_retry, which logs each attempt.
    On any other failure -- a missing/invalid API key, a malformed tool
    response, a TreatyTerms validation error, or a transient failure that
    exhausts its retries -- this logs it and leaves the run in the same
    "incomplete" state the regex-only path already produces
    (treaty=None, missing_fields unchanged), rather than crashing.
    """
    started_at = time.perf_counter()

    def _create_completion():
        client = get_client(timeout=_LLM_TIMEOUT_SECONDS)
        return client.messages.create(
            model=_LLM_MODEL,
            max_tokens=1024,
            tools=[_TREATY_EXTRACTION_TOOL],
            tool_choice={"type": "tool", "name": "extract_treaty_terms"},
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Extract the treaty terms from this reinsurance treaty "
                        f"document:\n\n{_format_sections_for_llm(state['sections'])}"
                    ),
                }
            ],
        )

    try:
        response = call_with_retry(_create_completion, description="LLM Extraction Fallback")
        tool_use = next(block for block in response.content if block.type == "tool_use")
        treaty = TreatyTerms(**tool_use.input)
    except Exception as exc:  # noqa: BLE001 -- any failure must degrade gracefully, not crash
        duration = time.perf_counter() - started_at
        logger.info(
            "LLM Extraction Fallback: extraction failed after %.2fs (model=%s, %s: %s)",
            duration,
            _LLM_MODEL,
            type(exc).__name__,
            exc,
        )
        return {"extraction_method": "none", "llm_error": f"{type(exc).__name__}: {exc}"}

    duration = time.perf_counter() - started_at
    usage = response.usage
    logger.info(
        "LLM Extraction Fallback: extracted treaty terms for cedent %r in %.2fs "
        "(model=%s, input_tokens=%d, output_tokens=%d)",
        treaty.cedent_name,
        duration,
        _LLM_MODEL,
        usage.input_tokens,
        usage.output_tokens,
    )
    ungrounded_fields = check_treaty_grounding(treaty, state["sections"])
    if ungrounded_fields:
        logger.warning(
            "LLM Extraction Fallback: %d field(s) failed grounding check: %s",
            len(ungrounded_fields),
            ungrounded_fields,
        )
    return {
        "treaty": treaty,
        "missing_fields": [],
        "extraction_method": "llm",
        "llm_error": None,
        "ungrounded_fields": ungrounded_fields,
    }


def verifier_node(state: WorkflowState) -> dict:
    """Validate extraction completeness; if complete, fetch historical claims for the cedent."""
    treaty = state.get("treaty")
    if treaty is None:
        logger.info("Verifier: extraction incomplete, skipping claims lookup and Analyst node")
        return {"complete": False, "claims": []}
    claims = query_historical_claims(treaty.cedent_name)
    logger.info("Verifier: found %d historical claim(s) for %r", len(claims), treaty.cedent_name)
    return {"complete": True, "claims": claims}


def burn_cost_check_node(state: WorkflowState) -> dict:
    """Compare treaty terms against historical claims and flag anomalies (the Burn-Cost Check, B0)."""
    treaty = state["treaty"]
    claims = state.get("claims", [])
    loss_ratio = calculate_loss_ratio(treaty.attachment_point, treaty.limit, claims)

    findings = []
    if not claims:
        findings.append(
            AnomalyFinding(
                field="claims",
                description=f"No historical claims data found for cedent '{treaty.cedent_name}'.",
                severity=Severity.LOW,
            )
        )
    if loss_ratio > LOSS_RATIO_HIGH_THRESHOLD:
        findings.append(
            AnomalyFinding(
                field="loss_ratio",
                description=(
                    f"Historical losses (loss ratio {loss_ratio:.2f}) would have "
                    "exceeded this layer's limit."
                ),
                severity=Severity.HIGH,
            )
        )
    elif loss_ratio >= LOSS_RATIO_MEDIUM_THRESHOLD:
        findings.append(
            AnomalyFinding(
                field="loss_ratio",
                description=(
                    f"Historical losses (loss ratio {loss_ratio:.2f}) would have "
                    "consumed a majority of this layer."
                ),
                severity=Severity.MEDIUM,
            )
        )

    report = AnomalyReport(treaty=treaty, claims=claims, loss_ratio=loss_ratio, findings=findings)
    logger.info(
        "Burn-Cost Check: loss ratio %.2f, %d finding(s)",
        loss_ratio,
        len(findings),
    )
    return {"report": report}


def _route_after_extractor(state: WorkflowState) -> str:
    return "llm_extraction_fallback" if state.get("missing_fields") else "verifier"


# Today's only implemented domain task (B0) -- matches src/domain_tasks.py's
# DOMAIN_TASKS entry with implementation_status="implemented". Used as the
# default selection so build_workflow_graph()/run_workflow() called with no
# selected_task_ids behave exactly like the previous fixed single-task graph.
_DEFAULT_SELECTED_TASK_IDS = frozenset({"burn_cost_check"})


def build_workflow_graph(selected_task_ids: set[str] | None = None):
    """Build and compile the workflow graph.

    The shared Extractor -> [LLM Extraction Fallback] -> Verifier pipeline
    always runs. Only the analysis node(s) for tasks that are both in
    selected_task_ids and marked implemented in src/domain_tasks.py's
    DOMAIN_TASKS registry then run -- a task selected but not yet
    implemented (or not selected at all) is simply skipped, same as if it
    didn't exist. The registry's `workflow_node` field names the actual
    node function to wire in, so this is the only place that decision is
    made -- src/domain_tasks.py can't drift from what actually runs.

    selected_task_ids defaults to {"burn_cost_check"} (B0, today's only
    implemented task) when not given, matching this function's previous
    fixed-graph behavior exactly.
    """
    selected = frozenset(selected_task_ids) if selected_task_ids is not None else _DEFAULT_SELECTED_TASK_IDS
    active_tasks = [
        task for task in DOMAIN_TASKS if task.id in selected and task.implementation_status == "implemented"
    ]
    if len(active_tasks) > 1:
        # Running more than one implemented task in the same graph needs S3's
        # multi-task result aggregation (WorkflowState.task_results) to avoid
        # multiple nodes overwriting the single WorkflowState.report field --
        # not built yet, and unreachable today since DOMAIN_TASKS has only one
        # implemented entry, but guard against it explicitly rather than
        # silently letting one task's result clobber another's.
        raise NotImplementedError(
            "Running more than one implemented domain task in the same graph "
            "requires S3's multi-task result aggregation (not yet built) -- "
            f"select at most one of: {sorted(task.id for task in active_tasks)}."
        )

    graph = StateGraph(WorkflowState)
    graph.add_node("extractor", extractor_node)
    graph.add_node("llm_extraction_fallback", llm_extraction_fallback)
    graph.add_node("verifier", verifier_node)

    graph.set_entry_point("extractor")
    graph.add_conditional_edges(
        "extractor",
        _route_after_extractor,
        {"llm_extraction_fallback": "llm_extraction_fallback", "verifier": "verifier"},
    )
    graph.add_edge("llm_extraction_fallback", "verifier")

    if active_tasks:
        task = active_tasks[0]
        node_fn = globals()[task.workflow_node]
        graph.add_node(task.id, node_fn)
        graph.add_edge(task.id, END)

        def _route_after_verifier(state: WorkflowState) -> str:
            return task.id if state.get("complete") else END

        graph.add_conditional_edges("verifier", _route_after_verifier, {task.id: task.id, END: END})
    else:

        def _route_after_verifier(state: WorkflowState) -> str:
            return END

        graph.add_conditional_edges("verifier", _route_after_verifier, {END: END})

    return graph.compile()


def run_workflow(sections: list[PageSection], selected_task_ids: set[str] | None = None) -> WorkflowState:
    """Run the full workflow graph on parsed treaty sections.

    See build_workflow_graph() for selected_task_ids' meaning and default.
    """
    app = build_workflow_graph(selected_task_ids)
    return app.invoke({"sections": sections, "extraction_method": "none"})


def run_workflow_from_pdf(path: str | Path, selected_task_ids: set[str] | None = None) -> WorkflowState:
    """Parse a treaty PDF and run the full workflow graph on it.

    Raises ParserError (propagated from extract_treaty_sections) if the
    PDF cannot be read or has no extractable text. See build_workflow_graph()
    for selected_task_ids' meaning and default.
    """
    sections = extract_treaty_sections(path)
    logger.info("Parsed %d page(s) from %s", len(sections), path)
    return run_workflow(sections, selected_task_ids)
