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
     policy: If the human adds or changes actions within an in-progress task, update that task's entry here (Files/Details/Status) to match, and log the change as a dated update in REASONING.md — see AGENTS.md "Mandatory Workflow". -->

<!-- Recently completed:
     ✅ 2026-09-03 11:52:52 Spec-First Development & File Structure (spec-first-file-structure)
     ✅ 2026-09-03 12:15:09 Define Core Data Schemas (define-core-data-schemas)
     ✅ 2026-09-03 13:19:12 Build PDF Ingestion & Parsing (build-pdf-ingestion-parsing)
     ✅ 2026-09-03 17:47:28 Implement Deterministic Tools (implement-deterministic-tools)
     ✅ 2026-09-03 18:44:29 Build the Agentic Workflow Graph (build-agentic-workflow-graph)
     See REASONING.md for detailed decision logs. -->

## P0

<!-- policy: P0 tasks are critical, urgent, blocks other work. Tasks that should ship ASAP. -->


## P1

<!-- policy: P1 tasks are core work that should ship. Default for planned features and important improvements. -->

- [ ] Write Integration Tests for End-to-End Workflow
  - **ID**: write-integration-tests
  - **Tags**: testing, integration
  - **Details**: Write integration tests exercising the full pipeline —
    parse a treaty PDF, extract terms, query historical claims, calculate
    the loss ratio, and produce the final `AnomalyReport` — as a single
    run through `src/workflow.py`, using the real `data/sample_treaty.pdf`
    and `data/sample_rich_treaty.pdf` fixtures rather than mocking
    individual nodes. Cover both success and failure paths end-to-end.
  - **Files**: `tests/test_integration.py`
  - **Acceptance**: `pytest tests/test_integration.py` passes and covers
    at least: (1) success — a full run on `sample_treaty.pdf` and on
    `sample_rich_treaty.pdf` each produces a valid `AnomalyReport`; (2)
    failure — a malformed/unreadable PDF fails the run with a clear,
    caught error rather than an unhandled exception; (3) failure — a
    cedent with no historical claims data is handled gracefully (e.g. an
    empty-claims `AnomalyReport` or an explicit flagged finding, not a
    crash); (4) failure — treaty text missing a required term (e.g. no
    extractable limit) is handled gracefully rather than crashing.

- [ ] Create User Interface & API
  - **ID**: create-ui-api
  - **Tags**: ui, streamlit, api, testing
  - **Details**: Build a clean Streamlit UI in `src/app.py` where a user
    can upload a mock treaty PDF, run the agent workflow in real-time,
    and view the structured anomaly report with page citations. Write
    unit tests for the app as part of this task (do not defer to a
    separate testing task), e.g. using `streamlit.testing.v1.AppTest` or
    by testing any extracted helper functions (e.g. report formatting)
    directly.
  - **Files**: `src/app.py`, `tests/test_app.py`
  - **Acceptance**: Uploading a sample treaty PDF through the running
    Streamlit app triggers the full workflow and renders the resulting
    `AnomalyReport` (including page citations) in the UI without errors.
    `pytest tests/test_app.py` passes and covers at least one successful
    upload-and-render run and one failure case (e.g. uploading a
    malformed PDF) surfacing a clear error in the UI instead of crashing.
  - **Blocked by**: write-integration-tests


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


