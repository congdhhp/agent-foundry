from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from .models import AgentManifest, ModelPolicyManifest


SECRET_RE = re.compile(
    r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*['\"]?[^'\"\s]+"
)


@dataclass(frozen=True)
class ModelRequest:
    task_id: str
    agent_id: str
    node_id: str
    node_type: str
    provider: str
    model: str
    prompt: str
    temperature: float
    timeout_seconds: int
    dry_run: bool


@dataclass(frozen=True)
class ModelResponse:
    provider: str
    model: str
    content: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float | None = None
    raw: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "content": self.content,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cost_usd": self.cost_usd,
        }


class DeterministicModelProvider:
    provider = "deterministic"

    def generate(self, request: ModelRequest) -> ModelResponse:
        if request.node_type == "output_composer":
            content = (
                f"Final response for task {request.task_id}: "
                f"composed by {request.model} from governed runtime context."
            )
        else:
            content = (
                f"Model output for {request.node_type} node '{request.node_id}' "
                f"on task {request.task_id}."
            )
        return ModelResponse(
            provider=request.provider,
            model=request.model,
            content=content,
            input_tokens=self._estimate_tokens(request.prompt),
            output_tokens=self._estimate_tokens(content),
            raw={"deterministic": True},
        )

    def _estimate_tokens(self, text: str) -> int:
        return max(1, len(text.split()))


class OpenAIChatModelProvider:
    provider = "openai"

    def generate(self, request: ModelRequest) -> ModelResponse:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required for openai model provider")

        payload = {
            "model": request.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an enterprise AI agent runtime component.",
                },
                {"role": "user", "content": request.prompt},
            ],
            "temperature": request.temperature,
        }
        body = json.dumps(payload).encode("utf-8")
        http_request = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(  # noqa: S310 - URL is fixed OpenAI API endpoint
                http_request,
                timeout=request.timeout_seconds,
            ) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise ValueError(f"OpenAI model call failed: {exc.code} {detail}") from exc
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return ModelResponse(
            provider=request.provider,
            model=request.model,
            content=content,
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            raw=data,
        )


class ModelGateway:
    def __init__(
        self,
        provider_override: str | None = None,
        model_override: str | None = None,
        allow_model_calls: bool = False,
    ) -> None:
        self.provider_override = provider_override
        self.model_override = model_override
        self.allow_model_calls = allow_model_calls
        self.providers = {
            "deterministic": DeterministicModelProvider(),
            "openai": OpenAIChatModelProvider(),
        }

    def build_request(
        self,
        agent: AgentManifest,
        model_policy: ModelPolicyManifest,
        state: dict[str, Any],
        node_id: str,
        node_type: str,
        node_config: dict[str, Any] | None = None,
    ) -> ModelRequest:
        provider = self.provider_override or model_policy.spec.default_provider
        model = self.model_override or model_policy.spec.default_model
        if not self.allow_model_calls:
            provider = "deterministic"
            model = "deterministic-local"
        self._validate_policy(provider, model, model_policy)
        prompt = self.compose_prompt(agent, model_policy, state, node_id, node_type, node_config or {})
        return ModelRequest(
            task_id=state["task_id"],
            agent_id=agent.metadata.id,
            node_id=node_id,
            node_type=node_type,
            provider=provider,
            model=model,
            prompt=prompt,
            temperature=model_policy.spec.temperature,
            timeout_seconds=model_policy.spec.timeout_seconds,
            dry_run=not self.allow_model_calls,
        )

    def generate(self, request: ModelRequest) -> ModelResponse:
        provider = self.providers.get(request.provider)
        if provider is None:
            raise ValueError(f"Unsupported model provider: {request.provider}")
        return provider.generate(request)

    def compose_prompt(
        self,
        agent: AgentManifest,
        model_policy: ModelPolicyManifest,
        state: dict[str, Any],
        node_id: str,
        node_type: str,
        node_config: dict[str, Any],
    ) -> str:
        skill_context = [
            {
                "skill": item["skill"],
                "required_capabilities": item["required_capabilities"],
                "instructions": item["instructions"],
            }
            for item in state.get("skill_context", [])
        ]
        prompt_data = {
            "agent": {
                "id": agent.metadata.id,
                "purpose": agent.spec.purpose,
                "policy": agent.spec.policy,
                "workflow": agent.spec.workflow,
            },
            "node": {
                "id": node_id,
                "type": node_type,
                "config": node_config,
            },
            "task": state["input"],
            "selected_skills": state.get("selected_skills", []),
            "skill_context": skill_context,
            "observations": state.get("observations", []),
            "evidence": state.get("evidence", []),
            "tool_outputs": state.get("tool_outputs", []),
            "approvals": state.get("approvals", []),
        }
        prompt = json.dumps(prompt_data, indent=2, sort_keys=True, default=str)
        if model_policy.spec.redact_secrets:
            prompt = SECRET_RE.sub(r"\1=[REDACTED]", prompt)
        return prompt[: model_policy.spec.max_prompt_chars]

    def _validate_policy(
        self, provider: str, model: str, model_policy: ModelPolicyManifest
    ) -> None:
        allowed_providers = model_policy.spec.allowed_providers
        if allowed_providers and provider not in allowed_providers:
            raise ValueError(
                f"Model provider {provider} is not allowed by {model_policy.metadata.id}"
            )
        allowed_models = model_policy.spec.allowed_models
        if allowed_models and model not in allowed_models:
            raise ValueError(
                f"Model {model} is not allowed by {model_policy.metadata.id}"
            )
