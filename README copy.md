# General-Purpose Agentic AI Platform

A **skills-first, tools-first, policy-enforced, evidence-backed, eval-gated, developer-native agentic AI platform**.

Core thesis:

> An agent is a dynamically composable artifact. Agent definitions are mutable. Agent runs are immutable snapshots.

Public mental model:

```text
Agent = Instructions + Skills + Tools + Policies
```

Production model:

```text
Agent = Runtime Layer
      + Behavior Layer
      + Action Layer
      + Context Layer
      + Governance Layer
      + Quality Layer
```

This repository contains the professional project documentation package generated from the official architecture source:

- Source document: `docs/source/full-architecture-v4.5.md`
- Source SHA-256: `f51a65ef1d0770fd56ea1465766a7afa4e5b13204d94c1ebd051c0bb7ec98fdb`

## Quick start for readers

| Role | Start here |
|---|---|
| Product / Founder | [`docs/product/prd.md`](docs/product/prd.md) |
| Architect / Tech Lead | [`docs/architecture/README.md`](docs/architecture/README.md) |
| Engineer | [`docs/implementation/engineering-plan.md`](docs/implementation/engineering-plan.md) |
| Security | [`docs/security/README.md`](docs/security/README.md) |
| Platform / SRE | [`docs/operations/README.md`](docs/operations/README.md) |
| Evaluations | [`docs/evaluation/README.md`](docs/evaluation/README.md) |
| User onboarding | [`docs/getting-started/quickstart.md`](docs/getting-started/quickstart.md) |

## Project principles

```text
Skills guide.
Tools act.
Policies decide.
Hooks enforce deterministic lifecycle behavior.
Knowledge grounds.
Memory remembers.
Evidence proves.
Evals gate release.
Snapshots make runs reproducible.
Revisions make change safe.
```

## Recommended MVP

The MVP should be a thin but executable governed runtime:

```text
Generic Runtime
+ SKILL.md Loader
+ Tool Catalog
+ Policy-before-tool-call
+ Evidence
+ Audit
+ Eval Runner
+ Guidance Files
+ Simple Memory
+ Commands
+ 2 Reference Agents
```

Recommended MVP pair:

```text
Research Agent
Incident Triage Agent
```

## Repository documentation map

```text
docs/
  getting-started/       user journey and basic concepts
  product/               PRD, personas, user flows
  architecture/          system architecture split into maintainable docs
  developer-experience/  AGENTS.md, memory, commands, hooks, extensions
  mvp/                   scope, acceptance tests, roadmap
  contracts/             runtime/data contracts and JSON schemas
  security/              threat model, controls, supply-chain safety
  evaluation/            eval strategy, rubrics, release gates
  operations/            observability, storage, failure handling
  governance/            revisioning, lifecycle, releases
  implementation/        engineering plan and module boundaries
  adr/                   architecture decision records
  examples/              ready-to-copy examples
```
