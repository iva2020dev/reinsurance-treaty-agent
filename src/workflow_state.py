"""Shared LangGraph state definition for the workflow graph.

Split out of src/workflow.py so that per-task service modules under
src/services/ (each defining a node function that takes WorkflowState)
can import this without creating a circular import with workflow.py,
which itself imports those service modules' node functions.
"""

from typing import Annotated, Literal, TypedDict

from src.models import AnomalyReport, ClaimsData, TaskResult, TreatyTerms
from src.parser import PageSection


def _merge_task_results(
    left: dict[str, TaskResult] | None, right: dict[str, TaskResult] | None
) -> dict[str, TaskResult]:
    """Combine concurrent per-task result writes into one dict.

    LangGraph's default state channel rejects a second write to the same
    key within one step -- when multiple analysis nodes run in parallel
    (multi-task fan-out), each returns its own {task_id: TaskResult} entry
    for the *same* `task_results` key, so it needs this reducer to merge
    rather than conflict. Each node only ever writes its own task_id, so a
    plain dict union is safe -- no two nodes should ever share a key.
    """
    return {**(left or {}), **(right or {})}


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
    # Additive alongside `report` (not a replacement) -- keyed by domain-task
    # id (src/domain_tasks.py), populated only for tasks that actually ran.
    # Annotated with a merge reducer so multiple analysis nodes running in
    # parallel (multi-task fan-out) each contribute their own entry instead
    # of conflicting -- see _merge_task_results().
    task_results: Annotated[dict[str, TaskResult], _merge_task_results]
