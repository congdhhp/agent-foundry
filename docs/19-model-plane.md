# Model Plane

**Audience:** Runtime Engineer, Platform Engineer, AI Engineer, Security Engineer
**Status:** Draft v1

## Purpose

The Model Plane turns workflow reasoning and output composition nodes into governed model calls.

It owns model policy resolution, provider selection, prompt/context composition, model-call audit events and deterministic dry-run behavior for local tests and evals.

## Current Implementation

Phase 7 provides:

1. `ModelPolicy` artifact schema.
2. `default-model-policy@1.0.0` example artifact.
3. `ModelGateway` abstraction.
4. Deterministic local provider for tests, evals and dry-run execution.
5. Optional OpenAI-compatible provider through `OPENAI_API_KEY`.
6. Runtime integration for `llm_reasoning`, `evaluator` and `output_composer` workflow nodes.
7. Model events in task audit logs.
8. CLI model options for `agent-foundry run`.
9. Retry count, fallback model list and output token budget controls.

## Model Policy Artifact

```yaml
apiVersion: agents.platform/v1
kind: ModelPolicy
metadata:
  id: default-model-policy
  version: 1.0.0
spec:
  defaultProvider: deterministic
  defaultModel: deterministic-local
  allowedProviders:
    - deterministic
    - openai
  allowedModels:
    - deterministic-local
    - gpt-4.1-mini
  fallbackModels:
    - deterministic-local
  maxPromptChars: 12000
  maxOutputTokens: 2048
  temperature: 0.2
  timeoutSeconds: 30
  retryCount: 1
  redactSecrets: true
```

## Provider Behavior

| Provider | Purpose |
|---|---|
| `deterministic` | Local deterministic model output for tests, evals and offline development |
| `openai` | Optional real model call using OpenAI-compatible chat completions |

Model calls are deterministic by default. A real provider is used only when the CLI passes `--allow-model-calls`.

## Runtime Flow

```text
workflow node
  -> model policy resolution
  -> prompt composition
  -> model.called event
  -> provider execution
  -> model.completed or model.failed event
  -> observation appended to runtime state
  -> checkpoint
```

`output_composer` stores its model output as the final response summary when the task completes.

## CLI

Run with deterministic local model behavior:

```bash
agent-foundry run examples/agents/research-agent.yaml \
  "Research capability contracts" \
  --model-provider deterministic \
  --model deterministic-local
```

Run with a real provider:

```bash
set OPENAI_API_KEY=<key>

agent-foundry run examples/agents/research-agent.yaml \
  "Research capability contracts" \
  --model-provider openai \
  --model gpt-4.1-mini \
  --allow-model-calls
```

## Audit Events

Runtime emits:

```text
model.called
model.completed
model.failed
```

`model.called` includes node ID, node type, provider, model, prompt size and dry-run status.

`model.completed` includes provider, model, input token count, output token count, optional cost and output size.

## Safety Rules

1. Default execution must not call external model providers.
2. Real model calls require explicit `--allow-model-calls`.
3. Model provider and model must be allowed by the selected model policy.
4. Prompt text is bounded by `maxPromptChars`.
5. Secret-like values are redacted before model execution when enabled by policy.
6. Tool execution remains controlled by capability bindings and policy-before-action.

## Future Work

1. Native Responses API provider.
2. Streaming support.
3. Cost calculation by model.
4. Circuit breaker policy.
5. Prompt template registry.
6. Structured output validation against skill output schemas.
7. Tenant-aware model routing and data residency constraints.
