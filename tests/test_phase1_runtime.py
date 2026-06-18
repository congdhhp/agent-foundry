from __future__ import annotations

from pathlib import Path

from agent_foundry.runtime import AgentRuntime, RuntimeOptions
from agent_foundry.storage import LocalSessionStore


ROOT = Path(__file__).resolve().parents[1]


def test_research_agent_run_creates_session_evidence_and_final_response(tmp_path: Path) -> None:
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
    assert response["agent_id"] == "research-agent"
    assert len(response["evidence"]) == 3

    session_dir = Path(response["session_dir"])
    assert (session_dir / "checkpoints.sqlite").exists()
    assert (session_dir / "events.jsonl").exists()
    assert (session_dir / "evidence.jsonl").exists()
    assert (session_dir / "artifacts" / "final_response.json").exists()

    store = LocalSessionStore(tmp_path / ".agent")
    events = store.read_jsonl(response["task_id"], "events.jsonl")
    event_types = {event["event_type"] for event in events}
    assert "task.started" in event_types
    assert "tool.executed" in event_types
    assert "evidence.created" in event_types
    assert "task.completed" in event_types


def test_coding_agent_pauses_when_shell_run_requires_approval(tmp_path: Path) -> None:
    runtime = AgentRuntime(
        RuntimeOptions(
            registry_root=ROOT,
            store_root=tmp_path / ".agent",
            workspace=ROOT,
            dry_run=True,
        )
    )

    response = runtime.run(
        ROOT / "examples" / "agents" / "coding-agent.yaml",
        "Fix failing tests in the current repository.",
    )

    assert response["status"] == "waiting_approval"
    assert response["approvals"]
    assert response["approvals"][0]["action"] == "shell.run@1.0"

    store = LocalSessionStore(tmp_path / ".agent")
    approvals = store.read_jsonl(response["task_id"], "approvals.jsonl")
    assert approvals[0]["status"] == "pending"

