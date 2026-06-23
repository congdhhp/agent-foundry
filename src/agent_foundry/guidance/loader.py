from __future__ import annotations

from pathlib import Path


class GuidanceLoader:
    def __init__(self, project_root: str | Path) -> None:
        self.project_root = Path(project_root)

    def load(self, guidance_files: list[str]) -> list[str]:
        loaded: list[str] = []
        for name in guidance_files:
            path = self.project_root / name
            if path.exists():
                loaded.append(path.read_text(encoding="utf-8"))
        return loaded
