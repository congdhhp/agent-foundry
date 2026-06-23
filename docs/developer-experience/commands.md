# Commands / Slash Commands

## Definition

A command is a user-facing shortcut that invokes a workflow, skill, output schema, or tool trajectory.

Examples:

```text
/debug-incident
/review-pr
/write-postmortem
/security-audit
```

## Command manifest

```yaml
id: debug-incident
description: Investigate an incident using metrics, logs, deployments, and runbooks.
skill: incident-triage
workflow: incident_triage_graph
defaultTools:
  - deployments.read
  - metrics.query
  - logs.search
outputSchema: incident_report
evalProfile: incident-triage-evals
```

## Relationship to skills

```text
Command = explicit user-facing entrypoint
Skill = reusable workflow knowledge
Workflow = runtime graph
Tool = executable action
```
