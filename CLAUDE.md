# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository RTA.

## Project Overview

## Architecture

## Key Architectural Patterns

### LLM-Calling Harness Pattern

Any code that calls the Anthropic API — client construction, timeouts,
retry/backoff — **MUST** go through `src/llm_client.py`
(`get_client(timeout=...)`, `call_with_retry(fn, ...)`) rather than
constructing `anthropic.Anthropic(...)` directly or re-implementing
retry logic inline at the call site. This keeps the harness concern
("how to call an LLM reliably") separate from business logic ("what
to ask for, how to parse the response, how to degrade on failure"),
which stays in the feature's own module (e.g. `src/workflow.py`).

- `get_client(timeout=...)` returns an `anthropic.Anthropic` client
  with the SDK's own silent retries disabled (`max_retries=0`) — this
  harness owns retries instead, so the two mechanisms don't stack.
- `call_with_retry(fn, ...)` takes any zero-arg callable, retries
  `src.llm_client.RETRYABLE_EXCEPTIONS` (timeout, connection error,
  rate limit, 5xx/overloaded/unavailable) with exponential backoff,
  logs every attempt, and re-raises the last exception on exhaustion
  so the caller decides how to degrade — it never swallows a failure
  itself.
- When adding a new LLM-calling feature (e.g. a future `B6`-`B8`/`C4`
  task from `CANDIDATE_TASKS.md`), reuse `call_with_retry()` rather
  than duplicating retry logic; extend `src/llm_client.py` itself (not
  each call site) if new harness behavior is needed (e.g. a different
  retry policy, request-level cost/latency tracking).
- Any module logs via its own `logging.getLogger(__name__)`; the
  Streamlit debug panel (`src/app.py`) attaches its handler to the
  parent `"src"` logger, so every `src.*` submodule's log lines
  (workflow nodes, this harness, or a future one) show up there
  automatically via normal logger propagation — no per-module wiring
  needed in `src/app.py`.

## Task Management & Reasoning

**🚨 MANDATORY: Always use TASKS.md and REASONING.md. No exceptions.**

This project uses `TASKS.md` following the [TASKS.md specification](https://github.com/tasksmd/tasks.md).

**Required Workflow:**
0. **Check for a matching skill** before treating this file (or
   `AGENTS.md`) as the complete picture — scan the available-skills
   listing for one matching the situation (e.g. this repo's TASKS.md
   convention) and invoke it with `Skill` first. A skill can add or
   override rules not written here; don't wait to reach for it
   reactively, only after something has already gone wrong.
1. **Read** `TASKS.md` at the start of EVERY session
2. **Pick** a task using `pnpm tasks:pick` or select from TASKS.md
3. **Claim** by appending `(@claude)` to the task title
4. **Branch** before making any commit: `git checkout -b task/<id>`.
   **Never commit or push directly to `main`/`master`** — not even for
   a small or docs-only change; see `AGENTS.md`'s "Branch and PR
   Discipline" for the full rule.
5. **Document** reasoning in `REASONING.md` BEFORE starting work:
   - Goal, Analysis, Decision, Action, Reasoning
6. **Update** `REASONING.md` during work with major decisions
7. **Sync** TASKS.md's entry for a task (Files, Details, Status) if the
   human adds or changes actions within it while it's in progress, and
   log the change in `REASONING.md` as a dated update — never let
   TASKS.md drift out of sync with the real scope of the work
8. **Complete** task and document outcome in `REASONING.md`
9. **Ask** for human approval before marking the task done — never
   self-approve; wait for an explicit go-ahead
10. **Remove** completed task from `TASKS.md` only after that approval
    (history in git), on its own branch/PR titled
    `Closing task as "Done": <task title>`
11. **Add** any new tasks discovered during work

**Priority levels:** P0 = critical, P1 = high, P2 = medium, P3 = low

See `AGENTS.md` for full task format, reasoning transcript examples, branch/PR discipline, and multi-agent coordination (this repo is also used with Junie).

## Commands

## Local Development Setup

```bash
```

## Required env vars:

## Key Files

| File | Purpose |
|------|---------|
| `src/workflow.py` | LangGraph state machine & node business logic (Extractor, LLM Extraction Fallback, Verifier, Analyst) |
| `src/llm_client.py` | LLM-calling harness (Anthropic client construction, retry/backoff) — see "LLM-Calling Harness Pattern" above |
| `src/app.py` | Streamlit UI |
| `src/tools.py` | Deterministic tools (historical claims lookup, loss-ratio calculation, LLM-output grounding check) |
| `src/models.py` | Pydantic data schemas |
| `src/parser.py` | PDF parsing into page sections |

## Deployment (Railway)
