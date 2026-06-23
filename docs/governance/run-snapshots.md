# Run Snapshots

Each run uses an immutable resolved snapshot.

A snapshot includes:

```text
agent revision
profile version
instructions/guidance versions
skill versions
command versions
tool versions
policy versions
hook versions
workflow version
knowledge scopes
memory index version
model policy
evidence model
eval profile
```

## Rule

```text
Changes apply to future runs by default.
Running tasks remain on their original snapshot unless explicitly paused/cancelled for security reasons.
```
