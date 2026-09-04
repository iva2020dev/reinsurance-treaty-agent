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
  - **Details**: The Extractor Node (`extract_treaty_terms()` in
    `src/workflow.py`) is currently pure regex, matching only the
    `Label: value` convention the two mock fixtures use (see
    `build-agentic-workflow-graph`'s decision in REASONING.md) — it
    extracts nothing from real-world treaty prose, synonyms, or
    reordered clauses. `anthropic`/`langchain-core` are already pinned
    in `requirements.txt` but unused in `src/`. Explore a hybrid: try
    the existing regex extractor first (free, deterministic, fully
    testable), and fall back to an LLM-based extraction only when
    regex fails to find one or more required fields — aiming to keep
    the cost/determinism/auditability benefits of regex for
    well-formed documents while gaining real-world robustness for
    messier ones. This is a research/spike task, not a committed
    feature: the goal is a written recommendation (approach, cost/
    latency/reliability tradeoffs observed, a rough sense of accuracy
    on a few non-`Label: value` sample treaty texts) and, if it looks
    worthwhile, a proposed design — not necessarily a merged
    implementation.
  - **Files**: `src/workflow.py`, `REASONING.md` (findings/
    recommendation)
  - **Acceptance**: `REASONING.md` documents what was tried, the
    observed pros/cons versus pure regex (cost, latency, determinism,
    auditability, accuracy on non-conforming sample text), and a clear
    recommendation on whether/how to proceed — with no changes to
    `extractor_node`'s existing input/output contract required to
    reach that recommendation.


