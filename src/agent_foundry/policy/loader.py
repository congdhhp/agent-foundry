from __future__ import annotations

from pathlib import Path

from agent_foundry.core.models import PolicyDocument
from agent_foundry.io.yaml import read_yaml


class PolicyLoader:
    def __init__(self, search_roots: list[str | Path]) -> None:
        self.search_roots = [Path(root) for root in search_roots]

    def load_many(self, policy_ids: list[str]) -> list[PolicyDocument]:
        policies: list[PolicyDocument] = []
        for policy_id in policy_ids:
            policy = self.load(policy_id)
            if policy is not None:
                policies.append(policy)
        return policies

    def load(self, policy_id: str) -> PolicyDocument | None:
        for root in self.search_roots:
            path = root / f"{policy_id}.yaml"
            if path.exists():
                return PolicyDocument.model_validate(read_yaml(path))
        return None
