from __future__ import annotations

import json
from pathlib import Path

from agent_foundry.agent_factory import AgentCreateRequest, AgentFactory
from agent_foundry.cli import main
from agent_foundry.loader import load_document
from agent_foundry.registry import LocalRegistry
from agent_foundry.tool_providers import ToolProviderRegistry
from agent_foundry.tools import ToolCall, ToolGateway


ROOT = Path(__file__).resolve().parents[1]


def test_capability_provider_discovery_lists_matching_provider_tools() -> None:
    matches = ToolProviderRegistry(ROOT).providers_for_capability("web.search@1.0")

    assert [match.provider_tool for match in matches] == ["browser.search"]
    assert matches[0].protocol == "in_process"
    assert matches[0].transport == "local"


def test_provider_health_and_compatibility_cover_mcp_stdio_provider() -> None:
    registry = ToolProviderRegistry(ROOT)

    health = registry.health("knowledge-mcp")
    compatibility = registry.compatibility("knowledge-mcp", "document.read@1.0")

    assert health.healthy
    assert health.protocol == "mcp"
    assert any(check.name == "mcp_stdio_command" for check in health.checks)
    assert compatibility.compatible
    assert compatibility.errors == []
    assert compatibility.checked[0]["provider_tool"] == "knowledge-mcp.read_document"


def test_tool_gateway_dry_runs_external_mcp_provider() -> None:
    gateway = ToolGateway(LocalRegistry(ROOT), workspace=ROOT, dry_run=True)

    result = gateway.execute(
        ToolCall(
            task_id="task_test",
            capability_ref="document.read@1.0",
            provider_tool="knowledge-mcp.read_document",
            task_input="Read onboarding document",
            prior_outputs=[],
        )
    )

    assert result.success
    assert result.provider_id == "knowledge-mcp"
    assert result.output["metadata"]["dry_run"] is True
    assert result.output["metadata"]["protocol"] == "mcp"
    assert result.output["metadata"]["transport"] == "stdio"


def test_cli_capability_providers_returns_provider_tool(capsys) -> None:
    exit_code = main(["capability", "providers", "document.read@1.0"])
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output[0]["provider_tool"] == "knowledge-mcp.read_document"


def test_cli_provider_health_returns_structured_checks(capsys) -> None:
    exit_code = main(["provider", "health", "knowledge-mcp"])
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output["healthy"] is True
    assert output["protocol"] == "mcp"
    assert {check["name"] for check in output["checks"]} >= {
        "enabled",
        "endpoint_configured",
        "mcp_stdio_command",
    }


def test_cli_agent_bind_tool_updates_local_agent_manifest(
    tmp_path: Path,
    capsys,
) -> None:
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

    exit_code = main(
        [
            "agent",
            "--registry-root",
            str(ROOT),
            "--store",
            str(tmp_path / ".agent"),
            "bind-tool",
            "my-research-agent",
            "--capability",
            "web.fetch@1.0",
            "--provider",
            "browser",
            "--tool",
            "fetch",
        ]
    )
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output["bound"] is True
    assert load_document(path)["spec"]["capabilityBindings"]["web.fetch@1.0"] == (
        "browser.fetch"
    )
