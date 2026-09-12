"""Key-date/renewal calendar extraction (B2): flag treaties approaching
renewal or a notice-period deadline.

Unlike burn_cost_check_node/exclusion_completeness_checklist_node (which
read from the already-extracted state["treaty"]), this task regexes the
raw parsed page sections directly -- TreatyTerms doesn't model dates at
all, and this task's own scope (per TASKS.md) is a self-contained pass
over text, not a shared-schema change.
"""

import logging
import re
import time
from datetime import date, timedelta

from src.models import AnomalyFinding, Severity, TaskResult
from src.parser import PageSection
from src.workflow_state import WorkflowState

logger = logging.getLogger(__name__)

# Flag an expiry or notice deadline within this many days as "approaching"
# (MEDIUM); a deadline already passed is always HIGH regardless of window.
RENEWAL_WINDOW_DAYS = 90

_INCEPTION_DATE_PATTERN = re.compile(r"Inception Date:\s*(\d{4}-\d{2}-\d{2})")
_EXPIRY_DATE_PATTERN = re.compile(r"Expiry Date:\s*(\d{4}-\d{2}-\d{2})")
_NOTICE_PERIOD_PATTERN = re.compile(r"Notice Period:\s*(\d+)\s*days?", re.IGNORECASE)


def _search_date(sections: list[PageSection], pattern: re.Pattern) -> date | None:
    """First match (in page order) wins, same convention as extract_treaty_terms()."""
    for section in sections:
        match = pattern.search(section.text)
        if match:
            return date.fromisoformat(match.group(1))
    return None


def _search_notice_period_days(sections: list[PageSection]) -> int | None:
    for section in sections:
        match = _NOTICE_PERIOD_PATTERN.search(section.text)
        if match:
            return int(match.group(1))
    return None


def key_date_renewal_calendar_extraction_node(state: WorkflowState) -> dict:
    """Extract inception/expiry/notice-period dates and flag an approaching
    or already-passed renewal/notice deadline (the Key-Date/Renewal
    Calendar Extraction, B2).
    """
    started_at = time.perf_counter()
    sections = state.get("sections", [])

    inception_date = _search_date(sections, _INCEPTION_DATE_PATTERN)
    expiry_date = _search_date(sections, _EXPIRY_DATE_PATTERN)
    notice_period_days = _search_notice_period_days(sections)

    findings = []
    today = date.today()

    if inception_date is None and expiry_date is None:
        findings.append(
            AnomalyFinding(
                field="key_dates",
                description="No inception/expiry dates found in this treaty.",
                severity=Severity.LOW,
            )
        )
    elif expiry_date is not None:
        days_until_expiry = (expiry_date - today).days
        if days_until_expiry < 0:
            findings.append(
                AnomalyFinding(
                    field="expiry_date",
                    description=(
                        f"Treaty expired on {expiry_date.isoformat()} "
                        f"({-days_until_expiry} day(s) ago) -- renewal is overdue."
                    ),
                    severity=Severity.HIGH,
                )
            )
        elif days_until_expiry <= RENEWAL_WINDOW_DAYS:
            findings.append(
                AnomalyFinding(
                    field="expiry_date",
                    description=(
                        f"Treaty expires on {expiry_date.isoformat()} "
                        f"({days_until_expiry} day(s) from now) -- approaching renewal."
                    ),
                    severity=Severity.MEDIUM,
                )
            )

        if notice_period_days is not None:
            notice_deadline = expiry_date - timedelta(days=notice_period_days)
            days_until_notice_deadline = (notice_deadline - today).days
            if days_until_notice_deadline < 0 <= days_until_expiry:
                findings.append(
                    AnomalyFinding(
                        field="notice_period",
                        description=(
                            f"The notice-period deadline for this treaty's renewal was "
                            f"{notice_deadline.isoformat()} -- notify the reinsurer per the "
                            "notice clause without further delay."
                        ),
                        severity=Severity.HIGH,
                    )
                )
            elif 0 <= days_until_notice_deadline <= RENEWAL_WINDOW_DAYS and days_until_expiry >= 0:
                findings.append(
                    AnomalyFinding(
                        field="notice_period",
                        description=(
                            f"The notice-period deadline for this treaty's renewal is "
                            f"{notice_deadline.isoformat()} ({days_until_notice_deadline} day(s) "
                            "from now)."
                        ),
                        severity=Severity.MEDIUM,
                    )
                )

    latency = time.perf_counter() - started_at
    # Deterministic task (date arithmetic only, no LLM call) -- cost is
    # always 0.0, matching src/cost_estimation.py's estimate_task_cost()
    # for deterministic-shaped tasks.
    task_result = TaskResult(status="ran", findings=findings, cost=0.0, latency=latency)
    logger.info(
        "[key_date_renewal_calendar_extraction] Key-Date/Renewal Calendar Extraction: %d finding(s)",
        len(findings),
    )
    return {"task_results": {"key_date_renewal_calendar_extraction": task_result}}
