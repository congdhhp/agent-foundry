from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from .models import CapabilityContractManifest, EvidenceObject, EvidenceSourceType


class EvidenceManager:
    def from_tool_result(
        self,
        task_id: str,
        capability_ref: str,
        capability: CapabilityContractManifest,
        summary: str,
        trusted: bool = True,
    ) -> EvidenceObject:
        return EvidenceObject(
            evidence_id=f"ev_{uuid4().hex[:12]}",
            task_id=task_id,
            source_type=EvidenceSourceType.TOOL_RESULT,
            source_uri=f"capability://{capability_ref}",
            capability=capability_ref,
            timestamp=datetime.now(UTC),
            sensitivity="internal",
            confidence=0.8,
            summary=summary,
            raw_ref=f"object://{task_id}/{capability.metadata.id}/{uuid4().hex[:8]}",
            trusted=trusted,
        )

