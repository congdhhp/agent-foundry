from __future__ import annotations

import json
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from agent_foundry.storage.local_store import LocalStore


def run_tui(store_root: Path) -> None:
    """Run a lightweight local operations console.

    If Textual is installed this function can grow into a full-screen app. The MVP
    fallback is intentionally dependency-light and still supports interactive
    inspection of runs, traces, and evidence.
    """

    console = Console()
    store = LocalStore(store_root)
    while True:
        console.clear()
        console.print(Panel("[bold]Agent Foundry[/bold]\nLocal governed-agent operations console"))
        sessions = list(store.list_sessions())
        table = Table(title="Runs")
        table.add_column("#")
        table.add_column("Task")
        table.add_column("Status")
        table.add_column("Agent")
        for index, session in enumerate(sessions, start=1):
            state_path = session / "state.json"
            state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
            table.add_row(
                str(index),
                session.name,
                str(state.get("status", "")),
                str(state.get("agentId", "")),
            )
        console.print(table)
        choice = Prompt.ask("Select run number, or q to quit", default="q")
        if choice.lower() == "q":
            return
        if not choice.isdigit() or int(choice) < 1 or int(choice) > len(sessions):
            continue
        _show_run(console, store, sessions[int(choice) - 1].name)
        Prompt.ask("Press Enter to return", default="")


def _show_run(console: Console, store: LocalStore, task_id: str) -> None:
    console.clear()
    state_path = store.session_dir(task_id) / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    events = store.read_events(task_id)
    evidence = store.read_evidence(task_id)
    console.print(
        Panel(
            f"[bold]Agent[/bold] {state.get('agentId', '-')}\n"
            f"[bold]Snapshot[/bold] {state.get('snapshotId', '-')}\n"
            f"[bold]Selected skill[/bold] {state.get('selectedSkill', '-')}\n"
            f"[bold]Status[/bold] {state.get('status', '-')}",
            title="Run",
        )
    )
    table = Table(title=f"Trace {task_id}")
    table.add_column("Event")
    table.add_column("Node")
    table.add_column("Payload")
    for event in events:
        table.add_row(event["event_type"], str(event.get("node_id") or ""), str(event.get("payload") or ""))
    console.print(table)
    ev_table = Table(title="Evidence")
    ev_table.add_column("ID")
    ev_table.add_column("Tool")
    ev_table.add_column("Summary")
    for item in evidence:
        ev_table.add_row(str(item.get("id")), str(item.get("tool") or ""), str(item.get("summary") or ""))
    console.print(ev_table)
    approvals = state.get("approvals", [])
    if approvals:
        approval_table = Table(title="Pending approvals")
        approval_table.add_column("Tool")
        approval_table.add_column("Status")
        approval_table.add_column("Reason")
        for approval in approvals:
            approval_table.add_row(
                str(approval.get("tool")),
                str(approval.get("status")),
                str(approval.get("reason")),
            )
        console.print(approval_table)
    if state.get("finalOutput"):
        console.print(Panel(json.dumps(state["finalOutput"], indent=2), title="Final output"))
