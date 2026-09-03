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
     policy: A scheduled cloud routine checks github.com/tasksmd/tasks.md for new releases roughly every second Monday; see AGENTS.md "Keeping tasks.md tooling current". -->

<!-- Recently completed (2026-08-13):
     ✅
     See REASONING.md for detailed decision logs. -->

## P0

<!-- policy: P0 tasks are critical, urgent, blocks other work. Tasks that should ship ASAP. -->


## P1

<!-- policy: P1 tasks are core work that should ship. Default for planned features and important improvements. -->

- [ ] Spec-First Development & File Structure
  - **ID**: spec-first-file-structure
  - **Tags**: scaffolding, architecture
  - **Details**: Create the modular architecture below so the codebase is
    clean, testable, and agent-friendly:
    ```
    reinsurance-treaty-agent/
    │
    ├── data/                  # Sample PDF treaty contracts & mock historical claims CSV
    ├── src/
    │   ├── __init__.py
    │   ├── models.py          # Pydantic data schemas (TreatyTerms, ClaimsData, AnomalyReport)
    │   ├── parser.py          # PDF ingestion and text extraction
    │   ├── tools.py           # Deterministic tools (database query, math calculators)
    │   ├── workflow.py        # LangGraph state machine & agent logic
    │   └── app.py             # Streamlit UI / FastAPI endpoints
    ├── tests/
    │   ├── test_parser.py
    │   └── test_workflow.py
    ```
  - **Files**: `data/`, `src/__init__.py`, `src/models.py`, `src/parser.py`, `src/tools.py`, `src/workflow.py`, `src/app.py`, `tests/test_parser.py`, `tests/test_workflow.py`
  - **Acceptance**: All listed directories/files exist with appropriate
    stub content (module docstrings/placeholders where logic isn't
    implemented yet); `src/__init__.py` makes `src` importable; test files
    are discoverable by pytest.


## P2

<!-- policy: P2 tasks are valuable but not blocking. Do after P0 and P1 are clear. -->


## P3

<!-- policy: P3 tasks are "someday/maybe". Kept for reference, not actively worked. -->


