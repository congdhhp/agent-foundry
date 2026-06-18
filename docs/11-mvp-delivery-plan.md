# MVP Delivery Plan

**Audience:** Founder, CTO, Product Owner, Technical Lead, Engineering Team  
**Status:** Draft v1

## MVP Thesis

The MVP must prove:

> Multiple agents from different domains can run on the same generic runtime, policy engine and capability abstraction, differing only by skills, workflows, tool bindings and policies.

## MVP Scope

Included:

1. Universal CLI.
2. Agent manifest loader.
3. Skill loader.
4. Capability registry.
5. Tool binding resolver.
6. Policy engine v0.
7. Generic runtime.
8. Local state/checkpoint store.
9. Audit event log.
10. Evidence object model.
11. Minimal eval runner.
12. Two reference agents.

Excluded:

1. A2A gateway.
2. Marketplace.
3. Advanced memory.
4. Full enterprise multi-tenancy.
5. Complex approval console.
6. Multi-model optimizer.
7. Knowledge graph.
8. Async distributed agents.

## Recommended Reference Agents

### Agent 1: Research Agent

Why:

1. Low risk.
2. Shows skill selection.
3. Shows knowledge/retrieval path.
4. Requires citations/evidence.
5. Useful demo for many stakeholders.

Capabilities:

1. `web.search@1.0`.
2. `web.fetch@1.0`.
3. `document.read@1.0`.
4. `citation.extract@1.0`.

### Agent 2: Coding Agent or Incident Triage Agent

Choose Coding Agent if the first market is developer productivity.

Choose Incident Triage Agent if the first market is enterprise/SRE.

Coding Agent proves:

1. Workspace capabilities.
2. Patch application.
3. Shell/test execution.
4. Approval/denial for risky commands.

Incident Triage Agent proves:

1. Observability capabilities.
2. Evidence-heavy reasoning.
3. Production policy.
4. Approval for remediation.

## Milestones

### M0: Repository and Documentation Foundation

Deliverables:

1. Documentation structure.
2. Architecture decision baseline.
3. Manifest templates.
4. Engineering standards.

Exit criteria:

1. New engineer can explain platform thesis.
2. MVP scope is explicit.
3. Required artifact types are documented.

### M1: Artifact Schemas and Local Registry

Deliverables:

1. Agent manifest schema.
2. Skill manifest schema.
3. Capability contract schema.
4. Policy schema.
5. Local registry loader.

Exit criteria:

1. CLI validates a sample agent.
2. Missing capability binding fails validation.
3. Deprecated skill fails publication validation.

### M2: Generic Runtime Skeleton

Deliverables:

1. Task state model.
2. Workflow executor.
3. Skill selection.
4. Local checkpointing.
5. Structured events.

Exit criteria:

1. Runtime executes a simple workflow.
2. State can be resumed from checkpoint.
3. Events are written to task session directory.

### M3: Capability Executor and Policy Engine

Deliverables:

1. Capability binding resolver.
2. Tool executor interface.
3. Policy engine v0.
4. Approval object.
5. Evidence manager v0.

Exit criteria:

1. Allowed read capability executes.
2. Denied capability is blocked.
3. Approval-required capability pauses task.
4. Tool result creates evidence.

### M4: Reference Agent 1 - Research

Deliverables:

1. Research skill package.
2. Research workflow.
3. Search/fetch/document capability adapters.
4. Citation/evidence output.
5. Research eval cases.

Exit criteria:

1. Research task produces cited output.
2. Unsupported claims fail verification.
3. Eval runner catches missing citation.

### M5: Reference Agent 2 - Coding or Incident

Deliverables:

1. Second agent manifest.
2. Domain skills.
3. Domain workflow.
4. At least three capability calls.
5. Policy side-effect test.

Exit criteria:

1. Same runtime executes both agents.
2. Capabilities and policies differ by manifest.
3. Side-effect action is denied or requires approval.

### M6: MVP Hardening

Deliverables:

1. Documentation cleanup.
2. Error handling.
3. Eval report.
4. Demo scripts.
5. Release checklist.

Exit criteria:

1. MVP success criteria pass.
2. Demo flow is repeatable.
3. Known risks and gaps are documented.

## MVP Success Criteria

1. Create agent from manifest.
2. Load skill package.
3. Validate capability bindings.
4. Execute stateful workflow.
5. Invoke at least three capabilities through tool executor.
6. Policy can block or require approval for side-effect action.
7. Output includes evidence IDs.
8. Audit events are written.
9. Eval runner checks skill activation and tool trajectory.
10. Two agents use the same runtime with different skills, tools and policies.

## Team Workstreams

| Workstream | Owner profile | Main outputs |
|---|---|---|
| Runtime | Senior backend/runtime engineer | State, workflow, checkpoint, execution loop |
| Artifacts | Platform engineer | Schemas, registry, validation |
| Tool plane | Integration engineer | Capability resolver, adapters, policy hooks |
| Policy/security | Security engineer | Policy engine, approvals, redaction, audit |
| Eval | AI/eval engineer | Golden cases, trajectory checks, reports |
| Reference agents | Applied AI engineer | Skills, workflows, demos |
| DevEx | CLI engineer | CLI commands, local storage, inspect/debug UX |

## Delivery Risks

| Risk | Mitigation |
|---|---|
| Runtime becomes domain-specific | Require capability and workflow abstraction in code review |
| Policy is postponed | Implement policy v0 before reference agents |
| Evals arrive too late | Add eval runner before second reference agent |
| Tool adapters leak provider specifics into skills | Use capability contract review gate |
| Scope expands to enterprise UI | Keep MVP CLI-first |

## Definition of Done

For an MVP feature:

1. Code implemented.
2. Schema or contract updated if applicable.
3. Unit tests added.
4. Eval case added for agentic behavior when applicable.
5. Audit event emitted for security-relevant action.
6. Documentation updated.
7. Demo path validated.

