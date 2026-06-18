from __future__ import annotations

import json
import shutil
from pathlib import Path

from agent_foundry.agent_factory import AgentCreateRequest, AgentFactory
from agent_foundry.artifact_management import ArtifactManager
from agent_foundry.cli import main
from agent_foundry.loader import load_document


ROOT = Path(__file__).resolve().parents[1]


def _copy_registry(tmp_path: Path) -> Path:
    registry_root = tmp_path / "registry"
    shutil.copytree(ROOT / "examples", registry_root / "examples")
    return registry_root


def test_created_skill_can_be_validated_and_attached_to_agent(tmp_path: Path) -> None:
    registry_root = _copy_registry(tmp_path)
    store_root = tmp_path / ".agent"
    manager = ArtifactManager(registry_root, store_root)

    skill_dir = manager.create_skill(
        "custom-research",
        name="Custom Research",
        description="Research topics with citation evidence.",
        owner="test-user",
        capabilities=["web.search@1.0", "web.fetch@1.0", "citation.extract@1.0"],
        workflow="research_graph@1.0.0",
    )
    validation = manager.validate_artifact("skill", "custom-research@1.0.0")

    assert validation.valid
    assert skill_dir.exists()
    assert (store_root / "artifact-index" / "index.json").exists()

    agent_path = AgentFactory(registry_root, store_root).create(
        AgentCreateRequest(
            agent_id="custom-research-agent",
            name="Custom Research Agent",
            purpose="Research topics with citations.",
            owner="test-user",
            skills=["custom-research@1.0.0"],
            policy="read-only@1.0.0",
            workflow="research_graph@1.0.0",
        )
    )
    manifest = load_document(agent_path)

    assert manifest["spec"]["capabilityBindings"] == {
        "web.search@1.0": "browser.search",
        "web.fetch@1.0": "browser.fetch",
        "citation.extract@1.0": "browser.extract",
    }


def test_artifact_lifecycle_publish_deprecate_and_version(tmp_path: Path) -> None:
    registry_root = _copy_registry(tmp_path)
    store_root = tmp_path / ".agent"
    manager = ArtifactManager(registry_root, store_root)
    path = manager.create_policy(
        "local-read-only",
        allow=["web.search@1.0", "web.fetch@1.0"],
    )

    publish = manager.publish("policy", path)
    versioned = manager.version_artifact("policy", "local-read-only@1.0.0", bump="minor")
    deprecated = manager.deprecate(
        "policy",
        "local-read-only@1.0.0",
        reason="Use the minor version with updated controls.",
        replacement="local-read-only@1.1.0",
    )
    policies = manager.list_artifacts("policy")

    assert publish["published"] is True
    assert versioned["new_ref"] == "local-read-only@1.1.0"
    assert Path(versioned["path"]).exists()
    assert deprecated["deprecated"] is True
    assert any(
        policy["ref"] == "local-read-only@1.0.0"
        and policy["lifecycle_status"] == "deprecated"
        for policy in policies
    )
    assert any(
        policy["ref"] == "local-read-only@1.1.0"
        and policy["lifecycle_status"] == "draft"
        for policy in policies
    )


def test_impact_analysis_reports_referencing_agents_and_eval_suites(tmp_path: Path) -> None:
    registry_root = _copy_registry(tmp_path)
    manager = ArtifactManager(registry_root, tmp_path / ".agent")

    impact = manager.impact("skill", "web-research@1.0.0")

    assert impact["migration_required"] is True
    assert [agent["agent"] for agent in impact["referenced_by_agents"]] == [
        "research-agent"
    ]
    assert impact["dependencies"]["capabilities"] == [
        "web.search@1.0",
        "web.fetch@1.0",
        "citation.extract@1.0",
    ]
    assert impact["eval_suites"] == [
        {
            "suite": "research-agent-evals@1.0.0",
            "path": str(registry_root / "examples" / "eval-suites" / "research-agent-evals.yaml"),
        }
    ]


def test_cli_policy_and_artifact_management_smoke(
    tmp_path: Path, capsys
) -> None:
    registry_root = _copy_registry(tmp_path)
    store_root = tmp_path / ".agent"

    assert (
        main(
            [
                "policy",
                "--registry-root",
                str(registry_root),
                "--store",
                str(store_root),
                "create",
                "cli-read-policy",
                "--allow",
                "web.search@1.0",
            ]
        )
        == 0
    )
    capsys.readouterr()

    assert (
        main(
            [
                "policy",
                "--registry-root",
                str(registry_root),
                "--store",
                str(store_root),
                "simulate",
                "cli-read-policy@1.0.0",
                "--capability",
                "web.search@1.0",
            ]
        )
        == 0
    )
    simulation = json.loads(capsys.readouterr().out)

    assert simulation["decision"] == "allow"

    assert (
        main(
            [
                "artifacts",
                "--registry-root",
                str(registry_root),
                "--store",
                str(store_root),
                "list",
                "--kind",
                "policy",
            ]
        )
        == 0
    )
    policies = json.loads(capsys.readouterr().out)

    assert any(policy["ref"] == "cli-read-policy@1.0.0" for policy in policies)
