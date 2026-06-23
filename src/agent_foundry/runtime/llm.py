from __future__ import annotations

import json
import re
from typing import Any

from pydantic import ValidationError

from agent_foundry.core.ids import new_id
from agent_foundry.core.models import (
    AgentState,
    CommandDefinition,
    ProposedToolCall,
    SkillDefinition,
    ToolDefinition,
)
from agent_foundry.models.provider import ChatModel
from agent_foundry.runtime.planner import DeterministicPlanner


class ModelPlanner:
    def __init__(self, model: ChatModel, fallback: DeterministicPlanner | None = None) -> None:
        self.model = model
        self.fallback = fallback or DeterministicPlanner()

    def plan(
        self,
        task_id: str,
        task_input: str,
        skill: SkillDefinition | None,
        command: CommandDefinition | None,
        tools: list[ToolDefinition],
        guidance: list[str],
    ) -> list[ProposedToolCall]:
        prompt = self._planner_prompt(task_input, skill, command, tools, guidance)
        baseline = self.fallback.plan(task_id, task_input, skill, command, tools)
        try:
            raw = self.model.complete(prompt)
            data = extract_json_object(raw)
            proposals = self._parse_tool_calls(task_id, data, tools)
            return merge_with_baseline(proposals, baseline)
        except Exception:
            return baseline

    def _planner_prompt(
        self,
        task_input: str,
        skill: SkillDefinition | None,
        command: CommandDefinition | None,
        tools: list[ToolDefinition],
        guidance: list[str],
    ) -> list[dict[str, str]]:
        tool_specs = [
            {
                "id": tool.id,
                "description": tool.description,
                "accessType": tool.accessType,
                "riskLevel": tool.riskLevel,
                "createsEvidence": tool.createsEvidence,
                "requiresApproval": tool.requiresApproval,
            }
            for tool in tools
        ]
        context = {
            "task": task_input,
            "selected_skill": skill.id if skill else None,
            "selected_command": command.id if command else None,
            "available_tools": tool_specs,
            "skill_description": skill.description if skill else "",
            "skill_workflow": (skill.body[:2500] if skill else ""),
            "guidance": "\n\n".join(guidance)[:2500],
        }
        return [
            {
                "role": "system",
                "content": (
                    "You are a planning node inside Agent Foundry. "
                    "Return JSON only. You may only propose tools from available_tools. "
                    "Do not execute tools, do not approve tools, and do not invent tool IDs. "
                    "Schema: {\"tool_calls\":[{\"tool\":\"tool.id\",\"input\":{},\"reason\":\"why\"}]}"
                ),
            },
            {"role": "user", "content": json.dumps(context, default=str)},
        ]

    def _parse_tool_calls(
        self,
        task_id: str,
        data: dict[str, Any],
        tools: list[ToolDefinition],
    ) -> list[ProposedToolCall]:
        by_id = {tool.id: tool for tool in tools}
        proposals: list[ProposedToolCall] = []
        for item in data.get("tool_calls", [])[:8]:
            if not isinstance(item, dict):
                continue
            tool_id = item.get("tool")
            tool = by_id.get(tool_id)
            if tool is None:
                continue
            try:
                proposals.append(
                    ProposedToolCall(
                        id=new_id("call"),
                        task_id=task_id,
                        tool=tool.id,
                        action_type=tool.actionType or tool.id,
                        input=item.get("input") if isinstance(item.get("input"), dict) else {},
                        reason=str(item.get("reason") or "Planned by model."),
                        access_type=tool.accessType,
                        risk_level=tool.riskLevel,
                    )
                )
            except ValidationError:
                continue
        return proposals


class ModelAnswerComposer:
    def __init__(self, model: ChatModel) -> None:
        self.model = model

    def compose(self, state: AgentState) -> dict[str, Any]:
        required_sections = self._required_sections(state.selectedSkill)
        evidence = [
            {"id": item.id, "tool": item.tool, "summary": item.summary, "confidence": item.confidence}
            for item in state.evidence
        ]
        tool_results = [
            {"tool": result.tool, "summary": result.summary, "output": result.output}
            for result in state.toolCalls
        ]
        prompt = [
            {
                "role": "system",
                "content": (
                    "You are an evidence-grounded answer composer inside Agent Foundry. "
                    "Return JSON only. Use only the provided evidence and tool results. "
                    "Every important claim must include evidence IDs. "
                    "Never claim that a pending approval action was executed."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "task": state.input,
                        "selected_skill": state.selectedSkill,
                        "required_sections": required_sections,
                        "evidence": evidence,
                        "tool_results": tool_results,
                        "pending_approvals": [approval.tool for approval in state.approvals],
                    },
                    default=str,
                ),
            },
        ]
        raw = self.model.complete(prompt)
        data = extract_json_object(raw)
        return ensure_required_output_shape(data, state, required_sections)

    def _required_sections(self, selected_skill: str | None) -> list[str]:
        if selected_skill == "incident-triage":
            return ["summary", "timeline", "hypotheses", "evidence", "next_actions", "evidence_refs", "pending_approvals"]
        if selected_skill == "web-research":
            return ["summary", "comparison", "findings", "evidence", "recommendation", "evidence_refs"]
        return ["summary", "evidence_refs"]


def extract_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?", "", stripped).strip()
        stripped = re.sub(r"```$", "", stripped).strip()
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
        if match is None:
            raise
        data = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise ValueError("Expected model to return a JSON object.")
    return data


def ensure_required_output_shape(data: dict[str, Any], state: AgentState, required_sections: list[str]) -> dict[str, Any]:
    output = dict(data)
    evidence_refs = [item.id for item in state.evidence]
    output.setdefault("summary", "Completed with evidence-backed results.")
    output.setdefault("evidence_refs", evidence_refs)
    if not output["evidence_refs"]:
        output["evidence_refs"] = evidence_refs
    output.setdefault("evidence", evidence_refs)
    output.setdefault("pending_approvals", [approval.tool for approval in state.approvals])
    for section in required_sections:
        output.setdefault(section, [] if section not in {"summary", "recommendation"} else "")
    return output


def merge_with_baseline(
    model_proposals: list[ProposedToolCall],
    baseline: list[ProposedToolCall],
) -> list[ProposedToolCall]:
    """Keep model ordering, then add baseline tools the model omitted.

    Skills encode required workflow coverage for the MVP reference agents. This
    keeps LLM planning useful without letting a sparse plan skip critical evidence
    collection steps such as metrics/logs/runbooks.
    """

    merged = list(model_proposals)
    seen = {proposal.tool for proposal in merged}
    for proposal in baseline:
        if proposal.tool not in seen:
            merged.append(proposal)
            seen.add(proposal.tool)
    return merged
