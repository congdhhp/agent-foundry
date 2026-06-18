# Capability and Tool Plane

**Audience:** Solution Architect, Platform Engineer, Integration Engineer, Security Engineer  
**Status:** Draft v1

## Purpose

The capability and tool plane decouples skills from concrete tools. Skills depend on versioned capability contracts. Tool providers implement those contracts.

This enables a skill such as incident triage to use `metrics.query@1.0` instead of directly depending on Prometheus, Datadog or another vendor.

## Capability Contract

A capability contract is an API contract with:

1. Stable ID and version.
2. Input schema.
3. Output schema.
4. Access type.
5. Risk level.
6. Semantic guarantees.
7. Constraints.
8. Evidence behavior.
9. Compatibility rules.

Example:

```yaml
apiVersion: agents.platform/v1
kind: CapabilityContract
metadata:
  id: metrics.query
  version: 1.0.0
spec:
  category: observability
  accessType: read
  riskLevel: low
  inputSchema:
    type: object
    required:
      - query
      - time_range
    properties:
      query:
        type: string
      time_range:
        type: object
        required: [start, end]
      step:
        type: string
  outputSchema:
    type: object
    required:
      - series
      - evidence_id
      - metadata
  semanticContract:
    guarantees:
      - Returns time-series metric data.
      - Does not mutate external systems.
      - Does not expose raw credentials.
    constraints:
      max_time_range: 30d
      max_series: 1000
      requires_tenant_scope: true
  evidence:
    creates_evidence: true
    evidence_type: metric_observation
```

## Capability Categories

| Category | Example capabilities |
|---|---|
| Knowledge | `knowledge.search`, `document.read`, `citation.extract` |
| Workspace | `file.read`, `file.patch`, `shell.run`, `git.diff` |
| Observability | `metrics.query`, `logs.search`, `traces.search` |
| Ticketing | `ticket.read`, `ticket.create`, `ticket.update` |
| Messaging | `message.draft`, `message.send` |
| CRM | `customer.read`, `case.update` |
| Payment | `payment.read`, `refund.execute` |
| Deployment | `deployments.read`, `deployment.rollback`, `service.restart` |
| Security | `dependency.scan`, `cve.search`, `secret.scan` |

## Risk Classification

| Risk | Access pattern | Default behavior |
|---|---|---|
| Low | Read docs, query public/internal metrics | Allow if authorized |
| Medium | Read logs, customer records, internal reports | Allow with audit and redaction |
| High | Send message, create ticket, update CRM | Require approval by default |
| Critical | Rollback deploy, delete data, refund, financial transaction | Strong approval or deny |

## Tool Provider Manifest

```yaml
apiVersion: agents.platform/v1
kind: ToolProvider
metadata:
  id: prometheus-mcp
  name: Prometheus MCP Server
spec:
  protocol: mcp
  transport: http
  endpoint: https://mcp.company.com/prometheus
  authProfile: service-oauth
  capabilities:
    - contract: metrics.query@1.0
      tool: query
      riskLevel: low
  tenantScope: required
  outputSanitization:
    redactSecrets: true
    maxPayloadBytes: 1000000
```

## Execution Flow

```text
Agent Runtime
-> Proposed capability call
-> Input schema validation
-> Risk classification
-> Policy check
-> Capability binding resolution
-> Provider auth/context resolution
-> MCP gateway routing
-> Tool execution
-> Output schema validation
-> Sanitization
-> Evidence creation
-> Audit event
-> Runtime observation
```

## Tool Execution Contract

```json
{
  "task_id": "task_123",
  "trace_id": "trace_abc",
  "agent_id": "monitoring-agent",
  "user_id": "user_456",
  "tenant_id": "tenant_a",
  "capability": "metrics.query@1.0",
  "provider": "prometheus-mcp",
  "tool": "query",
  "input": {
    "query": "rate(http_requests_total{status=~\"5..\"}[5m])",
    "time_range": {
      "start": "2026-06-17T09:30:00Z",
      "end": "2026-06-17T10:00:00Z"
    }
  },
  "policy_context": {
    "risk_level": "low",
    "approval_id": null
  }
}
```

## MCP Gateway Responsibilities

1. Authenticate provider access.
2. Authorize capability use by user, agent, tenant and environment.
3. Validate input.
4. Enforce policy.
5. Route to MCP server/tool.
6. Apply sandbox and egress controls.
7. Sanitize output.
8. Create evidence metadata.
9. Emit audit and trace events.
10. Enforce rate limits and payload limits.

## Output Sanitization

Every provider response should be processed for:

1. Secret redaction.
2. PII redaction if policy requires it.
3. Payload size limit.
4. Untrusted content tagging.
5. Source metadata preservation.
6. Executable instruction stripping when content is intended for model context.
7. Evidence ID attachment.

## Provider Compatibility Tests

Each provider must pass:

1. Input schema compatibility test.
2. Output schema compatibility test.
3. Semantic behavior smoke test.
4. Risk classification check.
5. Auth failure test.
6. Rate limit behavior test.
7. Audit event generation test.
8. Sanitization test.

## Capability Version Compatibility

Provider compatibility matrix:

| Contract change | Provider action |
|---|---|
| Add optional input | Provider can remain compatible |
| Add required input | Provider must update implementation |
| Add optional output | Provider should update but remains compatible |
| Remove output field | Major contract change |
| Change semantic guarantee | New major version |
| Increase risk level | Policy review required |

## MVP Implementation

For MVP, the tool plane can start with:

1. Local capability registry using YAML files.
2. In-process provider adapters for workspace, shell, retrieval and mock observability.
3. Policy check before provider invocation.
4. JSON schema validation.
5. Local evidence creation.
6. Structured audit events.

MCP gateway can be minimal at first, as long as the runtime already calls through the capability abstraction.

