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
     ✅ 2026-09-09 16:36:48 Save analysis results to a file (save-analysis-results-to-file)
     ✅ 2026-09-09 16:48:06 Auto-clear Analysis Results when a new treaty is selected (auto-clear-results-on-new-selection)
     ✅ 2026-09-09 17:08:35 Add Multi Domain-Task Selection (S) candidates to CANDIDATE_TASKS.md (candidate-s-section-multi-domain-task-selection)
     ✅ 2026-09-09 18:03:57 Domain task registry & metadata (domain-task-registry)
     ✅ 2026-09-10 15:13:52 Workflow refactor: split shared pipeline from per-task analysis nodes (workflow-refactor-multi-task-pipeline)
     ✅ 2026-09-10 15:25:39 Per-task cost estimation (pre-run) & actual cost tracking (post-run) (per-task-cost-estimation)
     ✅ 2026-09-10 15:49:37 Multi-task result aggregation & state schema (multi-task-result-aggregation-schema)
     ✅ 2026-09-10 16:12:54 Task selection UI (checkboxes, disabled/blurred not-implemented tasks, live cost readout) (multi-task-selection-ui)
     See REASONING.md for detailed decision logs. -->

## P0

<!-- policy: P0 tasks are critical, urgent, blocks other work. Tasks that should ship ASAP. -->

## P1

<!-- policy: P1 tasks are core work that should ship. Default for planned features and important improvements. -->

- [ ] Multi-task messaging & logging (@claude)
  - **ID**: multi-task-messaging-logging
  - **Tags**: harness, logging, multi-domain-task-selection
  - **Candidate ID**: S5 (`CANDIDATE_TASKS.md`)
  - **Blocked by**: workflow-refactor-multi-task-pipeline, multi-task-result-aggregation-schema
  - **Details**: Graduated from `CANDIDATE_TASKS.md` (`S5`, Priority 5
    of 8). Every node's log line gains a task-id tag (e.g. prefixing
    `"[burn_cost_check] "`), so a multi-task run's combined log stays
    attributable per task. A combined-run summary message (which tasks
    ran, which were skipped as not-implemented, which failed) drives
    both the UI banner and the saved log file, replacing today's
    single-task-only `format_extraction_status()` in `src/app.py`.
  - **Files**: `src/workflow.py`, `src/app.py`, `tests/test_workflow.py`,
    `tests/test_app.py`
  - **Acceptance**: Every workflow node's log lines are tagged with the
    task id they belong to; a new `format_multi_task_status()`-style
    function (replacing `format_extraction_status()`) summarizes which
    tasks ran/were skipped/failed across a `task_results` dict;
    `python -m pytest -q` passes with tests for both the tagging and
    the summary function.

- [ ] Multi-task results UI (per-task sections + combined summary)
  - **ID**: multi-task-results-ui
  - **Tags**: ui, streamlit, multi-domain-task-selection
  - **Candidate ID**: S7 (`CANDIDATE_TASKS.md`)
  - **Blocked by**: multi-task-result-aggregation-schema, multi-task-messaging-logging
  - **Details**: Graduated from `CANDIDATE_TASKS.md` (`S7`, Priority 7
    of 8). One expandable section per selected+implemented task inside
    the existing "Analysis Results" bordered container — each with its
    own findings/log/actual cost (from `per-task-cost-estimation`) —
    plus a combined header (total findings across tasks, total actual
    cost, which tasks were skipped and why), replacing today's single
    `format_report_markdown()` call in `src/app.py`.
  - **Files**: `src/app.py`, `tests/test_app.py`
  - **Acceptance**: Selecting only `B0` renders identically to today's
    single-report view (regression safety net); selecting a mix of
    implemented + not-implemented tasks renders one expandable section
    per selected task (implemented tasks show real findings, skipped
    ones show a clear "not implemented" message) plus a combined
    header with aggregate findings/cost; `AppTest`-based tests cover
    both the single-task and mixed-selection cases.

- [ ] End-to-end test coverage for multi-task selection
  - **ID**: multi-task-e2e-test-coverage
  - **Tags**: testing, multi-domain-task-selection
  - **Candidate ID**: S8 (`CANDIDATE_TASKS.md`)
  - **Blocked by**: workflow-refactor-multi-task-pipeline, multi-task-result-aggregation-schema, per-task-cost-estimation, multi-task-messaging-logging, multi-task-selection-ui, multi-task-results-ui
  - **Details**: Graduated from `CANDIDATE_TASKS.md` (`S8`, Priority 8
    of 8, the last item in the Multi Domain-Task Selection chain).
    Dedicated end-to-end coverage across the whole `S2`-`S7` chain,
    beyond each task's own unit tests: selecting only `B0` behaves
    exactly like today (regression safety net); selecting a mix of
    implemented + not-implemented tasks skips the latter gracefully
    with a clear per-task message; cost estimates/actuals round-trip
    correctly end-to-end; the new `task_results` schema serializes
    correctly for the debug panel (`serialize_state_for_debug()` in
    `src/app.py`).
  - **Files**: `tests/test_integration.py`, `tests/test_app.py`
  - **Acceptance**: A new end-to-end test (or small suite) exercises a
    real multi-task selection through `run_workflow`/the running app,
    covering: `B0`-only selection matches today's baseline exactly; a
    mixed implemented/not-implemented selection produces the right
    per-task statuses; cost figures round-trip from estimate to
    actual; the debug JSON dump includes `task_results` without
    crashing; `python -m pytest -q` passes.

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


