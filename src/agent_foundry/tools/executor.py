from __future__ import annotations

from time import perf_counter
from typing import Any

from agent_foundry.core.models import ApprovedToolCall, ToolResult


class MockToolExecutor:
    """Deterministic MVP tool executor.

    Real integrations can replace this class once policy/evidence flow is proven.
    """

    def execute(self, call: ApprovedToolCall) -> ToolResult:
        started = perf_counter()
        output, summary = self._mock_output(call.tool, call.input)
        latency_ms = int((perf_counter() - started) * 1000)
        return ToolResult(
            call_id=call.id,
            task_id=call.task_id,
            tool=call.tool,
            status="success",
            output=output,
            summary=summary,
            raw_ref=f"object://{call.task_id}/{call.id}",
            latency_ms=latency_ms,
        )

    def _mock_output(self, tool: str, inputs: dict[str, Any]) -> tuple[dict[str, Any], str]:
        if tool == "deployments.read":
            return (
                {
                    "service": inputs.get("service", "checkout"),
                    "environment": inputs.get("environment", "prod"),
                    "latest_deploy": "v1.2.3",
                    "deployed_at": "2026-06-23T05:02:00Z",
                    "changes": ["payment retry tuning", "checkout handler refactor"],
                },
                "Latest checkout production deployment is v1.2.3 at 2026-06-23T05:02:00Z.",
            )
        if tool == "metrics.query":
            return (
                {
                    "metric": "checkout.5xx_rate",
                    "baseline": 0.2,
                    "current": 8.4,
                    "unit": "percent",
                    "window": inputs.get("window", "30m"),
                    "started_after": "2026-06-23T05:05:00Z",
                },
                "Checkout 5xx rate increased from 0.2% to 8.4% shortly after deployment.",
            )
        if tool == "logs.search":
            return (
                {
                    "query": inputs.get("query", "status:5xx service:checkout"),
                    "matches": 1248,
                    "top_errors": [
                        "PaymentGatewayTimeout",
                        "CheckoutHandlerRetryExhausted",
                    ],
                    "redacted": True,
                },
                "Logs show elevated PaymentGatewayTimeout and retry exhaustion errors; sensitive fields redacted.",
            )
        if tool == "runbooks.read":
            return (
                {
                    "runbook": "checkout-5xx",
                    "recommendations": [
                        "Confirm deploy correlation.",
                        "Check payment gateway health.",
                        "Prepare rollback if error rate remains above threshold.",
                    ],
                },
                "Runbook recommends rollback preparation only after confirming deploy correlation and gateway health.",
            )
        if tool == "web.search":
            return (
                {
                    "query": inputs.get("query", ""),
                    "results": [
                        {
                            "title": "Agentic runtime architecture patterns",
                            "url": "https://example.com/agentic-runtime-patterns",
                        }
                    ],
                },
                "Found source discussing agentic runtime architecture patterns.",
            )
        if tool in {"document.read", "knowledge.search", "citation.extract"}:
            return (
                {"source": tool, "content": "Evidence-backed agent design favors explicit tools and policy gates."},
                f"{tool} returned source material for the research report.",
            )
        if tool == "deployment.rollback":
            return (
                {"status": "rollback_started", "environment": inputs.get("environment", "prod")},
                "Rollback command was executed.",
            )
        return ({"echo": inputs}, f"{tool} executed.")
