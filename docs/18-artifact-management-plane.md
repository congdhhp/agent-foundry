# Artifact Management Plane

**Audience:** Platform Engineer, Technical Lead, Skill Author, Governance Owner, CLI Engineer
**Status:** Draft v1

## Purpose

The Artifact Management Plane turns versioned YAML and package artifacts into governed platform assets.

It owns the authoring, validation, lifecycle, versioning, publishing, deprecation and impact analysis workflows for reusable artifacts such as skills, policies and workflows.

This plane is separate from the runtime. The runtime executes resolved agent profiles; the Artifact Management Plane manages the definitions that produce those profiles.

## Scope

Initial enterprise scope:

1. Skill management.
2. Policy management.
3. Workflow management.
4. Capability contract inspection and compatibility checks.
5. Eval suite linkage for publish gates.
6. Impact analysis across agents and artifact dependencies.

Out of scope for the first implementation:

1. Marketplace monetization.
2. Distributed multi-tenant registry service.
3. Remote artifact signing service.
4. Visual workflow editor.
5. Full approval UI.

## Current MVP State

The current local-first implementation supports:

1. File-based artifact registry.
2. Agent create, inspect, validate and publish commands.
3. Skill list, inspect and validate commands.
4. Generic artifact validate and inspect commands.
5. Eval suite run, report and publish-gate commands.

The current implementation does not yet provide dedicated create, publish, deprecate, version or impact-analysis commands for skills, policies and workflows.

## Design Principle

Artifacts should be managed as immutable, versioned product assets.

```text
Draft artifact
  -> local validation
  -> compatibility analysis
  -> eval gate
  -> approval or policy gate
  -> published immutable version
  -> deprecation with migration path
```

The platform should not rely on ad hoc edits to production artifacts. File-based authoring is acceptable for local development, but publishable artifacts need explicit lifecycle gates.

## Managed Artifact Types

| Artifact | Managed as | Primary owner | Required lifecycle |
|---|---|---|---|
| Skill | Package with metadata, instructions, schemas and evals | Skill Author | draft, review, published, deprecated, archived |
| Policy | Ruleset for allow, deny, transform and approval | Governance Owner | draft, active, superseded, deprecated |
| Workflow | Runtime graph/state definition | Runtime Owner | draft, active, deprecated |
| Capability Contract | Versioned abstract API | Platform Owner | draft, active, deprecated |
| Eval Suite | Test set and pass criteria | Eval Owner | draft, active, archived |

## Skill Management

Skill management commands should support:

```bash
agent-foundry skill create <skill-id>
agent-foundry skill list
agent-foundry skill inspect <skill-ref>
agent-foundry skill validate <skill-ref-or-path>
agent-foundry skill publish <skill-ref-or-path> --eval-suite <suite>
agent-foundry skill deprecate <skill-ref> --reason "<reason>" --replacement <skill-ref>
agent-foundry skill version <skill-ref> --bump major|minor|patch
agent-foundry skill impact <skill-ref>
```

Skill publish gates:

1. Metadata schema is valid.
2. `SKILL.md` exists and passes instruction linting.
3. Required capabilities exist.
4. Referenced default workflow exists.
5. Output schema exists.
6. Golden evals pass.
7. Safety evals pass for medium or higher risk skills.
8. Existing bound agents are not broken by a new version.

## Policy Management

Policy management commands should support:

```bash
agent-foundry policy create <policy-id>
agent-foundry policy list
agent-foundry policy inspect <policy-ref>
agent-foundry policy validate <policy-ref-or-path>
agent-foundry policy simulate <policy-ref> --agent <agent> --capability <capability-ref>
agent-foundry policy publish <policy-ref-or-path>
agent-foundry policy deprecate <policy-ref> --reason "<reason>" --replacement <policy-ref>
agent-foundry policy impact <policy-ref>
```

Policy publish gates:

1. Rule schema is valid.
2. Match conditions reference valid capability, risk or context fields.
3. No critical capability is accidentally allowed without approval.
4. Deny and approval behavior is verified by policy eval cases.
5. Simulations pass for representative agents.
6. Replacement guidance exists for superseded policies.

## Workflow Management

Workflow management commands should support:

```bash
agent-foundry workflow create <workflow-id>
agent-foundry workflow list
agent-foundry workflow inspect <workflow-ref>
agent-foundry workflow validate <workflow-ref-or-path>
agent-foundry workflow publish <workflow-ref-or-path> --eval-suite <suite>
agent-foundry workflow deprecate <workflow-ref> --reason "<reason>" --replacement <workflow-ref>
agent-foundry workflow impact <workflow-ref>
```

Workflow publish gates:

1. Graph schema is valid.
2. Node IDs are unique.
3. Referenced capabilities exist.
4. Required capabilities are satisfiable by at least one provider.
5. Policy behavior is compatible with capability nodes.
6. Regression evals pass for agents that use the workflow.
7. No published agent is silently moved to an incompatible graph.

## Impact Analysis

Impact analysis answers:

1. Which agents reference this artifact?
2. Which eval suites validate those agents?
3. Which capabilities and providers are affected?
4. Which sessions were produced by the affected artifact version?
5. Is the proposed change patch, minor or major?
6. What migration path is required?

Example output:

```json
{
  "artifact": "incident-triage@1.0.0",
  "referenced_by_agents": [
    "monitoring-agent"
  ],
  "required_capabilities": [
    "deployments.read@1.0",
    "metrics.query@1.0",
    "logs.search@1.0",
    "traces.search@1.0"
  ],
  "eval_suites": [
    "monitoring-agent-evals@1.0.0"
  ],
  "recommended_version_bump": "minor",
  "migration_required": false
}
```

## Local Storage Model

Local development can remain file-first:

```text
registry-root/
  examples/
    skills/
    policies/
    workflows/
    capabilities/
    eval-suites/

.agent/
  agents/
  artifact-index/
  evals/
  sessions/
```

The `artifact-index` can be generated from the registry root and used for fast list, lookup and impact analysis.

## Enterprise Storage Model

Enterprise deployment should persist:

1. Artifact metadata in a relational registry.
2. Artifact package contents in object storage or Git.
3. Publish approvals in audit storage.
4. Eval reports in eval storage.
5. Dependency edges in an artifact graph.
6. Historical immutable versions for reproducibility.

## API Surface

Minimum REST resources:

```text
GET    /artifacts
GET    /artifacts/{kind}
GET    /artifacts/{kind}/{id}/versions
GET    /artifacts/{kind}/{id}/versions/{version}
POST   /artifacts/{kind}
POST   /artifacts/{kind}/{id}/versions/{version}/validate
POST   /artifacts/{kind}/{id}/versions/{version}/publish
POST   /artifacts/{kind}/{id}/versions/{version}/deprecate
POST   /artifacts/{kind}/{id}/versions/{version}/impact
```

Dedicated convenience resources can wrap the generic artifact API:

```text
/skills
/policies
/workflows
/capabilities
/eval-suites
```

## Release Gates

An artifact can be published only if:

1. It validates against its schema.
2. Dependencies resolve to explicit versions.
3. Required eval suites pass.
4. Impact analysis is acknowledged.
5. Security or owner approval is complete when required.
6. Immutable version policy is enforced.

## Phase 6 Implementation Plan

Phase 6 should deliver local Artifact Management Plane commands before introducing a remote registry service.

Deliverables:

1. Unified artifact listing across agents, skills, policies, workflows, capabilities, providers and eval suites.
2. Dedicated `skill`, `policy` and `workflow` command groups.
3. Create scaffolds for skill, policy and workflow artifacts.
4. Publish, deprecate and version commands for local artifacts.
5. Impact analysis for agent-to-skill, agent-to-policy and agent-to-workflow references.
6. Artifact index persisted under `.agent/artifact-index`.
7. Tests for lifecycle gates and dependency analysis.

Exit criteria:

1. A user can create a skill from the CLI, validate it and attach it to an agent.
2. A user can inspect which agents are affected before changing a skill, policy or workflow.
3. Publishing an artifact records lifecycle status and blocks unsafe changes.
4. Deprecating an artifact provides replacement guidance.
5. Existing agent publish and eval suite gates continue to pass.

## Open Decisions

1. Whether local artifact publish should mutate source YAML or write metadata overlays under `.agent/artifact-index`.
2. Whether lifecycle status should be normalized across all artifacts.
3. Whether workflow visualization should be CLI-only, Mermaid output or a UI concern.
4. Whether impact analysis should include historical sessions in the local MVP.
5. How much approval workflow belongs in CLI before an enterprise API/UI exists.
