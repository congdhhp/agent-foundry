from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from agent_foundry.core.models import SkillDefinition


class SkillLoader:
    def __init__(self, search_roots: list[str | Path]) -> None:
        self.search_roots = [Path(root) for root in search_roots]

    def load_many(self, skill_ids: list[str]) -> list[SkillDefinition]:
        return [self.load(skill_id) for skill_id in skill_ids]

    def load(self, skill_id: str) -> SkillDefinition:
        for root in self.search_roots:
            candidates = [
                root / skill_id / "SKILL.md",
                root / f"{skill_id}.md",
            ]
            for path in candidates:
                if path.exists():
                    return self._parse(path, skill_id)
        return SkillDefinition(id=skill_id, name=skill_id, source_path=None)

    def _parse(self, path: Path, fallback_id: str) -> SkillDefinition:
        text = path.read_text(encoding="utf-8")
        metadata: dict[str, Any] = {}
        body = text
        if text.startswith("---"):
            _, frontmatter, body = text.split("---", 2)
            metadata = yaml.safe_load(frontmatter) or {}
        name = str(metadata.get("name") or fallback_id)
        return SkillDefinition(
            id=name,
            name=name,
            description=str(metadata.get("description") or ""),
            body=body.strip(),
            source_path=str(path),
        )
