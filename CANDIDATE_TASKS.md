# Candidate Tasks (Draft — Not Yet in TASKS.md)

This is a **staging list**, not the backlog. Nothing here has been
scoped, prioritized, or approved — it exists so we can clarify and
prioritize together before anything graduates into `TASKS.md` with a
real ID/Details/Files/Acceptance per the usual convention (see
`AGENTS.md`).

Two categories, per discussion on 2026-09-06:

- **A. Technical / AI Engineering & Production Harness** — validating
  model behavior, evaluation frameworks, agent-behavior quality
  checks/grounding, and reliability/scalability/cost/latency.
- **B. Business Domain** — grounded in everyday Treaty, Facultative,
  and Claims reinsurance practice, extending what the app already does
  for Treaty underwriting review.

Each item: a short description, a rough shape (deterministic / LLM /
hybrid, and rough dev-effort S/M/L), and why it matters. See the
2026-09-06 session's discussion in `REASONING.md`-adjacent chat history
for the fuller cost/effort comparison this list was drafted from.

---

## A. Technical / AI Engineering & Production Harness

### A1. Extraction accuracy eval suite (golden dataset)
Build a labeled set of treaty documents (regex-friendly and
prose/fuzzy variants, across more realistic real-world phrasings than
today's two fixtures) with known-correct `TreatyTerms`, plus an
automated scorer for the LLM Extraction Fallback's field-level
accuracy (precision/recall per field, not just pass/fail). Catches
prompt or model-version regressions before they reach production.
*Deterministic scoring harness + LLM-under-test. Effort: M.*

### A2. CI-integrated regression eval gate
Run A1's eval suite automatically (CI or scheduled) so a prompt/model
change can't silently regress extraction quality without anyone
noticing. Needs A1 first.
*Effort: S once A1 exists.*

### A3. Grounding/assurance check on LLM output
Before trusting an LLM-extracted value, verify it's actually
supported by the cited page's text (e.g. does the cited page contain
this dollar figure or a numerically-equivalent phrase?). Flag
low-confidence/ungrounded extractions instead of silently trusting the
tool-use output as-is.
*Hybrid: deterministic verification pass over LLM output. Effort: M.*

### A4. Adversarial input hardening
Stress-test the LLM extraction node against garbled/OCR-noise text,
non-English documents, empty pages, and documents near the context
limit; define and test explicit graceful-degradation behavior for
each, rather than discovering the failure mode in production.
*Effort: M.*

### A5. Human-in-the-loop review workflow
A lightweight mechanism for a human to flag "this extraction was
wrong" on a real run, capturing the case (input + LLM output +
correction) to grow the eval dataset in A1 over time.
*Effort: M (needs a small persistence layer, not just in-memory state).*

### A6. Cost & latency observability + guardrails
Surface cumulative LLM spend/latency (today's per-run duration/token
logging is a good start, but nothing aggregates across runs); add a
per-session or per-deployment cost ceiling or alert; consider caching
identical re-uploads to avoid redundant LLM calls.
*Effort: M.*

### A7. Retry/backoff resilience for the LLM call
Today's `llm_extraction_fallback` catches all exceptions broadly and
degrades gracefully (a good baseline) but never retries a transient
failure (timeout, 5xx, rate limit) — add bounded retry-with-backoff
before falling through to the graceful-degradation path.
*Effort: S.*

### A8. Fallback tiering / cost-aware escalation
Before invoking a full LLM re-extraction, consider a cheaper
targeted completion when regex found *most* fields and only one or
two are missing, rather than always re-extracting everything.
*Effort: M — real design work on prompt/schema for the partial case.*

### A9. Structured observability upgrade
Move beyond UI-only log capture + optional file save toward
structured (JSON) logs with a correlation ID per run, suitable for
piping to an external log aggregator in a real production deployment.
*Effort: M.*

### A10. Data-handling/PII review for third-party LLM calls
Document what data leaves the system on every LLM Extraction Fallback
call (full page text goes to Anthropic's API today); assess whether
redaction of cedent-identifying info is warranted before sending, for
a real compliance-sensitive deployment.
*Effort: S (review/document) to M (if redaction is actually implemented).*

---

## B. Business Domain

### Treaty (extends what the app already does)

- **B1. Mandatory-clause / exclusion completeness checklist** —
  compare extracted `exclusions` against a configurable list of
  expected clauses (war, nuclear, cyber, pandemic, sanctions, TRIA);
  flag missing ones as a new finding category.
  *Deterministic. Effort: S.*
- **B2. Renewal year-over-year diff** — accept two treaty PDFs
  (this year vs. last), extract both, diff `TreatyTerms` field-by-
  field, report what changed (rate, attachment, limit, new/removed
  exclusions).
  *Deterministic. Effort: M.*
- **B3. Multi-layer program extraction & aggregation** — today only
  Layer 1 of a multi-layer treaty is extracted; lift that
  simplification, extract all layers, compute burn cost per layer and
  for the combined program. Real schema change
  (`TreatyTerms` → layers), touches parser/workflow/analyst/UI/all
  existing fixtures.
  *Deterministic. Effort: L — likely its own task chain, like the
  hybrid-extraction work was.*
- **B4. Reinstatement cost modeling** — extract reinstatement terms
  and compute the added premium cost if a layer is fully exhausted.
  *Deterministic, depends on B3. Effort: M.*
- **B5. Key-date/renewal calendar extraction** — extract
  inception/expiry/notice-period dates and flag treaties approaching
  renewal.
  *Deterministic. Effort: S.*
- **B6. Plain-English treaty summary** — one LLM call producing a
  short executive summary (parties, layer, key dates, notable
  clauses). Should be opt-in (a button), not automatic, to preserve
  today's "LLM cost only when needed" default.
  *LLM. Effort: S/M.*
- **B7. Clause ambiguity/contradiction detection** — LLM reviews the
  whole document for internally inconsistent terms (e.g. attachment
  point defined differently in two places). Judgment-based output —
  harder to test than field extraction (needs example-based/golden
  tests, not just exact-match).
  *LLM. Effort: M.*
- **B8. Semantic compliance/clause matching** — LLM version of B1,
  matching clause *intent* rather than keywords, so it survives
  wording variation.
  *LLM. Effort: M.*
- **B9. Peer/portfolio benchmarking** — is this treaty's pricing an
  outlier vs. similar treaties already on file. Needs a portfolio data
  model (multiple treaties), not just single-document analysis — a
  bigger data-model addition than the others in this section.
  *Deterministic (once a portfolio store exists). Effort: L.*

### Facultative (new line — per-risk, individually underwritten, not yet covered)

Facultative reinsurance covers a *single* underlying risk/policy
(submitted individually for underwriting), unlike Treaty's whole-book
coverage — a genuinely different document shape and workflow.

- **B10. Facultative submission extraction** — parse a facultative
  slip/submission (risk description, insured values, location/
  occupancy, requested share/line, proposed rate) into a structured
  schema, analogous to today's `TreatyTerms` but per-risk.
  *Hybrid (regex+LLM, same pattern as Treaty). Effort: M — new schema,
  reuses the extraction pipeline pattern.*
- **B11. Facultative vs. treaty overlap check** — does this
  individual risk already fall within an existing treaty's automatic
  coverage (making facultative placement redundant), or does it exceed
  treaty capacity (requiring facultative cover)? Genuinely valuable
  cross-check spanning both lines.
  *Deterministic, depends on B10 + existing Treaty extraction.
  Effort: M.*
- **B12. Risk accumulation/PML aggregation check** — flag if
  accepting this facultative risk would push aggregate exposure in a
  zone/peril above internal limits. Needs an aggregation store across
  previously-accepted risks.
  *Deterministic. Effort: L — needs persistent aggregation state, not
  just single-document analysis.*
- **B13. Cat/peril exposure geocoding** — extract risk location and
  cross-reference against known catastrophe zones (flood/wildfire/
  earthquake) for a quick red-flag on facultative risk quality.
  *Hybrid (extraction + external geo/peril data lookup). Effort: M —
  needs an external data source, not just document analysis.*

### Claims (new line — claims handling/adjustment, distinct from underwriting)

- **B14. Claims bordereau reconciliation** — match a claims bordereau
  (list of individual claims reported by the cedent) against the
  treaty's terms: is each claim within scope, correctly allocated to
  the right layer. Generalizes what `query_historical_claims`/
  `calculate_loss_ratio` already do (aggregate burn cost) into
  per-claim validation of *reported* claims.
  *Deterministic. Effort: M.*
- **B15. Claim notification compliance check** — treaties often
  specify notice periods (e.g. "notify within 30 days"); deterministic
  check of claim-reported-date vs. loss-date vs. the treaty's notice
  clause, flagging late notifications.
  *Deterministic, depends on B5 (date extraction). Effort: S/M.*
- **B16. Large-loss/catastrophe claim flagging** — flag individual
  claims above a threshold for special handling/reporting to
  reinsurers ("cat claim protocols" in real practice).
  *Deterministic. Effort: S.*
- **B17. Claim exclusion applicability check** — given a claim's
  cause-of-loss narrative and the treaty's exclusion clauses (in
  prose), assess whether the claim is likely excluded. Genuinely hard,
  high business-value, LLM-suited (semantic matching between a claim
  narrative and exclusion wording) — real claims disputes turn on
  exactly this question.
  *LLM. Effort: M/L — needs careful prompt design and probably
  human-review framing (this is advisory, not a final determination).*
- **B18. Reserve development tracking** — track how a claim's reserve
  estimate changes over time, feeding back into future loss-ratio
  predictions. Bigger actuarial/data feature, needs time-series
  claims data the app doesn't currently model.
  *Deterministic (once the data model exists). Effort: L.*

---

## Notes for prioritization discussion

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
  later.
