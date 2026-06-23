# Layered Model

```text
Runtime Layer
  - Generic Runtime
  - Workflow
  - Checkpoint / Resume
  - Context Budget Manager

Behavior Layer
  - Agent Profile
  - Instructions
  - Guidance Files
  - Skills
  - Commands

Action Layer
  - Tools
  - MCP Servers
  - Extensions

Context Layer
  - Knowledge Scopes
  - Memory Scopes
  - Auto Memory
  - Context Resolution Engine

Governance Layer
  - Policies
  - Sandbox / Permission Modes
  - Hooks
  - Model Policy
  - Evidence Model

Quality Layer
  - Eval Profile
  - Agent Improvement Loop
```

## Interpretation

```text
Runtime    = how the agent executes
Behavior   = how the agent behaves
Action     = what the agent can do
Context    = what the agent can know or remember
Governance = what the agent is allowed to do and what must be enforced
Quality    = how the agent is tested and improved
```
