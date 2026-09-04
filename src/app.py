"""Streamlit UI / FastAPI endpoints."""

import logging
import tempfile
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import streamlit as st

from src.models import AnomalyReport
from src.parser import ParserError
from src.workflow import WorkflowState, run_workflow_from_pdf

SEVERITY_ICONS = {"low": "ℹ️", "medium": "⚠️", "high": "🚨"}
DEFAULT_LOG_FILE = Path("logs/workflow.log")


class _ListLogHandler(logging.Handler):
    """Captures formatted log records into a plain list for on-page display."""

    def __init__(self, sink: list[str]):
        super().__init__()
        self.sink = sink
        self.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))

    def emit(self, record: logging.LogRecord) -> None:
        self.sink.append(self.format(record))


def run_workflow_on_bytes(file_bytes: bytes) -> WorkflowState:
    """Write the uploaded bytes to a temp file and run the full agent workflow on them.

    Raises ParserError if the PDF cannot be read or has no extractable text.
    """
    with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
        tmp.write(file_bytes)
        tmp.flush()
        return run_workflow_from_pdf(Path(tmp.name))


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
        "claims": [claim.model_dump(mode="json") for claim in state.get("claims", [])],
        "complete": state.get("complete", False),
        "report": report.model_dump(mode="json") if (report := state.get("report")) else None,
    }


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


def main() -> None:
    st.set_page_config(page_title="Reinsurance Treaty Agent", page_icon="📄")
    st.title("Reinsurance Treaty Agent")
    st.write(
        "Upload a treaty PDF to extract its terms, compare them against "
        "historical claims, and flag anomalies."
    )

    uploaded_file = st.file_uploader("Treaty PDF", type="pdf")
    if uploaded_file is None:
        return

    log_lines: list[str] = []
    handler = _ListLogHandler(log_lines)
    workflow_logger = logging.getLogger("src.workflow")
    workflow_logger.addHandler(handler)
    workflow_logger.setLevel(logging.INFO)

    state: WorkflowState | None = None
    try:
        with st.spinner("Running agent workflow..."):
            try:
                state = run_workflow_on_bytes(uploaded_file.getvalue())
            except ParserError as exc:
                st.error(f"Could not read this PDF: {exc}")
            else:
                try:
                    report = extract_report(state)
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.markdown(format_report_markdown(report))
    finally:
        workflow_logger.removeHandler(handler)

    with st.expander("Debug: workflow execution"):
        st.caption(
            "This workflow has no LLM calls — extraction is regex-based, so "
            "there is no LLM usage/cost to report here, only the deterministic "
            "Extractor → Verifier → Analyst node steps below."
        )
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
            submitted = st.form_submit_button("Save logs to file", icon=":material/save:")
        if submitted:
            if log_lines:
                header = format_log_header(uploaded_file.name)
                save_logs_to_file([header, *log_lines, ""], mode=save_mode.lower())
                st.success(f"Saved {len(log_lines)} log line(s) to {DEFAULT_LOG_FILE} ({save_mode.lower()}).")
            else:
                st.warning("No log lines to save.")


if __name__ == "__main__":
    main()
