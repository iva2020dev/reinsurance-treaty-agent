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
     ✅ 2026-09-05 15:37:13 Build the Fuzzy Treaty Fixture (build-fuzzy-treaty-fixture)
     ✅ 2026-09-05 16:30:02 Implement the LLM Extraction Fallback Node (implement-llm-fallback-node)
     ✅ 2026-09-06 14:03:25 Surface LLM Extraction Fallback Status in the UI (update-ui-llm-fallback)
     ✅ 2026-09-06 14:11:27 End-to-End Test the Hybrid Flow and Document Deployment Config (integration-test-llm-fallback-deploy-config)
     ✅ 2026-09-06 15:14:46 Retry/Backoff Resilience for the LLM Call (llm-fallback-retry-backoff)
     ✅ 2026-09-06 15:29:45 Grounding/Assurance Check on LLM Output (llm-fallback-grounding-check)
     ✅ 2026-09-06 16:05:00 Extraction Accuracy Eval Suite (Golden Dataset) (extraction-accuracy-eval-suite)
     ✅ 2026-09-08 12:15:00 Tag Extraction Accuracy Eval Suite Pattern as 🔧 Harness (repo-agnostic) (tag-eval-suite-harness)
     ✅ 2026-09-08 12:20:00 Sync CANDIDATE_TASKS.md's Harness statuses with TASKS.md (sync-candidate-tasks-harness-status)
     ✅ 2026-09-08 13:00:00 Remove leftover "Radius" template content (remove-radius-template-leftovers)
     ✅ 2026-09-09 12:55:13 Treaty Sample Selection UI (prepared/golden samples, no local disk) (treaty-sample-selection-ui)
     ✅ 2026-09-09 13:42:47 Fix treaty-source input layout twitch on source toggle (fix-source-input-height-twitch)
     See REASONING.md for detailed decision logs. -->

## P0

<!-- policy: P0 tasks are critical, urgent, blocks other work. Tasks that should ship ASAP. -->

## P1

<!-- policy: P1 tasks are core work that should ship. Default for planned features and important improvements. -->

- [ ] Auto-clear Analysis Results when a new treaty is selected (@claude)
  - **ID**: auto-clear-results-on-new-selection
  - **Tags**: ui, streamlit, ux
  - **Candidate ID**: N/A (not graduated from `CANDIDATE_TASKS.md`;
    a small follow-up UX fix on `treaty-sample-selection-ui`'s
    already-shipped results container, requested directly)
  - **Details**: Today, once "Analyze" produces a result, the bordered
    "Analysis Results" container (`st.session_state["workflow_run"]`)
    stays visible until the user explicitly clicks "Close" or
    "Analyze" again — if they instead pick a *different* treaty
    (upload a new file, choose a different sample, clear the upload,
    or switch source mode) without re-clicking "Analyze", the
    container keeps showing the stale prior report, now describing a
    document that's no longer selected. Auto-clear (and effectively
    auto-close) the results container as soon as the current selection
    no longer matches the one the shown result was produced from.
  - **Files**: `src/app.py`
  - **Acceptance**: After analyzing one treaty, uploading a different
    file, choosing a different sample, or switching source mode (all
    without clicking "Analyze" again) immediately hides the results
    container; `python -m pytest -q` passes with new coverage for
    both cases.

- [ ] Save analysis results to a file (@claude)
  - **ID**: save-analysis-results-to-file
  - **Tags**: ui, streamlit, ux
  - **Candidate ID**: N/A (not graduated from `CANDIDATE_TASKS.md`;
    a small follow-up feature on `treaty-sample-selection-ui`'s
    already-shipped results container, requested directly)
  - **Details**: Add a "Save analysis results" button next to the
    rendered report (inside the "Analysis Results" container, only
    when a report was actually produced) that writes the same
    Markdown rendering shown on screen (`format_report_markdown`) to a
    new file under `results/` (new dir, gitignored like `logs/`).
    Filename naming rule, confirmed with the human: `<datetime
    stamp>_<treaty short name>_<highest severity>.md`, e.g.
    `20260909_140530_acme_insurance_co_high.md` — datetime as
    `YYYYmmdd_HHMMSS` (filesystem-safe, no colons), the cedent name
    slugified (lowercased, non-alphanumeric runs collapsed to `_`,
    truncated to 40 chars), and the highest-severity finding's label
    (`low`/`medium`/`high`, or `clean` if there are no findings) so a
    folder of saved reports can be scanned for risk at a glance. Each
    save always creates a new file (no append/overwrite choice, unlike
    the existing "Save to logs file" control) — timestamped to the
    second, so collisions are effectively impossible in normal use.
    Also add a "Download analysis results" button (`st.download_button`)
    right beside it, offering the same Markdown content/filename as a
    browser download — needed because Streamlit Community Cloud's
    filesystem is ephemeral with no file browser, so the server-side
    save alone isn't actually retrievable by a user in production; the
    download button works identically local and in production since it
    streams straight to the user's own machine.
  - **Files**: `src/app.py`, `.gitignore` (new `results/` entry)
  - **Acceptance**: After a successful analysis, clicking "Save
    analysis results" writes a new file under `results/` named per the
    rule above and shows a success message naming the saved path;
    clicking "Download analysis results" downloads the same content to
    the browser; `python -m pytest -q` passes with new unit tests for
    the naming/slugify/severity helpers and app-level tests confirming
    both buttons work.


- [ ] CI-Integrated Regression Eval Gate
  - **ID**: extraction-eval-ci-gate
  - **Tags**: ci, evaluation, extraction, llm
  - **Candidate ID**: A4 (`CANDIDATE_TASKS.md`)
  - **Blocked by**: extraction-accuracy-eval-suite
  - **Details**: Graduated from `CANDIDATE_TASKS.md` (`A4`, Priority 4
    of 10 in the Harness list). Run `extraction-accuracy-eval-suite`'s
    scorer automatically in CI (GitHub Actions) so a prompt/model/
    schema change that regresses extraction accuracy below an agreed
    threshold fails the build rather than shipping unnoticed. Needs a
    real `ANTHROPIC_API_KEY` available in CI to exercise the LLM path
    — this repo's CI currently lacks that secret (same gap tracked
    separately in the P2 `fix-claude-review-ci-secret` admin task,
    which also requires repo admin access this agent doesn't have).
  - **Files**: `.github/workflows/` (new or modified workflow),
    `README.md`
  - **Acceptance**: A CI run on a PR that regresses extraction
    accuracy below the agreed threshold fails the build with a clear
    message; a PR that doesn't regress passes.


## P2

<!-- policy: P2 tasks are valuable but not blocking. Do after P0 and P1 are clear. -->

- [ ] Fix Claude Code Review CI Check (missing API key secret)
  - **ID**: fix-claude-review-ci-secret
  - **Tags**: ci, github-actions, maintenance
  - **Candidate ID**: N/A (not graduated from `CANDIDATE_TASKS.md`;
    found directly while working another task)
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


