"""End-to-end integration tests for the full parse -> workflow pipeline.

Unlike tests/test_workflow.py (which tests each node in isolation),
these drive the real graph through run_workflow()/run_workflow_from_pdf()
with no node mocking, covering both success and failure paths.
"""

import pytest

from src.parser import ParserError, PageSection
from src.workflow import run_workflow, run_workflow_from_pdf

MINIMAL_TREATY_PATH = "data/sample_treaty.pdf"
RICH_TREATY_PATH = "data/sample_rich_treaty.pdf"


def test_full_pipeline_success_minimal_treaty():
    result = run_workflow_from_pdf(MINIMAL_TREATY_PATH)

    assert result["complete"] is True
    report = result["report"]
    assert report is not None
    assert report.treaty.cedent_name == "Acme Insurance Co."
    assert report.loss_ratio == pytest.approx(0.3)
    assert report.findings == []


def test_full_pipeline_success_rich_treaty():
    result = run_workflow_from_pdf(RICH_TREATY_PATH)

    assert result["complete"] is True
    report = result["report"]
    assert report is not None
    assert report.treaty.cedent_name == "Meridian Insurance Group, Inc."
    assert report.loss_ratio == pytest.approx(1.25)
    assert len(report.findings) == 1
    assert report.findings[0].severity == "high"


def test_full_pipeline_malformed_pdf_raises_parser_error(tmp_path):
    bad_path = tmp_path / "not_a_pdf.pdf"
    bad_path.write_bytes(b"not a pdf at all")

    with pytest.raises(ParserError):
        run_workflow_from_pdf(bad_path)


def test_full_pipeline_unknown_cedent_handled_gracefully():
    sections = [
        PageSection(
            page_number=1,
            text=(
                "Cedent: Nonexistent Cedent LLC\n"
                "Attachment Point: 500,000\n"
                "Limit: 1,000,000\n"
                "Reinsurance Premium: 50,000"
            ),
        )
    ]

    result = run_workflow(sections)

    assert result["complete"] is True
    report = result["report"]
    assert report is not None
    assert report.claims == []
    assert report.loss_ratio == 0.0
    assert len(report.findings) == 1
    assert report.findings[0].severity == "low"
    assert "No historical claims data" in report.findings[0].description


def test_full_pipeline_missing_required_term_handled_gracefully():
    sections = [
        PageSection(
            page_number=1,
            text="Cedent: Acme Insurance Co.\nAttachment Point: 500,000",
            # Missing "Limit:" and "Reinsurance Premium:" entirely.
        )
    ]

    result = run_workflow(sections)

    assert result["complete"] is False
    assert result.get("report") is None
    assert "limit" in result["missing_fields"]
    assert "reinsurance_premium" in result["missing_fields"]
