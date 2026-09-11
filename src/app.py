"""Streamlit UI / FastAPI endpoints."""

import hashlib
import logging
import re
import sys
import tempfile
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

from src.cost_estimation import estimate_task_cost
from src.domain_tasks import DOMAIN_TASKS
from src.models import AnomalyReport, TaskResult
from src.parser import ParserError, extract_treaty_sections
from src.sample_treaties import SAMPLE_TREATIES, get_sample_bytes
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


def _task_title(task_id: str) -> str:
    """The human-readable title for a domain task id, or the id itself
    if it's not (or no longer) in the DOMAIN_TASKS registry.
    """
    for task in DOMAIN_TASKS:
        if task.id == task_id:
            return task.title
    return task_id


def format_task_section_markdown(
    task_id: str, task_result: TaskResult | None, report: AnomalyReport | None
) -> str:
    """Markdown body for one selected task's own expandable results section.

    `burn_cost_check` is special-cased to reuse format_report_markdown()'s
    exact output (treaty terms, loss ratio, findings) since it's the only
    task that populates `report` today (see S3's decision in REASONING.md).
    Every other task renders generically from its own TaskResult, since
    that's all a future domain task will ever populate.
    """
    if task_id == "burn_cost_check" and report is not None:
        return format_report_markdown(report)

    if task_result is None:
        implemented_ids = {t.id for t in DOMAIN_TASKS if t.implementation_status == "implemented"}
        if task_id not in implemented_ids:
            return "_Not implemented yet._"
        return "_Did not run (extraction incomplete)._"

    if task_result.status != "ran":
        return f"_{task_result.status}._"

    lines = [f"**Cost:** ${task_result.cost:,.4f}  ·  **Latency:** {task_result.latency:.2f}s"]
    lines.append(f"\n### Findings ({len(task_result.findings)})")
    if not task_result.findings:
        lines.append("No anomalies found.")
    else:
        for finding in task_result.findings:
            icon = SEVERITY_ICONS.get(finding.severity, "")
            lines.append(f"- {icon} **[{finding.severity.upper()}]** {finding.description}")
    return "\n".join(lines)


def format_combined_results_summary(selected_task_ids: set[str], task_results: dict[str, TaskResult]) -> str:
    """Combined header shown above the per-task results sections: aggregate
    findings/cost across every task that ran, plus which selected tasks were
    skipped and why (not implemented, or extraction never reached them).
    """
    implemented_ids = {t.id for t in DOMAIN_TASKS if t.implementation_status == "implemented"}
    total_findings = 0
    total_cost = 0.0
    skipped_lines = []
    for task_id in sorted(selected_task_ids):
        result = task_results.get(task_id)
        if result is not None and result.status == "ran":
            total_findings += len(result.findings)
            total_cost += result.cost
        elif task_id not in implemented_ids:
            skipped_lines.append(f"- **{_task_title(task_id)}**: not implemented yet")
        else:
            skipped_lines.append(f"- **{_task_title(task_id)}**: did not run (extraction incomplete)")

    lines = [f"**{total_findings} finding(s)** across selected task(s) · **${total_cost:,.4f}** total actual cost"]
    if skipped_lines:
        lines.append("")
        lines.append("**Skipped:**")
        lines.extend(skipped_lines)
    return "\n".join(lines)


def format_report_markdown(report: AnomalyReport) -> str:
    """Render an AnomalyReport as a Markdown string, with page citations."""
    treaty = report.treaty
    citations = treaty.page_citations

    def cite(field: str) -> str:
        page = citations.get(field)
        return f" _(p. {page})_" if page is not None else ""

    lines = [
        f"### Treaty: {treaty.cedent_name}{cite('cedent_name')}",
        f"- **Attachment point:** {treaty.attachment_point:,.2f}{cite('attachment_point')}",
        f"- **Limit:** {treaty.limit:,.2f}{cite('limit')}",
        f"- **Reinsurance premium:** {treaty.reinsurance_premium:,.2f}{cite('reinsurance_premium')}",
    ]
    if treaty.exclusions:
        lines.append(f"- **Exclusions**{cite('exclusions')}: {', '.join(treaty.exclusions)}")

    lines.append(f"\n### Loss ratio: {report.loss_ratio:.2f}")
    lines.append(f"\n### Findings ({len(report.findings)})")
    if not report.findings:
        lines.append("No anomalies found.")
    else:
        for finding in report.findings:
            icon = SEVERITY_ICONS.get(finding.severity, "")
            lines.append(f"- {icon} **[{finding.severity.upper()}]** {finding.description}")

    return "\n".join(lines)


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
    report: AnomalyReport, log_lines: list[str] | None = None, when: datetime | None = None
) -> str:
    """format_report_markdown's content, for a saved/downloaded file: prefixed
    with an "Analysis Results" header (matching the on-screen container's own
    title), the run's generation timestamp, and (only if the LLM Extraction
    Fallback actually ran) its token usage -- none of these three are part of
    the on-screen report itself, which describes the treaty, not this run.
    """
    timestamp = (when or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
    lines = ["## Analysis Results", f"Generated: {timestamp}"]
    llm_usage = extract_llm_usage_summary(log_lines)
    if llm_usage:
        lines.append(f"LLM usage: {llm_usage}")
    lines.append("")
    lines.append(format_report_markdown(report))
    return "\n".join(lines)


def render_report_pdf(report: AnomalyReport, log_lines: list[str] | None = None, when: datetime | None = None) -> bytes:
    """Render an AnomalyReport as PDF bytes, mirroring format_results_document's content.

    Uses fpdf2's core (Latin-1-only) fonts, so this strips Markdown syntax
    and drops any character that can't be encoded (e.g. the severity emoji)
    rather than crashing -- the `[HIGH]`/`[MEDIUM]`/`[LOW]` label already
    carries that information in plain text.
    """
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    for raw_line in format_results_document(report, log_lines=log_lines, when=when).split("\n"):
        line = raw_line.strip()
        if not line:
            pdf.ln(4)
            continue
        is_heading = line.startswith("#")
        line = re.sub(r"^#+\s*", "", line)
        line = line.replace("**", "")
        line = line.replace("_(", "(").replace(")_", ")")
        line = line.encode("latin-1", "ignore").decode("latin-1")
        line = re.sub(r"\s+", " ", line).strip()
        if not line:
            continue
        pdf.set_font("Helvetica", style="B" if is_heading else "", size=13 if is_heading else 11)
        # multi_cell defaults to leaving the cursor at the right edge of the
        # last rendered line (new_x="RIGHT") rather than the next line's left
        # margin -- without resetting it, the next call gets ~0 width and
        # raises "Not enough horizontal space to render a single character".
        pdf.multi_cell(0, 7, line, new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())


def render_report_bytes(
    report: AnomalyReport, extension: str, log_lines: list[str] | None = None, when: datetime | None = None
) -> bytes:
    """Render report as bytes in the given format ("md" or "pdf")."""
    if extension == "pdf":
        return render_report_pdf(report, log_lines=log_lines, when=when)
    return format_results_document(report, log_lines=log_lines, when=when).encode("utf-8")


def save_analysis_result_to_file(
    report: AnomalyReport,
    extension: str,
    log_lines: list[str] | None = None,
    directory: Path = DEFAULT_RESULTS_DIR,
    when: datetime | None = None,
) -> Path:
    """Write report to a new timestamped file (under a per-treaty subdirectory
    of directory) in the given format, returning its path.
    """
    when = when or datetime.now()
    target_dir = results_subdirectory(report, directory)
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / format_results_filename(report, extension, when=when)
    path.write_bytes(render_report_bytes(report, extension, log_lines=log_lines, when=when))
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


def main() -> None:
    st.set_page_config(page_title="Reinsurance Treaty Agent", page_icon="📄")
    _inject_wide_main_container_css()
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

    review_clicked = st.button("Review treaty", disabled=not has_selection)
    if review_clicked and selected_bytes is not None and selected_name is not None:
        _show_review_dialog(selected_bytes, selected_name)

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
                report = extract_report(state)
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
                st.markdown(format_combined_results_summary(result_selected_task_ids, task_results))
                for task_id in sorted(result_selected_task_ids):
                    with st.expander(_task_title(task_id), expanded=True):
                        st.markdown(format_task_section_markdown(task_id, task_results.get(task_id), report))

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
                        saved_path = save_analysis_result_to_file(report, extension, log_lines=log_lines)
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
                        data=render_report_bytes(report, extension, log_lines=log_lines, when=download_when),
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
