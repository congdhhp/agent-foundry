# API, CLI and Storage

**Audience:** Backend Engineer, Platform Engineer, CLI Engineer, Technical Lead  
**Status:** Draft v1

## Universal CLI

The CLI should not be coding-centric. It is the local-first interface for composing, running, inspecting, approving and evaluating agents.

```bash
agent create
agent bind
agent run
agent inspect
agent approve
agent skills
agent tools
agent eval
agent publish
agent sessions
```

## CLI Command Groups

| Command group | Purpose |
|---|---|
| `agent create` | Create an agent from template and bindings |
| `agent run` | Execute a task against an agent |
| `agent inspect` | Show resolved profile, skills, policy and tools |
| `agent approve` | Approve or reject pending action |
| `agent skills` | List, validate and publish skills |
| `agent tools` | List providers and capability bindings |
| `agent eval` | Run eval suites |
| `agent sessions` | Inspect task state, traces and artifacts |
| `agent publish` | Promote agent after validation/evals |

## CLI Examples

Create monitoring agent:

```bash
agent create monitoring-agent \
  --template generic-task-agent@1.0.0 \
  --skill incident-triage@1.0.0 \
  --skill metrics-analysis@1.1.0 \
  --skill log-analysis@1.2.0 \
  --tool-group observability-readonly \
  --policy production-read-mostly@2.0.0
```

Run task:

```bash
agent run monitoring-agent \
  "Investigate checkout latency spike from the last 30 minutes"
```

Inspect:

```bash
agent inspect monitoring-agent --resolved
```

Run evals:

```bash
agent eval run sre-monitoring-agent-evals@1.0.0
```

## Local Storage Layout

```text
.agent/
  config.yaml
  agents/
    monitoring-agent.yaml
    coding-agent.yaml
  skills/
    incident-triage/
    bugfix/
  capabilities/
    metrics.query.yaml
    logs.search.yaml
  sessions/
    task_123/
      events.jsonl
      state.sqlite
      trace.jsonl
      artifacts/
  policies/
  tools/
```

## REST API

### Agent Endpoints

```text
POST   /agents
GET    /agents
GET    /agents/{agent_id}
PATCH  /agents/{agent_id}
POST   /agents/{agent_id}/run
POST   /agents/{agent_id}/publish
```

### Skill Endpoints

```text
GET    /skills
POST   /skills
GET    /skills/{skill_id}
POST   /skills/{skill_id}/validate
POST   /skills/{skill_id}/publish
```

### Capability and Tool Endpoints

```text
GET    /capabilities
GET    /capabilities/{capability_id}
GET    /tools/providers
POST   /tools/bindings
POST   /tools/providers/{provider_id}/validate
```

### Policy and Approval Endpoints

```text
GET    /policies
POST   /policies/{policy_id}/simulate
GET    /approvals
POST   /approvals/{approval_id}/approve
POST   /approvals/{approval_id}/deny
```

### Task Endpoints

```text
GET    /tasks/{task_id}
GET    /tasks/{task_id}/trace
GET    /tasks/{task_id}/artifacts
GET    /tasks/{task_id}/evidence
POST   /tasks/{task_id}/cancel
```

## Run Task API

```json
POST /agents/sre-monitoring-agent/run
{
  "input": "Investigate high error rate in checkout service",
  "metadata": {
    "environment": "prod",
    "service": "checkout",
    "time_window": "last_30_minutes"
  }
}
```

## Final Response Object

```json
{
  "task_id": "task_123",
  "status": "completed",
  "summary": "Error rate increased after deployment v1.2.3.",
  "confidence": "medium",
  "evidence": ["ev_metrics_1", "ev_logs_2", "ev_deploy_3"],
  "recommended_actions": [
    {
      "action": "rollback_deployment@1.0",
      "requires_approval": true,
      "risk": "critical"
    }
  ],
  "artifacts": [
    {
      "type": "incident_report",
      "uri": "artifact://task_123/report.md"
    }
  ]
}
```

## Storage Model

| Store | Purpose | Suggested technology |
|---|---|---|
| Agent Registry DB | Agents, templates, bindings | Postgres |
| Skill Registry | Skill packages and metadata | Git + object store + Postgres |
| Capability Registry | Capability contracts | Postgres/Git |
| State Store | Runtime state | Postgres/Redis |
| Checkpoint Store | Durable checkpoints | Postgres |
| Audit Store | Immutable audit events | Postgres/EventStore/Kafka + object store |
| Trace Store | Observability traces | OpenTelemetry backend/LangSmith/Langfuse |
| Vector Store | Embeddings | pgvector/Qdrant/Weaviate/Milvus |
| Search Index | Keyword/hybrid search | OpenSearch/Elasticsearch |
| Object Store | Artifacts, docs, raw tool outputs | S3-compatible |
| Eval Store | Eval results and datasets | Postgres + object store |

## Core Tables

```sql
create table agents (
  id text primary key,
  tenant_id text not null,
  name text not null,
  template_id text not null,
  purpose text,
  status text not null,
  manifest jsonb not null,
  created_at timestamp not null,
  updated_at timestamp not null
);

create table skills (
  id text not null,
  version text not null,
  owner text not null,
  risk_level text not null,
  lifecycle_status text not null,
  package_uri text not null,
  metadata jsonb not null,
  primary key (id, version)
);

create table capability_contracts (
  id text not null,
  version text not null,
  risk_level text not null,
  input_schema jsonb not null,
  output_schema jsonb not null,
  semantic_contract jsonb not null,
  primary key (id, version)
);

create table agent_skill_bindings (
  agent_id text not null,
  skill_id text not null,
  skill_version text not null,
  enabled boolean not null default true,
  priority int not null default 100,
  primary key (agent_id, skill_id, skill_version)
);

create table agent_tool_bindings (
  agent_id text not null,
  capability_id text not null,
  capability_version text not null,
  provider_id text not null,
  tool_name text not null,
  primary key (agent_id, capability_id, capability_version)
);

create table tasks (
  id text primary key,
  tenant_id text not null,
  agent_id text not null,
  user_id text not null,
  status text not null,
  input jsonb not null,
  output jsonb,
  created_at timestamp not null,
  updated_at timestamp not null
);

create table evidence (
  id text primary key,
  task_id text not null,
  source_type text not null,
  source_uri text,
  capability text,
  summary text not null,
  raw_ref text,
  sensitivity text not null,
  confidence numeric,
  created_at timestamp not null
);

create table audit_events (
  id text primary key,
  task_id text,
  agent_id text,
  user_id text,
  event_type text not null,
  payload jsonb not null,
  created_at timestamp not null
);
```

## API Design Principles

1. APIs accept artifact IDs with explicit versions.
2. Mutating endpoints emit audit events.
3. Publish endpoints run validation gates.
4. Task endpoints expose trace, evidence and artifacts separately.
5. Approval endpoints require authorization and structured decision payload.
6. API responses include correlation IDs.

## MVP API and CLI

MVP can start with CLI-first:

1. `agent run`.
2. `agent inspect`.
3. `agent eval`.
4. Local `.agent/` storage.
5. JSONL events.
6. YAML artifacts.

REST can be introduced once the runtime and local artifact model are stable.

