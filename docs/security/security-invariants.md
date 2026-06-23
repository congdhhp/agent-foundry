# Security Invariants

```text
No tool execution without policy decision.
No write/execute/send/delete/refund/rollback without approval if policy requires it.
No raw secret should enter model context.
No untrusted retrieved content may override instructions or policies.
No skill script runs outside sandbox.
No production output should contain unsupported high-risk claims.
No cross-scope memory access.
No untrusted extension may be promoted to production without review and eval.
No production run may execute without a resolved immutable snapshot.
```
