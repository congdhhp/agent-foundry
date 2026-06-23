# Tools and Actions

## Definition

A tool is an executable action available to an agent.

Examples:

```text
web.search
document.read
file.read
file.patch
shell.run
metrics.query
logs.search
deployments.read
deployment.rollback
message.draft
message.send
```

## Public model

```text
Agent has tools.
```

## Advanced internal model

```text
Tool may declare actionType/toolContract for policy, portability, and eval.
```

## Tool quality standard

Every production tool should define:

```text
purpose
when to use
when not to use
input schema
output schema
risk level
access type
side effects
evidence behavior
examples
failure modes
policy hints
```

## Tool permissions

Tools do not become available because a skill asks for them. Tool access is granted explicitly to the agent and governed by policy.
