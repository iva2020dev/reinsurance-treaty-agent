# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository RTA.

## Project Overview

## Architecture

## Key Architectural Patterns

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

## Deployment (Railway)
