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
     See REASONING.md for detailed decision logs. -->

## P0

<!-- policy: P0 tasks are critical, urgent, blocks other work. Tasks that should ship ASAP. -->


## P1

<!-- policy: P1 tasks are core work that should ship. Default for planned features and important improvements. -->

- [ ] Retry/Backoff Resilience for the LLM Call (@claude)
  - **ID**: llm-fallback-retry-backoff
  - **Tags**: reliability, extraction, llm
  - **Candidate ID**: A1 (`CANDIDATE_TASKS.md`)
  - **Details**: Graduated from `CANDIDATE_TASKS.md` (`A1`, Priority 1
    of 10 in the Harness list). In `src/workflow.py`'s
    `llm_extraction_fallback`, add bounded retry-with-backoff for
    *transient* failures only (`anthropic.APITimeoutError`,
    `anthropic.APIConnectionError`, `anthropic.RateLimitError`,
    `anthropic.InternalServerError`) before falling through to today's
    graceful-degradation path (`extraction_method="none"`, `llm_error`
    set). Non-transient failures (auth errors, a malformed tool
    response, a `TreatyTerms` validation error) must NOT be retried —
    they should fail straight to degradation exactly as today. Log
    each retry attempt (attempt number, backoff delay, exception) via
    the existing `"src.workflow"` logger so retries are visible in the
    debug panel like every other event. Cap total retries/backoff so a
    single upload can't hang indefinitely.
  - **Files**: `src/workflow.py`, `tests/test_workflow.py`
  - **Acceptance**: A mocked transient failure followed by a
    successful retry produces a correct `extraction_method="llm"`
    result, with retry attempts visible in captured log lines. A
    mocked non-transient failure (e.g. invalid API key) fails
    immediately with no retry, unchanged from today. A mocked failure
    that exhausts all retries degrades gracefully
    (`extraction_method="none"`, `llm_error` set) exactly like today,
    never crashing. `pytest tests/` passes.

- [ ] Grounding/Assurance Check on LLM Output
  - **ID**: llm-fallback-grounding-check
  - **Tags**: quality, extraction, llm
  - **Candidate ID**: A2 (`CANDIDATE_TASKS.md`)
  - **Details**: Graduated from `CANDIDATE_TASKS.md` (`A2`, Priority 2
    of 10 in the Harness list). After `llm_extraction_fallback`
    successfully extracts `TreatyTerms`, add a deterministic
    verification pass: for each extracted field with a
    `page_citations` entry, confirm the cited page's raw text actually
    supports the extracted value (exact match for `cedent_name`/
    `exclusions`; numeric-equivalence match for `attachment_point`/
    `limit`/`reinsurance_premium`, tolerating formatting differences
    like `"$200,000"` vs `200000`). If a field fails grounding, flag it
    (e.g. a new state field such as `ungrounded_fields`) rather than
    silently trusting it, and surface the flag in the UI/debug panel.
  - **Files**: `src/workflow.py`, `src/app.py`,
    `tests/test_workflow.py`, `tests/test_app.py`
  - **Acceptance**: A mocked LLM response whose `page_citations` point
    to text that doesn't actually support the claimed value is flagged
    as ungrounded (visible in the debug panel), while a normal,
    correctly-grounded response (e.g. today's fuzzy fixture) is not
    flagged. `pytest tests/` passes.

- [ ] Extraction Accuracy Eval Suite (Golden Dataset)
  - **ID**: extraction-accuracy-eval-suite
  - **Tags**: evaluation, extraction, llm
  - **Candidate ID**: A3 (`CANDIDATE_TASKS.md`)
  - **Details**: Graduated from `CANDIDATE_TASKS.md` (`A3`, Priority 3
    of 10 in the Harness list). Build a small labeled golden dataset
    of treaty documents (the three existing fixtures plus at least 2-3
    new prose/fuzzy variants with more realistic real-world phrasing
    than today's) with known-correct `TreatyTerms`, plus an automated
    scorer that runs each document through the full extraction
    pipeline (regex, falling back to the LLM Extraction Fallback where
    triggered) and reports field-level precision/recall — not just
    pass/fail — against the known-correct values. This is the harness
    that would catch a prompt or model-version regression before it
    reaches production, and is a prerequisite for `extraction-eval-ci-gate`.
  - **Files**: new golden-fixture + scorer location (e.g. `tests/eval/`),
    `README.md` (documents how to run the eval suite)
  - **Acceptance**: Running the eval suite locally produces a
    field-level accuracy report for every golden document, and a
    deliberately-broken extraction (e.g. a corrupted
    `_TREATY_EXTRACTION_TOOL` schema) is caught by a drop in scored
    accuracy. The existing `pytest tests/` suite still passes.

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


