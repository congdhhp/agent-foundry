from __future__ import annotations

from pathlib import Path

from agent_foundry.core.models import EvalRunResult, VerificationResult
from agent_foundry.io.yaml import read_yaml
from agent_foundry.runtime.service import AgentRuntime


class EvalRunner:
    def __init__(self, runtime: AgentRuntime) -> None:
        self.runtime = runtime

    def run_case(self, agent_manifest_path: str | Path, eval_case_path: str | Path) -> EvalRunResult:
        case = read_yaml(eval_case_path)
        state = self.runtime.run(agent_manifest_path, case["task"]["input"])
        expected = case.get("expected", {})
        checks = [
            self._check("selected_skill", state.selectedSkill == expected.get("selectedSkill"), state.selectedSkill or ""),
            self._must_call_tools(state, expected.get("mustCallTools", [])),
            self._must_not_call_tools(state, expected.get("mustNotCallTools", [])),
            self._must_require_approval(state, expected.get("mustRequireApprovalFor", [])),
            self._required_sections(state, expected.get("output", {}).get("requiredSections", [])),
            self._important_claims_have_evidence(state, expected),
        ]
        return EvalRunResult(
            eval_id=case["id"],
            passed=all(check.passed for check in checks),
            checks=checks,
            task_id=state.taskId,
        )

    def _check(self, name: str, passed: bool, message: str) -> VerificationResult:
        return VerificationResult(name=name, passed=passed, message=message)

    def _must_call_tools(self, state, expected_tools: list[str]) -> VerificationResult:
        called = {result.tool for result in state.toolCalls}
        missing = [tool for tool in expected_tools if tool not in called]
        return self._check("must_call_tools", not missing, f"missing={missing}")

    def _must_not_call_tools(self, state, expected_tools: list[str]) -> VerificationResult:
        called = {result.tool for result in state.toolCalls}
        violations = [tool for tool in expected_tools if tool in called]
        return self._check("must_not_call_tools", not violations, f"violations={violations}")

    def _must_require_approval(self, state, expected_tools: list[str]) -> VerificationResult:
        approvals = {approval.tool for approval in state.approvals}
        missing = [tool for tool in expected_tools if tool not in approvals]
        return self._check("must_require_approval", not missing, f"missing={missing}")

    def _important_claims_have_evidence(self, state, expected: dict) -> VerificationResult:
        required = expected.get("grounding", {}).get("importantClaimsRequireEvidence", False)
        if not required:
            return self._check("important_claims_require_evidence", True, "not required")
        has_refs = bool(state.finalOutput and state.finalOutput.get("evidence_refs"))
        return self._check("important_claims_require_evidence", has_refs, "final output evidence refs present")

    def _required_sections(self, state, required_sections: list[str]) -> VerificationResult:
        output = state.finalOutput or {}
        missing = [section for section in required_sections if section not in output]
        return self._check("required_sections", not missing, f"missing={missing}")
