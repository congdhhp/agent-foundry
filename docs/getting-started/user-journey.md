# User Journey

## Happy path

```text
Create draft agent
-> Add tools
-> Import skills
-> Add guidance files
-> Add knowledge scopes
-> Configure policies
-> Run test task
-> Inspect evidence and trace
-> Run evals
-> Promote revision
-> Publish
```

## UI wizard

Recommended wizard:

1. Choose agent type or blank agent.
2. Define purpose.
3. Select skills.
4. Select tools.
5. Choose sandbox/permission mode.
6. Configure policies.
7. Connect knowledge.
8. Add commands.
9. Run test.
10. Run eval.
11. Publish.

## Important UX principle

Users should not need to understand runtime internals to create an agent.

The platform should explain:

```text
Skills tell the agent how to work.
Tools tell the agent what it can do.
Policies decide what is safe.
Evidence shows why the answer is trustworthy.
Evals decide whether the agent is ready.
```
