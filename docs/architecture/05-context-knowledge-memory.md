# Context, Knowledge, and Memory

## Distinctions

```text
Guidance = persistent rules/context humans maintain
Knowledge = external sources the agent may retrieve
Memory = learned or retained information
Evidence = proof supporting a claim
```

## Auto Memory

Suggested local structure:

```text
.agent/memory/
  MEMORY.md
  debugging.md
  conventions.md
  decisions.md
  failures.md
```

`MEMORY.md` should be a concise index. Topic files store detailed notes and are read on demand.

## Memory rules

```text
Memory is context, not enforcement.
Policy is enforcement.
Hooks are deterministic enforcement.
```

## Memory promotion

Useful memory can be promoted to:

```text
AGENTS.md
team guidance
skill documentation
policy rule
eval case
```
