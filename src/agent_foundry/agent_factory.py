from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .agent_validation import AgentDeepValidator
from .evals import EvalRunner
from .loader import dump_yaml, load_document
from .models import AgentManifest
from .registry import LocalRegistry
from .skills import SkillRegistry
from .tool_providers import ToolProviderRegistry
from .validation import validate_document


@dataclass(frozen=True)
class AgentCreateRequest:
    agent_id: str
    name: str
    purpose: str
    owner: str
    skills: list[str]
    policy: str
    workflow: str
    template: str = "generic-task-agent@1.0.0"
    model_policy: str = "default-model-policy@1.0.0"
    eval_profile: str | None = None
    labels: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class AgentPublishResult:
    published: bool
    path: Path
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    eval_reports: list[dict[str, Any]] = field(default_factory=list)


class AgentFactory:
    def __init__(
        self,
        registry_root: str | Path = ".",
        store_root: str | Path = ".agent",
    ) -> None:
        self.registry_root = Path(registry_root)
        self.store_root = Path(store_root)
        self.agents_dir = self.store_root / "agents"
        self.registry = LocalRegistry(self.registry_root)
        self.skill_registry = SkillRegistry(self.registry_root)
        self.tool_provider_registry = ToolProviderRegistry(self.registry_root)

    def create(self, request: AgentCreateRequest, overwrite: bool = False) -> Path:
        self.agents_dir.mkdir(parents=True, exist_ok=True)
        path = self.agent_path(request.agent_id)
        if path.exists() and not overwrite:
            raise FileExistsError(f"Agent already exists: {path}")

        capability_bindings = self._auto_bind_capabilities(request.skills)
        manifest = {
            "apiVersion": "agents.platform/v1",
            "kind": "Agent",
            "metadata": {
                "id": request.agent_id,
                "name": request.name,
                "owner": request.owner,
                "status": "draft",
                "labels": request.labels,
            },
            "spec": {
                "template": request.template,
                "purpose": request.purpose,
                "skills": request.skills,
                "capabilityBindings": capability_bindings,
                "knowledgeScopes": [],
                "memoryScopes": ["session", "task"],
                "policy": request.policy,
                "workflow": request.workflow,
                "modelPolicy": request.model_policy,
                "evalProfile": request.eval_profile,
            },
        }
        agent = validate_document(manifest, "agent")
        path.write_text(
            dump_yaml(agent.model_dump(mode="json", by_alias=True, exclude_none=True)),
            encoding="utf-8",
        )
        return path

    def list_agents(self) -> list[dict[str, Any]]:
        agents: list[dict[str, Any]] = []
        if not self.agents_dir.exists():
            return agents
        for path in sorted(self.agents_dir.glob("*.yaml")):
            agent = self.load_local(path)
            agents.append(
                {
                    "id": agent.metadata.id,
                    "name": agent.metadata.name,
                    "status": agent.metadata.status,
                    "path": str(path),
                    "skills": agent.spec.skills,
                }
            )
        return agents

    def inspect(self, path_or_id: str | Path) -> dict[str, Any]:
        path = self.resolve_agent_path(path_or_id)
        agent = self.load_local(path)
        validation = AgentDeepValidator(self.registry_root).validate(path)
        bindings = self.tool_provider_registry.bindings_for_agent(agent)
        skill_details = []
        for skill_ref in agent.spec.skills:
            package = self.skill_registry.load_package(skill_ref)
            skill_details.append(
                {
                    "skill": package.ref,
                    "description": package.manifest.description,
                    "required_capabilities": package.manifest.requires.capabilities,
                    "package_path": str(package.root),
                }
            )
        return {
            "agent": {
                "id": agent.metadata.id,
                "name": agent.metadata.name,
                "status": agent.metadata.status,
                "owner": agent.metadata.owner,
                "purpose": agent.spec.purpose,
                "path": str(path),
            },
            "skills": skill_details,
            "bindings": [
                {
                    "capability": binding.capability,
                    "provider_tool": binding.provider_tool,
                    "provider_id": binding.provider_id,
                    "tool_name": binding.tool_name,
                    "valid": binding.valid,
                    "error": binding.error,
                }
                for binding in bindings
            ],
            "policy": agent.spec.policy,
            "workflow": agent.spec.workflow,
            "validation": {
                "valid": validation.valid,
                "errors": validation.errors,
                "warnings": validation.warnings,
            },
        }

    def publish(
        self,
        path_or_id: str | Path,
        eval_cases: list[str | Path] | None = None,
    ) -> AgentPublishResult:
        path = self.resolve_agent_path(path_or_id)
        agent = self.load_local(path)
        errors: list[str] = []
        warnings: list[str] = []

        validation = AgentDeepValidator(self.registry_root).validate(path)
        errors.extend(validation.errors)
        warnings.extend(validation.warnings)

        tools = self.tool_provider_registry.validate_all()
        errors.extend(tools.errors)
        warnings.extend(tools.warnings)

        for skill_ref in agent.spec.skills:
            package_validation = self.skill_registry.validate_package(skill_ref)
            errors.extend(package_validation.errors)
            warnings.extend(package_validation.warnings)

        eval_reports: list[dict[str, Any]] = []
        for eval_case in eval_cases or []:
            report = EvalRunner(self.registry_root, self.store_root / "evals").run(
                eval_case,
                path,
            )
            eval_reports.append(report.to_dict())
            if not report.passed:
                errors.append(f"Eval failed: {report.eval_id}")
        if not eval_cases:
            warnings.append("No eval cases were provided for publish gate.")

        if errors:
            return AgentPublishResult(
                published=False,
                path=path,
                errors=errors,
                warnings=warnings,
                eval_reports=eval_reports,
            )

        data = load_document(path)
        data.setdefault("metadata", {})["status"] = "published"
        published = validate_document(data, "agent")
        path.write_text(
            dump_yaml(published.model_dump(mode="json", by_alias=True, exclude_none=True)),
            encoding="utf-8",
        )
        return AgentPublishResult(
            published=True,
            path=path,
            errors=[],
            warnings=warnings,
            eval_reports=eval_reports,
        )

    def load_local(self, path: str | Path) -> AgentManifest:
        agent = validate_document(load_document(path), "agent")
        if not isinstance(agent, AgentManifest):
            raise TypeError(f"{path} is not an agent manifest")
        return agent

    def resolve_agent_path(self, path_or_id: str | Path) -> Path:
        path = Path(path_or_id)
        if path.exists():
            return path
        local_path = self.agent_path(str(path_or_id))
        if local_path.exists():
            return local_path
        raise FileNotFoundError(f"Agent not found: {path_or_id}")

    def agent_path(self, agent_id: str) -> Path:
        return self.agents_dir / f"{agent_id}.yaml"

    def _auto_bind_capabilities(self, skill_refs: list[str]) -> dict[str, str]:
        required: list[str] = []
        for skill_ref in skill_refs:
            skill = self.registry.load_skill(skill_ref)
            for capability in skill.requires.capabilities:
                if capability not in required:
                    required.append(capability)

        bindings: dict[str, str] = {}
        providers = self.registry.list_tool_providers()
        for capability_ref in required:
            for provider in providers:
                match = next(
                    (
                        capability
                        for capability in provider.spec.capabilities
                        if capability.contract == capability_ref
                    ),
                    None,
                )
                if match is not None:
                    bindings[capability_ref] = f"{provider.metadata.id}.{match.tool}"
                    break
            if capability_ref not in bindings:
                raise ValueError(f"No tool provider implements {capability_ref}")
        return bindings

