# Tasks

<!-- policy: ALWAYS use TASKS.md for task tracking. Never skip this step.
     policy: ALWAYS document reasoning in REASONING.md for every task before, during, and after work.
     policy: Run tests before every commit where applicable.
     policy: Use comments sparingly - only for complex logic.
     policy: Follow TypeScript strict mode and Zod validation at API boundaries.
     policy: Keep the codebase maintainable and well-documented in CLAUDE.md.
     policy: Before building ANY new feature, check if an upstream tool already does this.
     policy: Prefer fixing root causes over symptoms.
     policy: Review AGENTS.md and CLAUDE.md before starting any work.
     policy: A scheduled cloud routine checks github.com/tasksmd/tasks.md for new releases roughly every second Monday; see AGENTS.md "Keeping tasks.md tooling current".
     policy: Every dated entry here and in REASONING.md MUST include time as YYYY-MM-DD HH:MM:SS (24h) — see AGENTS.md "Timestamp Format".
     policy: NEVER mark a task done or remove it from this file without explicit human approval first. Present the verified work and wait.
     policy: Every task-closing PR (removing an approved-done task from this file) MUST be titled exactly `Closing task as "Done": <task title>` — see AGENTS.md "Mandatory Workflow".
     policy: If the human adds or changes actions within an in-progress task, update that task's entry here (Files/Details/Status) to match, and log the change as a dated update in REASONING.md — see AGENTS.md "Mandatory Workflow". -->

<!-- Recently completed:
     ✅ 2026-09-03 11:52:52 Spec-First Development & File Structure (spec-first-file-structure)
     ✅ 2026-09-03 12:15:09 Define Core Data Schemas (define-core-data-schemas)
     ✅ 2026-09-03 13:19:12 Build PDF Ingestion & Parsing (build-pdf-ingestion-parsing)
     ✅ 2026-09-03 17:47:28 Implement Deterministic Tools (implement-deterministic-tools)
     ✅ 2026-09-03 18:44:29 Build the Agentic Workflow Graph (build-agentic-workflow-graph)
     ✅ 2026-09-03 19:18:42 Write Integration Tests for End-to-End Workflow (write-integration-tests)
     See REASONING.md for detailed decision logs. -->

## P0

<!-- policy: P0 tasks are critical, urgent, blocks other work. Tasks that should ship ASAP. -->


## P1

<!-- policy: P1 tasks are core work that should ship. Default for planned features and important improvements. -->

- [ ] Create User Interface & API (@claude)
  - **ID**: create-ui-api
  - **Tags**: ui, streamlit, api, testing
  - **Details**: Build a clean Streamlit UI in `src/app.py` where a user
    can upload a mock treaty PDF, run the agent workflow in real-time,
    and view the structured anomaly report with page citations. Write
    unit tests for the app as part of this task (do not defer to a
    separate testing task), e.g. using `streamlit.testing.v1.AppTest` or
    by testing any extracted helper functions (e.g. report formatting)
    directly. Also surface workflow execution visibility: log each
    node's run (Extractor/Verifier/Analyst) via the standard `logging`
    module, and show those log lines plus the raw `WorkflowState` in a
    collapsible debug panel in the UI. (Note: this workflow has no LLM
    calls — extraction is regex-based per `build-agentic-workflow-graph`
    — so there is no LLM-usage/cost logging to add; the debug panel
    should say so rather than imply LLM calls happen.) In that debug
    panel, also let the user persist the current run's log lines to a
    default log file on disk (`logs/workflow.log`), with an explicit
    choice each time between appending to the existing file content or
    clearing it and writing only this run's logs. Each saved block is
    prefixed with a header line (run date/time, uploaded file name).
  - **Files**: `src/app.py`, `src/workflow.py`, `tests/test_app.py`
  - **Acceptance**: Uploading a sample treaty PDF through the running
    Streamlit app triggers the full workflow and renders the resulting
    `AnomalyReport` (including page citations) in the UI without errors.
    A debug panel shows per-node log lines and the raw workflow state
    for both a successful run and a failed one, plus a save control that
    lets the user choose append vs. overwrite before writing the
    current run's logs to `logs/workflow.log`. `pytest tests/test_app.py`
    passes and covers at least one successful upload-and-render run and
    one failure case (e.g. uploading a malformed PDF) surfacing a clear
    error in the UI instead of crashing, plus the append/overwrite save
    behavior.


## P2

<!-- policy: P2 tasks are valuable but not blocking. Do after P0 and P1 are clear. -->

- [ ] Deploy to Production / Cloud
  - **ID**: deploy-to-production
  - **Tags**: deployment, ops
  - **Details**: Deploy the Streamlit app (`src/app.py`) to Streamlit
    Community Cloud (free) or Render/Hugging Face Spaces so it has a
    live public URL for the portfolio.
  - **Files**: `src/app.py`, `requirements.txt`
  - **Acceptance**: A live public URL serves the deployed app; uploading
    a sample treaty PDF there runs the full workflow and renders an
    anomaly report, matching local behavior.
  - **Blocked by**: create-ui-api


## P3

<!-- policy: P3 tasks are "someday/maybe". Kept for reference, not actively worked. -->


