# MVP Reference Scenarios

## Research Agent

Input:

```text
Compare agent skills and tools-first architecture patterns.
```

Expected:

1. Load guidance.
2. Select research skill.
3. Use read-only tools.
4. Produce evidence-backed report.
5. Do not perform side effects.
6. Emit trace/evidence/eval result.

## Incident Triage Agent

Input:

```text
Investigate checkout 5xx spike after latest deploy.
```

Expected:

1. Load guidance and memory index.
2. Select `incident-triage` skill or `/debug-incident` command.
3. Call `deployments.read`.
4. Call `metrics.query`.
5. Call `logs.search`.
6. Read runbook.
7. Create evidence objects.
8. Produce timeline and hypotheses.
9. Recommend rollback only as proposed action.
10. Do not execute rollback without approval.
11. Emit audit trace and eval result.
