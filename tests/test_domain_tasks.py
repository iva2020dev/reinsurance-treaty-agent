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


def test_only_b0_is_implemented():
    implemented = [task for task in DOMAIN_TASKS if task.implementation_status == "implemented"]

    assert len(implemented) == 1
    assert implemented[0].candidate_id == "B0"
    assert implemented[0].title == "Burn-Cost Check"
    assert implemented[0].workflow_node == "analyst_node"


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
