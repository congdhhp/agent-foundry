from __future__ import annotations

from typing import Any, TypeAlias

from pydantic import BaseModel

from .models import (
    AgentManifest,
    CapabilityContractManifest,
    EvalCase,
    EvalSuiteManifest,
    EvidenceObject,
    ModelPolicyManifest,
    PolicyManifest,
    SkillManifest,
    ToolProviderManifest,
    WorkflowDefinition,
)

ArtifactModel: TypeAlias = type[BaseModel]

ARTIFACT_MODELS: dict[str, ArtifactModel] = {
    "agent": AgentManifest,
    "skill": SkillManifest,
    "capability": CapabilityContractManifest,
    "capability-contract": CapabilityContractManifest,
    "policy": PolicyManifest,
    "tool-provider": ToolProviderManifest,
    "tool": ToolProviderManifest,
    "workflow": WorkflowDefinition,
    "evidence": EvidenceObject,
    "eval": EvalCase,
    "eval-case": EvalCase,
    "eval-suite": EvalSuiteManifest,
    "model-policy": ModelPolicyManifest,
    "suite": EvalSuiteManifest,
}


def detect_artifact_type(document: dict[str, Any]) -> str:
    kind = document.get("kind")
    if kind == "Agent":
        return "agent"
    if kind == "CapabilityContract":
        return "capability-contract"
    if kind == "Policy":
        return "policy"
    if kind == "ToolProvider":
        return "tool-provider"
    if kind == "EvalSuite":
        return "eval-suite"
    if kind == "ModelPolicy":
        return "model-policy"
    if {"id", "version", "nodes", "runtime"}.issubset(document):
        return "workflow"
    if {"id", "version", "triggers", "requires", "lifecycle_status"}.issubset(document):
        return "skill"
    if {"evidence_id", "task_id", "source_type", "summary"}.issubset(document):
        return "evidence"
    if {"id", "task", "expected"}.issubset(document):
        return "eval-case"
    raise ValueError("Unable to detect artifact type. Pass --type explicitly.")


def validate_document(document: dict[str, Any], artifact_type: str | None = None) -> BaseModel:
    resolved_type = artifact_type or detect_artifact_type(document)
    model = ARTIFACT_MODELS.get(resolved_type)
    if model is None:
        known = ", ".join(sorted(ARTIFACT_MODELS))
        raise ValueError(f"Unknown artifact type '{resolved_type}'. Known types: {known}")
    return model.model_validate(document)


def artifact_summary(artifact: BaseModel) -> dict[str, Any]:
    if isinstance(artifact, AgentManifest):
        return {
            "type": "agent",
            "id": artifact.metadata.id,
            "name": artifact.metadata.name,
            "skills": len(artifact.spec.skills),
            "capability_bindings": len(artifact.spec.capability_bindings),
            "policy": artifact.spec.policy,
            "workflow": artifact.spec.workflow,
        }
    if isinstance(artifact, SkillManifest):
        workflow_hints = []
        if artifact.default_workflow is not None:
            workflow_hints.append(artifact.default_workflow)
        if artifact.workflow_hints.default is not None:
            workflow_hints.append(artifact.workflow_hints.default)
        workflow_hints.extend(artifact.workflow_hints.compatible)
        return {
            "type": "skill",
            "id": artifact.id,
            "version": artifact.version,
            "risk_level": artifact.risk_level,
            "lifecycle_status": artifact.lifecycle_status,
            "required_capabilities": len(artifact.requires.capabilities),
            "workflow_hints": list(dict.fromkeys(workflow_hints)),
        }
    if isinstance(artifact, CapabilityContractManifest):
        return {
            "type": "capability-contract",
            "id": artifact.metadata.id,
            "version": artifact.metadata.version,
            "access_type": artifact.spec.access_type,
            "risk_level": artifact.spec.risk_level,
        }
    if isinstance(artifact, PolicyManifest):
        return {
            "type": "policy",
            "id": artifact.metadata.id,
            "version": artifact.metadata.version,
            "rules": len(artifact.spec.rules),
        }
    if isinstance(artifact, ModelPolicyManifest):
        return {
            "type": "model-policy",
            "id": artifact.metadata.id,
            "version": artifact.metadata.version,
            "default_provider": artifact.spec.default_provider,
            "default_model": artifact.spec.default_model,
            "allowed_providers": artifact.spec.allowed_providers,
            "allowed_models": artifact.spec.allowed_models,
        }
    if isinstance(artifact, ToolProviderManifest):
        return {
            "type": "tool-provider",
            "id": artifact.metadata.id,
            "version": artifact.metadata.version,
            "protocol": artifact.spec.protocol,
            "capabilities": len(artifact.spec.capabilities),
        }
    if isinstance(artifact, WorkflowDefinition):
        return {
            "type": "workflow",
            "id": artifact.id,
            "version": artifact.version,
            "runtime": artifact.runtime,
            "nodes": len(artifact.nodes),
        }
    if isinstance(artifact, EvidenceObject):
        return {
            "type": "evidence",
            "id": artifact.evidence_id,
            "task_id": artifact.task_id,
            "source_type": artifact.source_type,
            "trusted": artifact.trusted,
        }
    if isinstance(artifact, EvalCase):
        return {
            "type": "eval-case",
            "id": artifact.id,
            "input": artifact.task.input,
        }
    if isinstance(artifact, EvalSuiteManifest):
        return {
            "type": "eval-suite",
            "id": artifact.metadata.id,
            "version": artifact.metadata.version,
            "cases": len(artifact.spec.cases),
            "min_pass_rate": artifact.spec.pass_criteria.min_pass_rate,
        }
    return {"type": artifact.__class__.__name__}

