# Extensions

## Definition

An extension is an installable bundle of reusable agent artifacts.

An extension may include:

```text
skills/
commands/
tools/
mcp-servers/
policies/
evals/
hooks/
templates/
```

## Example manifest

```yaml
id: sre-agent-pack
version: 1.0.0
source: github:company/sre-agent-pack
contents:
  skills:
    - incident-triage
    - postmortem-writing
  commands:
    - debug-incident
    - write-postmortem
  tools:
    - metrics.query
    - logs.search
  policies:
    - production-read-mostly
  evals:
    - incident-triage-evals
trust:
  level: untrusted
  commitPinned: true
  checksumVerified: false
```

## Install flow

```text
fetch
inspect
scan
pin version
install as untrusted
run eval
review
promote trust
```
