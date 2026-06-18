# Skill Package Template

## Directory

```text
skills/<skill-id>/
  SKILL.md
  skill.yaml
  capability_requirements.yaml
  output_schema.json
  evals/
    golden_cases.yaml
    safety_cases.yaml
    tool_trajectory_cases.yaml
```

## `skill.yaml`

```yaml
id: example-skill
version: 1.0.0
name: Example Skill
description: Describe what task pattern this skill solves.
owner: team-name
risk_level: low
lifecycle_status: draft

triggers:
  intents:
    - example_intent
  keywords:
    - example

requires:
  capabilities:
    - example.read@1.0

optional_capabilities: []

workflow_hints:
  default: general_reasoning_graph@1.0.0
  compatible: []
output_schema: example_output@1.0.0
```

## `SKILL.md`

```markdown
# Example Skill

## Purpose
Describe the outcome this skill helps produce.

## When to use
Use this skill when...

## When not to use
Do not use this skill when...

## Workflow
1. Clarify the task.
2. Gather required evidence.
3. Reason over observations.
4. Produce output in the required schema.

## Required capabilities
- example.read@1.0

## Evidence requirements
- Important claims must cite evidence IDs.

## Output requirements
- Include summary, evidence and confidence.

## Safety constraints
- Do not execute side effects.
- Do not expose secrets.
```
