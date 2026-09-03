# AGENTS.md

Agent instructions for working with the reinsurance-treaty-agent (RTA) codebase.

For project overview, architecture, commands, environment setup, deployment,
and key files, see **CLAUDE.md** — that's the canonical reference for
project facts. This file covers the cross-agent task workflow instead:
task management conventions, the reasoning transcript format, multi-agent
coordination, and custom skills.

## Task Management

This project **ALWAYS** uses `TASKS.md` as a lightweight task queue, following the [TASKS.md specification](https://github.com/tasksmd/tasks.md).

### Working with multiple agents

This repo is used with both Junie and Claude Code. Both read this file.

- One agent per task, one agent per uncommitted working tree at a time.
  Before starting either agent, `git status` should be clean.
- Note which agent is working a task in TASKS.md or REASONING.md so the
  other doesn't pick up the same item.
- Claude Code is the primary worker for this repo and should pick up
  tasks by default. Junie is secondary: use it only for quick, in-editor,
  single-file edits when Claude Code isn't already on the task, and
  prefer handing multi-file or cross-service work — anything needing
  tests run and verified before committing — to Claude Code.

### Mandatory Workflow

**🚨 CRITICAL: Every session MUST follow this workflow. No exceptions.**

1. **Read** `TASKS.md` at the start of EVERY session to understand current priorities
2. **Pick** a task using `pnpm tasks:pick` or manually select from TASKS.md
3. **Claim** the task by appending `(@your-name)` to the task title before starting work
   - Example: `- [ ] Fix authentication bug (@claude)`
4. **Document** your reasoning in `REASONING.md` with:
   - **Goal**: What you're trying to achieve
   - **Analysis**: Your understanding of the problem
   - **Decision**: What approach you're taking
   - **Action**: What you're doing
   - **Reasoning**: Why you made these choices
5. **Work** on the task following all policies in TASKS.md
6. **Update** REASONING.md during work with major decisions or discoveries
7. **Sync** if the human adds or changes actions within an in-progress
   task (e.g. "also add tests for this"): update that task's entry in
   TASKS.md (Files, Details, Status — whatever changed) to match what
   was actually asked for and done, and log the change in REASONING.md
   as a dated update under that task's entry. Never let TASKS.md drift
   out of sync with the real scope of the work.
8. **Ask** for human approval before marking a task done — present the
   verified work (what was built, how it was verified) and wait for an
   explicit go-ahead before removing the task from TASKS.md. Never
   self-approve a task as complete.
9. **Remove** completed tasks from TASKS.md only after that approval
   (history is tracked in git)
10. **Add** new tasks discovered during work to the appropriate priority section

### Priority Levels

- **P0** = Critical, urgent, blocks other work
- **P1** = High priority, important features/fixes
- **P2** = Medium priority, improvements
- **P3** = Low priority, nice-to-have

### Task Dependencies

- Tasks with dependencies **MUST** have an **ID** field so blockers can reference them
- Use the `**Blocked by**` field to indicate task dependencies (by ID)

### Task Format

```markdown
- [ ] Task description (@agent-name)
  - **ID**: unique-id
  - **Tags**: backend, frontend, etc.
  - **Details**: Additional context
  - **Files**: Relevant file paths
  - **Acceptance**: Completion criteria
  - **Blocked by**: other-task-id
```

The upstream [spec](https://github.com/tasksmd/tasks.md/blob/main/spec.md#metadata) (currently v0.10.2, matching the `@tasks-md/*` versions pinned in `package.json`) defines additional optional fields we don't use yet but may adopt as needed — e.g. **Touches** (write-set, for detecting overlap when Junie and Claude Code might work in parallel), **Blocked** (external blocker, distinct from **Blocked by**), and **Parent**/sub-tasks. All metadata beyond **ID**/**Tags**/**Details**/**Files**/**Acceptance**/**Blocked by** stays optional.

Per spec: a completed top-level task is always **removed** from `TASKS.md`, never marked `[x]` — that checkbox is reserved for sub-tasks tracking progress within a parent task. `tasks-lint` (v0.10.2+) flags a checked-off top-level task as an error.

### Keeping tasks.md tooling current

`https://github.com/tasksmd/tasks.md` is checked for new releases roughly every second Monday by a scheduled cloud routine (see `https://claude.ai/code/routines`). Each run:

1. Compares the pinned `@tasks-md/{cli,lint,parser}` version in `package.json` against the latest upstream release/npm version.
2. Always appends a dated entry to `REASONING.md` recording what was compared and the outcome — so every check is visible in the log, whether or not an update was found (do this even when there's nothing to report).
3. If a newer version exists, adds a new task to `TASKS.md` (tag `maintenance, dependencies`) describing the version jump and pointing at the upstream release notes/spec changelog for breaking changes — it does **not** perform the upgrade itself; that's picked up as a normal task later (see the 2026-08-15 REASONING.md entry for what a manual refresh like this looked like, including a breaking CLI change from a past bump: `tasks lint` → `tasks-lint`).
4. Commits and pushes whatever it changed (the `REASONING.md` entry, and the new `TASKS.md` task if any).

### Commands

```bash
pnpm tasks:lint         # Lint TASKS.md
pnpm tasks:pick         # Show next available task
pnpm tasks:install      # Install tasks.md commands for your agent
```

## Reasoning Transcript

**ALWAYS** document your reasoning in `REASONING.md` for every task. This provides transparency and helps future agents (and humans) understand decisions made.

### Format

```markdown
## YYYY-MM-DD HH:MM:SS

### Task: [Task Title]
- **Goal**: What you're trying to achieve
- **Analysis**: Your understanding of the problem/requirements
- **Decision**: What approach you're taking and why
- **Action**: What you're doing (high-level steps)
- **Reasoning**: Why you made these specific choices
- **Outcome**: What happened (add after completion)
```

### When to Update

- **Before** starting a task: Document goal, analysis, and planned approach
- **During** the task: Document major decisions, blockers, or discoveries
- **After** completing: Document outcome and any learnings

This creates a valuable audit trail of AI agent work.

### Timestamp Format

Every dated entry in `REASONING.md` and every "Recently completed" note in
`TASKS.md` **MUST** include the time of day alongside the date, in
24-hour `HH:MM:SS` format (`YYYY-MM-DD HH:MM:SS`) — not just the date.
For a completion note, use the time the task actually finished (e.g. a
PR's merge time), not the time the entry was written. This applies going
forward to all future entries, not just this one.

## Skills

Custom skills for this project are stored in `.agents/skills/`. Skills are reusable markdown files that provide specialized knowledge or workflows.

### Current Skills

### Creating Skills

You can create skills by:
- **Manually**: Create `.md` files in `.agents/skills/`
- **Using skill-creator**: Ask an AI agent to "create a skill for [topic]"
- **Import**: Use the add-skill tool for external skills

### Suggested Skills for reinsurance-treaty-agent (RTA)

Consider creating skills for:
- Radius deployment workflows (Railway, Docker)
- Socket.io event handling patterns
- Mapbox GL JS integration patterns
- Redis location caching patterns
- Database migration workflows (Drizzle + Django)
