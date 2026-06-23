# Product Requirements Document

## Product name

General-Purpose Agentic AI Platform

## Product statement

A governed platform for composing production-grade AI agents from reusable guidance, skills, tools, policies, memory, knowledge, evidence, evals, commands, hooks, and extensions.

## Core value proposition

Teams can start with a simple draft agent and progressively add capabilities safely, while preserving production governance and reproducibility.

## Primary users

1. Developers building local/team agents.
2. Platform engineers managing tools and policies.
3. Security teams reviewing skills, tools, memory, and extensions.
4. SRE teams building incident triage agents.
5. Product/ops teams building research/support agents.

## MVP objective

Prove that at least two agents from different domains can run on the same generic runtime while differing only in composition artifacts.

## MVP reference agents

```text
Research Agent
Incident Triage Agent
```

## Success metrics

- Agent can be created from manifest.
- `SKILL.md` can be loaded and selected.
- Tool calls are policy-checked.
- Side effects require approval.
- Evidence exists for important claims.
- Eval runner gates promotion.
- Runs are tied to immutable snapshots.
- Two reference agents share the same runtime.
