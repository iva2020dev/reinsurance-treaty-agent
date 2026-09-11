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
     See REASONING.md for detailed decision logs. -->

## P0

<!-- policy: P0 tasks are critical, urgent, blocks other work. Tasks that should ship ASAP. -->

## P1

<!-- policy: P1 tasks are core work that should ship. Default for planned features and important improvements. -->

- [ ] Mandatory-clause / exclusion completeness checklist (@claude)
  - **ID**: exclusion-completeness-checklist
  - **Tags**: domain-task, treaty, deterministic
  - **Candidate ID**: B1 (`CANDIDATE_TASKS.md`)
  - **Details**: Graduated from `CANDIDATE_TASKS.md` (`B1`, Priority 1
    of 9 in the Treaty section). Compare an extracted treaty's
    `TreatyTerms.exclusions` against a configurable list of expected
    mandatory clauses (war, nuclear, cyber, pandemic, sanctions, TRIA);
    flag any missing clause as a new `AnomalyFinding`. This is the
    second real domain task (after `burn_cost_check`/B0) to become
    `implementation_status="implemented"` in `src/domain_tasks.py`'s
    registry, wired into `build_workflow_graph()`'s existing fan-out
    machinery (`multi-task-graph-fanout`) — selecting it alongside
    `burn_cost_check` should genuinely run both in parallel, not via a
    monkeypatched stand-in like every fan-out test so far has used.
  - **Files**: `src/workflow.py`, `src/domain_tasks.py`,
    `tests/test_workflow.py`, `tests/test_domain_tasks.py`. Also
    `src/app.py` and `tests/test_app.py` (added: the checklist's
    checkbox default-checked state was keyed off `is_implemented`
    generically, which only happened to be correct with exactly one
    implemented task — with a second implemented task, this would
    auto-check both by default, changing the app's baseline behavior.
    Fixed by keying it off `workflow.py`'s actual default-selection
    set instead — a real bug, not just a testing gap.)
  - **Acceptance**: A new `exclusion_completeness_checklist_node` in
    `src/workflow.py` compares `state["treaty"].exclusions` against a
    module-level mandatory-clause keyword list (case-insensitive
    substring match, no LLM call) and returns a `TaskResult` with one
    `AnomalyFinding` per missing clause (empty findings if all present)
    under `task_results["exclusion_completeness_checklist"]`;
    `src/domain_tasks.py`'s matching `DomainTask` entry is updated to
    `implementation_status="implemented"`,
    `workflow_node="exclusion_completeness_checklist_node"`;
    `tests/test_domain_tasks.py::test_only_b0_is_implemented` is
    updated to reflect two implemented tasks; new tests cover: an
    exclusions list missing every mandatory clause, one missing only a
    single clause, and one with every mandatory clause present (no
    findings); selecting `burn_cost_check` alone continues to produce
    byte-identical behavior (regression safety net, verified via
    `python -m tests.eval.run_eval` staying at 100%, and a fresh page
    load still defaults to only `burn_cost_check` checked); selecting
    both `burn_cost_check` and `exclusion_completeness_checklist`
    together through the real (non-monkeypatched) UI/`run_workflow`
    produces both tasks' entries in `task_results`; `python -m pytest
    -q` passes.

- [ ] Include every selected task's results in the saved/downloaded results file (@claude)
  - **ID**: multi-task-results-in-saved-file
  - **Tags**: bug, multi-domain-task-selection
  - **Candidate ID**: N/A (real bug reported directly by the human;
    also flagged as known future work in `multi-task-results-ui`'s own
    `REASONING.md` entry: "Left `save_analysis_result_to_file`/
    `render_report_bytes` ... untouched ... that's implicitly future
    work once a second real task exists")
  - **Details**: The on-screen "Analysis Results" container
    (`multi-task-results-ui`) renders a combined summary plus one
    section per selected task. But `format_results_document()` (and
    everything downstream of it — `render_report_bytes()`,
    `render_report_pdf()`, `save_analysis_result_to_file()`, and the
    "Save"/"Download" buttons in `main()`) still only ever renders
    `format_report_markdown(report)` — `report` is
    `burn_cost_check`-specific (per `S3`'s decision), so any other
    selected task's results (e.g. `exclusion_completeness_checklist`'s
    findings, once implemented) are silently missing from the saved/
    downloaded file even though they're visible on screen. Confirmed
    directly by the human running the app.
  - **Files**: `src/app.py`, `tests/test_app.py`
  - **Acceptance**: `format_results_document()` gains optional
    `selected_task_ids`/`task_results` parameters; when provided, the
    saved/downloaded document renders the same combined summary +
    per-task sections as the on-screen view (reusing
    `format_combined_results_summary()`/`format_task_section_
    markdown()`), not just `report` alone; when omitted (existing
    callers/tests), behavior is unchanged (additive, not a breaking
    change to the existing single-report signature); `render_report_
    bytes()`/`render_report_pdf()`/`save_analysis_result_to_file()`
    thread the new parameters through; `main()`'s Save/Download buttons
    pass the real `result_selected_task_ids`/`task_results` for the
    current run; a new test selects two tasks (one real, one
    monkeypatched, following the established fan-out-test pattern) and
    asserts both tasks' content appears in the saved file's text;
    existing single-task save/download tests continue to pass
    unchanged; `python -m pytest -q` passes.
    **Further refinement (same pass, still requested directly)**: full
    "final report" restyling of the saved/downloaded file: "Analysis
    Results" as the single biggest heading (`#`), each task's own name
    one level down (`##`); tasks visually separated by horizontal
    rules; each task's Findings block wrapped in a severity-colored
    background (red/amber/blue/green for high/medium/low/clean, via
    `highest_severity_label()`); a final "Findings Summary" section
    listing every ran task's findings again, grouped by task. Treaty
    name/terms are hoisted into their own shared section (since every
    selected task analyzes the same treaty) rather than living inside
    the first task's own section.
  - **Files (updated)**: `src/app.py`, `tests/test_app.py`
  - **Acceptance (updated)**: The saved document reads as: title →
    treaty terms (shared, once) → combined summary → one `##`-level
    section per selected task (no treaty duplication) with its
    Findings in a severity-colored block → a final "Findings Summary"
    section repeating every ran task's findings grouped by task
    heading; `render_report_pdf()` renders heading levels at
    genuinely different font sizes (not all headings the same size),
    draws real horizontal rules for `---` markers, and fills each
    Findings block's background with its severity color; existing
    tests are updated to match the new structure (exact-equality
    assertions become structural/substring assertions where the
    content legitimately changed); `python -m pytest -q` passes.
    **Further refinements (same pass, four real bugs found by the
    human actually using the app)**:
    (1) The checklist's pre-run "Estimated cost" for Burn-Cost Check
    showed a nonzero figure while its post-run "Total actual cost"
    always shows $0.0000 — because `src/domain_tasks.py` labels it
    `shape="hybrid"` (implying it might call an LLM) but
    `burn_cost_check_node` never calls one at all (pure regex/
    arithmetic); `estimate_task_cost()` charges non-deterministic
    shapes a nonzero estimate regardless. Fix: correct the registry
    entry to `shape="deterministic"`, matching what the node actually
    does — makes the estimate genuinely $0.0000, consistent with the
    real actual cost.
    (2) The Findings block's colored `<div style="...">` HTML leaked
    onto the screen as literal visible text — `st.markdown()` doesn't
    render raw HTML by default (correctly, since treaty-derived text
    like exclusions is user-uploaded PDF content, and enabling
    `unsafe_allow_html=True` on it would be a stored-HTML-injection
    risk). Fix: on-screen rendering must never emit the HTML wrapper;
    only the saved-file path (`format_results_document()`/PDF, never
    passed through a browser) may.
    (3) Burn-Cost Check's own section never showed "Cost: $X ·
    Latency: Ys" the way every other task's section does, even though
    that data exists in its own `TaskResult` — its renderer only ever
    read from `report` (no cost/latency fields), ignoring the
    `task_result` parameter it's actually given. Fix: include the
    Cost/Latency line for Burn-Cost Check too.
    (4) Severity emoji (⚠️/🚨/ℹ️) already survive in the saved `.md`
    file (UTF-8, no stripping) but are silently dropped from the PDF
    (fpdf2's core Helvetica font is Latin-1-only). Fix: bundle DejaVu
    Sans (public-domain-friendly Bitstream Vera license,
    `assets/fonts/`) and use it for PDF rendering; low/medium map to
    their plain-Unicode counterparts (`ℹ`/`⚠`, DejaVu has these);
    high substitutes `‼` (DejaVu lacks the astral 🚨 glyph, as does
    essentially every non-color-emoji font).
  - **Files (further updated)**: `src/app.py`, `src/domain_tasks.py`,
    `tests/test_app.py`, `assets/fonts/DejaVuSans.ttf`,
    `assets/fonts/DejaVuSans-Bold.ttf`,
    `assets/fonts/DEJAVU_LICENSE.txt` (new)
  - **Acceptance (further updated)**: Burn-Cost Check's registry shape
    is `deterministic` and its pre-run estimate is $0.0000, matching
    its real $0.0000 actual cost; the on-screen view never shows raw
    `<div>`/`</div>` text, only real Streamlit-rendered color; Burn-Cost
    Check's on-screen/file section shows Cost/Latency like every other
    task; the PDF renders `ℹ`/`⚠`/`‼` severity symbols instead of
    dropping them silently; `python -m pytest -q` passes.
    **Further refinement (same pass)**: the LLM Extraction Fallback's
    real cost (previously shown only as raw token counts, never
    converted to a dollar figure, and never included in "Total actual
    cost") is now surfaced as its own line ("Extraction: LLM Fallback
    used ($X)") near the shared treaty section, using the
    already-defined but previously-unused `actual_task_cost()`
    (`src/cost_estimation.py`), and folded into "Total actual cost" so
    that figure is honest about the real spend for a run that needed
    the LLM fallback.
  - **Files (further updated)**: `src/app.py`, `tests/test_app.py`
  - **Acceptance (further updated)**: When a run used the LLM
    Extraction Fallback, both the saved file and the on-screen view
    show an "Extraction: LLM Fallback used ($X)" line with a real
    dollar figure (not just token counts), and "Total actual cost"
    includes that amount; when the LLM wasn't invoked (regex found
    everything), no such line appears and the total is unaffected;
    `python -m pytest -q` passes.
    **Further refinement (same pass)**: human asked twice why the
    total didn't equal the visible sum of per-task Cost lines (e.g.
    two tasks each showing $0.0000, but the total showing $0.0028) —
    the separate "Extraction: LLM Fallback used ($X)" caption wasn't
    enough to make the total's math self-evident on its own. Fix: when
    `extraction_cost > 0`, the combined summary line itself becomes a
    breakdown ("$0.0000 (tasks) + $0.0028 (extraction) = $0.0028 total
    actual cost") instead of just the final number; when
    `extraction_cost == 0` (the common case), unchanged single-number
    form. "total actual cost" wording explicitly kept per the human's
    stated preference.
    **Further refinement (same pass)**: the combined summary line
    mixed bold and plain segments ("**N finding(s)**" bold, " across
    selected task(s) · " plain, "**breakdown**" bold, " total actual
    cost" plain) — human asked for one consistent style throughout.
    Made the entire line one continuous bold span.
  - **Files (further updated)**: `src/app.py`, `tests/test_app.py`

- [ ] Regenerate workflow diagram for a multi-task selection example
  - **ID**: multi-task-graph-diagram-example
  - **Tags**: harness, docs, multi-domain-task-selection
  - **Candidate ID**: N/A (not graduated from `CANDIDATE_TASKS.md`; a
    follow-up found directly while discussing `multi-task-graph-
    fanout` with the human)
  - **Details**: `scripts/regenerate_workflow_graph.py`'s
    `get_mermaid_text()` always calls `build_workflow_graph()` with no
    arguments, rendering only the *default* single-task selection
    (`{"burn_cost_check"}`) into `README.md`'s mermaid block and
    `data/workflow_graph.png`. Now that `multi-task-graph-fanout` made
    the graph-building code genuinely selection-count-agnostic, the
    shipped diagram should also be able to show what a real multi-task
    selection looks like (`Verifier` branching to 2+ analysis nodes) —
    otherwise the diagram will keep looking identical forever even
    after fan-out is exercised in production, which hides the
    capability from anyone reading the README.
    **Important caveat, noted for whoever picks this up**: this is only
    meaningfully verifiable once a *second real* domain task (e.g. a
    graduated/implemented `B1`) exists in `src/domain_tasks.py`'s
    registry — today, demonstrating a 2-task selection still needs a
    mocked/monkeypatched node (like `multi-task-graph-fanout`'s own
    test uses), which isn't suitable content for a real, permanently-
    committed README diagram. If no second domain task is implemented
    yet when this is picked up, re-scope (e.g. to just the script
    plumbing, with the actual second example diagram deferred) or hold
    off rather than faking an example task.
  - **Files**: `scripts/regenerate_workflow_graph.py`, `README.md`,
    `tests/test_workflow_graph_docs.py`
  - **Acceptance**: `README.md` gains a second, clearly-labeled
    diagram (e.g. a `<!-- workflow-graph-multi-task:start/end -->`
    block) showing `build_workflow_graph()` for an explicit real
    multi-task selection, branching from `Verifier` to every included
    task's node; `tests/test_workflow_graph_docs.py` (or a new sibling
    test) verifies this second diagram also stays in sync with the
    live graph, the same way the existing single-task one does;
    `python -m pytest -q` passes.

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


