# Extension Manifest Schema

```yaml
id: string
version: string
source: string
contents:
  skills: string[]
  commands: string[]
  tools: string[]
  policies: string[]
  evals: string[]
  hooks: string[]
trust:
  level: untrusted | reviewed | team-approved | signed | blocked
  commitPinned: boolean
  checksumVerified: boolean
  reviewedBy: optional string
```
