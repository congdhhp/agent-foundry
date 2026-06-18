from __future__ import annotations

import re
from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

ARTIFACT_REF_RE = re.compile(r"^[A-Za-z0-9_.-]+@\d+\.\d+(?:\.\d+)?$")
CAPABILITY_REF_RE = re.compile(r"^[A-Za-z0-9_.-]+@\d+\.\d+(?:\.\d+)?$")
PROVIDER_TOOL_RE = re.compile(r"^[A-Za-z0-9_.-]+\.[A-Za-z0-9_.-]+$")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class LifecycleStatus(StrEnum):
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class AccessType(StrEnum):
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"


class PolicyDecision(StrEnum):
    ALLOW = "allow"
    REQUIRE_APPROVAL = "require_approval"
    DENY = "deny"
    REQUIRE_TRANSFORM = "require_transform"
    REQUIRE_STEP_UP_AUTH = "require_step_up_auth"


class WorkflowNodeType(StrEnum):
    LLM_REASONING = "llm_reasoning"
    CAPABILITY_CALL = "capability_call"
    KNOWLEDGE_RETRIEVAL = "knowledge_retrieval"
    HUMAN_APPROVAL = "human_approval"
    EVALUATOR = "evaluator"
    ROUTER = "router"
    ARTIFACT_WRITER = "artifact_writer"
    OUTPUT_COMPOSER = "output_composer"


class EvidenceSourceType(StrEnum):
    TOOL_RESULT = "tool_result"
    RETRIEVED_DOCUMENT = "retrieved_document"
    HUMAN_INPUT = "human_input"
    MODEL_VERIFIED_SOURCE = "model_verified_source"
    ARTIFACT = "artifact"
    REMOTE_AGENT_RESULT = "remote_agent_result"


def _validate_artifact_ref(value: str, field_name: str) -> str:
    if not ARTIFACT_REF_RE.match(value):
        raise ValueError(f"{field_name} must look like '<id>@<major>.<minor>[.<patch>]'")
    return value


def _validate_capability_ref(value: str, field_name: str) -> str:
    if not CAPABILITY_REF_RE.match(value):
        raise ValueError(f"{field_name} must look like '<capability>@<major>.<minor>[.<patch>]'")
    return value


class AgentMetadata(StrictModel):
    id: str
    name: str
    owner: str
    labels: dict[str, str] = Field(default_factory=dict)


class AgentSpec(StrictModel):
    template: str
    purpose: str
    skills: list[str] = Field(default_factory=list)
    capability_bindings: dict[str, str] = Field(default_factory=dict, alias="capabilityBindings")
    knowledge_scopes: list[str] = Field(default_factory=list, alias="knowledgeScopes")
    memory_scopes: list[str] = Field(default_factory=list, alias="memoryScopes")
    policy: str
    workflow: str
    model_policy: str | None = Field(default=None, alias="modelPolicy")
    eval_profile: str | None = Field(default=None, alias="evalProfile")

    @field_validator("template", "policy", "workflow", "model_policy", "eval_profile")
    @classmethod
    def validate_refs(cls, value: str | None, info: Any) -> str | None:
        if value is None:
            return value
        return _validate_artifact_ref(value, info.field_name)

    @field_validator("skills")
    @classmethod
    def validate_skills(cls, value: list[str]) -> list[str]:
        for skill in value:
            _validate_artifact_ref(skill, "skills")
        return value

    @field_validator("capability_bindings")
    @classmethod
    def validate_capability_bindings(cls, value: dict[str, str]) -> dict[str, str]:
        for capability, provider_tool in value.items():
            _validate_capability_ref(capability, "capabilityBindings key")
            if not PROVIDER_TOOL_RE.match(provider_tool):
                raise ValueError(
                    "capabilityBindings value must look like '<provider>.<tool>'"
                )
        return value


class AgentManifest(StrictModel):
    api_version: Literal["agents.platform/v1"] = Field(alias="apiVersion")
    kind: Literal["Agent"]
    metadata: AgentMetadata
    spec: AgentSpec


class SkillTriggers(StrictModel):
    intents: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)


class SkillRequires(StrictModel):
    capabilities: list[str] = Field(default_factory=list)

    @field_validator("capabilities")
    @classmethod
    def validate_capabilities(cls, value: list[str]) -> list[str]:
        for capability in value:
            _validate_capability_ref(capability, "requires.capabilities")
        return value


class SkillManifest(StrictModel):
    id: str
    version: str
    name: str
    description: str
    owner: str
    risk_level: RiskLevel
    lifecycle_status: LifecycleStatus
    triggers: SkillTriggers = Field(default_factory=SkillTriggers)
    requires: SkillRequires = Field(default_factory=SkillRequires)
    optional_capabilities: list[str] = Field(default_factory=list)
    default_workflow: str
    output_schema: str

    @field_validator("version")
    @classmethod
    def validate_version(cls, value: str) -> str:
        if not re.match(r"^\d+\.\d+(?:\.\d+)?$", value):
            raise ValueError("version must look like '<major>.<minor>[.<patch>]'")
        return value

    @field_validator("optional_capabilities")
    @classmethod
    def validate_optional_capabilities(cls, value: list[str]) -> list[str]:
        for capability in value:
            _validate_capability_ref(capability, "optional_capabilities")
        return value

    @field_validator("default_workflow", "output_schema")
    @classmethod
    def validate_artifact_refs(cls, value: str, info: Any) -> str:
        return _validate_artifact_ref(value, info.field_name)


class VersionedMetadata(StrictModel):
    id: str
    version: str
    name: str | None = None
    owner: str | None = None
    labels: dict[str, str] = Field(default_factory=dict)

    @field_validator("version")
    @classmethod
    def validate_version(cls, value: str) -> str:
        if not re.match(r"^\d+\.\d+(?:\.\d+)?$", value):
            raise ValueError("version must look like '<major>.<minor>[.<patch>]'")
        return value


class CapabilityEvidenceSpec(StrictModel):
    creates_evidence: bool = Field(alias="creates_evidence")
    evidence_type: str


class CapabilitySpec(StrictModel):
    category: str
    access_type: AccessType = Field(alias="accessType")
    risk_level: RiskLevel = Field(alias="riskLevel")
    input_schema: dict[str, Any] = Field(alias="inputSchema")
    output_schema: dict[str, Any] = Field(alias="outputSchema")
    semantic_contract: dict[str, Any] = Field(alias="semanticContract")
    evidence: CapabilityEvidenceSpec


class CapabilityContractManifest(StrictModel):
    api_version: Literal["agents.platform/v1"] = Field(alias="apiVersion")
    kind: Literal["CapabilityContract"]
    metadata: VersionedMetadata
    spec: CapabilitySpec


class ToolProviderCapability(StrictModel):
    contract: str
    tool: str
    risk_level: RiskLevel = Field(alias="riskLevel")

    @field_validator("contract")
    @classmethod
    def validate_contract(cls, value: str) -> str:
        return _validate_capability_ref(value, "contract")


class ToolProviderOutputSanitization(StrictModel):
    redact_secrets: bool = Field(default=True, alias="redactSecrets")
    max_payload_bytes: int = Field(default=1000000, alias="maxPayloadBytes")
    tag_untrusted: bool = Field(default=True, alias="tagUntrusted")


class ToolProviderSpec(StrictModel):
    protocol: str
    transport: str = "in_process"
    endpoint: str | None = None
    auth_profile: str | None = Field(default=None, alias="authProfile")
    capabilities: list[ToolProviderCapability]
    tenant_scope: str | None = Field(default=None, alias="tenantScope")
    output_sanitization: ToolProviderOutputSanitization = Field(
        default_factory=ToolProviderOutputSanitization,
        alias="outputSanitization",
    )


class ToolProviderManifest(StrictModel):
    api_version: Literal["agents.platform/v1"] = Field(alias="apiVersion")
    kind: Literal["ToolProvider"]
    metadata: VersionedMetadata
    spec: ToolProviderSpec


class PolicyRule(StrictModel):
    match: dict[str, Any]
    decision: PolicyDecision
    transforms: list[str] = Field(default_factory=list)
    approvers: list[str] = Field(default_factory=list)


class PolicySpec(StrictModel):
    rules: list[PolicyRule]


class PolicyManifest(StrictModel):
    api_version: Literal["agents.platform/v1"] = Field(alias="apiVersion")
    kind: Literal["Policy"]
    metadata: VersionedMetadata
    spec: PolicySpec


class WorkflowNode(StrictModel):
    id: str
    type: WorkflowNodeType
    capability: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)

    @field_validator("capability")
    @classmethod
    def validate_capability(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _validate_capability_ref(value, "capability")


class WorkflowDefinition(StrictModel):
    id: str
    version: str
    runtime: str
    state_schema: str
    nodes: list[WorkflowNode]

    @field_validator("version")
    @classmethod
    def validate_version(cls, value: str) -> str:
        if not re.match(r"^\d+\.\d+(?:\.\d+)?$", value):
            raise ValueError("version must look like '<major>.<minor>[.<patch>]'")
        return value


class EvidenceObject(StrictModel):
    evidence_id: str
    task_id: str
    source_type: EvidenceSourceType
    source_uri: str | None = None
    capability: str | None = None
    timestamp: datetime
    sensitivity: str
    confidence: float | None = Field(default=None, ge=0, le=1)
    summary: str
    raw_ref: str | None = None
    trusted: bool = False

    @field_validator("capability")
    @classmethod
    def validate_capability(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _validate_capability_ref(value, "capability")


class EvalTask(StrictModel):
    input: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvalExpected(StrictModel):
    selected_skills: dict[str, Any] = Field(default_factory=dict)
    tool_trajectory: dict[str, Any] = Field(default_factory=dict)
    provider_trajectory: dict[str, Any] = Field(default_factory=dict)
    policy: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)
    grounding: dict[str, Any] = Field(default_factory=dict)
    safety: dict[str, Any] = Field(default_factory=dict)


class EvalCase(StrictModel):
    id: str
    task: EvalTask
    expected: EvalExpected

