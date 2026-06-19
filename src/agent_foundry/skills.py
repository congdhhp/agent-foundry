from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from .loader import load_document
from .models import AgentManifest, SkillManifest
from .refs import ArtifactRef
from .validation import validate_document


REQUIRED_SKILL_FILES = ("SKILL.md",)


@dataclass(frozen=True)
class SkillPackage:
    root: Path
    manifest: SkillManifest
    instructions: str
    frontmatter: dict[str, Any]
    output_schema: dict[str, Any]
    eval_files: list[Path]

    @property
    def ref(self) -> str:
        return f"{self.manifest.id}@{self.manifest.version}"


@dataclass(frozen=True)
class SkillPackageValidation:
    path: Path
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    skill_ref: str | None = None


@dataclass(frozen=True)
class SkillSelection:
    skill: SkillManifest
    score: int
    reasons: list[str]

    @property
    def ref(self) -> str:
        return f"{self.skill.id}@{self.skill.version}"


class SkillRegistry:
    def __init__(self, root: str | Path = ".", store_root: str | Path | None = None) -> None:
        self.root = Path(root)
        self.store_root = Path(store_root) if store_root is not None else self.root / ".agent"
        self.skill_dirs = [
            self.store_root / "registry" / "skills",
            self.root / ".agents" / "skills",
            self.root / "examples" / "skills",
        ]

    def list_packages(self) -> list[SkillPackage]:
        packages: list[SkillPackage] = []
        seen: set[str] = set()
        for skills_dir in self.skill_dirs:
            if not skills_dir.exists():
                continue
            for skill_dir in sorted(path for path in skills_dir.iterdir() if path.is_dir()):
                package = self.load_package(skill_dir)
                if package.ref in seen:
                    continue
                seen.add(package.ref)
                packages.append(package)
        return packages

    def load_package(self, path_or_ref: str | Path) -> SkillPackage:
        path = Path(path_or_ref)
        if path.exists():
            skill_dir = path
            if skill_dir.is_file():
                skill_dir = skill_dir.parent
            return self._load_package_dir(skill_dir)
        ref = ArtifactRef.parse(str(path_or_ref))
        for skills_dir in self.skill_dirs:
            if not skills_dir.exists():
                continue
            for skill_dir in sorted(path for path in skills_dir.iterdir() if path.is_dir()):
                package = self._load_package_dir(skill_dir)
                if ref.matches(package.manifest.id, package.manifest.version):
                    return package
        raise FileNotFoundError(f"Could not resolve skill package {path_or_ref}")

    def validate_package(self, path_or_ref: str | Path) -> SkillPackageValidation:
        path = Path(path_or_ref)
        try:
            package = self.load_package(path_or_ref)
        except Exception as exc:  # noqa: BLE001 - validation should capture all package errors
            return SkillPackageValidation(path=path, valid=False, errors=[str(exc)])

        errors: list[str] = []
        warnings: list[str] = []
        for required in REQUIRED_SKILL_FILES:
            if not (package.root / required).exists():
                errors.append(f"Missing required file: {required}")
        if not package.eval_files:
            warnings.append("Skill has no eval files under evals/")
        for eval_file in package.eval_files:
            try:
                validate_document(load_document(eval_file), "eval-case")
            except Exception as exc:  # noqa: BLE001
                errors.append(f"Invalid eval file {eval_file.name}: {exc}")
        if not package.instructions.strip():
            errors.append("SKILL.md is empty")
        if "name" not in package.frontmatter:
            errors.append("SKILL.md frontmatter must include name")
        if "description" not in package.frontmatter:
            errors.append("SKILL.md frontmatter must include description")
        if not (package.root / "skill.yaml").exists():
            warnings.append("Missing governance sidecar: skill.yaml")
        if not (package.root / "output_schema.json").exists():
            warnings.append("Missing optional output schema: output_schema.json")
        if not package.manifest.requires.capabilities:
            warnings.append("Skill is instruction-only and has no required capabilities")

        return SkillPackageValidation(
            path=package.root,
            valid=not errors,
            errors=errors,
            warnings=warnings,
            skill_ref=package.ref,
        )

    def _load_package_dir(self, skill_dir: Path) -> SkillPackage:
        manifest_path = skill_dir / "skill.yaml"
        instructions_path = skill_dir / "SKILL.md"
        if not instructions_path.exists():
            raise FileNotFoundError(f"Missing skill instructions: {instructions_path}")
        frontmatter, instructions = self._read_skill_markdown(instructions_path)
        if manifest_path.exists():
            manifest = validate_document(load_document(manifest_path), "skill")
        else:
            manifest = self._derive_manifest(skill_dir, frontmatter)
        if not isinstance(manifest, SkillManifest):
            raise TypeError(f"{manifest_path} is not a skill manifest")
        output_schema_path = skill_dir / "output_schema.json"
        output_schema = (
            load_document(output_schema_path) if output_schema_path.exists() else {}
        )
        evals_dir = skill_dir / "evals"
        eval_files = sorted(evals_dir.glob("*.yaml")) if evals_dir.exists() else []
        return SkillPackage(
            root=skill_dir,
            manifest=manifest,
            instructions=instructions,
            frontmatter=frontmatter,
            output_schema=output_schema,
            eval_files=eval_files,
        )

    def _read_skill_markdown(self, path: Path) -> tuple[dict[str, Any], str]:
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        if not lines or lines[0].strip() != "---":
            return {}, text
        closing_index = None
        for index, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                closing_index = index
                break
        if closing_index is None:
            return {}, text
        raw_frontmatter = "\n".join(lines[1:closing_index])
        loaded = yaml.safe_load(raw_frontmatter) or {}
        if not isinstance(loaded, dict):
            loaded = {}
        return loaded, text

    def _derive_manifest(
        self,
        skill_dir: Path,
        frontmatter: dict[str, Any],
    ) -> SkillManifest:
        raw_name = str(frontmatter.get("name") or skill_dir.name)
        skill_id = str(frontmatter.get("id") or self._slugify(raw_name, skill_dir.name))
        capabilities = self._frontmatter_capabilities(frontmatter)
        manifest = {
            "id": skill_id,
            "version": str(frontmatter.get("version") or "1.0.0"),
            "name": raw_name,
            "description": str(
                frontmatter.get("description") or f"{skill_id} skill."
            ),
            "owner": str(frontmatter.get("owner") or "local-user"),
            "risk_level": str(frontmatter.get("risk_level") or "low"),
            "lifecycle_status": str(frontmatter.get("lifecycle_status") or "draft"),
            "triggers": {"intents": [], "keywords": []},
            "requires": {"capabilities": capabilities},
            "optional_capabilities": [],
            "output_schema": str(
                frontmatter.get("output_schema") or f"{skill_id}-output@1.0.0"
            ),
        }
        validated = validate_document(manifest, "skill")
        if not isinstance(validated, SkillManifest):
            raise TypeError(f"Could not derive skill manifest for {skill_dir}")
        return validated

    def _frontmatter_capabilities(self, frontmatter: dict[str, Any]) -> list[str]:
        capabilities = frontmatter.get("capabilities")
        if isinstance(capabilities, list):
            return [str(item) for item in capabilities]
        requires = frontmatter.get("requires")
        if isinstance(requires, dict) and isinstance(requires.get("capabilities"), list):
            return [str(item) for item in requires["capabilities"]]
        return []

    def _slugify(self, value: str, fallback: str) -> str:
        slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip().lower()).strip("-")
        return slug or fallback


class SkillSelector:
    def select(
        self,
        agent: AgentManifest,
        available_skills: list[SkillManifest],
        task_input: str,
    ) -> list[SkillSelection]:
        task_lower = task_input.lower()
        configured = set(agent.spec.skills)
        selections: list[SkillSelection] = []
        for skill in available_skills:
            ref = f"{skill.id}@{skill.version}"
            score = 0
            reasons: list[str] = []
            if ref in configured:
                score += 100
                reasons.append("agent_manifest")
            for keyword in skill.triggers.keywords:
                if keyword.lower() in task_lower:
                    score += 10
                    reasons.append(f"keyword:{keyword}")
            for intent in skill.triggers.intents:
                normalized = intent.replace("_", " ").lower()
                if normalized in task_lower:
                    score += 15
                    reasons.append(f"intent:{intent}")
            if f"${skill.id.lower()}" in task_lower:
                score += 100
                reasons.append("explicit_invocation")
            description_terms = self._important_terms(skill.description)
            matched_terms = [
                term for term in description_terms if term in task_lower
            ]
            if matched_terms:
                score += min(len(matched_terms), 4) * 5
                reasons.append("description_match")
            if score > 0:
                selections.append(SkillSelection(skill=skill, score=score, reasons=reasons))
        return sorted(selections, key=lambda item: item.score, reverse=True)

    def _important_terms(self, text: str) -> list[str]:
        stop_words = {
            "and",
            "for",
            "from",
            "into",
            "that",
            "the",
            "this",
            "with",
            "when",
            "your",
        }
        terms = re.findall(r"[a-z0-9][a-z0-9_.-]{2,}", text.lower())
        return [term for term in terms if term not in stop_words]
