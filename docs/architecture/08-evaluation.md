# Evaluation Architecture

## Eval types

```text
skill selection eval
tool trajectory eval
policy behavior eval
evidence presence eval
output schema eval
safety eval
context resolution eval
memory safety eval
hook behavior eval
extension trust eval
```

## Release gates

Blocking failures:

```text
forbidden tool call
policy behavior failure
secret or PII leak
schema invalid
missing required evidence
untrusted production skill
snapshot mismatch
```
