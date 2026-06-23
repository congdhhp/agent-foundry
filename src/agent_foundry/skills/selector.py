from __future__ import annotations

from agent_foundry.core.models import AgentManifest, CommandDefinition, SkillDefinition


class SkillSelector:
    def select(
        self,
        task_input: str,
        manifest: AgentManifest,
        skills: list[SkillDefinition],
        command: CommandDefinition | None = None,
    ) -> SkillDefinition | None:
        if command and command.skill:
            return self._find(skills, command.skill)

        lowered = task_input.lower()
        if any(term in lowered for term in ["incident", "5xx", "outage", "latency", "spike", "deploy"]):
            return self._find(skills, "incident-triage")
        if any(term in lowered for term in ["research", "compare", "source", "report"]):
            return self._find(skills, "web-research")
        if skills:
            return skills[0]
        return None

    def _find(self, skills: list[SkillDefinition], skill_id: str) -> SkillDefinition | None:
        for skill in skills:
            if skill.id == skill_id or skill.name == skill_id:
                return skill
        return None
