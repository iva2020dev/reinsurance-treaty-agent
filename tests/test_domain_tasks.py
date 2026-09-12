"""Tests for src.domain_tasks: the candidate domain task registry."""

from src.domain_tasks import DOMAIN_TASKS

_EXPECTED_CANDIDATE_IDS = {
    "B0", "B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B9",
    "C1", "C2", "C3", "C4", "C5",
    "F1", "F2", "F3", "F4",
}


def test_registry_has_one_entry_per_candidate_task():
    candidate_ids = [task.candidate_id for task in DOMAIN_TASKS]

    assert len(candidate_ids) == len(_EXPECTED_CANDIDATE_IDS)
    assert set(candidate_ids) == _EXPECTED_CANDIDATE_IDS


def test_ids_are_unique():
    ids = [task.id for task in DOMAIN_TASKS]

    assert len(ids) == len(set(ids))


def test_b0_b1_b2_b7_are_implemented():
    implemented = {task.candidate_id: task for task in DOMAIN_TASKS if task.implementation_status == "implemented"}

    assert set(implemented) == {"B0", "B1", "B2", "B7"}
    assert implemented["B0"].title == "Burn-Cost Check"
    assert implemented["B0"].workflow_node == "burn_cost_check_node"
    assert implemented["B1"].title == "Mandatory-clause / exclusion completeness checklist"
    assert implemented["B1"].workflow_node == "exclusion_completeness_checklist_node"
    assert implemented["B2"].title == "Key-date/renewal calendar extraction"
    assert implemented["B2"].workflow_node == "key_date_renewal_calendar_extraction_node"
    # B7 (Plain-English treaty summary) is deliberately implemented with NO
    # workflow_node -- it's a standalone opt-in feature with its own UI
    # trigger, not a graph node (see src/domain_tasks.py's module docstring
    # and src/services/plain_english_treaty_summary.py).
    assert implemented["B7"].title == "Plain-English treaty summary"
    assert implemented["B7"].workflow_node is None


def test_non_implemented_tasks_have_no_workflow_node():
    for task in DOMAIN_TASKS:
        if task.implementation_status == "not_implemented":
            assert task.workflow_node is None


def test_every_entry_has_required_fields_populated_with_valid_values():
    for task in DOMAIN_TASKS:
        assert task.id
        assert task.title
        assert task.candidate_id
        assert task.implementation_status in ("implemented", "not_implemented")
        assert task.shape in ("deterministic", "hybrid", "llm")
