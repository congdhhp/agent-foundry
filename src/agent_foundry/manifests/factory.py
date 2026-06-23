from __future__ import annotations

from agent_foundry.core.models import AgentManifest


def create_blank_agent_manifest(agent_id: str, name: str | None, purpose: str) -> AgentManifest:
    return AgentManifest.model_validate(
        {
            "apiVersion": "agents.platform/v1",
            "kind": "Agent",
            "metadata": {
                "id": agent_id,
                "name": name or agent_id,
                "owner": "local",
            },
            "spec": {
                "profile": {
                    "purpose": purpose,
                },
                "instructions": ["Be clear and safe."],
                "guidanceFiles": ["AGENTS.md"],
                "skills": [],
                "commands": [],
                "tools": [],
                "policies": ["read-only"],
                "memoryScopes": ["session", "task"],
                "modelPolicy": "default",
            },
        }
    )
