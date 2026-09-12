"""Semantic compliance/clause matching (B6): an LLM-shaped version of B1
(exclusion_completeness_checklist) that matches mandatory-clause *intent*
rather than keyword substrings, so it survives wording variation B1's
keyword-matching approach would miss (e.g. "acts of aggression between
sovereign states" for "war").

Reuses B1's own mandatory-clause category labels (not its keyword
lists, which are irrelevant here -- this task judges intent directly
against the raw exclusions text, not substring matches).
"""

import logging
import time

from src.cost_estimation import actual_task_cost
from src.llm_client import call_with_retry, get_client
from src.models import AnomalyFinding, Severity, TaskResult
from src.services.exclusion_completeness_checklist import MANDATORY_EXCLUSION_CLAUSES
from src.workflow_state import WorkflowState

logger = logging.getLogger(__name__)

_LLM_MODEL = "claude-haiku-4-5-20251001"
_LLM_TIMEOUT_SECONDS = 30.0

_MANDATORY_CLAUSE_CATEGORIES = tuple(MANDATORY_EXCLUSION_CLAUSES.keys())

_SEMANTIC_CLAUSE_MATCHING_TOOL = {
    "name": "assess_clause_coverage",
    "description": (
        "Assess whether each mandatory exclusion clause category's *intent* "
        "is covered by the treaty's exclusions text, even if the text is "
        "worded very differently from the category's own name (e.g. 'acts "
        "of aggression between sovereign states' covers the 'war' category)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "missing_categories": {
                "type": "array",
                "items": {"type": "string", "enum": list(_MANDATORY_CLAUSE_CATEGORIES)},
                "description": "Category labels whose intent is NOT covered by the exclusions text.",
            }
        },
        "required": ["missing_categories"],
    },
}


def _build_prompt(exclusions: list[str]) -> str:
    exclusions_text = "\n".join(f"- {clause}" for clause in exclusions) if exclusions else "(none extracted)"
    categories_text = ", ".join(_MANDATORY_CLAUSE_CATEGORIES)
    return (
        "Here is a reinsurance treaty's extracted exclusions text:\n\n"
        f"{exclusions_text}\n\n"
        f"Mandatory exclusion clause categories to check for: {categories_text}. "
        "Use the assess_clause_coverage tool to report which of these "
        "categories' intent is NOT covered by the exclusions text above, "
        "even when phrased differently than the category name itself."
    )


def semantic_clause_matching_node(state: WorkflowState) -> dict:
    """Flag any mandatory exclusion clause category whose *intent* isn't
    covered by the treaty's exclusions text (the Semantic Compliance/
    Clause Matching, B6).

    Unlike this repo's deterministic task nodes, this one is wired into
    build_workflow_graph()'s fan-out, so a failure here must degrade to a
    TaskResult(status="failed") rather than raise -- raising would crash
    the whole multi-task run for every other selected task too.
    """
    started_at = time.perf_counter()
    treaty = state["treaty"]

    def _create_completion():
        client = get_client(timeout=_LLM_TIMEOUT_SECONDS)
        return client.messages.create(
            model=_LLM_MODEL,
            max_tokens=256,
            tools=[_SEMANTIC_CLAUSE_MATCHING_TOOL],
            tool_choice={"type": "tool", "name": "assess_clause_coverage"},
            messages=[{"role": "user", "content": _build_prompt(treaty.exclusions)}],
        )

    try:
        response = call_with_retry(_create_completion, description="Semantic Clause Matching")
        tool_use = next(block for block in response.content if block.type == "tool_use")
        missing_categories = tool_use.input.get("missing_categories", [])
        usage = response.usage
    except Exception as exc:  # noqa: BLE001 -- any failure must degrade gracefully, not crash the run
        latency = time.perf_counter() - started_at
        logger.info(
            "[semantic_clause_matching] Semantic Clause Matching: failed after %.2fs (%s: %s)",
            latency,
            type(exc).__name__,
            exc,
        )
        return {
            "task_results": {
                "semantic_clause_matching": TaskResult(status="failed", findings=[], cost=0.0, latency=latency)
            }
        }

    findings = [
        AnomalyFinding(
            field="exclusions",
            description=(
                f"Mandatory exclusion clause not found in this treaty (semantic check): {category}."
            ),
            severity=Severity.MEDIUM,
        )
        for category in sorted(missing_categories)
    ]

    latency = time.perf_counter() - started_at
    cost = actual_task_cost(usage.input_tokens, usage.output_tokens)
    task_result = TaskResult(status="ran", findings=findings, cost=cost, latency=latency)
    logger.info(
        "[semantic_clause_matching] Semantic Clause Matching: %d missing categor%s in %.2fs "
        "(model=%s, input_tokens=%d, output_tokens=%d)",
        len(findings),
        "y" if len(findings) == 1 else "ies",
        latency,
        _LLM_MODEL,
        usage.input_tokens,
        usage.output_tokens,
    )
    return {"task_results": {"semantic_clause_matching": task_result}}
