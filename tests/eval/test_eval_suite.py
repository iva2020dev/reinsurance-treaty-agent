"""Tests for the extraction accuracy eval suite itself (tests/eval/).

Uses a mocked Anthropic client for the LLM-path cases (same pattern as
tests/test_workflow.py) so this suite is deterministic and needs no
real ANTHROPIC_API_KEY -- `python -m tests.eval.run_eval` is the tool
that exercises the real pipeline (including the live API) end to end.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

from tests.eval.golden_dataset import GOLDEN_DATASET, GoldenCase
from tests.eval.scorer import run_eval, score_case

SENTINEL_CASE = next(c for c in GOLDEN_DATASET if c.name == "sentinel_fuzzy")

CORRECT_SENTINEL_RESPONSE = {
    "cedent_name": "Sentinel Mutual Assurance",
    "attachment_point": 200_000,
    "limit": 1_000_000,
    "reinsurance_premium": 400_000,
    "exclusions": ["war or warlike operations", "nuclear reaction", "acts of terrorism", "pollution", "asbestos-related injury", "cyber-attacks", "pandemic"],
    "page_citations": {
        "cedent_name": 1,
        "attachment_point": 2,
        "limit": 2,
        "reinsurance_premium": 2,
    },
}


def _mock_llm_client(input_data: dict) -> MagicMock:
    mock_client = MagicMock()
    tool_use_block = SimpleNamespace(type="tool_use", input=input_data)
    mock_client.messages.create.return_value = SimpleNamespace(
        content=[tool_use_block],
        usage=SimpleNamespace(input_tokens=500, output_tokens=60),
    )
    return mock_client


def test_score_case_regex_path_cases_are_fully_correct():
    for case in GOLDEN_DATASET:
        if case.extraction_path != "regex":
            continue
        result = score_case(case)

        assert result.error is None
        assert all(result.field_correct.values())
        assert result.exclusions_precision == 1.0
        assert result.exclusions_recall == 1.0


def test_score_case_llm_path_correct_response_scores_perfectly(monkeypatch):
    monkeypatch.setattr(
        "src.llm_client.anthropic.Anthropic",
        lambda **kwargs: _mock_llm_client(CORRECT_SENTINEL_RESPONSE),
    )

    result = score_case(SENTINEL_CASE)

    assert result.error is None
    assert result.extraction_method == "llm"
    assert all(result.field_correct.values())
    assert result.exclusions_recall == 1.0


def test_score_case_flags_incorrect_field_from_corrupted_extraction(monkeypatch):
    """Simulates a regressed extraction (e.g. a corrupted tool schema/prompt):
    the LLM returns a wrong cedent name and an empty exclusions list."""
    corrupted_response = dict(
        CORRECT_SENTINEL_RESPONSE,
        cedent_name="A Totally Different Company",
        exclusions=[],
    )
    monkeypatch.setattr(
        "src.llm_client.anthropic.Anthropic",
        lambda **kwargs: _mock_llm_client(corrupted_response),
    )

    result = score_case(SENTINEL_CASE)

    assert result.field_correct["cedent_name"] is False
    assert result.field_correct["attachment_point"] is True
    assert result.exclusions_recall == 0.0


def test_run_eval_overall_accuracy_drops_when_a_case_regresses(monkeypatch):
    """The acceptance-criteria scenario: a deliberately-broken extraction is
    caught by a drop in scored accuracy across the dataset."""
    monkeypatch.setattr(
        "src.llm_client.anthropic.Anthropic",
        lambda **kwargs: _mock_llm_client(CORRECT_SENTINEL_RESPONSE),
    )
    regex_cases = [c for c in GOLDEN_DATASET if c.extraction_path == "regex"]
    baseline_report = run_eval(regex_cases + [SENTINEL_CASE])
    assert baseline_report.overall_accuracy() == 1.0

    broken_response = dict(CORRECT_SENTINEL_RESPONSE, attachment_point=1, limit=2, reinsurance_premium=3)
    monkeypatch.setattr(
        "src.llm_client.anthropic.Anthropic",
        lambda **kwargs: _mock_llm_client(broken_response),
    )
    regressed_report = run_eval(regex_cases + [SENTINEL_CASE])

    assert regressed_report.overall_accuracy() < baseline_report.overall_accuracy()


def test_score_case_handles_llm_failure_without_crashing(monkeypatch):
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = RuntimeError("simulated failure")
    monkeypatch.setattr("src.llm_client.anthropic.Anthropic", lambda **kwargs: mock_client)

    result = score_case(SENTINEL_CASE)

    assert result.error is not None
    assert all(value is False for value in result.field_correct.values())
    assert result.exclusions_precision == 0.0
    assert result.exclusions_recall == 0.0


def test_score_exclusions_matches_paraphrased_clauses_not_just_exact_strings():
    case = GoldenCase(
        name="paraphrase_check",
        pdf_path="data/sample_rich_fuzzy_treaty.pdf",
        extraction_path="llm",
        expected_cedent_name="Sentinel Mutual Assurance",
        expected_attachment_point=200_000,
        expected_limit=1_000_000,
        expected_reinsurance_premium=400_000,
        expected_exclusion_keywords=["war", "nuclear"],
    )
    from tests.eval.scorer import _score_exclusions

    precision, recall = _score_exclusions(
        case.expected_exclusion_keywords,
        ["Losses from War and hostilities", "Nuclear reaction of any kind"],
    )

    assert precision == 1.0
    assert recall == 1.0
