# Behavior: Profile, Instructions, Guidance, Skills, Commands

## Agent Profile

Defines identity, purpose, owner, domain, and modes.

## Instructions

Always-on system/application behavior.

## Guidance Files

Developer-native project context files:

```text
AGENTS.md
CLAUDE.md
GEMINI.md
.agent/guidance/*.md
```

Recommended canonical file:

```text
AGENTS.md
```

Compatibility files may import or mirror it.

## Skills

Reusable workflow packages. MVP requires only `SKILL.md`.

```text
skills/incident-triage/SKILL.md
```

## Commands

User-facing workflow shortcuts.

Examples:

```text
/debug-incident
/review-pr
/write-postmortem
/security-audit
```

Commands may bind default skill, workflow, tools, output schema, and eval profile.
