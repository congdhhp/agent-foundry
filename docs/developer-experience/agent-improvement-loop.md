# Agent Improvement Loop

## Goal

Continuously improve agents using traces, human feedback, evals, and revisioning.

## Loop

```text
Run agent
-> collect traces
-> label failures
-> convert failures to eval cases
-> update guidance/skills/tools/policies/hooks
-> run regression evals
-> create new revision
-> promote if release gates pass
```

## Failure labels

```text
wrong skill selected
wrong tool used
policy failed
missing evidence
unsafe output
memory stale
context missing
hook failed
latency/cost too high
```
