"""Tests for src.workflow."""

from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.models import ClaimsData, Severity, TreatyTerms
from src.parser import PageSection, extract_treaty_sections
from src.workflow import (
    analyst_node,
    extract_treaty_terms,
    extractor_node,
    llm_extraction_fallback,
    run_workflow,
    verifier_node,
)

SAMPLE_RICH_FUZZY_TREATY_PATH = "data/sample_rich_fuzzy_treaty.pdf"

WELL_FORMED_SECTIONS = [
    PageSection(
        page_number=1,
        text=(
            "REINSURANCE TREATY AGREEMENT\n"
            "Cedent: Test Cedent Co.\n"
            "Attachment Point: 100,000\n"
            "Limit: 200,000\n"
            "Reinsurance Premium: 10,000"
        ),
    ),
    PageSection(
        page_number=2,
        text=("EXCLUSIONS\nThis treaty excludes losses arising from:\nFire\nFlood"),
    ),
]

INCOMPLETE_SECTIONS = [
    PageSection(page_number=1, text="REINSURANCE TREATY AGREEMENT\nCedent: Test Cedent Co."),
]


def test_extractor_node_well_formed_input():
    result = extractor_node({"sections": WELL_FORMED_SECTIONS})

    treaty = result["treaty"]
    assert treaty is not None
    assert result["missing_fields"] == []
    assert treaty.cedent_name == "Test Cedent Co."
    assert treaty.attachment_point == 100_000
    assert treaty.limit == 200_000
    assert treaty.reinsurance_premium == 10_000
    assert treaty.exclusions == ["Fire", "Flood"]
    assert treaty.page_citations["attachment_point"] == 1
    assert treaty.page_citations["exclusions"] == 2


def test_extractor_node_flags_missing_fields():
    result = extractor_node({"sections": INCOMPLETE_SECTIONS})

    assert result["treaty"] is None
    assert "attachment_point" in result["missing_fields"]
    assert "limit" in result["missing_fields"]
    assert "reinsurance_premium" in result["missing_fields"]


def test_extract_treaty_terms_fails_on_fuzzy_prose_treaty():
    """Same substantive facts as the rich fixture, phrased as prose so
    regex genuinely can't find any required field -- the case the LLM
    fallback (a later task) needs to actually exercise."""
    sections = extract_treaty_sections(SAMPLE_RICH_FUZZY_TREATY_PATH)

    treaty, missing_fields = extract_treaty_terms(sections)

    assert treaty is None
    assert set(missing_fields) == {
        "cedent_name",
        "attachment_point",
        "limit",
        "reinsurance_premium",
    }


def test_llm_extraction_fallback_not_invoked_when_regex_succeeds(monkeypatch):
    mock_llm_node = MagicMock(side_effect=AssertionError("llm_extraction_fallback should not run"))
    monkeypatch.setattr("src.workflow.llm_extraction_fallback", mock_llm_node)

    result = run_workflow(WELL_FORMED_SECTIONS)

    mock_llm_node.assert_not_called()
    assert result["extraction_method"] == "regex"
    assert result["complete"] is True


def test_llm_extraction_fallback_succeeds_on_fuzzy_treaty(monkeypatch):
    tool_use_block = SimpleNamespace(
        type="tool_use",
        input={
            "cedent_name": "Sentinel Mutual Assurance",
            "attachment_point": 200_000,
            "limit": 1_000_000,
            "reinsurance_premium": 400_000,
            "exclusions": ["War", "Nuclear"],
            "page_citations": {
                "cedent_name": 1,
                "attachment_point": 2,
                "limit": 2,
                "reinsurance_premium": 2,
                "exclusions": 3,
            },
        },
    )
    mock_client = MagicMock()
    mock_usage = SimpleNamespace(input_tokens=512, output_tokens=64)
    mock_client.messages.create.return_value = SimpleNamespace(
        content=[tool_use_block], usage=mock_usage
    )
    monkeypatch.setattr("src.workflow.anthropic.Anthropic", lambda **kwargs: mock_client)

    sections = extract_treaty_sections(SAMPLE_RICH_FUZZY_TREATY_PATH)
    _, missing_fields = extract_treaty_terms(sections)
    assert missing_fields  # sanity: regex genuinely fails on this fixture first

    result = llm_extraction_fallback({"sections": sections})

    assert result["extraction_method"] == "llm"
    assert result["llm_error"] is None
    assert result["missing_fields"] == []
    treaty = result["treaty"]
    assert treaty.cedent_name == "Sentinel Mutual Assurance"
    assert treaty.attachment_point == 200_000
    assert treaty.limit == 1_000_000
    assert treaty.reinsurance_premium == 400_000
    mock_client.messages.create.assert_called_once()
    assert mock_client.messages.create.call_args.kwargs["tool_choice"] == {
        "type": "tool",
        "name": "extract_treaty_terms",
    }


def test_run_workflow_via_llm_extraction_fallback_flags_medium_finding(monkeypatch):
    """End-to-end: regex fails on the fuzzy fixture, the (mocked) LLM
    Extraction Fallback succeeds, and the real historical claim
    ($900,000, exceeding the mocked $200,000 attachment point) produces
    a non-zero loss ratio and a real MEDIUM finding -- not just an
    empty-findings happy path."""
    tool_use_block = SimpleNamespace(
        type="tool_use",
        input={
            "cedent_name": "Sentinel Mutual Assurance",
            "attachment_point": 200_000,
            "limit": 1_000_000,
            "reinsurance_premium": 400_000,
            "exclusions": [],
            "page_citations": {
                "cedent_name": 1,
                "attachment_point": 2,
                "limit": 2,
                "reinsurance_premium": 2,
            },
        },
    )
    mock_client = MagicMock()
    mock_client.messages.create.return_value = SimpleNamespace(
        content=[tool_use_block],
        usage=SimpleNamespace(input_tokens=512, output_tokens=64),
    )
    monkeypatch.setattr("src.workflow.anthropic.Anthropic", lambda **kwargs: mock_client)

    sections = extract_treaty_sections(SAMPLE_RICH_FUZZY_TREATY_PATH)
    result = run_workflow(sections)

    assert result["complete"] is True
    assert result["extraction_method"] == "llm"
    report = result["report"]
    assert report.loss_ratio == pytest.approx(0.7)
    assert len(report.findings) == 1
    assert report.findings[0].severity == Severity.MEDIUM


def test_llm_extraction_fallback_degrades_gracefully_on_failure(monkeypatch):
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = RuntimeError("simulated network failure")
    monkeypatch.setattr("src.workflow.anthropic.Anthropic", lambda **kwargs: mock_client)

    result = llm_extraction_fallback({"sections": []})

    assert result == {
        "extraction_method": "none",
        "llm_error": "RuntimeError: simulated network failure",
    }


def test_run_workflow_stays_incomplete_when_llm_extraction_fallback_also_fails(monkeypatch):
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = RuntimeError("simulated network failure")
    monkeypatch.setattr("src.workflow.anthropic.Anthropic", lambda **kwargs: mock_client)

    sections = extract_treaty_sections(SAMPLE_RICH_FUZZY_TREATY_PATH)
    result = run_workflow(sections)

    assert result["complete"] is False
    assert result["treaty"] is None
    assert result["extraction_method"] == "none"
    assert result["llm_error"] is not None
    mock_client.messages.create.assert_called_once()


def test_verifier_node_complete_triggers_historical_claims_lookup():
    treaty = TreatyTerms(
        cedent_name="Acme Insurance Co.",
        attachment_point=1_000_000,
        limit=5_000_000,
        reinsurance_premium=250_000,
    )

    result = verifier_node({"treaty": treaty})

    assert result["complete"] is True
    assert len(result["claims"]) == 3
    assert all(c.cedent_name == "Acme Insurance Co." for c in result["claims"])


def test_verifier_node_flags_incompleteness_without_calling_tools():
    result = verifier_node({"treaty": None})

    assert result["complete"] is False
    assert result["claims"] == []


def test_analyst_node_no_anomalies():
    treaty = TreatyTerms(
        cedent_name="X", attachment_point=1_000_000, limit=5_000_000, reinsurance_premium=250_000
    )
    claims = [ClaimsData(cedent_name="X", claim_amount=1_100_000, claim_date=date(2025, 1, 1))]

    result = analyst_node({"treaty": treaty, "claims": claims})

    report = result["report"]
    assert report.findings == []
    assert report.loss_ratio == 100_000 / 5_000_000


def test_analyst_node_flags_at_least_one_anomaly():
    treaty = TreatyTerms(
        cedent_name="X", attachment_point=1_000_000, limit=5_000_000, reinsurance_premium=250_000
    )

    result = analyst_node({"treaty": treaty, "claims": []})

    report = result["report"]
    assert len(report.findings) >= 1
    assert report.findings[0].severity == Severity.LOW
    assert "No historical claims data" in report.findings[0].description
