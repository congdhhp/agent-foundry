# Product Requirements

**Audience:** Product Owner, CTO, Solution Architect, Technical Lead  
**Status:** Draft v1  
**Scope:** Platform requirements for MVP and enterprise evolution

## Product Goal

Enable teams to create, govern, evaluate and operate specialized AI agents by composing reusable skills, capability contracts, tool providers, policies, workflows, knowledge scopes, memory scopes and model policies.

## Problem Statement

Organizations want AI agents for many domains, but most implementations suffer from:

1. Domain-specific agent code that cannot be reused.
2. Tool integrations tightly coupled to prompts and workflows.
3. Inconsistent approval and safety behavior.
4. Poor auditability of decisions and tool calls.
5. Weak release quality because evals are not first-class.
6. Difficulty moving from local prototypes to enterprise operations.

## Product Principles

1. Manifest-driven composition over custom implementation classes.
2. Skill packages over prompt snippets.
3. Capability contracts over direct vendor tools.
4. Policy-before-action over prompt-level safety.
5. Evidence over assertion.
6. Eval-first release over ad hoc testing.
7. Local-first usability with enterprise-grade architecture.

## Personas and Jobs To Be Done

| Persona | Job to be done | Success signal |
|---|---|---|
| AI Platform Engineer | Define platform runtime, registries and integrations | New agents can be created from manifests |
| Skill Author | Package reusable operational knowledge | Skill is validated, evaluated and published |
| Agent Owner | Configure a specialist agent safely | Agent passes validation and eval gates |
| End User | Ask an agent to perform a task | Receives useful, grounded, policy-compliant output |
| Approver | Review risky proposed actions | Approval request includes risk, reason and evidence |
| Security Engineer | Review supply chain and execution behavior | Tools, skills and outputs are auditable |
| SRE / Operator | Operate runtime and investigate failures | Trace, audit and checkpoint data are available |

## Primary Use Cases

### UC-01: Create an Agent From Manifest

An agent owner defines an agent manifest with skills, capability bindings, policy, workflow and model policy. The platform validates the manifest and creates an agent instance.

Acceptance criteria:

1. Required fields are validated.
2. Skill versions exist and are not deprecated.
3. Required capabilities are bound to compatible providers.
4. Effective policy can be resolved.
5. Eval profile is attached or explicitly waived for non-production.

### UC-02: Run a Research Task

A user runs a read-only research task. The agent selects research skills, retrieves sources, produces cited output and maps major claims to evidence.

Acceptance criteria:

1. Agent selects appropriate skills.
2. Retrieval creates evidence objects.
3. Final output contains citations/evidence references.
4. No side-effecting capability is invoked.
5. Audit log records model calls, retrieval and final answer.

### UC-03: Run a Coding Task

A user asks a coding agent to modify a repository. The agent reads files, plans changes, applies patches and runs tests within workspace policy.

Acceptance criteria:

1. File reads and patches go through capability bindings.
2. Shell commands are risk-classified.
3. Destructive commands are denied or require approval.
4. Final response includes changed files, test results and residual risks.
5. Audit log includes patch and command events.

### UC-04: Triage an Incident

An SRE asks an incident agent to investigate latency or error spikes. The agent collects metrics, logs, traces and deployments, then separates facts from hypotheses.

Acceptance criteria:

1. Metrics/logs/traces/deployments are collected through capabilities.
2. Sensitive log content is redacted according to policy.
3. Root-cause claims require evidence.
4. Remediation actions require approval.
5. Incident report artifact is generated.

### UC-05: Approve a Risky Action

An agent proposes a high-risk action such as sending a message, creating a ticket, rolling back a deployment or issuing a refund.

Acceptance criteria:

1. Runtime pauses before execution.
2. Approval object includes action, risk, reason and evidence refs.
3. Only authorized approvers can approve.
4. Rejection sends the agent back to replanning.
5. Audit records approval decision.

### UC-06: Publish a Skill

A skill author submits a skill package. The control plane validates metadata, capabilities, security constraints and eval results before publication.

Acceptance criteria:

1. Skill manifest and required files are present.
2. Required capabilities exist.
3. Static and semantic checks pass.
4. Safety and golden evals pass.
5. Owner approval is recorded.

## Functional Requirements

| ID | Requirement | Priority |
|---|---|---|
| FR-001 | Load and validate agent manifests | MVP |
| FR-002 | Load skill packages with metadata and instructions | MVP |
| FR-003 | Validate capability bindings against contracts | MVP |
| FR-004 | Resolve tool providers from capability contracts | MVP |
| FR-005 | Execute generic stateful workflow | MVP |
| FR-006 | Enforce policy before every tool call | MVP |
| FR-007 | Support human approval for risky actions | MVP |
| FR-008 | Create evidence objects from retrieval/tool results | MVP |
| FR-009 | Emit audit events for task lifecycle | MVP |
| FR-010 | Run minimal evals for skill activation and tool trajectory | MVP |
| FR-011 | Provide universal CLI for create/run/inspect/eval | MVP |
| FR-012 | Expose REST API for agent/task operations | Post-MVP |
| FR-013 | Support MCP gateway and provider registry | Post-MVP |
| FR-014 | Support enterprise IAM and tenant isolation | Enterprise |
| FR-015 | Support A2A delegation | Enterprise |

## Non-Functional Requirements

| Category | Requirement |
|---|---|
| Security | Least privilege by default; raw secrets never enter model context |
| Reliability | Runtime supports checkpoint/resume for long-running tasks |
| Auditability | Tool calls, approvals, policy decisions and outputs are auditable |
| Portability | Skills depend on capability contracts, not provider-specific tools |
| Maintainability | Domain logic stays in skills/workflows, not runtime conditionals |
| Extensibility | New capabilities and providers can be registered without modifying skills |
| Observability | Each task has trace ID, structured events, cost and latency metrics |
| Compliance | Sensitive outputs can be redacted and evidence can be retained by policy |

## MVP In Scope

1. Local-first CLI.
2. Manifest and local registry.
3. Skill loader.
4. Capability contract loader.
5. Tool binding resolver.
6. Policy engine v0.
7. Generic runtime with a small set of workflow templates.
8. Local state, audit and evidence files.
9. Minimal eval runner.
10. Two reference agents.

## MVP Out of Scope

1. Public marketplace.
2. Full web console.
3. Full multi-tenant SaaS billing.
4. Advanced long-term memory.
5. Knowledge graph.
6. Complex visual workflow designer.
7. A2A orchestration.
8. Full enterprise approval console.

## Release Criteria

The MVP release is acceptable when:

1. Two agents run on the same generic runtime.
2. At least three capabilities are invoked through the binding resolver.
3. Policy can allow, deny and require approval.
4. Evidence IDs appear in final output.
5. Audit events are written for task, model, tool, policy and output events.
6. Eval runner can fail a bad skill/tool trajectory.
7. Documentation and templates are sufficient for a new engineer to add a basic skill.

