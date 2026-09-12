"""Streamlit UI / FastAPI endpoints."""

import hashlib
import json
import logging
import re
import sys
import tempfile
from collections.abc import Callable
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

# Streamlit's launcher (including Streamlit Community Cloud) only adds this
# file's own directory (src/) to sys.path, not the repo root, so the absolute
# `src.*` imports below can't resolve unless the repo root is added here too.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import streamlit as st
from fpdf import FPDF

from src.cost_estimation import actual_task_cost, estimate_task_cost
from src.domain_tasks import DOMAIN_TASKS
from src.models import AnomalyFinding, AnomalyReport, TaskResult
from src.parser import ParserError, extract_treaty_sections
from src.sample_treaties import SAMPLE_TREATIES, get_sample_bytes
from src.services.plain_english_treaty_summary import generate_plain_english_treaty_summary
from src.workflow import DEFAULT_SELECTED_TASK_IDS, WorkflowState, run_workflow_from_pdf

SEVERITY_ICONS = {"low": "ℹ️", "medium": "⚠️", "high": "🚨"}
DEFAULT_LOG_FILE = Path("logs/workflow.log")
DEFAULT_RESULTS_DIR = Path("results")
_SEVERITY_RANK = {"low": 0, "medium": 1, "high": 2}
# Domain-task checklist row: checkbox+title, shape, label ("Estimated
# cost:"/"Not implemented"), value ("$X"). The total-cost row reuses these
# same weights (merging the first three into one wide label column) so its
# dollar value lines up under each task's own value column. Label:value
# keeps a 2:1 ratio, but the pair takes a smaller share of the row overall
# than checkbox+shape -- task titles need more room than short cost text.
_TASK_ROW_COLUMN_WEIGHTS = [3, 1, 1, 0.5]
# Tall enough to fit st.file_uploader's drag-and-drop box (the taller of the
# two treaty-source inputs) without clipping. Both the uploader and the
# selectbox render inside a bordered container of this same fixed height, so
# they present as equal-height boxes -- not just equal *page* height with the
# shorter selectbox floating in blank space.
SOURCE_INPUT_HEIGHT = 140


class _ListLogHandler(logging.Handler):
    """Captures formatted log records into a plain list for on-page display."""

    def __init__(self, sink: list[str]):
        super().__init__()
        self.sink = sink
        self.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))

    def emit(self, record: logging.LogRecord) -> None:
        self.sink.append(self.format(record))


def run_workflow_on_bytes(file_bytes: bytes, selected_task_ids: set[str] | None = None) -> WorkflowState:
    """Write the uploaded bytes to a temp file and run the full agent workflow on them.

    Raises ParserError if the PDF cannot be read or has no extractable text.
    See build_workflow_graph() (src/workflow.py) for selected_task_ids'
    meaning and default.
    """
    with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
        tmp.write(file_bytes)
        tmp.flush()
        return run_workflow_from_pdf(Path(tmp.name), selected_task_ids)


def get_pdf_page_count(file_bytes: bytes) -> int:
    """Cheaply parse a PDF's page count for the live cost estimate, with no LLM call.

    Returns 0 if the bytes can't be parsed as a PDF -- the caller (the
    per-task cost readout) should treat that the same as "unknown," not
    crash, since this runs on every rerun while a document is selected,
    before the user has committed to analyzing it.
    """
    with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
        tmp.write(file_bytes)
        tmp.flush()
        try:
            return len(extract_treaty_sections(Path(tmp.name)))
        except ParserError:
            return 0


def extract_report(state: WorkflowState) -> AnomalyReport:
    """Pull the AnomalyReport out of a WorkflowState, or raise if extraction was incomplete."""
    report = state.get("report")
    if report is None:
        missing = ", ".join(state.get("missing_fields", [])) or "unknown fields"
        raise ValueError(f"Could not extract required treaty terms: {missing}")
    return report


def resolve_report_for_display(state: WorkflowState) -> AnomalyReport:
    """Build the AnomalyReport used for the shared treaty-terms display and
    burn_cost_check's own section, regardless of whether burn_cost_check
    was selected/ran.

    state["report"] is only ever populated by burn_cost_check_node --
    every other domain task only writes to state["task_results"]. Gating
    on state["report"] (extract_report()'s check) would incorrectly
    report "could not extract required treaty terms" whenever
    burn_cost_check isn't selected, even though extraction (state
    ["treaty"]) actually succeeded. This checks state["treaty"] instead
    -- the real extraction-succeeded signal, set by the shared pipeline
    regardless of which analysis tasks are selected -- and falls back to
    a placeholder AnomalyReport (empty claims/findings, loss_ratio 0.0)
    when burn_cost_check didn't run. Safe: every place that reads
    report.loss_ratio/report.findings is already guarded by `task_id ==
    "burn_cost_check"` (_task_section_content(), _task_findings_for_
    severity(), format_findings_summary()), reached only when that task
    was actually selected -- so the placeholder's dummy values are never
    surfaced to the user.

    Raises ValueError (same message as extract_report()) if extraction
    itself failed -- state["treaty"] is None.
    """
    treaty = state.get("treaty")
    if treaty is None:
        missing = ", ".join(state.get("missing_fields", [])) or "unknown fields"
        raise ValueError(f"Could not extract required treaty terms: {missing}")
    report = state.get("report")
    if report is not None:
        return report
    return AnomalyReport(treaty=treaty, claims=state.get("claims", []), loss_ratio=0.0, findings=[])


def analyze_uploaded_pdf(file_bytes: bytes) -> AnomalyReport:
    """Run the full agent workflow on an uploaded PDF's raw bytes.

    Raises ParserError if the PDF cannot be read or has no extractable
    text, or ValueError if the treaty is missing required fields.
    """
    return extract_report(run_workflow_on_bytes(file_bytes))


def serialize_state_for_debug(state: WorkflowState) -> dict:
    """Convert a WorkflowState into a JSON-safe dict for a debug display (e.g. st.json)."""
    return {
        "sections": [asdict(section) for section in state.get("sections", [])],
        "treaty": treaty.model_dump(mode="json") if (treaty := state.get("treaty")) else None,
        "missing_fields": state.get("missing_fields", []),
        "extraction_method": state.get("extraction_method"),
        "llm_error": state.get("llm_error"),
        "ungrounded_fields": state.get("ungrounded_fields", []),
        "claims": [claim.model_dump(mode="json") for claim in state.get("claims", [])],
        "complete": state.get("complete", False),
        "report": report.model_dump(mode="json") if (report := state.get("report")) else None,
        "task_results": {
            task_id: task_result.model_dump(mode="json")
            for task_id, task_result in state.get("task_results", {}).items()
        },
    }


def format_extraction_status(state: WorkflowState) -> str:
    """Human-readable summary of which extraction path a run took, for the debug panel."""
    method = state.get("extraction_method")
    if method == "llm":
        return (
            "This run used the **LLM Extraction Fallback** (Claude Haiku 4.5) "
            "because the Extractor (Regex) step couldn't find every required "
            "field — see the log lines below for duration and token usage."
        )
    if method == "regex":
        return (
            "This run's Extractor (Regex) step found every required field, "
            "so no LLM call was needed."
        )
    llm_error = state.get("llm_error")
    if llm_error:
        return (
            "Regex extraction failed to find required fields, and the LLM "
            f"Extraction Fallback also could not recover them: {llm_error}"
        )
    return (
        "Regex extraction failed to find required fields, and the LLM "
        "Extraction Fallback was not run."
    )


def format_multi_task_status(selected_task_ids: set[str], task_results: dict[str, TaskResult]) -> str:
    """Human-readable summary of which selected domain task(s) ran, were
    skipped, or failed, for the debug panel and the saved log file.

    Additional to (not a replacement for) format_extraction_status() above --
    that reports *how* extraction happened (regex vs. LLM fallback), this
    reports *which domain tasks* ran, which is an orthogonal question.
    task_results (from src.workflow.WorkflowState) only ever holds entries
    for tasks that actually ran, so a selected id absent from it was either
    skipped (not implemented) or never reached (extraction incomplete) --
    distinguished here via src.domain_tasks.DOMAIN_TASKS' implementation_status.
    """
    if not selected_task_ids:
        return "No domain tasks were selected."

    implemented_ids = {task.id for task in DOMAIN_TASKS if task.implementation_status == "implemented"}
    lines = []
    for task_id in sorted(selected_task_ids):
        result = task_results.get(task_id)
        if result is not None:
            if result.status == "ran":
                lines.append(
                    f"- **{task_id}**: ran ({len(result.findings)} finding(s), "
                    f"${result.cost:,.4f}, {result.latency:.2f}s)"
                )
            else:
                lines.append(f"- **{task_id}**: {result.status}")
        elif task_id not in implemented_ids:
            lines.append(f"- **{task_id}**: skipped (not implemented)")
        else:
            lines.append(f"- **{task_id}**: did not run (extraction incomplete)")
    return "\n".join(lines)


def format_log_header(filename: str, when: datetime | None = None) -> str:
    """Build a one-line header identifying a workflow run, to prefix its saved log lines."""
    timestamp = (when or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
    return f"=== Run at {timestamp} | file: {filename} ==="


def save_logs_to_file(log_lines: list[str], mode: str, path: Path = DEFAULT_LOG_FILE) -> None:
    """Write log_lines to path, one per line.

    mode "append" adds them after the file's existing content; "overwrite"
    clears the file first so it holds only this run's lines.
    """
    if mode not in ("append", "overwrite"):
        raise ValueError(f"Unknown save mode: {mode!r}")
    path.parent.mkdir(parents=True, exist_ok=True)
    file_mode = "a" if mode == "append" else "w"
    with open(path, file_mode, encoding="utf-8") as f:
        for line in log_lines:
            f.write(line + "\n")


def _debug_extraction_status_text(state: WorkflowState | None) -> str:
    """Same status text as the debug panel's own caption -- extracted so
    it's shared by the on-screen caption and the downloadable report.
    """
    if state is None:
        return "No workflow state was produced -- the PDF could not be parsed, so no node ran."
    return format_extraction_status(state)


def format_debug_report_text(
    filename: str,
    state: WorkflowState | None,
    log_lines: list[str],
    selected_task_ids: set[str],
    task_results: dict[str, TaskResult],
    when: datetime | None = None,
) -> str:
    """Plain-text rendering of the "Analysis Workflow execution" debug
    panel's content (extraction status, multi-task status, captured log
    lines, and the full serialized workflow state), for direct download --
    mirrors what's already shown on screen.
    """
    lines = [format_log_header(filename, when=when), "", _debug_extraction_status_text(state)]
    lines.append(format_multi_task_status(selected_task_ids, task_results))
    lines.append("")
    lines.append("=== Captured log lines ===")
    lines.extend(log_lines or ["No log lines captured."])
    if state is not None:
        lines.append("")
        lines.append("=== Workflow state (debug) ===")
        lines.append(json.dumps(serialize_state_for_debug(state), indent=2))
    return "\n".join(lines)


def format_debug_report_json(
    filename: str,
    state: WorkflowState | None,
    log_lines: list[str],
    selected_task_ids: set[str],
    task_results: dict[str, TaskResult],
    when: datetime | None = None,
) -> dict:
    """Same content as format_debug_report_text(), as a real JSON-safe
    dict instead of a formatted string -- for the "JSON (.json)" download
    format choice.
    """
    return {
        "header": format_log_header(filename, when=when),
        "extraction_status": _debug_extraction_status_text(state),
        "multi_task_status": format_multi_task_status(selected_task_ids, task_results),
        "log_lines": list(log_lines or []),
        "state": serialize_state_for_debug(state) if state is not None else None,
    }


def format_debug_report_filename(extension: str, when: datetime | None = None) -> str:
    """Build the debug-report download filename: <timestamp>_debug.<extension>."""
    timestamp = (when or datetime.now()).strftime("%Y%m%d_%H%M%S")
    return f"{timestamp}_debug.{extension}"


def _task_title(task_id: str) -> str:
    """The human-readable title for a domain task id, or the id itself
    if it's not (or no longer) in the DOMAIN_TASKS registry.
    """
    for task in DOMAIN_TASKS:
        if task.id == task_id:
            return task.title
    return task_id


_FINDINGS_BACKGROUND_COLORS = {
    "high": "#f8d7da",
    "medium": "#fff3cd",
    "low": "#d1ecf1",
    "clean": "#d4edda",
}


def _findings_bullets_markdown(findings: list[AnomalyFinding]) -> str:
    """Bulleted findings list (icon + severity + description), or a
    "no anomalies" line when empty -- shared by every place findings are
    listed (a task's own section, the final Findings Summary).
    """
    if not findings:
        return "No anomalies found."
    lines = []
    for finding in findings:
        icon = SEVERITY_ICONS.get(finding.severity, "")
        lines.append(f"- {icon} **[{finding.severity.upper()}]** {finding.description}")
    return "\n".join(lines)


def _findings_heading_and_bullets_markdown(findings: list[AnomalyFinding]) -> str:
    """Plain "### Findings (N)" heading + bullets, no coloring/HTML -- used
    on screen (colored natively via Streamlit containers instead, see
    _SEVERITY_STREAMLIT_CONTAINERS) and as the base for the saved file's
    colored version (_wrap_findings_block()).
    """
    return f"### Findings ({len(findings)})\n{_findings_bullets_markdown(findings)}"


def _wrap_findings_block(findings: list[AnomalyFinding]) -> str:
    """The Findings block wrapped in an HTML div with a severity-colored
    background (via highest_severity_label()), for the saved file ONLY.
    Never render this through st.markdown() on screen -- Streamlit doesn't
    render raw HTML by default (correctly: treaty-derived text elsewhere
    on the page comes from an uploaded PDF the extractor doesn't sanitize,
    so enabling unsafe_allow_html would be a stored-HTML-injection risk).
    A saved/downloaded file has no such risk (fpdf2 treats these markers as
    plain text cues, never executes them; a Markdown viewer either renders
    the div or safely ignores it).
    """
    color = _FINDINGS_BACKGROUND_COLORS[highest_severity_label(findings)]
    body = _findings_heading_and_bullets_markdown(findings)
    return f'<div style="background-color:{color}; border-radius:6px; padding:10px 16px; margin:8px 0;">\n\n{body}\n\n</div>'


def _task_section_content(
    task_id: str,
    task_result: TaskResult | None,
    report: AnomalyReport | None,
    findings_markdown: Callable[[list[AnomalyFinding]], str],
) -> str:
    """Shared body for one task's results section (results only -- no
    treaty terms, which are shared across every task): Cost/Latency (when
    available) + Loss ratio (burn_cost_check only) + findings, with the
    findings portion rendered by `findings_markdown` -- plain for on-screen
    use (format_task_section_markdown()), HTML-colored for the saved file
    (_format_task_section_markdown_for_file()).

    `burn_cost_check` is special-cased since it's the only task that
    populates `report` today (see S3's decision in REASONING.md); it still
    shows its own Cost/Latency line from `task_result`, exactly like every
    other task, since burn_cost_check_node always returns one when it runs.
    """
    if task_id == "burn_cost_check" and report is not None:
        lines = []
        if task_result is not None:
            lines.append(f"**Cost:** ${task_result.cost:,.4f}  ·  **Latency:** {task_result.latency:.2f}s")
            lines.append("")
        lines.append(f"### Loss ratio: {report.loss_ratio:.2f}")
        lines.append("")
        lines.append(findings_markdown(report.findings))
        return "\n".join(lines)

    if task_result is None:
        implemented_ids = {t.id for t in DOMAIN_TASKS if t.implementation_status == "implemented"}
        if task_id not in implemented_ids:
            return "_Not implemented yet._"
        return "_Did not run (extraction incomplete)._"

    if task_result.status != "ran":
        return f"_{task_result.status}._"

    lines = [f"**Cost:** ${task_result.cost:,.4f}  ·  **Latency:** {task_result.latency:.2f}s", ""]
    lines.append(findings_markdown(task_result.findings))
    return "\n".join(lines)


def format_task_section_markdown(
    task_id: str, task_result: TaskResult | None, report: AnomalyReport | None
) -> str:
    """Plain Markdown body for one selected task's own expandable results
    section -- no HTML/coloring (see _task_findings_for_severity() for how
    the on-screen view applies color natively instead).
    """
    return _task_section_content(task_id, task_result, report, _findings_heading_and_bullets_markdown)


def _format_task_section_markdown_for_file(
    task_id: str, task_result: TaskResult | None, report: AnomalyReport | None
) -> str:
    """Same content as format_task_section_markdown(), but with the
    Findings block wrapped in a severity-colored HTML div -- for the saved
    file only (format_results_document()).
    """
    return _task_section_content(task_id, task_result, report, _wrap_findings_block)


def _task_findings_for_severity(
    task_id: str, task_result: TaskResult | None, report: AnomalyReport | None
) -> list[AnomalyFinding] | None:
    """The findings to color a task's on-screen section by, or None if the
    task didn't actually run (skipped/failed/not-implemented sections are
    shown plain, with no severity to color by).
    """
    if task_id == "burn_cost_check" and report is not None:
        return report.findings
    if task_result is not None and task_result.status == "ran":
        return task_result.findings
    return None


_SEVERITY_STREAMLIT_CONTAINERS = {
    "high": st.error,
    "medium": st.warning,
    "low": st.info,
    "clean": st.success,
}


def format_combined_results_summary(
    selected_task_ids: set[str], task_results: dict[str, TaskResult], extraction_cost: float = 0.0
) -> str:
    """Combined header shown above the per-task results sections: aggregate
    findings/cost across every task that ran, plus which selected tasks were
    skipped and why (not implemented, or extraction never reached them).

    extraction_cost (default 0.0, additive) folds in the LLM Extraction
    Fallback's real cost when it ran (see extract_llm_actual_cost()) -- a
    shared pipeline cost, not any one task's own, but still part of what
    this run actually cost.
    """
    implemented_ids = {t.id for t in DOMAIN_TASKS if t.implementation_status == "implemented"}
    total_findings = 0
    tasks_cost = 0.0
    skipped_lines = []
    for task_id in sorted(selected_task_ids):
        result = task_results.get(task_id)
        if result is not None and result.status == "ran":
            total_findings += len(result.findings)
            tasks_cost += result.cost
        elif task_id not in implemented_ids:
            skipped_lines.append(f"- **{_task_title(task_id)}**: not implemented yet")
        else:
            skipped_lines.append(f"- **{_task_title(task_id)}**: did not run (extraction incomplete)")

    total_cost = tasks_cost + extraction_cost
    # "\$" (not a bare "$") -- Streamlit's st.markdown() renders $...$ as
    # inline LaTeX math, and this line can have multiple "$" signs (three
    # in the breakdown case), which would otherwise pair up and switch part
    # of the line to a math-mode font instead of rendering as plain text.
    if extraction_cost:
        # Named breakdown, not just the final number -- the total otherwise
        # looks inconsistent with the per-task Cost lines shown below it,
        # since none of them include this shared, not-any-one-task's-own cost.
        cost_text = f"\\${tasks_cost:,.4f} (tasks) + \\${extraction_cost:,.4f} (extraction) = \\${total_cost:,.4f}"
    else:
        cost_text = f"\\${total_cost:,.4f}"
    lines = [f"**{total_findings} finding(s) across selected task(s) · {cost_text} total actual cost**"]
    if skipped_lines:
        lines.append("")
        lines.append("**Skipped:**")
        lines.extend(skipped_lines)
    return "\n".join(lines)


def format_findings_summary(selected_task_ids: set[str], task_results: dict[str, TaskResult], report: AnomalyReport) -> str:
    """Final "Findings Summary" section for the saved report: every task
    that actually ran, listed again under its own heading with its findings
    repeated -- a scannable recap after reading each task's own section.
    Skipped/not-run tasks aren't repeated here; format_combined_results_
    summary()'s "Skipped" list already covers those.
    """
    lines = ["# Findings Summary"]
    for task_id in sorted(selected_task_ids):
        if task_id == "burn_cost_check":
            findings = report.findings
        else:
            result = task_results.get(task_id)
            if result is None or result.status != "ran":
                continue
            findings = result.findings
        lines.append(f"\n## {_task_title(task_id)}")
        lines.append(_findings_bullets_markdown(findings))
    return "\n".join(lines)


def format_treaty_terms_markdown(report: AnomalyReport) -> str:
    """Shared treaty terms block, rendered once regardless of how many
    tasks ran on it -- every selected task analyzes this same treaty.
    """
    treaty = report.treaty
    citations = treaty.page_citations

    def cite(field: str) -> str:
        page = citations.get(field)
        return f" _(p. {page})_" if page is not None else ""

    lines = [
        f"## Treaty: {treaty.cedent_name}{cite('cedent_name')}",
        f"- **Attachment point:** {treaty.attachment_point:,.2f}{cite('attachment_point')}",
        f"- **Limit:** {treaty.limit:,.2f}{cite('limit')}",
        f"- **Reinsurance premium:** {treaty.reinsurance_premium:,.2f}{cite('reinsurance_premium')}",
    ]
    if treaty.exclusions:
        lines.append(f"- **Exclusions**{cite('exclusions')}: {', '.join(treaty.exclusions)}")
    return "\n".join(lines)


def format_report_markdown(report: AnomalyReport) -> str:
    """Render an AnomalyReport as a Markdown string: treaty terms, loss
    ratio, and findings. Kept as a single-report convenience combining
    format_treaty_terms_markdown() with burn_cost_check's own results --
    the multi-task saved-file path (format_results_document) renders the
    treaty separately instead, since every selected task shares it.
    """
    return f"{format_treaty_terms_markdown(report)}\n\n{format_task_section_markdown('burn_cost_check', None, report)}"


def slugify_treaty_name(name: str, max_length: int = 40) -> str:
    """Turn a treaty/cedent name into a short, filesystem-safe slug."""
    slug = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_").lower()
    return (slug or "treaty")[:max_length]


def highest_severity_label(findings: list) -> str:
    """The highest-severity finding's label, or "clean" if there are none."""
    if not findings:
        return "clean"
    return max(findings, key=lambda f: _SEVERITY_RANK[f.severity]).severity.value


_LLM_USAGE_RE = re.compile(r"input_tokens=(\d+), output_tokens=(\d+)")


def extract_llm_usage_summary(log_lines: list[str] | None) -> str | None:
    """Pull input/output token counts from the LLM Extraction Fallback's log
    line, if the LLM was actually invoked for this run -- None otherwise
    (e.g. the regex Extractor found every field, so no LLM call was made).
    """
    for line in log_lines or []:
        match = _LLM_USAGE_RE.search(line)
        if match:
            input_tokens, output_tokens = match.groups()
            return f"input tokens: {input_tokens}, output tokens: {output_tokens}"
    return None


def extract_llm_actual_cost(log_lines: list[str] | None) -> float | None:
    """The LLM Extraction Fallback's real dollar cost for this run (via
    actual_task_cost()), or None if the LLM wasn't invoked -- this is a
    shared pipeline cost, not attributable to any one selected domain
    task's own TaskResult (every selected task benefits from the same
    one-time extraction), so it's surfaced separately rather than folded
    into any task's own Cost figure.
    """
    for line in log_lines or []:
        match = _LLM_USAGE_RE.search(line)
        if match:
            input_tokens, output_tokens = (int(group) for group in match.groups())
            return actual_task_cost(input_tokens, output_tokens)
    return None


def format_extraction_cost_note(log_lines: list[str] | None) -> str | None:
    """A one-line note reporting the LLM Extraction Fallback's real dollar
    cost, or None if the LLM wasn't invoked for this run (regex found
    everything, so there's no extraction cost to report).
    """
    cost = extract_llm_actual_cost(log_lines)
    if cost is None:
        return None
    return f"Extraction: LLM Fallback used (${cost:,.4f})"


def results_subdirectory(report: AnomalyReport, base: Path = DEFAULT_RESULTS_DIR) -> Path:
    """The per-treaty subdirectory saved results for this cedent are organized under."""
    return base / slugify_treaty_name(report.treaty.cedent_name)


def format_results_filename(report: AnomalyReport, extension: str, when: datetime | None = None) -> str:
    """Build the saved-results filename: <timestamp>_<severity>.<extension>.

    The treaty name isn't repeated here -- it's the containing subdirectory
    (see results_subdirectory()), since results are organized per-treaty.
    """
    timestamp = (when or datetime.now()).strftime("%Y%m%d_%H%M%S")
    severity = highest_severity_label(report.findings)
    return f"{timestamp}_{severity}.{extension}"


def format_results_document(
    report: AnomalyReport,
    log_lines: list[str] | None = None,
    when: datetime | None = None,
    selected_task_ids: set[str] | None = None,
    task_results: dict[str, TaskResult] | None = None,
) -> str:
    """A saved/downloaded "final report" for this run: title, generation
    timestamp, (only if the LLM Extraction Fallback actually ran) its token
    usage, treaty terms, results, and -- when multiple tasks were run -- a
    closing Findings Summary. None of the run metadata is part of the
    on-screen report itself, which describes the treaty, not this run.

    selected_task_ids/task_results are optional and additive: when omitted
    (the default), renders exactly today's single format_report_markdown()
    output (treaty + burn_cost_check's results combined, no section rules
    or Findings Summary). When provided, renders "Analysis Results" as the
    top-level heading, treaty terms in their own shared section (every
    selected task analyzes the same treaty, not just one), the combined
    summary, one `##`-level section per selected task (severity-colored
    Findings), and a final Findings Summary recapping every ran task's
    findings -- sections separated by horizontal rules, styled like a
    finished report rather than a flat dump.
    """
    timestamp = (when or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
    lines = ["# Analysis Results" if selected_task_ids is not None else "## Analysis Results", f"Generated: {timestamp}"]
    llm_usage = extract_llm_usage_summary(log_lines)
    if llm_usage:
        lines.append(f"LLM usage: {llm_usage}")
    lines.append("")
    if selected_task_ids is None:
        lines.append(format_report_markdown(report))
    else:
        task_results = task_results or {}
        extraction_cost = extract_llm_actual_cost(log_lines)
        lines.append("---")
        lines.append("")
        lines.append(format_treaty_terms_markdown(report))
        extraction_note = format_extraction_cost_note(log_lines)
        if extraction_note:
            lines.append("")
            lines.append(extraction_note)
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append(
            format_combined_results_summary(selected_task_ids, task_results, extraction_cost=extraction_cost or 0.0)
        )
        for task_id in sorted(selected_task_ids):
            lines.append("")
            lines.append("---")
            lines.append("")
            lines.append(f"## {_task_title(task_id)}")
            lines.append("")
            lines.append(_format_task_section_markdown_for_file(task_id, task_results.get(task_id), report))
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append(format_findings_summary(selected_task_ids, task_results, report))
    return "\n".join(lines)


_PDF_HEADING_FONT_SIZES = {1: 16, 2: 14, 3: 12}
_DIV_BACKGROUND_COLOR_RE = re.compile(r'<div style="background-color:(#[0-9a-fA-F]{6})[^"]*">')

# fpdf2's core fonts (Helvetica etc.) are base-14 Latin-1-only, so the color
# severity emoji (SEVERITY_ICONS) never survived PDF rendering. DejaVu Sans
# (bundled under assets/fonts/, Bitstream Vera license -- redistributable)
# is a real Unicode TTF, but even it has no glyph for the astral/color
# emoji SEVERITY_ICONS uses (🚨 etc. are outside what any general-purpose
# non-color-emoji font includes) -- substitute plain Unicode symbols DejaVu
# does contain (verified via fontTools before choosing these) instead.
_FONTS_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"
_DEJAVU_REGULAR_PATH = _FONTS_DIR / "DejaVuSans.ttf"
_DEJAVU_BOLD_PATH = _FONTS_DIR / "DejaVuSans-Bold.ttf"
_PDF_SEVERITY_SYMBOLS = {"low": "ℹ", "medium": "⚠", "high": "‼"}
_EMOJI_TO_PDF_SYMBOL = {SEVERITY_ICONS[severity]: symbol for severity, symbol in _PDF_SEVERITY_SYMBOLS.items()}


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    return (int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16))


def render_report_pdf(
    report: AnomalyReport,
    log_lines: list[str] | None = None,
    when: datetime | None = None,
    selected_task_ids: set[str] | None = None,
    task_results: dict[str, TaskResult] | None = None,
) -> bytes:
    """Render an AnomalyReport as PDF bytes, mirroring format_results_document's content.

    Uses the bundled DejaVu Sans (a real Unicode TTF, not fpdf2's Latin-1-only
    core fonts) so severity symbols survive -- SEVERITY_ICONS' color emoji are
    substituted for plain Unicode equivalents DejaVu actually contains
    (_EMOJI_TO_PDF_SYMBOL), since no general-purpose font includes true
    color/astral emoji glyphs. Heading levels (#/##/###) get genuinely
    different font sizes (not one flat "heading" size), a literal `---` line
    is drawn as a real horizontal rule, and the HTML
    `<div style="background-color:...">`/`</div>` markers around a Findings
    block toggle a filled cell background matching format_results_document's
    Markdown styling.
    """
    pdf = FPDF()
    pdf.add_font("DejaVu", "", str(_DEJAVU_REGULAR_PATH))
    pdf.add_font("DejaVu", "B", str(_DEJAVU_BOLD_PATH))
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    document = format_results_document(
        report,
        log_lines=log_lines,
        when=when,
        selected_task_ids=selected_task_ids,
        task_results=task_results,
    )
    fill_color: tuple[int, int, int] | None = None
    for raw_line in document.split("\n"):
        line = raw_line.strip()
        if not line:
            pdf.ln(4)
            continue
        if line == "---":
            pdf.ln(2)
            pdf.set_draw_color(180, 180, 180)
            pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
            pdf.ln(4)
            continue
        div_match = _DIV_BACKGROUND_COLOR_RE.match(line)
        if div_match:
            fill_color = _hex_to_rgb(div_match.group(1))
            continue
        if line == "</div>":
            fill_color = None
            continue

        heading_match = re.match(r"^(#+)\s*", line)
        heading_level = len(heading_match.group(1)) if heading_match else 0
        line = re.sub(r"^#+\s*", "", line)
        line = line.replace("**", "")
        line = line.replace("_(", "(").replace(")_", ")")
        for emoji, symbol in _EMOJI_TO_PDF_SYMBOL.items():
            line = line.replace(emoji, symbol)
        line = re.sub(r"\s+", " ", line).strip()
        if not line:
            continue
        size = _PDF_HEADING_FONT_SIZES.get(heading_level, 11)
        pdf.set_font("DejaVu", style="B" if heading_level else "", size=size)
        if fill_color is not None:
            pdf.set_fill_color(*fill_color)
        # multi_cell defaults to leaving the cursor at the right edge of the
        # last rendered line (new_x="RIGHT") rather than the next line's left
        # margin -- without resetting it, the next call gets ~0 width and
        # raises "Not enough horizontal space to render a single character".
        pdf.multi_cell(0, 7, line, new_x="LMARGIN", new_y="NEXT", fill=fill_color is not None)

    return bytes(pdf.output())


def render_report_bytes(
    report: AnomalyReport,
    extension: str,
    log_lines: list[str] | None = None,
    when: datetime | None = None,
    selected_task_ids: set[str] | None = None,
    task_results: dict[str, TaskResult] | None = None,
) -> bytes:
    """Render report as bytes in the given format ("md" or "pdf")."""
    if extension == "pdf":
        return render_report_pdf(
            report, log_lines=log_lines, when=when, selected_task_ids=selected_task_ids, task_results=task_results
        )
    return format_results_document(
        report, log_lines=log_lines, when=when, selected_task_ids=selected_task_ids, task_results=task_results
    ).encode("utf-8")


def save_analysis_result_to_file(
    report: AnomalyReport,
    extension: str,
    log_lines: list[str] | None = None,
    directory: Path = DEFAULT_RESULTS_DIR,
    when: datetime | None = None,
    selected_task_ids: set[str] | None = None,
    task_results: dict[str, TaskResult] | None = None,
) -> Path:
    """Write report to a new timestamped file (under a per-treaty subdirectory
    of directory) in the given format, returning its path.
    """
    when = when or datetime.now()
    target_dir = results_subdirectory(report, directory)
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / format_results_filename(report, extension, when=when)
    path.write_bytes(
        render_report_bytes(
            report,
            extension,
            log_lines=log_lines,
            when=when,
            selected_task_ids=selected_task_ids,
            task_results=task_results,
        )
    )
    return path


def format_summary_document(summary_text: str, display_name: str, when: datetime | None = None) -> str:
    """A saved/downloaded plain-English summary document: title, generation
    timestamp, the picked treaty's display name, and the summary text.

    Deliberately independent of format_results_document()/AnomalyReport --
    the summary is generated straight from a picked treaty's raw sections,
    before (and regardless of whether) extraction/analysis ever runs, so
    there's no report to key this off.
    """
    timestamp = (when or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
    return (
        f"# Plain-English Treaty Summary\nGenerated: {timestamp}\nTreaty: {display_name}\n\n{summary_text}"
    )


def render_summary_pdf(summary_text: str, display_name: str, when: datetime | None = None) -> bytes:
    """Render a plain-English summary as PDF bytes, mirroring
    render_report_pdf's DejaVu-font setup (Unicode support) but without
    any of that function's severity-coloring/Findings-block handling --
    this document is just a title, a timestamp line, and prose.
    """
    pdf = FPDF()
    pdf.add_font("DejaVu", "", str(_DEJAVU_REGULAR_PATH))
    pdf.add_font("DejaVu", "B", str(_DEJAVU_BOLD_PATH))
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    document = format_summary_document(summary_text, display_name, when=when)
    for raw_line in document.split("\n"):
        line = raw_line.strip()
        if not line:
            pdf.ln(4)
            continue
        heading_match = re.match(r"^(#+)\s*", line)
        heading_level = len(heading_match.group(1)) if heading_match else 0
        line = re.sub(r"^#+\s*", "", line)
        size = _PDF_HEADING_FONT_SIZES.get(heading_level, 11)
        pdf.set_font("DejaVu", style="B" if heading_level else "", size=size)
        pdf.multi_cell(0, 7, line, new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())


def render_summary_bytes(summary_text: str, display_name: str, extension: str, when: datetime | None = None) -> bytes:
    """Render a plain-English summary as bytes in the given format ("md" or "pdf")."""
    if extension == "pdf":
        return render_summary_pdf(summary_text, display_name, when=when)
    return format_summary_document(summary_text, display_name, when=when).encode("utf-8")


def format_summary_filename(extension: str, when: datetime | None = None) -> str:
    timestamp = (when or datetime.now()).strftime("%Y%m%d_%H%M%S")
    return f"{timestamp}_plain_english_summary.{extension}"


def summary_results_subdirectory(display_name: str, base: Path = DEFAULT_RESULTS_DIR) -> Path:
    """The per-treaty subdirectory a saved summary is organized under.

    Keyed by the picked treaty's own display name/filename (slugified),
    not a cedent name -- unlike results_subdirectory(), the summary can be
    generated before extraction ever runs, so there's no extracted cedent
    name to key off yet.
    """
    return base / slugify_treaty_name(display_name)


def save_summary_to_file(
    summary_text: str,
    display_name: str,
    extension: str,
    directory: Path = DEFAULT_RESULTS_DIR,
    when: datetime | None = None,
) -> Path:
    """Write a plain-English summary to a new timestamped file (under a
    per-treaty subdirectory of directory) in the given format, returning
    its path.
    """
    when = when or datetime.now()
    target_dir = summary_results_subdirectory(display_name, directory)
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / format_summary_filename(extension, when=when)
    path.write_bytes(render_summary_bytes(summary_text, display_name, extension, when=when))
    return path


def _fingerprint(file_bytes: bytes) -> str:
    """A cheap content fingerprint used to detect a changed treaty selection."""
    return hashlib.sha256(file_bytes).hexdigest()


def _run_workflow_with_logging(
    file_bytes: bytes, display_name: str, selected_task_ids: set[str] | None = None
) -> dict:
    """Run the full workflow on file_bytes, capturing its log lines.

    Returned as a plain dict suitable for `st.session_state`, so the
    result survives reruns triggered by other widgets (e.g. the save-log
    form) after the "Analyze" click that produced it. See
    build_workflow_graph() (src/workflow.py) for selected_task_ids'
    meaning and default.
    """
    log_lines: list[str] = []
    handler = _ListLogHandler(log_lines)
    # "src" (not "src.workflow") so this also captures logging from
    # harness modules like src.llm_client, which log under their own
    # module name -- child loggers propagate up to this handler.
    src_logger = logging.getLogger("src")
    src_logger.addHandler(handler)
    src_logger.setLevel(logging.INFO)

    state: WorkflowState | None = None
    parser_error: str | None = None
    try:
        with st.spinner("Running agent workflow..."):
            try:
                state = run_workflow_on_bytes(file_bytes, selected_task_ids)
            except ParserError as exc:
                parser_error = str(exc)
    finally:
        src_logger.removeHandler(handler)

    return {
        "state": state,
        "log_lines": log_lines,
        "parser_error": parser_error,
        "selected_name": display_name,
        "selected_task_ids": selected_task_ids or set(),
        "fingerprint": _fingerprint(file_bytes),
    }


@st.dialog("Review treaty", width="small")
def _show_review_dialog(pdf_bytes: bytes, display_name: str) -> None:
    """Modal preview of the currently selected treaty's page-by-page text.

    Uses the "small" dialog width (Streamlit's narrower preset, centered
    over the main window) and a fixed-height scrollable content area, so
    a multi-page document doesn't grow the modal past a fixed footprint.
    """
    st.caption(display_name)
    with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
        tmp.write(pdf_bytes)
        tmp.flush()
        try:
            sections = extract_treaty_sections(Path(tmp.name))
        except ParserError as exc:
            st.error(f"Could not read this PDF: {exc}")
            return

    with st.container(height=440):
        for section in sections:
            st.markdown(f"**Page {section.page_number}**")
            st.text(section.text)


_MAIN_CONTAINER_MAX_WIDTH_PX = 800


def _inject_wide_main_container_css() -> None:
    """Widen the main content container by 15% over Streamlit's default
    "centered" layout width, via a fixed, hardcoded style block (safe to
    render with unsafe_allow_html=True -- no user-controlled or treaty-
    derived content is interpolated into it).

    Targets the stable data-testid="stMainBlockContainer" hook (Streamlit's
    own documented way to customize this container), not any
    st-emotion-cache-* class -- those are auto-generated hashes that can
    change on any Streamlit version bump or between reruns.
    """
    st.markdown(
        f"""
        <style>
        [data-testid="stMainBlockContainer"] {{
            max-width: {_MAIN_CONTAINER_MAX_WIDTH_PX}px !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _inject_ui_animation_css() -> None:
    """Tasteful, low-risk motion for the app's UI: fade/slide-in for
    elements that appear conditionally (containers, dialogs, alert
    banners), plus smooth hover/active transitions on buttons.

    Targets stable data-testid hooks only (never st-emotion-cache-*
    hash classes -- see _inject_wide_main_container_css()'s docstring
    for why). Fixed, hardcoded CSS -- safe with unsafe_allow_html=True,
    no user-controlled or treaty-derived content is interpolated here.

    Deliberately entrance-only, not exit: Streamlit reruns the whole
    script and only ever renders what the current run produces -- when
    a container's code path stops running (e.g. "Close" deletes its
    session_state entry and calls st.rerun()), the next render simply
    never creates that element, leaving no DOM node for a CSS
    transition to animate away. A real fade-*out* would need a hook to
    delay Streamlit's own removal (custom JS/a custom component), which
    is out of scope here -- fragile and unsupported by this repo's
    plain-Streamlit approach. A newly-appearing element, by contrast,
    is a genuine DOM insertion each time (confirmed against Streamlit's
    own React reconciliation), so an on-mount keyframe animation here
    reliably replays for it without spuriously re-triggering on
    unrelated reruns of an already-mounted element.

    @media (prefers-reduced-motion: reduce) disables all of this --
    accessibility best practice, not optional.
    """
    st.markdown(
        """
        <style>
        @keyframes fadeSlideIn {
            from { opacity: 0; transform: translateY(6px); }
            to { opacity: 1; transform: translateY(0); }
        }
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        [data-testid="stVerticalBlock"] {
            animation: fadeSlideIn 0.35s ease-out;
        }
        [data-testid="stAlert"] {
            animation: fadeIn 0.3s ease-out;
        }
        [data-testid="stDialog"] {
            animation: fadeIn 0.25s ease-out;
        }
        [data-testid="stButton"] button,
        [data-testid="stDownloadButton"] button {
            transition: transform 0.12s ease-out, box-shadow 0.12s ease-out;
        }
        [data-testid="stButton"] button:hover,
        [data-testid="stDownloadButton"] button:hover {
            transform: translateY(-1px);
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.12);
        }
        [data-testid="stButton"] button:active,
        [data-testid="stDownloadButton"] button:active {
            transform: translateY(0);
            box-shadow: none;
        }
        @media (prefers-reduced-motion: reduce) {
            [data-testid="stVerticalBlock"],
            [data-testid="stAlert"],
            [data-testid="stDialog"],
            [data-testid="stButton"] button,
            [data-testid="stDownloadButton"] button {
                animation: none !important;
                transition: none !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    st.set_page_config(page_title="Reinsurance Treaty Agent", page_icon="📄")
    _inject_wide_main_container_css()
    _inject_ui_animation_css()
    st.title("Reinsurance Treaty Agent")
    st.write(
        "Upload a treaty PDF, or choose one of the prepared sample "
        "treaties, to extract its terms, compare them against "
        "historical claims, and flag anomalies."
    )

    source_mode = st.radio(
        "Treaty source",
        ["Upload a treaty PDF", "Choose a reinsurance treaty"],
        horizontal=True,
        key="treaty_source_mode",
    )

    selected_bytes: bytes | None = None
    selected_name: str | None = None

    # Fixed height so switching between "Upload" and "Choose a sample" doesn't
    # shift the rest of the page -- st.file_uploader is much taller than
    # st.selectbox on its own, which would otherwise make the layout twitch.
    with st.container(height=SOURCE_INPUT_HEIGHT, border=True):
        if source_mode == "Upload a treaty PDF":
            uploaded_file = st.file_uploader("Treaty PDF", type="pdf")
            if uploaded_file is not None:
                selected_bytes = uploaded_file.getvalue()
                selected_name = uploaded_file.name
        else:
            placeholder = "— Select a sample —"
            labels = [placeholder] + [sample.label for sample in SAMPLE_TREATIES]
            choice = st.selectbox("Choose a reinsurance treaty", labels, key="sample_treaty_choice")
            if choice != placeholder:
                sample = next(s for s in SAMPLE_TREATIES if s.label == choice)
                selected_bytes = get_sample_bytes(sample)
                selected_name = sample.filename

    has_selection = selected_bytes is not None
    selected_fingerprint = _fingerprint(selected_bytes) if selected_bytes is not None else None

    review_col, summary_col = st.columns(2)
    with review_col:
        review_clicked = st.button("Review treaty", disabled=not has_selection)
    with summary_col:
        generate_summary_clicked = st.button(
            "Generate Plain-English Summary", icon=":material/summarize:", disabled=not has_selection
        )
    if review_clicked and selected_bytes is not None and selected_name is not None:
        _show_review_dialog(selected_bytes, selected_name)

    # Plain-English Treaty Summary (B7): a standalone opt-in action that
    # only depends on which treaty is picked, not on extraction/"Analyze"
    # -- placed here, right where the treaty is chosen, rather than in the
    # Analysis Results section below. Cached in its own session_state
    # entry (not run_result, which doesn't exist until "Analyze" is
    # clicked), invalidated whenever the treaty selection's fingerprint
    # changes.
    summary_state = st.session_state.get("plain_english_summary")
    if summary_state is not None and summary_state.get("fingerprint") != selected_fingerprint:
        del st.session_state["plain_english_summary"]
        summary_state = None

    if generate_summary_clicked and selected_bytes is not None and selected_name is not None:
        # Re-generating (whether the container below is still open or was
        # closed) always overwrites this state and re-renders it -- there's
        # no separate "regenerate" control, the same trigger button always
        # produces a fresh summary and reopens/replaces the container.
        with st.spinner("Generating summary..."):
            try:
                with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
                    tmp.write(selected_bytes)
                    tmp.flush()
                    sections = extract_treaty_sections(Path(tmp.name))
                result = generate_plain_english_treaty_summary(sections)
            except Exception as exc:  # noqa: BLE001 -- any failure must be shown, not crash the app
                summary_state = {
                    "fingerprint": selected_fingerprint,
                    "display_name": selected_name,
                    "text": None,
                    "input_tokens": None,
                    "output_tokens": None,
                    "error": str(exc),
                }
            else:
                summary_state = {
                    "fingerprint": selected_fingerprint,
                    "display_name": selected_name,
                    "text": result.text,
                    "input_tokens": result.input_tokens,
                    "output_tokens": result.output_tokens,
                    "error": None,
                }
            st.session_state["plain_english_summary"] = summary_state

    if summary_state is not None:
        with st.container(border=True):
            summary_header_col, summary_close_col = st.columns([6, 1])
            with summary_header_col:
                st.subheader("Plain-English Summary")
            with summary_close_col:
                summary_close_clicked = st.button("Close", icon=":material/close:", key="close_summary_button")
            if summary_close_clicked:
                del st.session_state["plain_english_summary"]
                st.rerun()

            if summary_state["error"]:
                st.error(f"Could not generate summary: {summary_state['error']}")
            else:
                st.markdown(summary_state["text"])
                # LLM usage is generation metadata, not part of the summary
                # itself -- shown as its own info line, never folded into
                # the text that gets saved/downloaded below.
                usage_cost = actual_task_cost(summary_state["input_tokens"], summary_state["output_tokens"])
                st.caption(
                    f"LLM usage: input tokens: {summary_state['input_tokens']}, "
                    f"output tokens: {summary_state['output_tokens']} (${usage_cost:,.4f})"
                )
                summary_format_choice = st.radio(
                    "Summary file format",
                    ["Markdown (.md)", "PDF (.pdf)"],
                    horizontal=True,
                    key="summary_format_choice",
                )
                summary_extension = "pdf" if summary_format_choice.startswith("PDF") else "md"
                summary_save_col, summary_download_col = st.columns(2)
                with summary_save_col:
                    if st.button("Save summary", icon=":material/save:"):
                        saved_summary_path = save_summary_to_file(
                            summary_state["text"], summary_state["display_name"], summary_extension
                        )
                        st.success(f"Saved summary to {saved_summary_path}.")
                with summary_download_col:
                    summary_download_when = datetime.now()
                    st.download_button(
                        "Download summary",
                        data=render_summary_bytes(
                            summary_state["text"],
                            summary_state["display_name"],
                            summary_extension,
                            when=summary_download_when,
                        ),
                        file_name=format_summary_filename(summary_extension, when=summary_download_when),
                        mime="application/pdf" if summary_extension == "pdf" else "text/markdown",
                        icon=":material/download:",
                    )

    st.subheader("Domain tasks to run")
    header_task_col, header_type_col, header_cost_col = st.columns(
        [_TASK_ROW_COLUMN_WEIGHTS[0], _TASK_ROW_COLUMN_WEIGHTS[1], sum(_TASK_ROW_COLUMN_WEIGHTS[2:])]
    )
    with header_task_col:
        st.caption("**Task**")
    with header_type_col:
        st.caption("**Type**")
    with header_cost_col:
        st.caption("**Cost (estimated)**")

    page_count = get_pdf_page_count(selected_bytes) if selected_bytes is not None else 0
    selected_task_ids: set[str] = set()
    total_estimated_cost = 0.0
    for task in DOMAIN_TASKS:
        if task.implementation_status == "implemented" and task.workflow_node is None:
            # A standalone opt-in task (today: plain_english_treaty_summary)
            # with its own separate UI trigger elsewhere, not a graph node --
            # it must never appear in this checklist, since selecting it
            # here and clicking "Analyze" would run it alongside whatever
            # else is selected, defeating its whole "opt-in, not automatic"
            # requirement. Every still-not-implemented task (workflow_node
            # is also None) still renders its usual disabled placeholder row
            # below -- this only excludes the implemented-but-standalone case.
            continue
        is_implemented = task.implementation_status == "implemented"
        checkbox_col, shape_col, label_col, value_col = st.columns(
            _TASK_ROW_COLUMN_WEIGHTS, vertical_alignment="center"
        )
        with checkbox_col:
            checked = st.checkbox(
                task.title,
                value=task.id in DEFAULT_SELECTED_TASK_IDS,
                disabled=not is_implemented,
                key=f"task_checkbox_{task.id}",
            )
        with shape_col:
            st.caption(task.shape)
        with label_col:
            if not is_implemented:
                st.caption("Not implemented")
            elif checked:
                selected_task_ids.add(task.id)
                estimated_cost = estimate_task_cost(task, page_count)
                total_estimated_cost += estimated_cost
                st.caption("Estimated cost:")
        with value_col:
            if is_implemented and checked:
                st.caption(f"${estimated_cost:,.4f}")
    # Same overall row width as _TASK_ROW_COLUMN_WEIGHTS (checkbox+shape+label
    # merged into one wide label column, since "Total estimated cost:" is
    # longer than "Estimated cost:"), so the value column -- and therefore
    # each dollar figure -- lines up in the same horizontal position.
    *_leading_weights, _value_weight = _TASK_ROW_COLUMN_WEIGHTS
    total_label_col, total_value_col = st.columns(
        [sum(_leading_weights), _value_weight], vertical_alignment="center"
    )
    with total_label_col:
        st.caption("**Total estimated cost:**")
    with total_value_col:
        st.caption(f"**${total_estimated_cost:,.4f}**")

    analyze_clicked = st.button(
        "Analyze", type="primary", disabled=not has_selection or not selected_task_ids
    )

    if analyze_clicked and selected_bytes is not None and selected_name is not None:
        st.session_state["workflow_run"] = _run_workflow_with_logging(
            selected_bytes, selected_name, selected_task_ids
        )

    run_result = st.session_state.get("workflow_run")
    if run_result is not None and run_result.get("fingerprint") != selected_fingerprint:
        # The treaty selection changed (new upload, different sample, cleared
        # upload, or switched source) since this result was produced -- clear
        # and close the results container rather than showing a stale report.
        del st.session_state["workflow_run"]
        run_result = None
    if run_result is None:
        return

    with st.container(border=True):
        header_col, close_col = st.columns([6, 1])
        with header_col:
            st.subheader("Analysis Results")
        with close_col:
            close_clicked = st.button("Close", icon=":material/close:")
        if close_clicked:
            del st.session_state["workflow_run"]
            st.rerun()

        state: WorkflowState | None = run_result["state"]
        log_lines: list[str] = run_result["log_lines"]
        parser_error: str | None = run_result["parser_error"]
        result_name: str = run_result["selected_name"]
        result_selected_task_ids: set[str] = run_result.get("selected_task_ids", set())

        if parser_error is not None:
            st.error(f"Could not read this PDF: {parser_error}")
        else:
            try:
                report = resolve_report_for_display(state)
            except ValueError as exc:
                message = str(exc)
                llm_error = state.get("llm_error")
                if llm_error:
                    message += f" (LLM Extraction Fallback also failed: {llm_error})"
                st.error(message)
            else:
                if state.get("extraction_method") == "llm":
                    st.warning(
                        "Extracted via **LLM Extraction Fallback** — this "
                        "treaty's format didn't match the regex extractor."
                    )
                ungrounded_fields = state.get("ungrounded_fields", [])
                if ungrounded_fields:
                    st.warning(
                        f"⚠️ {len(ungrounded_fields)} field(s) could not be "
                        f"verified against the cited source text: "
                        f"{', '.join(ungrounded_fields)}. Double-check these "
                        f"values before relying on this report."
                    )
                task_results: dict[str, TaskResult] = state.get("task_results", {})
                st.markdown(format_treaty_terms_markdown(report))
                extraction_cost = extract_llm_actual_cost(log_lines)
                extraction_note = format_extraction_cost_note(log_lines)
                if extraction_note:
                    st.caption(extraction_note)
                st.markdown(
                    format_combined_results_summary(
                        result_selected_task_ids, task_results, extraction_cost=extraction_cost or 0.0
                    )
                )
                for task_id in sorted(result_selected_task_ids):
                    with st.expander(_task_title(task_id), expanded=True):
                        task_result = task_results.get(task_id)
                        section_markdown = format_task_section_markdown(task_id, task_result, report)
                        findings = _task_findings_for_severity(task_id, task_result, report)
                        if findings is None:
                            st.markdown(section_markdown)
                        else:
                            _SEVERITY_STREAMLIT_CONTAINERS[highest_severity_label(findings)](section_markdown)

                format_choice = st.radio(
                    "Result file format",
                    ["Markdown (.md)", "PDF (.pdf)"],
                    horizontal=True,
                    key="results_format_choice",
                )
                extension = "pdf" if format_choice.startswith("PDF") else "md"

                save_col, download_col = st.columns(2)
                with save_col:
                    if st.button("Save analysis results", icon=":material/save:"):
                        saved_path = save_analysis_result_to_file(
                            report,
                            extension,
                            log_lines=log_lines,
                            selected_task_ids=result_selected_task_ids,
                            task_results=task_results,
                        )
                        st.success(f"Saved analysis results to {saved_path}.")
                with download_col:
                    # Streamlit Community Cloud's filesystem is ephemeral and
                    # has no file browser, so the server-side save above isn't
                    # actually retrievable in production -- this downloads the
                    # same content straight to the user's own machine instead,
                    # which works identically locally and in production.
                    # A single `when` for both the filename and the content, so
                    # they always agree even at a second boundary.
                    download_when = datetime.now()
                    st.download_button(
                        "Download analysis results",
                        data=render_report_bytes(
                            report,
                            extension,
                            log_lines=log_lines,
                            when=download_when,
                            selected_task_ids=result_selected_task_ids,
                            task_results=task_results,
                        ),
                        file_name=format_results_filename(report, extension, when=download_when),
                        mime="application/pdf" if extension == "pdf" else "text/markdown",
                        icon=":material/download:",
                    )

        with st.expander("Analysis Workflow execution"):
            if state is None:
                st.caption(
                    "No workflow state was produced — the PDF could not be "
                    "parsed, so no node ran."
                )
            else:
                st.caption(format_extraction_status(state))
            multi_task_status = format_multi_task_status(
                result_selected_task_ids, (state or {}).get("task_results", {})
            )
            st.markdown(multi_task_status)
            if log_lines:
                st.code("\n".join(log_lines), language="text")
            else:
                st.write("No log lines captured.")
            if state is not None:
                st.json(serialize_state_for_debug(state))

            debug_task_results = (state or {}).get("task_results", {})
            debug_format_choice = st.radio(
                "Debug report format",
                ["Text (.txt)", "JSON (.json)"],
                horizontal=True,
                key="debug_report_format_choice",
            )
            debug_extension = "json" if debug_format_choice.startswith("JSON") else "txt"
            debug_download_when = datetime.now()
            if debug_extension == "json":
                debug_report_data = json.dumps(
                    format_debug_report_json(
                        result_name,
                        state,
                        log_lines,
                        result_selected_task_ids,
                        debug_task_results,
                        when=debug_download_when,
                    ),
                    indent=2,
                ).encode("utf-8")
                debug_mime = "application/json"
            else:
                debug_report_data = format_debug_report_text(
                    result_name,
                    state,
                    log_lines,
                    result_selected_task_ids,
                    debug_task_results,
                    when=debug_download_when,
                ).encode("utf-8")
                debug_mime = "text/plain"
            st.download_button(
                "Download workflow execution details",
                data=debug_report_data,
                file_name=format_debug_report_filename(debug_extension, when=debug_download_when),
                mime=debug_mime,
                icon=":material/download:",
            )

            st.divider()
            with st.form("save_logs_form"):
                save_mode = st.segmented_control(
                    "Save mode",
                    ["Append", "Overwrite"],
                    default="Append",
                    required=True,
                    key="log_save_mode",
                )
                submitted = st.form_submit_button("Save to logs file", icon=":material/save:")
            if submitted:
                if log_lines:
                    header = format_log_header(result_name)
                    save_logs_to_file([header, multi_task_status, *log_lines, ""], mode=save_mode.lower())
                    st.success(f"Saved {len(log_lines)} log line(s) to {DEFAULT_LOG_FILE} ({save_mode.lower()}).")
                else:
                    st.warning("No log lines to save.")


if __name__ == "__main__":
    main()
