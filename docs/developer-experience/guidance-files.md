# Agent Guidance Files

## Purpose

Guidance files provide persistent context and rules for agents.

Recommended canonical file:

```text
AGENTS.md
```

Compatibility files:

```text
CLAUDE.md
GEMINI.md
```

These files should import or mirror the same guidance to avoid divergent behavior across tools.

## Guidance file contents

Recommended sections:

```text
Project overview
Repository layout
Build/test/lint commands
Coding standards
Architecture principles
Security constraints
Definition of done
Known pitfalls
```

## Guidance is not enforcement

```text
Guidance influences behavior.
Policy enforces decisions.
Hooks enforce deterministic lifecycle behavior.
```
