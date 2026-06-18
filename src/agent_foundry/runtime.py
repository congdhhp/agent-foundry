from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .agent_validation import AgentDeepValidator
from .evidence import EvidenceManager
from .model_gateway import ModelGateway
from .models import AgentManifest, PolicyDecision, WorkflowNodeType
from .policy import PolicyEngine
from .registry import LocalRegistry
from .skills import SkillRegistry, SkillSelector
from .storage import LocalSessionStore, new_task_id
from .tools import ToolCall, ToolGateway


@dataclass(frozen=True)
class RuntimeOptions:
    registry_root: Path = Path(".")
    store_root: Path = Path(".agent")
    workspace: Path = Path(".")
    dry_run: bool = True
    model_provider: str | None = None
    model: str | None = None
    allow_model_calls: bool = False


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
        self.tool_gateway = ToolGateway(
            self.registry, self.options.workspace, self.options.dry_run
        )
        self.model_gateway = ModelGateway(
            provider_override=self.options.model_provider,
            model_override=self.options.model,
            allow_model_calls=self.options.allow_model_calls,
        )

    def run(self, agent_path_or_ref: str | Path, task_input: str) -> dict[str, Any]:
        task_id = new_task_id()
        agent = self.registry.load_agent(agent_path_or_ref)
        validation = self.agent_validator.validate(agent_path_or_ref)
        if not validation.valid:
            raise ValueError(f"Agent validation failed: {validation.errors}")
        workflow = self.registry.load_workflow(agent.spec.workflow)
        policy = self.registry.load_policy(agent.spec.policy)
        model_policy = (
            self.registry.load_model_policy(agent.spec.model_policy)
            if agent.spec.model_policy is not None
            else self.registry.load_model_policy("default-model-policy@1.0.0")
        )
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
            "model_policy_id": f"{model_policy.metadata.id}@{model_policy.metadata.version}",
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
            "model_outputs": [],
            "final_output": None,
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
                "model_policy": state["model_policy_id"],
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
                outcome = self._execute_model_node(
                    agent,
                    model_policy,
                    state,
                    node.id,
                    node.type.value,
                    node.config,
                )
                self._checkpoint(state, node.id)
                if outcome == "failed":
                    return self._finalize(state, outcome)
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

        result = self.tool_gateway.execute(
            ToolCall(
                task_id=state["task_id"],
                capability_ref=capability_ref,
                provider_tool=provider_tool,
                task_input=state["input"],
                prior_outputs=state["tool_outputs"],
            )
        )
        state["tool_outputs"].append(result.output)
        state["observations"].append(
            {
                "node_id": node_id,
                "capability": capability_ref,
                "provider_id": result.provider_id,
                "tool_name": result.tool_name,
                "summary": result.summary,
            }
        )
        self.store.append_event(
            state["task_id"],
            "tool.executed",
            {
                "capability": capability_ref,
                "provider_tool": provider_tool,
                "provider_id": result.provider_id,
                "tool_name": result.tool_name,
                "duration_ms": result.duration_ms,
                "success": result.success,
                "sanitized": result.sanitized,
            },
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

    def _execute_model_node(
        self,
        agent: AgentManifest,
        model_policy: Any,
        state: dict[str, Any],
        node_id: str,
        node_type: str,
        node_config: dict[str, Any],
    ) -> str:
        try:
            request = self.model_gateway.build_request(
                agent,
                model_policy,
                state,
                node_id,
                node_type,
                node_config,
            )
            self.store.append_event(
                state["task_id"],
                "model.called",
                {
                    "node_id": node_id,
                    "node_type": node_type,
                    "provider": request.provider,
                    "model": request.model,
                    "prompt_chars": len(request.prompt),
                    "dry_run": request.dry_run,
                },
            )
            response = self.model_gateway.generate(request)
            model_output = {
                "node_id": node_id,
                "node_type": node_type,
                "provider": response.provider,
                "model": response.model,
                "content": response.content,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "cost_usd": response.cost_usd,
            }
            state["model_outputs"].append(model_output)
            observation = {
                "node_id": node_id,
                "type": node_type,
                "provider": response.provider,
                "model": response.model,
                "summary": response.content,
            }
            state["observations"].append(observation)
            if node_type == WorkflowNodeType.OUTPUT_COMPOSER.value:
                state["final_output"] = response.content
            self.store.append_trace(state["task_id"], observation)
            self.store.append_event(
                state["task_id"],
                "model.completed",
                {
                    "node_id": node_id,
                    "provider": response.provider,
                    "model": response.model,
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                    "cost_usd": response.cost_usd,
                    "content_chars": len(response.content),
                },
            )
            return "running"
        except Exception as exc:  # noqa: BLE001
            state["status"] = "failed"
            self.store.append_event(
                state["task_id"],
                "model.failed",
                {
                    "node_id": node_id,
                    "node_type": node_type,
                    "error": str(exc),
                },
            )
            state["observations"].append(
                {
                    "node_id": node_id,
                    "type": node_type,
                    "summary": f"Model node failed: {exc}",
                }
            )
            return "failed"

    def _finalize(self, state: dict[str, Any], status: str) -> dict[str, Any]:
        state["status"] = status
        response = {
            "task_id": state["task_id"],
            "agent_id": state["agent_id"],
            "status": status,
            "summary": self._final_summary(state),
            "evidence": [item["evidence_id"] for item in state["evidence"]],
            "approvals": state["approvals"],
            "model_policy": state.get("model_policy_id"),
            "model_outputs": state.get("model_outputs", []),
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

    def _final_summary(self, state: dict[str, Any]) -> str:
        if state["status"] == "waiting_approval":
            return "Task paused because policy requires approval."
        if state["status"] == "denied":
            return "Task stopped because policy denied an action."
        if state["status"] == "failed":
            return "Task failed during runtime execution."
        if state.get("final_output"):
            return str(state["final_output"])
        return (
            f"Task completed with {len(state['observations'])} observations and "
            f"{len(state['evidence'])} evidence item(s)."
        )
