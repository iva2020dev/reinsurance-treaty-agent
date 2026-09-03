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
     See REASONING.md for detailed decision logs. -->

## P0

<!-- policy: P0 tasks are critical, urgent, blocks other work. Tasks that should ship ASAP. -->


## P1

<!-- policy: P1 tasks are core work that should ship. Default for planned features and important improvements. -->

- [ ] Build PDF Ingestion & Parsing (@claude)
  - **ID**: build-pdf-ingestion-parsing
  - **Tags**: parsing, pdf
  - **Details**: Write a robust utility in `src/parser.py` using `pypdf`
    or a layout extractor to ingest a treaty PDF, extract text by page,
    and return structured sections with page citations.
  - **Files**: `src/parser.py`, `data/sample_treaty.pdf`, `data/sample_treaty_parsed.json`, `tests/test_parser.py`
  - **Acceptance**: Given a sample treaty PDF in `data/`, the parser
    returns structured text sections each tagged with the source page
    number; malformed/unreadable PDFs raise a clear, catchable error.
  - **Status**: Implemented and verified, including real
    `tests/test_parser.py` coverage (see REASONING.md, 2026-09-03
    12:26:10 and 12:49:35) — awaiting human approval before closing.
    See PR #5.

- [ ] Implement Deterministic Tools
  - **ID**: implement-deterministic-tools
  - **Tags**: tools, business-logic
  - **Details**: Build Python functions in `src/tools.py` that the agent
    can call: `query_historical_claims(cedent_name: str)` (reads a local
    mock CSV of past claims) and `calculate_loss_ratio(attachment_point:
    float, limit: float, claims: list)` (deterministic math, no LLM calls).
  - **Files**: `src/tools.py`, `data/`
  - **Acceptance**: `query_historical_claims` returns claims for a known
    cedent from the mock CSV (empty list for unknown cedents);
    `calculate_loss_ratio` returns a correct, deterministic ratio for
    known inputs and is covered by unit tests.

- [ ] Build the Agentic Workflow Graph
  - **ID**: build-agentic-workflow-graph
  - **Tags**: workflow, langgraph, agent
  - **Details**: Implement a LangGraph state machine in `src/workflow.py`
    with: an **Extractor Node** (extracts terms from parsed text against
    `src/models.py` schemas), a **Verifier Node** (validates completeness
    and triggers tool calls for historical claims), and an **Analyst
    Node** (compares treaty terms against historical data and flags
    anomalies).
  - **Files**: `src/workflow.py`
  - **Acceptance**: Running the graph end-to-end on parsed treaty text
    produces a populated `AnomalyReport`; each node's output is validated
    against its Pydantic schema before advancing to the next node.
  - **Blocked by**: build-pdf-ingestion-parsing, implement-deterministic-tools

- [ ] Write Unit Tests
  - **ID**: write-unit-tests
  - **Tags**: testing
  - **Details**: Write pytest test suites verifying schema validation
    (`src/models.py`), tool calculations (`src/tools.py`), and parser
    error handling (`src/parser.py`), extending `tests/test_parser.py`
    and adding coverage alongside `tests/test_workflow.py`.
  - **Files**: `tests/test_parser.py`, `tests/test_workflow.py`, `tests/`
  - **Acceptance**: `pytest tests/` passes and covers at least: one
    invalid-input case per schema, `calculate_loss_ratio` with known
    inputs/expected output, and the parser's behavior on a malformed PDF.
  - **Blocked by**: build-pdf-ingestion-parsing, implement-deterministic-tools, build-agentic-workflow-graph

- [ ] Create User Interface & API
  - **ID**: create-ui-api
  - **Tags**: ui, streamlit, api
  - **Details**: Build a clean Streamlit UI in `src/app.py` where a user
    can upload a mock treaty PDF, run the agent workflow in real-time,
    and view the structured anomaly report with page citations.
  - **Files**: `src/app.py`
  - **Acceptance**: Uploading a sample treaty PDF through the running
    Streamlit app triggers the full workflow and renders the resulting
    `AnomalyReport` (including page citations) in the UI without errors.
  - **Blocked by**: build-agentic-workflow-graph


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


