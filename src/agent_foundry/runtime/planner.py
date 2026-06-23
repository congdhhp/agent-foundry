from __future__ import annotations

from agent_foundry.core.ids import new_id
from agent_foundry.core.models import CommandDefinition, ProposedToolCall, SkillDefinition, ToolDefinition


class DeterministicPlanner:
    def plan(
        self,
        task_id: str,
        task_input: str,
        skill: SkillDefinition | None,
        command: CommandDefinition | None,
        tools: list[ToolDefinition],
    ) -> list[ProposedToolCall]:
        available = {tool.id: tool for tool in tools}
        if command and command.defaultTools:
            tool_ids = list(command.defaultTools)
        elif skill and skill.id == "incident-triage":
            tool_ids = ["deployments.read", "metrics.query", "logs.search", "runbooks.read", "deployment.rollback"]
        elif skill and skill.id == "web-research":
            tool_ids = ["web.search", "document.read", "knowledge.search", "citation.extract"]
        elif skill and skill.id == "coding-workflow":
            tool_ids = [
                "repo.status",
                "repo.map",
                "file.search",
                "file.read",
                "file.patch",
                "lint.run",
                "test.run",
                "repo.diff",
            ]
        else:
            tool_ids = []

        proposals: list[ProposedToolCall] = []
        for tool_id in tool_ids:
            tool = available.get(tool_id)
            if tool is None:
                continue
            proposals.append(
                ProposedToolCall(
                    id=new_id("call"),
                    task_id=task_id,
                    tool=tool.id,
                    action_type=tool.actionType or tool.id,
                    input=self._input_for(tool.id, task_input),
                    reason=f"Planned by {skill.id if skill else 'default'} workflow.",
                    access_type=tool.accessType,
                    risk_level=tool.riskLevel,
                )
            )
        return proposals

    def _input_for(self, tool_id: str, task_input: str) -> dict:
        if tool_id in {"deployments.read", "metrics.query", "logs.search", "runbooks.read", "deployment.rollback"}:
            base = {"service": "checkout", "environment": "prod", "task": task_input}
            if tool_id == "metrics.query":
                base["window"] = "30m"
            if tool_id == "logs.search":
                base["query"] = "service:checkout status:5xx"
            return base
        if tool_id == "web.search":
            return {"query": task_input}
        return {"query": task_input}
