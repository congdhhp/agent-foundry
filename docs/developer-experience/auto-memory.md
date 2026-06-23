# Auto Memory

## Purpose

Auto memory captures learned preferences, recurring patterns, corrections, and project-specific lessons across sessions.

## Suggested structure

```text
.agent/memory/
  MEMORY.md
  debugging.md
  conventions.md
  decisions.md
  failures.md
```

## `MEMORY.md`

`MEMORY.md` should be a concise index:

```markdown
# Project Memory Index

## Conventions
- See conventions.md

## Debugging notes
- See debugging.md

## Decisions
- See decisions.md
```

## Memory lifecycle

```text
candidate
accepted
deprecated
deleted
promoted
```

## Safety

Do not store:

```text
secrets
unnecessary PII
tokens
credentials
unverified facts as authoritative memory
```
