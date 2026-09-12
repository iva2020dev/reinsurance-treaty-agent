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
     ✅ 2026-09-10 17:04:17 Multi-task messaging & logging (multi-task-messaging-logging)
     ✅ 2026-09-10 21:58:20 Dynamic graph fan-out for multi-task selection (multi-task-graph-fanout)
     ✅ 2026-09-10 19:25:28 Document close/ and add-task/ branch-naming conventions in AGENTS.md (document-branch-naming-conventions)
     ✅ 2026-09-11 10:58:38 Multi-task results UI (per-task sections + combined summary) (multi-task-results-ui)
     ✅ 2026-09-11 12:19:38 End-to-end test coverage for multi-task selection (multi-task-e2e-test-coverage)
     ✅ 2026-09-11 13:06:31 Compact the "Domain tasks to run" checklist rows onto one line each (compact-domain-task-checklist-rows)
     ✅ 2026-09-11 19:41:05 Widen the main page container by 15% (widen-main-container)
     ✅ 2026-09-11 19:59:18 Adjust main container width to a fixed 800px (adjust-main-container-width)
     ✅ 2026-09-11 20:14:07 Include every selected task's results in the saved/downloaded results file, styled as a final report (multi-task-results-in-saved-file)
     ✅ 2026-09-11 15:22:12 Mandatory-clause / exclusion completeness checklist (exclusion-completeness-checklist)
     ✅ 2026-09-12 07:34:37 Add a Download button (with format selection) for the "Analysis Workflow execution" debug panel (debug-panel-download)
     ✅ 2026-09-12 08:10:00 Regenerate workflow diagram for a multi-task selection example (multi-task-graph-diagram-example)
     ✅ 2026-09-12 09:15:00 Isolate domain-task business logic into per-task service modules (isolate-domain-task-services)
     ✅ 2026-09-12 10:20:00 Key-date/renewal calendar extraction (key-date-renewal-calendar-extraction)
     ✅ 2026-09-12 10:50:00 Make the multi-task workflow graph example dynamic and widen its regen trigger (dynamic-workflow-graph-diagram)
     See REASONING.md for detailed decision logs. -->

## P0

<!-- policy: P0 tasks are critical, urgent, blocks other work. Tasks that should ship ASAP. -->

## P1

<!-- policy: P1 tasks are core work that should ship. Default for planned features and important improvements. -->

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

- [ ] Plain-English treaty summary (@claude)
  - **ID**: plain-english-treaty-summary
  - **Tags**: business-domain, treaty, llm
  - **Candidate ID**: B7 (`CANDIDATE_TASKS.md`, re-ranked Pri 3 of 8 on
    2026-09-12)
  - **Details**: One LLM call producing a short executive summary
    (parties, layer, key dates, notable clauses) directly from the
    picked treaty's raw parsed sections — not the extracted `TreatyTerms`
    (there's no dependency on extraction/"Analyze" at all, only on which
    treaty was picked). Must be opt-in (an explicit button/action), not
    automatic, to preserve the app's "LLM cost only when needed" default
    — see `CANDIDATE_TASKS.md`'s note that B6-B8/C4 would change the
    app's cost profile if made automatic. High business priority: used
    on nearly every treaty reviewed in real practice (new submissions
    and renewals alike), cheap and immediately useful to non-technical
    stakeholders.
    **Update (2026-09-12)**: human feedback on the open PR — since the
    summary only depends on which treaty is picked, its button moved to
    sit alongside "Review treaty" (right below "Choose a reinsurance
    treaty"), available before "Analyze", not inside "Analysis Results"
    after it; added save/download logic for the summary with format
    selection (Markdown/PDF), matching the existing analysis-results
    pattern.
  - **Files**: `src/services/plain_english_treaty_summary.py` (new),
    `src/domain_tasks.py`, `src/app.py` (standalone trigger UI next to
    "Review treaty", plus save/download helpers for the summary),
    `tests/services/test_plain_english_treaty_summary.py` (new),
    `CANDIDATE_TASKS.md`
  - **Acceptance**: a distinct opt-in action, available as soon as a
    treaty is picked (before "Analyze"), produces a short plain-English
    summary from that treaty's raw text; it never runs unless explicitly
    triggered, even when other domain tasks are selected or "Analyze" is
    clicked; the summary can be saved/downloaded with a format choice
    (Markdown/PDF), like the main analysis results; registered in
    `domain_tasks.py` as implemented (`shape="llm"`); `python -m pytest
    -q` passes.

- [ ] Multi-layer program extraction & aggregation
  - **ID**: multi-layer-program-extraction
  - **Tags**: business-domain, treaty, extraction, schema-change
  - **Candidate ID**: B4 (`CANDIDATE_TASKS.md`, re-ranked Pri 4 of 8 on
    2026-09-12)
  - **Details**: Today only Layer 1 of a multi-layer treaty is
    extracted (`TreatyTerms` models a single layer). Lift that
    simplification: extract every layer, compute burn cost per layer
    and for the combined program. Real schema change (`TreatyTerms` →
    a list of layers), touching the parser, extraction pipeline,
    workflow state, and UI, plus every existing fixture — Effort: L per
    `CANDIDATE_TASKS.md`, likely its own multi-task chain once actually
    picked up (same pattern as the earlier hybrid-extraction work),
    not necessarily a single PR. Segmenting which prose belongs to
    which layer is itself a document-quality-sensitive sub-problem —
    may need LLM-assisted layer-boundary detection even though
    per-layer figures stay a regex/arithmetic problem. High business
    priority despite the effort size: most real treaties *are*
    multi-layer programs, so today's single-layer simplification is a
    correctness gap affecting the majority of real-world documents, not
    an edge case — and a task this large should start early even though
    it delivers later. `B5` (Reinstatement cost modeling) depends on
    this.
  - **Files**: `src/models.py` (`TreatyTerms` schema change), `src/
    parser.py`, `src/workflow.py` (extraction pipeline), `src/
    services/` (per-layer + aggregate burn-cost logic), `src/app.py`,
    every fixture under `data/`, corresponding tests across `tests/`
  - **Acceptance**: a multi-layer treaty's every layer is extracted
    (not just Layer 1); burn cost is computed per layer and for the
    combined program; existing single-layer treaties/fixtures continue
    to work unchanged; `python -m pytest -q` and `python -m
    tests.eval.run_eval` both pass.

- [ ] Renewal year-over-year diff
  - **ID**: renewal-year-over-year-diff
  - **Tags**: business-domain, treaty, extraction
  - **Candidate ID**: B3 (`CANDIDATE_TASKS.md`, re-ranked Pri 5 of 8 on
    2026-09-12)
  - **Details**: Accept two treaty PDFs (this year vs. last), extract
    both via the existing extraction pipeline, diff `TreatyTerms`
    field-by-field, and report what changed (rate, attachment, limit,
    new/removed exclusions). Unlike every other domain task so far,
    this needs *two* input documents, not one — will likely need its
    own second-document UI entry point rather than fitting into the
    existing single-document task-selection flow; scope that UI
    question during implementation, not assumed here. High business
    value at every renewal (informs the actual renewal negotiation),
    and renewals recur constantly across a portfolio even though any
    single treaty only renews annually.
  - **Files**: `src/services/renewal_year_over_year_diff.py` (new),
    `src/app.py` (second-document input UI), `src/domain_tasks.py`,
    `tests/services/test_renewal_year_over_year_diff.py` (new),
    `CANDIDATE_TASKS.md`
  - **Acceptance**: given two treaty PDFs, the diff reports every
    changed field (rate/attachment/limit/premium, added/removed
    exclusions) between them; registered in `domain_tasks.py` as
    implemented; `python -m pytest -q` passes.

- [ ] Semantic compliance/clause matching
  - **ID**: semantic-clause-matching
  - **Tags**: business-domain, treaty, llm
  - **Candidate ID**: B6 (`CANDIDATE_TASKS.md`, re-ranked Pri 6 of 8 on
    2026-09-12)
  - **Details**: LLM version of `B1` (`exclusion_completeness_
    checklist`), matching mandatory-clause *intent* rather than
    keyword substrings, so it survives wording variation `B1`'s
    keyword-matching approach would miss. Important for compliance/risk
    sign-off on every treaty, but ranked after the cheaper deterministic
    B-series wins above since it's LLM-shaped (real per-run cost if run
    on every upload — see `CANDIDATE_TASKS.md`'s note on B6-B8/C4's cost
    profile if made automatic rather than opt-in).
  - **Files**: `src/services/semantic_clause_matching.py` (new),
    `src/domain_tasks.py`, `tests/services/
    test_semantic_clause_matching.py` (new), `CANDIDATE_TASKS.md`
  - **Acceptance**: given a treaty's extracted exclusions text, the
    node flags any of `B1`'s mandatory clause categories whose *intent*
    isn't covered, even when the exact keyword isn't present (e.g.
    "acts of aggression between sovereign states" for "war"); a golden/
    example-based test set (not just exact-match) covers at least one
    wording-variation case per mandatory clause category; registered in
    `domain_tasks.py` as implemented (`shape="llm"`); `python -m pytest
    -q` passes.

- [ ] Reinstatement cost modeling
  - **ID**: reinstatement-cost-modeling
  - **Tags**: business-domain, treaty, extraction
  - **Candidate ID**: B5 (`CANDIDATE_TASKS.md`, re-ranked Pri 7 of 8 on
    2026-09-12)
  - **Blocked by**: multi-layer-program-extraction
  - **Details**: Extract reinstatement terms and compute the added
    premium cost if a layer is fully exhausted. Depends on
    `multi-layer-program-extraction` (`B4`) since reinstatement is a
    per-layer concept. Real but specialized to layered programs already
    exhausted/reinstated — narrower and lower-frequency than the other
    B-series items, hence ranked near the end despite being
    deterministic.
  - **Files**: `src/services/reinstatement_cost_modeling.py` (new),
    `src/domain_tasks.py`, `tests/services/
    test_reinstatement_cost_modeling.py` (new), `CANDIDATE_TASKS.md`
  - **Acceptance**: given a treaty's reinstatement terms and a layer
    determined to be exhausted (per `multi-layer-program-extraction`'s
    per-layer burn-cost output), the node computes the added
    reinstatement premium cost; registered in `domain_tasks.py` as
    implemented; `python -m pytest -q` passes.

- [ ] Clause ambiguity/contradiction detection
  - **ID**: clause-ambiguity-detection
  - **Tags**: business-domain, treaty, llm
  - **Candidate ID**: B8 (`CANDIDATE_TASKS.md`, re-ranked Pri 8 of 8 on
    2026-09-12)
  - **Details**: LLM reviews the whole document for internally
    inconsistent terms (e.g. attachment point defined differently in
    two places). Judgment-based output — harder to test than field
    extraction; needs example-based/golden tests, not just exact-match.
    Valuable QA, but an occasional deep-review activity rather than
    daily underwriting work, hence ranked near the end of the B-series.
  - **Files**: `src/services/clause_ambiguity_detection.py` (new),
    `src/domain_tasks.py`, `tests/services/
    test_clause_ambiguity_detection.py` (new), `CANDIDATE_TASKS.md`
  - **Acceptance**: given a treaty document with a deliberately
    inconsistent term planted across two sections, the node flags the
    contradiction with both locations cited; a golden/example-based
    test set covers at least one contradiction case and one
    no-contradiction (true-negative) case; registered in
    `domain_tasks.py` as implemented (`shape="llm"`); `python -m pytest
    -q` passes.

- [ ] Peer/portfolio benchmarking
  - **ID**: peer-portfolio-benchmarking
  - **Tags**: business-domain, treaty, extraction, data-model
  - **Candidate ID**: B9 (`CANDIDATE_TASKS.md`, unchanged at Pri 9 —
    already last in the original ranking, stays last here too)
  - **Details**: Is this treaty's pricing an outlier vs. similar
    treaties already on file? Needs a portfolio data model (multiple
    treaties persisted, not just single-document analysis) — a bigger
    data-model addition than any other B-series item, and Effort: L per
    `CANDIDATE_TASKS.md` (likely its own task chain once picked up).
    Strategic and periodic (quarterly/annual portfolio review) rather
    than needed on every single-treaty review, so ranked last despite
    being deterministic once the portfolio store exists.
  - **Files**: a new portfolio persistence layer (module TBD at
    implementation time), `src/services/peer_portfolio_benchmarking.py`
    (new), `src/domain_tasks.py`, `tests/services/
    test_peer_portfolio_benchmarking.py` (new), `CANDIDATE_TASKS.md`
  - **Acceptance**: given a portfolio of previously-analyzed treaties
    and a new treaty's extracted terms, the node flags the new treaty's
    pricing as a statistical outlier (e.g. z-score threshold) against
    the portfolio; registered in `domain_tasks.py` as implemented;
    `python -m pytest -q` passes.


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


