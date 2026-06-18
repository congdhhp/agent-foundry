from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_foundry.cli import main
from agent_foundry.loader import load_document
from agent_foundry.model_gateway import ModelGateway
from agent_foundry.runtime import AgentRuntime, RuntimeOptions
from agent_foundry.storage import LocalSessionStore
from agent_foundry.validation import validate_document


ROOT = Path(__file__).resolve().parents[1]


def test_model_policy_artifact_validates() -> None:
    artifact = validate_document(
        load_document(ROOT / "examples" / "model-policies" / "default-model-policy.yaml")
    )

    assert artifact.metadata.id == "default-model-policy"
    assert artifact.spec.default_provider == "deterministic"
    assert "deterministic-local" in artifact.spec.allowed_models


def test_runtime_emits_model_events_and_outputs(tmp_path: Path) -> None:
    runtime = AgentRuntime(
        RuntimeOptions(
            registry_root=ROOT,
            store_root=tmp_path / ".agent",
            workspace=ROOT,
            dry_run=True,
        )
    )

    response = runtime.run(
        ROOT / "examples" / "agents" / "research-agent.yaml",
        "Compare capability contracts with direct tool binding.",
    )

    assert response["status"] == "completed"
    assert response["model_policy"] == "default-model-policy@1.0.0"
    assert response["model_outputs"]
    assert response["summary"].startswith("Final response for task")

    store = LocalSessionStore(tmp_path / ".agent")
    events = store.read_jsonl(response["task_id"], "events.jsonl")
    event_types = [event["event_type"] for event in events]
    assert "model.called" in event_types
    assert "model.completed" in event_types
    assert "model.failed" not in event_types


def test_model_gateway_enforces_model_policy() -> None:
    model_policy = validate_document(
        {
            "apiVersion": "agents.platform/v1",
            "kind": "ModelPolicy",
            "metadata": {
                "id": "deterministic-only",
                "version": "1.0.0",
                "name": "Deterministic Only",
                "owner": "test",
            },
            "spec": {
                "defaultProvider": "deterministic",
                "defaultModel": "deterministic-local",
                "allowedProviders": ["deterministic"],
                "allowedModels": ["deterministic-local"],
            },
        },
        "model-policy",
    )
    agent = validate_document(
        load_document(ROOT / "examples" / "agents" / "research-agent.yaml"),
        "agent",
    )
    gateway = ModelGateway(
        provider_override="openai",
        model_override="gpt-4.1-mini",
        allow_model_calls=True,
    )

    with pytest.raises(ValueError, match="not allowed"):
        gateway.build_request(
            agent,
            model_policy,
            {
                "task_id": "task_test",
                "input": "hello token=abc123456789",
                "selected_skills": [],
                "skill_context": [],
                "observations": [],
                "evidence": [],
                "tool_outputs": [],
                "approvals": [],
            },
            "reason",
            "llm_reasoning",
            {},
        )


def test_cli_run_accepts_model_options(tmp_path: Path, capsys) -> None:
    result = main(
        [
            "run",
            str(ROOT / "examples" / "agents" / "research-agent.yaml"),
            "Research capability contracts",
            "--store",
            str(tmp_path / ".agent"),
            "--model-provider",
            "deterministic",
            "--model",
            "deterministic-local",
        ]
    )
    output = json.loads(capsys.readouterr().out)

    assert result == 0
    assert output["status"] == "completed"
    assert output["model_outputs"][0]["provider"] == "deterministic"
