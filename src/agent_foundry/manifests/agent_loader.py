from __future__ import annotations

from pathlib import Path

from agent_foundry.core.models import AgentManifest
from agent_foundry.io.yaml import read_yaml


class AgentManifestLoader:
    def load(self, path: str | Path) -> AgentManifest:
        return AgentManifest.model_validate(read_yaml(path))
