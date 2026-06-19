from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from pydantic import ValidationError

from .agent_factory import AgentCreateRequest, AgentFactory
from .agent_validation import AgentDeepValidator
from .artifact_management import ArtifactManager, MANAGED_KINDS
from .evals import EvalRunner
from .loader import dump_json, dump_yaml, load_document
from .models import AgentManifest
from .registry import LocalRegistry
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


def _init(args: argparse.Namespace) -> int:
    registry_root = Path(args.registry_root)
    store_root = Path(args.store)
    local_registry = store_root / "registry"
    for name in [
        "agents",
        "skills",
        "policies",
        "workflows",
        "capabilities",
        "tools",
        "evals",
        "eval-suites",
        "model-policies",
    ]:
        (local_registry / name).mkdir(parents=True, exist_ok=True)
    (store_root / "sessions").mkdir(parents=True, exist_ok=True)
    (store_root / "artifact-index").mkdir(parents=True, exist_ok=True)
    if args.seed:
        source = registry_root / "examples"
        seed_items = source.iterdir() if source.exists() else []
        for child in seed_items:
            if child.is_dir():
                shutil.copytree(
                    child,
                    local_registry / child.name,
                    dirs_exist_ok=True,
                )
    config = {
        "registry_root": str(registry_root),
        "store_root": str(store_root),
        "local_registry": str(local_registry),
    }
    (store_root / "config.yaml").write_text(dump_yaml(config), encoding="utf-8")
    print(dump_json({"initialized": True, **config}))
    return 0


def _run(args: argparse.Namespace) -> int:
    runtime = AgentRuntime(
        RuntimeOptions(
            registry_root=Path(args.registry_root),
            store_root=Path(args.store),
            workspace=Path(args.workspace),
            dry_run=not args.allow_writes,
            model_provider=args.model_provider,
            model=args.model,
            allow_model_calls=args.allow_model_calls,
        )
    )
    response = runtime.run(args.agent, args.task)
    print(dump_json(response))
    return 0 if response["status"] in {
        "completed",
        "waiting_approval",
        "waiting_step_up_auth",
    } else 1


def _resume(args: argparse.Namespace) -> int:
    runtime = AgentRuntime(
        RuntimeOptions(
            registry_root=Path(args.registry_root),
            store_root=Path(args.store),
            workspace=Path(args.workspace),
            dry_run=not args.allow_writes,
            model_provider=args.model_provider,
            model=args.model,
            allow_model_calls=args.allow_model_calls,
        )
    )
    response = runtime.resume(args.task_id)
    print(dump_json(response))
    return 0 if response["status"] in {
        "completed",
        "waiting_approval",
        "waiting_step_up_auth",
    } else 1


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
        "metrics": "metrics.jsonl",
    }
    print(dump_json(store.read_jsonl(args.task_id, mapping[args.kind])))
    return 0


def _approvals(args: argparse.Namespace) -> int:
    store = LocalSessionStore(args.store)
    if args.approvals_command == "list":
        print(dump_json(store.read_jsonl(args.task_id, "approvals.jsonl")))
        return 0
    if args.approvals_command == "approve":
        print(
            dump_json(
                store.set_approval_status(
                    args.task_id,
                    args.approval_id,
                    "approved",
                    args.user,
                )
            )
        )
        return 0
    if args.approvals_command == "deny":
        print(
            dump_json(
                store.set_approval_status(
                    args.task_id,
                    args.approval_id,
                    "denied",
                    args.user,
                )
            )
        )
        return 0
    raise ValueError(f"Unknown approvals command: {args.approvals_command}")


def _skills(args: argparse.Namespace) -> int:
    registry = SkillRegistry(args.registry_root, args.store)
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


def _artifacts(args: argparse.Namespace) -> int:
    manager = ArtifactManager(args.registry_root, args.store)
    if args.artifacts_command == "list":
        kind = None if args.kind == "all" else args.kind
        print(dump_json(manager.list_artifacts(kind)))
        return 0
    if args.artifacts_command == "inspect":
        print(dump_json(manager.inspect(args.kind, args.target)))
        return 0
    if args.artifacts_command == "impact":
        print(dump_json(manager.impact(args.kind, args.target)))
        return 0
    if args.artifacts_command == "rebuild-index":
        print(dump_json({"artifacts": manager.list_artifacts()}))
        return 0
    raise ValueError(f"Unknown artifacts command: {args.artifacts_command}")


def _skill(args: argparse.Namespace) -> int:
    manager = ArtifactManager(args.registry_root, args.store)
    if args.skill_command == "list":
        print(dump_json(manager.list_artifacts("skill")))
        return 0
    if args.skill_command == "create":
        path = manager.create_skill(
            args.skill_id,
            name=args.name,
            description=args.description,
            owner=args.owner,
            capabilities=args.capability,
            workflow=args.workflow,
            compatible_workflows=args.compatible_workflow,
            output_schema=args.output_schema,
            overwrite=args.overwrite,
        )
        print(dump_json({"created": True, "path": str(path)}))
        return 0
    if args.skill_command == "inspect":
        print(dump_json(manager.inspect("skill", args.skill)))
        return 0
    if args.skill_command == "validate":
        result = manager.validate_artifact("skill", args.skill)
        print(dump_json(result.to_dict()))
        return 0 if result.valid else 1
    if args.skill_command == "publish":
        publish_result = manager.publish("skill", args.skill, args.eval_suite, args.agent)
        print(dump_json(publish_result))
        return 0 if publish_result["published"] else 1
    if args.skill_command == "deprecate":
        print(
            dump_json(
                manager.deprecate(
                    "skill",
                    args.skill,
                    reason=args.reason,
                    replacement=args.replacement,
                )
            )
        )
        return 0
    if args.skill_command == "version":
        print(
            dump_json(
                manager.version_artifact(
                    "skill",
                    args.skill,
                    bump=args.bump,
                    version=args.version,
                    overwrite=args.overwrite,
                )
            )
        )
        return 0
    if args.skill_command == "impact":
        print(dump_json(manager.impact("skill", args.skill)))
        return 0
    raise ValueError(f"Unknown skill command: {args.skill_command}")


def _policy(args: argparse.Namespace) -> int:
    manager = ArtifactManager(args.registry_root, args.store)
    if args.policy_command == "list":
        print(dump_json(manager.list_artifacts("policy")))
        return 0
    if args.policy_command == "create":
        path = manager.create_policy(
            args.policy_id,
            owner=args.owner,
            allow=args.allow,
            require_approval=args.require_approval,
            deny_risk_level=args.deny_risk_level,
            overwrite=args.overwrite,
        )
        print(dump_json({"created": True, "path": str(path)}))
        return 0
    if args.policy_command == "inspect":
        print(dump_json(manager.inspect("policy", args.policy)))
        return 0
    if args.policy_command == "validate":
        result = manager.validate_artifact("policy", args.policy)
        print(dump_json(result.to_dict()))
        return 0 if result.valid else 1
    if args.policy_command == "simulate":
        print(dump_json(manager.simulate_policy(args.policy, args.capability, args.agent)))
        return 0
    if args.policy_command == "publish":
        publish_result = manager.publish("policy", args.policy)
        print(dump_json(publish_result))
        return 0 if publish_result["published"] else 1
    if args.policy_command == "deprecate":
        print(
            dump_json(
                manager.deprecate(
                    "policy",
                    args.policy,
                    reason=args.reason,
                    replacement=args.replacement,
                )
            )
        )
        return 0
    if args.policy_command == "version":
        print(
            dump_json(
                manager.version_artifact(
                    "policy",
                    args.policy,
                    bump=args.bump,
                    version=args.version,
                    overwrite=args.overwrite,
                )
            )
        )
        return 0
    if args.policy_command == "impact":
        print(dump_json(manager.impact("policy", args.policy)))
        return 0
    raise ValueError(f"Unknown policy command: {args.policy_command}")


def _workflow(args: argparse.Namespace) -> int:
    manager = ArtifactManager(args.registry_root, args.store)
    if args.workflow_command == "list":
        print(dump_json(manager.list_artifacts("workflow")))
        return 0
    if args.workflow_command == "create":
        path = manager.create_workflow(
            args.workflow_id,
            runtime=args.runtime,
            state_schema=args.state_schema,
            capabilities=args.capability,
            overwrite=args.overwrite,
        )
        print(dump_json({"created": True, "path": str(path)}))
        return 0
    if args.workflow_command == "inspect":
        print(dump_json(manager.inspect("workflow", args.workflow)))
        return 0
    if args.workflow_command == "validate":
        result = manager.validate_artifact("workflow", args.workflow)
        print(dump_json(result.to_dict()))
        return 0 if result.valid else 1
    if args.workflow_command == "publish":
        publish_result = manager.publish("workflow", args.workflow, args.eval_suite, args.agent)
        print(dump_json(publish_result))
        return 0 if publish_result["published"] else 1
    if args.workflow_command == "deprecate":
        print(
            dump_json(
                manager.deprecate(
                    "workflow",
                    args.workflow,
                    reason=args.reason,
                    replacement=args.replacement,
                )
            )
        )
        return 0
    if args.workflow_command == "version":
        print(
            dump_json(
                manager.version_artifact(
                    "workflow",
                    args.workflow,
                    bump=args.bump,
                    version=args.version,
                    overwrite=args.overwrite,
                )
            )
        )
        return 0
    if args.workflow_command == "impact":
        print(dump_json(manager.impact("workflow", args.workflow)))
        return 0
    raise ValueError(f"Unknown workflow command: {args.workflow_command}")


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
                policy=args.policy,
                workflow=args.workflow,
                skills=args.skill,
                capabilities=args.capability,
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
        validation_result = AgentDeepValidator(args.registry_root, args.store).validate(target)
        print(
            dump_json(
                {
                    "valid": validation_result.valid,
                    "errors": validation_result.errors,
                    "warnings": validation_result.warnings,
                }
            )
        )
        return 0 if validation_result.valid else 1
    if args.agent_command == "publish":
        publish_result = factory.publish(args.agent, args.eval, args.eval_suite)
        print(
            dump_json(
                {
                    "published": publish_result.published,
                    "path": str(publish_result.path),
                    "errors": publish_result.errors,
                    "warnings": publish_result.warnings,
                    "eval_reports": publish_result.eval_reports,
                    "eval_suite_reports": publish_result.eval_suite_reports,
                }
            )
        )
        return 0 if publish_result.published else 1
    if args.agent_command == "bind-tool":
        provider_tool = args.provider_tool
        if provider_tool is None:
            if args.provider is None or args.tool is None:
                raise ValueError(
                    "Use --provider-tool or both --provider and --tool for binding."
                )
            provider_tool = f"{args.provider}.{args.tool}"
        path = factory.bind_tool(
            args.agent,
            args.capability,
            provider_tool,
            overwrite=args.overwrite,
        )
        print(
            dump_json(
                {
                    "bound": True,
                    "agent": str(path),
                    "capability": args.capability,
                    "provider_tool": provider_tool,
                }
            )
        )
        return 0
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
        case_report = runner.run(args.eval_case, args.agent)
        print(dump_json(case_report.to_dict()))
        return 0 if case_report.passed else 1
    if args.eval_command == "run-suite":
        suite_report = runner.run_suite(args.eval_suite, args.agent)
        print(dump_json(suite_report.to_dict()))
        return 0 if suite_report.passed else 1
    if args.eval_command == "reports":
        print(dump_json(runner.list_reports()))
        return 0
    if args.eval_command == "show":
        print(dump_json(runner.load_report(args.run_id)))
        return 0
    raise ValueError(f"Unknown eval command: {args.eval_command}")


def _tools(args: argparse.Namespace) -> int:
    providers = ToolProviderRegistry(args.registry_root, args.store)
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
                    for provider in providers.list_providers()
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
        if not isinstance(agent, AgentManifest):
            raise ValueError(f"{args.agent} is not an agent manifest")
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


def _provider(args: argparse.Namespace) -> int:
    providers = ToolProviderRegistry(args.registry_root, args.store)
    if args.provider_command == "list":
        print(
            dump_json(
                [
                    {
                        "id": provider.metadata.id,
                        "version": provider.metadata.version,
                        "name": provider.metadata.name,
                        "enabled": provider.spec.enabled,
                        "protocol": provider.spec.protocol.value,
                        "transport": provider.spec.transport.value,
                        "endpoint": provider.spec.endpoint,
                        "capabilities": [
                            {
                                "contract": capability.contract,
                                "tool": capability.tool,
                                "provider_tool": (
                                    f"{provider.metadata.id}.{capability.tool}"
                                ),
                                "risk_level": capability.risk_level.value,
                            }
                            for capability in provider.spec.capabilities
                        ],
                    }
                    for provider in providers.list_providers()
                ]
            )
        )
        return 0
    if args.provider_command == "inspect":
        provider = providers.inspect(args.provider)
        print(dump_json(provider.model_dump(mode="json", by_alias=True, exclude_none=True)))
        return 0
    if args.provider_command == "validate":
        validation_result = providers.validate(args.provider)
        print(
            dump_json(
                {
                    "valid": validation_result.valid,
                    "errors": validation_result.errors,
                    "warnings": validation_result.warnings,
                }
            )
        )
        return 0 if validation_result.valid else 1
    if args.provider_command == "health":
        print(dump_json(providers.health(args.provider).to_dict()))
        return 0
    if args.provider_command == "compatibility":
        compatibility_result = providers.compatibility(args.provider, args.capability)
        print(dump_json(compatibility_result.to_dict()))
        return 0 if compatibility_result.compatible else 1
    raise ValueError(f"Unknown provider command: {args.provider_command}")


def _capability(args: argparse.Namespace) -> int:
    registry = LocalRegistry(args.registry_root, args.store)
    providers = ToolProviderRegistry(args.registry_root, args.store)
    manager = ArtifactManager(args.registry_root, args.store)
    if args.capability_command == "list":
        print(dump_json(manager.list_artifacts("capability")))
        return 0
    if args.capability_command == "inspect":
        capability = registry.load_capability(args.capability)
        print(dump_json(capability.model_dump(mode="json", by_alias=True, exclude_none=True)))
        return 0
    if args.capability_command == "providers":
        matches = providers.providers_for_capability(args.capability)
        print(
            dump_json(
                [
                    {
                        "capability": match.capability,
                        "provider_id": match.provider_id,
                        "provider_tool": match.provider_tool,
                        "tool_name": match.tool_name,
                        "protocol": match.protocol,
                        "transport": match.transport,
                        "risk_level": match.risk_level,
                    }
                    for match in matches
                ]
            )
        )
        return 0
    raise ValueError(f"Unknown capability command: {args.capability_command}")


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

    init_parser = subparsers.add_parser("init", help="Initialize local Agent Foundry state")
    init_parser.add_argument("--registry-root", default=".")
    init_parser.add_argument("--store", default=".agent")
    init_parser.add_argument(
        "--seed",
        action="store_true",
        help="Copy bundled example artifacts into the local registry",
    )
    init_parser.set_defaults(func=_init)

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
    run_parser.add_argument("--model-provider")
    run_parser.add_argument("--model")
    run_parser.add_argument(
        "--allow-model-calls",
        action="store_true",
        help="Allow configured model provider network calls. Defaults to deterministic dry-run.",
    )
    run_parser.set_defaults(func=_run)

    resume_parser = subparsers.add_parser("resume", help="Resume a paused task")
    resume_parser.add_argument("task_id")
    resume_parser.add_argument("--registry-root", default=".")
    resume_parser.add_argument("--store", default=".agent")
    resume_parser.add_argument("--workspace", default=".")
    resume_parser.add_argument(
        "--allow-writes",
        action="store_true",
        help="Allow non-dry-run tool adapters where supported",
    )
    resume_parser.add_argument("--model-provider")
    resume_parser.add_argument("--model")
    resume_parser.add_argument(
        "--allow-model-calls",
        action="store_true",
        help="Allow configured model provider network calls.",
    )
    resume_parser.set_defaults(func=_resume)

    sessions_parser = subparsers.add_parser("sessions", help="List local task sessions")
    sessions_parser.add_argument("--store", default=".agent")
    sessions_parser.set_defaults(func=_sessions)

    show_parser = subparsers.add_parser("show", help="Show task session JSONL data")
    show_parser.add_argument("task_id")
    show_parser.add_argument(
        "kind", choices=["events", "trace", "evidence", "approvals", "metrics"]
    )
    show_parser.add_argument("--store", default=".agent")
    show_parser.set_defaults(func=_show)

    approvals_parser = subparsers.add_parser(
        "approvals",
        help="Inspect and decide pending approvals",
    )
    approvals_parser.add_argument("--store", default=".agent")
    approvals_subparsers = approvals_parser.add_subparsers(
        dest="approvals_command",
        required=True,
    )
    approvals_list = approvals_subparsers.add_parser("list", help="List task approvals")
    approvals_list.add_argument("task_id")
    approvals_approve = approvals_subparsers.add_parser(
        "approve",
        help="Approve a pending action",
    )
    approvals_approve.add_argument("task_id")
    approvals_approve.add_argument("approval_id")
    approvals_approve.add_argument("--user", default="local-user")
    approvals_deny = approvals_subparsers.add_parser(
        "deny",
        help="Deny a pending action",
    )
    approvals_deny.add_argument("task_id")
    approvals_deny.add_argument("approval_id")
    approvals_deny.add_argument("--user", default="local-user")
    approvals_parser.set_defaults(func=_approvals)

    skills_parser = subparsers.add_parser("skills", help="Manage local skill packages")
    skills_parser.add_argument("--registry-root", default=".")
    skills_parser.add_argument("--store", default=".agent")
    skills_subparsers = skills_parser.add_subparsers(dest="skills_command", required=True)
    skills_subparsers.add_parser("list", help="List local skills")
    skills_inspect = skills_subparsers.add_parser("inspect", help="Inspect a skill package")
    skills_inspect.add_argument("skill", help="Skill reference or package path")
    skills_validate = skills_subparsers.add_parser("validate", help="Validate a skill package")
    skills_validate.add_argument("skill", help="Skill reference or package path")
    skills_parser.set_defaults(func=_skills)

    artifacts_parser = subparsers.add_parser("artifacts", help="Manage artifact index")
    artifacts_parser.add_argument("--registry-root", default=".")
    artifacts_parser.add_argument("--store", default=".agent")
    artifacts_subparsers = artifacts_parser.add_subparsers(
        dest="artifacts_command", required=True
    )
    artifacts_list = artifacts_subparsers.add_parser("list", help="List managed artifacts")
    artifacts_list.add_argument("--kind", choices=["all", *MANAGED_KINDS], default="all")
    artifacts_inspect = artifacts_subparsers.add_parser(
        "inspect", help="Inspect an indexed artifact"
    )
    artifacts_inspect.add_argument("kind", choices=MANAGED_KINDS)
    artifacts_inspect.add_argument("target")
    artifacts_impact = artifacts_subparsers.add_parser(
        "impact", help="Show artifact dependency impact"
    )
    artifacts_impact.add_argument("kind", choices=MANAGED_KINDS)
    artifacts_impact.add_argument("target")
    artifacts_subparsers.add_parser("rebuild-index", help="Rebuild local artifact index")
    artifacts_parser.set_defaults(func=_artifacts)

    skill_parser = subparsers.add_parser("skill", help="Manage skill lifecycle")
    skill_parser.add_argument("--registry-root", default=".")
    skill_parser.add_argument("--store", default=".agent")
    skill_subparsers = skill_parser.add_subparsers(dest="skill_command", required=True)
    skill_subparsers.add_parser("list", help="List skill artifacts")
    skill_create = skill_subparsers.add_parser("create", help="Create a skill scaffold")
    skill_create.add_argument("skill_id")
    skill_create.add_argument("--name")
    skill_create.add_argument("--description")
    skill_create.add_argument("--owner", default="local-user")
    skill_create.add_argument("--capability", action="append", default=[])
    skill_create.add_argument(
        "--workflow",
        help="Optional recommended workflow hint for this skill.",
    )
    skill_create.add_argument(
        "--compatible-workflow",
        action="append",
        default=[],
        help="Optional workflow known to be compatible with this skill.",
    )
    skill_create.add_argument("--output-schema")
    skill_create.add_argument("--overwrite", action="store_true")
    skill_inspect = skill_subparsers.add_parser("inspect", help="Inspect a skill")
    skill_inspect.add_argument("skill")
    skill_validate = skill_subparsers.add_parser("validate", help="Validate a skill")
    skill_validate.add_argument("skill")
    skill_publish = skill_subparsers.add_parser("publish", help="Publish a skill")
    skill_publish.add_argument("skill")
    skill_publish.add_argument("--eval-suite")
    skill_publish.add_argument("--agent")
    skill_deprecate = skill_subparsers.add_parser("deprecate", help="Deprecate a skill")
    skill_deprecate.add_argument("skill")
    skill_deprecate.add_argument("--reason", required=True)
    skill_deprecate.add_argument("--replacement")
    skill_version = skill_subparsers.add_parser("version", help="Create a new skill version")
    skill_version.add_argument("skill")
    skill_version.add_argument("--bump", choices=["major", "minor", "patch"])
    skill_version.add_argument("--version")
    skill_version.add_argument("--overwrite", action="store_true")
    skill_impact = skill_subparsers.add_parser("impact", help="Show skill impact")
    skill_impact.add_argument("skill")
    skill_parser.set_defaults(func=_skill)

    policy_parser = subparsers.add_parser("policy", help="Manage policy lifecycle")
    policy_parser.add_argument("--registry-root", default=".")
    policy_parser.add_argument("--store", default=".agent")
    policy_subparsers = policy_parser.add_subparsers(dest="policy_command", required=True)
    policy_subparsers.add_parser("list", help="List policies")
    policy_create = policy_subparsers.add_parser("create", help="Create a policy scaffold")
    policy_create.add_argument("policy_id")
    policy_create.add_argument("--owner", default="local-user")
    policy_create.add_argument("--allow", action="append", default=[])
    policy_create.add_argument("--require-approval", action="append", default=[])
    policy_create.add_argument("--deny-risk-level", action="append", default=[])
    policy_create.add_argument("--overwrite", action="store_true")
    policy_inspect = policy_subparsers.add_parser("inspect", help="Inspect a policy")
    policy_inspect.add_argument("policy")
    policy_validate = policy_subparsers.add_parser("validate", help="Validate a policy")
    policy_validate.add_argument("policy")
    policy_simulate = policy_subparsers.add_parser("simulate", help="Simulate policy decision")
    policy_simulate.add_argument("policy")
    policy_simulate.add_argument("--capability", required=True)
    policy_simulate.add_argument("--agent")
    policy_publish = policy_subparsers.add_parser("publish", help="Publish a policy")
    policy_publish.add_argument("policy")
    policy_deprecate = policy_subparsers.add_parser("deprecate", help="Deprecate a policy")
    policy_deprecate.add_argument("policy")
    policy_deprecate.add_argument("--reason", required=True)
    policy_deprecate.add_argument("--replacement")
    policy_version = policy_subparsers.add_parser("version", help="Create a new policy version")
    policy_version.add_argument("policy")
    policy_version.add_argument("--bump", choices=["major", "minor", "patch"])
    policy_version.add_argument("--version")
    policy_version.add_argument("--overwrite", action="store_true")
    policy_impact = policy_subparsers.add_parser("impact", help="Show policy impact")
    policy_impact.add_argument("policy")
    policy_parser.set_defaults(func=_policy)

    workflow_parser = subparsers.add_parser("workflow", help="Manage workflow lifecycle")
    workflow_parser.add_argument("--registry-root", default=".")
    workflow_parser.add_argument("--store", default=".agent")
    workflow_subparsers = workflow_parser.add_subparsers(
        dest="workflow_command", required=True
    )
    workflow_subparsers.add_parser("list", help="List workflows")
    workflow_create = workflow_subparsers.add_parser(
        "create", help="Create a workflow scaffold"
    )
    workflow_create.add_argument("workflow_id")
    workflow_create.add_argument("--runtime", default="langgraph")
    workflow_create.add_argument("--state-schema", default="AgentState")
    workflow_create.add_argument("--capability", action="append", default=[])
    workflow_create.add_argument("--overwrite", action="store_true")
    workflow_inspect = workflow_subparsers.add_parser("inspect", help="Inspect a workflow")
    workflow_inspect.add_argument("workflow")
    workflow_validate = workflow_subparsers.add_parser("validate", help="Validate a workflow")
    workflow_validate.add_argument("workflow")
    workflow_publish = workflow_subparsers.add_parser("publish", help="Publish a workflow")
    workflow_publish.add_argument("workflow")
    workflow_publish.add_argument("--eval-suite")
    workflow_publish.add_argument("--agent")
    workflow_deprecate = workflow_subparsers.add_parser(
        "deprecate", help="Deprecate a workflow"
    )
    workflow_deprecate.add_argument("workflow")
    workflow_deprecate.add_argument("--reason", required=True)
    workflow_deprecate.add_argument("--replacement")
    workflow_version = workflow_subparsers.add_parser(
        "version", help="Create a new workflow version"
    )
    workflow_version.add_argument("workflow")
    workflow_version.add_argument("--bump", choices=["major", "minor", "patch"])
    workflow_version.add_argument("--version")
    workflow_version.add_argument("--overwrite", action="store_true")
    workflow_impact = workflow_subparsers.add_parser("impact", help="Show workflow impact")
    workflow_impact.add_argument("workflow")
    workflow_parser.set_defaults(func=_workflow)

    agent_parser = subparsers.add_parser("agent", help="Agent factory commands")
    agent_parser.add_argument("--registry-root", default=".")
    agent_parser.add_argument("--store", default=".agent")
    agent_subparsers = agent_parser.add_subparsers(dest="agent_command", required=True)
    agent_create = agent_subparsers.add_parser("create", help="Create a local agent")
    agent_create.add_argument("agent_id")
    agent_create.add_argument("--name", required=True)
    agent_create.add_argument("--purpose", required=True)
    agent_create.add_argument("--owner", default="local-user")
    agent_create.add_argument("--skill", action="append", default=[])
    agent_create.add_argument("--capability", action="append", default=[])
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
    agent_bind_tool = agent_subparsers.add_parser(
        "bind-tool",
        help="Bind an agent capability to a provider tool",
    )
    agent_bind_tool.add_argument("agent", help="Agent id or manifest path")
    agent_bind_tool.add_argument("--capability", required=True)
    agent_bind_tool.add_argument(
        "--provider-tool",
        help="Provider tool reference like browser.search",
    )
    agent_bind_tool.add_argument("--provider", help="Provider id, used with --tool")
    agent_bind_tool.add_argument("--tool", help="Tool name, used with --provider")
    agent_bind_tool.add_argument("--overwrite", action="store_true")
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
    tools_parser.add_argument("--store", default=".agent")
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

    provider_parser = subparsers.add_parser("provider", help="Manage tool providers")
    provider_parser.add_argument("--registry-root", default=".")
    provider_parser.add_argument("--store", default=".agent")
    provider_subparsers = provider_parser.add_subparsers(
        dest="provider_command",
        required=True,
    )
    provider_subparsers.add_parser("list", help="List provider manifests")
    provider_validate = provider_subparsers.add_parser(
        "validate",
        help="Validate one provider or all providers",
    )
    provider_validate.add_argument("provider", nargs="?")
    provider_inspect = provider_subparsers.add_parser(
        "inspect",
        help="Inspect a provider manifest",
    )
    provider_inspect.add_argument("provider")
    provider_health = provider_subparsers.add_parser(
        "health",
        help="Run local provider health checks",
    )
    provider_health.add_argument("provider")
    provider_compatibility = provider_subparsers.add_parser(
        "compatibility",
        help="Check provider compatibility with capability contracts",
    )
    provider_compatibility.add_argument("provider")
    provider_compatibility.add_argument("--capability")
    provider_parser.set_defaults(func=_provider)

    capability_parser = subparsers.add_parser(
        "capability",
        help="Inspect capability contracts and provider implementations",
    )
    capability_parser.add_argument("--registry-root", default=".")
    capability_parser.add_argument("--store", default=".agent")
    capability_subparsers = capability_parser.add_subparsers(
        dest="capability_command",
        required=True,
    )
    capability_subparsers.add_parser("list", help="List capability contracts")
    capability_inspect = capability_subparsers.add_parser(
        "inspect",
        help="Inspect a capability contract",
    )
    capability_inspect.add_argument("capability")
    capability_providers = capability_subparsers.add_parser(
        "providers",
        help="List providers that implement a capability",
    )
    capability_providers.add_argument("capability")
    capability_parser.set_defaults(func=_capability)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (FileExistsError, FileNotFoundError, ValueError, ValidationError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

