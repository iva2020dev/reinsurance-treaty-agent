"""Tests for src.services.semantic_clause_matching.

These mock the LLM call and verify the node correctly wires a mocked
tool-use response into findings/TaskResult -- they test the node's
output-shape/wiring against varied *input* phrasing, not the live
model's actual semantic-judgment quality (that would require a real API
call and belongs in a golden-dataset eval suite, out of scope here).
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

from src.models import TreatyTerms
from src.services.semantic_clause_matching import semantic_clause_matching_node


def _mock_tool_client(missing_categories: list[str]) -> MagicMock:
    tool_use_block = SimpleNamespace(type="tool_use", input={"missing_categories": missing_categories})
    mock_client = MagicMock()
    mock_client.messages.create.return_value = SimpleNamespace(
        content=[tool_use_block], usage=SimpleNamespace(input_tokens=200, output_tokens=20)
    )
    return mock_client


def _treaty_with_exclusions(exclusions: list[str]) -> TreatyTerms:
    return TreatyTerms(
        cedent_name="X",
        attachment_point=1_000_000,
        limit=5_000_000,
        reinsurance_premium=250_000,
        exclusions=exclusions,
    )


def test_no_missing_categories_produces_no_findings(monkeypatch):
    mock_client = _mock_tool_client([])
    monkeypatch.setattr("src.llm_client.anthropic.Anthropic", lambda **kwargs: mock_client)
    treaty = _treaty_with_exclusions(["war", "nuclear", "cyber", "pandemic", "sanctions", "tria"])

    result = semantic_clause_matching_node({"treaty": treaty})

    task_result = result["task_results"]["semantic_clause_matching"]
    assert task_result.status == "ran"
    assert task_result.findings == []
    assert task_result.cost > 0.0


def test_some_missing_categories_produces_matching_findings(monkeypatch):
    mock_client = _mock_tool_client(["sanctions", "tria"])
    monkeypatch.setattr("src.llm_client.anthropic.Anthropic", lambda **kwargs: mock_client)
    treaty = _treaty_with_exclusions(["War and warlike operations", "Nuclear contamination"])

    result = semantic_clause_matching_node({"treaty": treaty})

    task_result = result["task_results"]["semantic_clause_matching"]
    assert task_result.status == "ran"
    assert len(task_result.findings) == 2
    descriptions = " ".join(f.description for f in task_result.findings)
    assert "sanctions" in descriptions
    assert "tria" in descriptions
    assert all(f.severity == "medium" for f in task_result.findings)


def test_llm_failure_degrades_to_failed_task_result_not_raise(monkeypatch):
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = RuntimeError("boom")
    monkeypatch.setattr("src.llm_client.anthropic.Anthropic", lambda **kwargs: mock_client)
    treaty = _treaty_with_exclusions(["War"])

    result = semantic_clause_matching_node({"treaty": treaty})

    task_result = result["task_results"]["semantic_clause_matching"]
    assert task_result.status == "failed"
    assert task_result.findings == []
    assert task_result.cost == 0.0


def test_wording_variation_war_recognized_via_mocked_intent_match(monkeypatch):
    """The mocked model recognizes 'acts of aggression between sovereign
    states' as covering 'war' -- verifies the node passes the raw
    exclusions text through untouched (not a keyword match) and reflects
    whatever the model concludes.
    """
    mock_client = _mock_tool_client([])  # model judges "war" as covered despite the wording
    monkeypatch.setattr("src.llm_client.anthropic.Anthropic", lambda **kwargs: mock_client)
    treaty = _treaty_with_exclusions(["Acts of aggression between sovereign states"])

    result = semantic_clause_matching_node({"treaty": treaty})

    assert "Acts of aggression between sovereign states" in mock_client.messages.create.call_args.kwargs[
        "messages"
    ][0]["content"]
    assert result["task_results"]["semantic_clause_matching"].findings == []


def test_wording_variation_nuclear_recognized_via_mocked_intent_match(monkeypatch):
    mock_client = _mock_tool_client([])
    monkeypatch.setattr("src.llm_client.anthropic.Anthropic", lambda **kwargs: mock_client)
    treaty = _treaty_with_exclusions(["Radioactive contamination arising from fission or fusion"])

    result = semantic_clause_matching_node({"treaty": treaty})

    assert result["task_results"]["semantic_clause_matching"].findings == []


def test_wording_variation_cyber_recognized_via_mocked_intent_match(monkeypatch):
    mock_client = _mock_tool_client([])
    monkeypatch.setattr("src.llm_client.anthropic.Anthropic", lambda **kwargs: mock_client)
    treaty = _treaty_with_exclusions(["Unauthorized access to or corruption of electronic systems or data"])

    result = semantic_clause_matching_node({"treaty": treaty})

    assert result["task_results"]["semantic_clause_matching"].findings == []


def test_wording_variation_pandemic_recognized_via_mocked_intent_match(monkeypatch):
    mock_client = _mock_tool_client([])
    monkeypatch.setattr("src.llm_client.anthropic.Anthropic", lambda **kwargs: mock_client)
    treaty = _treaty_with_exclusions(["Widespread infectious illness affecting the general population"])

    result = semantic_clause_matching_node({"treaty": treaty})

    assert result["task_results"]["semantic_clause_matching"].findings == []


def test_wording_variation_sanctions_recognized_via_mocked_intent_match(monkeypatch):
    mock_client = _mock_tool_client([])
    monkeypatch.setattr("src.llm_client.anthropic.Anthropic", lambda **kwargs: mock_client)
    treaty = _treaty_with_exclusions(["Trade or economic restrictions imposed by a governing authority"])

    result = semantic_clause_matching_node({"treaty": treaty})

    assert result["task_results"]["semantic_clause_matching"].findings == []


def test_wording_variation_tria_recognized_via_mocked_intent_match(monkeypatch):
    mock_client = _mock_tool_client([])
    monkeypatch.setattr("src.llm_client.anthropic.Anthropic", lambda **kwargs: mock_client)
    treaty = _treaty_with_exclusions(["Acts of politically or ideologically motivated violence"])

    result = semantic_clause_matching_node({"treaty": treaty})

    assert result["task_results"]["semantic_clause_matching"].findings == []
