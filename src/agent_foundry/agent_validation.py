from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .models import PolicyDecision
from .policy import PolicyEngine
from .registry import LocalRegistry


@dataclass(frozen=True)
class AgentValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class AgentDeepValidator:
    def __init__(
        self,
        root: str | Path = ".",
        store_root: str | Path | None = None,
    ) -> None:
        self.registry = LocalRegistry(root, store_root)
        self.policy_engine = PolicyEngine()

    def validate(self, agent_path_or_ref: str | Path) -> AgentValidationResult:
        errors: list[str] = []
        warnings: list[str] = []
        try:
            agent = self.registry.load_agent(agent_path_or_ref)
        except Exception as exc:  # noqa: BLE001
            return AgentValidationResult(valid=False, errors=[str(exc)])

        try:
            policy = self.registry.load_policy(agent.spec.policy)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Policy cannot be resolved: {exc}")
            policy = None

        try:
            self.registry.load_workflow(agent.spec.workflow)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Workflow cannot be resolved: {exc}")

        if agent.spec.model_policy is not None:
            try:
                self.registry.load_model_policy(agent.spec.model_policy)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"Model policy cannot be resolved: {exc}")

        required_capabilities: set[str] = set()
        for skill_ref in agent.spec.skills:
            try:
                skill = self.registry.load_skill(skill_ref)
                required_capabilities.update(skill.requires.capabilities)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"Skill cannot be resolved: {skill_ref}: {exc}")

        for capability_ref in sorted(required_capabilities):
            if capability_ref not in agent.spec.capability_bindings:
                errors.append(f"Missing capability binding: {capability_ref}")
                continue
            provider_tool = agent.spec.capability_bindings[capability_ref]
            try:
                capability = self.registry.load_capability(capability_ref)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"Capability cannot be resolved: {capability_ref}: {exc}")
                continue
            try:
                self.registry.resolve_provider_tool(capability_ref, provider_tool)
            except Exception as exc:  # noqa: BLE001
                errors.append(
                    f"Provider binding invalid for {capability_ref} -> {provider_tool}: {exc}"
                )
            if policy is not None:
                decision = self.policy_engine.evaluate(policy, capability_ref, capability)
                if decision.decision == PolicyDecision.DENY:
                    errors.append(f"Policy denies required capability: {capability_ref}")
                if decision.decision == PolicyDecision.REQUIRE_APPROVAL:
                    warnings.append(
                        f"Policy requires approval for required capability: {capability_ref}"
                    )

        return AgentValidationResult(valid=not errors, errors=errors, warnings=warnings)
