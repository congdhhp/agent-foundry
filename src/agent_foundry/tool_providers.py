from __future__ import annotations

import builtins
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .models import (
    AgentManifest,
    ToolProviderManifest,
    ToolProviderProtocol,
    ToolProviderTransport,
)
from .registry import LocalRegistry
from .tools import SUPPORTED_IN_PROCESS_CAPABILITIES


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


@dataclass(frozen=True)
class ProviderCapabilityMatch:
    capability: str
    provider_id: str
    provider_tool: str
    tool_name: str
    protocol: str
    transport: str
    risk_level: str


@dataclass(frozen=True)
class ProviderCheck:
    name: str
    passed: bool
    status: str
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "status": self.status,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class ProviderHealthResult:
    provider_id: str
    protocol: str
    transport: str
    healthy: bool
    status: str
    checks: list[ProviderCheck] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "protocol": self.protocol,
            "transport": self.transport,
            "healthy": self.healthy,
            "status": self.status,
            "checks": [check.to_dict() for check in self.checks],
        }


@dataclass(frozen=True)
class ProviderCompatibilityResult:
    provider_id: str
    capability: str | None
    compatible: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checked: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "capability": self.capability,
            "compatible": self.compatible,
            "errors": self.errors,
            "warnings": self.warnings,
            "checked": self.checked,
        }


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
        return self.validate()

    def validate(self, provider_id: str | None = None) -> ToolProviderValidationResult:
        errors: list[str] = []
        warnings: list[str] = []
        providers = [self.inspect(provider_id)] if provider_id else self.list_providers()
        if not providers:
            errors.append("No tool providers found")
        for provider in providers:
            compatibility = self.compatibility(provider.metadata.id)
            errors.extend(compatibility.errors)
            warnings.extend(compatibility.warnings)
            health = self.health(provider.metadata.id)
            for check in health.checks:
                if not check.passed and check.status != "skipped":
                    errors.append(
                        f"{provider.metadata.id} failed {check.name}: {check.detail}"
                    )
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

    def providers_for_capability(
        self,
        capability_ref: str,
    ) -> list[ProviderCapabilityMatch]:
        matches: list[ProviderCapabilityMatch] = []
        self.registry.load_capability(capability_ref)
        for provider in self.list_providers():
            for capability in provider.spec.capabilities:
                if capability.contract != capability_ref:
                    continue
                matches.append(
                    ProviderCapabilityMatch(
                        capability=capability_ref,
                        provider_id=provider.metadata.id,
                        provider_tool=f"{provider.metadata.id}.{capability.tool}",
                        tool_name=capability.tool,
                        protocol=provider.spec.protocol.value,
                        transport=provider.spec.transport.value,
                        risk_level=capability.risk_level.value,
                    )
                )
        return matches

    def compatibility(
        self,
        provider_id: str,
        capability_ref: str | None = None,
    ) -> ProviderCompatibilityResult:
        provider = self.inspect(provider_id)
        errors: list[str] = []
        warnings: list[str] = []
        checked: list[dict[str, Any]] = []
        capabilities = [
            capability
            for capability in provider.spec.capabilities
            if capability_ref is None or capability.contract == capability_ref
        ]
        if capability_ref is not None and not capabilities:
            errors.append(f"Provider does not declare capability: {capability_ref}")
        for capability in capabilities:
            try:
                contract = self.registry.load_capability(capability.contract)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"Capability cannot be resolved: {capability.contract}: {exc}")
                continue
            input_schema_type = contract.spec.input_schema.get("type")
            output_schema_type = contract.spec.output_schema.get("type")
            if input_schema_type != "object":
                warnings.append(
                    f"{capability.contract} input schema is not an object: "
                    f"{input_schema_type}"
                )
            if output_schema_type != "object":
                warnings.append(
                    f"{capability.contract} output schema is not an object: "
                    f"{output_schema_type}"
                )
            if contract.spec.risk_level != capability.risk_level:
                warnings.append(
                    f"Risk mismatch for {provider.metadata.id}.{capability.tool}: "
                    f"provider={capability.risk_level.value}, "
                    f"contract={contract.spec.risk_level.value}"
                )
            capability_id = capability.contract.split("@", 1)[0]
            if (
                provider.spec.protocol == ToolProviderProtocol.IN_PROCESS
                and capability_id not in SUPPORTED_IN_PROCESS_CAPABILITIES
            ):
                errors.append(
                    f"No in-process adapter registered for capability {capability_id}"
                )
            checked.append(
                {
                    "capability": capability.contract,
                    "provider_tool": f"{provider.metadata.id}.{capability.tool}",
                    "access_type": contract.spec.access_type.value,
                    "contract_risk_level": contract.spec.risk_level.value,
                    "provider_risk_level": capability.risk_level.value,
                    "input_schema_type": input_schema_type,
                    "output_schema_type": output_schema_type,
                }
            )
        return ProviderCompatibilityResult(
            provider_id=provider.metadata.id,
            capability=capability_ref,
            compatible=not errors,
            errors=errors,
            warnings=warnings,
            checked=checked,
        )

    def health(self, provider_id: str) -> ProviderHealthResult:
        provider = self.inspect(provider_id)
        checks = [
            ProviderCheck(
                name="enabled",
                passed=provider.spec.enabled,
                status="passed" if provider.spec.enabled else "failed",
                detail="Provider is enabled."
                if provider.spec.enabled
                else "Provider is disabled in manifest.",
            )
        ]
        if provider.spec.protocol == ToolProviderProtocol.IN_PROCESS:
            unsupported = [
                capability.contract.split("@", 1)[0]
                for capability in provider.spec.capabilities
                if capability.contract.split("@", 1)[0]
                not in SUPPORTED_IN_PROCESS_CAPABILITIES
            ]
            checks.append(
                ProviderCheck(
                    name="in_process_adapter",
                    passed=not unsupported,
                    status="passed" if not unsupported else "failed",
                    detail="All declared capabilities have in-process adapters."
                    if not unsupported
                    else f"Missing adapters: {', '.join(sorted(unsupported))}",
                )
            )
        else:
            checks.extend(self._external_provider_checks(provider))
        healthy = all(check.passed for check in checks if check.status != "skipped")
        return ProviderHealthResult(
            provider_id=provider.metadata.id,
            protocol=provider.spec.protocol.value,
            transport=provider.spec.transport.value,
            healthy=healthy,
            status="healthy" if healthy else "unhealthy",
            checks=checks,
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

    def _external_provider_checks(
        self,
        provider: ToolProviderManifest,
    ) -> builtins.list[ProviderCheck]:
        checks: builtins.list[ProviderCheck] = []
        endpoint = provider.spec.endpoint or ""
        checks.append(
            ProviderCheck(
                name="endpoint_configured",
                passed=bool(endpoint),
                status="passed" if endpoint else "failed",
                detail=f"Endpoint is configured: {endpoint}"
                if endpoint
                else "Endpoint is required for external providers.",
            )
        )
        if provider.spec.transport == ToolProviderTransport.HTTP:
            parsed = urlparse(endpoint)
            valid_url = parsed.scheme in {"http", "https"} and bool(parsed.netloc)
            checks.append(
                ProviderCheck(
                    name="http_endpoint",
                    passed=valid_url,
                    status="passed" if valid_url else "failed",
                    detail="HTTP endpoint is valid."
                    if valid_url
                    else "HTTP transport requires an http(s) URL endpoint.",
                )
            )
            network_allowed = provider.spec.runtime_controls.allow_network
            checks.append(
                ProviderCheck(
                    name="network_egress",
                    passed=network_allowed,
                    status="passed" if network_allowed else "failed",
                    detail="Network egress is explicitly allowed."
                    if network_allowed
                    else "Network egress must be explicitly enabled for HTTP transport.",
                )
            )
        if (
            provider.spec.protocol == ToolProviderProtocol.MCP
            and provider.spec.transport == ToolProviderTransport.STDIO
        ):
            checks.append(
                ProviderCheck(
                    name="mcp_stdio_command",
                    passed=bool(endpoint.strip()),
                    status="passed" if endpoint.strip() else "failed",
                    detail="MCP stdio command is configured."
                    if endpoint.strip()
                    else "MCP stdio transport requires a command endpoint.",
                )
            )
        checks.append(
            ProviderCheck(
                name="live_probe",
                passed=True,
                status="skipped",
                detail=(
                    "Live external provider probes are not executed by the local "
                    "Phase 8 CLI unless a concrete adapter is installed."
                ),
            )
        )
        return checks
