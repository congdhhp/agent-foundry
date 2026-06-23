# Promotion Process

## Flow

```text
create draft revision
-> validate manifests
-> scan skills/extensions/hooks
-> run evals
-> review policy impact
-> owner approval
-> promote revision
-> new runs use promoted revision
```

## Production requirements

```text
policy checks pass
eval gates pass
security review complete for untrusted artifacts
snapshot reproducible
audit enabled
rollback plan available
```
