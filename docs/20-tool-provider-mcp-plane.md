# Tool Provider and MCP Plane

**Audience:** Solution Architect, Platform Engineer, Integration Engineer, Security Engineer  
**Status:** Draft v1  
**Implementation phase:** Phase 8

## Purpose

The Tool Provider and MCP Plane turns capability contracts into executable, governed integrations.

Skills declare what they need through capability contracts such as `web.search@1.0` or `document.read@1.0`. Agents bind those capabilities to concrete provider tools such as `browser.search` or `knowledge-mcp.read_document`. The runtime always executes through the gateway so policy, audit, sanitization and evidence behavior remain centralized.

## Core Separation

| Layer | Owns | Does not own |
|---|---|---|
| Skill | Task instructions and required capabilities | Concrete provider names or credentials |
| Capability contract | Abstract API, risk and evidence behavior | Vendor/runtime implementation |
| Tool provider manifest | Provider identity, protocol, transport, supported capabilities and controls | Agent-specific decisions |
| Agent manifest | Capability-to-provider bindings | Provider implementation code |
| Tool gateway | Resolution, execution, sanitization, audit and dry-run behavior | Skill authoring |

## Provider Manifest

Provider manifests live in `examples/tools` for bundled examples and `.agent/registry/tools` for user-authored providers.

```yaml
apiVersion: agents.platform/v1
kind: ToolProvider
metadata:
  id: knowledge-mcp
  version: 1.0.0
  name: Knowledge MCP Provider
  owner: ai-platform-team
spec:
  protocol: mcp
  transport: stdio
  endpoint: agent-foundry-mcp-knowledge
  capabilities:
    - contract: document.read@1.0
      tool: read_document
      riskLevel: low
  tenantScope: local
  runtimeControls:
    timeoutSeconds: 30
    allowNetwork: false
  healthCheck:
    enabled: true
    mode: configuration
  outputSanitization:
    redactSecrets: true
    maxPayloadBytes: 1000000
    tagUntrusted: true
```

## Supported Provider Modes

| Protocol | Transport | Current behavior |
|---|---|---|
| `in_process` | `local` | Executes built-in local adapters for supported capabilities |
| `mcp` | `stdio` | Validates provider configuration and performs safe dry-run routing |
| `mcp` | `http` | Validates URL and explicit network egress controls |
| `http` | `http` | Validates URL and explicit network egress controls |

Phase 8 intentionally keeps external provider execution conservative. Local runs prepare and audit external calls in dry-run mode unless a concrete adapter is installed and explicitly allowed.

## CLI Workflow

List providers:

```bash
agent-foundry provider list
```

Inspect provider manifest:

```bash
agent-foundry provider inspect browser
```

Run provider health checks:

```bash
agent-foundry provider health knowledge-mcp
```

Check provider-to-capability compatibility:

```bash
agent-foundry provider compatibility knowledge-mcp --capability document.read@1.0
```

Discover providers for a capability:

```bash
agent-foundry capability providers web.search@1.0
agent-foundry capability providers document.read@1.0
```

Bind an agent capability to a provider tool:

```bash
agent-foundry agent bind-tool my-research-agent \
  --capability web.search@1.0 \
  --provider browser \
  --tool search
```

The legacy `agent-foundry tools` command group remains available for compatibility. New workflows should prefer `provider` and `capability` because they match the platform domain model more precisely.

## Health Checks

Provider health checks are local and deterministic:

1. Provider is enabled.
2. In-process providers have runtime adapters for declared capabilities.
3. External providers have an endpoint.
4. HTTP providers use a valid `http` or `https` URL.
5. HTTP providers explicitly enable network egress.
6. MCP stdio providers declare a command endpoint.
7. Live external probes are skipped unless a concrete adapter is installed.

## Compatibility Checks

Compatibility checks verify:

1. Declared capability contracts can be resolved.
2. Input and output schemas are object-shaped.
3. Provider risk classification does not silently drift from the capability contract.
4. In-process providers declare only capabilities supported by runtime adapters.

These checks are intentionally fast enough to run during local development, CI and agent publish gates.

## Runtime Behavior

Execution flow:

```text
Workflow node
-> capability reference
-> agent capability binding
-> provider manifest resolution
-> policy evaluation
-> gateway execution or dry-run preparation
-> output sanitization
-> audit event
-> evidence object when required by the capability contract
```

Built-in tools are not owned by agents. They are platform adapters exposed through provider manifests. An agent can use one only when its manifest binds a required capability to that provider tool.

## Enterprise Extension Path

Next hardening steps:

1. Live MCP stdio adapter with JSON-RPC lifecycle handling.
2. Provider credential resolution through a secret manager.
3. Provider allowlist per environment and tenant.
4. Rate limiting with persisted counters.
5. Output schema validation against capability contracts.
6. Provider health probes and circuit breaker state.
7. Network egress policy enforcement at runtime.
8. Provider contract test suite generation from capability manifests.
