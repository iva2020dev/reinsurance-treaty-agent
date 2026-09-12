"""Mandatory-clause / exclusion completeness checklist (B1)."""

import logging
import time

from src.models import AnomalyFinding, Severity, TaskResult
from src.workflow_state import WorkflowState

logger = logging.getLogger(__name__)

# Mandatory exclusion clauses expected in a well-drafted treaty (B1), each
# mapped to case-insensitive substring(s) that identify it in real exclusion
# text (which is full prose, e.g. "War and warlike operations," not a bare
# keyword) -- configurable list per the candidate task's own description.
MANDATORY_EXCLUSION_CLAUSES: dict[str, tuple[str, ...]] = {
    "war": ("war",),
    "nuclear": ("nuclear",),
    "cyber": ("cyber",),
    "pandemic": ("pandemic", "communicable disease", "epidemic"),
    "sanctions": ("sanctions",),
    "tria": ("tria", "terrorism"),
}


def _missing_mandatory_clauses(exclusions: list[str]) -> list[str]:
    """Mandatory clause labels (from MANDATORY_EXCLUSION_CLAUSES) with no
    matching keyword anywhere in the treaty's extracted exclusions text.
    """
    combined_text = " ".join(exclusions).lower()
    return [
        clause
        for clause, keywords in MANDATORY_EXCLUSION_CLAUSES.items()
        if not any(keyword in combined_text for keyword in keywords)
    ]


def exclusion_completeness_checklist_node(state: WorkflowState) -> dict:
    """Flag any mandatory exclusion clause missing from the treaty's
    extracted exclusions (the Mandatory-Clause / Exclusion Completeness
    Checklist, B1).
    """
    started_at = time.perf_counter()
    treaty = state["treaty"]
    missing = _missing_mandatory_clauses(treaty.exclusions)

    findings = [
        AnomalyFinding(
            field="exclusions",
            description=f"Mandatory exclusion clause not found in this treaty: {clause}.",
            severity=Severity.MEDIUM,
        )
        for clause in sorted(missing)
    ]

    latency = time.perf_counter() - started_at
    # Deterministic task (keyword matching only, no LLM call) -- cost is
    # always 0.0, matching src/cost_estimation.py's estimate_task_cost()
    # for deterministic-shaped tasks.
    task_result = TaskResult(status="ran", findings=findings, cost=0.0, latency=latency)
    logger.info(
        "[exclusion_completeness_checklist] Exclusion Completeness Checklist: %d missing clause(s)",
        len(findings),
    )
    return {"task_results": {"exclusion_completeness_checklist": task_result}}
