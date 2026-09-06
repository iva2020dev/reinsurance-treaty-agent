# Candidate Tasks (Draft — Not Yet in TASKS.md)

This is a **staging list**, not the backlog. Nothing here has been
scoped or approved — it exists so we can clarify and prioritize
together before anything graduates into `TASKS.md` with a real
ID/Details/Files/Acceptance per the usual convention (see
`AGENTS.md`).

Two categories, per discussion on 2026-09-06:

- **A. Technical / AI Engineering & Production Harness** — validating
  model behavior, evaluation frameworks, agent-behavior quality
  checks/grounding, and reliability/scalability/cost/latency.
- **B. Business Domain** — grounded in everyday Treaty, Facultative,
  and Claims reinsurance practice, extending what the app already does
  for Treaty underwriting review.

Each item: a short description, a rough shape (deterministic / LLM /
hybrid, and rough dev-effort S/M/L), and why it matters. Items within
each section/subsection are listed in **suggested priority order**
(highest first) — a first-pass ranking by value, effort, and
dependency, not a final decision. See the 2026-09-06 session's
discussion in `REASONING.md` for the fuller cost/effort comparison
this list was drafted from.

---

## Summary

### Technical / AI Engineering & Production Harness

| Pri | ID | Task | Shape | Effort | Depends on |
|---|---|---|---|---|---|
| 1 | A7 | Retry/backoff resilience for the LLM call | Deterministic | S | — |
| 2 | A3 | Grounding/assurance check on LLM output | Hybrid | M | — |
| 3 | A1 | Extraction accuracy eval suite (golden dataset) | Hybrid | M | — |
| 4 | A2 | CI-integrated regression eval gate | Deterministic | S | A1 |
| 5 | A9 | Structured observability upgrade | Deterministic | M | — |
| 6 | A6 | Cost & latency observability + guardrails | Deterministic | M | — |
| 7 | A4 | Adversarial input hardening | Hybrid | M | — |
| 8 | A10 | Data-handling/PII review for third-party LLM calls | Deterministic | S/M | — |
| 9 | A8 | Fallback tiering / cost-aware escalation | Hybrid | M | — |
| 10 | A5 | Human-in-the-loop review workflow | Deterministic | M | — |

### Business Domain — Treaty

| Pri | ID | Task | Shape | Effort | Depends on |
|---|---|---|---|---|---|
| 1 | B1 | Mandatory-clause / exclusion completeness checklist | Deterministic | S | — |
| 2 | B5 | Key-date/renewal calendar extraction | Deterministic | S | — |
| 3 | B2 | Renewal year-over-year diff | Deterministic | M | — |
| 4 | B3 | Multi-layer program extraction & aggregation | Deterministic | L | — |
| 5 | B4 | Reinstatement cost modeling | Deterministic | M | B3 |
| 6 | B8 | Semantic compliance/clause matching | LLM | M | — |
| 7 | B6 | Plain-English treaty summary | LLM | S/M | — |
| 8 | B7 | Clause ambiguity/contradiction detection | LLM | M | — |
| 9 | B9 | Peer/portfolio benchmarking | Deterministic | L | — |

### Business Domain — Facultative

| Pri | ID | Task | Shape | Effort | Depends on |
|---|---|---|---|---|---|
| 1 | B10 | Facultative submission extraction | Hybrid | M | — |
| 2 | B11 | Facultative vs. treaty overlap check | Deterministic | M | B10 |
| 3 | B13 | Cat/peril exposure geocoding | Hybrid | M | — |
| 4 | B12 | Risk accumulation/PML aggregation check | Deterministic | L | — |

### Business Domain — Claims

| Pri | ID | Task | Shape | Effort | Depends on |
|---|---|---|---|---|---|
| 1 | B16 | Large-loss/catastrophe claim flagging | Deterministic | S | — |
| 2 | B15 | Claim notification compliance check | Deterministic | S/M | B5 |
| 3 | B14 | Claims bordereau reconciliation | Deterministic | M | — |
| 4 | B17 | Claim exclusion applicability check | LLM | M/L | — |
| 5 | B18 | Reserve development tracking | Deterministic | L | — |

---

## A. Technical / AI Engineering & Production Harness

### A7. Retry/backoff resilience for the LLM call — Priority 1
Today's `llm_extraction_fallback` catches all exceptions broadly and
degrades gracefully (a good baseline) but never retries a transient
failure (timeout, 5xx, rate limit) — add bounded retry-with-backoff
before falling through to the graceful-degradation path.
*Effort: S.*

### A3. Grounding/assurance check on LLM output — Priority 2
Before trusting an LLM-extracted value, verify it's actually
supported by the cited page's text (e.g. does the cited page contain
this dollar figure or a numerically-equivalent phrase?). Flag
low-confidence/ungrounded extractions instead of silently trusting the
tool-use output as-is.
*Hybrid: deterministic verification pass over LLM output. Effort: M.*

### A1. Extraction accuracy eval suite (golden dataset) — Priority 3
Build a labeled set of treaty documents (regex-friendly and
prose/fuzzy variants, across more realistic real-world phrasings than
today's two fixtures) with known-correct `TreatyTerms`, plus an
automated scorer for the LLM Extraction Fallback's field-level
accuracy (precision/recall per field, not just pass/fail). Catches
prompt or model-version regressions before they reach production.
*Deterministic scoring harness + LLM-under-test. Effort: M.*

### A2. CI-integrated regression eval gate — Priority 4
Run A1's eval suite automatically (CI or scheduled) so a prompt/model
change can't silently regress extraction quality without anyone
noticing. Needs A1 first.
*Effort: S once A1 exists.*

### A9. Structured observability upgrade — Priority 5
Move beyond UI-only log capture + optional file save toward
structured (JSON) logs with a correlation ID per run, suitable for
piping to an external log aggregator in a real production deployment.
*Effort: M.*

### A6. Cost & latency observability + guardrails — Priority 6
Surface cumulative LLM spend/latency (today's per-run duration/token
logging is a good start, but nothing aggregates across runs); add a
per-session or per-deployment cost ceiling or alert; consider caching
identical re-uploads to avoid redundant LLM calls.
*Effort: M.*

### A4. Adversarial input hardening — Priority 7
Stress-test the LLM extraction node against garbled/OCR-noise text,
non-English documents, empty pages, and documents near the context
limit; define and test explicit graceful-degradation behavior for
each, rather than discovering the failure mode in production.
*Effort: M.*

### A10. Data-handling/PII review for third-party LLM calls — Priority 8
Document what data leaves the system on every LLM Extraction Fallback
call (full page text goes to Anthropic's API today); assess whether
redaction of cedent-identifying info is warranted before sending, for
a real compliance-sensitive deployment.
*Effort: S (review/document) to M (if redaction is actually implemented).*

### A8. Fallback tiering / cost-aware escalation — Priority 9
Before invoking a full LLM re-extraction, consider a cheaper
targeted completion when regex found *most* fields and only one or
two are missing, rather than always re-extracting everything.
*Effort: M — real design work on prompt/schema for the partial case.*

### A5. Human-in-the-loop review workflow — Priority 10
A lightweight mechanism for a human to flag "this extraction was
wrong" on a real run, capturing the case (input + LLM output +
correction) to grow the eval dataset in A1 over time.
*Effort: M (needs a small persistence layer, not just in-memory state).*

---

## B. Business Domain

### Treaty (extends what the app already does)

- **B1. Mandatory-clause / exclusion completeness checklist** — Priority 1 —
  compare extracted `exclusions` against a configurable list of
  expected clauses (war, nuclear, cyber, pandemic, sanctions, TRIA);
  flag missing ones as a new finding category.
  *Deterministic. Effort: S.*
- **B5. Key-date/renewal calendar extraction** — Priority 2 — extract
  inception/expiry/notice-period dates and flag treaties approaching
  renewal.
  *Deterministic. Effort: S.*
- **B2. Renewal year-over-year diff** — Priority 3 — accept two treaty
  PDFs (this year vs. last), extract both, diff `TreatyTerms`
  field-by-field, report what changed (rate, attachment, limit,
  new/removed exclusions).
  *Deterministic. Effort: M.*
- **B3. Multi-layer program extraction & aggregation** — Priority 4 —
  today only Layer 1 of a multi-layer treaty is extracted; lift that
  simplification, extract all layers, compute burn cost per layer and
  for the combined program. Real schema change
  (`TreatyTerms` → layers), touches parser/workflow/analyst/UI/all
  existing fixtures.
  *Deterministic. Effort: L — likely its own task chain, like the
  hybrid-extraction work was.*
- **B4. Reinstatement cost modeling** — Priority 5 — extract
  reinstatement terms and compute the added premium cost if a layer is
  fully exhausted.
  *Deterministic, depends on B3. Effort: M.*
- **B8. Semantic compliance/clause matching** — Priority 6 — LLM
  version of B1, matching clause *intent* rather than keywords, so it
  survives wording variation.
  *LLM. Effort: M.*
- **B6. Plain-English treaty summary** — Priority 7 — one LLM call
  producing a short executive summary (parties, layer, key dates,
  notable clauses). Should be opt-in (a button), not automatic, to
  preserve today's "LLM cost only when needed" default.
  *LLM. Effort: S/M.*
- **B7. Clause ambiguity/contradiction detection** — Priority 8 — LLM
  reviews the whole document for internally inconsistent terms (e.g.
  attachment point defined differently in two places). Judgment-based
  output — harder to test than field extraction (needs
  example-based/golden tests, not just exact-match).
  *LLM. Effort: M.*
- **B9. Peer/portfolio benchmarking** — Priority 9 — is this treaty's
  pricing an outlier vs. similar treaties already on file. Needs a
  portfolio data model (multiple treaties), not just single-document
  analysis — a bigger data-model addition than the others in this
  section.
  *Deterministic (once a portfolio store exists). Effort: L.*

### Facultative (new line — per-risk, individually underwritten, not yet covered)

Facultative reinsurance covers a *single* underlying risk/policy
(submitted individually for underwriting), unlike Treaty's whole-book
coverage — a genuinely different document shape and workflow.

- **B10. Facultative submission extraction** — Priority 1 — parse a
  facultative slip/submission (risk description, insured values,
  location/occupancy, requested share/line, proposed rate) into a
  structured schema, analogous to today's `TreatyTerms` but per-risk.
  *Hybrid (regex+LLM, same pattern as Treaty). Effort: M — new schema,
  reuses the extraction pipeline pattern.*
- **B11. Facultative vs. treaty overlap check** — Priority 2 — does
  this individual risk already fall within an existing treaty's
  automatic coverage (making facultative placement redundant), or does
  it exceed treaty capacity (requiring facultative cover)? Genuinely
  valuable cross-check spanning both lines.
  *Deterministic, depends on B10 + existing Treaty extraction.
  Effort: M.*
- **B13. Cat/peril exposure geocoding** — Priority 3 — extract risk
  location and cross-reference against known catastrophe zones
  (flood/wildfire/earthquake) for a quick red-flag on facultative risk
  quality.
  *Hybrid (extraction + external geo/peril data lookup). Effort: M —
  needs an external data source, not just document analysis.*
- **B12. Risk accumulation/PML aggregation check** — Priority 4 — flag
  if accepting this facultative risk would push aggregate exposure in
  a zone/peril above internal limits. Needs an aggregation store
  across previously-accepted risks.
  *Deterministic. Effort: L — needs persistent aggregation state, not
  just single-document analysis.*

### Claims (new line — claims handling/adjustment, distinct from underwriting)

- **B16. Large-loss/catastrophe claim flagging** — Priority 1 — flag
  individual claims above a threshold for special handling/reporting
  to reinsurers ("cat claim protocols" in real practice).
  *Deterministic. Effort: S.*
- **B15. Claim notification compliance check** — Priority 2 —
  treaties often specify notice periods (e.g. "notify within 30
  days"); deterministic check of claim-reported-date vs. loss-date vs.
  the treaty's notice clause, flagging late notifications.
  *Deterministic, depends on B5 (date extraction). Effort: S/M.*
- **B14. Claims bordereau reconciliation** — Priority 3 — match a
  claims bordereau (list of individual claims reported by the cedent)
  against the treaty's terms: is each claim within scope, correctly
  allocated to the right layer. Generalizes what
  `query_historical_claims`/`calculate_loss_ratio` already do
  (aggregate burn cost) into per-claim validation of *reported*
  claims.
  *Deterministic. Effort: M.*
- **B17. Claim exclusion applicability check** — Priority 4 — given a
  claim's cause-of-loss narrative and the treaty's exclusion clauses
  (in prose), assess whether the claim is likely excluded. Genuinely
  hard, high business-value, LLM-suited (semantic matching between a
  claim narrative and exclusion wording) — real claims disputes turn
  on exactly this question.
  *LLM. Effort: M/L — needs careful prompt design and probably
  human-review framing (this is advisory, not a final determination).*
- **B18. Reserve development tracking** — Priority 5 — track how a
  claim's reserve estimate changes over time, feeding back into future
  loss-ratio predictions. Bigger actuarial/data feature, needs
  time-series claims data the app doesn't currently model.
  *Deterministic (once the data model exists). Effort: L.*

---

## Notes for prioritization discussion

- Priority order above is a first pass, ranked by a rough
  value/effort/dependency read — cheap+standalone+high-value items
  first within each category, foundational items before what depends
  on them (A1 before A2; B3 before B4; B10 before B11; B5 before B15),
  and the biggest/most speculative items (needing new persistent data
  models: A5, B9, B12, B18) last in their sections.
- Items marked **Effort: L** are likely each their own multi-task
  chain (like `explore-hybrid-regex-llm-fallback` was split into four),
  not a single `TASKS.md` entry.
- B6/B7/B8/B17 (the LLM-suited domain features) would, if made
  automatic rather than opt-in, change the app's cost profile from
  "LLM cost only on fallback" to "LLM cost on every run" — worth a
  deliberate decision, not a default.
- A1/A2 (eval suite + CI gate) arguably deserve doing *before* any
  further LLM-suited feature work (B6–B8, B17), since they're the
  harness that would catch a bad prompt/model change in those features
  later — reflected in Harness's own priority order above (A1 ranked
  ahead of A2, both ranked ahead of the harness items that don't touch
  the eval loop directly).
