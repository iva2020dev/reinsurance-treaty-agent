
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
  reinsurance_premium=400,000, cedent="Sentinel Mutual Assurance" (one
  $900,000 historical claim, which — since it falls entirely below the
  2,500,000 attachment point — cedes $0 into this layer once
  `calculate_loss_ratio` is applied, i.e. loss ratio 0.00, zero
  findings). [Corrected 2026-09-05: originally written here as
  "loss ratio 0.18," which was my own arithmetic error at the time
  (dividing claim/limit directly, ignoring the attachment-point
  subtraction `calculate_loss_ratio` actually performs) — see that
  date's entry below for why the fixture's numbers were later revised
  anyway, to produce a real non-zero finding.]
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

- **2026-09-05 (update)**: Human asked to make the PNG update
  automatic too, overriding the prior deliberate design (PNG was
  opt-in specifically to keep the pre-commit hook network-free).
  Decision: honor it, but make the network call itself non-fatal
  rather than blindly wiring `--png` into a hook that has `set -e` —
  `update_png()` in `scripts/regenerate_workflow_graph.py` now catches
  any exception from `draw_mermaid_png()` (offline, mermaid.ink down,
  etc.), prints a warning, and returns instead of raising, so a
  network hiccup can't hard-fail an unrelated commit that merely
  touches `src/workflow.py`. Only `README.md`'s diagram stays
  *guaranteed* in sync (still enforced by
  `tests/test_workflow_graph_docs.py`); the PNG is now best-effort
  automatic. Updated `.githooks/pre-commit` to pass `--png` and stage
  `data/workflow_graph.png` alongside `README.md`. Verified end-to-end
  by staging a trivial change to `src/workflow.py` and running
  `bash .githooks/pre-commit` directly: exit code 0, README reported
  "already up to date," PNG regenerated and staged correctly. Reverted
  the trivial test change afterward (`git restore --staged --worktree
  src/workflow.py`) so nothing spurious made it into the diff.
  `pytest tests/ -v` — 41 passed, no regressions.

- **2026-09-05 (update)**: Human asked to check the LLM run and add
  richer logs (duration, tokens, etc.). Wrapped
  `llm_fallback_extractor`'s API call with `time.perf_counter()` on
  both the success and failure paths, and added the model name plus
  `response.usage.input_tokens`/`output_tokens` (confirmed the
  `Usage` type exposes these directly, no extra parsing needed) to the
  success log line. Updated the mocked success test's fake response
  to include a `usage` object (the real success-path code now reads
  it, so the mock needed it too). Verified real log output two ways:
  a live run against `sample_rich_fuzzy_treaty.pdf` with this
  environment's actually-invalid key produced `LLM fallback:
  extraction failed after 0.98s (model=claude-haiku-4-5-20251001,
  AuthenticationError: ...)`; a mocked-success run produced `LLM
  fallback: extracted treaty terms for cedent 'Sentinel Mutual
  Assurance' in 0.00s (model=claude-haiku-4-5-20251001,
  input_tokens=743, output_tokens=58)`. `pytest tests/ -v` — 41
  passed, no regressions.

## 2026-09-05 19:37:47 — Fix stale "no secrets needed" deployment claim (docs only)

- **Goal**: Human reported the live deployed app showing "Could not
  extract required treaty terms: cedent_name, attachment_point,
  limit, reinsurance_premium." when uploading the fuzzy fixture, and
  asked what it means.
- **Analysis**: Traced the exact chain: regex fails on the fuzzy
  fixture by design → `llm_fallback_extractor` fires → without a
  configured `ANTHROPIC_API_KEY` on the live Streamlit Cloud
  deployment (never added — this repo's README still claimed "no
  secrets needed" from before `implement-llm-fallback-node`), the API
  call fails immediately → the failure path (by design, from that
  task) leaves `treaty=None` and the original `missing_fields`
  untouched, setting `extraction_method="none"`/`llm_error=<real
  error>` → `src/app.py`'s `extract_report()` only reads
  `missing_fields` today (doesn't know `extraction_method`/`llm_error`
  exist yet, since that's `update-ui-llm-fallback`'s job), so it shows
  the same generic message regardless of whether an LLM attempt even
  happened. Conclusion: not a graph/logic bug — the graceful
  degradation is working exactly as designed — but a real,
  now-stale doc claim (`README.md`'s Deployment section said "no
  `.streamlit/secrets.toml` or other secrets are needed, since this
  app makes no LLM/API calls," which was true when written but
  `implement-llm-fallback-node` invalidated it) that I missed
  updating when that task merged.
- **Decision**: Fix the doc now, on its own branch, separate from
  `update-ui-llm-fallback` (which will make failures like this
  visible in the UI itself, but is a bigger, separate change). Also
  confirmed with the human that they still want `ANTHROPIC_API_KEY`
  added as an actual Streamlit Cloud secret on the live app (a manual
  step only they can do, same as every prior secrets-configuration
  gap this session).
- **Action**: Updated `README.md`'s Deployment first-time-setup steps:
  added a step 5 explaining the `ANTHROPIC_API_KEY` secret is needed
  for the LLM fallback specifically (not for regex-only extraction),
  and that its absence degrades gracefully rather than crashing.
- **Outcome**: `pytest tests/ -v` — 41 passed (docs-only change,
  unaffected).

## 2026-09-05 20:30:53 — Redesign fuzzy fixture, rename LLM Extraction Fallback, clarify Regex logging

- **Goal**: Human, after confirming the LLM fallback worked correctly
  end-to-end on the live deployed app (real Claude Haiku 4.5 call,
  correct extraction, `loss_ratio=0.00`), asked for four things: (1)
  fix the stale "0.18" prediction noted above (done, see that entry's
  correction), (2) redesign `sample_rich_fuzzy_treaty.pdf` so the
  historical claim actually produces a non-zero loss ratio and a
  non-empty findings list — "to be more presented" — rather than the
  correct-but-unexciting 0.00/no-findings result, (3) have the
  Extractor's log lines explicitly say "Regex" so log output reads
  unambiguously next to the LLM step, (4) rename "LLM fallback"
  (function `llm_fallback_extractor`, node key, log-message prefix)
  to "LLM Extraction Fallback" everywhere.
- **Analysis**: The live result was correct given the fixture's
  original numbers (attachment 2,500,000/limit 5,000,000 vs. a single
  900,000 claim) — the claim falls entirely below attachment, so
  `calculate_loss_ratio` correctly cedes $0. To get a real finding
  without touching `data/historical_claims.csv` (shared fixture data;
  changing Sentinel Mutual Assurance's claim row risked nothing else
  in this repo since it's unused elsewhere, confirmed via grep, but
  changing the *treaty's* own numbers in the PDF prose is the more
  targeted, lower-risk lever and keeps the CSV fixture untouched) or
  adding a second claims row (which would have mirrored the rich
  fixture's multi-claim HIGH-finding approach but adds more moving
  parts than necessary), the simplest fix is lowering the fuzzy
  treaty's own attachment point/limit so the existing $900,000 claim
  actually falls inside the layer.
- **Decision**: New numbers: attachment_point=200,000,
  limit=1,000,000 (unchanged premium=400,000). Ceded = min(900,000,
  1,200,000) − 200,000 = 700,000; loss_ratio = 700,000/1,000,000 =
  **0.70** → one `MEDIUM` finding ("would have consumed a majority of
  this layer") — clean, comfortably inside the `[0.5, 1.0)` MEDIUM
  band, not an ambiguous boundary value. Verified this arithmetic
  directly (`calculate_loss_ratio(200_000, 1_000_000, claims)`) before
  touching the PDF, and separately re-verified that regex still fails
  on all four required fields with the new prose (same
  `_FIELD_PATTERNS` avoidance as before, just different dollar
  figures) — both by direct computation, not by re-running a real LLM
  call (this environment's own `.env` key is still invalid; the
  arithmetic and regex-failure checks don't need a real call to
  verify, only the graph's LLM step does, which is already covered by
  mocked tests plus the human's own live confirmation on the deployed
  app).
  For the rename: renamed the actual Python identifier
  (`llm_fallback_extractor` → `llm_extraction_fallback`, the function,
  the graph node key, the routing dict, and the monkeypatch target
  strings in tests) rather than only changing display strings, so the
  workflow graph diagram's node label changes too, not just log text.
  Also updated the two still-open `TASKS.md` entries
  (`implement-llm-fallback-node`, `update-ui-llm-fallback`,
  `integration-test-llm-fallback-deploy-config`) that referenced the
  old name/wording, keeping their **ID**s unchanged (renaming slugs
  that other entries reference via `Blocked by` adds risk
  disproportionate to a cosmetic rename) but updating titles/Details
  text for consistency with the new terminology.
  For Extractor logging: added "(Regex)" directly into
  `extractor_node`'s two existing log lines rather than inventing a
  new log format, so a log tail reads unambiguously (e.g. "Extractor
  (Regex): missing required fields [...]" immediately followed by "LLM
  Extraction Fallback: extracted treaty terms for cedent ...").
- **Action**: Regenerated `data/sample_rich_fuzzy_treaty.pdf` (updated
  the scratchpad generator script's page 2 prose to the new dollar
  figures, re-ran it, verified via direct computation before copying
  into the repo) and `data/sample_rich_fuzzy_treaty_parsed.json`.
  Updated `tests/test_parser.py`'s dollar-figure assertion
  (`"$2,500,000"` → `"$200,000"`). Renamed
  `llm_fallback_extractor`/`_route_after_extractor`'s target string/
  graph node key to `llm_extraction_fallback` throughout
  `src/workflow.py`; changed both its log lines' prefix to "LLM
  Extraction Fallback:"; added "(Regex)" to `extractor_node`'s two log
  lines. In `tests/test_workflow.py`: renamed the import and all
  monkeypatch target strings; renamed the four affected test functions
  (`test_llm_fallback_*` → `test_llm_extraction_fallback_*`); updated
  the mocked tool-use numbers in the existing success test to the new
  200,000/1,000,000 figures; added a new end-to-end test,
  `test_run_workflow_via_llm_extraction_fallback_flags_medium_finding`,
  that mocks a successful LLM response and asserts the *full*
  `run_workflow` result — `loss_ratio == pytest.approx(0.7)`, exactly
  one finding, `Severity.MEDIUM` — directly proving the redesigned
  fixture's intended non-trivial result, not just that extraction
  succeeded. Regenerated the workflow graph diagram and PNG (node
  label changed). Updated `README.md`: the Workflow Graph prose ("LLM
  Fallback Extractor Node" → "LLM Extraction Fallback Node"), the
  parser-fixture-table dollar figure, the full-suite and
  `test_workflow.py` example outputs/descriptions (renamed tests, new
  test added, counts 41→42 / 11→12).
- **Outcome**: `pytest tests/ -v` — 42 passed, no regressions. Grepped
  the whole repo (`src/`, `tests/`, `README.md`, `TASKS.md`) for any
  remaining `llm_fallback_extractor`/"LLM Fallback" references after
  all edits — none left outside this historical entry and the
  superseded-numbers correction above it (both intentionally kept as
  an accurate record of what changed and why, not scrubbed).

- **2026-09-05 16:30:02 — Approved done**: PR #27 merged into `main`
  (merge commit `1887010`, 2026-09-05T16:30:02Z). Human explicitly
  approved the task as done. Removed `implement-llm-fallback-node`
  from TASKS.md per the human-approval policy, and dropped it from
  `update-ui-llm-fallback`'s `Blocked by` field (now unblocked — no
  remaining blockers).

## 2026-09-05 20:43:03 — Task: Surface LLM Extraction Fallback Status in the UI (update-ui-llm-fallback)

- **Goal**: In `src/app.py`, show a clear on-page note when
  `extraction_method == "llm"`, a distinct note when both extraction
  paths failed (explaining why, via `llm_error`), and make sure the
  debug panel's JSON/caption reflect which path a run actually took —
  replacing the now-stale static "this workflow has no LLM calls"
  caption left over from before `implement-llm-fallback-node`.
- **Analysis**: `src/app.py` hadn't been touched since `create-ui-api`
  — confirmed via a fresh read, not memory, since several unrelated
  tasks had landed since. `serialize_state_for_debug()` only
  whitelisted the pre-fallback `WorkflowState` keys (`sections`,
  `treaty`, `missing_fields`, `claims`, `complete`, `report`) — missing
  `extraction_method`/`llm_error` entirely, exactly the gap the human
  hit live on the deployed app a few tasks ago. `extract_report()`'s
  `ValueError` message (`"Could not extract required treaty terms:
  ..."`) is the same for "regex never tried an LLM" and "LLM tried and
  failed" — needs `llm_error` folded in to distinguish them. The
  `implement-llm-fallback-node`/`build-fuzzy-treaty-fixture` tasks
  already work end-to-end (confirmed via `AppTest` with a mocked
  Anthropic client before writing any test assertions): a successful
  mocked run through the real `sample_rich_fuzzy_treaty.pdf` produces
  `extraction_method="llm"`, the correct treaty terms, and
  `loss_ratio=0.70`; a simulated total failure produces
  `extraction_method="none"` with a populated `llm_error`, no crash.
- **Decision**: Added `format_extraction_status(state) -> str` (a pure
  function, unit-testable directly per the "test pure logic with plain
  pytest" convention) producing one of four messages: regex-only
  success, LLM-fallback success, both-failed-with-reason, or a
  defensive "was not run" fallback for a combination that shouldn't
  actually occur given the graph's routing (no `extraction_method` set
  and no `llm_error`) — kept as a safety net rather than assuming the
  state shape, not because that branch is reachable in practice. Used
  `st.info` for the success-path LLM note (distinct from `st.error`/
  `st.warning`, matching Streamlit's own semantic convention for
  "worth knowing, not a problem") placed directly above the rendered
  report, only when `extraction_method == "llm"` — not shown for the
  regex-only path, to avoid noise on every normal upload. Extended the
  existing `ValueError` message with the `llm_error` detail (in
  parens) rather than inventing a second `st.error` call, since both
  errors describe the same single failed run.
- **Action**: Added `extraction_method`/`llm_error` to
  `serialize_state_for_debug()`; added `format_extraction_status()`;
  in `main()`, added the `st.info` success note, folded `llm_error`
  into the failure message, and replaced the static debug-panel
  caption with `format_extraction_status(state)` (or a distinct "no
  workflow state was produced" caption when `state is None`, i.e. a
  `ParserError` before any node ran). Added 4 tests to
  `tests/test_app.py`: a plain-pytest test of
  `format_extraction_status()`'s four branches; an `AppTest`-based
  test uploading the real fuzzy fixture with a mocked successful
  Claude response, asserting the `st.info` note, the rendered report
  (including `loss_ratio` 0.70), and `extraction_method="llm"` in the
  debug JSON; an `AppTest`-based test with a mocked failing client,
  asserting the combined error message and `llm_error` in the debug
  JSON. Manually verified both new `AppTest` scenarios by hand before
  writing formal assertions (same pattern as prior tasks). Updated
  `README.md`: the "Using the app" walkthrough (mentions the fuzzy
  fixture and the new note/error behavior), the full-suite and
  `test_app.py` example outputs/description table (counts 42→45 /
  14→17).
- **Outcome**: `pytest tests/ -v` — 45 passed, no regressions.
  Acceptance criteria met: the fuzzy fixture (mocked) shows the "LLM
  Extraction Fallback" note and `extraction_method="llm"` in the debug
  JSON; a simulated total failure shows the `llm_error` explanation
  instead of crashing. Have not yet asked for human approval to close
  the task.

- **2026-09-05 21:01:03 (update)**: Human confirmed the deployed app
  works correctly end-to-end (verified real `extraction_method:"llm"`,
  `llm_error:null`, correct treaty terms, `loss_ratio:0.7`, one
  `MEDIUM` finding) and asked to change the LLM Extraction Fallback
  note's color to a warning color. Changed `st.info` → `st.warning` in
  `src/app.py`; updated the matching `AppTest` assertion
  (`at.info` → `at.warning`) and the README description-table row.
  `pytest tests/ -v` — 45 passed, no regressions.

## 2026-09-06 10:37:43 — Draft CANDIDATE_TASKS.md (staging list, not yet in TASKS.md)

- **Goal**: Human asked to draft a list of candidate future tasks
  covering two categories — (1) technical/AI-engineering harness work
  (model behavior validation, evaluation frameworks, agent-behavior
  quality checks/grounding, reliability/scalability/cost/latency) and
  (2) business-domain features, explicitly asking to also consider
  Facultative and Claims reinsurance lines (not just Treaty, which is
  all this app covers today) — as a side `.md` file to clarify and
  prioritize together before anything is added to `TASKS.md`.
- **Analysis**: This session's earlier discussion (business-task
  question, then feature-idea question, then cost/effort-estimate
  question) already produced most of the Treaty-line domain candidates
  (clause checklist, renewal diff, multi-layer extraction, ambiguity
  detection, summary, semantic compliance) with rough effort/cost
  framing. Facultative and Claims are genuinely distinct workflows
  from what the app does today (Facultative = per-risk individual
  underwriting vs. Treaty's whole-book coverage; Claims = post-loss
  handling/adjustment vs. pre-bind underwriting review), so their
  candidate tasks needed to be reasoned through fresh rather than
  reused from earlier in the session.
- **Decision**: Named the file `CANDIDATE_TASKS.md` (parallels
  `TASKS.md`'s naming, unambiguous that it's pre-backlog). Kept every
  item to a short description + rough shape (deterministic/LLM/hybrid)
  + rough effort (S/M/L) — deliberately *not* full `TASKS.md`-spec'd
  entries (no ID/Files/Acceptance yet), since nothing here has been
  prioritized. Flagged two cross-cutting notes explicitly rather than
  burying them in individual items: (a) items marked **L** are likely
  each their own multi-task chain, same pattern as
  `explore-hybrid-regex-llm-fallback`'s split into four; (b) the
  LLM-suited domain features (summary, ambiguity detection, semantic
  compliance, claim-exclusion check) would change the app's cost
  profile from "LLM cost only on fallback" to "LLM cost on every run"
  if made automatic rather than opt-in — a deliberate product decision
  flagged for prioritization discussion, not a default assumed here.
- **Action**: Created `CANDIDATE_TASKS.md` at the repo root with
  sections A (10 harness items) and B (18 domain items across Treaty/
  Facultative/Claims), plus a closing "Notes for prioritization
  discussion" section.
- **Outcome**: `pytest tests/ -v` — 45 passed (docs-only addition,
  unaffected). This file is explicitly not part of the task-tracking
  convention yet — no ID/claim/branch-per-item until the human
  prioritizes and specific items graduate into `TASKS.md`.

- **2026-09-06 11:16:14 (update)**: Human asked to add a summary
  table on top of `CANDIDATE_TASKS.md` and prioritize items within
  each category/subsection. Added a `## Summary` table (Pri/ID/Task/
  Category/Shape/Effort/Depends on) right after the intro, covering
  all 28 items in one scannable view. Reordered every section/
  subsection's detailed entries into the same priority order (each
  heading now also says "— Priority N"), ranked by a rough
  value/effort/dependency read: cheap+standalone+high-value items
  first, foundational items before what depends on them (A1 before A2,
  B3 before B4, B10 before B11, B5 before B15), and the items needing
  a brand-new persistent data model (A5, B9, B12, B18) last in their
  section, since they're the biggest lift with the least immediate
  payoff. Kept original IDs unchanged (only reordered physical
  presentation) so cross-references in the "Notes" section and any
  future discussion still resolve. Expanded that Notes section with
  one line explaining the rationale so the ranking isn't just
  asserted without reasoning. `pytest tests/ -v` — 45 passed
  (docs-only, unaffected).

- **2026-09-06 12:41:36 (update)**: Human asked to split the single
  combined Summary table into separate named tables per category.
  Replaced the one 28-row table (with a `Category` column) with four
  tables under their own headings — "Technical / AI Engineering &
  Production Harness," "Business Domain — Treaty," "— Facultative,"
  "— Claims" — dropping the now-redundant `Category` column from each
  since it's implied by the table's heading. `pytest tests/ -v` — 45
  passed (docs-only, unaffected).

- **2026-09-06 12:53:22 (update)**: Human asked which of the four
  Summary tables reflects the Business Domain capability the app has
  actually shipped, then asked to name it "Burn-Cost Check," add it to
  the candidate tables as Done, and add a Status flag to every
  candidate task. **Goal**: make `CANDIDATE_TASKS.md` distinguish the
  one already-shipped item from the 27 proposed ones, without
  renumbering or otherwise disturbing the existing priority order.
  **Decision**: name the shipped capability `B0` (not folded into the
  B1-B18 numbering, since it isn't a candidate up for prioritization —
  it's the baseline). **Action**: (1) added a `Status` column (values
  `✅ Done` / `Proposed`) to all four `## Summary` tables; (2) added a
  `B0` row to the Treaty summary table with Pri `—` and Status
  `✅ Done`; (3) added a detailed `### B0. Burn-Cost Check` entry
  before B1 in the Treaty section, describing the actual shipped
  pipeline: Extractor (regex, falling back to LLM Extraction Fallback)
  → `query_historical_claims` → `calculate_loss_ratio` → severity-
  tiered `AnomalyFinding`s (LOW/MEDIUM/HIGH), pointing at
  `src/workflow.py`/`src/tools.py`/`src/app.py`; (4) updated the intro
  paragraph to explain the new Status column; (5) added a line to
  "Notes for prioritization discussion" clarifying B0 has no Priority
  because it isn't a candidate for re-ranking. Chose "Burn-Cost Check"
  (the human's own term, from the earlier planning discussion) over a
  more generic label like "Loss Ratio Check" since it's the standard
  reinsurance-industry name for exactly this analysis (comparing
  historical incurred losses against a layer to gauge its adequacy).
  **Outcome**: `python -m pytest tests/ -q` — 45 passed (docs-only,
  unaffected; note plain `pytest tests/` fails on `ModuleNotFoundError:
  No module named 'src'` from this shell — must run via
  `python -m pytest` for the repo-root path to resolve, unrelated to
  this change). PR #33 merged (mergedAt 2026-09-06T10:05:33Z).

- **2026-09-06 13:10:12 (chore)**: Human noticed `logs/` (created by
  the Streamlit app's "Save logs to file" control) wasn't showing up
  on GitHub/`main` and asked whether it's ignored. **Analysis**:
  `.gitignore` only had `*.log` (line 59, inherited from the Python
  template) — that ignores `logs/workflow.log` but not other file
  types dropped in the same directory (a stray `.txt` debug export was
  untracked-but-visible in `git status`, never actually committed).
  **Decision**: ignore the whole `logs/` directory rather than adding
  more file-extension patterns, since it's a runtime output directory,
  not source. **Action**: added `logs/` to `.gitignore` (on branch
  `chore/gitignore-logs-dir`, off up-to-date `main` post-merge of
  PR #33). **Outcome**: `python -m pytest tests/ -q` — 45 passed
  (unaffected).

- **2026-09-06 13:16:22 (update)**: Human asked to prioritize
  `CANDIDATE_TASKS.md` together, keeping the current suggested
  priority order but renumbering each item's ID to match its position,
  starting from 1 per category. **Analysis**: Treaty/Facultative/
  Claims all shared the `B` prefix (`B0`-`B18`), so restarting each at
  1 would collide (Facultative's new `B1` vs. Treaty's existing `B1`).
  Asked the human to choose a scoping scheme via AskUserQuestion;
  chosen: give each category its own prefix (`A` Harness, `B` Treaty,
  `F` Facultative, `C` Claims), keeping `B0` for the shipped Burn-Cost
  Check since it isn't a ranked candidate. **Action**: renumbered
  every ID across all four Summary tables, all detailed entries
  (headings and prose), all `Depends on` references, and the "Notes
  for prioritization discussion" section's cross-references, per this
  mapping (old → new): Harness A7→A1, A3→A2, A1→A3, A2→A4, A9→A5,
  A6→A6, A4→A7, A10→A8, A8→A9, A5→A10; Treaty B1→B1, B5→B2, B2→B3,
  B3→B4, B4→B5, B8→B6, B6→B7, B7→B8, B9→B9 (B0 unchanged); Facultative
  B10→F1, B11→F2, B13→F3, B12→F4; Claims B16→C1, B15→C2, B14→C3,
  B17→C4, B18→C5. No re-ranking — every item's relative order and
  Priority number within its category is unchanged, only the ID
  changed. **Outcome**: `python -m pytest tests/ -q` — 45 passed
  (docs-only, unaffected).

- **2026-09-06 13:17:51 (correction)**: Human flagged that Claims
  should be ordered before Facultative in `CANDIDATE_TASKS.md`.
  Reordered both the `## Summary` section (Claims table now precedes
  Facultative's) and the detailed `## B. Business Domain` section
  (Claims subsection now precedes Facultative's) to match — IDs (`C1`-
  `C5`, `F1`-`F4`) and every cross-reference are unchanged, this is
  purely a section-ordering fix. **Outcome**: `python -m pytest
  tests/ -q` — 45 passed (docs-only, unaffected).


- **2026-09-06 13:36:20 (update)**: Human asked how task shape depends
  on treaty content quality (plain/fixed vs. messy/unstructured/fuzzy/
  syntax-error-ridden), discussed as an advisory question first (no
  file changes), then asked to add the resulting analysis to
  `CANDIDATE_TASKS.md` plus a new attribute recording whether each
  task's answer requires extraction, interpretation, or both.
  **Analysis**: two independent axes explain shape inconsistencies
  across the list — (1) whether the task's deliverable inherently
  needs judgment (stays LLM-shaped regardless of document quality:
  `B6`-`B8`, `C4`, `A2`) vs. (2) how cleanly facts are expressed in
  the source text for tasks that are pure fact-extraction (`B0`-style
  tasks, whose shape degrades from Deterministic to Hybrid as document
  quality drops from templated to prose to garbled/OCR-noise to fully
  unstructured, at which point the honest answer is `A10`'s
  human-in-the-loop path, not more prompt engineering).
  **Decision**: added an **Answer Type** column
  (`Extraction`/`Interpretation`/`Both`/`N/A`) to all four Summary
  tables and a matching "Answer type: ..." line to every detailed
  entry; classified all 10 Harness items as `N/A` (they're
  infrastructure, not content-answering tasks) except `A2` (grounding
  check) as `Both` (extracts cited text, interprets equivalence);
  classified `B0`, `B1`-`B5`, `B9`, `C1`-`C3`, `C5`, `F1`-`F4` as
  `Extraction` (facts plus deterministic computation, no semantic
  judgment on the output itself); classified `B6`-`B8` and `C4` as
  `Both` (extraction step feeds a judgment step that's the actual
  deliverable). Added a new "## Document-quality sensitivity" section
  (with the plain-to-fixed-to-messy-to-unstructured table) between
  "B. Business Domain" and "Notes for prioritization discussion", and
  cross-linked it from `B4` (layer segmentation in messy prose), `F1`
  (facultative slips are less standardized than treaty wordings,
  expect more LLM reliance than `B0`), and `F3` (unstructured location
  prose needs LLM normalization before geocoding). **Outcome**:
  `python -m pytest tests/ -q` — 45 passed (docs-only, unaffected).

- **2026-09-06 14:03:25 (close)**: Human asked whether
  `update-ui-llm-fallback` should be closed before starting other
  work, since its implementation (PRs #31/#32) was already merged to
  `main` but the task was never formally marked done — and the next
  P1 task, `integration-test-llm-fallback-deploy-config`, was
  explicitly `Blocked by` it. **Goal**: close the task per the
  human-approval convention (`AGENTS.md`/`CLAUDE.md`), rather than
  leaving `TASKS.md` out of sync with real repo state. **Analysis**:
  re-verified the acceptance criteria are actually met on `main` today
  — `src/app.py`'s `format_extraction_status()` and the `st.warning`
  note cover the `extraction_method == "llm"` and `"none"`/`llm_error`
  cases, `serialize_state_for_debug()` already surfaces
  `extraction_method`/`llm_error` in the JSON debug view, and
  `tests/test_app.py` has passing tests for both cases. **Action**:
  human explicitly approved closing it as done; removed the task entry
  from `TASKS.md`'s P1 section (history preserved in git) and dropped
  the now-satisfied `Blocked by: update-ui-llm-fallback` line from
  `integration-test-llm-fallback-deploy-config`, on branch
  `close/update-ui-llm-fallback`, titled per convention
  `Closing task as "Done": Surface LLM Extraction Fallback Status in
  the UI`. **Outcome**: `python -m pytest tests/ -q` — 45 passed
  (confirms the acceptance criteria hold on `main` before closing).

- **2026-09-06 14:06:36 (start)**: Picked up
  `integration-test-llm-fallback-deploy-config` (P1, claimed). **Goal**:
  add one true end-to-end integration test exercising the LLM
  Extraction Fallback with a real Anthropic API call against
  `data/sample_rich_fuzzy_treaty.pdf`, skipping cleanly when
  `ANTHROPIC_API_KEY` isn't set, and confirm the deployment docs
  already cover the required Streamlit Cloud secret. **Analysis**:
  checked `README.md`'s Deployment section — the `ANTHROPIC_API_KEY`
  Streamlit Cloud secret is already documented (added during the
  earlier hybrid-extraction work), so that half of this task's
  `Details` is already satisfied; the only remaining work is the new
  integration test itself. `tests/test_integration.py` already exists
  with 5 tests driving `run_workflow_from_pdf()`/`run_workflow()`
  end-to-end with no node mocking — the new test follows that same
  pattern but is the first one in this repo to make a real network
  call, gated by `pytest.mark.skipif` on `ANTHROPIC_API_KEY` being
  unset (no existing skip-pattern precedent in this repo to match, so
  this establishes one). **Decision**: assert the final `AnomalyReport`
  for cedent Sentinel Mutual Assurance is correct end-to-end
  (`loss_ratio == 0.70`, one MEDIUM finding, `extraction_method ==
  "llm"`), matching the fuzzy fixture's known values from its earlier
  redesign. **Action**: (in progress — see next entry for what was
  actually changed).

- **2026-09-06 14:08:13 (outcome)**: **Action**: added
  `test_full_pipeline_llm_extraction_fallback_real_api_call` to
  `tests/test_integration.py`, gated with
  `@pytest.mark.skipif(not os.environ.get("ANTHROPIC_API_KEY"), ...)`
  — the first test in this repo to make a real network call, so this
  establishes the skip-pattern precedent the original task plan
  expected to already exist. No `README.md` change was needed since
  the Streamlit Cloud secret documentation was already added during
  the earlier hybrid-extraction work (confirmed at task pickup).
  **Outcome**: verified all three required behaviors directly rather
  than trusting the skip logic on paper: (1) with the local `.env`'s
  real key in place, `pytest tests/test_integration.py -v` ran the new
  test for real against the live Anthropic API and it passed; (2) with
  `.env` temporarily moved aside and `ANTHROPIC_API_KEY` unset
  (simulating a CI runner without the secret), the same test correctly
  `SKIPPED` instead of failing (5 passed, 1 skipped); `.env` was
  restored immediately after. (3) Full suite: `python -m pytest
  tests/ -q` — 46 passed (45 existing + 1 new, key present locally).
  Acceptance criteria for `integration-test-llm-fallback-deploy-config`
  are met. Awaiting human approval before marking done.

- **2026-09-06 14:11:27 (close)**: Human approved closing
  `integration-test-llm-fallback-deploy-config` as done — its
  acceptance criteria were verified on `main` (PR #37 merged): the
  real end-to-end integration test passes with `ANTHROPIC_API_KEY`
  present and skips cleanly without one, and `README.md`'s Streamlit
  Cloud secret documentation was already in place from earlier work.
  **Action**: removed the task entry from `TASKS.md`'s P1 section
  (history preserved in git), on branch
  `close/integration-test-llm-fallback-deploy-config`, titled per
  convention `Closing task as "Done": End-to-End Test the Hybrid Flow
  and Document Deployment Config`. This closes out the entire
  `explore-hybrid-regex-llm-fallback` task chain (fixture → node → UI
  → integration test/docs, all four sub-tasks now done); only
  `fix-claude-review-ci-secret` (P2) remains in `TASKS.md`. **Outcome**:
  `python -m pytest tests/ -q` — 46 passed (confirms acceptance holds
  before closing).

- **2026-09-06 14:18:16 (graduate)**: Continued the candidate-tasks
  prioritization discussion. Recommended a harness-first sequence
  (A1 -> A2 -> A3 -> A4, matching the Harness table's existing
  priority order), corrected after the human asked why A2 (grounding
  check) was initially skipped in a hastily-stated "A1 then A3 then
  A4" — no good reason; A2 catches a live run producing a confidently
  wrong, ungrounded extraction, which matters more immediately than
  a not-yet-existing regression-eval suite. Human approved graduating
  all four (A1-A4) into `TASKS.md`. **Action**: added four new P1
  entries — `llm-fallback-retry-backoff` (A1), `llm-fallback-grounding-check`
  (A2), `extraction-accuracy-eval-suite` (A3), `extraction-eval-ci-gate`
  (A4, `Blocked by: extraction-accuracy-eval-suite`) — each with
  Details/Files/Acceptance derived from the candidate entry's
  description plus the actual `src/workflow.py` code (confirmed
  `llm_extraction_fallback`'s current broad `except Exception` has no
  retry logic today, and `anthropic.Anthropic(timeout=...)` is
  constructed with no explicit `max_retries`). None are claimed yet —
  graduating to the backlog isn't the same as picking up work. Also
  added the two most recently closed tasks (`update-ui-llm-fallback`,
  `integration-test-llm-fallback-deploy-config`) to `TASKS.md`'s
  "Recently completed" comment block, which had fallen behind.
  Updated `CANDIDATE_TASKS.md`: marked A1-A4's Status as
  "📋 In TASKS.md" in the Harness summary table and each detailed
  entry (pointing at their new `TASKS.md` IDs), and added this Status
  value's meaning to the intro paragraph — the candidate list keeps
  these entries for historical/planning context rather than deleting
  them, since `TASKS.md` is now the live source of truth for their
  actual status. **Outcome**: `python -m pytest tests/ -q` — 46 passed
  (docs-only change, unaffected).

- **2026-09-06 14:21:07 (update)**: Human asked to add, to every task
  in `TASKS.md`, an explicit external key back to its
  `CANDIDATE_TASKS.md` ID. **Action**: added a structured
  **Candidate ID** field (right after **Tags**, before **Details**) to
  every task entry: `A1`/`A2`/`A3`/`A4` for the four just-graduated
  harness tasks, and an explicit "— (not from `CANDIDATE_TASKS.md`;
  found directly while working another task)" for
  `fix-claude-review-ci-secret`, which was discovered as a CI failure
  rather than sourced from the candidate list — kept it present but
  marked empty rather than omitting it, so every task consistently has
  the field per the human's "every task" instruction. **Outcome**:
  `python -m pytest tests/ -q` — 46 passed (docs-only, unaffected).

- **2026-09-06 14:23:40 (correction)**: Human asked why the
  `fix-claude-review-ci-secret` task's Candidate ID wasn't just "N/A"
  like the field's stated purpose implies for non-graduated tasks —
  it was already present but phrased as an em-dash explanation rather
  than a plain `N/A` value, which read as if the field were missing.
  Changed it to `N/A (not graduated from CANDIDATE_TASKS.md; found
  directly while working another task)` for consistency with how
  every other field's "no value" case should read. **Outcome**:
  `python -m pytest tests/ -q` — 46 passed (docs-only, unaffected).

- **2026-09-06 14:35:43 (start)**: Picked up
  `llm-fallback-retry-backoff` (P1, claimed). **Goal**: retry
  `llm_extraction_fallback`'s Anthropic API call on transient failures
  (timeout, connection error, rate limit, 5xx/overloaded/unavailable)
  with bounded exponential backoff before falling through to today's
  graceful-degradation path, while leaving non-transient failures
  (auth errors, malformed tool response, `TreatyTerms` validation
  errors) failing immediately exactly as today. **Analysis**: the
  installed `anthropic` SDK (1.3.0) already retries transient failures
  internally by default (`max_retries=2` on `anthropic.Anthropic()`,
  confirmed via `BaseClient._calculate_retry_timeout`'s exponential
  backoff + jitter) — but those retries are invisible to this app's
  own logging, since they happen inside the SDK before any exception
  reaches our code. That means relying on the SDK default wouldn't
  satisfy the task's acceptance criteria ("retry attempts visible in
  captured log lines"), and stacking our own retry loop on top of the
  SDK's default would silently multiply the worst-case delay/attempts.
  **Decision**: construct the client with `max_retries=0` (opt out of
  the SDK's silent retries) and implement an explicit, logged retry
  loop in `llm_extraction_fallback` for a specific tuple of retryable
  exception types (`anthropic.APITimeoutError`,
  `anthropic.APIConnectionError`, `anthropic.RateLimitError`,
  `anthropic.InternalServerError`, `anthropic.OverloadedError`,
  `anthropic.ServiceUnavailableError`), bounded at 2 retries (3 total
  attempts) with exponential backoff (1s, 2s). Everything else (a
  plain `StopIteration` from the `next()` tool-use lookup, a
  `TreatyTerms` `ValidationError`, `AuthenticationError`,
  `BadRequestError`, etc.) stays in the existing broad
  `except Exception` catch-all and fails on the first attempt, exactly
  as today — confirmed no regression against the existing
  `test_llm_extraction_fallback_degrades_gracefully_on_failure` test,
  which uses a plain `RuntimeError` and asserts
  `messages.create.assert_called_once()`.

- **2026-09-06 14:37:02 (outcome)**: **Action**: in
  `src/workflow.py`, added `_RETRYABLE_LLM_EXCEPTIONS`,
  `_LLM_MAX_RETRIES` (2), and `_LLM_RETRY_BASE_DELAY_SECONDS` (1.0,
  doubling per attempt); rewrote `llm_extraction_fallback` as a
  bounded retry loop around the existing try body, constructing the
  client with `max_retries=0`; logs each retry attempt (attempt
  number, exception, backoff delay) and, on final exhaustion, the
  total retry count, via the existing `"src.workflow"` logger. Added
  three tests to `tests/test_workflow.py`: a transient failure
  (`anthropic.APITimeoutError`) followed by success retries once and
  succeeds; a persistent transient failure exhausts all retries (3
  total calls, sleeps `[1.0, 2.0]`) and degrades gracefully exactly as
  before; a non-transient failure (`anthropic.AuthenticationError`)
  fails on the first attempt with no retry/sleep. All three monkeypatch
  `src.workflow.time.sleep` to a list-appending stub so retries don't
  actually delay the test run, while still asserting the exact delays
  used. **Outcome**: `python -m pytest tests/ -q` — 49 passed (46
  existing + 3 new), including the real-API integration test
  (`ANTHROPIC_API_KEY` present locally), confirming the success path
  and `max_retries=0` change didn't break the live LLM call.

- **2026-09-06 14:42:50 (refactor)**: Human asked to separate "service/
  harness" logic from workflow logic, prompted by
  `llm_extraction_fallback`'s retry loop just added in this same
  branch/PR. **Goal**: `src/workflow.py` should stay focused on the
  LangGraph state machine and business logic (what to ask the LLM for,
  how to parse/degrade); the mechanics of reliably calling an LLM
  (client construction, retry/backoff) belong in their own module, so
  future harness work (`A2` grounding check, later fallback-tiering
  ideas) has one obvious place to live rather than accumulating inline
  in `workflow.py`. **Decision**: new module `src/llm_client.py`
  exposing `get_client(timeout=...)` (constructs the client with
  `max_retries=0`, since this module owns retries now) and
  `call_with_retry(fn, ...)` (generic bounded retry-with-backoff over
  `RETRYABLE_EXCEPTIONS`, logging each attempt, re-raising the last
  exception on exhaustion rather than swallowing it — letting the
  caller decide how to degrade). This is intentionally generic (takes
  any zero-arg callable), not treaty-extraction-specific, so a future
  LLM-calling feature (`B6`-`B8`, `C4`) can reuse it without
  duplicating retry logic. **Action**: `llm_extraction_fallback` now
  builds a closure over the actual `messages.create(...)` call and
  passes it to `call_with_retry`, shrinking back to roughly its
  pre-retry-feature shape (a single try/except degrade block) with all
  retry mechanics delegated out. Removed `import anthropic` from
  `workflow.py` (no longer referenced there). Since retry log lines
  now come from the `"src.llm_client"` logger rather than
  `"src.workflow"`, widened `src/app.py`'s debug-panel log handler
  from `logging.getLogger("src.workflow")` to the parent
  `logging.getLogger("src")`, so it captures both (and any future
  harness submodule) via normal logger propagation — confirmed via
  `tests/test_app.py`'s existing debug-panel assertions, unchanged and
  passing. Updated all `monkeypatch.setattr(...)` targets in
  `tests/test_workflow.py` and `tests/test_app.py` from
  `"src.workflow.anthropic.Anthropic"`/`"src.workflow.time.sleep"` to
  `"src.llm_client.anthropic.Anthropic"`/`"src.llm_client.time.sleep"`,
  matching where the client/sleep calls now actually happen. Synced
  `TASKS.md`'s `llm-fallback-retry-backoff` entry (Files list, and a
  dated addendum to Details) to reflect this mid-task change in scope.
  **Outcome**: `python -m pytest tests/ -q` — 49 passed, including the
  real-API integration test, confirming the refactor is behavior-
  preserving.

- **2026-09-06 14:51:53 (docs)**: Human asked whether `src/llm_client.py`
  is repo-agnostic and, on hearing it's tied to the Anthropic SDK
  specifically (not vendor-agnostic, though feature-agnostic within
  this repo), asked to write down instructions for this
  "Anthropic-calling harness" pattern so future work follows it.
  **Action**: filled in `CLAUDE.md`'s previously-empty
  "Key Architectural Patterns" section with a new
  "LLM-Calling Harness Pattern" subsection: any Anthropic API call
  MUST go through `src/llm_client.py`'s `get_client()`/
  `call_with_retry()` rather than constructing `anthropic.Anthropic()`
  directly or reimplementing retry logic inline; extend
  `src/llm_client.py` itself for new harness behavior rather than each
  call site; documented the logger-propagation convention
  (`logging.getLogger(__name__)` per module, captured by `src/app.py`'s
  parent `"src"` logger handler) so a future harness module doesn't
  need special debug-panel wiring. Also filled in `CLAUDE.md`'s
  previously-empty "Key Files" table with the actual `src/` modules,
  including the new `src/llm_client.py`. **Outcome**: `python -m
  pytest tests/ -q` — 49 passed (docs-only, unaffected).

- **2026-09-06 15:03:32 (docs)**: Human asked where the retry/backoff
  feature was covered in `README.md` — it wasn't, confirmed via grep
  (no mention of "retry", "backoff", or "llm_client" anywhere).
  **Action**: (1) in "Workflow Graph", clarified the LLM Extraction
  Fallback Node's description — the pre-existing sentence "retries the
  extraction using Claude Haiku 4.5" predates this feature and meant
  "attempts extraction after regex failed," which now reads
  confusingly next to the new retry-on-transient-failure behavior;
  reworded it and added a sentence naming `src/llm_client.py`'s harness
  and its retry/backoff behavior explicitly. (2) in "Using the app"
  step 2, added a sentence describing the retry-then-give-up behavior
  for transient vs. non-transient failures. (3) in step 3's debug-panel
  bullet, noted that retry attempts appear as their own log lines.
  **Outcome**: `python -m pytest tests/ -q` — 49 passed (docs-only,
  unaffected).

- **2026-09-06 15:06:23 (docs)**: Human asked to add, to `README.md`,
  how to force a real transient LLM failure locally and in the running
  Streamlit app, with real command examples. **Action**: added a new
  "Manually forcing a real transient LLM failure" subsection after the
  test table in "Running Tests" — points `ANTHROPIC_BASE_URL` at an
  unreachable address (`https://127.0.0.1:1`) so a genuine
  `APIConnectionError` fires without a real network call or a valid
  API key, with two command examples: a direct
  `llm_extraction_fallback({'sections': []})` call (with the actual
  log output this produced when run, verbatim), and the same env var
  applied to `streamlit run src/app.py` for seeing the retry/backoff
  log lines and the eventual error in the debug panel and report.
  **Outcome**: `python -m pytest tests/ -q` — 49 passed (docs-only,
  unaffected).

- **2026-09-06 15:14:46 (close)**: Human approved closing
  `llm-fallback-retry-backoff` as done — its acceptance criteria were
  met on `main` via PR #40 (retry/backoff behavior, the
  `src/llm_client.py` harness separation, `CLAUDE.md` architecture
  docs, and `README.md` coverage including a manual-testing recipe,
  all merged). **Action**: removed the task entry from `TASKS.md`'s P1
  section (history preserved in git) and added it to the "Recently
  completed" comment block, on branch
  `close/llm-fallback-retry-backoff`, titled per convention
  `Closing task as "Done": Retry/Backoff Resilience for the LLM Call`.
  **Outcome**: `python -m pytest tests/ -q` — 49 passed (confirms
  acceptance holds before closing).

- **2026-09-06 15:21:01 (start)**: Picked up
  `llm-fallback-grounding-check` (P1, claimed). **Goal**: after
  `llm_extraction_fallback` extracts `TreatyTerms`, verify each cited
  field is actually supported by the cited page's raw text, flagging
  any that aren't rather than silently trusting the LLM's output.
  **Analysis**: inspected the real fuzzy fixture's per-page text
  (`extract_treaty_sections("data/sample_rich_fuzzy_treaty.pdf")`) —
  page 1's cedent name is line-wrapped ("Sentinel Mutual\nAssurance"),
  so a naive substring check would falsely flag the very fixture the
  existing passing tests already rely on; grounding checks must
  normalize whitespace (collapse to single spaces) before comparing.
  Financial figures on page 2 appear as `$200,000`/`$1,000,000`/
  `$400,000` — a numeric-equivalence check needs to strip `$`/`,`
  before parsing. **Decision**: implement the check as a new
  deterministic function in `src/tools.py` (alongside the other
  deterministic tools), not a new module or inline in
  `src/workflow.py` — this isn't an LLM-calling harness concern (no
  API call involved), it's a domain-specific verification tool, so it
  belongs with `calculate_loss_ratio`/`query_historical_claims` per
  the file's existing purpose. Per the task's own field-matching rule:
  exact (whitespace-normalized, case-insensitive) substring match for
  `cedent_name`/`exclusions`; numeric-equivalence match (parse `$`/
  comma-formatted numbers out of the page text, compare with
  tolerance) for `attachment_point`/`limit`/`reinsurance_premium`. A
  failing field is flagged in a new `ungrounded_fields` list, not
  blocking extraction — the run still completes, just annotated for
  transparency, per "flag it... rather than silently trusting it."

- **2026-09-06 15:29:45 (outcome)**: **Action**: added
  `check_treaty_grounding(treaty, sections) -> list[str]` to
  `src/tools.py`, using whitespace-normalized substring matching for
  `cedent_name`/`exclusions` and `$`/comma-tolerant numeric-equivalence
  matching for `attachment_point`/`limit`/`reinsurance_premium`; a
  field with no `page_citations` entry isn't checked. Wired it into
  `llm_extraction_fallback` (only the LLM path, per the task's scope —
  regex-extracted values are grounded by construction) via a new
  `ungrounded_fields: list[str]` `WorkflowState` field, logged with
  `logger.warning` when non-empty. `src/app.py`'s
  `serialize_state_for_debug` now surfaces `ungrounded_fields`, and
  `main()` shows a new `st.warning` naming any flagged fields.
  Discovered mid-implementation, via the real live API
  (`run_workflow_from_pdf("data/sample_rich_fuzzy_treaty.pdf")`), that
  the fuzzy fixture's PDF text hyphenates-and-wraps a word
  ("asbestos-\nrelated"), which naive whitespace normalization doesn't
  rejoin — a real, non-obvious false-positive risk on our own
  showcase fixture, not just a hypothetical edge case. Fixed by having
  `_normalize_whitespace` collapse a hyphen followed by whitespace
  before collapsing remaining whitespace (a genuine hyphen is never
  followed by whitespace in correctly-typeset text, so this only
  affects line-wrap artifacts); added a regression test for it.
  Verified against the live API again afterward: `ungrounded_fields ==
  []` on the real fixture, as expected. Added 8 new tests total: 6 in
  `tests/test_tools.py` (grounded/ungrounded per field type, missing
  citation, hyphen-wrap tolerance, no-citation-skipped), 1 in
  `tests/test_workflow.py` (ungrounded field flagged but extraction
  still completes), 1 in `tests/test_app.py` (the new warning + debug
  JSON). Also discovered `README.md`'s "Running Tests" example
  output/tables had already drifted out of sync with two *prior*
  merged PRs (#37's real-API integration test, #40's three retry
  tests, none of which were ever added) — since I was already
  regenerating these same blocks for my own new tests, fixed the whole
  section in one pass rather than leaving it half-stale; also added
  the grounding-check behavior to "Using the app" and the Workflow
  Graph section, and updated `CLAUDE.md`'s Key Files entry for
  `src/tools.py`. Synced `TASKS.md`'s Files list (moved the check
  itself to `src/tools.py`, added `tests/test_tools.py`/`README.md`/
  `CLAUDE.md`). **Outcome**: `python -m pytest tests/ -q` — 58 passed
  (50 prior + 8 new), including the real-API integration test.

- **2026-09-06 (closing)**: PR #42 merged into `main` at `918873e`.
  Human explicitly approved marking `llm-fallback-grounding-check`
  done. Removing it from `TASKS.md`'s P1 section on this
  `close/llm-fallback-grounding-check` branch/PR, titled
  `Closing task as "Done": Grounding/Assurance Check on LLM Output`,
  per the mandatory task-closing workflow.

- **2026-09-06 15:46:01 (chore)**: Human asked why `src/llm_client.py`'s
  tests weren't isolated — confirmed via `ls tests/` that no
  `test_llm_client.py` existed; its retry/backoff logic was only ever
  tested indirectly, as a side effect of `tests/test_workflow.py`'s
  tests for `llm_extraction_fallback`. Asked for three things: (1) add
  direct isolated unit tests for all of `src/llm_client.py`'s logic,
  (2) write a repo-agnostic instruction that tests must be split
  alongside a code split, tagged as a "harness" (generic) type of
  instruction, (3) audit existing instructions in `CLAUDE.md`/
  `AGENTS.md` and mark which ones are repo-agnostic ("harness") vs.
  specific to this repo. **Action**:
  1. Added `tests/test_llm_client.py` (10 tests) exercising
     `get_client()`/`call_with_retry()` directly against a fake
     zero-arg callable — no `src.workflow` involved at all: client
     construction passes `max_retries=0`; first-try success; single
     retry then success; exponential backoff across multiple retries;
     custom `max_retries`/`base_delay_seconds`; exhausting retries
     re-raises the last exception; a non-retryable Anthropic exception
     and a plain `ValueError` both propagate on the first attempt; all
     six `RETRYABLE_EXCEPTIONS` types actually trigger a retry (not
     just the one or two exercised elsewhere); attempt/description
     logging (via `caplog`).
  2. Trimmed `tests/test_workflow.py`'s two remaining retry-adjacent
     tests to business-outcome assertions only (extraction succeeds/
     degrades correctly), removing the now-duplicated exact
     attempt-count/backoff-delay assertions; deleted the third
     ("does_not_retry_non_transient_failure") test entirely as fully
     redundant with both the pre-existing `degrades_gracefully_on_failure`
     test and `test_llm_client.py`'s own non-retryable-exception tests.
  3. Added a new "Test Isolation Follows Code Split" subsection to
     `CLAUDE.md`'s "Key Architectural Patterns", tagged
     **🔧 Harness (repo-agnostic)**, generalizing beyond just this
     incident (also citing `check_treaty_grounding()` in
     `src/tools.py` as a positive example that was already isolated
     correctly, since its tests were added directly in
     `tests/test_tools.py`).
  4. Established a `🔧 Harness (repo-agnostic)` tag with a one-line
     legend in both files' intros, then audited every section: tagged
     `CLAUDE.md`'s "Task Management & Reasoning" and the general
     principle within "LLM-Calling Harness Pattern" (distinguishing it
     from the repo-specific `src/llm_client.py` file); tagged
     `AGENTS.md`'s "Mandatory Workflow", "Branch and PR Discipline",
     "Priority Levels", "Task Dependencies", "Task Format",
     "Reasoning Transcript", "Timestamp Format", and the "one agent per
     task/working tree" bullet within "Working with multiple agents"
     (left that section's header and the Junie-specific bullets
     untagged, since those are repo-specific agent-coordination
     choices, not a generic practice). Left "Keeping tasks.md tooling
     current" and "Commands" untagged (tied to this repo's specific
     tool/package-manager choices, not the underlying practice).
     Noted separately to the human (not fixed, out of this task's
     scope): `AGENTS.md`'s "Suggested Skills for reinsurance-treaty-agent"
     list names completely unrelated tech (Radius, Socket.io, Mapbox,
     Redis, Django) that doesn't match this repo at all — apparent
     leftover template content worth a human decision, not a silent
     rewrite.
  **Outcome**: `python -m pytest tests/ -q` — 58 passed (49 prior +
  10 new in `test_llm_client.py` − 1 removed from `test_workflow.py`).

- **2026-09-06 16:05:00 (start)**: Picked up
  `extraction-accuracy-eval-suite` (P1, claimed). **Goal**: build a
  labeled golden dataset of treaty documents plus an automated scorer
  reporting field-level precision/recall for the full extraction
  pipeline (regex, falling back to the LLM Extraction Fallback),
  catching a prompt/model-version regression before production.
  **Analysis**: inspected the 3 existing fixtures via
  `extract_treaty_sections`/`extract_treaty_terms` directly to pin
  down their exact known-correct values rather than guessing from
  memory: `data/sample_treaty.pdf` (Acme, regex path, single-layer),
  `data/sample_rich_treaty.pdf` (Meridian, regex path, only Layer 1
  fields survive since `TreatyTerms` models a single layer and the
  extractor takes each field's first page-order match), and
  `data/sample_rich_fuzzy_treaty.pdf` (Sentinel, LLM path -- regex
  genuinely fails on all 4 required fields). Existing fixtures were
  hand-built as minimal raw PDF byte streams (`Tj` text-show operators
  per line) -- no PDF-writing library (e.g. reportlab) is in
  `requirements.txt`/venv, so new fixtures need the same manual-byte-
  stream approach, not a new dependency. **Decision**: add 2 new prose
  fixtures (`Harborlight Mutual Insurance`, `Continental Assurance
  Partners`) styled differently from the existing fuzzy fixture
  (different structure, numeric formatting, exclusion phrasing) so the
  golden dataset exercises more real-world variety, per the task's
  "more realistic real-world phrasing than today's" ask -- both
  written via a small reusable raw-PDF-writing helper script, not a
  new library dependency. Scorer lives under `tests/eval/` (matching
  the task's own file hint) as: `golden_dataset.py` (a `GoldenCase`
  dataclass + the 5-case dataset), `scorer.py` (`run_eval()` calling
  `run_workflow_from_pdf()` per case and computing per-field
  precision/recall -- accuracy for scalar fields, true set-based
  precision/recall for the list-valued `exclusions` field, matched via
  normalized substring containment since an LLM's exact exclusion
  phrasing can vary), `run_eval.py` (a `python -m tests.eval.run_eval`
  CLI printing the report -- the actual runnable the task's acceptance
  criteria asks for, skipping LLM-path cases with a note when no
  `ANTHROPIC_API_KEY` is set, same convention as the existing real-API
  integration test), and `test_eval_suite.py` (pytest tests using a
  mocked LLM client for determinism, not the live API, consistent with
  the rest of this repo's test suite; one test simulates "a corrupted
  extraction schema" via a deliberately wrong mocked LLM response and
  asserts the scored accuracy actually drops, per the task's own
  acceptance criteria).

- **2026-09-06 (outcome)**: **Action**: built the 2 new fixtures via
  `tests/eval/build_fixtures.py`'s reusable raw-PDF writer, verified
  both defeat regex extraction as intended and generated their
  `_parsed.json` companions (matching the existing fixtures'
  convention). Implemented `tests/eval/golden_dataset.py` (5
  `GoldenCase`s), `scorer.py` (`score_case()`/`run_eval()`,
  `EvalReport` with per-field accuracy plus mean exclusions precision/
  recall), and `run_eval.py` (the `python -m tests.eval.run_eval` CLI).
  Ran the CLI directly against the live Anthropic API (a real key is
  present in this machine's local `.env`) as a genuine end-to-end
  validation of all 3 new/existing LLM-path fixtures' labeled values —
  100% accuracy across all 5 cases, confirming the golden dataset's
  expected values are actually correct against the real model, not
  just internally consistent. Added `tests/eval/test_eval_suite.py`
  (6 tests, mocked client, deterministic) covering: regex-path cases
  scoring perfectly with no mocking; a correct mocked LLM response
  scoring perfectly; a corrupted mocked response (wrong cedent name,
  emptied exclusions) being caught per-field; `run_eval()`'s aggregate
  accuracy actually dropping when a case regresses (the acceptance
  criteria's own scenario); a total LLM failure degrading to an error
  result rather than crashing; and the exclusions scorer crediting a
  paraphrased clause, not just an exact string. While regenerating
  `README.md`'s "Running Tests" example-output blocks for my own new
  tests, discovered PR #43 (test isolation) had already introduced the
  same kind of staleness this task's predecessor once fixed: the
  full-suite transcript was still "58 items" (now 73), `test_llm_client.py`
  had no per-file block at all despite existing, and one table row
  still named `test_llm_extraction_fallback_does_not_retry_non_transient_failure`,
  a test that PR #43 deleted. Fixed all three in the same pass rather
  than leaving them half-stale, and added a new "Running the Extraction
  Accuracy Eval Suite" section plus the 2 new fixtures to "Sample
  Treaty Fixtures". Also fixed an unrelated bug discovered while
  reviewing REASONING.md's tail before starting: resolving PR #43's
  merge conflict had duplicated ~76 lines of this file's own log (the
  `llm-fallback-grounding-check` start/outcome/closing sequence
  appeared twice) — fixed on its own branch/PR (#45), not bundled into
  this task. Synced `TASKS.md`'s Files list to the actual delivered
  files. **Outcome**: `python -m pytest tests/ -q` — 73 passed (67
  prior + 6 new in `tests/eval/test_eval_suite.py`).

- **2026-09-06 (closing)**: PR #46 merged into `main` at `7e07f6a`
  (PR #45's unrelated REASONING.md dedup fix merged first at
  `204f97e`). Human explicitly approved marking
  `extraction-accuracy-eval-suite` done. Removing it from `TASKS.md`'s
  P1 section on this `close/extraction-accuracy-eval-suite`
  branch/PR, titled `Closing task as "Done": Extraction Accuracy Eval
  Suite (Golden Dataset)`, per the mandatory task-closing workflow.
  Unblocks `extraction-eval-ci-gate`, which depended on this.

## 2026-09-07 12:00:00 — Task: Tag Extraction Accuracy Eval Suite Pattern as 🔧 Harness (repo-agnostic) (tag-eval-suite-harness)

- **Goal**: Give the Extraction Accuracy Eval Suite (`tests/eval/`)
  the same `🔧 Harness (repo-agnostic)` tagging treatment `CLAUDE.md`
  already gives the LLM-Calling Harness and Test Isolation sections,
  and explicitly separate its repo-agnostic scoring mechanics from its
  reinsurance-specific content. Requested directly by the human after
  discussing what the golden dataset is and running the suite.
- **Analysis**: `CLAUDE.md` had no dedicated section for the eval
  suite — only a one-line `Key Files` table row pointing to
  `README.md`'s "Running the Extraction Accuracy Eval Suite". Reviewed
  `tests/eval/golden_dataset.py`, `scorer.py`, and `run_eval.py`:
  the dataset-design principle (cover every code path — regex vs. LLM
  fallback), the scoring functions (`_numeric_match` exact/numeric
  match for scalars, `_score_exclusions` precision/recall over
  normalized substring containment for list fields), the
  exception-as-scored-failure handling in `score_case`, and the
  skip-on-missing-`ANTHROPIC_API_KEY` behavior in `run_eval.py` are
  all generic to any extraction/agent pipeline. Only the `TreatyTerms`
  fields being scored, the golden PDFs/expected values, and the
  domain exclusion keywords are reinsurance-specific.
- **Decision**: Add a new `###` subsection to `CLAUDE.md` under "Key
  Architectural Patterns" (after "Test Isolation Follows Code Split",
  before "Task Management & Reasoning"), tagged `🔧 Harness
  (repo-agnostic)` in its heading, mirroring the existing sections'
  style: an intro paragraph naming the general principle, then two
  bullet lists explicitly splitting repo-agnostic mechanics from
  repo-specific content. Chose a new section over retrofitting the tag
  onto the one-line `Key Files` row, since a table cell can't carry
  the explanatory split the human asked for. Left `README.md`'s
  existing walkthrough untouched — it's already accurate; only
  `CLAUDE.md`'s convention-level view needed the tag.
- **Action**: Added task entry to `TASKS.md` P2 (`tag-eval-suite-
  harness`) per the "no exceptions" TASKS.md/REASONING.md mandate,
  branched `task/tag-eval-suite-harness` off `main`, added the new
  tagged `### Extraction Accuracy Eval Suite Pattern — 🔧 Harness
  (repo-agnostic)` section to `CLAUDE.md`.
- **Outcome**: Documentation-only change — no code/tests affected;
  `python -m pytest -q` already ran clean (73 passed) earlier this
  session as a baseline, no re-run needed since no source files
  changed. Awaiting human review/approval before this task is marked
  done and removed from `TASKS.md`.
- **2026-09-08 (closing)**: PR #48 merged into `main` at `019728c`.
  Human explicitly approved marking `tag-eval-suite-harness` done.
  Removing it from `TASKS.md`'s P2 section on this
  `close/tag-eval-suite-harness` branch/PR, titled `Closing task as
  "Done": Tag Extraction Accuracy Eval Suite Pattern as 🔧 Harness
  (repo-agnostic)`, per the mandatory task-closing workflow.

## 2026-09-08 — Task: Sync CANDIDATE_TASKS.md's Harness statuses with TASKS.md (sync-candidate-tasks-harness-status)

- **Goal**: Human asked to mark the Business Domain — Treaty candidate
  tasks in `CANDIDATE_TASKS.md` as Done, "according to current TASKS
  state," and to add an instruction keeping `CANDIDATE_TASKS.md` in
  sync with `TASKS.md` going forward.
- **Analysis**: Checked `TASKS.md` (current P0-P3 sections plus its
  "Recently completed" list) and `REASONING.md` for any `B`-prefixed
  (Treaty) candidate task IDs — none of `B1`-`B9` have ever graduated
  into `TASKS.md`; `B0` (Burn-Cost Check) already correctly shows `✅
  Done` in `CANDIDATE_TASKS.md` as the shipped baseline. So the Treaty
  table was already accurate — there was nothing to flip there. What
  *was* stale: the Harness table's `A1` (`llm-fallback-retry-backoff`),
  `A2` (`llm-fallback-grounding-check`), and `A3`
  (`extraction-accuracy-eval-suite`) were completed and removed from
  `TASKS.md` on 2026-09-06 (per its "Recently completed" timestamps),
  but `CANDIDATE_TASKS.md` still showed all three as `📋 In TASKS.md`.
- **Decision**: Confirmed with the human via `AskUserQuestion` before
  acting on a corrected premise (asked whether they meant the Harness
  table instead of Treaty) — they confirmed. Fixed `A1`-`A3` to `✅
  Done` in both the summary table and their detailed `###` entries
  (mirroring `B0`'s existing "shipped as `<id>`" phrasing). For the
  sync instruction, added a new (non-Harness-tagged, since
  `CANDIDATE_TASKS.md` is specific to this repo) "Keeping
  CANDIDATE_TASKS.md in Sync" subsection to `AGENTS.md`, placed after
  "Branch and PR Discipline" — the natural home given `AGENTS.md` is
  already the canonical multi-agent task-workflow doc `CLAUDE.md`
  defers to — rather than inventing a separate doc or duplicating the
  rule inside `CANDIDATE_TASKS.md` itself (which instead gets a short
  pointer back to `AGENTS.md`).
- **Action**: Added task entry to `TASKS.md` P2
  (`sync-candidate-tasks-harness-status`), branched
  `task/sync-candidate-tasks-harness-status` off `main`. Edited
  `CANDIDATE_TASKS.md`: summary table rows for `A1`-`A3` →
  `✅ Done`; detailed section headers for `A1`-`A3` →
  `✅ Done (shipped as \`<id>\`)`; updated the Status-column legend
  paragraph to stop saying "currently just... B0" (no longer true) and
  added a "Keeping this in sync" note pointing at `AGENTS.md`. Edited
  `AGENTS.md`: new "Keeping CANDIDATE_TASKS.md in Sync" subsection
  documenting the graduate/complete-must-update-CANDIDATE_TASKS.md
  rule, with this exact gap as its own dated example.
- **Outcome**: Documentation-only change — no code/tests affected;
  no test re-run needed. Awaiting human review/approval before this
  task is marked done and removed from `TASKS.md`.
- **2026-09-08 (closing)**: PR #49 merged into `main` at `ecdb37a`.
  Human explicitly approved marking
  `sync-candidate-tasks-harness-status` done. Removing it from
  `TASKS.md`'s P2 section on this `close/sync-candidate-tasks-harness-
  status` branch/PR, titled `Closing task as "Done": Sync
  CANDIDATE_TASKS.md's Harness statuses with TASKS.md`, per the
  mandatory task-closing workflow.

## 2026-09-08 — Task: Remove leftover "Radius" template content (remove-radius-template-leftovers)

- **Goal**: Human asked (investigation mode) to remove all mentions of
  a side/unrelated repo called "Radius" from this repo, verify nothing
  breaks, and open a PR to wait for approval.
- **Analysis**: `grep -rniI "radius"` across `*.md`/`*.py`/`*.json`/
  `*.toml`/`*.yml`/`*.yaml`/`*.txt` found four live hits: `AGENTS.md`'s
  "Suggested Skills for reinsurance-treaty-agent (RTA)" list (naming
  Radius, Socket.io, Mapbox, Redis, Django — none used by this repo),
  and `.agents/skills/README.md` (titled "Radius Project Skills",
  claiming a `radius-socketio` skill that doesn't exist anywhere in
  this repo — confirmed via `find .agents -type f`: only `README.md`
  is git-tracked there, no such skill file). A fifth hit in
  `REASONING.md`'s 2026-09-06 entry is a historical log record of
  discovering this exact gap at the time — left untouched, since
  `REASONING.md` is an append-only transcript, not something to
  rewrite. Confirmed via `grep` that no other file references
  `.agents/skills/README.md` by path, so deleting it is safe.
- **Decision**: Asked the human via `AskUserQuestion` whether to (a)
  strip only the literal "Radius" line, (b) remove the whole bogus
  list, or (c) replace it with real RTA-relevant suggestions — chose
  (a) would leave equally-irrelevant Socket.io/Mapbox/Redis/Django
  behind, so didn't default to it. Human picked (b): remove the whole
  list. Deleted `.agents/skills/README.md` outright rather than
  rewriting it, since it duplicates `AGENTS.md`'s own accurate
  "Skills" section (`## Skills`, already correct for this repo) with
  zero real content of its own.
- **Action**: Branched `task/remove-radius-template-leftovers` off
  `main`. `git rm .agents/skills/README.md`. Removed the "Suggested
  Skills for reinsurance-treaty-agent (RTA)" section from `AGENTS.md`
  entirely (5 bullet lines + heading). Added task entry to `TASKS.md`
  P2 (`remove-radius-template-leftovers`).
- **Outcome**: `python -m pytest -q` — 73 passed (unaffected,
  docs/cleanup only). Re-ran the `radius` grep — only the historical
  `REASONING.md` log line remains, as expected. Awaiting human
  review/approval before this task is marked done and removed from
  `TASKS.md`.
- **2026-09-08 (closing)**: PR #52 merged into `main` at `e17f35b`.
  Human explicitly approved marking `remove-radius-template-leftovers`
  done. Removing it from `TASKS.md`'s P2 section on this
  `close/remove-radius-template-leftovers` branch/PR, titled
  `Closing task as "Done": Remove leftover "Radius" template content`,
  per the mandatory task-closing workflow.

## 2026-09-09 10:12:34 — Task: Add Treaty Sample Selection UI to CANDIDATE_TASKS.md (candidate-a11-sample-selection-ui)

- **Goal**: While planning the separate Multi Domain-Task Selection
  (`S`) feature with the human (drafted in `DOMAIN_TASK_SELECTION_PLAN.md`,
  which the human asked to keep outside this repo, in their PyCharm
  Scratches folder, once approved), the human requested a new task:
  let a user select a prepared/golden treaty sample directly in the
  Streamlit UI (not from local disk) to start analysis. Human then
  flagged that this item (originally drafted as `S9`) is not a
  domain-task-selection concern — it's generic app/harness UX — and
  asked for it to be moved into `CANDIDATE_TASKS.md`'s Harness
  section instead, as `A1`.
- **Analysis**: `A1` is already taken (`✅ Done`, "Retry/backoff
  resilience for the LLM call") and Harness IDs are numbered by
  current priority rank, not reused/inserted — asked the human via
  `AskUserQuestion` whether to append as the next free ID (`A11`,
  no disruption to `A1`-`A10`) or literally renumber everything to
  make it `A1`. Human chose `A11`.
- **Decision**: `A11` — "Treaty sample selection UI (prepared/golden
  samples, no local disk)" — added to the Harness section only, with
  a cross-reference note left in `DOMAIN_TASK_SELECTION_PLAN.md`
  (kept outside this repo) pointing to it instead of duplicating it
  as an `S`-series item.
- **Action**: Branched `feature/domain-task-selection-candidates` off
  `main`. Edited `CANDIDATE_TASKS.md`: added `A11` row to the Harness
  summary table (Priority 11, Status `Proposed`, Deterministic, N/A,
  S/M, no dependencies) and its detailed `###` entry, referencing the
  5 golden cases in `tests/eval/golden_dataset.py`
  (`acme_minimal`, `meridian_rich`, `sentinel_fuzzy`,
  `harborlight_prose`, `continental_prose`) as the samples this UI
  would surface. Added `candidate-a11-sample-selection-ui` to
  `TASKS.md`'s P2 section.
- **Outcome**: Documentation-only change — no source files touched.
  `python -m pytest -q` expected unaffected (verifying before commit).
  Awaiting human review/approval before this task is marked done and
  removed from `TASKS.md`.

## 2026-09-09 10:17:43 — Task: Graduate A11 (Treaty Sample Selection UI) into TASKS.md as P0 (treaty-sample-selection-ui)

- **Goal**: Human asked to move `A11` ("Treaty sample selection UI
  (prepared/golden samples, no local disk)") from `CANDIDATE_TASKS.md`
  into the real backlog in `TASKS.md`, as a P0 task.
- **Analysis**: This is distinct from the earlier
  `candidate-a11-sample-selection-ui` P2 entry, which only tracked the
  docs-only work of *adding* `A11` as a candidate to
  `CANDIDATE_TASKS.md` (committed at `b257d4d`) — that entry's own
  acceptance criteria are already met, but it hasn't been marked
  done/removed yet since that needs separate human approval per the
  mandatory workflow. This new action is the actual graduation:
  `A11`'s scope becomes a real, scoped `TASKS.md` task.
- **Decision**: Added a new P0 entry `treaty-sample-selection-ui`
  carrying `A11`'s full scope (sample selector alongside the existing
  uploader, backed by a small in-repo sample registry over the 5
  golden-dataset PDFs, no local-disk path ever used, same explicit
  "Analyze" action, works identically local vs. Railway). Updated
  `CANDIDATE_TASKS.md`'s `A11` Status (summary table row + detailed
  entry heading) from `Proposed` to `📋 In TASKS.md`, per the
  Status-column convention documented near the top of that file.
- **Action**: Continued on `feature/domain-task-selection-candidates`
  (already open for `A11`-related docs work). Edited `TASKS.md` (new
  P0 entry) and `CANDIDATE_TASKS.md` (Status → `📋 In TASKS.md`, both
  places).
- **Outcome**: Documentation/backlog change only — no source files
  touched yet; `python -m pytest -q` expected unaffected (verifying
  before commit). The pre-existing `candidate-a11-sample-selection-ui`
  P2 entry is now fully superseded by this graduation and left as-is
  pending the human's explicit go-ahead to close it out, per the
  "never self-approve/remove a task" rule.

## 2026-09-09 10:20:39 — Task: Close out candidate-a11-sample-selection-ui (superseded, never merged)

- **Goal**: Human approved closing out the `candidate-a11-sample-
  selection-ui` P2 entry now that it's fully superseded by the
  `treaty-sample-selection-ui` P0 graduation.
- **Analysis**: The repo's normal task-closing convention (see e.g.
  `remove-radius-template-leftovers`'s and `sync-candidate-tasks-
  harness-status`'s closing entries above) is a dedicated
  `close/<id>` branch off `main`, titled `Closing task as "Done":
  <task title>`, because those tasks had already been merged into
  `main` and needed their own removal PR there. `candidate-a11-
  sample-selection-ui` never reached `main` — it was added and
  completed entirely within this still-open
  `feature/domain-task-selection-candidates` branch (commit
  `b257d4d`). Branching off `main` to "close" it would diff against a
  version of `TASKS.md` that never had the entry, producing a no-op/
  confusing PR. (Briefly created such a branch, recognized this, and
  discarded it before making any commit there.)
- **Decision**: Remove the `candidate-a11-sample-selection-ui` entry
  directly on this same feature branch instead — its work (adding
  `A11` to `CANDIDATE_TASKS.md`) is already committed here, and its
  tracking entry is redundant with `treaty-sample-selection-ui` now
  that `A11` has graduated.
- **Action**: Deleted the `candidate-a11-sample-selection-ui` entry
  from `TASKS.md`'s P2 section.
- **Outcome**: `TASKS.md` no longer lists it; `treaty-sample-
  selection-ui` (P0) remains as the single live tracking entry for
  this work going forward.

## 2026-09-09 10:29:10 — Update: treaty-sample-selection-ui scope change (review-in-modal)

- **Change**: Human requested adding the ability to review the
  selected treaty in a modal window, as an addition to the
  in-progress `treaty-sample-selection-ui` (P0) task / `A11` candidate
  (not yet started implementation).
- **Action**: Updated `TASKS.md`'s `treaty-sample-selection-ui` Details
  and Acceptance to add a "Review treaty" action opening a modal
  (`st.dialog`) showing the selected document's content (sample or
  uploaded) before "Analyze" is run; applies to both the sample
  selector and the existing uploader path. Mirrored the same addition
  into `CANDIDATE_TASKS.md`'s `A11` detailed entry to keep the two in
  sync per the file's own "Keeping this in sync" rule.
- **Outcome**: Scope updated on both files; no implementation started
  yet, so no test/behavior change to verify.

## 2026-09-09 10:30:50 — Update: treaty-sample-selection-ui scope change (gate Analyze on selection)

- **Change**: Human requested that "Analyze" render blurred/inactive
  until a treaty is selected (via either the sample selector or the
  uploader), as a further addition to the in-progress
  `treaty-sample-selection-ui` (P0) task / `A11` candidate (still not
  started implementation).
- **Action**: Updated `TASKS.md`'s `treaty-sample-selection-ui`
  Details and Acceptance to require "Analyze" be disabled/blurred on
  initial load and whenever no document is selected, becoming
  clickable only once a sample or uploaded file is selected, and
  disabled again if the selection is cleared — reusing the same
  disabled-state styling pattern already planned for not-implemented
  tasks elsewhere (`S6` in `DOMAIN_TASK_SELECTION_PLAN.md`, kept
  outside this repo). Mirrored the same addition into
  `CANDIDATE_TASKS.md`'s `A11` detailed entry to keep the two in sync.
- **Outcome**: Scope updated on both files; no implementation started
  yet, so no test/behavior change to verify.

## 2026-09-09 12:06:06 — Task: Treaty Sample Selection UI (treaty-sample-selection-ui)

- **Goal**: Implement `treaty-sample-selection-ui` (P0, graduated from
  `A11`): let the user pick a prepared/golden treaty sample directly
  in the Streamlit UI (bundled from the repo, no local-disk path),
  review the currently selected document (sample or uploaded) in a
  modal before running analysis, and gate the "Analyze" action so it's
  blurred/disabled until a treaty is selected.
- **Analysis**:
  - `src/app.py`'s `main()` today has **no explicit "Analyze" action**
    — `st.file_uploader` alone triggers the full workflow immediately
    on upload (`if uploaded_file is None: return`, then it runs).
    `TASKS.md`'s Details describe the sample-selector path "surfacing
    the same explicit Analyze action the uploader path uses today,"
    which assumes an action that doesn't actually exist yet. Since the
    Analyze-gating requirement is meaningless without an explicit
    action to gate, introducing an explicit "Analyze" button (replacing
    today's upload-triggers-immediately behavior) is in scope here,
    not a separate task — confirmed by re-reading the full Details,
    which also require gating to apply to "either the sample selector
    or the uploader," implying one shared action for both paths.
  - `data/*.pdf` already holds all 5 golden-dataset PDFs referenced by
    id in `tests/eval/golden_dataset.py`
    (`acme_minimal`/`meridian_rich`/`sentinel_fuzzy`/
    `harborlight_prose`/`continental_prose`). Not importing that
    module from `src/` (tests importing from `src` is fine; the
    reverse isn't) — instead adding a small, independent
    `src/sample_treaties.py` registry with its own labels, per
    `TASKS.md`'s suggested `Files` list.
  - `src/parser.extract_treaty_sections(path)` already returns
    per-page text with page numbers — reusable as-is for the review
    modal's content (no new PDF-rendering dependency needed).
  - Verified `st.dialog` (Streamlit 1.63, installed) is fully
    exercisable under `streamlit.testing.v1.AppTest`: a manual probe
    script confirmed calling a `@st.dialog`-decorated function after a
    button click renders its content into `at.markdown` with no
    exception, so the modal can get real automated test coverage, not
    just a "doesn't crash" check.
- **Decision**: Add a `st.radio` treaty-source toggle ("Upload a
  treaty PDF" vs. "Choose a reinsurance treaty") so exactly one
  selection mechanism is active at a time (avoids ambiguity between a
  stale upload and a newly chosen sample). Both paths resolve to a
  single `(bytes, display_name)` pair. Add "Review treaty" and
  "Analyze" buttons side by side, both `disabled=` when no document is
  selected; "Review treaty" opens an `st.dialog` showing the selected
  PDF's per-page text via `extract_treaty_sections`; "Analyze" runs
  the existing workflow exactly as today once clicked.
- **Action**: Branched `task/treaty-sample-selection-ui` off `main`.
  Implementing `src/sample_treaties.py` + `src/app.py` changes next,
  with new/updated tests in `tests/test_app.py` (existing upload-tests
  need updating since upload no longer auto-runs analysis).

- **Outcome**: Implemented in `src/app.py`:
  - `src/sample_treaties.py` (new): `SampleTreaty` dataclass + `SAMPLE_TREATIES`
    (5 golden samples) + `get_sample_bytes()`, all reading from `data/`.
  - `main()` now shows an `st.radio` "Treaty source" toggle (Upload vs.
    Choose a reinsurance treaty), resolving to one `(selected_bytes,
    selected_name)` pair regardless of path.
  - Introduced explicit "Review treaty" and "Analyze" buttons, both
    `disabled=` until a treaty is selected (satisfies the gating
    requirement; also replaces the old upload-triggers-immediately
    behavior, per the corrected understanding logged above).
  - "Review treaty" opens `_show_review_dialog` (`@st.dialog`), which
    writes the selected bytes to a temp file, runs
    `extract_treaty_sections`, and renders each page's text.
  - Analysis results now persist in `st.session_state["workflow_run"]`
    (set only when "Analyze" is clicked) rather than being recomputed
    on every rerun — needed because, once gated behind a button, a
    `st.button`'s return value is only `True` on the exact rerun it was
    clicked; without session-state persistence, any later widget
    interaction (e.g. the save-log form) would silently wipe the
    rendered report. Caught this via `test_app_save_button_writes_
    default_log_file` failing with `StopIteration` (the Save button
    disappeared because `main()` returned early on that rerun).
  - `tests/test_app.py`: added `_click_button`/`_upload_and_click_analyze`
    helpers (byproduct of buttons no longer being at fixed indices);
    updated the 6 pre-existing upload-flow tests to click "Analyze"
    after uploading (upload alone no longer auto-runs); added 3 new
    tests: Analyze/Review disabled-until-selected, sample selector
    lists all 5 golden cases and runs analysis end-to-end, and the
    review modal shows the selected document's page text.
  - Verified `st.dialog` is fully exercisable under `AppTest` via a
    throwaway probe script (see Analysis above) before relying on it
    for real test coverage.
- **Verification**: `python -m pytest -q` — 76 passed (73 previously +
  3 new). Manually booted `streamlit run src/app.py` headlessly —
  health check OK, no exceptions in the server log; full interactive
  click-through wasn't done in a real browser (none available in this
  environment), so behavior confidence rests on the `AppTest` suite
  (which does exercise real button clicks, selection, and the dialog's
  rendered content, not just "doesn't crash").
  Awaiting human review/approval before this task is marked done and
  removed from `TASKS.md`.

## 2026-09-09 12:20:20 — Update: Analyze button color (treaty-sample-selection-ui)

- **Change**: Human asked to change the "Analyze" button's color from
  red (Streamlit's default `type="primary"` color) to blue, since it
  reads as a proceed/confirm action.
- **Analysis**: Streamlit has no per-button color override — a
  button's `type="primary"` styling is driven entirely by the app-wide
  theme's `primaryColor`. "Analyze" is the app's only primary-styled
  button today, so a theme-wide change has the same visible effect as
  a per-button one would, with no other element affected.
- **Action**: Added `.streamlit/config.toml` with
  `[theme] primaryColor = "#1E88E5"` (a standard blue), on the same
  `task/treaty-sample-selection-ui` branch since it directly follows
  from the "Analyze" button just added there.
- **Outcome**: `python -m pytest -q` — 76 passed (unaffected, styling
  only). Manually booted `streamlit run src/app.py` — healthy, no
  server-log errors.

## 2026-09-09 12:23:15 — Update: review modal size/position (treaty-sample-selection-ui)

- **Change**: Human asked to make the "Review treaty" modal narrower
  (sized to the sample content rather than full width), centered in
  the main window, and shorter.
- **Analysis**: `st.dialog`'s only sizing control is `width`, a
  `"small"` (default) or `"large"` preset — no arbitrary width/height.
  `st.dialog` is always centered over the whole viewport already, so
  no change was needed for centering. There's no dialog-level max-
  height option, but `st.container(height=...)` creates a fixed-height
  scrollable region, which caps the modal's effective height
  regardless of how many pages a document has.
- **Action**: Switched `_show_review_dialog`'s `@st.dialog` from
  `width="large"` to `width="small"` (narrower, Streamlit's default
  preset). Wrapped the per-page text loop in
  `st.container(height=350)` so the modal's content area scrolls
  internally past that height instead of growing the dialog.
- **Outcome**: `python -m pytest -q` — 76 passed (unaffected, no new
  elements added/removed, just a container wrapper). Manually booted
  `streamlit run src/app.py` — healthy, no server-log errors.

## 2026-09-09 12:26:02 — Update: review modal height increase (treaty-sample-selection-ui)

- **Change**: Human confirmed the modal's top position is good and
  asked to move the bottom border lower by ~20-25% (i.e. increase
  height), after the previous 350px cap.
- **Action**: Increased `_show_review_dialog`'s `st.container` height
  from 350 to 440 (~26% increase).
- **Outcome**: `python -m pytest -q` — 76 passed (unaffected, height
  value only).

## 2026-09-09 12:29:58 — Update: label renames (treaty-sample-selection-ui)

- **Change**: Human asked to rename two labels in `src/app.py`:
  the debug expander from "Debug: workflow execution" to "Analysis
  Workflow execution", and the save-log button from "Save logs to
  file" to "Save to logs file".
- **Action**: Renamed both in `src/app.py`; updated
  `tests/test_app.py`'s `_click_button(at, "Save logs to file")` call
  to match the new label.
- **Outcome**: `python -m pytest -q` — 76 passed.

## 2026-09-09 12:39:17 — Update: bordered results container with Close (treaty-sample-selection-ui)

- **Change**: Human asked to wrap the analysis results (report +
  warnings + debug expander) in a bordered container with a "Close"
  button, and confirmed that clicking "Analyze" again should clear the
  results container and restart the workflow from the beginning.
- **Analysis**: The "start from the beginning on re-Analyze" part was
  already correct by construction — `st.session_state["workflow_run"]`
  is fully overwritten (not merged/appended) inside the
  `if analyze_clicked:` block, which runs *before* `run_result` is
  read for rendering, so a second "Analyze" click always replaces the
  prior run's state/log_lines/report wholesale. Verified this with a
  new test (`test_app_re_analyzing_replaces_previous_results`) rather
  than assuming it, since the ordering it depends on isn't obvious
  from a a glance. For "Close", the natural mechanism is removing
  `st.session_state["workflow_run"]` and calling `st.rerun()`
  immediately (rather than just setting a flag and letting the normal
  end-of-script rerun happen) so the stale content doesn't flash for
  one frame before disappearing.
- **Decision**: Wrapped everything from the results section onward
  (error/warning/report markdown through the debug expander and
  save-log form) in a single `st.container(border=True)`, with a
  "Analysis Results" subheader and a "Close" button (✕ icon) in a
  narrow column beside it, for a self-contained, clearly-scoped
  results panel that's easy to dismiss without affecting the
  selection controls above it.
- **Action**: Edited `src/app.py`'s `main()`. Added
  `test_app_close_button_clears_results` and
  `test_app_re_analyzing_replaces_previous_results` to
  `tests/test_app.py`.
- **Outcome**: `python -m pytest -q` — 78 passed (76 previously + 2
  new). Manually booted `streamlit run src/app.py` — healthy, no
  server-log errors.

## 2026-09-09 12:43:58 — Verification: full test suite + coverage of new functionality (treaty-sample-selection-ui)

- **Goal**: Human asked to test everything and check coverage of the
  new functionality before considering this task complete.
- **Action**: Ran `python -m pytest -q` (full suite) and, since
  `pytest-cov`/`coverage` weren't installed, temporarily `pip install
  coverage`ed (not added to `requirements.txt` — dev-only, local
  check) and ran `python -m coverage run -m pytest -q` +
  `coverage report -m --include="src/app.py,src/sample_treaties.py"`.
- **Findings**: Initial coverage was 97% on `src/app.py` (100% on the
  new `src/sample_treaties.py`), with one real gap in the new
  functionality: `_show_review_dialog`'s `ParserError` branch (a
  malformed/unreadable PDF opened via "Review treaty") was untested —
  the happy path had a test, the error path didn't. Added
  `test_app_review_treaty_shows_error_for_malformed_pdf` to close it.
  The 3 remaining uncovered lines (`sys.path` bootstrap guard, an
  unreachable-in-practice `save_logs_to_file` mode validation, and the
  "no log lines to save" branch) are pre-existing, unrelated to this
  task's new code, and not worth chasing here.
- **Outcome**: `python -m pytest -q` — 79 passed (78 previously + 1
  new). Coverage on the touched/new files: `src/app.py` 98%,
  `src/sample_treaties.py` 100%. All new functionality from this
  task's work (sample registry, source toggle, Review/Analyze gating,
  review modal happy+error paths, Close button, re-Analyze
  replacement) now has direct test coverage, not just "doesn't crash"
  checks.

## 2026-09-09 12:46:55 — Add automatic coverage reporting on every test run (treaty-sample-selection-ui)

- **Goal**: Human asked to make coverage generate/update automatically
  every time tests run, following the manual `coverage run`/`coverage
  report` check done in the previous verification step, and asked how
  to open `.coverage` in an IDE.
- **Analysis**: `.coverage` (coverage.py's own data file) and
  `htmlcov/` were already in `.gitignore` from the repo's original
  template, so no gitignore change needed. No `pytest.ini`/
  `pyproject.toml` existed yet to hold pytest config.
- **Decision**: Add `pytest-cov` to `requirements.txt` and a new
  `pytest.ini` with `addopts = --cov=src --cov-report=term-missing
  --cov-report=html`, so a plain `python -m pytest` (locally or in any
  future CI step) always regenerates both the `.coverage` data file
  and a browsable `htmlcov/index.html` report, without needing a
  separate manual coverage invocation.
- **Action**: Edited `requirements.txt`, added `pytest.ini`.
- **Outcome**: `python -m pytest -q` now prints a per-file
  term-missing coverage table and writes `htmlcov/` automatically —
  verified: 79 passed, coverage summary shown for all `src/*` modules
  (98% overall, matching the manual check from the prior entry).
  `.coverage`/`htmlcov/` correctly stay untracked (`git status`
  confirmed).

## 2026-09-09 12:51:37 — Document test coverage in README.md (treaty-sample-selection-ui)

- **Goal**: Human asked to add README documentation explaining how
  coverage is generated, what it is, and how to see/interact with it.
- **Action**: Added a "### Test Coverage" subsection to
  `README.md`'s "## Running Tests" section (right before "## Running
  the Extraction Accuracy Eval Suite"), covering: what coverage means
  and its limits, what `pytest.ini`'s `addopts` auto-generates on every
  `pytest` run (`.coverage`, `htmlcov/`, the terminal summary table),
  how to view it (browser via `htmlcov/index.html`, or PyCharm's
  native "Run with Coverage" for in-editor gutters — explicitly noting
  `.coverage` itself isn't meant to be opened directly, since a user
  asked exactly that in this session), and that neither output is
  committed (already gitignored).
- **Outcome**: `python -m pytest -q` — 79 passed, coverage table
  printed as expected (98% overall). Docs-only change, no code
  touched.

## 2026-09-09 12:55:13 — Closing task: Treaty Sample Selection UI (treaty-sample-selection-ui)

- PR #55 merged into `main` at `566cf1a`. Human explicitly approved
  marking `treaty-sample-selection-ui` done. Removing it from
  `TASKS.md`'s P0 section (and adding it to the "Recently completed"
  list) on this `close/treaty-sample-selection-ui` branch/PR, titled
  `Closing task as "Done": Treaty Sample Selection UI (prepared/golden
  samples, no local disk)`, per the mandatory task-closing workflow.
  Also updated `CANDIDATE_TASKS.md`'s `A11` Status (summary row +
  detailed heading) from `📋 In TASKS.md` to `✅ Done (shipped as
  \`treaty-sample-selection-ui\`)`, matching the pattern used for
  `A1`-`A3`.

## 2026-09-09 13:29:37 — Task: Fix treaty-source input layout twitch (fix-source-input-height-twitch)

- **Goal**: Human asked to make "Treaty PDF" (`st.file_uploader`) and
  "Choose a reinsurance treaty" (`st.selectbox`) render at the same
  height, so toggling the "Treaty source" radio doesn't shift the UI
  elements below it.
- **Analysis**: `st.file_uploader` renders a much taller drag-and-drop
  box than `st.selectbox`'s single-line dropdown; since `main()`
  renders exactly one of the two depending on `source_mode`, switching
  the radio changes the page's total height, visibly shifting the
  Review/Analyze buttons and anything below.
- **Decision**: Wrap both branches in a shared
  `st.container(height=SOURCE_INPUT_HEIGHT, border=False)`, a new
  module-level constant (180px — enough to fit the uploader's box
  without clipping); the selectbox branch just leaves the remaining
  space blank, so both paths occupy the identical fixed height and
  nothing below ever moves.
- **Action**: Branched `task/fix-source-input-height-twitch` off
  `main`. Added `fix-source-input-height-twitch` to `TASKS.md`'s P1.
  Edited `src/app.py`.
- **Outcome**: `python -m pytest -q` — 79 passed (unaffected; widgets
  unchanged, only wrapped in a container). Manually booted `streamlit
  run src/app.py` — healthy, no server-log errors. Awaiting human
  review/approval before this task is marked done and removed from
  `TASKS.md`.

## 2026-09-09 13:38:19 — Update: bordered box so inputs match visually (fix-source-input-height-twitch)

- **Change**: Human confirmed the page-shift/twitch was fixed
  (Review/Analyze buttons stay put), but pointed out the two inputs
  themselves still look visibly different in height (the uploader's
  drag-and-drop `section` vs. the selectbox's own short input) — the
  ask was for the two input *boxes* to visually match, not just for
  the overall page height to stay constant with blank space under the
  shorter one.
- **Action**: Changed the shared `st.container(height=SOURCE_INPUT_
  HEIGHT, ...)` from `border=False` to `border=True`, so both the
  uploader and the selectbox render inside a visibly bordered box of
  the same fixed height — presenting as two equal-height boxes rather
  than one widget floating in blank space next to a differently-sized
  one.
- **Outcome**: `python -m pytest -q` — 79 passed (unaffected). Manually
  booted `streamlit run src/app.py` — healthy, no server-log errors.

## 2026-09-09 13:40:49 — Update: tune SOURCE_INPUT_HEIGHT (fix-source-input-height-twitch)

- **Change**: Human iterated on `SOURCE_INPUT_HEIGHT` live against the
  running local app (no browser available in this environment to
  verify visually myself): 180 left too much blank space under the
  bordered selectbox; 110 was too small and caused the file uploader's
  own content to clip into an internal vertical scrollbar. Settled on
  140, confirmed good.
- **Action**: Set `SOURCE_INPUT_HEIGHT = 140` in `src/app.py`.
- **Outcome**: `python -m pytest -q` — 79 passed (unaffected, constant
  value only). Confirmed working by the human against the live app.

## 2026-09-09 13:42:47 — Closing task: Fix treaty-source input layout twitch (fix-source-input-height-twitch)

- PR #57 merged into `main` at `1868322`. Human explicitly approved
  marking `fix-source-input-height-twitch` done. Removing it from
  `TASKS.md`'s P1 section (and adding it to the "Recently completed"
  list) on this `close/fix-source-input-height-twitch` branch/PR,
  titled `Closing task as "Done": Fix treaty-source input layout
  twitch on source toggle`, per the mandatory task-closing workflow.

## 2026-09-09 15:48:58 — Task: Auto-clear Analysis Results on new treaty selection (auto-clear-results-on-new-selection)

- **Goal**: Human asked for the "Analysis Results" container to clear
  and close automatically once a new treaty is chosen, rather than
  requiring an explicit "Close" click or a re-"Analyze" click first.
- **Analysis**: `st.session_state["workflow_run"]` previously only
  changed on an explicit "Analyze" click or "Close" click — nothing
  detected that the underlying selection (uploaded file / chosen
  sample / source mode) had since changed, so the container could show
  a report for a document that's no longer selected.
- **Decision**: Store a content fingerprint (`hashlib.sha256` of the
  analyzed bytes) alongside each `workflow_run` result. On every
  render, compare it against a fingerprint of the *currently* selected
  bytes (`None` if nothing is selected); a mismatch means the
  selection changed since that result was produced, so drop
  `workflow_run` and skip rendering — same effect as clicking "Close",
  but automatic. A cheap hash rather than object identity/name
  comparison, since two different samples could coincidentally share a
  filename structure and a name-only check felt less certain to catch
  every real change.
- **Action**: Branched `task/auto-clear-results-on-new-selection` off
  `main`. Added `auto-clear-results-on-new-selection` to `TASKS.md`'s
  P1. Edited `src/app.py` (`_fingerprint()` helper,
  `_run_workflow_with_logging()` now stores it, main() compares and
  clears). Added
  `test_app_results_auto_clear_when_a_new_file_is_uploaded_without_re_analyzing`
  and `test_app_results_auto_clear_when_switching_to_sample_selector`
  to `tests/test_app.py`.
- **Outcome**: `python -m pytest -q` — 81 passed (79 previously + 2
  new). Manually booted `streamlit run src/app.py` — healthy, no
  server-log errors. Awaiting human review/approval before this task
  is marked done and removed from `TASKS.md`.

## 2026-09-09 15:55:45 — Task: Save analysis results to a file (save-analysis-results-to-file)

- **Goal**: Human asked for a "Save analysis results" feature, with a
  naming rule of datetime stamp + treaty short name + one more
  component the human wanted my input on.
- **Decision (asked via AskUserQuestion)**: For the third naming
  component, offered highest-severity / loss-ratio / extraction-method
  / none — human picked highest severity (lets a folder of saved
  reports be scanned for risk at a glance). For file format, offered
  Markdown / JSON / both — human picked Markdown, matching what's
  already rendered on screen (`format_report_markdown`), so the saved
  file is exactly what a reviewer already saw.
- **Analysis**: `_sample_report()`'s severity is a `Severity(str,
  Enum)` member — discovered while testing that Python's default
  `Enum.__str__` (`"Severity.HIGH"`) is used inside an f-string, not
  the plain string value, even though `Severity` inherits `str`;
  fixed by taking `.value` explicitly. Also had to read
  `MINIMAL_TREATY_PATH`'s bytes *before* `monkeypatch.chdir(tmp_path)`
  in the app-level test — a relative path breaks after the chdir,
  same pattern as the existing `test_app_save_button_writes_default_
  log_file`.
- **Action**: Branched `task/save-analysis-results-to-file` off
  `main`. Added `save-analysis-results-to-file` to `TASKS.md`'s P1.
  Edited `src/app.py`: `DEFAULT_RESULTS_DIR`, `_SEVERITY_RANK`,
  `slugify_treaty_name()`, `highest_severity_label()`,
  `format_results_filename()`, `save_analysis_result_to_file()`, and a
  "Save analysis results" button inside the successful-report branch
  of the results container. Added `results/` to `.gitignore` (mirrors
  `logs/`). Added 9 new tests to `tests/test_app.py` covering the
  naming/slugify/severity helpers directly plus an app-level test
  confirming the button writes a real file.
- **Outcome**: `python -m pytest -q` — 90 passed (81 previously + 9
  new). Coverage: `src/app.py` 99%.
  Manually booted `streamlit run src/app.py` — healthy, no server-log
  errors. Awaiting human review/approval before this task is marked
  done and removed from `TASKS.md`.

## 2026-09-09 16:03:23 — Update: add Download button for production (save-analysis-results-to-file)

- **Change**: Human asked whether saved results are visible in
  production. Explained the two real limitations: Streamlit Community
  Cloud's filesystem is ephemeral (a server-side save doesn't survive
  redeploy/restart/sleep) and there's no file browser exposed to the
  user anyway, even within the same session — the same pre-existing
  limitation the "Save to logs file" button already has. Offered three
  options via `AskUserQuestion` (switch to download-only, keep
  server-side + add download, or leave as-is); human chose to keep
  the server-side save (useful for local dev) and add a download
  button alongside it.
- **Action**: Added a "Download analysis results" `st.download_button`
  next to "Save analysis results" in `src/app.py`, offering the same
  `format_report_markdown()` content and `format_results_filename()`
  name as a direct browser download — works identically locally and
  in production since it needs no server-side persistence. Updated
  `TASKS.md`'s `save-analysis-results-to-file` entry to cover both
  buttons. Added
  `test_app_download_analysis_results_button_is_offered_after_analysis`
  to `tests/test_app.py` — discovered along the way that `AppTest`'s
  `DownloadButton.proto` only exposes a mock media URL, not the raw
  bytes/filename passed to `st.download_button`, so the test checks
  what's actually observable (button exists, `.md` extension) rather
  than re-asserting content/filename already covered by the naming
  helpers' own direct unit tests.
- **Outcome**: `python -m pytest -q` — 91 passed (90 previously + 1
  new). Coverage: `src/app.py` 99%. Manually booted `streamlit run
  src/app.py` — healthy, no server-log errors.

## 2026-09-09 16:13:48 — Update: add PDF format with a format selector (save-analysis-results-to-file)

- **Change**: Human asked to save results in both `.md` and `.pdf`
  formats. Mid-implementation, human further specified: let the user
  select the format *before* saving, rather than always producing
  both or offering separate per-format buttons.
- **Decision**: Added a "Result file format" `st.radio` (Markdown /
  PDF) right above the Save/Download buttons; both buttons now act on
  whichever format is currently selected, rather than one button per
  format. `format_results_filename()` and `save_analysis_result_to_file()`
  gained a required `extension` parameter; a new `render_report_bytes()`
  dispatches to either `format_report_markdown().encode()` or the new
  `render_report_pdf()`.
- **Analysis**: No existing PDF-writing dependency in the repo
  (`pypdf` only *reads*/parses PDFs). Chose `fpdf2` — pure Python, no
  system binary/library dependency (unlike `weasyprint`/`wkhtmltopdf`),
  so it installs cleanly on Streamlit Community Cloud's free tier.
  `render_report_pdf()` walks `format_report_markdown()`'s lines,
  strips Markdown syntax (headers/bold/italic-citation parens) and
  drops any character fpdf2's core Helvetica font (Latin-1 only) can't
  encode — covers the severity emoji, whose information already
  exists as a plain-text `[HIGH]`/`[MEDIUM]`/`[LOW]` label in the same
  line. Hit and fixed a real bug: `multi_cell()`'s default
  `new_x=XPos.RIGHT` leaves the cursor at the right edge of the last
  rendered line rather than resetting to the left margin, so every
  call after the first heading got ~0 available width and raised
  `FPDFException: Not enough horizontal space to render a single
  character` — fixed by passing `new_x="LMARGIN", new_y="NEXT"`
  explicitly. Verified the fix by reproducing standalone (not just
  reading fpdf2's docs) and confirming via `pypdf.PdfReader` that the
  generated PDF's text is actually extractable and correct, not just
  "no exception raised."
- **Action**: Added `fpdf2` to `requirements.txt`. Edited `src/app.py`:
  `render_report_pdf()`, `render_report_bytes()`, updated
  `format_results_filename()`/`save_analysis_result_to_file()`
  signatures, added the format radio and wired both buttons to it.
  Updated `TASKS.md`'s `save-analysis-results-to-file` entry.
  Updated/added tests in `tests/test_app.py` for the new signatures,
  PDF content extraction, and format-selection behavior for both
  buttons.
- **Outcome**: `python -m pytest -q` — 96 passed (91 previously, some
  updated + net new for PDF coverage). Coverage: `src/app.py` 98%.
  Manually booted `streamlit run src/app.py` — healthy, no server-log
  errors.

## 2026-09-09 16:22:39 — Update: per-treaty folders, generation timestamp, LLM usage in content (save-analysis-results-to-file)

- **Goal**: Three follow-up requests from the human, folded into one
  pass: (1) "name and organise analysis results" — clarified via
  `AskUserQuestion` to mean the `results/` folder structure; (2) "add
  datetime stamp in content" — inside the saved/downloaded file, not
  just the filename; (3) "add LLM usage data results if any" — the
  LLM Extraction Fallback's token counts, when it actually ran.
- **Decision (1 — organization)**: Results now live under
  `results/<treaty-slug>/<timestamp>_<severity>.<ext>` — a
  subdirectory per treaty (`results_subdirectory()`), rather than one
  flat directory. `format_results_filename()` dropped the treaty slug
  (now redundant with the containing folder), keeping just
  `<timestamp>_<severity>.<extension>`.
- **Decision (2 — timestamp in content)**: New
  `format_results_document()` wraps `format_report_markdown()`'s
  content with a `Generated: <timestamp>` line, used only for saved/
  downloaded output (not the on-screen `st.markdown` render, which
  describes the treaty, not this specific run).
- **Decision (3 — LLM usage)**: `src/workflow.py`'s
  `llm_extraction_fallback` only *logs* `input_tokens`/`output_tokens`
  (`src/workflow.py:226-234`) — never stores them in `WorkflowState`.
  Rather than changing the workflow's state schema (a bigger, riskier
  change touching the harness), added
  `extract_llm_usage_summary(log_lines)` to parse that exact log
  line's token counts back out of the already-captured `log_lines`
  (the same list the debug expander already displays) — `None` when
  the LLM never ran (regex succeeded), so the saved content only
  mentions LLM usage when it's actually relevant.
- **Action**: Edited `src/app.py`: `results_subdirectory()`,
  `extract_llm_usage_summary()`, `format_results_document()`; threaded
  `log_lines`/`when` through `render_report_pdf()`,
  `render_report_bytes()`, `save_analysis_result_to_file()`; `main()`
  now passes `log_lines` to both Save and Download, and computes a
  single `when` per Download click so its filename and content always
  agree. Updated `TASKS.md`'s `save-analysis-results-to-file` entry.
  Updated/added tests in `tests/test_app.py`: new filename format, new
  `results_subdirectory`/`extract_llm_usage_summary`/
  `format_results_document` unit tests, and a full app-level test
  (`test_app_save_analysis_results_includes_llm_usage_when_fallback_ran`)
  that actually mocks the LLM path and asserts the token-usage line
  lands in the real saved file — not just that the helper function
  works in isolation.
- **Outcome**: `python -m pytest -q` — 102 passed (96 previously + 6
  new). Coverage: `src/app.py` 99%. Manually booted `streamlit run
  src/app.py` — healthy, no server-log errors.

## 2026-09-09 16:27:52 — Update: add "Analysis Results" header to saved content (save-analysis-results-to-file)

- **Change**: Human asked to add an "Analysis Results" header to the
  saved/downloaded results file content, matching the on-screen
  container's own title.
- **Action**: `format_results_document()` now starts with
  `"## Analysis Results"` before the `Generated:`/`LLM usage:` lines.
  `render_report_pdf()`'s heading detection (previously
  `line.startswith("###")`, matching only `format_report_markdown`'s
  own `### Treaty: ...` heading) generalized to `line.startswith("#")`
  so the new `##`-level header is also bolded/sized as a heading in
  the PDF, not rendered as plain body text. Updated `TASKS.md`'s
  entry and the relevant tests in `tests/test_app.py`
  (`format_results_document`'s and `render_report_pdf`'s content
  assertions).
- **Outcome**: `python -m pytest -q` — 102 passed (unaffected count;
  existing tests updated, no net-new). Coverage: `src/app.py` 99%.
  Manually booted `streamlit run src/app.py` — healthy, no server-log
  errors.

## 2026-09-09 16:36:48 — Closing task: Save analysis results to a file (save-analysis-results-to-file)

- PR #60 merged into `main` at `eac417f`. Human explicitly approved
  marking `save-analysis-results-to-file` done. Removing it from
  `TASKS.md`'s P1 section (and adding it to the "Recently completed"
  list) on this `close/save-analysis-results-to-file` branch/PR,
  titled `Closing task as "Done": Save analysis results to a file`,
  per the mandatory task-closing workflow.

## 2026-09-09 16:48:06 — Closing task: Auto-clear Analysis Results on new treaty selection (auto-clear-results-on-new-selection), PR #59 closed unmerged

- **Goal**: Human asked to resolve PR #59's merge conflict with `main`.
- **Analysis**: Investigating the conflict revealed its real cause:
  `task/save-analysis-results-to-file` (PR #60, merged via PR #61) was
  accidentally branched off `task/auto-clear-results-on-new-selection`
  instead of off `main` — confirmed via `gh pr view 60 --json commits`,
  whose first commit is `588727d`, the exact commit that *is* PR #59.
  So `main` already contains this feature's fingerprint-based
  auto-clear logic byte-for-byte (verified: `git show
  df354dc:src/app.py` already has `selected_fingerprint` and the
  `run_result.get("fingerprint") != selected_fingerprint` check).
  Attempting the merge confirmed this: the only real conflicts were
  adjacent-insertion whitespace/ordering, not logic differences,
  because both sides already held identical code.
- **Decision (asked via AskUserQuestion)**: Since merging PR #59 would
  be a no-op, closed it without merging rather than force a redundant
  merge commit — offered both options, human chose closing.
- **Action**: `gh pr close 59` with an explanatory comment. Branched
  `close/auto-clear-results-on-new-selection` off `main`. Removed
  `auto-clear-results-on-new-selection` from `TASKS.md`'s P1 (its
  content already shipped, so this is a same-content closure, not a
  new merge) and added it to "Recently completed".
- **Outcome**: PR #59 closed (not merged) on GitHub. `TASKS.md` no
  longer lists the task, since its functionality is confirmed already
  live on `main`. Local `task/auto-clear-results-on-new-selection`
  branch left as-is for now (safe to delete later — its content is
  fully superseded).

## 2026-09-09 17:02:04 — Task: Add Multi Domain-Task Selection (S) candidates to CANDIDATE_TASKS.md (candidate-s-section-multi-domain-task-selection)

- **Goal**: Human asked to return to the Multi Domain-Task Selection
  feature and finally execute the original plan's deliverable: add the
  `S1`-`S8` candidate tasks to `CANDIDATE_TASKS.md` on a branch.
- **Context recap**: This feature was designed earlier in this session
  (goal/analysis/design decisions/the `S` section draft), but per the
  human's request the design writeup itself
  (`DOMAIN_TASK_SELECTION_PLAN.md`) was kept **outside this repo**, in
  the human's PyCharm Scratches folder (renamed
  `Reinsurance_DOMAIN_TASK_SELECTION_PLAN.md`), rather than committed
  here — only this round's actual deliverable (the `S` section in
  `CANDIDATE_TASKS.md`) was meant to land in the repo. That deliverable
  was never executed at the time, because the conversation moved on to
  a different request (S9/A11) before circling back.
- **Analysis**: Re-reading the scratch plan file found a leftover
  inconsistency from an earlier edit in this session: its "detailed
  entries" section still contained the full old `S9` (treaty sample
  selection UI) writeup, even though a note directly above it, and the
  summary table, already correctly said `S9` was tracked separately as
  `A11` instead — an incomplete edit from when that decision was made.
  Cleaned it up in the scratch file (deleted the stray `S9` paragraph)
  before using the file as the source for this task, so the `S`
  section added here correctly contains only `S1`-`S8`.
  Also found two stale local git branches from earlier in this session
  with no unique commits: `task/domain-task-selection-candidates`
  (superseded by the renamed `feature/...` branch) and
  `task/auto-clear-results-on-new-selection` (already fully merged via
  a different branch, PR closed unmerged) — deleted both (local, and
  the latter's remote copy too) as routine cleanup.
- **Action**: Branched `feature/multi-domain-task-selection-candidates`
  off `main` (a fresh name, since `feature/domain-task-selection-
  candidates` was already used and merged for the `A11` addition).
  Edited `CANDIDATE_TASKS.md`: updated the intro "two categories" text
  to "three categories" describing `S`; updated the ID-scheme note;
  added a new "Multi Domain-Task Selection" summary table (`S1`-`S8`)
  after the Facultative summary table; added a full `## S. Multi
  Domain-Task Selection` detailed section (context paragraph + 8
  `###`-style entries) after `## B. Business Domain`'s Facultative
  entries, before `## Document-quality sensitivity`. Added
  `candidate-s-section-multi-domain-task-selection` to `TASKS.md`'s
  P2, per the repo's "no exceptions" task-tracking convention.
- **Outcome**: `python -m pytest -q` — 102 passed, unaffected
  (docs-only change, no source files touched). Confirmed no `S[0-9]`
  ID collisions existed before writing. Awaiting human review/approval
  before this task is marked done and removed from `TASKS.md`, and
  before deciding which (if any) `S` item(s) actually graduate into
  real work.

## 2026-09-09 17:08:35 — Closing task: Add Multi Domain-Task Selection (S) candidates to CANDIDATE_TASKS.md (candidate-s-section-multi-domain-task-selection)

- PR #63 merged into `main` at `363839e`. Human explicitly approved
  marking `candidate-s-section-multi-domain-task-selection` done.
  Removing it from `TASKS.md`'s P2 section (and adding it to the
  "Recently completed" list) on this `close/candidate-s-section-
  multi-domain-task-selection` branch/PR, titled `Closing task as
  "Done": Add Multi Domain-Task Selection (S) candidates to
  CANDIDATE_TASKS.md`, per the mandatory task-closing workflow.

## 2026-09-09 17:15:50 — Task: Graduate S1 (Domain task registry & metadata) into TASKS.md as P1 (domain-task-registry)

- **Goal**: Human asked to graduate `S1` from `CANDIDATE_TASKS.md`
  into the real backlog in `TASKS.md`, at P1 priority. (This is the
  graduation step only — scoping the work for later pickup, not
  implementing it now; explained the distinction to the human before
  they confirmed.)
- **Analysis**: Checked `src/workflow.py` for the actual node function
  names (`extractor_node`, `verifier_node`, `analyst_node`) to make
  the registry's planned "which workflow node(s) it needs" field
  concrete and accurate (`B0` → `analyst_node`) rather than vague.
  Counted `CANDIDATE_TASKS.md`'s Business Domain tables precisely
  (`B0`-`B9`: 10, one shipped; `C1`-`C5`: 5; `F1`-`F4`: 4 — 19 total)
  so the acceptance criteria's "one entry per candidate" claim is
  verifiably correct, not just plausible-sounding.
- **Decision**: Scoped `domain-task-registry` narrowly to just
  building the catalog module and its own tests — explicitly *not*
  wiring it into `src/workflow.py` or `src/app.py` yet (that's `S2`/
  `S6`'s job), so this graduated task has no behavior-changing blast
  radius on the shipped app when picked up.
- **Action**: Branched `feature/graduate-s1-domain-task-registry` off
  `main`. Added `domain-task-registry` to `TASKS.md`'s P1. Updated
  `CANDIDATE_TASKS.md`'s `S1` Status (summary row + detailed heading)
  from `Proposed` to `📋 In TASKS.md`, per the file's own sync
  convention.
- **Outcome**: Documentation/backlog change only — no source files
  touched yet; `python -m pytest -q` expected unaffected (verifying
  before commit).

## 2026-09-09 17:58:40 — Task: Domain task registry & metadata (domain-task-registry)

- **Goal**: Implement `domain-task-registry` (P1, graduated from
  `S1`): a small catalog listing every candidate domain task from
  `CANDIDATE_TASKS.md`'s Business Domain tables, as the future single
  source of truth for `S2`'s graph builder and `S6`'s selector UI —
  scoped to just the registry itself, no wiring into `src/workflow.py`
  or `src/app.py`.
- **Analysis**: Re-read `CANDIDATE_TASKS.md`'s Treaty/Claims/
  Facultative summary tables directly (not from memory) to get exact
  titles, candidate IDs, and Shape values: `B0`-`B9` (10, only `B0`
  shipped), `C1`-`C5` (5), `F1`-`F4` (4) — 19 total. Checked
  `src/workflow.py` for the real node function name (`analyst_node`)
  so `B0`'s `workflow_node` field is accurate, not a guess.
- **Decision**: A frozen dataclass (`DomainTask`) with
  `id`/`title`/`candidate_id`/`implementation_status`/`shape`/
  `workflow_node` fields, matching `src/sample_treaties.py`'s existing
  registry pattern in this repo (same frozen-dataclass-list shape) for
  consistency. `implementation_status` and `shape` typed as `Literal`
  string unions rather than a new enum class, since `Severity` in
  `src/models.py` already sets the local precedent of using plain
  lowercase string values for this kind of small fixed vocabulary.
  Deliberately did not add a lookup helper function (e.g.
  `get_domain_task(candidate_id)`) — the task's acceptance criteria
  only calls for the data structure itself; a lookup helper is
  speculative until `S2`/`S6` actually need one.
- **Action**: Branched `task/domain-task-registry` off `main`.
  Creating `src/domain_tasks.py` (the registry) and
  `tests/test_domain_tasks.py` (direct unit tests) next.

- **Outcome**: Implemented `src/domain_tasks.py`: a `DomainTask` frozen
  dataclass (`id`/`title`/`candidate_id`/`implementation_status`/
  `shape`/`workflow_node`) and a `DOMAIN_TASKS` list with all 19
  entries (`B0`-`B9`, `C1`-`C5`, `F1`-`F4`), only `B0` marked
  `implemented` with `workflow_node="analyst_node"`. Added
  `tests/test_domain_tasks.py` with 5 direct unit tests: one entry per
  candidate ID (no duplicates/omissions), unique `id`s, exactly `B0`
  implemented (with the correct title/node), every non-implemented
  entry has `workflow_node=None`, and every entry's fields are
  populated with valid values.
- **Verification**: `python -m pytest -q` — 107 passed (102 previously
  + 5 new), 100% coverage on the new module. `src/app.py` and
  `src/workflow.py` untouched, confirming no behavior change to the
  running app, per this task's explicit scope limit. Awaiting human
  review/approval before this task is marked done and removed from
  `TASKS.md`.

## 2026-09-09 18:03:57 — Closing task: Domain task registry & metadata (domain-task-registry)

- PR #66 merged into `main` at `9c71784`. Human explicitly approved
  marking `domain-task-registry` done. Removing it from `TASKS.md`'s
  P1 section (and adding it to the "Recently completed" list) on this
  `close/domain-task-registry` branch/PR, titled `Closing task as
  "Done": Domain task registry & metadata`, per the mandatory
  task-closing workflow. Also updated `CANDIDATE_TASKS.md`'s `S1`
  Status (summary row + detailed heading) from `📋 In TASKS.md` to
  `✅ Done (shipped as \`domain-task-registry\`)`, matching the pattern
  used for `A1`-`A3`/`A11`.

## 2026-09-09 22:36:13 — Task: Graduate S2-S8 into TASKS.md as P1 (Multi Domain-Task Selection)

- **Goal**: Human asked to graduate all remaining `S`-series
  candidates (`S2`-`S8`) into `TASKS.md` at once, to then pick them up
  and implement one at a time in later sessions.
- **Decision**: Used P1 for all seven, matching `S1`'s priority
  (`domain-task-registry`) — the human didn't specify a level, and
  keeping the whole chain visibly at the same priority as the already-
  shipped first piece felt like the least surprising default; easy to
  re-prioritize individual entries later if needed.
- **Analysis**: Checked `src/models.py`/`src/workflow.py` for the
  exact current schema (`WorkflowState.report: AnomalyReport | None`,
  `class WorkflowState(TypedDict, total=False)`) so `S3`'s planned
  `task_results: dict[str, TaskResult]` replacement is described
  precisely, not vaguely. Reused each candidate's `CANDIDATE_TASKS.md`
  writeup as the base `Details` text, but added concrete `Files`/
  `Acceptance` sections scoped against this repo's actual file/
  function names (e.g. `S2`'s `analyst_node` → `burn_cost_check_node`
  rename, `S4`'s reuse of `src/app.py`'s already-shipped
  `extract_llm_usage_summary()` log-parsing pattern for the actual-
  cost side) — CANDIDATE_TASKS.md entries don't carry that level of
  implementation detail, but a real `TASKS.md` entry needs enough to
  be picked up and started without re-deriving scope from scratch.
  Added `Blocked by` fields reflecting the dependency chain already
  documented in `CANDIDATE_TASKS.md`'s Depends-on column (`S3`→`S2`;
  `S5`→`S2`,`S3`; `S6`→`S4`; `S7`→`S3`,`S5`; `S8`→ all of `S2`-`S7`)
  so picking the wrong one out of order is caught by the task list
  itself, not just tribal knowledge.
- **Action**: Branched `feature/graduate-s2-s8-multi-domain-task-
  selection` off `main`. Added 7 new `TASKS.md` P1 entries:
  `workflow-refactor-multi-task-pipeline` (`S2`),
  `multi-task-result-aggregation-schema` (`S3`),
  `per-task-cost-estimation` (`S4`), `multi-task-messaging-logging`
  (`S5`), `multi-task-selection-ui` (`S6`), `multi-task-results-ui`
  (`S7`), `multi-task-e2e-test-coverage` (`S8`). Updated
  `CANDIDATE_TASKS.md`'s `S2`-`S8` Status (summary rows + detailed
  headings) from `Proposed` to `📋 In TASKS.md`, per the file's sync
  convention.
- **Outcome**: `python -m pytest -q` — 107 passed, unaffected
  (docs-only change, no source files touched). Awaiting human review/
  approval before this graduates for real (task-by-task pickup starts
  after that, per the human's stated plan).

## 2026-09-10 14:56:31 — Task: Workflow refactor: split shared pipeline from per-task analysis nodes (workflow-refactor-multi-task-pipeline)

- **Goal**: Implement `workflow-refactor-multi-task-pipeline` (P1,
  graduated from `S2`): keep `Extractor → [LLM Fallback] → Verifier`
  as a shared pipeline every domain task needs, rename `analyst_node`
  to `burn_cost_check_node` (logic unchanged), and parameterize
  `build_workflow_graph()` by a set of selected task IDs so it only
  runs the analysis node(s) for tasks that are both selected and
  marked `implemented` in `src/domain_tasks.py`'s registry — with
  selecting only `B0` behaving exactly like today's fixed graph
  (regression safety net).
- **Note on process**: Implemented this before branching/claiming in
  `TASKS.md`, out of order relative to the mandatory workflow (branch
  → claim → document reasoning → implement). Corrected by claiming the
  task and creating `task/workflow-refactor-multi-task-pipeline` before
  committing anything — no work was lost, but flagging the ordering
  slip here rather than silently glossing over it.
- **Analysis**: Checked every caller of `analyst_node`/
  `build_workflow_graph`/`run_workflow`/`run_workflow_from_pdf`
  (`src/app.py`, `tests/test_workflow.py`, `tests/test_integration.py`,
  `tests/eval/scorer.py`) before touching anything, to confirm which
  call sites pass no task-selection argument today and therefore need
  the new parameter's default to reproduce today's exact behavior.
  Found `README.md`'s mermaid diagram is auto-generated by
  `scripts/regenerate_workflow_graph.py` (invoked by the
  `.githooks/pre-commit` hook, already enabled in this checkout) and
  guarded by `tests/test_workflow_graph_docs.py` — renaming the
  `"analyst"` node ID would break that test until the diagram is
  regenerated, so ran the regeneration script as part of this change
  rather than leaving the doc-sync test to catch it.
- **Decision**: `build_workflow_graph(selected_task_ids: set[str] |
  None = None)` — `None` defaults to `frozenset({"burn_cost_check"})`,
  reproducing the old fixed graph exactly for every existing caller.
  The registry's `workflow_node` string field is resolved directly via
  `globals()[task.workflow_node]` rather than maintaining a second,
  separately-updated `{task_id: callable}` mapping in `workflow.py` —
  this keeps `src/domain_tasks.py` the single source of truth for both
  "is this implemented" and "which function runs it," so the two can't
  drift out of sync (the whole point of `S1`'s registry). Explicitly
  guarded against selecting more than one *implemented* task at once
  (raises `NotImplementedError` naming `S3` as the actual blocker) —
  unreachable today since the registry has only one implemented entry,
  but silently letting a second task's node overwrite
  `WorkflowState.report` would be a real, confusing bug once `S3`'s
  multi-task schema doesn't exist yet to prevent it; explicit failure
  beats silent data loss.
- **Action**: Branched `task/workflow-refactor-multi-task-pipeline` off
  `main` (after the fact, per the process note above). Edited
  `src/workflow.py` (rename, parameterized `build_workflow_graph()`,
  updated `run_workflow()`/`run_workflow_from_pdf()` signatures),
  `src/domain_tasks.py` (updated `workflow_node` value + docstring),
  `tests/test_domain_tasks.py`, `tests/test_workflow.py` (renamed
  tests + 4 new tests covering the selection parameter: default
  matches explicit `B0`-only selection, empty selection completes with
  no report, selecting a not-implemented task skips gracefully, and
  the multi-implemented-task guard actually raises), `tests/test_app.py`
  (updated the "Analyst" log-text assertion to "Burn-Cost Check").
  Ran `scripts/regenerate_workflow_graph.py` to update `README.md`'s
  diagram, and fixed the few "Analyst" prose/table mentions in
  `README.md` for consistency with the rename (left historical
  "Example output" transcript blocks alone, since those already
  predate several other unrelated additions and are documented
  elsewhere as point-in-time snapshots, not living truth).
- **Outcome**: `python -m pytest -q` — 111 passed (107 previously + 4
  new). Coverage: `src/workflow.py` 99% (only a pre-existing
  unreachable line gap remains). Ran
  `python -m tests.eval.run_eval` manually — all 5 golden cases still
  score 100%, confirming byte-identical end-to-end behavior. Manually
  booted `streamlit run src/app.py` — healthy, no server-log errors.
  Awaiting human review/approval before this task is marked done and
  removed from `TASKS.md`.

## 2026-09-10 15:13:52 — Closing task: Workflow refactor: split shared pipeline from per-task analysis nodes (workflow-refactor-multi-task-pipeline)

- PR #69 merged into `main` at `bb2546f`. Human explicitly approved
  marking `workflow-refactor-multi-task-pipeline` done. Removing it
  from `TASKS.md`'s P1 section (and adding it to the "Recently
  completed" list) on this `close/workflow-refactor-multi-task-
  pipeline` branch/PR, titled `Closing task as "Done": Workflow
  refactor: split shared pipeline from per-task analysis nodes`, per
  the mandatory task-closing workflow. Also updated
  `CANDIDATE_TASKS.md`'s `S2` Status (summary row + detailed heading)
  from `📋 In TASKS.md` to `✅ Done (shipped as \`workflow-refactor-
  multi-task-pipeline\`)`, matching the pattern used for `S1`/`A1`-
  `A3`/`A11`.

## 2026-09-10 15:18:32 — Task: Per-task cost estimation (pre-run) & actual cost tracking (post-run) (per-task-cost-estimation)

- **Goal**: Implement `per-task-cost-estimation` (P1, graduated from
  `S4`): a cost-math module providing a pre-run per-task $ estimate
  (near-zero for `deterministic` tasks, document-length-scaled for
  `llm`/`hybrid` tasks) and a post-run actual-cost conversion from real
  token counts — module only, no UI wiring (that's `S6`).
- **Analysis**: No existing pricing constants anywhere in this repo
  (`src/llm_client.py` and `src/workflow.py` only ever log raw token
  counts, never convert to $). Used the `claude-api` skill (triggered
  per this session's own instructions, since I was about to hardcode
  Anthropic pricing) to get authoritative, current published pricing
  for Claude Haiku 4.5 (`src/workflow.py`'s `_LLM_MODEL =
  "claude-haiku-4-5-20251001"`) rather than recalling a possibly-stale
  number from training: **$1.00 / 1M input tokens, $5.00 / 1M output
  tokens**.
- **Decision**: Kept the pre-run estimate deliberately rough and
  clearly labeled as such — a fixed "~500 input tokens/page" heuristic
  and a fixed small output-token estimate for a single structured
  tool-use response, not a real token count (that would need actually
  tokenizing the document, which is out of scope for a pre-run
  estimate before any node has run). `estimate_task_cost(task,
  page_count)` branches purely on `task.shape` — `deterministic` is
  always `0.0` regardless of page count, since no LLM call is
  involved; `llm`/`hybrid` scale linearly with `page_count`.
  `actual_task_cost(input_tokens, output_tokens)` is a pure function
  over real numbers, no estimation involved — this is what `S4`'s
  Acceptance calls the "actual" side, fed by `llm_extraction_fallback`'s
  already-logged usage once a later task (`S5`/`S6`) wires it in.
- **Action**: Claimed `per-task-cost-estimation` and branched
  `task/per-task-cost-estimation` off `main` before writing any code
  (learned from the previous task's ordering slip). Creating
  `src/cost_estimation.py` and `tests/test_cost_estimation.py` next.

- **Outcome**: Implemented `src/cost_estimation.py`: `HAIKU_INPUT_
  PRICE_PER_TOKEN`/`HAIKU_OUTPUT_PRICE_PER_TOKEN` constants ($1.00/
  $5.00 per 1M tokens), `estimate_task_cost(task, page_count)` (0.0
  for `deterministic`, linearly page-scaled for `llm`/`hybrid`), and
  `actual_task_cost(input_tokens, output_tokens)` (pure $ conversion).
  Added `tests/test_cost_estimation.py` with 7 direct unit tests:
  deterministic is always zero (including at high page counts),
  llm-shaped cost scales with page count, hybrid-shaped is non-zero,
  actual cost matches the published per-token prices at 1M tokens,
  actual cost matches a known real example (500/60 tokens, the same
  numbers used in `tests/test_app.py`'s mock LLM client), and zero
  tokens costs zero.
- **Verification**: `python -m pytest -q` — 118 passed (111 previously
  + 7 new), 100% coverage on the new module. `src/app.py` and
  `src/workflow.py` untouched, confirming no wiring into the UI or
  workflow yet, per this task's explicit scope limit (that's `S6`'s
  job). Awaiting human review/approval before this task is marked done
  and removed from `TASKS.md`.

## 2026-09-10 15:25:39 — Closing task: Per-task cost estimation (pre-run) & actual cost tracking (post-run) (per-task-cost-estimation)

- PR #71 merged into `main` at `b4a62b4`. Human explicitly approved
  marking `per-task-cost-estimation` done. Removing it from
  `TASKS.md`'s P1 section (and adding it to the "Recently completed"
  list) on this `close/per-task-cost-estimation` branch/PR, titled
  `Closing task as "Done": Per-task cost estimation (pre-run) & actual
  cost tracking (post-run)`, per the mandatory task-closing workflow.
  Also updated `CANDIDATE_TASKS.md`'s `S4` Status (summary row +
  detailed heading) from `📋 In TASKS.md` to `✅ Done (shipped as
  \`per-task-cost-estimation\`)`, matching the pattern used for
  `S1`/`S2`/`A1`-`A3`/`A11`.

## 2026-09-10 15:38:00 — Task: Multi-task result aggregation & state schema (multi-task-result-aggregation-schema)

- **Goal**: Implement `multi-task-result-aggregation-schema` (P1,
  graduated from `S3`): add a `TaskResult` schema and
  `WorkflowState.task_results` so results can eventually be tracked
  per-task instead of as one combined report.
- **Scope conflict found before writing code**: The task's `Details`
  said to *replace* `WorkflowState.report` with `task_results`, but
  its own `Files` list didn't include `src/app.py` — which depends
  heavily on `state["report"]` today (report rendering, Save/Download,
  PDF export, per-treaty results organization — all built in later
  sessions after `S3` was originally drafted, before any of that
  existed). A literal replacement would silently break `src/app.py`
  without it being in scope to fix. Asked the human via
  `AskUserQuestion` rather than guessing which way to resolve it.
- **Decision**: Human chose: keep `WorkflowState.report` exactly as it
  is today (so `src/app.py` keeps working completely unchanged), and
  add `task_results` **alongside** it, additive — designed so the
  schema is ready to hold multiple entries once more than one domain
  task can run on the same treaty, without actually implementing that
  multi-task execution now (`S2`'s existing `NotImplementedError`
  guard for >1 implemented task still applies). Updated `TASKS.md`'s
  entry to record this scope revision explicitly (dated inline) before
  writing any code, per the "if the human changes actions within an
  in-progress task, update the entry and log it" rule — this is an
  unusually large scope narrowing to leave undocumented.
  Also decided: populating `skipped_not_implemented`/`failed` entries
  for the *full* selected-task-ids set (not just what actually ran) is
  `S5`'s job, not this one — `S5`'s own Details already describe
  exactly that ("combined-run summary... which tasks ran/skipped/
  failed"), and doing it here would need `selected_task_ids` threaded
  into runtime state, a bigger change than this task's stated Files
  list implies. This task only populates a `"ran"` entry for whatever
  task actually executed.
- **Action**: Claimed `multi-task-result-aggregation-schema` and
  branched `task/multi-task-result-aggregation-schema` off `main`
  before writing any code. Implementing `TaskResult` in
  `src/models.py` and wiring `task_results` into
  `burn_cost_check_node`/`WorkflowState` next.

- **Outcome**: Implemented `TaskResult` (`src/models.py`:
  `status`/`findings`/`cost`/`latency`, deliberately generic across
  task shapes unlike `AnomalyReport`'s burn-cost-check-specific
  `treaty`/`claims`/`loss_ratio` fields). Added `WorkflowState.
  task_results: dict[str, TaskResult]` (`src/workflow.py`), populated
  alongside (not instead of) `report` in `burn_cost_check_node`:
  `{"burn_cost_check": TaskResult(status="ran", findings=<same as
  report.findings>, cost=0.0, latency=<measured via
  time.perf_counter()>)}`. Added 3 new tests to
  `tests/test_workflow.py`: the node populates both keys consistently,
  `run_workflow()`'s `task_results` matches its `report`, and an empty
  task selection produces no `task_results` at all (nothing ran).
- **Verification**: `python -m pytest -q` — 121 passed (118 previously
  + 3 new), all unchanged (no existing test needed modification,
  confirming `report`'s behavior is genuinely untouched). Coverage:
  `src/workflow.py` 99%. Ran `python -m tests.eval.run_eval` manually
  — all 5 golden cases still 100%. Manually booted `streamlit run
  src/app.py` — healthy, no server-log errors. Awaiting human review/
  approval before this task is marked done and removed from
  `TASKS.md`.

## 2026-09-10 15:49:37 — Closing task: Multi-task result aggregation & state schema (multi-task-result-aggregation-schema)

- PR #73 merged into `main` at `9470f3c`. Human explicitly approved
  marking `multi-task-result-aggregation-schema` done. Removing it
  from `TASKS.md`'s P1 section (and adding it to the "Recently
  completed" list) on this `close/multi-task-result-aggregation-
  schema` branch/PR, titled `Closing task as "Done": Multi-task result
  aggregation & state schema`, per the mandatory task-closing
  workflow. Also updated `CANDIDATE_TASKS.md`'s `S3` Status (summary
  row + detailed heading) from `📋 In TASKS.md` to `✅ Done (shipped as
  \`multi-task-result-aggregation-schema\`)`, and rewrote its detailed
  entry's description to reflect the shipped (additive) scope instead
  of the original "replace `report`" text, so `CANDIDATE_TASKS.md`
  doesn't describe a design that was deliberately not built.

## 2026-09-10 15:55:24 — Task: Task selection UI (multi-task-selection-ui)

- **Goal**: Implement `multi-task-selection-ui` (P1, graduated from
  `S6`): a checkbox per `src/domain_tasks.py` registry entry in
  `src/app.py`, disabled for not-implemented tasks, showing a live
  per-task cost estimate (from `per-task-cost-estimation`'s
  `estimate_task_cost()`) plus a running cumulative total; the checked
  task ID set feeds `build_workflow_graph()` (via
  `run_workflow_from_pdf`'s `selected_task_ids` param from
  `workflow-refactor-multi-task-pipeline`) when "Analyze" is clicked.
- **Analysis**: `estimate_task_cost(task, page_count)` needs a page
  count, which isn't known until a document is parsed — but the
  live-cost requirement means it must be available before "Analyze"
  runs the full workflow. Reused the same pattern the existing
  "Review treaty" dialog already uses (write selected bytes to a temp
  file, call `extract_treaty_sections()` for cheap local PDF parsing,
  no LLM call) to get a page count as soon as a document is selected,
  before any task is even run.
- **Decision**: Render one `st.checkbox` per `DOMAIN_TASKS` entry
  between the source-input container and the Review/Analyze buttons.
  Not-implemented tasks render `disabled=True` with a "Not
  implemented" caption (same visual pattern as the existing disabled
  Review/Analyze buttons). The only implemented task (`B0`/
  `burn_cost_check`) defaults to checked, preserving today's
  "B0 runs by default" convenience while still being a real, uncheckable-
  if-desired checkbox — satisfies "explicit selection step" without
  silently changing default behavior for existing users. "Analyze" is
  now also disabled when no task is checked (in addition to the
  existing no-document-selected guard). Checked task IDs are collected
  into a `set[str]` and threaded through `run_workflow_on_bytes()` →
  `run_workflow_from_pdf()` → `build_workflow_graph()`'s existing
  `selected_task_ids` parameter (from `S2`) — no new plumbing needed
  there, just passing the UI's selection through what `S2` already
  built.
- **Action**: Claimed `multi-task-selection-ui` and branched
  `task/multi-task-selection-ui` off `main` before writing code.
  Implementing the checkbox list, page-count helper, and threading
  `selected_task_ids` through `src/app.py`'s workflow-running
  functions next.

- **Outcome**: Implemented in `src/app.py`: `get_pdf_page_count()`
  (cheap local PDF parse for the live cost estimate, no LLM call);
  threaded `selected_task_ids` through `run_workflow_on_bytes()` and
  `_run_workflow_with_logging()` down to `run_workflow_from_pdf()`;
  added a "Domain tasks to run" checklist between the source-input
  container and the Review/Analyze buttons — one `st.checkbox` per
  `DOMAIN_TASKS` entry, disabled with a "Not implemented" caption for
  every non-implemented task, defaulting checked for `burn_cost_check`
  (the only implemented one today). Each checked task shows its live
  `estimate_task_cost()` figure; a running total appears below the
  list. "Analyze" is now also disabled when no task is checked (in
  addition to the existing no-document-selected guard).
  Found along the way: `burn_cost_check` is `hybrid`-shaped (matching
  `CANDIDATE_TASKS.md`'s `B0` Shape column), not `deterministic`, so
  its live estimate is never exactly `$0.0000` even with no document
  selected (`cost_estimation.py`'s fixed output-token estimate still
  applies) — caught this via a wrong test assumption, fixed the test
  rather than the (correct) implementation once traced back to
  `src/domain_tasks.py`'s actual registry entry.
  Added 4 new tests to `tests/test_app.py`: one checkbox per registry
  entry with only implemented ones enabled, `B0` defaults checked with
  the correct hybrid-shaped cost estimate shown, "Analyze" disables
  when the only checked task is unchecked, and the cost estimate
  increases for a larger selected document.
- **Verification**: `python -m pytest -q` — 125 passed (121 previously
  + 4 new), zero existing tests modified (only the one new test I
  wrote wrong needed a fix, not any pre-existing test). Coverage:
  `src/app.py` 99%. Ran `python -m tests.eval.run_eval` manually — all
  5 golden cases still 100%. Manually booted `streamlit run
  src/app.py` — healthy, no server-log errors. Awaiting human review/
  approval before this task is marked done and removed from
  `TASKS.md`.

## 2026-09-10 16:12:54 — Closing task: Task selection UI (multi-task-selection-ui)

- PR #75 merged into `main` at `950f7b1`. Human explicitly approved
  marking `multi-task-selection-ui` done. Removing it from
  `TASKS.md`'s P1 section (and adding it to the "Recently completed"
  list) on this `close/multi-task-selection-ui` branch/PR, titled
  `Closing task as "Done": Task selection UI (checkboxes, disabled/
  blurred not-implemented tasks, live cost readout)`, per the
  mandatory task-closing workflow. Also updated `CANDIDATE_TASKS.md`'s
  `S6` Status (summary row + detailed heading) from `📋 In TASKS.md` to
  `✅ Done (shipped as \`multi-task-selection-ui\`)`, matching the
  pattern used for `S1`-`S4`/`A1`-`A3`/`A11`.

## 2026-09-10 16:17:04 — Task: Multi-task messaging & logging (multi-task-messaging-logging)

- **Goal**: Implement `multi-task-messaging-logging` (P1, graduated
  from `S5`): tag per-task log lines with a task-id, and add a
  combined-run summary of which tasks ran/were skipped/failed.
- **Two judgment calls made before writing code** (smaller than `S3`'s
  scope conflict, but worth recording since the task's own wording
  doesn't quite match implementation reality):
  1. **"Every node's log line gains a task-id tag"** — read literally,
     this would tag `extractor_node`/`llm_extraction_fallback`/
     `verifier_node`'s log lines too, but those are the *shared*
     pipeline every domain task needs, not any one task's own work —
     tagging them with e.g. `"[burn_cost_check]"` would misattribute
     shared infrastructure to one task. Tagging only the per-task
     analysis node(s) (today: just `burn_cost_check_node`) is the
     accurate reading of the *intent* (a multi-task run's combined log
     staying attributable per task), even though it's not literally
     "every node."
  2. **"A new `format_multi_task_status()`-style function... replacing
     `format_extraction_status()`"** — checked `format_extraction_
     status()`'s actual current use (`src/app.py`, one `st.caption` in
     the debug expander) and found it reports something genuinely
     different and still useful: *how* extraction happened (regex vs.
     LLM fallback), which is orthogonal to *which domain tasks ran*.
     Literally replacing it would delete working, still-relevant
     information the debug panel currently shows. Following the same
     additive precedent the human set for `S3`'s `report`/`task_results`
     conflict: keep `format_extraction_status()` as-is, add `format_
     multi_task_status()` as a second, additional caption line right
     after it, rather than deleting the first.
- **Design for the "skipped" determination**: `WorkflowState.task_
  results` (from `S3`) only ever holds entries for tasks that actually
  ran (`S3`'s own deliberate scope limit) — it was never going to carry
  the full selected-task-ids set needed to know what was *skipped*.
  Rather than threading `selected_task_ids` into runtime state (the
  "bigger change" `S3` explicitly deferred to this task), compute the
  skip/fail summary in `src/app.py` by diffing the UI's already-known
  `selected_task_ids` (from `S6`, already available at the point
  `_run_workflow_with_logging()` is called) against `task_results`'
  keys — no `WorkflowState` schema change needed. Stored
  `selected_task_ids` in the `workflow_run` session-state dict
  (alongside `state`/`log_lines`/etc.) so it's still available when the
  debug panel renders on a later rerun, same pattern already used for
  `selected_name`/`fingerprint`.
- **Action**: Claimed `multi-task-messaging-logging` and branched
  `task/multi-task-messaging-logging` off `main` before writing code.
  Implementing the log tag in `src/workflow.py` and `format_multi_
  task_status()` + wiring in `src/app.py` next.

- **Outcome**: Implemented: `src/workflow.py`'s `burn_cost_check_node`
  log line now prefixed `"[burn_cost_check] "`. Added `src/app.py`'s
  `format_multi_task_status(selected_task_ids, task_results)` —
  additive alongside `format_extraction_status()`, not replacing it —
  reporting per selected task whether it `ran` (with findings/cost/
  latency), was `skipped (not implemented)`, `did not run (extraction
  incomplete)`, or carries some other `TaskResult.status` (e.g.
  `failed`). Threaded `selected_task_ids` into the `workflow_run`
  session-state dict (same pattern as `selected_name`/`fingerprint`)
  so it survives reruns for the debug panel. Wired the summary into
  both the "Analysis Workflow execution" expander (as a new
  `st.markdown` line) and the saved log file (prefixed alongside the
  existing run header).
  Added 5 new tests to `tests/test_app.py` (`format_multi_task_status`
  covering all four branches: no selection, ran, not-implemented-
  skip, incomplete-extraction, failed) and 1 to `tests/test_workflow.py`
  (`caplog`-based confirmation the log line is actually tagged) and 1
  more to an existing app-level debug-panel test (the summary line
  actually appears after a real Analyze run, not just in isolation).
- **Verification**: `python -m pytest -q` — 131 passed (125 previously
  + 6 new), zero existing tests modified — confirms both
  `format_extraction_status()` and the existing log/debug behavior are
  genuinely untouched. Coverage: `src/app.py` 99%, `src/workflow.py`
  99%. Ran `python -m tests.eval.run_eval` manually — all 5 golden
  cases still 100%. Manually booted `streamlit run src/app.py` —
  healthy, no server-log errors. Awaiting human review/approval before
  this task is marked done and removed from `TASKS.md`.

## 2026-09-10 17:04:17 — Closing task: Multi-task messaging & logging (multi-task-messaging-logging)

- PR #77 merged into `main` at `38d0e99`. Human explicitly approved
  marking `multi-task-messaging-logging` done. Removing it from
  `TASKS.md`'s P1 section (and adding it to the "Recently completed"
  list) on this `close/multi-task-messaging-logging` branch/PR, titled
  `Closing task as "Done": Multi-task messaging & logging`, per the
  mandatory task-closing workflow. Also updated `CANDIDATE_TASKS.md`'s
  `S5` Status (summary row + detailed heading) from `📋 In TASKS.md` to
  `✅ Done (shipped as \`multi-task-messaging-logging\`)`, and rewrote
  its detailed entry to describe the shipped scope (only the per-task
  node tagged, not "every node"; additive alongside `format_
  extraction_status()`, not replacing it) rather than the original
  wording — same pattern as `S3`'s closing entry.

## 2026-09-10 17:13:33 — New task discovered: Dynamic graph fan-out for multi-task selection (multi-task-graph-fanout)

- **Context**: Human asked how the current `data/workflow_graph.png`
  diagram would change as more domain tasks become implemented. In
  answering, re-examined `build_workflow_graph()`
  (`workflow-refactor-multi-task-pipeline`'s output) and confirmed a
  real gap: it only ever wires in *at most one* implemented+selected
  task node — selecting more than one raises `NotImplementedError`
  rather than actually fanning out. This is invisible today (the
  registry has exactly one implemented entry) but means the graph-
  *building* code doesn't yet genuinely support multi-task selection,
  just a "one or zero" special case.
- **Action**: Per the human's explicit instruction ("add it as a
  tasks.md directly"), added `multi-task-graph-fanout` straight to
  `TASKS.md`'s P1 (bypassing `CANDIDATE_TASKS.md` staging, since this
  is a follow-up fix to already-shipped `S2` work discovered directly
  during this session, not a new candidate needing prioritization
  discussion). Scoped per the human's explicit constraint: the graph
  should fan out to every selected+implemented task after `Verifier`
  while leaving the shared pipeline nodes (`extractor_node`,
  `llm_extraction_fallback`, `verifier_node`) completely untouched.
  Not implemented yet — this is the task-creation step only, per the
  "Add any new tasks discovered during work" step of the mandatory
  workflow.

## 2026-09-10 17:19:42 — Task: Dynamic graph fan-out for multi-task selection (multi-task-graph-fanout)

- **Goal**: Implement `multi-task-graph-fanout` (P1, added directly to
  `TASKS.md`): replace `build_workflow_graph()`'s single-node special
  case + `NotImplementedError` guard with real parallel fan-out to
  every selected+implemented task, leaving the shared pipeline nodes
  untouched.
- **Verified before writing code, not assumed**: confirmed via
  `inspect.signature`/docstring that LangGraph 1.2.11's `add_
  conditional_edges` routing function genuinely supports returning a
  `Sequence[Hashable]` for multi-target fan-out (this was an assertion
  I made when drafting the task's Acceptance criteria — checked it
  rather than trusting my own earlier claim). Then ran a minimal
  throwaway two-node fan-out graph to see the *actual* runtime
  behavior, not just the type signature — this surfaced a real gap the
  task description missed: LangGraph's default state channel
  (`last_value` reducer) raises `InvalidUpdateError` if two nodes
  write to the *same* state key in the same step, unconditionally
  (doesn't compare values, just rejects a second write). Since two
  parallel task nodes would each return a `task_results` dict update,
  `WorkflowState.task_results` needs an `Annotated[..., reducer]` merge
  function to combine concurrent partial dict writes, or real fan-out
  would immediately break the moment a second implemented task
  existed — exactly the scenario this task exists to prepare for.
- **Decision**: Add a small `_merge_task_results()` reducer and type
  `task_results` as `Annotated[dict[str, TaskResult],
  _merge_task_results]` in `WorkflowState`. Leave `report` unannotated
  (no reducer) — it's deliberately `burn_cost_check`-specific per
  `S3`'s decision, and no other node should ever write it, so a
  same-step conflict on `report` should stay a real error if it ever
  happens (signals a future task wrongly writing to a field that isn't
  its own), not something to silently paper over with a reducer.
- **Action**: Claimed `multi-task-graph-fanout` and branched
  `task/multi-task-graph-fanout` off `main` before writing code.
  Implementing the reducer, the general fan-out loop in
  `build_workflow_graph()`, and replacing the now-obsolete multi-
  implemented-task-raises test with one that actually proves two
  distinct task nodes both run in parallel next.

- **Outcome**: Implemented in `src/workflow.py`: `_merge_task_results()`
  reducer + `task_results: Annotated[dict[str, TaskResult],
  _merge_task_results]` on `WorkflowState`; `build_workflow_graph()`'s
  single-node special case and `NotImplementedError` guard replaced
  with a loop that adds a node + edge-to-`END` for every task in
  `active_tasks`, and a routing function returning the full
  `active_task_ids` list (LangGraph's real multi-target fan-out) or
  `END`. Replaced the now-obsolete `test_build_workflow_graph_rejects_
  more_than_one_implemented_task` with `test_build_workflow_graph_fans_
  out_to_multiple_implemented_tasks`, which monkeypatches a second,
  genuinely distinct node function into `src.workflow`'s namespace
  (not reusing `burn_cost_check_node` twice, to prove real independent
  execution) and confirms both tasks' `task_results` entries appear
  after a real `run_workflow()` call — not just that the graph compiles
  without raising. Also fixed `test_run_workflow_empty_selection_
  produces_no_task_results` (found by running the suite, not
  anticipated): with `task_results` now reducer-backed, LangGraph seeds
  it with `{}` even when no node writes to it, instead of omitting the
  key entirely — `src/app.py` was already defensive (`.get(...,  {})`)
  so this needed no production-code change, only the test's expectation
  updated to match the new (still-correct) contract.
- **Verification**: `python -m pytest -q` — 131 passed (same count:
  1 obsolete test removed, 1 new one added, 1 existing one fixed for
  the reducer-seeding behavior). Coverage: `src/workflow.py` 99%. Ran
  `python -m tests.eval.run_eval` manually — all 5 golden cases still
  100%, confirming byte-identical behavior for today's real single-task
  selection. Confirmed via `git diff` that the shared pipeline node
  functions (`extractor_node`, `llm_extraction_fallback`,
  `verifier_node`) have zero diff, and that `data/workflow_graph.png`/
  `README.md`'s diagram is completely unchanged (default selection
  still resolves to the same single-node shape). Manually booted
  `streamlit run src/app.py` — healthy, no server-log errors. Awaiting
  human review/approval before this task is marked done and removed
  from `TASKS.md`.

## 2026-09-10 21:50:40 — New task discovered: Regenerate workflow diagram for a multi-task selection example (multi-task-graph-diagram-example)

- **Context**: Human asked why `data/workflow_graph.png` didn't
  visually change after `multi-task-graph-fanout` shipped, then asked
  how to make the diagram change automatically. Explained: the
  `.githooks/pre-commit` hook already auto-regenerates it on every
  commit touching `src/workflow.py` — it's just that
  `scripts/regenerate_workflow_graph.py`'s `get_mermaid_text()` always
  renders `build_workflow_graph()`'s *default* (single-task) selection,
  so the automation working correctly still produces an unchanged
  picture until there's a real multi-task example to render.
- **Action**: Per the human's instruction, added
  `multi-task-graph-diagram-example` directly to `TASKS.md`'s P1
  (bypassing `CANDIDATE_TASKS.md`, same as `multi-task-graph-fanout` —
  a follow-up gap found directly in this session's own work, not a new
  candidate). Explicitly noted a caveat for whoever picks it up: it's
  only meaningfully verifiable once a second *real* domain task is
  implemented (not just mocked, since a mocked example isn't
  appropriate for a permanently-committed README diagram) — flagged
  so this doesn't get picked up prematurely and produce a misleading
  or fake example.

## 2026-09-10 21:58:20 — Closing task: Dynamic graph fan-out for multi-task selection (multi-task-graph-fanout)

- PR #80 merged into `main` at `e352b23`. Human explicitly approved
  marking `multi-task-graph-fanout` done. Removing it from `TASKS.md`'s
  P1 section (and adding it to the "Recently completed" list) on this
  `close/multi-task-graph-fanout` branch/PR, titled `Closing task as
  "Done": Dynamic graph fan-out for multi-task selection`, per the
  mandatory task-closing workflow. No `CANDIDATE_TASKS.md` update
  needed — this task was never graduated from there (`Candidate ID:
  N/A`, added directly to `TASKS.md`).

## 2026-09-10 — New task discovered: Document branch-naming conventions in AGENTS.md (document-branch-naming-conventions)

- **Goal**: Human asked to "check updates in AGENTS" — review
  `AGENTS.md` for anything needing an update given how this session has
  actually been working.
- **Analysis**: Re-read `AGENTS.md` in full. Its "Mandatory Workflow"
  (step 5) and "Branch and PR Discipline" sections only document
  `task/<id>` as a branch-naming convention. In actual practice this
  session, two more conventions have been used consistently but never
  written down: `close/<id>` for step 11's task-closing branch (only
  the PR *title* convention, `Closing task as "Done": <title>`, is
  documented — not the branch name), and `add-task/<id>` for a
  standalone docs-only branch when step 12 ("Add new tasks discovered
  during work") is done as its own PR, separate from later picking up
  and implementing that task (which still uses `task/<id>`). This is
  exactly the pattern being followed right now to add this very task.
  Also noticed a stray, unmatched `</id></id>` fragment at the end of
  the working-tree copy of `AGENTS.md`; checked `git log -- AGENTS.md`
  and `git show HEAD:AGENTS.md` before treating it as a real bug — the
  committed file was clean, so this was a local, uncommitted artifact
  only. Discarded it via `git checkout -- AGENTS.md` rather than filing
  a fix task for a bug that doesn't exist in git history.
- **Decision**: Add a new P2 task, `document-branch-naming-conventions`,
  directly to `TASKS.md` (bypassing `CANDIDATE_TASKS.md` staging, per
  the precedent set by `multi-task-graph-fanout`/`multi-task-graph-
  diagram-example` — this is a fix discovered while doing requested
  review work, not a new candidate needing prioritization). Scoped to
  `AGENTS.md` only: name `close/<id>` and `add-task/<id>` explicitly
  alongside `task/<id>` so all three real conventions are documented.
- **Action**: Added the task to `TASKS.md`'s P2 section (`Candidate ID:
  N/A`, `Files: AGENTS.md`). Following the very convention this task is
  about documenting, this addition is being made on its own
  `add-task/document-branch-naming-conventions` branch/PR — not on
  `close/multi-task-graph-fanout` (where it was originally drafted by
  mistake; moved off via `git stash` before switching branches) and not
  bundled with actually implementing the task later.
- **Outcome**: Docs-only change to `TASKS.md`; no source code touched,
  so no test run needed beyond confirming the repo still discovers
  tests normally. Will run the full suite anyway before pushing, as a
  sanity check on a clean tree.

## 2026-09-10 — Fix: Unclosed `<id>` XML tag in AGENTS.md (fix-agents-md-unclosed-id-tag)

- **Goal**: Human reported a linter flagging "Unclosed XML tag '<id>'"
  at `AGENTS.md` lines 126 and 129.
- **Analysis**: Both lines use a nested-backtick pattern —
  `` `📋 In TASKS.md as \`<id>\`` `` — meant to render the whole status
  string (including its own literal backticks around `<id>`) as one
  inline code span. Standard Markdown doesn't support escaping
  backticks with `\` inside a single-backtick code span: the first
  unescaped-looking backtick after `as ` actually closes the span
  early, leaving `<id>\`` as raw text outside any code span — which is
  why a linter parses the bare `<id>` as an unclosed HTML/XML tag
  instead of literal code content. `AGENTS.md` line 59
  (`` `task/<id>` ``) is a normal single-backtick span with no nested
  backticks, so it wasn't affected.
- **Decision**: Rewrite both spans using CommonMark's documented way to
  include a literal backtick inside a code span — a longer backtick
  run as the delimiter, with a padding space on each side since the
  content itself starts/ends with a backtick: `` `` 📋 In TASKS.md as
  `<id>` `` ``. This keeps `<id>` genuinely inside a code span (so
  linters/renderers treat it as literal text, not a tag) without
  changing the displayed text at all.
- **Action**: Fixed both lines in `AGENTS.md`. Grepped the rest of the
  repo's `.md` files for the same broken `` \`< `` pattern — found one
  more occurrence, in a historical dated `REASONING.md` log entry
  (2026-09-08 area); left it untouched since editing past transcript
  entries would misrepresent the historical record, and transcripts
  aren't linted documentation.
- **Outcome**: `python -m pytest -q` — 131 passed, no regressions
  (docs-only change, no source touched).

## 2026-09-10 — Task: Document close/ and add-task/ branch-naming conventions in AGENTS.md (document-branch-naming-conventions)

- **Goal**: Implement `document-branch-naming-conventions` (P2): name
  `close/<id>` and `add-task/<id>` explicitly in `AGENTS.md`'s
  Mandatory Workflow / Branch and PR Discipline sections, alongside
  the existing `task/<id>`, since this session has used all three
  conventions consistently but only `task/<id>` was documented.
- **Analysis**: `AGENTS.md`'s Mandatory Workflow step 5 documents
  `task/<id>`. Step 11 (closing an approved-done task) currently
  documents only the PR *title* convention
  (`Closing task as "Done": <task title>`) without naming the branch
  itself — this session has consistently used `close/<id>` there (see
  e.g. `close/multi-task-graph-fanout`, PR #82). Step 12 ("Add new
  tasks discovered during work") doesn't distinguish between two
  different real situations: adding a task as part of an already-open
  task's own branch/PR (no separate branch needed), versus adding it
  as a standalone docs-only change with its own branch/PR when
  discovered outside any in-progress task's scope — this session has
  used `add-task/<id>` for the latter case (e.g.
  `add-task/document-branch-naming-conventions` itself, PR #83).
- **Decision**: Edit step 11 to name the branch as
  `close/<id>` (e.g. `close/document-branch-naming-conventions`)
  alongside the existing PR-title naming. Edit step 12 to name
  `add-task/<id>` for the standalone-docs-PR case specifically,
  while noting `task/<id>` still applies once that task is later
  picked up and actually implemented — so the distinction between
  "adding the task" and "doing the task" stays clear. Kept both edits
  minimal and additive: no restructuring of the checklist's numbering
  or existing prose beyond inserting the missing branch names.
- **Action**: Edited `AGENTS.md`'s Mandatory Workflow steps 11 and 12
  to name `close/<id>` and `add-task/<id>` respectively, and added a
  short paragraph to the "Branch and PR Discipline" section right
  after its existing `task/<short-name>` example, summarizing all
  three branch prefixes and what each is for — since the acceptance
  criterion named both sections explicitly, not just the checklist.
- **Outcome**: `python -m pytest -q` — 131 passed, no regressions
  (docs-only change, no source touched). Reviewed the full diff: only
  the three targeted spots changed, no unrelated restructuring.
  Awaiting human review/approval before this task is marked done and
  removed from `TASKS.md`.
