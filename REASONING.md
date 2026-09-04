
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

