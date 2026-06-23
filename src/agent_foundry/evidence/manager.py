from __future__ import annotations

from agent_foundry.core.ids import new_id
from agent_foundry.core.models import Evidence, ToolResult
from agent_foundry.core.time import utc_now


class EvidenceManager:
    def create_from_tool_result(self, result: ToolResult, trace_id: str) -> Evidence:
        return Evidence(
            id=new_id("ev"),
            task_id=result.task_id,
            trace_id=trace_id,
            source_type="tool_result",
            source_uri=f"{result.tool}://{result.call_id}",
            tool=result.tool,
            summary=result.summary,
            raw_ref=result.raw_ref,
            sensitivity="internal",
            confidence=0.87,
            created_at=utc_now(),
        )
