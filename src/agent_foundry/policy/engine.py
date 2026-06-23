from __future__ import annotations

from agent_foundry.core.ids import new_id
from agent_foundry.core.models import (
    PolicyDecision,
    PolicyDecisionKind,
    PolicyDocument,
    PolicyMatch,
    ProposedToolCall,
    ToolDefinition,
)


class PolicyEngine:
    def evaluate(
        self,
        proposed: ProposedToolCall,
        tool: ToolDefinition,
        policies: list[PolicyDocument],
    ) -> PolicyDecision:
        for policy in policies:
            for rule in policy.rules:
                if self._matches(rule.match, proposed, tool):
                    return self._decision_from_rule(proposed, tool, rule.decision, rule.obligations, rule.reason)

        if tool.requiresApproval:
            return self._decision(
                proposed,
                tool,
                PolicyDecisionKind.REQUIRE_APPROVAL,
                f"{tool.id} requires approval by tool definition.",
                ["create_audit_event"],
            )

        return self._decision(
            proposed,
            tool,
            PolicyDecisionKind.DENY,
            "No policy rule allowed this tool call.",
            ["create_audit_event"],
        )

    def _matches(self, match: PolicyMatch, proposed: ProposedToolCall, tool: ToolDefinition) -> bool:
        if match.tool is not None and match.tool != proposed.tool:
            return False
        if match.actionType is not None and match.actionType != (proposed.action_type or tool.actionType):
            return False
        if match.accessType is not None and match.accessType != tool.accessType:
            return False
        if match.riskLevel is not None and match.riskLevel != tool.riskLevel:
            return False
        if match.environment is not None and match.environment != proposed.input.get("environment"):
            return False
        return True

    def _decision_from_rule(
        self,
        proposed: ProposedToolCall,
        tool: ToolDefinition,
        decision: str,
        obligations: list[str],
        reason: str | None,
    ) -> PolicyDecision:
        normalized = {
            "allow": PolicyDecisionKind.ALLOW,
            "deny": PolicyDecisionKind.DENY,
            "require_approval": PolicyDecisionKind.REQUIRE_APPROVAL,
            "require_transform": PolicyDecisionKind.REQUIRE_TRANSFORM,
            "require_step_up_auth": PolicyDecisionKind.REQUIRE_STEP_UP_AUTH,
        }.get(decision.lower(), PolicyDecisionKind.DENY)

        if tool.requiresApproval and normalized == PolicyDecisionKind.ALLOW:
            normalized = PolicyDecisionKind.REQUIRE_APPROVAL
            reason = reason or f"{tool.id} requires approval by tool definition."

        return self._decision(
            proposed,
            tool,
            normalized,
            reason or f"Matched policy rule for {tool.id}.",
            obligations,
        )

    def _decision(
        self,
        proposed: ProposedToolCall,
        tool: ToolDefinition,
        kind: PolicyDecisionKind,
        reason: str,
        obligations: list[str],
    ) -> PolicyDecision:
        return PolicyDecision(
            decision_id=new_id("pol"),
            task_id=proposed.task_id,
            tool_call_id=proposed.id,
            tool=proposed.tool,
            action_type=proposed.action_type or tool.actionType,
            decision=kind,
            reason=reason,
            obligations=obligations,
        )
