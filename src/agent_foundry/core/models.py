from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class FoundryModel(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class AccessType(StrEnum):
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PolicyDecisionKind(StrEnum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    REQUIRE_TRANSFORM = "REQUIRE_TRANSFORM"
    REQUIRE_STEP_UP_AUTH = "REQUIRE_STEP_UP_AUTH"


class RunStatus(StrEnum):
    STARTED = "started"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentMetadata(FoundryModel):
    id: str
    name: str
    owner: str | None = None


class AgentProfile(FoundryModel):
    purpose: str
    domain: str | None = None
    modes: list[str] = Field(default_factory=list)


class AgentSpec(FoundryModel):
    profile: AgentProfile
    instructions: list[str] = Field(default_factory=list)
    guidanceFiles: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    commands: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    policies: list[str] = Field(default_factory=list)
    hooks: list[str] = Field(default_factory=list)
    workflow: str | None = None
    knowledgeScopes: list[str] = Field(default_factory=list)
    memoryScopes: list[str] = Field(default_factory=list)
    modelPolicy: str | None = None
    evidenceModel: str | None = None
    evalProfile: str | None = None


class AgentManifest(FoundryModel):
    apiVersion: str
    kind: str
    metadata: AgentMetadata
    spec: AgentSpec


class SkillDefinition(FoundryModel):
    id: str
    name: str
    description: str = ""
    body: str = ""
    source_path: str | None = None


class CommandDefinition(FoundryModel):
    id: str
    description: str = ""
    skill: str | None = None
    workflow: str | None = None
    defaultTools: list[str] = Field(default_factory=list)
    outputSchema: str | None = None
    evalProfile: str | None = None


class ToolDefinition(FoundryModel):
    id: str
    name: str
    description: str
    provider: str | None = None
    accessType: AccessType
    riskLevel: RiskLevel
    inputSchema: dict[str, Any] = Field(default_factory=dict)
    outputSchema: dict[str, Any] = Field(default_factory=dict)
    createsEvidence: bool = False
    requiresApproval: bool | str = False
    actionType: str | None = None
    whenToUse: list[str] = Field(default_factory=list)
    whenNotToUse: list[str] = Field(default_factory=list)
    examples: list[dict[str, Any]] = Field(default_factory=list)
    failureModes: list[str] = Field(default_factory=list)


class PolicyMatch(FoundryModel):
    tool: str | None = None
    actionType: str | None = None
    accessType: AccessType | None = None
    riskLevel: RiskLevel | None = None
    environment: str | None = None


class PolicyRule(FoundryModel):
    match: PolicyMatch
    decision: str
    obligations: list[str] = Field(default_factory=list)
    reason: str | None = None


class PolicyDocument(FoundryModel):
    id: str
    rules: list[PolicyRule] = Field(default_factory=list)


class ProposedToolCall(FoundryModel):
    id: str
    task_id: str
    tool: str
    action_type: str | None = None
    input: dict[str, Any] = Field(default_factory=dict)
    reason: str = ""
    access_type: AccessType | None = None
    risk_level: RiskLevel | None = None


class PolicyDecision(FoundryModel):
    decision_id: str
    task_id: str
    tool_call_id: str
    tool: str
    action_type: str | None = None
    decision: PolicyDecisionKind
    reason: str
    obligations: list[str] = Field(default_factory=list)


class ApprovedToolCall(FoundryModel):
    id: str
    task_id: str
    tool: str
    action_type: str | None = None
    input: dict[str, Any] = Field(default_factory=dict)
    policy_decision_id: str


class ToolResult(FoundryModel):
    call_id: str
    task_id: str
    tool: str
    status: str
    output: dict[str, Any] = Field(default_factory=dict)
    summary: str
    raw_ref: str | None = None
    latency_ms: int = 0


class Evidence(FoundryModel):
    id: str
    task_id: str
    trace_id: str
    source_type: str
    source_uri: str
    tool: str | None = None
    summary: str
    raw_ref: str | None = None
    sensitivity: str = "internal"
    confidence: float = 0.8
    created_at: datetime


class RuntimeEvent(FoundryModel):
    event_id: str
    event_type: str
    timestamp: datetime
    trace_id: str
    task_id: str
    agent_id: str
    agent_revision: str
    snapshot_id: str
    node_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class ResolvedAgentSnapshot(FoundryModel):
    snapshot_id: str
    agent_id: str
    agent_revision: str
    created_at: datetime
    manifest: AgentManifest
    guidance: list[str] = Field(default_factory=list)
    skills: list[SkillDefinition] = Field(default_factory=list)
    commands: list[CommandDefinition] = Field(default_factory=list)
    tools: list[ToolDefinition] = Field(default_factory=list)
    policies: list[PolicyDocument] = Field(default_factory=list)
    component_versions: dict[str, str] = Field(default_factory=dict)


class ApprovalRecord(FoundryModel):
    approval_id: str
    task_id: str
    tool_call_id: str
    tool: str
    status: str
    reason: str


class VerificationResult(FoundryModel):
    name: str
    passed: bool
    message: str


class EvalRunResult(FoundryModel):
    eval_id: str
    passed: bool
    checks: list[VerificationResult] = Field(default_factory=list)
    task_id: str | None = None


class AgentState(FoundryModel):
    taskId: str
    traceId: str
    agentId: str
    agentRevision: str
    snapshotId: str
    input: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    status: RunStatus = RunStatus.STARTED
    selectedSkill: str | None = None
    selectedCommand: str | None = None
    resolvedSnapshot: ResolvedAgentSnapshot
    resolvedContext: dict[str, Any] = Field(default_factory=dict)
    plan: list[str] = Field(default_factory=list)
    proposedToolCalls: list[ProposedToolCall] = Field(default_factory=list)
    policyDecisions: list[PolicyDecision] = Field(default_factory=list)
    toolCalls: list[ToolResult] = Field(default_factory=list)
    approvals: list[ApprovalRecord] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    finalOutput: dict[str, Any] | None = None
    verificationResults: list[VerificationResult] = Field(default_factory=list)
    evalResults: list[EvalRunResult] = Field(default_factory=list)
