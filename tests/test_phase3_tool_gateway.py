from __future__ import annotations

from pathlib import Path

from agent_foundry.evals import EvalRunner
from agent_foundry.registry import LocalRegistry
from agent_foundry.runtime import AgentRuntime, RuntimeOptions
from agent_foundry.tool_providers import ToolProviderRegistry
from agent_foundry.tools import OutputSanitizer, ToolCall, ToolGateway


ROOT = Path(__file__).resolve().parents[1]


def test_tool_provider_registry_validates_contracts() -> None:
    result = ToolProviderRegistry(ROOT).validate_all()

    assert result.valid
    assert result.errors == []


def test_tool_bindings_for_research_agent_resolve_to_providers() -> None:
    agent = LocalRegistry(ROOT).load_agent(ROOT / "examples" / "agents" / "research-agent.yaml")
    bindings = ToolProviderRegistry(ROOT).bindings_for_agent(agent)

    assert bindings
    assert all(binding.valid for binding in bindings)
    assert {binding.provider_id for binding in bindings} == {"browser"}


def test_tool_gateway_sanitizes_secret_like_output() -> None:
    sanitizer = OutputSanitizer()
    provider = LocalRegistry(ROOT).load_tool_provider("browser")

    output, sanitized = sanitizer.sanitize(
        {"content": "token=abc123456789 password=hunter2", "metadata": {}},
        provider.spec.output_sanitization,
    )

    assert sanitized
    assert "[REDACTED]" in output["content"]
    assert output["metadata"]["sanitized"] is True
    assert output["metadata"]["trusted"] is False


def test_tool_gateway_executes_provider_bound_call() -> None:
    gateway = ToolGateway(LocalRegistry(ROOT), workspace=ROOT, dry_run=True)

    result = gateway.execute(
        ToolCall(
            task_id="task_test",
            capability_ref="web.search@1.0",
            provider_tool="browser.search",
            task_input="Research capability contracts",
            prior_outputs=[],
        )
    )

    assert result.success
    assert result.provider_id == "browser"
    assert result.tool_name == "search"
    assert result.output["metadata"]["sanitized"] is True


def test_runtime_tool_events_include_provider_metadata(tmp_path: Path) -> None:
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
        "Research capability contracts",
    )

    events = runtime.store.read_jsonl(response["task_id"], "events.jsonl")
    tool_events = [event["payload"] for event in events if event["event_type"] == "tool.executed"]
    assert tool_events
    assert tool_events[0]["provider_id"] == "browser"
    assert tool_events[0]["provider_tool"] == "browser.search"
    assert tool_events[0]["sanitized"] is True


def test_eval_runner_checks_provider_trajectory(tmp_path: Path) -> None:
    report = EvalRunner(ROOT, tmp_path / ".agent" / "evals").run(
        ROOT / "examples" / "evals" / "research_basic.yaml",
        ROOT / "examples" / "agents" / "research-agent.yaml",
    )

    assert report.passed
    assert any(check.name.startswith("provider_must_call:") for check in report.checks)

