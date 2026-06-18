from __future__ import annotations

from pathlib import Path

from agent_foundry.agent_factory import AgentCreateRequest, AgentFactory
from agent_foundry.evals import EvalRunner
from agent_foundry.loader import dump_yaml, load_document


ROOT = Path(__file__).resolve().parents[1]


def test_eval_suite_runner_persists_report(tmp_path: Path) -> None:
    runner = EvalRunner(ROOT, tmp_path / ".agent" / "evals")

    report = runner.run_suite(
        ROOT / "examples" / "eval-suites" / "research-agent-evals.yaml",
        ROOT / "examples" / "agents" / "research-agent.yaml",
    )

    assert report.passed
    assert report.total_cases == 1
    assert report.pass_rate == 1.0
    assert Path(report.report_dir, "report.json").exists()
    assert Path(report.report_dir, "cases.jsonl").exists()
    assert runner.load_report(report.run_id)["suite_id"] == "research-agent-evals"
    assert runner.list_reports()[0]["run_id"] == report.run_id


def test_eval_suite_required_checks_can_fail(tmp_path: Path) -> None:
    suite_path = tmp_path / "strict-suite.yaml"
    suite_path.write_text(
        dump_yaml(
            {
                "apiVersion": "agents.platform/v1",
                "kind": "EvalSuite",
                "metadata": {
                    "id": "strict-research-agent-evals",
                    "version": "1.0.0",
                    "name": "Strict Research Agent Evals",
                    "owner": "test",
                },
                "spec": {
                    "cases": [str(ROOT / "examples" / "evals" / "research_basic.yaml")],
                    "passCriteria": {
                        "minPassRate": 1.0,
                        "requiredChecks": ["nonexistent_check"],
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    report = EvalRunner(ROOT, tmp_path / ".agent" / "evals").run_suite(
        suite_path,
        ROOT / "examples" / "agents" / "research-agent.yaml",
    )

    assert not report.passed
    assert report.required_check_results == {"nonexistent_check": False}
    assert "required_check:nonexistent_check did not pass" in report.failed_checks


def test_agent_publish_accepts_eval_suite_gate(tmp_path: Path) -> None:
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

    result = factory.publish(
        path,
        eval_suites=[ROOT / "examples" / "eval-suites" / "research-agent-evals.yaml"],
    )

    assert result.published
    assert result.errors == []
    assert result.eval_suite_reports[0]["passed"] is True
    assert load_document(path)["metadata"]["status"] == "published"


def test_coding_eval_suite_checks_approval_gate(tmp_path: Path) -> None:
    report = EvalRunner(ROOT, tmp_path / ".agent" / "evals").run_suite(
        ROOT / "examples" / "eval-suites" / "coding-agent-evals.yaml",
        ROOT / "examples" / "agents" / "coding-agent.yaml",
    )

    assert report.passed
    check_names = {
        check["name"]
        for case_report in report.to_dict()["case_reports"]
        for check in case_report["checks"]
    }
    assert "approval_required:shell.run@1.0" in check_names
    assert "expected_status:waiting_approval" in check_names
