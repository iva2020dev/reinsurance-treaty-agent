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
     See REASONING.md for detailed decision logs. -->

## P0

<!-- policy: P0 tasks are critical, urgent, blocks other work. Tasks that should ship ASAP. -->

## P1

<!-- policy: P1 tasks are core work that should ship. Default for planned features and important improvements. -->

- [ ] Workflow refactor: split shared pipeline from per-task analysis nodes (@claude)
  - **ID**: workflow-refactor-multi-task-pipeline
  - **Tags**: harness, refactor, multi-domain-task-selection
  - **Candidate ID**: S2 (`CANDIDATE_TASKS.md`)
  - **Details**: Graduated from `CANDIDATE_TASKS.md` (`S2`, Priority 2
    of 8 in the Multi Domain-Task Selection list). Today's
    `Extractor → [LLM Extraction Fallback] → Verifier` stays a shared
    pipeline every domain task needs (produces `TreatyTerms` +
    `claims`); rename/scope `analyst_node` to `burn_cost_check_node`
    (`B0`'s Burn-Cost Check logic, unchanged), and parameterize
    `build_workflow_graph()` by a set of selected task IDs (using
    `src/domain_tasks.py`'s registry to resolve IDs to node functions)
    — it always runs the shared pipeline, then only the analysis
    node(s) for tasks that are both selected and
    `implementation_status="implemented"` (today: only `B0`/
    `burn_cost_check_node`). Selecting only `B0` must behave exactly
    like today's single-task graph (regression safety net) — no
    caller-visible behavior change until a second domain task actually
    exists.
  - **Files**: `src/workflow.py`, `tests/test_workflow.py`,
    `tests/test_integration.py`
  - **Acceptance**: `build_workflow_graph(selected_task_ids: set[str])`
    (or equivalent) always runs Extractor → [LLM Fallback] → Verifier,
    then only `burn_cost_check_node` when `"burn_cost_check"` (`B0`) is
    in `selected_task_ids`; calling it with just `B0` selected produces
    identical output/behavior to today's fixed graph on every existing
    fixture; `python -m pytest -q` passes with `analyst_node`
    references updated to `burn_cost_check_node` throughout the test
    suite; likely its own multi-task chain once picked up (Effort: L,
    same pattern as the `B4`/hybrid-extraction chains), not a single
    commit.

- [ ] Multi-task result aggregation & state schema
  - **ID**: multi-task-result-aggregation-schema
  - **Tags**: harness, refactor, multi-domain-task-selection
  - **Candidate ID**: S3 (`CANDIDATE_TASKS.md`)
  - **Blocked by**: workflow-refactor-multi-task-pipeline
  - **Details**: Graduated from `CANDIDATE_TASKS.md` (`S3`, Priority 3
    of 8). Replace `WorkflowState.report: AnomalyReport | None`
    (`src/workflow.py`) with `WorkflowState.task_results:
    dict[str, TaskResult]` — one entry per selected task, each with a
    `status` (`ran` / `skipped_not_implemented` / `failed`), its
    findings, cost, and latency — so the UI (`S7`) can render N
    independent per-task results instead of a single report. `B0`'s
    entry (key `"burn_cost_check"`) carries today's `AnomalyReport`
    fields; every other selected-but-not-implemented task gets a
    `skipped_not_implemented` entry with no findings.
  - **Files**: `src/models.py` (new `TaskResult` model), `src/workflow.py`,
    `tests/test_workflow.py`
  - **Acceptance**: A new `TaskResult` Pydantic model in `src/models.py`
    with `status`/`findings`/`cost`/`latency` fields; `WorkflowState`
    exposes `task_results` keyed by domain-task id; selecting only
    `B0` produces a `task_results` dict with exactly one `ran` entry
    equivalent to today's `AnomalyReport`; `python -m pytest -q`
    passes with existing single-report assertions updated to read from
    `task_results["burn_cost_check"]`.

- [ ] Per-task cost estimation (pre-run) & actual cost tracking (post-run)
  - **ID**: per-task-cost-estimation
  - **Tags**: harness, cost-observability, multi-domain-task-selection
  - **Candidate ID**: S4 (`CANDIDATE_TASKS.md`)
  - **Details**: Graduated from `CANDIDATE_TASKS.md` (`S4`, Priority 4
    of 8). The first real $-cost logic in this app — narrower/scoped
    version of `A6` ("Cost & latency observability"), specific to
    per-task estimate/actual display rather than `A6`'s broader
    always-on observability. Pre-run: a rough per-task cost estimate
    from document page/token count × task shape (`src/domain_tasks.py`'s
    `shape` field) — near-zero for `deterministic` tasks, a
    model-price-based estimate for `llm`/`hybrid` tasks — plus a live
    cumulative total as the `S6` UI's checkboxes toggle. Post-run:
    convert `llm_extraction_fallback`'s already-logged `input_tokens`/
    `output_tokens` (same log line `extract_llm_usage_summary()` in
    `src/app.py` already parses for the saved-results feature) into an
    actual $ figure via the model's published per-token price,
    replacing the estimate once a task completes.
  - **Files**: `src/cost_estimation.py` (new), `tests/test_cost_estimation.py`
    (new)
  - **Acceptance**: An `estimate_task_cost(task, page_count)` function
    (or equivalent) returns near-zero for every `deterministic`-shaped
    task and a non-zero, page-count-scaled estimate for `llm`/`hybrid`-
    shaped ones; an `actual_task_cost(input_tokens, output_tokens)`
    function converts real token counts into a $ figure using the
    model's published price; direct unit tests for both; this task
    only adds the cost-math module — it does not wire estimates into
    the UI yet (that's `S6`).

- [ ] Multi-task messaging & logging
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

- [ ] Task selection UI (checkboxes, disabled/blurred not-implemented tasks, live cost readout)
  - **ID**: multi-task-selection-ui
  - **Tags**: ui, streamlit, multi-domain-task-selection
  - **Candidate ID**: S6 (`CANDIDATE_TASKS.md`)
  - **Blocked by**: per-task-cost-estimation
  - **Details**: Graduated from `CANDIDATE_TASKS.md` (`S6`, Priority 6
    of 8). A checkbox/multiselect control in `src/app.py` listing every
    task from `src/domain_tasks.py`'s `DOMAIN_TASKS` registry; only
    tasks with `implementation_status="implemented"` (today: just
    `B0`) are enabled/checkable, every other task rendered visually
    disabled/blurred with a "Not implemented" badge (matching this
    app's existing disabled-button styling pattern, e.g. the Review/
    Analyze buttons' `disabled=` state in `main()`); checking an
    enabled task shows its live cost estimate from `per-task-cost-
    estimation`'s `estimate_task_cost()`, plus a running cumulative
    total across all checked tasks. Replaces the implicit
    "`B0` always runs" behavior with an explicit selection step.
  - **Files**: `src/app.py`, `tests/test_app.py`
  - **Acceptance**: The Streamlit UI shows one checkbox per registry
    entry; not-implemented tasks are visibly disabled and can't be
    checked; checking `B0` shows a live cost estimate and updates a
    running total; the selected task ID set feeds into `build_workflow_
    graph()` (from `workflow-refactor-multi-task-pipeline`) when
    "Analyze" is clicked; `AppTest`-based tests cover the disabled
    state, the cost readout, and that only checked+implemented tasks
    actually run.

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


