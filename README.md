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

## Use a real LLM

By default, the runtime uses deterministic planning unless a model is configured. Set a provider API key and model to let the model propose tool calls and compose the final answer from evidence.

OpenAI or OpenAI-compatible providers:

```bash
$env:OPENAI_API_KEY="your-api-key"
$env:AGENT_FOUNDRY_PROVIDER="openai-compatible"
$env:AGENT_FOUNDRY_MODEL="gpt-4o-mini"

agent-foundry run docs/examples/agents/incident-triage-agent.yaml "Investigate checkout 5xx spike after latest deploy" --planner llm
```

Gemini:

```bash
$env:GEMINI_API_KEY="your-gemini-api-key"
$env:AGENT_FOUNDRY_PROVIDER="gemini"
$env:AGENT_FOUNDRY_MODEL="gemini-2.5-flash"

agent-foundry run docs/examples/agents/research-agent.yaml "Compare agent skills and tools-first architecture patterns." --planner llm --provider gemini
```

OpenAI-compatible gateways or local proxies:

```bash
$env:AGENT_FOUNDRY_BASE_URL="http://localhost:8000/v1"
$env:AGENT_FOUNDRY_API_KEY="local-key"
$env:AGENT_FOUNDRY_MODEL="your-model"
```

The default `--planner auto` mode uses the model when a provider is configured and falls back to deterministic planning otherwise. You can also pass `--provider openai-compatible`, `--provider openai`, or `--provider gemini` per run.

The model can only propose tool calls. Tool execution still goes through policy evaluation first, and critical actions such as `deployment.rollback` remain approval-gated.
