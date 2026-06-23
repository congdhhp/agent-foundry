from __future__ import annotations

from pathlib import Path

from agent_foundry.commands.command_loader import CommandLoader
from agent_foundry.core.ids import new_id
from agent_foundry.core.models import (
    AgentState,
    ApprovalRecord,
    ApprovedToolCall,
    CommandDefinition,
    PolicyDecisionKind,
    ResolvedAgentSnapshot,
    RunStatus,
    RuntimeEvent,
)
from agent_foundry.core.time import utc_now
from agent_foundry.evidence.manager import EvidenceManager
from agent_foundry.evidence.verifier import OutputVerifier
from agent_foundry.guidance.loader import GuidanceLoader
from agent_foundry.manifests.agent_loader import AgentManifestLoader
from agent_foundry.models.provider import ChatModel
from agent_foundry.policy.engine import PolicyEngine
from agent_foundry.policy.loader import PolicyLoader
from agent_foundry.runtime.llm import ModelAnswerComposer, ModelPlanner
from agent_foundry.runtime.planner import DeterministicPlanner
from agent_foundry.skills.selector import SkillSelector
from agent_foundry.skills.skill_loader import SkillLoader
from agent_foundry.storage.local_store import LocalStore
from agent_foundry.tools.catalog import ToolCatalog
from agent_foundry.tools.executor import MockToolExecutor


class AgentRuntime:
    def __init__(
        self,
        project_root: str | Path = ".",
        store_root: str | Path = ".agent",
        planner_mode: str = "auto",
        model_provider: ChatModel | None = None,
    ) -> None:
        self.project_root = Path(project_root)
        self.planner_mode = planner_mode
        self.model_provider = model_provider
        if planner_mode not in {"auto", "deterministic", "llm"}:
            raise ValueError("planner_mode must be one of: auto, deterministic, llm")
        if planner_mode == "llm" and model_provider is None:
            raise ValueError("LLM planner mode requires a configured model provider.")
        self.store = LocalStore(self.project_root / store_root)
        self.manifest_loader = AgentManifestLoader()
        self.guidance_loader = GuidanceLoader(self.project_root)
        self.skill_loader = SkillLoader([self.project_root / "docs" / "examples" / "skills", self.project_root / ".agent" / "skills"])
        self.command_loader = CommandLoader([self.project_root / "docs" / "examples" / "commands", self.project_root / ".agent" / "commands"])
        self.policy_loader = PolicyLoader([self.project_root / "docs" / "examples" / "policies", self.project_root / ".agent" / "policies"])
        self.tool_catalog = ToolCatalog.from_yaml(self.project_root / "docs" / "examples" / "tools" / "tools.yaml")
        self.selector = SkillSelector()
        self.planner = DeterministicPlanner()
        self.policy_engine = PolicyEngine()
        self.executor = MockToolExecutor()
        self.evidence_manager = EvidenceManager()
        self.verifier = OutputVerifier()

    def run(self, agent_manifest_path: str | Path, task_input: str, command_id: str | None = None) -> AgentState:
        manifest = self.manifest_loader.load(agent_manifest_path)
        task_id = new_id("task")
        trace_id = new_id("trace")
        revision = "rev-local"
        snapshot_id = new_id("snap")

        guidance = self.guidance_loader.load(manifest.spec.guidanceFiles)
        skills = self.skill_loader.load_many(manifest.spec.skills)
        commands = self.command_loader.load_many(manifest.spec.commands)
        policies = self.policy_loader.load_many(manifest.spec.policies)
        tools = self.tool_catalog.subset(manifest.spec.tools)
        command = self._select_command(command_id, commands)

        snapshot = ResolvedAgentSnapshot(
            snapshot_id=snapshot_id,
            agent_id=manifest.metadata.id,
            agent_revision=revision,
            created_at=utc_now(),
            manifest=manifest,
            guidance=guidance,
            skills=skills,
            commands=commands,
            tools=tools,
            policies=policies,
            component_versions={
                "manifest": str(agent_manifest_path),
                "tools": "docs/examples/tools/tools.yaml",
                "policies": ",".join(manifest.spec.policies),
            },
        )
        self.store.write_snapshot(task_id, snapshot)

        selected_skill = self.selector.select(task_input, manifest, skills, command)
        state = AgentState(
            taskId=task_id,
            traceId=trace_id,
            agentId=manifest.metadata.id,
            agentRevision=revision,
            snapshotId=snapshot_id,
            input=task_input,
            selectedSkill=selected_skill.id if selected_skill else None,
            selectedCommand=command.id if command else None,
            resolvedSnapshot=snapshot,
            resolvedContext={
                "guidance_count": len(guidance),
                "skill_ids": [skill.id for skill in skills],
                "command_ids": [cmd.id for cmd in commands],
                "policy_ids": [policy.id for policy in policies],
            },
        )
        self._event(state, "task.started", "receive_task", {"input": task_input})
        self._event(state, "agent.snapshot.used", "resolve_snapshot", {"snapshot_id": snapshot_id})
        if selected_skill:
            self._event(state, "skill.selected", "select_skill", {"skill": selected_skill.id})
        if command:
            self._event(state, "command.selected", "select_command", {"command": command.id})

        use_llm = self._use_llm()
        if use_llm:
            self._event(state, "model.used", "plan", {"mode": self.planner_mode})
            proposals = ModelPlanner(self.model_provider, self.planner).plan(
                task_id,
                task_input,
                selected_skill,
                command,
                tools,
                guidance,
            )
        else:
            proposals = self.planner.plan(task_id, task_input, selected_skill, command, tools)
        state.proposedToolCalls = proposals
        state.plan = [proposal.tool for proposal in proposals]

        for proposal in proposals:
            self._event(state, "tool.proposed", "propose_tool", {"tool": proposal.tool, "call_id": proposal.id})
            tool = self.tool_catalog.require(proposal.tool)
            decision = self.policy_engine.evaluate(proposal, tool, policies)
            state.policyDecisions.append(decision)
            self._event(
                state,
                "policy.evaluated",
                "policy_check",
                {"tool": proposal.tool, "decision": decision.decision, "reason": decision.reason},
            )
            if decision.decision == PolicyDecisionKind.ALLOW:
                approved = ApprovedToolCall(
                    id=proposal.id,
                    task_id=task_id,
                    tool=proposal.tool,
                    action_type=proposal.action_type,
                    input=proposal.input,
                    policy_decision_id=decision.decision_id,
                )
                result = self.executor.execute(approved)
                state.toolCalls.append(result)
                self._event(
                    state,
                    "tool.executed",
                    "execute_tool",
                    {"tool": result.tool, "status": result.status, "summary": result.summary},
                )
                if tool.createsEvidence:
                    evidence = self.evidence_manager.create_from_tool_result(result, trace_id)
                    state.evidence.append(evidence)
                    self.store.append_evidence(evidence)
                    self._event(
                        state,
                        "evidence.created",
                        "create_evidence",
                        {"evidence_id": evidence.id, "tool": result.tool},
                    )
            elif decision.decision == PolicyDecisionKind.REQUIRE_APPROVAL:
                state.approvals.append(
                    ApprovalRecord(
                        approval_id=new_id("approval"),
                        task_id=task_id,
                        tool_call_id=proposal.id,
                        tool=proposal.tool,
                        status="pending",
                        reason=decision.reason,
                    )
                )
                self._event(
                    state,
                    "approval.requested",
                    "approval_gate",
                    {"tool": proposal.tool, "reason": decision.reason},
                )

        state.finalOutput = self._compose_output(state, use_llm=use_llm)
        self._event(state, "output.generated", "compose_answer", {"sections": list(state.finalOutput)})
        state.verificationResults = self.verifier.verify(state)
        self._event(
            state,
            "task.completed",
            "persist_trace",
            {"passed_verification": all(result.passed for result in state.verificationResults)},
        )
        state.status = RunStatus.WAITING_APPROVAL if state.approvals else RunStatus.COMPLETED
        self.store.write_state(state)
        return state

    def _use_llm(self) -> bool:
        if self.planner_mode == "deterministic":
            return False
        if self.planner_mode == "llm":
            return True
        return self.model_provider is not None

    def _select_command(self, command_id: str | None, commands: list[CommandDefinition]) -> CommandDefinition | None:
        if command_id is None:
            return None
        for command in commands:
            if command.id == command_id:
                return command
        raise ValueError(f"Command {command_id} is not available for this agent.")

    def _event(self, state: AgentState, event_type: str, node_id: str, payload: dict) -> None:
        event = RuntimeEvent(
            event_id=new_id("evt"),
            event_type=event_type,
            timestamp=utc_now(),
            trace_id=state.traceId,
            task_id=state.taskId,
            agent_id=state.agentId,
            agent_revision=state.agentRevision,
            snapshot_id=state.snapshotId,
            node_id=node_id,
            payload=payload,
        )
        self.store.append_event(event)

    def _compose_output(self, state: AgentState, use_llm: bool = False) -> dict:
        if use_llm and self.model_provider is not None:
            try:
                self._event(state, "model.used", "compose_answer", {"mode": self.planner_mode})
                return ModelAnswerComposer(self.model_provider).compose(state)
            except Exception as exc:
                self._event(
                    state,
                    "model.fallback",
                    "compose_answer",
                    {"reason": str(exc)[:500]},
                )
        evidence_refs = [evidence.id for evidence in state.evidence]
        if state.selectedSkill == "incident-triage":
            return {
                "summary": "Checkout 5xx increased shortly after the latest production deployment. Rollback is only proposed and requires approval.",
                "timeline": [
                    "v1.2.3 deployed to prod at 2026-06-23T05:02:00Z.",
                    "5xx rate began increasing around 2026-06-23T05:05:00Z.",
                    "Logs show PaymentGatewayTimeout and retry exhaustion errors.",
                ],
                "hypotheses": [
                    {
                        "claim": "The latest checkout deployment may have contributed to the 5xx spike.",
                        "confidence": "medium",
                        "evidence_refs": evidence_refs[:3],
                    }
                ],
                "evidence": evidence_refs,
                "next_actions": [
                    "Check payment gateway health.",
                    "Prepare rollback plan, but do not execute without approval.",
                    "Continue monitoring checkout.5xx_rate.",
                ],
                "evidence_refs": evidence_refs,
                "pending_approvals": [approval.tool for approval in state.approvals],
            }
        if state.selectedSkill == "coding-workflow":
            executed_tools = [result.tool for result in state.toolCalls]
            verification_tools = [tool for tool in executed_tools if tool in {"lint.run", "test.run", "repo.diff"}]
            return {
                "summary": "Coding workflow resolved repository context, proposed scoped edits through policy, and captured verification evidence.",
                "change_plan": [
                    "Inspect repository state and relevant code context.",
                    "Apply file changes only through the policy-gated patch tool.",
                    "Run lint, tests, and diff inspection before final handoff.",
                ],
                "changed_files": [],
                "verification": verification_tools,
                "evidence": evidence_refs,
                "recommendation": "Approve the proposed patch only after reviewing the intended file scope and then rerun verification.",
                "evidence_refs": evidence_refs,
                "pending_approvals": [approval.tool for approval in state.approvals],
            }
        return {
            "summary": "Research workflow completed with evidence-backed source material.",
            "comparison": [
                "Skills encode reusable workflow guidance.",
                "Tools encode executable actions and must remain governed by policy.",
                "A tools-first architecture keeps the public action model simple while allowing internal tool contracts.",
            ],
            "findings": [
                "Agentic runtime designs benefit from explicit tool contracts and policy gates.",
                "Skills should guide workflows without granting tool permissions.",
            ],
            "evidence": evidence_refs,
            "recommendation": "Keep skills lightweight and route every executable action through explicit tools, policy decisions, evidence, and audit.",
            "evidence_refs": evidence_refs,
        }
