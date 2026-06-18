from __future__ import annotations

from pathlib import Path

from agent_foundry.agent_factory import AgentCreateRequest, AgentFactory
from agent_foundry.loader import load_document
from agent_foundry.runtime import AgentRuntime, RuntimeOptions


ROOT = Path(__file__).resolve().parents[1]


def test_agent_factory_creates_agent_with_auto_bindings(tmp_path: Path) -> None:
    factory = AgentFactory(ROOT, tmp_path / ".agent")

    path = factory.create(
        AgentCreateRequest(
            agent_id="my-research-agent",
            name="My Research Agent",
            purpose="Research topics with citations.",
            owner="test-user",
            skills=["web-research@1.0.0"],
            policy="read-only@1.0.0",
            workflow="research_graph@1.0.0",
        )
    )

    manifest = load_document(path)
    assert manifest["metadata"]["status"] == "draft"
    assert manifest["spec"]["capabilityBindings"] == {
        "web.search@1.0": "browser.search",
        "web.fetch@1.0": "browser.fetch",
        "citation.extract@1.0": "browser.extract",
    }


def test_agent_factory_inspect_includes_effective_composition(tmp_path: Path) -> None:
    factory = AgentFactory(ROOT, tmp_path / ".agent")
    factory.create(
        AgentCreateRequest(
            agent_id="my-research-agent",
            name="My Research Agent",
            purpose="Research topics with citations.",
            owner="test-user",
            skills=["web-research@1.0.0"],
            policy="read-only@1.0.0",
            workflow="research_graph@1.0.0",
        )
    )

    result = factory.inspect("my-research-agent")

    assert result["agent"]["status"] == "draft"
    assert result["validation"]["valid"] is True
    assert result["skills"][0]["skill"] == "web-research@1.0.0"
    assert all(binding["valid"] for binding in result["bindings"])


def test_agent_factory_publish_runs_gates_and_sets_status(tmp_path: Path) -> None:
    factory = AgentFactory(ROOT, tmp_path / ".agent")
    path = factory.create(
        AgentCreateRequest(
            agent_id="my-research-agent",
            name="My Research Agent",
            purpose="Research topics with citations.",
            owner="test-user",
            skills=["web-research@1.0.0"],
            policy="read-only@1.0.0",
            workflow="research_graph@1.0.0",
        )
    )

    result = factory.publish(path, [ROOT / "examples" / "evals" / "research_basic.yaml"])

    assert result.published
    assert result.errors == []
    assert result.eval_reports[0]["passed"] is True
    assert load_document(path)["metadata"]["status"] == "published"


def test_created_agent_can_run_through_runtime(tmp_path: Path) -> None:
    factory = AgentFactory(ROOT, tmp_path / ".agent")
    path = factory.create(
        AgentCreateRequest(
            agent_id="my-research-agent",
            name="My Research Agent",
            purpose="Research topics with citations.",
            owner="test-user",
            skills=["web-research@1.0.0"],
            policy="read-only@1.0.0",
            workflow="research_graph@1.0.0",
        )
    )

    runtime = AgentRuntime(
        RuntimeOptions(
            registry_root=ROOT,
            store_root=tmp_path / ".agent" / "sessions-store",
            workspace=ROOT,
            dry_run=True,
        )
    )
    response = runtime.run(path, "Research capability contracts")

    assert response["status"] == "completed"
    assert response["agent_id"] == "my-research-agent"
    assert len(response["evidence"]) == 3

