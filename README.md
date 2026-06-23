# agent-foundry

A skill-centric, policy-aware, tool-agnostic platform for building governed AI agents.

This repo now contains both the architecture documentation and a thin executable MVP runtime.

## MVP runtime

The first implementation slice is Python-based:

```text
Pydantic contracts
Typer CLI
Rich terminal output
Local .agent runtime storage
Policy-gated mock tool execution
Evidence and trace JSONL
Eval runner
Lightweight interactive terminal console
```

LangGraph is intentionally kept as a runtime adapter boundary. The domain contracts, policy engine, evidence model, eval runner, and local storage do not depend on LangGraph.

## Try it

```bash
python -m pip install -e .

python -m pytest

agent-foundry agent inspect docs/examples/agents/incident-triage-agent.yaml

agent-foundry agent create my-agent --purpose "Help with local tasks."

agent-foundry run docs/examples/agents/incident-triage-agent.yaml "Investigate checkout 5xx spike after latest deploy"

agent-foundry eval run docs/examples/agents/incident-triage-agent.yaml docs/examples/evals/incident-triage-eval.yaml

agent-foundry tui
```

Generated run state is written under `.agent/` and is ignored by git.
