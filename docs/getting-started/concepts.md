# Core Concepts

## User-facing mental model

```text
Guidance = rules and project context the agent should know
Memory = what the agent learned and may recall
Skills = reusable workflows
Commands = shortcuts to invoke workflows
Tools = what the agent can do
Policies = what the agent is allowed to do
Hooks = deterministic lifecycle enforcement
Knowledge = sources the agent can retrieve
Evidence = why the result is trustworthy
Evals = tests before publishing
```

## Minimum agent

A minimum draft agent can exist with:

```text
Profile + Purpose/Instructions + Default Runtime + Default Model Policy + Default Safety Policy
```

It behaves like a chatbot until tools and/or skills are added.

## Production agent

A production agent should include:

```text
Policies
Evidence model
Eval profile
Audit/trace
Snapshot/revisioning
Approval flow for risky tools
```
