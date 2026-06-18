# Production Readiness Checklist

**Audience:** CTO, Technical Lead, SRE, Security Engineer, Release Owner  
**Status:** Draft v1

## Purpose

This checklist defines the minimum gates for moving Agent Foundry components from prototype to production. It is intentionally stricter than the MVP checklist.

## Runtime

- [ ] Stateful workflow execution
- [ ] Checkpoint/resume
- [ ] Retry and fallback policy
- [ ] Human approval node
- [ ] Tool call audit
- [ ] Output verification
- [ ] Evidence manager
- [ ] Safe interruption and recovery
- [ ] Idempotency handling for side effects
- [ ] Task cancellation
- [ ] Trace ID propagation

## Skills

- [ ] Skill package format
- [ ] Skill metadata
- [ ] Skill versioning
- [ ] Skill evals
- [ ] Skill owner
- [ ] Skill approval workflow
- [ ] Skill signing
- [ ] Skill deprecation policy
- [ ] Skill security review
- [ ] Skill compatibility validation

## Artifact Management

- [ ] Unified artifact registry
- [ ] Skill lifecycle commands
- [ ] Policy lifecycle commands
- [ ] Workflow lifecycle commands
- [ ] Artifact publish gates
- [ ] Artifact deprecation workflow
- [ ] Artifact version bump workflow
- [ ] Artifact impact analysis
- [ ] Artifact dependency graph
- [ ] Immutable published artifact versions
- [ ] Migration guidance for deprecated artifacts
- [ ] Historical reproducibility for sessions created with older artifact versions

## Capabilities, Tools and MCP

- [ ] Capability contract registry
- [ ] Tool provider registry
- [ ] MCP Gateway
- [ ] Tool authentication
- [ ] Tool authorization
- [ ] Tool policy enforcement
- [ ] Output sanitization
- [ ] Rate limiting
- [ ] Tool metrics
- [ ] Provider compatibility tests
- [ ] Network egress controls
- [ ] Provider health checks

## Policy and Security

- [ ] SSO/IAM
- [ ] RBAC/ABAC
- [ ] Tenant isolation
- [ ] Secret redaction
- [ ] PII redaction
- [ ] DLP controls
- [ ] Prompt injection defenses
- [ ] Skill supply-chain review
- [ ] MCP server allowlist
- [ ] SIEM integration
- [ ] Step-up authentication for critical actions
- [ ] Break-glass process

## Evidence and Evaluation

- [ ] Evidence object model
- [ ] Claim-to-evidence mapping
- [ ] Output verifier
- [ ] Skill evals
- [ ] Agent evals
- [ ] Workflow evals
- [ ] Tool trajectory evals
- [ ] Safety evals
- [ ] Policy evals
- [ ] Regression suite
- [ ] Release gates
- [ ] Online eval sampling

## Observability

- [ ] Distributed tracing
- [ ] Token/cost tracking
- [ ] Tool latency metrics
- [ ] Model latency metrics
- [ ] Approval metrics
- [ ] Eval metrics
- [ ] Audit export
- [ ] Evidence traceability
- [ ] Operational dashboards
- [ ] Alerting for failed checkpoints and policy bypass attempts

## Data and Storage

- [ ] Schema migrations
- [ ] Backup/restore
- [ ] Retention policy
- [ ] Immutable audit log
- [ ] Object storage lifecycle policy
- [ ] Encryption at rest
- [ ] Encryption in transit
- [ ] Access review for sensitive stores
- [ ] Historical artifact reproducibility

## Deployment and Operations

- [ ] Environment separation
- [ ] Configuration management
- [ ] Rollback plan
- [ ] Health checks
- [ ] Readiness/liveness probes
- [ ] Capacity plan
- [ ] Runbooks
- [ ] Incident response process
- [ ] Release notes
- [ ] Post-release monitoring

## A2A Readiness

A2A should remain disabled until:

- [ ] Single-agent runtime is stable
- [ ] MCP tool plane is stable
- [ ] Policy-before-action works
- [ ] Eval/release gate works
- [ ] Trace/audit are sufficient
- [ ] Agent identity model is implemented
- [ ] Delegation policy is implemented
- [ ] Remote result validation is implemented

## Production Go/No-Go

Production release requires:

1. No critical open security risks.
2. High risks have explicit owner and mitigation.
3. Production agents pass required eval gates.
4. Policy simulation passes.
5. Audit and trace coverage are verified.
6. Rollback procedure is tested.
7. Operations owner accepts runbooks.
8. Security owner accepts threat controls.
