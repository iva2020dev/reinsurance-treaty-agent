"""Tests for src.services.key_date_renewal_calendar_extraction."""

from datetime import date, timedelta

from src.parser import PageSection
from src.services.key_date_renewal_calendar_extraction import (
    RENEWAL_WINDOW_DAYS,
    key_date_renewal_calendar_extraction_node,
)


def _sections(text: str) -> list[PageSection]:
    return [PageSection(page_number=1, text=text)]


def test_no_dates_found_flags_low_severity():
    result = key_date_renewal_calendar_extraction_node({"sections": _sections("Cedent: Test Co.")})

    task_result = result["task_results"]["key_date_renewal_calendar_extraction"]
    assert task_result.status == "ran"
    assert len(task_result.findings) == 1
    assert task_result.findings[0].severity == "low"
    assert "No inception/expiry dates" in task_result.findings[0].description


def test_expiry_far_in_future_produces_no_findings():
    expiry = date.today() + timedelta(days=RENEWAL_WINDOW_DAYS + 30)
    sections = _sections(f"Inception Date: 2020-01-01\nExpiry Date: {expiry.isoformat()}")

    result = key_date_renewal_calendar_extraction_node({"sections": sections})

    assert result["task_results"]["key_date_renewal_calendar_extraction"].findings == []


def test_expiry_within_window_flags_medium():
    expiry = date.today() + timedelta(days=30)
    sections = _sections(f"Expiry Date: {expiry.isoformat()}")

    result = key_date_renewal_calendar_extraction_node({"sections": sections})

    findings = result["task_results"]["key_date_renewal_calendar_extraction"].findings
    assert len(findings) == 1
    assert findings[0].field == "expiry_date"
    assert findings[0].severity == "medium"
    assert "approaching renewal" in findings[0].description


def test_expiry_already_passed_flags_high():
    expiry = date.today() - timedelta(days=5)
    sections = _sections(f"Expiry Date: {expiry.isoformat()}")

    result = key_date_renewal_calendar_extraction_node({"sections": sections})

    findings = result["task_results"]["key_date_renewal_calendar_extraction"].findings
    assert len(findings) == 1
    assert findings[0].field == "expiry_date"
    assert findings[0].severity == "high"
    assert "overdue" in findings[0].description


def test_notice_period_deadline_already_passed_flags_high_alongside_expiry():
    expiry = date.today() + timedelta(days=10)
    sections = _sections(f"Expiry Date: {expiry.isoformat()}\nNotice Period: 30 days")

    result = key_date_renewal_calendar_extraction_node({"sections": sections})

    findings = result["task_results"]["key_date_renewal_calendar_extraction"].findings
    fields = {f.field for f in findings}
    assert fields == {"expiry_date", "notice_period"}
    notice_finding = next(f for f in findings if f.field == "notice_period")
    assert notice_finding.severity == "high"
    assert "notify the reinsurer" in notice_finding.description


def test_notice_period_deadline_upcoming_flags_medium():
    expiry = date.today() + timedelta(days=100)
    sections = _sections(f"Expiry Date: {expiry.isoformat()}\nNotice Period: 30 days")

    result = key_date_renewal_calendar_extraction_node({"sections": sections})

    findings = result["task_results"]["key_date_renewal_calendar_extraction"].findings
    notice_finding = next(f for f in findings if f.field == "notice_period")
    assert notice_finding.severity == "medium"


def test_only_inception_date_present_produces_no_crash_and_no_findings():
    sections = _sections("Inception Date: 2024-01-01")

    result = key_date_renewal_calendar_extraction_node({"sections": sections})

    assert result["task_results"]["key_date_renewal_calendar_extraction"].findings == []


def test_log_line_is_tagged_with_its_task_id(caplog):
    with caplog.at_level("INFO", logger="src.services.key_date_renewal_calendar_extraction"):
        key_date_renewal_calendar_extraction_node({"sections": _sections("Cedent: X")})

    messages = [record.message for record in caplog.records]
    assert any(message.startswith("[key_date_renewal_calendar_extraction] ") for message in messages)
