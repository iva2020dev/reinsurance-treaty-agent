"""Tests for src.services.exclusion_completeness_checklist."""

from src.models import TreatyTerms
from src.services.exclusion_completeness_checklist import exclusion_completeness_checklist_node


def test_exclusion_completeness_checklist_node_flags_every_missing_clause():
    treaty = TreatyTerms(
        cedent_name="X",
        attachment_point=1_000_000,
        limit=5_000_000,
        reinsurance_premium=250_000,
        exclusions=["War and warlike operations", "Nuclear reaction or contamination"],
    )

    result = exclusion_completeness_checklist_node({"treaty": treaty})

    task_result = result["task_results"]["exclusion_completeness_checklist"]
    assert task_result.status == "ran"
    missing_clauses = {f.field for f in task_result.findings}  # sanity: field is always "exclusions"
    assert missing_clauses == {"exclusions"}
    descriptions = " ".join(f.description for f in task_result.findings)
    assert "cyber" in descriptions
    assert "pandemic" in descriptions
    assert "sanctions" in descriptions
    assert "tria" in descriptions
    assert "war" not in descriptions
    assert "nuclear" not in descriptions
    assert len(task_result.findings) == 4
    assert all(f.severity == "medium" for f in task_result.findings)


def test_exclusion_completeness_checklist_node_flags_only_the_one_missing_clause():
    treaty = TreatyTerms(
        cedent_name="X",
        attachment_point=1_000_000,
        limit=5_000_000,
        reinsurance_premium=250_000,
        exclusions=[
            "War, invasion, act of foreign enemy, hostilities or warlike operations",
            "Nuclear reaction, nuclear radiation, or radioactive contamination",
            "Terrorism, as defined under the Terrorism Risk Insurance Act (TRIA)",
            "Cyber-attack, data breach, or loss of electronic data",
            "Communicable disease, pandemic, or epidemic-related business interruption",
        ],
    )

    result = exclusion_completeness_checklist_node({"treaty": treaty})

    task_result = result["task_results"]["exclusion_completeness_checklist"]
    assert len(task_result.findings) == 1
    assert "sanctions" in task_result.findings[0].description


def test_exclusion_completeness_checklist_node_no_findings_when_all_clauses_present():
    treaty = TreatyTerms(
        cedent_name="X",
        attachment_point=1_000_000,
        limit=5_000_000,
        reinsurance_premium=250_000,
        exclusions=["war", "nuclear", "cyber", "pandemic", "sanctions", "terrorism"],
    )

    result = exclusion_completeness_checklist_node({"treaty": treaty})

    assert result["task_results"]["exclusion_completeness_checklist"].findings == []
