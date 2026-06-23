from pathlib import Path

from agent_foundry.evals.runner import EvalRunner
from agent_foundry.io.yaml import write_yaml
from agent_foundry.manifests.agent_loader import AgentManifestLoader
from agent_foundry.manifests.factory import create_blank_agent_manifest
from agent_foundry.models.provider import GeminiGenerateContentChatModel, OpenAICompatibleChatModel, build_model_from_env
from agent_foundry.runtime.service import AgentRuntime


ROOT = Path(__file__).resolve().parents[1]


class FakeModel:
    def complete(self, messages):
        joined = "\n".join(message["content"] for message in messages)
        if "tool_calls" in joined:
            return """
            {
              "tool_calls": [
                {"tool": "deployments.read", "input": {"service": "checkout", "environment": "prod"}, "reason": "Check latest deploy."},
                {"tool": "metrics.query", "input": {"service": "checkout", "environment": "prod", "window": "30m"}, "reason": "Check error rate."},
                {"tool": "logs.search", "input": {"service": "checkout", "environment": "prod", "query": "status:5xx"}, "reason": "Inspect errors."},
                {"tool": "runbooks.read", "input": {"service": "checkout", "environment": "prod"}, "reason": "Read runbook."},
                {"tool": "deployment.rollback", "input": {"service": "checkout", "environment": "prod"}, "reason": "Risky proposed remediation."},
                {"tool": "secrets.read", "input": {}, "reason": "This must be ignored."}
              ]
            }
            """
        return """
        {
          "summary": "Model-composed incident report using evidence only.",
          "timeline": ["Deployment, metrics, logs, and runbook were reviewed."],
          "hypotheses": [{"claim": "The deploy may be correlated.", "evidence_refs": []}],
          "evidence": [],
          "next_actions": ["Do not rollback without approval."],
          "evidence_refs": [],
          "pending_approvals": ["deployment.rollback"]
        }
        """


class SparseFakeModel:
    def complete(self, messages):
        joined = "\n".join(message["content"] for message in messages)
        if "tool_calls" in joined:
            return '{"tool_calls":[{"tool":"deployments.read","input":{"service":"checkout","environment":"prod"},"reason":"Start with deploy."}]}'
        return '{"summary":"Sparse model answer","evidence_refs":[]}'


def test_incident_runtime_policy_evidence_snapshot(tmp_path):
    runtime = AgentRuntime(project_root=ROOT, store_root=tmp_path / ".agent")
    state = runtime.run(
        ROOT / "docs" / "examples" / "agents" / "incident-triage-agent.yaml",
        "Investigate checkout 5xx spike after latest deploy",
    )

    assert state.selectedSkill == "incident-triage"
    assert state.snapshotId.startswith("snap_")
    assert "deployment.rollback" in {approval.tool for approval in state.approvals}
    assert "deployment.rollback" not in {result.tool for result in state.toolCalls}
    assert {"deployments.read", "metrics.query", "logs.search"}.issubset({result.tool for result in state.toolCalls})
    assert state.evidence
    assert state.finalOutput
    assert state.finalOutput["evidence_refs"]


def test_eval_case_passes(tmp_path):
    runtime = AgentRuntime(project_root=ROOT, store_root=tmp_path / ".agent")
    result = EvalRunner(runtime).run_case(
        ROOT / "docs" / "examples" / "agents" / "incident-triage-agent.yaml",
        ROOT / "docs" / "examples" / "evals" / "incident-triage-eval.yaml",
    )

    assert result.passed


def test_blank_agent_manifest_can_be_created(tmp_path):
    manifest = create_blank_agent_manifest("my-agent", "My Agent", "Help with local tasks.")
    target = tmp_path / "my-agent.yaml"
    write_yaml(target, manifest.model_dump(mode="json", exclude_none=True))

    loaded = AgentManifestLoader().load(target)

    assert loaded.metadata.id == "my-agent"
    assert loaded.spec.skills == []
    assert loaded.spec.tools == []
    assert loaded.spec.policies == ["read-only"]


def test_llm_planner_still_uses_policy_gate(tmp_path):
    runtime = AgentRuntime(
        project_root=ROOT,
        store_root=tmp_path / ".agent",
        planner_mode="llm",
        model_provider=FakeModel(),
    )
    state = runtime.run(
        ROOT / "docs" / "examples" / "agents" / "incident-triage-agent.yaml",
        "Investigate checkout 5xx spike after latest deploy",
    )

    proposed = {call.tool for call in state.proposedToolCalls}
    called = {result.tool for result in state.toolCalls}

    assert "secrets.read" not in proposed
    assert "deployment.rollback" in proposed
    assert "deployment.rollback" not in called
    assert "deployment.rollback" in {approval.tool for approval in state.approvals}
    assert state.finalOutput
    assert state.finalOutput["evidence_refs"]


def test_model_provider_factory_supports_openai_compatible(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv("AGENT_FOUNDRY_PROVIDER", "openai-compatible")
    monkeypatch.setenv("AGENT_FOUNDRY_API_KEY", "test-key")
    monkeypatch.setenv("AGENT_FOUNDRY_MODEL", "test-model")

    provider = build_model_from_env()

    assert isinstance(provider, OpenAICompatibleChatModel)
    assert provider.model == "test-model"


def test_model_provider_factory_supports_gemini(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("AGENT_FOUNDRY_API_KEY", raising=False)
    monkeypatch.setenv("AGENT_FOUNDRY_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("AGENT_FOUNDRY_MODEL", "gemini-test")

    provider = build_model_from_env()

    assert isinstance(provider, GeminiGenerateContentChatModel)
    assert provider.model == "gemini-test"


def test_sparse_llm_plan_is_augmented_with_baseline_tools(tmp_path):
    runtime = AgentRuntime(
        project_root=ROOT,
        store_root=tmp_path / ".agent",
        planner_mode="llm",
        model_provider=SparseFakeModel(),
    )
    state = runtime.run(
        ROOT / "docs" / "examples" / "agents" / "incident-triage-agent.yaml",
        "Investigate checkout 5xx spike after latest deploy",
    )

    proposed = [call.tool for call in state.proposedToolCalls]

    assert proposed[0] == "deployments.read"
    assert {"metrics.query", "logs.search", "runbooks.read", "deployment.rollback"}.issubset(set(proposed))
    assert "deployment.rollback" not in {result.tool for result in state.toolCalls}
