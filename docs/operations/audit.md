# Audit

## Minimum audit events

```text
task.started
agent.snapshot.created
agent.snapshot.used
agent.profile.loaded
guidance.loaded
memory.index.loaded
skill.selected
command.selected
tool.proposed
policy.evaluated
hook.executed
approval.requested
approval.granted
approval.denied
tool.executed
evidence.created
output.generated
task.completed
eval.scored
agent.component.added
agent.component.removed
agent.component.disabled
agent.revision.promoted
```

Production audit should be append-only or immutable.
