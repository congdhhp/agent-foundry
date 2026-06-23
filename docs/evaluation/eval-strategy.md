# Eval Strategy

## MVP eval types

```text
skill selection eval
tool trajectory eval
policy behavior eval
evidence presence eval
output schema eval
basic safety eval
context resolution eval
memory safety eval
hook behavior eval
snapshot integrity eval
```

## Regression loop

```text
trace failure
-> label failure
-> create eval case
-> fix guidance/skill/tool/policy/hook
-> run regression eval
-> promote new revision
```
