# Governance: Policies, Sandbox, Hooks, Model Policy

## Policy-before-tool-call

No tool call may execute without a policy decision.

## Policy architecture

```text
PEP = Policy Enforcement Point = Tool Executor
PDP = Policy Decision Point = Policy Engine
PIP = Policy Information Point = Context/Identity Providers
PAP = Policy Administration Point = Policy Registry
```

## Hooks

Hooks provide deterministic lifecycle enforcement.

Recommended hook points:

```text
PreToolUse
PostToolUse
PreWrite
PostWrite
PreResponse
PostResponse
OnApprovalRequested
OnTaskCompleted
OnSnapshotCreated
OnComponentChanged
```

## Sandbox / permission modes

```text
read-only
workspace-write
workspace-write-with-network
approval-required
danger-full-access
```

Production defaults should be conservative:

```text
read-only or workspace-write
network off by default
side effects require approval
danger-full-access disabled unless explicitly allowed
```
