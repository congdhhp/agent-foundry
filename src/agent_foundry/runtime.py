from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .agent_validation import AgentDeepValidator
from .evidence import EvidenceManager
from .models import AgentManifest, PolicyDecision, WorkflowNodeType
from .policy import PolicyEngine
from .registry import LocalRegistry
from .skills import SkillRegistry, SkillSelector
from .storage import LocalSessionStore, new_task_id
from .tools import ToolExecutor


@dataclass(frozen=True)
class RuntimeOptions:
    registry_root: Path = Path(".")
    store_root: Path = Path(".agent")
    workspace: Path = Path(".")
    dry_run: bool = True


class AgentRuntime:
    def __init__(self, options: RuntimeOptions | None = None) -> None:
        self.options = options or RuntimeOptions()
        self.registry = LocalRegistry(self.options.registry_root)
        self.skill_registry = SkillRegistry(self.options.registry_root)
        self.skill_selector = SkillSelector()
        self.agent_validator = AgentDeepValidator(self.options.registry_root)
        self.store = LocalSessionStore(self.options.store_root)
        self.policy_engine = PolicyEngine()
        self.evidence_manager = EvidenceManager()
        self.tool_executor = ToolExecutor(self.options.workspace, self.options.dry_run)

    def run(self, agent_path_or_ref: str | Path, task_input: str) -> dict[str, Any]:
        task_id = new_task_id()
        agent = self.registry.load_agent(agent_path_or_ref)
        validation = self.agent_validator.validate(agent_path_or_ref)
        if not validation.valid:
            raise ValueError(f"Agent validation failed: {validation.errors}")
        workflow = self.registry.load_workflow(agent.spec.workflow)
        policy = self.registry.load_policy(agent.spec.policy)
        skill_packages = [
            self.skill_registry.load_package(skill_ref) for skill_ref in agent.spec.skills
        ]
        skill_selections = self.skill_selector.select(
            agent,
            [package.manifest for package in skill_packages],
            task_input,
        )

        state: dict[str, Any] = {
            "task_id": task_id,
            "agent_id": agent.metadata.id,
            "workflow_id": f"{workflow.id}@{workflow.version}",
            "input": task_input,
            "status": "running",
            "selected_skills": [selection.ref for selection in skill_selections],
            "skill_context": [
                {
                    "skill": package.ref,
                    "instructions": package.instructions,
                    "required_capabilities": package.manifest.requires.capabilities,
                }
                for package in skill_packages
            ],
            "skill_selection": [
                {
                    "skill": selection.ref,
                    "score": selection.score,
                    "reasons": selection.reasons,
                }
                for selection in skill_selections
            ],
            "observations": [],
            "evidence": [],
            "approvals": [],
            "tool_outputs": [],
        }

        self.store.create_session(task_id)
        self.store.append_event(
            task_id,
            "task.started",
            {"agent_id": agent.metadata.id, "input": task_input},
        )
        self.store.append_event(
            task_id,
            "skill.selected",
            {
                "skills": state["selected_skills"],
                "selection": state["skill_selection"],
            },
        )
        self.store.append_event(
            task_id,
            "runtime.context.composed",
            {
                "skills": [
                    {
                        "skill": item["skill"],
                        "required_capabilities": item["required_capabilities"],
                    }
                    for item in state["skill_context"]
                ]
            },
        )
        self._checkpoint(state, "task.started")

        for node in workflow.nodes:
            self.store.append_event(
                task_id,
                "workflow.node.started",
                {"node_id": node.id, "node_type": node.type.value},
            )

            if node.type == WorkflowNodeType.CAPABILITY_CALL:
                outcome = self._execute_capability_node(agent, policy, state, node.id, node.capability)
                self._checkpoint(state, node.id)
                if outcome in {"waiting_approval", "denied", "failed"}:
                    return self._finalize(state, outcome)
                continue

            if node.type in {
                WorkflowNodeType.LLM_REASONING,
                WorkflowNodeType.EVALUATOR,
                WorkflowNodeType.OUTPUT_COMPOSER,
            }:
                observation = {
                    "node_id": node.id,
                    "type": node.type.value,
                    "summary": self._synthetic_node_summary(node.id, node.type.value, task_input),
                }
                state["observations"].append(observation)
                self.store.append_trace(task_id, observation)
                self._checkpoint(state, node.id)
                continue

            observation = {
                "node_id": node.id,
                "type": node.type.value,
                "summary": "Node type acknowledged by Phase 1 runtime.",
            }
            state["observations"].append(observation)
            self._checkpoint(state, node.id)

        return self._finalize(state, "completed")

    def _execute_capability_node(
        self,
        agent: AgentManifest,
        policy: Any,
        state: dict[str, Any],
        node_id: str,
        capability_ref: str | None,
    ) -> str:
        if capability_ref is None:
            state["status"] = "failed"
            state["observations"].append(
                {"node_id": node_id, "summary": "Capability node missing capability."}
            )
            return "failed"

        provider_tool = agent.spec.capability_bindings.get(capability_ref)
        if provider_tool is None:
            state["status"] = "denied"
            state["observations"].append(
                {
                    "node_id": node_id,
                    "capability": capability_ref,
                    "summary": "Capability is not bound for this agent.",
                }
            )
            self.store.append_event(
                state["task_id"],
                "policy.denied",
                {"capability": capability_ref, "reason": "missing binding"},
            )
            return "denied"

        capability = self.registry.load_capability(capability_ref)
        policy_result = self.policy_engine.evaluate(policy, capability_ref, capability)
        self.store.append_event(
            state["task_id"],
            "policy.evaluated",
            {
                "capability": capability_ref,
                "decision": policy_result.decision.value,
                "reason": policy_result.reason,
            },
        )

        if policy_result.decision == PolicyDecision.DENY:
            state["status"] = "denied"
            state["observations"].append(
                {
                    "node_id": node_id,
                    "capability": capability_ref,
                    "summary": "Policy denied capability execution.",
                }
            )
            return "denied"

        if policy_result.decision == PolicyDecision.REQUIRE_APPROVAL:
            approval = {
                "approval_id": f"appr_{state['task_id']}_{node_id}",
                "task_id": state["task_id"],
                "agent_id": state["agent_id"],
                "action": capability_ref,
                "risk_level": capability.spec.risk_level.value,
                "reason": "Policy requires approval before executing this capability.",
                "status": "pending",
            }
            state["status"] = "waiting_approval"
            state["approvals"].append(approval)
            self.store.append_approval(state["task_id"], approval)
            self.store.append_event(state["task_id"], "approval.requested", approval)
            return "waiting_approval"

        result = self.tool_executor.execute(
            capability_ref,
            provider_tool,
            state["input"],
            state["tool_outputs"],
        )
        state["tool_outputs"].append(result.output)
        state["observations"].append(
            {
                "node_id": node_id,
                "capability": capability_ref,
                "summary": result.summary,
            }
        )
        self.store.append_event(
            state["task_id"],
            "tool.executed",
            {"capability": capability_ref, "provider_tool": provider_tool},
        )

        if capability.spec.evidence.creates_evidence:
            evidence = self.evidence_manager.from_tool_result(
                state["task_id"],
                capability_ref,
                capability,
                result.summary,
            )
            evidence_data = evidence.model_dump(mode="json", by_alias=True, exclude_none=True)
            state["evidence"].append(evidence_data)
            self.store.append_evidence(state["task_id"], evidence_data)
            self.store.append_event(
                state["task_id"],
                "evidence.created",
                {"evidence_id": evidence.evidence_id, "capability": capability_ref},
            )

        return "running"

    def _finalize(self, state: dict[str, Any], status: str) -> dict[str, Any]:
        state["status"] = status
        response = {
            "task_id": state["task_id"],
            "agent_id": state["agent_id"],
            "status": status,
            "summary": self._final_summary(state),
            "evidence": [item["evidence_id"] for item in state["evidence"]],
            "approvals": state["approvals"],
            "session_dir": str(self.store.session_dir(state["task_id"])),
        }
        self.store.save_artifact(state["task_id"], "final_response.json", response)
        self.store.append_event(state["task_id"], "task.completed", response)
        self._checkpoint(state, f"task.{status}")
        return response

    def _checkpoint(self, state: dict[str, Any], node_id: str) -> None:
        checkpoint_id = self.store.save_checkpoint(
            state["task_id"],
            state["workflow_id"],
            node_id,
            state,
            state["status"],
        )
        self.store.append_event(
            state["task_id"],
            "checkpoint.created",
            {"checkpoint_id": checkpoint_id, "node_id": node_id},
        )

    def _synthetic_node_summary(self, node_id: str, node_type: str, task_input: str) -> str:
        return f"{node_type} node '{node_id}' processed task: {task_input}"

    def _final_summary(self, state: dict[str, Any]) -> str:
        if state["status"] == "waiting_approval":
            return "Task paused because policy requires approval."
        if state["status"] == "denied":
            return "Task stopped because policy denied an action."
        return (
            f"Task completed with {len(state['observations'])} observations and "
            f"{len(state['evidence'])} evidence item(s)."
        )
