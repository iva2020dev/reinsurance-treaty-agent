"""Registry of every candidate domain task tracked in CANDIDATE_TASKS.md.

This is the single source of truth for what domain tasks exist, which
are actually implemented, and which workflow node(s) they need --
future consumers (a graph builder that only runs implemented+selected
tasks, a frontend task selector) read from this list rather than each
maintaining their own copy, so they can't drift apart.

Only `B0` (the Burn-Cost Check, `burn_cost_check_node` in `src/workflow.py`) is
implemented today; every other entry mirrors a still-`Proposed`
candidate in `CANDIDATE_TASKS.md`'s Business Domain tables and has no
workflow node yet.
"""

from dataclasses import dataclass
from typing import Literal

ImplementationStatus = Literal["implemented", "not_implemented"]
TaskShape = Literal["deterministic", "hybrid", "llm"]


@dataclass(frozen=True)
class DomainTask:
    id: str
    title: str
    candidate_id: str  # this task's ID in CANDIDATE_TASKS.md, e.g. "B0"
    implementation_status: ImplementationStatus
    shape: TaskShape
    workflow_node: str | None  # the src/workflow.py node function name, if implemented


DOMAIN_TASKS: list[DomainTask] = [
    # Business Domain -- Treaty (CANDIDATE_TASKS.md: B0-B9)
    DomainTask(
        id="burn_cost_check",
        title="Burn-Cost Check",
        candidate_id="B0",
        implementation_status="implemented",
        # Deterministic: burn_cost_check_node itself only does arithmetic
        # (calculate_loss_ratio + threshold checks) on already-extracted
        # data -- it never calls an LLM. The shared upstream extraction
        # pipeline can fall back to an LLM, but that's not this task's own
        # behavior; estimate_task_cost() must match what this node actually
        # does, not the pipeline it happens to run after.
        shape="deterministic",
        workflow_node="burn_cost_check_node",
    ),
    DomainTask(
        id="exclusion_completeness_checklist",
        title="Mandatory-clause / exclusion completeness checklist",
        candidate_id="B1",
        implementation_status="implemented",
        shape="deterministic",
        workflow_node="exclusion_completeness_checklist_node",
    ),
    DomainTask(
        id="key_date_renewal_calendar_extraction",
        title="Key-date/renewal calendar extraction",
        candidate_id="B2",
        implementation_status="not_implemented",
        shape="deterministic",
        workflow_node=None,
    ),
    DomainTask(
        id="renewal_year_over_year_diff",
        title="Renewal year-over-year diff",
        candidate_id="B3",
        implementation_status="not_implemented",
        shape="deterministic",
        workflow_node=None,
    ),
    DomainTask(
        id="multi_layer_program_extraction",
        title="Multi-layer program extraction & aggregation",
        candidate_id="B4",
        implementation_status="not_implemented",
        shape="deterministic",
        workflow_node=None,
    ),
    DomainTask(
        id="reinstatement_cost_modeling",
        title="Reinstatement cost modeling",
        candidate_id="B5",
        implementation_status="not_implemented",
        shape="deterministic",
        workflow_node=None,
    ),
    DomainTask(
        id="semantic_clause_matching",
        title="Semantic compliance/clause matching",
        candidate_id="B6",
        implementation_status="not_implemented",
        shape="llm",
        workflow_node=None,
    ),
    DomainTask(
        id="plain_english_treaty_summary",
        title="Plain-English treaty summary",
        candidate_id="B7",
        implementation_status="not_implemented",
        shape="llm",
        workflow_node=None,
    ),
    DomainTask(
        id="clause_ambiguity_detection",
        title="Clause ambiguity/contradiction detection",
        candidate_id="B8",
        implementation_status="not_implemented",
        shape="llm",
        workflow_node=None,
    ),
    DomainTask(
        id="peer_portfolio_benchmarking",
        title="Peer/portfolio benchmarking",
        candidate_id="B9",
        implementation_status="not_implemented",
        shape="deterministic",
        workflow_node=None,
    ),
    # Business Domain -- Claims (CANDIDATE_TASKS.md: C1-C5)
    DomainTask(
        id="large_loss_claim_flagging",
        title="Large-loss/catastrophe claim flagging",
        candidate_id="C1",
        implementation_status="not_implemented",
        shape="deterministic",
        workflow_node=None,
    ),
    DomainTask(
        id="claim_notification_compliance_check",
        title="Claim notification compliance check",
        candidate_id="C2",
        implementation_status="not_implemented",
        shape="deterministic",
        workflow_node=None,
    ),
    DomainTask(
        id="claims_bordereau_reconciliation",
        title="Claims bordereau reconciliation",
        candidate_id="C3",
        implementation_status="not_implemented",
        shape="deterministic",
        workflow_node=None,
    ),
    DomainTask(
        id="claim_exclusion_applicability_check",
        title="Claim exclusion applicability check",
        candidate_id="C4",
        implementation_status="not_implemented",
        shape="llm",
        workflow_node=None,
    ),
    DomainTask(
        id="reserve_development_tracking",
        title="Reserve development tracking",
        candidate_id="C5",
        implementation_status="not_implemented",
        shape="deterministic",
        workflow_node=None,
    ),
    # Business Domain -- Facultative (CANDIDATE_TASKS.md: F1-F4)
    DomainTask(
        id="facultative_submission_extraction",
        title="Facultative submission extraction",
        candidate_id="F1",
        implementation_status="not_implemented",
        shape="hybrid",
        workflow_node=None,
    ),
    DomainTask(
        id="facultative_treaty_overlap_check",
        title="Facultative vs. treaty overlap check",
        candidate_id="F2",
        implementation_status="not_implemented",
        shape="deterministic",
        workflow_node=None,
    ),
    DomainTask(
        id="cat_peril_exposure_geocoding",
        title="Cat/peril exposure geocoding",
        candidate_id="F3",
        implementation_status="not_implemented",
        shape="hybrid",
        workflow_node=None,
    ),
    DomainTask(
        id="risk_accumulation_pml_check",
        title="Risk accumulation/PML aggregation check",
        candidate_id="F4",
        implementation_status="not_implemented",
        shape="deterministic",
        workflow_node=None,
    ),
]
