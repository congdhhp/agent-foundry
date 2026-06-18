# Agent Foundry

Agent Foundry is a skill-centric, policy-aware, tool-agnostic platform for building governed AI agents.

The core thesis:

> Agent is a composition artifact, not a bespoke implementation class.

Instead of creating separate implementations such as `CodingAgent`, `MonitoringAgent` or `SupportAgent`, Agent Foundry composes agents from versioned artifacts:

```text
Agent = Runtime
      + Identity
      + Goal
      + Skills
      + Capability Bindings
      + Tool Providers
      + Knowledge Scopes
      + Memory Scopes
      + Policy
      + Workflow
      + Model Policy
      + Eval Profile
```

## What This Project Is

Agent Foundry is designed to become an enterprise-grade foundation for composing specialized AI agents across domains such as:

- Research
- Coding
- Monitoring and incident triage
- Customer support
- Security review
- Data analysis

The platform emphasizes:

1. Skill-centric composition.
2. Capability contracts over direct tool coupling.
3. Runtime-enforced policy before action.
4. Evidence-backed outputs.
5. Eval-first release gates.
6. Local-first execution with an enterprise-ready path.

## Documentation

The project documentation lives in [docs/](./docs/README.md).

Recommended starting points:

- [Executive Overview](./docs/00-executive-overview.md)
- [Product Requirements](./docs/01-product-requirements.md)
- [Architecture Overview](./docs/02-architecture-overview.md)
- [MVP Delivery Plan](./docs/11-mvp-delivery-plan.md)
- [Engineering Standards](./docs/13-engineering-standards.md)

The original architecture blueprint is available at:

- [General-Purpose AI Agent Platform Architecture](./general_purpose_agent_platform_architecture.md)

## MVP Direction

The MVP should prove that multiple agents from different domains can run on the same generic runtime, policy engine and capability abstraction.

MVP includes:

- Universal CLI
- Agent manifest loader
- Skill loader
- Capability registry
- Tool binding resolver
- Policy engine v0
- Generic runtime
- Local state and audit event store
- Evidence object model
- Minimal eval runner
- Two reference agents

Recommended first reference agents:

1. Research Agent
2. Coding Agent or Incident Triage Agent

## Repository Status

This repository currently contains the architecture blueprint and enterprise-grade documentation baseline. Implementation should proceed from the MVP delivery plan and artifact templates under [docs/templates/](./docs/templates/).
