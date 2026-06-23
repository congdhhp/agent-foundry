# User Flows

## Create blank agent

```text
Create agent
-> Pick blank
-> Enter purpose
-> Save as Draft
```

## Import GitHub skill

```text
Search skills
-> Inspect SKILL.md
-> Scan files/scripts
-> Pin commit
-> Import as untrusted
-> Run eval
-> Promote trust level
```

## Add risky tool

```text
Add tool
-> Display risk
-> Attach default policy
-> Require approval/sandbox
-> Save new revision
```

## Promote production revision

```text
Create draft revision
-> Validate manifests
-> Run evals
-> Security review if needed
-> Owner approval
-> Promote revision
-> New runs use promoted snapshot
```
