# Policy, Security and Governance

**Audience:** Security Engineer, Platform Engineer, Solution Architect, Compliance Owner  
**Status:** Draft v1

## Governance Principle

Policy is enforced by the platform runtime and tool plane, not merely suggested in prompts.

Core invariant:

```text
plan action
-> classify risk
-> build policy context
-> evaluate policy
-> allow / transform / approve / deny
-> execute only when permitted
```

## Policy Decision Model

| Decision | Meaning |
|---|---|
| `ALLOW` | Action can execute immediately |
| `REQUIRE_APPROVAL` | Runtime must pause and request human approval |
| `DENY` | Action must not execute |
| `REQUIRE_TRANSFORM` | Input/output must be transformed before proceeding |
| `REQUIRE_STEP_UP_AUTH` | User or approver must re-authenticate or satisfy stronger auth |

## Policy Context

Policy evaluation should include:

1. User identity.
2. Agent identity.
3. Tenant.
4. Environment.
5. Task metadata.
6. Capability.
7. Provider.
8. Access type.
9. Risk level.
10. Data sensitivity.
11. Approval state.
12. Time and location constraints.
13. Session constraints.
14. Evidence references when applicable.

## Policy Manifest Example

```yaml
apiVersion: agents.platform/v1
kind: Policy
metadata:
  id: production-read-mostly
  version: 2.0.0
spec:
  rules:
    - match:
        capability: metrics.query@1.0
      decision: allow

    - match:
        capability: logs.search@1.0
      decision: allow
      transforms:
        - redact_secrets
        - redact_pii_if_external

    - match:
        capability: message.send@1.0
      decision: require_approval
      approvers:
        - role:sre_oncall

    - match:
        capability: deployment.rollback@1.0
        environment: prod
      decision: require_approval
      approvers:
        - role:sre_lead
        - role:service_owner

    - match:
        capability: secrets.read@1.0
      decision: deny
```

## Approval Object

```json
{
  "approval_id": "appr_123",
  "task_id": "task_456",
  "agent_id": "monitoring-agent",
  "action": "deployment.rollback@1.0",
  "risk_level": "critical",
  "reason": "Agent recommends rollback due to 5xx spike after deploy v1.2.3",
  "evidence_refs": ["ev_1", "ev_2", "ev_3"],
  "requested_by": "agent",
  "approvers": ["sre_lead", "service_owner"],
  "status": "pending"
}
```

## Identity Model

The platform distinguishes:

1. User identity.
2. Agent identity.
3. Service identity.
4. Tool provider identity.
5. Remote agent identity.

Every tool call must be attributable:

```text
user -> agent -> capability -> provider -> external system
```

## Authorization Model

Recommended controls:

1. RBAC for coarse-grained roles.
2. ABAC for tenant, environment, data sensitivity and task metadata.
3. ReBAC where ownership relationships matter.
4. Capability-level authorization.
5. Environment-level policy.
6. Task-scoped credentials.
7. Provider-level allowlist.

## Threat Model

The platform must defend against:

1. Prompt injection from docs, web, email, tickets and logs.
2. Tool misuse.
3. Unauthorized data access.
4. Cross-tenant leakage.
5. Secret exfiltration.
6. Unsafe code/shell execution.
7. Malicious skill packages.
8. Malicious MCP servers.
9. Malicious remote agents through A2A.
10. Over-permissioned agent identity.
11. Audit evasion.
12. Data retention violation.
13. Model/provider misconfiguration.
14. Insecure output handling.
15. Excessive agency.

## Prompt Injection Controls

Mandatory controls:

1. Tag retrieved/tool content as untrusted unless explicitly trusted.
2. Separate instructions from data in runtime messages.
3. Do not allow retrieved content to override platform, policy or skill instructions.
4. Use a tool-call firewall before executing actions.
5. Validate output schemas.
6. Verify claims against evidence.
7. Require human approval for side effects.
8. Deny dangerous capabilities in untrusted contexts.

## Skill Supply-Chain Controls

Skills are operational text and can be malicious. Required controls:

1. Owner metadata.
2. Version pinning.
3. Signed skill packages for production.
4. Allowed source registry.
5. Static checks.
6. Semantic checks.
7. Eval checks.
8. Security review.
9. Dependency/resource scanning.
10. Runtime permission restrictions.

## MCP Security Controls

MCP servers require:

1. Authentication.
2. Authorization.
3. Transport security.
4. Tool allowlist.
5. Input validation.
6. Output sanitization.
7. Rate limiting.
8. Audit.
9. Network egress control.
10. Sandbox for local/stdio tools.

## Secret Handling

Agents should never see raw secrets.

```text
Agent requests capability
-> provider uses secret internally
-> provider returns sanitized result
```

Rules:

1. Secrets are not injected into prompts.
2. Secrets are not persisted in evidence summaries.
3. Tool output is scanned and redacted.
4. Secret access capability is denied by default.
5. Break-glass access requires strong approval and audit.

## Data Classification

| Classification | Examples | Default controls |
|---|---|---|
| public | Public docs, marketing pages | Standard audit |
| internal | Runbooks, internal metrics | Tenant/user auth |
| confidential | Source code, customer contracts | ACL, redaction, retention |
| restricted | Credentials, payment data, regulated PII | Deny by default or strong approval |

## Governance Gates

| Gate | Applies to | Required checks |
|---|---|---|
| Skill review | Skill publication | Owner, policy compliance, evals, injection safety |
| Capability review | Contract activation | Schema, risk, semantic contract |
| Provider review | Tool registration | Auth, sandbox, output sanitization, audit |
| Agent publish | Production agent | Manifest, policy, capability binding, eval pass |
| Policy release | Policy activation | Simulation, regression, approver routing |

## Audit Requirements

Audit events must be immutable or append-only and include:

1. Actor identity.
2. Agent identity.
3. Task ID.
4. Event type.
5. Policy decision.
6. Capability/provider.
7. Approval status.
8. Timestamp.
9. Correlation/trace ID.

## MVP Security Scope

MVP must include:

1. Capability risk levels.
2. Policy engine with allow, deny and approval.
3. Structured approval object.
4. Secret/PII redaction hook.
5. Audit event log.
6. Deny-by-default for critical actions.
7. Basic prompt injection guidance for retrieved content.

