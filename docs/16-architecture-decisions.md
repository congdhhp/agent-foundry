# Architecture Decisions

**Audience:** CTO, Solution Architect, Technical Lead, Staff Engineer  
**Status:** Draft v1  
**Source:** Architecture blueprint ADR section

## Purpose

This document summarizes the major architecture decisions that should guide implementation and review. Detailed rationale lives in the architecture blueprint; this file provides a working index for engineering execution.

## ADR-001: Agent Is a Composition Artifact

**Decision:** Represent an agent as a composition of template, skills, tools, policies, workflows, model policy, memory scopes and eval profile.

**Rationale:** Avoid domain-specific agent class explosion and maximize reuse.

**Consequences:**

1. Strong manifests and validators are required.
2. Runtime must remain domain-neutral.
3. New domains should add skills/workflows/bindings, not new runtime branches.

## ADR-002: Skills Are First-Class Packages

**Decision:** A skill is a versioned package with `SKILL.md`, metadata, workflow hints, policy hints, capability requirements, examples and evals.

**Rationale:** Prompt-only skills are not governable enough for enterprise use.

**Consequences:**

1. Skill lifecycle management is required.
2. Security review and evals become part of skill publication.
3. Agents should pin skill versions.

## ADR-003: Use Capability Contracts for Tools

**Decision:** Skills depend on abstract capability contracts, not concrete provider tools.

**Rationale:** Allow portability between providers such as Prometheus/Datadog, Elasticsearch/Splunk or Jira/ServiceNow.

**Consequences:**

1. Capability registry is required.
2. Tool providers must pass compatibility tests.
3. Contracts must define semantics, not only names.

## ADR-004: Use MCP for Tool and Context Integration

**Decision:** MCP Gateway is the standard path for external tools, data and local resources.

**Rationale:** Standardized discovery and invocation boundaries reduce integration sprawl.

**Consequences:**

1. MCP security, auth, audit and sanitization are mandatory.
2. Runtime should not call vendor SDKs directly.
3. Provider failure behavior must be observable.

## ADR-005: Use A2A Only for Agent Delegation

**Decision:** A2A is for independent remote/specialist agents, not simple tool calls.

**Rationale:** Prevent unnecessary multi-agent complexity.

**Consequences:**

1. MCP remains the default tool path.
2. A2A requires agent identity, delegation policy and result validation.
3. A2A is not part of MVP.

## ADR-006: Use LangGraph for Stateful Workflow Orchestration

**Decision:** Use LangGraph, or an equivalent graph runtime, as the first workflow orchestration kernel.

**Rationale:** Agent tasks require stateful execution, checkpointing, HITL and resumability.

**Consequences:**

1. Workflow definitions need state schemas.
2. Nodes must be inspectable and auditable.
3. Runtime state must be compatible with checkpoint/resume.

## ADR-007: Policy Before Action

**Decision:** Every proposed action is policy-checked before execution.

**Rationale:** Agentic systems can create side effects; safety must be enforced at runtime.

**Consequences:**

1. Tool execution has additional policy latency.
2. Approval handling is a runtime primitive.
3. Tests must cover allow, deny, transform and approval paths.

## ADR-008: Separate Control Plane From Execution Runtime

**Decision:** Registries, validation, publishing and evals belong to the control plane; runtime receives resolved artifacts.

**Rationale:** Reduces coupling between governance and runtime implementation.

**Consequences:**

1. Artifact resolution layer is required.
2. Runtime should not load arbitrary production skill files directly.
3. Local MVP may combine services physically but should preserve logical boundaries.

## ADR-009: Evidence Is First-Class

**Decision:** Evidence objects are core runtime primitives.

**Rationale:** Incident, support, research, security and finance workflows require grounded claims and auditability.

**Consequences:**

1. Tool and retrieval results must create evidence IDs.
2. Final outputs should map claims to evidence.
3. Verification and evals must check grounding.

## ADR-010: A2A Is Not Part of MVP

**Decision:** Do not build A2A in the MVP.

**Rationale:** Single-agent runtime, MCP tool plane, policy and eval must be stable first.

**Consequences:**

1. MVP complexity is lower.
2. Multi-agent delegation is deferred.
3. Architecture should still reserve the collaboration plane boundary.

## Decision Review Policy

Review an ADR when:

1. Runtime starts accumulating domain-specific logic.
2. Skills require direct provider names.
3. Policy enforcement is bypassed.
4. Evidence is optional for high-impact claims.
5. A2A is proposed before MVP success criteria are met.
6. New artifact types are introduced.

