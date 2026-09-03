# Radius Project Skills

This directory contains custom skills for AI agents working on the Radius project.

## What are Skills?

Skills are reusable markdown files that provide specialized knowledge, workflows, or tools to AI agents. They're automatically loaded when relevant keywords or patterns appear in conversations.

## Skill Structure

Each skill should be a markdown file (`.md`) with:

```markdown
# Skill Name

Brief description of what this skill does and when to use it.

## Usage

Instructions on how to use the skill...

## Examples

Concrete examples...
```

## Creating Skills

You can create skills by:

1. **Manually**: Create `.md` files in this directory
2. **Using skill-creator**: Ask an AI agent to "create a skill for [topic]"
3. **Import from GitHub**: Use `/add-skill <github-url>`

## Current Custom Skills

- **radius-socketio** - Socket.io patterns for Radius (dual database strategy, socket-to-user mapping, event handling)

## Suggested Skills for Radius

Consider creating skills for:
- Radius deployment workflows
- Socket.io event handling patterns
- Mapbox integration patterns
- Redis location caching patterns
- Django AI service integration
