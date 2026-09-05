"""Tests for src.workflow."""

from datetime import date

from src.models import ClaimsData, Severity, TreatyTerms
from src.parser import PageSection, extract_treaty_sections
from src.workflow import analyst_node, extract_treaty_terms, extractor_node, verifier_node

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
