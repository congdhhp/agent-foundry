from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ArtifactRef:
    id: str
    version: str

    @classmethod
    def parse(cls, value: str) -> ArtifactRef:
        if "@" not in value:
            raise ValueError(f"Artifact reference must include '@': {value}")
        artifact_id, version = value.rsplit("@", 1)
        if not artifact_id or not version:
            raise ValueError(f"Invalid artifact reference: {value}")
        return cls(id=artifact_id, version=version)

    def matches(self, candidate_id: str, candidate_version: str) -> bool:
        if self.id != candidate_id:
            return False
        return candidate_version == self.version or candidate_version.startswith(
            f"{self.version}."
        )

    def __str__(self) -> str:
        return f"{self.id}@{self.version}"
