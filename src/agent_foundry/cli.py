from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pydantic import ValidationError

from .loader import dump_json, load_document
from .runtime import AgentRuntime, RuntimeOptions
from .schemas import export_schemas, schema_names
from .storage import LocalSessionStore
from .validation import artifact_summary, validate_document


def _validate(args: argparse.Namespace) -> int:
    failed = False
    for path in args.paths:
        try:
            document = load_document(path)
            artifact = validate_document(document, args.type)
            print(f"OK {path} {dump_json(artifact_summary(artifact))}")
        except (ValueError, ValidationError) as exc:
            failed = True
            print(f"ERROR {path}: {exc}", file=sys.stderr)
    return 1 if failed else 0


def _inspect(args: argparse.Namespace) -> int:
    document = load_document(args.path)
    artifact = validate_document(document, args.type)
    if args.full:
        print(dump_json(artifact.model_dump(mode="json", by_alias=True, exclude_none=True)))
    else:
        print(dump_json(artifact_summary(artifact)))
    return 0


def _schemas(args: argparse.Namespace) -> int:
    if args.schemas_command == "list":
        for name in schema_names():
            print(name)
        return 0
    if args.schemas_command == "export":
        written = export_schemas(Path(args.output))
        for path in written:
            print(path)
        return 0
    raise ValueError(f"Unknown schemas command: {args.schemas_command}")


def _run(args: argparse.Namespace) -> int:
    runtime = AgentRuntime(
        RuntimeOptions(
            registry_root=Path(args.registry_root),
            store_root=Path(args.store),
            workspace=Path(args.workspace),
            dry_run=not args.allow_writes,
        )
    )
    response = runtime.run(args.agent, args.task)
    print(dump_json(response))
    return 0 if response["status"] in {"completed", "waiting_approval"} else 1


def _sessions(args: argparse.Namespace) -> int:
    store = LocalSessionStore(args.store)
    print(dump_json(store.list_sessions()))
    return 0


def _show(args: argparse.Namespace) -> int:
    store = LocalSessionStore(args.store)
    mapping = {
        "events": "events.jsonl",
        "trace": "trace.jsonl",
        "evidence": "evidence.jsonl",
        "approvals": "approvals.jsonl",
    }
    print(dump_json(store.read_jsonl(args.task_id, mapping[args.kind])))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agent-foundry")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="Validate artifact files")
    validate_parser.add_argument("paths", nargs="+")
    validate_parser.add_argument("--type", choices=schema_names())
    validate_parser.set_defaults(func=_validate)

    inspect_parser = subparsers.add_parser("inspect", help="Inspect an artifact file")
    inspect_parser.add_argument("path")
    inspect_parser.add_argument("--type", choices=schema_names())
    inspect_parser.add_argument("--full", action="store_true")
    inspect_parser.set_defaults(func=_inspect)

    schemas_parser = subparsers.add_parser("schemas", help="List or export JSON schemas")
    schemas_subparsers = schemas_parser.add_subparsers(dest="schemas_command", required=True)
    schemas_subparsers.add_parser("list", help="List known artifact schemas")
    export_parser = schemas_subparsers.add_parser("export", help="Export JSON schemas")
    export_parser.add_argument("--output", default="schemas")
    schemas_parser.set_defaults(func=_schemas)

    run_parser = subparsers.add_parser("run", help="Run an agent task locally")
    run_parser.add_argument("agent", help="Agent manifest path or agent reference")
    run_parser.add_argument("task", help="Task input")
    run_parser.add_argument("--registry-root", default=".")
    run_parser.add_argument("--store", default=".agent")
    run_parser.add_argument("--workspace", default=".")
    run_parser.add_argument(
        "--allow-writes",
        action="store_true",
        help="Allow non-dry-run tool adapters where supported",
    )
    run_parser.set_defaults(func=_run)

    sessions_parser = subparsers.add_parser("sessions", help="List local task sessions")
    sessions_parser.add_argument("--store", default=".agent")
    sessions_parser.set_defaults(func=_sessions)

    show_parser = subparsers.add_parser("show", help="Show task session JSONL data")
    show_parser.add_argument("task_id")
    show_parser.add_argument(
        "kind", choices=["events", "trace", "evidence", "approvals"]
    )
    show_parser.add_argument("--store", default=".agent")
    show_parser.set_defaults(func=_show)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (ValueError, ValidationError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

