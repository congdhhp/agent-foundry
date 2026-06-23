# CLI Command Spec

```bash
agent create <agent-id>
agent inspect <agent-id>
agent run <agent-id> "<task>"
agent trace show <task-id>
agent evidence show <task-id>

agent tools add <agent-id> <tool-id>
agent tools remove <agent-id> <tool-id>
agent tools list <agent-id>

agent skills search github "<query>"
agent skills inspect <source>
agent skills import <source> --agent <agent-id> --trust untrusted
agent skills scan <agent-id> <skill-id>
agent skills trust <agent-id> <skill-id> --level team-approved

agent commands add <agent-id> <command-id>
agent hooks add <agent-id> <hook-id>
agent eval run <agent-id> --revision <revision>
agent promote <agent-id> --revision <revision> --env production
```
