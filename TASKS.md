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
     ✅ 2026-09-04 16:10:50 Create User Interface & API (create-ui-api)
     ✅ 2026-09-04 19:02:30 Deploy to Production / Cloud (deploy-to-production)
     See REASONING.md for detailed decision logs. -->

## P0

<!-- policy: P0 tasks are critical, urgent, blocks other work. Tasks that should ship ASAP. -->


## P1

<!-- policy: P1 tasks are core work that should ship. Default for planned features and important improvements. -->


## P2

<!-- policy: P2 tasks are valuable but not blocking. Do after P0 and P1 are clear. -->

- [ ] Fix Claude Code Review CI Check (missing API key secret)
  - **ID**: fix-claude-review-ci-secret
  - **Tags**: ci, github-actions, maintenance
  - **Details**: The `claude-review` GitHub Actions workflow
    (`Claude Code Review`) fails on every PR with: "Environment variable
    validation failed: Either ANTHROPIC_API_KEY, CLAUDE_CODE_OAUTH_TOKEN,
    or workload identity federation ... is required when using direct
    Anthropic API." The workflow needs a valid `ANTHROPIC_API_KEY` (or
    `CLAUDE_CODE_OAUTH_TOKEN`) configured as a GitHub Actions secret for
    this repo (Settings → Secrets and variables → Actions) — this
    requires repo admin access and can't be done by an agent from a
    local checkout. Confirmed failing on PR #14 and PR #15
    (2026-09-04), both with the identical error, so this isn't specific
    to either PR's diff.
  - **Files**: (none in-repo — GitHub repo Settings, and possibly the
    `claude-review` workflow file under `.github/workflows/` if it also
    needs a config change once the secret exists)
  - **Acceptance**: A new commit pushed to an open PR triggers the
    `Claude Code Review` check and it completes with a real review
    comment posted (summary/bugs/security/suggestions), not an
    environment-variable validation failure.


## P3

<!-- policy: P3 tasks are "someday/maybe". Kept for reference, not actively worked. -->

- [ ] Explore a Hybrid Regex+LLM Extraction Fallback
  - **ID**: explore-hybrid-regex-llm-fallback
  - **Tags**: research, extraction, llm
  - **Description**: The Extractor Node (`extract_treaty_terms()` in
    `src/workflow.py`) is currently pure regex, matching only the
    `Label: value` convention the two mock fixtures use (see
    `build-agentic-workflow-graph`'s decision in REASONING.md) — it
    extracts nothing from real-world treaty prose, synonyms, or
    reordered clauses. Add a hybrid fallback: try the existing regex
    extractor first (free, deterministic, fully testable), and only
    call an LLM when regex fails to find one or more required fields —
    keeping the cost/determinism/auditability benefits of regex for
    well-formed documents while gaining real-world robustness for
    messier ones.
  - **Plan**:
    1. **Fuzzy fixture**: hand-roll `data/sample_rich_fuzzy_treaty.pdf`
       (raw PDF bytes, same technique as the existing two fixtures —
       no PDF-writing library is installed) — same substantive facts
       as a real treaty (cedent **Sentinel Mutual Assurance**, already
       in `data/historical_claims.csv` with one $900,000 claim but
       unused by either existing fixture; an attachment point/limit/
       premium; exclusions), but phrased as natural prose across pages
       instead of `Label: value` lines, so `_FIELD_PATTERNS` matches
       nothing and `extract_treaty_terms()` reports `missing_fields`
       for at least one required field. Add a companion
       `sample_rich_fuzzy_treaty_parsed.json` (matching the existing
       fixture convention) and a README table row.
    2. **LLM fallback node**: add a new LangGraph node,
       `llm_fallback_extractor`, wired in only when the regex
       extractor's `missing_fields` is non-empty (a conditional edge
       after `extractor`, mirroring the existing
       `_route_after_verifier` pattern) — not folded into
       `extractor_node` itself, so the workflow graph diagram and the
       debug panel's per-node logs can show plainly whether a run used
       regex only or needed the fallback.
       - **Model**: Claude **Haiku 4.5** (`claude-haiku-4-5-20251001`)
         — the current lightweight/cheap/fast tier, matching "compact,
         modern, good performance, not expensive." Not Sonnet/Opus
         (overkill and slower/pricier for a structured short-document
         extraction task).
       - **Structured output**: use Anthropic tool-use (forced
         `tool_choice`) with a tool schema mirroring `TreatyTerms`
         (including per-field page citations), not free-text parsing —
         matches the existing `page_citations` dict shape.
       - **Input**: the same `PageSection` text already extracted by
         `pypdf` — no OCR/vision needed for *this* failure mode, since
         the fixture has fully extractable text, just non-conforming
         phrasing. True scanned/image-only PDFs are a different
         failure mode (`pypdf` itself raises `ParserError` before
         extraction) and would need a separate OCR/vision-based path —
         explicitly out of scope here; a natural follow-on task.
       - **Safety**: wrap the API call with a timeout and catch
         auth/rate-limit/network errors — on any failure (including a
         missing `ANTHROPIC_API_KEY`), log it and fall through to the
         existing "incomplete" path (`treaty=None`, original regex
         `missing_fields`) rather than crashing the run.
    3. **State/contract**: extend `WorkflowState` with
       `extraction_method: Literal["regex", "llm", "none"]` (and an
       optional `llm_error: str | None`) so both intermediate (what
       regex found before falling back) and final results stay
       visible in the debug panel — `extractor_node`'s own return
       contract (`TreatyTerms | None` + `missing_fields`) stays
       unchanged.
    4. **UI**: in `src/app.py`, show a clear on-page note when
       `extraction_method == "llm"` (e.g. "Extracted via LLM fallback
       — this treaty's format didn't match the regex extractor"), and
       have the new node log through the existing `"src.workflow"`
       logger so it shows up in the debug panel's log view and JSON
       state for free — same pattern as the existing three nodes, no
       new logging plumbing needed.
    5. **Config**: load `ANTHROPIC_API_KEY` via `python-dotenv`
       locally (already pinned, unused today); once this ships,
       document adding it as a Streamlit Community Cloud secret for
       the deployed app, and confirm the app still works (regex-only,
       no crash) for anyone without the key configured.
    6. **Tests**: a unit test for the new node/helper (mock the
       Anthropic client — no real API calls in CI), plus one true
       end-to-end integration test using the real
       `sample_rich_fuzzy_treaty.pdf` fixture and a real API call
       (skipped/xfail if no API key is present in the environment).
  - **Files**: `src/workflow.py`, `src/app.py`, `src/models.py`
    (`WorkflowState`/schema additions only, no `TreatyTerms` contract
    break), `data/sample_rich_fuzzy_treaty.pdf` (+ `.json` sibling),
    `tests/test_workflow.py`, `tests/test_integration.py`,
    `tests/test_app.py`, `README.md`, `requirements.txt`
    (`python-dotenv` load call).
  - **Acceptance**: Uploading `sample_rich_fuzzy_treaty.pdf` through
    the app triggers the LLM fallback (regex alone reports missing
    fields), the UI clearly indicates the fallback was used, the debug
    panel shows both the regex attempt and the LLM result, and the
    final `AnomalyReport` is produced correctly for cedent Sentinel
    Mutual Assurance. Regex-only behavior on the two existing
    fixtures is unchanged. The app still runs (regex-only, informative
    log/UI note) if `ANTHROPIC_API_KEY` is absent.


