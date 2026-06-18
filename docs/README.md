# Agent Foundry Documentation

**Status:** Draft v1  
**Last updated:** 2026-06-18  
**Primary source:** [general_purpose_agent_platform_architecture.md](../general_purpose_agent_platform_architecture.md)

Agent Foundry is a skill-centric, policy-aware, tool-agnostic platform for composing governed AI agents. The core thesis is:

> Agent is a composition artifact, not a bespoke implementation class.

This documentation set turns the architecture blueprint into an enterprise-grade project documentation baseline for product, architecture, engineering, security, operations and delivery.

## Reading Paths

| Audience | Recommended path |
|---|---|
| Founder / CTO / Product Owner | [Executive Overview](./00-executive-overview.md), [Product Requirements](./01-product-requirements.md), [MVP Delivery Plan](./11-mvp-delivery-plan.md) |
| Solution Architect / Technical Lead | [Architecture Overview](./02-architecture-overview.md), [Domain and Manifest Model](./03-domain-and-manifest-model.md), [Runtime and Workflow](./06-runtime-workflow.md), [Model Plane](./19-model-plane.md) |
| Senior / Staff Engineer | [Skill System](./04-skill-system.md), [Capability and Tool Plane](./05-capability-tool-plane.md), [Artifact Management Plane](./18-artifact-management-plane.md), [API, CLI and Storage](./09-api-cli-storage.md), [Engineering Standards](./13-engineering-standards.md) |
| Security / Governance | [Policy, Security and Governance](./07-policy-security-governance.md), [Evidence, Evaluation and Observability](./08-evidence-evaluation-observability.md), [Risk Register](./14-risk-register.md) |
| Platform / SRE | [Deployment and Operations](./10-deployment-operations.md), [API, CLI and Storage](./09-api-cli-storage.md), [Risk Register](./14-risk-register.md) |

## Documentation Map

| Document | Purpose |
|---|---|
| [00 Executive Overview](./00-executive-overview.md) | Product thesis, value proposition, differentiation and strategic scope |
| [01 Product Requirements](./01-product-requirements.md) | Personas, use cases, functional and non-functional requirements |
| [02 Architecture Overview](./02-architecture-overview.md) | System architecture, planes, major components and invariants |
| [03 Domain and Manifest Model](./03-domain-and-manifest-model.md) | Core entities, manifests, validation rules and lifecycle |
| [04 Skill System](./04-skill-system.md) | Skill package model, lifecycle, selection and authoring standards |
| [05 Capability and Tool Plane](./05-capability-tool-plane.md) | Capability contracts, MCP gateway, provider binding and tool execution |
| [06 Runtime and Workflow](./06-runtime-workflow.md) | Generic runtime, LangGraph workflow, state, checkpoints and HITL |
| [07 Policy, Security and Governance](./07-policy-security-governance.md) | Policy-before-action, IAM, threat controls and approvals |
| [08 Evidence, Evaluation and Observability](./08-evidence-evaluation-observability.md) | Evidence model, verification, eval gates, audit and telemetry |
| [09 API, CLI and Storage](./09-api-cli-storage.md) | CLI commands, REST API, storage model and artifact layout |
| [10 Deployment and Operations](./10-deployment-operations.md) | Local, enterprise and Kubernetes deployment, runbooks and SLOs |
| [11 MVP Delivery Plan](./11-mvp-delivery-plan.md) | MVP scope, milestones, acceptance criteria and delivery sequence |
| [12 Reference Agents](./12-reference-agents.md) | Research, coding, monitoring, support and security agent templates |
| [13 Engineering Standards](./13-engineering-standards.md) | Repository standards, implementation principles, testing and release quality |
| [14 Risk Register](./14-risk-register.md) | Enterprise risk register with mitigations and ownership |
| [15 Glossary](./15-glossary.md) | Shared vocabulary for product and engineering |
| [16 Architecture Decisions](./16-architecture-decisions.md) | ADR summary and consequences |
| [17 Production Readiness Checklist](./17-production-readiness-checklist.md) | Release readiness gates for runtime, skills, tools, policy and operations |
| [18 Artifact Management Plane](./18-artifact-management-plane.md) | Enterprise-grade lifecycle, versioning, publishing and impact analysis for skills, policies and workflows |
| [19 Model Plane](./19-model-plane.md) | Model policy, provider abstraction, prompt composition and runtime model events |

## Templates

| Template | Purpose |
|---|---|
| [Agent manifest](./templates/agent-manifest.template.yaml) | Starting point for a new agent instance |
| [Skill package](./templates/skill-package.template.md) | Required contents for a skill package |
| [Capability contract](./templates/capability-contract.template.yaml) | Versioned API contract for tool-agnostic capabilities |
| [Policy](./templates/policy.template.yaml) | Policy profile with allow, approval, transform and deny rules |
| [Eval case](./templates/eval-case.template.yaml) | Golden/safety/tool-trajectory eval case schema |

## Documentation Principles

1. Keep the runtime domain-neutral.
2. Treat skills, capabilities, policies and workflows as versioned artifacts.
3. Define behavior through contracts, not vendor-specific tool names.
4. Require policy evaluation before tool execution.
5. Require evidence for factual, operational and high-impact claims.
6. Use evals as release gates, not optional reports.
7. Keep MVP executable-first and enterprise-ready, but not enterprise-heavy.
