from __future__ import annotations

from pathlib import Path

from agent_foundry.core.models import ToolDefinition
from agent_foundry.io.yaml import read_yaml


class ToolCatalog:
    def __init__(self, tools: dict[str, ToolDefinition]) -> None:
        self._tools = tools

    @classmethod
    def from_yaml(cls, path: str | Path) -> "ToolCatalog":
        raw = read_yaml(path)
        tools = {
            item["id"]: ToolDefinition.model_validate(item)
            for item in raw.get("tools", [])
        }
        return cls(tools)

    def get(self, tool_id: str) -> ToolDefinition | None:
        return self._tools.get(tool_id)

    def require(self, tool_id: str) -> ToolDefinition:
        tool = self.get(tool_id)
        if tool is None:
            raise KeyError(f"Tool not found: {tool_id}")
        return tool

    def subset(self, tool_ids: list[str]) -> list[ToolDefinition]:
        return [self.require(tool_id) for tool_id in tool_ids if self.get(tool_id)]

    def all(self) -> list[ToolDefinition]:
        return list(self._tools.values())
