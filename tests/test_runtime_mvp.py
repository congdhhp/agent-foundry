from pathlib import Path

from agent_foundry.evals.runner import EvalRunner
from agent_foundry.io.yaml import write_yaml
from agent_foundry.manifests.agent_loader import AgentManifestLoader
from agent_foundry.manifests.factory import create_blank_agent_manifest
from agent_foundry.runtime.service import AgentRuntime


ROOT = Path(__file__).resolve().parents[1]


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
