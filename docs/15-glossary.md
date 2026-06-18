# Glossary

**Audience:** All contributors  
**Status:** Draft v1

## Terms

| Term | Definition |
|---|---|
| Agent | A composed runtime instance with identity, goal, skills, tools, policy, workflow, memory, knowledge and eval profile |
| Agent Template | Reusable blueprint for creating agent instances |
| Agent Instance | Concrete configured agent created from a template and manifest |
| Agent Manifest | Versioned configuration that defines an agent's skills, tools, policies, workflow and scopes |
| A2A | Agent-to-Agent protocol/plane for delegating work to independent remote agents |
| Approval | Structured human decision required before executing a risky action |
| Artifact | Versioned object such as agent, skill, capability, policy, workflow or eval |
| Artifact Management Plane | Control-plane capability for creating, validating, publishing, versioning, deprecating and impact-analyzing artifacts |
| Audit Event | Append-only security/compliance event |
| Capability Contract | Versioned abstract API required by skills and implemented by providers |
| Capability Binding | Mapping from capability contract to provider/tool implementation |
| Checkpoint | Durable runtime state snapshot used for resume/retry |
| Control Plane | Registry, validation, versioning, publishing, governance and eval layer |
| Evidence | Traceable object supporting a claim, observation or recommendation |
| Eval | Test that checks skill, workflow, policy, tool trajectory, safety or output quality |
| Execution Plane | Runtime layer that executes tasks, calls tools/models and persists state |
| HITL | Human-in-the-loop approval or review step |
| Knowledge Scope | Authorized retrieval scope such as runbooks, docs, tickets or code |
| MCP | Model Context Protocol, used as tool/context integration boundary |
| Memory Scope | Controlled retention scope for session, task, user, agent, team or domain memory |
| Model Gateway | Central layer for model routing, redaction, cost, caching and trace |
| Policy | Rules that decide whether actions are allowed, denied, transformed or require approval |
| Provider | Concrete tool implementation for one or more capability contracts |
| Runtime | Generic execution engine for workflows and tasks |
| Skill | Versioned package of operational knowledge, required capabilities, safety rules, examples and evals |
| Tool Plane | Capability resolution, provider routing, tool execution and sanitization layer |
| Workflow | Inspectable graph or state machine for task execution |

## Decision Vocabulary

| Term | Meaning |
|---|---|
| `ALLOW` | Execute action immediately |
| `REQUIRE_APPROVAL` | Pause and request human approval |
| `DENY` | Do not execute action |
| `REQUIRE_TRANSFORM` | Transform input/output before proceeding |
| `REQUIRE_STEP_UP_AUTH` | Require stronger authentication before proceeding |

## Risk Vocabulary

| Risk level | Meaning |
|---|---|
| Low | Read-only or low-impact action |
| Medium | Sensitive read or bounded internal write |
| High | External side effect or important internal mutation |
| Critical | Production, financial, destructive or regulated action |

## Claim Vocabulary

| Claim type | Meaning |
|---|---|
| Fact | Directly supported by source |
| Observation | Derived from retrieved/tool data |
| Hypothesis | Plausible but not fully proven |
| Verified conclusion | Supported by sufficient evidence |
| Recommendation | Suggested next action with risk/policy context |
| Assumption | Explicitly stated uncertain premise |
