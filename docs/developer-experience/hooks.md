# Hooks

## Purpose

Hooks provide deterministic lifecycle enforcement.

Skills guide. Policies decide. Hooks enforce.

## Recommended hook points

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

## Example

```yaml
hooks:
  PreToolUse:
    - match:
        tool: shell.run
      command: ./scripts/check-shell-policy.sh

  PostToolUse:
    - match:
        tool: file.patch
      command: npm run format

  PreResponse:
    - command: ./scripts/check-evidence-coverage.sh
```

## Safety

Hook scripts must be treated as executable code and governed by sandbox, trust level, and review process.
