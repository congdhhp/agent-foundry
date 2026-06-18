# Engineering Standards

**Audience:** Engineering Team, Technical Lead, Staff Engineer  
**Status:** Draft v1

## Engineering Principles

1. Keep runtime generic.
2. Put domain behavior in skills, workflows and capability bindings.
3. Treat manifests and contracts as public APIs.
4. Enforce policy in code, not only in prompts.
5. Create audit events for security-relevant behavior.
6. Make evidence and evals part of feature delivery.
7. Prefer small executable vertical slices over broad unfinished frameworks.

## Repository Structure Target

Recommended future structure:

```text
agent-foundry/
  README.md
  docs/
  src/
    agent_foundry/
      cli/
      control_plane/
      runtime/
      skills/
      capabilities/
      tools/
      policies/
      evidence/
      evals/
      storage/
      observability/
  examples/
    agents/
    skills/
    capabilities/
    policies/
    evals/
  tests/
    unit/
    integration/
    evals/
  scripts/
```

## Coding Standards

1. Domain-neutral runtime modules must not import domain-specific skills.
2. Capability executor must not bypass policy engine.
3. Tool provider adapters must validate input/output schemas.
4. Audit events must be structured and stable.
5. Exceptions must include task ID and trace ID where available.
6. Public artifact schemas must have version fields.
7. Configuration must be explicit and inspectable.
8. Secret values must never be logged or passed to model context.

## Runtime Code Boundaries

| Module | Allowed responsibility | Must not do |
|---|---|---|
| `runtime` | Execute workflows, manage state, route actions | Hard-code domain tools |
| `skills` | Load and select skill metadata/instructions | Execute external tools directly |
| `capabilities` | Validate contracts and resolve bindings | Contain provider credentials |
| `tools` | Provider adapters and MCP calls | Make policy decisions alone |
| `policies` | Evaluate action decisions | Execute tools |
| `evidence` | Create and index evidence | Invent unsupported claims |
| `evals` | Run test cases and gates | Change runtime behavior |
| `storage` | Persist state, audit, artifacts | Interpret model/tool semantics |

## Testing Strategy

| Test layer | What to test |
|---|---|
| Unit tests | Schema parsing, policy decisions, resolver logic, evidence creation |
| Contract tests | Capability provider compatibility |
| Integration tests | Runtime plus tool adapters plus storage |
| Workflow tests | Graph transitions and checkpoint/resume |
| Eval tests | Skill activation, tool trajectory, safety and grounding |
| Security tests | Injection controls, redaction, deny rules |
| Regression tests | Previously passing skills/agents still pass |

## Required Tests by Change Type

| Change | Required tests |
|---|---|
| New skill | Skill activation, safety, output schema, tool trajectory if applicable |
| New capability | Schema validation, compatibility, risk classification |
| New provider | Contract test, auth failure, output sanitization, audit |
| New policy rule | Policy simulation, approval routing, regression |
| Runtime change | Unit, workflow, checkpoint and integration tests |
| Evidence change | Evidence schema, claim mapping, verifier tests |
| CLI change | CLI command tests and local storage compatibility |

## Code Review Checklist

1. Does the change preserve runtime neutrality?
2. Are capability contracts used instead of concrete tools?
3. Are tool calls policy-checked?
4. Are new side effects risk-classified?
5. Are secrets excluded from prompts/logs/evidence?
6. Are audit events emitted?
7. Are evidence requirements clear?
8. Are tests/evals updated?
9. Are docs/templates updated when contracts change?
10. Is the change scoped to the requested behavior?

## Release Process

Recommended release stages:

1. Merge to main after tests and review.
2. Run full contract and eval suite.
3. Generate release notes with changed artifacts.
4. Validate migration and rollback.
5. Promote to staging.
6. Run smoke tasks for reference agents.
7. Approve production promotion.
8. Monitor online evals and operational metrics.

## Artifact Compatibility Policy

1. Published artifact versions are immutable.
2. Breaking changes require new major version.
3. Agents pin versions by default.
4. Deprecations include migration guidance.
5. Runtime must be able to inspect historical task traces with historical artifact versions.

## Logging Standards

Every structured log should include when available:

1. `trace_id`.
2. `task_id`.
3. `agent_id`.
4. `tenant_id`.
5. `event_type`.
6. `component`.
7. `severity`.

Do not log:

1. Raw secrets.
2. Unredacted regulated PII.
3. Full raw tool payloads unless explicitly retained by policy.
4. Credentials, API keys or tokens.

## Documentation Standards

1. New concepts require docs.
2. New artifact types require templates.
3. New capability contracts require examples.
4. New risk behavior requires security docs and risk register updates.
5. Architecture decisions should be captured as ADRs or updates to the architecture blueprint.

## Definition of Ready

A feature is ready for engineering when:

1. User/problem statement is clear.
2. Affected artifact types are known.
3. Capability and policy implications are identified.
4. Acceptance criteria are documented.
5. Test/eval expectations are defined.

## Definition of Done

A feature is done when:

1. Implementation is complete.
2. Tests pass.
3. Evals pass if agentic behavior changed.
4. Audit/evidence behavior is correct.
5. Documentation is updated.
6. Operational impact is understood.
7. Security review is complete for high-risk changes.

