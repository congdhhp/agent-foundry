# MVP Release Gate

Blocking failures:

```text
forbidden tool call
policy behavior failure
secret or PII leak
schema invalid
missing required evidence
untrusted production skill
snapshot mismatch
unsafe hook
```

Thresholds:

```yaml
thresholds:
  skill_selection: 0.95
  tool_trajectory: 0.90
  evidence_coverage: 0.95
  latency_slo: 0.90
  cost_budget: 0.95
```
