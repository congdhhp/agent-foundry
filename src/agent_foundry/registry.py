from __future__ import annotations

from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from .loader import load_document
from .models import (
    AgentManifest,
    CapabilityContractManifest,
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
    """Loads Phase 0 artifacts from the repository's examples directory."""

    def __init__(self, root: str | Path = ".") -> None:
        self.root = Path(root)
        self.examples_dir = self.root / "examples"

    def load_agent(self, path_or_ref: str | Path) -> AgentManifest:
        path = Path(path_or_ref)
        if path.exists():
            return self._load_file(path, AgentManifest, "agent")
        local_path = self.root / ".agent" / "agents" / f"{path_or_ref}.yaml"
        if local_path.exists():
            return self._load_file(local_path, AgentManifest, "agent")
        ref = ArtifactRef.parse(str(path_or_ref))
        return self._find_by_ref(self.examples_dir / "agents", ref, AgentManifest, "agent")

    def load_skill(self, ref_value: str) -> SkillManifest:
        ref = ArtifactRef.parse(ref_value)
        candidates = [
            path
            for path in (self.examples_dir / "skills").glob("*/skill.yaml")
            if path.is_file()
        ]
        return self._find_candidate_by_ref(candidates, ref, SkillManifest, "skill")

    def load_capability(self, ref_value: str) -> CapabilityContractManifest:
        ref = ArtifactRef.parse(ref_value)
        return self._find_by_ref(
            self.examples_dir / "capabilities",
            ref,
            CapabilityContractManifest,
            "capability-contract",
        )

    def load_policy(self, ref_value: str) -> PolicyManifest:
        ref = ArtifactRef.parse(ref_value)
        return self._find_by_ref(
            self.examples_dir / "policies", ref, PolicyManifest, "policy"
        )

    def load_model_policy(self, ref_value: str) -> ModelPolicyManifest:
        ref = ArtifactRef.parse(ref_value)
        return self._find_by_ref(
            self.examples_dir / "model-policies",
            ref,
            ModelPolicyManifest,
            "model-policy",
        )

    def list_tool_providers(self) -> list[ToolProviderManifest]:
        tools_dir = self.examples_dir / "tools"
        if not tools_dir.exists():
            return []
        providers: list[ToolProviderManifest] = []
        for path in sorted(tools_dir.glob("*.yaml")) + sorted(tools_dir.glob("*.yml")):
            providers.append(self._load_file(path, ToolProviderManifest, "tool-provider"))
        return providers

    def load_tool_provider(self, provider_id: str) -> ToolProviderManifest:
        tools_dir = self.examples_dir / "tools"
        for provider in self.list_tool_providers():
            if provider.metadata.id == provider_id:
                return provider
        raise FileNotFoundError(f"Could not resolve tool provider {provider_id}")

    def resolve_provider_tool(
        self, capability_ref: str, provider_tool: str
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
            self.examples_dir / "workflows", ref, WorkflowDefinition, "workflow"
        )

    def _find_by_ref(
        self,
        directory: Path,
        ref: ArtifactRef,
        expected_type: type[T],
        artifact_type: str,
    ) -> T:
        candidates = sorted(directory.glob("*.yaml")) + sorted(directory.glob("*.yml"))
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
                ModelPolicyManifest,
                PolicyManifest,
                ToolProviderManifest,
            ),
        ):
            return artifact.metadata.id, artifact.metadata.version
        if isinstance(artifact, AgentManifest):
            return artifact.metadata.id, "0.0.0"
        raise TypeError(f"Unsupported artifact identity: {artifact.__class__.__name__}")
