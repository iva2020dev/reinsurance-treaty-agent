"""Tests for src.services.burn_cost_check."""

from datetime import date

from src.models import ClaimsData, Severity, TaskResult, TreatyTerms
from src.services.burn_cost_check import burn_cost_check_node


def test_burn_cost_check_node_no_anomalies():
    treaty = TreatyTerms(
        cedent_name="X", attachment_point=1_000_000, limit=5_000_000, reinsurance_premium=250_000
    )
    claims = [ClaimsData(cedent_name="X", claim_amount=1_100_000, claim_date=date(2025, 1, 1))]

    result = burn_cost_check_node({"treaty": treaty, "claims": claims})

    report = result["report"]
    assert report.findings == []
    assert report.loss_ratio == 100_000 / 5_000_000


def test_burn_cost_check_node_flags_at_least_one_anomaly():
    treaty = TreatyTerms(
        cedent_name="X", attachment_point=1_000_000, limit=5_000_000, reinsurance_premium=250_000
    )

    result = burn_cost_check_node({"treaty": treaty, "claims": []})

    report = result["report"]
    assert len(report.findings) >= 1
    assert report.findings[0].severity == Severity.LOW
    assert "No historical claims data" in report.findings[0].description


def test_burn_cost_check_node_also_populates_task_results_alongside_report():
    treaty = TreatyTerms(
        cedent_name="X", attachment_point=1_000_000, limit=5_000_000, reinsurance_premium=250_000
    )
    claims = [ClaimsData(cedent_name="X", claim_amount=1_100_000, claim_date=date(2025, 1, 1))]

    result = burn_cost_check_node({"treaty": treaty, "claims": claims})

    assert set(result["task_results"]) == {"burn_cost_check"}
    task_result = result["task_results"]["burn_cost_check"]
    assert isinstance(task_result, TaskResult)
    assert task_result.status == "ran"
    assert task_result.findings == result["report"].findings
    assert task_result.cost == 0.0
    assert task_result.latency >= 0.0


def test_burn_cost_check_node_log_line_is_tagged_with_its_task_id(caplog):
    treaty = TreatyTerms(
        cedent_name="X", attachment_point=1_000_000, limit=5_000_000, reinsurance_premium=250_000
    )

    with caplog.at_level("INFO", logger="src.services.burn_cost_check"):
        burn_cost_check_node({"treaty": treaty, "claims": []})

    messages = [record.message for record in caplog.records]
    assert any(message.startswith("[burn_cost_check] ") for message in messages)
