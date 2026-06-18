from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ToolExecutionResult:
    capability: str
    provider_tool: str
    output: dict[str, Any]
    summary: str


class ToolExecutor:
    def __init__(self, workspace: str | Path = ".", dry_run: bool = True) -> None:
        self.workspace = Path(workspace).resolve()
        self.dry_run = dry_run

    def execute(
        self,
        capability_ref: str,
        provider_tool: str,
        task_input: str,
        prior_outputs: list[dict[str, Any]],
    ) -> ToolExecutionResult:
        capability_id = capability_ref.split("@", 1)[0]
        handlers = {
            "web.search": self._web_search,
            "web.fetch": self._web_fetch,
            "citation.extract": self._citation_extract,
            "file.read": self._file_read,
            "file.patch": self._file_patch,
            "shell.run": self._shell_run,
            "git.diff": self._git_diff,
        }
        handler = handlers.get(capability_id, self._generic)
        output, summary = handler(task_input, prior_outputs)
        return ToolExecutionResult(
            capability=capability_ref,
            provider_tool=provider_tool,
            output=output,
            summary=summary,
        )

    def _web_search(
        self, task_input: str, prior_outputs: list[dict[str, Any]]
    ) -> tuple[dict[str, Any], str]:
        result = {
            "results": [
                {
                    "title": "Mock source about agent capability contracts",
                    "url": "mock://source/capability-contracts",
                    "snippet": f"Relevant source for: {task_input}",
                }
            ],
            "metadata": {"mock": True},
        }
        return result, "Found 1 mock source relevant to the research task."

    def _web_fetch(
        self, task_input: str, prior_outputs: list[dict[str, Any]]
    ) -> tuple[dict[str, Any], str]:
        url = "mock://source/capability-contracts"
        for output in reversed(prior_outputs):
            results = output.get("results")
            if isinstance(results, list) and results:
                url = str(results[0].get("url", url))
                break
        result = {
            "content": (
                "Capability contracts decouple agent skills from concrete tool "
                "providers and make policy, compatibility and evidence behavior "
                "explicit."
            ),
            "metadata": {"url": url, "trusted": False, "mock": True},
        }
        return result, f"Fetched mock content from {url}."

    def _citation_extract(
        self, task_input: str, prior_outputs: list[dict[str, Any]]
    ) -> tuple[dict[str, Any], str]:
        result = {
            "citations": [
                {
                    "label": "Mock capability contract source",
                    "uri": "mock://source/capability-contracts",
                }
            ],
            "metadata": {"mock": True},
        }
        return result, "Extracted 1 citation from fetched content."

    def _file_read(
        self, task_input: str, prior_outputs: list[dict[str, Any]]
    ) -> tuple[dict[str, Any], str]:
        target = self._resolve_workspace_path("README.md")
        content = target.read_text(encoding="utf-8") if target.exists() else ""
        result = {
            "content": content,
            "metadata": {"path": str(target), "exists": target.exists()},
        }
        return result, f"Read workspace file {target.name}."

    def _file_patch(
        self, task_input: str, prior_outputs: list[dict[str, Any]]
    ) -> tuple[dict[str, Any], str]:
        target = self._resolve_workspace_path("README.md")
        result = {
            "applied": False,
            "metadata": {
                "path": str(target),
                "dry_run": self.dry_run,
                "reason": "Phase 1 executor does not apply generated patches by default.",
            },
        }
        return result, "Evaluated file.patch in dry-run mode."

    def _shell_run(
        self, task_input: str, prior_outputs: list[dict[str, Any]]
    ) -> tuple[dict[str, Any], str]:
        command = ["python", "-m", "pytest"]
        if self.dry_run:
            result = {
                "exit_code": None,
                "stdout": "",
                "stderr": "",
                "metadata": {"dry_run": True, "command": " ".join(command)},
            }
            return result, "Prepared shell.run in dry-run mode."
        completed = subprocess.run(
            command,
            cwd=self.workspace,
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )
        result = {
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
        return result, f"Executed shell command with exit code {completed.returncode}."

    def _git_diff(
        self, task_input: str, prior_outputs: list[dict[str, Any]]
    ) -> tuple[dict[str, Any], str]:
        completed = subprocess.run(
            ["git", "diff", "--"],
            cwd=self.workspace,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        result = {
            "diff": completed.stdout,
            "metadata": {"exit_code": completed.returncode},
        }
        return result, "Collected git diff from workspace."

    def _generic(
        self, task_input: str, prior_outputs: list[dict[str, Any]]
    ) -> tuple[dict[str, Any], str]:
        return {"metadata": {"mock": True}}, "Executed generic mock capability."

    def _resolve_workspace_path(self, relative_path: str) -> Path:
        target = (self.workspace / relative_path).resolve()
        if not str(target).startswith(str(self.workspace)):
            raise ValueError(f"Path escapes workspace: {target}")
        return target

