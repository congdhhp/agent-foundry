# Storage Model

## MVP local storage

```text
.agent/
  agents/
  revisions/
  snapshots/
  guidance/
  memory/
    MEMORY.md
  skills/
  commands/
  tools/
  policies/
  hooks/
  evals/
  sessions/
    task_123/
      state.json
      events.jsonl
      evidence.jsonl
      snapshot.json
      artifacts/
      eval-result.json
```

## Future relational model

```text
agents
agent_versions
agent_revisions
agent_snapshots
skills
skill_versions
tools
tool_providers
commands
hooks
extensions
tasks
events
tool_calls
policy_decisions
approvals
evidence
artifacts
eval_runs
memory_entries
```
