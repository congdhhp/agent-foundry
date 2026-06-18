from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .models import AgentManifest, ToolProviderManifest
from .registry import LocalRegistry


@dataclass(frozen=True)
class ToolProviderValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AgentToolBinding:
    capability: str
    provider_tool: str
    provider_id: str
    tool_name: str
    valid: bool
    error: str | None = None


class ToolProviderRegistry:
    def __init__(
        self,
        root: str | Path = ".",
        store_root: str | Path | None = None,
    ) -> None:
        self.registry = LocalRegistry(root, store_root)

    def list_providers(self) -> list[ToolProviderManifest]:
        return self.registry.list_tool_providers()

    def inspect(self, provider_id: str) -> ToolProviderManifest:
        return self.registry.load_tool_provider(provider_id)

    def validate_all(self) -> ToolProviderValidationResult:
        errors: list[str] = []
        warnings: list[str] = []
        providers = self.list_providers()
        if not providers:
            errors.append("No tool providers found")
        for provider in providers:
            if not provider.spec.capabilities:
                warnings.append(f"Provider has no capabilities: {provider.metadata.id}")
            for capability in provider.spec.capabilities:
                try:
                    contract = self.registry.load_capability(capability.contract)
                except Exception as exc:  # noqa: BLE001
                    errors.append(
                        f"{provider.metadata.id}.{capability.tool} references missing "
                        f"contract {capability.contract}: {exc}"
                    )
                    continue
                if contract.spec.risk_level.value != capability.risk_level.value:
                    warnings.append(
                        f"Risk mismatch for {provider.metadata.id}.{capability.tool}: "
                        f"provider={capability.risk_level.value}, "
                        f"contract={contract.spec.risk_level.value}"
                    )
        return ToolProviderValidationResult(
            valid=not errors,
            errors=errors,
            warnings=warnings,
        )

    def bindings_for_agent(self, agent: AgentManifest) -> list[AgentToolBinding]:
        bindings: list[AgentToolBinding] = []
        for capability_ref, provider_tool in sorted(agent.spec.capability_bindings.items()):
            provider_id, tool_name = self._split_provider_tool(provider_tool)
            try:
                self.registry.resolve_provider_tool(capability_ref, provider_tool)
                bindings.append(
                    AgentToolBinding(
                        capability=capability_ref,
                        provider_tool=provider_tool,
                        provider_id=provider_id,
                        tool_name=tool_name,
                        valid=True,
                    )
                )
            except Exception as exc:  # noqa: BLE001
                bindings.append(
                    AgentToolBinding(
                        capability=capability_ref,
                        provider_tool=provider_tool,
                        provider_id=provider_id,
                        tool_name=tool_name,
                        valid=False,
                        error=str(exc),
                    )
                )
        return bindings

    def _split_provider_tool(self, provider_tool: str) -> tuple[str, str]:
        if "." not in provider_tool:
            return provider_tool, ""
        provider_id, tool_name = provider_tool.split(".", 1)
        return provider_id, tool_name

    def list(self) -> list[ToolProviderManifest]:
        return self.list_providers()
