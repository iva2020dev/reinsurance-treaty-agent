# Candidate Tasks (Draft — Not Yet in TASKS.md)

This is a **staging list**, not the backlog. Nothing here has been
scoped or approved — it exists so we can clarify and prioritize
together before anything graduates into `TASKS.md` with a real
ID/Details/Files/Acceptance per the usual convention (see
`AGENTS.md`).

Three categories, per discussion on 2026-09-06 (`A`/`B`) and
2026-09-09 (`S`):

- **A. Technical / AI Engineering & Production Harness** — validating
  model behavior, evaluation frameworks, agent-behavior quality
  checks/grounding, and reliability/scalability/cost/latency.
- **B. Business Domain** — grounded in everyday Treaty, Facultative,
  and Claims reinsurance practice, extending what the app already does
  for Treaty underwriting review.
- **S. Multi Domain-Task Selection** — cross-cutting harness/UI work
  that lets a user choose which `B`-series (and eventually `C`/
  `F`-series) domain task(s) to run against a given treaty, with
  per-task cost visibility, rather than every future domain task
  becoming another thing that always runs on every upload. Not itself
  a business-domain content task (so it doesn't belong under `B`), and
  substantial enough (FE+BE+new cost-estimation harness) to warrant
  its own category rather than being squeezed into `A`. See
  `REASONING.md`'s 2026-09-09 entries for the fuller design writeup
  this section was drafted from.

Each item: a short description, a rough shape (deterministic / LLM /
hybrid, and rough dev-effort S/M/L), and why it matters. Items within
each section/subsection are listed in **suggested priority order**
(highest first) — a first-pass ranking by value, effort, and
dependency, not a final decision. See the 2026-09-06 session's
discussion in `REASONING.md` for the fuller cost/effort comparison
this list was drafted from.

Every table below also has a **Status** column: **✅ Done** marks
capability already shipped in the app today (the Treaty **Burn-Cost
Check**, `B0`, plus any candidate that graduated into `TASKS.md` and
was later completed and removed from it there — e.g. Harness's `A1`-
`A3`); **📋 In TASKS.md** marks an item that's graduated into the real
backlog (with its own ID/Details/Files/Acceptance there) but isn't
done yet — see `TASKS.md` for its current status, not here; everything
else is **Proposed** — not started, not scoped, not approved.

**Keeping this in sync**: this file is not auto-updated when `TASKS.md`
changes — whoever graduates a candidate into `TASKS.md`, or completes/
removes one from it, must also update that candidate's row (and its
detailed entry below) here in the same PR. See `AGENTS.md`'s "Keeping
CANDIDATE_TASKS.md in Sync" for the exact rule.

IDs are scoped per category (`A` = Harness, `B` = Treaty, `F` =
Facultative, `C` = Claims, `S` = Multi Domain-Task Selection) and
numbered by current priority position, starting at 1 in each — so the
ID itself tells you the category and current rank. `B0` is the
exception: it's the shipped baseline, not a ranked candidate.

Every table also has an **Answer Type** column, per the 2026-09-06
discussion on how document quality drives task shape (see
"Document-quality sensitivity" below):

- **Extraction** — the output is factual data pulled from the
  document; correctness means matching what's literally written, no
  judgment about meaning/intent required. These are the tasks whose
  *shape* (Deterministic vs. Hybrid) is most sensitive to how cleanly
  the source document is formatted.
- **Interpretation** — the output is a judgment or synthesis that
  requires understanding meaning or intent, not literally stated in
  the text. These stay LLM-shaped regardless of how clean the
  document is.
- **Both** — a distinct extraction step feeds a judgment step that is
  the actual deliverable (e.g. extract a claim narrative *and* judge
  whether it falls under an exclusion).
- **N/A** — harness/infrastructure items that aren't themselves
  answering a question about treaty content.

---

## Summary

### Technical / AI Engineering & Production Harness

| Pri | ID | Task | Status | Shape | Answer Type | Effort | Depends on |
|---|---|---|---|---|---|---|---|
| 1 | A1 | Retry/backoff resilience for the LLM call | ✅ Done | Deterministic | N/A | S | — |
| 2 | A2 | Grounding/assurance check on LLM output | ✅ Done | Hybrid | Both | M | — |
| 3 | A3 | Extraction accuracy eval suite (golden dataset) | ✅ Done | Hybrid | N/A | M | — |
| 4 | A4 | CI-integrated regression eval gate | 📋 In TASKS.md | Deterministic | N/A | S | A3 |
| 5 | A5 | Structured observability upgrade | Proposed | Deterministic | N/A | M | — |
| 6 | A6 | Cost & latency observability + guardrails | Proposed | Deterministic | N/A | M | — |
| 7 | A7 | Adversarial input hardening | Proposed | Hybrid | N/A | M | — |
| 8 | A8 | Data-handling/PII review for third-party LLM calls | Proposed | Deterministic | N/A | S/M | — |
| 9 | A9 | Fallback tiering / cost-aware escalation | Proposed | Hybrid | N/A | M | — |
| 10 | A10 | Human-in-the-loop review workflow | Proposed | Deterministic | N/A | M | — |
| 11 | A11 | Treaty sample selection UI (prepared/golden samples, no local disk) | ✅ Done | Deterministic | N/A | S/M | — |

### Business Domain — Treaty

| Pri | ID | Task | Status | Shape | Answer Type | Effort | Depends on |
|---|---|---|---|---|---|---|---|
| — | B0 | **Burn-Cost Check** | **✅ Done** | Hybrid | Extraction | — (shipped) | — |
| 1 | B1 | Mandatory-clause / exclusion completeness checklist | Proposed | Deterministic | Extraction | S | — |
| 2 | B2 | Key-date/renewal calendar extraction | Proposed | Deterministic | Extraction | S | — |
| 3 | B3 | Renewal year-over-year diff | Proposed | Deterministic | Extraction | M | — |
| 4 | B4 | Multi-layer program extraction & aggregation | Proposed | Deterministic | Extraction | L | — |
| 5 | B5 | Reinstatement cost modeling | Proposed | Deterministic | Extraction | M | B4 |
| 6 | B6 | Semantic compliance/clause matching | Proposed | LLM | Both | M | — |
| 7 | B7 | Plain-English treaty summary | Proposed | LLM | Both | S/M | — |
| 8 | B8 | Clause ambiguity/contradiction detection | Proposed | LLM | Both | M | — |
| 9 | B9 | Peer/portfolio benchmarking | Proposed | Deterministic | Extraction | L | — |

### Business Domain — Claims

| Pri | ID | Task | Status | Shape | Answer Type | Effort | Depends on |
|---|---|---|---|---|---|---|---|
| 1 | C1 | Large-loss/catastrophe claim flagging | Proposed | Deterministic | Extraction | S | — |
| 2 | C2 | Claim notification compliance check | Proposed | Deterministic | Extraction | S/M | B2 |
| 3 | C3 | Claims bordereau reconciliation | Proposed | Deterministic | Extraction | M | — |
| 4 | C4 | Claim exclusion applicability check | Proposed | LLM | Both | M/L | — |
| 5 | C5 | Reserve development tracking | Proposed | Deterministic | Extraction | L | — |

### Business Domain — Facultative

| Pri | ID | Task | Status | Shape | Answer Type | Effort | Depends on |
|---|---|---|---|---|---|---|---|
| 1 | F1 | Facultative submission extraction | Proposed | Hybrid | Extraction | M | — |
| 2 | F2 | Facultative vs. treaty overlap check | Proposed | Deterministic | Extraction | M | F1 |
| 3 | F3 | Cat/peril exposure geocoding | Proposed | Hybrid | Extraction | M | — |
| 4 | F4 | Risk accumulation/PML aggregation check | Proposed | Deterministic | Extraction | L | — |

### Multi Domain-Task Selection

| Pri | ID | Task | Status | Shape | Answer Type | Effort | Depends on |
|---|---|---|---|---|---|---|---|
| 1 | S1 | Domain task registry & metadata | ✅ Done | Deterministic | N/A | S | — |
| 2 | S2 | Workflow refactor: split shared pipeline from per-task analysis nodes | 📋 In TASKS.md | Deterministic | N/A | L | S1 |
| 3 | S3 | Multi-task result aggregation & state schema | 📋 In TASKS.md | Deterministic | N/A | M | S2 |
| 4 | S4 | Per-task cost estimation (pre-run) & actual cost tracking (post-run) | 📋 In TASKS.md | Hybrid | N/A | M | S1 |
| 5 | S5 | Multi-task messaging & logging | 📋 In TASKS.md | Deterministic | N/A | S/M | S2, S3 |
| 6 | S6 | Task selection UI (checkboxes, disabled/blurred not-implemented tasks, live cost readout) | 📋 In TASKS.md | Deterministic | N/A | M | S1, S4 |
| 7 | S7 | Multi-task results UI (per-task sections + combined summary) | 📋 In TASKS.md | Deterministic | N/A | M | S3, S5 |
| 8 | S8 | End-to-end test coverage for multi-task selection | 📋 In TASKS.md | Deterministic | N/A | M | S2-S7 |

---

## A. Technical / AI Engineering & Production Harness

### A1. Retry/backoff resilience for the LLM call — Priority 1 — ✅ Done (shipped as `llm-fallback-retry-backoff`)
Today's `llm_extraction_fallback` catches all exceptions broadly and
degrades gracefully (a good baseline) but never retries a transient
failure (timeout, 5xx, rate limit) — add bounded retry-with-backoff
before falling through to the graceful-degradation path.
*Effort: S. Answer type: N/A (infrastructure, not a content-answering task).*

### A2. Grounding/assurance check on LLM output — Priority 2 — ✅ Done (shipped as `llm-fallback-grounding-check`)
Before trusting an LLM-extracted value, verify it's actually
supported by the cited page's text (e.g. does the cited page contain
this dollar figure or a numerically-equivalent phrase?). Flag
low-confidence/ungrounded extractions instead of silently trusting the
tool-use output as-is.
*Hybrid: deterministic verification pass over LLM output. Effort: M.
Answer type: Both — extracts the cited source text, then interprets
whether it's numerically/semantically equivalent to the claimed value.*

### A3. Extraction accuracy eval suite (golden dataset) — Priority 3 — ✅ Done (shipped as `extraction-accuracy-eval-suite`)
Build a labeled set of treaty documents (regex-friendly and
prose/fuzzy variants, across more realistic real-world phrasings than
today's two fixtures) with known-correct `TreatyTerms`, plus an
automated scorer for the LLM Extraction Fallback's field-level
accuracy (precision/recall per field, not just pass/fail). Catches
prompt or model-version regressions before they reach production.
*Deterministic scoring harness + LLM-under-test. Effort: M.
Answer type: N/A (a harness that scores other tasks' extraction
quality, not itself an extraction task).*

### A4. CI-integrated regression eval gate — Priority 4 — 📋 In TASKS.md as `extraction-eval-ci-gate`
Run A3's eval suite automatically (CI or scheduled) so a prompt/model
change can't silently regress extraction quality without anyone
noticing. Needs A3 first.
*Effort: S once A3 exists. Answer type: N/A (infrastructure).*

### A5. Structured observability upgrade — Priority 5
Move beyond UI-only log capture + optional file save toward
structured (JSON) logs with a correlation ID per run, suitable for
piping to an external log aggregator in a real production deployment.
*Effort: M. Answer type: N/A (infrastructure).*

### A6. Cost & latency observability + guardrails — Priority 6
Surface cumulative LLM spend/latency (today's per-run duration/token
logging is a good start, but nothing aggregates across runs); add a
per-session or per-deployment cost ceiling or alert; consider caching
identical re-uploads to avoid redundant LLM calls.
*Effort: M. Answer type: N/A (infrastructure).*

### A7. Adversarial input hardening — Priority 7
Stress-test the LLM extraction node against garbled/OCR-noise text,
non-English documents, empty pages, and documents near the context
limit; define and test explicit graceful-degradation behavior for
each, rather than discovering the failure mode in production.
*Effort: M. Answer type: N/A (tests other tasks' extraction robustness,
not itself an extraction task — see "Document-quality sensitivity"
below, which this item exists to defend against).*

### A8. Data-handling/PII review for third-party LLM calls — Priority 8
Document what data leaves the system on every LLM Extraction Fallback
call (full page text goes to Anthropic's API today); assess whether
redaction of cedent-identifying info is warranted before sending, for
a real compliance-sensitive deployment.
*Effort: S (review/document) to M (if redaction is actually implemented).
Answer type: N/A (infrastructure/compliance).*

### A9. Fallback tiering / cost-aware escalation — Priority 9
Before invoking a full LLM re-extraction, consider a cheaper
targeted completion when regex found *most* fields and only one or
two are missing, rather than always re-extracting everything.
*Effort: M — real design work on prompt/schema for the partial case.
Answer type: N/A (infrastructure/cost-control).*

### A10. Human-in-the-loop review workflow — Priority 10
A lightweight mechanism for a human to flag "this extraction was
wrong" on a real run, capturing the case (input + LLM output +
correction) to grow the eval dataset in A3 over time.
*Effort: M (needs a small persistence layer, not just in-memory state).
Answer type: N/A (infrastructure).*

### A11. Treaty sample selection UI (prepared/golden samples, no local disk) — Priority 11 — ✅ Done (shipped as `treaty-sample-selection-ui`)
Today `src/app.py`'s `main()` only accepts a treaty via
`st.file_uploader`, so trying any prepared sample (including the 5
golden cases in `tests/eval/golden_dataset.py`: `acme_minimal`,
`meridian_rich`, `sentinel_fuzzy`, `harborlight_prose`,
`continental_prose`) means manually finding the matching file under
`data/*.pdf` on the local machine and re-uploading it — not viable for
a reviewer/demo user without repo access. Add a second entry point
alongside the uploader: a "Choose a reinsurance treaty" selector (e.g.
`st.selectbox` or a small button grid) listing every prepared sample
by name/label, packaged with the PDF bytes shipped in the repo itself
(bundled as package data / read from `data/` at app start — never a
path typed or picked from the *user's* local disk), so it behaves
identically whether the app runs locally or deployed (Railway).
Picking a sample surfaces the same explicit "Analyze" action the
uploader path uses today (no auto-run on selection), then feeds into
the existing workflow exactly like an uploaded file — same downstream
code path, so this is UI-only plus a small sample registry, not a
workflow change. Also adds a "Review treaty" action that opens the
currently selected document (sample or uploaded) in a modal window
(`st.dialog`) showing its content, so the user can confirm they picked
the right document before running "Analyze" — applies to both the
sample-selector and uploader paths. "Analyze" itself is gated: rendered
blurred/disabled until a treaty is selected (sample or upload), and
disabled again if the selection is cleared.
*Deterministic (UI + static sample registry, no new analysis logic).
Effort: S/M. Answer type: N/A (infrastructure/UX, not itself a
content-answering task) — this is app-generic UX unrelated to which
domain task runs, distinct from the Multi Domain-Task Selection (`S`)
work tracked separately in `DOMAIN_TASK_SELECTION_PLAN.md`.*

---

## B. Business Domain

### Treaty (extends what the app already does)

- **B0. Burn-Cost Check** — Status: ✅ Done (implemented) —
  what the app already does today, end to end: extract a treaty's terms
  (attachment point, limit, premium, exclusions — via the regex
  Extractor, falling back to the LLM Extraction Fallback when the
  regex step can't find every required field), look up the cedent's
  historical claims (`query_historical_claims`), compute the burn-cost
  loss ratio for the layer (`calculate_loss_ratio`: ceded losses within
  the layer, summed and divided by the limit), and flag anomalies by
  severity (LOW when there's no claims history, MEDIUM at a 0.5+ loss
  ratio, HIGH above 1.0). Every item below in this Treaty section is a
  proposed extension of, or addition alongside, this shipped baseline.
  - *Shape: Hybrid (regex-first, LLM fallback). Effort: shipped —
    see `src/workflow.py`, `src/tools.py`, `src/app.py`. Answer type:
    Extraction (the loss-ratio math and severity thresholds are
    deterministic once the terms/claims are extracted — no judgment
    involved).*

- **B1. Mandatory-clause / exclusion completeness checklist** — Priority 1 —
  compare extracted `exclusions` against a configurable list of
  expected clauses (war, nuclear, cyber, pandemic, sanctions, TRIA);
  flag missing ones as a new finding category.
  *Deterministic. Effort: S. Answer type: Extraction (a set comparison
  over already-extracted clause names, no semantic judgment).*
- **B2. Key-date/renewal calendar extraction** — Priority 2 — extract
  inception/expiry/notice-period dates and flag treaties approaching
  renewal.
  *Deterministic. Effort: S. Answer type: Extraction.*
- **B3. Renewal year-over-year diff** — Priority 3 — accept two treaty
  PDFs (this year vs. last), extract both, diff `TreatyTerms`
  field-by-field, report what changed (rate, attachment, limit,
  new/removed exclusions).
  *Deterministic. Effort: M. Answer type: Extraction.*
- **B4. Multi-layer program extraction & aggregation** — Priority 4 —
  today only Layer 1 of a multi-layer treaty is extracted; lift that
  simplification, extract all layers, compute burn cost per layer and
  for the combined program. Real schema change
  (`TreatyTerms` → layers), touches parser/workflow/analyst/UI/all
  existing fixtures.
  *Deterministic. Effort: L — likely its own task chain, like the
  hybrid-extraction work was. Answer type: Extraction — though note
  segmenting which prose belongs to which layer is itself a
  document-quality-sensitive sub-problem (see "Document-quality
  sensitivity" below); may need LLM-assisted layer boundary detection
  even though per-layer figures stay a regex/arithmetic problem.*
- **B5. Reinstatement cost modeling** — Priority 5 — extract
  reinstatement terms and compute the added premium cost if a layer is
  fully exhausted.
  *Deterministic, depends on B4. Effort: M. Answer type: Extraction.*
- **B6. Semantic compliance/clause matching** — Priority 6 — LLM
  version of B1, matching clause *intent* rather than keywords, so it
  survives wording variation.
  *LLM. Effort: M. Answer type: Both — extracts candidate clause text,
  then interprets whether its intent matches the expected clause
  despite different wording.*
- **B7. Plain-English treaty summary** — Priority 7 — one LLM call
  producing a short executive summary (parties, layer, key dates,
  notable clauses). Should be opt-in (a button), not automatic, to
  preserve today's "LLM cost only when needed" default.
  *LLM. Effort: S/M. Answer type: Both — selects/extracts the salient
  facts, then composes an interpretive narrative from them.*
- **B8. Clause ambiguity/contradiction detection** — Priority 8 — LLM
  reviews the whole document for internally inconsistent terms (e.g.
  attachment point defined differently in two places). Judgment-based
  output — harder to test than field extraction (needs
  example-based/golden tests, not just exact-match).
  *LLM. Effort: M. Answer type: Both — extracts candidate statements
  about the same concept from multiple locations, then judges whether
  they're consistent.*
- **B9. Peer/portfolio benchmarking** — Priority 9 — is this treaty's
  pricing an outlier vs. similar treaties already on file. Needs a
  portfolio data model (multiple treaties), not just single-document
  analysis — a bigger data-model addition than the others in this
  section.
  *Deterministic (once a portfolio store exists). Effort: L. Answer
  type: Extraction — "outlier" is a statistical threshold rule (e.g.
  z-score) over extracted figures, not a semantic judgment.*

### Claims (new line — claims handling/adjustment, distinct from underwriting)

- **C1. Large-loss/catastrophe claim flagging** — Priority 1 — flag
  individual claims above a threshold for special handling/reporting
  to reinsurers ("cat claim protocols" in real practice).
  *Deterministic. Effort: S. Answer type: Extraction.*
- **C2. Claim notification compliance check** — Priority 2 —
  treaties often specify notice periods (e.g. "notify within 30
  days"); deterministic check of claim-reported-date vs. loss-date vs.
  the treaty's notice clause, flagging late notifications.
  *Deterministic, depends on B2 (date extraction). Effort: S/M. Answer
  type: Extraction.*
- **C3. Claims bordereau reconciliation** — Priority 3 — match a
  claims bordereau (list of individual claims reported by the cedent)
  against the treaty's terms: is each claim within scope, correctly
  allocated to the right layer. Generalizes what
  `query_historical_claims`/`calculate_loss_ratio` already do
  (aggregate burn cost) into per-claim validation of *reported*
  claims.
  *Deterministic. Effort: M. Answer type: Extraction.*
- **C4. Claim exclusion applicability check** — Priority 4 — given a
  claim's cause-of-loss narrative and the treaty's exclusion clauses
  (in prose), assess whether the claim is likely excluded. Genuinely
  hard, high business-value, LLM-suited (semantic matching between a
  claim narrative and exclusion wording) — real claims disputes turn
  on exactly this question.
  *LLM. Effort: M/L — needs careful prompt design and probably
  human-review framing (this is advisory, not a final determination).
  Answer type: Both — extracts the claim narrative and exclusion
  wording, then interprets whether the former falls under the latter.*
- **C5. Reserve development tracking** — Priority 5 — track how a
  claim's reserve estimate changes over time, feeding back into future
  loss-ratio predictions. Bigger actuarial/data feature, needs
  time-series claims data the app doesn't currently model.
  *Deterministic (once the data model exists). Effort: L. Answer type:
  Extraction.*

### Facultative (new line — per-risk, individually underwritten, not yet covered)

Facultative reinsurance covers a *single* underlying risk/policy
(submitted individually for underwriting), unlike Treaty's whole-book
coverage — a genuinely different document shape and workflow.

- **F1. Facultative submission extraction** — Priority 1 — parse a
  facultative slip/submission (risk description, insured values,
  location/occupancy, requested share/line, proposed rate) into a
  structured schema, analogous to today's `TreatyTerms` but per-risk.
  *Hybrid (regex+LLM, same pattern as Treaty). Effort: M — new schema,
  reuses the extraction pipeline pattern. Answer type: Extraction —
  facultative slips are generally *less* standardized across brokers
  than Treaty wordings, so expect this to lean on the LLM side of the
  hybrid more often than `B0` does (see "Document-quality sensitivity"
  below).*
- **F2. Facultative vs. treaty overlap check** — Priority 2 — does
  this individual risk already fall within an existing treaty's
  automatic coverage (making facultative placement redundant), or does
  it exceed treaty capacity (requiring facultative cover)? Genuinely
  valuable cross-check spanning both lines.
  *Deterministic, depends on F1 + existing Treaty extraction.
  Effort: M. Answer type: Extraction.*
- **F3. Cat/peril exposure geocoding** — Priority 3 — extract risk
  location and cross-reference against known catastrophe zones
  (flood/wildfire/earthquake) for a quick red-flag on facultative risk
  quality.
  *Hybrid (extraction + external geo/peril data lookup). Effort: M —
  needs an external data source, not just document analysis. Answer
  type: Extraction — though a location given as unstructured prose
  ("a warehouse near the river on the east side of town") rather than
  a structured address pushes the extraction step itself toward LLM
  normalization before geocoding can run.*
- **F4. Risk accumulation/PML aggregation check** — Priority 4 — flag
  if accepting this facultative risk would push aggregate exposure in
  a zone/peril above internal limits. Needs an aggregation store
  across previously-accepted risks.
  *Deterministic. Effort: L — needs persistent aggregation state, not
  just single-document analysis. Answer type: Extraction.*

---

## S. Multi Domain-Task Selection

Today the app runs exactly one hard-coded analysis per uploaded
treaty: `Extractor → [LLM Extraction Fallback] → Verifier → Analyst`,
where `analyst_node` in `src/workflow.py` *is* the Burn-Cost Check
(`B0`) — it's the only domain task that exists, and it always runs.
`B1`-`B9` above list eight more candidate domain tasks, none
implemented yet. As more of these get built, the app needs a way for
the user to **choose which domain task(s) to run** against a given
treaty, see what each one will cost before/after running it, and see
results per task plus a combined total — rather than every future
task becoming another thing that always runs on every upload (which
would make cost/latency balloon uncontrollably as `B1`-`B9` get
implemented). This section is cross-cutting harness/UI work in
service of that, not a business-domain content task itself, so it's
its own category rather than nested under `A` or `B` — see
`REASONING.md`'s 2026-09-09 entries for the fuller design writeup
(current architecture facts gathered, and the two confirmed design
decisions: a per-task cost *estimate* shown before running, replaced
by the *actual* measured cost after; and `S1`'s registry as the single
source of truth both the backend graph builder and the frontend
selector read from).

- **S1. Domain task registry & metadata** — Priority 1 — ✅ Done (shipped as `domain-task-registry`) — a small
  catalog (e.g. `src/domain_tasks.py`) listing every candidate domain
  task: id, title, its `CANDIDATE_TASKS.md` ID (`B0`, `B1`, ...),
  implementation status (`implemented` / `not_implemented`), shape,
  and which workflow node(s) it needs. This is the single source of
  truth both the backend graph builder (`S2`) and the frontend
  selector (`S6`) read from, so the two can't drift.
  *Deterministic. Effort: S. Answer type: N/A (infrastructure).*
- **S2. Workflow refactor: split shared pipeline from per-task
  analysis nodes** — Priority 2 — 📋 In TASKS.md as
  `workflow-refactor-multi-task-pipeline` — today's
  `Extractor → [LLM Fallback]
  → Verifier` stays a shared pipeline every domain task needs
  (produces `TreatyTerms` + `claims`); `analyst_node` gets renamed/
  scoped to a `burn_cost_check_node` (`B0`'s logic, unchanged), and
  `build_workflow_graph()` becomes parameterized by a set of selected
  task IDs — it always runs the shared pipeline, then only the
  analysis node(s) for implemented+selected tasks.
  *Deterministic. Effort: L — likely its own multi-task chain once
  graduated (same pattern as `B4`). Answer type: N/A (infrastructure).*
- **S3. Multi-task result aggregation & state schema** — Priority 3 —
  📋 In TASKS.md as `multi-task-result-aggregation-schema` — replace `WorkflowState.report: AnomalyReport | None` with a
  `task_results: dict[str, TaskResult]` (one entry per selected task:
  status `ran`/`skipped_not_implemented`/`failed`, findings, cost,
  latency), so the UI can render N independent results instead of one.
  *Deterministic, depends on S2. Effort: M. Answer type: N/A
  (infrastructure).*
- **S4. Per-task cost estimation (pre-run) & actual cost tracking
  (post-run)** — Priority 4 — 📋 In TASKS.md as
  `per-task-cost-estimation` — the first real $-cost logic in this
  app. Pre-run: a rough per-task estimate from document page/token
  count × task shape (near-zero for deterministic tasks, a
  model-price-based estimate for LLM/hybrid tasks) plus a live
  cumulative total as checkboxes toggle. Post-run: convert
  `llm_extraction_fallback`'s already-logged `input_tokens`/
  `output_tokens` (and any future task's own LLM calls) into an actual
  $ figure via the model's published per-token price, replacing the
  estimate once a task completes. Narrower/scoped version of `A6`
  ("Cost & latency observability"), specific to per-task estimate/
  actual display rather than the broader always-on observability `A6`
  covers.
  *Hybrid: deterministic estimate math + real LLM usage for the
  actual. Effort: M, depends on S1. Answer type: N/A
  (infrastructure/cost-control).*
- **S5. Multi-task messaging & logging** — Priority 5 — 📋 In TASKS.md
  as `multi-task-messaging-logging` — every node's
  log line gains a task-id tag; a combined-run summary message (which
  tasks ran, which were skipped as not-implemented, which failed)
  drives both the UI banner and the saved log file, replacing today's
  single-task-only `format_extraction_status`.
  *Deterministic, depends on S2, S3. Effort: S/M. Answer type: N/A
  (infrastructure).*
- **S6. Task selection UI** — Priority 6 — 📋 In TASKS.md as
  `multi-task-selection-ui` — a checkbox/multiselect
  control listing every task from `S1`'s registry; only tasks marked
  `implemented` (today: just `B0`) are enabled, every other task
  rendered visually disabled/blurred with a "Not implemented" badge;
  selecting an enabled task shows its live cost estimate from `S4`,
  plus a running cumulative total across all checked tasks.
  *Deterministic, depends on S1, S4. Effort: M. Answer type: N/A
  (infrastructure/UX).*
- **S7. Multi-task results UI** — Priority 7 — 📋 In TASKS.md as
  `multi-task-results-ui` — one expandable section
  per selected+implemented task (its own findings/log/actual cost),
  plus a combined header (total findings across tasks, total actual
  cost, which tasks were skipped and why), replacing today's single
  `format_report_markdown` call.
  *Deterministic, depends on S3, S5. Effort: M. Answer type: N/A
  (infrastructure/UX).*
- **S8. End-to-end test coverage** — Priority 8 — 📋 In TASKS.md as
  `multi-task-e2e-test-coverage` — verifies: selecting
  only `B0` behaves exactly like today (regression safety net),
  selecting a mix of implemented + not-implemented tasks skips the
  latter gracefully with a clear per-task message, cost estimates/
  actuals round-trip correctly, and the new `task_results` schema
  serializes correctly for the debug panel.
  *Deterministic, depends on S2-S7. Effort: M. Answer type: N/A
  (infrastructure).*

---

## Document-quality sensitivity

Per the 2026-09-06 discussion: a task's Shape (Deterministic / Hybrid /
LLM) isn't a fixed property of the task — it depends on two largely
independent things, and conflating them is why "shape" can look
inconsistent across the list above.

1. **Does the task's Answer Type require interpretation?** Tasks
   marked **Interpretation** or **Both** above stay LLM-shaped no
   matter how clean the source document is, because the deliverable
   itself requires judgment (matching clause *intent*, detecting
   *contradiction*, deciding whether a narrative falls under an
   exclusion). Document quality changes their cost/confidence, never
   converts them into a pure regex problem.
2. **How clean is the document the facts must come from?** For tasks
   marked **Extraction**, shape is a direct function of how reliably
   the needed facts appear in predictable syntax:

   | Content quality | Extraction behavior | Shape it forces |
   |---|---|---|
   | Plain/fixed (`Label: value`, consistent template) | regex matches directly | Deterministic — cheap, fast, no LLM cost |
   | Structured but varies by cedent/broker | regex rules multiply per template, gets brittle | Deterministic-with-decay → push toward Hybrid before N regex dialects are worth maintaining |
   | Prose/fuzzy natural language | regex reports `missing_fields`, needs a semantic parse | Hybrid — exactly `B0`'s current regex-first/LLM-fallback pattern |
   | Messy/OCR noise, syntax errors, garbled text | breaks assumptions under *both* regex and LLM — corrupted key terms can make an LLM confidently extract a wrong number | Hybrid **plus** mandatory grounding/verification (`A2`); this is why `A7` (adversarial input hardening) is its own harness item rather than folded into extraction |
   | Genuinely unstructured/free-form (e.g. amendment letters, correspondence-style endorsements) | no reliable automatic path | Human-in-the-loop (`A10`) as the actual fallback, not more prompt engineering |

Practical implications already reflected in individual entries above:
`B1`/`B2`/`B3` are rated Deterministic assuming clean-enough source
text — if real submitted treaties skew toward messy prose, they
inherit `B0`'s Hybrid shape rather than staying pure-regex. `B4`'s
Effort:L partly comes from this axis (segmenting layers within messy
prose is itself a fuzzy-document problem). `F1` (Facultative
submission extraction) should be expected to lean on its LLM half more
than `B0` does, since facultative slips are typically less
standardized across brokers than treaty wordings. `A2` (grounding
check) and `A3`/`A4` (eval suite + CI gate, which should explicitly
include messy/fuzzy/garbled fixtures, not just clean ones) are the
harness items that most directly defend against this axis, which is
an argument for prioritizing them before extraction work expands to
new, less-standardized document sources (Facultative in particular).

---

## Notes for prioritization discussion

- Priority order above is a first pass, ranked by a rough
  value/effort/dependency read — cheap+standalone+high-value items
  first within each category, foundational items before what depends
  on them (A3 before A4; B4 before B5; F1 before F2; B2 before C2),
  and the biggest/most speculative items (needing new persistent data
  models: A10, B9, F4, C5) last in their sections.
- Items marked **Effort: L** are likely each their own multi-task
  chain (like `explore-hybrid-regex-llm-fallback` was split into four),
  not a single `TASKS.md` entry.
- B6/B7/B8/C4 (the LLM-suited domain features) would, if made
  automatic rather than opt-in, change the app's cost profile from
  "LLM cost only on fallback" to "LLM cost on every run" — worth a
  deliberate decision, not a default.
- B0 (Burn-Cost Check) is not a candidate — it's the shipped baseline
  every other Treaty item extends or sits alongside. It's listed with
  no Priority (not up for re-ranking) so the numbered priorities above
  stay comparable to how they read before B0 was added.
- A3/A4 (eval suite + CI gate) arguably deserve doing *before* any
  further LLM-suited feature work (B6–B8, C4), since they're the
  harness that would catch a bad prompt/model change in those features
  later — reflected in Harness's own priority order above (A3 ranked
  ahead of A4, both ranked ahead of the harness items that don't touch
  the eval loop directly).
