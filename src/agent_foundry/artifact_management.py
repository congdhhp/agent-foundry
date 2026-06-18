from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from .evals import EvalRunner
from .loader import dump_yaml, load_document
from .models import (
    AgentManifest,
    CapabilityContractManifest,
    EvalSuiteManifest,
    ModelPolicyManifest,
    PolicyManifest,
    SkillManifest,
    ToolProviderManifest,
    WorkflowDefinition,
)
from .policy import PolicyEngine
from .registry import LocalRegistry
from .refs import ArtifactRef
from .skills import SkillRegistry
from .storage import utc_now
from .validation import artifact_summary, validate_document


MANAGED_KINDS = (
    "agent",
    "skill",
    "policy",
    "workflow",
    "capability",
    "tool-provider",
    "eval-suite",
    "model-policy",
)


@dataclass(frozen=True)
class ArtifactEntry:
    kind: str
    artifact_id: str
    version: str
    ref: str
    path: Path
    lifecycle_status: str
    source: str
    dependencies: dict[str, list[str]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "id": self.artifact_id,
            "version": self.version,
            "ref": self.ref,
            "path": str(self.path),
            "lifecycle_status": self.lifecycle_status,
            "source": self.source,
            "dependencies": self.dependencies,
        }


@dataclass(frozen=True)
class ArtifactValidationResult:
    kind: str
    ref: str
    path: Path
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "ref": self.ref,
            "path": str(self.path),
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
        }


class ArtifactManager:
    def __init__(
        self,
        registry_root: str | Path = ".",
        store_root: str | Path = ".agent",
    ) -> None:
        self.registry_root = Path(registry_root)
        self.store_root = Path(store_root)
        self.examples_dir = self.registry_root / "examples"
        self.index_dir = self.store_root / "artifact-index"
        self.index_path = self.index_dir / "index.json"
        self.state_path = self.index_dir / "state.json"
        self.registry = LocalRegistry(self.registry_root)
        self.skill_registry = SkillRegistry(self.registry_root)

    def list_artifacts(self, kind: str | None = None) -> list[dict[str, Any]]:
        entries = self.discover(kind)
        self._persist_index(entries)
        return [entry.to_dict() for entry in entries]

    def inspect(self, kind: str, target: str | Path) -> dict[str, Any]:
        entry = self.resolve(kind, target)
        artifact = self._load_entry(entry)
        return {
            "artifact": entry.to_dict(),
            "summary": artifact_summary(artifact),
            "impact": self.impact(kind, entry.ref),
        }

    def create_skill(
        self,
        skill_id: str,
        name: str | None = None,
        description: str | None = None,
        owner: str = "local-user",
        capabilities: list[str] | None = None,
        workflow: str = "general_reasoning_graph@1.0.0",
        output_schema: str | None = None,
        overwrite: bool = False,
    ) -> Path:
        skill_dir = self.examples_dir / "skills" / skill_id
        if skill_dir.exists() and not overwrite:
            raise FileExistsError(f"Skill package already exists: {skill_dir}")
        skill_dir.mkdir(parents=True, exist_ok=True)
        capabilities = capabilities or []
        output_schema_ref = output_schema or f"{skill_id}-output@1.0.0"
        manifest = {
            "id": skill_id,
            "version": "1.0.0",
            "name": name or skill_id.replace("-", " ").title(),
            "description": description or f"{skill_id} skill.",
            "owner": owner,
            "risk_level": "low",
            "lifecycle_status": "draft",
            "triggers": {"intents": [], "keywords": []},
            "requires": {"capabilities": capabilities},
            "optional_capabilities": [],
            "default_workflow": workflow,
            "output_schema": output_schema_ref,
        }
        (skill_dir / "skill.yaml").write_text(dump_yaml(manifest), encoding="utf-8")
        (skill_dir / "SKILL.md").write_text(
            f"# {manifest['name']}\n\nDescribe how this skill should solve tasks.\n",
            encoding="utf-8",
        )
        output_schema_doc = {
            "type": "object",
            "additionalProperties": True,
            "properties": {
                "summary": {"type": "string"},
                "evidence_refs": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
        }
        (skill_dir / "output_schema.json").write_text(
            json.dumps(output_schema_doc, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        evals_dir = skill_dir / "evals"
        evals_dir.mkdir(exist_ok=True)
        golden_case = {
            "id": f"{skill_id.replace('-', '_')}_golden_001",
            "task": {
                "input": f"Run a representative task for {skill_id}.",
                "metadata": {"domain": "local"},
            },
            "expected": {
                "selected_skills": {"must_include": [f"{skill_id}@1.0.0"]},
                "tool_trajectory": {"must_call": capabilities},
                "safety": {"must_not_execute_side_effects": True},
            },
        }
        (evals_dir / "golden_cases.yaml").write_text(
            dump_yaml(golden_case), encoding="utf-8"
        )
        self._update_state(
            "skill",
            skill_id,
            "1.0.0",
            {
                "lifecycle_status": "draft",
                "path": str(skill_dir / "skill.yaml"),
                "created_at": utc_now(),
            },
        )
        self.list_artifacts()
        return skill_dir

    def create_policy(
        self,
        policy_id: str,
        owner: str = "local-user",
        allow: list[str] | None = None,
        require_approval: list[str] | None = None,
        deny_risk_level: list[str] | None = None,
        overwrite: bool = False,
    ) -> Path:
        path = self.examples_dir / "policies" / f"{policy_id}.yaml"
        if path.exists() and not overwrite:
            raise FileExistsError(f"Policy already exists: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        rules: list[dict[str, Any]] = []
        for capability in allow or []:
            rules.append({"match": {"capability": capability}, "decision": "allow"})
        for capability in require_approval or []:
            rules.append(
                {"match": {"capability": capability}, "decision": "require_approval"}
            )
        for risk_level in deny_risk_level or ["critical"]:
            rules.append({"match": {"riskLevel": risk_level}, "decision": "deny"})
        document = {
            "apiVersion": "agents.platform/v1",
            "kind": "Policy",
            "metadata": {
                "id": policy_id,
                "version": "1.0.0",
                "name": policy_id.replace("-", " ").title(),
                "owner": owner,
            },
            "spec": {"rules": rules},
        }
        path.write_text(dump_yaml(document), encoding="utf-8")
        self._update_state(
            "policy",
            policy_id,
            "1.0.0",
            {
                "lifecycle_status": "draft",
                "path": str(path),
                "created_at": utc_now(),
            },
        )
        self.list_artifacts()
        return path

    def create_workflow(
        self,
        workflow_id: str,
        runtime: str = "langgraph",
        state_schema: str = "AgentState",
        capabilities: list[str] | None = None,
        overwrite: bool = False,
    ) -> Path:
        path = self.examples_dir / "workflows" / f"{workflow_id}.yaml"
        if path.exists() and not overwrite:
            raise FileExistsError(f"Workflow already exists: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        nodes: list[dict[str, Any]] = [
            {"id": "understand_task", "type": "llm_reasoning"}
        ]
        for index, capability in enumerate(capabilities or [], start=1):
            node_id = capability.split("@", 1)[0].replace(".", "_").replace("-", "_")
            nodes.append(
                {
                    "id": f"call_{index}_{node_id}",
                    "type": "capability_call",
                    "capability": capability,
                }
            )
        nodes.append({"id": "compose_output", "type": "output_composer"})
        document = {
            "id": workflow_id,
            "version": "1.0.0",
            "runtime": runtime,
            "state_schema": state_schema,
            "nodes": nodes,
        }
        path.write_text(dump_yaml(document), encoding="utf-8")
        self._update_state(
            "workflow",
            workflow_id,
            "1.0.0",
            {
                "lifecycle_status": "draft",
                "path": str(path),
                "created_at": utc_now(),
            },
        )
        self.list_artifacts()
        return path

    def validate_artifact(
        self, kind: str, target: str | Path
    ) -> ArtifactValidationResult:
        entry = self.resolve(kind, target)
        errors: list[str] = []
        warnings: list[str] = []
        ref = entry.ref
        try:
            if kind == "skill":
                package_result = self.skill_registry.validate_package(entry.path)
                errors.extend(package_result.errors)
                warnings.extend(package_result.warnings)
                package = self.skill_registry.load_package(entry.path)
                ref = package.ref
                errors.extend(self._validate_skill_dependencies(package.manifest))
            elif kind == "policy":
                policy = self._load_policy_path(entry.path)
                ref = f"{policy.metadata.id}@{policy.metadata.version}"
                errors.extend(self._validate_policy_dependencies(policy))
            elif kind == "workflow":
                workflow = self._load_workflow_path(entry.path)
                ref = f"{workflow.id}@{workflow.version}"
                errors.extend(self._validate_workflow_dependencies(workflow))
            else:
                artifact = self._load_entry(entry)
                summary = artifact_summary(artifact)
                ref = f"{summary['id']}@{summary.get('version', entry.version)}"
        except Exception as exc:  # noqa: BLE001
            errors.append(str(exc))
        return ArtifactValidationResult(
            kind=kind,
            ref=ref,
            path=entry.path,
            valid=not errors,
            errors=errors,
            warnings=warnings,
        )

    def publish(
        self,
        kind: str,
        target: str | Path,
        eval_suite: str | Path | None = None,
        agent: str | Path | None = None,
    ) -> dict[str, Any]:
        result = self.validate_artifact(kind, target)
        eval_suite_reports: list[dict[str, Any]] = []
        warnings = list(result.warnings)
        if eval_suite is not None and agent is not None:
            report = EvalRunner(self.registry_root, self.store_root / "evals").run_suite(
                eval_suite,
                agent,
            )
            eval_suite_reports.append(report.to_dict())
            if not report.passed:
                result.errors.append(
                    f"Eval suite failed: {report.suite_id}@{report.suite_version}"
                )
        elif eval_suite is not None:
            suite = validate_document(load_document(eval_suite), "eval-suite")
            if not isinstance(suite, EvalSuiteManifest):
                result.errors.append(f"{eval_suite} is not an eval suite")
            warnings.append("Eval suite was validated but not run because --agent was omitted.")

        if result.errors:
            return {
                "published": False,
                "validation": result.to_dict(),
                "warnings": warnings,
                "eval_suite_reports": eval_suite_reports,
            }

        artifact_id, version = self._split_ref(result.ref)
        self._update_state(
            kind,
            artifact_id,
            version,
            {
                "lifecycle_status": "published",
                "path": str(result.path),
                "published_at": utc_now(),
                "validation": result.to_dict(),
                "eval_suite_reports": eval_suite_reports,
            },
        )
        self.list_artifacts()
        return {
            "published": True,
            "kind": kind,
            "ref": result.ref,
            "path": str(result.path),
            "warnings": warnings,
            "eval_suite_reports": eval_suite_reports,
        }

    def deprecate(
        self,
        kind: str,
        target: str | Path,
        reason: str,
        replacement: str | None = None,
    ) -> dict[str, Any]:
        entry = self.resolve(kind, target)
        self._update_state(
            kind,
            entry.artifact_id,
            entry.version,
            {
                "lifecycle_status": "deprecated",
                "path": str(entry.path),
                "deprecated_at": utc_now(),
                "reason": reason,
                "replacement": replacement,
            },
        )
        self.list_artifacts()
        return {
            "deprecated": True,
            "kind": kind,
            "ref": entry.ref,
            "reason": reason,
            "replacement": replacement,
        }

    def version_artifact(
        self,
        kind: str,
        target: str | Path,
        bump: str | None = None,
        version: str | None = None,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        entry = self.resolve(kind, target)
        new_version = version or self._bump_version(entry.version, bump or "patch")
        if kind == "skill":
            new_path = self._version_skill(entry.path, new_version, overwrite)
        elif kind == "policy":
            new_path = self._version_yaml_artifact(
                entry.path, "policy", entry.artifact_id, new_version, overwrite
            )
        elif kind == "workflow":
            new_path = self._version_yaml_artifact(
                entry.path, "workflow", entry.artifact_id, new_version, overwrite
            )
        else:
            raise ValueError(f"Versioning is not supported for {kind}")

        self._update_state(
            kind,
            entry.artifact_id,
            new_version,
            {
                "lifecycle_status": "draft",
                "path": str(new_path),
                "created_at": utc_now(),
                "source_ref": entry.ref,
            },
        )
        self.list_artifacts()
        return {
            "versioned": True,
            "kind": kind,
            "source_ref": entry.ref,
            "new_ref": f"{entry.artifact_id}@{new_version}",
            "path": str(new_path),
        }

    def impact(self, kind: str, target: str | Path) -> dict[str, Any]:
        entry = self.resolve(kind, target)
        impacted_agents = []
        for agent_entry in self.discover("agent"):
            try:
                agent = self._load_agent_path(agent_entry.path)
            except Exception:  # noqa: BLE001
                continue
            if self._agent_references(agent, kind, entry.ref):
                impacted_agents.append(
                    {
                        "agent": agent.metadata.id,
                        "path": str(agent_entry.path),
                        "status": agent.metadata.status,
                        "skills": agent.spec.skills,
                        "policy": agent.spec.policy,
                        "workflow": agent.spec.workflow,
                        "eval_profile": agent.spec.eval_profile,
                    }
                )

        dependencies = entry.dependencies
        eval_suites = self._eval_suites_for_agents(impacted_agents)
        return {
            "artifact": entry.ref,
            "kind": kind,
            "path": str(entry.path),
            "lifecycle_status": entry.lifecycle_status,
            "referenced_by_agents": impacted_agents,
            "dependencies": dependencies,
            "eval_suites": eval_suites,
            "recommended_version_bump": "minor" if impacted_agents else "patch",
            "migration_required": bool(impacted_agents),
        }

    def simulate_policy(
        self,
        policy: str | Path,
        capability_ref: str,
        agent: str | Path | None = None,
    ) -> dict[str, Any]:
        policy_entry = self.resolve("policy", policy)
        policy_manifest = self._load_policy_path(policy_entry.path)
        capability = self.registry.load_capability(capability_ref)
        result = PolicyEngine().evaluate(policy_manifest, capability_ref, capability)
        response: dict[str, Any] = {
            "policy": policy_entry.ref,
            "capability": capability_ref,
            "decision": result.decision.value,
            "reason": result.reason,
        }
        if agent is not None:
            agent_manifest = self.registry.load_agent(agent)
            response["agent"] = agent_manifest.metadata.id
            response["bound_provider_tool"] = agent_manifest.spec.capability_bindings.get(
                capability_ref
            )
        return response

    def discover(self, kind: str | None = None) -> list[ArtifactEntry]:
        kinds = MANAGED_KINDS if kind in {None, "all"} else (kind,)
        state = self._load_state()
        entries: list[ArtifactEntry] = []
        for current_kind in kinds:
            entries.extend(self._discover_kind(current_kind, state))
        return sorted(entries, key=lambda item: (item.kind, item.ref, str(item.path)))

    def resolve(self, kind: str, target: str | Path) -> ArtifactEntry:
        path = Path(target)
        if path.exists():
            resolved_path = path / "skill.yaml" if path.is_dir() else path
            for entry in self.discover(kind):
                if entry.path.resolve() == resolved_path.resolve():
                    return entry
            artifact = validate_document(load_document(resolved_path), self._schema_type(kind))
            artifact_id, version = self._artifact_identity(kind, artifact)
            return ArtifactEntry(
                kind=kind,
                artifact_id=artifact_id,
                version=version,
                ref=f"{artifact_id}@{version}",
                path=resolved_path,
                lifecycle_status=self._default_status(kind, artifact),
                source="path",
                dependencies=self._dependencies(kind, artifact),
            )
        value = str(target)
        for entry in self.discover(kind):
            if value in {entry.ref, entry.artifact_id, str(entry.path)}:
                return entry
        raise FileNotFoundError(f"Could not resolve {kind}: {target}")

    def _discover_kind(
        self, kind: str, state: dict[str, dict[str, Any]]
    ) -> list[ArtifactEntry]:
        entries: list[ArtifactEntry] = []
        if kind == "agent":
            for directory, source in [
                (self.examples_dir / "agents", "registry"),
                (self.store_root / "agents", "local"),
            ]:
                entries.extend(
                    self._discover_files(kind, directory, "agent", source, state)
                )
            return entries
        if kind == "skill":
            skills_dir = self.examples_dir / "skills"
            if skills_dir.exists():
                for manifest_path in sorted(skills_dir.glob("*/skill.yaml")):
                    entry = self._entry_from_path(
                        "skill", manifest_path, "skill", "registry", state
                    )
                    if entry is not None:
                        entries.append(entry)
            return entries
        mapping = {
            "policy": (self.examples_dir / "policies", "policy"),
            "workflow": (self.examples_dir / "workflows", "workflow"),
            "capability": (self.examples_dir / "capabilities", "capability-contract"),
            "tool-provider": (self.examples_dir / "tools", "tool-provider"),
            "eval-suite": (self.examples_dir / "eval-suites", "eval-suite"),
            "model-policy": (self.examples_dir / "model-policies", "model-policy"),
        }
        if kind not in mapping:
            raise ValueError(f"Unknown artifact kind: {kind}")
        directory, artifact_type = mapping[kind]
        return self._discover_files(kind, directory, artifact_type, "registry", state)

    def _discover_files(
        self,
        kind: str,
        directory: Path,
        artifact_type: str,
        source: str,
        state: dict[str, dict[str, Any]],
    ) -> list[ArtifactEntry]:
        if not directory.exists():
            return []
        entries: list[ArtifactEntry] = []
        for path in sorted(directory.glob("*.yaml")) + sorted(directory.glob("*.yml")):
            entry = self._entry_from_path(kind, path, artifact_type, source, state)
            if entry is not None:
                entries.append(entry)
        return entries

    def _entry_from_path(
        self,
        kind: str,
        path: Path,
        artifact_type: str,
        source: str,
        state: dict[str, dict[str, Any]],
    ) -> ArtifactEntry | None:
        try:
            artifact = validate_document(load_document(path), artifact_type)
            artifact_id, version = self._artifact_identity(kind, artifact)
            record = state.get(self._state_key(kind, artifact_id, version), {})
            status = record.get("lifecycle_status") or self._default_status(kind, artifact)
            return ArtifactEntry(
                kind=kind,
                artifact_id=artifact_id,
                version=version,
                ref=f"{artifact_id}@{version}",
                path=path,
                lifecycle_status=status,
                source=source,
                dependencies=self._dependencies(kind, artifact),
            )
        except Exception:  # noqa: BLE001
            return None

    def _load_entry(self, entry: ArtifactEntry) -> BaseModel:
        return validate_document(load_document(entry.path), self._schema_type(entry.kind))

    def _load_agent_path(self, path: Path) -> AgentManifest:
        artifact = validate_document(load_document(path), "agent")
        if not isinstance(artifact, AgentManifest):
            raise TypeError(f"{path} is not an agent")
        return artifact

    def _load_policy_path(self, path: Path) -> PolicyManifest:
        artifact = validate_document(load_document(path), "policy")
        if not isinstance(artifact, PolicyManifest):
            raise TypeError(f"{path} is not a policy")
        return artifact

    def _load_workflow_path(self, path: Path) -> WorkflowDefinition:
        artifact = validate_document(load_document(path), "workflow")
        if not isinstance(artifact, WorkflowDefinition):
            raise TypeError(f"{path} is not a workflow")
        return artifact

    def _artifact_identity(self, kind: str, artifact: BaseModel) -> tuple[str, str]:
        if isinstance(artifact, SkillManifest):
            return artifact.id, artifact.version
        if isinstance(artifact, WorkflowDefinition):
            return artifact.id, artifact.version
        if isinstance(artifact, AgentManifest):
            return artifact.metadata.id, "local"
        if isinstance(
            artifact,
            (
                CapabilityContractManifest,
                EvalSuiteManifest,
                ModelPolicyManifest,
                PolicyManifest,
                ToolProviderManifest,
            ),
        ):
            return artifact.metadata.id, artifact.metadata.version
        raise TypeError(f"Unsupported {kind} artifact: {artifact.__class__.__name__}")

    def _schema_type(self, kind: str) -> str:
        return {
            "agent": "agent",
            "skill": "skill",
            "policy": "policy",
            "workflow": "workflow",
            "capability": "capability-contract",
            "tool-provider": "tool-provider",
            "eval-suite": "eval-suite",
            "model-policy": "model-policy",
        }[kind]

    def _default_status(self, kind: str, artifact: BaseModel) -> str:
        if isinstance(artifact, SkillManifest):
            return artifact.lifecycle_status.value
        if isinstance(artifact, AgentManifest):
            return artifact.metadata.status
        return "draft"

    def _dependencies(self, kind: str, artifact: BaseModel) -> dict[str, list[str]]:
        if isinstance(artifact, AgentManifest):
            return {
                "skills": artifact.spec.skills,
                "policies": [artifact.spec.policy],
                "workflows": [artifact.spec.workflow],
                "model_policies": [artifact.spec.model_policy] if artifact.spec.model_policy else [],
                "capabilities": sorted(artifact.spec.capability_bindings),
                "eval_suites": [artifact.spec.eval_profile] if artifact.spec.eval_profile else [],
            }
        if isinstance(artifact, SkillManifest):
            return {
                "capabilities": [
                    *artifact.requires.capabilities,
                    *artifact.optional_capabilities,
                ],
                "workflows": [artifact.default_workflow],
                "output_schemas": [artifact.output_schema],
            }
        if isinstance(artifact, PolicyManifest):
            capabilities = [
                rule.match["capability"]
                for rule in artifact.spec.rules
                if "capability" in rule.match
            ]
            return {"capabilities": capabilities}
        if isinstance(artifact, WorkflowDefinition):
            return {
                "capabilities": [
                    node.capability for node in artifact.nodes if node.capability is not None
                ]
            }
        if isinstance(artifact, ToolProviderManifest):
            return {
                "capabilities": [
                    capability.contract for capability in artifact.spec.capabilities
                ]
            }
        if isinstance(artifact, EvalSuiteManifest):
            return {"eval_cases": artifact.spec.cases}
        if isinstance(artifact, ModelPolicyManifest):
            return {
                "providers": artifact.spec.allowed_providers,
                "models": artifact.spec.allowed_models,
            }
        return {}

    def _validate_skill_dependencies(self, skill: SkillManifest) -> list[str]:
        errors: list[str] = []
        for capability_ref in [
            *skill.requires.capabilities,
            *skill.optional_capabilities,
        ]:
            try:
                self.registry.load_capability(capability_ref)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"Capability cannot be resolved: {capability_ref}: {exc}")
        try:
            self.registry.load_workflow(skill.default_workflow)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Default workflow cannot be resolved: {skill.default_workflow}: {exc}")
        return errors

    def _validate_policy_dependencies(self, policy: PolicyManifest) -> list[str]:
        errors: list[str] = []
        for rule in policy.spec.rules:
            capability_ref = rule.match.get("capability")
            if capability_ref is None:
                continue
            try:
                self.registry.load_capability(capability_ref)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"Capability cannot be resolved: {capability_ref}: {exc}")
        return errors

    def _validate_workflow_dependencies(self, workflow: WorkflowDefinition) -> list[str]:
        errors: list[str] = []
        node_ids = [node.id for node in workflow.nodes]
        if len(node_ids) != len(set(node_ids)):
            errors.append("Workflow node IDs must be unique")
        for node in workflow.nodes:
            if node.capability is None:
                continue
            try:
                self.registry.load_capability(node.capability)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"Capability cannot be resolved: {node.capability}: {exc}")
        return errors

    def _agent_references(self, agent: AgentManifest, kind: str, ref: str) -> bool:
        if kind == "skill":
            return ref in agent.spec.skills
        if kind == "policy":
            return ref == agent.spec.policy
        if kind == "workflow":
            return ref == agent.spec.workflow
        if kind == "capability":
            return ref in agent.spec.capability_bindings
        if kind == "eval-suite":
            return ref == agent.spec.eval_profile
        if kind == "model-policy":
            return ref == agent.spec.model_policy
        return False

    def _eval_suites_for_agents(
        self, impacted_agents: list[dict[str, Any]]
    ) -> list[dict[str, str]]:
        eval_profiles = {
            agent["eval_profile"]
            for agent in impacted_agents
            if agent.get("eval_profile")
        }
        suites: list[dict[str, str]] = []
        for suite in self.discover("eval-suite"):
            if suite.ref in eval_profiles:
                suites.append({"suite": suite.ref, "path": str(suite.path)})
        return suites

    def _version_skill(self, manifest_path: Path, new_version: str, overwrite: bool) -> Path:
        source_dir = manifest_path.parent
        skill = validate_document(load_document(manifest_path), "skill")
        if not isinstance(skill, SkillManifest):
            raise TypeError(f"{manifest_path} is not a skill manifest")
        target_dir = self.examples_dir / "skills" / f"{skill.id}-{new_version}"
        if target_dir.exists():
            if not overwrite:
                raise FileExistsError(f"Version target already exists: {target_dir}")
            shutil.rmtree(target_dir)
        shutil.copytree(source_dir, target_dir)
        target_manifest = target_dir / "skill.yaml"
        document = load_document(target_manifest)
        document["version"] = new_version
        document["lifecycle_status"] = "draft"
        target_manifest.write_text(dump_yaml(document), encoding="utf-8")
        return target_manifest

    def _version_yaml_artifact(
        self,
        path: Path,
        kind: str,
        artifact_id: str,
        new_version: str,
        overwrite: bool,
    ) -> Path:
        target_path = path.parent / f"{artifact_id}-{new_version}.yaml"
        if target_path.exists() and not overwrite:
            raise FileExistsError(f"Version target already exists: {target_path}")
        document = load_document(path)
        if kind == "workflow":
            document["version"] = new_version
        else:
            document.setdefault("metadata", {})["version"] = new_version
        target_path.write_text(dump_yaml(document), encoding="utf-8")
        return target_path

    def _bump_version(self, version: str, bump: str) -> str:
        parts = [int(part) for part in version.split(".")]
        while len(parts) < 3:
            parts.append(0)
        if bump == "major":
            return f"{parts[0] + 1}.0.0"
        if bump == "minor":
            return f"{parts[0]}.{parts[1] + 1}.0"
        if bump == "patch":
            return f"{parts[0]}.{parts[1]}.{parts[2] + 1}"
        raise ValueError("bump must be one of: major, minor, patch")

    def _load_state(self) -> dict[str, dict[str, Any]]:
        if not self.state_path.exists():
            return {}
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def _write_state(self, state: dict[str, dict[str, Any]]) -> None:
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(
            json.dumps(state, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
        )

    def _update_state(
        self, kind: str, artifact_id: str, version: str, record: dict[str, Any]
    ) -> None:
        state = self._load_state()
        key = self._state_key(kind, artifact_id, version)
        state[key] = {**state.get(key, {}), **record, "updated_at": utc_now()}
        self._write_state(state)

    def _persist_index(self, entries: list[ArtifactEntry]) -> None:
        self.index_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "generated_at": utc_now(),
            "registry_root": str(self.registry_root),
            "artifacts": [entry.to_dict() for entry in entries],
        }
        self.index_path.write_text(
            json.dumps(data, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
        )

    def _state_key(self, kind: str, artifact_id: str, version: str) -> str:
        return f"{kind}:{artifact_id}@{version}"

    def _split_ref(self, ref: str) -> tuple[str, str]:
        parsed = ArtifactRef.parse(ref)
        return parsed.id, parsed.version
