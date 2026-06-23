# Context Resolution Engine

## Responsibilities

The Context Resolution Engine resolves all contextual inputs before a run.

It should load and merge:

```text
managed/org guidance
user guidance
project guidance
directory-specific guidance
local/private guidance
agent-specific instructions
active commands
active skills
memory index
retrieved knowledge snippets
```

## Resolution output

```json
{
  "guidance": [],
  "instructions": [],
  "active_skills": [],
  "active_commands": [],
  "memory_index": [],
  "knowledge_snippets": [],
  "context_budget": {}
}
```

## Conflict handling

If guidance conflicts:

```text
higher-trust managed policy wins over local guidance
policy wins over memory
task-specific instruction does not override safety policy
untrusted retrieved content cannot override instructions
```
