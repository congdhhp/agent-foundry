from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from agent_foundry.evals.runner import EvalRunner
from agent_foundry.manifests.agent_loader import AgentManifestLoader
from agent_foundry.manifests.factory import create_blank_agent_manifest
from agent_foundry.io.yaml import write_yaml
from agent_foundry.runtime.service import AgentRuntime
from agent_foundry.storage.local_store import LocalStore
from agent_foundry.tui.app import run_tui

app = typer.Typer(help="Agent Foundry MVP CLI")
agent_app = typer.Typer(help="Inspect and manage agents")
trace_app = typer.Typer(help="Inspect run traces")
evidence_app = typer.Typer(help="Inspect run evidence")
eval_app = typer.Typer(help="Run eval cases")
app.add_typer(agent_app, name="agent")
app.add_typer(trace_app, name="trace")
app.add_typer(evidence_app, name="evidence")
app.add_typer(eval_app, name="eval")

console = Console()


@agent_app.command("inspect")
def inspect_agent(agent_manifest: Path = typer.Argument(..., exists=True, readable=True)) -> None:
    manifest = AgentManifestLoader().load(agent_manifest)
    table = Table(title=f"{manifest.metadata.name} ({manifest.metadata.id})")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Owner", manifest.metadata.owner or "")
    table.add_row("Purpose", manifest.spec.profile.purpose)
    table.add_row("Skills", ", ".join(manifest.spec.skills))
    table.add_row("Commands", ", ".join(manifest.spec.commands))
    table.add_row("Tools", ", ".join(manifest.spec.tools))
    table.add_row("Policies", ", ".join(manifest.spec.policies))
    table.add_row("Eval Profile", manifest.spec.evalProfile or "")
    console.print(table)


@agent_app.command("create")
def create_agent(
    agent_id: str = typer.Argument(...),
    name: str | None = typer.Option(None, "--name"),
    purpose: str = typer.Option("Describe what this agent should help with.", "--purpose"),
    output: Path | None = typer.Option(None, "--output", "-o"),
) -> None:
    manifest = create_blank_agent_manifest(agent_id=agent_id, name=name, purpose=purpose)
    target = output or Path(".agent") / "agents" / f"{agent_id}.yaml"
    target.parent.mkdir(parents=True, exist_ok=True)
    write_yaml(target, manifest.model_dump(mode="json", exclude_none=True))
    console.print(f"Created draft agent manifest: [bold]{target}[/bold]")


@app.command("run")
def run_agent(
    agent_manifest: Path = typer.Argument(..., exists=True, readable=True),
    task: str = typer.Argument(...),
    command: str | None = typer.Option(None, "--command", "-c"),
    store: Path = typer.Option(Path(".agent"), "--store"),
) -> None:
    runtime = AgentRuntime(project_root=Path.cwd(), store_root=store)
    state = runtime.run(agent_manifest, task, command_id=command)
    console.print(f"[bold]Task:[/bold] {state.taskId}")
    console.print(f"[bold]Agent:[/bold] {state.agentId}@{state.agentRevision}")
    console.print(f"[bold]Snapshot:[/bold] {state.snapshotId}")
    console.print(f"[bold]Selected skill:[/bold] {state.selectedSkill or '-'}")
    _print_policy_table(state.policyDecisions)
    _print_evidence_table([e.model_dump() for e in state.evidence])
    console.print("[bold]Result[/bold]")
    console.print_json(data=state.finalOutput or {})


@trace_app.command("show")
def show_trace(task_id: str, store: Path = typer.Option(Path(".agent"), "--store")) -> None:
    events = LocalStore(Path.cwd() / store).read_events(task_id)
    table = Table(title=f"Trace {task_id}")
    table.add_column("Type")
    table.add_column("Node")
    table.add_column("Payload")
    for event in events:
        table.add_row(event["event_type"], str(event.get("node_id") or ""), str(event.get("payload") or {}))
    console.print(table)


@evidence_app.command("show")
def show_evidence(task_id: str, store: Path = typer.Option(Path(".agent"), "--store")) -> None:
    evidence = LocalStore(Path.cwd() / store).read_evidence(task_id)
    _print_evidence_table(evidence)


@eval_app.command("run")
def run_eval(
    agent_manifest: Path = typer.Argument(..., exists=True, readable=True),
    eval_case: Path = typer.Argument(..., exists=True, readable=True),
    store: Path = typer.Option(Path(".agent"), "--store"),
) -> None:
    runtime = AgentRuntime(project_root=Path.cwd(), store_root=store)
    result = EvalRunner(runtime).run_case(agent_manifest, eval_case)
    table = Table(title=f"Eval {result.eval_id}: {'PASS' if result.passed else 'FAIL'}")
    table.add_column("Check")
    table.add_column("Passed")
    table.add_column("Message")
    for check in result.checks:
        table.add_row(check.name, "yes" if check.passed else "no", check.message)
    console.print(table)
    console.print(f"Task: {result.task_id}")


@app.command("tui")
def tui(store: Path = typer.Option(Path(".agent"), "--store")) -> None:
    run_tui(Path.cwd() / store)


def _print_policy_table(decisions) -> None:
    table = Table(title="Policy decisions")
    table.add_column("Tool")
    table.add_column("Decision")
    table.add_column("Reason")
    for decision in decisions:
        table.add_row(decision.tool, decision.decision.value, decision.reason)
    console.print(table)


def _print_evidence_table(evidence_rows: list[dict]) -> None:
    table = Table(title="Evidence")
    table.add_column("ID")
    table.add_column("Tool")
    table.add_column("Summary")
    for evidence in evidence_rows:
        table.add_row(str(evidence.get("id")), str(evidence.get("tool") or ""), str(evidence.get("summary") or ""))
    console.print(table)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
