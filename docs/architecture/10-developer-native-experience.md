# Developer-Native Agent Experience

Modern CLI agents are converging around:

```text
repo guidance files
auto memory
skills
slash/custom commands
hooks
sandbox and approval modes
extensions/plugins
context hierarchy
context budget/progressive disclosure
```

This platform should support these patterns while preserving enterprise governance.

## Recommended UX concepts

```text
AGENTS.md = canonical cross-tool guidance
.agent/memory/MEMORY.md = local/project memory index
.agent/commands/*.md = custom commands
.agent/hooks.yaml = deterministic hook configuration
.agent/extensions.yaml = installed extension manifest
```

## Extension bundle

An extension may package:

```text
skills/
commands/
tools/
mcp-servers/
policies/
evals/
hooks/
templates/
```
