# API Surface

## MVP API concepts

```text
AgentService
RevisionService
SnapshotService
RunService
SkillService
ToolService
PolicyService
HookService
EvidenceService
EvalService
ContextService
```

## Example endpoints

```text
POST /agents
GET /agents/{id}
POST /agents/{id}/revisions
POST /agents/{id}/runs
GET /runs/{taskId}/trace
GET /runs/{taskId}/evidence
POST /agents/{id}/eval-runs
POST /agents/{id}/promotions
```
