from __future__ import annotations

from pathlib import Path

from agent_foundry.core.models import CommandDefinition
from agent_foundry.io.yaml import read_yaml


class CommandLoader:
    def __init__(self, search_roots: list[str | Path]) -> None:
        self.search_roots = [Path(root) for root in search_roots]

    def load_many(self, command_ids: list[str]) -> list[CommandDefinition]:
        commands: list[CommandDefinition] = []
        for command_id in command_ids:
            command = self.load(command_id)
            if command is not None:
                commands.append(command)
        return commands

    def load(self, command_id: str) -> CommandDefinition | None:
        for root in self.search_roots:
            path = root / f"{command_id}.yaml"
            if path.exists():
                return CommandDefinition.model_validate(read_yaml(path))
        return None
