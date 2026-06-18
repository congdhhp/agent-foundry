# Reference Agents

**Audience:** Product Owner, Skill Author, Solution Architect, Applied AI Engineer  
**Status:** Draft v1

## Purpose

Reference agents demonstrate how Agent Foundry composes specialized agents from the same generic runtime.

Each reference agent defines:

1. Purpose.
2. Skills.
3. Capability bindings.
4. Policy posture.
5. Workflow.
6. Output expectations.
7. Eval focus.

## Research Agent

Purpose:

```text
Research topics, compare sources and produce cited reports.
```

Manifest sketch:

```yaml
agent:
  id: research-agent
  name: Research Agent
  template: generic-task-agent@1.0.0
  purpose: Research topics, compare sources and produce cited reports.

skills:
  - web-research@1.0.0
  - source-evaluation@1.0.0
  - summarization@1.0.0
  - citation-analysis@1.0.0
  - report-writing@1.0.0

capabilityBindings:
  web.search@1.0: browser.search
  web.fetch@1.0: browser.fetch
  document.read@1.0: document.read
  citation.extract@1.0: citation.extract

policy:
  default_mode: read_only
  denied:
    - external_post@1.0
    - payment.execute@1.0
    - account.change@1.0
```

Eval focus:

1. Select research skills correctly.
2. Use relevant sources.
3. Cite claims.
4. Avoid unsupported factual conclusions.
5. Avoid side-effecting actions.

## Coding Agent

Purpose:

```text
Modify code safely and verify with tests.
```

Manifest sketch:

```yaml
agent:
  id: coding-agent
  name: Coding Agent
  template: generic-task-agent@1.0.0
  purpose: Modify code safely and verify with tests.

skills:
  - codebase-understanding@1.0.0
  - bug-fixing@1.0.0
  - refactoring@1.0.0
  - test-generation@1.0.0
  - code-review@1.0.0
  - pull-request-drafting@1.0.0

capabilityBindings:
  file.read@1.0: workspace.read_file
  file.patch@1.0: workspace.apply_patch
  code.search@1.0: workspace.search_symbols
  shell.run@1.0: sandbox.run_command
  git.diff@1.0: git.diff
  pr.create@1.0: github.create_pr

policy:
  default_mode: workspace_write
  approval_required:
    - dependency.install@1.0
    - network.access@1.0
    - git.push@1.0
    - pr.create@1.0
    - destructive_command@1.0
```

Eval focus:

1. Read relevant code before editing.
2. Apply scoped patches.
3. Run appropriate tests.
4. Avoid destructive commands.
5. Summarize changes and residual risks.

## Monitoring Agent

Purpose:

```text
Investigate production alerts and incidents.
```

Manifest sketch:

```yaml
agent:
  id: monitoring-agent
  name: Monitoring Agent
  template: generic-task-agent@1.0.0
  purpose: Investigate production alerts and incidents.

skills:
  - alert-triage@1.0.0
  - metrics-analysis@1.1.0
  - log-analysis@1.2.0
  - trace-analysis@1.0.0
  - deployment-correlation@1.0.0
  - runbook-execution@1.0.0
  - incident-communication@1.0.0
  - postmortem-writing@1.0.0

capabilityBindings:
  metrics.query@1.0: prometheus.query
  logs.search@1.0: elasticsearch.search
  traces.search@1.0: jaeger.search
  deployments.read@1.0: github_deployments.read
  incident.read@1.0: pagerduty.read
  message.draft@1.0: slack.draft

policy:
  default_mode: read_only
  approval_required:
    - service.restart@1.0
    - deployment.rollback@1.0
    - incident.resolve@1.0
    - message.send@1.0
```

Eval focus:

1. Collect metrics, logs, traces and deployments.
2. Correlate timeline.
3. Separate facts from hypotheses.
4. Require evidence for root-cause claims.
5. Require approval for remediation.

## Support Agent

Purpose:

```text
Analyze customer cases and draft safe, policy-compliant responses.
```

Manifest sketch:

```yaml
agent:
  id: refund-support-agent
  name: Refund Support Agent
  template: generic-task-agent@1.0.0
  purpose: Analyze refund requests and draft customer responses.

skills:
  - ticket-analysis@1.0.0
  - refund-policy-analysis@1.0.0
  - customer-tone-writing@1.0.0
  - crm-update@1.0.0
  - email-drafting@1.0.0

capabilityBindings:
  ticket.read@1.0: zendesk.read_ticket
  payment.read@1.0: stripe.read_payment
  policy.search@1.0: kb.search
  email.draft@1.0: gmail.create_draft
  crm.update@1.0: salesforce.update_case

policy:
  default_mode: draft_only
  approval_required:
    - payment.refund@1.0
    - email.send@1.0
    - crm.update@1.0
```

Eval focus:

1. Read relevant ticket/customer policy.
2. Avoid direct refund execution without approval.
3. Produce customer-safe tone.
4. Avoid leaking internal policy notes.
5. Draft, not send, external communication by default.

## Security Agent

Purpose:

```text
Review code, configs, dependencies and runtime evidence for security risks.
```

Manifest sketch:

```yaml
agent:
  id: security-review-agent
  name: Security Review Agent
  template: generic-task-agent@1.0.0
  purpose: Review code, configs, dependencies and runtime evidence for security risks.

skills:
  - threat-modeling@1.0.0
  - code-security-review@1.0.0
  - dependency-risk-analysis@1.0.0
  - config-review@1.0.0
  - vulnerability-triage@1.0.0

capabilityBindings:
  repo.read@1.0: github.read_repo
  dependency.scan@1.0: scanner.scan_dependencies
  config.read@1.0: workspace.read_config
  cve.search@1.0: vuln_db.search
  ticket.create@1.0: jira.create_issue

policy:
  default_mode: read_mostly
  approval_required:
    - ticket.create@1.0
    - pr.comment@1.0
    - security_exception.create@1.0
```

Eval focus:

1. Identify real security risks.
2. Avoid unsupported vulnerability claims.
3. Use severity and confidence consistently.
4. Require evidence for findings.
5. Require approval for issue/comment creation.

## Reference Agent Comparison

| Agent | Primary proof point | Risk level |
|---|---|---|
| Research | Evidence and citation | Low |
| Coding | Workspace write and tests | Medium |
| Monitoring | Production investigation and approval | Medium to high |
| Support | Customer data and external draft safety | Medium to high |
| Security | Evidence-backed risk analysis | Medium |

