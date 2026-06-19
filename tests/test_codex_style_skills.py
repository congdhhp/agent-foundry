from __future__ import annotations

import json
from pathlib import Path

from agent_foundry.agent_factory import AgentCreateRequest, AgentFactory
from agent_foundry.cli import main
from agent_foundry.loader import load_document
from agent_foundry.runtime import AgentRuntime, RuntimeOptions
from agent_foundry.skills import SkillRegistry, SkillSelector
from agent_foundry.validation import validate_document


ROOT = Path(__file__).resolve().parents[1]


def test_skill_registry_loads_instruction_only_repo_skill(tmp_path: Path) -> None:
    skill_dir = tmp_path / ".agents" / "skills" / "local-operator"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        """---
name: local-operator
description: Use when installing software or operating a local computer safely.
---

# Local Operator

Plan local computer operations and ask for approval before risky actions.
""",
        encoding="utf-8",
    )

    registry = SkillRegistry(tmp_path, tmp_path / ".agent")
    package = registry.load_package("local-operator@1.0.0")
    validation = registry.validate_package("local-operator@1.0.0")

    assert package.ref == "local-operator@1.0.0"
    assert package.manifest.requires.capabilities == []
    assert package.frontmatter["name"] == "local-operator"
    assert validation.valid
    assert "Missing governance sidecar: skill.yaml" in validation.warnings


def test_skill_selector_implicitly_matches_skill_description(tmp_path: Path) -> None:
    skill_dir = tmp_path / ".agents" / "skills" / "local-operator"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        """---
name: local-operator
description: Use when installing software or operating a local computer safely.
---

# Local Operator
""",
        encoding="utf-8",
    )
    skill = SkillRegistry(tmp_path, tmp_path / ".agent").load_package(
        "local-operator@1.0.0"
    ).manifest
    agent = validate_document(
        {
            "apiVersion": "agents.platform/v1",
            "kind": "Agent",
            "metadata": {
                "id": "general-agent",
                "name": "General Agent",
                "owner": "test",
            },
            "spec": {
                "template": "generic-task-agent@1.0.0",
                "purpose": "General local assistance.",
                "skills": [],
                "capabilityBindings": {},
                "policy": "read-only@1.0.0",
                "workflow": "general_reasoning_graph@1.0.0",
            },
        },
        "agent",
    )

    selections = SkillSelector().select(
        agent,
        [skill],
        "Help with installing software safely.",
    )

    assert selections[0].ref == "local-operator@1.0.0"
    assert "description_match" in selections[0].reasons


def test_general_agent_without_skills_can_run_reasoning_workflow(tmp_path: Path) -> None:
    factory = AgentFactory(ROOT, tmp_path / ".agent")
    path = factory.create(
        AgentCreateRequest(
            agent_id="general-agent",
            name="General Agent",
            purpose="Answer general questions safely.",
            owner="test-user",
            policy="read-only@1.0.0",
            workflow="general_reasoning_graph@1.0.0",
        )
    )
    runtime = AgentRuntime(
        RuntimeOptions(
            registry_root=ROOT,
            store_root=tmp_path / ".agent" / "sessions",
            workspace=ROOT,
            dry_run=True,
        )
    )

    response = runtime.run(path, "Explain what an agent skill is.")

    assert response["status"] == "completed"
    assert response["agent_id"] == "general-agent"


def test_cli_agent_create_accepts_direct_capability_without_skill(
    tmp_path: Path,
    capsys,
) -> None:
    exit_code = main(
        [
            "agent",
            "--registry-root",
            str(ROOT),
            "--store",
            str(tmp_path / ".agent"),
            "create",
            "local-operator",
            "--name",
            "Local Operator",
            "--purpose",
            "Operate this computer with approval gates.",
            "--policy",
            "workspace-write@1.0.0",
            "--workflow",
            "general_reasoning_graph@1.0.0",
            "--capability",
            "shell.run@1.0",
        ]
    )
    output = json.loads(capsys.readouterr().out)
    manifest = load_document(output["path"])

    assert exit_code == 0
    assert manifest["spec"]["skills"] == []
    assert manifest["spec"]["capabilityBindings"]["shell.run@1.0"] == (
        "sandbox.run_command"
    )
