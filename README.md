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

This repository currently contains the architecture blueprint, enterprise-grade documentation baseline and implementation through Phase 6 local artifact management plane.

## Developer Quickstart

Install locally:

```bash
python -m pip install -e .[dev]
```

Validate example artifacts:

```bash
agent-foundry validate examples/agents/research-agent.yaml
agent-foundry validate examples/capabilities/web.search.yaml
agent-foundry validate examples/policies/read-only.yaml
```

Run a local Phase 1 task:

```bash
agent-foundry run examples/agents/research-agent.yaml "Compare capability contracts with direct tool binding."
```

Inspect local sessions and task data:

```bash
agent-foundry sessions
agent-foundry show <task_id> events
agent-foundry show <task_id> evidence
```

Use Phase 2 composition commands:

```bash
agent-foundry skills list
agent-foundry skills validate examples/skills/web-research
agent-foundry agent validate examples/agents/research-agent.yaml
agent-foundry eval run examples/evals/research_basic.yaml --agent examples/agents/research-agent.yaml
agent-foundry eval run-suite examples/eval-suites/research-agent-evals.yaml --agent examples/agents/research-agent.yaml
agent-foundry eval reports
agent-foundry eval show <run_id>
agent-foundry tools list
agent-foundry tools validate
agent-foundry tools bindings examples/agents/research-agent.yaml
```

Use Phase 6 artifact management commands:

```bash
agent-foundry artifacts list
agent-foundry skill create my-research-skill --capability web.search@1.0 --workflow research_graph@1.0.0
agent-foundry skill validate my-research-skill@1.0.0
agent-foundry skill impact web-research@1.0.0
agent-foundry policy simulate read-only@1.0.0 --capability web.search@1.0
agent-foundry workflow impact research_graph@1.0.0
```

Create and publish a local agent:

```bash
agent-foundry agent create my-research-agent \
  --name "My Research Agent" \
  --purpose "Research topics with citations" \
  --skill web-research@1.0.0 \
  --policy read-only@1.0.0 \
  --workflow research_graph@1.0.0

agent-foundry agent inspect my-research-agent
agent-foundry agent publish my-research-agent --eval-suite examples/eval-suites/research-agent-evals.yaml
agent-foundry run .agent/agents/my-research-agent.yaml "Research capability contracts"
```

Inspect an artifact:

```bash
agent-foundry inspect examples/agents/research-agent.yaml
```

Export generated JSON Schemas:

```bash
agent-foundry schemas export --output schemas
```

Run tests:

```bash
python -m pytest
```
