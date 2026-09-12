"""Burn-Cost Check (B0): compare treaty terms against historical claims."""

import logging
import time

from src.models import AnomalyFinding, AnomalyReport, Severity, TaskResult
from src.tools import calculate_loss_ratio
from src.workflow_state import WorkflowState

logger = logging.getLogger(__name__)

LOSS_RATIO_MEDIUM_THRESHOLD = 0.5
LOSS_RATIO_HIGH_THRESHOLD = 1.0


def burn_cost_check_node(state: WorkflowState) -> dict:
    """Compare treaty terms against historical claims and flag anomalies (the Burn-Cost Check, B0)."""
    started_at = time.perf_counter()
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
    latency = time.perf_counter() - started_at
    # Burn-Cost Check is a deterministic task (no LLM call) -- cost is always
    # 0.0, matching src/cost_estimation.py's estimate_task_cost() for
    # deterministic-shaped tasks.
    task_result = TaskResult(status="ran", findings=findings, cost=0.0, latency=latency)
    logger.info(
        "[burn_cost_check] Burn-Cost Check: loss ratio %.2f, %d finding(s)",
        loss_ratio,
        len(findings),
    )
    return {"report": report, "task_results": {"burn_cost_check": task_result}}
