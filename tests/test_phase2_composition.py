from __future__ import annotations

from pathlib import Path

from agent_foundry.agent_validation import AgentDeepValidator
from agent_foundry.evals import EvalRunner
from agent_foundry.loader import load_document
from agent_foundry.runtime import AgentRuntime, RuntimeOptions
from agent_foundry.skills import SkillRegistry, SkillSelector
from agent_foundry.validation import validate_document


ROOT = Path(__file__).resolve().parents[1]


def test_skill_registry_lists_and_validates_packages() -> None:
    registry = SkillRegistry(ROOT)
    packages = registry.list_packages()
    refs = {package.ref for package in packages}

    assert "web-research@1.0.0" in refs
    assert "bug-fixing@1.0.0" in refs
    assert "incident-triage@1.0.0" in refs

    result = registry.validate_package("incident-triage@1.0.0")
    assert result.valid
    assert result.skill_ref == "incident-triage@1.0.0"


def test_skill_selector_scores_agent_default_and_keywords() -> None:
    agent = validate_document(
        load_document(ROOT / "examples" / "agents" / "monitoring-agent.yaml"),
        "agent",
    )
    skill = SkillRegistry(ROOT).load_package("incident-triage@1.0.0").manifest

    selections = SkillSelector().select(
        agent,
        [skill],
        "Investigate incident latency spike in checkout.",
    )

    assert selections[0].ref == "incident-triage@1.0.0"
    assert "agent_manifest" in selections[0].reasons
    assert any(reason.startswith("keyword:") for reason in selections[0].reasons)


def test_agent_deep_validation_checks_required_capability_bindings() -> None:
    result = AgentDeepValidator(ROOT).validate(
        ROOT / "examples" / "agents" / "monitoring-agent.yaml"
    )

    assert result.valid
    assert result.errors == []


def test_monitoring_agent_runs_incident_triage_workflow(tmp_path: Path) -> None:
    runtime = AgentRuntime(
        RuntimeOptions(
            registry_root=ROOT,
            store_root=tmp_path / ".agent",
            workspace=ROOT,
            dry_run=True,
        )
    )

    response = runtime.run(
        ROOT / "examples" / "agents" / "monitoring-agent.yaml",
        "Investigate checkout latency spike after latest deploy.",
    )

    assert response["status"] == "completed"
    assert response["agent_id"] == "monitoring-agent"
    assert len(response["evidence"]) == 4


def test_eval_runner_checks_research_tool_trajectory(tmp_path: Path) -> None:
    report = EvalRunner(ROOT, tmp_path / ".agent" / "evals").run(
        ROOT / "examples" / "evals" / "research_basic.yaml",
        ROOT / "examples" / "agents" / "research-agent.yaml",
    )

    assert report.passed
    assert {check.name for check in report.checks} >= {
        "selected_skill:web-research@1.0.0",
        "must_call:web.search@1.0",
        "must_call:web.fetch@1.0",
        "must_call:citation.extract@1.0",
    }

