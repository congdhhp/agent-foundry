from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pydantic import ValidationError

from .agent_factory import AgentCreateRequest, AgentFactory
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
    factory = AgentFactory(args.registry_root, args.store)
    if args.agent_command == "create":
        labels = _parse_labels(args.label)
        path = factory.create(
            AgentCreateRequest(
                agent_id=args.agent_id,
                name=args.name,
                purpose=args.purpose,
                owner=args.owner,
                skills=args.skill,
                policy=args.policy,
                workflow=args.workflow,
                template=args.template,
                model_policy=args.model_policy,
                eval_profile=args.eval_profile,
                labels=labels,
            ),
            overwrite=args.overwrite,
        )
        print(dump_json({"created": True, "path": str(path)}))
        return 0
    if args.agent_command == "list":
        print(dump_json(factory.list_agents()))
        return 0
    if args.agent_command == "inspect":
        print(dump_json(factory.inspect(args.agent)))
        return 0
    if args.agent_command == "validate":
        target: str | Path = args.agent
        try:
            target = factory.resolve_agent_path(args.agent)
        except FileNotFoundError:
            target = args.agent
        result = AgentDeepValidator(args.registry_root).validate(target)
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
    if args.agent_command == "publish":
        result = factory.publish(args.agent, args.eval, args.eval_suite)
        print(
            dump_json(
                {
                    "published": result.published,
                    "path": str(result.path),
                    "errors": result.errors,
                    "warnings": result.warnings,
                    "eval_reports": result.eval_reports,
                    "eval_suite_reports": result.eval_suite_reports,
                }
            )
        )
        return 0 if result.published else 1
    raise ValueError(f"Unknown agent command: {args.agent_command}")


def _parse_labels(values: list[str]) -> dict[str, str]:
    labels: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"Label must look like key=value: {value}")
        key, label_value = value.split("=", 1)
        labels[key] = label_value
    return labels


def _eval(args: argparse.Namespace) -> int:
    runner = EvalRunner(args.registry_root, args.store)
    if args.eval_command == "run":
        report = runner.run(args.eval_case, args.agent)
        print(dump_json(report.to_dict()))
        return 0 if report.passed else 1
    if args.eval_command == "run-suite":
        report = runner.run_suite(args.eval_suite, args.agent)
        print(dump_json(report.to_dict()))
        return 0 if report.passed else 1
    if args.eval_command == "reports":
        print(dump_json(runner.list_reports()))
        return 0
    if args.eval_command == "show":
        print(dump_json(runner.load_report(args.run_id)))
        return 0
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

    agent_parser = subparsers.add_parser("agent", help="Agent factory commands")
    agent_parser.add_argument("--registry-root", default=".")
    agent_parser.add_argument("--store", default=".agent")
    agent_subparsers = agent_parser.add_subparsers(dest="agent_command", required=True)
    agent_create = agent_subparsers.add_parser("create", help="Create a local agent")
    agent_create.add_argument("agent_id")
    agent_create.add_argument("--name", required=True)
    agent_create.add_argument("--purpose", required=True)
    agent_create.add_argument("--owner", default="local-user")
    agent_create.add_argument("--skill", action="append", required=True)
    agent_create.add_argument("--policy", required=True)
    agent_create.add_argument("--workflow", required=True)
    agent_create.add_argument("--template", default="generic-task-agent@1.0.0")
    agent_create.add_argument("--model-policy", default="default-model-policy@1.0.0")
    agent_create.add_argument("--eval-profile")
    agent_create.add_argument("--label", action="append", default=[])
    agent_create.add_argument("--overwrite", action="store_true")

    agent_subparsers.add_parser("list", help="List locally created agents")
    agent_inspect = agent_subparsers.add_parser("inspect", help="Inspect local agent composition")
    agent_inspect.add_argument("agent")
    agent_validate = agent_subparsers.add_parser(
        "validate", help="Deep-validate an agent and its bindings"
    )
    agent_validate.add_argument("agent", help="Agent manifest path or agent reference")
    agent_publish = agent_subparsers.add_parser("publish", help="Publish a local agent")
    agent_publish.add_argument("agent", help="Agent id or manifest path")
    agent_publish.add_argument("--eval", action="append", default=[])
    agent_publish.add_argument("--eval-suite", action="append", default=[])
    agent_parser.set_defaults(func=_agent)

    eval_parser = subparsers.add_parser("eval", help="Run local eval cases and suites")
    eval_parser.add_argument("--registry-root", default=".")
    eval_parser.add_argument("--store", default=".agent/evals")
    eval_subparsers = eval_parser.add_subparsers(dest="eval_command", required=True)
    eval_run = eval_subparsers.add_parser("run", help="Run an eval case")
    eval_run.add_argument("eval_case")
    eval_run.add_argument("--agent", required=True)
    eval_run_suite = eval_subparsers.add_parser("run-suite", help="Run an eval suite")
    eval_run_suite.add_argument("eval_suite")
    eval_run_suite.add_argument("--agent", required=True)
    eval_subparsers.add_parser("reports", help="List persisted eval suite reports")
    eval_show = eval_subparsers.add_parser("show", help="Show a persisted eval suite report")
    eval_show.add_argument("run_id")
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
    except (FileNotFoundError, ValueError, ValidationError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

