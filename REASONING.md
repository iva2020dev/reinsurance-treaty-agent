
# REASONING.md

This file contains the reasoning transcript of the AI agent for the current session.

## 2026-09-03 11:52:52 — Task: Spec-First Development & File Structure (spec-first-file-structure)

- **Goal**: Create the modular `data/`, `src/`, `tests/` scaffold described
  in the task so subsequent feature work (parsing, tools, workflow, app) has
  an agreed, importable structure to build against.
- **Analysis**: Repo currently has no `src/`, `data/`, or `tests/` directories
  — only project scaffolding (CLAUDE.md, AGENTS.md, TASKS.md, REASONING.md,
  `.github/`, `.idea/`, `requirements.txt`). `requirements.txt` already lists
  pydantic, langgraph, langchain-core, anthropic, fastapi, uvicorn, pytest,
  python-dotenv, pypdf, streamlit — consistent with the module responsibilities
  named in the task (models.py/Pydantic, parser.py/pypdf, workflow.py/langgraph,
  app.py/Streamlit or FastAPI). No existing Python package structure to
  conform to, so this is a from-scratch scaffold.
- **Decision**: Create each file as a stub with a module docstring only
  (no placeholder classes/functions) — the task's Acceptance criterion asks
  for "stub content" and importability/pytest-discoverability, not working
  logic; inventing schemas/logic ahead of a real spec would be scope creep
  for a task titled "Spec-First Development & File Structure." `data/` gets
  a `.gitkeep` since git does not track empty directories. Test files get a
  minimal placeholder test each so pytest discovers and passes them (an
  empty test file with no test functions is discoverable but doesn't prove
  collection actually works).
- **Action**:
  - `src/__init__.py` — empty, makes `src` an importable package.
  - `src/models.py`, `src/parser.py`, `src/tools.py`, `src/workflow.py`,
    `src/app.py` — module docstring stating purpose (matching the comment
    in the task's tree diagram), no other content yet.
  - `tests/test_parser.py`, `tests/test_workflow.py` — module docstring +
    one trivial placeholder test each (`test_module_imports`) so pytest
    collects and passes them, proving the scaffold is wired up.
  - `data/.gitkeep` — placeholder so the empty directory is tracked.
- **Outcome**: Ran `python3 -m pytest tests/ -v` — 2 passed
  (`tests/test_parser.py::test_module_imports`,
  `tests/test_workflow.py::test_module_imports`), confirming `src` is
  importable and both test files are discovered and pass. All Acceptance
  criteria met; task removed from TASKS.md per the tasks.md spec (completed
  top-level tasks are removed, not checked off — history lives in git).
  PR #1 (`task/spec-first-file-structure`) merged by the repo owner at
  2026-09-03 11:52:52 UTC (merge commit `7bd522a`).

## 2026-09-03 12:14:15 — Task: Define Core Data Schemas (define-core-data-schemas)

- **Goal**: Define strict Pydantic v2 schemas in `src/models.py` for
  extracted treaty terms, historical claims, and the final anomaly audit
  report — the shared contract that `parser.py`, `tools.py`, and
  `workflow.py` will all be built against.
- **Analysis**: `src/models.py` currently has only a module docstring
  (from the spec-first-file-structure scaffold). `requirements.txt` pins
  `pydantic>=2.0`, so v2 syntax (`BaseModel`, `Field`, `field_validator`)
  is available. The task's acceptance criteria name three schemas
  (`TreatyTerms`, `ClaimsData`, `AnomalyReport`) and specific treaty
  fields (attachment point, limit, reinsurance premium, exclusions).
  Downstream tasks need: `build-pdf-ingestion-parsing` — a page-citation
  concept (so `TreatyTerms` fields should be traceable to source pages);
  `implement-deterministic-tools` — `calculate_loss_ratio` takes
  `attachment_point`, `limit`, and a `claims` list, and
  `query_historical_claims` returns claims for a cedent, so `ClaimsData`
  needs a `cedent_name` plus a claim amount; `build-agentic-workflow-graph`
  — the Analyst node "flags anomalies," so `AnomalyReport` needs a list of
  discrete, typed findings, not just free text.
- **Decision**: Model each treaty field's page citation directly on
  `TreatyTerms` (a `page_citations: dict[str, int]` mapping field name to
  source page) rather than a separate wrapper type, since the task asks
  for "structured sections with page citations" attached to extracted
  terms, and the Streamlit UI (`create-ui-api`) needs to render citations
  next to the values they support. Exclusions are `list[str]` (free-text
  clauses — a treaty can have an open-ended number of exclusion clauses,
  not a fixed schema). `ClaimsData` represents one historical claim record
  (cedent, claim amount, date) rather than a claims-list wrapper, since
  `query_historical_claims` naturally returns `list[ClaimsData]` and
  `calculate_loss_ratio` takes `list[ClaimsData]` — matching both
  downstream tool signatures without an extra container type.
  `AnomalyReport` holds a list of `AnomalyFinding` (field, description,
  severity) plus the computed loss ratio and treaty/claims echoed back,
  so the UI can render one finding per anomaly with severity-based styling.
  Used `field_validator`/`Field(gt=0)` where negative values are
  nonsensical (limit, premium, attachment point, claim amount) rather than
  leaving them unconstrained, since "strict schemas" was explicit in the
  task goal.
- **Action**: Rewrote `src/models.py`: added `Severity` enum, `TreatyTerms`
  (attachment_point, limit, reinsurance_premium, exclusions,
  page_citations), `ClaimsData` (cedent_name, claim_amount, claim_date),
  `AnomalyFinding` (field, description, severity), and `AnomalyReport`
  (treaty, claims, loss_ratio, findings). All numeric fields use
  `Field(gt=0)`; `exclusions` defaults to an empty list.
- **Outcome**: Ran an ad-hoc validation script (not committed — permanent
  schema tests belong to the separate `write-unit-tests` task, which lists
  "one invalid-input case per schema" as an explicit acceptance criterion):
  constructing `TreatyTerms`/`ClaimsData`/`AnomalyFinding`/`AnomalyReport`
  with valid data succeeds and round-trips through `model_dump_json()`;
  `TreatyTerms(attachment_point=-1, ...)` and `ClaimsData(cedent_name="",
  ...)` both raise `pydantic.ValidationError` as required. Re-ran
  `pytest tests/` — 2 passed, no regressions. Acceptance criteria met;
  task removed from TASKS.md per the tasks.md spec.

## 2026-09-03 12:26:10 — Task: Build PDF Ingestion & Parsing (build-pdf-ingestion-parsing)

- **Goal**: Write a robust utility in `src/parser.py` using `pypdf` to
  ingest a treaty PDF, extract text by page, and return structured
  sections tagged with page citations — feeding `TreatyTerms` extraction
  in the later workflow task.
- **Analysis**: `data/` only had a `.gitkeep` — no sample treaty PDF
  existed. `requirements.txt` pins `pypdf` (already installed,
  6.16.2) but no PDF-writing library (`reportlab`, `fpdf`) is available
  to generate a realistic sample, and adding a new dependency for a
  test fixture felt like scope creep for a parsing task. `pypdf.PdfReader`
  gives per-page text via `page.extract_text()`, which directly satisfies
  "extract text by page... with page citations" if I keep a 1:1 mapping
  from page index to extracted text.
- **Decision**: Hand-rolled a minimal valid PDF (raw `%PDF-1.4` objects,
  content streams with `Tj` text-showing operators, manually computed
  xref offsets) as `data/sample_treaty.pdf` for verification, rather than
  add a new runtime dependency just to synthesize a fixture — pypdf reads
  it back correctly (verified per-page `extract_text()` round-trip below).
  Designed `parser.py`'s public API as `extract_treaty_sections(path) ->
  list[PageSection]` where `PageSection` is a small local dataclass
  (`page_number`, `text`) — a lightweight return type dedicated to parser
  output, distinct from `src/models.py`'s domain schemas (`TreatyTerms`
  etc.), since raw per-page text isn't itself treaty-term data; the
  Extractor Node (a later task) is responsible for turning `PageSection`
  text into `TreatyTerms` with `page_citations`. Wrapped `pypdf`'s file-open
  and per-page extraction in a `try/except` re-raising as a single
  `ParserError` (a small custom exception), so malformed/unreadable PDFs
  fail with one clear, catchable error type as the acceptance criterion
  requires, instead of letting pypdf's various internal exceptions leak
  through uncaught. Skip pages that extract to empty text only if the
  whole document extracts empty (i.e. treat "no text at all" as a parse
  failure, since a treaty PDF with zero extractable text is unusable
  input) but keep individual blank pages as empty-string sections rather
  than dropping them (page numbering must stay accurate for citations).
- **Action**: Added `src/parser.py` with `PageSection` (dataclass),
  `ParserError` (exception), and `extract_treaty_sections(path: str |
  Path) -> list[PageSection]`. Added `data/sample_treaty.pdf` (2-page
  mock treaty: page 1 has attachment point/limit/premium, page 2 has
  exclusions) generated by a throwaway script in the scratchpad
  (not committed — only its output, the PDF fixture, is part of the repo).
- **Outcome**: Ran an ad-hoc verification script (not committed — permanent
  parser tests belong to the separate `write-unit-tests` task): happy path
  on `data/sample_treaty.pdf` returns 2 `PageSection`s with correct
  1-indexed `page_number`s and the expected text on each page; a
  malformed PDF (`b"not a pdf at all"`) and a missing file both raise
  `ParserError` with a clear message. Re-ran `pytest tests/` — 2 passed,
  no regressions. Acceptance criteria met. Per the newly added policy
  (never mark a task done without explicit human approval), the task
  is kept open in TASKS.md with a `Status` note pointing here and to
  PR #5, and the `Blocked by: build-pdf-ingestion-parsing` references in
  `build-agentic-workflow-graph` and `write-unit-tests` are restored,
  pending that approval.

- **2026-09-03 12:49:35 update**: Saved the parser's actual output on
  the fixture as `data/sample_treaty_parsed.json` (next to
  `data/sample_treaty.pdf`) so the extraction result is visible without
  re-running Python. Also replaced the placeholder
  `tests/test_parser.py::test_module_imports` with three real tests
  (happy path returns 2 correctly page-numbered sections; malformed PDF
  and missing file both raise `ParserError`) — asked the human first
  whether to do this now vs. defer to `write-unit-tests`; they said do
  it now. `pytest tests/` — 4 passed.

- **2026-09-03 13:09:58 update**: Human asked for a second, richer sample
  treaty — `data/sample_rich_treaty.pdf` — with more specific insurance-
  contract content than the minimal first fixture. Built it with the
  same hand-rolled PDF approach (no PDF-writing library available): 4
  pages covering parties/period/territory/currency, two XoL layers with
  attachment points, limits, premiums, reinstatements and brokerage, a
  10-item exclusions list, and claims/reporting/arbitration/governing-law
  provisions — closer to a real property-cat XoL treaty than the
  original single-section fixture. Verified `extract_treaty_sections`
  returns 4 correctly page-numbered sections with the expected content
  on each page, saved the result as `data/sample_rich_treaty_parsed.json`
  (same naming convention as the first fixture), and added
  `test_extract_treaty_sections_handles_rich_multi_page_treaty` to
  `tests/test_parser.py`. Re-ran the full suite: `pytest tests/ -v` — 5
  passed, no regressions. Updated `README.md`'s example outputs (test
  counts had drifted after this addition) and added a "Sample Treaty
  Fixtures" table documenting both PDFs and their saved parse results.

- **2026-09-03 13:14:15 update**: Human asked to see both treaty tests
  and make them clearly distinct. Renamed
  `test_extract_treaty_sections_returns_one_section_per_page` to
  `test_extract_treaty_sections_handles_minimal_two_page_treaty` so it
  reads as the symmetric counterpart to
  `..._handles_rich_multi_page_treaty` (same "handles_<size>_treaty"
  pattern, naming which fixture and page count each covers). Updated
  the matching command/output examples in `README.md`. Ran both by name
  (`pytest tests/test_parser.py -k "minimal_two_page_treaty or
  rich_multi_page_treaty" -v`) — 2 passed; re-ran the full suite —
  5 passed, no regressions.

- **2026-09-03 13:16:23 update**: Added that `-k` command, its output,
  and the fixture/checks comparison table to `README.md`'s Running
  Tests section, so the "both treaty tests, distinct" example shown in
  chat is also documented for future readers rather than living only
  in the conversation.
- **2026-09-03 13:19:12 — Approved done**: PR #5 merged into `main`
  (merge commit `4c0b571`, 2026-09-03T13:17:45Z). Human explicitly
  approved the task as done. Removed `build-pdf-ingestion-parsing` from
  TASKS.md per the human-approval policy, and restored the
  `Blocked by` references on `build-agentic-workflow-graph` and
  `write-unit-tests` to no longer name it.

## 2026-09-03 13:27:28 — Rearranged backlog: split write-unit-tests, added write-integration-tests

- **Goal**: Human asked to split the standalone `write-unit-tests` task
  across each functionality task that creates new code, with necessary
  Acceptance Criteria added to each, and to replace `write-unit-tests`
  with a new task covering integration tests for the whole workflow
  (success and failure cases).
- **Analysis**: A single trailing `write-unit-tests` task risks unit
  tests being written well after the code they cover (as already
  happened once with `build-pdf-ingestion-parsing`, where
  `tests/test_parser.py` had to be retrofitted after the fact on
  request). The three still-open functionality tasks
  (`implement-deterministic-tools`, `build-agentic-workflow-graph`,
  `create-ui-api`) each produce new testable code, so unit-test
  responsibility and AC belong on each of them directly, matching the
  precedent already set by `define-core-data-schemas` and
  `build-pdf-ingestion-parsing`, which included their own verification.
  A genuine end-to-end integration task is still needed, though — no
  single functionality task exercises the full parse → extract → tool
  calls → analyst pipeline together, and only an integration test can
  catch a contract mismatch between nodes that unit tests (which test
  nodes/functions in isolation) would miss.
- **Decision**: Added `- **Tags**: ..., testing` and an explicit
  "write unit tests as part of this task" instruction plus a
  `tests/test_*.py` file and matching AC to
  `implement-deterministic-tools` (unit tests for both tool functions,
  including a known/unknown cedent and an edge case),
  `build-agentic-workflow-graph` (per-node tests: Extractor on
  well-formed input; Verifier with complete vs. missing/incomplete data;
  Analyst with vs. without a flagged anomaly), and `create-ui-api` (a
  successful upload-and-render run plus one failure case, via
  `streamlit.testing.v1.AppTest` or by testing extracted helpers).
  Added `implement-deterministic-tools`'s missing mock claims CSV to its
  own Files/Details, since `query_historical_claims` needs one to read
  and no such fixture exists yet. Replaced `write-unit-tests` with
  `write-integration-tests`: a single `tests/test_integration.py`
  driving the real `src/workflow.py` graph (no node mocking) against the
  two existing PDF fixtures, with AC requiring both success (two
  fixtures, valid `AnomalyReport`) and three distinct failure paths
  (malformed PDF, cedent with no historical claims, missing required
  treaty term) — "for all cases: success and failed" as asked. Placed it
  right after `build-agentic-workflow-graph` (its only blocker) and
  before `create-ui-api`, and added it as a second blocker on
  `create-ui-api` so the UI is only built once the underlying workflow
  is proven correct end-to-end, not just unit-by-unit.
- **Action**: Edited TASKS.md: added `tests: testing` tag + unit-test
  Details/Files/AC to `implement-deterministic-tools`,
  `build-agentic-workflow-graph`, and `create-ui-api`; removed
  `write-unit-tests`; added `write-integration-tests` (blocked by
  `build-agentic-workflow-graph`); updated `create-ui-api`'s
  `Blocked by` to `build-agentic-workflow-graph, write-integration-tests`.
  `deploy-to-production` is unchanged (still blocked by `create-ui-api`
  only — transitively covers the new task).
- **Outcome**: Verified the new dependency chain is acyclic and each
  `Blocked by` reference names an ID that still exists in TASKS.md
  (grep check). No code changed — TASKS.md restructuring only.

## 2026-09-03 17:23:12 — Task: Implement Deterministic Tools (implement-deterministic-tools)

- **Goal**: Build `query_historical_claims(cedent_name)` and
  `calculate_loss_ratio(attachment_point, limit, claims)` in
  `src/tools.py`, plus a mock historical-claims CSV under `data/` and
  unit tests, per the task's (now-embedded) AC.
- **Analysis**: `src/models.py` already defines `ClaimsData` (cedent_name,
  claim_amount, claim_date) — `query_historical_claims` should return
  `list[ClaimsData]`, reusing that schema rather than inventing a new
  claim shape. No claims CSV exists yet under `data/`. The two existing
  treaty fixtures name cedents "Acme Insurance Co." (`sample_treaty.pdf`)
  and "Meridian Insurance Group, Inc." (`sample_rich_treaty.pdf`) — using
  those same names in the mock CSV means the later
  `write-integration-tests` task can exercise a real
  parse-then-query-claims path without needing a second set of fixture
  names invented from scratch.
  For `calculate_loss_ratio`: the task only says "deterministic math,"
  not which formula. A reinsurance XoL layer's "burn rate" — the
  standard way to express how much of a layer's capacity historical
  losses would have consumed — is: for each claim, the amount ceded to
  this layer is `max(0, min(claim_amount, attachment_point + limit) -
  attachment_point)` (i.e. the claim capped at the layer's top, minus
  everything below the attachment point); loss_ratio is the sum of ceded
  amounts divided by the limit. This uses exactly the three inputs named
  in the task signature and produces a standard, interpretable ratio
  (0 = layer untouched historically, 1.0 = layer would have been fully
  exhausted, >1.0 = losses would have exceeded the layer).
- **Decision**: `query_historical_claims` reads the CSV with the stdlib
  `csv` module (no new dependency — `pandas` isn't in requirements.txt
  and the file is small/flat) and returns `list[ClaimsData]`, so its
  output round-trips through the same Pydantic validation as everywhere
  else. Filtering is case-sensitive exact match on `cedent_name` (no
  fuzzy matching) — the task and AC only specify "a known cedent" vs.
  "an unknown cedent," not partial/fuzzy lookup, and adding fuzzy
  matching would be unrequested scope. `calculate_loss_ratio` takes
  `claims: list[ClaimsData]` (typed, matching the schema) rather than a
  bare `list`, and sums claim_amount directly rather than requiring the
  caller to pre-extract amounts. Named the mock CSV
  `data/historical_claims.csv` (matches the domain term
  "historical claims" used throughout AGENTS.md/TASKS.md), with columns
  `cedent_name,claim_amount,claim_date` mirroring `ClaimsData` field
  order/names exactly, and included both existing fixture cedents plus
  one additional cedent name that appears nowhere in the CSV (to test the
  "unknown cedent" path meaningfully) and one cedent with multiple claim
  rows (to test aggregation).
- **Action**: Added `data/historical_claims.csv` (7 rows across 3
  cedents: "Acme Insurance Co." with 3 claims, "Meridian Insurance
  Group, Inc." — quoted, since its name contains a comma — with 2
  claims, and "Sentinel Mutual Assurance" with 1 claim, unused by any
  existing test so it's available for future integration coverage).
  Implemented `query_historical_claims()` and `calculate_loss_ratio()`
  in `src/tools.py` per the design above. Added `tests/test_tools.py`
  with 5 tests: known cedent (3 rows, correct sum), unknown cedent
  (empty list), a known-inputs loss-ratio calculation (one claim below
  the attachment point ceding 0, one partially ceding), an empty-claims
  edge case (ratio 0.0), and a claim exceeding the layer top (ratio
  capped at 1.0).
- **Outcome**: `pytest tests/test_tools.py -v` — 5 passed. Manually
  verified the CSV's comma-containing cedent name ("Meridian Insurance
  Group, Inc.") is parsed correctly by `csv.DictReader` as a single
  field (2 claims returned, not split on the embedded comma). Full
  suite `pytest tests/ -v` — 10 passed, no regressions. Acceptance
  criteria met.

- **2026-09-03 17:40:48 update**: Human asked to document the tools
  tests in `README.md`. Added a "Run just the tools tests" example
  (command + output + a checks table, matching the existing parser
  section's format) to the Running Tests section, and refreshed the
  full-suite example output (it still said "5 items"/"5 passed" from
  before `test_tools.py` existed — now correctly shows all 10).
  Verified the documented full-suite and tools-only commands both
  produce exactly the output shown: `pytest tests/ -v` — 10 passed;
  `pytest tests/test_tools.py -v` — 5 passed.
- **2026-09-03 17:47:28 — Approved done**: PR #8 merged into `main`
  (merge commit `0b101bd`, 2026-09-03T17:46:35Z). Human explicitly
  approved the task as done. Removed `implement-deterministic-tools`
  from TASKS.md per the human-approval policy, and restored
  `build-agentic-workflow-graph`'s `Blocked by` field (it no longer
  names any blocker, since implement-deterministic-tools was its only
  one and is now closed).

## 2026-09-03 17:52:56 — Task: Build the Agentic Workflow Graph (build-agentic-workflow-graph)

- **Goal**: Implement a LangGraph state machine in `src/workflow.py`
  with an Extractor Node, a Verifier Node, and an Analyst Node, running
  end-to-end on parsed treaty text to produce a populated
  `AnomalyReport`, with unit tests per node covering both the
  success and the incomplete/no-anomaly-vs-anomaly branches.
- **Analysis**: `langgraph` 1.2.11 is installed (`StateGraph`, `END`
  importable). `src/parser.py`'s `extract_treaty_sections()` returns
  `list[PageSection]` (page_number + text) — the natural input to the
  Extractor Node. `src/tools.py` already has `query_historical_claims`
  and `calculate_loss_ratio`, both taking/returning `ClaimsData` from
  `src/models.py`. A gap surfaced while designing the Extractor Node:
  `TreatyTerms` (from the already-closed `define-core-data-schemas`
  task) has no cedent name field, but the Verifier Node must call
  `query_historical_claims(cedent_name)`, and a cedent name is a treaty
  term, not workflow-only scratch state — so it belongs on `TreatyTerms`
  itself, and by extension on the `AnomalyReport` it produces. No
  permanent test file exercises `TreatyTerms` today (only an earlier
  ad-hoc script, not committed), so widening the schema now breaks
  nothing tracked by CI.
  Separately: the task doesn't specify *how* the Extractor Node reads
  terms out of text — via an LLM, or deterministically. `requirements.txt`
  has `anthropic`/`langchain-core`, and a real `ANTHROPIC_API_KEY` is
  present in this environment's `.env`, so an LLM-based extractor is
  possible. But this project's own README describes its LangGraph layer
  as "deterministic agent orchestration," and the two existing PDF
  fixtures use a consistent `Label: value` layout specifically so a
  deterministic extractor can read them.
- **Decision**: Added `cedent_name: str = Field(min_length=1)` to
  `TreatyTerms` in `src/models.py` — a schema widening, not a breaking
  change, since no other code constructs `TreatyTerms` without it yet.
  Built the Extractor Node as **regex-based, not LLM-based**: it's
  free, deterministic (no network call, no flakiness, no per-run cost
  against a real API key), and testable without mocking an LLM client —
  directly in line with "deterministic agent orchestration." The
  tradeoff, made explicit rather than hidden: it only works on treaty
  text using the `Label: value` convention the fixtures use, not
  arbitrary prose; swapping in an LLM-based extractor later would only
  require replacing this one node's internals, since the node's
  input/output contract (`PageSection` list in, `TreatyTerms` or
  `None` + missing-field list out) doesn't change either way.
  For a treaty with multiple layers (the rich fixture has two), the
  extractor takes each field's *first* regex match across pages in page
  order — i.e. Layer 1 — since `TreatyTerms` models a single layer and
  the task doesn't ask for multi-layer extraction.
  Exclusions are extracted by finding the "EXCLUSIONS" section and
  taking every non-empty line after it that doesn't end in `:` (drops
  the intro sentence "This treaty excludes losses ... from:"), stripping
  any leading "N. " numbering — this handles both the minimal fixture's
  unnumbered 2-item list and the rich fixture's numbered 10-item list
  with one rule.
  The Verifier Node's "validates completeness" is interpreted as: if
  the Extractor Node found every required field (cedent, attachment
  point, limit, premium) and successfully built a valid `TreatyTerms`,
  proceed to query historical claims for that cedent; otherwise, mark
  the run incomplete and skip the tool call entirely (there's no cedent
  to query for). Missing/incomplete is a normal, expected branch (e.g. a
  scanned or non-conforming treaty), not an exception — the graph should
  end gracefully with `complete: False`, not crash.
  The Analyst Node flags a `LOW` finding if the cedent has zero
  historical claims (a data-quality flag, not a math result), and a
  `MEDIUM`/`HIGH` finding if the computed loss ratio is
  \>=0.5 / \>1.0 respectively (thresholds chosen as clearly-labeled,
  round, defensible defaults — a layer at or past half-exhausted
  historically is worth a human's attention, past fully-exhausted is
  more urgent — not derived from any real actuarial standard, since
  none was specified).
- **Action**: Added `cedent_name` to `TreatyTerms` in `src/models.py`.
  Implemented `src/workflow.py`: `WorkflowState` (TypedDict),
  `extract_treaty_terms()`/`extractor_node`, `verifier_node`,
  `analyst_node`, `build_workflow_graph()` (LangGraph `StateGraph` with
  a conditional edge after the verifier: complete → analyst, incomplete
  → END), and `run_workflow()`. Added `tests/test_workflow.py` (6
  tests): Extractor on well-formed synthetic sections and on sections
  missing all numeric fields; Verifier with a real cedent (triggers
  `query_historical_claims` against the real CSV, 3 claims returned)
  and with `treaty=None` (flags incomplete, empty claims, no tool
  call); Analyst with no anomalies (moderate loss ratio, non-empty
  claims → `findings == []`) and with at least one (empty claims →
  `LOW` "no historical data" finding).
- **Outcome**: Ran the full graph end-to-end via `run_workflow()` on
  both real fixtures: `sample_treaty.pdf` → complete, loss_ratio 0.3,
  no findings; `sample_rich_treaty.pdf` → complete, loss_ratio 1.25
  (two Meridian claims: 15M and 42M against a 10M/20M Layer-1 layer),
  one `HIGH` finding — confirms both the regex extraction and the
  loss-ratio math are correct against real, richer treaty text, not
  just synthetic test fixtures. `pytest tests/test_workflow.py -v` — 6
  passed. Full suite `pytest tests/ -v` — 15 passed, no regressions.
  Acceptance criteria met.

- **2026-09-03 18:16:32 update**: Human asked how the LangGraph could be
  visualized, then asked to add it to `README.md`. Used
  `app.get_graph().draw_mermaid()` (no extra dependency needed, unlike
  `draw_png()` which requires `pygraphviz`/Graphviz) and pasted its
  exact output — including the `flowchart` config frontmatter block —
  into a new "Workflow Graph" section at the top of `README.md`, with
  the one-line command to regenerate it if the graph's structure
  changes. Verified the pasted diagram is byte-for-byte what that
  command currently produces.

- **2026-09-03 18:26:01 update**: Human asked to view the graph
  visually. Rendered it with `app.get_graph().draw_mermaid_png()` (this
  calls the public `mermaid.ink` rendering service over the network,
  unlike the text-only `draw_mermaid()` used in `README.md` — worth
  noting if this is ever run on a graph structure that shouldn't leave
  the machine, though this one is harmless), showed it inline, then
  saved a permanent copy to `data/workflow_graph.png` on request.

- **2026-09-03 18:31:41 update**: Human asked to implement auto-
  regeneration of the workflow graph diagram whenever `src/workflow.py`
  changes. Split this into three pieces rather than one network-
  dependent hook:
  1. `scripts/regenerate_workflow_graph.py` — the actual regeneration
     logic, extracted so both the hook and a human can call it.
     Replaces the mermaid block in `README.md` between
     `<!-- workflow-graph:start/end -->` markers (added those markers
     first, since find-and-replace needs a stable anchor).
     `--png` additionally regenerates `data/workflow_graph.png`.
  2. `.githooks/pre-commit` — checks whether `src/workflow.py` is
     staged; if so, runs the script and re-stages `README.md`. Does
     **not** regenerate the PNG automatically: `draw_mermaid_png()`
     calls the public `mermaid.ink` service over the network on every
     invocation, and a commit hook that can fail/hang without network
     access, or that silently depends on an external service's
     uptime, is worse than a manual `--png` step run when actually
     wanted. Requires `git config core.hooksPath .githooks` once (added
     to `README.md`'s Setup section) since git hooks aren't
     auto-enabled from a committed `.githooks/` directory.
  3. `tests/test_workflow_graph_docs.py` — a safety net independent of
     the hook: asserts the live graph's mermaid text is contained in
     README's documented block, so drift is caught by `pytest` even if
     someone commits with `--no-verify` or never ran
     `git config core.hooksPath`.
  Tested all three end-to-end with temporary throwaway edits to
  `src/workflow.py` (reverted after, not committed): (a) staging a
  comment-only change correctly reported "already up to date"; (b)
  staging a real structural change (rerouting `analyst -> verifier`
  instead of `analyst -> END`) correctly regenerated and re-staged
  `README.md` with the new edges; (c) tampering with README's mermaid
  block by hand and running the new test correctly failed with a clear
  "out of date, run this command" message. Updated the full-suite
  example output in `README.md` (15 → 16, for the new test).

- **2026-09-03 18:44:29 — Approved done**: PR #10 merged into `main`
  (merge commit `525356b`, 2026-09-03T18:43:36Z). Human explicitly
  approved the task as done. Removed `build-agentic-workflow-graph`
  from TASKS.md per the human-approval policy, and dropped it from the
  `Blocked by` fields on `write-integration-tests` (now unblocked) and
  `create-ui-api` (now blocked only by `write-integration-tests`).

## 2026-09-03 19:05:13 — Task: Write Integration Tests for End-to-End Workflow (write-integration-tests)

- **Goal**: Write `tests/test_integration.py` exercising the full
  pipeline (parse → extract → query claims → calculate loss ratio →
  `AnomalyReport`) end-to-end, covering both success and three
  distinct failure paths, per this task's embedded AC.
- **Analysis**: `run_workflow(sections)` (from `build-agentic-workflow-
  graph`) takes already-parsed `PageSection`s, not a PDF path — but the
  task's Details explicitly says "parse a treaty PDF, extract terms,
  ... as a single run through `src/workflow.py`." There is currently no
  single function covering parse-through-report; callers must chain
  `extract_treaty_sections()` (from `src/parser.py`) and `run_workflow()`
  themselves. That chaining is exactly what an integration test should
  exercise, and will also be needed by the later `create-ui-api` task
  (upload a PDF, get a report) — so it belongs in `src/workflow.py`
  now, not duplicated ad hoc in the test file.
  Of the four required failure cases, only "malformed/unreadable PDF"
  needs a real bad file (already covered structurally by the existing
  parser tests' malformed-PDF fixture pattern). "Unknown cedent" and
  "missing required term" don't correspond to either existing PDF
  fixture (both fixture cedents exist in `historical_claims.csv`, and
  both fixtures have every required field) — inventing a new PDF binary
  for each would add fixture-generation complexity for no real fidelity
  gain, since the workflow's input contract is `list[PageSection]`
  either way.
- **Decision**: Added `run_workflow_from_pdf(path)` to `src/workflow.py`
  — parses then runs the graph, propagating `ParserError` uncaught for
  a malformed/unreadable file (that's already the "clear, caught error"
  the parser guarantees; wrapping it in a second exception type would
  only obscure the real cause). For "unknown cedent" and "missing
  required term," build synthetic `PageSection` lists using the same
  `Label: value` text convention the real fixtures use (identical in
  spirit to `tests/test_workflow.py`'s existing synthetic sections) and
  drive them through `run_workflow()` directly — this is testing the
  full node-to-node pipeline with real graph execution, not mocking any
  node, so it satisfies "rather than mocking individual nodes" even
  though it isn't literally one of the two named PDF fixtures. Using the
  two real PDFs is reserved for the two success cases, exactly as named
  in the AC.
- **Action**: Added `run_workflow_from_pdf(path)` to `src/workflow.py`
  (parses then runs the graph, propagating `ParserError` unchanged).
  Added `tests/test_integration.py` (5 tests): the two success cases on
  the real PDF fixtures; malformed PDF raising `ParserError`; unknown
  cedent (synthetic sections) producing a valid report with a `LOW`
  finding and `loss_ratio == 0.0`; missing required fields (synthetic
  sections) ending with `complete: False` and no `report` key set at
  all (not `None` — LangGraph only sets keys a node actually returns,
  so a skipped Analyst Node leaves `report` absent from the state dict;
  had to switch the assertion from `result["report"]` to
  `result.get("report")` after a `KeyError` caught this). Documented the
  new test file in `README.md` (command, output, checks table) and
  refreshed the full-suite example output (16 → 21).
- **Outcome**: `pytest tests/test_integration.py -v` — 5 passed. Full
  suite `pytest tests/ -v` — 21 passed, no regressions. Re-ran
  `tests/test_workflow_graph_docs.py` specifically — still passes,
  since `run_workflow_from_pdf` adds a function but no new graph nodes/
  edges, so the documented diagram is still accurate. Acceptance
  criteria met.

- **Note**: While committing, the `.githooks/pre-commit` hook (added in
  `build-agentic-workflow-graph`) failed — it ran the bare `python3` on
  `PATH`, which under git's hook execution environment resolved to a
  different, wrong-architecture Python than the project's venv (`arm64`
  venv vs. an `x86_64` `python3` resolved elsewhere), so
  `regenerate_workflow_graph.py`'s `langgraph`/`pydantic` imports failed
  with an `ImportError`. Fixed the hook to invoke
  `$(git rev-parse --show-toplevel)/venv/bin/python3` directly (falling
  back to bare `python3` only if no venv is found) rather than relying
  on `PATH`. This is a small, obviously-correct fix discovered while
  verifying this task's own commit, not a scope change — noting it here
  per that policy rather than opening a separate task for it.

- **2026-09-03 19:18:42 — Approved done**: PR #12 merged into `main`
  (merge commit `65084f9`, 2026-09-03T19:17:47Z). Human explicitly
  approved the task as done. Removed `write-integration-tests` from
  TASKS.md per the human-approval policy, and dropped it from
  `create-ui-api`'s `Blocked by` field (now unblocked — no remaining
  blockers).

## 2026-09-04 09:15:58

### Task: Create User Interface & API (create-ui-api)
- **Goal**: Build a Streamlit UI (`src/app.py`) where uploading a mock
  treaty PDF runs the full agent workflow and renders the resulting
  `AnomalyReport` (with page citations), plus unit tests
  (`tests/test_app.py`).
- **Analysis**: `src/app.py` currently only holds the module docstring
  placeholder (`"""Streamlit UI / FastAPI endpoints."""`); `streamlit`
  is already pinned in `requirements.txt`, so the stack choice was made
  before this task started. `src/workflow.py` already exposes
  `run_workflow_from_pdf(path: str | Path) -> WorkflowState`, which
  parses a PDF (`extract_treaty_sections`, raising `ParserError` on a
  malformed/unreadable/no-text PDF) and runs the
  Extractor→Verifier→Analyst graph, returning a `WorkflowState` dict
  that holds `report: AnomalyReport | None` and `complete: bool`. Two
  terminal cases matter for the UI: (a) `ParserError` from a bad PDF —
  must surface as a clear on-page error, not a crash; (b) a structurally
  valid PDF that's missing required treaty fields — the graph completes
  but routes to `END` before the Analyst node, so `state["report"]` is
  absent (not `None` — LangGraph only sets keys a node actually
  returns; the `write-integration-tests` task hit and documented this
  exact `KeyError` pitfall above). `AnomalyReport` (in `src/models.py`)
  holds `treaty` (with `page_citations: dict[str, field] -> page`),
  `claims`, `loss_ratio`, and `findings: list[AnomalyFinding]`
  (field/description/severity).
- **Decision**: Streamlit is not up for reconsideration here — it's
  already the pinned dependency and the task's own acceptance criteria
  name it explicitly (`streamlit.testing.v1.AppTest`), and the blocked
  P2 task `deploy-to-production` assumes a Streamlit app too, so
  swapping frameworks would be an undiscussed scope change. `run_workflow_from_pdf`
  needs a real filesystem path, so the uploaded `UploadedFile` will be
  written to a `tempfile.NamedTemporaryFile` before calling it (no
  existing helper accepts an in-memory buffer, and adding one to
  `workflow.py` would be scope creep beyond what this task asks for).
  Report formatting (turning `AnomalyReport` into the on-page layout)
  will be extracted into plain helper function(s) in `app.py` so
  `tests/test_app.py` can test formatting logic directly without
  needing a running Streamlit server, per the task's own suggested
  testing approach.
- **Action**: Implementing `src/app.py` (file uploader → temp file →
  `run_workflow_from_pdf` → render treaty terms/claims/loss
  ratio/findings with page citations, catching `ParserError` and the
  missing-report case into on-page error messages) and
  `tests/test_app.py` (one successful upload-and-render case, one
  malformed-PDF failure case, per the task's acceptance criteria).
- **Reasoning**: Reusing `run_workflow_from_pdf` end-to-end (rather than
  re-implementing parsing/graph invocation in the UI layer) keeps the UI
  a thin presentation layer over the already-tested workflow, and
  matches how `write-integration-tests` already exercises the same
  function.
- **Outcome**: Implemented `src/app.py`:
  `analyze_uploaded_pdf(file_bytes) -> AnomalyReport` (writes the
  upload to a `NamedTemporaryFile`, calls `run_workflow_from_pdf`,
  raises `ValueError` with the missing-field names if `state["report"]`
  is absent — mirroring the `result.get("report")` pattern from
  `test_integration.py`), `format_report_markdown(report) -> str`
  (treaty terms with inline page citations, loss ratio, findings with a
  severity icon), and `main()` wiring `st.file_uploader` to both,
  catching `ParserError`/`ValueError` into `st.error(...)` instead of
  letting the app crash. Added `tests/test_app.py` (6 tests): 2 unit
  tests on `format_report_markdown` against a hand-built `AnomalyReport`
  (citations, no-findings case), 2 on `analyze_uploaded_pdf` against the
  real PDF fixtures (success on `sample_rich_treaty.pdf`, `ParserError`
  on garbage bytes), and 2 using `streamlit.testing.v1.AppTest` driving
  the actual `file_uploader` widget end-to-end (success on
  `sample_treaty.pdf` renders the cedent name; malformed bytes produce
  exactly one `st.error` mentioning "Could not read this PDF" with no
  uncaught exception) — satisfying the AC's "one successful
  upload-and-render run and one failure case" both at the helper level
  and through the real widget. `pytest tests/test_app.py -v` — 6
  passed; `pytest tests/ -v` — 27 passed, no regressions. Manually
  started `streamlit run src/app.py` (headless, port 8501) and
  confirmed it serves HTTP 200 with no startup errors, then stopped it;
  didn't drive it through an actual browser since the `AppTest` tests
  already exercise the real upload widget end-to-end against the real
  fixtures, which is a stronger check than a manual click-through for
  this app's one interactive control. Have not yet asked for human
  approval to close the task.

- **2026-09-04 ~09:32:00 (update, exact time not captured live) —
  `ModuleNotFoundError` running locally**: Human
  ran `streamlit run src/app.py` from the repo root and hit
  `ModuleNotFoundError: No module named 'src'` on
  `from src.models import AnomalyReport`. Root cause: `streamlit run`
  only adds the script's own directory (`src/`) to `sys.path`, not the
  repo root, so the absolute `src.*` imports in `app.py` (needed so the
  same imports also work when `tests/test_app.py` does
  `from src.app import ...` with pytest's rootdir on the path) can't
  resolve. This wasn't caught during verification because I tested via
  `AppTest` (which imports `app.py` as a module, same as pytest) and a
  bare `streamlit run` invocation that happened not to surface it in
  that check — I hadn't tried the exact command a user would naturally
  type. Fix: documented `python3 -m streamlit run src/app.py` (repo
  root, venv active) as the run command in a new "Running the App"
  section in `README.md` — `-m` puts the repo root on `sys.path`,
  resolving the imports — rather than restructuring `app.py`'s imports,
  since the existing absolute-import style keeps `src/app.py` and
  `tests/test_app.py` consistent with the rest of the codebase's
  `src.*` import convention. Verified with
  `python -m streamlit run src/app.py --server.headless true`: served
  HTTP 200, no `ModuleNotFoundError`/traceback in the server log.

- **2026-09-04 09:40:05 (scope change)**: Human asked to see "logs
  regarding workflow running, agent work and LLM usage" and to add that
  as an extension of this still-open task rather than a new one.
  Checked `src/`: there are no `logging` calls anywhere in the codebase
  today, and — per `build-agentic-workflow-graph`'s decision above —
  the Extractor node is regex-based, not LLM-based, so there is no LLM
  usage to log; `anthropic`/`langchain-core` are pinned in
  `requirements.txt` but unused in `src/`. Synced `TASKS.md`'s
  `create-ui-api` entry (Details/Files/Acceptance) to add: per-node
  logging via the standard `logging` module in `src/workflow.py`, and a
  collapsible debug panel in `src/app.py` showing those log lines plus
  the raw `WorkflowState`, with an explicit note in the panel that no
  LLM calls occur so there's nothing to show there. Decision: use
  stdlib `logging` (not a custom event list threaded through
  `WorkflowState`) so log lines are captured via a module-level
  `logging.Handler` attached in `app.py` — keeps `workflow.py`
  framework-agnostic (still just plain functions returning dicts, no UI
  awareness) while giving the UI everything it needs to display. Also
  added the human's requested `.gitignore` entries for the
  environment-specific `developing-with-streamlit` skill symlinks under
  `.agents/skills/` and `.claude/skills/` (confirmed both were
  untracked before adding the rule, so this ignores them going forward
  without removing anything from git history).
- **Action**: Invoked the `developing-with-streamlit` skill before
  editing `app.py` (required for Streamlit work) and used its layout
  guidance to pick `st.expander` for the debug panel ("diagnostic
  output that should not dominate the main view"). Added
  `logger = logging.getLogger(__name__)` plus `logger.info(...)` calls
  to `extractor_node`, `verifier_node`, `analyst_node`, and
  `run_workflow_from_pdf` in `src/workflow.py`. In `src/app.py`: split
  `analyze_uploaded_pdf` into `run_workflow_on_bytes` (temp file + run,
  returns the raw `WorkflowState`) and `extract_report` (pulls
  `AnomalyReport` out or raises `ValueError`) — `analyze_uploaded_pdf`
  itself is kept as a thin wrapper of the two so its existing signature/
  behavior, and the tests already written against it, are unchanged.
  Added `_ListLogHandler` (a `logging.Handler` appending formatted
  records to a plain list) and `serialize_state_for_debug` (converts
  `WorkflowState` — including nested `PageSection` dataclasses and
  pydantic models — into a JSON-safe dict). `main()` now attaches the
  handler to the `"src.workflow"` logger for the duration of each run
  (removed in a `finally`), and renders a "Debug: workflow execution"
  expander with an explicit note that no LLM calls occur, the captured
  log lines (`st.code`), and `st.json(serialize_state_for_debug(state))`
  when a state was produced (i.e. except when a `ParserError` fires
  before parsing produces any sections).
- **Outcome**: Added 4 tests to `tests/test_app.py`:
  `test_serialize_state_for_debug_is_json_safe` (plain pytest, no
  `AppTest`, per the skill's "test pure logic with plain pytest"
  guidance), and 2 `AppTest`-based tests confirming the debug expander
  renders log lines mentioning "Extractor"/"Analyst" and the full
  serialized state as JSON on a successful run, and that the panel
  degrades gracefully (no log lines, no JSON block) when a `ParserError`
  fires before any node runs. `pytest tests/test_app.py -v` — 9 passed;
  `pytest tests/ -v` — 30 passed, no regressions. Manually confirmed via
  a Python-level `AppTest` run (outside pytest) that uploading
  `data/sample_treaty.pdf` populates both the log lines (e.g. "INFO
  src.workflow: Parsed 2 page(s) from ...") and the JSON debug state
  with the full `WorkflowState` contents. A Streamlit app the human had
  running on port 8501 will pick up these changes on next page refresh
  (hot-reload) — did not need to restart it. Have not yet asked for
  human approval to close the task.

- **2026-09-04 09:48:57 (scope change)**: Human asked to add a save
  control inside the debug panel: a button to persist the current run's
  captured log lines to a default log file, asking each time whether to
  append to the existing file or clear it and write only this run's
  lines. Synced `TASKS.md`'s `create-ui-api` entry (Details/Acceptance)
  to describe this. Decision: default log path `logs/workflow.log`
  (new `logs/` directory, created on first save) — already covered by
  the existing blanket `*.log` rule in `.gitignore`, so no gitignore
  change needed. Chose `st.segmented_control("Append"/"Overwrite",
  required=True)` for the mode picker over `st.radio` per the
  `developing-with-streamlit` skill's selection-widgets guidance (2
  options, single-select, all visible → segmented control, not
  horizontal radio), paired with a "Save logs to file" button so the
  write only happens on an explicit click, not on every rerun the mode
  picker itself triggers. Kept the file-writing logic in a plain
  `save_logs_to_file(log_lines, mode, path)` helper with no Streamlit
  imports, so it can be unit-tested directly with `tmp_path` rather than
  through `AppTest`.
- **Action**: Added `DEFAULT_LOG_FILE = Path("logs/workflow.log")` and
  `save_logs_to_file(log_lines, mode, path=DEFAULT_LOG_FILE)` (raises
  `ValueError` on an unknown mode; creates the parent directory; `"a"`
  vs `"w"` file mode for append/overwrite) to `src/app.py`. In the debug
  expander, added `st.segmented_control("Save mode", ["Append",
  "Overwrite"], default="Append", required=True)` plus a "Save logs to
  file" button that calls `save_logs_to_file` with the current run's
  `log_lines` on click (warns instead if there are no lines to save).
  Confirmed `logs/workflow.log` doesn't need a new `.gitignore` entry —
  it's already caught by the existing blanket `*.log` rule (verified by
  creating the file and checking `git status` showed nothing new).
- **Outcome**: Added 5 tests to `tests/test_app.py`: 3 plain-pytest
  tests on `save_logs_to_file` (overwrite replaces content, append
  preserves it, missing parent directory is created), and 2 more using
  `AppTest` — one confirming the debug panel still degrades gracefully
  on a `ParserError` (pre-existing test, unaffected), and
  `test_app_save_button_writes_default_log_file` which `chdir`s into
  `tmp_path` (via `monkeypatch`), uploads a real PDF fixture, sets the
  segmented control to "Overwrite", clicks the save button, and asserts
  `tmp_path/logs/workflow.log` was written with the run's log lines and
  a success message appeared. `pytest tests/test_app.py -v` — 13 passed;
  `pytest tests/ -v` — 34 passed, no regressions. Manually verified via
  a Python-level `AppTest` run (outside pytest, in a temp cwd) that
  clicking the button after selecting "Overwrite" wrote
  `logs/workflow.log` with the expected `INFO src.workflow: ...` lines
  and produced the `st.success` confirmation. Have not yet asked for
  human approval to close the task.

- **2026-09-04 10:01:35 (bugfix)**: Human reported the browser Network
  tab showing a new request fire on every click of "Append"/
  "Overwrite," and separately reported seeing "No log lines to save"
  even after a successful report render. Root cause of both: the
  segmented control wasn't inside a form, so selecting a save mode
  triggered an immediate full script rerun on its own — which
  re-parses the uploaded PDF and re-runs the whole workflow just to
  toggle a setting (wasteful, and the extra Network activity the human
  saw). That doesn't fully explain "No log lines to save" on its own
  (a fresh rerun should still repopulate `log_lines` identically each
  time), but killed and had the human restart the Streamlit process
  first to rule out a stale hot-reloaded copy of `src/workflow.py`
  (edited many times this session) as a contributing factor before
  changing more code blind. Fix: wrapped the segmented control and
  save button in `st.form("save_logs_form")` with
  `st.form_submit_button(...)`, per the `developing-with-streamlit`
  skill's best-practice ("Use st.form to batch related inputs and
  rerun only on submit, especially when intermediate widget changes
  would trigger expensive work") — now selecting Append/Overwrite
  causes no rerun at all; only clicking "Save logs to file" does.
  Verified via a standalone `AppTest` run (matching the existing
  `test_app_save_button_writes_default_log_file` sequence: select
  "Overwrite", click submit) that the save still completes correctly
  inside the form. `pytest tests/test_app.py -v` — 13 passed;
  `pytest tests/ -v` — 34 passed, no regressions (existing tests still
  pass unchanged since `AppTest`'s `.run()` forces a rerun regardless of
  form boundaries, so test behavior around `at.segmented_control`/
  `at.button` was unaffected by this change).

- **2026-09-04 10:04:16 (scope change)**: Human asked for a header
  before each saved log block: run date/time, uploaded file name.
  Synced `TASKS.md`'s `create-ui-api` Details to mention it. Added
  `format_log_header(filename, when=None) -> str` to `src/app.py`
  (`"=== Run at YYYY-MM-DD HH:MM:SS | file: <name> ==="`, `when`
  injectable for deterministic testing) and, on save, wrote
  `[header, *log_lines, ""]` instead of bare `log_lines` — the trailing
  `""` gives a blank-line separator between consecutive runs in append
  mode. Used `uploaded_file.name` (already available in `main()`, no
  new plumbing needed) for the filename. Added
  `test_format_log_header_includes_timestamp_and_filename` (plain
  pytest, fixed `when=` for a deterministic assertion) and extended
  `test_app_save_button_writes_default_log_file` to assert the header
  line appears in the written file. `pytest tests/test_app.py -v` — 14
  passed; `pytest tests/ -v` — 35 passed, no regressions.

- **2026-09-04 15:47:27 (small fix)**: Human asked to align the saved
  log line format with what an IDE console shows; clarified via
  `AskUserQuestion` that this meant a per-line timestamp using the
  standard Python `logging` convention (`YYYY-MM-DD HH:MM:SS,mmm`), not
  PyCharm's own internal `idea.log` format. Changed
  `_ListLogHandler`'s formatter in `src/app.py` from
  `"%(levelname)s %(name)s: %(message)s"` to `"%(asctime)s %(levelname)s
  %(name)s: %(message)s"` — a one-line change since `%(asctime)s` is a
  built-in `logging.Formatter` field, no new plumbing needed. This
  affects both the debug panel's `st.code` display and the saved
  `logs/workflow.log` file, since both read from the same `log_lines`
  list. `pytest tests/ -v` — 35 passed, unaffected (existing assertions
  are substring checks, not exact-format matches). Manually verified via
  a standalone `AppTest` run that saved lines now read like
  `2026-09-04 15:47:59,920 INFO src.workflow: Parsed 4 page(s) from
  ...`.

- **2026-09-04 15:58:23 (README fix)**: Human asked to check
  `README.md`/`TASKS.md`/`REASONING.md` and confirmed the review
  finding: every other test file (`test_parser.py`, `test_tools.py`,
  `test_workflow.py`, `test_integration.py`) has a "Run just X" section
  in `README.md` with example output and a per-test table, but
  `tests/test_app.py` (14 tests, added by this task) had none, and the
  top "Running Tests" full-suite example was stale at "21 passed"
  (actual: 35). Fixed both: refreshed the full-suite example output to
  the real 35-item run, and added a matching "Run just the app tests"
  section for `tests/test_app.py` with real example output and a
  14-row table describing each test. `pytest tests/ -v` — 35 passed,
  unaffected (docs-only change).

- **2026-09-04 18:04:34 (README addition)**: Human asked for
  instructions on running the app in a browser and interacting with it.
  Extended `README.md`'s "Running the App" section: noted the printed
  `Local URL` and that the process stays up until `Ctrl+C`, then added
  a numbered "Using the app" walkthrough — upload a PDF (pointing at
  both `data/` fixtures), what renders and how failures surface, what's
  in the debug expander (per-node log, raw JSON state, the Append/
  Overwrite save control and where it writes), and that uploading a
  different PDF simply reruns the app. `pytest tests/ -v` — 35 passed,
  unaffected (docs-only change).

## 2026-09-04 19:04:51 — New task: Fix Claude Code Review CI Check (fix-claude-review-ci-secret)

- **Goal**: Record a new P2 task for a CI gap discovered while checking
  the status of PR #14 (`docs/branch-push-discipline`) and PR #15
  (`task/create-ui-api`) on GitHub.
- **Analysis**: Both PRs show `mergeable: true` with no manual reviews,
  but the automated `Claude Code Review` GitHub Actions check
  (`claude-review`) failed on both, with the identical error in each
  run's log: `Environment variable validation failed: Either
  ANTHROPIC_API_KEY, CLAUDE_CODE_OAUTH_TOKEN, or workload identity
  federation ... is required when using direct Anthropic API.` The
  workflow fails before ever reaching the actual review step (it fails
  during Claude Code's own setup), and both PRs hit the exact same
  error regardless of their very different diffs (2 files vs. 7 files
  changed) — so this is a repo-level CI configuration gap (a missing
  `ANTHROPIC_API_KEY`/`CLAUDE_CODE_OAUTH_TOKEN` secret under this
  repo's GitHub Settings → Secrets and variables → Actions), not
  something wrong with either PR's actual content.
- **Decision**: This isn't fixable from a local checkout or by an
  agent — it requires repo admin access on GitHub to add the secret,
  so it goes in the backlog as P2 (valuable, not blocking any of the
  currently open task work) rather than being worked now.
- **Action**: Added `fix-claude-review-ci-secret` to `TASKS.md`'s P2
  section, documenting the exact error, that it was confirmed
  identical on PR #14 and PR #15, and that the acceptance criterion is
  a real review comment appearing on a subsequent push instead of the
  env-var failure.
- **Reasoning**: Following the "Add new tasks discovered during work"
  policy — this was found incidentally while checking PR status, not
  part of either open PR's scope, so it's tracked as its own backlog
  item rather than silently folded into either PR.

- **2026-09-04 16:10:50 — Approved done**: PR #15 merged into `main`
  (merge commit `67f7135`, 2026-09-04T16:10:50Z). Human explicitly
  approved the task as done. Removed `create-ui-api` from TASKS.md per
  the human-approval policy, and dropped it from
  `deploy-to-production`'s `Blocked by` field (now unblocked — no
  remaining blockers).

- **2026-09-04 19:15:03 (reprioritize)**: Human asked to move
  `deploy-to-production` from P2 to P1, now that its only blocker
  (`create-ui-api`) is done. Moved the entry (unchanged otherwise) in
  `TASKS.md` from the P2 section to the top of P1.

## 2026-09-04 20:55:54 — New task: Explore a Hybrid Regex+LLM Extraction Fallback (explore-hybrid-regex-llm-fallback)

- **Goal**: Record a new backlog item after walking the human through
  why the Extractor Node is regex-based rather than LLM-based (see
  `build-agentic-workflow-graph`'s original decision above) and the
  pros/cons of each approach — the human asked to track a hybrid
  regex-first, LLM-fallback approach as something to actually explore.
- **Analysis**: Regex-only extraction only works on the `Label: value`
  convention the two mock fixtures use; it extracts nothing from prose,
  synonyms, or reordered clauses, which is exactly the shape real-world
  treaty PDFs would take. `anthropic`/`langchain-core` are already
  pinned in `requirements.txt` but unused — so the dependency cost of
  trying an LLM path is already paid, just not exercised.
  `extractor_node`'s contract (`PageSection` list in → `TreatyTerms` or
  `None` + missing-fields list out) was deliberately kept
  implementation-agnostic when it was built, so a fallback doesn't
  require changing anything upstream/downstream of the node.
- **Decision**: Filed as P3 ("someday/maybe"), not P1/P2 — this is
  explicitly framed as a research/spike task (a written recommendation
  with observed tradeoffs), not a committed feature with a hard
  acceptance bar requiring a merged implementation. That distinction is
  written directly into the task's Details/Acceptance so whoever picks
  it up next doesn't over-scope it into a full LLM integration before
  the tradeoffs are actually validated.
- **Action**: Added `explore-hybrid-regex-llm-fallback` to `TASKS.md`'s
  P3 section, referencing `build-agentic-workflow-graph`'s original
  decision and pointing at `extractor_node`'s existing contract as the
  reason a fallback wouldn't need to change anything else.
- **Reasoning**: Following the "Add new tasks discovered during work"
  policy — this came directly out of a design-rationale discussion
  with the human, not out of implementation work on an existing task,
  so it's tracked as its own backlog item.

## 2026-09-04 21:03:07

### Task: Deploy to Production / Cloud (deploy-to-production)
- **Goal**: Get the Streamlit app (`src/app.py`) deployed to a live
  public URL — Streamlit Community Cloud, Render, or Hugging Face
  Spaces — per the task's Acceptance criterion, so a sample treaty
  upload there runs the full workflow and matches local behavior.
- **Analysis**: Checked for a matching skill (per the new
  "check for a matching skill first" step added in
  `docs/branch-push-discipline`) — no skill in this environment covers
  deploying to Streamlit Community Cloud, Render, or Hugging Face
  Spaces specifically; the closest ("run") only covers running the app
  locally. All three named platforms are external hosted services that
  require an account and, for an automatable path, an API token/secret
  I don't have and can't create myself:
  - **Streamlit Community Cloud** has no public deploy API — deploying
    requires signing in at share.streamlit.io with GitHub OAuth and
    clicking "Deploy" through the web UI. Not automatable from a local
    checkout at all.
  - **Render** and **Hugging Face Spaces** do have APIs/CLIs, but both
    need an account-scoped API key/token that isn't present in this
    environment (unlike, say, `ANTHROPIC_API_KEY`, which the earlier
    `build-agentic-workflow-graph` task found already configured).
  This is the same category of blocker as `fix-claude-review-ci-secret`
  from earlier this session — a real external-account/credential step
  only the human can take, not something to work around by guessing.
- **Decision**: Before doing anything else, ask the human which
  platform to target and whether they already have an account/token
  for it, rather than picking one unilaterally or attempting a path
  that will just fail partway through for lack of credentials.
- **Action**: Claimed the task (`(@claude)` in TASKS.md), created
  `task/deploy-to-production` branch. Asking the human now via
  `AskUserQuestion` before any further action.
- **Update**: Human chose Streamlit Community Cloud. Confirmed
  `iva2020dev/reinsurance-treaty-agent` is a **public** GitHub repo
  (`gh repo view --json visibility` → `PUBLIC`), so no special
  permissions are needed for Community Cloud (free tier).
  While prepping, found a real compatibility risk worth fixing before
  handing off the manual deploy step: Streamlit Cloud's launcher
  behaves like a bare `streamlit run src/app.py`, which is the exact
  invocation this repo's own README already documented as broken
  (`ModuleNotFoundError: No module named 'src'`, from the earlier
  `create-ui-api` session) — so the deployed app would likely have
  hit the same error. Confirmed the root cause precisely by reading
  the installed `streamlit` package's own source:
  `streamlit/web/bootstrap.py:73` does
  `sys.path.insert(0, os.path.dirname(main_script_path))` — i.e. it
  adds only `src/` (the script's own directory) to `sys.path`, never
  the repo root, regardless of invocation method (bare `streamlit run`,
  `python -m streamlit run`, or Streamlit Cloud's own launcher, which
  uses this same `bootstrap.py`).
  **Decision**: Fix this at the source in `src/app.py` itself, rather
  than only documenting a workaround command Streamlit Cloud won't
  follow — added `sys.path.insert(0, str(_REPO_ROOT))` (computed via
  `Path(__file__).resolve().parent.parent`) at the top of the file,
  before the `src.*` imports. This makes the file resolve its own
  imports correctly no matter how it's launched, which is exactly what
  a file Streamlit Cloud will `exec()` directly needs.
  **Verified** by replicating Streamlit's own script-execution
  mechanism precisely (`sys.path.insert(0, os.path.dirname(...))` then
  `exec(compile(...))`, run from an unrelated `/tmp` cwd to remove any
  ambiguity) — import succeeded after the fix; confirmed still true via
  `pytest tests/ -v` (35 passed) and a live `streamlit run src/app.py`
  (no `-m`) serving HTTP 200 with no errors in its log. Also confirmed
  `src/tools.py`'s `HISTORICAL_CLAIMS_CSV` path is already
  `__file__`-relative (not cwd-dependent), so that data lookup needs no
  equivalent fix, and that all files the app needs at runtime
  (`data/historical_claims.csv`, the two sample PDFs) are tracked in
  git, not just present locally.
  Updated `README.md`: added a "Deployment" section with the manual
  Streamlit Community Cloud setup steps (sign in, Create app, repo
  `iva2020dev/reinsurance-treaty-agent` / branch `main` / main file
  `src/app.py`, no secrets needed since there are no LLM/API calls) and
  a note on why it auto-redeploys on push; also updated "Running the
  App" since bare `streamlit run src/app.py` now works too (the `-m`
  requirement is gone, though `-m` still works as before).
  This PR prepares everything that can be done from a local checkout;
  actually clicking "Deploy" at share.streamlit.io requires GitHub
  OAuth in a browser, which only the human can do — once merged to
  `main` and deployed, the human needs to share the resulting public
  URL back so the Acceptance criterion (upload a sample PDF there,
  confirm it matches local behavior) can be verified.
- **Outcome**: Human deployed and shared the live URL:
  https://reinsurance-treaty-agent-extraction.streamlit.app/. Checked
  the platform's own `/api/v2/app/status` endpoint —
  `{"status":5,"viewerAuthEnabled":false,"isCpuThrottled":false,
  "streamlitVersion":"1.63.0",...}` — confirming it's running,
  publicly viewable, and on the expected Streamlit version (matches
  local). A plain `curl`/`WebFetch` to the app's root path got
  redirected to a `/-/login` page; this looked like a viewer-access
  restriction at first, but the human confirmed the app loads directly
  with no login prompt in an actual browser, including incognito (no
  cookies) — and the `viewerAuthEnabled: false` status field agrees.
  Concluded the redirect is Streamlit Cloud's own anti-automation/edge
  gate on the root path for non-browser clients, unrelated to the
  app's real (public) access setting — not an app or access-config
  bug, just a limit of what an automated HTTP check can observe here.
  Human then uploaded `sample_rich_treaty.pdf` on the live app and
  confirmed the rendered report: loss ratio 1.25, one `HIGH` finding
  ("Historical losses (loss ratio 1.25) would have exceeded this
  layer's limit.") — matches `test_full_pipeline_success_rich_treaty`
  exactly, confirming the deployed app's behavior is identical to
  local. Acceptance criterion met.
  Added the live URL to `README.md` (a top-level "Live demo" line, and
  inline in the Deployment section's setup steps) per the human's
  explicit request, since the task's own stated purpose was "a live
  public URL for the portfolio" — documenting it in the repo directly
  serves that goal.
- **2026-09-04 22:00:46 update**: Human asked for a "separate section
  Deployment" and to check its content. It already existed (added in
  this same task's earlier commit) but sat at the very end of the
  file, after "Sample Treaty Fixtures" — likely why it read as
  missing. Asked the human where it should live; they chose right
  after "Running the App" (before "Running Tests"), grouping the two
  action-oriented sections (run locally, then how it's deployed)
  ahead of the more reference-y test/fixture sections. Moved the whole
  `## Deployment` block (setup steps, keeping-up-to-date note,
  compatibility note) there unchanged except for one real content gap
  found while reviewing: added that Streamlit Community Cloud's free
  tier requires the GitHub repo to be **public** (verified true for
  this repo via `gh repo view` earlier in this task) — a real
  prerequisite the section never stated, which would silently block
  anyone following these steps from a private fork. `pytest tests/ -v`
  — 35 passed (docs-only change, unaffected).

- **2026-09-04 19:02:30 — Approved done**: PR #20 merged into `main`
  (merge commit `46f60ce`, 2026-09-04T19:02:30Z). Human explicitly
  approved the task as done. Removed `deploy-to-production` from
  TASKS.md per the human-approval policy.

- **2026-09-04 22:06:22 (reprioritize)**: Human asked to move
  `explore-hybrid-regex-llm-fallback` from P3 to P1 — no longer
  "someday/maybe," now core work that should ship next. Moved the
  entry (unchanged otherwise) from the P3 section to the top of P1 in
  `TASKS.md`. Left its Details/Acceptance as-is (still framed as a
  research/spike with a written-recommendation bar, not a required
  merged implementation) since the human only asked to reprioritize,
  not to change scope.

## 2026-09-04 22:20:39 — Task: Restructure explore-hybrid-regex-llm-fallback (docs only)

- **Goal**: Human asked to clarify/restructure this task's `TASKS.md`
  entry into labeled sections (Description, Plan/steps, etc.), rather
  than the flat `Details`/`Acceptance` it had, and to lock in concrete
  decisions rather than leave it fully open-ended: a
  `sample_rich_fuzzy_treaty.pdf` fixture specifically built to defeat
  the regex extractor, a real LLM fallback flow (compact/modern/cheap/
  fast model), UI updates to stay informative about which extraction
  path ran, appropriate logging, and preserving intermediate + final
  results. Used `EnterPlanMode` given the architectural surface (new
  graph node, new dependency integration, UI/state changes, model
  choice) even though this particular PR only touches `TASKS.md`/
  `REASONING.md` — the plan itself is the thing being delivered here,
  for whoever picks the task up next.
- **Analysis**: Grounded the plan in the actual codebase rather than
  writing an abstract recommendation: `extract_treaty_terms()`'s
  contract (`TreatyTerms | None` + `missing_fields`) is what any
  fallback must preserve; `anthropic` 1.3.0 is already installed and
  `.env` already has a real `ANTHROPIC_API_KEY` (confirmed present,
  not read/printed) but nothing in `src/` uses it yet; both existing
  PDF fixtures were hand-rolled raw `%PDF-1.4` bytes (no PDF-writing
  library installed), so the new fixture must follow suit;
  `data/historical_claims.csv` has a third cedent, "Sentinel Mutual
  Assurance" ($900,000 claim, unused by either existing fixture) — a
  clean choice for a fresh, deterministic end-to-end case; `src/app.py`'s
  debug panel already renders the full `WorkflowState` as JSON and
  captures every `"src.workflow"` logger call, so extending state and
  logging through the existing node pattern gets picked up by the UI
  for free; the workflow graph diagram is already auto-regenerated and
  cross-checked by `tests/test_workflow_graph_docs.py`, so adding a
  graph node is already tooled for; the app is live on Streamlit
  Community Cloud with no secrets configured today, so a real LLM call
  will need a production secret added there too, and must degrade
  gracefully (not crash) if that secret is ever missing.
- **Decision**: Locked in, in the plan (not yet implemented):
  - A **dedicated new LangGraph node** (`llm_fallback_extractor`),
    not folded into `extractor_node` — makes the graph diagram and
    per-node debug logs show plainly whether a run needed the
    fallback, and keeps `extractor_node` itself simple/unchanged.
  - **Claude Haiku 4.5** (`claude-haiku-4-5-20251001`) as the model —
    the current lightweight/cheap/fast tier, matching the human's
    "compact, modern, light-weight, good performance, not expensive"
    ask; Sonnet/Opus would be overkill for a short structured-
    extraction task.
  - **Tool-use (forced structured output)**, not free-text parsing,
    for reliability and to match the existing `page_citations` shape.
  - **No OCR/vision** for this specific failure mode — the fixture
    will have fully extractable text, just non-`Label: value` prose;
    OCR/vision addresses a different failure mode (genuinely scanned
    PDFs, which `parser.py` already rejects with `ParserError` before
    extraction) and is called out explicitly as future/out-of-scope
    rather than silently ignored.
  - `WorkflowState` gains `extraction_method`/`llm_error` fields
    (additive only) so intermediate (regex attempt) and final (LLM or
    regex result) state both stay visible — no change to
    `extractor_node`'s own contract.
  - Graceful degradation is explicit in the plan: any LLM-call
    failure (including a missing key) falls back to today's existing
    "incomplete" behavior, never a crash.
- **Action**: Rewrote `explore-hybrid-regex-llm-fallback`'s `TASKS.md`
  entry: `Details` → `Description` (why) + a 6-step numbered `Plan`
  (fixture, fallback node + model/structured-output/input/safety
  choices, state/contract, UI, config, tests), updated `Files` to
  reflect the fuller surface (`src/app.py`, `src/models.py`,
  `tests/test_app.py`, `README.md`, `requirements.txt` in addition to
  `src/workflow.py`), and rewrote `Acceptance` to describe the actual
  end-to-end behavior expected (fallback triggers on the new fixture,
  UI indicates it, debug panel shows both intermediate and final
  state, existing fixtures unaffected, graceful no-key degradation).
- **Reasoning**: This elevates the task from "write a recommendation"
  to "here is the concrete implementation plan an engineer would
  follow" — deliberately, since the human's request was directive
  (create the fixture, set the flow, update the UI) rather than
  open-ended research framing. No `src/` code changes were made in
  this pass; that's the next pickup of this task, now with a plan to
  follow instead of a blank slate.
- **Outcome**: `pytest tests/ -v` — 35 passed, unaffected (docs-only
  change).

## 2026-09-04 22:32:05 — Rearranged backlog: split explore-hybrid-regex-llm-fallback into a sequenced task set

- **Goal**: Human asked to proceed with
  `explore-hybrid-regex-llm-fallback` with the specific goal of
  "creat[ing] a tasks set to implement" the hybrid approach — i.e.
  split the single restructured task (Description + 6-step Plan) into
  discrete, individually-pickup-able tasks, rather than starting to
  write `src/` code directly. Matches the precedent set by the
  `13:27:28` backlog rearrangement above (splitting `write-unit-tests`
  into per-task work plus a dedicated `write-integration-tests`): when
  a single task bundles genuinely separable pieces of work with a
  natural build order, split it into a chain rather than leaving one
  oversized entry.
- **Analysis**: The approved 6-step Plan already has a natural
  dependency order: the fuzzy fixture (step 1) is needed before the
  fallback node can be tested against a real "regex fails" case (step
  2); the node's `extraction_method`/`llm_error` state (folded into
  step 2, since it's the same code change) must exist before the UI can
  surface it (step 4); the UI note must exist before a true end-to-end
  test can assert on it, and deployment config (step 5) naturally pairs
  with that final end-to-end verification (step 6). That gives four
  tasks, not six — steps 3 (state/contract) and 2 (fallback node) are
  the same PR's worth of `src/workflow.py` work, so they're one task,
  not two; likewise step 5 (config) pairs naturally with step 6's
  end-to-end test as the final task, since deployment secrets only
  matter once the whole flow is proven to work.
- **Decision**: Four tasks, in a straight `Blocked by` chain:
  1. `build-fuzzy-treaty-fixture` (no blocker) — the fixture plus tests
     proving it defeats regex, standalone from any LLM code.
  2. `implement-llm-fallback-node` (blocked by #1) — the actual
     `llm_fallback_extractor` node, model/structured-output/safety
     choices, and the additive `WorkflowState` fields, with mocked-
     client unit tests (no real API calls needed to verify the node's
     logic in isolation).
  3. `update-ui-llm-fallback` (blocked by #2) — the on-page fallback
     note and confirming the debug panel surfaces the new state, via
     `AppTest`.
  4. `integration-test-llm-fallback-deploy-config` (blocked by #3) —
     the one true end-to-end test with a real API call (skipped
     without a key) plus the Streamlit Cloud secret documentation,
     since this is the only point where "does the whole thing actually
     work together, and is it deployable" can be verified.
  Verified the chain is acyclic and every `Blocked by` ID resolves to
  a task still present in `TASKS.md` (grep check, matching how the
  prior split was verified).
- **Action**: Replaced the single `explore-hybrid-regex-llm-fallback`
  entry in `TASKS.md` with the four tasks above, each carrying its own
  ID/Tags/Details/Files/Acceptance derived directly from the relevant
  slice of the original 6-step Plan — no content was invented beyond
  what was already decided in the prior restructuring pass.
- **Reasoning**: Following the same policy as the earlier split: no
  `src/` code changes in this pass, `TASKS.md` restructuring only. Each
  task is now independently sized and pickup-able (matching this
  repo's established task granularity), with tests bundled into their
  own task per the `create-ui-api`/`implement-deterministic-tools`
  convention ("write tests as part of this task, don't defer") rather
  than as a separate trailing testing task.
- **Outcome**: `pytest tests/ -v` — 35 passed, unaffected (docs-only
  change). Confirmed via `grep` that all four `**ID**`s are unique and
  the single `**Blocked by**` chain (`build-fuzzy-treaty-fixture` →
  `implement-llm-fallback-node` → `update-ui-llm-fallback` →
  `integration-test-llm-fallback-deploy-config`) is linear with no
  cycles.

## 2026-09-05 18:20:21 — Task: Build the Fuzzy Treaty Fixture (build-fuzzy-treaty-fixture)

- **Goal**: Hand-roll `data/sample_rich_fuzzy_treaty.pdf` — same
  substantive treaty facts as a real document, but phrased as prose
  instead of the `Label: value` convention — so `extract_treaty_terms()`
  genuinely fails to find required fields via regex, giving the later
  `implement-llm-fallback-node` task something real to fall back on.
- **Analysis**: `_FIELD_PATTERNS` in `src/workflow.py` requires the
  exact literal strings `"Cedent:"`, `"Attachment Point:"`, `"Limit:"`,
  `"Reinsurance Premium:"` immediately followed by a value — so prose
  simply needs to avoid those four literal substrings to defeat every
  required field, not just one (stronger than the task's minimum bar
  of "at least one"). `data/historical_claims.csv` already has
  "Sentinel Mutual Assurance" (exact string, no comma so no CSV
  quoting needed) with one $900,000 claim, unused by either existing
  fixture — using it here means a later end-to-end test gets a real,
  non-empty `query_historical_claims` result. Both existing fixtures
  were hand-rolled as raw `%PDF-1.4` objects with manually-computed
  xref byte offsets (no PDF-writing library installed, confirmed
  still true — `pip list` shows no `reportlab`/`fpdf`); computing
  those offsets by hand is exactly the kind of thing worth automating
  instead of repeating error-prone arithmetic, so this fixture is
  built by a small script (not committed, per the same convention
  `build-pdf-ingestion-parsing` used) that constructs the objects and
  computes real xref offsets from the actual serialized bytes, rather
  than hand-typing them. `TreatyTerms.limit` (per
  `calculate_loss_ratio`) is the *width* of the layer above the
  attachment point, not the absolute top — worth being explicit about
  in the prose so the wording is unambiguous for whoever implements
  the LLM extractor next, not just defeat-the-regex noise.
- **Decision**: 4 pages, deliberately avoiding all four
  `_FIELD_PATTERNS` literals anywhere in the text (not just one), so
  regex fails completely rather than partially — a cleaner, more
  useful test case for the LLM fallback than a fixture that trips up
  regex on only one field:
  1. Parties/intro — names "Sentinel Mutual Assurance" as the ceding
     company in a sentence, never as `Cedent: ...`.
  2. Financial terms — states the attachment point ($2,500,000), the
     layer width ("a further five million dollars ($5,000,000) of
     loss in excess of the attachment point," to keep the same
     attachment+width semantics as the real fixtures, not the
     absolute layer top) and premium ($400,000) in full sentences.
  3. Exclusions — a prose paragraph (not a numbered list) naming the
     same categories the real fixtures use; not required to parse
     correctly since `exclusions` isn't in `_REQUIRED_FIELDS`.
  4. Claims/reporting/arbitration/governing law — realism only,
     matching the rich fixture's page 4 flavor.
  Expected numbers, for later tasks to assert against:
  attachment_point=2,500,000, limit=5,000,000 (layer top 7,500,000),
  reinsurance_premium=400,000, cedent="Sentinel Mutual Assurance"
  (one $900,000 historical claim → loss ratio 0.18 if/when the LLM
  fallback successfully extracts these and the graph runs to
  completion).
- **Action**: Building `data/sample_rich_fuzzy_treaty.pdf` +
  `data/sample_rich_fuzzy_treaty_parsed.json`, adding
  `test_extract_treaty_sections_handles_fuzzy_rich_treaty` (or
  similar) to `tests/test_parser.py` (proves `pypdf` gets real
  non-empty text, not a `ParserError`), a workflow-level test in
  `tests/test_workflow.py` proving `extract_treaty_terms()` returns a
  non-empty `missing_fields` list on it, and a `README.md` Sample
  Treaty Fixtures table row.
- **Outcome**: Reused the existing `make_sample_pdf.py` helper (found
  in an earlier session's scratchpad — it already computes xref
  offsets from the actual serialized bytes via `len(buf)` tracking,
  not hand-typed arithmetic) and wrote a `make_fuzzy_treaty.py` script
  driving it with the four prose pages described above. Verified the
  generated PDF against the real code before committing it: `pypdf`
  extracts real, non-empty text per page (confirmed no `ParserError`),
  and `extract_treaty_terms()` returns `treaty=None` with
  `missing_fields == ["cedent_name", "attachment_point", "limit",
  "reinsurance_premium"]` — regex fails on *all four* required fields,
  not just the task's minimum bar of one. Noticed the extracted text
  contains "quoteright" (U+2019) in place of every ASCII apostrophe
  (e.g. "Reinsurer's" → "Reinsurer's") — traced this to Helvetica's
  default `StandardEncoding` mapping code 0x27 to that glyph, not
  plain apostrophe; confirmed the *existing* `sample_rich_treaty_parsed.json`
  has the identical artifact ("Cedent’s employees"), so this is
  pre-existing, consistent hand-rolled-PDF behavior, not a new bug —
  left as-is rather than over-engineering a fix for a test fixture.
  Copied the verified PDF into `data/sample_rich_fuzzy_treaty.pdf`,
  generated `data/sample_rich_fuzzy_treaty_parsed.json` via the real
  `extract_treaty_sections()` (same convention as the other two
  fixtures). Added `test_extract_treaty_sections_handles_fuzzy_rich_treaty`
  to `tests/test_parser.py` and `test_extract_treaty_terms_fails_on_fuzzy_prose_treaty`
  to `tests/test_workflow.py` (the latter asserting the exact
  4-field `missing_fields` set via the real fixture, not synthetic
  sections — matching the task's "regex genuinely fails on it"
  acceptance bar). Added the fixture to `README.md`'s Sample Treaty
  Fixtures table and refreshed every stale test-count example output
  in `README.md` that the two new tests shifted (full suite 35→37,
  `test_parser.py` 4→5 including its keyword-filter example, and
  `test_workflow.py` 6→7). `pytest tests/ -v` — 37 passed, no
  regressions. Acceptance criteria met; have not asked for human
  approval to close the task yet.

- **2026-09-05 15:37:13 — Approved done**: PR #25 merged into `main`
  (merge commit `60b385c`, 2026-09-05T15:37:13Z). Human explicitly
  approved the task as done. Removed `build-fuzzy-treaty-fixture` from
  TASKS.md per the human-approval policy, and dropped it from
  `implement-llm-fallback-node`'s `Blocked by` field (now unblocked —
  no remaining blockers).

## 2026-09-05 18:43:49 — Task: Implement the LLM Fallback Extraction Node (implement-llm-fallback-node)

- **Goal**: Add a new `llm_fallback_extractor` LangGraph node to
  `src/workflow.py`, invoked only when the regex extractor's
  `missing_fields` is non-empty, using Claude Haiku 4.5 with forced
  tool-use structured output, additive `WorkflowState` fields
  (`extraction_method`, `llm_error`), and graceful degradation on any
  failure — per the plan already locked into `TASKS.md`.
- **Analysis**: Investigated the installed `anthropic` SDK (1.3.0)
  directly rather than assuming its API shape: `Anthropic(api_key=...,
  timeout=...)` accepts a per-client timeout; `messages.create` takes
  `tools`/`tool_choice`; forcing a specific tool is
  `tool_choice={"type": "tool", "name": "..."}` (confirmed via
  `anthropic.types.ToolChoiceToolParam`'s source). Constructing
  `anthropic.Anthropic()` with **no** API key at all does *not* raise
  — the error only surfaces on the actual request, and as a plain
  **`TypeError`** ("Could not resolve authentication method..."), not
  an `anthropic.AnthropicError` subclass. Separately, tried a real
  call against this environment's `.env` key and got
  `anthropic.AuthenticationError: ... API key is invalid` (401) — so
  this environment's key is present but not usable, confirming (a)
  the task's own scoping to mocked-client tests only for this task
  (a real successful call can't be verified here) and (b) that a
  bare `except anthropic.AnthropicError` would miss the
  missing-key `TypeError` case entirely — two structurally different
  exceptions for what's conceptually the same "no working
  credentials" failure. `python-dotenv` is pinned but unused; nothing
  in `src/` loads `.env` today.
- **Decision**: Catch a broad `except Exception` around the whole
  API-call-and-parse block (not an enumerated list of SDK exception
  types) — justified concretely by the finding above, not just
  defensive habit; every failure path (missing key, invalid key,
  network/timeout, malformed tool response, a `ValidationError`
  building `TreatyTerms` from the model's output) must degrade to the
  same graceful "extraction_method=none, llm_error=<message>" result
  rather than crashing the run, and no single exception hierarchy
  covers all of them. Call `load_dotenv()` once at module import in
  `src/workflow.py` (harmless if `.env` doesn't exist, e.g. in
  production where the key comes from a real environment variable /
  Streamlit secret instead). Tool schema's `limit` field description
  explicitly states it's the *width* above the attachment point, not
  the absolute top — matching the same semantic the regex path and
  `calculate_loss_ratio` already use, so the model can't reasonably
  extract an ambiguous value. `extractor_node` gains
  `extraction_method: "regex"` on its own success path (so the debug
  panel always shows which path produced a report, even when the LLM
  node never runs); the LLM node sets `"llm"` on success or leaves
  `"none"` (the state's default, set in `run_workflow`'s initial
  invoke dict) plus `llm_error` on failure.
- **Action**: Implemented in `src/workflow.py`: `load_dotenv()` at
  import time; `_TREATY_EXTRACTION_TOOL` (forced tool-use schema
  mirroring `TreatyTerms`, `limit`'s description spelling out the
  width-not-top semantic); `llm_fallback_extractor(state)` (builds a
  page-tagged prompt via a new `_format_sections_for_llm` helper,
  calls Claude Haiku 4.5 with `tool_choice` forcing the one tool,
  constructs `TreatyTerms` from the tool-use block's `input`, and
  catches any exception broadly per the Analysis above); a new
  `_route_after_extractor` conditional edge (`missing_fields` non-empty
  → `llm_fallback_extractor`, else straight to `verifier`); wired the
  new node into `build_workflow_graph()` and updated
  `run_workflow()`'s initial state to default `extraction_method` to
  `"none"`. `extractor_node` now also returns `extraction_method:
  "regex"` on its own success path. Regenerated the workflow graph
  diagram via `scripts/regenerate_workflow_graph.py` (as
  `tests/test_workflow_graph_docs.py` requires) and updated the prose
  description above it in `README.md`.
- **Outcome**: Manually verified both routing branches end-to-end
  before writing tests: `run_workflow_from_pdf("data/sample_treaty.pdf")`
  (regex succeeds) stays `extraction_method="regex"`, `llm_error=None`,
  never touching the new node; `run_workflow_from_pdf(
  "data/sample_rich_fuzzy_treaty.pdf")` against this environment's
  actually-invalid `.env` key genuinely exercises the fallback path
  and degrades to `extraction_method="none"` with a real
  `AuthenticationError` message in `llm_error`, `complete=False`, no
  crash — confirming the graceful-degradation design against a real
  (if unusable) API key, not just a mock. Added 4 tests to
  `tests/test_workflow.py`, all mocking `src.workflow.anthropic.Anthropic`
  (or patching `llm_fallback_extractor` itself) per the task's own "no
  real API calls" scoping: the fallback node is never invoked when
  regex succeeds; given the fuzzy fixture's sections and a mocked
  successful tool-use response, produces a valid `TreatyTerms` with
  `extraction_method="llm"`; a simulated failure returns exactly
  `{"extraction_method": "none", "llm_error": "..."}` with no crash;
  and an end-to-end `run_workflow` case where both regex and the
  (mocked-failing) LLM fallback fail, ending with `complete=False`.
  `pytest tests/ -v` — 41 passed, no regressions. Refreshed every
  README test-count example the 4 new tests shifted (full suite
  37→41, `test_workflow.py` 7→11) and added rows for the new tests to
  its description table. Acceptance criteria met; have not asked for
  human approval to close the task yet.

- **2026-09-05 (update)**: Human asked why `data/workflow_graph.png`
  wasn't updated alongside the new node. Checked
  `scripts/regenerate_workflow_graph.py`: the PNG is deliberately
  opt-in via a `--png` flag, not part of the default run (which only
  updates `README.md`'s mermaid text) or the pre-commit hook — its own
  docstring explains why: `draw_mermaid_png()` calls the public
  mermaid.ink rendering service over the network, which the hook must
  avoid to keep working offline. Confirmed via `git log` that the PNG
  hadn't been touched since the original `build-agentic-workflow-graph`
  commit (2026-09-03), so it was genuinely stale, showing the old
  3-node graph — not embedded in `README.md` (verified via grep, no
  reference), so low-impact, but still a tracked file that would
  mislead anyone opening it directly. Ran
  `python3 scripts/regenerate_workflow_graph.py --png`; visually
  confirmed the regenerated PNG now shows all 4 nodes and the new
  conditional routing.

