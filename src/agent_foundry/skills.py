from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .loader import load_document
from .models import AgentManifest, SkillManifest
from .refs import ArtifactRef
from .validation import validate_document


REQUIRED_SKILL_FILES = ("SKILL.md", "skill.yaml", "output_schema.json")


@dataclass(frozen=True)
class SkillPackage:
    root: Path
    manifest: SkillManifest
    instructions: str
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
    def __init__(self, root: str | Path = ".") -> None:
        self.root = Path(root)
        self.skills_dir = self.root / "examples" / "skills"

    def list_packages(self) -> list[SkillPackage]:
        packages: list[SkillPackage] = []
        if not self.skills_dir.exists():
            return packages
        for skill_dir in sorted(path for path in self.skills_dir.iterdir() if path.is_dir()):
            packages.append(self.load_package(skill_dir))
        return packages

    def load_package(self, path_or_ref: str | Path) -> SkillPackage:
        path = Path(path_or_ref)
        if path.exists():
            skill_dir = path
            if skill_dir.is_file():
                skill_dir = skill_dir.parent
            return self._load_package_dir(skill_dir)
        ref = ArtifactRef.parse(str(path_or_ref))
        if not self.skills_dir.exists():
            raise FileNotFoundError(f"Could not resolve skill package {path_or_ref}")
        for skill_dir in sorted(path for path in self.skills_dir.iterdir() if path.is_dir()):
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
            errors.append("Missing eval files under evals/")
        for eval_file in package.eval_files:
            try:
                validate_document(load_document(eval_file), "eval-case")
            except Exception as exc:  # noqa: BLE001
                errors.append(f"Invalid eval file {eval_file.name}: {exc}")
        if not package.instructions.strip():
            errors.append("SKILL.md is empty")
        if not package.manifest.requires.capabilities:
            warnings.append("Skill has no required capabilities")

        return SkillPackageValidation(
            path=package.root,
            valid=not errors,
            errors=errors,
            warnings=warnings,
            skill_ref=package.ref,
        )

    def _load_package_dir(self, skill_dir: Path) -> SkillPackage:
        manifest_path = skill_dir / "skill.yaml"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Missing skill manifest: {manifest_path}")
        manifest = validate_document(load_document(manifest_path), "skill")
        if not isinstance(manifest, SkillManifest):
            raise TypeError(f"{manifest_path} is not a skill manifest")
        instructions_path = skill_dir / "SKILL.md"
        instructions = (
            instructions_path.read_text(encoding="utf-8")
            if instructions_path.exists()
            else ""
        )
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
            output_schema=output_schema,
            eval_files=eval_files,
        )


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
            if score > 0:
                selections.append(SkillSelection(skill=skill, score=score, reasons=reasons))
        return sorted(selections, key=lambda item: item.score, reverse=True)
