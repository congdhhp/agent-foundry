# Sandbox and Permission Modes

## Modes

```text
read-only
workspace-write
workspace-write-with-network
approval-required
danger-full-access
```

## Recommended defaults

| Environment | Default mode |
|---|---|
| Draft local | workspace-write, no network unless needed |
| Team shared | read-only or workspace-write |
| Published | read-only unless tools require write |
| Production | read-only / approval-required |

## Rules

```text
Sandbox is the technical boundary.
Approval policy decides when to ask humans.
Policy decides whether an action is allowed.
Hooks enforce deterministic checks.
```
