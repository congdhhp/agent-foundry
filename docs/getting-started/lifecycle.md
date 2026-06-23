# Agent Lifecycle

## Stages

```text
Draft
-> Tool-enabled
-> Skill-augmented
-> Reviewed
-> Eval-passed
-> Published
-> Production
```

| Stage | Description | Production-ready? |
|---|---|---|
| Draft | Runtime + profile + instructions | No |
| Tool-enabled | Tools added with default policies | No |
| Skill-augmented | Skills added from local/GitHub/registry | No |
| Reviewed | Skill/tool/policy compatibility reviewed | Not yet |
| Eval-passed | Required evals pass | Candidate |
| Published | Team can use approved revision | Yes for team use |
| Production | Strong governance, audit, approval, release gate | Yes |

## Key lifecycle rule

```text
Agent definitions are mutable.
Agent runs are immutable snapshots.
```
