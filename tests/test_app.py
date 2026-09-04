"""Tests for src.app: report formatting helpers and the running Streamlit UI."""

import json
from datetime import datetime
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from src.app import (
    analyze_uploaded_pdf,
    format_log_header,
    format_report_markdown,
    save_logs_to_file,
    serialize_state_for_debug,
)
from src.models import AnomalyFinding, AnomalyReport, ClaimsData, Severity, TreatyTerms
from src.parser import ParserError

RICH_TREATY_PATH = "data/sample_rich_treaty.pdf"
MINIMAL_TREATY_PATH = "data/sample_treaty.pdf"


def _sample_report() -> AnomalyReport:
    treaty = TreatyTerms(
        cedent_name="Acme Insurance Co.",
        attachment_point=100_000,
        limit=200_000,
        reinsurance_premium=10_000,
        exclusions=["Fire", "Flood"],
        page_citations={"cedent_name": 1, "attachment_point": 1, "exclusions": 2},
    )
    return AnomalyReport(
        treaty=treaty,
        claims=[ClaimsData(cedent_name="Acme Insurance Co.", claim_amount=50_000, claim_date="2024-01-01")],
        loss_ratio=1.25,
        findings=[
            AnomalyFinding(field="loss_ratio", description="Losses exceeded the limit.", severity=Severity.HIGH)
        ],
    )


def test_format_report_markdown_includes_terms_citations_and_findings():
    markdown = format_report_markdown(_sample_report())

    assert "Acme Insurance Co." in markdown
    assert "(p. 1)" in markdown
    assert "(p. 2)" in markdown
    assert "Fire, Flood" in markdown
    assert "1.25" in markdown
    assert "**[HIGH]** Losses exceeded the limit." in markdown


def test_format_report_markdown_no_findings():
    report = _sample_report().model_copy(update={"findings": []})

    markdown = format_report_markdown(report)

    assert "No anomalies found." in markdown


def test_analyze_uploaded_pdf_success():
    report = analyze_uploaded_pdf(Path(RICH_TREATY_PATH).read_bytes())

    assert report.treaty.cedent_name == "Meridian Insurance Group, Inc."
    assert report.loss_ratio == pytest.approx(1.25)


def test_analyze_uploaded_pdf_malformed_raises_parser_error():
    with pytest.raises(ParserError):
        analyze_uploaded_pdf(b"not a pdf at all")


def test_app_upload_and_render_success():
    at = AppTest.from_file("../src/app.py")
    at.run()

    with open(MINIMAL_TREATY_PATH, "rb") as f:
        at.file_uploader[0].set_value([("sample_treaty.pdf", f.read(), "application/pdf")])
    at.run()

    assert not at.exception
    markdown_text = "\n".join(m.value for m in at.markdown)
    assert "Acme Insurance Co." in markdown_text


def test_app_upload_malformed_pdf_shows_error_not_crash():
    at = AppTest.from_file("../src/app.py")
    at.run()

    at.file_uploader[0].set_value([("bad.pdf", b"not a pdf at all", "application/pdf")])
    at.run()

    assert not at.exception
    assert len(at.error) == 1
    assert "Could not read this PDF" in at.error[0].value


def test_serialize_state_for_debug_is_json_safe():
    report = _sample_report()
    state = {
        "sections": [],
        "treaty": report.treaty,
        "missing_fields": [],
        "claims": report.claims,
        "complete": True,
        "report": report,
    }

    debug_dict = serialize_state_for_debug(state)
    json.dumps(debug_dict)  # must not raise

    assert debug_dict["treaty"]["cedent_name"] == "Acme Insurance Co."
    assert debug_dict["report"]["loss_ratio"] == pytest.approx(1.25)


def test_app_debug_panel_shows_log_lines_and_state_on_success():
    at = AppTest.from_file("../src/app.py")
    at.run()

    with open(MINIMAL_TREATY_PATH, "rb") as f:
        at.file_uploader[0].set_value([("sample_treaty.pdf", f.read(), "application/pdf")])
    at.run()

    assert not at.exception
    assert len(at.expander) == 1
    log_text = "\n".join(c.value for c in at.code)
    assert "src.workflow" in log_text
    assert "Extractor" in log_text
    assert "Analyst" in log_text

    debug_state = json.loads(at.json[0].value)
    assert debug_state["treaty"]["cedent_name"] == "Acme Insurance Co."
    assert debug_state["complete"] is True


def test_app_debug_panel_shows_log_lines_on_parser_failure():
    at = AppTest.from_file("../src/app.py")
    at.run()

    at.file_uploader[0].set_value([("bad.pdf", b"not a pdf at all", "application/pdf")])
    at.run()

    assert not at.exception
    log_text = "\n".join(c.value for c in at.code)
    assert log_text == ""  # ParserError raised before any node logs anything
    assert len(at.json) == 0  # no state was produced to show


def test_format_log_header_includes_timestamp_and_filename():
    header = format_log_header("sample_treaty.pdf", when=datetime(2026, 9, 4, 10, 15, 32))

    assert header == "=== Run at 2026-09-04 10:15:32 | file: sample_treaty.pdf ==="


def test_save_logs_to_file_overwrite_replaces_existing_content(tmp_path):
    path = tmp_path / "workflow.log"
    path.write_text("stale line\n")

    save_logs_to_file(["new line"], mode="overwrite", path=path)

    assert path.read_text() == "new line\n"


def test_save_logs_to_file_append_keeps_existing_content(tmp_path):
    path = tmp_path / "workflow.log"
    path.write_text("first line\n")

    save_logs_to_file(["second line"], mode="append", path=path)

    assert path.read_text() == "first line\nsecond line\n"


def test_save_logs_to_file_creates_parent_directory(tmp_path):
    path = tmp_path / "logs" / "workflow.log"

    save_logs_to_file(["a line"], mode="overwrite", path=path)

    assert path.read_text() == "a line\n"


def test_app_save_button_writes_default_log_file(tmp_path, monkeypatch):
    pdf_bytes = Path(MINIMAL_TREATY_PATH).read_bytes()
    monkeypatch.chdir(tmp_path)

    at = AppTest.from_file("../src/app.py")
    at.run()
    at.file_uploader[0].set_value([("sample_treaty.pdf", pdf_bytes, "application/pdf")])
    at.run()

    at.segmented_control[0].set_value("Overwrite").run()
    at.button[0].click().run()

    assert not at.exception
    log_file = tmp_path / "logs" / "workflow.log"
    assert log_file.exists()
    content = log_file.read_text()
    assert "=== Run at " in content
    assert "file: sample_treaty.pdf ===" in content
    assert "Extractor" in content
    assert any("Saved" in s.value for s in at.success)