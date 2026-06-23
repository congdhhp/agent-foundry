# Module Boundaries

Recommended structure:

```text
packages/
  core/
  runtime/
  context/
  guidance/
  memory/
  skills/
  commands/
  tools/
  policy/
  hooks/
  evidence/
  evals/
  revisions/
  cli/
  storage/
```

## Dependency rules

```text
core has no vendor dependencies
runtime depends on core/context/policy/tools/evidence
policy is called before tools
evidence depends on tool/retrieval outputs, not model assertions only
evals must run in CI
```
