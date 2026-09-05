"""LangGraph state machine & agent logic."""

import logging
import re
import time
from pathlib import Path
from typing import Literal, TypedDict

import anthropic
from dotenv import load_dotenv
from langgraph.graph import END, StateGraph
from pydantic import ValidationError

from src.models import AnomalyFinding, AnomalyReport, ClaimsData, Severity, TreatyTerms
from src.parser import PageSection, extract_treaty_sections
from src.tools import calculate_loss_ratio, query_historical_claims

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
    _route_after_extractor). On any failure -- a missing/invalid API key,
    a network/timeout error, a malformed tool response, or a TreatyTerms
    validation error -- logs it and leaves the run in the same
    "incomplete" state the regex-only path already produces
    (treaty=None, missing_fields unchanged), rather than crashing.
    """
    started_at = time.perf_counter()
    try:
        client = anthropic.Anthropic(timeout=_LLM_TIMEOUT_SECONDS)
        response = client.messages.create(
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
    return {
        "treaty": treaty,
        "missing_fields": [],
        "extraction_method": "llm",
        "llm_error": None,
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


def analyst_node(state: WorkflowState) -> dict:
    """Compare treaty terms against historical claims and flag anomalies."""
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
        "Analyst: loss ratio %.2f, %d finding(s)",
        loss_ratio,
        len(findings),
    )
    return {"report": report}


def _route_after_extractor(state: WorkflowState) -> str:
    return "llm_extraction_fallback" if state.get("missing_fields") else "verifier"


def _route_after_verifier(state: WorkflowState) -> str:
    return "analyst" if state.get("complete") else END


def build_workflow_graph():
    """Build and compile the Extractor -> [LLM Extraction Fallback] -> Verifier -> Analyst LangGraph state machine."""
    graph = StateGraph(WorkflowState)
    graph.add_node("extractor", extractor_node)
    graph.add_node("llm_extraction_fallback", llm_extraction_fallback)
    graph.add_node("verifier", verifier_node)
    graph.add_node("analyst", analyst_node)

    graph.set_entry_point("extractor")
    graph.add_conditional_edges(
        "extractor",
        _route_after_extractor,
        {"llm_extraction_fallback": "llm_extraction_fallback", "verifier": "verifier"},
    )
    graph.add_edge("llm_extraction_fallback", "verifier")
    graph.add_conditional_edges("verifier", _route_after_verifier, {"analyst": "analyst", END: END})
    graph.add_edge("analyst", END)

    return graph.compile()


def run_workflow(sections: list[PageSection]) -> WorkflowState:
    """Run the full workflow graph on parsed treaty sections."""
    app = build_workflow_graph()
    return app.invoke({"sections": sections, "extraction_method": "none"})


def run_workflow_from_pdf(path: str | Path) -> WorkflowState:
    """Parse a treaty PDF and run the full workflow graph on it.

    Raises ParserError (propagated from extract_treaty_sections) if the
    PDF cannot be read or has no extractable text.
    """
    sections = extract_treaty_sections(path)
    logger.info("Parsed %d page(s) from %s", len(sections), path)
    return run_workflow(sections)
