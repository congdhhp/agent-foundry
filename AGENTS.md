# AGENTS.md

This repository describes a General-Purpose Agentic AI Platform.

## How agents should work in this repository

When working on this repository:

1. Prefer clear architecture decisions over vague abstractions.
2. Keep the public user mental model simple.
3. Do not reintroduce `Capability` as a public concept.
4. Treat tools as the public action primitive.
5. Treat skills as lightweight `SKILL.md` workflow packages.
6. Keep production safety explicit: policy, evidence, audit, eval, snapshots.
7. Preserve the principle: agent definitions are mutable, agent runs are immutable snapshots.
8. Keep MVP executable and thin; avoid building the whole enterprise platform first.

## Preferred terminology

```text
Guidance = persistent project/user/team context and rules
Memory = what the agent learned and may recall
Skills = reusable task workflows
Commands = user-facing workflow entrypoints
Tools = actions the agent can invoke
Policies = rules that decide whether actions are allowed
Hooks = deterministic lifecycle enforcement
Knowledge = sources the agent may retrieve
Evidence = proof used to support claims
Eval = tests before publish/production
```

## Documentation standards

- Write docs in Markdown.
- Use short sections and explicit examples.
- Prefer YAML/JSON examples for contracts.
- Keep MVP and post-MVP clearly separated.
- Include safety implications for tools, skills, memory, hooks, and extensions.

## Verification before changes

Before considering documentation complete, check:

- Architecture terminology is consistent.
- Public model remains simple.
- Production model remains layered.
- Security invariants are preserved.
- MVP remains executable.
- Examples align with contracts.
