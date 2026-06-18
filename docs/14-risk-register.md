# Risk Register

**Audience:** CTO, Security Engineer, Platform Engineer, Product Owner  
**Status:** Draft v1

## Risk Scoring

| Level | Meaning |
|---|---|
| Low | Manageable with standard engineering controls |
| Medium | Requires explicit mitigation and monitoring |
| High | Requires design review and release gate |
| Critical | Requires executive/security approval or default denial |

## Register

| ID | Risk | Impact | Likelihood | Severity | Mitigation | Owner |
|---|---|---:|---:|---:|---|---|
| R-001 | Skill injection or malicious skill | Unsafe behavior, data leak | Medium | High | Signed skills, source allowlist, review, evals, sandbox | Security / AI Platform |
| R-002 | Tool misuse | Data loss or external side effects | Medium | High | Policy engine, approvals, capability scoping, audit | Platform |
| R-003 | Prompt injection from docs/logs/web | Wrong actions, leakage | High | High | Untrusted tagging, instruction/data separation, tool firewall | Security |
| R-004 | Over-general runtime | Poor UX and weak task performance | Medium | Medium | Domain workflow templates and reference agents | Product / Runtime |
| R-005 | Capability abstraction too shallow | Vendor lock-in returns | Medium | High | Semantic contracts, compatibility tests, provider matrix | Architecture |
| R-006 | A2A overuse | Complexity, latency, trust failures | Medium | Medium | Defer A2A, use only for independent agents | Architecture |
| R-007 | MCP server compromise | Tool/data compromise | Low to Medium | High | Auth, allowlist, sandbox, egress controls, audit | Security / Platform |
| R-008 | Cross-tenant leakage | Severe compliance breach | Low | Critical | Tenant isolation, ACL-aware retrieval, test isolation | Security |
| R-009 | Hallucinated evidence | Wrong decisions with false trust | Medium | High | Evidence IDs from system only, verifier, output schema | Runtime / Eval |
| R-010 | Eval gaps | Regressions escape release | High | High | Eval gates, golden datasets, online monitoring | Eval |
| R-011 | Cost explosion | Budget and adoption issue | Medium | Medium | Model gateway, quotas, caching, cost tracking | Platform |
| R-012 | Long-running task failure | Poor reliability | Medium | Medium | Durable checkpoints, retries, resume, idempotency | Runtime |
| R-013 | Human approval fatigue | Users approve blindly | Medium | Medium | Risk tiering, concise evidence, batch policies, analytics | Product |
| R-014 | Secret exfiltration | Security breach | Medium | Critical | Secrets never enter model context, redaction, deny defaults | Security |
| R-015 | Unbounded agency | Unsafe autonomous action | Medium | High | Action budgets, risk tiers, approval, deny critical actions | Platform |
| R-016 | Weak audit immutability | Compliance failure | Low | High | Append-only audit, retention policy, tamper evidence | Platform / Security |
| R-017 | Skill version drift | Non-reproducible behavior | Medium | Medium | Version pinning and immutable published artifacts | Platform |
| R-018 | Provider output schema drift | Runtime failures or bad evidence | Medium | Medium | Contract tests and provider health checks | Tooling |
| R-019 | Policy rule conflict | Incorrect allow/deny behavior | Medium | High | Policy simulation, conflict detection, regression tests | Security / Platform |
| R-020 | Model provider misconfiguration | Data exposure or poor quality | Low to Medium | High | Model policy, allowlist, redaction, routing tests | Platform |

## Risk Treatment Strategy

1. Critical risks are deny-by-default until explicitly reviewed.
2. High risks require design review and automated regression coverage.
3. Medium risks require documented mitigation and monitoring.
4. Low risks can be tracked through normal engineering process.

## Risk Review Cadence

Recommended cadence:

1. Weekly during MVP.
2. Before each production release.
3. After any security incident.
4. When adding high-risk capabilities.
5. When integrating new external providers.

## Production Readiness Risk Gates

Before production:

1. Policy-before-action is implemented.
2. Audit events are append-only.
3. Secrets do not enter model context.
4. High/critical actions require approval or are denied.
5. Capability providers pass contract tests.
6. Eval gates are enforced for production agents.
7. Tenant and ACL boundaries are tested.
8. Incident runbooks exist.

