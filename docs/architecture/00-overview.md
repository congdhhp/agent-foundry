# Architecture Overview

## Thesis

> An agent is a dynamically composable artifact, not a separate implementation.

## Public model

```text
Agent = Instructions + Skills + Tools + Policies
```

## Production model

```text
Agent = Runtime Layer
      + Behavior Layer
      + Action Layer
      + Context Layer
      + Governance Layer
      + Quality Layer
```

## Key decisions

1. Tools are the public action primitive.
2. `Capability` is not a public concept.
3. Skills are lightweight `SKILL.md` workflow packages.
4. Guidance files provide project/user/team context.
5. Auto memory captures learned preferences and patterns.
6. Commands provide user-facing entrypoints.
7. Hooks provide deterministic lifecycle enforcement.
8. Every tool call must pass policy before execution.
9. Important claims require evidence.
10. Evals gate promotion.
11. Agent definitions are mutable.
12. Agent runs are immutable snapshots.
