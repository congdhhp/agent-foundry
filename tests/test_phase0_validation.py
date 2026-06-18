from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from agent_foundry.loader import load_document
from agent_foundry.schemas import export_schema, schema_names
from agent_foundry.validation import detect_artifact_type, validate_document


ROOT = Path(__file__).resolve().parents[1]


EXAMPLE_ARTIFACTS = [
    ROOT / "examples" / "agents" / "research-agent.yaml",
    ROOT / "examples" / "agents" / "coding-agent.yaml",
    ROOT / "examples" / "agents" / "monitoring-agent.yaml",
    ROOT / "examples" / "capabilities" / "web.search.yaml",
    ROOT / "examples" / "capabilities" / "web.fetch.yaml",
    ROOT / "examples" / "capabilities" / "citation.extract.yaml",
    ROOT / "examples" / "capabilities" / "file.read.yaml",
    ROOT / "examples" / "capabilities" / "file.patch.yaml",
    ROOT / "examples" / "capabilities" / "shell.run.yaml",
    ROOT / "examples" / "capabilities" / "git.diff.yaml",
    ROOT / "examples" / "capabilities" / "metrics.query.yaml",
    ROOT / "examples" / "capabilities" / "logs.search.yaml",
    ROOT / "examples" / "capabilities" / "traces.search.yaml",
    ROOT / "examples" / "capabilities" / "deployments.read.yaml",
    ROOT / "examples" / "policies" / "read-only.yaml",
    ROOT / "examples" / "policies" / "workspace-write.yaml",
    ROOT / "examples" / "policies" / "observability-read-only.yaml",
    ROOT / "examples" / "tools" / "browser.yaml",
    ROOT / "examples" / "tools" / "workspace.yaml",
    ROOT / "examples" / "tools" / "sandbox.yaml",
    ROOT / "examples" / "tools" / "git.yaml",
    ROOT / "examples" / "tools" / "observability.yaml",
    ROOT / "examples" / "workflows" / "research_graph.yaml",
    ROOT / "examples" / "workflows" / "coding_task_graph.yaml",
    ROOT / "examples" / "workflows" / "general_reasoning_graph.yaml",
    ROOT / "examples" / "workflows" / "incident_triage_graph.yaml",
    ROOT / "examples" / "evals" / "research_basic.yaml",
    ROOT / "examples" / "evals" / "incident_triage_basic.yaml",
    ROOT / "examples" / "evidence" / "evidence-example.json",
    ROOT / "examples" / "skills" / "web-research" / "skill.yaml",
    ROOT / "examples" / "skills" / "web-research" / "evals" / "golden_cases.yaml",
    ROOT / "examples" / "skills" / "bug-fixing" / "skill.yaml",
    ROOT / "examples" / "skills" / "bug-fixing" / "evals" / "golden_cases.yaml",
    ROOT / "examples" / "skills" / "incident-triage" / "skill.yaml",
    ROOT / "examples" / "skills" / "incident-triage" / "evals" / "golden_cases.yaml",
]


@pytest.mark.parametrize("path", EXAMPLE_ARTIFACTS, ids=lambda path: path.name)
def test_example_artifacts_validate(path: Path) -> None:
    document = load_document(path)
    artifact = validate_document(document)
    assert artifact is not None


def test_detects_agent_artifact_type() -> None:
    document = load_document(ROOT / "examples" / "agents" / "research-agent.yaml")
    assert detect_artifact_type(document) == "agent"


def test_detects_skill_artifact_type() -> None:
    document = load_document(ROOT / "examples" / "skills" / "web-research" / "skill.yaml")
    assert detect_artifact_type(document) == "skill"


def test_invalid_capability_binding_is_rejected() -> None:
    document = load_document(ROOT / "examples" / "agents" / "research-agent.yaml")
    document["spec"]["capabilityBindings"]["not-a-versioned-capability"] = "browser.search"
    with pytest.raises(ValidationError):
        validate_document(document)


def test_schema_registry_exports_json_schemas() -> None:
    names = schema_names()
    assert "agent" in names
    assert "policy" in names
    schema = export_schema("agent")
    assert schema["type"] == "object"
    assert "properties" in schema

