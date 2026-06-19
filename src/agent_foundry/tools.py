from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter
from typing import Any

from .models import (
    ToolProviderManifest,
    ToolProviderOutputSanitization,
    ToolProviderProtocol,
)
from .registry import LocalRegistry


SUPPORTED_IN_PROCESS_CAPABILITIES = frozenset(
    {
        "web.search",
        "web.fetch",
        "citation.extract",
        "file.read",
        "file.patch",
        "shell.run",
        "git.diff",
        "metrics.query",
        "logs.search",
        "traces.search",
        "deployments.read",
    }
)


@dataclass(frozen=True)
class ToolExecutionResult:
    capability: str
    provider_tool: str
    provider_id: str
    tool_name: str
    output: dict[str, Any]
    summary: str
    duration_ms: int
    success: bool
    sanitized: bool


class ToolExecutor:
    def __init__(self, workspace: str | Path = ".", dry_run: bool = True) -> None:
        self.workspace = Path(workspace).resolve()
        self.dry_run = dry_run

    def execute(
        self,
        provider: ToolProviderManifest,
        capability_ref: str,
        provider_tool: str,
        task_input: str,
        prior_outputs: list[dict[str, Any]],
    ) -> ToolExecutionResult:
        if provider.spec.protocol != ToolProviderProtocol.IN_PROCESS:
            if self.dry_run:
                return self._dry_run_external_provider(
                    provider,
                    capability_ref,
                    provider_tool,
                )
            raise ValueError(
                f"Provider protocol is not supported by local executor: "
                f"{provider.metadata.id}/{provider.spec.protocol}"
            )
        capability_id = capability_ref.split("@", 1)[0]
        if capability_id not in SUPPORTED_IN_PROCESS_CAPABILITIES:
            raise ValueError(
                f"No in-process adapter is registered for capability {capability_id}"
            )
        handlers = {
            "web.search": self._web_search,
            "web.fetch": self._web_fetch,
            "citation.extract": self._citation_extract,
            "file.read": self._file_read,
            "file.patch": self._file_patch,
            "shell.run": self._shell_run,
            "git.diff": self._git_diff,
            "metrics.query": self._metrics_query,
            "logs.search": self._logs_search,
            "traces.search": self._traces_search,
            "deployments.read": self._deployments_read,
        }
        handler = handlers.get(capability_id, self._generic)
        output, summary = handler(task_input, prior_outputs)
        return ToolExecutionResult(
            capability=capability_ref,
            provider_tool=provider_tool,
            provider_id=provider_tool.split(".", 1)[0],
            tool_name=provider_tool.split(".", 1)[1] if "." in provider_tool else provider_tool,
            output=output,
            summary=summary,
            duration_ms=0,
            success=True,
            sanitized=False,
        )

    def _dry_run_external_provider(
        self,
        provider: ToolProviderManifest,
        capability_ref: str,
        provider_tool: str,
    ) -> ToolExecutionResult:
        return ToolExecutionResult(
            capability=capability_ref,
            provider_tool=provider_tool,
            provider_id=provider.metadata.id,
            tool_name=provider_tool.split(".", 1)[1] if "." in provider_tool else provider_tool,
            output={
                "metadata": {
                    "dry_run": True,
                    "protocol": provider.spec.protocol.value,
                    "transport": provider.spec.transport.value,
                    "endpoint": provider.spec.endpoint,
                    "timeout_seconds": provider.spec.runtime_controls.timeout_seconds,
                }
            },
            summary=(
                f"Prepared external provider call for {provider.metadata.id} "
                f"using protocol {provider.spec.protocol.value}/"
                f"{provider.spec.transport.value}."
            ),
            duration_ms=0,
            success=True,
            sanitized=False,
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
            dry_run_result: dict[str, Any] = {
                "exit_code": None,
                "stdout": "",
                "stderr": "",
                "metadata": {"dry_run": True, "command": " ".join(command)},
            }
            return dry_run_result, "Prepared shell.run in dry-run mode."
        completed = subprocess.run(
            command,
            cwd=self.workspace,
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )
        completed_result: dict[str, Any] = {
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
        return completed_result, f"Executed shell command with exit code {completed.returncode}."

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

    def _metrics_query(
        self, task_input: str, prior_outputs: list[dict[str, Any]]
    ) -> tuple[dict[str, Any], str]:
        result = {
            "series": [
                {"metric": "latency_p95_ms", "points": [120, 180, 430, 510]},
                {"metric": "http_5xx_rate", "points": [0.01, 0.02, 0.07, 0.08]},
            ],
            "metadata": {"mock": True, "task": task_input},
        }
        return result, "Collected mock metrics showing latency and 5xx increase."

    def _logs_search(
        self, task_input: str, prior_outputs: list[dict[str, Any]]
    ) -> tuple[dict[str, Any], str]:
        result = {
            "entries": [
                {
                    "service": "checkout",
                    "level": "error",
                    "message": "Timeout calling payment dependency after latest deploy.",
                }
            ],
            "metadata": {"mock": True, "redacted": True},
        }
        return result, "Collected sanitized mock logs for checkout errors."

    def _traces_search(
        self, task_input: str, prior_outputs: list[dict[str, Any]]
    ) -> tuple[dict[str, Any], str]:
        result = {
            "traces": [
                {
                    "trace_id": "trace_mock_001",
                    "slow_span": "payment.authorize",
                    "duration_ms": 940,
                }
            ],
            "metadata": {"mock": True},
        }
        return result, "Collected mock traces with slow payment span."

    def _deployments_read(
        self, task_input: str, prior_outputs: list[dict[str, Any]]
    ) -> tuple[dict[str, Any], str]:
        result = {
            "deployments": [
                {
                    "service": "checkout",
                    "version": "v1.2.3",
                    "timestamp": "2026-06-18T06:00:00Z",
                }
            ],
            "metadata": {"mock": True},
        }
        return result, "Read mock deployment history for checkout service."

    def _generic(
        self, task_input: str, prior_outputs: list[dict[str, Any]]
    ) -> tuple[dict[str, Any], str]:
        return {"metadata": {"mock": True}}, "Executed generic mock capability."

    def _resolve_workspace_path(self, relative_path: str) -> Path:
        target = (self.workspace / relative_path).resolve()
        if not str(target).startswith(str(self.workspace)):
            raise ValueError(f"Path escapes workspace: {target}")
        return target


@dataclass(frozen=True)
class ToolCall:
    task_id: str
    capability_ref: str
    provider_tool: str
    task_input: str
    prior_outputs: list[dict[str, Any]]
    transforms: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ProviderBinding:
    provider: ToolProviderManifest
    tool_name: str

    @property
    def provider_id(self) -> str:
        return self.provider.metadata.id


class OutputSanitizer:
    SECRET_PATTERNS = [
        re.compile(r"(?i)(api[_-]?key\s*[:=]\s*)[A-Za-z0-9_\-]{8,}"),
        re.compile(r"(?i)(token\s*[:=]\s*)[A-Za-z0-9_\-\.]{8,}"),
        re.compile(r"(?i)(password\s*[:=]\s*)\S+"),
        re.compile(r"sk-[A-Za-z0-9]{16,}"),
    ]

    def sanitize(
        self,
        output: dict[str, Any],
        policy: ToolProviderOutputSanitization,
        transforms: list[str] | None = None,
    ) -> tuple[dict[str, Any], bool]:
        requested_transforms = transforms or []
        redact = policy.redact_secrets or "redact_secrets" in requested_transforms
        sanitized_output = self._redact(output) if redact else dict(output)
        if "drop_raw" in requested_transforms:
            sanitized_output.pop("raw", None)
        serialized = json.dumps(sanitized_output, sort_keys=True, default=str)
        changed = serialized != json.dumps(output, sort_keys=True, default=str)
        max_payload_bytes = policy.max_payload_bytes
        for transform in requested_transforms:
            if transform == "truncate_output":
                max_payload_bytes = min(max_payload_bytes, 10000)
            elif transform.startswith("truncate_bytes:"):
                max_payload_bytes = min(
                    max_payload_bytes,
                    int(transform.split(":", 1)[1]),
                )
        if len(serialized.encode("utf-8")) > max_payload_bytes:
            sanitized_output = {
                "truncated": True,
                "metadata": {
                    "originalBytes": len(serialized.encode("utf-8")),
                    "maxPayloadBytes": max_payload_bytes,
                },
            }
            changed = True
        metadata = sanitized_output.setdefault("metadata", {})
        metadata["sanitized"] = True
        changed = True
        if requested_transforms:
            metadata["policyTransforms"] = requested_transforms
        if policy.tag_untrusted or "tag_untrusted" in requested_transforms:
            metadata["trusted"] = False
        return sanitized_output, changed

    def _redact(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {key: self._redact(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._redact(item) for item in value]
        if isinstance(value, str):
            redacted = value
            for pattern in self.SECRET_PATTERNS:
                redacted = pattern.sub(self._replace_secret, redacted)
            return redacted
        return value

    def _replace_secret(self, match: re.Match[str]) -> str:
        if match.lastindex:
            return f"{match.group(1)}[REDACTED]"
        return "[REDACTED]"


class ToolGateway:
    def __init__(
        self,
        registry: LocalRegistry,
        workspace: str | Path = ".",
        dry_run: bool = True,
    ) -> None:
        self.registry = registry
        self.executor = ToolExecutor(workspace, dry_run)
        self.sanitizer = OutputSanitizer()

    def resolve(self, capability_ref: str, provider_tool: str) -> ProviderBinding:
        provider, tool_name = self.registry.resolve_provider_tool(
            capability_ref, provider_tool
        )
        return ProviderBinding(provider=provider, tool_name=tool_name)

    def execute(self, call: ToolCall) -> ToolExecutionResult:
        binding = self.resolve(call.capability_ref, call.provider_tool)
        started = perf_counter()
        try:
            raw = self.executor.execute(
                binding.provider,
                call.capability_ref,
                call.provider_tool,
                call.task_input,
                call.prior_outputs,
            )
            output, sanitized = self.sanitizer.sanitize(
                raw.output,
                binding.provider.spec.output_sanitization,
                call.transforms,
            )
            success = True
            summary = raw.summary
        except Exception as exc:  # noqa: BLE001 - gateway returns structured tool failures
            output = {"error": str(exc), "metadata": {"sanitized": True}}
            sanitized = True
            success = False
            summary = f"Tool execution failed: {exc}"
        duration_ms = int((perf_counter() - started) * 1000)
        return ToolExecutionResult(
            capability=call.capability_ref,
            provider_tool=call.provider_tool,
            provider_id=binding.provider_id,
            tool_name=binding.tool_name,
            output=output,
            summary=summary,
            duration_ms=duration_ms,
            success=success,
            sanitized=sanitized,
        )
