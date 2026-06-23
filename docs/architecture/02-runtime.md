# Runtime Architecture

## Responsibilities

The generic runtime:

- Receives task input.
- Loads resolved agent snapshot.
- Selects skills/commands.
- Resolves context.
- Plans actions.
- Proposes tool calls.
- Sends proposed tool calls to policy.
- Executes allowed tools.
- Runs hooks.
- Creates evidence.
- Verifies output.
- Records trace/audit.
- Supports checkpoint/resume.

## Execution flow

```text
ReceiveTask
-> ResolveAgentSnapshot
-> ResolveContext
-> SelectCommandOrSkill
-> Plan
-> ProposeToolCall
-> PolicyCheck
-> RunPreToolHooks
-> ExecuteTool
-> RunPostToolHooks
-> CreateEvidence
-> Verify
-> ComposeAnswer
-> PersistTrace
```

## Runtime invariant

```text
The runtime never executes tools directly from model output.
The runtime executes only approved tool calls after policy evaluation.
```
