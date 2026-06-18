from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .models import CapabilityContractManifest, PolicyDecision, PolicyManifest, PolicyRule


DECISION_PRIORITY = {
    PolicyDecision.ALLOW: 1,
    PolicyDecision.REQUIRE_TRANSFORM: 2,
    PolicyDecision.REQUIRE_APPROVAL: 3,
    PolicyDecision.REQUIRE_STEP_UP_AUTH: 4,
    PolicyDecision.DENY: 5,
}


@dataclass(frozen=True)
class PolicyResult:
    decision: PolicyDecision
    matched_rules: list[PolicyRule] = field(default_factory=list)
    reason: str = ""
    transforms: list[str] = field(default_factory=list)
    approvers: list[str] = field(default_factory=list)

    @property
    def allowed(self) -> bool:
        return self.decision == PolicyDecision.ALLOW

    @property
    def approval_required(self) -> bool:
        return self.decision == PolicyDecision.REQUIRE_APPROVAL

    @property
    def step_up_required(self) -> bool:
        return self.decision == PolicyDecision.REQUIRE_STEP_UP_AUTH

    @property
    def transform_required(self) -> bool:
        return self.decision == PolicyDecision.REQUIRE_TRANSFORM


class PolicyEngine:
    def evaluate(
        self,
        policy: PolicyManifest,
        capability_ref: str,
        capability: CapabilityContractManifest,
        extra_context: dict[str, Any] | None = None,
    ) -> PolicyResult:
        context: dict[str, Any] = {
            "capability": capability_ref,
            "capabilityId": capability.metadata.id,
            "accessType": capability.spec.access_type.value,
            "riskLevel": capability.spec.risk_level.value,
            "category": capability.spec.category,
        }
        if extra_context:
            context.update(extra_context)

        matched = [rule for rule in policy.spec.rules if self._matches(rule, context)]
        if not matched:
            return PolicyResult(
                decision=PolicyDecision.DENY,
                matched_rules=[],
                reason="No policy rule matched; default deny.",
            )

        decision = max(matched, key=lambda rule: DECISION_PRIORITY[rule.decision]).decision
        transforms = self._unique(item for rule in matched for item in rule.transforms)
        approvers = self._unique(item for rule in matched for item in rule.approvers)
        return PolicyResult(
            decision=decision,
            matched_rules=matched,
            reason=f"Matched {len(matched)} policy rule(s).",
            transforms=transforms,
            approvers=approvers,
        )

    def _matches(self, rule: PolicyRule, context: dict[str, Any]) -> bool:
        for key, expected in rule.match.items():
            actual = context.get(key)
            if actual != expected:
                return False
        return True

    def _unique(self, values: Any) -> list[Any]:
        unique_values: list[Any] = []
        for value in values:
            if value not in unique_values:
                unique_values.append(value)
        return unique_values
