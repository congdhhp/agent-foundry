# Third-Party Skill Import

## Principle

Third-party skills from GitHub or public registries are untrusted by default.

## Import flow

```text
Discover
-> Fetch
-> Inspect
-> Static scan
-> Semantic review
-> Permission/tool compatibility analysis
-> Sandbox decision
-> Add as untrusted
-> Run eval
-> Promote to trusted
```

## Required metadata

```yaml
skillTrust:
  source: github
  repo: org/repo
  path: skills/incident-triage
  commit: abc123
  checksum: sha256:...
  trustLevel: untrusted
  scriptsEnabled: false
  reviewedBy: null
```

## Rule

```text
Skills can suggest tools.
Skills cannot grant themselves tool access.
```
