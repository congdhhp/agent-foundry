# Quickstart

## Create a draft agent

```bash
agent create my-agent
```

A draft agent has:

```text
runtime
profile
purpose/instructions
default model policy
default safety policy
```

It may have no skills, no tools, no knowledge, no memory, no evals yet.

## Add tools

```bash
agent tools add my-agent web.search
agent tools add my-agent document.read
agent tools add my-agent logs.search
```

Risky tools should automatically receive safe defaults:

```text
read tools -> allow with audit
write tools -> approval by default
execute tools -> sandbox + approval
critical tools -> approval or deny
```

## Add skills

```bash
agent skills import github:org/repo/skills/incident-triage --agent my-agent --trust untrusted
```

Imported third-party skills are untrusted by default.

## Run

```bash
agent run my-agent "Investigate checkout 5xx spike after latest deploy"
```

## Inspect evidence and trace

```bash
agent trace show task_123
agent evidence show task_123
```

## Run evals

```bash
agent eval run my-agent
```

## Publish

```bash
agent publish my-agent --revision rev-005
```
