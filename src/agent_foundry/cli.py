from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pydantic import ValidationError

from .agent_validation import AgentDeepValidator
from .evals import EvalRunner
from .loader import dump_json, load_document
from .runtime import AgentRuntime, RuntimeOptions
from .schemas import export_schemas, schema_names
from .skills import SkillRegistry
from .storage import LocalSessionStore
from .tool_providers import ToolProviderRegistry
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


def _skills(args: argparse.Namespace) -> int:
    registry = SkillRegistry(args.registry_root)
    if args.skills_command == "list":
        rows = [
            {
                "skill": package.ref,
                "risk_level": package.manifest.risk_level,
                "lifecycle_status": package.manifest.lifecycle_status,
                "required_capabilities": package.manifest.requires.capabilities,
            }
            for package in registry.list_packages()
        ]
        print(dump_json(rows))
        return 0
    if args.skills_command == "inspect":
        package = registry.load_package(args.skill)
        print(
            dump_json(
                {
                    "skill": package.ref,
                    "path": str(package.root),
                    "description": package.manifest.description,
                    "required_capabilities": package.manifest.requires.capabilities,
                    "eval_files": [str(path) for path in package.eval_files],
                }
            )
        )
        return 0
    if args.skills_command == "validate":
        result = registry.validate_package(args.skill)
        print(
            dump_json(
                {
                    "path": str(result.path),
                    "valid": result.valid,
                    "skill_ref": result.skill_ref,
                    "errors": result.errors,
                    "warnings": result.warnings,
                }
            )
        )
        return 0 if result.valid else 1
    raise ValueError(f"Unknown skills command: {args.skills_command}")


def _agent(args: argparse.Namespace) -> int:
    if args.agent_command == "validate":
        result = AgentDeepValidator(args.registry_root).validate(args.agent)
        print(
            dump_json(
                {
                    "valid": result.valid,
                    "errors": result.errors,
                    "warnings": result.warnings,
                }
            )
        )
        return 0 if result.valid else 1
    raise ValueError(f"Unknown agent command: {args.agent_command}")


def _eval(args: argparse.Namespace) -> int:
    if args.eval_command == "run":
        report = EvalRunner(args.registry_root, args.store).run(args.eval_case, args.agent)
        print(dump_json(report.to_dict()))
        return 0 if report.passed else 1
    raise ValueError(f"Unknown eval command: {args.eval_command}")


def _tools(args: argparse.Namespace) -> int:
    providers = ToolProviderRegistry(args.registry_root)
    if args.tools_command == "list":
        print(
            dump_json(
                [
                    {
                        "id": provider.metadata.id,
                        "version": provider.metadata.version,
                        "protocol": provider.spec.protocol,
                        "transport": provider.spec.transport,
                        "capabilities": [
                            {
                                "contract": capability.contract,
                                "tool": capability.tool,
                                "risk_level": capability.risk_level,
                            }
                            for capability in provider.spec.capabilities
                        ],
                    }
                    for provider in providers.list()
                ]
            )
        )
        return 0
    if args.tools_command == "inspect":
        provider = providers.inspect(args.provider)
        print(dump_json(provider.model_dump(mode="json", by_alias=True, exclude_none=True)))
        return 0
    if args.tools_command == "validate":
        result = providers.validate_all()
        print(
            dump_json(
                {
                    "valid": result.valid,
                    "errors": result.errors,
                    "warnings": result.warnings,
                }
            )
        )
        return 0 if result.valid else 1
    if args.tools_command == "bindings":
        document = load_document(args.agent)
        agent = validate_document(document, "agent")
        bindings = providers.bindings_for_agent(agent)
        print(
            dump_json(
                [
                    {
                        "capability": binding.capability,
                        "provider_tool": binding.provider_tool,
                        "provider_id": binding.provider_id,
                        "tool_name": binding.tool_name,
                        "valid": binding.valid,
                        "error": binding.error,
                    }
                    for binding in bindings
                ]
            )
        )
        return 0 if all(binding.valid for binding in bindings) else 1
    raise ValueError(f"Unknown tools command: {args.tools_command}")


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

    skills_parser = subparsers.add_parser("skills", help="Manage local skill packages")
    skills_parser.add_argument("--registry-root", default=".")
    skills_subparsers = skills_parser.add_subparsers(dest="skills_command", required=True)
    skills_subparsers.add_parser("list", help="List local skills")
    skills_inspect = skills_subparsers.add_parser("inspect", help="Inspect a skill package")
    skills_inspect.add_argument("skill", help="Skill reference or package path")
    skills_validate = skills_subparsers.add_parser("validate", help="Validate a skill package")
    skills_validate.add_argument("skill", help="Skill reference or package path")
    skills_parser.set_defaults(func=_skills)

    agent_parser = subparsers.add_parser("agent", help="Agent validation commands")
    agent_parser.add_argument("--registry-root", default=".")
    agent_subparsers = agent_parser.add_subparsers(dest="agent_command", required=True)
    agent_validate = agent_subparsers.add_parser(
        "validate", help="Deep-validate an agent and its bindings"
    )
    agent_validate.add_argument("agent", help="Agent manifest path or agent reference")
    agent_parser.set_defaults(func=_agent)

    eval_parser = subparsers.add_parser("eval", help="Run local eval cases")
    eval_parser.add_argument("--registry-root", default=".")
    eval_parser.add_argument("--store", default=".agent/evals")
    eval_subparsers = eval_parser.add_subparsers(dest="eval_command", required=True)
    eval_run = eval_subparsers.add_parser("run", help="Run an eval case")
    eval_run.add_argument("eval_case")
    eval_run.add_argument("--agent", required=True)
    eval_parser.set_defaults(func=_eval)

    tools_parser = subparsers.add_parser("tools", help="Inspect tool providers")
    tools_parser.add_argument("--registry-root", default=".")
    tools_subparsers = tools_parser.add_subparsers(dest="tools_command", required=True)
    tools_subparsers.add_parser("list", help="List tool providers")
    tools_subparsers.add_parser("validate", help="Validate tool providers")
    tools_inspect = tools_subparsers.add_parser("inspect", help="Inspect a provider")
    tools_inspect.add_argument("provider")
    tools_bindings = tools_subparsers.add_parser(
        "bindings", help="Validate an agent's provider bindings"
    )
    tools_bindings.add_argument("agent")
    tools_parser.set_defaults(func=_tools)

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

