from __future__ import annotations

from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from .loader import load_document
from .models import (
    AgentManifest,
    CapabilityContractManifest,
    EvalSuiteManifest,
    ModelPolicyManifest,
    PolicyManifest,
    SkillManifest,
    ToolProviderManifest,
    WorkflowDefinition,
)
from .refs import ArtifactRef
from .validation import validate_document

T = TypeVar("T", bound=BaseModel)


class LocalRegistry:
    """Loads artifacts from user registry first, then bundled examples."""

    def __init__(
        self,
        root: str | Path = ".",
        store_root: str | Path | None = None,
    ) -> None:
        self.root = Path(root)
        self.store_root = Path(store_root) if store_root is not None else self.root / ".agent"
        self.examples_dir = self.root / "examples"
        self.user_registry_dir = self.store_root / "registry"

    def load_agent(self, path_or_ref: str | Path) -> AgentManifest:
        path = Path(path_or_ref)
        if path.exists():
            return self._load_file(path, AgentManifest, "agent")
        for local_path in [
            self.store_root / "agents" / f"{path_or_ref}.yaml",
            self.user_registry_dir / "agents" / f"{path_or_ref}.yaml",
            self.examples_dir / "agents" / f"{path_or_ref}.yaml",
        ]:
            if local_path.exists():
                return self._load_file(local_path, AgentManifest, "agent")
        ref = ArtifactRef.parse(str(path_or_ref))
        return self._find_by_ref(
            self._artifact_dirs("agents"),
            ref,
            AgentManifest,
            "agent",
        )

    def load_skill(self, ref_value: str) -> SkillManifest:
        ref = ArtifactRef.parse(ref_value)
        candidates = [
            path
            for directory in self._artifact_dirs("skills")
            for path in directory.glob("*/skill.yaml")
            if path.is_file()
        ]
        return self._find_candidate_by_ref(candidates, ref, SkillManifest, "skill")

    def load_capability(self, ref_value: str) -> CapabilityContractManifest:
        ref = ArtifactRef.parse(ref_value)
        return self._find_by_ref(
            self._artifact_dirs("capabilities"),
            ref,
            CapabilityContractManifest,
            "capability-contract",
        )

    def load_policy(self, ref_value: str) -> PolicyManifest:
        ref = ArtifactRef.parse(ref_value)
        return self._find_by_ref(
            self._artifact_dirs("policies"),
            ref,
            PolicyManifest,
            "policy",
        )

    def load_model_policy(self, ref_value: str) -> ModelPolicyManifest:
        ref = ArtifactRef.parse(ref_value)
        return self._find_by_ref(
            self._artifact_dirs("model-policies"),
            ref,
            ModelPolicyManifest,
            "model-policy",
        )

    def list_tool_providers(self) -> list[ToolProviderManifest]:
        providers: list[ToolProviderManifest] = []
        seen: set[str] = set()
        for directory in self._artifact_dirs("tools"):
            if not directory.exists():
                continue
            for path in sorted(directory.glob("*.yaml")) + sorted(directory.glob("*.yml")):
                provider = self._load_file(path, ToolProviderManifest, "tool-provider")
                ref = f"{provider.metadata.id}@{provider.metadata.version}"
                if ref in seen:
                    continue
                seen.add(ref)
                providers.append(provider)
        return providers

    def load_tool_provider(self, provider_id: str) -> ToolProviderManifest:
        for provider in self.list_tool_providers():
            if provider.metadata.id == provider_id:
                return provider
        raise FileNotFoundError(f"Could not resolve tool provider {provider_id}")

    def resolve_provider_tool(
        self,
        capability_ref: str,
        provider_tool: str,
    ) -> tuple[ToolProviderManifest, str]:
        if "." not in provider_tool:
            raise ValueError(
                f"Provider tool binding must look like '<provider>.<tool>': {provider_tool}"
            )
        provider_id, tool_name = provider_tool.split(".", 1)
        provider = self.load_tool_provider(provider_id)
        for capability in provider.spec.capabilities:
            if capability.contract == capability_ref and capability.tool == tool_name:
                return provider, tool_name
        raise ValueError(
            f"Provider {provider_id} does not implement {capability_ref} via tool {tool_name}"
        )

    def load_workflow(self, ref_value: str) -> WorkflowDefinition:
        ref = ArtifactRef.parse(ref_value)
        return self._find_by_ref(
            self._artifact_dirs("workflows"),
            ref,
            WorkflowDefinition,
            "workflow",
        )

    def load_eval_suite(self, ref_value: str) -> EvalSuiteManifest:
        ref = ArtifactRef.parse(ref_value)
        return self._find_by_ref(
            self._artifact_dirs("eval-suites"),
            ref,
            EvalSuiteManifest,
            "eval-suite",
        )

    def _artifact_dirs(self, name: str) -> list[Path]:
        return [self.user_registry_dir / name, self.examples_dir / name]

    def _find_by_ref(
        self,
        directories: list[Path],
        ref: ArtifactRef,
        expected_type: type[T],
        artifact_type: str,
    ) -> T:
        candidates = [
            path
            for directory in directories
            if directory.exists()
            for path in sorted(directory.glob("*.yaml")) + sorted(directory.glob("*.yml"))
        ]
        return self._find_candidate_by_ref(candidates, ref, expected_type, artifact_type)

    def _find_candidate_by_ref(
        self,
        candidates: list[Path],
        ref: ArtifactRef,
        expected_type: type[T],
        artifact_type: str,
    ) -> T:
        for path in candidates:
            artifact = self._load_file(path, expected_type, artifact_type)
            artifact_id, version = self._artifact_identity(artifact)
            if ref.matches(artifact_id, version):
                return artifact
        raise FileNotFoundError(f"Could not resolve {artifact_type} reference {ref}")

    def _load_file(self, path: Path, expected_type: type[T], artifact_type: str) -> T:
        artifact = validate_document(load_document(path), artifact_type)
        if not isinstance(artifact, expected_type):
            raise TypeError(f"{path} did not load as {expected_type.__name__}")
        return artifact

    def _artifact_identity(self, artifact: BaseModel) -> tuple[str, str]:
        if isinstance(artifact, SkillManifest):
            return artifact.id, artifact.version
        if isinstance(artifact, WorkflowDefinition):
            return artifact.id, artifact.version
        if isinstance(
            artifact,
            (
                CapabilityContractManifest,
                EvalSuiteManifest,
                ModelPolicyManifest,
                PolicyManifest,
                ToolProviderManifest,
            ),
        ):
            return artifact.metadata.id, artifact.metadata.version
        if isinstance(artifact, AgentManifest):
            return artifact.metadata.id, "0.0.0"
        raise TypeError(f"Unsupported artifact identity: {artifact.__class__.__name__}")
