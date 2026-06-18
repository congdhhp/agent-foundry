from __future__ import annotations

from pathlib import Path
import shutil

from agent_foundry.loader import dump_yaml, load_document
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


def test_paused_task_can_be_approved_and_resumed(tmp_path: Path) -> None:
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
    approval = response["approvals"][0]

    runtime.store.set_approval_status(
        response["task_id"],
        approval["approval_id"],
        "approved",
        "test-user",
    )
    resumed = runtime.resume(response["task_id"])

    assert resumed["status"] == "completed"
    assert resumed["approvals"][0]["status"] == "approved"


def test_workflow_edges_define_execution_order(tmp_path: Path) -> None:
    registry_root = tmp_path / "registry"
    shutil.copytree(ROOT / "examples", registry_root / "examples")
    workflow_path = registry_root / "examples" / "workflows" / "edge_graph.yaml"
    workflow_path.write_text(
        dump_yaml(
            {
                "id": "edge_graph",
                "version": "1.0.0",
                "runtime": "langgraph",
                "state_schema": "AgentState",
                "nodes": [
                    {"id": "compose", "type": "output_composer"},
                    {"id": "reason", "type": "llm_reasoning"},
                ],
                "edges": [{"source": "reason", "target": "compose"}],
            }
        ),
        encoding="utf-8",
    )
    agent_path = registry_root / "examples" / "agents" / "research-agent.yaml"
    agent_manifest = load_document(agent_path)
    agent_manifest["spec"]["skills"] = []
    agent_manifest["spec"]["workflow"] = "edge_graph@1.0.0"
    agent_manifest["spec"]["capabilityBindings"] = {}
    agent_path.write_text(dump_yaml(agent_manifest), encoding="utf-8")

    runtime = AgentRuntime(
        RuntimeOptions(
            registry_root=registry_root,
            store_root=tmp_path / ".agent",
            workspace=registry_root,
            dry_run=True,
        )
    )
    response = runtime.run(agent_path, "Reason then compose")
    events = runtime.store.read_jsonl(response["task_id"], "events.jsonl")
    started = [
        event["payload"]["node_id"]
        for event in events
        if event["event_type"] == "workflow.node.started"
    ]

    assert started == ["reason", "compose"]
