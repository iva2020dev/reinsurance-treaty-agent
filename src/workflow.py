"""LangGraph state machine & agent logic."""

import re
from typing import TypedDict

from langgraph.graph import END, StateGraph
from pydantic import ValidationError

from src.models import AnomalyFinding, AnomalyReport, ClaimsData, Severity, TreatyTerms
from src.parser import PageSection
from src.tools import calculate_loss_ratio, query_historical_claims

_REQUIRED_FIELDS = ("cedent_name", "attachment_point", "limit", "reinsurance_premium")

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
    return {"treaty": treaty, "missing_fields": missing_fields}


def verifier_node(state: WorkflowState) -> dict:
    """Validate extraction completeness; if complete, fetch historical claims for the cedent."""
    treaty = state.get("treaty")
    if treaty is None:
        return {"complete": False, "claims": []}
    return {"complete": True, "claims": query_historical_claims(treaty.cedent_name)}


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
    return {"report": report}


def _route_after_verifier(state: WorkflowState) -> str:
    return "analyst" if state.get("complete") else END


def build_workflow_graph():
    """Build and compile the Extractor -> Verifier -> Analyst LangGraph state machine."""
    graph = StateGraph(WorkflowState)
    graph.add_node("extractor", extractor_node)
    graph.add_node("verifier", verifier_node)
    graph.add_node("analyst", analyst_node)

    graph.set_entry_point("extractor")
    graph.add_edge("extractor", "verifier")
    graph.add_conditional_edges("verifier", _route_after_verifier, {"analyst": "analyst", END: END})
    graph.add_edge("analyst", END)

    return graph.compile()


def run_workflow(sections: list[PageSection]) -> WorkflowState:
    """Run the full workflow graph on parsed treaty sections."""
    app = build_workflow_graph()
    return app.invoke({"sections": sections})
