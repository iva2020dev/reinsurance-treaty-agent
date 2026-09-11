"""End-to-end integration tests for the full parse -> workflow pipeline.

Unlike tests/test_workflow.py (which tests each node in isolation),
these drive the real graph through run_workflow()/run_workflow_from_pdf()
with no node mocking, covering both success and failure paths.
"""

import os

import pytest

from src.parser import ParserError, PageSection
from src.workflow import run_workflow, run_workflow_from_pdf

MINIMAL_TREATY_PATH = "data/sample_treaty.pdf"
RICH_TREATY_PATH = "data/sample_rich_treaty.pdf"
FUZZY_TREATY_PATH = "data/sample_rich_fuzzy_treaty.pdf"


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


def test_full_pipeline_explicit_b0_only_selection_matches_default_baseline():
    """End-to-end (S8): passing selected_task_ids={"burn_cost_check"}
    explicitly produces byte-identical results to the no-argument default
    call above -- the regression safety net named in this task's
    Acceptance, proving build_workflow_graph()'s default resolution
    (src/workflow.py) hasn't silently drifted from the real B0 selection.
    """
    default_result = run_workflow_from_pdf(MINIMAL_TREATY_PATH)
    explicit_result = run_workflow_from_pdf(MINIMAL_TREATY_PATH, selected_task_ids={"burn_cost_check"})

    assert explicit_result["report"] == default_result["report"]
    # Compare everything except latency, which is real measured wall-clock
    # time (time.perf_counter() in burn_cost_check_node) and so legitimately
    # differs slightly between two separate runs.
    for key in ("burn_cost_check",):
        explicit_result["task_results"][key] = explicit_result["task_results"][key].model_copy(
            update={"latency": 0.0}
        )
        default_result["task_results"][key] = default_result["task_results"][key].model_copy(update={"latency": 0.0})
    assert explicit_result["task_results"] == default_result["task_results"]


def test_full_pipeline_two_implemented_tasks_selected_together_both_run(monkeypatch):
    """End-to-end (S8): a genuine multi-task selection through the real
    run_workflow_from_pdf() entry point (not the lower-level run_workflow()
    already covered by multi-task-graph-fanout's own test) produces
    task_results entries for both tasks.
    """
    import src.workflow as workflow_module
    from src.domain_tasks import DomainTask
    from src.models import TaskResult

    def _second_task_node(state):
        return {"task_results": {"second_task": TaskResult(status="ran", findings=[], cost=0.002, latency=0.2)}}

    monkeypatch.setattr(workflow_module, "_second_task_node", _second_task_node, raising=False)
    monkeypatch.setattr(
        workflow_module,
        "DOMAIN_TASKS",
        [
            DomainTask(
                id="burn_cost_check",
                title="Burn-Cost Check",
                candidate_id="B0",
                implementation_status="implemented",
                shape="hybrid",
                workflow_node="burn_cost_check_node",
            ),
            DomainTask(
                id="second_task",
                title="Second Task",
                candidate_id="B1",
                implementation_status="implemented",
                shape="deterministic",
                workflow_node="_second_task_node",
            ),
        ],
    )

    result = run_workflow_from_pdf(MINIMAL_TREATY_PATH, selected_task_ids={"burn_cost_check", "second_task"})

    assert result["complete"] is True
    assert result["task_results"]["burn_cost_check"].status == "ran"
    assert result["task_results"]["second_task"].status == "ran"
    assert result["task_results"]["second_task"].cost == pytest.approx(0.002)


def test_full_pipeline_mixed_implemented_and_not_implemented_selection_skips_the_latter_gracefully():
    """End-to-end (S8): selecting a mix of an implemented task and a
    genuinely not-implemented one (from the real DOMAIN_TASKS registry, no
    monkeypatching needed) completes normally, with only the implemented
    task's entry appearing in task_results -- the not-implemented one is
    simply absent, which src.app.format_multi_task_status() and
    format_combined_results_summary() already turn into a clear per-task
    message for the UI (their own unit tests cover that formatting; this
    proves the underlying data they read is correct end-to-end).
    """
    from src.domain_tasks import DOMAIN_TASKS

    not_implemented_id = next(t.id for t in DOMAIN_TASKS if t.implementation_status == "not_implemented")

    result = run_workflow_from_pdf(
        MINIMAL_TREATY_PATH, selected_task_ids={"burn_cost_check", not_implemented_id}
    )

    assert result["complete"] is True
    assert result["task_results"]["burn_cost_check"].status == "ran"
    assert not_implemented_id not in result["task_results"]


@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="requires a real ANTHROPIC_API_KEY to call the live Anthropic API",
)
def test_full_pipeline_llm_extraction_fallback_real_api_call():
    """True end-to-end test of the hybrid flow: no mocking of the LLM client.

    The fuzzy fixture's prose defeats the regex extractor by design, so
    this exercises a real `llm_extraction_fallback` call against the
    live Anthropic API. Skipped automatically when no API key is
    configured (e.g. in CI), so it never fails a run that simply lacks
    the secret.
    """
    result = run_workflow_from_pdf(FUZZY_TREATY_PATH)

    assert result["extraction_method"] == "llm"
    assert result["llm_error"] is None
    assert result["complete"] is True

    report = result["report"]
    assert report is not None
    assert report.treaty.cedent_name == "Sentinel Mutual Assurance"
    assert report.loss_ratio == pytest.approx(0.70)
    assert len(report.findings) == 1
    assert report.findings[0].severity == "medium"
