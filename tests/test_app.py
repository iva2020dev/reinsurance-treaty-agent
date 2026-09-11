"""Tests for src.app: report formatting helpers and the running Streamlit UI."""

import io
import json
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from streamlit.testing.v1 import AppTest

from src.app import (
    analyze_uploaded_pdf,
    extract_llm_usage_summary,
    format_combined_results_summary,
    format_extraction_status,
    format_log_header,
    format_multi_task_status,
    format_report_markdown,
    format_results_document,
    format_results_filename,
    format_task_section_markdown,
    highest_severity_label,
    render_report_bytes,
    render_report_pdf,
    results_subdirectory,
    save_analysis_result_to_file,
    save_logs_to_file,
    serialize_state_for_debug,
    slugify_treaty_name,
)
from src.domain_tasks import DOMAIN_TASKS
from src.models import AnomalyFinding, AnomalyReport, ClaimsData, Severity, TaskResult, TreatyTerms
from src.parser import ParserError

RICH_TREATY_PATH = "data/sample_rich_treaty.pdf"
MINIMAL_TREATY_PATH = "data/sample_treaty.pdf"
FUZZY_TREATY_PATH = "data/sample_rich_fuzzy_treaty.pdf"


def _click_button(at: AppTest, label: str) -> AppTest:
    """Click the first button with the given label and rerun."""
    button = next(b for b in at.button if b.label == label)
    return button.click().run()


def _upload_and_click_analyze(at: AppTest, filename: str, file_bytes: bytes) -> AppTest:
    """Upload a PDF via the uploader path and click Analyze, returning the rerun app."""
    at.file_uploader[0].set_value([(filename, file_bytes, "application/pdf")])
    at.run()
    return _click_button(at, "Analyze")


def _mock_llm_client(*, input_data: dict | None = None, error: Exception | None = None) -> MagicMock:
    """A mock anthropic.Anthropic() client for patching src.llm_client.anthropic.Anthropic."""
    mock_client = MagicMock()
    if error is not None:
        mock_client.messages.create.side_effect = error
        return mock_client
    tool_use_block = SimpleNamespace(type="tool_use", input=input_data)
    mock_client.messages.create.return_value = SimpleNamespace(
        content=[tool_use_block],
        usage=SimpleNamespace(input_tokens=500, output_tokens=60),
    )
    return mock_client


FUZZY_TREATY_LLM_RESPONSE = {
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
}


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


def test_app_analyze_button_disabled_until_treaty_selected():
    at = AppTest.from_file("../src/app.py")
    at.run()

    review_button = next(b for b in at.button if b.label == "Review treaty")
    analyze_button = next(b for b in at.button if b.label == "Analyze")
    assert review_button.disabled
    assert analyze_button.disabled

    with open(MINIMAL_TREATY_PATH, "rb") as f:
        at.file_uploader[0].set_value([("sample_treaty.pdf", f.read(), "application/pdf")])
    at.run()

    review_button = next(b for b in at.button if b.label == "Review treaty")
    analyze_button = next(b for b in at.button if b.label == "Analyze")
    assert not review_button.disabled
    assert not analyze_button.disabled


def test_app_shows_one_checkbox_per_domain_task_only_implemented_enabled():
    at = AppTest.from_file("../src/app.py")
    at.run()

    assert len(at.checkbox) == len(DOMAIN_TASKS)
    implemented_titles = {t.title for t in DOMAIN_TASKS if t.implementation_status == "implemented"}
    for checkbox in at.checkbox:
        if checkbox.label in implemented_titles:
            assert not checkbox.disabled
        else:
            assert checkbox.disabled
            assert not checkbox.value


def test_app_review_treaty_button_renders_before_domain_tasks_checklist():
    at = AppTest.from_file("../src/app.py")
    at.run()

    main_children = list(at.main.children.values())
    review_index = next(i for i, block in enumerate(main_children) if getattr(block, "label", None) == "Review treaty")
    subheader_index = next(
        i
        for i, block in enumerate(main_children)
        if getattr(block, "value", None) == "Domain tasks to run"
    )
    analyze_index = next(i for i, block in enumerate(main_children) if getattr(block, "label", None) == "Analyze")

    assert review_index < subheader_index < analyze_index


def test_app_total_estimated_cost_value_aligns_under_the_per_task_value_column():
    """The total row's value ("$X") sits in a column with the same weight
    (fraction of row width) as each task row's own value column, so the
    dollar figures line up vertically even though "Total estimated cost:"
    is longer text than "Estimated cost:" (label column widened instead).
    """
    at = AppTest.from_file("../src/app.py")
    at.run()

    main_children = list(at.main.children.values())
    total_cost_row = next(
        block
        for block in reversed(main_children)
        if getattr(block, "type", None) == "flex_container"
        and any(
            getattr(caption, "value", "") == "**Total estimated cost:**"
            for col in block.children.values()
            for caption in getattr(col, "children", {}).values()
        )
    )
    total_columns = list(total_cost_row.children.values())
    assert len(total_columns) == 2
    assert list(total_columns[0].children.values())[0].value == "**Total estimated cost:**"
    assert list(total_columns[1].children.values())[0].value == "**$0.0010**"

    task_row = next(
        block
        for block in main_children
        if getattr(block, "type", None) == "flex_container"
        and any(
            getattr(cb, "label", None) == "Burn-Cost Check"
            for col in block.children.values()
            for cb in getattr(col, "children", {}).values()
        )
    )
    task_columns = list(task_row.children.values())
    assert len(task_columns) == 4
    # Total's value column weight matches the task row's own value column.
    assert total_columns[1].weight == pytest.approx(task_columns[3].weight)


def test_app_total_estimated_cost_always_visible_even_with_nothing_selected():
    at = AppTest.from_file("../src/app.py")
    at.run()

    # Burn-Cost Check defaults to checked, so the total starts nonzero --
    # confirms the caption is present even before any user interaction.
    captions = [c.value for c in at.caption]
    assert "**Total estimated cost:**" in captions
    assert "**$0.0010**" in captions

    burn_cost_checkbox = next(c for c in at.checkbox if c.label == "Burn-Cost Check")
    at = burn_cost_checkbox.uncheck().run()

    # With nothing selected, the line stays visible rather than
    # disappearing -- only its value drops to $0.0000.
    captions = [c.value for c in at.caption]
    assert "**Total estimated cost:**" in captions
    assert "**$0.0000**" in captions


def test_app_shows_each_domain_task_shape_in_its_own_column():
    at = AppTest.from_file("../src/app.py")
    at.run()

    captions = [c.value for c in at.caption]
    for task in DOMAIN_TASKS:
        assert task.shape in captions


def test_app_domain_tasks_checklist_has_a_labeled_header_row():
    at = AppTest.from_file("../src/app.py")
    at.run()

    captions = [c.value for c in at.caption]
    assert "**Task**" in captions
    assert "**Type**" in captions
    assert "**Cost (estimated)**" in captions
    # Header appears before any task's own captions (i.e. right under the
    # "Domain tasks to run" subheader, not interleaved into the checklist).
    header_index = captions.index("**Task**")
    first_shape_index = captions.index(DOMAIN_TASKS[0].shape)
    assert header_index < first_shape_index


def test_app_burn_cost_check_defaults_checked_and_shows_cost_estimate():
    at = AppTest.from_file("../src/app.py")
    at.run()

    burn_cost_checkbox = next(c for c in at.checkbox if c.label == "Burn-Cost Check")
    assert burn_cost_checkbox.value is True
    # B0 is hybrid-shaped, so estimate_task_cost() includes the fixed
    # output-token estimate even with no document selected (page_count=0).
    # Label and value are separate captions (own columns), so check both
    # are present rather than one combined string.
    captions = [c.value for c in at.caption]
    assert "Estimated cost:" in captions
    assert "$0.0010" in captions
    assert "**Total estimated cost:**" in captions
    assert "**$0.0010**" in captions


def test_app_analyze_disabled_when_no_task_is_selected():
    at = AppTest.from_file("../src/app.py")
    at.run()

    with open(MINIMAL_TREATY_PATH, "rb") as f:
        at.file_uploader[0].set_value([("sample_treaty.pdf", f.read(), "application/pdf")])
    at.run()

    analyze_button = next(b for b in at.button if b.label == "Analyze")
    assert not analyze_button.disabled

    burn_cost_checkbox = next(c for c in at.checkbox if c.label == "Burn-Cost Check")
    at = burn_cost_checkbox.uncheck().run()

    analyze_button = next(b for b in at.button if b.label == "Analyze")
    assert analyze_button.disabled


def test_app_cost_estimate_increases_with_a_larger_selected_document():
    at = AppTest.from_file("../src/app.py")
    at.run()

    with open(MINIMAL_TREATY_PATH, "rb") as f:
        at.file_uploader[0].set_value([("sample_treaty.pdf", f.read(), "application/pdf")])
    at = at.run()
    small_captions = [c.value for c in at.caption]

    with open(RICH_TREATY_PATH, "rb") as f:
        at.file_uploader[0].set_value([("sample_rich_treaty.pdf", f.read(), "application/pdf")])
    at = at.run()
    large_captions = [c.value for c in at.caption]

    def _total_cost(captions: list[str]) -> float:
        # The total's value is its own caption, immediately after the
        # "**Total estimated cost:**" label caption (separate columns).
        label_index = captions.index("**Total estimated cost:**")
        return float(captions[label_index + 1].strip("$*"))

    assert _total_cost(large_captions) > _total_cost(small_captions)


def test_app_upload_and_render_success():
    at = AppTest.from_file("../src/app.py")
    at.run()

    with open(MINIMAL_TREATY_PATH, "rb") as f:
        at = _upload_and_click_analyze(at, "sample_treaty.pdf", f.read())

    assert not at.exception
    markdown_text = "\n".join(m.value for m in at.markdown)
    assert "Acme Insurance Co." in markdown_text


def test_app_results_ui_shows_one_section_per_task_and_combined_header_for_two_implemented_tasks(monkeypatch):
    """Selecting two genuinely distinct implemented tasks together renders one
    expandable section per task, plus a combined header aggregating both.

    Uses the same monkeypatch technique as
    test_build_workflow_graph_fans_out_to_multiple_implemented_tasks
    (tests/test_workflow.py) to make a second task real-implemented for this
    test, since src.domain_tasks.DOMAIN_TASKS has only one implemented entry
    today. Patches two separate bindings: src.workflow's own (already-cached,
    used at call time by build_workflow_graph regardless of how app.py's
    script is re-run) and src.domain_tasks' own module attribute (since
    AppTest re-executes src/app.py fresh on every .run(), its
    `from src.domain_tasks import DOMAIN_TASKS` re-resolves against
    sys.modules['src.domain_tasks'] each time, not against any binding
    a test file's own `import src.app` would see).
    """
    import src.workflow as workflow_module
    from src.domain_tasks import DomainTask
    from src.models import AnomalyFinding, Severity, TaskResult

    def _second_task_node(state):
        return {
            "task_results": {
                "second_task": TaskResult(
                    status="ran",
                    findings=[AnomalyFinding(field="x", description="second task finding", severity=Severity.LOW)],
                    cost=0.005,
                    latency=0.3,
                )
            }
        }

    monkeypatch.setattr(workflow_module, "_second_task_node", _second_task_node, raising=False)
    two_implemented = [
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
            candidate_id="SYNTHETIC",
            implementation_status="implemented",
            shape="deterministic",
            workflow_node="_second_task_node",
        ),
    ]
    monkeypatch.setattr(workflow_module, "DOMAIN_TASKS", two_implemented)
    monkeypatch.setattr("src.domain_tasks.DOMAIN_TASKS", two_implemented)

    at = AppTest.from_file("../src/app.py")
    at.run()

    with open(MINIMAL_TREATY_PATH, "rb") as f:
        at.file_uploader[0].set_value([("sample_treaty.pdf", f.read(), "application/pdf")])
    at.run()
    # "Second Task" isn't in DEFAULT_SELECTED_TASK_IDS, so it defaults
    # unchecked -- check it explicitly to select both tasks.
    second_task_checkbox = next(c for c in at.checkbox if c.label == "Second Task")
    at = second_task_checkbox.check().run()
    at = _click_button(at, "Analyze")

    assert not at.exception
    labels = [e.label for e in at.expander]
    assert "Burn-Cost Check" in labels
    assert "Second Task" in labels

    markdown_text = "\n".join(m.value for m in at.markdown)
    assert "second task finding" in markdown_text
    # Combined header: 0 burn_cost_check findings + 1 second_task finding.
    assert "1 finding(s)" in markdown_text
    assert "$0.0050" in markdown_text
    assert "Skipped" not in markdown_text


def test_app_cost_estimate_shown_pre_run_and_actual_cost_round_trips_to_debug_json(monkeypatch):
    """End-to-end (S8): a pre-run cost estimate is shown for a selected
    llm/hybrid-shaped task, and after running, that task's real actual cost
    (from its own TaskResult, not the estimate) round-trips correctly into
    the debug panel's serialized JSON -- proving estimate_task_cost() (S4)
    and TaskResult/serialize_state_for_debug() (S3/S8) are wired together
    correctly end-to-end, not just unit-tested in isolation.

    Same two-task monkeypatch technique as the results-UI test above.
    """
    import json as json_module

    import src.workflow as workflow_module
    from src.domain_tasks import DomainTask
    from src.models import TaskResult

    def _second_task_node(state):
        return {"task_results": {"second_task": TaskResult(status="ran", findings=[], cost=0.0042, latency=0.4)}}

    monkeypatch.setattr(workflow_module, "_second_task_node", _second_task_node, raising=False)
    two_implemented = [
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
            candidate_id="SYNTHETIC",
            implementation_status="implemented",
            shape="llm",
            workflow_node="_second_task_node",
        ),
    ]
    monkeypatch.setattr(workflow_module, "DOMAIN_TASKS", two_implemented)
    monkeypatch.setattr("src.domain_tasks.DOMAIN_TASKS", two_implemented)

    at = AppTest.from_file("../src/app.py")
    at.run()

    with open(MINIMAL_TREATY_PATH, "rb") as f:
        at.file_uploader[0].set_value([("sample_treaty.pdf", f.read(), "application/pdf")])
    at = at.run()
    # "Second Task" isn't in DEFAULT_SELECTED_TASK_IDS, so it defaults
    # unchecked -- check it explicitly to select it alongside Burn-Cost Check.
    second_task_checkbox = next(c for c in at.checkbox if c.label == "Second Task")
    at = second_task_checkbox.check().run()

    # Pre-run: the now-checked llm-shaped task shows a nonzero estimate.
    pre_run_captions = "\n".join(c.value for c in at.caption)
    assert "Estimated cost" in pre_run_captions

    at = _click_button(at, "Analyze")
    assert not at.exception

    # Post-run: the debug panel's serialized state includes task_results
    # with second_task's real actual cost -- $0.0042, not the pre-run
    # estimate (which is a page-count-based heuristic, not this figure).
    debug_dict = json_module.loads(at.json[0].value)
    assert debug_dict["task_results"]["second_task"]["cost"] == pytest.approx(0.0042)
    assert debug_dict["task_results"]["second_task"]["status"] == "ran"
    assert debug_dict["task_results"]["burn_cost_check"]["status"] == "ran"


def test_app_results_ui_shows_not_implemented_message_for_a_selected_but_unimplemented_task():
    """A task selected alongside an implemented one, but never populated in
    task_results because it isn't implemented, gets its own section with a
    clear "not implemented" message rather than being silently dropped.

    Today's checkbox UI disables any not-implemented task's checkbox
    outright, so this selection can't happen by clicking through the real
    UI -- injected directly into session_state instead, the same situation
    format_multi_task_status's own "not implemented" branch already covers
    generically for the debug panel.
    """
    not_implemented_id = next(t.id for t in DOMAIN_TASKS if t.implementation_status == "not_implemented")
    not_implemented_title = next(t.title for t in DOMAIN_TASKS if t.id == not_implemented_id)

    at = AppTest.from_file("../src/app.py")
    at.run()

    with open(MINIMAL_TREATY_PATH, "rb") as f:
        at = _upload_and_click_analyze(at, "sample_treaty.pdf", f.read())

    assert not at.exception
    at.session_state["workflow_run"]["selected_task_ids"] = {"burn_cost_check", not_implemented_id}
    at.run()

    assert not at.exception
    labels = [e.label for e in at.expander]
    assert "Burn-Cost Check" in labels
    assert not_implemented_title in labels

    markdown_text = "\n".join(m.value for m in at.markdown)
    assert "Not implemented yet." in markdown_text
    assert f"- **{not_implemented_title}**: not implemented yet" in markdown_text


def test_app_close_button_clears_results():
    at = AppTest.from_file("../src/app.py")
    at.run()

    with open(MINIMAL_TREATY_PATH, "rb") as f:
        at = _upload_and_click_analyze(at, "sample_treaty.pdf", f.read())

    assert not at.exception
    assert any(b.label == "Close" for b in at.button)
    markdown_text = "\n".join(m.value for m in at.markdown)
    assert "Acme Insurance Co." in markdown_text

    at = _click_button(at, "Close")

    assert not at.exception
    assert not any(b.label == "Close" for b in at.button)
    markdown_text = "\n".join(m.value for m in at.markdown)
    assert "Acme Insurance Co." not in markdown_text


def test_app_re_analyzing_replaces_previous_results():
    at = AppTest.from_file("../src/app.py")
    at.run()

    with open(MINIMAL_TREATY_PATH, "rb") as f:
        at = _upload_and_click_analyze(at, "sample_treaty.pdf", f.read())

    assert not at.exception
    markdown_text = "\n".join(m.value for m in at.markdown)
    assert "Acme Insurance Co." in markdown_text

    with open(RICH_TREATY_PATH, "rb") as f:
        at = _upload_and_click_analyze(at, "sample_rich_treaty.pdf", f.read())

    assert not at.exception
    markdown_text = "\n".join(m.value for m in at.markdown)
    assert "Meridian Insurance Group, Inc." in markdown_text
    assert "Acme Insurance Co." not in markdown_text
    # Exactly one results container's worth of content — not stacked/duplicated.
    assert sum("Treaty:" in m.value for m in at.markdown) == 1


def test_app_results_auto_clear_when_a_new_file_is_uploaded_without_re_analyzing():
    at = AppTest.from_file("../src/app.py")
    at.run()

    with open(MINIMAL_TREATY_PATH, "rb") as f:
        at = _upload_and_click_analyze(at, "sample_treaty.pdf", f.read())

    assert not at.exception
    assert any(b.label == "Close" for b in at.button)
    markdown_text = "\n".join(m.value for m in at.markdown)
    assert "Acme Insurance Co." in markdown_text

    with open(RICH_TREATY_PATH, "rb") as f:
        at.file_uploader[0].set_value([("sample_rich_treaty.pdf", f.read(), "application/pdf")])
    at.run()

    assert not at.exception
    assert not any(b.label == "Close" for b in at.button)
    markdown_text = "\n".join(m.value for m in at.markdown)
    assert "Acme Insurance Co." not in markdown_text


def test_app_results_auto_clear_when_switching_to_sample_selector():
    at = AppTest.from_file("../src/app.py")
    at.run()

    with open(MINIMAL_TREATY_PATH, "rb") as f:
        at = _upload_and_click_analyze(at, "sample_treaty.pdf", f.read())

    assert not at.exception
    assert any(b.label == "Close" for b in at.button)

    at.radio[0].set_value("Choose a reinsurance treaty").run()

    assert not at.exception
    assert not any(b.label == "Close" for b in at.button)
    markdown_text = "\n".join(m.value for m in at.markdown)
    assert "Acme Insurance Co." not in markdown_text


def test_app_upload_malformed_pdf_shows_error_not_crash():
    at = AppTest.from_file("../src/app.py")
    at.run()

    at = _upload_and_click_analyze(at, "bad.pdf", b"not a pdf at all")

    assert not at.exception
    assert len(at.error) == 1
    assert "Could not read this PDF" in at.error[0].value


def test_app_sample_selector_lists_all_golden_samples_and_runs_analysis():
    at = AppTest.from_file("../src/app.py")
    at.run()

    at.radio[0].set_value("Choose a reinsurance treaty").run()
    sample_select = at.selectbox[0]
    labels = sample_select.options
    assert len(labels) == 6  # placeholder + 5 golden samples

    acme_label = next(label for label in labels if label.startswith("Acme Insurance Co."))
    sample_select.set_value(acme_label).run()

    at = _click_button(at, "Analyze")

    assert not at.exception
    markdown_text = "\n".join(m.value for m in at.markdown)
    assert "Acme Insurance Co." in markdown_text


def test_app_review_treaty_shows_selected_document_text_in_modal():
    at = AppTest.from_file("../src/app.py")
    at.run()

    with open(MINIMAL_TREATY_PATH, "rb") as f:
        at.file_uploader[0].set_value([("sample_treaty.pdf", f.read(), "application/pdf")])
    at.run()

    at = _click_button(at, "Review treaty")

    assert not at.exception
    markdown_text = "\n".join(m.value for m in at.markdown)
    assert "Page 1" in markdown_text
    text_values = "\n".join(t.value for t in at.text)
    assert "Acme Insurance Co." in text_values


def test_app_review_treaty_shows_error_for_malformed_pdf():
    at = AppTest.from_file("../src/app.py")
    at.run()

    at.file_uploader[0].set_value([("bad.pdf", b"not a pdf at all", "application/pdf")])
    at.run()

    at = _click_button(at, "Review treaty")

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


def test_serialize_state_for_debug_includes_task_results():
    state = {
        "sections": [],
        "missing_fields": [],
        "claims": [],
        "complete": True,
        "task_results": {
            "burn_cost_check": TaskResult(
                status="ran",
                findings=[AnomalyFinding(field="x", description="a", severity=Severity.HIGH)],
                cost=0.001,
                latency=0.05,
            )
        },
    }

    debug_dict = serialize_state_for_debug(state)
    json.dumps(debug_dict)  # must not raise

    assert debug_dict["task_results"]["burn_cost_check"]["status"] == "ran"
    assert debug_dict["task_results"]["burn_cost_check"]["cost"] == pytest.approx(0.001)
    assert len(debug_dict["task_results"]["burn_cost_check"]["findings"]) == 1


def test_serialize_state_for_debug_defaults_task_results_to_empty_dict_when_absent():
    debug_dict = serialize_state_for_debug({"sections": [], "missing_fields": [], "claims": [], "complete": False})

    assert debug_dict["task_results"] == {}


def test_app_debug_panel_shows_log_lines_and_state_on_success():
    at = AppTest.from_file("../src/app.py")
    at.run()

    with open(MINIMAL_TREATY_PATH, "rb") as f:
        at = _upload_and_click_analyze(at, "sample_treaty.pdf", f.read())

    assert not at.exception
    # 2 expanders: one per-task results section ("Burn-Cost Check", from
    # multi-task-results-ui) plus the debug panel itself.
    assert len(at.expander) == 2
    assert [e.label for e in at.expander] == ["Burn-Cost Check", "Analysis Workflow execution"]
    log_text = "\n".join(c.value for c in at.code)
    assert "src.workflow" in log_text
    assert "Extractor" in log_text
    assert "Burn-Cost Check" in log_text

    debug_state = json.loads(at.json[0].value)
    assert debug_state["treaty"]["cedent_name"] == "Acme Insurance Co."
    assert debug_state["complete"] is True

    markdown_text = "\n".join(m.value for m in at.markdown)
    assert "- **burn_cost_check**: ran (0 finding(s)" in markdown_text


def test_app_debug_panel_shows_log_lines_on_parser_failure():
    at = AppTest.from_file("../src/app.py")
    at.run()

    at = _upload_and_click_analyze(at, "bad.pdf", b"not a pdf at all")

    assert not at.exception
    log_text = "\n".join(c.value for c in at.code)
    assert log_text == ""  # ParserError raised before any node logs anything
    assert len(at.json) == 0  # no state was produced to show


def test_format_extraction_status_for_each_extraction_method():
    assert "no LLM call was needed" in format_extraction_status({"extraction_method": "regex"})
    assert "LLM Extraction Fallback" in format_extraction_status({"extraction_method": "llm"})
    assert "also could not recover them: boom" in format_extraction_status(
        {"extraction_method": "none", "llm_error": "boom"}
    )
    assert "was not run" in format_extraction_status({"extraction_method": "none"})


def test_format_multi_task_status_no_tasks_selected():
    assert format_multi_task_status(set(), {}) == "No domain tasks were selected."


def test_format_multi_task_status_ran_task_shows_findings_cost_and_latency():
    task_results = {
        "burn_cost_check": TaskResult(
            status="ran",
            findings=[AnomalyFinding(field="loss_ratio", description="x", severity=Severity.HIGH)],
            cost=0.001,
            latency=0.05,
        )
    }

    status = format_multi_task_status({"burn_cost_check"}, task_results)

    assert "burn_cost_check" in status
    assert "ran" in status
    assert "1 finding(s)" in status
    assert "$0.0010" in status
    assert "0.05s" in status


def test_format_multi_task_status_not_implemented_task_shows_skipped():
    not_implemented_id = next(
        t.id for t in DOMAIN_TASKS if t.implementation_status == "not_implemented"
    )

    status = format_multi_task_status({not_implemented_id}, {})

    assert f"- **{not_implemented_id}**: skipped (not implemented)" in status


def test_format_multi_task_status_implemented_but_missing_result_shows_incomplete():
    status = format_multi_task_status({"burn_cost_check"}, {})

    assert "- **burn_cost_check**: did not run (extraction incomplete)" in status


def test_format_multi_task_status_failed_task_shows_failed_status():
    task_results = {"burn_cost_check": TaskResult(status="failed")}

    status = format_multi_task_status({"burn_cost_check"}, task_results)

    assert "- **burn_cost_check**: failed" in status


def test_format_task_section_markdown_burn_cost_check_reuses_report_rendering():
    report = AnomalyReport(
        treaty=TreatyTerms(
            cedent_name="Acme Insurance Co.",
            attachment_point=1_000_000,
            limit=5_000_000,
            reinsurance_premium=200_000,
        ),
        claims=[],
        loss_ratio=0.3,
        findings=[],
    )

    section = format_task_section_markdown("burn_cost_check", None, report)

    assert section == format_report_markdown(report)


def test_format_task_section_markdown_ran_task_shows_its_own_findings_cost_latency():
    task_result = TaskResult(
        status="ran",
        findings=[AnomalyFinding(field="x", description="something odd", severity=Severity.MEDIUM)],
        cost=0.0025,
        latency=1.5,
    )

    section = format_task_section_markdown("second_task", task_result, None)

    assert "$0.0025" in section
    assert "1.50s" in section
    assert "Findings (1)" in section
    assert "something odd" in section


def test_format_task_section_markdown_ran_task_with_no_findings():
    task_result = TaskResult(status="ran", findings=[], cost=0.0, latency=0.1)

    section = format_task_section_markdown("second_task", task_result, None)

    assert "No anomalies found." in section


def test_format_task_section_markdown_failed_task_shows_status():
    section = format_task_section_markdown("second_task", TaskResult(status="failed"), None)

    assert section == "_failed._"


def test_format_task_section_markdown_not_implemented_task_shows_clear_message():
    not_implemented_id = next(t.id for t in DOMAIN_TASKS if t.implementation_status == "not_implemented")

    section = format_task_section_markdown(not_implemented_id, None, None)

    assert section == "_Not implemented yet._"


def test_format_task_section_markdown_implemented_task_missing_result_shows_incomplete():
    # "burn_cost_check" is a real implemented registry id, but with no
    # task_result and no report -- this is the "extraction never reached
    # it" case (distinct from a genuinely not-implemented task).
    section = format_task_section_markdown("burn_cost_check", None, None)

    assert section == "_Did not run (extraction incomplete)._"


def test_format_combined_results_summary_aggregates_findings_and_cost_across_ran_tasks():
    task_results = {
        "burn_cost_check": TaskResult(
            status="ran",
            findings=[AnomalyFinding(field="x", description="a", severity=Severity.HIGH)],
            cost=0.001,
            latency=0.1,
        ),
        "second_task": TaskResult(
            status="ran",
            findings=[
                AnomalyFinding(field="y", description="b", severity=Severity.LOW),
                AnomalyFinding(field="z", description="c", severity=Severity.LOW),
            ],
            cost=0.002,
            latency=0.2,
        ),
    }

    summary = format_combined_results_summary({"burn_cost_check", "second_task"}, task_results)

    assert "3 finding(s)" in summary
    assert "$0.0030" in summary
    assert "Skipped" not in summary


def test_format_combined_results_summary_lists_skipped_tasks_with_reasons(monkeypatch):
    not_implemented_id = next(t.id for t in DOMAIN_TASKS if t.implementation_status == "not_implemented")
    not_implemented_title = next(t.title for t in DOMAIN_TASKS if t.id == not_implemented_id)
    # "second_task" is a real *implemented* id per this patched registry, but
    # has no entry in task_results -- exercises the "did not run (extraction
    # incomplete)" branch specifically, distinct from "not implemented yet".
    from src.domain_tasks import DomainTask

    patched_tasks = list(DOMAIN_TASKS) + [
        DomainTask(
            id="second_task",
            title="Second Task",
            candidate_id="B1",
            implementation_status="implemented",
            shape="deterministic",
            workflow_node="_second_task_node",
        )
    ]
    monkeypatch.setattr("src.app.DOMAIN_TASKS", patched_tasks)
    task_results = {
        "burn_cost_check": TaskResult(status="ran", findings=[], cost=0.0, latency=0.1),
    }

    summary = format_combined_results_summary({"burn_cost_check", not_implemented_id, "second_task"}, task_results)

    assert f"- **{not_implemented_title}**: not implemented yet" in summary
    assert "- **Second Task**: did not run (extraction incomplete)" in summary


def test_app_shows_llm_extraction_fallback_note_and_state_on_success(monkeypatch):
    mock_client = _mock_llm_client(input_data=FUZZY_TREATY_LLM_RESPONSE)
    monkeypatch.setattr("src.llm_client.anthropic.Anthropic", lambda **kwargs: mock_client)

    at = AppTest.from_file("../src/app.py")
    at.run()
    with open(FUZZY_TREATY_PATH, "rb") as f:
        at = _upload_and_click_analyze(at, "sample_rich_fuzzy_treaty.pdf", f.read())

    assert not at.exception
    assert any("LLM Extraction Fallback" in w.value for w in at.warning)
    markdown_text = "\n".join(m.value for m in at.markdown)
    assert "Sentinel Mutual Assurance" in markdown_text
    assert "0.70" in markdown_text

    debug_state = json.loads(at.json[0].value)
    assert debug_state["extraction_method"] == "llm"
    assert debug_state["llm_error"] is None
    assert debug_state["ungrounded_fields"] == []
    assert not any("could not be verified" in w.value for w in at.warning)
    assert any("LLM Extraction Fallback" in c.value for c in at.caption)


def test_app_shows_ungrounded_field_warning_when_grounding_check_fails(monkeypatch):
    response = dict(FUZZY_TREATY_LLM_RESPONSE, cedent_name="A Completely Different Company Name")
    mock_client = _mock_llm_client(input_data=response)
    monkeypatch.setattr("src.llm_client.anthropic.Anthropic", lambda **kwargs: mock_client)

    at = AppTest.from_file("../src/app.py")
    at.run()
    with open(FUZZY_TREATY_PATH, "rb") as f:
        at = _upload_and_click_analyze(at, "sample_rich_fuzzy_treaty.pdf", f.read())

    assert not at.exception
    assert any("could not be verified" in w.value and "cedent_name" in w.value for w in at.warning)

    debug_state = json.loads(at.json[0].value)
    assert debug_state["ungrounded_fields"] == ["cedent_name"]


def test_app_shows_llm_error_when_both_extraction_paths_fail(monkeypatch):
    mock_client = _mock_llm_client(error=RuntimeError("simulated network failure"))
    monkeypatch.setattr("src.llm_client.anthropic.Anthropic", lambda **kwargs: mock_client)

    at = AppTest.from_file("../src/app.py")
    at.run()
    with open(FUZZY_TREATY_PATH, "rb") as f:
        at = _upload_and_click_analyze(at, "sample_rich_fuzzy_treaty.pdf", f.read())

    assert not at.exception
    assert len(at.error) == 1
    assert "LLM Extraction Fallback also failed" in at.error[0].value
    assert "simulated network failure" in at.error[0].value

    debug_state = json.loads(at.json[0].value)
    assert debug_state["extraction_method"] == "none"
    assert "simulated network failure" in debug_state["llm_error"]


def test_slugify_treaty_name_strips_punctuation_and_lowercases():
    assert slugify_treaty_name("Acme Insurance Co.") == "acme_insurance_co"


def test_slugify_treaty_name_truncates_to_max_length():
    long_name = "A" * 100
    assert len(slugify_treaty_name(long_name, max_length=10)) == 10


def test_slugify_treaty_name_falls_back_when_nothing_alphanumeric():
    assert slugify_treaty_name("!!!") == "treaty"


def test_highest_severity_label_no_findings_is_clean():
    assert highest_severity_label([]) == "clean"


def test_highest_severity_label_picks_the_highest_of_several():
    findings = [
        AnomalyFinding(field="a", description="a", severity=Severity.LOW),
        AnomalyFinding(field="b", description="b", severity=Severity.HIGH),
        AnomalyFinding(field="c", description="c", severity=Severity.MEDIUM),
    ]
    assert highest_severity_label(findings) == "high"


def test_format_results_filename_matches_naming_rule():
    report = _sample_report()  # cedent "Acme Insurance Co.", one HIGH finding
    filename = format_results_filename(report, "md", when=datetime(2026, 9, 9, 14, 5, 30))

    assert filename == "20260909_140530_high.md"


def test_format_results_filename_uses_given_extension():
    report = _sample_report()
    filename = format_results_filename(report, "pdf", when=datetime(2026, 9, 9, 14, 5, 30))

    assert filename == "20260909_140530_high.pdf"


def test_results_subdirectory_is_per_treaty():
    report = _sample_report()  # cedent "Acme Insurance Co."

    assert results_subdirectory(report, Path("results")) == Path("results/acme_insurance_co")


def test_extract_llm_usage_summary_finds_token_counts():
    log_lines = [
        "2026-09-09 10:00:00 INFO src.workflow: some other line",
        "2026-09-09 10:00:01 INFO src.llm_client: LLM Extraction Fallback: extracted treaty terms for "
        "cedent 'Acme' in 1.23s (model=claude-haiku-4-5-20251001, input_tokens=500, output_tokens=60)",
    ]

    assert extract_llm_usage_summary(log_lines) == "input tokens: 500, output tokens: 60"


def test_extract_llm_usage_summary_none_when_llm_not_invoked():
    log_lines = ["2026-09-09 10:00:00 INFO src.workflow: Extractor (Regex): extracted treaty terms"]

    assert extract_llm_usage_summary(log_lines) is None
    assert extract_llm_usage_summary(None) is None


def test_format_results_document_includes_timestamp_and_report():
    report = _sample_report()
    doc = format_results_document(report, when=datetime(2026, 9, 9, 14, 5, 30))

    assert doc.startswith("## Analysis Results")
    assert "Generated: 2026-09-09 14:05:30" in doc
    assert "Acme Insurance Co." in doc
    assert "LLM usage" not in doc


def test_format_results_document_includes_llm_usage_when_present():
    report = _sample_report()
    log_lines = ["... input_tokens=500, output_tokens=60 ..."]
    doc = format_results_document(report, log_lines=log_lines, when=datetime(2026, 9, 9, 14, 5, 30))

    assert "LLM usage: input tokens: 500, output tokens: 60" in doc


def test_render_report_pdf_contains_the_reports_text():
    from pypdf import PdfReader

    report = _sample_report()
    pdf_bytes = render_report_pdf(report, when=datetime(2026, 9, 9, 14, 5, 30))

    assert pdf_bytes.startswith(b"%PDF")
    text = PdfReader(io.BytesIO(pdf_bytes)).pages[0].extract_text()
    assert "Analysis Results" in text
    assert "Generated: 2026-09-09 14:05:30" in text
    assert "Acme Insurance Co." in text
    assert "HIGH" in text
    assert "Losses exceeded the limit." in text


def test_render_report_bytes_dispatches_by_extension():
    report = _sample_report()
    when = datetime(2026, 9, 9, 14, 5, 30)

    assert render_report_bytes(report, "md", when=when) == format_results_document(report, when=when).encode(
        "utf-8"
    )
    assert render_report_bytes(report, "pdf", when=when).startswith(b"%PDF")


def test_save_analysis_result_to_file_writes_markdown(tmp_path):
    report = _sample_report()

    saved_path = save_analysis_result_to_file(report, "md", directory=tmp_path, when=datetime(2026, 9, 9, 14, 5, 30))

    assert saved_path == tmp_path / "acme_insurance_co" / "20260909_140530_high.md"
    assert saved_path.read_text() == format_results_document(report, when=datetime(2026, 9, 9, 14, 5, 30))


def test_save_analysis_result_to_file_writes_pdf(tmp_path):
    report = _sample_report()

    saved_path = save_analysis_result_to_file(
        report, "pdf", directory=tmp_path, when=datetime(2026, 9, 9, 14, 5, 30)
    )

    assert saved_path == tmp_path / "acme_insurance_co" / "20260909_140530_high.pdf"
    assert saved_path.read_bytes().startswith(b"%PDF")


def test_save_analysis_result_to_file_creates_parent_directory(tmp_path):
    report = _sample_report()
    directory = tmp_path / "results"

    saved_path = save_analysis_result_to_file(
        report, "md", directory=directory, when=datetime(2026, 9, 9, 14, 5, 30)
    )

    assert saved_path.exists()


def test_app_save_analysis_results_button_writes_markdown_by_default(tmp_path, monkeypatch):
    pdf_bytes = Path(MINIMAL_TREATY_PATH).read_bytes()
    monkeypatch.chdir(tmp_path)

    at = AppTest.from_file("../src/app.py")
    at.run()
    at = _upload_and_click_analyze(at, "sample_treaty.pdf", pdf_bytes)

    at = _click_button(at, "Save analysis results")

    assert not at.exception
    assert any("Saved analysis results to" in s.value for s in at.success)
    saved_files = list((tmp_path / "results" / "acme_insurance_co").glob("*.md"))
    assert len(saved_files) == 1


def test_app_save_analysis_results_button_writes_pdf_when_selected(tmp_path, monkeypatch):
    pdf_bytes = Path(MINIMAL_TREATY_PATH).read_bytes()
    monkeypatch.chdir(tmp_path)

    at = AppTest.from_file("../src/app.py")
    at.run()
    at = _upload_and_click_analyze(at, "sample_treaty.pdf", pdf_bytes)

    at.radio[1].set_value("PDF (.pdf)").run()
    at = _click_button(at, "Save analysis results")

    assert not at.exception
    saved_files = list((tmp_path / "results" / "acme_insurance_co").glob("*.pdf"))
    assert len(saved_files) == 1


def test_app_save_analysis_results_includes_llm_usage_when_fallback_ran(tmp_path, monkeypatch):
    mock_client = _mock_llm_client(input_data=FUZZY_TREATY_LLM_RESPONSE)
    monkeypatch.setattr("src.llm_client.anthropic.Anthropic", lambda **kwargs: mock_client)
    fuzzy_bytes = Path(FUZZY_TREATY_PATH).read_bytes()
    monkeypatch.chdir(tmp_path)

    at = AppTest.from_file("../src/app.py")
    at.run()
    at = _upload_and_click_analyze(at, "sample_rich_fuzzy_treaty.pdf", fuzzy_bytes)
    at = _click_button(at, "Save analysis results")

    assert not at.exception
    saved_files = list((tmp_path / "results").glob("*/*.md"))
    assert len(saved_files) == 1
    assert "LLM usage: input tokens: 500, output tokens: 60" in saved_files[0].read_text()


def test_app_download_analysis_results_button_matches_selected_format():
    at = AppTest.from_file("../src/app.py")
    at.run()

    with open(MINIMAL_TREATY_PATH, "rb") as f:
        at = _upload_and_click_analyze(at, "sample_treaty.pdf", f.read())

    download_buttons = [b for b in at.download_button if b.label == "Download analysis results"]
    assert len(download_buttons) == 1
    # AppTest's DownloadButton only exposes a mock media URL, not the raw
    # bytes/filename passed to st.download_button -- so this only checks
    # what's actually observable here (the button exists, offering the
    # format matching the radio choice); format_results_filename()'s
    # naming and render_report_bytes()'s content are covered by their own
    # direct unit tests above.
    assert download_buttons[0].proto.url.endswith(".md")

    at.radio[1].set_value("PDF (.pdf)").run()

    download_buttons = [b for b in at.download_button if b.label == "Download analysis results"]
    assert len(download_buttons) == 1
    assert download_buttons[0].proto.url.endswith(".pdf")


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
    at = _upload_and_click_analyze(at, "sample_treaty.pdf", pdf_bytes)

    at.segmented_control[0].set_value("Overwrite").run()
    at = _click_button(at, "Save to logs file")

    assert not at.exception
    log_file = tmp_path / "logs" / "workflow.log"
    assert log_file.exists()
    content = log_file.read_text()
    assert "=== Run at " in content
    assert "file: sample_treaty.pdf ===" in content
    assert "Extractor" in content
    assert any("Saved" in s.value for s in at.success)