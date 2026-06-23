# Extension Security

Extensions may contain executable hooks, MCP servers, tools, policies, commands, and skills.

## Install requirements

```text
inspect manifest
pin version/commit
verify checksum if available
scan scripts and hooks
mark untrusted by default
run evals before promotion
require review for production
```

## Trust levels

```text
untrusted
reviewed
team-approved
signed
blocked
```
