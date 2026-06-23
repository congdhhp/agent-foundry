# Agent Revisions

Every component change should create a new revision.

Examples:

```text
rev-001: initial draft
rev-002: add logs.search
rev-003: import incident-triage skill
rev-004: add production-read-mostly policy
rev-005: eval-passed candidate
```

## Rule

```text
Published/production agents are promoted by revision, not mutated in place.
```
