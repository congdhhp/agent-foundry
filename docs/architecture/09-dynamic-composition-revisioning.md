# Dynamic Composition and Revisioning

## Core rule

```text
Agent definitions are mutable.
Agent runs are immutable snapshots.
```

## Mutable components

```text
instructions
guidance files
skills
commands
tools
policies
hooks
workflow
knowledge scopes
memory scopes
model policy
evidence model
eval profile
extensions
```

## Agent revisions

Every component change should create a new agent revision.

```text
incident-triage-agent@rev-001
incident-triage-agent@rev-002
incident-triage-agent@rev-003
```

## Run snapshots

Every run records the resolved immutable snapshot used:

```text
agent revision
skill versions
tool versions
policy versions
hook versions
guidance versions
memory index version
model policy
workflow
```

## Default behavior

Changes apply to future runs by default. Running tasks use their original snapshot unless explicitly paused/cancelled for security reasons.
