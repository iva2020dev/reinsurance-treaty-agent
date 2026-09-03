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
     See REASONING.md for detailed decision logs. -->

## P0

<!-- policy: P0 tasks are critical, urgent, blocks other work. Tasks that should ship ASAP. -->


## P1

<!-- policy: P1 tasks are core work that should ship. Default for planned features and important improvements. -->

- [ ] Implement Deterministic Tools
  - **ID**: implement-deterministic-tools
  - **Tags**: tools, business-logic, testing
  - **Details**: Build Python functions in `src/tools.py` that the agent
    can call: `query_historical_claims(cedent_name: str)` (reads a local
    mock CSV of past claims) and `calculate_loss_ratio(attachment_point:
    float, limit: float, claims: list)` (deterministic math, no LLM calls).
    Add a mock historical-claims CSV under `data/` for
    `query_historical_claims` to read. Write unit tests covering both
    functions as part of this task (do not defer to a separate testing
    task).
  - **Files**: `src/tools.py`, `data/` (mock claims CSV), `tests/test_tools.py`
  - **Acceptance**: `query_historical_claims` returns claims for a known
    cedent from the mock CSV, and an empty list for an unknown cedent;
    `calculate_loss_ratio` returns a correct, deterministic ratio for
    known inputs. `pytest tests/test_tools.py` passes and covers: a known
    cedent, an unknown cedent (empty list), `calculate_loss_ratio` with a
    known expected result, and at least one edge case (e.g. an empty
    claims list).

- [ ] Build the Agentic Workflow Graph
  - **ID**: build-agentic-workflow-graph
  - **Tags**: workflow, langgraph, agent, testing
  - **Details**: Implement a LangGraph state machine in `src/workflow.py`
    with: an **Extractor Node** (extracts terms from parsed text against
    `src/models.py` schemas), a **Verifier Node** (validates completeness
    and triggers tool calls for historical claims), and an **Analyst
    Node** (compares treaty terms against historical data and flags
    anomalies). Write unit tests for each node as part of this task (do
    not defer to a separate testing task).
  - **Files**: `src/workflow.py`, `tests/test_workflow.py`
  - **Acceptance**: Running the graph end-to-end on parsed treaty text
    produces a populated `AnomalyReport`; each node's output is validated
    against its Pydantic schema before advancing to the next node.
    `pytest tests/test_workflow.py` passes and covers, per node in
    isolation: the Extractor Node on well-formed input; the Verifier Node
    both when required data is complete and when it is missing/incomplete
    (triggers the historical-claims tool call / flags incompleteness); and
    the Analyst Node both when it finds no anomalies and when it flags at
    least one.
  - **Blocked by**: implement-deterministic-tools

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
  - **Blocked by**: build-agentic-workflow-graph

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
  - **Blocked by**: build-agentic-workflow-graph, write-integration-tests


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


