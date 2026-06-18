# Incident Triage Skill

## Purpose

Investigate alerts, production errors, latency spikes and suspected regressions with evidence.

## When to use

Use this skill when a user asks to investigate an incident, alert, outage, latency spike or error-rate increase.

## Workflow

1. Clarify incident scope.
2. Collect deployment history.
3. Query metrics.
4. Search logs.
5. Search traces.
6. Correlate timeline.
7. Separate facts from hypotheses.
8. Produce next safe actions.

## Required capabilities

- metrics.query@1.0
- logs.search@1.0
- traces.search@1.0
- deployments.read@1.0

## Evidence requirements

- Root-cause claims require evidence.
- Recommendations must include risk and confidence.

## Safety constraints

- Do not execute remediation.
- Do not expose secrets from logs.
- Do not send external incident updates without approval.

